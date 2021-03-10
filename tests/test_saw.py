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

Finally, please note that examples from docs/rst/snippets are executed
using doctest. These files use a suffix convention to determine which
.pwb file to use in the CASE_PATH constant.
"""

import logging
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, Mock, seal
import threading
import signal
import time

import numpy as np
import pandas as pd
import networkx as nx
from scipy.sparse import csr_matrix

from esa import SAW, COMError, PowerWorldError, CommandNotRespectedError, \
    Error
from esa.saw import convert_to_windows_path

# noinspection PyUnresolvedReferences
from tests.constants import PATH_14, PATH_14_PWD, PATH_2000, \
    PATH_9, THIS_DIR, AREA_AUX_FILE, DATA_DIR, VERSION

# Initialize the 14 bus SimAutoWrapper. Adding type hinting to make
# development easier.
# noinspection PyTypeChecker
saw_14 = None  # type: SAW


def skip_if_version_below(version=21):
    """Use this method to skip tests below a given PowerWorld Simulator
    version.
    """
    if VERSION < version:
        raise unittest.SkipTest('Simulator version < {}.'.format(version))


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
        self.assertEqual(PATH_14,
                         my_saw_14.pwb_file_path)

        # Ensure we have the expected object_fields.
        self.assertEqual(2, len(my_saw_14._object_fields))

        for f in ['bus', 'shunt']:
            df = my_saw_14._object_fields[f]
            self.assertIsInstance(df, pd.DataFrame)

            cols = df.columns.to_numpy().tolist()
            if len(cols) == len(my_saw_14.FIELD_LIST_COLUMNS):
                self.assertEqual(cols, my_saw_14.FIELD_LIST_COLUMNS)
            elif len(cols) == len(my_saw_14.FIELD_LIST_COLUMNS_OLD):
                self.assertEqual(cols, my_saw_14.FIELD_LIST_COLUMNS_OLD)
            else:
                raise AssertionError(
                    'Columns, {}, do not match either FIELD_LIST_COLUMNS or '
                    'FIELD_LIST_COLUMNS_OLD.'.format(cols))

    def test_error_during_dispatch(self):
        """Ensure an exception is raised if dispatch fails."""
        with patch('win32com.client.gencache.EnsureDispatch',
                   side_effect=TypeError):
            with self.assertRaises(TypeError):
                SAW(PATH_14, early_bind=True)


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
            ParamList=(branch_key_fields['internal_field_name'].tolist()
                       + ['LineStatus']))
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

        self.assertEqual(1, p.call_count)
        self.assertDictEqual(
            p.mock_calls[0][2],
            {'ObjectType': 'load', 'ParamList': cols,
             # Note the DataFrame will get sorted by bus number, and
             # type casting will be applied.
             'ValueList': [[3, '1', 94.9, 29.0], [13, '1', 13.8, 5.1]]}
        )

    def test_with_comma_decimal_delimiter(self):
        """Ensure the method works with a comma decimal delimiter.

        Test motivated by the following issue:

        https://github.com/mzy2240/ESA/issues/61

        Also note the following comments:
        https://github.com/openjournals/joss-reviews/issues/2289#issuecomment-644265540
        https://github.com/openjournals/joss-reviews/issues/2289#issuecomment-644371941

        Note that the root of the problem in the aforementioned issues
        and comment is the _to_numeric method itself, so this is a
        high-level (and lazy?) way of getting at the problem.
        """
        # Create a DataFrame with mixed types for commands.
        cols = ['BusNum', 'LoadID', 'LoadMW', 'LoadMVR']
        command_df = pd.DataFrame(
            [[13, '1', 13.8, '5.1'],
             [3, ' 1 ', 94.9, '29.0']],
            columns=cols
        )

        # For sanity sake, add some type assertions.
        self.assertEqual(command_df['BusNum'].dtype, np.dtype('int64'))
        self.assertEqual(command_df['LoadID'].dtype, np.dtype('object'))
        self.assertEqual(command_df['LoadMW'].dtype, np.dtype('float64'))
        self.assertEqual(command_df['LoadMVR'].dtype, np.dtype('object'))

        # Alright, our command DataFrame is as we want it.
        # Now, call the change_parameters_multiple_element_df method.
        # Patch the comma delimiter and _call_simauto method.
        with patch.object(saw_14, 'decimal_delimiter', new=','):
            with patch.object(saw_14, '_call_simauto', return_value=None):
                saw_14.change_parameters_multiple_element_df(
                    'load', command_df)


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

        # Key fields have changed for 3 winding transformers between
        # versions.
        if VERSION in [21, 22]:
            expected = ['BusIdentifier', 'BusIdentifier:1', 'BusIdentifier:2',
                        'LineCircuit']
        elif VERSION == 17:
            expected = ['BusName_NomVolt:4', 'BusNum3W:3', 'LineCircuit']
        else:
            raise NotImplementedError(
                'We do not know when key fields for 3 winding transformers'
                'changed, and have thus far only looked into PWS versions '
                '17 and 21. Please update this test if you are running a '
                'different version of Simulator.')

        # Ensure the list comes back correctly.
        self.assertListEqual(expected, saw_14.get_key_field_list('3WXFormer'))


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

    def test_with_additional_fields(self):
        """Add additional fields to the result"""
        # Ensure the number of fields before and after doesn't change.
        num_fields_before = len(saw_14.POWER_FLOW_FIELDS['bus'])

        result = saw_14.get_power_flow_results(ObjectType='Bus',
                                               additional_fields=['AreaNum'])
        self.assertTrue('AreaNum' in result.columns.values.tolist())

        # Check fields.
        num_fields_after = len(saw_14.POWER_FLOW_FIELDS['bus'])
        self.assertEqual(num_fields_before, num_fields_after)


class IdentifyNumericFieldsTestCase(unittest.TestCase):
    """Test identify_numeric_fields."""

    # noinspection PyMethodMayBeStatic
    def test_correct(self):
        # Intentionally make the fields out of alphabetical order.
        if VERSION in [21, 22]:
            fields = ['LineStatus', 'LockOut', 'LineR', 'LineX', 'BusNum']
            expected = np.array([False, False, True, True, True])
        elif VERSION == 17:
            # The LockOut field is not present in version 17.
            fields = ['LineStatus', 'LineR', 'LineX', 'BusNum']
            expected = np.array([False, True, True, True])
        else:
            raise NotImplementedError(
                'If you encounter this error, please update this test for the '
                'version of PowerWorld Simulator that you are using. Thus far,'
                ' it has only been tested with version 17 and 21.'
            )

        actual = \
            saw_14.identify_numeric_fields(ObjectType='Branch', fields=fields)
        np.testing.assert_array_equal(actual, expected)


class GetVersionAndBuildDateTestCase(unittest.TestCase):
    """Test get_version_and_builddate."""

    # noinspection PyMethodMayBeStatic
    def test_correct(self):
        self.assertIsInstance(saw_14.get_version_and_builddate(), tuple)


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
        # UIVisible introduced in version 20.
        if VERSION >= 20:
            self.saw.set_simauto_property('UIVisible', False)
            self.assertFalse(self.saw._pwcom.UIVisible)
        else:
            with self.assertLogs(logger=self.saw.log, level='WARN'):
                self.saw.set_simauto_property('UIVisible', False)

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

    def test_set_bad_property_name(self):
        m = 'The given property_name, junk,'
        with self.assertRaisesRegex(ValueError, m):
            self.saw.set_simauto_property(property_name='junk',
                                          property_value='42')

    def test_attr_error_for_ui_visible(self):
        """Force the UIVisible attribute to throw an error.
        """
        with self.assertLogs(logger=self.saw.log, level='WARN'):
            with patch.object(self.saw, '_set_simauto_property',
                              side_effect=AttributeError):
                self.saw.set_simauto_property('UIVisible', True)

    def test_re_raise_attr_error(self):
        """Ensure that a non UIVisible property correctly re-raises
        the attribute error.
        """
        with patch.object(self.saw, '_set_simauto_property',
                          side_effect=AttributeError('my special error')):
            with self.assertRaisesRegex(AttributeError, 'my special error'):
                self.saw.set_simauto_property('CreateIfNotFound', False)


class GetYbusTestCase(unittest.TestCase):
    """Test get_ybus function."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(PATH_14, early_bind=True)

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_get_ybus_default(self):
        """It should return a scipy csr_matrix.
        """
        self.assertIsInstance(self.saw.get_ybus(), csr_matrix)

    def test_get_ybus_full(self):
        """It should return a numpy array of full matrix.
        """
        self.assertIsInstance(self.saw.get_ybus(True), np.ndarray)


