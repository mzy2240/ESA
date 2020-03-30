"""Tests for saw.py. One can use these tests as examples.

IMPORTANT NOTES FOR DEVELOPERS, PLEASE READ:

It can take quite a long time to initialize a SAW object due to the
time it takes for SimAuto to start and then for it to load a case. In
order to keep these tests running in a reasonable amount of time, a
global SAW object, saw_14, is leveraged. This is unfortunate in that
it breaks one of the fundamental rules of good testing: test isolation.
Since this global object is used for most tests, it becomes important
for the test developer to "clean up after themselves." If you
change the state of the saw_14 object in a test (e.g. by calling
GetFieldList for a new object type), make sure to undo the state change
at the end of the test (e.g. removing the entry for that object type
from saw_14.object_fields). While this is a pain, it's better than
writing a test suite that takes 10 minutes to run a small handful of
tests.

Note that the saw_14 object is initialized in the setUpModule method,
and torn down in the tearDownModule. If we need to add another SAW
object corresponding to a different case (which is likely, seeing as
the IEEE 14 bus test case doesn't have all possible components), make
sure to follow the pattern used for saw_14: Initialize to None in
main code body, initialize actual SAW object in setUpModule (don't
forget to tag it as global!), and then call the object's exit() method
in tearDownModule.
"""

import unittest
from unittest.mock import patch
import os
import numpy as np
import pandas as pd
from esa import SAW, COMError, PowerWorldError, CommandNotRespectedError
from esa.saw import convert_to_posix_path, convert_to_windows_path
import logging
import doctest

# Handle pathing.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.join(THIS_DIR, 'cases')
DATA_DIR = os.path.join(THIS_DIR, 'data')
SNIPPET_DIR = os.path.join(THIS_DIR, '..', 'docs', 'rst', 'snippets')
SNIPPET_FILES = [os.path.join(SNIPPET_DIR, x) for x in
                 os.listdir(SNIPPET_DIR) if x.endswith('.rst')]

# Path to IEEE 14 bus model.
PATH_14 = os.path.join(CASE_DIR, 'ieee_14', 'IEEE 14 bus.pwb')

# Path to the Texas 2000 bus model.
PATH_2000 = os.path.join(CASE_DIR, 'tx2000', 'tx2000_base.PWB')
PATH_2000_mod = os.path.join(
    CASE_DIR, 'tx2000_mod', 'ACTIVSg2000_AUG-09-2018_Ride_version7.PWB')

# Aux file for filtering transformers by LTC control.
LTC_AUX_FILE = os.path.join(THIS_DIR, 'ltc_filter.aux')

# Initialize the 14 bus SimAutoWrapper. Adding type hinting to make
# development easier.
# noinspection PyTypeChecker
saw_14 = None  # type: SAW

# Map cases for doc testing.
CASE_MAP = {'14': PATH_14, '2000': PATH_2000}

# Path to file containing lines for one of the examples.
CANDIDATE_LINES = os.path.join(DATA_DIR, 'CandidateLines.csv')


# noinspection PyPep8Naming
def setUpModule():
    """In order to allow us to split the test cases by functionality
    under test without loading the case (which is expensive) for every
    test case, we'll load the case once. If more PowerWorld cases are
    added to this module, initialize them here.
    """
    global saw_14
    saw_14 = SAW(PATH_14)


# noinspection PyPep8Naming
def tearDownModule():
    """We need to ensure we clean up all our SimAuto servers, so call
    exit and then delete the wrappers here.
    """
    global saw_14
    saw_14.exit()
    del saw_14


########################################################################
# Misc tests
########################################################################


class InitializationTestCase(unittest.TestCase):
    """Test initialization."""

    def test_bad_path(self):
        with self.assertRaisesRegex(PowerWorldError, 'OpenCase: '):
            SAW(FileName='bogus')

    def test_init_expected_behavior(self):
        # Initialize
        my_saw_14 = SAW(PATH_14,
                        object_field_lookup=('bus', 'shunt'))

        # Ensure we have a log attribute.
        self.assertIsInstance(my_saw_14.log, logging.Logger)

        # Ensure our pwb_file_path matches our given path.
        self.assertEqual(convert_to_posix_path(PATH_14),
                         my_saw_14.pwb_file_path)

        # Ensure we have the expected object_fields.
        self.assertEqual(2, len(my_saw_14._object_fields))

        for f in ['bus', 'shunt']:
            df = my_saw_14._object_fields[f]
            self.assertIsInstance(df, pd.DataFrame)
            self.assertSetEqual({'key_field', 'internal_field_name',
                                 'field_data_type', 'description',
                                 'display_name'},
                                set(df.columns.to_numpy()))


########################################################################
# Helper function tests
########################################################################


