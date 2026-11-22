# Review findings: ipd p6pon8

- Subject-Id: p6pon8
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Antigravity / Gemini
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text, front matter, Mermaid diagrams, E-01 through E-05, V-01 through V-05, Project conventions, Proposed changes, Open questions, and Approval and execution gate of `.aw/records/plans/pending/20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Deferred, Scope check, Spec sync | Bare IDs (`ed0yds`, `26euz0`, `zp2yyu`, `x21s6w`) | Added concise descriptive labels for each referenced sibling plan and backlog item | Technical writing requirement 1 and reference check rule (name what referenced artifacts define or own). |
| E-02, E-03, E-04 Expected outcomes | Dense 100+ word single-sentence outcomes | Split into short, complete sentences naming each actor, condition, and outcome | Technical writing requirements 2 and 3 (short complete sentences, explicit actor and action). |
| Project conventions, Proposed changes | Informal `file.py` (`func`) references | Standardized code citations to `path::Symbol` format (for example `src/pubrun/capture/console.py::ConsoleInterceptor.stop`, `tests/test_signals.py::TestSignalNonMainThread.test_warns_on_non_main_thread`) | `steps/p-proofread.md` Section 11.1 code citation format. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: `.aw/records/plans/pending/20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md` front matter, Scope-Paths, E-items, and downstream contracts with `ed0yds`, `frzw20`, and existing capture-engine tests.

1. Yes: adds `format_safe_error_detail()` (consumed across `ed0yds`) and changes `SubprocessSpy`, `ConsoleInterceptor`, `SignalExitCapture`, and `ResourceWatcher` install/uninstall/stop contracts relied upon by `ed0yds` and existing tests.
2. Yes: directly modifies secret-redaction logic (`src/pubrun/capture/redaction.py`, `src/pubrun/capture/invocation.py`) and process-global hook restoration (`subprocess.Popen`, `os.system`, `sys.stdout`/`sys.stderr`, `faulthandler`, `signal`, `sys.excepthook`).
3. No: 5 E-items in 2 task groups across 6 cohesive capture modules and 1 new test file (7 Scope-Paths).
4. Yes: `- Scope-Paths:` explicitly lists all 7 files modified or created.
5. Yes: defects in global hook restoration or redaction can break host-program I/O, signal delivery, or exception handling, or leak secrets into manifests (`Blocks-Release: next`).

AW-TIER: standard

### Step R1

- Checked: Every cited file and symbol against the repository: `src/pubrun/capture/redaction.py`, `src/pubrun/capture/invocation.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/console.py`, `src/pubrun/capture/signals.py`, `src/pubrun/capture/resources.py`, `tests/test_capture.py`, `tests/test_signals.py`, `tests/test_resources.py`, `tests/test_quality.py`, `tests/test_edge_cases.py`, `tests/test_cli.py`, `tests/test_pause_resume.py`, backlog item `x21s6w`, orchestrator `frzw20`, and dependent child plan `ed0yds`. All cited files exist; concrete code-level hazards in `signals.py` (`_previous_excepthook = None` breaking third-party chains), `subprocesses.py` (cross-run `Popen.wait` index reuse, concurrent `uninstall()` `IndexError` in `os.system`, raw `str(e)`), `resources.py` (unstarted/aborted final poll, unguarded `emit()`), `console.py` (`TqdmSafeTee.flush()` unguarded `original_stream`), and `tests/test_signals.py`/`tests/test_cli.py` compatibility were verified and addressed.

### Step R2

- Checked: E/V 1:1 bijection (`E-01`..`E-05` to `V-01`..`V-05`), Scope-Paths completeness, `Item-Dependencies: none`, cross-plan API compatibility with `ed0yds`, runtime-demonstration reachability of `V-01`..`V-05`, and `## Approval and execution gate` compliance against `steps/r2-executability.md` and `steps/s7-finalize.md`. Caught and fixed prohibited scope-fence STOP wording and hand-rolled `git mv` lifecycle wording (PR-006).

### Step R3

- Checked: Secret redaction boundaries in `redaction.py`, `invocation.py`, `subprocesses.py`, and `signals.py`. Caught and fixed unredacted raw `str(e)` in `SubprocessSpy` and unredacted `_exit_exception` in `SignalExitCapture._excepthook`, plus `format_safe_error_detail()` key-value/colon/flag/custom-regex-fallback edge cases (PR-001).

### Step R4

