Before running the example below, define a CASE_PATH variable like so
(adapt the path as needed for your system):

.. code:: python

    CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\ieee_14\IEEE 14 bus_pws_version_21.pwb"

On to the quick start!

Start by Importing the SimAuto Wrapper (SAW) class:

.. code:: python

   >>> from esa import SAW


Initialize SAW instance using 14 bus test case:

.. code:: python

   >>> saw = SAW(FileName=CASE_PATH)

Solve the power flow:

.. code:: python

   >>> saw.SolvePowerFlow()

Retrieve power flow results for buses. This will return a Pandas
DataFrame to make your life easier.

.. code:: python

    >>> bus_data = saw.get_power_flow_results('bus')
    >>> bus_data
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

Retrieve power flow results for generators:

.. code:: python

    >>> gen_data = saw.get_power_flow_results('gen')
    >>> gen_data
       BusNum GenID       GenMW     GenMVR
    0       1     1  232.391691 -16.549389
    1       2     1   40.000001  43.555957
    2       3     1    0.000000  25.074852
    3       6     1    0.000000  12.729700
    4       8     1    0.000000  17.623067


Let's change generator injections! But first, we need to know which
fields PowerWorld needs in order to identify generators. These fields
are known as key fields.

.. code:: python

    >>> gen_key_fields = saw.get_key_field_list('gen')
    >>> gen_key_fields
    ['BusNum', 'GenID']


Change generator active power injection at buses 3 and 8 via SimAuto
function:

.. code:: python

    >>> params = gen_key_fields + ['GenMW']
    >>> values = [[3, '1', 30], [8, '1', 50]]
    >>> saw.ChangeParametersMultipleElement(ObjectType='gen', ParamList=params, ValueList=values)


Did it work? Spoiler: it does!

.. code:: python

    >>> new_gen_data = saw.GetParametersMultipleElement(ObjectType='gen', ParamList=params)
    >>> new_gen_data
       BusNum GenID       GenMW
    0       1     1  232.391691
    1       2     1   40.000001
    2       3     1   30.000001
    3       6     1    0.000000
    4       8     1   50.000000


It would seem the generator active power injections have changed. Let's
re-run the power flow and see if bus voltages and angles change.
Spoiler: they do.

.. code:: python

    >>> saw.SolvePowerFlow()
    >>> new_bus_data = saw.get_power_flow_results('bus')
    >>> cols = ['BusPUVolt', 'BusAngle']
    >>> diff = bus_data[cols] - new_bus_data[cols]
    >>> diff
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


Wouldn't it be easier if we could change parameters with a DataFrame?
Wouldn't it be nice if we didn't have to manually check if our updates
were respected? You're in luck!

Create a copy of the ``gen_data`` DataFrame so that we can modify its
values and use it to update parameters in PowerWorld. Then, change the
generation for the generators at buses 2, 3, and 6.

.. code:: python

    >>> gen_copy = gen_data.copy(deep=True)
    >>> gen_copy.loc[gen_copy['BusNum'].isin([2, 3, 6]), 'GenMW'] = [0.0, 100.0, 100.0]
    >>> gen_copy
       BusNum GenID       GenMW     GenMVR
    0       1     1  232.391691 -16.549389
    1       2     1    0.000000  43.555957
    2       3     1  100.000000  25.074852
    3       6     1  100.000000  12.729700
    4       8     1    0.000000  17.623067


Use helper function ``change_and_confirm_params_multiple_element`` to
both command the generators and to confirm that PowerWorld respected the
command. This is incredibly useful because if you directly use
``ChangeParametersMultipleElements``, PowerWorld may unexpectedly not
update the parameter you tried to change! If the following does not
raise an exception, we're in good shape (it doesn't)!

.. code:: python

   >>> saw.change_and_confirm_params_multiple_element(ObjectType='gen', command_df=gen_copy.drop('GenMVR', axis=1))

Run the power flow and observe the change in generation at the slack
bus (bus 1):

.. code:: python

    >>> saw.SolvePowerFlow()
    >>> new_gen_data = saw.get_power_flow_results('gen')
    >>> new_gen_data
       BusNum GenID       GenMW     GenMVR
    0       1     1   62.128144  14.986289
    1       2     1    0.000000  10.385347
    2       3     1  100.000000   0.000000
    3       6     1  100.000000  -3.893420
    4       8     1    0.000000  17.399502


What if we try to change generator voltage set points? Start by getting
a DataFrame with the current settings. Remember to always access the
key fields so that when we want to update parameters later PowerWorld
knows how to find the generators.

.. code:: python

    >>> gen_v = saw.GetParametersMultipleElement('gen', gen_key_fields + ['GenRegPUVolt'])
    >>> gen_v
       BusNum GenID  GenRegPUVolt
    0       1     1      1.060000
    1       2     1      1.045000
    2       3     1      1.025425
    3       6     1      1.070000
    4       8     1      1.090000

Now, change all voltage set points to 1 per unit:

.. code:: python

    >>> gen_v['GenRegPUVolt'] = 1.0
    >>> gen_v
       BusNum GenID  GenRegPUVolt
    0       1     1           1.0
    1       2     1           1.0
    2       3     1           1.0
    3       6     1           1.0
    4       8     1           1.0

    >>> saw.change_and_confirm_params_multiple_element('gen', gen_v)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "C:\Users\myuser\git\ESA\esa\saw.py", line 199, in change_and_confirm_params_multiple_element
        raise CommandNotRespectedError(m)
    esa.saw.CommandNotRespectedError: After calling ChangeParametersMultipleElement, not all parameters were actually changed within PowerWorld. Try again with a different parameter (e.g. use GenVoltSet instead of GenRegPUVolt).

So, PowerWorld didn't respect that command, but we've been saved from
future confusion by the ``change_and_confirm_params_multiple_element``
helper function.

Let's call the LoadState SimAuto function:

.. code:: python

    >>> saw.LoadState()
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "C:\Users\myuser\git\ESA\esa\saw.py", line 967, in LoadState
        return self._call_simauto('LoadState')
      File "C:\Users\myuser\git\ESA\esa\saw.py", line 1227, in _call_simauto
        raise PowerWorldError(output[0])
    esa.saw.PowerWorldError: LoadState: State hasn't been previously stored.

This behavior is expected - it is not valid to call ``LoadState`` if
``SaveState`` has not yet been called. In the exception above, not that
a ``PowerWorldError`` is raised. This empowers users to handle
exceptions in whatever manner they see fit:

.. code:: python

    >>> from esa import PowerWorldError
    >>> try:
    ...     saw.LoadState()
    ... except PowerWorldError:
    ...     print("Oh my, we've encountered a PowerWorldError!")
    ...
    Oh my, we've encountered a PowerWorldError!


Finally, make sure to clean up after yourself so you don't have COM
objects hanging around.

.. code:: python

    >>> saw.exit()

After walking through this quick start, you should be ready to start
using ESA to improve your simulation and analysis work flows!