class ChangeAndConfirmParamsMultipleElementTestCase(unittest.TestCase):
    """Test change_and_confirm_params_multiple_element."""

    @classmethod
    def setUpClass(cls) -> None:
        # Get branch data, including LineStatus, which is a string.
        branch_key_fields = \
            saw_14.get_key_fields_for_object_type('branch')
        cls.branch_data = saw_14.GetParametersMultipleElement(
            ObjectType='branch',
            ParamList=branch_key_fields['internal_field_name'].tolist()
                       + ['LineStatus'])
        # Make a copy so we can modify it without affecting the original
        # DataFrame.
        cls.branch_data_copy = cls.branch_data.copy()

    @classmethod
    def tearDownClass(cls) -> None:
        # Put the branches back as they were.
        # noinspection PyUnresolvedReferences
        saw_14.ChangeParametersMultipleElement(
            ObjectType='Branch', ParamList=cls.branch_data.columns.tolist(),
            ValueList=cls.branch_data.to_numpy().tolist())

    def test_with_string_value(self):
        """This test will prove the following has been resolved if this
        test passes:
        https://github.com/mzy2240/ESA/issues/8#issue-537818522
        """
        # Open the line from bus 6 to 13.
        from_6 = self.branch_data_copy['BusNum'] == 6
        to_13 = self.branch_data_copy['BusNum:1'] == 13
        self.branch_data_copy.loc[from_6 & to_13, 'LineStatus'] = 'Open'

        # Change and confirm.
        self.assertIsNone(
            saw_14.change_and_confirm_params_multiple_element(
                ObjectType='Branch', command_df=self.branch_data_copy))

    def test_success(self):
        """Send in a simple command that matches what's already in the
        case and ensure the output from PowerWorld matches.
        """
        # Create DataFrame which a) only modifies a couple elements
        # (not all), b) does not actually change anything (e.g. matches
        # the initial case values), and c) has NOT been cleaned (e.g.
        # bad data types (string where float should be), not sorted by
        # BusNum).
        # Part a) ensures the merge + comparison in the method is
        #   working.
        # Part b) means we don't need to clean up after ourselves and
        #   set things back.
        # Part c) ensures the user doesn't have to provide a perfect
        #   pre-cleaned DataFrame.
        command_df = pd.DataFrame(
            [[13, '1', 13.5, '5.8'],
             [3, ' 1 ', '94.2', '19.0']],
            columns=['BusNum', 'LoadID', 'LoadMW', 'LoadMVR']
        )

        # Patch the call to ChangeParametersMultipleElement.
        with patch.object(saw_14, 'ChangeParametersMultipleElement'):
            self.assertIsNone(
                saw_14.change_and_confirm_params_multiple_element(
                    ObjectType='load', command_df=command_df))

    def test_failure_numeric(self):
        """Don't actually send in a command, and ensure that we get
        an exception.
        """
        # Note this DataFrame is only one value off from what's in the
        # base case model (130.5 in first row).
        command_df = pd.DataFrame(
            [[13, '1', 130.5, '5.8'],
             [3, ' 1 ', '94.2', '19.0']],
            columns=['BusNum', 'LoadID', 'LoadMW', 'LoadMVR']
        )

        # Patch the call to ChangeParametersMultipleElement.
        with patch.object(saw_14, 'ChangeParametersMultipleElement'):
            with self.assertRaisesRegex(CommandNotRespectedError,
                                        'After calling .* not all parameters'):
                saw_14.change_and_confirm_params_multiple_element(
                    ObjectType='load', command_df=command_df)

    def test_failure_string(self):
        """Don't actually send in a command, and ensure that we get
        an exception.
        """
        # Note this DataFrame is only one value off from what's in the
        # base case model (all loads are in).
        command_df = pd.DataFrame(
            [[13, '1', 'Closed'],
             [3, ' 1 ', 'Open']],
            columns=['BusNum', 'LoadID', 'LoadStatus']
        )

        # Patch the call to ChangeParametersMultipleElement.
        with patch.object(saw_14, 'ChangeParametersMultipleElement'):
            with self.assertRaisesRegex(CommandNotRespectedError,
                                        'After calling .* not all parameters'):
                saw_14.change_and_confirm_params_multiple_element(
                    ObjectType='load', command_df=command_df)


class ChangeParametersMultipleElementDFTestCase(unittest.TestCase):
    """Test change_parameters_multiple_element_df."""

    def test_success(self):
        """Send in a simple command that matches what's already in the
        case and ensure the output from PowerWorld matches.
        """
        # Create DataFrame for sending in commands, and ensure that
        # ChangeParametersMultipleElement is called correctly.
        cols = ['BusNum', 'LoadID', 'LoadMW', 'LoadMVR']
        command_df = pd.DataFrame(
            [[13, '1', 13.8, '5.1'],
             [3, ' 1 ', '94.9', '29.0']],
            columns=cols
        )

        # Patch the call to ChangeParametersMultipleElement.
        with patch.object(saw_14, 'ChangeParametersMultipleElement') as p:
            self.assertIsNone(
                saw_14.change_parameters_multiple_element_df(
                    ObjectType='load', command_df=command_df))

        p.assert_called_once()
        self.assertDictEqual(
            p.mock_calls[0][2],
            {'ObjectType': 'load', 'ParamList': cols,
             # Note the DataFrame will get sorted by bus number, and
             # type casting will be applied.
             'ValueList': [[3, '1', 94.9, 29.0], [13, '1', 13.8, 5.1]]}
        )


class CleanDFOrSeriesTestCase(unittest.TestCase):
    def test_bad_df_columns(self):
        """If the DataFrame columns are not valid fields, we should get
        an error.
        """
        bad_df = pd.DataFrame([[1, 'bleh']], columns=['BusNum', 'bleh'])
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14.clean_df_or_series(obj=bad_df, ObjectType='gen')

    def test_bad_df_columns_2(self):
        """This time, use upper-case so we don't get an index error."""
        bad_df = pd.DataFrame([[1, 'bleh']], columns=['BusNum', 'Bleh'])
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14.clean_df_or_series(obj=bad_df, ObjectType='gen')

    # noinspection PyMethodMayBeStatic
    def test_works_df(self):
        """Ensure that when using valid fields, the DataFrame comes back
        as expected.
        """
        df_in = pd.DataFrame([[' 6    ', '7.2234 ', ' yes '],
                              [' 3', '11', '   no ']],
                             columns=['BusNum', 'GenMW', 'GenAGCAble'])
        df_expected = pd.DataFrame([[3, 11.0, 'no'], [6, 7.2234, 'yes']],
                                   columns=['BusNum', 'GenMW', 'GenAGCAble'])

        df_actual = saw_14.clean_df_or_series(obj=df_in, ObjectType='gen')

        pd.testing.assert_frame_equal(df_actual, df_expected)

    def test_bad_type(self):
        """Ensure a TypeError is raised if 'obj' is a bad type."""
        with self.assertRaisesRegex(TypeError, 'The given object is not a Da'):
            # noinspection PyTypeChecker
            saw_14.clean_df_or_series(obj=42, ObjectType='shunt')

    def test_series_bad_index(self):
        """If a Series has an Index that doesn't match known fields, we
        should get an exception.
        """
        bad_series = pd.Series([1, 'a'], index=['BusNum', 'Bad_Field'])
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14.clean_df_or_series(obj=bad_series, ObjectType='gen')


