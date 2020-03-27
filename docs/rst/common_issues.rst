This section will describes some (maybe) common issues and their
solutions.

Installation/Virtual Environment Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have issues installing ESA and/or its dependencies, you may need
to do some manual work installing pre-requisites in your virtual
environment. Hopefully following these simple directions will help fix
most issues.

1. Start fresh! Completely remove your virtual environment and recreate
   it. `PyCharm makes this pretty
   easy <https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html>`__,
   or you can do so manually using `Python's
   guide <https://docs.python.org/3/tutorial/venv.html>`__. The
   remaining directions will assume you're typing commands into your
   **activated** virtual envrionment.
2. Reinstall pip:
   ``python -m pip install --upgrade --force-reinstall pip``. We're
   intentionally using ``python -m pip`` instead of just ``pip`` to
   avoid possible path issues. Note that you might need to run this
   command twice (the first may fail for some unknown reason).
3. Check out ESA's
   `setup.py <https://github.com/mzy2240/ESA/blob/master/setup.py>`__
   file and look for ``install_requires``. It'll look something like
   ``['pandas', 'numpy', 'pywin32', 'pypiwin32']``.
4. Using what we found under ``install_requires``, install ESA's
   dependencies manually. To avoid dependencies on a compiler, we'll get
   binary distributions only:
   ``python -m pip install --upgrade --only-binary :all: pandas numpy pywin32 pypiwin32``

   -  If this command fails, you may need to pick and choose which
      dependencies you grab binary distributions for, and which you get
      other types of distributions for. Here's the `Python
      documentation <https://pip.pypa.io/en/stable/reference/pip_install/>`__.
      If we only want to get binary distributions for ``pandas`` and
      ``numpy``, we'd modify the previous command to instead read like
      so:
      ``python -m pip install --upgrade --only-binary pandas,numpy pandas numpy pywin32 pypiwin32``

5. After you've installed ESA's dependencies, it's time to install ESA:
   ``python -m pip install esa``

Errors/Issues Initializing a SAW Instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section will cover some common issues when attempting to initialize
a SAW instance. The first thing to check is that your arguments are
correct - you can find the documentation
`here <file:///C:/Users/brand/git/ESA/docs/html/esa.html#esa.saw.SAW>`__.

esa.saw.PowerWorldError: OpenCase: Errors have occurred
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You may see an error stack trace that looks something like the
following:

.. code:: python

   Traceback (most recent call last):
     File "<input>", line 1, in <module>
     File "C:\Users\brand\git\ESA\esa\saw.py", line 111, in __init__
       self.OpenCase(FileName=FileName)
     File "C:\Users\brand\git\ESA\esa\saw.py", line 680, in OpenCase
       return self._call_simauto('OpenCase', self.pwb_file_path)
     File "C:\Users\brand\git\ESA\esa\saw.py", line 1101, in _call_simauto
       raise PowerWorldError(output[0])
   esa.saw.PowerWorldError: OpenCase: Errors have occurred

Often, this is due to a bad path specification. Ensure you're providing
a **full** file path, including the file extension (.pwb), and that the
file exists at the exact path you specified.

TypeError: This COM object can not automate the makepy process - please run makepy manually for this object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see an error like the above, try initializing your SAW object
again but set ``early_bind=False``. While we're unsure of the root cause
of this issue, it seems to be related to the fact that
``early_bind=True`` preemptively creates some Python files related to
the SimAuto COM API.

AttributeError: module 'win32com.gen_py.C99F1760-277E-11D5-A106-00C04F469176x0x20x0' has no attribute 'CLSIDToClassMap'
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see an error like that listed above, it's possible the pywin32
cache has been somehow corrupted. Simply delete the following directory
(the default):
``C:\Users\<your user directory>\AppData\Local\Temp\gen_py``