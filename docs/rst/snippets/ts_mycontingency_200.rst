This example illustrates the procedure to perform transient stability(TS) analysis
and obtain the TS result. To retrieve the result, the most convenient way is to create
a plot object and connect the object/fields pairs to it, then you will be able to query it
using the :code:`TSGetCongencyResults` function.

.. code:: python

    CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\il200\ACTIVSg200.pwb"

Load the case first and then solve a PF (optional):

.. code:: python

    >>> from esa import SAW
    >>> saw = SAW(CASE_PATH)
    >>> saw.SolvePowerFlow()

Then perform TS analysis (make sure you already have a desired plot object)

.. code:: python

    >>> t1 = 0.0
    >>> t2 = 15.0
    >>> stepsize = 0.01

        # Solve.
    >>> cmd = 'TSSolve("{}",[{},{},{},NO])'.format(
            self.ctg_name, t1, t2, stepsize
        )
    >>> saw.RunScriptCommand(cmd)

Once it is done, you could retrieve (and visualize) the results:

.. code:: python

    >>> objFieldList = ['Plot ''Area_Avg Bus Hz''']  # "Area_Avg Bus Hz" is the plot name
    >>> result = sa.TSGetContingencyResults("My Transient Contingency", objFieldList, 0, 12)  # "My Transient Contingency" is the contingency name
    >>> df = result[1]  #result[0] is meta data
    >>> df.columns = ['Time (s)', 'Area_Avg Bus Hz']
    >>> df.plot(x='Time (s)', y='Area_Avg Bus Hz')
.. image:: https://github.com/mzy2240/ESA/raw/develop/docs/rst/snippets/ts_result.png
    :width: 100 %
    :align: center

The whole process, including setting up plots and creating contingencies, could be fully
automated, but it might be easier for most users to pre-define the plots and contingencies
in the case and then load the case using ESA. GetParametersMultipleElement cannot be used
here to retrieve the TS datapoints (which is a very rare situation).

