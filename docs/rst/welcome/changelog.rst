Changes made with each ESA release are listed here. Please note that
versions prior to 1.0.0 are not listed here, but are still available on
`PyPi <https://pypi.org/project/esa/#history>`__.

Version 1.2.6
^^^^^^^^^^^^^

* Add functions to obtain branch and shunt impedance
* Add a helper function to convert dataframe into auxiliary(aux/axd) data section

Version 1.2.5
^^^^^^^^^^^^^

* Add one example for fast contingency analysis (N-1 & N-2)
* Supports changing system models based on temperature

Version 1.2.4
^^^^^^^^^^^^^

* Supports latest PW22 (Nov and Dec build) and PW23

Version 1.2.3
^^^^^^^^^^^^^

* Fix the AOT import error

Version 1.2.2
^^^^^^^^^^^^^

* Fix the AOT version-dependent issue
* Update the dependency version

Version 1.2.1
^^^^^^^^^^^^^

* Greatly improve the fast contingency analysis by taking advantage of
  SIMD, JIT and AOT. Now it could finish a N-1 and N-2 contingency analysis of
  a synthetic 2000 bus grid in less than 15 seconds!
* Adjust the release process to include AOT functions

Version 1.2.0
^^^^^^^^^^^^^

* Optimize the process to use the same order as shown in simulator
  (note: if pw_order is used, all data in the dataframe will be string type)
* Add a method to obtain the incidence matrix
* Implement a modified fast N-1 and N-2 contingency analysis algorithm.
  The algorithm is originally developed by Prof. Kostya Turitsyn from MIT and
  the implementation has been slightly modified and adapted to work with ESA.
* Add a few helper functions to facilitate contingency analysis powered by the simulator.

Version 1.1.0
^^^^^^^^^^^^^

* Allow users to use the same order as shown in simulator for all the
  dataframes
* Add a helper function to generate LODF matrix

Version 1.0.9
^^^^^^^^^^^^^

* Update the pre-install process and the common issues
* Update the helper function 'get_ybus' with a new argument to accept
  external ybus file

Version 1.0.8
^^^^^^^^^^^^^

* Add new helper function 'to_graph'. The new function could help
  generate NetworkX graph model from the case, in two different levels:
  bus-as-node and substation-as-node. Parallel lines are preserved, and
  directedgraph is supported (currently the direction is fixed to be
  the same as real power flow).

Version 1.0.7
^^^^^^^^^^^^^

* Add new functions: get_ybus, get_jacobian

Version 1.0.6
^^^^^^^^^^^^^

* Hopefully finally fixing locale-based issues. Fixes began in 1.0.4,
  and continued in 1.0.5.
* Finalizing JOSS paper. Once published, the citation will be added to
  the top-level README and the documentation.

Version 1.0.5
^^^^^^^^^^^^^

* It turns out version 1.0.4 did not fully/correctly handle automatic
  locale setting. This version should now properly handle different
  decimal delimiters automatically.
* Bug fix: The ``additional_fields`` parameter to ``SAW``'s
  ``get_power_flow_results`` was permanently adding the
  ``additional_fields`` to the corresponding list in the ``SAW``
  object's ``SAW.POWER_FLOW_FIELDS`` attribute.

Version 1.0.4
^^^^^^^^^^^^^

* Added support for other locales by automatically detecting the
  system's decimal delimiter. This should allow users in Europe and
  elsewhere to leverage ESA. Thanks to
  `robinroche <https://github.com/robinroche>`__ for pointing out the
  problem during our `JOSS <https://joss.theoj.org/>`__ review in
  `this comment <https://github.com/openjournals/joss-reviews/issues/2289#issuecomment-643482550>`__.

Version 1.0.3
^^^^^^^^^^^^^

* New SAW attribute, ``build_date``
* New SAW attribute, ``version``
* New SAW helper method, ``get_version_and_builddate``
* Add argument ``additional_fields`` for ``get_power_flow_results`` method
  which provides an easy and consistent way to add more fields to the power
  flow result
* Updating so that ESA is compatible with Simulator version 17. Note
  that this does not imply ESA has been tested with versions 16, 18, 19,
  or 20. However, ESA *should* work with all these versions.
* Added case files for Simulator versions 16-22(beta) and renamed the cases
  accordingly (suffixed with ``pws_version_<version goes here>.pwb``.
* Updated documentation to discuss different versions of Simulator.

Version 1.0.2
^^^^^^^^^^^^^

* Add area number to the power flow result
* Update the citation section
* Fix a bug in the test file that will result in a failure if some
  default names are changed in PowerWorld

Version 1.0.1
^^^^^^^^^^^^^

* Add new functions: update_ui, OpenOneline and CloseOneline
* Add documents to meet the requirement of JOSS
* Add one more example into the documentation
* Update the coverage_to_rst.py so that it's more clear that the errors
  that get printed during testing are as expected.
* Update the release process
* Fix minor typos

Version 1.0.0
^^^^^^^^^^^^^

ESA version 1.0.0 is the first ESA release in which 100% of SimAuto
functions are wrapped, and testing coverage is at 100%.
