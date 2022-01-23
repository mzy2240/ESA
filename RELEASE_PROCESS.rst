Release Process
===============

This document describes the steps needed to publish a new release of
ESA.

#.  (Optional) If any updates has been made to the ``_performance.py``
    then you need to compile the module first by running
    ``pythran --config compiler.blas=mkl -O3 -ffast-math -DUSE_XSIMD esa/_performance.py -o esa/performance.pyd``.
#.  Ensure you have checked out the ``develop`` branch and have a clean
    repository (no local changes, new files, etc.).
#.  Run all tests for all Python versions (3.5 - 3.8) by running the
    script ``tests\run_tests_for_all_python_versions.py`` or manually
    run all tests in all Python environments by running the following
    from the top level of the repository after activating each virtual
    environment:
    ``python -m unittest discover tests``.
#.  Assess testing coverage by running ``docs\rst\coverage_to_rst.py``.
#.  Check the top-level README file - if testing coverage is *NOT* at
    100%, we need to add tests to get it there before proceeding. Add
    the tests, and start over.
#.  Update ``VERSION`` file (careful not to add a newline at the end).
#.  Update ``docs\rst\welcome\changelog.rst``. Add detailed notes
    related to what has changed in this release. This should include
    new functions/features added, bugs fixed, and any changes that
    break backwards compatibility (ideally, there should not be any
    breaking changes).
#.  Install esa locally into your virtual environment that you plan to
    use for building the documentation (see next step) by executing
    ``python -m pip install -e .[test,doc]``. Note the ``-e`` specifies
    "editable" mode so that the installation process does not copy all
    the files into your virtual environment's ``Lib\site-packages``
    directory. This local, editable installation will automatically
    update ``__version__`` in ``__init__.py``.
#.  If all tests were successful, build the documentation (see README
    in ``docs\rst`` directory). Note that there should **NOT** be
    **ANY** warnings or errors in the console output when building the
    documentation.
#.  When ready, commit all the new changes to the ``develop`` branch.
#.  Checkout the ``master`` branch, and run ``git merge develop``
#.  After merging, add a version tag like so:
    ``git tag -a v1.0.1 -m "ESA version 1.0.1"``
#.  Run ``git push``
#.  Run ``git push --tags``
#.  Ensure setuptools and wheel are up to date:
    ``python -m pip install --upgrade setuptools wheel``
#.  Generate the distribution archive by running this command from the
    same directory where ``setup.py`` is located:
    ``python setup.py sdist bdist_wheel``
#.  Upload the distribution archive to the Python Package Index by
    running this command: ``python -m twine upload dist/*``.
    Before uploading make sure there is only one archive version in the
    ``dist`` directory.