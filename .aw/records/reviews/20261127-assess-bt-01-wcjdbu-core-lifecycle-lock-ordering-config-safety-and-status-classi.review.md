# Review findings: ipd wcjdbu

- Subject-Id: wcjdbu
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-01-wcjdbu-core-lifecycle-lock-ordering-config-safety-and-status-classi.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`). Expanded acronyms (`JSON`, `PID`, `TOCTOU`, `OS`, `AST`, `QA`, `CI`) on first use, standardized `path::Symbol` code citations, and updated the Mermaid `flowchart` to include the `writer is None` fallback branch in `Run.stop()` and general write-exception lock preservation (`PR-006`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### Safe finalization and lock-removal order` | Flowchart omitted `Run.stop()` `writer is None` branch and labeled failure narrowly as `"write raises OSError"` | Added `HASW{"writer present?"}` branch for `writer is None` and generalized failure edge to `"write fails (exception)"` | Keep Mermaid flowchart consistent with `E-01` and `ArtifactWriter.write_artifacts` (`PR-006`) |
| `Scope`, `E-03`, `E-04`, `E-05`, `## Project conventions discovered`, `## Findings` | Used `JSON`, `PID`, `TOCTOU`, `OS`, `AST`, `QA`, `CI` without first-use expansion and module-dotted names (`pubrun.config._section`) | Expanded acronyms on first use and standardized `path::Symbol` citations (`src/pubrun/config.py::_section`, `src/pubrun/core.py::_classify_exit_outcome`, `src/pubrun/status.py::...`) | Satisfy technical writing standard requirement 1 and spec Section 11.1 (`PR-006`) |
| `E-01`, `E-04`, `V-01`, `V-04`, `## Spec / documentation sync`, `- Scope-Paths:` | Omitted `DummyRun` callable guard on `_remove_lock_file`, omitted `test_lock_file_removed_on_atexit_finalization` update in `tests/test_status.py`, omitted deadlock-free `_merge_and_migrate()` lock ordering and `Run.__init__()` ghost-mode rollback details, and marked `## Spec / documentation sync` as `N/A` | Added callable guard for `_remove_lock_file`, updated `test_lock_file_removed_on_atexit_finalization` expectations, specified keeping `_hardware_thread.join()` and `SubprocessSpy.install()` outside `_run_lock`, specified `Run.__init__()` ghost-mode rollback on unexpected `_bootstrap_engines()` failure, and added `docs/architecture.md` + `docs/functional_spec.md` sync | Prevent existing test breakage (`PR-001`), prevent deadlocks and ambiguous rollback behavior (`PR-002`), and keep architecture/spec docs truthful (`PR-004`) |
| `E-02`, `E-03`, `E-04`, `## Required tests / validation`, `V-02`, `V-03`, `V-04`, `V-05` | Omitted hostname and `pid > 0`/`started_at_utc` guards in `RunInfo._load_from_manifest`, `_enrich_from_manifest` dict check, `isinstance(argv, list)` check, `AmbiguousRunSelectorError` `candidates` list, function-local `builtins` import for both `open()` branches in `_read_pyproject_project_meta`, root-UID skip allowance in `V-04`, and four directly affected pytest modules | Added all guards, local `builtins.open` across both branches, full `candidates=[by_recency, *other_exact]`, root-UID skip wording in `V-04`, and `test_writer.py`, `test_capture_isolation.py`, `test_commit_identity.py`, `test_timing_consumers.py` to validation | Ensure cross-host safety, `mypy` cleanliness, namespace hygiene, and complete regression validation (`PR-003`, `PR-005`) |
| `## Approval and execution gate` | Omitted `--scope-reason`/`--scope-ack`, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize wcjdbu` ownership | Tightened all five execution-contract clauses to match `r2-executability.md` and `s7-finalize.md` | Satisfy mandatory execution-contract rules (`PR-006`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 1`, `- Scope-Paths:` (originally 8 paths, expanded to 10 with `docs/architecture.md` and `docs/functional_spec.md`), 5 E-items in 3 task groups.