class GetJacobianTestCase(unittest.TestCase):
    """Test get_jacobian function."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(PATH_14, early_bind=True)

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_get_jacobian_default(self):
        """It should return a scipy csr_matrix.
        """
        self.assertIsInstance(self.saw.get_jacobian(), csr_matrix)

    def test_get_jacobian_full(self):
        """It should return a numpy array of full matrix.
        """
        self.assertIsInstance(self.saw.get_jacobian(full=True), np.ndarray)


class ToGraphTestCase(unittest.TestCase):
    """Test the to_graph function."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(PATH_14, early_bind=True)

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_to_graph_default(self):
        """It should return a networkx multigraph object.
        """
        self.assertIsInstance(self.saw.to_graph(), nx.MultiGraph)

    def test_to_graph_invalid_node_type(self):
        """It should raise a value exception.
        """
        self.assertRaises(ValueError, self.saw.to_graph, node='area')

    def test_to_graph_bus_with_node_attr(self):
        """Node should have an attribute named BusName"""
        graph = self.saw.to_graph(node='bus', node_attr='BusName')
        self.assertIsNotNone(graph.nodes(data='BusName'))

    def test_to_graph_directed(self):
        """It should return a networkx multidigraph object."""
        self.assertIsInstance(self.saw.to_graph(directed=True),
                              nx.MultiDiGraph)

    def test_to_graph_geographic(self):
        """Geographic information should exist in the node's attributes"""
        graph = self.saw.to_graph(node='bus', geographic=True)
        self.assertIsNotNone(graph.nodes(data='Latitude:1'))

    def test_to_graph_with_edge_attr(self):
        """Edge attributes should exist"""
        graph = self.saw.to_graph(node='bus', edge_attr='LineMVA')
        self.assertIsNotNone(graph.edges(data='LineMVA'))

    def test_to_graph_with_edge_attrs(self):
        """Edge attributes should exist"""
        graph = self.saw.to_graph(node='bus', edge_attr=['LineMVR', 'LineMVA'])
        self.assertIsNotNone(graph.edges(data='LineMVA'))

    def test_to_graph_with_invalid_edge_attrs(self):
        """ValueError should raise"""
        with self.assertRaisesRegex(ValueError, 'The given object has fields '
                                                'which do not match a '
                                                'PowerWorld internal field '
                                                'name!'):
            self.saw.to_graph(node='bus', edge_attr=['TAMU'])

    def test_to_graph_with_invalid_node_attrs(self):
        """ValueError should raise"""
        with self.assertRaisesRegex(ValueError, 'The given object has fields '
                                                'which do not match a '
                                                'PowerWorld internal field '
                                                'name!'):
            self.saw.to_graph(node='bus', node_attr=['TAMU'])

    def test_to_graph_substation(self):
        """AttributeError should raise cause the 14 bus case does not have
        any substation assigned"""
        with self.assertRaises(AttributeError):
            self.saw.to_graph(node='substation', geographic=True)


