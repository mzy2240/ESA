Common Issues
=============
This section will describes some (maybe) common issues and their
solutions. If you encounter and solve an issue, please file a `GitHub
issue <https://github.com/mzy2240/ESA/issues>`__ so that we can add your
problem and solution to this section.

Before diving too deeply into the issues listed here, first ensure that
you have all the prerequisite software installed (including PowerWorld
Simulator and the SimAuto add-on) and are using a supported version of
Python (>= 3.5).

.. _venv-issues:

Installation/Virtual Environment Issues
---------------------------------------

If you have issues installing ESA and/or its dependencies, you may need
to do some manual work installing prerequisites in your virtual
environment. Hopefully following these simple directions will help fix
most issues.

1. Start fresh! Completely remove your virtual environment and recreate
   it. `PyCharm makes this pretty
   easy <https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html>`__,
   or you can do so manually using `Python's
   guide <https://docs.python.org/3/tutorial/venv.html>`__. The
   remaining directions will assume you're typing commands into your
   **activated** virtual envrionment.
2. Reinstall pip and setuptools:
   ``python -m pip install --upgrade --force-reinstall pip setuptools``.
   We're intentionally using ``python -m pip`` instead of just ``pip``
   to avoid possible path issues. Note that you might need to run this
   command twice (the first may fail for some unknown reason).
3. Check out ESA's
   `setup.py <https://github.com/mzy2240/ESA/blob/master/setup.py>`__
   file and look for ``install_requires``. It'll look something like
   ``['pandas', 'numpy', 'pywin32', 'pypiwin32']``.
4. Using what we found under ``install_requires``, install ESA's
   dependencies manually. To avoid compiler dependencies, we'll get
   binary distributions only:
   ``python -m pip install --upgrade --only-binary :all: pandas numpy pywin32 pypiwin32``

   -  If this command fails, you may need to pick and choose which
      dependencies you grab binary distributions for, and which you get
      other types of distributions for. Here's the `Python
      documentation <https://pip.pypa.io/en/stable/reference/pip_install/>`__.
      As a strictly illustrative example, if we only want to get binary
      distributions for ``pandas`` and ``numpy``, we'd modify the
      previous command to instead read like so:
      ``python -m pip install --upgrade --only-binary pandas,numpy pandas numpy pywin32 pypiwin32``

   - The authors of ESA have at times had issues installing pywin32 and
     pypiwin32 when *not* using the ``--only-binary`` option. So, if
     you're encountering errors you suspect are related to pywin32,
     try to uninstall and reinstall pywin32 and pypiwin32 with the
     ``--only-binary`` option.

5. After you've installed ESA's dependencies, it's time to install ESA:
   ``python -m pip install esa``

PyCharm Virtual Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you use PyCharm to automatically create virtual environments for you,
there's a little extra work to do to get everything working for Python
3.8 (and possibly for other Python versions as well). Start up a
terminal *inside* PyCharm (click on the ``Terminal`` button which
defaults to the lower left area). In the terminal, run:
``python -m pip install -U --force-reinstall pip``. Note you may need to
run this command twice - mine failed the first time. The same may be
required for ``setuptools`` and/or ``distutils``.

Errors/Issues Initializing a SAW Instance
-----------------------------------------

This section will cover some common issues when attempting to initialize
a SAW instance. The first thing to check is that your arguments are
correct - check the API documentation first.

esa.saw.PowerWorldError: OpenCase: Errors have occurred
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You may see an error stack trace that looks something like the
following:

.. code:: python

   Traceback (most recent call last):
     File "<input>", line 1, in <module>
     File "C:\Users\myuser\git\ESA\esa\saw.py", line 111, in __init__
       self.OpenCase(FileName=FileName)
     File "C:\Users\myuser\git\ESA\esa\saw.py", line 680, in OpenCase
       return self._call_simauto('OpenCase', self.pwb_file_path)
     File "C:\Users\myuser\git\ESA\esa\saw.py", line 1101, in _call_simauto
       raise PowerWorldError(output[0])
   esa.saw.PowerWorldError: OpenCase: Errors have occurred

Often, this is due to a bad path specification. Ensure you're providing
a **full** file path, including the file extension (.pwb), and that the
file exists at the exact path you specified.

Also, make sure that the
file is **actually** a PowerWorld binary file. If you open the file with
a text editor and see a bunch of weird symbols that are unintelligible
to a mere mortal, it's likely a PowerWorld binary file. If, upon opening
the file you see something like:

..

    | version https://git-lfs.github.com/spec/v1
    | oid sha256:f05131d24da96daa6a6712c5b9d368c81eeaea5dc7d0b6c7bec7d03ccf021b4a
    | size 34

Then you're looking at a Git LFS pointer file, and likely need to
install `Git LFS <https://git-lfs.github.com/>`__ and perform a
``git lfs pull``.

TypeError: This COM object can not automate the makepy process - please run makepy manually for this object
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see an error like the above, try initializing your SAW object
again but set ``early_bind=False``. While we're unsure of the root cause
of this issue, it seems to be related to the fact that
``early_bind=True`` preemptively creates some Python files related to
the SimAuto COM API, and file permission issues can crop up.

AttributeError: module 'win32com.gen_py.C99F1760-277E-11D5-A106-00C04F469176x0x20x0' has no attribute 'CLSIDToClassMap'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see an error like that listed above, it's possible the pywin32
cache has been somehow corrupted (perhaps your computer crashed while
a script which uses ESA was running). Simply delete the following
directory (the default, you may have to adapt for your system):

``C:\Users\<your user directory>\AppData\Local\Temp\gen_py``

The key part here is ``gen_py``. If the above path isn't right for you,
use Windows to search for ``gen_py``.

ModuleNotFoundError: no module pywintypes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see an error like that listed above, try reinstalling pywin32
and pypiwin32 with the ``--only-binary`` option, as described in the
:ref:`venv-issues` section.

esa.saw.PowerWorldError: Access Violation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see an error like that listed above, you probably could observe
the same errors using script functionality in the PowerWorld Simulator
interface. When you start the simulator (either the GUI or ESA) in a
remote desktop environment, due to security reasons the system may block
the simulator to save or create any files. As a result, any functions
that require the simulator to generate files will fail with such errors.
There are not much things we could do from our side, but one possible
hack is to login locally and use the simulator first, then use the
remote desktop to continue your work.