Release Process
===============

This document describes the steps needed to publish a new release of
ESA.

#.  Run all tests for all Python versions (3.5 - 3.8) by running the
    script ``tests\run_tests_for_all_python_versions.py`` or manually
    run all tests in all Python environments by running the following
    from the top level of the repository after activating your virtual
    environment:
    ``python -m unittest discover tests``.
#.  Update ``VERSION`` file (careful not to add a newline at the end).
#.  If all tests are successful, build documentation (see the README in
    ``docs\rst`` directory).
#.  When ready, commit all the new changes and update to the Github
    repository.
#.  Generate the distribution archive.
#.  Upload the distribution archive to the Python Package Index.