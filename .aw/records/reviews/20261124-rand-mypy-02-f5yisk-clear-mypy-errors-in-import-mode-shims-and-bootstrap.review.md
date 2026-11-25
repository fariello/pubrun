# Review findings: ipd f5yisk

- Subject-Id: f5yisk
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-rand-mypy-02-f5yisk-clear-mypy-errors-in-import-mode-shims-and-bootstrap.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `cadf615` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(b), (d), and (e) are satisfied by the Mermaid ratchet flowchart.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Mermaid node A, Project conventions, Findings, Deferred | Stated `gzc672` was `approved` and listed 20 legacy modules (13 remaining), omitted `pubrun.capture.subprocesses` from the override and `z5xr49` from its comment, and omitted `update-commit-file` from `.pre-commit-config.yaml` | Reflects executed `gzc672`, 21 legacy modules (14 remaining), `pubrun.capture.subprocesses` on the override list, `qqwebg and z5xr49` comment, and `update-commit-file` post-commit hook | Factual accuracy against current `pyproject.toml`, executed `gzc672`, and `.pre-commit-config.yaml` (PR-002). |
| E-01 Expected outcome and V-01 (2) | Used nonexistent `PUBRUN_DISABLE=1` and `HOME=<scratch dir>` without `PYTHONPATH=src` | Uses a `tempfile.TemporaryDirectory()` (`cwd`) subprocess probe with `PYTHONPATH` pointing at the checkout's `src/`, verifying `mod.__file__` resolves inside the checkout and leaving no `runs/` directory | Prevents working-tree pollution and vacuous imports from another checkout's editable install (PR-001). |
| E-03, Required tests / validation, V-01 (3), V-03 | V-01..V-03 omitted three of the six required test files, mutation checks did not pass `--no-incremental`, and `58 source files` was hardcoded without execution-time re-derivation | Runs all six required test files in V-01 (3), uses `mypy --no-incremental` for ratchet mutation checks, and notes execution-time re-derivation for the source file count (`58` at review) | Check R2 validation completeness, cache safety, and re-derivation convention (PR-003). |
| E-01, E-02, Findings, Gate item 5 | Cited `_bootstrap._get_caller_info` without `path::Symbol`, quoted `# Populate the parent pubrun namespace` as an exact single-line comment (differs in `noauto.py`), and opened Gate item 5 unconditionally | Uses Section 11.1 `path::Symbol` citations, refers to the comment block accurately, and states conditional runner/executor ownership in Gate item 5 | Section 11.1 citation rules and Check S7 execution-contract rule (PR-004, PR-005). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/auto.py`, `full.py`, `minimal.py`, `noauto.py`, `noconsole.py`, `nopatch.py`, `_bootstrap.py`, `pyproject.toml`), 3 E-items in 2 task groups, `- Kind: child`.

1. Yes (bounded): edits `[tool.mypy.overrides]` in `pyproject.toml` (shared ratchet contract across the `rand-mypy` Set and CI `typecheck` gate) and all six public import-mode modules (`pubrun.auto`, `full`, `minimal`, `noauto`, `noconsole`, `nopatch`) plus `pubrun._bootstrap`.
2. No: touches no code guarding private data, commits, worktree isolation, merges to `main`, or the sandbox.
3. No: 3 focused E-items across 2 task groups applying a uniform 3-line typing change in 6 shims, 3 lines in `_bootstrap.py`, and 7 entry deletions in `pyproject.toml`.
4. Yes: `src/pubrun/auto.py`, `src/pubrun/full.py`, `src/pubrun/minimal.py`, `src/pubrun/noauto.py`, `src/pubrun/noconsole.py`, `src/pubrun/nopatch.py`, `src/pubrun/_bootstrap.py`, `pyproject.toml`.
5. Yes (bounded): an import-time error or leaked/missing attribute in the six mode shims or `_bootstrap.py` would break `import pubrun.<mode>` for users, though `tests/test_import_modes.py` catches breakage and the diff is small and easy to revert.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/_bootstrap.py` (lines 1-284, verifying `import warnings`, `Optional` import, `_get_caller_info` line 152 and `frame = frame.f_back` line 166, `is_mode_submodule_import_in_progress` line 273 and line 281); all six import-mode modules (`src/pubrun/auto.py:52-78`, `full.py:57-83`, `minimal.py:50-76`, `noauto.py:52-79`, `noconsole.py:45-71`, `nopatch.py:47-73`, verifying exact `import pubrun as _pkg  # noqa: E402` and `del _pkg` lines); `pyproject.toml:106-141`; `.pre-commit-config.yaml:1-42`; `.aw/records/plans/executed/20261123-test-audit-02-gzc672-mypy-type-check-repair-and-ci-type-gate.ipd.md`; all six named test files exist; `grep -rn "PUBRUN_" src/pubrun/`; `mypy --no-incremental` (`Success: no issues found in 58 source files`, exit 0); and `MYPYPATH=src mypy --config-file /dev/null --explicit-package-bases --ignore-missing-imports --no-incremental --follow-imports=silent` on the 7 target files (`Found 20 errors in 7 files`: 18 `Cannot assign to a type [misc]` + 2 `Incompatible types in assignment [assignment]`).
- PR-001: `grep -rn "PUBRUN_DISABLE" src/pubrun/` returned zero matches (nonexistent env var), `pubrun` writes `runs/` to CWD rather than `HOME`, and omitting `PYTHONPATH=src` imported the editable install outside the worktree. Fixed in E-01 and V-01 (2).
- PR-002: `pyproject.toml:115-141` lists 21 modules (not 20) including `pubrun.capture.subprocesses` with comment citing `qqwebg and z5xr49`, `gzc672` is now `executed`, and `.pre-commit-config.yaml:36-42` also defines `update-commit-file`. Fixed across Mermaid node A, Project conventions, Findings, and Deferred.
- PR-005: fixed `noauto.py` comment description and applied Section 11.1 `path::Symbol` citations in E-02 and Findings.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-03` to `V-01`..`V-03`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:gzc672, executed:m66tfv`, runtime-demonstration reachability of V-01 (2) (subprocess imports of the six E-01 modules) and V-03 (3) (`mypy --no-incremental` after E-03 removes the seven overrides), alignment of `Required tests / validation` with `V-01`..`V-03`, and all five execution-contract elements in the gate.
- PR-001: replaced the broken `PUBRUN_DISABLE=1 HOME=...` check with an isolated `tempfile.TemporaryDirectory()` + `PYTHONPATH=src` subprocess probe verified locally to pass for all six mode modules with zero untracked files left behind.
- PR-003: aligned V-01 (3) with all six test files in `Required tests / validation`, added `--no-incremental` to mutation checks in `Required tests / validation` and V-03 (3), and added execution-time re-derivation wording for `58 source files`.
- PR-004: updated Gate item 5 to state conditional runner/executor finalization ownership explicitly.

