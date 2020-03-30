Installing ESA from source is quite simple, and does not require any
extra tools. One might choose to install ESA from source if you plan
to extend or modify ESA, or would like to run ESA's suite of tests.

The first step is to obtain a copy of the ESA repository. There are two
ways to obtain a copy: download a .zip archive or use Git to clone the
repository. `Here's a link to ESA's GitHub repository.
<https://github.com/mzy2240/ESA>`__ On the GitHub page you can find a
link to "Clone or download."

If you choose to clone the repository with Git, you'll also need to
install `Git Large File Storage <https://git-lfs.github.com/>`__. After
installation, use Git Bash or a Command Prompt window to execute the
following:

.. code:: bat

    cd C:\Users\myuser\git\ESA
    git lfs install
    git pull
    git lfs pull

If you choose to download a .zip archive, you'll of course need to
extract the archive to the desired directory.

Once you have a copy of the ESA repository, simply run the following
in a Command Prompt window *after* activating your virtual environment
(adapt path to match your setup):

.. code:: bat

    cd C:\Users\myuser\git\ESA
    python -m pip install .

If you would like to be able to run tests, you'll need to install the
testing dependencies:

.. code:: bat

    python -m pip install .[test]

Similarly, to build the documentation, you'll need:

.. code:: bat

    python -m pip install .[doc]

If you want to both run tests and build the documentation:

.. code:: bat

    python -m pip install .[test,doc]

You can find the specified "extras" in setup.py - look for
``extras_require``.
