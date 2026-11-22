# Review findings: ipd 8co0wy

- Subject-Id: 8co0wy
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Antigravity / Gemini
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text, front matter, Mermaid diagram, E-01 through E-05, V-01 through V-05, Project conventions, Findings, Proposed changes, Deferred, Scope check, Spec/documentation sync, Open questions, and Approval and execution gate of `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Concern, Goal, Findings, Proposed changes, Deferred | Unexpanded `CPU`, `UTC`, `I/O`, `POSIX`, `TUI` | Expanded each acronym/abbreviation on first use | Technical writing requirement 1 (expand acronyms on first use). |
| Capture timing flow diagram | Omitted symmetric post-profiler-setup `start_mono`, launch-failure `ended_at_utc`/`capture_state`, and `id(rec)` lookup semantics | Aligned nodes B, C, E, and F with normative text in `## Proposed changes` | Technical writing requirements 12(d) and 12(e) (diagram must match normative text). |
| E-01, E-02, E-03, E-04 Expected outcomes | Dense single-sentence blocks | Split into short, complete sentences | Technical writing requirement 2 (short, complete sentences). |
| Project conventions, Findings, Proposed changes | Informal `file.py` + `method()` references | Standardized code citations to `path::Symbol` format (for example `src/pubrun/core.py::phase.__enter__`, `src/pubrun/capture/subprocesses.py::SubprocessSpy`) | `steps/p-proofread.md` Section 11.1 code citation rules. |
| Deferred, Scope check, Spec sync, Gate item 1 | Bare IDs (`e1fwy2`, `vrr1fv`, `3tvesf`, `6hp1zu`) and missing `- Carrier:` lines | Attached concise descriptive labels and added `- Carrier: e1fwy2`, `- Carrier: vrr1fv`, and `- Carrier: 3tvesf` | Technical writing requirement 1, reference rule, and `check.ipd-uncarried-obligation`. |
| Validation and cross-check boilerplate | Two em dashes (`—as distinct from ... by construction—`) triggering `IPD-C802` | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md` front matter, `- Scope-Paths:`, E-items, and cross-plan interfaces with `e1fwy2`, `vrr1fv`, and `3tvesf` in Set `timing-acc`.

1. Yes: extends `events.jsonl` `phase_end` payload (`elapsed_seconds`, `duration_clock`) and `manifest.json` `subprocesses[]` records produced by `SubprocessSpy` and explicit `pubrun.subprocess.*`/`pubrun.popen` wrappers (`elapsed_seconds`, `duration_clock`, `capture_state`), which sibling plans `vrr1fv` and `3tvesf` rely on.
2. No: does not touch code guarding private data, repository commits, worktree isolation, merges to main, or the sandbox (`redact_argv` in `SubprocessSpy` stays unchanged).
3. No: 5 E-items across 2 focused task groups and 6 related Scope-Paths (3 source files, 3 test files).
4. Yes: `- Scope-Paths:` explicitly lists all 6 files modified or audited.
5. Yes: `SubprocessSpy` monkey-patches global `subprocess.Popen` and `os.system` across threads; a locking, indexing, or exception-handling defect could break host subprocess execution or manifest schema conformance, and a `phase.__exit__` defect could break profiler teardown or exception propagation.

AW-TIER: standard

### Step R1

- Checked: Every cited file, symbol, schema definition, and sibling artifact against the repository: `src/pubrun/core.py` (`phase.__init__`/`__enter__`/`__exit__`, mid-file `import time` at line 466, `_PubrunSubprocessNamespace.run`, `_PubrunSubprocessNamespace.Popen`, `popen`), `src/pubrun/capture/subprocesses.py` (`SubprocessSpy.install`, `uninstall`, `finalize_all`, `_patched_popen_init`, `_patched_popen_wait`, `_patched_os_system`), `src/pubrun/capture/resources.py` (`ResourceWatcher._poll_cpu`, `_poll_tree_cpu`, zero `time.time()` calls across all 546 lines), `src/pubrun/capture/system_metrics.py`, `src/pubrun/events.py::EventStream.emit`, `schemas/manifest.schema.json` (`$defs.subprocess_record`, `$defs.capture_state`), `tests/test_events.py`, `tests/test_capture.py` (`TestFinalizeAll`), `tests/test_explicit_api.py`, `tests/test_api.py` (`phase_end` assertions), `tests/test_resources.py`, `.aw/records/backlog/graduated/20261121-pubrun-improve-01-6hp1zu-timing-accuracy.backlog.md`, orchestrator `nr63qr`, prerequisite `e1fwy2` (and its review record), and sibling plans `vrr1fv` and `3tvesf`.

### Step R2

- Checked: E/V 1:1 bijection (`E-01`..`E-05` to `V-01`..`V-05`), Scope-Paths completeness, `Item-Dependencies: executed:e1fwy2` matching orchestrator `nr63qr`, runtime-demonstration reachability of all `V-*` items, and `## Approval and execution gate` compliance against `steps/r2-executability.md` and `steps/s7-finalize.md`. Caught and fixed non-conforming scope-fence STOP wording, audit-only `--scope-ack` guidance for `resources.py`, and hand-rolled lifecycle move instructions (PR-004).

