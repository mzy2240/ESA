""""""
import unittest
from unittest.mock import patch
import os
import numpy as np
import pandas as pd
from esa import SAW
from esa.saw import COMError, PowerWorldError,\
    convert_to_posix_path, CommandNotRespectedError
import logging

# Handle pathing.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to IEEE 14 bus model.
PATH_14 = os.path.join(THIS_DIR, 'cases', 'ieee_14', 'IEEE 14 bus.pwb')

# Initialize the 14 bus SimAutoWrapper.
saw_14 = None


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
        self.assertEqual(2, len(my_saw_14.object_fields))

        for f in ['bus', 'shunt']:
            df = my_saw_14.object_fields[f]
            self.assertIsInstance(df, pd.DataFrame)
            self.assertSetEqual({'key_field', 'internal_field_name',
                                 'field_data_type', 'description',
                                 'display_name'},
                                set(df.columns.values))

########################################################################
# Helper function tests
########################################################################


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
                self.assertSetEqual(set(result.columns.values),
                                    set(object_fields))
                # No NaNs.
                self.assertFalse(result.isna().any().any())

    def test_shunt(self):
        """There are no shunts in the IEEE 14 bus model."""
        self.assertIsNone(saw_14.get_power_flow_results('shunt'))

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
            cls.key_field_df_gens['internal_field_name'].values.tolist()
        # Combine key fields with our desired attribute.
        cls.params.append('GenVoltSet')
        cls.gen_v_pu = saw_14.GetParametersMultipleElement(
            ObjectType='gen', ParamList=cls.params)

    # noinspection PyUnresolvedReferences
    @classmethod
    def tearDownClass(cls) -> None:
        """Always be nice and clean up after yourself and put your toys
        away. No, but seriously, put the voltage set points back."""
        value_list = cls.gen_v_pu.values.tolist()
        saw_14.ChangeParametersMultipleElement(
            ObjectType='gen', ParamList=cls.params, ValueList=value_list)

    # noinspection DuplicatedCode
    def test_change_gen_voltage_set_points(self):
        """Set all generator voltages to 1, and ensure the command
        sticks.
        """
        # https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/ChangeParametersMultipleElement_Sample_Code_Python.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____9
        # Start by converting our generator data to a list of lists.
        value_list = self.gen_v_pu.values.tolist()

        # Loop over the values, set to 1.
        for v in value_list:
            # Set voltage at 1.
            v[-1] = 1.0

        # Send in the command.
        result = saw_14.ChangeParametersMultipleElement(
            ObjectType='gen', ParamList=self.params, ValueList=value_list)

        self.assertIsNone(result)

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
        # actual = pd.to_numeric(gen_v['GenRegPUVolt']).values
        actual = pd.to_numeric(gen_v['GenVoltSet']).values
        expected = np.array([1.0] * actual.shape[0])

        np.testing.assert_array_equal(actual, expected)

    def test_missing_key_fields(self):
        # Extract a portion of the gen_v_pu DataFrame which was created
        # in setUpClass. Notably, this is missing GenID.
        df = self.gen_v_pu[['BusNum', 'GenVoltSet']]

        # Convert to list.
        value_list = df.values.tolist()

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
        value_list = self.gen_v_pu.values.tolist()

        # Delete an entry.
        del value_list[1][-1]

        m = 'Number of fields and number of values given are not equal'
        with self.assertRaisesRegex(PowerWorldError, m):
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
            cls.key_field_df_gens['internal_field_name'].values.tolist()
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
        value_list = self.gen_v_pu.values.tolist()

        # Loop over the values, set to 1.
        for v in value_list:
            # Set voltage at 1.
            v[-1] = 1.0

        # Send in the command.
        result = saw_14.ChangeParametersMultipleElement(
            ObjectType='gen', ParamList=self.params, ValueList=value_list)

        self.assertIsNone(result)

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

        result = saw_14.change_and_confirm_params_multiple_element(
            ObjectType='gen', command_df=command_df)

        self.assertIsNone(result)


