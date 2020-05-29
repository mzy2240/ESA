Tests
=====

This directory should contain all code, PowerWorld cases, and data
needed to fully test ESA. There should be a Python module named 
"test_<module>" for each ESA module. At present, ESA only has the 
SAW module.

Cases
-----

Use this directory to store PowerWorld cases.

Data
----

Use this directory to store other data needed for testing.

area_filter.aux
--------------

PowerWorld auxiliary file that defines a filter which obtains only buses in
the east area. Used for testing ProcessAuxFile, and is also a useful
template for defining filters in aux files.

README.rst
----------

This file.

run_tests_for_all_python_versions.py
------------------------------------

Script to run tests for all supported Python versions. Check out its
docstring for more information.

test_saw.py
-----------

Python file for running tests related to the SAW module.

test_snippets.py
----------------

Python file for running tests related to the documentation snippets.