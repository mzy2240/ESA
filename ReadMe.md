# ESA
A python package that makes PowerWorld Simauto easier yet more powerful to use. There are two major scripts in this collection:
 
* Manager.py
* Workers.py
* PYSimAuto.py
## Environment
python 3.5 or above (recommend the latest Anaconda 3)
## Installation
`pip install ssimauto`
## Usage
Before using the package, make sure you have PowerWorld Simulator and SimAuto add-on installed. Use script below to start:

```
from ssimauto import Manager

from ssimauto import Workers

from ssimauto import PYSimAuto
```
## from ssimauto import PYSimAuto
PYSimAuto is a wrapper for the PowerWorld SimAuto COM object. It is designed to be easy to use, and it includes most of the SimAuto functions and script actions included in the script sections of the Auxiliary Files.
Most common methods are listed below.

|  Function   |      Action      |        Argument      |
|-------------|----------------|-----------------------|
| openCase(pwb_file_path) |  Opens case defined by the full file path | *pwb_file_path*: string (Required). This string includes the directory location and full file name. |
| saveCase() |    Saves case with changes to existing file name and path.   |  |
| saveCaseAs(pwb_file_path) | If file name and path are specified, saves case as a new file.Overwrites any existing file with the same name and path. | *pwb_file_path*: string (Optional)   |
|saveCaseAsAux(file_name, FilterName, ObjectType, ToAppend, FieldList)|If file name and path are specified, saves case as a new aux file.Overwrites any existing file with the same name and path.|*file_name*=string (Optional).  *FilterName*: string (Optional). *ObjectType*: string (Optional). *ToAppend*: boolean (Optional)  Default is True. *FieldList*: variant (Optional)  Default is 'all'|
|closeCase()|Closes case without saving changes.||
|getListOfDevices(ObjType, filterName)|Request a list of objects and their key fields|*ObjType*: string (Required), *filterName*: string (Required)|
|runScriptCommand(script_command)|Input a script command as in an Auxiliary file SCRIPT{} statement or the PowerWorld Script command prompt.|*script_command*: string (Required)|
|loadAuxFileText(self, auxtext)|Creates and loads an Auxiliary file with the text specified in auxtext parameter.|*auxtext*: string (Required)|
|getFieldList(ObjectType)|The GetFieldList function is used to find all fields contained within a given object type.|*ObjectType*: string (Required)|
|getParametersSingleElement(element_type, field_list, value_list)|Retrieves parameter data according to the fields specified in field_list.|*element_type*: string (Required). *field_list*: variant (Required) A variant array storing strings. *value_list*: variant (Required) A variant array storing variants.|
|getParametersMultipleElement(elementtype, fieldlist, filtername)|The GetParametersMultipleElement function is used to request the values of specified fields for a set of objects in the load flow case.|*elementtype*: string (Required). *fieldlist*: string (Required). *filtername*: string (Optional).|
|get3PBFaultCurrent(busnum)|Calculates the three phase fault; this can be done even with cases which only contain positive sequence impedances|*busnum*: string (Required)|
|createFilter(condition, objecttype, filtername, filterlogic, filterpre, enabled)|Creates a filter in PowerWorld. The attempt is to reduce the clunkiness of creating a filter in the API, which entails creating an aux data file|*condition, objecttype, filtername*: string (Required). *filterlogic*: string (Optional) Default is 'AND'. *filterpre*: string (optional) Default is 'NO'. *enabled*: string (Optional) Default is 'YES' |
|saveState()|SaveState is used to save the current state of the power system.||
|loadState()|LoadState is used to load the system state previously saved with the SaveState function.||
|changeParameters(ObjType, Paramlist, ValueArray)|ChangeParameters is used to change single or multiple parameters of a single object.|*ObjType*: string (Required). *Paramlist*: variant of array (Required), *ValueArray*: A variant array storing variants (Required)|
|sendToExcel(ObjectType, FilterName, FieldList)|Send data from the Simulator Automation Server to an Excel spreadsheet.|*ObjectType*: String (Required). *FilterName*: String (Required). *FieldList*: Variant This parameter must either be an array of fields for the given object or the string "ALL".|
|tsCalculateCriticalClearTime(Branch)|Use this action to calculate critical clearing time for faults on the lines that meet the specified filter.|*Branch*: string (Required)|
|tsResultStorageSetAll(objectttype, choice)|This command will allow setting which object types are stored in memory during a transient stability run. This will affect all fields and states for the specified objecttype. |*objectttype*: string (Required). *choice*: string (Required).|
|tsSolve(ContingencyName)|Solves only the specified contingency|*ContingencyName*: string (Required).|
|tsGetContingencyResults(CtgName, ObjFieldList, StartTime, StopTime)|Read transient stability results directly into the SimAuto COM obkect and be further used. This function should ONLY be used after the simulation is run|*CtgName*: string (Required). *ObjFieldList*: string (Required). *StartTime*: string (Optional). *StopTime*: string (Optional)|
|setData(ObjectType, FieldList, ValueList, Filter)|Use this action to set fields for particular objects.|*ObjectType*: string (Required). *FieldList*: A variant of string (Required). *ValueList*: A variant of string (Required). *Filter*: string (Optional) |
|delete(ObjectType)|Use this delete objects of a particular type. A filter may optionally be specified to only delete objects that meet a filter.|*ObjectType*: string (Required)|
|createData(ObjectType, FieldList, ValueList)|Use this action to create particular objects.|*ObjectType*: string (Required). *FieldList*: A variant of string (Required). *ValueList*: A variant of string. (Required).|
|writeAuxFile(FileName, FilterName, ObjectType, FieldList, ToAppend, EString)|This function can be used to write data from the case in the Simulator Automation Server to a PowerWorld Auxiliary file.|*FileName*: string (Required). *FilterName*: string (Required). *ObjectType*: string (Required). *FieldList*: A variant of string  (Required). *ToAppend* =True. *EString*=None |
|calculateLODF(Branch, LinearMethod, PostClosureLCDF)|Use this action to calculate the Line Outage Distribution Factors (or the Line Closure Distribution Factors) for a particular branch.|*Branch*: string (Required). *LinearMethod*: string (Oprional) Default is 'DC'. *PostClosureLCDF*: string (Optional) Default is 'YES'.|
|saveJacobian(JacFileName, JIDFileName, FileType, JacForm)|Use this action to save the Jacobian Matrix to a text file or a file formatted for use with Matlab.|*JacFileName, JIDFileName*: string (Required). *FileType*: string 'M' or 'TEX' or 'EXPM' (Required). *JacForm*: string 'R' or 'P' (Required).|
|saveYbusInMatlabFormat(fileName, IncludeVoltages)|Use this action to save the YBus to a file formatted for use with Matlab|*fileName*: string (Required). *IncludeVoltages*: string (Optional) Default is 'YES'.|
|setParticipationFactors(Method, ConstantValue, Object)|Use this action to modify the generator participation factors in the case. |*Method*: string 'MAXMWRAT'or 'RESERVE' or 'CONSTANT' (Required). *ConstantValue*: float (Required). *Object*: string (Required)|
|tsRunUntilSpecifiedTime(ContingencyName, RunOptions)|This command allows manual control of the transient stability run.|*ContingencyName*: string (Required). *RunOptions*: string '[StopTime(in seconds), StepSize(numbers), StepsInCycles='YES', ResetStartTime='NO', NumberOfTimeStepsToDo=0]' (Required).|
|tsWriteOptions(fileName, Options, Keyfield|Save the transient stability option settings to an auxiliary file.|*fileName*: string (Required). *Options*: string '[SaveDynamicModel, SaveStabilityOptions, SaveStabilityEvents, SaveResultsEvents, SavePlotDefinitions]' (Optional). *Keyfield*: string (Optional)|
|enterMode(mode)|This action will change the mode in which Simulator is operating.|*mode*: string (Required)|
## Developer
If you have any questions, feel free to contact the developers.

Zeyu Mao, PhD student in Texas A&M University, zeyumao2@tamu.edu  

Yijing Liu, PhD student in Texas A&M University, yiji21@tamu.edu
