If you want to follow along, you'll first need to define your own
``CASE_PATH`` constant, like so (adapt the path for your system):

.. code:: python

    CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\ieee_14\IEEE 14 bus.pwb"

Then, import the SimAuto wrapper (SAW) class and initialize an instance:

.. code:: python

    >>> from esa import SAW
    >>> saw = SAW(CASE_PATH)

Retrieve key fields for loads:

.. code:: python

    >>> kf = saw.get_key_field_list('load')
    >>> kf
    ['BusNum', 'LoadID']

Pull load data including active and reactive power demand:

.. code:: python

    >>> load_frame = saw.GetParametersMultipleElement('load', kf + ['LoadSMW', 'LoadSMVR'])
    >>> load_frame
        BusNum LoadID    LoadSMW   LoadSMVR
    0        2      1  21.699999  12.700000
    1        3      1  94.199997  19.000000
    2        4      1  47.799999  -3.900000
    3        5      1   7.600000   1.600000
    4        6      1  11.200000   7.500000
    5        9      1  29.499999  16.599999
    6       10      1   9.000000   5.800000
    7       11      1   3.500000   1.800000
    8       12      1   6.100000   1.600000
    9       13      1  13.500001   5.800000
    10      14      1  14.900000   5.000000

Uniformly increase loading by 50% and solve the power flow:

.. code:: python

    >>> load_frame[['LoadSMW', 'LoadSMVR']] *= 1.5
    >>> saw.change_parameters_multiple_element_df('load', load_frame)
    >>> saw.SolvePowerFlow()

Clean up when done:

.. code:: python

    >>> saw.exit()

Easy, isn't it?