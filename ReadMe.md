# ESA
A python package that could dramatically reduce the time for general power system computation tasks by using a parallel and distributed framework.
## Citation
If you use ESA in any of your work, please use the following citation:
```latex
TODO
```
## Environment
Python 3 (recommend to use the latest Anaconda 3 with Python 3.7 or above)
## Installation
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install foobar.

```bash
pip install esa
```
## Pre-requisites
- Microsoft Windows Operating System (PowerWorld is Windows only)
- PowerWorld Simulator with SimAuto add-on installed
- [Git Large File Storage (LFS)](https://git-lfs.github.com/) (required to download
case files and run tests). After installing, simply change directories to
this repository, and run `git lfs install`. You will likely need to run a
`git pull` or `git lfs pull` after installing and setting up Git LFS.
After initial setup, you shouldn't need to do anything else with Git LFS.
## Usage
Before using the package, make sure you have PowerWorld Simulator with SimAuto add-on installed.

```python
from esa import SAW
pw = SAW("pwb_file_path")               # initialize the simauto object
fl = pw.GetFieldList("Bus")             # get a list of all the available fields for bus object
op = pw.SolvePowerFlow()                # solve the power flow
op = pw.get_power_flow_results("Bus")   # retrieve the power flow result
```
#### Simauto functions
We have implemented most of the native simauto functions. To call these functions, you can use the exact same function
name as defined [here](https://www.powerworld.com/WebHelp/Default.htm#MainDocumentation_HTML/Simulator_Automation_Server_Functions.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____3).

#### Script commands
Most of the script commands are supported by using the RunScriptCommand function. For more details, please check the 
[Auxiliary File Format](https://www.powerworld.com/WebHelp/Default.htm#Other_Documents/Auxiliary-File-Format.pdf%3FTocPath%3DAuxiliary%2520Script%252FData%2520Files%7C_____2). Here is one example:
```python
op = pw.RunScriptCommand("EnterMode(EDIT)")     # Enter the edit mode
```

#### Native functions
Besides the simauto functions and the script commands, we also implement some high-level functions in order to simplify
the programming logics and have a better formatted output. Here are the list: 

|  Function   |      Action      |        Argument      |
|-------------|----------------|-----------------------|
| change_and_confirm_params_multiple_element |  Change parameters for multiple objects of the same type, and confirm that the change was respected by PowerWorld. | *ObjectType*: string (Required). *command_df*: DataFrame (Required). |
| exit |    Manually close the PowerWorld COM object.   |  |
| get_key_fields_for_object_type | Helper function to get all key fields for an object type. | *ObjectType*: string (Required).  |
| get_power_flow_results |Get the power flow results from SimAuto server.|*ObjectType*: string (Required)

## License
[MIT](https://choosealicense.com/licenses/mit/)

## Contributing
We welcome contributions! Please read out `contributing.md`.
