# Review findings: ipd zcuoll

- Subject-Id: zcuoll
- Subject-Type: ipd
- Reviewed-At: 2026-11-24
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-a0o2xx-01-zcuoll-audit-lock-ordering-and-prevent-re-entrant-deadlocks-in-leth.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The H2 heading list and order, the existing E-01 to E-04 and V-01 to V-04 ids, checkbox states, and field names are kept. E-01 to E-04 were rewritten in place and E-05 to E-09 with V-05 to V-09 were added (PR-004, PR-005). Substantive rewrites are recorded under Findings.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence naming "same-thread deadlocks" | What the user sees today (hang, outcome `running`), then four numbered results | Requirements 2 and 9. |
| Project conventions | `module.function` citation form | `path::Name` and `path#Heading` forms, plus the `pubrun-hw` lock order, the README promise, and child-process test conventions | Requirement 5; `steps/p-proofread.md` Section 11.1. |
| Findings | Six-item lock list, partly wrong | Inventory table with type, path, review-time probe result, and the plan's action for each lock | Requirements 5 and 11 (PR-001, PR-002). |
| Diagram | Edge label "No - already held", branch "skip conflicting write" | Bounded-acquire decision; both branches write the manifest | Requirement 12; removed the hyphen-as-dash label and the manifest-losing branch (PR-003). |
| Workflow history | Oldest first | Newest first | `steps/s7-finalize.md`: the section is newest-first. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:`, E-01 to E-04, every lock site reachable from `src/pubrun/capture/signals.py::_finalize_active_run`, and sibling plans that name the same files.

1. No: no spec, CLI option, manifest field, or configuration key changes; the lock-ordering contract in `docs/architecture.md` gains a rule but keeps the existing order.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. Yes: 4 E-items at review start (9 after review) in 5 source modules at start (7 after review), all on the finalization path of a concurrent system.
4. Yes: 6 files at review start; the review added 5.
5. Yes: a mistake in lock handling hangs or kills the host program, or loses the final manifest, and concurrency defects are hard to reproduce.

AW-TIER: complex

### Step R1

- Checked: every symbol and claim against the code. `src/pubrun/capture/signals.py::_finalize_active_run`, `::SignalExitCapture._make_handler`, `::SignalExitCapture.get_records`; `src/pubrun/tracker.py::Run._finalize_state`, `::Run._rollback_owned_hooks`, `::Run.to_manifest_dict`, `::Run._check_section_failed`, `::Run._store_capture_error_detail`, `::Run._refresh_packages_at_finalization`, nested `_collect_hardware`; `src/pubrun/writer.py::ArtifactWriter.write_artifacts`, `::write_startup_manifest`, `::sync_config_if_changed`; `src/pubrun/events.py::EventStream`; `src/pubrun/capture/file_io.py::FileIoBudgetTracker`, `::finalize_pending_registrations`, `::get_or_create_budget_tracker`; `src/pubrun/capture/subprocesses.py::SubprocessSpy`; `src/pubrun/capture/resources.py::ResourceWatcher`; `src/pubrun/__init__.py::_get_commit`; `src/pubrun/capture/packages.py::_get_distribution_index`; `src/pubrun/_bootstrap.py::get_import_metadata`; every `threading.Lock()` and `threading.RLock()` constructor under `src/pubrun`.
- `_run_lock` and `_write_lock` are `RLock`: the plan's same-thread risk for them was wrong (PR-001).
- `SubprocessSpy.get_records` takes no lock; `_bootstrap.get_import_metadata` takes no lock (PR-001).
- `ResourceWatcher` has no `get_summary`; the methods are `stop` and `to_manifest_dict` (corrected in E-07).
- `EventStream._lock`, `FileIoBudgetTracker._lock`, and `finalize_pending_registrations` were missing (PR-002).

### Step R2

- Checked: E/V bijection, Scope-Paths, dependencies, evidence demands, and the gate. `aw ipd lint --phase author --agent` was clean before edits; `--phase review-finalize --agent` was clean after edits, with two `IPD-Z603` advisories (9 E-items, 10 Scope-Paths) answered by the `- Cohesion rationale:`.
- Probes at review (Python scripts under `/tmp/opencode/zc`, CPython 3.14, Linux, `PYTHONPATH=src`). A daemon thread held a lock and called `_finalize_active_run()`; "hangs" means still blocked after 4 to 6 seconds:
  - Hangs: `Run._errors_lock`, `Run._data_files_lock`, `ResourceWatcher._lock`, `EventStream._lock`, `FileIoBudgetTracker._lock`, `SubprocessSpy._lock` (on the auto-started run that owns the spy; a second `Run()` does not own it and returned), `packages._CACHE_LOCK`.
  - Returns: `pubrun._commit_lock` (commit already cached), `_bootstrap._lock`, `writer._durability_warn_lock`, `file_io._warn_lock`, `file_io._fallback_data_files_lock`.
  - Cross-thread: main thread holds `_errors_lock`, a second thread holds `_run_lock` and calls `Run._check_section_failed` or `Run.to_manifest_dict`: both hang. Main thread holds `_write_lock`, a second thread holds `_run_lock` and calls `write_startup_manifest(is_refresh=True)`: both hang.
  - Real signal: a child process holding `run._errors_lock` did not exit within 3 seconds of `SIGTERM`; a second `SIGTERM` killed it (return code -15) and `manifest.json` still read outcome `running`.

### Step R3

- Checked: security and robustness. The change records no new data and opens no new input path. The risk is availability (a hang or a crash in a signal handler) and integrity of the final manifest. A lock-free fallback runs only while the process is about to be killed, and `manifest.json` is written through a temporary file and `os.replace`, so a reader never sees a partial file. The residual race where a `pubrun-hw` refresh replaces the final manifest is recorded under Deferred with its reason.

### Step R4

- Checked: engineering soundness. A "skip conflicting write" fallback would lose the manifest that the handler exists to write (PR-003). `RLock` alone fixes only the same-thread form. An in-process test that holds a lock and calls `_finalize_active_run` hangs pytest if the fix regresses (PR-006). The fix is user-visible, so `CHANGELOG.md` needs an entry, and `docs/architecture.md` "Lock ordering" is the contract to extend (PR-008).

### Step R5

- Checked: the eight viewpoints in `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`.
- QA/QC and testing: V-items asked only for diffs (PR-007); the tests now observe a real `SIGTERM` with a timeout and a mutation check proves they detect the hang.
- Architect: one helper in `signals.py` keeps the signal-context rule in one place and avoids an import cycle; callers do not read the private latch.
- Software engineer: each E-item is one file; the lock-free branch does the same work, so there is one code path to reason about.
- Power user and stakeholder: `README.md` promises pubrun "never alters, slows, or crashes the program it observes"; a hang on `SIGTERM` breaks that and breaks schedulers (Slurm, Kubernetes) that send `SIGTERM` before `SIGKILL`.
- Novice: the `CHANGELOG.md` entry says what changed without lock vocabulary.
- UI/UX: no interface change.

### Step R6

- Checked: whether the plan should become a Set. 9 E-items and 10 Scope-Paths exceed the `IPD-Z603` guidance. A split is possible: (1) helper plus `tracker.py` and `writer.py` with the cross-thread tests; (2) `events.py` and `file_io.py`; (3) `subprocesses.py` and `resources.py`. It is not recommended: the parts deliver one invariant, every later part depends on the helper, and each E-item is already one file. The `- Cohesion rationale:` records this. No split finding is raised, so readiness is not forced to `no-go`.

### Step R7

- Checked: the Set `a0o2xx` (this plan is its only member and there is no Order 00 orchestrator) and pending plans that share files. `focjwv` (reviewed) rewrites `SubprocessSpy.finalize_all` and adds a lock-free `Popen.__del__` hook in `src/pubrun/capture/subprocesses.py` (PR-009). `m66tfv` (reviewed) edits `tests/test_signals.py` in other tests (`TestSignalNonMainThread`, `TestLethalSignalFinalization`); no conflict, and this plan adopts its `cwd=tmp_path` and no-fixed-sleep conventions. `7y0gmc` (reviewed) edits `src/pubrun/capture/resources.py` seams but not `stop` or `to_manifest_dict`; no ordering needed. `mspqm6` edits other sections of `docs/architecture.md`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R1 (wrong premise) | `src/pubrun/core.py` "_run_lock = threading.RLock()"; `src/pubrun/writer.py::ArtifactWriter` "self._write_lock = threading.RLock()"; `src/pubrun/capture/subprocesses.py::SubprocessSpy.get_records` returns `cls._records` without a lock; `src/pubrun/tracker.py::Run._finalize_state` waits on `_run_lock` while `pubrun-hw` holds it in `_collect_hardware` | The plan treated every lock as a same-thread hazard and would have added tests for `_run_lock` and `_write_lock` that pass without any fix. It missed the cross-thread form that commit `94e504a` fixed for one lock: `pubrun-hw` holds `_run_lock` and waits on a lock the interrupted main thread holds. Probes reproduced it with `_errors_lock` and with `_write_lock`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Findings rewritten with an inventory table and probe results; bounded acquires cover both forms; E-08 adds the two cross-thread cases. |
| PR-002 | high | UNDER-SCOPE | R1 (missing locks) | `src/pubrun/events.py::EventStream.close` "with self._lock:"; `src/pubrun/capture/file_io.py::FileIoBudgetTracker.to_summary_dict` "with self._lock:"; `src/pubrun/capture/file_io.py::finalize_pending_registrations` "with lock:"; probes: all hang | Three locks that finalization takes were not in the plan or in `- Scope-Paths:`. Each one hangs a lethal-signal exit when the interrupted code holds it. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added E-04 and E-05 with V-04 and V-05; `src/pubrun/events.py` and `src/pubrun/capture/file_io.py` added to `- Scope-Paths:`. |
| PR-003 | high | IN-SCOPE | R4 (design defect) | Original diagram "Use lock-free fallback or skip conflicting write"; original E-02 "return cleanly without deadlocking rather than blocking forever"; `README.md` "never alters, slows, or crashes the program it observes" | Returning early from `write_artifacts` when `_write_lock` is busy would leave `manifest.json` at outcome `running`, which is the failure the handler exists to prevent. The plan did not define the fallback per lock. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 helper `finalization_lock` with a per-lock bound; on timeout each caller does the same work lock-free and never skips the manifest write. Recorded as D-2. |
| PR-004 | medium | IN-SCOPE | R2 (right-sizing) | Original E-02 spans `tracker.py` and `writer.py`; E-03 spans `subprocesses.py` and `resources.py`; `IPD-Z603` guidance "about one file" per E-item | Multi-file E-items let a partial edit pass a single V-item. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | One file per E-item (E-01 to E-07, E-09 pairs two docs); each V-item names its own diff and its own test case. |
| PR-005 | medium | UNDER-SCOPE | R2 (gap in coverage) | `src/pubrun/capture/resources.py::ResourceWatcher.stop` "self.join(timeout=min(self.interval + 1, 5))"; `src/pubrun/__init__.py::_get_commit` "with _commit_lock:" | A signal-time `stop` can wait 5 seconds on the sampler thread. `_commit_lock` looked like a hazard; review showed the commit is cached by the startup manifest write before the run is published, so it is reachable only after the test helper `_reset_commit_cache()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-07 caps the join at 0.5 seconds in signal context. `_commit_lock` recorded as unchanged with evidence in the inventory and under Deferred. |
| PR-006 | medium | IN-SCOPE | R4 (test design) | Original E-04 "hold ... on the calling thread, invoke `_finalize_active_run`"; probe: such a call blocked its thread indefinitely | An in-process held-lock test hangs the whole pytest run when the fix regresses, instead of failing. It also cannot show that the process exits on a real signal. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-08: each held-lock case runs in a child process that receives a real `SIGTERM`, with `proc.wait(timeout=30)` and a named failure; helper tests hold the lock on a helper thread. |
| PR-007 | medium | IN-SCOPE | R2 (weak evidence) | Original V-01 to V-03 "Paste the relevant `git diff`"; V-04 "the summary line of a full `pytest` run showing 0 failures"; executed plan `m780uj` V-items record a full-suite failure that also fails on baseline | A diff does not show behavior, and "0 failures" may be unreachable because of an unrelated baseline failure. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Each V-item names its test case; V-08 adds related suites, a baseline comparison for any full-suite failure, and a mutation check. |
| PR-008 | medium | UNDER-SCOPE | R4 (doc sync and release notes) | `docs/architecture.md` "Lock ordering:" bullet; `CHANGELOG.md` `## [Unreleased]` `### Fixed` has the `94e504a` entry "A SIGTERM or SIGHUP that arrives while the background hardware refresh is writing the manifest no longer hangs the process." | The plan put the new rule only in a code comment and had no changelog entry for a user-visible hang fix. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added E-09 and V-09; `docs/architecture.md` and `CHANGELOG.md` added to `- Scope-Paths:`. |
| PR-009 | medium | UNDER-SCOPE | R7 (ordering) | `focjwv` Proposed changes "Rewrite `SubprocessSpy.finalize_all` in four phases"; this plan's original `- Item-Dependencies: none` | Both plans edit the lock blocks of `SubprocessSpy.finalize_all`. Without an edge, this plan could bound the old blocks and `focjwv` would then add new unbounded ones. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | `- Item-Dependencies: executed:focjwv`; E-06 applies the helper to the final lock blocks and leaves the `Popen.__del__` hook alone. |
| PR-010 | low | IN-SCOPE | S7 (execution contract) and `AGENTS.md` matrix validation | Original gate "commit only the scoped files through `aw commit`, and complete the post-gate lifecycle transition under `ipd-lifecycle`"; Deferred "None."; `tests/test_signals.py::TestLethalSignalFinalization` skips on win32 | The gate lacked the five-part contract. Signal behavior is POSIX-only, so `AGENTS.md` matrix discipline applies and needs a push. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Five-part contract naming `aw commit zcuoll` and `aw ipd finalize zcuoll`; matrix run under Deferred with `Carrier-Declined`; V-08 item 5 states the OS and Python version. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `complex` | `standard` | Tier answers 3 and 5 are yes; concurrency across 7 source modules | yes |
| D-2 | What to do when a lock is busy during signal finalization | Bounded acquire, then the same work lock-free; never skip the manifest | Skip the write; convert every lock to `RLock`; block as today | Commit `94e504a` pattern; `RLock` fixes only the same-thread form; `README.md` "never alters, slows, or crashes" | yes |
| D-3 | Bound values | 2.0 s for `_run_lock` and `_write_lock`, 0.25 s for the others, 0 s for a lock that already timed out | One bound for all; no wait at all | `pubrun-hw` legitimately holds `_run_lock` across a durable write, matching the existing `hw_done.wait(timeout=2.0)`; short critical sections elsewhere; the total stays under the tests' 30 s timeout | yes |
| D-4 | Change `_commit_lock`, `_CACHE_LOCK`, and the warning locks? | No; document them | Bound them too | Review traced no path where the main thread holds them during a finalization that needs them | yes |
| D-5 | Split into a Set? | No, keep one plan with a cohesion rationale | Three child plans (see Step R6) | One invariant; every part depends on the helper; each E-item is one file | yes |

### Step S5

- Checked: open questions. The plan has none, and the findings created none: each fix follows from repository evidence and review-time probes, D-2 follows the pattern commit `94e504a` already chose, and D-5 is a reversible structure choice. No finding is OPEN or DEFERRED, so the lane outcome carries no question.

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. All three changed (E-05 to E-09 and V-05 to V-09 added, five paths added, `executed:focjwv` added), so a re-check was done in this round: `aw ipd lint --phase review-finalize --agent` reported clean with 0 errors and 0 warnings and two `IPD-Z603` advisories answered by the cohesion rationale; each new E-item maps to one V-item; each V-item names a test case that E-08 creates; `focjwv` exists in `.aw/records/plans/pending/` with `- Status: reviewed`. No new question or structural ambiguity remains. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: complex`.

AW-REVIEW: DONE
