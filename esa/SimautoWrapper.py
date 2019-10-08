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
from .decorators import handle_file_exception, handle_convergence_exception, \
    handle_general_exception
from pathlib import Path

# Listing of PowerWorld data types. I guess 'real' means float?
DATA_TYPES = ['Integer', 'Real', 'String']
# Hard-code based on indices.
NUMERIC_TYPES = DATA_TYPES[0:2]
NON_NUMERIC_TYPES = DATA_TYPES[-1]


class sa(object):
    """A SimAuto Wrapper in Python"""

    def __init__(self, pwb_file_path=None, earlybind=False, visible=False):
        try:
            if earlybind:
                self.__pwcom__ = win32com.client.gencache.EnsureDispatch('pwrworld.SimulatorAuto')
            else:
                self.__pwcom__ = win32com.client.dynamic.Dispatch('pwrworld.SimulatorAuto')
        except Exception as e:
            print(str(e))
            print("Unable to launch SimAuto.",
                  "Please confirm that your PowerWorld license includes the SimAuto add-on ",
                  "and that SimAuto has been successfuly installed.")
        # print(self.__ctime__(), "SimAuto launched")
        file_path = Path(pwb_file_path)
        self.pwb_file_path = file_path.as_posix()
        self.output = ''
        self.error = False
        self.error_message = ''
        self.COMout = ''
        self.__pwcom__.UIVisible = visible
        if self.openCase():
            print(self.__ctime__(), "Case loaded")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()
        return True

    def __ctime__(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def __setfilenames__(self):
        self.file_folder = os.path.split(self.pwb_file_path)[0]
        self.file_name = os.path.splitext(os.path.split(self.pwb_file_path)[1])[0]
        self.aux_file_path = self.file_folder + '/' + self.file_name + '.aux'  # some operations require an aux file
        self.save_file_path = os.path.splitext(os.path.split(self.pwb_file_path)[1])[0]

    def __pwerr__(self):
        if self.COMout is None:
            self.output = None
            self.error = False
            self.error_message = ''
        elif self.COMout[0] == '':
            self.output = None
            self.error = False
            self.error_message = ''
        elif 'No data' in self.COMout[0]:
            self.output = None
            self.error = False
            self.error_message = self.COMout[0]
        else:
            self.output = self.COMout[-1]
            self.error = True
            self.error_message = self.COMout[0]
        return self.error

    def _call_simauto(self, func: str, *args):
        """Helper function for calling the SimAuto server.

        :param func: Name of PowerWorld SimAuto function to call.

        :param args: Remaining arguments to this function will be
            passed directly to func.

        :returns: Result from PowerWorld. This will vary from function
            to function.

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

        # TODO: Handle errors. Maybe we can handle errors differently
        #   based on specific keyword arguments to the method.

        # After errors have been handled, return the data.
        return output[1]

    @handle_file_exception
    def openCase(self):
        """Opens case defined by the full file path; if this is undefined, opens by previous file path"""
        self.COMout = self.__pwcom__.OpenCase(self.pwb_file_path)

    @handle_file_exception
    def saveCase(self):
        """Saves case with changes to existing file name and path."""
        self.COMout = self.__pwcom__.SaveCase(self.pwb_file_path, 'PWB', True)

    def saveCaseAs(self, pwb_file_path=None):
        """If file name and path are specified, saves case as a new file.
        Overwrites any existing file with the same name and path."""
        if pwb_file_path is not None:
            file_path = Path(pwb_file_path)
            self.pwb_file_path = file_path.as_posix()
        return self.saveCase()

    @handle_file_exception
    def saveCaseAsAux(self, file_name, FilterName='', ObjectType=None, ToAppend=True, FieldList='all'):
        """If file name and path are specified, saves case as a new aux file.
        Overwrites any existing file with the same name and path."""
        file_path = Path(file_name)
        self.aux_file_path = file_path.as_posix()
        self.COMout = self.__pwcom__.WriteAuxFile(self.aux_file_path, FilterName, ObjectType, ToAppend, FieldList)

    @handle_file_exception
    def closeCase(self):
        """Closes case without saving changes."""
        self.COMout = self.__pwcom__.CloseCase()

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

    def getListOfDevices(self, ObjType: str, FilterName='') -> \
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

    @handle_general_exception
    def runScriptCommand(self, script_command):
        """Input a script command as in an Auxiliary file SCRIPT{} statement or the PowerWorld Script command prompt."""
        output = self.__pwcom__.RunScriptCommand(script_command)
        return output

    @handle_general_exception
    def loadAuxFileText(self, auxtext):
        """Creates and loads an Auxiliary file with the text specified in auxtext parameter."""
        f = open(self.aux_file_path, 'w')
        f.writelines(auxtext)
        f.close()
        output = self.__pwcom__.ProcessAuxFile(self.aux_file_path)
        return output

    @handle_file_exception
    def openOneLine(self, filename, view="", fullscreen="NO", showfull="NO"):
        filename = Path(filename)
        script = f"OpenOneline({filename.as_posix()}, {view}, {fullscreen}, {showfull})"
        output = self.runScriptCommand(script)
        return output

    @handle_general_exception
    def getFieldList(self, ObjectType: str): # The second output should be a n*4 matrix, but the raw data is n*5
        output = self.__pwcom__.GetFieldList(ObjectType)
        df = pd.DataFrame(np.array(output[1]))
        return df

    @handle_general_exception
    def getParametersSingleElement(self, element_type: str, field_list: list, value_list: list):
        """Retrieves parameter data according to the fields specified in field_list.
        value_list consists of identifying parameter values and zeroes and should be
        the same length as field_list"""
        assert len(field_list) == len(value_list)
        field_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, field_list)
        value_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, value_list)
        output = self.__pwcom__.GetParametersSingleElement(element_type, field_array, value_array)
        return output

    @handle_general_exception
    def getParametersMultipleElement(self, elementtype: str, fieldlist: list, filtername: str = ''):
        fieldarray = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, fieldlist)
        output = self.__pwcom__.GetParametersMultipleElement(elementtype, fieldarray, filtername)
        try:
            df = pd.DataFrame(np.array(output[-1]).transpose(), columns=fieldlist)
            return df
        except Exception:
            return False

    @handle_convergence_exception
    def runPF(self, method: str = 'RECTNEWT'):
        script_command = "SolvePowerFlow(%s)" % method.upper()
        self.COMout = self.__pwcom__.RunScriptCommand(script_command)

    @handle_general_exception
    def getPowerFlowResult(self, elementtype):
        """
        Get the power flow results from SimAuto server. Needs to specify the object type, e.g. bus, load, generator, etc
        """
        if 'bus' in elementtype.lower():
            fieldlist = ['BusNum', 'BusName', 'BusPUVolt', 'BusAngle', 'BusNetMW', 'BusNetMVR']
        elif 'gen' in elementtype.lower():
            fieldlist = ['BusNum', 'GenID', 'GenMW', 'GenMVR']
        elif 'load' in elementtype.lower():
            fieldlist = ['BusNum', 'LoadID', 'LoadMW', 'LoadMVR']
        elif 'shunt' in elementtype.lower():
            fieldlist = ['BusNum', 'ShuntID', 'ShuntMW', 'ShuntMVR']
        elif 'branch' in elementtype.lower():
            fieldlist = ['BusNum', 'BusNum:1', 'LineCircuit', 'LineMW', 'LineMW:1', 'LineMVR', 'LineMVR:1']
        fieldarray = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, fieldlist)
        output = self.__pwcom__.GetParametersMultipleElement(elementtype, fieldarray, '')
        try:
            df = pd.DataFrame(np.array(output[-1]).transpose(), columns=fieldlist)
            return df
        except Exception:
            return False

    def get3PBFaultCurrent(self, busnum):
        """Calculates the three phase fault; this can be done even with cases which
        only contain positive sequence impedances"""
        scriptcmd = f'Fault([BUS {busnum}], 3PB);\n'
        self.COMout = self.run_script(scriptcmd)
        fieldlist = ['BusNum', 'FaultCurMag']
        return self.getParametersSingleElement('BUS', fieldlist, [busnum, 0])

    @handle_general_exception
    def createFilter(self, condition, objecttype, filtername, filterlogic='AND', filterpre='NO', enabled='YES'):
        """Creates a filter in PowerWorld. The attempt is to reduce the clunkiness of
        # creating a filter in the API, which entails creating an aux data file"""
        auxtext = '''
            DATA (FILTER, [ObjectType,FilterName,FilterLogic,FilterPre,Enabled])
            {
            "{objecttype}" "{filtername}" "{filterlogic}" "{filterpre}" "{enabled]"
                <SUBDATA Condition>
                    {condition}
                </SUBDATA>
            }'''.format(condition=condition, objecttype=objecttype, filtername=filtername, filterlogic=filterlogic,
                        filterpre=filterpre, enabled=enabled)
        output = self.__pwcom__.load_aux(auxtext)
        return output

    @handle_general_exception
    def saveState(self):
        """SaveState is used to save the current state of the power system."""
        output = self.__pwcom__.SaveState()
        return output

    @handle_general_exception
    def loadState(self):
        """LoadState is used to load the system state previously saved with the SaveState function."""
        output = self.__pwcom__.LoadState()
        return output

    @property
    @handle_general_exception
    def ProcessID(self):
        """Retrieve the process ID of the currently running SimulatorAuto process"""
        output = self.__pwcom__.ProcessID
        return output

    @property
    @handle_general_exception
    def BuildDate(self):
        """Retrieve the build date of the PowerWorld Simulator executable currently running with the SimulatorAuto process"""
        output = self.__pwcom__.RequestBuildDate
        return output

    @handle_general_exception
    def changeParameters(self, ObjType, Paramlist, ValueArray):
        """
        ChangeParameters is used to change single or multiple parameters of a single object.
        Paramlist is a variant array storing strings that are Simulator object field variables,
        and must contain the key fields for the objecttype.
        Create variant arrays (one for each element being changed) with values corresponding to the fields in ParamList.
        """
        output = self.__pwcom__.ChangeParameters(ObjType, Paramlist, ValueArray)
        return output

    @handle_general_exception
    def changeParametersMultipleElement(self, ObjType: str, Paramlist: list, ValueArray: list):
        """
        :param ObjType: String The type of object you are changing parameters for.
        :param Paramlist: Variant A variant array storing strings (COM Type BSTR). This array stores a list of PowerWorldâ object field variables, as defined in the section on PowerWorld Object Fields. The ParamList must contain the key field variables for the specific device, or the device cannot be identified.
        :param ValueArray: Variant A variant array storing arrays of variants. This is the difference between the multiple element and single element change parameter functions. This array stores a list of arrays of values matching the fields laid out in ParamList. You construct ValueList by creating an array of variants with the necessary parameters for each device, and then inserting each individual array of values into the ValueList array. SimAuto will pick out each array from ValueList, and calls ChangeParametersSingleElement internally for each array of values in ValueList.
        :return: True or False
        """
        ValueArray = [VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, subArray) for subArray in ValueArray]
        output = self.__pwcom__.ChangeParametersMultipleElement(ObjType, Paramlist, ValueArray)
        return output

    @handle_file_exception
    def sendToExcel(self, ObjectType: str, FilterName: str, FieldList):
        """Send data from the Simulator Automation Server to an Excel spreadsheet."""
        self.COMout = self.__pwcom__.SendToExcel(ObjectType, FilterName, FieldList)

    @property
    @handle_general_exception
    def UIVisible(self):
        output = self.__pwcom__.UIVisible
        return output

    @property
    @handle_general_exception
    def CurrentDir(self):
        output = self.__pwcom__.CurrentDir
        return output

    @handle_general_exception
    def tsCalculateCriticalClearTime(self, Branch):
        """
        Use this action to calculate critical clearing time for faults on the lines that meet the specified filter.
        A single line can be specified in the format [BRANCH keyfield1 keyfield2 ckt] or [BRANCH label].
        Multiple lines can be selected by specifying a filter.
        For the specified lines, this calculation will determine the first time a violation is reached (critical clearing time),
        where a violation is determined based on all enabled Transient Limit Monitors. For each line, results are saved as a new
        Transient Contingency on a line, with the fault duration equal to the critical clearing time.
        """
        output = self.runScriptCommand("TSCalculateCriticalClearTime (%s)" % Branch)
        return output

    @handle_general_exception
    def tsResultStorageSetAll(self, objectttype, choice):
        output = self.runScriptCommand("TSResultStorageSetAll (%s) (%s)" % (objectttype, choice))
        return output

    @handle_general_exception
    def tsSolve(self, ContingencyName):
        """
        Solves only the specified contingency
        """
  #      self.TSResultStorageSetAll('Bus', 'Yes')
        output = self.runScriptCommand("TSSolve (%s)" % ContingencyName)
        return output

    @handle_general_exception
    def tsGetContingencyResults(self, CtgName, ObjFieldList, StartTime=None, StopTime=None):
        """
        Read transient stability results directly into the SimAuto COM obkect and be further used.
        !!!!! This function should ONLY be used after the simulation is run
        (for example, use this after running script commands tsSolveAll or tsSolve).
        ObjFieldList = ['"Plot ''Bus_4_Frequency''"'] or ObjFieldList = ['"Bus 4 | frequency"']
        """
        output = self.__pwcom__.TSGetContingencyResults(CtgName, ObjFieldList, StartTime, StopTime)
        return output

    @handle_general_exception
    def setData(self, ObjectType: str, FieldList: str, ValueList: str, Filter=''):
        """
        Use this action to set fields for particular objects. If a filter is specified, then it will set the respective fields for all
        objects which meet this filter. Otherwise, if no filter is specified, then the keyfields must be included in the field
        list so that the object can be found. e.g.FieldList = '[Number,NomkV]'
        """
        output = \
            self.runScriptCommand("SetData({},{},{},{})"
                                  .format(ObjectType, FieldList, ValueList,
                                          Filter))
        self.saveCase()
        return output

    @handle_general_exception
    def delete(self, ObjectType: str):
        output = self.runScriptCommand("Delete(%s)" % ObjectType)
        return output

    @handle_general_exception
    def createData(self, ObjectType: str, FieldList: str, ValueList: str):
        output = self.runScriptCommand("CreateData(%s,%s,%s)" % (ObjectType, FieldList, ValueList))
        return output

    @handle_file_exception
    def writeAuxFile(self, FileName, FilterName, ObjectType, FieldList, ToAppend=True, EString=None):
        """
        The WriteAuxFile function can be used to write data from the case in the Simulator Automation Server
        to a PowerWorldâ Auxiliary file. The name of an advanced filter which was PREVIOUSLY DEFINED in the
        case before being loaded in the Simulator Automation Server. If no filter is desired, then simply pass
        an empty string. If a filter name is passed but the filter cannot be found in the loaded case, no filter is used.
        """
        file_path = Path(FileName)
        self.aux_file_path = file_path.as_posix()
        self.COMout = self.__pwcom__.WriteAuxFile(self.aux_file_path, FilterName, ObjectType, FieldList, ToAppend)

    @handle_general_exception
    def calculateLODF(self, Branch, LinearMethod='DC', PostClosureLCDF='YES'):
        """
        Use this action to calculate the Line Outage Distribution Factors (or the Line Closure Distribution Factors) for a
        particular branch. If the branch is presently closed, then the LODF values will be calculated, otherwise the LCDF
        values will be calculated. You may optionally specify the linear calculation method as well. If no Linear Method is
        specified, Lossless DC will be used.
        The LODF results will be sent to excel
        """
        output = self.runScriptCommand("CalculateLODF (%s,%s,%s)" %(Branch, LinearMethod, PostClosureLCDF))
        return output

    @handle_file_exception
    def saveJacobian(self, JacFileName, JIDFileName, FileType, JacForm):
        """
        Use this action to save the Jacobian Matrix to a text file or a file formatted for use with Matlab
        """
        self.SaveJacCOMout = self.runScriptCommand("SaveJacobian(%s,%s,%s,%s) " % (JacFileName, JIDFileName, FileType, JacForm))

    @handle_file_exception
    def saveYbusInMatlabFormat(self, fileName, IncludeVoltages='Yes'):
        """
        Use this action to save the YBus to a file formatted for use with Matlab
        """
        self.SaveYBusCOMout = self.runScriptCommand("SaveYbusInMatlabFormat(%s,%s)" %(fileName, IncludeVoltages))

    @handle_general_exception
    def setParticipationFactors(self, Method, ConstantValue, Object):
        """
        Use this action to modify the generator participation factors in the case
        Method: 'MAXMWRAT'or 'RESERVE' or 'CONSTANT'
        ConstantValue : The value used if CONSTANT method is specified. If CONSTANT method is not specified, enter 0 (zero).
        Object : Specify which generators to set the participation factor for.
        [Area Num], [Area "name"], [Area "label"]
        [Zone Num], [Zone "name"], [Zone "label"]
        SYSTEM
        AREAZONE or DISPLAYFILTERS
        """
        output = self.runScriptCommand("SetParticipationFactors (%s,%s,%s)" %(Method, ConstantValue, Object))
        return output

    @handle_general_exception
    def tsRunUntilSpecifiedTime(self, ContingencyName, RunOptions):
        """
        This command allows manual control of the transient stability run. The simulation can be run until a
        specified time or number of times steps and then paused for further evaluation.
        RunOptions = '[StopTime(in seconds), StepSize(numbers), StepsInCycles='YES', ResetStartTime='NO', NumberOfTimeStepsToDo=0]'
        """
        output = self.runScriptCommand("TSRunUntilSpecifiedTime (%s,%s)" % (ContingencyName, RunOptions))
        return output

    @handle_general_exception
    def tsWriteOptions(self, fileName, Options, Keyfield=' Primary'):
        """
        Save the transient stability option settings to an auxiliary file.
        Options = [SaveDynamicModel, SaveStabilityOptions, SaveStabilityEvents, SaveResultsEvents, SavePlotDefinitions]
        SaveDynamicModel : (optional) NO doesn’t save dynamic model (default YES)
        SaveStabilityOptions : (optional) NO doesn’t save stability options (default YES)
        SaveStabilityEvents : (optional) NO doesn’t save stability events (default YES)
        SaveResultsSettings : (optional) NO doesn’t save results settings (default YES)
        SavePlotDefinitions : (optional) NO doesn’t save plot definitions (default YES)
        KeyField : (optional) Specifies key: can be Primary, Secondary, or Label (default Primary)
        """
        output = self.runScriptCommand("TSWriteOptions(%s,%s)" %(fileName, Options))
        return output

    @handle_general_exception
    def enterMode(self, mode):
        output = self.runScriptCommand("EnterMode(%s)" % mode)
        return output

    def exit(self):
        """Clean up for the PowerWorld COM object"""
        self.closeCase()
        del self.__pwcom__
        self.__pwcom__ = None
        return None