### Step R3

- Checked: all five bullets of Check R3 full form. The changes are pure static type annotations (`_Any`, `FrameType`, `Optional[FrameType]`) and `pyproject.toml` `ignore_errors` removals; no authentication, authorization, secrets, network calls, subprocess changes, or sensitive logging surfaces are touched. The V-01 probe runs in an isolated temporary directory without shell interpolation, and V-03 runs `python3 scripts/sanitize_paths.py --check --all`. No finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (3 single-concern E-items across 2 task groups; uniform typing edits across the 6 shims are one cohesive concern; no splitting warranted); Python 3.8 syntax compatibility (`from typing import Any as _Any`, `from types import FrameType`, `Optional[FrameType]`); anti-regression (deleting `_pkg, _pkg_module, _Any` preserves the exact public namespace of all six shims; `tests/test_import_modes.py` and five related suites pin runtime behavior); spec and documentation sync (no `.spec.md` or `docs/` file mentions `mypy`; `0uxy76` updates `CONTRIBUTING.md` and `CHANGELOG.md` once the full burn-down completes). No additional findings beyond PR-001..PR-005.

### Step S5

- Checked: `## Open questions` is `None.`. Every review finding PR-001..PR-005 had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1 / R2 (nonexistent `PUBRUN_DISABLE`, CWD pollution, missing `PYTHONPATH=src`) | Plan `E-01` (line 64), `V-01` (line 147); `grep -rn "PUBRUN_DISABLE" src/pubrun/` (0 matches); default `import pubrun` path outside worktree | `PUBRUN_DISABLE` does not exist in `src/pubrun/`, `HOME` does not redirect `runs/` created in CWD by auto-starting mode modules, and omitting `PYTHONPATH=src` imports another checkout's editable install in runner worktrees. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the E-01 Expected outcome and V-01 (2) probe with a `tempfile.TemporaryDirectory()` (`cwd`) + `PYTHONPATH=src` subprocess check asserting `mod.__file__` is inside the checkout's `src/` and zero leaked `_pkg`/`_pkg_module`/`_Any` attributes. |
| PR-002 | MEDIUM | IN-SCOPE | R1 (stale post-`gzc672` override count, comment, and pre-commit hooks) | `pyproject.toml:115-141` (21 modules including `pubrun.capture.subprocesses`, `qqwebg and z5xr49`); `.pre-commit-config.yaml:36-42` (`update-commit-file`); Plan lines 37, 84, 87, 100, 116 | Plan stated `gzc672` was unexecuted with 20 legacy modules (13 remaining) excluding `pubrun.capture.subprocesses`, cited only `qqwebg` in the comment, and omitted `update-commit-file` from `.pre-commit-config.yaml`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Mermaid node A, Project conventions, Findings (preserving historical measurement while noting post-`gzc672` state), and Deferred (`14 legacy modules`). |
| PR-003 | MEDIUM | IN-SCOPE | R2 (test-coverage gap between Required tests and V-items, cache safety, re-derivation) | Plan `E-03` (line 79), `Required tests / validation` (lines 128-130), `V-01` (line 147), `V-03` (line 157) | Three of the six test files in `Required tests / validation` (`test_capture_isolation.py`, `test_report_subpackage_integrity.py`, `test_profile_deprecation.py`) were not demanded by any `V-*` item; ratchet mutation checks ran `mypy` without `--no-incremental`; `58 source files` was hardcoded without execution-time re-derivation. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated V-01 (3) to run all six required test files, added `--no-incremental` to mutation checks in Required tests and V-03 (3), and noted execution-time re-derivation for the source file count (`58` at review). |
| PR-004 | LOW | IN-SCOPE | S7 / R2 (execution contract runner/executor finalize ownership) | Plan `Approval and execution gate` item 5 (line 171); `steps/s7-finalize.md:33-36` | Gate item 5 opened with an unconditional `aw ipd finalize f5yisk` instruction without stating runner ownership inside `aw oc run` / `aw agy run`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Gate item 5 to state conditional runner/executor finalization ownership explicitly. |
| PR-005 | LOW | IN-SCOPE | Check P / Section 11.1 (symbol citations and `noauto.py` comment anchor) | Plan `E-01` (line 53), `E-02` (lines 68-69), `Findings` (line 95); `src/pubrun/noauto.py:52-53`, `src/pubrun/_bootstrap.py:148,256` | E-01 quoted `# Populate the parent pubrun namespace` as an exact line (in `noauto.py` it has trailing prose), and E-02/Findings cited `_bootstrap` functions without `path::Symbol` syntax. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Clarified E-01 to refer to the `# Populate the parent pubrun namespace` comment block and updated E-02 and Findings to `src/pubrun/_bootstrap.py::...` citations. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Edits the shared `[tool.mypy.overrides]` ratchet in `pyproject.toml` and six public import-mode modules plus `_bootstrap.py`, with 3 focused E-items. | yes |
| D-2 | Keep `Deferred / out of scope` carrier for remaining 14 legacy modules pointing at `qe6dad` (naming `qe6dad`, `k6fs5k`, `0uxy76` in prose) | Keep `- Carrier: qe6dad` with updated 14-module count naming all three sibling carriers | Split into three separate deferred bullets | All three sibling child plans are already authored in Set `rand-mypy` and named in the prose; keeping one carrier line stays concise and lint-clean. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All five findings (PR-001..PR-005) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
