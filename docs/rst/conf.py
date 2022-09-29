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
import inspect
import os
import sys
from os.path import dirname, relpath
from typing import Union
from pathlib import Path
import esa
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../../'))

# Get the project root dir, which is the parent dir of this
doc_path = Path(__file__).parent
project_root = doc_path.parent.parent
src_root = project_root / "esa"

# package data
about = {}
with open(src_root / "__about__.py") as fp:
    exec(fp.read(), about)

# Open and read the version file.
with open('../../VERSION', 'r') as fh:
    __version__ = fh.read()

# -- Project information -----------------------------------------------------

project = 'ESA'
copyright = '2022, Zeyu Mao, Brandon Thayer, Yijing Liu'
author = 'Zeyu Mao, Brandon Thayer, Yijing Liu'

# The short X.Y version
version = __version__
# The full version, including alpha/beta/rc tags.
release = version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc', "sphinx.ext.linkcode"]

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
                    'snippets', 'welcome', 'citation.rst', 'README.rst',
                    '.coverage', 'coverage.rst', 'coverage_to_rst.py']

# Include module's functions and class' methods
# Note from Zeyu: This feature requires at least Sphinx version 5.2
autoclass_content = 'both'
autodoc_member_order = "bysource"
toc_object_entries_show_parents = 'all'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'press'  #alabaster
html_logo = '_static/esa_logo.webp'
html_theme_options = {
  "external_links": [
      ("Github", "https://github.com/mzy2240/ESA"),
      ("PyPI", "https://pypi.org/project/esa/")
  ]
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

########################################################################
# Prevent skipping __init___
# Source: https://stackoverflow.com/a/9772922
########################################################################

def linkcode_resolve(
    domain: str, info
) -> Union[None, str]:  # NOQA: C901
    """
    Determine the URL corresponding to Python object
    Notes
    -----
    From https://github.com/numpy/numpy/blob/v1.15.1/doc/source/conf.py, 7c49cfa
    on Jul 31. License BSD-3. https://github.com/numpy/numpy/blob/v1.15.1/LICENSE.txt
    """
    if domain != "py":
        return None

    modname = info["module"]
    fullname = info["fullname"]

    submod = sys.modules.get(modname)
    if submod is None:
        return None

    obj = submod
    for part in fullname.split("."):
        try:
            obj = getattr(obj, part)
        except Exception:
            return None

    # strip decorators, which would resolve to the source of the decorator
    # possibly an upstream bug in getsourcefile, bpo-1764286
    try:
        unwrap = inspect.unwrap
    except AttributeError:
        pass
    else:
        if callable(obj):
            obj = unwrap(obj)

    try:
        fn = inspect.getsourcefile(obj)
    except Exception:
        fn = None
    if not fn:
        return None

    try:
        source, lineno = inspect.getsourcelines(obj)
    except Exception:
        lineno = None

    if lineno:
        linespec = "#L%d-L%d" % (lineno, lineno + len(source) - 1)
    else:
        linespec = ""

    fn = relpath(fn, start=dirname(esa.__file__))

    if "dev" in about["__version__"]:
        return "{}/blob/master/{}/{}{}".format(
            about["__github__"],
            about["__package_name__"],
            fn,
            linespec,
        )
    else:
        return "{}/blob/v{}/{}/{}{}".format(
            about["__github__"],
            about["__version__"],
            about["__package_name__"],
            fn,
            linespec,
        )