- Checked: Engineering rubric A (correctness/concurrency/data integrity), C (architecture/operability), D (anti-regression/invariants), E (testing/verification), F (KISS/principles), right-sizing/conceptual density (all 5 E-items are bounded and focused), and `## Spec / documentation sync`. Caught and fixed `SubprocessSpy` generation-tagging and `os.system` `IndexError` races (PR-002), `ConsoleInterceptor` `TqdmSafeTee.flush()` and pytest `faulthandler` test-isolation details (PR-003), `SignalExitCapture` non-main-thread regression and `_excepthook` closure chain bug (PR-004), `ResourceWatcher.stop()` unstarted/aborted polling and unguarded `emit()` bugs (PR-005), and expanded targeted regression tests (PR-008).

### Step S5

- Checked: Pre-existing `OQ-01` and all review findings. All 8 findings had Low remediation risk and were fixed in place with zero remaining unresolved or deferred findings and zero blocking human questions. Fixed `OQ-01` owner provenance per `steps/s5-questions.md` rule 5 (PR-007) and recorded reversible decisions below.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R3 (Secret redaction completeness and `format_safe_error_detail` edge cases) | `src/pubrun/capture/subprocesses.py:171,239`; `src/pubrun/capture/signals.py:223,228`; `src/pubrun/capture/redaction.py:145`; `p6pon8:116-121` | `SubprocessSpy` (`_patched_popen_init`, `_patched_os_system`) and `SignalExitCapture._excepthook` still store raw unredacted `str(e)` / `exc_value`; `format_safe_error_detail()` did not cover empty messages, `max_len <= 3`, colon/space-separated secrets (`password: val`, `--token val`), hyphenated `sk-proj-...` keys, or fallback to default regex when a custom config regex is invalid. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Routed `SubprocessSpy` failure details and active `SignalExitCapture._excepthook` messages (preserving `"SystemExit(42)"` for int/None codes) through `format_safe_error_detail()`, and specified empty-message, `max_len <= 3`, key-value/colon/flag/hyphenated-key, and invalid-regex-fallback handling in Proposed changes item 1 (recommendation strength: strong). |
| PR-002 | high | IN-SCOPE | R4 (Concurrency and cross-run record corruption in `SubprocessSpy`) | `src/pubrun/capture/subprocesses.py:177,190-197,225-245`; `p6pon8:125-141` | Two runtime bugs remained in `SubprocessSpy`: (a) after `uninstall()` and re-`install()`, a lingering `Popen.wait()` from Run 1 carries `_pubrun_idx = 0` and can overwrite Run 2's `_records[0]`; (b) in `_patched_os_system`, concurrent `uninstall()` clears `_records = []`, causing `cls._records[idx]` to raise `IndexError` into the host script. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required tagging `Popen` instances with `self._pubrun_state = state` and `self._pubrun_rec = rec` (updating only when `state["active"]` and `self._pubrun_state is state`), and holding a direct local `rec` reference in the `os.system` wrapper instead of re-indexing `cls._records[idx]`, with behavioral tests in E-05 (recommendation strength: very strong). |
| PR-003 | high | IN-SCOPE | R1 / R4 (`ConsoleInterceptor` `TqdmSafeTee.flush` safety and `faulthandler` test isolation) | `src/pubrun/capture/console.py:166-184`; `tests/test_cli.py:1049-1075`; `p6pon8:144-166,207` | `TqdmSafeTee.flush()` only catches `BrokenPipeError` on `original_stream.flush()` (not closed-stream `OSError`/`ValueError`), detaching `self.log_file = None` before logging was not specified to prevent stderr recursion, and pytest's built-in `faulthandler` plugin enables `faulthandler` before tests run, which would break the "disabled before `start()`" test unless explicitly disabled and restored in `finally`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified `(BrokenPipeError, OSError, ValueError)` guard in `TqdmSafeTee.flush()`, detaching `log_file = None` with `_in_error_log` guard, `self._cached_result` idempotency in `ConsoleInterceptor.stop()`, and explicit `faulthandler` disable/restore fixture discipline in `tests/test_hook_ownership_rollback.py` (recommendation strength: strong). |
| PR-004 | high | IN-SCOPE | R1 / R4 (`SignalExitCapture` third-party `excepthook` chain break and non-main-thread regression) | `src/pubrun/capture/signals.py:136-147,176-190,231-232,256`; `tests/test_signals.py:345-364`; `p6pon8:170-185` | `_restore_excepthook()` sets `self._previous_excepthook = None` even when a post-install third-party `excepthook` still wraps `_excepthook`, silently breaking exception forwarding; `_excepthook` lacked an `_active` deactivation check; `_make_handler` needed to skip `_finalize_active_run()` when deactivated; and `install()` rollback needed to distinguish expected per-signal `(OSError, ValueError)` non-main-thread skips from unexpected install failures to preserve `TestSignalNonMainThread`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required closure-captured `prev_hook` and `if not _self._active:` passive passthrough in `_excepthook()`, skipping `_finalize_active_run()` when deactivated in `_make_handler()`, and preserving per-signal `(OSError, ValueError)` skipping while rolling back on unexpected install or excepthook errors, with behavioral tests in E-05 (recommendation strength: very strong). |
| PR-005 | high | IN-SCOPE | R4 (`ResourceWatcher.stop()` unstarted/aborted poll and unguarded `emit()`) | `src/pubrun/capture/resources.py:458-482`; `tests/test_resources.py:129-143`; `p6pon8:186-196` | Skipping `join()` on an unstarted `ResourceWatcher` still entered `if not self.is_alive():` and polled an unstarted or already self-aborted watcher; `event_stream.emit()` inside `_update_metrics()` was unguarded and could kill the polling thread. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required checking `was_started = self.ident is not None`, running final polling only when `was_started and not self.is_alive() and not self._aborted_due_to_failures` inside `try/except`, and guarding `event_stream.emit()` inside `_update_metrics()` (recommendation strength: strong). |
| PR-006 | high | IN-SCOPE | R2 / S7 (Execution contract policy) | `.aw/records/plans/pending/20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md:287,290`; `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | Gate item 2 carried prohibited "if additional files seem required, STOP and report" wording for out-of-scope edits, and gate item 5 instructed a hand-rolled lifecycle move to `executed/` instead of conditional runner/executor `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Rewrote gate item 2 as a scope declaration with `--scope-reason`/`--scope-ack` justification (reserving STOP for genuinely unsafe conditions) and gate item 5 with conditional runner/executor `aw ipd finalize` ownership (recommendation strength: very strong). |
| PR-007 | low | IN-SCOPE | S5 (Open-question owner provenance) | `.aw/records/plans/pending/20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md:244-250`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | `OQ-01` recorded `- Owner: maintainer (confirmed upon plan approval)` on a resolved question that the plan author resolved from Python `faulthandler` stdlib behavior rather than the maintainer answering. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Updated `- Owner:` to `plan author (confirmable upon plan approval)` and logged the reversible decision in `### Decisions` (`D-1`) below (recommendation strength: strong). |
| PR-008 | low | IN-SCOPE | P / Technical Writing and regression test coverage | `.aw/records/plans/pending/20261121-cap-isolation-01-p6pon8-safe-diagnostic-redaction-and-hook-ownership-rollback-across.ipd.md:79,84,221-240`; `tests/test_edge_cases.py:171-206`; `tests/test_pause_resume.py:27-97`; `tests/test_cli.py:1049-1085` | Bare sibling IDs lacked descriptive labels, E-03/E-04 Expected outcomes were dense single run-on sentences, code citations lacked `path::Symbol` form, and `Required tests / validation` omitted `tests/test_edge_cases.py`, `tests/test_pause_resume.py`, and `tests/test_cli.py -k "faulthandler or excepthook"`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added descriptive labels for cited IDs, split E-02/E-03/E-04 run-on outcomes, standardized `path::Symbol` citations, and added the missing regression test targets to E-05, V-05, and Required tests (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | `faulthandler` ownership policy (`OQ-01`) when already enabled before `ConsoleInterceptor.start()`, and owner provenance | Enable `faulthandler` on `stderr.log` only when `faulthandler.is_enabled()` is `False`, disable on `stop()` only when owned, and record `- Owner: plan author (confirmable upon plan approval)` | Always call `faulthandler.enable(file=self.stderr_log)` and `disable()` (destroys user/test-runner `faulthandler` state because stdlib does not expose the prior file object) | `src/pubrun/capture/console.py:231-235,264-271`; `tests/test_cli.py:1049-1075`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | How to keep `SignalExitCapture._excepthook` safe when a post-install third-party wrapper remains attached after `uninstall()` | Capture `prev_hook = sys.excepthook` in a local closure variable and short-circuit to `prev_hook` when `not _self._active` | Read `self._previous_excepthook` inside `_excepthook` (becomes `None` after `_restore_excepthook()`, breaking the third-party chain) | `src/pubrun/capture/signals.py:205-258`; `tests/test_edge_cases.py:171-191` | yes |
| D-3 | How to prevent `SubprocessSpy` cross-run record overwrites and concurrent `uninstall()` `IndexError` | Tag `Popen` instances with `self._pubrun_state = state` and `self._pubrun_rec = rec`, and hold a direct local `rec` reference in `os.system` | Continue indexing `cls._records[idx]` (races with `cls._records = []` on `uninstall()` and reuses index 0 across re-installs) | `src/pubrun/capture/subprocesses.py:176-247` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
