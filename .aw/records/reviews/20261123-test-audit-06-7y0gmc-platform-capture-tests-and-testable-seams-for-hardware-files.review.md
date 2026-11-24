# Review findings: ipd 7y0gmc

- Subject-Id: 7y0gmc
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-06-7y0gmc-platform-capture-tests-and-testable-seams-for-hardware-files.ipd.md` (front matter, Goal, diagram, E-01 to E-05, conventions, findings, proposed changes, deferrals, scope check, required tests, documentation sync, open questions, V-01 to V-05, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Proofreading kept front-matter keys, the H2 heading list and order, E/V ids, checkbox states, Execution state values, and item field names. Substantive rewrites of E-items, V-items, the diagram, and the gate are recorded under Findings, not here.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence naming "testable seams" and five modules with no definitions | Says what each module captures, defines "testable seam" and "backward compatible", and lists the three seams | Define terms at first use; a reader new to the repository cannot act on undefined names. |
| Goal | Diagram labels with no counterpart in the text (`PLATFORM_HELPER`, `PROC_STAT_IO_PARSER`) | Diagram entities named after the real functions and test files, with a legend sentence | Requirement 12(e): a diagram uses the same terms as the text. |
| Project conventions | "13 `pytest.skip` calls" | 14 calls, 13 on `None` results and 1 legitimate non-Linux skip | The bare count did not match `grep -c` and did not say which skips stay. |
| Project conventions | Three bullets | Adds the `_PLATFORM` import constraint, existing coverage in `tests/test_capture_engine_bugs.py`, the CI matrix and Python 3.8 syntax floor, and the `AGENTS.md` matrix rule | The executor needs these facts to write tests that pass on every CI job. |
| Short-Description, Concern, Scope | Named `liveness.py` as a seam target | Names the seams actually added | The review dropped the `liveness.py` seam (PR-003). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (7 entries before review, 6 after), E-01 to E-05, and the production code each item touches (`src/pubrun/capture/liveness.py`, `filesystem.py`, `system_metrics.py`, `resources.py`, `hardware.py`) and its callers (`src/pubrun/tracker.py` `set_poll_timeout`, `src/pubrun/report/checks.py` `get_system_memory`).

1. Partly: the plan edits `src/` functions, but every change adds a defaulted parameter to a private or internal helper. No public API, manifest field, or schema changes.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. No: 5 E-items in 3 task groups; E-01 is a small set of mechanical signature changes.
4. Yes: 6 files after review, matching the E-items.
5. Low: every seam keeps its old default, and the mutation checks in the V-items catch a wrong default or a broken branch.

AW-TIER: standard

### Step R1

- Checked: every cited path and symbol against lane HEAD `75bba55`. `liveness._PLATFORM = sys.platform` is read at call time by `is_pid_alive`, `get_process_start_time`, `is_same_process`, `get_rss_bytes`, and `get_cpu_percent`. `tests/test_liveness.py` imports `_PLATFORM` in four tests. The liveness reader names are `get_rss_bytes` and `get_cpu_percent`. `filesystem._parse_proc_mounts`, `_parse_proc_mountinfo`, `_mac_mount_table(timeout=2.0)`, `_classify_windows_path`, `_classify_windows(paths)`, `LiveProbe.__init__(self, path, wait_budget_s)`, `_live_probe_sem`, and `_statvfs_metrics` exist. `system_metrics.get_system_memory`, `read_proc_stat_cpu_times`, and `get_proc_io` take no argument and hardcode their `/proc` path. `resources._poll_timeout`, `set_poll_timeout`, `_get_rss_windows` (ctypes first, then `wmic`), `_get_rss_darwin`, and `ResourceWatcher._sample_system_metrics` exist. `hardware._get_gpus(config_hw, timeout, *, budget=None)`, `_get_cpu_model`, `_get_total_memory_bytes`, and `get_hardware` exist.
- Baseline before any edit: `tests/test_hardware.py`, `tests/test_liveness.py`, `tests/test_env_capture.py`, `tests/test_resources.py`, and `tests/test_capture_engine_bugs.py` gave `118 passed in 3.12s`, 0 skipped, on Linux with Python 3.14.6. Full suite with coverage: `1882 passed, 2 skipped in 436.45s`, with the plan's five coverage figures confirmed.
- PR-005: E-03 named `get_process_rss_bytes` and `get_process_cpu_seconds`, which do not exist; the readers are `get_rss_bytes` and `get_cpu_percent`.
- PR-010: E-04 placed the `DRIVE_REMOTE` and `GetVolumePathNameW` logic in `_classify_windows`; it lives in `_classify_windows_path`, and `_classify_windows` only loops over paths and isolates failures.
- PR-003: E-01 asked to make `liveness.py` dispatch on `sys.platform` dynamically. Dispatch already reads the module attribute `_PLATFORM` at call time, so `monkeypatch.setattr(liveness, "_PLATFORM", ...)` already reaches every branch. The refactor would add risk to the four tests that import `_PLATFORM` and buy nothing.
- PR-004: E-01 asked for a per-instance `poll_timeout` on `ResourceWatcher`. The readers use the module global `_poll_timeout`, which a test can patch and which `tracker.py` sets once through `set_poll_timeout`.

### Step R2

- Checked: author-phase lint (`aw ipd lint --phase author --agent`: `clean`, exit 0, 1 `IPD-Z602` advisory), the E/V bijection, each V-item against what its E-item produces, and each E-item by prototype. The prototype ran in a scratch copy of the lane at `75bba55` under `/tmp/opencode`, never in the lane. It applied the E-01 seams, the E-03(a) and E-03(b) edits to `tests/test_liveness.py`, and 31 prototype test functions (32 cases with parametrization) covering E-02 to E-05. Each strengthened test was checked against a temporary one-line break of the production code it guards.
- Prototype results: the prototype tests and the five capture test files gave `145 passed`; with `tests/test_new_features.py` and `tests/test_capture_isolation.py` added, `170 passed`. The full suite in random order on a complete scratch copy with every prototype change, `python3 -m pytest tests/ -q --no-cov -p randomly --randomly-seed=4242`, gave `1914 passed, 2 skipped in 526.35s (0:08:46)`, against `1882 passed, 2 skipped` before. The injected-semaphore tests passed 20 of 20 repeated runs.
- PR-001: every V-item asked only for passing output. The current tests already pass, and a passing run cannot show that a test would catch a regression. In the prototype, each mutation now named in V-02 to V-05 failed at least one test, including the `nvidia-smi` MiB conversion, the clock-field guard, `PermissionError` alive semantics, the `rfind(")")` parse, `EPOCH_DIFF`, `STILL_ACTIVE`, the `0xFFFFFFFF` guard, the macOS mount-point split, `DRIVE_REMOTE`, the probe cap and release, `fields[4]`, the `io_counters` delta, the load maximum, the iowait last value, the `wmic` fallback, and the `set_poll_timeout` fallback. The first mutation pass reported false survivors: a same-size edit made within the same second as the previous one reused the cached `.pyc`. The rule now requires deleting `__pycache__` and setting `PYTHONDONTWRITEBYTECODE=1`.
- PR-006: E-03(a) said "fail hard on Linux" without a mechanism and without saying which skip stays. The prototype helper `_unsupported(what)` fails on Linux and skips elsewhere. With `_get_start_time_linux` returning `None`, the current file gave `19 passed, 8 skipped` and the revised file gave `8 failed, 19 passed`. With `_get_rss_linux`, `_get_cpu_linux`, or `_check_command_linux` returning `None`, the revised file gave 1, 1, and 3 failures. The skip in `test_generic_script_token_is_inconclusive` stays because it guards a Linux-only helper.
- PR-009: E-02, E-03(c), and E-05(b) did not say how to fake the platform. The review machine has `nvidia-smi`, so an unmocked GPU test would depend on the host. `ctypes.windll` does not exist off Windows, so it must be patched with `raising=False`. The Windows fakes must write results through the `ctypes.byref` argument's `_obj`. `_get_rss_windows` assigns `argtypes` and `restype` to the functions, which fails on a bound method. `os.sysconf` does not exist on Windows. In `_check_command_windows`, a Windows backslash path is not split by `PurePath` on Linux, so `_match_script_in_tokens("train.py", ["python", "C:\\x\\train.py"])` returned `None`. The E-items now state each of these.
- PR-011: no item would catch a mistyped default path. At review, changing the `read_proc_stat_cpu_times` default to `"/nonexistent"` left all 141 tests in the existing capture test files passing. E-04(e) adds a default-path test; in the prototype it failed for each of the four default paths mutated.
- PR-012: E-05 gave no sample data. A first prototype with distinct memory values passed when the `min_available` condition was replaced with `True`, so it could not tell keep-first from keep-last. The revised data includes a tie and a falling final load and iowait value. It failed under that mutation, under `<` changed to `<=`, and under an iowait "last" that never updates. With those data the redundant outer condition (`avail < prev + 1`) can be removed and the tests still pass, so E-01(d) removes it.
- PR-007: E-03(b) duplicated `TestLivenessHardening.test_nonpositive_and_none_pids_are_not_alive`. It was kept, because it turns a no-op `pass` into a real assertion at no cost, and the reason it is safe on every platform (the `pid <= 0` check before dispatch) is now stated.

### Step R3

- Checked: the new tests patch module attributes with `monkeypatch`, which restores them, write only inside `tmp_path`, and run no real subprocess. The mutation checks edit production files only temporarily, and the gate forbids committing a change to `liveness.py` or `hardware.py`. No security finding.

### Step R4

- Checked: the `AGENTS.md` "no code-pinning tests" rule (no new test reads production source), right-sizing, sibling scopes, and the Set orchestrator `vdxiw8`. No other `test-audit` plan declares these files in `- Scope-Paths:`. `m66tfv` owns `tests/test_env_capture.py` and `tests/test_resources.py`, which this plan runs but does not edit, and `2mwjjw` owns invocation and redaction tests. The orchestrator's row 06 still says `liveness.py` gets seams; that is recorded as a `Carrier: vdxiw8` deferral.
- PR-002: the gate told the executor to "move this plan to `.aw/records/plans/executed/`" by hand, and lacked the scope declaration, the validation-honesty rule, and the runner and executor split for finalization. It now carries the five-element execution contract with `aw commit 7y0gmc` and `aw ipd finalize 7y0gmc`.
- PR-015: E-03 depended on E-01, but after PR-003 it needs no seam, so it is now independent. E-02 was already independent. The plan lacked the CI matrix and Python 3.8 syntax note and a deferral for the push-gated matrix run.
- PR-013: the diagram named entities that do not appear in the text and showed a `liveness.py` seam the plan no longer adds.
- PR-014: the documentation-sync N/A gave no evidence, and the required-tests list had no skip summary, random-order run, or full suite. At review, `grep` over `docs/`, `README.md`, `CHANGELOG.md`, and `.aw/records/specs/` found no mention of the changed functions.
- PR-008: the plan said "13 `pytest.skip` calls"; `grep -c` gives 14, of which 13 fire on `None` results.

### Step S5

- Checked: open questions (none), deferrals (one `Carrier: vdxiw8` for the orchestrator description, which exists in `pending/`; two `Carrier-Declined` entries added at review, for the push-gated CI matrix run and the per-instance `poll_timeout`). Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so the lane outcome carries no question.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R2 (evidence cannot prove the change) | Baseline `118 passed`; prototype mutations; stale `.pyc` false survivors | V-items asked only for passing output, which the current tests already produce. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-02 to V-05 name one-line mutations that must fail, with a bytecode-safe procedure and restore step; V-03 adds a skip count. |
| PR-002 | medium | IN-SCOPE | S7 (execution contract) | Gate text "move this plan to `.aw/records/plans/executed/`" | The gate told the executor to move the plan by hand and lacked three contract elements. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Replaced with the five-element contract and `aw ipd finalize 7y0gmc`. |
| PR-003 | medium | IN-SCOPE | R1 (unneeded production change) | `liveness._PLATFORM` read at call time; 4 test imports of `_PLATFORM` | E-01 asked for a `liveness.py` dispatch refactor that tests do not need and that risks existing imports. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | `liveness.py` removed from E-01 and `- Scope-Paths:`; tests patch `_PLATFORM`, `os.kill`, `open`, and `ctypes.windll`. |
| PR-004 | low | IN-SCOPE | R1 (redundant seam) | `resources._poll_timeout`, `set_poll_timeout`, `tracker.py` caller | E-01 asked for a per-instance `poll_timeout` duplicating a patchable global. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Dropped; `Carrier-Declined` deferral records why. |
| PR-005 | medium | IN-SCOPE | R1 (citation) | `liveness.get_rss_bytes`, `liveness.get_cpu_percent` | E-03 named two functions that do not exist. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03 uses the real names. |
| PR-006 | medium | IN-SCOPE | R2 (unspecified technique) | Prototype: `19 passed, 8 skipped` before, `8 failed, 19 passed` after | E-03(a) gave no fail-on-Linux mechanism and did not say which skip stays. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03(a) specifies `_unsupported(what)`, the 13 call sites, and the one retained skip. |
| PR-007 | low | IN-SCOPE | R2 (duplicate coverage) | `TestLivenessHardening.test_nonpositive_and_none_pids_are_not_alive` | E-03(b) duplicates an existing assertion without saying so or why it is safe. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Kept, with the `pid <= 0` reason stated. |
| PR-008 | low | IN-SCOPE | P (stale count) | `grep -c pytest.skip tests/test_liveness.py` gives 14 | The plan's "13" did not match and did not separate the legitimate skip. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Conventions state 14 = 13 on `None` + 1 Linux-only. |
| PR-009 | medium | IN-SCOPE | R2 (unspecified, platform-specific) | `/usr/bin/nvidia-smi` on review host; `hasattr(ctypes, "windll")` is `False` on Linux; bound-method `argtypes` | Platform-fake mechanics were unstated, so tests could depend on the host or fail off Windows. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02, E-03(c), E-04(b), and E-05(b) state the patch targets, `raising=False`, `byref._obj`, and callable-object fakes. |
| PR-010 | low | IN-SCOPE | R1 (citation) | `filesystem._classify_windows_path` holds `DRIVE_REMOTE` logic | E-04 attributed the classifier logic to `_classify_windows`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04(b) tests `_classify_windows_path` and `_classify_windows` separately. |
| PR-011 | medium | IN-SCOPE | R2 (missing test) | Default `/proc/stat` mutated to `/nonexistent`: `141 passed` | A mistyped default path in a new seam would pass every test. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04(e) adds a default-path test; V-04 mutates each default. |
| PR-012 | medium | IN-SCOPE | R2 (weak test data) | `min_available` condition replaced with `True`: prototype passed | E-05 gave no data, and plain distinct values cannot tell keep-first from keep-last. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05(a) fixes the samples, including a tie, and the exact expected aggregates; E-01(d) removes the redundant condition. |
| PR-013 | low | IN-SCOPE | P (diagram) | Diagram labels `PLATFORM_HELPER`, `PROC_STAT_IO_PARSER`, `RESOURCE_WATCHER` per-instance timeout | Diagram used terms absent from the text and showed seams the plan no longer adds. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Diagram redrawn with real function and file names and a legend. |
| PR-014 | low | IN-SCOPE | R4 (doc sync, validation list) | `grep` over `docs/`, `README.md`, `CHANGELOG.md`, `.aw/records/specs/` | The N/A had no evidence, and the required tests had no skip summary or full suite. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | N/A cites the search; required tests add `-rs`, a random-order full suite, and the mutation checks. |
| PR-015 | low | IN-SCOPE | R4 (dependencies, matrix) | `.github/workflows/ci.yml` matrix; `requires-python = ">=3.8"` | E-03 depended on E-01 needlessly, and the plan lacked the matrix note and its deferral. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03 depends on none; conventions add the matrix and Python 3.8 syntax notes; a `Carrier-Declined` deferral covers the push-gated run. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Five E-items; `src/` changes are defaulted parameters on private or internal helpers; no public contract | yes |
| D-2 | Refactor `liveness.py` platform dispatch? | No; patch `_PLATFORM` | Read `sys.platform` dynamically | `_PLATFORM` is read at call time; four tests import it | yes |
| D-3 | Keep the `LiveProbe` `semaphore` parameter, given that the global can be patched? | Keep | Patch `filesystem._live_probe_sem` | The parameter ties release to the semaphore acquired, and tests never touch the process-wide cap | yes |
| D-4 | Test `/proc` readers by patching `builtins.open` or by a `path` parameter? | `path` parameter | Patch `builtins.open` | A real file in `tmp_path` exercises `os.path.exists` and `open` without a global patch | yes |
| D-5 | Add a per-instance `poll_timeout` to `ResourceWatcher`? | No | Add it | The global is patchable and set once per run; a second source adds drift | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. The E/V id set is unchanged (E-01 to E-05, V-01 to V-05, `Highest E allocated: 05`). `- Item-Dependencies:` is unchanged (`none`). `- Scope-Paths:` lost `src/pubrun/capture/liveness.py` (PR-003). A re-review pass is required.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: re-read the revised plan in full against lane HEAD `75bba55`. Every symbol cited in the rewritten items resolves, including `LiveProbe._thread`, `_get_start_time_windows`'s `EPOCH_DIFF`, `_is_pid_alive_windows`'s `0xFFFFFFFF` guard, `_check_command_windows`'s `lines[1]`, `_get_total_memory_bytes`'s `int(lines[1]) * 1024`, `get_hardware`'s `except Exception as e:`, and the `io_counters` delta in `ResourceWatcher.to_manifest_dict`. Every expected value in E-02 to E-05 matches a prototype assertion that passed. The read-error case in E-04(d) was confirmed: passing a directory as `path` returns `None` from `read_proc_stat_cpu_times` and `get_proc_io`.

### Step R2

- Checked: `aw ipd lint --phase review-finalize --agent`: `clean`, exit 0, 0 findings. E-01 to E-05 map 1:1 to V-01 to V-05. Dependencies are acyclic: E-04 and E-05 need E-01; E-01 to E-03 need none. `- Scope-Paths:` matches the Scope line, the gate's scope declaration, and the files the E-items edit. `grep -c pytest.skip` on the prototype `tests/test_liveness.py` gave 2, the value V-03 expects.

### Step R4

- Checked: no revised item asks a test to read production source. The removal of `liveness.py` from `- Scope-Paths:` touches no sibling plan's scope. The gate now forbids committing a `liveness.py` or `hardware.py` change, which matches the mutation-only use of those files.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 made no edits, so the E/V id set, `- Scope-Paths:`, and `- Item-Dependencies:` are unchanged since Round 1's S6. No new finding. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
