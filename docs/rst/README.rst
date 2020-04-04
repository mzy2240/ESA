rst
====

This directory contains all the files needed to build ESA's
documentation, which is in  `reStructuredText
<http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`__
(.rst) format.

Building the Documentation
--------------------------

First, ensure you've installed all pre-requisite packages for building
the documentation. These pre-requisites can be found in ``setup.py`` at
the repository's top-level, under the ``extras_require`` argument to
``setuptools.setup``.

Next, activate your virtual environment, and change directories to here.

Finally, simply execute ``make html`` to build the documentation.

Initial One Time Setup (DO NOT RUN THIS)
----------------------------------------

The following is just for recording what was done to set things up
initially. All commands were run with an activated virtual environment
within the sphinx directory. Some information may now be out of date,
but this at least gives a clue as to how things were done.

#.  Run ``sphinx-quickstart``
#.  Run ``sphinx-apidoc -o . ../esa``
#.  Add ``esa`` and `modules`` lines to ``index.rst``.
#.  Add ``'spinx.ext.autodoc'`` extension in conf.py.
#.  Uncomment and modify the ``# -- Path setup`` section of conf.py

Files
-----

All ``.rst`` files are used in creating ESA's documentation. The "main"
file is ``index.rst``.

conf.py
^^^^^^^
Sphinx configuration file.

coverage.rst
^^^^^^^^^^^^

Testing coverage table created by ``coverage_to_rst.py``. Included by
overview.rst.

coverage_to_rst.py
^^^^^^^^^^^^^^^^^^

Runs ESA unittests and assesses testing coverage. Modifies top level
README file and generates coverage.rst.

make.bat
^^^^^^^^

Windows batch script used to kick off the documentation build.

Makefile
^^^^^^^^

Makefile for the documentation build.

Directories
-----------

This section discusses all directories contained in this directory.
Please keep it up to date.

_static
^^^^^^^

Store static files here.

_templates
^^^^^^^^^^

Store templates here.

installation, snippets, welcome
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These directories contain files that are included to the corresponding
.rst files. Note that the ``snippets`` directory is special, as all
examples in the files get executed as part of ESA's testing suite.
Please see the README within the ``snippets``