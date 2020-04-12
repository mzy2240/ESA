This examples shows how to make various of plots using Matplotlib. Matplotlib is a comprehensive library for creating static, animated, and interactive visualizations in Python. You'll first need to install Matplotlib into your virtual environment (which should be activated!), which is most easily done by.
  
.. code:: bat

    python -m pip install -U matplotlib
 
Before following along with the example, define the CASE_PATH constant like so, adapting the path to your system.

.. code:: python

  CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_base.PWB"
  
Now let's get started!

Perform imports, initialize a ``SAW`` instance.

.. code:: python

    >>> from esa import SAW
    >>> import matplotlib.pyplot as plt
 
Initialize SAW instance using 2000 bus test case:

.. code:: python

  >>> saw = SAW(FileName=CASE_PATH)
Solve the power flow:

.. code:: python

  >>> saw.SolvePowerFlow()
 
Let's change line loading percentage. But first, we need to know which fields PowerWorld needs in order to identify branches. These fields are known as key fields.

.. code:: python

  >>> gen_key_fields = saw.get_key_field_list('Branch')
  >>> gen_key_fields
  ['BusNum', 'BusNum:1', 'LineCircuit']
  
Get line loading percentage at all buses via SimAuto function:

.. code:: python

  >>> params = gen_key_fields + ['LineMaxPercent']
  >>> branch_data = saw.GetParametersMultipleElement(ObjectType='Branch', ParamList=params)
  >>> branch_data
        BusNum  BusNum:1 LineCircuit  LineMaxPercent
  0       1001      1064           1       30.873056
  1       1001      1064           2       30.873056
  2       1001      1071           1       35.950521
  3       1001      1071           2       35.950521
  4       1002      1007           1        5.299143

Then Let's start to plot with Matplotlib!

.. code:: python

  >>> branch_data.plot(kind='scatter',x='BusNum',y='LineMaxPercent', color='blue')
  >>> plt.show()
  