1. Yes: modifies core finalization lock-removal ordering (`.pubrun.lock`), `Run._finalize_state` exit-outcome classification, public `status.py` run classification for lockless `outcome: "running"` manifests, `find_run()` selector ambiguity/stripping semantics, and `status._resolve_output_dir` `~`/`$VAR` expansion relied upon alongside CLI/TUI sibling plans (`qum7gf`, `kk83rk`).
2. No: does not touch private-data redaction, git commits, worktree isolation, merges to main, or sandbox guards (touches `.pubrun.lock` lifecycle and symlink-safe directory sizing in `status.py::_dir_size`).
3. Yes: 5 E-items across 3 task groups modifying 5 core runtime modules (`tracker.py`, `writer.py`, `status.py`, `config.py`, `__init__.py`), 3 test files, and 2 architecture/spec docs across 10 findings (`BUG-C1`..`C4`, `BUG-C6`..`C10`, `TEST-U11`).
4. Yes: `- Scope-Paths:` explicitly lists all 10 modified files.
5. Yes: mistakes in lock-removal order, `_merge_and_migrate()` `_run_lock` acquisition, or `RunInfo` classification can deadlock with `pubrun-hw` or concurrent `stop()`, lose crash-detection locks, break `ArtifactWriter` test doubles (`DummyRun`), or break `tests/test_status.py`.

AW-TIER: complex

### Step R1

- Checked: every file, symbol, test, and doc citation against the repository: `src/pubrun/tracker.py` (`_call_get_packages`, `Run.__init__`, `Run._bootstrap_engines`, `Run._merge_and_migrate`, `Run._rollback_owned_hooks`, `Run._finalize_state`, `Run._refresh_packages_at_finalization`, `Run.stop`, `Run.to_manifest_dict`), `src/pubrun/writer.py` (`ArtifactWriter.write_artifacts`, `_atomic_json_write`), `src/pubrun/status.py` (`RunInfo._enrich_from_manifest`, `RunInfo._load_from_manifest`, `RunInfo._load_from_lock`, `close_out_crashed_run`, `_resolve_output_dir`, `AmbiguousRunSelectorError`, `find_run`, `_dir_size`), `src/pubrun/config.py` (`_deep_merge`, `_section`, `profile_deprecation_notice`), `src/pubrun/__init__.py` (`_read_pyproject_project_meta`, `__dir__`), `src/pubrun/core.py` (`_classify_exit_outcome`, `start`, `stop`), `src/pubrun/capture/signals.py` (`record_exit_code`, `_exit_details`), `src/pubrun/capture/subprocesses.py` (`SubprocessSpy.install`, `uninstall`), `src/pubrun/capture/liveness.py` (`is_same_process`, `_script_name_forms`), `tests/test_status.py`, `tests/test_status_bugs.py`, `tests/test_core_lifecycle_bugs.py`, `tests/test_writer.py`, `tests/test_capture_isolation.py`, `tests/test_tracker.py`, `tests/test_config.py`, `tests/test_timing_consumers.py`, `tests/test_report_checks_bugs.py`, `docs/architecture.md`, and `docs/functional_spec.md`.
- Verified: every cited bug exists in the current source tree; uncovered an existing test contradiction in `tests/test_status.py::TestLockFile.test_lock_file_removed_on_atexit_finalization:107-115` and `tests/test_writer.py::DummyRun:48-63` (`PR-001`), a lock-ordering deadlock hazard in `Run._merge_and_migrate:1176-1304` (`PR-002`), missing guards in `src/pubrun/status.py` (`PR-003`), and contradicting documentation in `docs/architecture.md:54` and `docs/functional_spec.md:946-948` (`PR-004`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability, non-tautological evidence, and execution-gate contract.
- Verified: all `V-*` items demand concrete diffs and pytest/mypy outputs reachable by construction; `PR-001` resolved the breaking existing test expectation; `PR-005` fixed the root-UID unsatisfiable pass wording in `V-04` and expanded the validation suite; `PR-006` completed all five execution-contract clauses.

### Step R3

- Checked: trust boundaries and filesystem safety across `src/pubrun/status.py::_dir_size` (symlink exclusion and per-entry `OSError` resilience), `RunInfo._load_from_manifest` / `_load_from_lock` / `_enrich_from_manifest` (malformed/untrusted JSON resilience), `RunInfo._load_from_manifest` host check before local PID liveness probing, `src/pubrun/__init__.py::_read_pyproject_project_meta` avoiding unintended provenance recording via `builtins.open`, and `Run.__init__()` / `_merge_and_migrate()` redacting error details via `format_safe_error_detail()`.
- Verified: no hardcoded secrets, safe symlink/error handling, and cross-host PID liveness isolation (`PR-003`).

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified: `PR-001` preserves `DummyRun` and updates `test_lock_file_removed_on_atexit_finalization`; `PR-002` prevents AB-BA deadlocks in `_merge_and_migrate()` and specifies ghost-mode rollback in `Run.__init__()`; `PR-003` closes cross-host PID, `mypy`, `_enrich_from_manifest`, `argv`, and `AmbiguousRunSelectorError.candidates` gaps in `status.py`; `PR-004` syncs `docs/architecture.md` and `docs/functional_spec.md`; `PR-005` covers all modified modules in `## Required tests / validation` and preserves `pubrun.__dir__()` hygiene.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `tests/test_status.py::TestLockFile.test_lock_file_removed_on_atexit_finalization` failure and `DummyRun` incompatibility (`PR-001`) plus root-UID skip wording in `V-04` (`PR-005`).
  2. Testing and regression: expanded `## Required tests / validation` to include `test_writer.py`, `test_capture_isolation.py`, `test_commit_identity.py`, and `test_timing_consumers.py` (`PR-005`), and added unexpected-bootstrap-exception and remote-host lockless manifest test cases (`PR-002`, `PR-003`).
  3. UI / UX: confirmed `find_run` whitespace stripping and complete `AmbiguousRunSelectorError.candidates` reporting (`PR-003`) improve CLI error clarity.
  4. Architect: caught `_run_lock` deadlock hazard with `pubrun-hw` and `SubprocessSpy.install()` in `_merge_and_migrate()` (`PR-002`) and architecture/spec drift (`PR-004`).
  5. Software engineer: caught missing `mypy` narrowing and hostname check in `RunInfo._load_from_manifest`, `_enrich_from_manifest` non-dict assignment, non-list `argv[0]`, and `pubrun.__dir__()` namespace hygiene (`PR-003`, `PR-005`).
  6. Power user: verified `~`/`$VAR` expansion in `_resolve_output_dir` works for both `str` and `Path` inputs and preserves HPC remote-host safety (`PR-003`).
  7. Novice: verified non-dict `.pubrun.toml` sections degrade cleanly without cryptic `AttributeError` tracebacks or leaked hooks (`PR-002`).
  8. Stakeholder: confirmed full coverage of all 9 bugs (`BUG-C1`..`C4`, `BUG-C6`..`C10`) and `TEST-U11` assigned to Order 01 by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, already Order 01 of the 10-child Set `assess-bt`).
