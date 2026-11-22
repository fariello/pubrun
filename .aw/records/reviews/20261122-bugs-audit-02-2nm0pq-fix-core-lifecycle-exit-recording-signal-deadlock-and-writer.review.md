# Review findings: ipd 2nm0pq

- Subject-Id: 2nm0pq
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, Mermaid diagram, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261122-bugs-audit-02-2nm0pq-fix-core-lifecycle-exit-recording-signal-deadlock-and-writer.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal` and `Signal and exit finalization lifecycle` | Dense single-sentence goal; flowchart omitted `KeyboardInterrupt` -> `"interrupted"` and `_serialize_config_and_digest` | Split `Goal` into two sentences, expanded acronyms (`JSON`, `TOML`, `CLI`, `fd`), and aligned flowchart labels with text | Technical writing requirements 1, 2, 12(d), and 12(e) |
| Symbol citations across `E-01`..`E-04`, `Findings`, `Proposed changes`, `V-01`..`V-04` | Bare dotted names and nonexistent symbols (`EventLogger`, `SubprocessProxy`, `_handle_signal`) | Standardized `path::Symbol` citations using verified symbols (`EventStream`, `_PubrunSubprocessNamespace`, `SignalExitCapture._make_handler`) | `steps/p-proofread.md` Section 11.1 and factual accuracy |
| `## Spec / documentation sync` | Bare unsubstantiated `N/A` | Cited verified `docs/configuration.md`, `docs/api.md`, `docs/functional_spec.md` coverage plus `src/pubrun/core.py::diff` docstring update | `steps/r4-engineering.md` spec/documentation sync rule |
| `## Approval and execution gate` | Missing honesty, never-push, scope-declaration, and conditional finalize rules; vague manual-move wording | Replaced with compliant 5-item Execution contract using `--scope-reason`/`--scope-ack`, HARD MUST pasted output rule, never-push, and conditional `aw ipd finalize 2nm0pq` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, `src/pubrun/tracker.py`, `src/pubrun/capture/signals.py`, `src/pubrun/writer.py`, `src/pubrun/core.py`, `src/pubrun/events.py`, `src/pubrun/config.py`, `src/pubrun/capture/console.py`, `src/pubrun/capture/subprocesses.py`, and Set `bugs-audit` orchestrator `jqqvkh`.

1. Yes: modifies core public APIs (`pubrun.start`, `pubrun.stop`, `pubrun.diff`, `pubrun.audit_run`, `pubrun.tracked_run`, `pubrun.subprocess`, `pubrun.popen`, `pubrun.print`, `pubrun.phase`), `python -m` auto-start boot detection, and `manifest.json` `status.outcome`, `signals.exit_code`, `subprocesses`, and `filesystem.output_dir` contracts.
2. Yes: touches `src/pubrun/core.py` explicit subprocess redaction (`redact_argv` and `format_safe_error_detail` guarding secrets in `manifest.json`) and `pubrun.phase` profile path traversal sanitization (`../../bad:name`).
3. No: 5 focused E-items across 4 task groups within 5 tightly coupled core lifecycle modules and 1 regression test file (child 02 of 9 in Set `bugs-audit`).
4. Yes: `- Scope-Paths:` explicitly lists all 6 modified files.
5. Yes: a mistake in signal handlers can deadlock host scripts on `SIGTERM`; a mistake in `_execute_boot_sequence` breaks every `python -m pubrun` CLI command; a mistake in `_serialize_config_and_digest` drops runs into ghost mode; and unredacted subprocess records leak secrets into manifests.

AW-TIER: complex

### Step R1