class GetKeyFieldsForObjectType(unittest.TestCase):
    """Test the get_key_fields_for_object_type method."""

    def test_gens(self):
        """Gens should have bus number and generator ID key fields."""
        # Query.
        result = saw_14.get_key_fields_for_object_type("Gen")
        # Check length.
        self.assertEqual(2, result.shape[0])
        # Check fields.
        self.assertEqual('BusNum', result.loc[0, 'internal_field_name'])
        self.assertEqual('GenID', result.loc[1, 'internal_field_name'])

    def test_branches(self):
        """Branches have three key fields: bus from, bus to, and circuit
        ID.
        """
        # Query
        result = saw_14.get_key_fields_for_object_type("Branch")
        # Check length.
        self.assertEqual(3, result.shape[0])
        # Check fields.
        self.assertEqual('BusNum', result.loc[0, 'internal_field_name'])
        self.assertEqual('BusNum:1', result.loc[1, 'internal_field_name'])
        self.assertEqual('LineCircuit', result.loc[2, 'internal_field_name'])

    def test_buses(self):
        """Buses should only have one key field - their number."""
        # Query.
        result = saw_14.get_key_fields_for_object_type("Bus")
        # Check length.
        self.assertEqual(1, result.shape[0])
        # Check fields.
        self.assertEqual('BusNum', result.loc[0, 'internal_field_name'])

    def test_shunts(self):
        """Shunts, similar to generators, will have a bus number and an
        ID."""
        # Query.
        result = saw_14.get_key_fields_for_object_type("Shunt")
        # Check length.
        self.assertEqual(2, result.shape[0])
        # Check fields.
        self.assertEqual('BusNum', result.loc[0, 'internal_field_name'])
        self.assertEqual('ShuntID', result.loc[1, 'internal_field_name'])

    def test_nonexistent_object(self):
        """Not really sure why this raises a COMError rather than a
        PowerWorldError..."""
        with self.assertRaises(COMError):
            saw_14.get_key_fields_for_object_type('sorry, not here')

    def test_cached(self):
        """Test that the "caching" is working as intended."""
        # Generators are in the default listing.
        with patch.object(saw_14, '_call_simauto',
                          wraps=saw_14._call_simauto) as p:
            kf = saw_14.get_key_fields_for_object_type('GEN')

        self.assertIsInstance(kf, pd.DataFrame)
        self.assertEqual(0, p.call_count)

        # Now, actually look something up.
        with patch.object(saw_14, '_call_simauto',
                          wraps=saw_14._call_simauto) as p:
            kf = saw_14.get_key_fields_for_object_type('area')

        self.assertIsInstance(kf, pd.DataFrame)
        self.assertEqual(1, p.call_count)


class GetKeyFieldListTestCase(unittest.TestCase):
    """Test get_key_field_list."""

    @classmethod
    def tearDownClass(cls) -> None:
        # Remove the cached three winding transformer from saw_14 to
        # avoid screwing up state for other tests.
        del saw_14._object_key_fields['3wxformer']
        del saw_14._object_fields['3wxformer']

    def test_gen(self):
        """Ensure generator listing matches."""
        # Ensure this one is cached.
        self.assertIn('gen', saw_14._object_key_fields)

        # Ensure the list comes back correctly.
        self.assertListEqual(['BusNum', 'GenID'],
                             saw_14.get_key_field_list('Gen'))

    def test_3wxformer(self):
        """Ensure 3WXFormer listing matches."""
        # Ensure this is NOT cached.
        self.assertNotIn('3wxformer', saw_14._object_key_fields)

        # Ensure the list comes back correctly.
        self.assertListEqual(
            ['BusIdentifier', 'BusIdentifier:1', 'BusIdentifier:2',
             'LineCircuit'],
            saw_14.get_key_field_list('3WXFormer')
        )


