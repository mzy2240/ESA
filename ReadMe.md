# ESA
A python package that could dramatically reduce the time for general power system computation tasks by using a parallel and distributed framework.
## Citation
If you use ESA in any of your work, please use the following citation:
```latex
TODO
```
## Contributing
We welcome contributions! Please read out `contributing.md`.
## Environment
python 3.5 or above (recommend to use the latest Anaconda 3)
## Installation
`pip install esa`
## Pre-requisites
- Microsoft Windows Operating System (PowerWorld is Windows only)
- PowerWorld Simulator with SimAuto add-on installed
- [Git Large File Storage (LFS)](https://git-lfs.github.com/) (required to download
case files and run tests). After installing, simply change directories to
this repository, and run `git lfs install`. You will likely need to run a
`git pull` or `git lfs pull` after installing and setting up Git LFS.
After initial setup, you shouldn't need to do anything else with Git LFS.
## Usage
Before using the package, make sure you have PowerWorld Simulator and SimAuto add-on installed. Use script below to start:

```
from esa import Manager

from esa import Workers

from esa import sa
```
### Manager
Manager is a task scheduler for distributed workers. It is designed for task distribution and worker management.
```buildoutcfg
manager = Manager(progressbar=False)
manager.addTask(["some_task"])           # Add tasks
manager.onFinish(a_callback_func)        # The function will be called when all tasks are done
manager.onSingleResult(a_callback_func)  # The function will be called when any task is done
manager.start()                          # Manager starts to work (*non-block)
manager.stop()                           # Manager stops working
manager.loop_forever()                   # Manager starts to work (*block)
```
Using the following properties can help you track the task progress:
```buildoutcfg
manager.status                           # Manager status and remaining tasks
manager.management                       # Statistics for workers
manager.time                             # The time format that manager uses
```

### Workers
Workers is a group of PowerWorld Simauto COM objects. It is designed to get the task from Manager and execute the task with PYSimAuto in parallel.
```buildoutcfg
worker = Workers(number=1, ip="165.91.215.167", port=1883, auto_shutdown=False, timeout=0, file_path="")
worker.start()
```
### sa
sa is a wrapper for the PowerWorld SimAuto COM object. It is designed to be easy to use, and it includes most of the SimAuto functions and script actions included in the script sections of the Auxiliary Files.
Most common methods are listed below.
```buildoutcfg
pysimauto = sa(pwb_file_path)
pysimauto.getListOfDevices(ObjType, filterName)                               # Get a list of objects and their key fields
ContingencyName = 'My Transient Contingency'                                  # Contingency that has already been defined in PowerWorld Simulator
pysimauto.tsSolve(ContingencyName)                                            # Solve contingency
pysimauto.tsGetContingencyResults(CtgName, ObjFieldList, StartTime, StopTime) # This function should ONLY be used after the simulation is run
Branch = '"Branch ''4'' ''5'' ''1''"'                                         # Branch label should be entered as a string
pysimatuo.tsCalculateCriticalClearTime(Branch)                                # Calculate CCT of the branch and the result is returned to PW as a new ctg.
```
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
|getParametersMultipleElement(elementtype, fieldlist, filtername)|The GetParametersMultipleElement function is used to request the values of specified fields for a set of objects in the load flow case.|*elementtype*: string (Required). *fieldlist*: list of string (Required). *filtername*: string (Optional).|
|runPF(method)|Run the power flow |*method*: string (Optional, default NR)|
|getPowerFlowResult(elementtype)|Get the power flow results from SimAuto server.|*elementtype*: string (Required, e.g. bus, gen, load, etc.)|
|get3PBFaultCurrent(busnum)|Calculates the three phase fault; this can be done even with cases which only contain positive sequence impedances|*busnum*: string (Required)|
|createFilter(condition, objecttype, filtername, filterlogic, filterpre, enabled)|Creates a filter in PowerWorld. The attempt is to reduce the clunkiness of creating a filter in the API, which entails creating an aux data file|*condition, objecttype, filtername*: string (Required). *filterlogic*: string (Optional) Default is 'AND'. *filterpre*: string (optional) Default is 'NO'. *enabled*: string (Optional) Default is 'YES' |
|saveState()|SaveState is used to save the current state of the power system.||
|loadState()|LoadState is used to load the system state previously saved with the SaveState function.||
|changeParameters(ObjType, Paramlist, ValueArray)|ChangeParameters is used to change single or multiple parameters of a single object.|*ObjType*: string (Required). *Paramlist*: variant of array (Required), *ValueArray*: A variant array storing variants (Required)|
|changeParametersMultipleElement(ObjType, Paramlist, ValueArray)|changeParametersMultipleElement is used to change single or multiple parameters of multiple objects.|*ObjType*: string (Required). *Paramlist*: variant of array (Required), *ValueArray*: A variant array storing variants (Required)|
|sendToExcel(ObjectType, FilterName, FieldList)|Send data from the Simulator Automation Server to an Excel spreadsheet.|*ObjectType*: String (Required). *FilterName*: String (Required). *FieldList*: Variant This parameter must either be an array of fields for the given object or the string "ALL".|
|tsCalculateCriticalClearTime(Branch)|Use this action to calculate critical clearing time for faults on the lines that meet the specified filter.|*Branch*: string (Required)|
|tsResultStorageSetAll(objectttype, choice)|This command will allow setting which object types are stored in memory during a transient stability run. This will affect all fields and states for the specified objecttype. |*objectttype*: string (Required). *choice*: string (Required).|
|tsSolve(ContingencyName)|Solves only the specified contingency|*ContingencyName*: string (Required).|
|tsGetContingencyResults(CtgName, ObjFieldList, StartTime, StopTime)|Read transient stability results directly into the SimAuto COM obkect and be further used. This function should ONLY be used after the simulation is run.|*CtgName*: string (Required). *ObjFieldList*: string (Required). *StartTime*: string (Optional). *StopTime*: string (Optional)|
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

## Developers
If you have any questions regarding this package, please feel free to contact the developers via GitHub.

