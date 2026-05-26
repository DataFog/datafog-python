# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import re
from pathlib import Path

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "DataFog"
copyright = "2024, DataFog Inc."
author = "Sid Mohan"
_version_file = Path(__file__).resolve().parents[1] / "datafog" / "__about__.py"
_version_match = re.search(r'^__version__ = "([^"]+)"', _version_file.read_text(), re.M)
release = f"v{_version_match.group(1)}" if _version_match else "v0.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc", "sphinx.ext.autosummary", "sphinx.ext.napoleon"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

autosummary_generate = True
napoleon_use_rtype = False
napoleon_use_ivar = False
napoleon_use_param = False

# Keep API docs buildable from the lightweight core/dev install. These
# integrations are documented, but they live behind optional extras.
autodoc_mock_imports = ["PIL", "pytesseract", "spacy"]