class UpdateUITestCase(unittest.TestCase):
    """Test the update_ui method. To avoid conflicts with
    other tests we'll create a fresh SAW instance here.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(PATH_14, early_bind=True)

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_update_default(self):
        """It should work with or without the visible UI.
        """
        self.assertIsNone(self.saw.update_ui())


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


class ChangeParametersMultipleElementFlatInputTestCase(unittest.TestCase):
    """Test ChangeParametersMultipleElementFlatInput"""

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
        num_objects = len(value_list)
        flattened_value_list = [val for sublist in value_list for val in
                                sublist]
        saw_14.ChangeParametersMultipleElementFlatInput(
            ObjectType='gen', ParamList=cls.params,
            NoOfObjects=num_objects, ValueList=flattened_value_list)

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
        num_objects = len(value_list)
        # noinspection PyTypeChecker
        flattened_value_list = [val for sublist in value_list for val in
                                sublist]
        self.assertIsNone(saw_14.ChangeParametersMultipleElementFlatInput(
            ObjectType='gen', ParamList=self.params,
            NoOfObjects=num_objects, ValueList=flattened_value_list))

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

    # noinspection PyTypeChecker
    def test_nested_value_list(self):
        with self.assertRaisesRegex(Error,
                                    'The value list has to be a 1-D array'):
            value_list = self.gen_v_pu.to_numpy().tolist()
            num_objects = len(value_list)
            saw_14.ChangeParametersMultipleElementFlatInput(
                ObjectType='gen', ParamList=self.params,
                NoOfObjects=num_objects, ValueList=value_list)


class ChangeParametersTestCase(unittest.TestCase):
    """Test ChangeParameters.

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
        saw_14.ChangeParameters('Branch', self.params, values_list)

        # Retrieve the updated line parameters.
        new_line_data = saw_14.GetParametersMultipleElement(
            'Branch', self.params)

        # Ensure the update went through.
        self.assertEqual(new_line_data.iloc[0]['LineR'], new_r)


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
        actual = field_list.columns.to_numpy().tolist()

        # Check FIELD_LIST_COLUMNS first, then check
        # FIELD_LIST_COLUMNS_OLD
        new = False
        old = False

        try:
            self.assertEqual(saw_14.FIELD_LIST_COLUMNS, actual)
        except AssertionError:
            new = True

        try:
            self.assertEqual(saw_14.FIELD_LIST_COLUMNS_OLD, actual)
        except AssertionError as e2:
            old = True

        if new and old:
            raise AssertionError('Valid columns:\n{}\n{}\nReceived:{}'
                                 .format(saw_14.FIELD_LIST_COLUMNS,
                                         saw_14.FIELD_LIST_COLUMNS_OLD,
                                         actual))

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

    def test_switch_to_old_field_list(self):
        """Ensure that switching to "FIELD_LIST_COLUMNS_OLD works as
        it should.
        """
        # Patch _object_fields to force a key error.
        with patch.object(saw_14, '_object_fields', new={'dict': 1}):
            # Patch _call_simauto to give us data that matches the shape
            # of the FIELD_LIST_COLUMNS_OLD.
            out = [['x'] * len(saw_14.FIELD_LIST_COLUMNS_OLD) for _ in
                   range(10)]

            with patch.object(saw_14, '_call_simauto', return_value=out):
                result = saw_14.GetFieldList('bus')

        # Ensure the result is a DataFrame.
        self.assertIsInstance(result, pd.DataFrame)

        # Ensure the columns are the "OLD" ones.
        self.assertListEqual(result.columns.tolist(),
                             saw_14.FIELD_LIST_COLUMNS_OLD)

        # Ensure the shape is right. Hard-code the 10.
        self.assertEqual(result.shape,
                         (10, len(saw_14.FIELD_LIST_COLUMNS_OLD)))

    def test_df_value_error_not_from_old_list(self):
        """Make sure ValueError gets re-raised."""
        # Patch DataFrame creation to raise error.
        with patch('pandas.DataFrame', side_effect=ValueError('stuff n th')):
            # Patch _object fields so that SimAuto is called. Using a
            # dict for 'new' is Brandon's hack to force a KeyError.
            with patch.object(saw_14, '_object_fields', new={'dict': 1}):
                # Ensure we get our DataFrame ValueError back.
                with self.assertRaisesRegex(ValueError, 'stuff n th'):
                    saw_14.GetFieldList('bus')


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


