# Review findings: ipd focjwv

- Subject-Id: focjwv
- Subject-Type: ipd
- Reviewed-At: 2026-11-24
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-86p7x3-01-focjwv-handle-popen-children-reaped-via-subprocess-internals-or-lef.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The H2 heading list and order, the existing E-01 to E-03 and V-01 to V-03 ids, checkbox states, and field names are unchanged. E-04, E-05, V-04, and V-05 were added (see PR-007 and PR-008). Substantive rewrites are recorded under Findings.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One long sentence | Says what `SubprocessSpy` records today, then three numbered results | Requirements 2 and 9. |
| E-01 Expected outcome | One paragraph mixing mechanism and result | Seven numbered outcomes, each checkable | Requirement 6; lets V-01 name each unit. |
| Project conventions | `module.function` citation form, partial patched-target list | `path::Name` and `path#Heading` forms, full target list, lock type, consumer list, CPython facts | Requirement 5; `steps/p-proofread.md` Section 11.1. |
| Findings | Three cases, case 1 attributed to `_cleanup()` or `__del__` together | Four cases with review-time probe results, plus the deadlock and sentinel hazards | Requirements 5 and 11: the two internal paths behave differently. |
| Diagram | Edge label "Yes - returncode set after prev __del__" | Separate decisions on the value of `returncode` in the hook | Requirement 12; removed the hyphen-as-dash label and the merged decision. |
| Workflow history | Oldest first | Newest first | `steps/s7-finalize.md`: the section is newest-first. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:`, E-01 to E-03, `src/pubrun/capture/subprocesses.py`, `schemas/manifest.schema.json`, and the manifest consumers.

1. Yes: the manifest value of `subprocesses[].capture_state.status` changes from `"complete"` to `"partial"` for unwaited children, and `docs/manifest.md` documents that output format.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. No: 3 E-items at review start (5 after review) in 1 task group, one source module.
4. Yes: 3 files at review start; the review added 4 more that describe the same behavior.
5. Yes: a new process-global patch on `subprocess.Popen.__del__` runs on any thread during garbage collection, so a mistake can deadlock or break the host program.

AW-TIER: standard

### Step R1

- Checked: every symbol and claim in the plan against the code. `src/pubrun/capture/subprocesses.py::SubprocessSpy.install`, `::uninstall`, `::finalize_all`, `_complete_popen_record`; `src/pubrun/tracker.py::Run._rollback_owned_hooks`; `schemas/manifest.schema.json` `$defs.subprocess_record`, `$defs.capture_state`, `$defs.status_value`; CPython `subprocess.Popen.__del__`, `subprocess._cleanup`, `Popen._internal_poll` (read with `inspect.getsource` on 3.12.3 and 3.14.6).
- The plan said `SubprocessSpy` patches `__init__`, `wait`, and `poll`: correct. Six doc lists omit `poll` (PR-007).
- The plan said the schema allows `"partial"` with `detail`: correct. `ended_at_utc` and `exit_code` allow `null`.
- The plan said only `test_detached_subprocess_finalized` must change: wrong (PR-005).
- Backlog `86p7x3` says the status stays `"running"`: wrong, the code writes `"complete"`; corrected in the plan's Findings.

### Step R2

- Checked: E/V bijection, Scope-Paths, dependencies, evidence demands, and the gate. `aw ipd lint --phase author --agent` was clean before edits; `--phase review-finalize --agent` was clean after edits.
- Probes at review (Python scripts under `/tmp/opencode`, CPython 3.12.3 and 3.14.6, Linux):
  - A `__del__` wrapper read `returncode == 7` for an exited, collected child.
  - A child dropped while running entered `subprocess._active`. After the next `Popen()` ran `_cleanup()`, it was gone from `_active` and its `weakref.ref` was dead. A wrapper that kept a strong reference read `returncode == 3`.
  - A child reaped with `os.waitpid` before `__del__` got `returncode == 9223372036854775807` (`sys.maxsize`).
  - `os.waitid(..., WEXITED | WNOHANG | WNOWAIT)` returned `None` for a running child, 7 for an exited one (with `returncode` still `None`, later `wait()` returned 7), and -15 for a SIGTERM-killed one.
  - A `__del__` wrapper that ran while its own thread held a `threading.Lock` could not acquire that lock within 1 second.

### Step R3

- Checked: security and robustness of the new hook. The hook records no new data: argv redaction is unchanged and the `detail` strings are fixed literals with no paths or values. The risk is availability: a hook that blocks, raises, or keeps objects alive. PR-002 and PR-004 cover blocking and object lifetime; the hook body is wrapped in `try/except Exception` and chains to the previous `__del__` first in `try/finally`.

### Step R4

- Checked: engineering soundness, tests, docs, and release notes. The weak-reference-only design loses case 2 (PR-001). `finalize_all` would call `_complete_popen_record` under a non-reentrant lock (PR-002). Tests relied on `time.sleep(0.1)` timing (PR-005). User-visible manifest values change, so `CHANGELOG.md` needs an entry (PR-008). `AGENTS.md` matrix-validation discipline applies to a capture-engine output change (PR-009).

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R4 (design defect) | Original Proposed changes item 1 "Store a `weakref.ref(self)` ... mapped to the record"; CPython `subprocess.Popen.__del__` appends a running instance to `_active`; probe: weakref dead after `_cleanup()` | A child dropped while running is reaped later by `subprocess._cleanup()`, which calls `_internal_poll` and then frees the object without calling `__del__` again. A weak reference is dead by then, so the plan's headline case (`_cleanup()` reaping) records nothing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | The hook keeps a strong reference for a still-running child in `_pending_running`; a drain after each patched `Popen.__init__` and in `finalize_all` reads `returncode`. E-01 outcome 4; `test_cleanup_reaped_child_records_exit_code`. |
| PR-002 | high | UNDER-SCOPE | R3 (deadlock) | `src/pubrun/capture/subprocesses.py` `_lock = threading.Lock()`; `SubprocessSpy.finalize_all` "with cls._lock:"; `_complete_popen_record` "with cls._lock:"; probe: a `__del__` wrapper could not acquire a lock its own thread held | The original hook called `_complete_popen_record`, which takes the non-reentrant `SubprocessSpy._lock`. Garbage collection can run `__del__` on a thread that already holds that lock, which blocks the host forever. The original `finalize_all` design would also call `_complete_popen_record` while holding the lock. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | The hook takes no lock and only appends to `collections.deque` queues. `finalize_all` runs the drain and the `poll()` calls outside the lock. E-01 outcomes 2 and 5; `test_popen_del_hook_does_not_take_spy_lock`. |
| PR-003 | medium | UNDER-SCOPE | R1 (sentinel value) | CPython `Popen.__del__(self, _maxsize=sys.maxsize, ...)` calls `_internal_poll(_deadstate=_maxsize)`; probe: `returncode == 9223372036854775807` after `os.waitpid` | When the exit status was collected outside `subprocess`, `returncode` is `sys.maxsize`. The plan would record that as a real exit code. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | `_complete_record` maps `sys.maxsize` to `"partial"` with the detail "child exit status was collected outside pubrun and is unavailable". E-01 outcome 6; `test_externally_reaped_child_is_partial_not_sentinel`. |
| PR-004 | medium | UNDER-SCOPE | R4 (object lifetime) | Original Proposed changes "clean up the mapping entry when the record completes or during `finalize_all()`"; `src/pubrun/capture/subprocesses.py::SubprocessSpy.uninstall` resets only records | Holding `Popen` references across runs would leak objects and could deliver one run's exit into another run's records. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | `install` and `uninstall` reset `_pending_exits`, `_pending_running`, and `_popen_refs`; `finalize_all` clears the last two; the hook checks `_pubrun_state is state` and `state["active"]`. E-01 outcome 7. |
| PR-005 | medium | UNDER-SCOPE | R2 (tests) | `tests/test_capture.py::TestFinalizeAll::test_upgrades_partial_to_complete` "assert rec[\"capture_state\"][\"status\"] == \"complete\""; `::TestSubprocessSpyMonotonicTiming::test_finalize_all_monotonic_non_collision_and_post_finalize_wait` "assert real_rec[\"capture_state\"][\"status\"] == \"complete\""; `test_detached_subprocess_finalized` uses `time.sleep(0.1)` | Two more existing tests assert `"complete"` for unwaited records and would fail. The detached-child test's outcome depended on whether a 0.1-second child had exited, so the new assertions would be flaky. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Proposed changes item 2 names every changed and new test, makes each child's exit depend on a closed stdin pipe, and waits with `os.waitid(WNOWAIT)` or the original `poll`. |
| PR-006 | medium | IN-SCOPE | R2 (weak evidence) | Original V-01 "Paste `git diff` ... showing weakref tracking"; V-02 "plus the summary line of a full `pytest` run showing 0 failures" | A diff does not show behavior, and the full suite has a known xdist-only failure unrelated to this plan (recorded in executed plan `m780uj`), so "0 failures" could be unachievable. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-items name each outcome, add a mutation check that disables the hook, an unraisable-exception check, a baseline comparison for any full-suite failure, and dash and stale-phrase greps whose patterns were run at review. |
| PR-007 | medium | UNDER-SCOPE | R4 (doc sync) | `docs/functional_spec.md#15.1 Mechanism` "monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system`"; same list in `docs/architecture.md` (3 places), `docs/api.md` (table row), and `docs/functional_spec.md` ("Enforce transactional installation") | Six lists of patched targets omit `Popen.poll` today and would omit `Popen.__del__`. `docs/functional_spec.md#15.2 Recorded Fields` says finalization "closes an unwaited record". | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added E-04 and V-04 and the three files to `- Scope-Paths:`. |
| PR-008 | medium | UNDER-SCOPE | R4 (release notes) | `CHANGELOG.md` `## [Unreleased]` has a `### Fixed` section | Manifests change from `"complete"` to `"partial"` for unwaited children, which users filtering on status will see. The plan had no changelog entry. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added E-05 and V-05 and `CHANGELOG.md` to `- Scope-Paths:`. |
| PR-009 | medium | IN-SCOPE | S7 (execution contract) and `AGENTS.md` matrix validation | Original gate "commit only the scoped files through `aw commit`, and complete the post-gate lifecycle transition under `ipd-lifecycle`"; `AGENTS.md` "Matrix-validation discipline"; CPython `_cleanup()` is a no-op on Windows | The gate lacked the precondition, scope declaration, validation-honesty rule, never-push rule, and the runner or executor split for `aw ipd finalize`. The plan did not say that OS-dependent behavior needs the CI matrix, which needs a push. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Five-part execution contract naming `aw commit focjwv` and `aw ipd finalize focjwv`; matrix run recorded under Deferred with `Carrier-Declined`, and V-02 item 5 states the OS and Python version that ran. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Tier answers 1 and 5 are yes; one module, one task group | yes |
| D-2 | Patch private `Popen._internal_poll`? | No | Patch it | The plan's own Scope forbids it, and public hooks plus a strong-reference queue cover all four cases measured at review | yes |
| D-3 | Status for an exit status collected outside pubrun | `"partial"` with a detail, `exit_code` null | Record `sys.maxsize`; record `0` like CPython's ECHILD branch | `sys.maxsize` and `0` would both be invented exit codes | yes |
| D-4 | Fix the six doc target lists in this plan or file a backlog item | This plan | New backlog item | This plan adds `Popen.__del__`, so every list must change anyway; `poll` is fixed in the same edit | yes |

### Step S5

- Checked: open questions. The plan has none, and the findings created none: each fix follows from repository and CPython evidence, and the backlog item `86p7x3` acceptance criteria allow either recording the exit code or a distinct status, which the plan does for each case. No finding is OPEN or DEFERRED, so the lane outcome carries no question.

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. E-04, E-05, V-04, and V-05 were added and `- Scope-Paths:` gained four files, so a re-check was done in this round: `aw ipd lint --phase review-finalize --agent` reported clean with 0 findings, the new E-items each map to one V-item, and the V-04 and V-03 stale-text greps were run against the current docs (6 and 1 matches) to confirm they detect the text they must remove. No new question or structural ambiguity remains. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
