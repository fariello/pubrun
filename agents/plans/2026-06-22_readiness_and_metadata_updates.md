# Implementation Plan: Repository Readiness and Metadata Updates

This implementation plan outlines the steps to prepare the `pubrun` repository for public adoption and release. It details the precise file modifications, new files, and verification steps aligned during the review interview.

All changes will be implemented **locally** first. No commits will be pushed to the remote repository until explicitly instructed.

---

## 1. Design & Wording Decisions (Aligned)

*   **README Phrasing (Line 7)**: Keep the developer-friendly marketing term `"stupidly simple, zero-dependency"`.
*   **README Phrasing (Line 54)**: Replace with `"pubrun removes this friction by automating execution tracking and metadata compilation."` to maintain technical precision while keeping the impact high.
*   **README Phrasing (Line 56)**: Replace `"so your run is instantly citable"` with `"making your run immediately documentable and ready for publication."` to reflect the local nature of the collected provenance.
*   **Code of Conduct Email**: Adopt Contributor Covenant v2.1 with contact address `gfariello@uri.edu`.
*   **PR Template constraint**: Add a mandatory checkbox confirming that the proposed contribution adheres to the core zero-dependency, lightweight, and zero-configuration philosophy.
*   **Seed Issues**: No seed issues will be opened by us; we will let them be opened naturally by external contributors.
*   **Citation Templates**: Replace early publication/journal placeholders in the codebase with a generic citation referencing the `pubrun` GitHub repository.

---

## 2. Proposed Changes

### A. Remove Publication Placeholders in Codebase

We will update the citation command output and report templates to reference the GitHub repository instead of the journal.

#### [MODIFY] [src/pubrun/__main__.py](file:///home/gfariello/VC/pubrun/src/pubrun/__main__.py)
Update `_run_cite(style: str)`:
*   **APA style**:
    *   *Current*: `"Fariello, G. (2026). pubrun: A zero-dependency Python library for execution provenance and telemetry capture. Journal of Open Source Software, 11(121), 8024. https://doi.org/10.21105/joss.08024"`
    *   *Proposed*: `"Fariello, G. (2026). pubrun: A zero-dependency Python library for execution provenance and telemetry capture. GitHub repository, https://github.com/fariello/pubrun"`
*   **MLA style**:
    *   *Current*: `"Fariello, Gabriele. \"pubrun: A zero-dependency Python library for execution provenance and telemetry capture.\" Journal of Open Source Software, vol. 11, no. 121, 2026, p. 8024, https://doi.org/10.21105/joss.08024."`
    *   *Proposed*: `"Fariello, Gabriele. \"pubrun: A zero-dependency Python library for execution provenance and telemetry capture.\" GitHub, 2026, https://github.com/fariello/pubrun."`
*   **Chicago style**:
    *   *Current*: `'Fariello, Gabriele. 2026. "pubrun: A zero-dependency Python library for execution provenance and telemetry capture." Journal of Open Source Software 11 (121): 8024. https://doi.org/10.21105/joss.08024.'`
    *   *Proposed*: `'Fariello, Gabriele. 2026. "pubrun: A zero-dependency Python library for execution provenance and telemetry capture." GitHub. https://github.com/fariello/pubrun.'`
*   **BibTeX style**:
    *   *Current*:
        ```bibtex
        @article{fariello_pubrun_2026,
          author    = {Gabriele Fariello},
          title     = {pubrun: A zero-dependency Python library for execution provenance and telemetry capture},
          journal   = {Journal of Open Source Software},
          volume    = {11},
          number    = {121},
          pages     = {8024},
          year      = {2026},
          doi       = {10.21105/joss.08024},
          url       = {https://doi.org/10.21105/joss.08024}
        }
        ```
    *   *Proposed*:
        ```bibtex
        @misc{fariello_pubrun_2026,
          author    = {Gabriele Fariello},
          title     = {pubrun: A zero-dependency Python library for execution provenance and telemetry capture},
          howpublished = {\url{https://github.com/fariello/pubrun}},
          year      = {2026}
        }
        ```

#### [MODIFY] [src/pubrun/report/templates.py](file:///home/gfariello/VC/pubrun/src/pubrun/report/templates.py)
*   **Markdown template (`MARKDOWN_TEMPLATE`)**:
    *   *Current*: `[1] Fariello, G. (2026). pubrun: A zero-dependency Python library for execution provenance and telemetry capture. *Journal of Open Source Software*, 11(121), 8024. https://doi.org/10.21105/joss.08024`
    *   *Proposed*: `[1] Fariello, G. (2026). pubrun: A zero-dependency Python library for execution provenance and telemetry capture. GitHub repository, https://github.com/fariello/pubrun`
