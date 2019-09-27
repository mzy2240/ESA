
import pandas as pd
import numpy as np
import os
import win32com
from win32com.client import VARIANT
import pythoncom
import datetime
from .exceptions import ConvergenceException, GeneralException, FileException


class sa(object):
    """A SimAuto Wrapper in Python"""

    def __init__(self, pwb_file_path=None, earlybind=False):
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
        print(self.__ctime__(), "SimAuto launched")
        self.pwb_file_path = pwb_file_path
        self.__setfilenames__()
        self.output = ''
        self.error = False
        self.error_message = ''
        self.COMout = ''
        if self.openCase():
            print(self.__ctime__(), "Case loaded")

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

    def do(self, task):
        method_to_call = getattr(self, task)
        return method_to_call()

    def test(self):
        print("pass")

    def openCase(self, pwb_file_path=None):
        """Opens case defined by the full file path; if this is undefined, opens by previous file path"""
        if pwb_file_path is None and self.pwb_file_path is None:
            pwb_file_path = input('Enter full pwb file path > ')
        if pwb_file_path:
            self.pwb_file_path = os.path.splitext(pwb_file_path)[0] + '.pwb'
        else:
            self.COMout = self.__pwcom__.OpenCase(self.file_folder + '/' + self.file_name + '.pwb')
            if self.__pwerr__():
                raise FileException(self.error_message)
        return True

    def saveCase(self):
        """Saves case with changes to existing file name and path."""
        self.pwb_file_path = self.pwb_file_path.replace('/', '\\')
        self.COMout = self.__pwcom__.SaveCase(self.pwb_file_path, 'PWB', True)
        if self.__pwerr__():
            raise FileException(self.error_message)
        return True

    def saveCaseAs(self, pwb_file_path=None):
        """If file name and path are specified, saves case as a new file.
        Overwrites any existing file with the same name and path."""
        if pwb_file_path is not None:
            self.pwb_file_path = os.path.splitext(pwb_file_path)[0] + '.pwb'
            self.__setfilenames__()
        return self.saveCase()

    def saveCaseAsAux(self, file_name=None, FilterName='', ObjectType=None, ToAppend=True, FieldList='all'):
        """If file name and path are specified, saves case as a new aux file.
        Overwrites any existing file with the same name and path."""
        if file_name is None:
            file_name = self.file_folder + '/' + self.file_name + '.aux'
        self.file_folder = os.path.split(file_name)[0]
        self.save_file_path = os.path.splitext(os.path.split(file_name)[1])[0]
        self.aux_file_path = self.file_folder + '/' + self.save_file_path + '.aux'
        self.COMout = self.__pwcom__.WriteAuxFile(self.aux_file_path, FilterName, ObjectType, ToAppend, FieldList)
        if self.__pwerr__():
            raise FileException(self.error_message)
        return True

    def closeCase(self):
        """Closes case without saving changes."""
        self.COMout = self.__pwcom__.CloseCase()
        if self.__pwerr__():
            raise FileException(self.error_message)
        return True

    def getListOfDevices(self, ObjType, filterName):
        """Request a list of objects and their key fields"""
        output = self.__pwcom__.ListOfDevices(ObjType, filterName)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        else:
            print(self.__ctime__(), "List of", ObjType, ":", output)
            # df = pd.DataFrame(np.array(self.__pwcom__.output[1]).transpose(), columns=fieldlist)
            # df = df.replace('', np.nan, regex=True)
            return output
        return None

    def runScriptCommand(self, script_command):
        """Input a script command as in an Auxiliary file SCRIPT{} statement or the PowerWorld Script command prompt."""
        self.COMout = self.__pwcom__.RunScriptCommand(script_command)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return True

    def loadAuxFileText(self, auxtext):
        """Creates and loads an Auxiliary file with the text specified in auxtext parameter."""
        f = open(self.aux_file_path, 'w')
        f.writelines(auxtext)
        f.close()
        self.COMout = self.__pwcom__.ProcessAuxFile(self.aux_file_path)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return True

    def getFieldList(self, ObjectType: str): # The second output should be a n*4 matrix, but the raw data is n*5
        _output = self.__pwcom__.GetFieldList(ObjectType)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        df = pd.DataFrame(np.array(_output[1]))
        # df = df.replace('', np.nan, regex=True
        print(df)
        print(self.__ctime__(), "Field list:", _output)
        return df

    def getParametersSingleElement(self, element_type: str, field_list: list, value_list: list):
        """Retrieves parameter data according to the fields specified in field_list.
        value_list consists of identifying parameter values and zeroes and should be
        the same length as field_list"""
        assert len(field_list) == len(value_list)
        field_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, field_list)
        value_array = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, value_list)
        self.COMout = self.__pwcom__.GetParametersSingleElement(element_type, field_array, value_array)
        # return self.COMout
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        elif self.COMout is not None:
            return self.COMout[-1]
            # df = pd.DataFrame(np.array(self.COMout[-1]).transpose(), columns=field_list)
            # df = df.replace('', np.nan, regex=True)
            # return df
        return None

    def getParametersMultipleElement(self, elementtype: str, fieldlist: list, filtername: str = ''):
        fieldarray = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, fieldlist)
        self.COMout = self.__pwcom__.GetParametersMultipleElement(elementtype, fieldarray, filtername)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        elif self.COMout is not None:
            df = pd.DataFrame(np.array(self.COMout[-1]).transpose(), columns=fieldlist)
            # df = df.replace('', np.nan, regex=True)
            return df
        return None

    def runPF(self, method: str = 'RECTNEWT'):
        script_command = "SolvePowerFlow(%s)" % method.upper()
        self.COMout = self.__pwcom__.RunScriptCommand(script_command)
        if self.__pwerr__():
            raise ConvergenceException(self.error_message)
            # print('Error encountered with script:\n\n%s\n\n', self.error_message)
            # print('Script command which was attempted:\n\n%s\n\n', script_command)
            # return False
        return True

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
        self.COMout = self.__pwcom__.GetParametersMultipleElement(elementtype, fieldarray, '')
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        elif self.COMout is not None:
            df = pd.DataFrame(np.array(self.COMout[-1]).transpose(), columns=fieldlist)
            # df = df.replace('', np.nan, regex=True)
            return df
        return None

    def get3PBFaultCurrent(self, busnum):
        """Calculates the three phase fault; this can be done even with cases which
        only contain positive sequence impedances"""
        scriptcmd = f'Fault([BUS {busnum}], 3PB);\n'
        self.COMout = self.run_script(scriptcmd)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        fieldlist = ['BusNum', 'FaultCurMag']
        return self.getParametersSingleElement('BUS', fieldlist, [busnum, 0])

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
        self.COMout = self.__pwcom__.load_aux(auxtext)
        if self.__pwcom__.error:
            raise GeneralException(self.error_message)
        return True

    def saveState(self):
        """SaveState is used to save the current state of the power system."""
        output = self.__pwcom__.SaveState()
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        else:
            print(self.__ctime__(), "State:", output)
            return output
        return None

    def loadState(self):
        """LoadState is used to load the system state previously saved with the SaveState function."""
        output = self.__pwcom__.LoadState()
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        else:
            print(self.__ctime__(), "State:", output)
            # df = pd.DataFrame(np.array(self.__pwcom__.output[1]).transpose(), columns=fieldlist)
            # df = df.replace('', np.nan, regex=True)
            return output
        return None

    @property
    def ProcessID(self):
        """Retrieve the process ID of the currently running SimulatorAuto process"""
        output = self.__pwcom__.ProcessID
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        else:
            print(self.__ctime__(), "Process ID:", output)
            # df = pd.DataFrame(np.array(self.__pwcom__.output[1]).transpose(), columns=fieldlist)
            # df = df.replace('', np.nan, regex=True)
            return output
        return None

    @property
    def BuildDate(self):
        """Retrieve the build date of the PowerWorld Simulator executable currently running with the SimulatorAuto process"""
        output = self.__pwcom__.RequestBuildDate
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        elif self.error_message != '':
            raise GeneralException(self.error_message)
        else:
            print(self.__ctime__(), "Build date:", output)
            # df = pd.DataFrame(np.array(self.__pwcom__.output[1]).transpose(), columns=fieldlist)
            # df = df.replace('', np.nan, regex=True)
            return output
        return None

    def changeParameters(self, ObjType, Paramlist, ValueArray):
        """
        ChangeParameters is used to change single or multiple parameters of a single object.
        Paramlist is a variant array storing strings that are Simulator object field variables,
        and must contain the key fields for the objecttype.
        Create variant arrays (one for each element being changed) with values corresponding to the fields in ParamList. 
        """
        self.COMout = self.__pwcom__.ChangeParameters(ObjType, Paramlist, ValueArray)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return True

    def changeParametersMultipleElement(self, ObjType: str, Paramlist: list, ValueArray: list):
        """
        :param ObjType: String The type of object you are changing parameters for.
        :param Paramlist: Variant A variant array storing strings (COM Type BSTR). This array stores a list of PowerWorldâ object field variables, as defined in the section on PowerWorld Object Fields. The ParamList must contain the key field variables for the specific device, or the device cannot be identified.
        :param ValueArray: Variant A variant array storing arrays of variants. This is the difference between the multiple element and single element change parameter functions. This array stores a list of arrays of values matching the fields laid out in ParamList. You construct ValueList by creating an array of variants with the necessary parameters for each device, and then inserting each individual array of values into the ValueList array. SimAuto will pick out each array from ValueList, and calls ChangeParametersSingleElement internally for each array of values in ValueList.
        :return: True or False
        """
        ValueArray = [VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_ARRAY, subArray) for subArray in ValueArray]
        self.COMout = self.__pwcom__.ChangeParametersMultipleElement(ObjType, Paramlist, ValueArray)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return True

    def sendToExcel(self, ObjectType: str, FilterName: str, FieldList):
        """Send data from the Simulator Automation Server to an Excel spreadsheet."""
        self.COMout = self.__pwcom__.SendToExcel(ObjectType, FilterName, FieldList)
        if self.__pwerr__():
            raise FileException(self.error_message)
        return True

    @property
    def UIVisible(self):
        output = self.__pwcom__.UIVisible
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return output

    @property
    def CurrentDir(self):
        output = self.__pwcom__.CurrentDir
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return output
    
    def tsCalculateCriticalClearTime(self, Branch):
        """
        Use this action to calculate critical clearing time for faults on the lines that meet the specified filter.
        A single line can be specified in the format [BRANCH keyfield1 keyfield2 ckt] or [BRANCH label]. 
        Multiple lines can be selected by specifying a filter. 
        For the specified lines, this calculation will determine the first time a violation is reached (critical clearing time),
        where a violation is determined based on all enabled Transient Limit Monitors. For each line, results are saved as a new 
        Transient Contingency on a line, with the fault duration equal to the critical clearing time. 
        """
        _output = self.runScriptCommand("TSCalculateCriticalClearTime (%s)" % Branch)
        print(self.__ctime__(), _output)

        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return _output
    
    def tsResultStorageSetAll(self, objectttype, choice):
        
        self.COMout = self.runScriptCommand("TSResultStorageSetAll (%s) (%s)" % (objectttype, choice))
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return True        
        
    def tsSolve(self, ContingencyName):
        """
        Solves only the specified contingency
        """
  #      self.TSResultStorageSetAll('Bus', 'Yes')
        _output = self.runScriptCommand("TSSolve (%s)" % ContingencyName)
        print(_output)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "TsSolve executed")
        
        return None

    def tsGetContingencyResults(self, CtgName, ObjFieldList, StartTime=None, StopTime=None):
        """
        Read transient stability results directly into the SimAuto COM obkect and be further used.
        !!!!! This function should ONLY be used after the simulation is run
        (for example, use this after running script commands tsSolveAll or tsSolve).
        ObjFieldList = ['"Plot ''Bus_4_Frequency''"'] or ObjFieldList = ['"Bus 4 | frequency"']
        """
        _output = self.__pwcom__.TSGetContingencyResults(CtgName, ObjFieldList, StartTime, StopTime)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        # print(_output[2][-1])
        # print(self.__ctime__(), "TS result: %s" % str(_output[2]))
        return _output
    
    def setData(self, ObjectType: str, FieldList: str, ValueList: str, Filter=''):
        """
        Use this action to set fields for particular objects. If a filter is specified, then it will set the respective fields for all
        objects which meet this filter. Otherwise, if no filter is specified, then the keyfields must be included in the field
        list so that the object can be found. e.g.FieldList = '[Number,NomkV]'
        """
        _output = self.runScriptCommand("SetData(%s,%s,%s)" % (ObjectType, FieldList, ValueList))
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "Setting data: %s" % ObjectType)
        # self.saveCase()
        self.saveCase()
        return self.COMout

    def delete(self, ObjectType: str):
        _output = self.runScriptCommand("Delete(%s)" % ObjectType)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "Delete: %s" % ObjectType)
        # self.saveCase()
        return None

    def createData(self, ObjectType: str, FieldList: str, ValueList: str):
        _output = self.runScriptCommand("CreateData(%s,%s,%s)" % (ObjectType, FieldList, ValueList))
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "Creating data: %s" % ObjectType)
        # self.saveCase()
        return None
    
    def writeAuxFile(self, FileName, FilterName, ObjectType, FieldList, ToAppend=True, EString=None):
        """
        The WriteAuxFile function can be used to write data from the case in the Simulator Automation Server 
        to a PowerWorldâ Auxiliary file. The name of an advanced filter which was PREVIOUSLY DEFINED in the 
        case before being loaded in the Simulator Automation Server. If no filter is desired, then simply pass 
        an empty string. If a filter name is passed but the filter cannot be found in the loaded case, no filter is used.
        """
        self.COMout = self.__pwcom__.WriteAuxFile(FileName, FilterName, ObjectType, FieldList, ToAppend)
        if self.__pwerr__():
            raise FileException(self.error_message)
        print(self.__ctime__(), "Writing Aux File (%s):" % ObjectType)
        return None
    
    def calculateLODF(self, Branch, LinearMethod='DC', PostClosureLCDF='YES'):
        """
        Use this action to calculate the Line Outage Distribution Factors (or the Line Closure Distribution Factors) for a
        particular branch. If the branch is presently closed, then the LODF values will be calculated, otherwise the LCDF
        values will be calculated. You may optionally specify the linear calculation method as well. If no Linear Method is
        specified, Lossless DC will be used.
        The LODF results will be sent to excel
        """  
        self.CalLODFout3 = self.runScriptCommand("CalculateLODF (%s,%s,%s)" %(Branch, LinearMethod, PostClosureLCDF))
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "Calculate LODF (%s):" % Branch)
        self.sendToExcel('Branch', '',['BusNumFrom','BusNumTo','LODF'])
        return self.CalLODFout3          
        
    def saveJacobian(self, JacFileName, JIDFileName, FileType, JacForm):
        """
        Use this action to save the Jacobian Matrix to a text file or a file formatted for use with Matlab
        """
        self.SaveJacCOMout = self.runScriptCommand("SaveJacobian(%s,%s,%s,%s) " % (JacFileName, JIDFileName, FileType, JacForm))
        if self.__pwerr__():
            raise FileException(self.error_message)
        print(self.__ctime__(), "Successfully savd Jacobian to(%s):" % FileType)
        return None
    
    def saveYbusInMatlabFormat(self, fileName, IncludeVoltages='Yes'):
        """
        Use this action to save the YBus to a file formatted for use with Matlab
        """
        self.SaveYBusCOMout = self.runScriptCommand("SaveYbusInMatlabFormat(%s,%s)" %(fileName, IncludeVoltages))
        if self.__pwerr__():
            raise FileException(self.error_message)
        print(self.__ctime__(), "Successfully savd Ybus_inMatlabFormat to(%s):" % fileName)
        return None
    
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
        self.SetParticipationFactorCOMout = self.runScriptCommand("SetParticipationFactors (%s,%s,%s)" %(Method, ConstantValue, Object))
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "Successfully set ParticipationFactor to(%s):" % Method)
        return True
    
    def tsRunUntilSpecifiedTime(self, ContingencyName, RunOptions):
        """
        This command allows manual control of the transient stability run. The simulation can be run until a
        specified time or number of times steps and then paused for further evaluation.
        RunOptions = '[StopTime(in seconds), StepSize(numbers), StepsInCycles='YES', ResetStartTime='NO', NumberOfTimeStepsToDo=0]'
        """
        self.tsRunUntilSpecifiedTimeCOMout = self.runScriptCommand("TSRunUntilSpecifiedTime (%s,%s)" % (ContingencyName, RunOptions))     
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "Run until specified time(%s):" % ContingencyName)
        return True
    
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
        self.WriteOptionsCOMout = self.runScriptCommand("TSWriteOptions(%s,%s)" %(fileName, Options))
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        print(self.__ctime__(), "Save transient stability option seting to(%s):" % fileName)
        return True
        
    def enterMode(self, mode):
        self.COMout = self.runScriptCommand("EnterMode(%s)" % mode)
        if self.__pwerr__():
            raise GeneralException(self.error_message)
        return True
    
     
    def exit(self):
        """Clean up for the PowerWorld COM object"""
        self.closeCase()
        del self.__pwcom__
        self.__pwcom__ = None
        return None

    # def __del__(self):
    #     self.exit()


   

