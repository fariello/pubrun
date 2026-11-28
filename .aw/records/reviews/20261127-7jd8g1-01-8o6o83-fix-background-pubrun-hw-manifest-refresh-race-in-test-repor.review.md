# Review findings: ipd 8o6o83

- Subject-Id: 8o6o83
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-7jd8g1-01-8o6o83-fix-background-pubrun-hw-manifest-refresh-race-in-test-repor.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Verified the Mermaid flowchart matches all cited paths and symbols (`active_run`, `Run._bootstrap_engines`, `pubrun-hw`, `write_startup_manifest(is_refresh=True)`, `orig_manifest`). Replaced `N/A.` with `Not applicable.` in `## Spec / documentation sync`, hardened Command 1 with `PUBRUN_IMPORT_MODE=minimal PUBRUN_RUN_MODE_OVERRIDE="" PYTHONPATH=src` and the exact pytest node ID (`PR-001`), aligned `## Approval and execution gate` clause 2 with the 2026-09-01 scope-fence ruling (`PR-002`), and rephrased `V-01`/`V-02` to pin behaviors rather than collected counts or fixed test names (`PR-003`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Required tests / validation` Command 1 | Ran bare `python3 -c 'import threading, pytest, pubrun.writer ...'` with `-k` substring match and without `PYTHONPATH=src` or `PUBRUN_IMPORT_MODE=minimal` | Prefixed Command 1 with `PUBRUN_IMPORT_MODE=minimal PUBRUN_RUN_MODE_OVERRIDE="" PYTHONPATH=src` and targeted the exact pytest node ID | Prevent importing a different checkout, auto-starting a run in `cwd`, and spuriously tripping `spy_write` (`PR-001`) |
| `## Spec / documentation sync` | Started with `N/A.` | Replaced `N/A.` with `Not applicable.` | Expand abbreviation per technical writing standard Req 1 (`PR-003`) |
| `V-01`, `V-02` | Required collected count `1 passed` in `V-01` and exact test function names as pass bars in `V-02` | Rephrased both V-items to demand the pinned runtime behaviors and mechanisms with test function names as non-binding pointers subject to execution-time re-derivation | Satisfy re-derivation convention in `r2-executability.md:65` (`PR-003`) |
| `## Approval and execution gate` clause 2 | Instructed executor to "stop and report" on an out-of-scope edit | Rewrote clause 2 to direct justifying genuinely required scope deltas via `--scope-reason`/`--scope-ack` at finalization and reserving stop-and-report for genuinely unsafe conditions | Comply with 2026-09-01 scope-fence wording ruling in `s7-finalize.md:37-46` (`PR-002`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: 7jd8g1`, `- Order: 1`, `- Scope-Paths: tests/test_explicit_api.py`, 2 E-items in 2 task groups, no `.spec.md` file.

1. No: modifies a single test function in `tests/test_explicit_api.py` without changing any spec, CLI option, output format, configuration key, or production code contract.
2. No: touches only `tests/test_explicit_api.py` and does not touch code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 2 small E-items across 1 test file (`E-01` test update, `E-02` validation).
4. Yes: `- Scope-Paths:` explicitly lists `tests/test_explicit_api.py`.
5. No: test-only 3-line edit with zero production code impact and trivial reversibility.

AW-TIER: simple

### Step Q

- Checked: `.aw/records/backlog/graduated/20261127-7jd8g1-01-7jd8g1-fix-background-pubrun-hw-manifest-refresh-race-in.backlog.md`, `tests/test_explicit_api.py` (`active_run`, `test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively`, and every other `manifest.json` read in the file), `src/pubrun/tracker.py` (`Run._bootstrap_engines:834-991`, `Run._collect_hardware_section:752-775`), `src/pubrun/writer.py` (`ArtifactWriter.write_startup_manifest:433-488`), `src/pubrun/resources/default.toml` (`[capture.hardware]`, `[capture.resources]`), `tests/test_startup_overhead_writes.py::test_hardware_off_skips_thread_spawn_and_duplicate_startup_write:187-228`, `tests/test_runtime_safety.py`, `tests/test_signals.py`, `tests/test_package_lifecycle.py`, and all `manifest.json` writers across `src/pubrun/`.
- Verified:
  - What could this change break: nothing in production code or other tests. `active_run` is untouched (only the single call site passes `capture={"hardware": {"depth": "off"}}`), `test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` tests reserved-name rejection in `pubrun.report()` / `pubrun.artifact()` (orthogonal to hardware capture), and `src/pubrun/tracker.py:964` (`pubrun-hw`) is the sole asynchronous writer of `manifest.json` during an active run (`ResourceWatcher` never writes `manifest.json`). Every other `manifest.json` assertion in `tests/test_explicit_api.py` reads after `tracker.stop()`.
  - Actionable risks caught: (1) Command 1's bare `python3 -c 'import pubrun.writer ...'` lacked `PYTHONPATH=src` and `PUBRUN_IMPORT_MODE=minimal PUBRUN_RUN_MODE_OVERRIDE=""`, which could import an outside checkout, create untracked `runs/` in the repository root via `pubrun` auto-start, and spuriously trip `assert refreshes == []` from the auto-started run's own `pubrun-hw` thread (`PR-001`); (2) `## Approval and execution gate` clause 2 contained the prohibited "stop and report" scope-delta wording (`PR-002`); (3) `V-01`/`V-02` used a collected test count and fixed test names as pass bars instead of pinned behaviors with execution-time re-derivation, and `## Spec / documentation sync` used `N/A.` (`PR-003`).

### Step S5

- Checked: `## Open questions` contains `None.`. All three findings (`PR-001`, `PR-002`, `PR-003`) had `Low` overall Remediation Risk, were settled by repository code and documented workflow policy, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `q-quick-risk.md` / `r2-executability.md` (Validation probe isolation) | `.aw/records/plans/pending/20261127-7jd8g1-01-8o6o83-fix-background-pubrun-hw-manifest-refresh-race-in-test-repor.ipd.md:106-124` vs `src/pubrun/__init__.py:443-470`, `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress:307-335`, `src/pubrun/core.py::_execute_boot_sequence:982-1026`, `tests/conftest.py::_subprocess_pythonpath:19-39` | Validation Command 1 omitted `PYTHONPATH=src` and `PUBRUN_IMPORT_MODE=minimal PUBRUN_RUN_MODE_OVERRIDE=""`. Importing `pubrun.writer` outside `pytest.main()` can resolve another checkout via an editable `.pth` entry and triggers `pubrun` auto-start in `cwd`, creating untracked `runs/` artifacts and spawning a `pubrun-hw` thread whose in-flight `write_startup_manifest(is_refresh=True)` can race with `spy_write` and spuriously fail `assert refreshes == []`. In addition, `-k` substring selection can over-match future tests. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Prefixed Command 1 with `PUBRUN_IMPORT_MODE=minimal PUBRUN_RUN_MODE_OVERRIDE="" PYTHONPATH=src` and passed the exact pytest node ID `tests/test_explicit_api.py::test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` (recommendation strength: `very strong`). |
| PR-002 | MEDIUM | IN-SCOPE | `s7-finalize.md` (Scope-fence wording) | `.aw/records/plans/pending/20261127-7jd8g1-01-8o6o83-fix-background-pubrun-hw-manifest-refresh-race-in-test-repor.ipd.md:163` vs `.aw/system/workflows/plan-review/steps/s7-finalize.md:37-46` | `## Approval and execution gate` clause 2 instructed the executor to "stop and report" if execution appears to require touching an additional file, violating the 2026-09-01 maintainer scope-fence ruling in `s7-finalize.md:37-46`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote clause 2 to declare expected paths, direct justifying genuinely necessary deltas via `--scope-reason`/`--scope-ack` at finalization rather than stopping mid-run, and reserve stop-and-report for genuinely unsafe conditions (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `p-proofread.md` / `r2-executability.md` (Re-derivation and technical writing) | `.aw/records/plans/pending/20261127-7jd8g1-01-8o6o83-fix-background-pubrun-hw-manifest-refresh-race-in-test-repor.ipd.md:137,148,153` vs `.aw/system/workflows/plan-review/steps/r2-executability.md:65`, `.aw/system/workflows/technical-writing/technical-writing.md:29` | `V-01` used a collected test count (`1 passed`) as part of its pass bar and `V-02` treated exact test function names as pass bars instead of non-binding pointers over pinned behaviors with execution-time re-derivation (`r2-executability.md:65`), and `## Spec / documentation sync` used `N/A.`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rephrased `V-01` and `V-02` around pinned runtime behaviors and mechanisms with current test node names cited as non-binding pointers re-derived at execution time, and replaced `N/A.` with `Not applicable.` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `8o6o83` | `simple` | `standard` | Single-file test-only fix (2 E-items in `tests/test_explicit_api.py`) touching zero specs, public APIs, security/sandbox surfaces, or production code; tier questions 1, 2, 3, and 5 are all No (`steps/t-tier.md`). | yes |
| D-2 | Whether to also change `active_run` fixture defaults or other tests in `tests/test_explicit_api.py` | Keep the fix scoped to `test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` | Pass `hardware.depth="off"` inside `active_run` globally | `tests/test_explicit_api.py:453-464` uses shallow `opts.update(kwargs)` (overridden by callers passing `capture={"profiling": ...}`), and every other `manifest.json` read in `tests/test_explicit_api.py` occurs after `tracker.stop()`. Matches backlog `7jd8g1` exactly. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; every revision (`PR-001`, `PR-002`, `PR-003`) was swept across `## Required tests / validation`, `## Spec / documentation sync`, `V-01`, `V-02`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
