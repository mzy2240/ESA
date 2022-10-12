This example shows how to perform the contingency analysis via PW's built-in capability. We assume
you already have the aux file that contains all the contingencies.

The initialization procedure is the same as others.

.. code:: python

    >>> CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_base_pws_version_21.pwb"
    >>> from esa import SAW
    >>> saw = SAW(CASE_PATH, CreateIfNotFound=True)
    >>> saw.pw_order = True

Make sure your case already has a valid operating states. If not, run power flow first:

.. code:: python

    >>> saw.SolvePowerFlow()

Then load the auxiliary file into Powerworld.

.. code:: python

    >>> filepath_aux = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_contingency_auxfile.aux"
    >>> saw.ProcessAuxFile(filepath_aux)
    
Run the powerworld script command to solve all the contingencies that are not set to skip in the
loaded auxiliary file.

.. code:: python

    >>> cmd_solve = 'CTGSolveAll({},{})'.format('NO','YES')
    >>> saw.RunScriptCommand(cmd_solve)

Use ESA to obtain the CA result

.. code:: python

    >>> result = saw.GetParametersMultipleElement('Contingency', ['CTGLabel', 'CTGSolved', 'CTGProc', 'CTGCustMonViol', 'CTGViol'])

The result is presented in a Pandas DataFrame.