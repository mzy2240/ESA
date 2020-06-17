ESA Overview
============
Please see :ref:`about-simauto` for a description of SimAuto as well as
for links to PowerWorld's documentation.

When using ESA, you'll likely only use a single class: ``SAW``, which is
short for SimAuto Wrapper. After you've installed the esa package
(refer to :ref:`installation`), you'll import the ``SAW`` class like so:

.. code-block:: python

    from esa import SAW
    saw = SAW('<full path to case file>')

All methods of the SAW class are fully documented. Additionally, all
inputs and outputs use type hinting so that your interactive development
environment (IDE, such as PyCharm) will automatically highlight
incorrect input types.

Naming Conventions
------------------

When browsing the documentation, you'll notice that naming
conventions are mixed, with some being CamelCase and others being
lower_case_with_underscores. We use the CamelCase convention to indicate
that we're more or less directly calling a
`PowerWorld SimAuto Function <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server_Functions.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____3>`__
(e.g. ``SAW.ChangeParametersMultipleElement``) or a
`PowerWorld Script Command <https://www.powerworld.com/WebHelp/Content/MainDocumentation_HTML/Auxiliary_Files.htm>`__
(e.g. ``SAW.SolvePowerFlow``). CamelCase is also used when describing
variables which are more or less directly passed into a SimAuto
function (e.g. ``ObjectType``). The lower_case_with_underscores
convention is used in function naming to indicate that a function is a
higher-level function which may call multiple PowerWorld functions
and/or not return everything from PowerWorld. Some examples of these
functions are
``SAW.change_and_confirm_params_multiple_element``,
``SAW.change_parameters_multiple_element_df``,
``SAW.get_key_fields_for_object_type``, and
``SAW.get_power_flow_results``. In general, it is recommended to use
these higher level functions where possible. Note these show up toward
the bottom of the API documentation since methods which start with
upper case letters come before methods that start with lower case
letters. Variables use the lower_case_with_underscores convention any
time the variable is not a direct SimAuto input.

Functions/Methods
-----------------

SimAuto Functions
^^^^^^^^^^^^^^^^^

The ``SAW`` class has every SimAuto function implemented. I.e., you
can call a ``SAW`` method corresponding to every documented `SimAuto
function <https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server_Functions.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7CAutomation%2520Server%2520Functions%7C_____3>`__.


High-Level/Helper Functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^

As mentioned in the `Naming Conventions`_ section, we recommend you use
the high level helper functions (which use the
lower_case_with_underscores convention) where possible.

.. _runscriptcommand:

RunScriptCommand
^^^^^^^^^^^^^^^^

For PowerWorld functionality not directly covered by the SimAuto
functions, you'll want to use ``RunScriptCommand``. Note that we
already have some methods defined which are script commands, e.g.
``SAW.SolvePowerFlow``. So, you may want to search for the function
you want before directly using ``RunScriptCommand``.

It's worth noting that ``RunScriptCommand`` will directly return results
from PowerWorld, which will come back with all sorts of nasty data types
(e.g. strings with leading and trailing whitespace). Your best course of
action is to create a DataFrame/Series from the output, and use the
``clean_df_or_series`` method afterwards.

Documentation from PowerWorld on available script commands can be found
`here
<https://github.com/mzy2240/ESA/blob/master/docs/Auxiliary%20File%20Format.pdf>`__.

clean_df_or_series
^^^^^^^^^^^^^^^^^^

This helper function will do automatic type translation for you based
on known PowerWorld data types. If you're dealing with direct outputs
from PowerWorld (e.g. from using ``RunScriptCommand``), this method
will save you all sorts of trouble. Read the method's API documentation
thoroughly before using.

Data Types
----------

All method input and output data types are documented in the API
documentation. Where possible, ``SAW`` methods return Pandas DataFrames
or Pandas Series. If there's nothing to return, ``None`` will be
returned. ESA makes extensive use of type hinting so that your IDE can
automatically highlight issues related to data types.

.. _powerworld-variables:

PowerWorld Variables
--------------------

At present, ESA uses PowerWorld "Variable Names" as opposed to
PowerWorld "Concise Variable Names." A listing of these variables can be
found `here
<https://github.com/mzy2240/ESA/blob/master/docs/power_world_object_fields.xlsx>`__.
It would seem that PowerWorld is moving toward "Concise Variable Names,"
and in a future update ESA may support these (see `this issue
<https://github.com/mzy2240/ESA/issues/1#issue-525219427>`__).

Testing Coverage
----------------

The ESA team strives to write good tests with 100% coverage. The table
below provides the latest test coverage data for ESA.

.. include:: coverage.rst

Contributing
------------

We welcome contributions to ESA - please give
`contributing.md <https://github.com/mzy2240/ESA/blob/master/contributing.md>`__
a read.