# Review findings: ipd qe6dad

- Subject-Id: qe6dad
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-rand-mypy-03-qe6dad-clear-mypy-errors-in-analysis-report-config-status-and-event.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `8d2fd7c` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(b), (d), and (e) are satisfied by the Mermaid ratchet flowchart.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Mermaid node A, E-05, Project conventions, Findings, Required tests / validation, V-05 (2) | Assumed `gzc672` was unexecuted with 20 override entries excluding `pubrun.capture.subprocesses`, allowed `mypy` exit 1 on `capture/subprocesses.py`, and piped `mypy 2>&1 \| tail -5` | Reflects executed `gzc672` (21 override entries including `pubrun.capture.subprocesses`), requires `mypy` exit 0 with `Success: no issues found in <N> source files` (`58` at review; re-derive at execution time) | Aligns validation with current `pyproject.toml` and prevents masking `mypy` exit status (PR-001). |
| E-03, Project conventions, V-03 (4) | Cited `src/pubrun/status.clean_runs` (invalid path), assumed `EXIT` is always the 5th whitespace-split token even when `argv` has extra arguments, and asked `git diff --stat` for "2 changed lines" | Uses `src/pubrun/status.py::clean_runs`, warns that extra `argv` arguments insert a space inside `SCRIPT` so tests should slice by header offset or pass a single-token `argv`, and asks `git diff --stat` for `2 insertions(+), 2 deletions(-)` | Citation accuracy and preventing fragile test/stat checks (PR-002). |
| Required tests / validation and V-05 (3) | Ran ratchet mutation checks with bare `mypy` without checking `exit=1` | Uses `mypy --no-incremental; echo "exit=$?"` asserting an `error:` line for the mutated file and `exit=1` | Prevents stale `.mypy_cache` interference and verifies non-zero exit (PR-003). |
| E-01, E-04, Findings, Gate item 5 | Claimed `_format_array_diff` tests membership on `added_set`/`removed_set`, said E-01 is "five lines plus the import", said "Add `Tuple` ... if it is not already there" in `diagnostics.py`, lacked Section 11.1 `::` citations, and opened Gate item 5 unconditionally | Fixes `_format_array_diff` description, E-01 line count (four lines plus one import = five total), notes `Tuple` is already imported on `diagnostics.py:5`, applies Section 11.1 `path::Symbol` citations, and states conditional runner/executor finalize ownership in Gate item 5 | Factual accuracy, Section 11.1 citations, and Check S7 execution-contract rule (PR-004, PR-005). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/analysis/diff.py`, `src/pubrun/analysis/render.py`, `src/pubrun/config.py`, `src/pubrun/status.py`, `src/pubrun/events.py`, `src/pubrun/report/diagnostics.py`, `tests/test_status_clean_table.py`, `pyproject.toml`), 5 E-items in 2 task groups, `- Kind: child`.

1. Yes (bounded): modifies `[tool.mypy.overrides]` in `pyproject.toml` (shared ratchet contract across Set `rand-mypy` and CI `typecheck`) and edits six modules across analysis, config, status, events, and report diagnostics.
2. No: touches no code guarding private data, commits, worktree isolation, merges to `main`, or the sandbox.
3. No: 5 focused E-items across 2 task groups within standard sizing guidance (5 E-items, 8 Scope-Paths); all code edits are local annotations plus one local display-variable rename.
4. Yes: `src/pubrun/analysis/diff.py`, `src/pubrun/analysis/render.py`, `src/pubrun/config.py`, `src/pubrun/status.py`, `src/pubrun/events.py`, `src/pubrun/report/diagnostics.py`, `tests/test_status_clean_table.py`, `pyproject.toml`.
5. Yes (bounded): a mistake in `status.clean_runs` (which deletes run directories), `events.EventStream`, or `config.load_local_config` could affect runtime behavior, though the edits are pure type annotations plus one display-variable rename backed by a new behavioral test and mutation check, and are easy to revert.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/analysis/diff.py` (lines 4, 38, 114, 118, 130, 139, 242); `src/pubrun/analysis/render.py` (lines 6, 23-41, 133-134); `src/pubrun/config.py` (lines 6, 117); `src/pubrun/events.py` (lines 5, 47-58, 124, 146, 156, 171); `src/pubrun/status.py` (lines 1424-1470, verifying `clean_runs` table headers and lines 1451, 1460); `src/pubrun/report/diagnostics.py` (lines 5, 377, 781-784, 1117, 1227); `tests/test_status_bugs.py` (lines 29-44 `_make_completed`); `pyproject.toml:115-141`; all 10 existing test files in line 96 exist; and ran `MYPYPATH=src mypy --config-file /dev/null --explicit-package-bases --ignore-missing-imports --no-incremental --follow-imports=silent` on the six target files (`Found 20 errors in 6 files`: 5 in `diff.py`, 4 in `render.py`, 1 in `config.py`, 5 in `events.py`, 1 in `status.py`, 4 in `diagnostics.py`).
- PR-001: `pyproject.toml:115-141` already lists 21 modules including `pubrun.capture.subprocesses` (`gzc672` executed), so `mypy` already exits 0 on `main` and must exit 0 after E-05. Fixed.
- PR-002: `E-03` cited invalid path `src/pubrun/status.clean_runs`, and `tests/test_status_bugs.py:38` uses `"argv": [f"{script}.py", "--epochs=3"]` which embeds a space in `SCRIPT` (`status.py:1446`). Fixed.
- PR-004: `src/pubrun/analysis/render.py:39-40` only iterates over `added_set`/`removed_set`, E-01 changes 4 lines + 1 import = 5 lines total, and `src/pubrun/report/diagnostics.py:5` already imports `Tuple`. Fixed along with Section 11.1 `path::Symbol` citations.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-05` to `V-01`..`V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:gzc672, executed:m66tfv`, alignment of all 11 test files between `Required tests / validation` and `V-01`..`V-05`, runtime-demonstration reachability of V-03 (4) (`status.clean_runs` mutation test) and V-05 (3) (`mypy --no-incremental` ratchet mutation checks), and all five execution-contract elements in the gate.
- PR-001: tightened `E-05`, `Required tests / validation`, and `V-05 (2)` to require `mypy` exit 0 with `Success: no issues found in <N> source files` (`58` at review; re-derive at execution time), removing the stale `capture/subprocesses.py` exit-1 loophole and `| tail -5` pipe.
- PR-002: corrected `V-03 (4)` `git diff --stat` expectation to `2 insertions(+), 2 deletions(-)`.
- PR-003: added `--no-incremental` and explicit `exit=1` verification to the `Required tests / validation` and `V-05 (3)` mutation checks.
- PR-005: updated Gate item 5 to state conditional runner/executor finalization ownership explicitly.

### Step R3

- Checked: all five bullets of Check R3 full form. The code edits are pure static type annotations plus renaming one display string local (`exit_code` -> `exit_str`) in `status.clean_runs` (after `filter_runs` has already used the `exit_code` filter parameter, reducing shadowing risk). No authentication, authorization, secrets, network calls, subprocess changes, or sensitive logging surfaces are touched. `V-05` runs `python3 scripts/sanitize_paths.py --check --all`. No finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (5 single-concern E-items across 2 task groups, 8 Scope-Paths; each is executable in one focused pass; no splitting warranted); Python 3.8 syntax compatibility (`Dict`, `List`, `Optional`, `Tuple`, `Iterable`, `TextIO`); anti-regression (E-03 adds behavioral test `tests/test_status_clean_table.py` with mutation check for the only non-annotation edit); spec and documentation sync (no `.spec.md` or `docs/` file mentions `mypy`; `0uxy76` updates `CONTRIBUTING.md` and `CHANGELOG.md` once the burn-down completes). No additional findings beyond PR-001..PR-005.

### Step S5

- Checked: `## Open questions` is `None.`. Every review finding PR-001..PR-005 had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1 / R2 (stale post-`gzc672` override state weakening `mypy` exit gate) | `pyproject.toml:115-141` (`pubrun.capture.subprocesses` listed; 21 modules); Plan lines 35, 87, 92-93, 111, 139, 178 | Plan assumed `gzc672` was unexecuted with 20 modules excluding `pubrun.capture.subprocesses`, allowing `mypy` exit 1 on `capture/subprocesses.py` in V-05 (2) and masking exit status via `mypy 2>&1 \| tail -5` in Required tests. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Mermaid node A, Project conventions, Findings, E-05, Required tests, and V-05 (2) to reflect executed `gzc672` (21 entries) and require `mypy` exit 0 (`Success: no issues found in <N> source files`, `58` at review; re-derive at execution time). |
| PR-002 | MEDIUM | IN-SCOPE | R1 / R2 (`status.clean_runs` path typo, `SCRIPT` column spacing, `diff --stat` wording) | Plan `E-03` (line 70), `Project conventions` (line 95), `V-03` (line 168); `src/pubrun/status.py:1446`; `tests/test_status_bugs.py:38` | E-03 cited invalid path `src/pubrun/status.clean_runs`; `_make_completed` uses two-token `argv` which inserts a space in `SCRIPT` and shifts whitespace column splitting; V-03 (4) asked `git diff --stat` for "2 changed lines" instead of `2 insertions(+), 2 deletions(-)`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated to `src/pubrun/status.py::clean_runs`, documented header-offset slicing or single-token `argv` for `tests/test_status_clean_table.py`, and updated V-03 (4) `git diff --stat` expectation. |
| PR-003 | MEDIUM | IN-SCOPE | R2 (ratchet mutation check cache safety and exit status) | Plan `Required tests / validation` (line 140), `V-05` (line 178) | Ratchet mutation checks ran bare `mypy` without `--no-incremental` (risking stale `.mypy_cache`) and did not require `exit=1` explicitly. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Required tests and V-05 (3) to run `mypy --no-incremental; echo "exit=$?"` verifying an `error:` line for the mutated file and `exit=1`. |
| PR-004 | LOW | IN-SCOPE | R1 / Check P (minor factual inaccuracies and Section 11.1 citations) | `src/pubrun/analysis/render.py:39-40`, `src/pubrun/report/diagnostics.py:5`; Plan lines 56-60, 64-65, 75-80, 102-106 | E-01 overstated `_format_array_diff` as testing membership and counted "five lines plus the import" (actually 4 + 1 = 5 total); E-04 treated `Tuple` import in `diagnostics.py` as conditional even though line 5 already imports it; code citations lacked Section 11.1 `path::Symbol` form. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected the `_format_array_diff` description, E-01 line count, and `diagnostics.py` `Tuple` note, and updated code citations to Section 11.1 `path::Symbol` syntax. |
| PR-005 | LOW | IN-SCOPE | S7 / R2 (execution contract runner/executor finalize ownership) | Plan `Approval and execution gate` item 5 (line 192); `steps/s7-finalize.md:33-36` | Gate item 5 opened with an unconditional `aw ipd finalize qe6dad` instruction without stating runner ownership inside `aw oc run` / `aw agy run`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Gate item 5 to state conditional runner/executor finalization ownership explicitly. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Edits `[tool.mypy.overrides]` in `pyproject.toml` and six modules across analysis, config, status, events, and diagnostics, with 5 focused E-items. | yes |
| D-2 | Tighten `V-05 (2)` to require `mypy` exit 0 unconditionally | Require `mypy` exit 0 | Keep fallback allowing 2 `capture/subprocesses.py` errors | `gzc672` is already `executed` and added `pubrun.capture.subprocesses` to `pyproject.toml:128`, verified by `mypy --no-incremental` exiting 0 on `HEAD`. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All five findings (PR-001..PR-005) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
