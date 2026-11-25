# Review findings: ipd k6fs5k

- Subject-Id: k6fs5k
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-rand-mypy-04-k6fs5k-clear-mypy-errors-in-capture-modules.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `d6832e0` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(b), (d), and (e) are satisfied by the Mermaid ratchet flowchart.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Concern, Scope, Goal, Mermaid nodes A/F/G, E-05, Project conventions, Findings, Proposed changes, Rejected alternatives, Required tests, V-05 | Stated `gzc672` listed 20 modules excluding `pubrun.capture.subprocesses` and instructed E-05 and V-05 (1) to delete only five capture entries | Reflects executed `gzc672` (21 modules including `pubrun.capture.subprocesses` for backlog `z5xr49`), instructs E-05 and V-05 (1) to delete all six `pubrun.capture.*` entries, and requires `mypy` exit 0 with execution-time source-file count re-derivation | Prevents leaving `pubrun.capture.subprocesses` stranded in `ignore_errors` and aligns with current `pyproject.toml` (PR-001). |
| Required tests / validation and V-04 (2)-(3) | V-04 (3) listed only three mutants (omitting the non-dict `capture_state` mutant promised by E-04, Findings, and Required tests), and the 8-run loop piped `pytest` to `\| tail -1` without checking exit status | Adds the fourth mutant (`_startup_cs_raw if _startup_cs_raw else {}` failing `test_merge_treats_non_dict_capture_state_as_empty`) to V-04 (3) and checks exit 0 on every iteration of the 8-run `-p randomly` loop | Aligns V-04 with E-04 and ensures every new test catches its mutant and fails closed on non-zero exit (PR-002). |
| Required tests / validation and V-05 (3) | Ratchet mutation checks ran bare `mypy` on only `resources.py` and `console.py` without checking `exit=1` | Runs `mypy --no-incremental; echo "exit=$?"` verifying `exit=1` across `resources.py`, `console.py`, and `subprocesses.py` | Prevents stale `.mypy_cache` interference and proves `subprocesses.py` is no longer excused (PR-003). |
| E-01..E-04, Project conventions, Findings, Gate item 5 | Code and test symbol references lacked Section 11.1 `path::Symbol` syntax (and E-03 quoted `for rec in cls._records:` instead of `for rec in list(cls._records):`); Gate item 5 opened unconditionally | Applies Section 11.1 `path::Symbol` citations, fixes the `list(cls._records)` quote, and states conditional runner/executor finalization ownership in Gate item 5 | Section 11.1 citation rules and Check S7 execution-contract rule (PR-004, PR-005). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/capture/console.py`, `file_io.py`, `filesystem.py`, `packages.py`, `resources.py`, `subprocesses.py`, `tests/test_capture_mypy_guarded_paths.py`, `pyproject.toml`), 5 E-items in 2 task groups, `- Kind: child`.

1. Yes (bounded): modifies `[tool.mypy.overrides]` in `pyproject.toml` (shared ratchet contract across Set `rand-mypy` and CI `typecheck`) and adds `ConsoleInterceptor` annotations that child `0uxy76` (`tracker.py`) depends on.
2. No: touches no code guarding private data, commits, worktree isolation, merges to `main`, or the sandbox (edits only type annotations, `os.fspath`, `cast`, local variable renames, and tests).
3. No: 5 focused E-items across 2 task groups within standard sizing guidance (5 E-items, 8 Scope-Paths), all scoped to `src/pubrun/capture/`.
4. Yes: `src/pubrun/capture/console.py`, `src/pubrun/capture/file_io.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/packages.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/subprocesses.py`, `tests/test_capture_mypy_guarded_paths.py`, `pyproject.toml`.
5. Yes (bounded): a mistake in `file_io.py`, `packages.py`, `filesystem.py`, or `subprocesses.py` could corrupt run provenance or subprocess exit-code harvesting, though the edits are type annotations and local renames backed by existing suites plus four new mutation-tested behavioral checks and are easy to revert.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/capture/console.py` (lines 4, 96, 269-272, 397-415); `src/pubrun/capture/file_io.py` (lines 66-76, 764-773, 2418-2455); `src/pubrun/capture/filesystem.py` (lines 21, 394-421); `src/pubrun/capture/packages.py` (lines 1614-1632); `src/pubrun/capture/resources.py` (lines 6, 285-318, 364-471); `src/pubrun/capture/subprocesses.py` (lines 205-231, 595-678); `pyproject.toml:115-141`; all 12 referenced test files exist and symbols `TestUnwaitedPopenHarvesting`, `test_unwaited_uncollected_child_polled_at_finalize`, `test_cleanup_reaped_child_records_exit_code`, and `test_probe_paths_dedupes_by_mount` resolve; ran `MYPYPATH=src mypy --config-file /dev/null --explicit-package-bases --ignore-missing-imports --no-incremental --follow-imports=silent` on all six capture files (`Found 44 errors in 6 files`: 5 `console.py`, 9 `file_io.py`, 1 `filesystem.py`, 8 `packages.py`, 19 `resources.py`, 2 `subprocesses.py`).
- PR-001: `pyproject.toml:128` already lists `pubrun.capture.subprocesses` (21 total override entries after `gzc672` executed), contradicting the plan's claim that only five capture modules were listed. Fixed across the entire plan so E-05 deletes all six `pubrun.capture.*` entries.
- PR-005: fixed `for rec in cls._records:` -> `for rec in list(cls._records):` (actual `src/pubrun/capture/subprocesses.py:613`) and updated code/test citations to Section 11.1 `path::Symbol` forms.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-05` to `V-01`..`V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:gzc672, executed:m66tfv`, alignment of all 13 test files in `Required tests / validation` with `V-01`..`V-05`, runtime-demonstration reachability of V-04 (3) (four source mutants against E-04 tests) and V-05 (3) (`mypy --no-incremental` ratchet mutation checks), and all five execution-contract elements in the gate.
- PR-001: updated E-05 and V-05 (1)-(2) to delete all six capture entries and require `mypy` exit 0 (`Success: no issues found in <N> source files`, `58` at review; re-derive at execution time).
- PR-002: added the missing fourth mutant (`_startup_cs_raw if _startup_cs_raw else {}` failing `test_merge_treats_non_dict_capture_state_as_empty`) to V-04 (3) and made the 8-run `-p randomly` loop check exit 0 on every iteration.
- PR-003: updated ratchet mutation checks to run `mypy --no-incremental; echo "exit=$?"` verifying `exit=1`, and added `src/pubrun/capture/subprocesses.py` alongside `resources.py` and `console.py`.
- PR-004: updated Gate item 5 to state conditional runner/executor finalization ownership explicitly.

### Step R3

- Checked: all five bullets of Check R3 full form. The edits are static type annotations, `os.fspath` type narrowing, `typing.cast`, and local variable renames (`rec` -> `proc_rec`), touching no authentication, authorization, secrets, network calls, or redaction logic. E-04's subprocess test spawns only `[sys.executable, "-c", ...]` with an argv list (no shell) and cleans up via `SubprocessSpy.uninstall()` and `subprocess._cleanup()` in `finally`. V-05 runs `python3 scripts/sanitize_paths.py --check --all`. No finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (5 single-concern E-items across 2 task groups, 8 Scope-Paths; each is executable in one focused pass; no splitting warranted); Python 3.8 syntax compatibility (`Optional`, `Dict`, `List`, `Tuple`, `TextIO`, `cast`, `Any`); anti-regression (E-04 adds four mutation-tested behavioral tests for all uncovered edited paths, and `cast` in `filesystem.py` preserves empty-string behavior); spec and documentation sync (no `.spec.md` or `docs/` file mentions `mypy`; `0uxy76` updates `CONTRIBUTING.md` and `CHANGELOG.md`). No additional findings beyond PR-001..PR-005.

### Step S5

- Checked: `## Open questions` is `None.`. Every review finding PR-001..PR-005 had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1 / R2 (missing `pubrun.capture.subprocesses` removal from `pyproject.toml` override) | `pyproject.toml:115-141` (`pubrun.capture.subprocesses` at line 128; 21 entries total); Plan lines 5-6, 29, 37, 43-45, 98, 105-106, 131, 137, 153, 194 | Plan assumed `pubrun.capture.subprocesses` was not on `pyproject.toml`'s `ignore_errors` list and instructed E-05 and V-05 (1) to delete only five capture entries, which would leave `pubrun.capture.subprocesses` excused from `mypy` and strand it in the ratchet. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Swept the whole plan so E-05 and V-05 (1) delete all six `pubrun.capture.*` entries (including `pubrun.capture.subprocesses`), updated `gzc672` context to 21 entries, and required `mypy` exit 0 with execution-time source-file count re-derivation. |
| PR-002 | MEDIUM | IN-SCOPE | R2 (missing 4th E-04 mutant in V-04 and exit-status masking in 8-run loop) | Plan `E-04` (line 93), `Findings` (line 121), `Required tests / validation` (lines 155-156), `V-04` (line 189) | V-04 (3) listed only three mutants, omitting the fourth mutant (`_startup_cs_raw if _startup_cs_raw else {}` failing `test_merge_treats_non_dict_capture_state_as_empty`) promised by E-04, Findings, and Required tests; the 8-run loop piped `pytest` to `\| tail -1`, masking non-zero exit codes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the fourth mutant to V-04 (3) and updated the 8-run `-p randomly` loop to fail closed on any non-zero exit. |
| PR-003 | MEDIUM | IN-SCOPE | R2 (ratchet mutation check cache safety, exit status, and `subprocesses.py` coverage) | Plan `Required tests / validation` (line 154), `V-05` (line 194) | Ratchet mutation checks ran bare `mypy` without `--no-incremental`, did not verify `exit=1` explicitly, and did not test `src/pubrun/capture/subprocesses.py` after removing it from `ignore_errors`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Required tests and V-05 (3) to run `mypy --no-incremental; echo "exit=$?"` verifying `exit=1` across `resources.py`, `console.py`, and `subprocesses.py`. |
| PR-004 | LOW | IN-SCOPE | S7 / R2 (execution contract runner/executor finalize ownership) | Plan `Approval and execution gate` item 5 (line 208); `steps/s7-finalize.md:33-36` | Gate item 5 opened with an unconditional `aw ipd finalize k6fs5k` instruction without stating runner ownership inside `aw oc run` / `aw agy run`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Gate item 5 to state conditional runner/executor finalization ownership explicitly. |
| PR-005 | LOW | IN-SCOPE | Check P / Section 11.1 (symbol citations and `list(cls._records)` quote) | `src/pubrun/capture/subprocesses.py:613`; Plan lines 57-88, 108, 115, 123 | E-03 quoted `for rec in cls._records:` instead of `for rec in list(cls._records):`, and code/test symbol citations omitted Section 11.1 `path::Symbol` form. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected the quote to `for rec in list(cls._records):` and updated citations to Section 11.1 `path::Symbol` syntax. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Edits `[tool.mypy.overrides]` in `pyproject.toml`, `ConsoleInterceptor` annotations depended on by `0uxy76`, and six capture modules with 5 focused E-items. | yes |
| D-2 | Include `pubrun.capture.subprocesses` in E-05's `pyproject.toml` deletions | Delete all six `pubrun.capture.*` entries in E-05 | Leave `pubrun.capture.subprocesses` for `0uxy76` | `pyproject.toml:128` currently lists `pubrun.capture.subprocesses` (added during `gzc672` execution), and `k6fs5k`'s Goal is to put the entire `capture` subpackage under CI `typecheck`. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All five findings (PR-001..PR-005) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