class GetPowerFlowResultsTestCase(unittest.TestCase):
    """Test get_power_flow_result"""

    @classmethod
    def setUpClass(cls) -> None:
        """Run the power flow to ensure we have results to fetch."""
        saw_14.SolvePowerFlow()

    def test_bad_field(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported ObjectType'):
            saw_14.get_power_flow_results(ObjectType='nonexistent')

    def test_all_valid_types_except_shunts(self):
        """Loop and sub test over all types, except shunts."""
        # Loop over the POWER_FLOW_FIELDS dictionary.
        for object_type, object_fields in SAW.POWER_FLOW_FIELDS.items():
            # Skip shunts, we'll do that separately (there aren't any
            # in the 14 bus model).
            if object_type == 'shunt':
                continue

            # Perform a test for each valid type.
            with self.subTest(object_type):
                # Get results.
                result = saw_14.get_power_flow_results(ObjectType=object_type)
                # We should get a DataFrame back.
                self.assertIsInstance(result, pd.DataFrame)
                # Ensure the DataFrame has all the columns we expect.
                self.assertSetEqual(set(result.columns.to_numpy()),
                                    set(object_fields))
                # No NaNs.
                self.assertFalse(result.isna().any().any())

    def test_shunt(self):
        """There are no shunts in the IEEE 14 bus model."""
        self.assertIsNone(saw_14.get_power_flow_results('shunt'))


class IdentifyNumericFieldsTestCase(unittest.TestCase):
    """Test identify_numeric_fields."""

    # noinspection PyMethodMayBeStatic
    def test_correct(self):
        # Intentionally make the fields out of alphabetical order.
        fields = ['LineStatus', 'LockOut', 'LineR', 'LineX', 'BusNum']
        np.testing.assert_array_equal(
            saw_14.identify_numeric_fields(
                ObjectType='Branch', fields=fields),
            np.array([False, False, True, True, True])
        )


class SetSimAutoPropertyTestCase(unittest.TestCase):
    """Test the set_simauto_property method. To avoid conflicts with
    other tests we'll create a fresh SAW instance here.
    """
    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(PATH_14, early_bind=True)

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_set_create_if_not_found_true(self):
        self.saw.set_simauto_property('CreateIfNotFound', True)
        self.assertTrue(self.saw._pwcom.CreateIfNotFound)

    def test_set_create_if_not_found_false(self):
        self.saw.set_simauto_property('CreateIfNotFound', False)
        self.assertFalse(self.saw._pwcom.CreateIfNotFound)

    def test_set_create_if_not_found_bad_value(self):
        with self.assertRaisesRegex(
                ValueError, 'The given property_value, bad, is invalid'):
            self.saw.set_simauto_property('CreateIfNotFound', 'bad')

    def test_set_ui_visible_true(self):
        # Patch the _pwcom object so we don't actually activate the UI.
        # If we actually activate the UI, it can cause the tests to
        # hang. E.g., if an update is available which requires user
        # input as to whether to download or wait.
        with patch.object(self.saw, '_pwcom') as p:
            self.saw.set_simauto_property('UIVisible', True)

        self.assertTrue(p.UIVisible)

    def test_set_ui_visible_false(self):
        self.saw.set_simauto_property('UIVisible', False)
        self.assertFalse(self.saw._pwcom.UIVisible)

    def test_set_ui_visible_bad_value(self):
        with self.assertRaisesRegex(
                ValueError, 'The given property_value, bad, is invalid'):
            self.saw.set_simauto_property('UIVisible', 'bad')

    def test_set_current_dir_here(self):
        self.saw.set_simauto_property(property_name='CurrentDir',
                                      property_value=THIS_DIR)
        self.assertEqual(self.saw._pwcom.CurrentDir, THIS_DIR)

    def test_set_current_dir_bad(self):
        with self.assertRaisesRegex(ValueError, 'The given path for Current'):
            self.saw.set_simauto_property(property_name='CurrentDir',
                                          property_value=r'C:\bad\path')


########################################################################
# SimAuto functions tests
########################################################################


class ChangeParametersMultipleElementTestCase(unittest.TestCase):
    """Test ChangeParametersMultipleElement"""

    @classmethod
    def setUpClass(cls) -> None:
        # Get generator key fields.
        cls.key_field_df_gens = saw_14.get_key_fields_for_object_type('gen')
        cls.params = \
            cls.key_field_df_gens['internal_field_name'].to_numpy().tolist()
        # Combine key fields with our desired attribute.
        cls.params.append('GenVoltSet')
        cls.gen_v_pu = saw_14.GetParametersMultipleElement(
            ObjectType='gen', ParamList=cls.params)

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls) -> None:
        """Always be nice and clean up after yourself and put your toys
        away. No, but seriously, put the voltage set points back."""
        value_list = cls.gen_v_pu.to_numpy().tolist()
        saw_14.ChangeParametersMultipleElement(
            ObjectType='gen', ParamList=cls.params, ValueList=value_list)

    # noinspection DuplicatedCode
    def test_change_gen_voltage_set_points(self):
        """Set all generator voltages to 1, and ensure the command
        sticks.
        """
        # https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/ChangeParametersMultipleElement_Sample_Code_Python.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____9
        # Start by converting our generator data to a list of lists.
        value_list = self.gen_v_pu.to_numpy().tolist()

        # Loop over the values, set to 1.
        # noinspection PyTypeChecker
        for v in value_list:
            # Set voltage at 1.
            v[-1] = 1.0

        # Send in the command.
        # noinspection PyTypeChecker
        self.assertIsNone(saw_14.ChangeParametersMultipleElement(
            ObjectType='gen', ParamList=self.params, ValueList=value_list))

        # Check results.
        gen_v = saw_14.GetParametersMultipleElement(
            ObjectType='gen', ParamList=self.params)

        # Our present results should not be the same as the original.
        try:
            pd.testing.assert_frame_equal(gen_v, self.gen_v_pu)
        except AssertionError:
            # Frames are not equal. Success.
            pass
        else:
            self.fail('DataFrames are equal, but they should not be.')

        # Our current results should have all 1's for the GenRegPUVolt
        # column.
        # actual = pd.to_numeric(gen_v['GenRegPUVolt']).to_numpy()
        actual = pd.to_numeric(gen_v['GenVoltSet']).to_numpy()
        expected = np.array([1.0] * actual.shape[0])

        np.testing.assert_array_equal(actual, expected)

    def test_missing_key_fields(self):
        # Extract a portion of the gen_v_pu DataFrame which was created
        # in setUpClass. Notably, this is missing GenID.
        df = self.gen_v_pu[['BusNum', 'GenVoltSet']]

        # Convert to list.
        value_list = df.to_numpy().tolist()

        with self.assertRaisesRegex(PowerWorldError,
                                    'does not adequately define each object'):
            saw_14.ChangeParametersMultipleElement(
                ObjectType='gen', ParamList=['BusNum', 'GenVoltSet'],
                ValueList=value_list)

    def test_bad_object_type(self):
        with self.assertRaisesRegex(PowerWorldError,
                                    'Object type bad not recognized'):
            saw_14.ChangeParametersMultipleElement(ObjectType='bad',
                                                   ParamList=['BusNum'],
                                                   ValueList=[[1]])

    def test_mismatched_list_lengths(self):
        # Start by converting our generator data to a list of lists.
        value_list = self.gen_v_pu.to_numpy().tolist()

        # Delete an entry.
        # noinspection PyUnresolvedReferences
        del value_list[1][-1]

        m = 'Number of fields and number of values given are not equal'
        with self.assertRaisesRegex(PowerWorldError, m):
            # noinspection PyTypeChecker
            saw_14.ChangeParametersMultipleElement(
                ObjectType='gen', ParamList=self.params,
                ValueList=value_list
            )