- Confirmed: each E-item maps to a cohesive, small, localized pass (`E-01` tracker/writer lifecycle + 2-line doc sync, `E-02` ~5-line config/init fixes, `E-03` status.py hardening, `E-04` regression tests, `E-05` validation). No further splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt`: orchestrator `n6250e` (Order 00) and sibling children `ndobra`, `thbepl`, `qum7gf`, `kk83rk`, `n39jh9`, `dqaj9a`, `kgoymu`, `4eo4z2`, and `37sth0`.
- Verified: all 10 `Scope-Paths` in `wcjdbu` (including the newly added `docs/architecture.md` and `docs/functional_spec.md`) remain strictly disjoint from all nine sibling children in `assess-bt` and from pending plans `8o6o83` and `3u1xgk`; `_resolve_output_dir` `~`/`$VAR` expansion aligns cleanly with `qum7gf` (`BUG-U5` TUI) and `kk83rk` (`BUG-U5` CLI).

### Step S5

- Checked: `## Open questions` contains `None.`. All six findings (`PR-001` through `PR-006`) had `Low` overall Remediation Risk, were settled by repository code, test, and documentation evidence, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r4-engineering.md` D (Anti-regression) / `r2-executability.md` | `tests/test_status.py::TestLockFile.test_lock_file_removed_on_atexit_finalization:107-115`, `tests/test_writer.py::DummyRun:48-63`, `src/pubrun/writer.py::ArtifactWriter.write_artifacts:388-392` | Moving `.pubrun.lock` removal from `Run._rollback_owned_hooks(stage="finalization")` into `ArtifactWriter.write_artifacts()` breaks `TestLockFile.test_lock_file_removed_on_atexit_finalization` (which calls `run._finalize_state()` directly and asserts lock absence before `write_artifacts()`), and an unguarded `self.run._remove_lock_file()` call in `write_artifacts()` raises `AttributeError` on `tests/test_writer.py::DummyRun`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required callable `getattr(self.run, "_remove_lock_file", None)` in `E-01`, updated `E-04` and `V-04` to update `TestLockFile.test_lock_file_removed_on_atexit_finalization` to assert lock persistence across `_finalize_state()` and removal after `writer.write_artifacts()`, and added `tests/test_writer.py` to validation (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r4-engineering.md` A (Concurrency and lock ordering) / `r2-executability.md` | `src/pubrun/tracker.py::Run._merge_and_migrate:1176-1304`, `src/pubrun/tracker.py::Run.__init__:488-527`, `src/pubrun/tracker.py::Run._finalize_state:1521-1565` | `E-01` directed serializing `_api_overrides` read-merge-commit under `_run_lock` without keeping `_hardware_thread.join()`/`_hardware_future_done.wait()` and `SubprocessSpy.install()` outside `_run_lock` (risking AB-BA deadlock with `pubrun-hw` or concurrent `stop()`), did not specify ghost-mode rollback semantics for `Run.__init__()`'s `_bootstrap_engines()` guard, omitted `isinstance(new_base_str, (str, os.PathLike))` before `Path(new_base_str)`, and omitted the `exc_val is None` fallback in `_finalize_state()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified exact deadlock-free lock discipline in `E-01` (join hardware and call `SubprocessSpy.install()` outside `_run_lock`; perform authoritative read-merge-resolve-move-notice-commit under `_run_lock`; re-check and uninstall spy under `_run_lock` if finalized), specified `Run.__init__()` ghost-mode rollback contract, added `new_base_str` and `exc_val`/`exc_type` guards, and added an unexpected-bootstrap-exception rollback test to `E-04` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` A, C (Correctness, cross-host safety, typing) | `src/pubrun/status.py::RunInfo._enrich_from_manifest:300-320`, `RunInfo._load_from_manifest:350-445`, `RunInfo._load_from_lock:451-507`, `find_run:1065-1095`, `AmbiguousRunSelectorError:963-990` | `E-03` invoked `is_same_process(self.pid, self.started_at_utc, ...)` without checking `(not self.hostname or self.hostname == get_hostname())` or `self.pid > 0` / `started_at_utc is not None` (`mypy` narrowing + remote-host safety), omitted placement before `_received_sigpipe()` and live `elapsed`/`rss_bytes`/`cpu_percent` population, omitted `isinstance(data, dict)` in `_enrich_from_manifest` and `isinstance(argv, list)` before indexing `argv[0]`, and omitted `candidates=[by_recency, *other_exact]` for multi-collision `AmbiguousRunSelectorError`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-03` with hostname and `pid`/`started_at_utc` guards, branch ordering, live metrics population, `_enrich_from_manifest` and `argv` guards, `os.fspath()` handling in `_resolve_output_dir`, and `candidates=[by_recency, *other_exact]` in `find_run`; added remote-hostname/missing-PID test cases to `E-04` (recommendation strength: `strong`). |
| PR-004 | MEDIUM | UNDER-SCOPE | `r4-engineering.md` (Spec and documentation sync) / `plan-review.md` 0.3 | `docs/architecture.md:54`, `docs/functional_spec.md:946-948`, `.aw/records/plans/pending/20261127-assess-bt-01-wcjdbu-core-lifecycle-lock-ordering-config-safety-and-status-classi.ipd.md:142-144` | `## Spec / documentation sync` claimed `N/A`, but `docs/architecture.md:54` and `docs/functional_spec.md:946-948` both explicitly document `.pubrun.lock` removal inside `_finalize_state()` / `_rollback_owned_hooks(stage="finalization")` before package refresh and `write_artifacts()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `docs/architecture.md` and `docs/functional_spec.md` to `- Scope-Paths:`, added finalization doc updates to `E-01` and `V-01`, and updated `## Spec / documentation sync` and `## Scope check` (recommendation strength: `strong`). |
| PR-005 | MEDIUM | UNDER-SCOPE | `r4-engineering.md` E (Testing and verification) / `r2-executability.md` | `src/pubrun/__init__.py::_read_pyproject_project_meta:109,134`, `src/pubrun/__init__.py::__dir__:407-408`, `tests/test_writer.py`, `tests/test_capture_isolation.py`, `tests/test_commit_identity.py`, `tests/test_timing_consumers.py` | `## Required tests / validation` omitted four directly affected regression suites (`test_writer.py`, `test_capture_isolation.py`, `test_commit_identity.py`, `test_timing_consumers.py`), `E-02` omitted updating both `open()` branches with a function-local `builtins` import (avoiding `pubrun.__dir__()` pollution), and `V-04` demanded unconditional pass on `test_ghost_mode_no_lock_file` even under root UID where the added guard skips it. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added all four suites to `## Required tests / validation`, clarified function-local `builtins.open` across both branches in `E-02`, and updated `V-04` to accept pass or root-UID skip for `test_ghost_mode_no_lock_file` (recommendation strength: `strong`). |
| PR-006 | MEDIUM | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `.aw/records/plans/pending/20261127-assess-bt-01-wcjdbu-core-lifecycle-lock-ordering-config-safety-and-status-classi.ipd.md:6,30-40,49,51,67,73,80,86,97,112,179-188` | `## Approval and execution gate` omitted `--scope-reason`/`--scope-ack`, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize wcjdbu` ownership; prose left `JSON`, `PID`, `TOCTOU`, `OS`, `AST`, `QA`, and `CI` unexpanded on first use and used module-dotted names; Mermaid diagram omitted the `writer is None` branch and narrowed failure to `OSError`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Tightened all five clauses of `## Approval and execution gate`, expanded acronyms on first use, standardized `path::Symbol` citations, and aligned the Mermaid flowchart with `E-01` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `wcjdbu` | `complex` | `standard` | Order 01 of 10-child Set `assess-bt`; changes lock-finalization ordering, status classification, and `find_run()`/`_resolve_output_dir()` contracts across 5 core runtime modules; answers Yes to tier questions 1, 3, and 5 in `steps/t-tier.md`. | yes |
| D-2 | How to handle `docs/architecture.md` and `docs/functional_spec.md` lock-removal order drift (`PR-004`) | Add both files to `wcjdbu`'s `- Scope-Paths:` and sync them in `E-01` / `V-01` | Leave docs stale or defer to a separate plan | `docs/architecture.md:54`, `docs/functional_spec.md:946-948`, zero overlap with any sibling child in `assess-bt` or other pending plans, and `plan-review.md` 0.3 / `r4-engineering.md` sync requirement. | yes |
| D-3 | How to reconcile `tests/test_status.py::TestLockFile.test_lock_file_removed_on_atexit_finalization` with `BUG-C2` (`PR-001`) | Update the test in `E-04` to assert `.pubrun.lock` persists across `_finalize_state()` and is removed after `writer.write_artifacts()` | Keep removing `.pubrun.lock` inside `_finalize_state()` (defeating `BUG-C2`) | `tests/test_status.py:107-115`, `src/pubrun/writer.py::ArtifactWriter.register_atexit:247-251` (which registers `self.write_artifacts`, not `_finalize_state`), and `wcjdbu` Goal / `BUG-C2`. | yes |

