ESA is a "Pip-installable" Python package that eases interaction with
the PowerWorld Simulator Automation Server (SimAuto). PowerWorld
Simulator is a powerful, commercial-grade electric grid simulation tool
with a wide range of capabilities. Information on Simulator can be found
`here
<https://www.powerworld.com/products/simulator/overview>`__ and
information on SimAuto can be found `here
<https://www.powerworld.com/products/simulator/add-ons-2/simauto>`__.
Since ESA directly interfaces with SimAuto, ESA users will need a
PowerWorld license and installation that also includes SimAuto.

ESA makes working with SimAuto, well, easy. Users don't have to worry
about input or output data type conversions, data mapping,
determining whether SimAuto has reported an error, and more.
Additionally, ESA uses the scientific computing packages you know and
love, including Numpy and Pandas. In addition to wrapping 100% of the
functions provided by SimAuto, ESA provides helper functions that
further ease development. Below is a quick motivating example (also
found in :ref:`increase-loading`) that shows how easy it is to use
SimAuto.

.. include:: snippets/increase_loading_14.rst
