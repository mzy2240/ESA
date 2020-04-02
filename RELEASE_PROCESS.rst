Release Process
===============

This document describes the steps needed to publish a new release of
ESA.

#.  Run all tests for all Python versions by running the script
    ``tests\run_tests_for_all_python_versions.py``.
#.  Update ``VERSION`` file (careful not to add a newline at the end).
#.  If all tests are successful, build documentation (see docs in
    ``docs`` directory).
#.  TODO