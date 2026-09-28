# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# For a full list of options see:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).parent.resolve()
_ROOT = _HERE.parent

# Document the sources even when pyrolib is not installed. The package lives in
# src/, so src/ (not src/pyrolib/) is what belongs on sys.path.
sys.path.insert(0, str(_ROOT / "src"))

from pyrolib import __version__ as pyrover  # noqa: E402

# -- Project information -----------------------------------------------------

project = "pyrolib"
copyright = "2022-2026, Aurélien Costes and contributors"
author = "Aurélien Costes"


def _copy_markdown_from_root(name, destination):
    """Copy a root-level markdown file into the doc source tree.

    Paths are anchored on this file so the build works from any directory.
    """
    print(f"copying {name}")
    shutil.copy(_ROOT / name, _HERE / destination)


def _get_version():
    ver = pyrover
    ver_split = [key for key in ver.split(".") if key]
    if len(ver_split) >= 3:
        release = ".".join(ver.split(".")[:3])
        version = ".".join(ver.split(".")[:2])
    elif len(ver_split) == 2:
        release = "%s.0" % ver
        version = ver
    elif len(ver_split) == 1:
        release = "%s.0.0" % ver.replace(".", "")
        version = "%s.0" % ver.replace(".", "")
    return release, version


# The full version, coming from pyrolib.__version__
release, version = _get_version()

_copy_markdown_from_root("README.md", "readme_copy.md")
_copy_markdown_from_root("CHANGELOG.md", "changelog_copy.md")

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

# The how-to guides use $...$ inline maths (e.g. $\Delta_x$, $\Gamma_x$), which
# MyST only recognises with the dollarmath extension enabled.
myst_enable_extensions = [
    "dollarmath",
    "colon_fence",
]

source_suffix = [".rst", ".md"]

# The master toctree document.
master_doc = "index"

language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

pygments_style = None


# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_show_sourcelink = False
html_static_path = ["_static"]
html_logo = "_static/logo.png"
html_favicon = "_static/favicon.ico"
html_title = "pyrolib documentation"
html_short_title = "pyrolib"


# -- Options for HTMLHelp output ---------------------------------------------

htmlhelp_basename = "doc"


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, project + ".tex", project, author, "manual"),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, project, project + " Documentation", [author], 1)]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        project,
        project + " Documentation",
        author,
        project,
        "Python tools for the MesoNH-Blaze model.",
        "Miscellaneous",
    ),
]


# -- Options for Epub output -------------------------------------------------

epub_title = project

# A list of files that should not be packed into the epub file.
epub_exclude_files = ["search.html"]
