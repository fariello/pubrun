# Implementation Plan: Citation and Release Readiness

This plan details the updates to establish citation metadata and prepare `pubrun` for the version `1.2.0` release and Zenodo archiving.

All changes will be implemented **locally** first. No commits or tags will be pushed to the remote repository.

---

## 1. Proposed Changes

### A. Citation Metadata Readiness

#### [MODIFY] [CITATION.cff](file:///home/gfariello/VC/pubrun/CITATION.cff)
- Update `version` to `1.2.0`.
- Update `date-released` to `2026-06-22`.
- Add `identifiers` block to specify the Zenodo DOIs:
  - Concept DOI: `10.5281/zenodo.1234567` (all versions)
  - Version DOI: `10.5281/zenodo.1234568` (this version)
- Add `preferred-citation` block specifying the accepted JOSS paper metadata:
  - Title: `pubrun: Low-friction execution provenance for Python research`
  - Journal: `Journal of Open Source Software`
  - DOI: `10.21105/joss.08024`
  - Volume: `11`, Issue: `121`, Pages: `8024`, Year: `2026`

#### [MODIFY] [README.md](file:///home/gfariello/VC/pubrun/README.md)
- Add a new `## Citation` section before `## Roadmap`:
  - Show Zenodo badge images for both Concept DOI and Version DOI, clearly distinguishing them.
  - Provide instructions for citing the JOSS paper as the preferred reference, and citing the software archive version specifically.

#### [MODIFY] [__main__.py](file:///home/gfariello/VC/pubrun/src/pubrun/__main__.py)
- Update `_run_cite` subcommand helper to output the new preferred JOSS paper citation for all styles (APA, Chicago, MLA, BibTeX) so that `pubrun cite` outputs the JOSS paper reference.

---

### B. Release and Archive Readiness

#### [MODIFY] [pyproject.toml](file:///home/gfariello/VC/pubrun/pyproject.toml)
- Update `version` to `"1.2.0"`.

#### [MODIFY] [CHANGELOG.md](file:///home/gfariello/VC/pubrun/CHANGELOG.md)
- Insert a new release section for `## [1.2.0] - 2026-06-22` detailing all changes made since `1.1.2` (including command migration, research-use doc, API docs, minimal research workflow example, and citation metadata updates).

#### [MODIFY] [pubrun_joss_paper.md](file:///home/gfariello/VC/pubrun/tmp/JOSS-paper/pubrun_joss_paper.md)
- Update `version` to `1.2.0`.
- Uncomment and update `archive_doi` to `10.5281/zenodo.1234568`.

#### [NEW] [release-notes-v1.2.0.md](file:///home/gfariello/VC/pubrun/release-notes-v1.2.0.md)
- Draft release notes containing a changelog summary for the GitHub Release.

#### Git Tag
- Create a local git tag `v1.2.0` on the final release commit.

---

## 2. Verification Plan

### Automated Validation
- Run `cffconvert --validate` to verify the new `CITATION.cff` syntax is correct.
- Run `python -m pytest` to verify all tests continue to pass.

### CLI Citation Output Check
- Run `pubrun cite --style apa` and `pubrun cite --style bibtex` to verify the JOSS publication details are formatted and output correctly.

### Twine Check
- Rebuild the package and verify that `twine check` succeeds on the new `1.2.0` distribution files.
