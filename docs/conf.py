# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
sys.path.insert(0, os.path.abspath('../'))
print(os.path.abspath('../'))
import sphinx_rtd_theme
from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pupilio Documentation'
copyright = '2026, HangZhou Technology Technology Co., Ltd.'
author = 'Gancheng Zhu'
release = '1.5.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.mathjax',
    'sphinx_markdown_tables',
    'recommonmark',
]
autosectionlabel_prefix_document = True

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = [sphinx_rtd_theme.get_html_theme_path()]


source_parsers = {
    '.md': CommonMarkParser,
}

source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}


# app setup hook
def setup(app):
    app.add_config_value('recommonmark_config', {
        #'url_resolver': lambda url: github_doc_root + url,
        'auto_toc_tree_section': 'Contents',
        'enable_math': False,
        'enable_inline_math': False,
        'enable_eval_rst': True,
    }, True)
    app.add_transform(AutoStructify)
