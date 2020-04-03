At this point in time, one can only run unittests if ESA is installed
from source and if you've installed the ``test`` dependencies. A
future version of ESA may make tests available when installing via Pip.

Using a Command Prompt window, change directories to the ESA repository
and run the tests like so (adapt paths as necessary):

.. code:: bat

    cd C:\Users\myuser\git\ESA
    my-venv\Scripts\activate.bat
    python -m unittest discover tests

During the running of the tests, you'll see some logging output and
error messages - this is expected. What's important is that at the end,
you see a message like:

    | Ran 73 tests in 34.542s
    |
    | OK (expected failures=2)

If something is wrong, you'll see some indications of failure. The
"expected failures" are okay, and do not indicate there are any issues.

If you've installed the testing dependencies listed in setup.py, you
should have "coverage.py" installed. If you'd like to assess ESA's
testing coverage, the incantation looks like (run from top-level of
ESA repository after activating virtual environment):

.. code:: bat

    coverage run
    coverage report -m

Note that the arguments to ``coverage run`` are provided by
``.coveragerc`` at the top-level of the repository.
