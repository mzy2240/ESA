Changes made with each ESA release are listed here. Please note that
versions prior to 1.0.0 are not listed here, but are still available on
`PyPi <https://pypi.org/project/esa/#history>`__.

Version 1.0.3
^^^^^^^^^^^^^

* New SAW property, ``build_date``
* New SAW helper method, ``get_simulator_version``
* Updating so that ESA is compatible with Simulator version 17. Note
  that this does not imply ESA has been tested with versions 16, 18, 19,
  or 20. However, ESA *should* work with all these versions.
* Added case files for Simulator versions 16-21 and renamed the cases
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
