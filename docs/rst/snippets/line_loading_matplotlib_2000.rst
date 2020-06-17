This examples shows how to make a histogram of percent line loading in
a power system model using SimAuto, ESA, and Matplotlib.

`Matplotlib <https://matplotlib.org/>`__ is a "comprehensive library for
creating static, animated, and interactive visualizations in Python."
You'll first need to install Matplotlib into your virtual environment
(which should be activated!), which is most easily done by:

.. code:: bat

    python -m pip install -U matplotlib

Before following along with the example, define the CASE_PATH constant
(the file path to a PowerWorld ``.pwb`` case file) like so, adapting the
path to your system.

.. code:: python

  CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_base_pws_version_21.pwb"

Now let's get started!

Perform imports, initialize a ``SAW`` instance:

.. code:: python

    >>> from esa import SAW
    >>> import matplotlib.pyplot as plt

Initialize SAW instance using 2000 bus test case:

.. code:: python

    >>> saw = SAW(FileName=CASE_PATH)

Solve the power flow:

.. code:: python

    >>> saw.SolvePowerFlow()

Let's obtain line loading percentages. But first, we need to know which
fields PowerWorld needs in order to identify branches. These fields are
known as key fields.

.. code:: python

    >>> branch_key_fields = saw.get_key_field_list('Branch')
    >>> branch_key_fields
    ['BusNum', 'BusNum:1', 'LineCircuit']

Get line loading percentage at all buses via SimAuto function:

.. code:: python

    >>> params = branch_key_fields + ['LinePercent']
    >>> branch_data = saw.GetParametersMultipleElement(ObjectType='Branch', ParamList=params)
    >>> branch_data
          BusNum  BusNum:1 LineCircuit  LinePercent
    0       1001      1064           1    30.879348
    1       1001      1064           2    30.879348
    2       1001      1071           1    35.731801
    3       1001      1071           2    35.731801
    4       1002      1007           1     5.342946
    ...      ...       ...         ...          ...
    3199    8157      5124           1    36.371236
    3200    8157      8156           1    46.769588
    3201    8158      8030           1    25.982494
    3202    8159      8158           1    43.641971
    3203    8160      8159           1    57.452701
    <BLANKLINE>
    [3204 rows x 4 columns]

To learn more about variables such as ``LinePercent``, see
:ref:`powerworld-variables`.

Then let's start to plot with Matplotlib!

.. code:: python

    >>> axes = branch_data.plot(kind='hist', y='LinePercent')
    >>> axes.set_xlabel('Line Percent Loading')
    Text(0.5, 0, 'Line Percent Loading')
    >>> axes.set_ylabel('Number of Lines')
    Text(0, 0.5, 'Number of Lines')
    >>> axes.set_title('Histogram of Line Loading')
    Text(0.5, 1.0, 'Histogram of Line Loading')
    >>> plt.show(block=False)

The results should look like:

.. image:: https://github.com/mzy2240/ESA/raw/develop/docs/rst/snippets/line_loading_histogram.png
    :width: 100 %
    :align: center
