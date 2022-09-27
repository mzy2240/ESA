This example shows how to do fast contingency analysis (N-1 & N-2) using
ESA. The fast contingency analysis is a slightly improved implementation
of `this paper <https://ieeexplore.ieee.org/document/7390321>`__. It is generally
much faster than the built-in CA that simulator provides (which, by the way,
could also be invoked from ESA).

The initialization procedure is the same as others.

.. code:: python

    >>> CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_base_pws_version_21.pwb"
    >>> from esa import SAW
    >>> saw = SAW(CASE_PATH)

Make sure your case already has a valid operating states. If not, run power flow first:

.. code:: python

    >>> saw.SolvePowerFlow()

Then let's run N-1 first.

.. code:: python

    >>> saw.run_contingency_analysis('N-1')
    The size of N-1 islanding set is 451.0
    Fast N-1 analysis was performed, 156 dangerous N-1 contigencies were found, 138 lines are violated
    Grid is not N-1 secure. Invoke n1_protect function to automatically increasing limits through lines.
    Out: (False, array([0, 0, 0, ..., 1, 0, 0]), None)

So the test system (TX2000) is not N-1 secured. In this case, when running N-2,
the line limit will be automatically adjusted to ensure no N-1 violations. Based on
the use case you have, you could adjust the line limits manually as well.

.. code:: python

    >>> saw.run_contingency_analysis('N-2')
.. image:: https://github.com/mzy2240/ESA/raw/develop/docs/rst/snippets/n-2.gif
    :width: 100 %
    :align: center

You could also validate the fast CA result with the built-in CA result by
simply set the argument `validate=True` when calling `run_contingency_analysis` function.