class GetParametersMultipleElementFlatOutput(unittest.TestCase):
    """Test GetParametersMultipleElementFlatOutput"""

    def test_get_gen_voltage_set_points(self):
        params = ['BusNum', 'GenID', 'GenRegPUVolt']
        results = saw_14.GetParametersMultipleElementFlatOutput(
            ObjectType='gen', ParamList=params)

        self.assertIsInstance(results, tuple)

        # Check that the length of the tuple is as expected, noting that
        # the first two elements denote the number of elements and
        # number of fields per element.
        self.assertEqual(int(results[0]) * int(results[1]) + 2,
                         len(results))

    def test_shunts(self):
        # 14 bus has no shunts.
        kf = saw_14.get_key_field_list('shunt')
        self.assertIsNone(
            saw_14.GetParametersMultipleElementFlatOutput(
                'shunt', kf))


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


class GetParametersTestCase(unittest.TestCase):
    """Test GetParameters method."""

    # noinspection PyMethodMayBeStatic
    def test_expected_results(self):
        fields = ['BusNum', 'BusNum:1', 'LineCircuit', 'LineX']

        actual = saw_14.GetParameters(
            ObjectType='branch', ParamList=fields, Values=[4, 9, '1', 0])

        expected = pd.Series([4, 9, '1', 0.556180], index=fields)

        pd.testing.assert_series_equal(actual, expected)

    def test_nonexistent_object(self):
        """Ensure an exception is raised if the object cannot be found.
        """
        with self.assertRaisesRegex(PowerWorldError, 'Object not found'):
            # 14 bus certainly does not have a 100th bus.
            # noinspection PyUnusedLocal
            actual = saw_14.GetParameters(
                ObjectType='gen', ParamList=['BusNum', 'GenID', 'GenMW'],
                Values=[100, '1', 0]
            )

    def test_bad_field(self):
        """Ensure an exception is raised when a bad field is provided.
        """
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14.GetParameters(
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
        # noinspection PyTypeChecker
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


class GetCaseHeaderTestCase(unittest.TestCase):
    """Test GetCaseHeader"""

    def test_case_header(self):
        # Call method.
        out = saw_14.GetCaseHeader()

        self.assertIsInstance(out, tuple)

        for item in out:
            self.assertIsInstance(item, str)


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
        cls.saw = SAW(FileName=PATH_2000, early_bind=True, UIVisible=False)

    @classmethod
    def tearDownClass(cls) -> None:
        # noinspection PyUnresolvedReferences
        cls.saw.exit()

    def test_process_aux_ltc_filter(self):
        # Process the aux file. Note the aux file has a named filter,
        # "area_filter"
        self.saw.ProcessAuxFile(FileName=AREA_AUX_FILE)

        # Get bus key fields.
        kf = self.saw.get_key_field_list('bus')

        # Get bus data, using the named filter.
        area_bus = self.saw.GetParametersMultipleElement(
            ObjectType='bus', ParamList=kf, FilterName="area_filter"
        )

        # Check that the filter worked.
        bus = self.saw.GetParametersMultipleElement(
            ObjectType='bus', ParamList=kf + ['AreaName']
        )

        # Ensure the bus data is not getting filtered.
        self.assertNotEqual(area_bus.shape[0], bus.shape[0])

        # Ensure the number of buses in the area matches up.
        bus_expected = bus['AreaName'] == 'East'
        self.assertEqual(bus_expected.sum(), area_bus.shape[0])


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


class OpenCaseTypeTestCase(unittest.TestCase):
    """Test OpenCaseType. The tests here are admittedly a bit crude."""
    @classmethod
    def setUpClass(cls) -> None:
        cls.saw = SAW(PATH_14)

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls) -> None:
        cls.saw.exit()

    def test_expected_behavior(self):
        self.saw.CloseCase()
        self.saw.OpenCaseType(PATH_14, 'PWB')
        # Ensure our pwb_file_path matches our given path.
        self.assertEqual(PATH_14,
                         self.saw.pwb_file_path)

    def test_options_single(self):
        # Ensure this runs without error.
        self.saw.OpenCaseType(PATH_14, 'PWB', 'YES')

    def test_options_multiple(self):
        # Ensure this runs without error.
        self.saw.OpenCaseType(PATH_14, 'PWB', ['YES', 'NEAR'])