- Checked: Verified every cited symbol, lock type, config key, and runtime behavior against `src/pubrun/core.py`, `src/pubrun/tracker.py`, `src/pubrun/capture/signals.py`, `src/pubrun/writer.py`, `src/pubrun/events.py`, `src/pubrun/config.py`, `src/pubrun/capture/console.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/__init__.py`, `docs/configuration.md`, `docs/api.md`, `docs/functional_spec.md`, `tests/test_events.py`, `tests/test_capture_isolation.py`, `tests/test_startup_overhead_writes.py`, `tests/test_timing_accuracy.py`, and empirical `python3 -m` `runpy` frame probes. Caught naive `python -m` detection hazard (`PR-001`), missing `_serialize_config_and_digest` `default=str` and startup config isolation (`PR-002`), nonexistent symbol names (`EventLogger`, `SubprocessProxy`, `_handle_signal`), already-fixed behaviors (`core.start` active-run kwargs, `write_artifacts` isolation, `EventStream` `_lock` detachment), and `V-01(c)` testing re-entrant `_run_lock` instead of non-reentrant `SignalExitCapture._lock` (`PR-003`).

### Step R2

- Checked: Verified author lint preflight (`aw ipd lint --phase author --agent` exit 0, `clean`, 0 findings), 1:1 `E-01`..`E-05` to `V-01`..`V-05` bijection (co-locating per-bug test authoring inside `E-01`..`E-04` so each `V-*` directly validates its owning `E-*`), 6-file `- Scope-Paths:` parity, `- Item-Dependencies: none` matching `jqqvkh`, concrete behavioral evidence in all `V-*` items (all reachable by construction via local `pytest` subprocesses and unit tests, no code-pinning), and `## Approval and execution gate` (fixed missing execution-contract clauses in `PR-005`).

### Step R3