class ChangeParametersMultipleElementExpectedFailure(unittest.TestCase):
    """Test case to illustrate the PowerWorld sometimes will not report
    an error, but won't actually change a parameter when you ask it to.
    TODO: Determine the mechanism by which PowerWorld does or does not
        change values. Could we check if they're "changeable" before
        hand?
    """

    @classmethod
    def setUpClass(cls) -> None:
        # Get generator key fields.
        cls.key_field_df_gens = saw_14.get_key_fields_for_object_type('gen')
        cls.params = \
            cls.key_field_df_gens['internal_field_name'].to_numpy().tolist()
        # Combine key fields with our desired attribute.
        cls.params.append('GenRegPUVolt')
        cls.gen_v_pu = saw_14.GetParametersMultipleElement(
            ObjectType='gen', ParamList=cls.params)

    # noinspection DuplicatedCode
    @unittest.expectedFailure
    def test_change_gen_voltage_set_points(self):
        """Set all generator voltages to 1, and ensure the command
        sticks.
        """
        # https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/ChangeParametersMultipleElement_Sample_Code_Python.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____9
        # Start by converting our generator data to a list of lists.
        value_list = self.gen_v_pu.to_numpy().tolist()

        # Loop over the values, set to 1.
        # noinspection PyTypeChecker
        for v in value_list:
            # Set voltage at 1.
            v[-1] = 1.0

        # Send in the command.
        # noinspection PyTypeChecker
        self.assertIsNone(saw_14.ChangeParametersMultipleElement(
            ObjectType='gen', ParamList=self.params, ValueList=value_list))

        # Check results.
        gen_v = saw_14.GetParametersMultipleElement(
            ObjectType='gen', ParamList=self.params)

        # Our present results should not be the same as the original.
        try:
            pd.testing.assert_frame_equal(gen_v, self.gen_v_pu)
        except AssertionError:
            # Frames are not equal. Success.
            pass
        else:
            self.fail('DataFrames are equal, but they should not be.')

    # noinspection DuplicatedCode
    @unittest.expectedFailure
    def test_change_gen_voltage_set_points_via_helper(self):
        """Use change_and_confirm_params_multiple_element.
        """
        command_df = self.gen_v_pu.copy(deep=True)
        command_df['GenRegPUVolt'] = 1.0

        # noinspection PyNoneFunctionAssignment
        result = saw_14.change_and_confirm_params_multiple_element(
            ObjectType='gen', command_df=command_df)

        self.assertIsNone(result)


