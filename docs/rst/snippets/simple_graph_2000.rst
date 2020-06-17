This example shows how to easily transform a grid model into a graph
supported by `NetworkX <https://networkx.github.io/>`__. NetworkX is a
popular Python package for analyzing graph structure, building network
models and designing new network algorithms. You'll first need to
install NetworkX into your virtual environment (which should be
activated!), which is most easily done by:

.. code:: bat

    python -m pip install networkx

Before following along with the example, define the ``CASE_PATH``
constant (the file path to a PowerWorld ``.pwb`` case file) like so,
adapting the path to your system:

.. code:: python

    CASE_PATH = r"C:\Users\myuser\git\ESA\tests\cases\tx2000\tx2000_base_pws_version_21.pwb"

On to the example!

Perform imports, initialize a ``SAW`` instance:

.. code:: python

    >>> from esa import SAW
    >>> import pandas as pd
    >>> import networkx as nx
    >>> saw = SAW(CASE_PATH, early_bind=True)

Get a DataFrame with all branches (lines, transformers, etc.):

.. code:: python

    >>> kf = saw.get_key_field_list('branch')
    >>> kf
    ['BusNum', 'BusNum:1', 'LineCircuit']
    >>> branch_df = saw.GetParametersMultipleElement('branch', kf)
    >>> branch_df
          BusNum  BusNum:1 LineCircuit
    0       1001      1064           1
    1       1001      1064           2
    2       1001      1071           1
    3       1001      1071           2
    4       1002      1007           1
    ...      ...       ...         ...
    3199    8157      5124           1
    3200    8157      8156           1
    3201    8158      8030           1
    3202    8159      8158           1
    3203    8160      8159           1
    <BLANKLINE>
    [3204 rows x 3 columns]

To learn more about variables such as ``LineCircuit``, see
:ref:`powerworld-variables`.

Create the graph from the DataFrame. Yes, it is this simple. Use
``Graph`` instead of ``MultiGraph`` if there are no parallel branches.

.. code:: python

    >>> graph = nx.from_pandas_edgelist(branch_df, "BusNum", "BusNum:1", create_using=nx.MultiGraph)
    >>> graph.number_of_nodes()
    2000
    >>> graph.number_of_edges()
    3204

Clean up:

.. code:: python

    saw.exit()
