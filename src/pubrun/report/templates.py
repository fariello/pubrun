"""
Templates for generating publication-ready methods sections.
"""

# A curated list of popular Data Science, ML, and NLP packages to proactively highlight
HIGHLIGHT_PACKAGES = {
    # Core Data Science
    "numpy", "pandas", "scipy", "scikit-learn", "statsmodels",
    # Plotting
    "matplotlib", "seaborn", "plotly",
    # Deep Learning / ML
    "torch", "tensorflow", "keras", "jax", "xgboost", "lightgbm",
    # NLP
    "nltk", "spacy", "transformers", "gensim"
}

MARKDOWN_TEMPLATE = """
### Computational Methods

Computational experiments were executed on a machine running {os_name} equipped with an {cpu_model} and {ram_gb} GB of RAM. The execution environment relied on Python {python_version} ({python_impl}). 

{packages_text}

To guarantee computational reproducibility, the exact state of the source code was archived at Git commit `{git_commit}`{git_repo_text}. Environment and execution provenance were natively tracked using the `pubrun` library [1].

**References:**
[1] Fariello, G. (2026). *pubrun: Lightweight native execution provenance and reproducibility tracking*. https://bitbucket.org/gfariello/pubrun
"""

LATEX_TEMPLATE = """
\\subsection*{{Computational Methods}}

Computational experiments were executed on a machine running {os_name} equipped with an {cpu_model} processor and {ram_gb} GB of RAM. The execution environment relied on Python {python_version} ({python_impl}). 

{packages_text}

To guarantee computational reproducibility, the exact state of the source code was archived at Git commit \\texttt{{{git_commit}}}{git_repo_text}. Environment and execution provenance were natively tracked using the \\texttt{{pubrun}} library \\cite{{fariello_pubrun_2026}}.

%% Ensure you add the following to your .bib file:
%% @software{{fariello_pubrun_2026,
%%   author = {{Fariello, Gabriel}},
%%   title = {{pubrun: Lightweight native execution provenance and reproducibility tracking}},
%%   year = {{2026}},
%%   url = {{https://bitbucket.org/gfariello/pubrun}}
%% }}
"""
