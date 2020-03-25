"""saw is short for SimAuto Wrapper. This module provides a class,
SAW, for interfacing with PowerWorld's Simulator Automation Server
(aka SimAuto).

The documentation for SimAuto can be found
`here
<https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7C_____1>`__
"""
import pandas as pd
import numpy as np
import pywintypes
import pythoncom
import win32com
from win32com.client import VARIANT
from typing import Union, List
from pathlib import Path, PureWindowsPath
import logging
import os

# TODO: Make logging more configurable.
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)

# Listing of PowerWorld data types. I guess 'real' means float?
DATA_TYPES = ['Integer', 'Real', 'String']
# Hard-code based on indices.
NUMERIC_TYPES = DATA_TYPES[0:2]
NON_NUMERIC_TYPES = DATA_TYPES[-1]

# Message for NotImplementedErrors.
NIE_MSG = ('This method is either not complete or untested. We appreciate '
           'contributions, so if you would like to complete and test this '
           'method, please read contributing.md. If there is commented out '
           'code, you can uncomment it and re-install esa from source at '
           'your own risk.')


# noinspection PyPep8Naming
class SAW(object):
    """A SimAuto Wrapper in Python"""

    # Class level property defining the fields which will be returned
    # for different ObjectTypes by the get_power_flow_results method.
    POWER_FLOW_FIELDS = {
        'bus': ['BusNum', 'BusName', 'BusPUVolt', 'BusAngle', 'BusNetMW',
                'BusNetMVR'],
        'gen': ['BusNum', 'GenID', 'GenMW', 'GenMVR'],
        'load': ['BusNum', 'LoadID', 'LoadMW', 'LoadMVR'],
        'shunt': ['BusNum', 'ShuntID', 'ShuntMW', 'ShuntMVR'],
        'branch': ['BusNum', 'BusNum:1', 'LineCircuit', 'LineMW',
                   'LineMW:1', 'LineMVR', 'LineMVR:1']
    }

    # Class level property defining the columns used by the DataFrame
    FIELD_LIST_COLUMNS = \
        ['key_field', 'internal_field_name', 'field_data_type', 'description',
         'display_name']

    # SimAuto properties that we allow users to set via the
    # set_simauto_property method.
    SIMAUTO_PROPERTIES = {'CreateIfNotFound': bool, 'CurrentDir': str,
                          'UIVisible': bool}

    def __init__(self, FileName, early_bind=False, UIVisible=False,
                 object_field_lookup=('bus', 'gen', 'load', 'shunt',
                                      'branch'),
                 CreateIfNotFound=False):
        """Initialize SimAuto wrapper. The case will be opened, and
        object fields given in object_field_lookup will be retrieved.

        :param FileName: Full file path to .pwb file to open. This will
            be passed to the SimAuto function OpenCase.
        :param early_bind: Whether (True) or not (False) to connect to
            SimAuto via early binding.
        :param UIVisible: Whether or not to display the PowerWorld UI.
        :param CreateIfNotFound: Set CreateIfNotFound = True if objects
            that are updated through the ChangeParameters functions
            should be created if they do not already exist in the case.
            Objects that already exist will be updated.
            Set CreateIfNotFound = False to not create new objects
            and only update existing ones.
        :param object_field_lookup: Listing of PowerWorld objects to
            initially look up available fields for. Objects not
            specified for lookup here will be looked up later as
            necessary.

        Note that
        `Microsoft recommends
        <https://docs.microsoft.com/en-us/office/troubleshoot/office-developer/binding-type-available-to-automation-clients>`__
        early binding in most cases.
        """
        # Initialize logger.
        self.log = logging.getLogger(self.__class__.__name__)
        # Useful reference for early vs. late binding:
        # https://docs.microsoft.com/en-us/office/troubleshoot/office-developer/binding-type-available-to-automation-clients
        #
        # Useful reference for early and late binding in pywin32:
        # https://youtu.be/xPtp8qFAHuA
        try:
            if early_bind:
                # Use early binding.
                self._pwcom = win32com.client.gencache.EnsureDispatch(
                    'pwrworld.SimulatorAuto')
            else:
                # Use late binding.
                self._pwcom = win32com.client.dynamic.Dispatch(
                    'pwrworld.SimulatorAuto')
        except Exception as e:
            m = ("Unable to launch SimAuto. ",
                 "Please confirm that your PowerWorld license includes "
                 "the SimAuto add-on, and that SimAuto has been "
                 "successfully installed.")
            self.log.exception(m)

            raise e

        # Initialize self.pwb_file_path. It will be set in the OpenCase
        # method.
        self.pwb_file_path = None
        # Set the CreateIfNotFound and UIVisible properties.
        self.set_simauto_property('CreateIfNotFound', CreateIfNotFound)
        self.set_simauto_property('UIVisible', UIVisible)
        # Open the case.
        self.OpenCase(FileName=FileName)

        # Look up and cache field listing and key fields for the given
        # object types in object_field_lookup.
        self._object_fields = dict()
        self._object_key_fields = dict()

        for obj in object_field_lookup:
            # Always use lower case.
            o = obj.lower()

            # Get the field listing. This will store the resulting
            # field list in self._object_fields[o].
            self.GetFieldList(o)

            # Get the key fields for this object. This will store the
            # results in self._object_key_fields[o]
            self.get_key_fields_for_object_type(ObjectType=o)

    ####################################################################
    # Helper Functions
    ####################################################################
    def change_and_confirm_params_multiple_element(self, ObjectType: str,
                                                   command_df: pd.DataFrame) \
            -> None:
        """Change parameters for multiple objects of the same type, and
        confirm that the change was respected by PowerWorld.

        :param ObjectType: The type of objects you are changing
            parameters for.
        :param command_df: Pandas DataFrame representing the objects
            which will have their parameters changed. The columns should
            be object field variable names, and MUST include the key
            fields for the given ObjectType (which you can get via the
            get_key_fields_for_object_type method). Columns which are
            not key fields indicate parameters to be changed, while the
            key fields are used internally by PowerWorld to look up
            objects. Each row of the DataFrame represents a single
            element.

        :raises CommandNotRespectedError: if PowerWorld does not
            actually change the parameters.
        :raises: PowerWorldError: if PowerWorld reports an error.

        :returns: None
        """
        # Start by cleaning up the DataFrame. This will avoid silly
        # issues later (e.g. comparing ' 1 ' and '1').
        cleaned_df = self._change_parameters_multiple_element_df(
                ObjectType=ObjectType, command_df=command_df)

        # Now, query for the given parameters.
        df = self.GetParametersMultipleElement(
            ObjectType=ObjectType, ParamList=cleaned_df.columns.tolist())

        # Check to see if the two DataFrames are equivalent.
        eq = self._df_equiv_subset_of_other(df1=cleaned_df, df2=df,
                                            ObjectType=ObjectType)

        # If DataFrames are not equivalent, raise a
        # CommandNotRespectedError.
        if not eq:
            m = ('After calling ChangeParametersMultipleElement, not all '
                 'parameters were actually changed within PowerWorld. Try '
                 'again with a different parameter (e.g. use GenVoltSet '
                 'instead of GenRegPUVolt).')
            raise CommandNotRespectedError(m)

        # All done.
        return None

    def change_parameters_multiple_element_df(
            self, ObjectType: str, command_df: pd.DataFrame) -> None:
        """Helper to call ChangeParametersMultipleElement, but uses a
        DataFrame to determine parameters and values. This method is
        lighter weight but perhaps "riskier" than the
        "change_and_confirm_params_multiple_element" method, as no
        effort is made to ensure PowerWorld respected the given command.

        :param ObjectType: The type of objects you are changing
            parameters for.
        :param command_df: Pandas DataFrame representing the objects
            which will have their parameters changed. The columns should
            be object field variable names, and MUST include the key
            fields for the given ObjectType (which you can get via the
            get_key_fields_for_object_type method). Columns which are
            not key fields indicate parameters to be changed, while the
            key fields are used internally by PowerWorld to look up
            objects. Each row of the DataFrame represents a single
            element.
        """
        # Simply call the helper function.
        self._change_parameters_multiple_element_df(
            ObjectType=ObjectType, command_df=command_df)

    def clean_df_or_series(self, obj: Union[pd.DataFrame, pd.Series],
                           ObjectType: str) -> Union[pd.DataFrame, pd.Series]:
        """Helper to cast data to the correct types, clean up strings,
        and sort DataFrame by BusNum (if applicable/present).

        :param obj: DataFrame or Series to clean up. It's assumed that
            the object came more or less directly from placing results
            from calling SimAuto into a DataFrame or Series. This means
            all data will be strings (even if they should be numeric)
            and data which should be strings often have unnecessary
            white space. If obj is a DataFrame (Series), the columns
            (index) must be existing fields for the given object type
            (i.e. are present in the 'internal_field_name' column of the
            corresponding DataFrame which comes from calling
            GetFieldList for the given object type).
        :param ObjectType: Object type the data in the DataFrame relates
            to. E.g. 'gen'

        :raises ValueError: if the DataFrame (Series) columns (index)
            are not valid fields for the given object type.

        :raises TypeError: if the input 'obj' is not a DataFrame or
            Series.
        """
        # Get the type of the obj.
        if isinstance(obj, pd.DataFrame):
            df_flag = True
            fields = obj.columns.to_numpy()
        elif isinstance(obj, pd.Series):
            df_flag = False
            fields = obj.index.to_numpy()
        else:
            raise TypeError('The given object is not a DataFrame or '
                            'Series!')

        # Determine which types are numeric.
        numeric = self.identify_numeric_fields(ObjectType=ObjectType,
                                               fields=fields)
        numeric_fields = fields[numeric]

        # Make the numeric fields, well, numeric.
        obj[numeric_fields] = obj[numeric_fields].apply(pd.to_numeric)

        # Now handle the non-numeric cols.
        nn_cols = fields[~numeric]

        # Start by ensuring the non-numeric columns are indeed strings.
        obj[nn_cols] = obj[nn_cols].astype(str)

        # Here we'll strip off the white space.
        if df_flag:
            # Need to use apply to strip strings from multiple columns.
            obj[nn_cols] = obj[nn_cols].apply(lambda x: x.str.strip())
        else:
            # A series is much simpler, and the .str.strip() method can
            # be used directly.
            obj[nn_cols] = obj[nn_cols].str.strip()

        # Sort by BusNum if present.
        if df_flag:
            try:
                obj.sort_values(by='BusNum', axis=0, inplace=True)
            except KeyError:
                # If there's no BusNum don't sort the DataFrame.
                pass
            else:
                # Re-index with simple monotonically increasing values.
                obj.index = np.arange(start=0, stop=obj.shape[0])

        return obj

    def create_filter(self, condition, object_type, filter_name,
                      filter_logic='AND', filter_pre='NO', enabled='YES'):
        """
        NOT IMPLEMENTED.

        Creates a filter in PowerWorld. The attempt is to reduce the
        clunkiness of creating a filter in the API, which entails
        creating an aux data file.
        """
        raise NotImplementedError(NIE_MSG)
        # aux_text = '''
        #     DATA (FILTER, [ObjectType,FilterName,FilterLogic,FilterPre,Enabled])
        #     {
        #     "{objecttype}" "{filtername}" "{filterlogic}" "{filterpre}" "{enabled]"
        #         <SUBDATA Condition>
        #             {condition}
        #         </SUBDATA>
        #     }'''.format(condition=condition, objecttype=object_type,
        #                 filtername=filter_name, filterlogic=filter_logic,
        #                 filterpre=filter_pre, enabled=enabled)
        # return self._call_simauto('LoadAux', aux_text)

    def exit(self):
        """Clean up for the PowerWorld COM object"""
        self.CloseCase()
        del self._pwcom
        self._pwcom = None
        return None

    def get_key_fields_for_object_type(self, ObjectType: str) -> pd.DataFrame:
        """Helper function to get all key fields for an object type.

        :param ObjectType: The type of the object to get key fields for.

        :returns: DataFrame with the following columns:
            'internal_field_name', 'field_data_type', 'description', and
            'display_name'. The DataFrame will be indexed based on the key
            field returned by the Simulator, but modified to be 0-based.

        This method uses the GetFieldList function, documented
        `here
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/GetFieldList_Function.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____14>`__.

        It's also worth looking at the key fields documentation
        `here
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/Key_Fields.htm>`__.
        """
        # Cast to lower case.
        obj_type = ObjectType.lower()

        # See if we've already looked up the key fields for this object.
        # If we have, just return the cached results.
        try:
            key_field_df = self._object_key_fields[obj_type]
        except KeyError:
            # We haven't looked up key fields for this object yet.
            pass
        else:
            # There's not work to do here. Return the DataFrame.
            return key_field_df

        # Get the listing of fields for this object type.
        field_list = self.GetFieldList(ObjectType=obj_type, copy=False)

        # Here's what I've gathered:
        # Key fields will be of the format *<number><letter>*
        #   where the <letter> part is optional. It seems the
        #   letter is only listed for the last key field.
        # Required fields are indicated with '**'.
        # There are also fields of the form *<letter>* and these
        #   seem to be composite fields? E.g. 'BusName_NomVolt'.

        # Extract key fields.
        key_field_mask = \
            field_list['key_field'].str.match(r'\*[0-9]+[A-Z]*\*').to_numpy()
        # Making a copy isn't egregious here because there are a
        # limited number of key fields, so this will be a small frame.
        key_field_df = field_list.loc[key_field_mask].copy()

        # Replace '*' with the empty string.
        key_field_df['key_field'] = \
            key_field_df['key_field'].str.replace(r'\*', '')

        # Remove letters.
        key_field_df['key_field'] = \
            key_field_df['key_field'].str.replace('[A-Z]*', '')

        # Get numeric, 0-based index.
        key_field_df['key_field_index'] = \
            pd.to_numeric(key_field_df['key_field']) - 1

        # Drop the key_field column (we only wanted to convert to an
        # index).
        key_field_df.drop('key_field', axis=1, inplace=True)

        # Use the key_field_index for the DataFrame index.
        key_field_df.set_index(keys='key_field_index', drop=True,
                               verify_integrity=True, inplace=True)

        # Sort the index.
        key_field_df.sort_index(axis=0, inplace=True)

        # Ensure the index is as expected (0, 1, 2, 3, etc.)
        assert np.array_equal(
            key_field_df.index.to_numpy(),
            np.arange(0, key_field_df.index.to_numpy()[-1] + 1))

        # Track for later.
        self._object_key_fields[obj_type] = key_field_df

        return key_field_df

    def get_key_field_list(self, ObjectType: str) -> List[str]:
        """Convenience function to get a list of key fields for a given
        object type.

        :param ObjectType: PowerWorld object type for which you would
            like a list of key fields. E.g. 'gen'.

        :returns: List of key fields for the given object type. E.g.
            ['BusNum', 'GenID']
        """
        # Lower case only.
        obj_type = ObjectType.lower()

        # Attempt to get the key field DataFrame from our cached
        # dictionary.
        try:
            key_field_df = self._object_key_fields[obj_type]
        except KeyError:
            # DataFrame isn't cached. Get it.
            key_field_df = self.get_key_fields_for_object_type(obj_type)

        # Return a listing of the internal field name.
        return key_field_df['internal_field_name'].tolist()

    def get_power_flow_results(self, ObjectType: str) -> \
            Union[None, pd.DataFrame]:
        """Get the power flow results from SimAuto server.

        :param ObjectType: Object type to get results for. Valid types
            are the keys in the POWER_FLOW_FIELDS class attribute (case
            insensitive).

        :returns: Pandas DataFrame with the corresponding results, or
            None if the given ObjectType is not present in the model.

        :raises ValueError: if given ObjectType is invalid.
        """
        object_type = ObjectType.lower()
        # Get the listing of fields for this object type.
        try:
            field_list = self.POWER_FLOW_FIELDS[object_type]
        except KeyError:
            raise ValueError('Unsupported ObjectType for power flow results, '
                             '{}.'.format(ObjectType))

        return self.GetParametersMultipleElement(ObjectType=object_type,
                                                 ParamList=field_list)

    def get_three_phase_bolted_fault_current(self, bus_num):
        """
        NOT IMPLEMENTED.

        Calculates the three phase fault; this can be done even with
        cases which only contain positive sequence impedances"""
        raise NotImplementedError(NIE_MSG)
        # script_cmd = f'Fault([BUS {bus_num}], 3PB);\n'
        # result = self.RunScriptCommand(script_cmd)
        # field_list = ['BusNum', 'FaultCurMag']
        # return self.GetParametersSingleElement('BUS', field_list,
        #                                        [bus_num, 0])

    def identify_numeric_fields(self, ObjectType: str,
                                fields: Union[List, np.ndarray]) -> \
            np.ndarray:
        """Helper which looks up PowerWorld internal field names to
        determine if they're numeric (True) or not (False).

        :param ObjectType: Type of object for which we're identifying
            numeric fields. E.g. "Branch" or "gen"
        :param fields: List of PowerWorld internal fields names for
            which we're identifying if they are or aren't numeric.
            E.g. ['BusNum', 'BusNum:1', 'LineCircuit', 'LineStatus']

        :returns: Numpy boolean array indicating which of the given
            fields are numeric. Going along with the example given for
            "fields": np.array([True, True, False, False])
        """
        # Start by getting the field list for this ObjectType. Note
        # that in most cases this will be cached and thus be quite
        # fast. If it isn't cached now, it will be after calling this.
        field_list = self.GetFieldList(ObjectType=ObjectType, copy=False)

        # Rely on the fact that the field_list is already sorted by
        # internal_field_name to get indices related to the given
        # internal field names.
        idx = field_list['internal_field_name'].to_numpy().searchsorted(fields)

        # Ensure the columns are actually in the field_list. This is
        # necessary because search sorted gives the index of where the
        # given values would go, and doesn't guarantee the values are
        # actually present. However, we want to use searchsorted for its
        # speed and leverage the fact that our field_list DataFrame is
        # already sorted.
        try:
            # ifn for "internal_field_name."
            ifn = field_list['internal_field_name'].to_numpy()[idx]

            # Ensure given fields are present in the field list.
            if set(ifn) != set(fields):
                raise ValueError('The given object has fields which do not'
                                 ' match a PowerWorld internal field name!')
        except IndexError:
            # An index error also indicates failure.
            raise ValueError('The given object has fields which do not'
                             ' match a PowerWorld internal field name!')

        # Now extract the corresponding data types.
        data_types = field_list['field_data_type'].to_numpy()[idx]

        # Determine which types are numeric and return.
        return np.isin(data_types, NUMERIC_TYPES)

    def set_simauto_property(self, property_name: str,
                             property_value: Union[str, bool]):
        """Set a SimAuto property, e.g. CreateIfNotFound. The currently
        supported properties are listed in the SAW.SIMAUTO_PROPERTIES
        class constant.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server_Properties.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Properties%7C_____1>`__

        :param property_name: Name of the property to set, e.g.
            UIVisible.
        :param property_value: Value to set the property to, e.g. False.
        """
        # Ensure the given property name is valid.
        if property_name not in self.SIMAUTO_PROPERTIES:
            raise ValueError(('The given property_name, {}, is not currently '
                              'supported. Valid properties are: {}')
                             .format(property_name,
                                     list(self.SIMAUTO_PROPERTIES.keys())))

        # Ensure the given property value has a valid type.
        # noinspection PyTypeHints
        if not isinstance(property_value,
                          self.SIMAUTO_PROPERTIES[property_name]):
            m = ('The given property_value, {}, is invalid. It must be '
                 'of type {}.').format(property_value,
                                       self.SIMAUTO_PROPERTIES[property_name])
            raise ValueError(m)

        # If we're setting CurrentDir, ensure the path is valid.
        # It seems PowerWorld does not check this.
        if property_name == 'CurrentDir':
            if not os.path.isdir(property_value):
                raise ValueError('The given path for CurrentDir, {}, is '
                                 'not a valid path!'.format(property_value))

        # Set the property.
        # noinspection PyUnresolvedReferences
        try:
            setattr(self._pwcom, property_name, property_value)
        except pywintypes.com_error:
            # Well, this is unexpected.
            raise ValueError('The given property_name, property_value '
                             'pair ({}, {}), resulted in an error. Please '
                             'help us out by filing an issue on GitHub.')

    ####################################################################
    # SimAuto Server Functions
    ####################################################################

    def ChangeParameters(self, ObjType, ParamList, ValueArray):
        """
        NOT IMPLEMENTED.

        ChangeParameters is used to change single or multiple parameters
        of a single object. ParamList is a variant array storing strings
        that are Simulator object field variables, and must contain the
        key fields for the objecttype. Create variant arrays (one for
        each element being changed) with values corresponding to the
        fields in ParamList.
        """
        raise NotImplementedError(NIE_MSG)
        # output = self._call_simauto('ChangeParameters', ObjType, ParamList,
        #                             ValueArray)
        # return output

    def ChangeParametersSingleElement(self, ObjectType: str, ParamList: list,
                                      Values: list) -> None:
        """Set a list of parameters for a single object.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ChangeParametersSingleElement_Function.htm>`__

        :param ObjectType: The type of object you are changing
            parameters for.
        :param ParamList: List of object field variable names. Note this
            MUST include the key fields for the given ObjectType
            (which you can get via the get_key_fields_for_object_type
            method).
        :param Values: List of values corresponding to the parameters in
            the ParamList.
        """
        return self._call_simauto('ChangeParametersSingleElement',
                                  ObjectType,
                                  convert_list_to_variant(ParamList),
                                  convert_list_to_variant(Values))

    def ChangeParametersMultipleElement(self, ObjectType: str, ParamList: list,
                                        ValueList: list) -> None:
        """Set parameters for multiple objects of the same type.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ChangeParametersMultipleElement_Function.htm>`__

        :param ObjectType: The type of object you are changing
            parameters for.
        :param ParamList: Listing of object field variable names. Note
            this MUST include the key fields for the given ObjectType
            (which you can get via the get_key_fields_for_object_type
            method).
        :param ValueList: List of lists corresponding to the ParamList.
            Should have length n, where n is the number of elements you
            with to change parameters for. Each sub-list should have
            the same length as ParamList, and the items in the sub-list
            should correspond 1:1 with ParamList.
        :returns: Result from calling SimAuto, which should always
            simply be None.

        :raises PowerWorldError: if PowerWorld reports an error.
        """
        # Call SimAuto and return the result (should just be None)
        return self._call_simauto('ChangeParametersMultipleElement',
                                  ObjectType,
                                  convert_list_to_variant(ParamList),
                                  convert_nested_list_to_variant(ValueList))

    def ChangeParametersMultipleElementFlatInput(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def CloseCase(self):
        """Closes case without saving changes.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/CloseCase_Function.htm>`__
        """
        return self._call_simauto('CloseCase')

    def GetCaseHeader(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def GetFieldList(self, ObjectType: str, copy=False) -> pd.DataFrame:
        """Get all fields associated with a given ObjectType.

        :param ObjectType: The type of object for which the fields are
            requested.
        :param copy: Whether or not to return a copy of the DataFrame.
            You may want a copy if you plan to make any modifications.

        :returns: Pandas DataFrame with columns 'key_field,'
            'internal_field_name,' 'field_data_type,' 'description,'
            and 'display_name.'

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/GetFieldList_Function.htm>`__
        """
        # Get the ObjectType in lower case.
        object_type = ObjectType.lower()

        # Either look up stored DataFrame, or call SimAuto.
        try:
            output = self._object_fields[object_type]
        except KeyError:
            # We haven't looked up fields for this object yet.
            # Call SimAuto, and place results into a DataFrame.
            result = self._call_simauto('GetFieldList', ObjectType)
            output = pd.DataFrame(np.array(result),
                                  columns=self.FIELD_LIST_COLUMNS)

            # While it appears PowerWorld gives us the list sorted by
            # internal_field_name, let's make sure it's always sorted.
            output.sort_values(by=['internal_field_name'], inplace=True)

            # Store this for later.
            self._object_fields[object_type] = output

        # Either return a copy or not.
        if copy:
            return output.copy(deep=True)
        else:
            return output

    def GetParametersSingleElement(self, ObjectType: str,
                                   ParamList: list, Values: list) -> pd.Series:
        """Request values of specified fields for a particular object.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetParametersSingleElement_Function.htm>`__

        :param ObjectType: The type of object you're retrieving
            parameters for.
        :param ParamList: List of strings indicating parameters to
            retrieve. Note the key fields MUST be present. One can
            obtain key fields for an object type via the
            get_key_fields_for_object_type method.
        :param Values: List of values corresponding 1:1 to parameters in
            the ParamList. Values must be included for the key fields,
            and the remaining values should be set to 0.

        :returns: Pandas Series indexed by the given ParamList. This
            Series will be cleaned by clean_df_or_series, so data will
            be of the appropriate type and strings are cleaned up.

        :raises PowerWorldError: if the object cannot be found.
        :raises ValueError: if any given element in ParamList is not
            valid for the given ObjectType.
        :raises AssertionError: if the given ParamList and Values do
            not have the same length.
        """
        # Ensure list lengths match.
        assert len(ParamList) == len(Values), \
            'The given ParamList and Values must have the same length.'

        # Call PowerWorld.
        output = self._call_simauto('GetParametersSingleElement', ObjectType,
                                    convert_list_to_variant(ParamList),
                                    convert_list_to_variant(Values))

        # Convert to Series.
        s = pd.Series(output, index=ParamList)

        # Clean the Series and return.
        return self.clean_df_or_series(obj=s, ObjectType=ObjectType)

    def GetParametersMultipleElement(self, ObjectType: str, ParamList: list,
                                     FilterName: str = '') -> \
            Union[pd.DataFrame, None]:
        """Request values of specified fields for a set of objects in
        the load flow case.

        `PowerWorld Documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/GetParametersMultipleElement_Function.htm>`__

        :param ObjectType: Type of object to get parameters for.
        :param ParamList: List of variables to obtain for the given
            object type. E.g. ['BusNum', 'GenID', 'GenMW']. One
            can use the method GetFieldList to get a listing of all
            available fields. Additionally, you'll likely want to always
            return the key fields associated with the objects. These
            key fields can be obtained via the
            get_key_fields_for_object_type method.
        :param FilterName: Name of an advanced filter defined in the
            load flow case.

        :returns: Pandas DataFrame with columns matching the given
            ParamList. If the provided ObjectType is not present in the
            case, None will be returned.

        :raises PowerWorldError: if PowerWorld reports an error.
        :raises ValueError: if any parameters given in the ParamList
            are not valid for the given object type.

        TODO: Should we cast None to NaN to be consistent with how
            Pandas/Numpy handle bad/missing data?
        """
        output = self._call_simauto('GetParametersMultipleElement',
                                    ObjectType,
                                    convert_list_to_variant(ParamList),
                                    FilterName)
        if output is None:
            # Given object isn't present.
            return output

        # Create DataFrame.
        df = pd.DataFrame(np.array(output).transpose(),
                          columns=ParamList)

        # Clean DataFrame and return it.
        return self.clean_df_or_series(obj=df, ObjectType=ObjectType)

    def GetParametersMultipleElementFlatOutput(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def GetParameters(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def GetSpecificFieldList(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def GetSpecificFieldMaxNum(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def ListOfDevices(self, ObjType: str, FilterName='') -> \
            Union[None, pd.DataFrame]:
        """Request a list of objects and their key fields. This function
        is general, and you may be better off running more specific
        methods like "get_gens"

        :param ObjType: The type of object for which you are acquiring
            the list of devices. E.g. "Shunt," "Gen," "Bus," "Branch,"
            etc.
        :param FilterName: Name of an advanced filter defined in the
            load flow case open in the automation server. Use the
            empty string (default) if no filter is desired. If the
            given filter cannot be found, the server will default to
            returning all objects in the case of type ObjectType.

        :returns: None if there are no objects of the given type in the
            model. Otherwise, a DataFrame of key fields will be
            returned. There will be a row for each object of the given
            type, and columns for each key field. If the "BusNum"
            key field is present, the data will be sorted by BusNum.
        """
        # Start by getting the key fields associated with this object.
        kf = self.get_key_fields_for_object_type(ObjType)

        # Now, query for the list of devices.
        output = self._call_simauto('ListOfDevices', ObjType, FilterName)

        # If all data in the 2nd dimension comes back None, there
        # are no objects of this type and we should return None.
        all_none = True
        for i in output:
            if i is not None:
                all_none = False
                break

        if all_none:
            # TODO: May be worth adding logging here.
            return None

        # If we're here, we have this object type in the model.
        # Create a DataFrame.
        df = pd.DataFrame(output).transpose()
        # The return from get_key_fields_for_object_type is designed to
        # match up 1:1 with values here. Set columns.
        df.columns = kf['internal_field_name'].to_numpy()

        # Ensure the DataFrame has the correct types, is sorted by
        # BusNum, and has leading/trailing white space stripped.
        df = self.clean_df_or_series(obj=df, ObjectType=ObjType)

        # All done.
        return df

    def ListOfDevicesAsVariantStrings(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def ListOfDevicesFlatOutput(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def LoadState(self) -> None:
        """LoadState is used to load the system state previously saved
        with the SaveState function. Note that LoadState will not
        properly function if the system topology has changed due to the
        addition or removal of the system elements.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/LoadState_Function.htm>`__
        """
        return self._call_simauto('LoadState')

    def OpenCase(self, FileName: Union[str, None] = None) -> None:
        """Load PowerWorld case into the automation server.

        :param FileName: Full path to the case file to be loaded. If
            None, this method will attempt to use the last FileName
            used to open a case.

        :raises TypeError: if FileName is None, and OpenCase has never
            been called before.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/OpenCase_Function.htm>`__
        """
        # If not given a file name, ensure the pwb_file_path is valid.
        if FileName is None:
            if self.pwb_file_path is None:
                raise TypeError('When OpenCase is called for the first '
                                'time, a FileName is required.')
        else:
            # Set pwb_file_path according to the given FileName.
            self.pwb_file_path = convert_to_posix_path(FileName)

        # Open the case. PowerWorld should return None.
        return self._call_simauto('OpenCase', self.pwb_file_path)

    def OpenCaseType(self):
        """NOT IMPLEMENTED."""
        raise NotImplementedError(NIE_MSG)

    def ProcessAuxFile(self, FileName):
        """
        Load a PowerWorld Auxiliary file into SimAuto. This allows
        you to create a text file (conforming to the PowerWorld
        Auxiliary file format) that can list a set of data changes and
        other information for making batch changes in Simulator.

        :param FileName: Name of auxiliary file to load. Should be a
            full path.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/ProcessAuxFile_Function.htm>`__
        """
        return self._call_simauto('ProcessAuxFile', FileName)

    def RunScriptCommand(self, Statements):
        """Execute a list of script statements. The script actions are
        those included in the script sections of auxiliary files.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/RunScriptCommand_Function.htm>`__

        `Auxiliary File Format
        <https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`__
        """
        output = self._call_simauto('RunScriptCommand', Statements)
        return output

    def SaveCase(self, FileName=None, FileType='PWB', Overwrite=True):
        """Save the current case to file.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/SaveCase_Function.htm>`__

        :param FileName: The name of the file you wish to save as,
            including file path. If None, the original path which was
            used to open the case (passed to this class's initializer)
            will be used.
        :param FileType: String indicating the format of the case file
            to write out. Here's what PowerWorld currently supports:
            * "PTI23": "PTI33" specific PTI version (raw).
            * "GE14": "GE21" GE PSLF version (epc).
            * "IEEE": IEEE common format (cf).
            * "UCTE": UCTE Data Exchange (uct).
            * "AUX": PowerWorld Auxiliary format (aux).
            * "AUXSECOND": PowerWorld Auxiliary format (aux) using
            secondary key fields.
            * "AUXLABEL": PowerWorld Auxiliary format (aux) using
            labels as key field identifiers.
            * "AUXNETWORK": PowerWorld Auxiliary format (aux) saving
            only network data.
            * "PWB5" through "PWB20": specific PowerWorld Binary
            version (pwb).
            * "PWB":  PowerWorld Binary (most recent) (pwb).
        :param Overwrite: Whether (True) or not (False) to overwrite the
            file if it already exists. If False and the specified file
            already exists, an exception will be raised.
        """
        if FileName is not None:
            f = convert_to_windows_path(FileName)
        else:
            if self.pwb_file_path is None:
                raise TypeError('SaveCase was called without a FileName, but '
                                'it would appear OpenCase has not yet been '
                                'called.')
            f = convert_to_windows_path(self.pwb_file_path)

        return self._call_simauto('SaveCase', f, FileType, Overwrite)

    def SaveState(self) -> None:
        """SaveState is used to save the current state of the power
        system. This can be useful if you are interested in comparing
        various cases, much as the "Difference Flows" feature works in
        the Simulator application.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/SaveState_Function.htm>`__
        """
        return self._call_simauto('SaveState')

    def SendToExcel(self, ObjectType: str, FilterName: str, FieldList):
        """NOT IMPLEMENTED.

        Send data from SimAuto to an Excel spreadsheet.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/SendToExcel_Function.htm>`__
        """
        raise NotImplementedError(NIE_MSG)
        # return self._call_simauto('SendToExcel', ObjectType, FilterName,
        #                           FieldList)

    def TSGetContingencyResults(self, CtgName, ObjFieldList,
                                StartTime=None, StopTime=None):
        """NOT IMPLEMENTED.

        Read transient stability results directly into the SimAuto COM
        object and be further used.
        !!!!! This function should ONLY be used after the simulation is run
        (for example, use this after running script commands tsSolveAll
        or tsSolve).
        ObjFieldList = ['"Plot ''Bus_4_Frequency''"'] or
        ObjFieldList = ['"Bus 4 | frequency"']
        """
        raise NotImplementedError(NIE_MSG)
        # output = self._call_simauto('TSGetContingencyResults', CtgName,
        #                             ObjFieldList, StartTime, StopTime)
        # return output

    def WriteAuxFile(self, FileName, FilterName, ObjectType, FieldList,
                     ToAppend=True, EString=None):
        """NOT IMPLEMENTED.

        The WriteAuxFile function can be used to write data from the
        case in the Simulator Automation Server to a PowerWorld
        Auxiliary file. The name of an advanced filter which was
        PREVIOUSLY DEFINED in the case before being loaded in the
        Simulator Automation Server. If no filter is desired, then
        simply pass an empty string. If a filter name is passed but the
        filter cannot be found in the loaded case, no filter is used.

        `PowerWorld documentation
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/WriteAuxFile_Function.htm>`__
        """
        raise NotImplementedError(NIE_MSG)
        # aux_file = convert_to_posix_path(FileName)
        # return self._call_simauto('WriteAuxFile', aux_file,
        #                           FilterName, ObjectType, EString, ToAppend,
        #                           FieldList)

    ####################################################################
    # PowerWorld ScriptCommand helper functions
    ####################################################################

    def SolvePowerFlow(self, SolMethod: str = 'RECTNEWT') -> None:
        """Run the SolvePowerFlow command.

        :param SolMethod: Solution method to be used for the Power Flow
            calculation. Case insensitive. Valid options are:
            'RECTNEWT' - Rectangular Newton-Raphson
            'POLARNEWTON' - Polar Newton-Raphson
            'GAUSSSEIDEL' - Gauss-Seidel
            'FASTDEC' - Fast Decoupled
            'ROBUST' - Attempt robust solution process
            'DC' - DC power flow

        See
        `Auxiliary File Format.pdf
        <https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`__
        for more details.
        """
        script_command = "SolvePowerFlow(%s)" % SolMethod.upper()
        return self.RunScriptCommand(script_command)

    ####################################################################
    # PowerWorld SimAuto Properties
    ####################################################################
    @property
    def CurrentDir(self):
        output = self._pwcom.CurrentDir
        return output

    @property
    def ProcessID(self):
        """Retrieve the process ID of the currently running
        SimulatorAuto process"""
        output = self._pwcom.ProcessID
        return output

    @property
    def RequestBuildDate(self):
        """Retrieve the build date of the PowerWorld Simulator
        executable currently running with the SimulatorAuto process
        """
        return self._pwcom.RequestBuildDate

    @property
    def UIVisible(self):
        output = self._pwcom.UIVisible
        return output

    ####################################################################
    # Private Methods
    ####################################################################

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()
        return True

    def _call_simauto(self, func: str, *args):
        """Helper function for calling the SimAuto server.

        :param func: Name of PowerWorld SimAuto function to call.

        :param args: Remaining arguments to this function will be
            passed directly to func.

        :returns: Result from PowerWorld. This will vary from function
            to function. If PowerWorld returns ('',), this method
            returns None.

        :raises PowerWorldError: If PowerWorld indicates an exception
            occurred.

        :raises AttributeError: If the given func is invalid.

        :raises COMError: If attempting to call the SimAuto function
            results in an error.

        The listing of valid functions can be found `here
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server_Functions.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____3>`__.
        """
        # Get a reference to the SimAuto function from the COM object.
        try:
            f = getattr(self._pwcom, func)
        except AttributeError:
            raise AttributeError('The given function, {}, is not a valid '
                                 'SimAuto function.'.format(func)) from None

        # Call the function.
        try:
            output = f(*args)
        except Exception:
            m = ('An error occurred when trying to call {} with '
                 '{}').format(func, args)
            self.log.exception(m)
            raise COMError(m)

        # handle errors
        if output == ('',):
            # If we just get a tuple with the empty string in it,
            # there's nothing to return.
            return None
        if output is None or output[0] == '':
            pass
        elif 'No data' in output[0]:
            pass
        else:
            raise PowerWorldError(output[0])

        # After errors have been handled, return the data (which is in
        # position 1 of the tuple).
        return output[1]

    def _change_parameters_multiple_element_df(
            self, ObjectType: str, command_df: pd.DataFrame) -> pd.DataFrame:
        """Private helper for changing parameters for multiple elements
        with a command DataFrame as input. See docstring for public
        method "change_parameters_multiple_element_df" for more details.

        :returns: "Cleaned" version of command_df (passed through
            clean_df_or_series).
        """
        # Start by cleaning up the DataFrame. This will avoid silly
        # issues later (e.g. comparing ' 1 ' and '1').
        cleaned_df = self.clean_df_or_series(obj=command_df,
                                             ObjectType=ObjectType)

        # Convert columns and data to lists and call PowerWorld.
        # noinspection PyTypeChecker
        self.ChangeParametersMultipleElement(
            ObjectType=ObjectType, ParamList=cleaned_df.columns.tolist(),
            ValueList=cleaned_df.to_numpy().tolist())

        return cleaned_df

    def _df_equiv_subset_of_other(self, df1: pd.DataFrame, df2: pd.DataFrame,
                                  ObjectType: str) -> bool:
        """Helper to indicate if one DataFrame is an equivalent subset
        of another (True) or not (False) for a given PowerWorld object
        type. Here, we're defining "equivalent subset" as all of df1
        being present in df2 (e.g. columns, index, values, etc.), and
        all data are "equivalent." Numeric data will be compared with
        Numpy's "allclose" function, and string data will be compared
        with Numpy's "array_equal" function. Types will be cast based on
        the given parameters (columns in the DataFrame).

        :param df1: First DataFrame. Could possibly originate from a
            method such as "GetParametersMultipleElement." Column names
            should be PowerWorld variable names, and the key fields
            should be included.
        :param df2: Second DataFrame. See description of df1.
        :param ObjectType: PowerWorld object type for which the
            DataFrames represent data for. E.g. 'gen' or 'load'.

        :returns: True if DataFrames are "equivalent," False otherwise.
        """
        # Get the key fields for this ObjectType.
        kf = self.get_key_fields_for_object_type(ObjectType=ObjectType)

        # Merge the DataFrames on the key fields.
        merged = pd.merge(left=df1, right=df2, how='inner',
                          on=kf['internal_field_name'].tolist(),
                          suffixes=('_in', '_out'), copy=False)

        # Time to check if our input and output values match. Note this
        # relies on our use of "_in" and "_out" suffixes above.
        cols_in = merged.columns[merged.columns.str.endswith('_in')]
        cols_out = merged.columns[merged.columns.str.endswith('_out')]

        # We'll be comparing string and numeric columns separately. The
        # numeric columns must use np.allclose to avoid rounding error,
        # while the strings should use array_equal as the strings should
        # exactly match.
        cols = cols_in.str.replace('_in', '')
        numeric_cols = self.identify_numeric_fields(ObjectType=ObjectType,
                                                    fields=cols)
        str_cols = ~numeric_cols

        # If all numeric data are "close" and all string data match
        # exactly, this will return True. Otherwise, False will be
        # returned.
        return (
                np.allclose(
                    merged[cols_in[numeric_cols]].to_numpy(),
                    merged[cols_out[numeric_cols]].to_numpy()
                )
                and
                np.array_equal(
                    merged[cols_in[str_cols]].to_numpy(),
                    merged[cols_out[str_cols]].to_numpy()
                )
        )


def convert_to_posix_path(p):
    """Given a path, p, convert it to a Posix path."""
    return Path(p).as_posix()


def convert_to_windows_path(p):
    """Given a path, p, convert it to a Windows path."""
    return str(PureWindowsPath(p))


def convert_list_to_variant(list_in: list) -> VARIANT:
    """Given a list, convert to a variant array.

    :param list_in: Simple one-dimensional Python list, e.g. [1, 'a', 7]
    """
    # noinspection PyUnresolvedReferences
    return VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, list_in)


def convert_nested_list_to_variant(list_in: list) -> List[VARIANT]:
    """Given a list of lists, convert to a variant array.

    :param list_in: List of lists, e.g. [[1, '1'], [1, '2'], [2, '1']]
    """
    return [convert_list_to_variant(sub_array) for sub_array in list_in]


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class PowerWorldError(Error):
    """Raised when PowerWorld reports an error following a SimAuto call.
    """
    pass


class COMError(Error):
    """Raised when attempting to call a SimAuto function results in an
    error.
    """
    pass


class CommandNotRespectedError(Error):
    """Raised if a command sent into PowerWorld is not respected, but
    PowerWorld itself does not raise an error. This exception should
    be used with helpers that double-check commands.
    """
    pass