class ChangeParametersSingleElementTestCase(unittest.TestCase):
    """Test ChangeParametersSingleElement.

    TODO: This test case could use some more tests, e.g. expected
        errors, etc.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.line_key_fields = saw_14.get_key_fields_for_object_type(
                'Branch')['internal_field_name'].tolist()
        cls.line_r = ['LineR']
        cls.params = cls.line_key_fields + cls.line_r
        cls.line_data = saw_14.GetParametersMultipleElement(
            ObjectType='Branch', ParamList=cls.params)

    @classmethod
    def tearDownClass(cls) -> None:
        """Be a good boy and put things back the way you found them."""
        # noinspection PyUnresolvedReferences
        saw_14.change_and_confirm_params_multiple_element(
            'Branch', cls.line_data)

    def test_change_line_r(self):
        # Let's just change the first line resistance.
        new_r = self.line_data.iloc[0]['LineR'] * 2
        # Intentionally making a copy so that we don't modify the
        # original DataFrame - we'll be using that to reset the line
        # parameters after this test has run.
        value_series = self.line_data.iloc[0].copy()
        value_series['LineR'] = new_r
        values_list = value_series.tolist()
        saw_14.ChangeParametersSingleElement('Branch', self.params,
                                             values_list)

        # Retrieve the updated line parameters.
        new_line_data = saw_14.GetParametersMultipleElement(
            'Branch', self.params)

        # Ensure the update went through.
        self.assertEqual(new_line_data.iloc[0]['LineR'], new_r)


class GetFieldListTestCase(unittest.TestCase):
    """Test the GetFieldList method"""

    def check_field_list(self, field_list):
        """Helper to check a returned field list DataFrame."""
        self.assertIsInstance(field_list, pd.DataFrame)
        self.assertEqual(saw_14.FIELD_LIST_COLUMNS,
                         field_list.columns.to_numpy().tolist())
        pd.testing.assert_frame_equal(
            field_list, field_list.sort_values(by=['internal_field_name']))

    def test_does_not_call_simauto_if_not_necessary(self):
        """Ensure that if the field list has already been accessed for
        the given object type that SimAuto is not called again.
        """
        # Generators are looked up by default on initialization.
        with patch.object(saw_14, '_call_simauto') as m:
            field_list = saw_14.GetFieldList(ObjectType='gen')

        # Ensure DataFrame is as expected.
        self.check_field_list(field_list)

        # Ensure _call_simauto was not called
        self.assertEqual(m.call_count, 0)

    def test_simauto_called_for_new_object_type(self):
        """Ensure that for a new object type, SimAuto is called and
        the new result is stored in the object_fields dictionary.
        """
        # Let's look up field for three winding transformers.
        # Cast to lower case so we can easily use the variable later.
        obj_type = '3WXFormer'.lower()

        # Start by ensuring we don't currently have this in the
        # dictionary.
        self.assertNotIn(obj_type, saw_14._object_fields)

        # Call GetFieldList.
        try:
            with patch.object(saw_14, '_call_simauto',
                              wraps=saw_14._call_simauto) as p:
                field_list = saw_14.GetFieldList(ObjectType=obj_type)

            # Check our field list.
            self.check_field_list(field_list)

            # Ensure _call_simauto was called.
            self.assertEqual(p.call_count, 1)
            p.assert_called_with('GetFieldList', obj_type)

            # We should now have the object type in the object_fields
            # attribute.
            self.assertIn(obj_type, saw_14._object_fields)

        finally:
            # Always remove from the object_fields dictionary to avoid
            # state changes that could impact other tests.
            del saw_14._object_fields[obj_type]

    def test_copy_true(self):
        """Ensure we get a copy when asked for."""
        field_list = saw_14.GetFieldList('gen', copy=True)
        self.assertIsNot(field_list, saw_14._object_fields['gen'])

    def test_copy_false(self):
        """Ensure we don't get a copy when we don't ask for it."""
        field_list = saw_14.GetFieldList('branch')
        self.assertIs(field_list, saw_14._object_fields['branch'])

    def test_works_if_object_type_not_in_model(self):
        """Ensure we still get a valid field listing even if the given
        object type is not in the model. Shunts are not present in the
        14 bus test case.
        """
        field_list = saw_14.GetFieldList('shunt')
        self.check_field_list(field_list)


class GetParametersMultipleElementTestCase(unittest.TestCase):
    """Test GetParametersMultipleElement"""

    def test_get_gen_voltage_set_points(self):
        params = ['BusNum', 'GenID', 'GenRegPUVolt']
        results = saw_14.GetParametersMultipleElement(
            ObjectType='gen', ParamList=params)

        self.assertIsInstance(results, pd.DataFrame)
        self.assertSetEqual(set(params), set(results.columns.to_numpy()))

    def test_shunts_returns_none(self):
        """There are no shunts in the 14 bus model."""
        results = saw_14.GetParametersMultipleElement(ObjectType='shunt',
                                                      ParamList=['BusNum'])
        self.assertIsNone(results)

    def test_get_nonexistent_parameter(self):
        """We should get a ValueError for a bogus parameter."""
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14.GetParametersMultipleElement(
                ObjectType='branch', ParamList=['ThisNotReal'])

    def test_bad_object_type(self):
        """A bad object type should raise an exception."""
        with self.assertRaises(PowerWorldError):
            saw_14.GetParametersMultipleElement(
                ObjectType='bogus', ParamList=['BusNum']
            )


class GetParametersSingleElementTestCase(unittest.TestCase):
    """Test GetParameterSingleElement method."""

    # noinspection PyMethodMayBeStatic
    def test_expected_results(self):
        fields = ['BusNum', 'BusNum:1', 'LineCircuit', 'LineX']

        actual = saw_14.GetParametersSingleElement(
            ObjectType='branch', ParamList=fields, Values=[4, 9, '1', 0])

        expected = pd.Series([4, 9, '1', 0.556180], index=fields)

        pd.testing.assert_series_equal(actual, expected)

    def test_nonexistent_object(self):
        """Ensure an exception is raised if the object cannot be found.
        """
        with self.assertRaisesRegex(PowerWorldError, 'Object not found'):
            # 14 bus certainly does not have a 100th bus.
            # noinspection PyUnusedLocal
            actual = saw_14.GetParametersSingleElement(
                ObjectType='gen', ParamList=['BusNum', 'GenID', 'GenMW'],
                Values=[100, '1', 0]
            )

    def test_bad_field(self):
        """Ensure an exception is raised when a bad field is provided.
        """
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14.GetParametersSingleElement(
                ObjectType='gen', ParamList=['BusNum', 'GenID', 'BogusParam'],
                Values=[1, '1', 0]
            )


class GetSpecificFieldListTestCase(unittest.TestCase):
    """Test GetSpecificFieldList"""

    def helper(self, df):
        """Helper for checking basic DataFrame attributes."""
        # Ensure columns match up.
        self.assertListEqual(list(df.columns),
                             saw_14.SPECIFIC_FIELD_LIST_COLUMNS)

        # The dtypes for all columns should be strings, which are
        # 'objects' in Pandas.
        self.assertTrue((df.dtypes == np.dtype('O')).all())

        # Ensure we're sorted by the first column.
        self.assertTrue(
            df[saw_14.SPECIFIC_FIELD_LIST_COLUMNS[0]].is_monotonic_increasing)

        # Ensure the index starts at 0 and is monotonic
        self.assertTrue(df.index[0] == 0)
        self.assertTrue(df.index.is_monotonic_increasing)

    def test_all(self):
        """As documented, try using the ALL specifier."""
        # Fetch all gen parameters.
        out = saw_14.GetSpecificFieldList('gen', ['ALL'])

        # Do basic tests.
        self.helper(out)

        # For whatever reason, the following does not work. We get
        # lengths of 808 and 806, respectively. This is not worth
        # investigating.
        # # Ensure we get the same number of parameters as were pulled for
        # # GetFieldList.
        # out2 = saw_14.GetFieldList('gen')
        #
        # self.assertEqual(out.shape[0], out2.shape[0])

        #

    def test_all_location(self):
        """As documented, try using variablename:ALL"""
        out = saw_14.GetSpecificFieldList('load', ['ABCLoadAngle:ALL'])

        # Do basic tests.
        self.helper(out)

        # We should get three entries back.
        self.assertEqual(3, out.shape[0])

    def test_some_variables(self):
        """Pass a handful of variables in."""
        v = ['GenVoltSet', 'GenMW', 'GenMVR']
        out = saw_14.GetSpecificFieldList('gen', v)

        # Do basic tests.
        self.helper(out)

        # We should get an entry for each item in the list.
        self.assertEqual(len(v), out.shape[0])


class GetSpecificFieldMaxNumTestCase(unittest.TestCase):
    """Test GetSpecificFieldMaxNum."""
    def test_load_angle(self):
        # While there are 3 ABCLoadAngle variables, the maximum number
        # is 2.
        self.assertEqual(
            2, saw_14.GetSpecificFieldMaxNum('load', 'ABCLoadAngle'))

    def test_bad_input(self):
        with self.assertRaisesRegex(PowerWorldError,
                                    'PowerWorld simply returned -1'):
            saw_14.GetSpecificFieldMaxNum('bogus', 'bogus')


class ListOfDevicesTestCase(unittest.TestCase):
    """Test ListOfDevices for the 14 bus case."""

    # noinspection PyMethodMayBeStatic
    def test_gens(self):
        """Ensure there are 5 generators at the correct buses."""
        # Query.
        result = saw_14.ListOfDevices(ObjType='Gen')
        # The 14 bus case has 5 generators at buses 1, 2, 3, 6, and 8.
        # Since there's only one generator at each bus, they have an
        # ID of 1. However, ID is a string field.
        expected = pd.DataFrame([[1, '1'], [2, '1'], [3, '1'], [6, '1'],
                                 [8, '1']], columns=['BusNum', 'GenID'])

        pd.testing.assert_frame_equal(expected, result)

    def test_shunts(self):
        """There are no shunts in th 14 bus model."""
        result = saw_14.ListOfDevices(ObjType="Shunt")
        self.assertIsNone(result)

    def test_branches(self):
        """Ensure we get the correct number of branches, and ensure
        we get back the expected fields.
        """
        result = saw_14.ListOfDevices(ObjType="Branch")
        # 3 transformers, 17 lines.
        self.assertEqual(20, result.shape[0])
        # Check columns.
        self.assertIn('BusNum', result.columns.to_numpy())
        self.assertIn('BusNum:1', result.columns.to_numpy())
        self.assertIn('LineCircuit', result.columns.to_numpy())

        # Ensure our BusNum columns are numeric.
        # noinspection PyUnresolvedReferences
        self.assertTrue(pd.api.types.is_numeric_dtype(result['BusNum']))
        # noinspection PyUnresolvedReferences
        self.assertTrue(pd.api.types.is_numeric_dtype(result['BusNum:1']))

        # Ensure our LineCircuit is a string.
        # noinspection PyUnresolvedReferences
        self.assertTrue(pd.api.types.is_string_dtype(result['LineCircuit']))

        # Ensure there's no leading space in LineCircuit.
        pd.testing.assert_series_equal(result['LineCircuit'],
                                       result['LineCircuit'].str.strip())

        # For the grand finale, ensure we're sorted by BusNum.
        pd.testing.assert_frame_equal(result, result.sort_values(by='BusNum'))

    # noinspection PyMethodMayBeStatic
    def test_buses(self):
        """As the name implies, we should get 14 buses."""
        result = saw_14.ListOfDevices(ObjType="Bus")
        expected = pd.DataFrame(
            data=np.arange(1, 15, dtype=np.int64).reshape(14, 1),
            index=np.arange(0, 14),
            columns=['BusNum'])
        pd.testing.assert_frame_equal(expected, result)


class ListOfDevicesAsVariantStrings(unittest.TestCase):
    """Test ListOfDevicesAsVariantStrings"""
    def test_buses(self):
        # Call method.
        out = saw_14.ListOfDevicesAsVariantStrings('bus')

        # We should get a tuple of tuples.
        self.assertEqual(1, len(out))

        # 14 buses.
        self.assertEqual(14, len(out[0]))


class ListOfDevicesFlatOutputTestCase(unittest.TestCase):
    """Test ListOfDevicesFlatOutput."""
    def test_buses(self):
        # Call method for buses.
        out = saw_14.ListOfDevicesFlatOutput('bus')
        self.assertTrue(isinstance(out, tuple))

        # Since buses have a single key field (BusNum), we'll only get
        # one return per bus. So, including the two fields at the
        # beginning of the list, we'll have 16 elements.
        self.assertEqual(16, len(out))


class LoadStateErrorTestCase(unittest.TestCase):
    """Test LoadState without calling SaveState, and ensure we get an
    error from PowerWorld.

    We'll spin up a new SAW instance so as to have state independence
    from other tests, at the cost of increasing test run time by
    several seconds.
    """
    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(PATH_14)

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls) -> None:
        cls.saw.exit()
        del cls.saw

    def test_load_state_errors(self):
        """Call LoadState without calling SaveState."""
        with self.assertRaisesRegex(
                PowerWorldError, "State hasn't been previously stored."):
            self.saw.LoadState()


class LoadStateSaveStateTestCase(unittest.TestCase):
    """Test that LoadState works after calling SaveState."""

    def test_save_change_load(self):
        """Save the state, make a change, load the state, ensure changes
        were reverted.
        """
        # Get branch data.
        branch_key_fields = saw_14.get_key_field_list('branch')
        branch_data = saw_14.GetParametersMultipleElement(
            'branch', branch_key_fields + ['LineStatus'])

        # Save the state.
        self.assertIsNone(saw_14.SaveState())

        # Open a line.
        branch_data_copy = branch_data.copy(deep=True)
        self.assertEqual('Closed', branch_data_copy.loc[3, 'LineStatus'])
        branch_data_copy.loc[3, 'LineStatus'] = 'Open'
        saw_14.change_and_confirm_params_multiple_element(
            'branch', branch_data_copy)

        # Load the saved state.
        self.assertIsNone(saw_14.LoadState())

        # Ensure that new branch data equals original.
        branch_data_new = saw_14.GetParametersMultipleElement(
            'branch', branch_key_fields + ['LineStatus'])

        pd.testing.assert_frame_equal(branch_data, branch_data_new)


class ProcessAuxFileTestCase(unittest.TestCase):
    """Light weight testing of ProcessAuxFile."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(FileName=PATH_2000_mod, early_bind=True, UIVisible=False)

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_process_aux_ltc_filter(self):
        # Process the aux file. Note the aux file has a named filter,
        # "ltc_filter"
        self.saw.ProcessAuxFile(FileName=LTC_AUX_FILE)

        # Get branch key fields.
        kf = self.saw.get_key_field_list('branch')

        # Get transformer data, using the named filter.
        ltc = self.saw.GetParametersMultipleElement(
            ObjectType='branch', ParamList=kf, FilterName="ltc_filter"
        )

        # Check that the filter worked.
        branch = self.saw.GetParametersMultipleElement(
            ObjectType='branch', ParamList=kf + ['LineXFType']
        )

        # Ensure the branch data is not getting filtered.
        self.assertNotEqual(ltc.shape[0], branch.shape[0])

        # Ensure the number of LTC transformers matches up.
        ltc_expected = branch['LineXFType'] == 'LTC'
        self.assertEqual(ltc_expected.sum(), ltc.shape[0])