class OpenCaseTestCase(unittest.TestCase):
    """Test OpenCase."""
    def test_failure_if_pwb_file_path_none(self):
        m = 'When OpenCase is called for the first time,'
        with patch.object(saw_14, 'pwb_file_path', new=None):
            with self.assertRaisesRegex(TypeError, m):
                saw_14.OpenCase()


class TSGetContingencyResultsTestCase(unittest.TestCase):
    """Test TSGetContingencyResults."""

    @classmethod
    def setUpClass(cls) -> None:
        # Open up the nine bus model.
        cls.saw = SAW(PATH_9, early_bind=True)

        # The 9 bus model has a contingency already defined:
        cls.ctg_name = 'My Transient Contingency'

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls) -> None:
        cls.saw.exit()

    def test_nonexistent_ctg(self):
        """Should get Nones back when running a contingency that does
        not exist.
        """
        # Define contingency name.
        ctg_name = 'ctgName'

        #
        obj_field_list = ['"Plot ''Gen_Rotor Angle''"']

        #
        t1 = '0.0'
        t2 = '10.0'

        meta, data = self.saw.TSGetContingencyResults(ctg_name, obj_field_list,
                                                      t1, t2)

        self.assertIsNone(meta)
        self.assertIsNone(data)

    @unittest.skip('This test hangs. PowerWorld somehow gets upset if you '
                   'ask for results and have not solved the transient '
                   'contingency.')
    def test_existing_ctg(self):
        """THIS HANGS! Contingency exists in case, but has not been
        solved yet."""
        # This came from a PowerWorld example:
        obj_field_list = ['"Plot ''Gen_Rotor Angle''"']

        #
        t1 = '0.0'
        t2 = '10.0'

        result = self.saw.TSGetContingencyResults(
            self.ctg_name, obj_field_list, t1, t2)

        print(result)

        pass

    def test_solve_and_run(self):
        """Solve the contingency and run the function."""
        # This came from a PowerWorld example:
        obj_field_list = ['"Plot ''Gen_Rotor Angle''"']

        #
        t1 = '0.0'
        t2 = '10.0'

        # Solve.
        self.saw.RunScriptCommand('TSSolve("{}")'.format(self.ctg_name))

        # Get results.
        meta, data = self.saw.TSGetContingencyResults(
            self.ctg_name, obj_field_list, t1, t2)

        # Check types.
        self.assertIsInstance(meta, pd.DataFrame)
        self.assertIsInstance(data, pd.DataFrame)

        # Ensure shapes are as expected.
        self.assertEqual(meta.shape[0], data.shape[1] - 1)

        # Data should all be floats.
        for dtype in data.dtypes:
            self.assertEqual(dtype, np.float64)

        # Rows in meta should match columns in data.
        meta_rows = meta.index.tolist()
        data_cols = data.columns.tolist()

        # Remove time from data columns.
        data_cols.remove('time')

        self.assertListEqual(meta_rows, data_cols)

    def test_individual_object_field_pair(self):
        """Obtain the result for an individual object/field pair"""
        # The target is the frequency data from Bus 4.
        obj_field_list = ['"Bus 4 | frequency"']

        # Set up TS parameters
        t1 = 0.0
        t2 = 10.0
        stepsize = 0.01

        # Solve.
        cmd = 'TSSolve("{}",[{},{},{},NO])'.format(
            self.ctg_name, t1, t2, stepsize
        )
        self.saw.RunScriptCommand(cmd)

        # Get results.
        meta, data = self.saw.TSGetContingencyResults(
            self.ctg_name, obj_field_list, str(t1), str(t2))

        # Ensure shapes are as expected.
        self.assertEqual(meta.shape[0], 1)  # Only 1 object/field pair
        self.assertEqual(data.shape[1], 2)  # Plus the time column

        # ObjectType should be Bus
        self.assertEqual(meta['ObjectType'].values[0], 'Bus')

        # Primary key should be 4.
        self.assertEqual(meta['PrimaryKey'].values[0], '4')

        # Start and end time should match the arguments in the query.
        self.assertEqual(data['time'].iloc[0], t1)
        self.assertEqual(data['time'].iloc[-1], t2)

        # Data row count >= (t2 - t1)/stepsize + contingency count + 1
        # This is due to the repeated time point when contingencies
        # occur, and also some contingencies are self-cleared (which
        # only show once in the contingency element list but will also
        # result in repeated time point when it is cleared.
        params = self.saw.get_key_field_list('TSContingencyElement')
        contingency = self.saw.GetParametersMultipleElement(
            'TSContingencyElement', params)
        self.assertGreaterEqual(data.shape[0],
                                (t2-t1)/stepsize+contingency.shape[0]+1)