### Step R3

- Checked: Verified raw process-local `time.perf_counter()` counter values are never serialized into `events.jsonl` or `manifest.json` (`_start_monos` stays in-memory only and is cleared on `install()`/`uninstall()`), existing `redact_argv` sanitization in `SubprocessSpy` is preserved, and exception handling never swallows host exceptions.

### Step R4

- Checked: Engineering rubric A (correctness/data integrity), C (architecture/operability), D (anti-regression/domain invariants), E (testing/verification), F (KISS/principles), right-sizing/conceptual density (5 focused E-items across 6 Scope-Paths), and `## Spec / documentation sync` (deferred cleanly to `3tvesf`). Caught and fixed `core.py` `import time` order, `phase.__init__` `_start_mono` init and unambiguous post-profiler-setup boundary (PR-001), `Popen.__init__`/`popen` launch-failure parity and `TimeoutExpired` handling (PR-002), `SubprocessSpy` `id(rec)` keying to prevent stale-index collisions with `TestFinalizeAll` and `uninstall()` races (PR-003), and deterministic unstarted-instance `ResourceWatcher` / `cProfile.dump_stats` / `tests/test_api.py` test coverage (PR-005).

### Step S5

- Checked: Pre-existing `OQ-01`, deferred carrier obligations, and all review findings. All 7 findings had Low remediation risk and were fixed in place with zero remaining unresolved or deferred findings and zero blocking human questions. Fixed `OQ-01` owner provenance per `steps/s5-questions.md` rule 5, added `- Carrier:` lines to all three deferred rows (PR-006), and recorded reversible decisions `D-1` and `D-2` below.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R4.A / R4.D (`phase` initialization, import order, and start boundary) | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:56,99-101`; `src/pubrun/core.py:315-412,466` | `import time` appears at line 466 of `src/pubrun/core.py` below `class phase:`; `phase.__init__` did not initialize `self._start_mono = None` (risking `AttributeError` if `__enter__` is skipped); and Proposed changes #1 hedged the `start_mono` capture boundary ("after profiler startup ... or before user body executes"). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required moving `import time` to top-level imports in `src/pubrun/core.py`, initializing `self._start_mono: Optional[float] = None` in `phase.__init__`, capturing `self._start_mono = time.perf_counter()` as the final line of `phase.__enter__` (symmetric with `end_mono` before profiler teardown in `__exit__`), and guarding `self._start_mono is not None` and `exc_val is not None` in `__exit__` (recommendation strength: very strong). |
| PR-002 | high | IN-SCOPE | R4.A / R4.D (Explicit subprocess failure parity and schema conformance) | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:61,102-105`; `src/pubrun/core.py:737-889`; `e1fwy2:157-162` | `Popen.__init__` and `popen()` did not catch launch exceptions (`FileNotFoundError`, `OSError`) despite E-02 requiring consistent failed-invocation recording; `run()` exception records must preserve existing `"error"` alongside schema-required `"capture_state"`; and `Popen.wait(timeout)`/`communicate(timeout)` needed explicit non-logging on `TimeoutExpired`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified launch-exception recording with `ended_at_utc`, `elapsed_seconds`, `duration_clock`, `"error"`, and schema-conformant `"capture_state"` across `run()`, `Popen.__init__()`, and `popen()`, guarded `_pubrun_start_mono` lookup, and preserved `TimeoutExpired` deferral across E-02, Proposed changes #2, and V-02 (recommendation strength: very strong). |
| PR-003 | high | IN-SCOPE | R4.A / R3 (`SubprocessSpy` stale-index collision and concurrency races) | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:66,107-111`; `src/pubrun/capture/subprocesses.py:75-96,112-122,187-247`; `tests/test_capture.py::TestFinalizeAll:173-204` | Keying `_start_monos` by integer list index `idx` allows stale entries from un-cleaned runs to collide with synthetic `SubprocessSpy._records = [...]` in `TestFinalizeAll`, risks `IndexError` in `_patched_os_system` if `uninstall()` runs concurrently, and did not protect already-finalized durations if `_patched_popen_wait` runs after `finalize_all()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified `id(rec)`-keyed `_start_monos: Dict[int, Tuple[Dict[str, Any], float]]` cleared under `cls._lock` in both `install()` and `uninstall()`, local `rec` references in `_patched_os_system`, and preserving already-finalized durations when `entry` was already popped in `_patched_popen_wait` (recommendation strength: very strong). |
| PR-004 | high | IN-SCOPE | R2 / S7 (Execution contract policy) | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:188,191`; `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`; `.aw/system/workflows/plan-review/steps/r2-executability.md:59-60` | Execution contract item 2 contained prohibited "if additional files seem required, STOP and report" wording and omitted `--scope-ack` guidance for audit-only `resources.py`, and item 5 instructed a hand-rolled lifecycle move to `executed/` instead of conditional direct-vs-runner `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Rewrote gate item 2 as a scope declaration with `--scope-reason`/`--scope-ack` guidance (explicitly noting unmodified audit-only `resources.py` via `--scope-ack`, reserving STOP for genuinely unsafe conditions) and gate item 5 with conditional direct-vs-runner `aw ipd finalize 8co0wy` ownership (recommendation strength: very strong). |
| PR-005 | medium | UNDER-SCOPE | R4.E (Deterministic test mechanics and `tests/test_api.py` coverage) | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:73,78,114-118`; `tests/test_api.py:132-145`; `tests/test_explicit_api.py:121-152` | Testing `ResourceWatcher` CPU sampling with monkeypatched `time.perf_counter` on a live background thread risks thread races; profiler dump exclusion lacked a deterministic clock-advance mechanism; `Popen` launch failure was omitted from test cases; and `tests/test_api.py` (which asserts on `phase_end`) was omitted from E-05, Required tests, and V-05. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified unstarted-instance `ResourceWatcher._poll_cpu()`/`_poll_tree_cpu()` tests, deterministic `cProfile.Profile.dump_stats` clock-advance test, `Popen` launch-failure test, scoped `monkeypatch` fake-clock helpers, and added `tests/test_api.py` to E-05, Required tests, and V-05 (recommendation strength: strong). |
| PR-006 | low | IN-SCOPE | S5 (Open-question owner provenance and uncarried deferred obligations) | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:120-124,149`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91` | `OQ-01` recorded `- Owner: maintainer (confirmed upon plan approval)` on an author-resolved question, and the three deferred rows lacked structured `- Carrier: <id6>` lines (`check.ipd-uncarried-obligation`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Updated `OQ-01` `- Owner:` to `plan author (binding upon plan approval)`, logged reversible decision `D-1`, and added `- Carrier: e1fwy2`, `- Carrier: vrr1fv`, and `- Carrier: 3tvesf` to the deferred rows (recommendation strength: very strong). |
| PR-007 | low | IN-SCOPE | Check P (Technical writing, diagram parity, and `IPD-C802` hygiene) | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:5,30,36-46,56-73,83-94,122-129,154` | Acronyms (`CPU`, `UTC`, `I/O`, `POSIX`, `TUI`) were unexpanded on first use; E-01..E-04 Expected outcomes were dense run-on sentences; bare artifact IDs lacked descriptive labels; code citations lacked `path::Symbol` form; diagram nodes lagged the normative text; and line 154 carried two em dashes (`IPD-C802`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Expanded acronyms, split run-on sentences, added descriptive labels to referenced IDs, standardized `path::Symbol` citations, synchronized the Mermaid diagram, and replaced line 154 em dashes with parentheses (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Phase duration boundary when phase profiling is enabled (`OQ-01`) and owner provenance | Capture `self._start_mono` at the end of `phase.__enter__` (after profiler startup) and `end_mono` at the start of `phase.__exit__` (before profiler stop/dump), with `- Owner: plan author (binding upon plan approval)` | Prompt maintainer before review completion; include profiler startup/dump I/O inside `phase_end.payload.elapsed_seconds` | `.aw/records/plans/pending/20261121-timing-acc-02-8co0wy-monotonic-phase-subprocess-and-resource-timing.ipd.md:145-150`; `src/pubrun/core.py::phase:334-412`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | Keying scheme for `SubprocessSpy._start_monos` | Key by `id(rec)` storing `(rec, start_mono)` under `cls._lock`, cleared in both `install()` and `uninstall()` | Key by integer list index `idx` (vulnerable to cross-test stale index collision with `tests/test_capture.py::TestFinalizeAll` and concurrent `uninstall()`) | `src/pubrun/capture/subprocesses.py::SubprocessSpy:58-247`; `tests/test_capture.py::TestFinalizeAll:173-204` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Goal`, diagram, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