- Checked: Verified secret redaction in `src/pubrun/core.py::_PubrunSubprocessNamespace` (`run`/`Popen`) and `popen` (`redact_argv` on split `argv` and `format_safe_error_detail` on exception messages, plus `format_safe_error_detail` on non-int `sys.exit` messages in `signals.py`), path-traversal mitigation in `src/pubrun/core.py::phase` (`profile-<safe_name>.prof` stripping `/`, `\`, `:`, `..`, and non-`[a-zA-Z0-9_-]` chars), elimination of signal-handler deadlock on non-reentrant `SignalExitCapture._lock`, and `try/finally` file-descriptor cleanup in `EventStream.close()`/`migrate_directory()`.

### Step R4

- Checked: Evaluated engineering rubric sections A (signal lock safety, `sys.exit` transactional install/restore, `default=str` in both `_serialize_config_and_digest` and `_atomic_json_write`, `_CORE_SHORTCUTS`-preserving override accumulation in `_merge_and_migrate`, `Run.stop` `_active_run` clearing under `_run_lock`), C (reusing `SubprocessSpy._safe_shlex_split`, `redact_argv`, `format_safe_error_detail`, and `_tee_paused()` instead of duplicating logic), D (preserving `cap-isolation`, `startup-perf`, and `timing-acc` contracts including transactional signal rollback, passive passthrough, identity-guarded restore, and `write_artifacts()` lock ordering), E (concrete subprocess, signal, concurrency, and fd-leak tests in `tests/test_core_lifecycle_bugs.py` plus full `pytest -q`), F (KISS, preventing silent `python -m` auto-start failure and silent exception-as-completed reporting), right-sizing (5 cohesive E-items without inverted `E-05`/`V-01`..`V-04` test dependencies), and `## Spec / documentation sync` (verified existing `docs/` coverage + `core.diff` docstring fix).

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught `python -m pubrun` auto-start hazard via empirical `runpy` probe (`PR-001`), `_serialize_config_and_digest` `TypeError` crash before `_atomic_json_write` (`PR-002`), and `V-01(c)` testing `RLock` instead of non-reentrant `SignalExitCapture._lock` (`PR-003`).
  2. **Testing and regression expert:** Fixed inverted `V-01`..`V-04` dependency on `E-05`, added negative test for `python -m pubrun status` not creating runs (`PR-001`), and pinned already-fixed `core.start` / `EventStream` / `write_artifacts` guarantees (`PR-003`, `PR-006`).
  3. **UI / UX expert:** Verified accurate `pubrun.print` behavior (`file=`, no double-writing under console tee, `paused()`) and iterable `pubrun.popen` (`PR-004`).
  4. **Systems and software architect:** Aligned `sys.exit` wrapper with `cap-isolation` transactional rollback/identity-guard contract, ensured `_merge_and_migrate` respects `_CORE_SHORTCUTS` and updates `output_base_dir`, and kept `write_artifacts()` lock ordering intact (`PR-003`, `PR-004`).
  5. **Software engineer:** Fixed nonexistent symbols (`EventLogger`, `SubprocessProxy`, `_handle_signal`) and execution-contract gate (`PR-003`, `PR-005`).
  6. **Sophisticated power user:** Confirmed `python -m <user_pkg>` (both `__init__.py` and `__main__.py`), `pubrun.start(output_dir=Path(...))`, `pubrun.phase` with `yappi` + mid-phase `stop()`, and `for line in pubrun.popen(...)` all work reliably (`PR-001`, `PR-002`, `PR-004`).
  7. **Complete novice:** Split dense `Goal`, expanded acronyms, aligned flowchart with text, and fixed stale `[diff].ignore` docstring (`PR-004`, `PR-006`).
  8. **Stakeholder:** Confirmed all 13 core lifecycle bugs assigned to `2nm0pq` in Set `bugs-audit` (`jqqvkh`) are resolved thoroughly with zero silent deferrals.

### Step R6

- Checked: Evaluated decomposition across `E-01`..`E-05`. `2nm0pq` is already child 02 of 9 in Set `bugs-audit`, covering 5 tightly coupled core lifecycle modules (`tracker.py`, `signals.py`, `writer.py`, `core.py`, `events.py`). Because `core.start` active-run kwargs, `write_artifacts` isolation, and `EventStream` `_lock` detachment are already present in HEAD, the net edit footprint fits cleanly in 4 focused implementation E-items plus 1 verification E-item without splitting into a separate Plan Set.

### Step R7

- Checked: Verified alignment with Set `bugs-audit` orchestrator `jqqvkh` and sibling child plans (`njn1up`..`kqzd15`). Confirmed `- Item-Dependencies: none` matches `jqqvkh`, `- Scope-Paths:` (`tracker.py`, `signals.py`, `writer.py`, `core.py`, `events.py`, `test_core_lifecycle_bugs.py`) is completely disjoint from all 8 sibling child plans in `bugs-audit`, and `SignalExitCapture` / `ArtifactWriter` / `EventStream` edits preserve all invariants landed by `cap-isolation`, `startup-perf`, and `timing-acc`.

### Step S5

- Checked: Audited pre-existing `## Open questions` (`None`), `## Deferred / out of scope` (`None`), and all 6 review findings (`PR-001`..`PR-006`). All 6 findings had Low remediation risk and were fixed in place. Recorded reversible evidence-based decisions `D-1`..`D-4` below (with `D-1` empirically demonstrated via `python3 -m` `runpy` probe per `steps/s5-questions.md` HOW-question rule). Zero unresolved or blocking human questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | R1/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-02-2nm0pq-fix-core-lifecycle-exit-recording-signal-deadlock-and-writer.ipd.md:69,96,113,153`, `src/pubrun/core.py:476-479`, `src/pubrun/__init__.py:311` | Removing `"__main__.py"` and `"-m"` from `_execute_boot_sequence` and checking only `"pubrun.__main__" in sys.modules` breaks `python -m pubrun ...`: empirical `runpy` probe confirmed that when `runpy._run_module_as_main("pubrun")` imports `pubrun/__init__.py`, `"pubrun.__main__"` is not yet in `sys.modules`, `__main__.__spec__` is `None`, and `sys.argv[0]` is `"-m"`, so every `python -m pubrun` CLI call would auto-start a tracked run. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `_is_pubrun_cli_invocation()` checking CLI script basenames, `"pubrun.__main__" in sys.modules`, `__main__.__spec__.name`, and `runpy` stack frames (`mod_name == "pubrun"` or `mod_name.startswith("pubrun.")`) when `sys.argv[0] == "-m"`, and required `V-03` to verify both `python -m <temp_pkg>` auto-starting and `python -m pubrun status` not auto-starting (`D-1`, recommendation strength: very strong). |
| PR-002 | BLOCKER | IN-SCOPE | R1/R4.A | `.aw/records/plans/pending/20261122-bugs-audit-02-2nm0pq-fix-core-lifecycle-exit-recording-signal-deadlock-and-writer.ipd.md:60-62,98,112,148`, `src/pubrun/writer.py:106,150-154,201,278-326,365-375` | `E-02` added `default=str` only to `_atomic_json_write`, missing `src/pubrun/writer.py::_serialize_config_and_digest` (`json.dumps` at line 152), which runs BEFORE `_atomic_json_write` and would still crash `pubrun.start(output_dir=Path(tmp))` with `TypeError`. Also claimed `write_artifacts()` lacked per-artifact isolation (already present at lines 278-326) while missing that `write_startup_manifest()` at line 371 does not isolate `_write_config_if_needed`, demoting the run to ghost mode on config error. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required `default=str` in both `_serialize_config_and_digest` and `_atomic_json_write`, preserved existing `write_artifacts()` isolation, and isolated `_write_config_if_needed` in `write_startup_manifest()` (`D-2`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R1/R4.A/R4.E | `.aw/records/plans/pending/20261122-bugs-audit-02-2nm0pq-fix-core-lifecycle-exit-recording-signal-deadlock-and-writer.ipd.md:53-75,95-106,143`, `src/pubrun/events.py:10,98-156`, `src/pubrun/core.py:26,145-158,877-885`, `src/pubrun/capture/signals.py:46-59,73,214-264` | Cited nonexistent symbols `EventLogger` (actual: `EventStream`), `SubprocessProxy` (actual: `_PubrunSubprocessNamespace`), and `_handle_signal` (actual: closure in `SignalExitCapture._make_handler`); misstated `core.start` double-check and `EventStream` `_lock` detachment as unfixed; misstated `BUG-06` as dropping tuples (already handled at line 882; string splitting is the gap); and `V-01(c)` tested `SIGTERM` while `_run_lock` (already an `RLock`) is held instead of non-reentrant `SignalExitCapture._lock`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected all symbol names and root causes, aligned `sys.exit` wrapper with `SignalExitCapture`'s transactional rollback/passive-passthrough/identity-guard pattern, updated `EventStream` fix to `try/finally` descriptor cleanup, and updated `V-01(c)` to test `SIGTERM` while `signal_capture._lock` is held plus re-entrant `_finalize_active_run()` (`D-3`, recommendation strength: very strong). |
| PR-004 | HIGH | UNDER-SCOPE | R1/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-02-2nm0pq-fix-core-lifecycle-exit-recording-signal-deadlock-and-writer.ipd.md:55,69,74,111,113`, `src/pubrun/config.py:170-173`, `src/pubrun/tracker.py:788-815,915`, `src/pubrun/core.py:180,235-272,344-438,556-603`, `src/pubrun/capture/console.py:21-24` | Under-specified critical mechanisms: `_merge_and_migrate` must preserve `_CORE_SHORTCUTS` without mutating caller dicts and update `self.output_base_dir` on migration; `core.print` duplicate-write guard needed exact `ConsoleInterceptor.stdout_tee` and `_tee_paused()` conditions; `core.phase` needed explicit safe filename sanitization (`payload["path"]` vs raw `name`) and `try/finally` `yappi` reset regardless of `is_active`; `audit_run`/`tracked_run` needed shared `BaseException`/`SystemExit(0)`/`KeyboardInterrupt` classification; and `core.diff` docstring still cited `[diff].ignore`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified all four mechanisms and the `core.diff` docstring update explicitly in `E-01`, `E-03`, `E-04`, `Proposed changes`, and `V-01`/`V-03`/`V-04` (`D-4`, recommendation strength: very strong). |
| PR-005 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261122-bugs-audit-02-2nm0pq-fix-core-lifecycle-exit-recording-signal-deadlock-and-writer.ipd.md:167-172`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | `## Approval and execution gate` omitted the HARD MUST pasted-output honesty rule, never-push rule, `--scope-reason`/`--scope-ack` scope declaration, and conditional runner vs standalone `aw ipd finalize 2nm0pq` ownership, and used vague manual-move wording. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract (recommendation strength: very strong). |
| PR-006 | MEDIUM | IN-SCOPE | Check P/R2/R4 | `.aw/records/plans/pending/20261122-bugs-audit-02-2nm0pq-fix-core-lifecycle-exit-recording-signal-deadlock-and-writer.ipd.md:22-45,53-82,130-165` | `Workflow history` was oldest-first; `V-01`..`V-04` depended on `tests/test_core_lifecycle_bugs.py` not created until `E-05`; `Spec / documentation sync` was bare `N/A`; code citations lacked `path::Symbol` format; acronyms were unexpanded; and flowchart omitted `KeyboardInterrupt` and `_serialize_config_and_digest`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reordered `Workflow history` newest-first, co-located per-bug test authoring inside `E-01`..`E-04` (with `E-05` running full-suite regression verification), substantiated `Spec / documentation sync` with verified doc citations, standardized `path::Symbol` citations, expanded acronyms, and updated the flowchart (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should `_execute_boot_sequence` distinguish `python -m <user_pkg>` from `python -m pubrun` during `pubrun/__init__.py` import? | Check CLI script basenames (`pubrun`/`pbr`), `"pubrun.__main__" in sys.modules`, `__main__.__spec__.name`, and (when `sys.argv[0] == "-m"`) active `runpy` stack frames whose `mod_name` is `"pubrun"` or starts with `"pubrun."`. | Check only `"pubrun.__main__" in sys.modules` (empirically demonstrated via `python3 -m demo_pkg` probe to fail during `runpy` `__init__.py` import, breaking `python -m pubrun` CLI). | `src/pubrun/core.py:476-479`, `src/pubrun/__init__.py:311`, empirical `python3 -m` `runpy` frame probe | yes |
| D-2 | Where must `default=str` and startup config-write isolation be applied in `src/pubrun/writer.py`? | Pass `default=str` in both `_serialize_config_and_digest` (`json.dumps`) and `_atomic_json_write` (`json.dump`), preserve existing `write_artifacts()` isolation, and isolate `_write_config_if_needed()` inside `write_startup_manifest()`. | Pass `default=str` only in `_atomic_json_write` (still crashes at `_serialize_config_and_digest` line 152 before `_atomic_json_write` runs). | `src/pubrun/writer.py:106,150-154,201,278-326,365-375` | yes |
| D-3 | Which lock and re-entrancy scenario must `V-01(c)` test for `BUG-08`? | Test `SIGTERM` delivery while non-reentrant `signal_capture._lock` is held and test nested re-entrant `_finalize_active_run()` calls, while keeping `sys.exit` wrapper aligned with `SignalExitCapture`'s transactional rollback and passive-passthrough contract. | Test only `_run_lock` (already `threading.RLock()` at `src/pubrun/core.py:26`, which does not reproduce the non-reentrant deadlock in `SignalExitCapture._lock`). | `src/pubrun/core.py:26`, `src/pubrun/capture/signals.py:46-59,73,91-135,214-264` | yes |
| D-4 | How should `_merge_and_migrate` preserve prior overrides and `_CORE_SHORTCUTS` without mutating caller dicts? | Track accumulated normalized API overrides on `self._api_overrides`, merge new overrides into a deep copy, resolve via `resolve_config`, and update `self.output_base_dir = new_base` on migration. | Call `_deep_merge(self.config, overrides)` directly (bypasses `_CORE_SHORTCUTS` normalization in `src/pubrun/config.py:170-173`). | `src/pubrun/config.py:22-33,170-173`, `src/pubrun/tracker.py:788-815,915` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed (still `E-01`..`E-05` and `V-01`..`V-05`), `- Scope-Paths:` and `- Item-Dependencies:` did not change, and a full cross-section sweep confirmed zero stale tokens (`EventLogger`, `SubprocessProxy`, `_handle_signal`) and full alignment across front matter, workflow history, flowchart, checklist, findings, proposed changes, doc sync, validation items, and execution gate.

AW-REVIEW: DONE