class WriteAuxFileTestCaseTestCase(unittest.TestCase):
    """Test WriteAuxFile."""

    def test_file_is_created(self):
        temp_path = tempfile.NamedTemporaryFile(mode='w', suffix='.axd',
                                                delete=False)
        temp_path.close()
        saw_14.WriteAuxFile(FileName=temp_path.name,
                            FilterName="",
                            ObjectType="Bus",
                            FieldList="all")
        self.assertTrue(os.path.isfile(temp_path.name))
        os.unlink(temp_path.name)


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

    def test_save_with_missing_path(self):
        m = 'SaveCase was called without a FileName, but it would appear'
        with patch.object(saw_14, 'pwb_file_path', new=None):
            with self.assertRaisesRegex(TypeError, m):
                saw_14.SaveCase()


class SendToExcel(unittest.TestCase):
    """Test SendTOExcel
    The author was not able to sufficiently test this method, since
    the tested function would open an excel sheet and copy to it without
    saving. This also creates a big problem when trying to use the excel
    COM interface to access the sheet and verify the data, cause the COM
    object is likely in use and cannot be operated by another process.
    """

    def test_nonexistobject(self):
        """Ensure an exception is raised if the object can't be found"""
        with self.assertRaises(PowerWorldError):
            # No object type named Gen1 "
            fields = ['BusNum', 'GenID', 'BusNomVolt']
            saw_14.SendToExcel(
                ObjectType='Gen1', FilterName='', FieldList=fields)


########################################################################
# Properties tests
########################################################################

