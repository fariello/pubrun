# Review findings: ipd m5s3g8

- Subject-Id: m5s3g8
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-8l-06-m5s3g8-status-clean-and-run-scanning-safety-scalability-and-termina.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --detail` exited `0` (`conforming`, zero advisories). Expanded acronyms (`TTY`, `ASCII`, `PID`, `RAM`, `ANSI`, `CLI`) on first use, anchored symbols with `path::Symbol`, and updated the Mermaid `flowchart LR` diagram to include `report/output.py::use_color`, `find_run`, `load_manifest`, and all three test files.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-02`, `V-02`, `## Project conventions`, `## Deferred / out of scope` | Defaulted `keep_manifest: bool = False` on `RunInfo` and `scan_runs()`, breaking TUI `RunsSidebar`/`RunDetailsView`/`ActionsPanel` (Order 09) and `_run_methods_aggregate` (Order 08) immediately on Order 06 merge | Kept `keep_manifest: bool = True` default for backward compatibility, added `load_manifest()`, used `keep_manifest=False` internally in `clean_runs()`/`find_run()`, and recorded explicit `2ge0ea`/`3q5rd5` opt-in carriers | Prevent blocker TUI breakage between Order 06 and Order 09 (`PR-001`) |
| `E-02`, `E-05`, `## Deferred / out of scope` | Required `find_run()` to error on ambiguous prefixes without specifying `AmbiguousRunSelectorError(candidates=...)`, updating `tests/test_status.py:813-826`, or noting `_emit_ambiguous_selector()` in `__main__.py` | Extended `AmbiguousRunSelectorError` with optional `candidates`, updated `tests/test_status.py:813-826`, guarded fast path to exact 8+-char run IDs, and deferred `__main__.py::_emit_ambiguous_selector` formatting to `2ge0ea` | Keep exception contract clean and avoid breaking existing prefix/CLI tests (`PR-002`) |
| `E-01`, `E-03`, `E-05`, `- Scope-Paths:` | TTY color gating broke `tests/test_status.py:969-978` and `tests/test_status_bugs.py:316-339`; `clean_runs()` re-prompting broke `tests/test_status.py:827-860` and `_parse_selection()` list return; `tests/test_output.py` was omitted | Added `tests/test_output.py` to `- Scope-Paths:`, pinned `NO_COLOR > FORCE_COLOR > isatty` precedence, added `_parse_selection_detailed()` keeping `_parse_selection()` list return, and added explicit updates for all three breaking test sites | Prevent blocker test regressions in `test_status.py` and `test_status_bugs.py` (`PR-003`) |
| `E-01`, `V-01` (`clean_runs`, `safe_delete_run_dir`) | Unspecified `safe_delete_run_dir` return type and exact `force_remote_locks=True` boundary; applying `limit` before remote-lock exclusion would starve `clean --limit N`; naive status validation risked breaking `TestBug01EmptyStatusFilter` | Specified `safe_delete_run_dir(...) -> Tuple[bool, Optional[str]]`, enforced `force_remote_locks=True` only bypasses readable remote-host locks (never symlink/confinement/active-local-PID/unreadable locks), excluded remote locks before `limit`, and validated non-empty tokens before stripping `"running"` | Preserve fail-closed security invariants and `TestBug01EmptyStatusFilter` (`PR-004`) |
| `E-02`, `E-03`, `E-04`, `V-02`..`V-04` | `render_verbose_list` lacked `all_runs` parameter; `_truncate` lacked `max_len <= 0` guard and `stream` seam; `_populate_artifact_sizes` did not specify `O(1)` `os.stat()` sizing; dynamic `#` width omitted `clean_runs()` | Added `all_runs=None` to `render_verbose_list`, added `max_len <= 0` and `stream=None` to `_truncate`, specified single-`os.stat()` `_populate_artifact_sizes`, and applied dynamic `#` width to both `render_short_list` and `clean_runs` | Eliminate edge-case bugs and keep 1,000+ run scanning O(1) per run (`PR-005`) |
| `## Goal`, Mermaid diagram, `## Required tests / validation`, `V-05`, `## Approval and execution gate` | Missing five-clause execution gate, missing `test_output.py`/`test_status_clean_table.py`/`test_tui*.py` in validation, suite-only `V-05`, unexpanded acronyms, incomplete Mermaid diagram | Added five-clause execution gate, expanded validation to all 12 affected suites, named concrete test units in `V-05`, expanded acronyms, and updated Mermaid diagram | Satisfy execution-contract, regression-coverage, and technical-writing rules (`PR-006`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-8l`, `- Order: 6`, `- Scope-Paths:` (5 files: `status.py`, `report/output.py`, `tests/test_status.py`, `tests/test_status_bugs.py`, `tests/test_output.py`), 5 E-items in 4 task groups.

1. Yes: introduces public helpers (`VALID_STATUSES`, `safe_delete_run_dir`, `RunInfo.load_manifest`, `report/output.py::use_color`), extends `AmbiguousRunSelectorError`, and changes `filter_runs(limit <= 0)` / `find_run()` ambiguity contracts.
2. Yes: `safe_delete_run_dir()` and `clean_runs()` enforce destructive-deletion security boundaries (symlink escape, parent-directory confinement, active local PID locks, unreadable locks, and remote-host locks).
3. Yes: spans six rollup findings (`ROLL-05`, `ROLL-18`, `ROLL-21`, `ROLL-24`, `ROLL-25`, `ROLL-35`) and serves as a direct dependency for children `caeqdz` (Order 07), `2ge0ea` (Order 08), `3q5rd5` (Order 09), and `6y55x4` (Order 10).
4. Yes: `- Scope-Paths:` explicitly lists all 5 modified files.
5. Yes: regressions in `safe_delete_run_dir`, `filter_runs(limit)`, or `RunInfo.manifest` can cause data loss (deleting live or out-of-tree directories) or break the entire TUI and CLI test suites.

AW-TIER: complex

### Step R1

- Checked: every cited source file, caller, and test against the repository:
  - `src/pubrun/status.py:1-1683` (`RunInfo`, `filter_runs`, `can_safely_auto_close_crashed_run`, `close_out_crashed_run`, `scan_runs`, `_MAX_RECENCY_INDEX`, `AmbiguousRunSelectorError`, `find_run`, `_truncate`, `_status_marker`, `_render_summary`, `render_short_list`, `render_verbose_list`, `render_inspect`, `_parse_selection`, `clean_runs`).
  - `src/pubrun/report/output.py:1-116` (`_use_color`, `_prefix`, `emit`).
  - Cross-module callers: `src/pubrun/__main__.py:25-33,70-155,880-920,2275-2369`, `src/pubrun/tui/widgets/sidebar.py:1-89`, `src/pubrun/tui/widgets/details.py:282-444`, `src/pubrun/tui/widgets/actions.py:168-206`.
  - Tests: `tests/test_status.py:1-1171`, `tests/test_status_bugs.py:1-354`, `tests/test_status_clean_table.py:1-65`, `tests/test_output.py:1-122`, `tests/test_runtime_safety.py:85-153`, `tests/test_new_features.py:423-457`, `tests/test_cli_negative_paths.py:265-351`.
- Verified: static reading of `src/pubrun/tui/widgets/{sidebar,details,actions}.py` caught the blocker `keep_manifest=False` default breakage (`PR-001`), reading `src/pubrun/__main__.py:25-33` and `tests/test_status.py:813-860,969-978` plus `tests/test_status_bugs.py:76-92,316-339` caught all existing-test and CLI-handler interactions (`PR-002`, `PR-003`, `PR-004`).

### Step R2

- Checked: strict 1:1 `E-01..E-05` <-> `V-01..V-05` bijection, `- Highest E allocated: 05`, `- Scope-Paths:` completeness (all 5 modified files, `<= 8`), `- Item-Dependencies: none`, concrete named `path::Symbol` units in every `V-*` item, non-tautological validation evidence, and the five-clause execution contract.
- Verified: every `E-*` maps cleanly to an observable `V-*` and the validation suite exercises all status, output, CLI-negative, and TUI consumers.

### Step R3

- Checked: destructive-action security invariants in `safe_delete_run_dir()` and `clean_runs()` (symlink rejection, `resolve().parent` confinement, active local PID refusal, unreadable/corrupt/symlinked `.pubrun.lock` refusal, and strict scoping of `force_remote_locks=True` to readable foreign-host locks only), plus fail-closed `filter_runs()` validation (`limit < 0` / `bool`, unknown statuses, invalid `--older-than`).
- Verified: `PR-004` ensures `force_remote_locks=True` can never bypass symlink, confinement, unreadable-lock, or active-local-PID protections, and that `limit == 0` deletes zero runs.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing, and `## Spec / documentation sync`.
- Verified: `PR-001` preserves TUI and CLI backward compatibility via `keep_manifest=True` default + `load_manifest()`; `PR-002` aligns `AmbiguousRunSelectorError` across `status.py`, tests, and `2ge0ea`; `PR-003` aligns TTY color tests and interactive re-prompt tests; `PR-004` locks down `safe_delete_run_dir()` and remote-lock filtering order; `PR-005` closes `render_verbose_list`, `_truncate`, `_populate_artifact_sizes`, and dynamic `#` width edge cases; `PR-006` adds the five-clause execution gate and expanded validation.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `keep_manifest=False` breaking TUI widgets (`PR-001`) and `limit` slicing before remote-lock exclusion (`PR-004`).
  2. Testing and regression: caught `test_status.py:813-860,969-978`, `test_status_bugs.py:76-92,316-339`, and `test_output.py` interactions and added TUI/CLI regression suites to `## Required tests / validation` (`PR-002`, `PR-003`, `PR-006`).
  3. UI / UX: fixed empty vs filtered-empty messaging in both `render_short_list` and `render_verbose_list`, added ignored-token feedback + single re-prompt in `clean_runs`, removed `DIM` codes, and ensured 60-col and `#1000+` tables render cleanly (`PR-003`, `PR-005`).
  4. Architect: kept `keep_manifest: bool = True` default and cleanly partitioned downstream adoption into `2ge0ea` (Order 08) and `3q5rd5` (Order 09) with zero circular dependencies (`PR-001`, `PR-002`).
  5. Software engineer: preserved `_parse_selection()` list return via `_parse_selection_detailed()`, specified `safe_delete_run_dir() -> Tuple[bool, Optional[str]]`, and kept `_populate_artifact_sizes()` `O(1)` via `os.stat()` (`PR-003`, `PR-004`, `PR-005`).
  6. Power user: enabled `force_remote_locks=True` for stale HPC node locks, `#1000+` recency indices, `find_run(..., runs=...)`, and `FORCE_COLOR` override on pipes (`PR-001`, `PR-004`, `PR-005`).
  7. Novice: replaced misleading `pubrun run -- python your_script.py` onboarding copy with accurate `import pubrun` / `pubrun init` guidance and added `#` index footer tip (`PR-005`).
  8. Stakeholder: maintained 100% backward compatibility with existing run directories, manifests, and public `status.py` / `report/output.py` signatures (`PR-001`, `PR-002`, `PR-003`).

### Step R6

- Checked: decomposition and sizing across `E-01..E-05` (5 E-items, 4 task groups, 5 Scope-Paths, Order 06 of 10-child Set `assess-8l`).
- Confirmed: cohesive, right-sized child plan focused exclusively on `status.py` and `report/output.py` (5 Scope-Paths `<= 8`, 5 E-items `<= 5`). No splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-8l`: orchestrator `k80suw` (Order 00), `caeqdz` (Order 07, depends on `executed:m5s3g8` for `report/output.py::use_color`), `2ge0ea` (Order 08, depends on `executed:m5s3g8` for `VALID_STATUSES`, `force_remote_locks`, `find_run(runs=...)`, `keep_manifest=False`, and `_emit_ambiguous_selector`), `3q5rd5` (Order 09, depends on `executed:m5s3g8` for `safe_delete_run_dir` and `scan_runs(..., keep_manifest=False)`), and `6y55x4` (Order 10, depends on `executed:m5s3g8`).
- Verified: every contract depended on by `caeqdz`, `2ge0ea`, and `3q5rd5` (`use_color`, `VALID_STATUSES`, `safe_delete_run_dir`, `force_remote_locks`, `scan_runs(..., keep_manifest=False)`, `RunInfo.load_manifest`, `find_run(..., runs=...)`) is explicitly specified in `m5s3g8` with zero file overlap across siblings and zero cycles.

### Step S5

- Checked: `## Open questions` contains `None.`. All six findings (`PR-001` through `PR-006`) had `Low` overall Remediation Risk, were settled by repository code, caller, and test evidence, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` D / `r7-cross-plan.md` | `src/pubrun/tui/widgets/sidebar.py:39`, `src/pubrun/tui/widgets/details.py:282-444`, `src/pubrun/tui/widgets/actions.py:168-206`, `.aw/records/plans/pending/20261127-assess-8l-06-m5s3g8-status-clean-and-run-scanning-safety-scalability-and-termina.ipd.md:59` | Setting `keep_manifest: bool = False` as the default on `scan_runs()` and `RunInfo` in Order 06 immediately sets `r.manifest = None` for `RunsSidebar`, breaking `RunDetailsView`, `ActionsPanel`, and `tests/test_tui*.py` before Child 09 (`3q5rd5`) migrates the TUI (and colliding with `2ge0ea`'s `_run_methods_aggregate` reuse of `r.manifest`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Kept `keep_manifest: bool = True` default on `RunInfo` and `scan_runs()`, added `RunInfo.load_manifest()`, used `keep_manifest=False` internally in `clean_runs()`/`find_run()`, and recorded `2ge0ea`/`3q5rd5` opt-in carriers in `## Deferred / out of scope` (recommendation strength: `very strong`). |
| PR-002 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A, D / `r7-cross-plan.md` | `src/pubrun/status.py:874-935`, `src/pubrun/__main__.py:25-33,89,887,2297`, `tests/test_status.py:813-826` | Raising an error on ambiguous ID prefixes in `find_run()` breaks `tests/test_status.py:821,825` (which assert `is None`), and raising `AmbiguousRunSelectorError` without an optional `candidates` field causes `__main__.py::_emit_ambiguous_selector()` to print `"the abcdth-most-recent run"`; an unrestricted dir-name fast path would also miss custom directory names. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Extended `AmbiguousRunSelectorError` with optional `candidates`, restricted the `os.scandir()` fast path to exact 8+-char full run IDs with fallback to `scan_runs`, updated `E-05` to align `tests/test_status.py:813-826`, and deferred `__main__.py::_emit_ambiguous_selector` formatting to `2ge0ea` (recommendation strength: `very strong`). |
| PR-003 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` D, E | `tests/test_status.py:827-860,888-935,969-978`, `tests/test_status_bugs.py:284-303,316-339`, `src/pubrun/report/output.py:66-72` | Switching `status.py` to TTY-aware `use_color()` breaks `tests/test_status.py:969-978` and `tests/test_status_bugs.py:316-339` (which assert ANSI escapes under non-TTY `pytest`); re-prompting in `clean_runs()` causes `StopIteration` in `tests/test_status.py:834-835`; changing `_parse_selection()` return type breaks 13 direct unit tests; and `tests/test_output.py` was omitted from `- Scope-Paths:`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `tests/test_output.py` to `- Scope-Paths:`, pinned `force_no_color` / `NO_COLOR > FORCE_COLOR > isatty` precedence, kept `_parse_selection()` list return via `_parse_selection_detailed()`, and specified exact updates for `test_status.py` and `test_status_bugs.py` in `E-05` (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D | `src/pubrun/status.py:1470-1518,1655-1681`, `tests/test_status_bugs.py:75-92`, `tests/test_status.py:862-885` | `safe_delete_run_dir()` lacked a defined return signature and explicit guarantee that `force_remote_locks=True` never bypasses symlink, confinement, active-local-PID, or unreadable-lock checks; applying `limit` before excluding remote-locked runs starves `clean --limit N`; and naive `status_filter` validation could break `TestBug01EmptyStatusFilter` (`"running"` / empty strings). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `safe_delete_run_dir(...) -> Tuple[bool, Optional[str]]` restricting `force_remote_locks=True` strictly to readable foreign-host locks, ordered `clean_runs()` to validate non-empty tokens before stripping `"running"` and exclude remote locks before applying `limit`, and preserved `"  Failed to remove <name>: <err>"` stderr formatting (recommendation strength: `very strong`). |
| PR-005 | HIGH | IN-SCOPE | `r4-engineering.md` A, C, F | `src/pubrun/status.py:428-448,1025-1030,1139-1210,1529-1606` | `render_verbose_list()` had no `all_runs` parameter for filtered-empty messages; `_truncate()` lacked a `max_len <= 0` guard and `stream` test seam; `_populate_artifact_sizes()` did not specify `O(1)` `os.stat()` sizing for `events.jsonl` and `stdout.log`+`stderr.log`; and dynamic `#` width was omitted from `clean_runs()` tables. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `all_runs=None` to `render_verbose_list()`, added `max_len <= 0` guard and `stream=None` to `_truncate()`, specified single-`os.stat()` `_populate_artifact_sizes()`, and applied dynamic `#` width to both `render_short_list()` and `clean_runs()` (recommendation strength: `very strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `.aw/records/plans/pending/20261127-assess-8l-06-m5s3g8-status-clean-and-run-scanning-safety-scalability-and-termina.ipd.md:28-38,130-134,167-174` | `## Approval and execution gate` omitted the five-clause execution contract; `## Required tests / validation` omitted `test_output.py`, `test_status_clean_table.py`, `test_new_features.py`, `test_cli_negative_paths.py`, `test_timing_consumers.py`, `test_profile_deprecation.py`, and `test_tui*.py`; `V-05` was suite-only; acronyms were unexpanded; and the Mermaid diagram omitted `report/output.py`, `find_run`, and test suites. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Wrote the five-clause execution gate, expanded validation and `V-05` to all 12 affected suites with named units, expanded acronyms on first use, and updated the Mermaid diagram (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `m5s3g8` | `complex` | `standard` | Touches destructive deletion security boundaries (`safe_delete_run_dir`, `clean_runs`), modifies public contracts consumed by children `07`–`10`, and spans 6 rollup findings; answers Yes to all five tier questions in `steps/t-tier.md`. | yes |
| D-2 | Default value of `keep_manifest` on `RunInfo` and `scan_runs()` | Default `keep_manifest: bool = True`, use `keep_manifest=False` inside `clean_runs()`/`find_run()` and explicitly in `2ge0ea`/`3q5rd5` | Default `keep_manifest: bool = False` (immediately breaks `RunsSidebar`/`RunDetailsView`/`ActionsPanel` and `tests/test_tui*.py` in Order 06 before `3q5rd5` runs in Order 09) | Static inspection of `src/pubrun/tui/widgets/{sidebar,details,actions}.py` and `3q5rd5:62,99` (which already passes `keep_manifest=False` explicitly). | yes |
| D-3 | Exception type for ambiguous prefix/substring matches in `find_run()` | Extend `AmbiguousRunSelectorError` with optional `candidates: Optional[List[RunInfo]] = None` | Introduce a brand-new exception class (swallowed by `except Exception:` in `__main__.py:92,890` and uncaught traceback in `__main__.py:2296`) | `src/pubrun/__main__.py:89,887,2297` already catch `AmbiguousRunSelectorError`; `2ge0ea` updates `_emit_ambiguous_selector()`. | yes |

### Step S6

- Checked: Round 1 added `tests/test_output.py` to `- Scope-Paths:` and refined `E-01`..`E-05` and `V-01`..`V-05`. Per `steps/s6-rereview.md` rule 1, a second pass (Round 2) is required to verify the revised Scope-Paths, contracts, cross-references, and lint conformance.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised `.aw/records/plans/pending/20261127-assess-8l-06-m5s3g8-status-clean-and-run-scanning-safety-scalability-and-termina.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. Confirmed all acronyms are expanded on first use, all `E-01..E-05` and `V-01..V-05` items name exact `path::Symbol` units with observable criteria, and the Mermaid `flowchart LR` covers all 5 `- Scope-Paths:` entries.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R2

- Checked: verified `- Highest E allocated: 05` matches `E-01..E-05` and `V-01..V-05` (strict 1:1 bijection); verified `- Scope-Paths:` lists all 5 modified files (`<= 8`, zero `IPD-Z603` advisories); verified `- Item-Dependencies: none` has zero overlap with Orders 01–05; verified no superseded wording remains; verified the five-clause execution gate states conditional runner/executor finalize ownership with no forbidden "STOP and report" scope-fence wording.

### Step R7

- Checked: verified zero file overlap with any sibling in Set `assess-8l`, confirmed downstream children `caeqdz`, `2ge0ea`, `3q5rd5`, and `6y55x4` all depend on `executed:m5s3g8`, and confirmed all three downstream handoffs (`2ge0ea`, `3q5rd5`, `6y55x4`) are cleanly recorded in `## Deferred / out of scope`.

### Step S5

- Checked: `## Open questions` contains `None.`; all six findings (`PR-001` through `PR-006`) are `FIXED`; zero blocking questions or irreversible decisions remain; lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` D / `r7-cross-plan.md` | `src/pubrun/tui/widgets/{sidebar,details,actions}.py` | Defaulting `keep_manifest=False` on `scan_runs()`/`RunInfo` would break TUI widgets and `tests/test_tui*.py` in Order 06 before `3q5rd5` runs. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `keep_manifest=True` default + `load_manifest()` + internal `keep_manifest=False` in `clean_runs`/`find_run` + `2ge0ea`/`3q5rd5` carriers are reconciled across `E-02`, `V-02`, and `Deferred` (recommendation strength: `very strong`). |
| PR-002 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A, D / `r7-cross-plan.md` | `src/pubrun/status.py:874-935`, `src/pubrun/__main__.py:25-33`, `tests/test_status.py:813-826` | Ambiguous prefix error needed `AmbiguousRunSelectorError(candidates=...)`, fast-path guard, `test_status.py` update, and `2ge0ea` `_emit_ambiguous_selector` handoff. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-02`, `E-05`, `V-02`, and `Deferred` specify the full exception, fast-path, test, and `2ge0ea` contract (recommendation strength: `very strong`). |
| PR-003 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` D, E | `tests/test_status.py:827-978`, `tests/test_status_bugs.py:284-339`, `src/pubrun/report/output.py:66-72` | TTY color tests, interactive re-prompt cancel tests, `_parse_selection` return type, and missing `tests/test_output.py` Scope-Path. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `tests/test_output.py` is in `- Scope-Paths:`, `_parse_selection_detailed` preserves `_parse_selection`, and `E-03`/`E-05` reconcile all test assertions (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D | `src/pubrun/status.py:1470-1518,1655-1681`, `tests/test_status_bugs.py:75-92` | `safe_delete_run_dir` return/security boundary, `limit` vs remote-lock ordering, and `TestBug01EmptyStatusFilter` preservation. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-01` and `V-01` lock down `safe_delete_run_dir`, remote-lock exclusion order, and status-filter validation order (recommendation strength: `very strong`). |
| PR-005 | HIGH | IN-SCOPE | `r4-engineering.md` A, C, F | `src/pubrun/status.py:428-448,1025-1030,1139-1210,1529-1606` | `render_verbose_list` `all_runs`, `_truncate` `max_len <= 0`/`stream`, `O(1)` `_populate_artifact_sizes`, and `clean_runs` dynamic `#` width. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-02`, `E-03`, and `E-04` close every edge case cleanly (recommendation strength: `very strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `m5s3g8` | Missing five-clause gate, incomplete validation list, suite-only `V-05`, unexpanded acronyms, and incomplete Mermaid diagram. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: five-clause gate, 12-suite validation, named `V-05` units, acronyms, and Mermaid diagram are all reconciled (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `m5s3g8` | `complex` | `standard` | Touches destructive deletion security boundaries and public contracts for children `07`–`10`; answers Yes to all five tier questions in `steps/t-tier.md`. | yes |
| D-2 | Default value of `keep_manifest` on `RunInfo` and `scan_runs()` | Default `keep_manifest: bool = True`, use `keep_manifest=False` inside `clean_runs()`/`find_run()` and explicitly in `2ge0ea`/`3q5rd5` | Default `keep_manifest: bool = False` | Preserves TUI widgets and `tests/test_tui*.py` in Order 06 before `3q5rd5` runs in Order 09. | yes |
| D-3 | Exception type for ambiguous prefix/substring matches in `find_run()` | Extend `AmbiguousRunSelectorError` with optional `candidates` | New exception class | Already caught in `__main__.py:89,887,2297` and aligned with `2ge0ea`. | yes |

### Step S6

- Checked: Round 2 introduced no further edits, no new findings, and no structural changes. All revisions from Round 1 are internally consistent and reconciled across all sections. Ready for Step S7 finalization (`APPROVE WITH REVISIONS APPLIED`, `go-pending-approval`).

AW-REVIEW: DONE
