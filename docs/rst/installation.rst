Overview
~~~~~~~~

Installing ESA is easy, and most users will simply want to use Python's
package manager, Pip, to install ESA. The subsections below cover
installation via Pip (:ref:`install-pip`) and from source
(:ref:`install-source`). Additionally, optional post-installation
instructions are provided.

.. _virtual-environments

On Virtual Environments
~~~~~~~~~~~~~~~~~~~~~~~

Like any Python project, the use of virtual environments is **strongly**
encouraged. If you're new to virtual environments, Python provides a
nice `tutorial <https://docs.python.org/3/tutorial/venv.html>`__.

All directions that provide command line snippets will assume that you
have already activated your virtual environment. The general procedure
is shown below (you'll need to substitute your own path).

.. code:: bat

    cd C:\Users\myuser\path\to\virtual\environment
    Scripts\activate.bat

.. _install-pip

Installation with Pip (easiest)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the Python package manager `pip <https://pip.pypa.io/en/stable/>`__
to install ESA:

.. code:: bat

   python -m pip install esa

.. _install-source

Installation from Source
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to make modifications to ESA for your own purposes, you'll
likely want to clone the Git repository and install from source.
Fortunately, this is quite easy. The following directions will assume
that your project is at ``C:\Users\myuser\git\myproject`` and that your
virtual environment is at ``C:\Users\myuser\git\myproject\venv``. If
you're new to virtual environments, Python provides a nice
`tutorial <https://docs.python.org/3/tutorial/venv.html>`__.

Start by cloning ESA into ``C:\Users\myuser\git\ESA``. This can be
accomplished in a variety of ways, but perhaps the simplest is by using
Git Bash:

.. code:: bash

   cd ~/git
   git clone https://github.com/mzy2240/ESA.git

Alternatively, you can use GitHub to download a zip archive of ESA, and
then you can extract it.

After the cloning has completed, close Git Bash and open up a command
prompt. Run the following:

.. code:: cmd

   cd C:\Users\myuser\git\myproject
   venv\Scripts\activate.bat

Your prompt should change to be prefixed by ``(venv)`` indicating that
your virtual environment has been activated. Now, perform the following:

.. code:: cmd

   cd ../ESA
   python setup.py install

Post-Installation (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need to run a post-installation script related to a pre-requisite
Python package, `pywin32 <https://github.com/mhammond/pywin32>`__. As
per pywin32's directions, you'll need to run the following with an
**elevated** (administrator) command prompt after navigating to your
virtual environment's directory:

.. code:: cmd

   Scripts\activate.bat
   python Scripts/pywin32_postinstall.py -install

(this ``Scripts`` directory can be found within your virtual environment
where your Python packages are installed. If you followed along in the
"Installation from Source" example, this ``Scripts`` directory would be
found at ``C:\Users\myuser\git\myproject\venv``.)

