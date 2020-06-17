This example shows how to add transmission lines to a model.

Before starting the example, please define the constants
``CASE_PATH`` (the file path to a PowerWorld ``.pwb`` case file) and
``CANDIDATE_LINES`` (file path to a ``.csv`` file with data related to
lines we'd like to add to the model) like the following, adapting paths
to your system. You can find the case and .csv file referenced in the
``tests`` directory of the ESA repository.

.. code:: python

    CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_base_pws_version_21.pwb"
    CANDIDATE_LINES = r"C:\Users\myuser\git\ESA\tests\data\CandidateLines.csv"

Import packages/classes and read the ``CANDIDATE_LINES`` .csv file.

.. code:: python

    >>> from esa import SAW
    >>> import pandas as pd
    >>> line_df = pd.read_csv(CANDIDATE_LINES)
    >>> line_df
       From Number  To Number  Ckt        R        X        B  Lim MVA A
    0         8155       5358    3  0.00037  0.00750  0.52342       2768
    1         8154       8135    3  0.00895  0.03991  0.00585        149
    2         8153       8108    3  0.01300  0.05400  0.02700        186
    3         8152       8160    3  0.00538  0.03751  0.00613        221
    4         8155       8057    3  0.00037  0.00750  0.52342       2768
    5         8154       8153    3  0.01300  0.05400  0.02700        186
    6         8155       8135    3  0.00538  0.03751  0.00613        221


Instantiate a ``SAW`` object. Set ``CreateIfNotFound`` to ``True`` so
that new lines can be added:

.. code:: python

    >>> saw=SAW(FileName=CASE_PATH, CreateIfNotFound=True, early_bind=True)

Rename columns in the ``line_df`` to match PowerWorld variables. We are
renaming variables from the "Concise Variable Name" convention to the
"Variable Name" convention. See `power_world_object_fields.xlsx
<https://github.com/mzy2240/ESA/blob/master/docs/power_world_object_fields.xlsx>`__.
Also note `this issue
<https://github.com/mzy2240/ESA/issues/1#issue-525219427>`__ is also
relevant. To learn more about PowerWorld variables, see
:ref:`powerworld-variables`.

.. code:: python

    >>> line_df.rename(
    ... columns={
    ... 'From Number': 'BusNum',
    ... 'To Number': 'BusNum:1',
    ... 'Ckt': 'LineCircuit',
    ... 'R': 'LineR',
    ... 'X': 'LineX',
    ... 'B': 'LineC',
    ... 'Lim MVA A': 'LineAMVA'
    ... },
    ... inplace=True)
    >>> line_df.columns
    Index(['BusNum', 'BusNum:1', 'LineCircuit', 'LineR', 'LineX', 'LineC',
           'LineAMVA'],
          dtype='object')

Secondary and tertiary limits are required fields that we must add
manually, since they were not present in the .csv file:

.. code:: python

    >>> line_df['LineAMVA:1'] = 0.0
    >>> line_df['LineAMVA:2'] = 0.0

Check to see if the first line is actually present. An error will
indicate that it's not.

.. code:: python

    >>> line_key_fields = saw.get_key_field_list('branch')
    >>> line_key_fields
    ['BusNum', 'BusNum:1', 'LineCircuit']
    >>> first_line = saw.GetParametersSingleElement('branch', line_key_fields, line_df.loc[0, line_key_fields].tolist())
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "C:\Users\myuser\git\ESA\esa\saw.py", line 693, in GetParametersSingleElement
        output = self._call_simauto('GetParametersSingleElement', ObjectType,
      File "C:\Users\myuser\git\ESA\esa\saw.py", line 1227, in _call_simauto
        raise PowerWorldError(output[0])
    esa.saw.PowerWorldError: GetParameters: Object not found

Enter edit mode to enable the creation of new devices, and use
the ``change_and_confirm_params_multiple_element`` helper function to
easily create the lines. This function will automagically confirm that
the lines will be created.

.. code:: python

    >>> saw.RunScriptCommand("EnterMode(EDIT);")
    >>> saw.change_and_confirm_params_multiple_element('branch', line_df)

Now, we should be able to find that first line without error:

.. code:: python

    >>> first_line = saw.GetParametersSingleElement('branch', line_key_fields, line_df.loc[0, line_key_fields].tolist())
    >>> first_line
    BusNum         8152
    BusNum:1       8160
    LineCircuit       3
    dtype: object

Always clean up:

.. code:: python

    >>> saw.exit()