# noinspection PyStatementEffect
class SimAutoPropertiesTestCase(unittest.TestCase):
    """Test the SimAuto attributes."""

    def test_current_dir(self):
        cwd = saw_14.CurrentDir
        self.assertIsInstance(cwd, str)
        self.assertIn('ESA', cwd)

    def test_process_id(self):
        pid = saw_14.ProcessID
        self.assertIsInstance(pid, int)

    def test_request_build_date(self):
        bd = saw_14.RequestBuildDate
        self.assertIsInstance(bd, int)

    def test_ui_visible(self):
        # UIVisible introduced in version 20.
        if VERSION >= 20:
            self.assertFalse(saw_14.UIVisible)
        else:
            with self.assertLogs(logger=saw_14.log, level='WARN'):
                saw_14.UIVisible

    def test_attr_error_ui_visible(self):
        """Patch UIVisible, and ensure we get a warning when it throws
        an attribute error.
        """
        # Create a mock for saw_14_pwcom. This is necessary because
        # patching attributes of the actual COM object doesn't work
        # very well.
        com_patch = MagicMock()
        # seal the mock so that attempts to access non-existent
        # attribute will result in an AttributeError.
        seal(com_patch)

        # Mock out _pwcom and get the UIVisible attribute.
        with patch.object(saw_14, '_pwcom', new=com_patch):
            with self.assertLogs(logger=saw_14.log, level='WARN'):
                result = saw_14.UIVisible

        self.assertFalse(result)

    def test_create_if_not_found(self):
        self.assertFalse(saw_14.CreateIfNotFound)


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


class OpenOneLineTestCase(unittest.TestCase):
    """Test the OpenOneLine method. Note PowerWorld doesn't return
    anything for this script command, so we should always get None back
    unless there is an error.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # For now, skip old versions of PowerWorld.
        # TODO: remove this skip statement after saving the .pwd files
        #   in different PowerWorld formats.
        skip_if_version_below(21)

    def test_open_default(self):
        """Open the correct pwd file.
        """
        self.assertIsNone(saw_14.OpenOneLine(PATH_14_PWD))

    def test_open_invalid_format_file(self):
        """Open the non-PWD file should raise a PowerWorld Error
        """
        with self.assertRaisesRegex(PowerWorldError,
                                    'Error opening oneline'):
            saw_14.OpenOneLine(PATH_14)


class CloseOnelineTestCase(unittest.TestCase):
    """Test the CloseOneline method. Note PowerWorld doesn't return
    anything for this script command, so we should always get None back
    unless there is an error.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # For now, skip old versions of PowerWorld.
        # TODO: remove this skip statement after saving the .pwd files
        #   in different PowerWorld formats.
        skip_if_version_below(21)

    def test_close_default(self):
        """Close the last focused oneline diagram.
        """
        saw_14.OpenOneLine(PATH_14_PWD)
        self.assertIsNone(saw_14.CloseOneline())

    def test_close_with_name(self):
        """Close the oneline diagram with the CORRECT name.
        """
        saw_14.OpenOneLine(PATH_14_PWD)
        self.assertIsNone(saw_14.CloseOneline(os.path.basename(PATH_14_PWD)))

    def test_close_with_wrong_name(self):
        """Close the oneline diagram with wrong name should raise a
        PowerWorld Error
        """
        saw_14.OpenOneLine(PATH_14_PWD)
        with self.assertRaisesRegex(PowerWorldError,
                                    'Cannot find Oneline'):
            saw_14.CloseOneline("A file that cannot be found")

    def test_close_with_invalid_identifier(self):
        """Close the oneline diagram with invalid identifier should
        raise a PowerWorld Error
        """
        saw_14.OpenOneLine(PATH_14_PWD)
        with self.assertRaisesRegex(PowerWorldError,
                                    'invalid identifier character'):
            saw_14.CloseOneline(PATH_14_PWD)


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


class CallSimAutoTestCase(unittest.TestCase):
    """Test portions of _call_simauto not covered by the higher level
    methods.
    """
    def test_bad_function(self):
        with self.assertRaisesRegex(AttributeError, 'The given function, bad'):
            saw_14._call_simauto('bad')

    def test_weird_type_error(self):
        """I'll be honest - I'm just trying to get testing coverage to
        100%, and I have no idea how to get this exception raised
        without doing some hacking. Here we go.
        """
        m = MagicMock()
        m.GetParametersSingleElement = Mock(return_value=('issues', 12))
        with patch.object(saw_14, '_pwcom', new=m):
            with patch('esa.saw.PowerWorldError',
                       side_effect=TypeError('weird things')):
                with self.assertRaises(TypeError):
                    saw_14.GetParametersSingleElement('bus', ['BusNum'], [1])


