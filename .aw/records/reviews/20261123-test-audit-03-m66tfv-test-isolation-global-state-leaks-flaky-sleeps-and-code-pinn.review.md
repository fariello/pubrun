# Review findings: ipd m66tfv

- Subject-Id: m66tfv
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-03-m66tfv-test-isolation-global-state-leaks-flaky-sleeps-and-code-pinn.ipd.md` (front matter, Goal, Mermaid flowchart, E-01 to E-05, V-01 to V-05, conventions, findings, proposed changes, deferrals, scope check, required tests, documentation sync, open questions, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Proofreading edits kept front-matter values, the H2 heading list and order, E/V ids, checkbox states, Execution state values, and item field names unchanged. Substantive rewrites of E-items, V-items, and the gate are recorded under Findings, not here.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence naming "process-global test leaks", "flaky fixed-duration synchronization", and "code-pinning" without saying what each is | Three defect kinds, each defined in plain terms, with the `AGENTS.md` rule quoted | Requirements on defining terms at first use and one idea per sentence. |
| Goal, diagram | Three nodes; "post-test restore" listed caches and stdio but not the run stop or the signal handlers the plan must restore | Lead-in paragraph explaining the fixture teardown order; four nodes in the order the revised E-01 performs them | The diagram did not show the step that fixes the main defect (requirement 12). |
| Project conventions | One bullet on `pubrun_state_isolation` | Adds the three autouse fixtures and their teardown order, the import-time auto-start, and the `-p no:randomly` default | The executor needs these facts to place the E-01 change correctly. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (8 test files at start), E-01 to E-05, `tests/conftest.py`, every test the E-items name, `src/pubrun/capture/signals.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/resources.py`, `src/pubrun/report/output.py`, `benchmarks/harness.py`, siblings `bzi46m`, `g18xdt`, and `7y0gmc`, and orchestrator `vdxiw8`.

1. No: tests only; no library, CLI, file-format, or configuration contract changes.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. No: 5 E-items, one concern (test isolation and determinism), one or two test files per item.
4. Yes, but incomplete: the plan needs a regression test for the `conftest.py` fix that no listed file holds (PR-004).
5. Partly: `tests/conftest.py` runs around every test, so a mistake there can fail or mask many tests. It is a test-only change, reversible, and the full suite shows the effect.

AW-TIER: standard

### Step R1

- Checked: every cited path and symbol against lane HEAD `b360b6c`. `tests/conftest.py` defines autouse fixtures `isolated_cwd` (line 38), `clean_active_run`, and `pubrun_state_isolation`, in that order. `tests/test_signals.py:345` `test_warns_on_non_main_thread` calls `cap.install()` with no `uninstall()`; `:458` `time.sleep(0.5)` before `proc.send_signal(signal.SIGTERM)`. `tests/test_env_capture.py:135` `_t.sleep(30)`, `:155` `_t.sleep(0.4)`, `:161` `_t.sleep(0.5)`. `tests/test_resources.py:115-125` 1-second polling loop after `watcher._stop_event.clear()`. `tests/test_startup_overhead_writes.py:497` `time.sleep(0.02)`. `tests/test_bench_command.py:731-734` `test_schema_is_v5` reads `benchmarks/harness.py` with `read_text()` and calls `re.search`; `:346-349` and `:805-808` register `_bench_scenarios` and `_bench_aggregate` in `sys.modules` and never remove them. `benchmarks/test_pull_submissions.py:224` `test_no_eval_exec_in_source`. `tests/test_output.py:82-89` asserts on `out._DEFAULT_STREAM`. `pubrun.core.phase._yappi_active` is set with `getattr(phase, "_yappi_active", False)` in `src/pubrun/core.py:497-527`. `pubrun._reset_commit_cache` is at `src/pubrun/__init__.py:269`. `pubrun.capture.packages.invalidate_package_cache` is at `src/pubrun/capture/packages.py:634`.
- PR-001: pytest tears autouse fixtures down in reverse setup order, so `pubrun_state_isolation` tears down first and sets `pubrun.tracker._active_run = None`; `clean_active_run` then finds no active run and stops nothing. A scratch probe confirmed the previous test's run was still `is_active` True in the next test. Removing the early clear made it False. E-01 as written added more resets but left this order defect in place.
- PR-002: a leak census plugin (snapshot before and after every test) over `tests/` plus `benchmarks/test_pull_submissions.py` (`1902 passed, 2 skipped in 438.69s`) found the process signal handlers for SIGINT, SIGTERM, SIGHUP, SIGUSR1, and SIGUSR2 leaking from `test_hook_ownership_rollback.py`, `test_startup_overhead_writes.py::test_concurrent_hardware_refresh_vs_finalize_no_deadlock_or_clobber`, and `test_timing_accuracy.py::test_stalled_hardware_refresh_write_isolated_from_workload` (two parameters). E-01's list did not include signal handlers. `sys.excepthook` and `sys.exit` leaked from `test_new_features.py::TestConcurrentStart::test_only_one_run_created` and `test_signals.py::test_warns_on_non_main_thread`. `sys.modules` gained `_bench_scenarios` and `_bench_aggregate`. `_live_probe_sem` dropped from 8 to 6 permits. No leak of `sys.stdout`, `sys.stderr`, `_finalizing_active_run`, or `_yappi_active` was observed; `yappi` is not installed in the lane.
- PR-003: `invalidate_package_cache()` forces a full distribution-index rebuild of about 0.35 s; 322 tests reach the index in-process. Invalidating before every test raised a 93-test sample from 5.23 s to 20.70 s (50 rebuilds, 16.3 s). The cache is keyed by an environment fingerprint, so a stale index is not a correctness risk.

### Step R2

- Checked: author-phase lint (`aw ipd lint --phase author --agent`: `clean`, 0 findings), the E/V bijection, each V-item against what its E-item produces, and every command in a single Linux lane (lane `python3`: pytest 8.2.2, pytest-randomly 4.1.0; also a Python 3.12 virtual environment with pytest 9.2.0 and pytest-randomly 5.1.0).
- Prototype: all five E-items were applied in a scratch clone of the lane at `b360b6c` (not in the lane). Full suite in random order, `python3 -m pytest -p randomly --randomly-seed=12345 tests/ benchmarks/test_pull_submissions.py -q`: `1900 passed, 2 skipped in 442.98s`. The unmodified clone: `1902 passed, 2 skipped in 442.59s`. With the prototype, the leak census reported exactly one test per run: the first test collected. That report is not a leak. The census snapshot before that test still holds the hooks installed by the import-time auto-started run, and the snapshot after it holds the interpreter's own hooks, because `clean_active_run` stopped that run. No other test changed any tracked global.
- PR-005: E-05(a) asked for `h.run(...)["schema"] == "pubrun-benchmark/5"`. One `h.run` call took 15 s to 58 s at review. Sibling `bzi46m` E-02(a) already makes the identical `benchmarks/test_benchmarks.py` test behavioral, and `TestHarnessRedactedOnlyDefault.test_run_without_out_path_writes_nothing` in the same file already asserts the schema string on a real run. Deleting the code-pinning test loses no coverage.
- PR-006: E-05(c) as written would fail: `out.debug` prints nothing unless debug output is enabled (`src/pubrun/report/output.py` `debug_enabled()`), and the module global `_debug_enabled` must be restored afterwards. The prototype sets it with `monkeypatch.setattr` and sets `NO_COLOR=1`; it passed, and failed when `ok` was rerouted to stderr.
- PR-007: E-02 said "and other `cap.install()` tests", leaving the executor to decide which. Every other `cap.install()` test in `tests/test_signals.py` already uninstalls on its success path; E-01 covers the failure path. The SIGTERM test passed 30 of 30 runs without `time.sleep(0.5)`, because the child installs its handler in `pubrun.start()` before it prints the run directory. `cwd=tmp_path` does not change behavior, since `isolated_cwd` already puts the pytest process in `tmp_path`.
- PR-008: V-01 asked for `tests/test_signals.py` and `tests/test_env_capture.py` to pass in random order, but both already pass, so the evidence could not show E-01 works. No test anywhere exercised the teardown fix.
- PR-010: E-04 offered "`threading.Event` / pre-start mock" without choosing. For the resource test, patching `_poll_rss` before `start()` still needs a running thread and a wait; driving `_update_metrics()` directly is deterministic and still fails if 0 is treated as unreadable (prototype, `rss > 0`: `1 failed`). For the concurrent-readers test, a plain `Event` set after any read can be satisfied by a read that began before `stop()`; the prototype counts `len(readers) + 1` further reads under a `threading.Condition`.
- An unrelated failure seen in the scratch clone, `tests/test_cli.py::TestCliRunTests::test_run_tests_end_to_end_mock_validates_manifest`, came from stale `__pycache__` files in the clone; it passed after they were removed and passes in the lane.

### Step R3

- Checked: no new subprocess, network, or shell use. `test_conftest_isolation.py` runs pytest in a subprocess through the `pytester` fixture on a temporary directory. Deleting `test_no_eval_exec_in_source` removes a source-text scan, not a security control; `test_run_gh_uses_argv_no_shell`, `test_repo_slug_injection_rejected`, and `test_path_confinement_rejects_escape` keep the behavioral checks of the untrusted-input path. `python3 scripts/sanitize_paths.py --check --all` exited 0 on the prototype. No security finding.

### Step R4

- Checked: rubric sections on testability, anti-regression, right-sizing, and the `AGENTS.md` "no code-pinning tests" rule.
- PR-004: the fixture fix in E-01 had no regression test. Added `tests/test_conftest_isolation.py` to E-01 and `- Scope-Paths:`. It copies `tests/conftest.py` into a `pytester` project and asserts on outcomes (run stopped, hooks and handlers restored), not on fixture source. At review it passed with the prototype change and failed without it.
- PR-009: the gate said to "move this plan to `.aw/records/plans/executed/`" by hand and lacked the scope declaration, the validation-honesty rule, and the runner and executor split for finalization. It now carries the five-element execution contract with `aw ipd finalize m66tfv` and `--scope-reason`/`--scope-ack`, and it says not to edit `src/pubrun/` (sibling `7y0gmc` owns those seams).
- Sibling overlap: `g18xdt` scopes `tests/test_api.py` and `tests/test_new_features.py`; `7y0gmc` scopes `src/pubrun/capture/filesystem.py` and `resources.py` and says its new tests go to a separate file to stay disjoint from this plan. No Scope-Paths overlap.
- The new 9th Scope-Path triggers the `IPD-Z603` advisory (guidance: 8). The gate's cohesion rationale records why the file stays in this plan.

### Step S5

- Checked: open questions (none), deferrals (`Carrier: qqwebg` exists as an open backlog item; two `Carrier-Declined`), and every finding. Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so nothing needs a human answer and the lane outcome carries no question.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R1 (wrong mechanism) | `tests/conftest.py` fixture order; scratch probe: previous run `is_active` True in the next test | `pubrun_state_isolation` clears `_active_run` before `clean_active_run` can stop the run, so leftover runs and their hooks are never stopped. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01(a) stops the active run before `_reset()`; diagram and conventions describe the order. |
| PR-002 | high | IN-SCOPE | R1 (incomplete state list) | Leak census: SIGINT/TERM/HUP/USR1/USR2 handlers leak from 4 tests in 3 files | E-01 did not restore signal handlers, the most widely leaked global. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01(b) snapshots and restores every `_TARGET_SIGNALS` handler on the main thread; a deferral records why the out-of-scope tests need no edit. |
| PR-003 | medium | IN-SCOPE | R1 (performance regression) | 93-test sample 5.23 s to 20.70 s with per-test `invalidate_package_cache()` | E-01 would have quadrupled the run time of package-heavy tests for no correctness gain. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01(d) excludes it and gives the reason; V-01 checks it is absent. |
| PR-004 | medium | UNDER-SCOPE | R4 (no regression test) | No test exercised `conftest.py` teardown; prototype `pytester` test fails without the fix | The fixture fix could regress silently. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added `tests/test_conftest_isolation.py` to E-01(e), Scope, Scope-Paths, and the gate. |
| PR-005 | medium | IN-SCOPE | R2 (duplicate, slow) | `h.run` 15 s to 58 s; `bzi46m` E-02(a); `test_run_without_out_path_writes_nothing` | Rewriting `test_schema_is_v5` with `h.run` duplicated coverage and added up to a minute. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05(a) deletes the test and names the tests that already cover the schema. |
| PR-006 | medium | IN-SCOPE | R2 (would fail) | `src/pubrun/report/output.py` `debug_enabled()`; prototype passes and fails on rerouted `ok` | The planned stream test would see no `debug` output. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05(d) enables debug with `monkeypatch`, sets `NO_COLOR`, and states the assertions. |
| PR-007 | low | IN-SCOPE | R2 (executor decision left open) | `tests/test_signals.py` `cap.install()` tests; SIGTERM test 30 of 30 without sleep | "Other `cap.install()` tests" was undefined; the sleep removal and `cwd=tmp_path` lacked a basis. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 names the one test to change, explains why the sleep is unnecessary, and states that `cwd=tmp_path` is only explicit. |
| PR-008 | medium | IN-SCOPE | R2 (evidence cannot prove the change) | V-01 subset passes before E-01 | V-01 evidence would pass whether or not E-01 worked. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-01 requires the new test passing, then failing with the change reverted; V-03, V-04, and V-05 name the exact checks. |
| PR-009 | medium | IN-SCOPE | S7 (execution contract) | Plan `## Approval and execution gate` "move this plan to `.aw/records/plans/executed/`" | The gate told the executor to move the plan by hand and lacked three contract elements. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Replaced with the five-element contract and `aw ipd finalize m66tfv` with runner and executor ownership. |
| PR-010 | low | IN-SCOPE | R2 (ambiguous technique) | E-04 "`threading.Event` / pre-start mock"; prototype `rss > 0` mutation fails | E-04 left the synchronization design open, and a plain `Event` could be satisfied by a read from before `stop()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04 specifies direct `_update_metrics()` calls and a counted `threading.Condition` wait. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Scope-Paths needed a new file (tier answer 4), and `conftest.py` affects every test (answer 5); no public contract or safety-critical code | yes |
| D-2 | Where is the leftover run stopped? | In `pubrun_state_isolation` teardown, before `_reset()` | Reorder the fixtures; drop the early clear from `_reset()` | Keeps fixture order and `_reset()` unchanged for setup; the fix sits next to the snapshot it complements | yes |
| D-3 | Invalidate the package cache per test? | No | Per test; per module | Fingerprint-keyed cache; measured 4x slowdown on a sample | yes |
| D-4 | Rewrite or delete `test_bench_command.py::test_schema_is_v5`? | Delete | Rewrite with `h.run` | Two behavioral tests cover the schema; a rewrite costs 15 s to 58 s | yes |
| D-5 | Edit the out-of-scope tests that leak hooks? | No; the fixture restores their state | Add those files to this plan | Two of the files belong to `g18xdt`; after E-01 they leak nothing into later tests | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. The E/V id set is unchanged (E-01 to E-05, V-01 to V-05, `Highest E allocated: 05`, so `aw ipd sync` was not needed). `- Scope-Paths:` gained `tests/test_conftest_isolation.py`. `- Item-Dependencies:` is unchanged. A re-review pass is required.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: re-read the revised plan in full. Every citation in the rewritten E-items and V-items resolves at `b360b6c`, including `TestHarnessRedactedOnlyDefault.test_run_without_out_path_writes_nothing` (`tests/test_bench_command.py:540`), `pubrun.capture.signals._TARGET_SIGNALS` (`src/pubrun/capture/signals.py:27`), `ResourceWatcher._update_metrics` (`src/pubrun/capture/resources.py:474`), `LiveProbe._done` (`src/pubrun/capture/filesystem.py:321`), and the three retained `benchmarks/test_pull_submissions.py` behavioral tests. `tests/test_conftest_isolation.py` does not exist yet and no other plan creates it.

### Step R2

- Checked: `aw ipd lint --phase review-finalize --agent`: `clean`, exit 0, 0 errors, 0 warnings, 1 `IPD-Z603` advisory (9 Scope-Paths), which the gate's cohesion rationale addresses. E-01 to E-05 map 1:1 to V-01 to V-05; no `TODO` or `E-NEW` remains. Dependencies are acyclic (E-02 to E-04 need E-01; E-05 needs none). Each V-item names commands that run in a single Linux lane. Scope-Paths matches the Scope line, the gate's scope declaration, and the files the E-items edit.

### Step R4

- Checked: the new test asserts outcomes through a subprocess pytest run and reads `tests/conftest.py` only to install it as a fixture file, not to inspect its text. No rewritten test reads production source. Each E-item still edits one or two files.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 made no edits, so the E/V id set, `- Scope-Paths:`, and `- Item-Dependencies:` are unchanged since the start of this pass. No new finding. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