class RunScriptCommandTestCase(unittest.TestCase):
    """Light weight testing of RunScriptCommand."""

    # noinspection PyMethodMayBeStatic
    def test_calls_call_simauto(self):
        """RunScriptCommand is a simple wrapper. Enforce this."""
        with patch.object(saw_14, '_call_simauto') as p:
            saw_14.RunScriptCommand(Statements='Some stuff')

        # _call_simauto should have been called once and the statements
        # should simply be passed through.
        p.assert_called_once_with('RunScriptCommand', 'Some stuff')

    def test_exception_for_bad_statement(self):
        """Ensure an exception is thrown for a bad statement."""
        with self.assertRaisesRegex(PowerWorldError,
                                    'Error in script statements definition'):
            saw_14.RunScriptCommand(Statements='invalid statement')


class SaveCaseTestCase(unittest.TestCase):
    """Test SaveCase."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.out_file = os.path.join(THIS_DIR, 'tmp.pwb')

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls) -> None:
        os.remove(cls.out_file)

    def test_save_creates_file(self):
        """Simply save the case and then ensure the file is present."""
        # File should not exist.
        self.assertFalse(os.path.isfile(self.out_file))

        # Save file.
        saw_14.SaveCase(FileName=self.out_file)

        # File should exist (it'll get cleaned up by tearDownClass).
        self.assertTrue(os.path.isfile(self.out_file))

    def test_bad_type(self):
        """A bad FileType should result in a PowerWorldError."""
        with self.assertRaises(PowerWorldError):
            saw_14.SaveCase(FileName=self.out_file, FileType='BAD',
                            Overwrite=True)

    # noinspection PyMethodMayBeStatic
    def test_save_with_same_file(self):
        """Save case with the existing file, but don't actually call
        SimAuto.
        """
        with patch.object(saw_14, '_call_simauto') as p:
            saw_14.SaveCase()

        p.assert_called_once_with(
            'SaveCase', convert_to_windows_path(saw_14.pwb_file_path),
            'PWB', True)


########################################################################
# ScriptCommand helper tests
########################################################################


class SolvePowerFlowTestCase(unittest.TestCase):
    """Test the SolvePowerFlow method. Note PowerWorld doesn't return
    anything for this script command, so we should always get None back
    unless there is an error.
    """

    def test_solve_defaults(self):
        """Solving the power flow with default options should just work.
        """
        self.assertIsNone(saw_14.SolvePowerFlow())

    def test_solve_bad_method(self):
        """Given a bad solver, we should expect an exception."""
        with self.assertRaisesRegex(PowerWorldError,
                                    'Invalid solution method'):
            saw_14.SolvePowerFlow(SolMethod='junk')


########################################################################
# Misc tests
########################################################################


class TestCreateNewLinesFromFile2000Bus(unittest.TestCase):
    """Test for looking into
    https://github.com/mzy2240/ESA/issues/4#issue-526268959
    """

    @classmethod
    def setUpClass(cls) -> None:
        # We're creating lines, so we want CreateIfNotFound to be
        # true.
        cls.saw = SAW(FileName=PATH_2000, CreateIfNotFound=True,
                      early_bind=True)
        cls.line_df = pd.read_csv(os.path.join(DATA_DIR, 'CandidateLines.csv'))

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_create_lines(self):
        # Rename columns to match PowerWorld variables.
        self.line_df.rename(
            # TODO: Will need to update this renaming once
            #   https://github.com/mzy2240/ESA/issues/1#issue-525219427
            #   is addressed.
            columns={
                'From Number': 'BusNum',
                'To Number': 'BusNum:1',
                'Ckt': 'LineCircuit',
                'R': 'LineR',
                'X': 'LineX',
                'B': 'LineC',
                'Lim MVA A': 'LineAMVA'
            },
            inplace=True)

        # We're required to set other limits too.
        self.line_df['LineAMVA:1'] = 0.0
        self.line_df['LineAMVA:2'] = 0.0

        # Move into edit mode so we can add lines.
        self.saw.RunScriptCommand("EnterMode(EDIT);")

        # Create the lines.
        self.saw.change_and_confirm_params_multiple_element(
            ObjectType='branch', command_df=self.line_df)


########################################################################
# DOC TESTS
########################################################################
# The "load_tests" and "get_snippet_suites" methods below take care of
# everything needed to run all the snippets.

# To enable unittest discovery:
# https://docs.python.org/3.8/library/doctest.html#unittest-api
def load_tests(loader, tests, ignore):
    suites = get_snippet_suites()
    for s in suites:
        tests.addTests(s)
    return tests


def get_snippet_suites():
    """Return list of DocFileSuites"""
    out = []
    # Loop over the available cases.
    for suffix, case_path in CASE_MAP.items():
        # Filter files by suffix, which corresponds to the case.
        files = [x for x in SNIPPET_FILES if x.endswith(suffix + '.rst')]

        if len(files) > 0:

            # Define global variables needed for the examples.
            g = {'CASE_PATH': case_path}
            if '2000' in suffix:
                # One example adds lines and depends on a .csv file.
                g['CANDIDATE_LINES'] = CANDIDATE_LINES

            # Create a DocFileSuite.
            out.append(doctest.DocFileSuite(
                *files, module_relative=False,
                globs=g))

    return out


if __name__ == '__main__':
    unittest.main()
