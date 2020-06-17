From PowerWorld's `SimAuto page
<https://www.powerworld.com/products/simulator/add-ons-2/simauto>`__::

    "The Simulator Automation Server (SimAuto) allows you to take
    advantage of the power of automation to extend the functionality of
    PowerWorld Simulator to any external program that you write. Using
    Simulator Automation Server you can launch and control PowerWorld
    Simulator from within another application, enabling you to: access
    the data of a Simulator case, perform defined Simulator functions
    and other data manipulations, and send results back to your original
    application, to a Simulator auxiliary file, or to a Microsoft® Excel
    spreadsheet."

In essence, SimAuto is PowerWorld Simulator's application programming
interface (API). As such, SimAuto users can perform *almost* any task
that can be done through Simulator's graphic user interface (GUI), but
via their own program. This opens up a wealth of opportunity to perform
tasks such as:

*   Task automation

*   Sensitivity analysis

*   Co-simulation

*   Machine learning

*   And more!

For more SimAuto details, here are some PowerWorld links:

*   `SimAuto Description <https://www.powerworld.com/products/simulator/add-ons-2/simauto>`__

*   `PowerWorld Web Help <https://www.powerworld.com/WebHelp/>`__

*   `SimAuto Documentation`_

Since SimAuto strives to be accessible to "any external" program and
uses Windows `COM
<https://docs.microsoft.com/en-us/windows/win32/com/the-component-object-model>`__,
it can be cumbersome, tedious, and difficult to use. That's where ESA
comes in!

SimAuto Functions
^^^^^^^^^^^^^^^^^

Here's a listing of the currently (as of 2020-06-17, Simulator version
21) available SimAuto functions (documented `here <simauto-docs_>`_):

*   ChangeParameters
*   ChangeParametersSingleElement
*   ChangeParametersMultipleElement
*   CloseCase
*   GetFieldList
*   GetParametersSingleElement
*   GetParametersMultipleElement
*   GetParameters
*   GetSpecificFieldList
*   GetSpecificFieldMaxNum
*   ListOfDevices
*   LoadState
*   OpenCase
*   ProcessAuxFile
*   :ref:`runscriptcommand`
*   SaveCase
*   SaveState
*   SendToExcel (not recommended for use with ESA as documented in
    :ref:`esa-saw-api`)
*   TSGetContingencyResults
*   WriteAuxFile

For ESA's implementation/wrapping of these methods, see
:ref:`esa-saw-api`.

SimAuto Properties
^^^^^^^^^^^^^^^^^^

Here's a listing of the currently (as of 2020-06-17, Simulator version
21) available SimAuto properties (documented `here <simauto-docs_>`_):

*   ExcelApp (like ``SendToExcel`` function, not recommended for use
    with ESA)
*   CreateIfNotFound
*   CurrentDir
*   ProcessID
*   RequestBuildDate
*   UIVisible (Simulator versions >= 20)

For ESA's implementation/wrapping of these properties, see
:ref:`esa-saw-api`.

.. _SimAuto Documentation: https://www.powerworld.com/WebHelp/#MainDocumentation_HTML/Simulator_Automation_Server.htm%3FTocPath%3DAutomation%2520Server%2520Add-On%2520(SimAuto)%7C_____1
.. _simauto-docs: `SimAuto Documentation`_