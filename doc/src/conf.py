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

import sphinx_rtd_theme  # noqa: F401

from karabo import __version__

# We need to add the parent directory to the path so that Sphinx can find the
# modules to document.
sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------

project = "Karabo-Pipeline"
copyright = "2024, i4ds"
author = "i4ds, ETHZ"

# The full version, including alpha/beta/rc tags
release = __version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_rtd_theme",
    "myst_parser",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to doc directory, that match files and
# directories to ignore when looking for doc files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [  # TODO: why do we have example scripts in this dir?
    "examples/_example_scripts",
    "examples/combine_examples.py",
    "examples/example_structure.md",
]

add_module_names = False

html_last_updated_fmt = ""

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_sidebars = {
    "**": ["globaltoc.html", "relations.html", "sourcelink.html", "searchbox.html"]
}
html_theme = "sphinx_rtd_theme"
html_logo = "_static/logo.png"
html_theme_options = {
    "logo_only": True,
    "display_version": True,
    "collapse_navigation": True,
    "sticky_navigation": True,
    "titles_only": False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
