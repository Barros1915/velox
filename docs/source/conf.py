# Velox Framework - Sphinx Configuration
# ================================
# Generated for Velox v1.0.0

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

# -- Project info -------------------------------------------------------------
project = 'Velox'
copyright = '2026, Velox Team'
author = 'Velox Team'
release = '1.0.0'

# The short X.Y version
version = '1.0'

# -- General configuration ---------------------------------------------------
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix(es) of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# -- Options for HTML output -----------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = '../../assets/logo_velox.png'
html_css_files = ['css/custom.css']

# -- autodoc configuration -------------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
}

# -- Extensions --------------------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',      # Google/NumPy style docstrings
    'sphinx.ext.viewcode',     # Links to source code
    'sphinx.ext.intersphinx',  # Links to other docs
]

# -- Napoleon settings -------------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# -- Intersphinx settings ---------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}