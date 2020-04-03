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
#.  Assess testing coverage by running ``docs\rst\coverage_to_rst.py``
#.  Update ``VERSION`` file (careful not to add a newline at the end).
#.  If all tests are successful, build documentation (see the README in
    ``docs\rst`` directory).
#.  When ready, commit all the new changes and push updates to the
    GitHub repository.
#.  Generate the distribution archive by running this command from the
    same directory where ``setup.py`` is located:
    ``python setup.py sdist bdist_wheel``
#.  Upload the distribution archive to the Python Package Index by
    running this command: ``python -m twine upload dist/*``.
    Before uploading make sure there is only one archive version in the
    ``dist`` directory.