class GetFieldListTestCase(unittest.TestCase):
    """Test the GetFieldList method"""

    def check_field_list(self, field_list):
        """Helper to check a returned field list DataFrame."""
        self.assertIsInstance(field_list, pd.DataFrame)
        self.assertEqual(saw_14.FIELD_LIST_COLUMNS,
                         field_list.columns.values.tolist())
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
        self.assertNotIn(obj_type, saw_14.object_fields)

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
            self.assertIn(obj_type, saw_14.object_fields)

        finally:
            # Always remove from the object_fields dictionary to avoid
            # state changes that could impact other tests.
            del saw_14.object_fields[obj_type]

    def test_copy_true(self):
        """Ensure we get a copy when asked for."""
        field_list = saw_14.GetFieldList('gen', copy=True)
        self.assertIsNot(field_list, saw_14.object_fields['gen'])

    def test_copy_false(self):
        """Ensure we don't get a copy when we don't ask for it."""
        field_list = saw_14.GetFieldList('branch')
        self.assertIs(field_list, saw_14.object_fields['branch'])

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
        self.assertSetEqual(set(params), set(results.columns.values))

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
        self.assertIn('BusNum', result.columns.values)
        self.assertIn('BusNum:1', result.columns.values)
        self.assertIn('LineCircuit', result.columns.values)

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


class RunScriptCommandTestCase(unittest.TestCase):
    """Light weight testing of RunScriptCommand."""

    # noinspection PyMethodMayBeStatic
    def test_calls_call_simauto(self):
        """RunScriptCommand is a simple wrapper. Enforce this."""
        with patch.object(saw_14, '_call_simauto') as p:
            saw_14.RunScriptCommand(Statements='Some stuff')

        # _call_simauto should have been called once.
        p.assert_called_once()

        # The Statements should simply be passed through.
        p.assert_called_with('RunScriptCommand', 'Some stuff')

    def test_exception_for_bad_statement(self):
        """Ensure an exception is thrown for a bad statement."""
        with self.assertRaisesRegex(PowerWorldError,
                                    'Error in script statements definition'):
            saw_14.RunScriptCommand(Statements='invalid statement')

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
        result = saw_14.SolvePowerFlow()
        self.assertIsNone(result)

    def test_solve_bad_method(self):
        """Given a bad solver, we should expect an exception."""
        with self.assertRaisesRegex(PowerWorldError,
                                    'Invalid solution method'):
            saw_14.SolvePowerFlow(SolMethod='junk')

########################################################################
# Private method tests
########################################################################


class ChangeAndConfirmParamsMultipleElementTestCase(unittest.TestCase):
    """Test change_and_confirm_params_multiple_element."""

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
            result = saw_14.change_and_confirm_params_multiple_element(
                ObjectType='load', command_df=command_df)

        self.assertIsNone(result)

    def test_failure(self):
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


class CleanDFOrSeriesTestCase(unittest.TestCase):
    def test_bad_df_columns(self):
        """If the DataFrame columns are not valid fields, we should get
        an error.
        """
        bad_df = pd.DataFrame([[1, 'bleh']], columns=['BusNum', 'bleh'])
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14._clean_df_or_series(obj=bad_df, ObjectType='gen')

    def test_bad_df_columns_2(self):
        """This time, use upper-case so we don't get an index error."""
        bad_df = pd.DataFrame([[1, 'bleh']], columns=['BusNum', 'Bleh'])
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14._clean_df_or_series(obj=bad_df, ObjectType='gen')

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

        df_actual = saw_14._clean_df_or_series(obj=df_in, ObjectType='gen')

        pd.testing.assert_frame_equal(df_actual, df_expected)

    def test_bad_type(self):
        """Ensure a TypeError is raised if 'obj' is a bad type."""
        with self.assertRaisesRegex(TypeError, 'The given object is not a Da'):
            saw_14._clean_df_or_series(obj=42, ObjectType='shunt')

    def test_series_bad_index(self):
        """If a Series has an Index that doesn't match known fields, we
        should get an exception.
        """
        bad_series = pd.Series([1, 'a'], index=['BusNum', 'Bad_Field'])
        with self.assertRaisesRegex(ValueError, 'The given object has fields'):
            saw_14._clean_df_or_series(obj=bad_series, ObjectType='gen')


if __name__ == '__main__':
    unittest.main()
