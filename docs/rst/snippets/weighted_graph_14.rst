This example shows how one can create a weighted graph using branch
impedance values as weights. You'll need to have the NetworkX Python
package installed into your virtual environment in order to execute
this example on your machine (``python -m pip install networkx``).

Before following along with the example, define the ``CASE_PATH``
constant like so, adapting the path to your system:

.. code:: python

    CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\ieee_14\IEEE 14 bus.pwb"

Onward!

Imports and initialization:

.. code:: python

    >>> import networkx as nx
    >>> from esa import SAW
    >>> import re
    >>> import os
    >>> saw = SAW(CASE_PATH, early_bind=True)
    >>> g = nx.Graph()

Save YBus matrix to file:

.. code:: python

    >>> ybus_file = CASE_PATH.replace('pwb', 'mat')
    >>> cmd = 'SaveYbusInMatlabFormat("{}", NO)'.format(ybus_file)
    >>> saw.RunScriptCommand(cmd)

Read YBus matrix file into memory. The first two lines are skipped via
the ``readline`` method because they aren't needed.

.. code:: python

    >>> with open(ybus_file, 'r') as f:
    ...     f.readline()
    ...     f.readline()
    ...     mat_str = f.read()
    ...
    'j = sqrt(-1);\n'
    'Ybus = sparse(14);\n'

We're done with the file itself now. Remove it:

.. code:: python

    >>> os.remove(ybus_file)

Remove all white space, split by semicolons, and define a couple regular
expressions (ie --> integer expression, fe --> float expression):

.. code:: python

    >>> mat_str = re.sub(r'\s', '', mat_str)
    >>> lines = re.split(';', mat_str)
    >>> ie = r'[0-9]+'
    >>> fe = r'-*[0-9]+\.[0-9]+'
    >>> exp = re.compile(r'(?:Ybus\()({ie}),({ie})(?:\)=)({fe})(?:\+j\*)(?:\()({fe})'.format(ie=ie, fe=fe))

Loop over the lines from the file and build up the graph. Ignore
diagonal Y bus matrix entries and buses which are not connected
(have 0 admittance between them).

.. code:: python

    >>> for line in lines:
    ...     match = exp.match(line)
    ...     if match is None:
    ...         continue
    ...     idx1, idx2, real, imag = match.groups()
    ...     if idx1 == idx2:
    ...         continue
    ...     neg_admittance = float(real) + 1j * float(imag)
    ...     try:
    ...         impedance = -1 / neg_admittance
    ...     except ZeroDivisionError:
    ...         continue
    ...     g.add_edge(int(idx1), int(idx2), r=impedance.real, x=impedance.imag)
    ...

Explore some graph properties to ensure it worked:

.. code:: python

    >>> g.number_of_nodes()
    14
    >>> g.number_of_edges()
    20
    >>> data_1_2 = g.get_edge_data(1, 2)
    >>> data_1_2['r']
    0.01937987032338931
    >>> data_1_2['x']
    0.05917003035204804

As always, clean up when done:

.. code:: python

    >>> saw.exit()