class ToNumericTestCase(unittest.TestCase):
    """Test the _to_numeric method. Fortunately, most of the code in
    the _to_numeric method is already covered by other existing tests,
    so here we'll be focusing on using commas as a decimal delimiter.
    """

    # noinspection PyMethodMayBeStatic
    def test_df_commas(self):
        df_in = pd.DataFrame([['1,2', ' 3,5'], ['4,7 ', "  1,059"]])
        expected = pd.DataFrame([[1.2, 3.5], [4.7, 1.059]])

        with patch.object(saw_14, 'decimal_delimiter', new=','):
            df_out = saw_14._to_numeric(df_in)

        pd.testing.assert_frame_equal(expected, df_out)

    # noinspection PyMethodMayBeStatic
    def test_series_commas(self):
        series_in = pd.Series(['456,3', '82,1', '97'])
        expected = pd.Series([456.3, 82.1, 97])

        with patch.object(saw_14, 'decimal_delimiter', new=','):
            series_out = saw_14._to_numeric(series_in)

        pd.testing.assert_series_equal(expected, series_out)

    def test_bad_data_input(self):
        """Only DataFrames and Series are allowed."""
        with self.assertRaisesRegex(TypeError, 'data must be either a Data'):
            # noinspection PyTypeChecker
            saw_14._to_numeric('not a df')

    def test_bad_errors_input(self):
        """Pandas will throw an error if the errors input is invalid."""
        s_in = pd.Series(np.array(['1.2'] * 3))
        with self.assertRaisesRegex(ValueError, 'invalid error value'):
            saw_14._to_numeric(data=s_in, errors='silly')

    def test_get_power_flow_results_with_commas(self):
        """This test isn't exactly in the right place, but the spirit
        of it belongs here.

        Essentially, we're going to take the output from the following
        comment:
        https://github.com/mzy2240/ESA/issues/56#issuecomment-643814343

        And ensure things work without throwing an error.

        Note the issue was originally brought up in this comment:
        https://github.com/openjournals/joss-reviews/issues/2289#issuecomment-643482550
        """
        # Hard-code expected output from the comment linked in the
        # docstring.
        output = (('    1', '    2', '    3', '    4', '    5', '    6',
                   '    7', '    8', '    9', '   10', '   11', '   12',
                   '   13', '   14'),
                  ('Bus 1', 'Bus 2', 'Bus 3', 'Bus 4', 'Bus 5', 'Bus 6',
                   'Bus 7', 'Bus 8', 'Bus 9', 'Bus 10', 'Bus 11', 'Bus 12',
                   'Bus 13', 'Bus 14'),
                  ('  1,05999994', '  1,04499996', '  1,00999999',
                   '  1,01767162', '  1,01951459', '  1,07000005',
                   '  1,06152019', '  1,09000003', '  1,05593281',
                   '  1,05098559', '  1,05690694', '  1,05518907',
                   '  1,05038265', '  1,03553058'), (
                  '  0,00000000', ' -4,98255334', '-12,72502699',
                  '-10,31282882', ' -8,77379918', '-14,22086891',
                  '-13,35955842', '-13,35957101', '-14,93845750',
                  '-15,09722071', '-14,79055172', '-15,07551240',
                  '-15,15619553', '-16,03356498'), (
                  '232,39169121', ' 18,30000132', '-94,19999719',
                  '-47,79999852', ' -7,59999976', '-11,20000035',
                  '  0,00000000', '  0,00000000', '-29,49999869',
                  ' -9,00000036', ' -3,50000001', ' -6,10000007',
                  '-13,50000054', '-14,90000039'), (
                  '-16,54938906', ' 30,85595667', '  6,07485175',
                  '  3,90000008', ' -1,60000008', '  5,22969961',
                  '  0,00000000', ' 17,62306690', '  4,58488762',
                  ' -5,79999983', ' -1,79999992', ' -1,60000008',
                  ' -5,79999983', ' -5,00000007'))

        # Force the decimal delimiter to be a comma.
        with patch.object(saw_14, 'decimal_delimiter', new=','):
            # Patch _call_simauto.
            with patch.object(saw_14, '_call_simauto', return_value=output):
                df = saw_14.get_power_flow_results('bus')

        # Ensure it's a DataFrame.
        self.assertIsInstance(df, pd.DataFrame)

        # Ensure BusNum comes back as an integer. This isn't a great
        # test, but it's something.
        self.assertTrue(df['BusNum'].dtype == np.dtype('int64'))

        # Ensure we get floats for voltage.
        self.assertTrue(df['BusPUVolt'].dtype == np.dtype('float64'))


if __name__ == '__main__':
    unittest.main()
