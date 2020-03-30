# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../../'))

# Open and read the version file.
with open('../../VERSION', 'r') as fh:
    __version__ = fh.read()

# -- Project information -----------------------------------------------------

project = 'ESA'
copyright = '2020, Zeyu Mao, Brandon Thayer, Yijing Liu'
author = 'Zeyu Mao, Brandon Thayer, Yijing Liu'

# The short X.Y version
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
#
# Note from Brandon: Add directories containing sub-files to avoid
# warnings during build time. Hopefully this doesn't shoot us in the
# foot later.
# https://stackoverflow.com/a/15438962/11052174
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'installation',
                    'snippets', 'welcome', 'citation.rst', 'README.rst']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

########################################################################
# Prevent skipping __init___
# Source: https://stackoverflow.com/a/9772922
########################################################################

autoclass_content = 'both'
