# Review findings: ipd 3u1xgk

- Subject-Id: 3u1xgk
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-b3dejs-01-3u1xgk-avoid-loading-pubrun-capture-packages-from-report-methods-py.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Updated the Mermaid diagram `PKG` label to list both re-exported symbols (`_PEP503_RE, normalize_package_name`), replaced `N/A.` with `Not applicable.` in `## Spec / documentation sync`, and aligned prose across `## Goal`, `E-03`, `E-04`, `## Project conventions discovered`, `V-01..V-04`, and `## Approval and execution gate` with the verified repository behavior and review findings (`PR-001`, `PR-002`, `PR-003`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Goal`, `E-03` Expected outcome, `## Project conventions discovered` bullet 4 | Stated that importing `pubrun.report.methods` directly leaves `pubrun.capture.packages` and `importlib.metadata` unloaded without stating the non-auto-start import-mode precondition | Qualified direct import isolation with a non-auto-start import mode (`pubrun.minimal`, `pubrun.noauto`, or `PUBRUN_IMPORT_MODE=minimal` with `PUBRUN_RUN_MODE_OVERRIDE=""`) and documented `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress` | Make import-boot precondition explicit and factually accurate (`PR-001`, technical writing standard Req 5) |
| `### Module import and run-stop dependency flow` | `PKG` node label listed only `re-exports normalize_package_name` | Updated `PKG` node label to `re-exports _PEP503_RE, normalize_package_name` | Match `E-02` symbols in Mermaid diagram (technical writing standard Req 12(e), `PR-003`) |
| `E-04` bullet 2 | Fresh-subprocess test imported `pubrun.report.methods` without `pubrun.minimal` and passed `"zope.interface"` beside `"Scikit_Learn"` without asserting `"zope-interface"` rendering | Added `import pubrun.minimal` before importing `pubrun.report.methods` and split manifest checks to assert both highlighted `"scikit-learn (v1.5.0)"` and non-highlighted `"zope-interface (v6.0)"` | Prevent auto-start failure (`PR-001`) and exercise `_extract_valid_packages` normalization (`PR-003`) |
| `## Spec / documentation sync` | Started with `N/A.` | Replaced `N/A.` with `Not applicable.` | Expand abbreviation per technical writing standard Req 1 (`PR-003`) |
| `V-01`, `V-02`, `V-03`, `V-04` | `V-01`/`V-02` lacked `PUBRUN_IMPORT_MODE=minimal PUBRUN_RUN_MODE_OVERRIDE=""`; `V-03` lacked concrete temp-dir-isolated subprocess commands and direct `methods` isolation check; `V-04` treated test function names as pass bars | Added `PUBRUN_IMPORT_MODE=minimal PUBRUN_RUN_MODE_OVERRIDE=""` to `V-01`/`V-02`; added two concrete `TemporaryDirectory()`/minimal-mode subprocess commands to `V-03`; rephrased `V-04` around pinned behaviors with test names as non-binding pointers subject to execution-time re-derivation | Fix failing/dirtying validation commands (`PR-001`) and satisfy `r2-executability.md` evidence and re-derivation rules (`PR-003`) |
| `## Approval and execution gate` clause 2 | Instructed executor to "stop and report" on any out-of-scope edit or untouched declared file | Rewrote clause 2 to direct justifying genuinely required scope deltas via `--scope-reason`/`--scope-ack` at finalization and reserving stop-and-report for genuinely unsafe conditions | Comply with 2026-09-01 scope-fence wording ruling in `s7-finalize.md:37-46` (`PR-002`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: b3dejs`, `- Order: 1`, `- Scope-Paths:` (`src/pubrun/_pep503.py, src/pubrun/capture/packages.py, src/pubrun/report/methods.py, tests/test_import_modes.py, tests/test_package_resolution.py`), 4 E-items in 2 task groups, no `.spec.md` file.

1. Yes: extracts `normalize_package_name` and `_PEP503_RE` from `src/pubrun/capture/packages.py` into a new internal module `src/pubrun/_pep503.py` while preserving the PEP 561 re-export contract relied upon by `src/pubrun/report/reproducibility.py`, existing test suites, and downstream typed callers.
2. No: none of the five files in `- Scope-Paths:` guard private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 4 focused E-items in 2 task groups across 3 closely related source modules and 2 test files.
4. Yes: `- Scope-Paths:` explicitly lists all 5 files (`src/pubrun/_pep503.py`, `src/pubrun/capture/packages.py`, `src/pubrun/report/methods.py`, `tests/test_import_modes.py`, `tests/test_package_resolution.py`).
5. No: the refactor is local and easily reversible, and no persistent data format or irreversible migration is touched.

AW-TIER: standard

### Step R1

- Checked: every file, symbol, config key, and record cited in `3u1xgk` against the repository: `.aw/records/backlog/graduated/20261127-b3dejs-01-b3dejs-avoid-loading-pubrun-capture-packages-from-report.backlog.md`, `.aw/records/plans/executed/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md`, `pyproject.toml`, `src/pubrun/py.typed`, `src/pubrun/__init__.py` (`_get_version`, `_resolve_version`, `_is_mode_import`, `_execute_boot_sequence`), `src/pubrun/_bootstrap.py` (`is_mode_submodule_import_in_progress`, `select_mode`), `src/pubrun/_config_boot.py`, `src/pubrun/_modes.py`, `src/pubrun/minimal.py`, `src/pubrun/core.py` (`_execute_boot_sequence`), `src/pubrun/tracker.py` (`_call_get_packages`, `Run._refresh_packages_at_finalization`, `Run.to_manifest_dict`), `src/pubrun/writer.py` (`ArtifactWriter.write_artifacts`), `src/pubrun/capture/packages.py` (`_PEP503_RE`, `normalize_package_name`, `_EXTRA_MARKER_RE`), `src/pubrun/capture/_markers.py` (`_PEP503_RE`, `_normalize_name`), `src/pubrun/report/__init__.py`, `src/pubrun/report/methods.py` (`_NORMALIZED_HIGHLIGHTS`, `_extract_valid_packages`, `extract_highlighted_packages`, `generate_report`, `generate_report_multi`), `src/pubrun/report/templates.py`, `src/pubrun/report/file_evidence.py`, `src/pubrun/report/reproducibility.py`, `tests/test_import_modes.py` (`TestModePep561AndColdStart::test_packages_mode_off_keeps_packages_module_unloaded`), `tests/test_package_resolution.py` (`test_normalize_package_name_pep503`), `tests/test_report_subpackage_integrity.py` (`test_no_mode_module_shadows_a_pubrun_subpackage`), and presence of all nine test files in Command 1.
- Verified: all cited paths and symbols exist and match their descriptions, with one factual contradiction uncovered by reading `src/pubrun/__init__.py:443-470`, `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress:307-335`, and `src/pubrun/core.py::_execute_boot_sequence:982-1026`: importing `pubrun._pep503` or `pubrun.report.methods` without selecting a non-auto-start mode triggers `pubrun` auto-start, writing `runs/` and loading both `pubrun.capture.packages` and `importlib.metadata` (`PR-001`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-04` <-> `V-01..V-04`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:p4ueaj`, runtime-demonstration reachability for every `V-*` item, re-derivation convention (`r2-executability.md:65`), and the five-clause execution contract including 2026-09-01 scope-fence wording (`s7-finalize.md:37-46`).
- Verified: `PR-001` made `V-01`, `V-02`, and `E-04` bullet 2 runnable without triggering `pubrun` auto-start; `PR-002` removed the prohibited "stop and report" scope-delta directive from `## Approval and execution gate` clause 2; `PR-003` added concrete `TemporaryDirectory()`/minimal-mode subprocess commands to `V-03` covering both `pubrun.minimal.stop()` and direct `pubrun.report.methods` isolation and rephrased `V-04` so pinned behaviors are the bar while test function names are non-binding pointers subject to execution-time re-derivation.

### Step R3

- Checked: full security and privacy rubric (`r3-security.md` B) across `src/pubrun/_pep503.py`, `src/pubrun/capture/packages.py`, `src/pubrun/report/methods.py`, and validation commands.
- Verified: `_PEP503_RE = re.compile(r"[-_.]+")` is a linear-time character-class regex with no catastrophic backtracking (ReDoS) risk; no secrets, network calls, external commands, privilege paths, or sensitive data logging are introduced; adding `PUBRUN_IMPORT_MODE=minimal`, `PUBRUN_RUN_MODE_OVERRIDE=""`, and `tempfile.TemporaryDirectory()` to `V-01..V-03` (`PR-001`, `PR-003`) prevents unintended side-effect writes into the repository working tree.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - A/C: extracting `_PEP503_RE` and `normalize_package_name` to `src/pubrun/_pep503.py` (pure `re`, Python 3.8-3.14 compatible, auto-packaged by Hatch and checked by `mypy`) with explicit PEP 561 re-exports in `src/pubrun/capture/packages.py` cleanly breaks the `report -> capture` import edge while keeping `import re` in `packages.py` (still used by `_EXTRA_MARKER_RE`). Leaving `src/pubrun/capture/_markers.py` untouched avoids unrelated churn.
  - D/E: all four invariants (`mode == "off"` full lifecycle through `stop()` + `methods.md`; direct `report.methods` isolation under non-auto-start mode for both highlighted and non-highlighted package rendering; shared identity + PEP 561 re-export under `mypy --strict --no-implicit-reexport`; no subpackage shadowing) map to concrete behavioral tests and validation commands after `PR-001` and `PR-003`.
  - Right-sizing: 4 E-items in 2 task groups across 5 Scope-Paths; each E-item is a single-concern pass suitable for a modest executor. No split warranted.
  - `## Spec / documentation sync`: substantiated (no CLI, config, schema, or public API changes).

### Step S5

- Checked: `## Open questions` contains `None.`. All three findings (`PR-001`, `PR-002`, `PR-003`) had `Low` overall Remediation Risk, were settled by repository code and documented workflow rules, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` A, E | `.aw/records/plans/pending/20261127-b3dejs-01-3u1xgk-avoid-loading-pubrun-capture-packages-from-report-methods-py.ipd.md:29,74,81,94,140,145` vs `src/pubrun/__init__.py:443-470`, `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress:307-335`, `src/pubrun/core.py::_execute_boot_sequence:982-1026` | `V-01`, `V-02`, `E-04` bullet 2, `## Goal`, `E-03` Expected outcome, and `## Project conventions discovered` bullet 4 assumed importing `pubrun._pep503` or `pubrun.report.methods` directly in a fresh subprocess does not start a run or load `pubrun.capture.packages`/`importlib.metadata`. Because `is_mode_submodule_import_in_progress` only exempts the six mode submodules, a bare import under default `auto` mode runs `_execute_boot_sequence()`, auto-starts a run (creating `runs/` in `cwd`), and loads both `pubrun.capture.packages` and `importlib.metadata`, causing `V-01` and `E-04` bullet 2 to fail and `V-02` to pollute the workspace. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Qualified non-auto-start import mode (`pubrun.minimal`, `pubrun.noauto`, or `PUBRUN_IMPORT_MODE=minimal` with `PUBRUN_RUN_MODE_OVERRIDE=""`) across `## Goal`, `E-03` Expected outcome, `E-04` bullet 2, `## Project conventions discovered` bullet 4, `V-01`, and `V-02` (recommendation strength: `very strong`). |
| PR-002 | MEDIUM | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` (Scope-fence wording) | `.aw/records/plans/pending/20261127-b3dejs-01-3u1xgk-avoid-loading-pubrun-capture-packages-from-report-methods-py.ipd.md:165` vs `.aw/system/workflows/plan-review/steps/s7-finalize.md:37-46` | `## Approval and execution gate` clause 2 instructed the executor to "stop and report" if execution appears to require touching an additional file or leaving a declared file untouched, violating the 2026-09-01 maintainer scope-fence ruling in `s7-finalize.md:37-46`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote clause 2 to declare expected paths, direct justifying genuinely necessary deltas with `--scope-reason`/`--scope-ack` at finalization rather than stopping mid-run, and reserve stop-and-report for genuinely unsafe conditions (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` E / `p-proofread.md` | `.aw/records/plans/pending/20261127-b3dejs-01-3u1xgk-avoid-loading-pubrun-capture-packages-from-report-methods-py.ipd.md:36,81,129,150,155` vs `src/pubrun/report/methods.py::generate_report:293-308`, `.aw/system/workflows/plan-review/steps/r2-executability.md:65`, `.aw/system/workflows/technical-writing/technical-writing.md:29,45` | (1) `E-04` bullet 2 passed `"zope.interface"` in the same manifest as highlighted `"Scikit_Learn"`, where `generate_report` short-circuits on highlighted packages and never exercises `_extract_valid_packages` on `"zope.interface"`; (2) `V-03` lacked concrete temp-dir-isolated subprocess commands and omitted checking direct `pubrun.report.methods` isolation; (3) `V-04` treated specific test function names as pass bars instead of non-binding pointers with execution-time re-derivation; (4) Mermaid `PKG` label omitted `_PEP503_RE` and `## Spec / documentation sync` used `N/A.`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-04` bullet 2 to test both highlighted `"Scikit_Learn"` and non-highlighted `"zope.interface"` manifests; added two concrete `TemporaryDirectory()`/minimal-mode subprocess commands to `V-03`; rephrased `V-04` around pinned behaviors with execution-time re-derivation; updated Mermaid `PKG` label and expanded `N/A.` to `Not applicable.` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `3u1xgk` | `standard` | `simple`, `complex` | Preserves a shared PEP 561 module export contract (`pubrun.capture.packages.normalize_package_name` -> `pubrun._pep503`) relied upon by `reproducibility.py` and tests (tier question 1 = Yes), while remaining a small 4-item refactor with no security/sandbox surface (`steps/t-tier.md`). | yes |
| D-2 | How to verify direct `pubrun._pep503` and `pubrun.report.methods` import isolation without triggering `pubrun` auto-start | Select non-auto-start mode (`pubrun.minimal` or `PUBRUN_IMPORT_MODE=minimal` with `PUBRUN_RUN_MODE_OVERRIDE=""`) in fresh subprocesses | Expand `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress` to exempt internal/report submodules | `src/pubrun/__init__.py:443-470`, `src/pubrun/_bootstrap.py:307-335`, `tests/test_import_modes.py::TestModePep561AndColdStart:1456-1514`, and backlog `b3dejs` (which scopes only decoupling `report/methods.py` from `capture/packages.py`, not altering `pubrun` root auto-start semantics). | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; every revision (`PR-001`, `PR-002`, `PR-003`) was swept across `## Goal`, the Mermaid diagram, `E-03`, `E-04`, `## Project conventions discovered`, `## Spec / documentation sync`, `V-01..V-04`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
