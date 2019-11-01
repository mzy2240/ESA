# Contributing to Easy SimAuto
We welcome contributions to ESA! If you find a bug, please
file an issue on [Github](https://github.com/mzy2240/ESA/issues).

The primary purpose of this document is to describe what's required to 
make a contribution to the source code.

## Fork and Pull Request
The simplest method to contribute is to first fork the repository, make
changes, and then submit a pull request.

## Starting Out
While this document attempts to be comprehensive, the best way to get 
a feel for the project is to peruse the source code. Specifically, take
a look at esa/saw.py and tests/test_saw.py.

## Conventions and Style
The following sections describe expected conventions and style for 
contributing to ESA.
### PEP-8
In general, ESA follows [PEP-8](https://www.python.org/dev/peps/pep-0008/).
Please read the PEP in full if you have not already. The good news is
you don't need to memorize everything - modern IDEs like PyCharm make 
following PEP-8 very easy.

The only time one should deviate from the PEP-8 is with regard to
function naming and function input variable naming. Functions and their
inputs should be named to match [PowerWorld's documentation](https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7C_____1).

Example:
```python
def ChangeParametersMultipleElement(self, ObjectType: str, ParamList: list,
                                    ValueList: list):
...
``` 

Notice the function and input variables exactly match PowerWorld. 
However, internal variables should conform to PEP-8. E.g., following the
previous example above you may do the following:
```python
# Cast ObjectType to lower case so it matches dictionary keys. 
object_type = ObjectType.lower()
```

ESA follows the convention that attributes/methods/etc. which start 
with an underscore are private.

### Docstrings and Type Hinting
Every function should include a detailed docstring that describes what 
the function does, and also describes all parameters and return values
in detail. Additionally, the docstring should provide a direct link to
applicable PowerWorld documentation. It's also generally useful to 
document what exceptions the function/method may raise.

Docstrings should use reStructuredText (rst) format, as described in
[PEP-287](https://www.python.org/dev/peps/pep-0287/). A useful cheat
sheet can be found [here](https://thomas-cokelaer.info/tutorials/sphinx/rest_syntax.html). 

Additionally, functions should utilize type hinting to help users and 
developers know explicitly what types of objects they'll be dealing 
with.

Here's an example of both type hinting and a good docstring:
```python
def OpenCase(self, FileName: Union[str, None] = None) -> None:
    """Load PowerWorld case into the automation server.

    :param FileName: Full path to the case file to be loaded. If
        None, this method will attempt to use the last FileName
        used to open a case.

    :raises TypeError: if FileName is None, and OpenCase has never
        been called before.

    `PowerWorld documentation
    <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/OpenCase_Function.htm>`_
    """
```
 
### Inputs and Outputs
Where applicable, the preferred return types are `pandas.DataFrame` and
`pandas.Series`. A return of `None` should be used to indicate that a 
function operated but has nothing to return.

## Unit Testing
Any and all functions, methods, classes, etc. should be tested. ESA 
uses the built-in [unittest](https://docs.python.org/3/library/unittest.html)
module, as well as [unittest.mock](https://docs.python.org/3/library/unittest.mock.html).
 
The objective is to have 100% testing coverage. Tools such as
[Coverage.py](https://coverage.readthedocs.io/en/latest/) can be used
to assess test coverage.
 
Please read the docstring in test_saw.py - it has very important 
information related to avoiding state conflicts that may arise 
between tests (in an ideal world, this wouldn't be a problem, but we 
just don't live in an ideal world :)).

Note that due to the nature of this project, many tests aren't truly
"unit" tests in that they actually call SimAuto. 

## Using the Helper Methods
The SAW class has a variety of private helper methods, prefixed with
and underscore. A developer should use these liberally, as they're 
designed to make development easy. 

### Details for the SAW class
Never call SimAuto directly - always use the `_call_simauto` helper.

Any and all DataFrames/Series that are created via output from
PowerWorld should be passed through the `_clean_df_or_series` method.