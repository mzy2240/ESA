ESA depends on the pywin32 Python package in order to interface with
Windows components. Unfortunately, pywin32 does not always cleanly
install automatically when installing ESA, so it's recommended that you
first manually install pywin32. In your activated virtual environment,
execute the following:

.. code:: bat

    python -m pip install --only-binary :all: pypiwin32 pywin32

The authors have found that the ``--only-binary`` flag is often
necessary to get pywin32 to work - without it, pywin32 is unable to find
some necessary libraries.