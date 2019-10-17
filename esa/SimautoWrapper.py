import pandas as pd
import numpy as np
import os
import win32com
from win32com.client import VARIANT
import pythoncom
import datetime
from .exceptions import GeneralException
import re
from typing import Union
from pathlib import Path

# Listing of PowerWorld data types. I guess 'real' means float?
DATA_TYPES = ['Integer', 'Real', 'String']
# Hard-code based on indices.
NUMERIC_TYPES = DATA_TYPES[0:2]
NON_NUMERIC_TYPES = DATA_TYPES[-1]


class sa(object):
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

    def __init__(self, pwb_file_path=None, earlybind=False, visible=False):
        try:
            if earlybind:
                self.__pwcom__ = win32com.client.gencache.EnsureDispatch(
                    'pwrworld.SimulatorAuto')
            else:
                self.__pwcom__ = win32com.client.dynamic.Dispatch(
                    'pwrworld.SimulatorAuto')
        except Exception as e:
            print(str(e))
            print("Unable to launch SimAuto. ",
                  "Please confirm that your PowerWorld license includes "
                  "the SimAuto add-on, and that SimAuto has been "
                  "successfully installed.")
        # print(self.__ctime__(), "SimAuto launched")
        file_path = Path(pwb_file_path)
        self.pwb_file_path = file_path.as_posix()
        self.aux_file_path = None
        self.output = ''
        self.error = False
        self.error_message = ''
        self.__pwcom__.UIVisible = visible
        if self.OpenCase():
            print(self.__ctime__(), "Case loaded")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()
        return True

    @staticmethod
    def __ctime__():
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def __setfilenames__(self):
        self.file_folder = os.path.split(self.pwb_file_path)[0]
        self.file_name = \
            os.path.splitext(os.path.split(self.pwb_file_path)[1])[0]
        # some operations require an aux file
        self.aux_file_path = self.file_folder + '/' + self.file_name + '.aux'
        self.save_file_path = os.path.splitext(
            os.path.split(self.pwb_file_path)[1])[0]

    def _call_simauto(self, func: str, *args):
        """Helper function for calling the SimAuto server.

        :param func: Name of PowerWorld SimAuto function to call.

        :param args: Remaining arguments to this function will be
            passed directly to func.

        :returns: Result from PowerWorld. This will vary from function
            to function. If PowerWorld returns ('',), this method
            returns None.

        The listing of valid functions can be found `here
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server_Functions.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____3>`_.
        """
        # Get a reference to the SimAuto function from the COM object.
        try:
            f = getattr(self.__pwcom__, func)
        except AttributeError:
            raise AttributeError('The given function, {}, is not a valid '
                                 'SimAuto function.'.format(func)) from None

        # Call the function.
        output = f(*args)

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
            raise GeneralException(output[0])

        # After errors have been handled, return the data (which is in
        # position 1 of the tuple).
        return output[1]

    # noinspection PyPep8Naming
    def OpenCase(self):
        """Opens case defined by the full file path; if this is
        undefined, opens by previous file path"""
        return self._call_simauto('OpenCase', self.pwb_file_path)

    # noinspection PyPep8Naming
    def SaveCase(self):
        """Saves case with changes to existing file name and path."""
        return self._call_simauto('SaveCase', self.pwb_file_path, 'PWB', True)

    def save_case_as(self, pwb_file_path=None):
        """If file name and path are specified, saves case as a new
        file. Overwrites any existing file with the same name and path.
        """
        if pwb_file_path is not None:
            file_path = Path(pwb_file_path)
            self.pwb_file_path = file_path.as_posix()
        return self.SaveCase()

    # noinspection PyPep8Naming
    def save_case_as_aux_file(self, file_name, FilterName='', ObjectType=None,
                              ToAppend=True, FieldList='all'):
        """If file name and path are specified, saves case as a new aux
        file. Overwrites any existing file with the same name and
        path.
        """
        file_path = Path(file_name)
        self.aux_file_path = file_path.as_posix()
        return self._call_simauto('WriteAuxFile', self.aux_file_path,
                                  FilterName, ObjectType, ToAppend, FieldList)

    # noinspection PyPep8Naming
    def CloseCase(self):
        """Closes case without saving changes."""
        return self._call_simauto('CloseCase')

    # noinspection PyPep8Naming
    def get_object_type_key_fields(self, ObjType: str) -> pd.DataFrame:
        """Helper function to get all key fields for an object type.

        :param ObjType: The type of the object to get key fields for.

        :returns: DataFrame with the following columns:
            'internal_field_name', 'field_type', 'description', and
            'alt_name'. The DataFrame will be indexed based on the key
            field returned by the Simulator, but modified to be 0-based.

        This method uses the GetFieldList function, documented
        `here
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/GetFieldList_Function.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____14>`_.

        It's also worth looking at the key fields documentation
        `here
        <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/Key_Fields.htm>`_.
        """
        field_list = self._call_simauto('GetFieldList', ObjType)

        # Initialize list of lists to hold our data.
        data = []

        # Loop over the returned list.
        for t in field_list:
            # Here's what I've gathered:
            # Key fields will be of the format *<number><letter>*
            #   where the <letter> part is optional. It seems the
            #   letter is only be listed for the last key field.
            # Required fields are indicated with '**'.
            # There are also fields of the form *<letter>* and these
            #   seem to be composite fields? E.g. 'BusName_NomVolt'.

            # Use a regular expression to test for key fields.
            if re.match(r'\*[0-9]+[A-Z]*\*', t[0]):
                # Convert the key field from a 1-based weird index
                # thing to a standard 0-based index.
                i = int(re.sub('[A-Z]*', '', re.sub(r'\*', '', t[0]))) - 1

                # Put the index and the rest of the parameters in
                # the list.
                data.append((i, *t[1:]))

        # Put the data into a DataFrame.
        df = pd.DataFrame(data,
                          columns=['key_field_index',
                                   'internal_field_name',
                                   'field_type', 'description',
                                   'alt_name'])

        # Use the key_field_index for the DataFrame index.
        df.set_index(keys='key_field_index', drop=True,
                     verify_integrity=True, inplace=True)

        # Sort the index.
        df.sort_index(axis=0, inplace=True)

        # Ensure the index is as expected (0, 1, 2, 3, etc.)
        assert np.array_equal(df.index.values,
                              np.arange(0, df.index.values[-1] + 1))

        return df

    # noinspection PyPep8Naming
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
            returning all objects in the case of type ObjType.

        :returns: None if there are no objects of the given type in the
            model. Otherwise, a DataFrame of key fields will be
            returned. There will be a row for each object of the given
            type, and columns for each key field. If the "BusNum"
            key field is present, the data will be sorted by BusNum.
        """
        # Start by getting the key fields associated with this object.
        kf = self.get_object_type_key_fields(ObjType)

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
        # The return from get_object_type_key_fields is designed to
        # match up 1:1 with values here. Set columns.
        df.columns = kf['internal_field_name'].values

        # Cast columns to numeric as appropriate. Strip leading/
        # trailing whitespace from string columns.
        for row in kf.itertuples():
            if row.field_type in NUMERIC_TYPES:
                # Cast data to numeric.
                df[row.internal_field_name] = \
                    pd.to_numeric(df[row.internal_field_name])
            elif row.field_type in NON_NUMERIC_TYPES:
                # Strip leading/trailing white space.
                df[row.internal_field_name] = \
                    df[row.internal_field_name].str.strip()
            else:
                # Well, we didn't expect this type.
                raise ValueError('Unexpected field_type, {}, for {}.'
                                 .format(row.field_type,
                                         row.internal_field_name))

        # Sort by BusNum if present.
        try:
            df.sort_values(by='BusNum', axis=0, inplace=True)
        except KeyError:
            # If there's no BusNum don't sort the DataFrame.
            pass
        else:
            # Re-index with simple monotonically increasing values.
            df.index = np.arange(start=0, stop=df.shape[0])

        # All done. We now have a well-formed DataFrame.
        return df

    # noinspection PyPep8Naming
    def RunScriptCommand(self, Statements):
        """Input a script command as in an Auxiliary file SCRIPT{}
        statement or the PowerWorld Script command prompt.

        `PowerWorld documentation for RunScriptCommand
        <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/RunScriptCommand_Function.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____41>`_

        `Auxiliary File Format
        <https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`_
        """
        output = self._call_simauto('RunScriptCommand', Statements)
        return output

    # noinspection PyPep8Naming
    def ProcessAuxFile(self, auxtext):
        """Creates and loads an Auxiliary file with the text specified
        in auxtext parameter."""
        f = open(self.aux_file_path, 'w')
        f.writelines(auxtext)
        f.close()
        output = self._call_simauto('ProcessAuxFile', self.aux_file_path)
        return output

    # noinspection PyPep8Naming
    def OpenOneLine(self, filename, view="", fullscreen="NO", showfull="NO"):
        filename = Path(filename)
        script = f"OpenOneline({filename.as_posix()}, {view}, {fullscreen}" \
                 f" {showfull})"
        output = self.RunScriptCommand(script)
        return output

    # noinspection PyPep8Naming
    def GetFieldList(self, ObjectType: str):
        # The second output should be a n*4 matrix, but the raw data is
        # n*5
        output = self._call_simauto('GetFieldList', ObjectType)
        df = pd.DataFrame(np.array(output))
        return df

    # noinspection PyPep8Naming
    def GetParametersSingleElement(self, element_type: str,
                                   field_list: list, value_list: list):
        """Retrieves parameter data according to the fields specified in
        field_list. value_list consists of identifying parameter values
        and zeroes and should be the same length as field_list
        """
        assert len(field_list) == len(value_list)
        # noinspection PyUnresolvedReferences
        field_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY,
                              field_list)
        # noinspection PyUnresolvedReferences
        value_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY,
                              value_list)
        output = self._call_simauto('GetParametersSingleElement',
                                    element_type, field_array, value_array)
        return output

    # noinspection PyPep8Naming
    def GetParametersMultipleElement(self, ObjectType: str, ParamList: list,
                                     FilterName: str = '') -> \
            Union[pd.DataFrame, None]:
        """Request values of specified fields for a set of objects in
        the load flow case.

        :param ObjectType: Type of object to get parameters for.
        :param ParamList: List of variables to obtain for the given
            object type. E.g. ['BusNum', 'GenID', 'GenRegPUVolt']. One
            can use the method GetFieldList to get a listing of all
            available fields. Additionally, you'll likely want to always
            return the key fields associated with the objects. These
            key fields can be obtained via the
            get_object_type_key_fields method.
        :param FilterName: Name of an advanced filter defined in the
            load flow case.

        :returns: Pandas DataFrame with columns matching the given
            ParamList. If the provided ObjectType is not present in the
            case, None will be returned. Note that if a given parameter
            is "bad" (e.g. doesn't exist), the corresponding column in
            the DataFrame will consist only of None.

        TODO: Should we cast None to NaN to be consistent with
        """
        # noinspection PyUnresolvedReferences
        param_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY,
                              ParamList)
        output = self._call_simauto('GetParametersMultipleElement',
                                    ObjectType, param_array, FilterName)
        if output is None:
            # Given object isn't present.
            return output

        # Create and return DataFrame.
        return pd.DataFrame(np.array(output).transpose(),
                            columns=ParamList)

    # noinspection PyPep8Naming
    def SolvePowerFlow(self, SolMethod: str = 'RECTNEWT'):
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
        <https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`_
        for more details.
        """
        script_command = "SolvePowerFlow(%s)" % SolMethod.upper()
        return self.RunScriptCommand(script_command)

    # noinspection PyPep8Naming
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

        # Get the listing of fields for this object type.
        try:
            field_list = self.POWER_FLOW_FIELDS[ObjectType.lower()]
        except KeyError:
            raise ValueError('Unsupported ObjectType for power flow results, '
                             '{}.'.format(ObjectType))

        # noinspection PyUnresolvedReferences
        field_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY,
                              field_list)

        output = self._call_simauto('GetParametersMultipleElement',
                                    ObjectType, field_array, '')

        # If no output is given,
        if output is None:
            return None

        return pd.DataFrame(np.array(output).transpose(),
                            columns=field_list)

    def get_three_phase_bolted_fault_current(self, bus_num):
        """Calculates the three phase fault; this can be done even with
        cases which only contain positive sequence impedances"""
        script_cmd = f'Fault([BUS {bus_num}], 3PB);\n'
        result = self.RunScriptCommand(script_cmd)
        field_list = ['BusNum', 'FaultCurMag']
        return self.GetParametersSingleElement('BUS', field_list, [bus_num, 0])

    def create_filter(self, condition, object_type, filter_name,
                      filter_logic='AND', filter_pre='NO', enabled='YES'):
        """Creates a filter in PowerWorld. The attempt is to reduce the
        clunkiness of creating a filter in the API, which entails
        creating an aux data file.
        """
        aux_text = '''
            DATA (FILTER, [ObjectType,FilterName,FilterLogic,FilterPre,Enabled])
            {
            "{objecttype}" "{filtername}" "{filterlogic}" "{filterpre}" "{enabled]"
                <SUBDATA Condition>
                    {condition}
                </SUBDATA>
            }'''.format(condition=condition, objecttype=object_type,
                        filtername=filter_name, filterlogic=filter_logic,
                        filterpre=filter_pre, enabled=enabled)
        return self._call_simauto('LoadAux', aux_text)

    # noinspection PyPep8Naming
    def SaveState(self):
        """SaveState is used to save the current state of the power
        system.
        """
        output = self._call_simauto('SaveState')
        return output

    # noinspection PyPep8Naming
    def LoadState(self):
        """LoadState is used to load the system state previously saved
        with the SaveState function.
        """
        return self._call_simauto('LoadState')

    # noinspection PyPep8Naming
    @property
    def ProcessID(self):
        """Retrieve the process ID of the currently running
        SimulatorAuto process"""
        output = self.__pwcom__.ProcessID
        return output

    # noinspection PyPep8Naming
    @property
    def RequestBuildDate(self):
        """Retrieve the build date of the PowerWorld Simulator
        executable currently running with the SimulatorAuto process
        """
        return self.__pwcom__.RequestBuildDate

    # noinspection PyPep8Naming
    def ChangeParameters(self, ObjType, Paramlist, ValueArray):
        """
        ChangeParameters is used to change single or multiple parameters
        of a single object. ParamList is a variant array storing strings
        that are Simulator object field variables, and must contain the
        key fields for the objecttype. Create variant arrays (one for
        each element being changed) with values corresponding to the
        fields in ParamList.
        """
        output = self._call_simauto('ChangeParameters', ObjType, Paramlist,
                                    ValueArray)
        return output

    # noinspection PyPep8Naming
    def ChangeParametersMultipleElement(self, ObjType: str,
                                        ParamList: list, ValueArray: list):
        """
        :param ObjType: String The type of object you are changing
            parameters for.
        :param ParamList: Variant A variant array storing strings (COM
            Type BSTR). This array stores a list of PowerWorld object
            field variables, as defined in the section on PowerWorld
            Object Fields. The ParamList must contain the key field
            variables for the specific device, or the device cannot be
            identified.
        :param ValueArray: Variant A variant array storing arrays of
            variants. This is the difference between the multiple
            element and single element change parameter functions.
            This array stores a list of arrays of values matching the
            fields laid out in ParamList. You construct ValueList by
            creating an array of variants with the necessary parameters
            for each device, and then inserting each individual array of
            values into the ValueList array. SimAuto will pick out each
            array from ValueList, and calls
            ChangeParametersSingleElement internally for each array of
            values in ValueList.
        :return: True or False
        """
        # noinspection PyUnresolvedReferences
        ValueArray = [VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY,
                              subArray) for subArray in ValueArray]
        return self._call_simauto('ChangeParametersMultipleElement',
                                  ObjType, ParamList, ValueArray)

    # noinspection PyPep8Naming
    def SendToExcel(self, ObjectType: str, FilterName: str, FieldList):
        """Send data from the Simulator Automation Server to an Excel
        spreadsheet."""
        return self._call_simauto('SendToExcel', ObjectType, FilterName,
                                  FieldList)

    # noinspection PyPep8Naming
    @property
    def UIVisible(self):
        output = self.__pwcom__.UIVisible
        return output

    # noinspection PyPep8Naming
    @property
    def CurrentDir(self):
        output = self.__pwcom__.CurrentDir
        return output

    # noinspection PyPep8Naming
    def TSCalculateCriticalClearTime(self, Branch):
        """
        Use this action to calculate critical clearing time for faults
        on the lines that meet the specified filter. A single line can
        be specified in the format [BRANCH keyfield1 keyfield2 ckt] or
        [BRANCH label]. Multiple lines can be selected by specifying a
        filter. For the specified lines, this calculation will determine
        the first time a violation is reached (critical clearing time),
        where a violation is determined based on all enabled Transient
        Limit Monitors. For each line, results are saved as a new
        Transient Contingency on a line, with the fault duration equal
        to the critical clearing time.
        """
        return self.RunScriptCommand(
            "TSCalculateCriticalClearTime (%s)" % Branch)

    # noinspection PyPep8Naming
    def TSResultStorageSetAll(self, ObjectType, Choice):
        return self.RunScriptCommand(
            "TSResultStorageSetAll (%s) (%s)" % (ObjectType, Choice))

    # noinspection PyPep8Naming
    def TSSolve(self, ContingencyName):
        """
        Solves only the specified contingency
        """
        return self.RunScriptCommand("TSSolve (%s)" % ContingencyName)

    # noinspection PyPep8Naming
    def TSGetContingencyResults(self, CtgName, ObjFieldList,
                                StartTime=None, StopTime=None):
        """
        Read transient stability results directly into the SimAuto COM
        object and be further used.
        !!!!! This function should ONLY be used after the simulation is run
        (for example, use this after running script commands tsSolveAll
        or tsSolve).
        ObjFieldList = ['"Plot ''Bus_4_Frequency''"'] or
        ObjFieldList = ['"Bus 4 | frequency"']
        """
        output = self._call_simauto('TSGetContingencyResults', CtgName,
                                    ObjFieldList, StartTime, StopTime)
        return output

    # noinspection PyPep8Naming
    def SetData(self, ObjectType: str, FieldList: str, ValueList: str,
                Filter=''):
        """
        Use this action to set fields for particular objects. If a
        filter is specified, then it will set the respective fields for
        all objects which meet this filter. Otherwise, if no filter is
        specified, then the keyfields must be included in the field
        list so that the object can be found. e.g.
        FieldList = '[Number,NomkV]'
        """

        return self.RunScriptCommand("SetData({},{},{},{})"
                                     .format(ObjectType, FieldList, ValueList,
                                             Filter))

    # noinspection PyPep8Naming
    def Delete(self, ObjectType: str):
        return self.RunScriptCommand("Delete(%s)" % ObjectType)

    # noinspection PyPep8Naming
    def CreateData(self, ObjectType: str, FieldList: str, ValueList: str):
        return self.RunScriptCommand("CreateData({},{},{})"
                                     .format(ObjectType, FieldList, ValueList))

    # noinspection PyPep8Naming
    def WriteAuxFile(self, FileName, FilterName, ObjectType, FieldList,
                     ToAppend=True, EString=None):
        """
        The WriteAuxFile function can be used to write data from the
        case in the Simulator Automation Server to a PowerWorld
        Auxiliary file. The name of an advanced filter which was
        PREVIOUSLY DEFINED in the case before being loaded in the
        Simulator Automation Server. If no filter is desired, then
        simply pass an empty string. If a filter name is passed but the
        filter cannot be found in the loaded case, no filter is used.
        """
        file_path = Path(FileName)
        self.aux_file_path = file_path.as_posix()
        return self._call_simauto('WriteAuxFile', self.aux_file_path,
                                  FilterName, ObjectType, FieldList, ToAppend)

    # noinspection PyPep8Naming
    def CalculateLODF(self, Branch, LinearMethod='DC', PostClosureLCDF='YES'):
        """
        Use this action to calculate the Line Outage Distribution
        Factors (or the Line Closure Distribution Factors) for a
        particular branch. If the branch is presently closed, then the
        LODF values will be calculated, otherwise the LCDF values will
        be calculated. You may optionally specify the linear calculation
        method as well. If no Linear Method is specified, Lossless DC
        will be used. The LODF results will be sent to excel
        """
        return self.RunScriptCommand("CalculateLODF ({},{},{})"
                                     .format(Branch, LinearMethod,
                                             PostClosureLCDF))

    # noinspection PyPep8Naming
    def SaveJacobian(self, JacFileName, JIDFileName, FileType, JacForm):
        """
        Use this action to save the Jacobian Matrix to a text file or a
        file formatted for use with MATLAB
        """
        return self.RunScriptCommand("SaveJacobian({},{},{},{})"
                                     .format(JacFileName, JIDFileName,
                                             FileType, JacForm))

    # noinspection PyPep8Naming
    def SaveYbusInMatlabFormat(self, FileName, IncludeVoltages='Yes'):
        """
        Use this action to save the YBus to a file formatted for use
        with MATLAB
        """
        return self.RunScriptCommand("SaveYbusInMatlabFormat({},{})"
                                     .format(FileName, IncludeVoltages))

    # noinspection PyPep8Naming
    def SetParticipationFactors(self, Method, ConstantValue, Object):
        """
        Use this action to modify the generator participation factors in
        the case.

        :param Method: 'MAXMWRAT'or 'RESERVE' or 'CONSTANT'
        :param ConstantValue : The value used if CONSTANT method is
            specified. If CONSTANT method is not specified, enter 0
            (zero).
        :param Object : Specify which generators to set the
            participation factor for.

        [Area Num], [Area "name"], [Area "label"]
        [Zone Num], [Zone "name"], [Zone "label"]
        SYSTEM
        AREAZONE or DISPLAYFILTERS
        """
        return self.RunScriptCommand("SetParticipationFactors ({},{},{})"
                                     .format(Method, ConstantValue, Object))

    # noinspection PyPep8Naming
    def TSRunUntilSpecifiedTime(self, ContingencyName, RunOptions):
        """
        This command allows manual control of the transient stability
        run. The simulation can be run until a specified time or number
        of times steps and then paused for further evaluation.
        :param ContingencyName: TODO
        :param RunOptions: '[StopTime(in seconds), StepSize(numbers),
            StepsInCycles='YES', ResetStartTime='NO',
            NumberOfTimeStepsToDo=0]'
        """
        return self.RunScriptCommand("TSRunUntilSpecifiedTime ({},{})"
                                     .format(ContingencyName, RunOptions))

    # noinspection PyPep8Naming
    def TSWriteOptions(self, FileName, Options, KeyField=' Primary'):
        """
        Save the transient stability option settings to an auxiliary
        file.

        :param FileName: TODO
        :param Options: [SaveDynamicModel, SaveStabilityOptions,
            SaveStabilityEvents, SaveResultsEvents, SavePlotDefinitions]

            SaveDynamicModel : (optional) NO doesn't save dynamic model
                (default YES)
            SaveStabilityOptions : (optional) NO doesn't save stability
                options (default YES)
            SaveStabilityEvents : (optional) NO doesn't save stability
                events (default YES)
            SaveResultsSettings : (optional) NO doesn't save results
                settings (default YES)
            SavePlotDefinitions : (optional) NO doesn't save plot
                definitions (default YES)
        :param KeyField: (optional) Specifies key: can be Primary,
            Secondary, or Label (default Primary)
        TODO: KeyField isn't currently used?
        """
        return self.RunScriptCommand("TSWriteOptions({},{})"
                                     .format(FileName, Options))

    # noinspection PyPep8Naming
    def EnterMode(self, mode):
        return self.RunScriptCommand("EnterMode(%s)" % mode)

    def exit(self):
        """Clean up for the PowerWorld COM object"""
        self.CloseCase()
        del self.__pwcom__
        self.__pwcom__ = None
        return None
