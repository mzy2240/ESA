# Easy SimAuto (ESA)
This Python package provides an easy to use and light-weight wrapper for
interfacing with PowerWorld's Simulator Automation Server (SimAuto). 

This file contains some motivation for the ESA package, a quick start, 
installation directions, common issues, and some examples/snippets.

## Why Use ESA?
Directly interacting with PowerWorld via the Windows COM object can be
quite cumbersome. Data type inputs and outputs can be odd, returns
come back unlabeled, and you have to use pywin32 to interface with
SimAuto. 

ESA makes all these tasks quick and easy, is well documented, 
automagically translates data to the appropriate types, and uses 
Pandas DataFrames and Series where possible. For some motivating 
examples, please the the "Quick Start" section of this document.

## Citation
If you use ESA in any of your work, please use the following citation:
```latex
@misc{ESA,
  author = {Zeyu Mao, Brandon Thayer and Yijing Liu},
  title = {Easy SimAuto (ESA)},
  year = {2019},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/mzy2240/ESA}},
  commit = {<copy + paste the specific commit you used here>}
}
```

## Documentation
ESA is documented [here](https://mzy2240.github.io/ESA/).

## Quick Start
The following quick start example uses the IEEE 14 bus case, which can
be found [in the repository](https://github.com/mzy2240/ESA/tree/master/tests/cases/ieee_14)
or from [Texas A&M](https://electricgrids.engr.tamu.edu/electric-grid-test-cases/ieee-14-bus-system/).

You can find API documentation [here](https://mzy2240.github.io/ESA/html/index.html).
```python
# Import the SimAuto Wrapper (SAW)
>>> from esa import SAW

# Initialize SAW instance using 14 bus test case. Adapt path as needed
# for your file system.
>>> saw = SAW(FileName=r'C:\Users\myuser\git\ESA\tests\cases\ieee_14\IEEE 14 bus.pwb')

# Solve the power flow.
>>> saw.SolvePowerFlow()

# Retrieve power flow results for buses. This will return a Pandas 
# DataFrame to make your life easier.
>>> bus_data = saw.get_power_flow_results('bus')
>>> print(bus_data)
    BusNum BusName  BusPUVolt   BusAngle    BusNetMW  BusNetMVR
0        1   Bus 1   1.060000   0.000000  232.391691 -16.549389
1        2   Bus 2   1.045000  -4.982553   18.300001  30.855957
2        3   Bus 3   1.010000 -12.725027  -94.199997   6.074852
3        4   Bus 4   1.017672 -10.312829  -47.799999   3.900000
4        5   Bus 5   1.019515  -8.773799   -7.600000  -1.600000
5        6   Bus 6   1.070000 -14.220869  -11.200000   5.229700
6        7   Bus 7   1.061520 -13.359558    0.000000   0.000000
7        8   Bus 8   1.090000 -13.359571    0.000000  17.623067
8        9   Bus 9   1.055933 -14.938458  -29.499999   4.584888
9       10  Bus 10   1.050986 -15.097221   -9.000000  -5.800000
10      11  Bus 11   1.056907 -14.790552   -3.500000  -1.800000
11      12  Bus 12   1.055189 -15.075512   -6.100000  -1.600000
12      13  Bus 13   1.050383 -15.156196  -13.500001  -5.800000
13      14  Bus 14   1.035531 -16.033565  -14.900000  -5.000000

# Retrieve power flow results for generators.
>>> gen_data = saw.get_power_flow_results('gen')
>>> print(gen_data)
   BusNum GenID       GenMW     GenMVR
0       1     1  232.391691 -16.549389
1       2     1   40.000001  43.555957
2       3     1    0.000000  25.074852
3       6     1    0.000000  12.729700
4       8     1    0.000000  17.623067

# Let's change generator injections! But first, we need to know which 
# fields PowerWorld needs in order to identify generators. These fields
# are known as key fields.
>>> gen_key_fields = saw.get_key_fields_for_object_type('gen')
>>> print(gen_key_fields['internal_field_name'])
key_field_index
0    BusNum
1     GenID
Name: internal_field_name, dtype: object
>>> key_fields = gen_key_fields['internal_field_name'].tolist()
>>> print(key_fields)
['BusNum', 'GenID']

# Change generator active power injection at buses 3 and 8 via SimAuto
# function.
>>> params = key_fields + ['GenMW']
>>> values = [[3, '1', 30], [8, '1', 50]]
>>> saw.ChangeParametersMultipleElement(ObjectType='gen', ParamList=params, ValueList=values)

# Did it work? Spoiler: it does!
>>> new_gen_data = saw.GetParametersMultipleElement(ObjectType='gen', ParamList=params)
>>> print(new_gen_data)
   BusNum GenID       GenMW
0       1     1  232.391691
1       2     1   40.000001
2       3     1   30.000001
3       6     1    0.000000
4       8     1   50.000000

# It would seem the generator active power injections have changed. Let's 
# re-run the power flow and see if bus voltages and angles change. Spoiler:
# they do.
>>> saw.SolvePowerFlow()
>>> new_bus_data = saw.get_power_flow_results('bus')
>>> cols = ['BusPUVolt', 'BusAngle']
>>> print(bus_data[cols] - new_bus_data[cols])
       BusPUVolt   BusAngle
0   0.000000e+00   0.000000
1  -1.100000e-07  -2.015596
2  -5.700000e-07  -4.813164
3  -8.650700e-03  -3.920185
4  -7.207540e-03  -3.238592
5  -5.900000e-07  -4.586528
6  -4.628790e-03  -7.309167
7  -3.190000e-06 -11.655362
8  -7.189370e-03  -6.284631
9  -6.256150e-03  -5.987861
10 -3.514030e-03  -5.297895
11 -2.400800e-04  -4.709888
12 -1.351040e-03  -4.827348
13 -4.736110e-03  -5.662158

# Wouldn't it be easier if we could change parameters with a DataFrame?
# Wouldn't it be nice if we didn't have to manually check if our updates
# were respected? You're in luck!
#
# Create a copy of the gen_data DataFrame so that we can modify its 
# values and use it to update parameters in PowerWorld.
>>> gen_copy = gen_data.copy()
# Change generation at buses 2, 3 and 6.
>>> gen_copy.loc[gen_copy['BusNum'].isin([2, 3, 6]), 'GenMW'] = [0.0, 100.0, 100.0]
>>> print(gen_copy)
   BusNum GenID       GenMW     GenMVR
0       1     1  232.391691 -16.549389
1       2     1    0.000000  43.555957
2       3     1  100.000000  25.074852
3       6     1  100.000000  12.729700
4       8     1    0.000000  17.623067

# Use helper function to both command the generators and to confirm that
# PowerWorld respected the command. This is incredibly useful because
# if you directly use ChangeParametersMultipleElements, PowerWorld may
# unexpectedly not update the parameter you tried to change! If the 
# following does not raise an exception, we're in good shape (it doesn't)!
>>> saw.change_and_confirm_params_multiple_element(ObjectType='gen', command_df=gen_copy.drop('GenMVR', axis=1))

# Run the power flow and observe the change in generation at the slack
# bus (bus 1).
>>> saw.SolvePowerFlow()
>>> print(saw.get_power_flow_results('gen'))
   BusNum GenID       GenMW     GenMVR
0       1     1   62.128144  14.986289
1       2     1    0.000000  10.385347
2       3     1  100.000000   0.000000
3       6     1  100.000000  -3.893420
4       8     1    0.000000  17.399502

# What if we try to change generator voltage set points? Start by getting
# a DataFrame with the current settings. Remember to always access the
# key fields so that when we want to update parameters later PowerWorld
# knows how to find the generators.
>>> gen_v = saw.GetParametersMultipleElement('gen', key_fields + ['GenRegPUVolt'])
>>> print(gen_v)
   BusNum GenID  GenRegPUVolt
0       1     1      1.060000
1       2     1      1.045000
2       3     1      1.010001
3       6     1      1.070001
4       8     1      1.090003
>>> gen_v['GenRegPUVolt'] = 1.0
>>> print(gen_v)
   BusNum GenID  GenRegPUVolt
0       1     1           1.0
1       2     1           1.0
2       3     1           1.0
3       6     1           1.0
4       8     1           1.0
>>> saw.change_and_confirm_params_multiple_element('gen', gen_v)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "C:\Users\blthayer\git\gym-powerworld\venv\lib\site-packages\esa\saw.py", line 201, in change_and_confirm_params_multiple_element
    raise CommandNotRespectedError(m)
esa.saw.CommandNotRespectedError: After calling ChangeParametersMultipleElement, not all parameters were actually changed within PowerWorld. Try again with a different parameter (e.g. use GenVoltSet instead of GenRegPUVolt).

# So, PowerWorld didn't respect that command, but we've been saved from
# future confusion by the helper function.

# Let's call the LoadState SimAuto function.
>>> saw.LoadState()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "C:\Users\blthayer\git\gym-powerworld\venv\lib\site-packages\esa\saw.py", line 635, in LoadState
    raise NotImplementedError(NIE_MSG)
NotImplementedError: This method is either not complete or untested. We appreciate contributions, so if you would like to complete and test this method, please read contributing.md. If there is commented out code, you can uncomment it and re-install esa from source at your own risk.

# This behavior is expected - if we have not implemented/tested a SimAuto
# function, it will raise a NotImplementedError.

# Finally, make sure to clean up after yourself so you don't have COM
# objects hanging around.
saw.exit()
```

## Pre-requisites
- Microsoft Windows 10 Operating System (PowerWorld is Windows only).
- PowerWorld Simulator with SimAuto add-on installed.
- [Git Large File Storage (LFS)](https://git-lfs.github.com/)
(**OPTIONAL**: required to download case files and run tests). After
installing Git LFS, simply change directories to this repository, and
run `git lfs install`. You will likely need to run a `git pull` or
`git lfs pull` after installing and setting up Git LFS. After initial
setup, you shouldn't need to do anything else with Git LFS.
- Python >=3.5.

### Notes on Python versions
The authors of ESA have tested with Python 3.5,
3.6, 3.7, and 3.8. Many users may find it easiest to use Anaconda,
but this is not recommended for users familiar with using Pip and/or
virtual environments directly (or via PyCharm), as Anaconda provides an
unnecessarily bloated installation.

#### Important Notes for PyCharm + Python 3.8
If you use PyCharm to automatically create virtual environments for you,
there's a little extra work to do to get everything working for Python
3.8. Start up a terminal *inside* PyCharm (click on the `Terminal` 
button which defaults to the lower left area). In the terminal, run:
`python -m pip install -U --force-reinstall pip`. Note you may need to
run this command twice - mine failed the first time.

## Installation
This section covers installation via Pip, installation from source, and
some __important__ post installation steps that **must** be taken.

### Installation with Pip (easiest)
Use the Python package manager [pip](https://pip.pypa.io/en/stable/) to
install ESA:

```bash
pip install esa
```

### Installation from Source
If you want to make modifications to ESA for your own purposes, you'll
likely want to clone the Git repository and install from source. 
Fortunately, this is quite easy. The following directions will assume
that your project is at `C:\Users\myuser\git\myproject` and that your
virtual environment is at `C:\Users\myuser\git\myproject\venv`. If 
you're new to virtual environments, Python provides a nice
[tutorial](https://docs.python.org/3/tutorial/venv.html).

Start by cloning ESA into `C:\Users\myuser\git\ESA`. This can be 
accomplished in a variety of ways, but perhaps the simplest is by using
Git Bash:
```
cd ~/git
git clone https://github.com/mzy2240/ESA.git
```

After the cloning has completed, close Git Bash and open up a command
prompt. Run the following:

```cmd
cd C:\Users\myuser\git\myproject
venv\Scripts\activate.bat
```

Your prompt should change to be prefixed by `(venv)` indicating that 
your virtual environment has been activated. Now, perform the following:

```cmd
cd ../ESA
python setup.py install
```

### Post-Installation (optional)
You need to run a post-installation script related to a
pre-requisite Python package, [pywin32](https://github.com/mhammond/pywin32).
As per pywin32's directions, you'll need to run the following with
an __elevated__ (administrator) command prompt after navigating to your
virtual environment's directory:
```cmd
Scripts\activate.bat
python Scripts/pywin32_postinstall.py -install
```
(this `Scripts` directory can be found within your virtual environment
where your Python packages are installed. If you followed along in the
"Installation from Source" example, this `Scripts` directory would be
found at `C:\Users\myuser\git\myproject\venv`.)

## License
[MIT](https://choosealicense.com/licenses/mit/)

## Contributing
We welcome contributions! Please read out `contributing.md`.

## Common Issues
This section will describes some (maybe) common issues and their solutions.

### Installation/Virtual Environment Issues
If you have issues installing ESA and/or its dependencies, you may need
to do some manual work installing pre-requisites in your virtual 
environment. Hopefully following these simple directions will help fix
most issues.

1. Start fresh! Completely remove your virtual environment and recreate
it. [PyCharm makes this pretty easy](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html),
or you can do so manually using [Python's guide](https://docs.python.org/3/tutorial/venv.html). 
The remaining directions will assume you're typing commands into your
**activated** virtual envrionment.
2. Reinstall pip: `python -m pip install --upgrade --force-reinstall pip`.
We're intentionally using `python -m pip` instead of just `pip` to avoid
possible path issues. Note that you might need to run this command 
twice (the first may fail for some unknown reason).
3. Check out ESA's [setup.py](https://github.com/mzy2240/ESA/blob/master/setup.py)
file and look for `install_requires`. It'll look something like
`['pandas', 'numpy', 'pywin32', 'pypiwin32']`.
4. Using what we found under `install_requires`, install ESA's
dependencies manually. To avoid dependencies on a compiler, we'll get
binary distributions only:
`python -m pip install --upgrade --only-binary :all: pandas numpy pywin32 pypiwin32`
    - If this command fails, you may need to pick and choose which dependencies
    you grab binary distributions for, and which you get other types of
    distributions for. Here's the [Python documentation](https://pip.pypa.io/en/stable/reference/pip_install/).
    If we only want to get binary distributions for `pandas` and `numpy`,
    we'd modify the previous command to instead read like so:
    `python -m pip install --upgrade --only-binary pandas,numpy pandas numpy pywin32 pypiwin32`
5. After you've installed ESA's dependencies, it's time to install ESA:
`python -m pip install esa`

### Errors/Issues Initializing a SAW Instance
This section will cover some common issues when attempting to initialize
a SAW instance. The first thing to check is that your arguments are 
correct - you can find the documentation [here](file:///C:/Users/brand/git/ESA/docs/html/esa.html#esa.saw.SAW).

#### esa.saw.PowerWorldError: OpenCase: Errors have occurred
You may see an error stack trace that looks something like the
following:
```python
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "C:\Users\brand\git\ESA\esa\saw.py", line 111, in __init__
    self.OpenCase(FileName=FileName)
  File "C:\Users\brand\git\ESA\esa\saw.py", line 680, in OpenCase
    return self._call_simauto('OpenCase', self.pwb_file_path)
  File "C:\Users\brand\git\ESA\esa\saw.py", line 1101, in _call_simauto
    raise PowerWorldError(output[0])
esa.saw.PowerWorldError: OpenCase: Errors have occurred
```

Often, this is due to a bad path specification. Ensure you're providing
a **full** file path, including the file extension (.pwb), and that the
file exists at the exact path you specified.

#### TypeError: This COM object can not automate the makepy process - please run makepy manually for this object
If you see an error like the above, try initializing your SAW object
again but set `early_bind=False`. While we're unsure of the root cause
of this issue, it seems to be related to the fact that `early_bind=True`
preemptively creates some Python files related to the SimAuto COM API.

## Examples and Snippets

### Add Lines to Model
This example shows how to add transmission lines to a model. You can
find the case and .csv file referenced in the `tests` directory. This
example will assume you execute this code within the repository at the
top level (this level).

```python
from esa import SAW
import pandas as pd
import os

# File with lines to add.
line_df = pd.read_csv(os.path.join('tests', 'data', 'CandidateLines.csv'))

# Fire up a SAW object. Ensure CreateIfNotFound is True so that we can
# use ChangeParametersMultipleElement to create new objects.
this_dir = os.path.dirname(os.path.abspath(__file__))
saw = SAW(FileName=os.path.join(this_dir, 'tests', 'cases', 'tx2000',
                                'tx2000_base.PWB'),
          CreateIfNotFound=True, early_bind=True)

# Rename columns to match PowerWorld variables.
line_df.rename(
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
line_df['LineAMVA:1'] = 0.0
line_df['LineAMVA:2'] = 0.0

# Move into edit mode so we can add lines.
saw.RunScriptCommand("EnterMode(EDIT);")

# Create the lines.
saw.change_and_confirm_params_multiple_element(
    ObjectType='branch', command_df=line_df)
```