*   **LaTeX template (`LATEX_TEMPLATE`)**:
    *   *Current*:
        ```latex
        %% @article{fariello_pubrun_2026,
        %%   author    = {Gabriele Fariello},
        %%   title     = {pubrun: A zero-dependency Python library for execution provenance and telemetry capture},
        %%   journal   = {Journal of Open Source Software},
        %%   volume    = {11},
        %%   number    = {121},
        %%   pages     = {8024},
        %%   year      = {2026},
        %%   doi       = {10.21105/joss.08024},
        %%   url       = {https://doi.org/10.21105/joss.08024}
        %% }
        ```
    *   *Proposed*:
        ```latex
        %% @misc{fariello_pubrun_2026,
        %%   author    = {Gabriele Fariello},
        %%   title     = {pubrun: A zero-dependency Python library for execution provenance and telemetry capture},
        %%   howpublished = {\url{https://github.com/fariello/pubrun}},
        %%   year      = {2026}
        %% }
        ```

---

### B. Add `CODE_OF_CONDUCT.md` and Link It

#### [NEW] [CODE_OF_CONDUCT.md](file:///home/gfariello/VC/pubrun/CODE_OF_CONDUCT.md)
We will add the standard Contributor Covenant v2.1 to the repository root.
*   **Contact Address**: `gfariello@uri.edu`.

#### [MODIFY] [CONTRIBUTING.md](file:///home/gfariello/VC/pubrun/CONTRIBUTING.md)
Add a Code of Conduct section at the end of the contributing guide linking to the Code of Conduct document:
```markdown
## Code of Conduct

Contributors are expected to adhere to the [Code of Conduct](file:///home/gfariello/VC/pubrun/CODE_OF_CONDUCT.md). Please report any unacceptable behavior to gfariello@uri.edu.
```

---

### C. Create Pull Request Template

#### [NEW] [.github/pull_request_template.md](file:///home/gfariello/VC/pubrun/.github/pull_request_template.md)
Create a detailed template requiring contributors to state PR details, test results, and compliance with the zero-dependency architecture:
```markdown
## Description
Provide a brief summary of the changes proposed in this Pull Request, including the problem being solved or the feature being added.

## Related Issues
Link any relevant issues (e.g. `Closes #123`).

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Documentation update
- [ ] Refactor or packaging change

## Verification and Testing
Explain how these changes were tested:
- [ ] Automated tests run locally (`pytest`) and all passed.
- [ ] Manual verification steps (please describe below).

## Checklist
- [ ] I have read the [CONTRIBUTING.md](file:///home/gfariello/VC/pubrun/CONTRIBUTING.md) guide.
- [ ] My code follows the code style of this project.
- [ ] My changes maintain the core design philosophy (zero-dependency on Python 3.11+, lightweight footprint, and zero-configuration design).
- [ ] My changes generate no new warnings or lint issues.
- [ ] I have added/updated tests that prove my fix is effective or that my feature works.
- [ ] I have updated the documentation accordingly.
```

---

### D. Tone Down README Wording

#### [MODIFY] [README.md](file:///home/gfariello/VC/pubrun/README.md)
Revise lines 54 and 56 of the `README.md` to be precise and realistic:
*   **Line 54**:
    *   *Current*: `` `pubrun` permanently ends this friction. ``
    *   *Proposed*: `` `pubrun` removes this friction by automating execution tracking and metadata compilation. ``
*   **Line 56**:
    *   *Current*: `` ...LaTeX/Markdown blocks so your run is instantly citable. ``
    *   *Proposed*: `` ...LaTeX/Markdown blocks making your run immediately documentable and ready for publication. ``

---

## 3. Verification Plan

### Local Automated Tests
Run the test suite to verify that no package changes cause regression:
```bash
/home/gfariello/venv/p3.14/bin/pytest
```

### Citation Command Outputs Verification
Run the citation parser CLI directly to ensure APA, MLA, Chicago, and BibTeX outputs are rendered using the generic repository URL:
```bash
/home/gfariello/venv/p3.14/bin/python -m pubrun cite apa
/home/gfariello/venv/p3.14/bin/python -m pubrun cite MLA
/home/gfariello/venv/p3.14/bin/python -m pubrun cite Chicago
/home/gfariello/venv/p3.14/bin/python -m pubrun cite bibtex
```

### Packaging & Render Check
Compile a new wheel locally and run a twine validation check to confirm the edited README description renders correctly for PyPI packaging:
```bash
rm -rf dist/*
/home/gfariello/venv/p3.14/bin/python -m build
/home/gfariello/venv/p3.14/bin/twine check dist/*
```
