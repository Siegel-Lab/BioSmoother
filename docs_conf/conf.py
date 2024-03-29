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
# sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../'))

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

import libbiosmoother

# -- Project information -----------------------------------------------------

project = 'biosmoother'
copyright = '2023, Markus R. Schmidt, Anna Barcons-Simon, Claudia Rabuffo, and T. Nicolai Siegel'
author = 'Markus R. Schmidt, Anna Barcons-Simon, Claudia Rabuffo, and T. Nicolai Siegel'

# The full version, including alpha/beta/rc tags
b_version = (pkg_resources.files("biosmoother") / "VERSION").read_text()
release = b_version.split("-")[1 if b_version.startswith("D-") else 0]

rst_epilog = """
.. |BioSmootherVersion| replace:: {versionnum}
""".format(
versionnum = b_version,
) + """
.. |libBioSmootherVersion| replace:: {versionnum}
""".format(
versionnum = libbiosmoother.LIB_BIO_SMOOTHER_CPP_VERSION,
)

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx_mdinclude",
    "sphinxarg.ext",
    'sphinxemoji.sphinxemoji',
]

html_theme_options = {
    'navigation_depth': 8,
    'collapse_navigation': False,
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

master_doc = "index"


html_favicon="../biosmoother/static/favicon.ico"
