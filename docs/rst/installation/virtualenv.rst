Like any Python project, the use of virtual environments is **strongly**
encouraged. If you're new to virtual environments, Python provides a
nice `tutorial <https://docs.python.org/3/tutorial/venv.html>`__.

After installing Python on your machine, open up a Command Prompt window
(Hit the "Windows" key and the "R" key simultaneously, type in "cmd" in
the popup, then hit Enter) then set up a virtual environment like so
(adapt paths as necessary):

.. code:: bat

    cd C:\path\to\my\project
    C:\path\to\python.exe -m venv my-venv

Then, activate the virtual environment like so (in the same terminal):

.. code:: bat

    my-venv\Scripts\activate.bat

**All installation directions assume your virtual environment has been
activated.**

Next, update pip and setuptools (in your activated virtual environment):

.. code:: bat

    python -m pip install --upgrade --force-reinstall pip setuptools