Add Lines to Model
~~~~~~~~~~~~~~~~~~

This example shows how to add transmission lines to a model. You can
find the case and .csv file referenced in the ``tests`` directory. This
example will assume you execute this code within the repository at the
top level (this level).

.. code:: python

   from esa import SAW
   import pandas as pd
   import os

   # File with lines to add.
   line_df = pd.read_csv(os.path.join('tests', 'data', 'CandidateLines.csv'))

   # Fire up a SAW object. Ensure CreateIfNotFound is True so that we can
   # use ChangeParametersMultipleElement to create new objects.
   this_dir = os.path.dirname(os.path.abspath(__file__))
   saw = SAW(FileName=os.path.join(this_dir, 'tests', 'cases', 'tx2000',
                                   'tx2000_base.PWB'),
             CreateIfNotFound=True, early_bind=True)

   # Rename columns to match PowerWorld variables.
   line_df.rename(
       # TODO: Will need to update this renaming once
       #   https://github.com/mzy2240/ESA/issues/1#issue-525219427
       #   is addressed.
       columns={
           'From Number': 'BusNum',
           'To Number': 'BusNum:1',
           'Ckt': 'LineCircuit',
           'R': 'LineR',
           'X': 'LineX',
           'B': 'LineC',
           'Lim MVA A': 'LineAMVA'
       },
       inplace=True)

   # We're required to set other limits too.
   line_df['LineAMVA:1'] = 0.0
   line_df['LineAMVA:2'] = 0.0

   # Move into edit mode so we can add lines.
   saw.RunScriptCommand("EnterMode(EDIT);")

   # Create the lines.
   saw.change_and_confirm_params_multiple_element(
       ObjectType='branch', command_df=line_df)

   # Close the object so we don't get COM objects hanging around.
   saw.exit()

From Grid Model to Graph
~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to easily transform a grid model into a graph
supported by NetworkX. NetworkX is a popular Python package for
analyzing graph structure, building network models and designing new
network algorithms.

.. code:: python

   from esa import SAW
   import pandas as pd
   import os

   # Load the case
   this_dir = os.path.dirname(os.path.abspath(__file__))
   saw = SAW(FileName=os.path.join(this_dir, 'tests', 'cases', 'tx2000',
                                   'tx2000_base.PWB'),
             early_bind=True)

   # Get the branch information in the dataframe format.
   params = saw.get_key_field_list('branch')
   Branch = saw.GetParametersMultipleElement(ObjectType='branch', ParamList=params)

   # Create the graph from the branch dataframe. That's it!
   # Use Graph instead of MultiGraph if there is no parallel line in your case.
   import networkx as nx
   g = nx.from_pandas_edgelist(Branch, "BusNum", "BusNum:1",create_using=nx.MultiGraph)

   # Close the object so we don't get COM objects hanging around.
   saw.exit()