### Step S6

- Checked: `- Scope-Paths:` changed during Round 1 (added `docs/architecture.md` and `docs/functional_spec.md` for `PR-004`). Per `steps/s6-rereview.md` rule 1, trigger a bounded Round 2 verification pass over the revised plan.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised `.aw/records/plans/pending/20261127-assess-bt-01-wcjdbu-core-lifecycle-lock-ordering-config-safety-and-status-classi.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. All acronyms are expanded on first use, all code citations follow `path::Symbol`, and the Mermaid diagram matches `E-01` verbatim.

### Step R1

- Checked: verified the newly added `Scope-Paths` (`docs/architecture.md` `### Finalization:54`, `docs/functional_spec.md` `### 19.2 Finalization Lifecycle:946-948`) and all revised citations in `E-01..E-05` and `V-01..V-05`. Zero broken or stale references.

### Step R2

- Checked: verified E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` (10 paths, all accounted for in `E-01..E-04`, `## Scope check`, and `## Approval and execution gate`), `## Required tests / validation` (11 test files + 3-OS `mypy`), and `aw ipd lint --phase review-finalize --agent` passing cleanly.

### Step R7

- Checked: re-verified disjointness of all 10 `Scope-Paths` (including `docs/architecture.md` and `docs/functional_spec.md`) against all nine sibling children in Set `assess-bt` (`ndobra`, `thbepl`, `qum7gf`, `kk83rk`, `n39jh9`, `dqaj9a`, `kgoymu`, `4eo4z2`, `37sth0`) and pending plans `8o6o83` and `3u1xgk`. Zero conflicts.

### Step S5

- Checked: zero open questions, zero unfixed or deferred findings, and zero irreversible decisions.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Step S6

- Checked: no `E-*` or `V-*` items, `- Scope-Paths:`, or `- Item-Dependencies:` changed in Round 2; every Round 1 revision (`PR-001` through `PR-006`) is swept and consistent across front matter, diagram, `E-01..E-05`, `## Findings`, `## Proposed changes`, `## Scope check`, `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, and `## Approval and execution gate`. No further pass is needed.

AW-REVIEW: DONE
