# Review findings: ipd kgoymu

- Subject-Id: kgoymu
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-08-kgoymu-global-test-isolation-assertion-hardening-and-sleep-or-pinni.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Added a Mermaid `flowchart LR` illustrating the fixture-isolation and 8-file hardening scope (Req 12), corrected the misnamed and missing module cache/latch citations in `E-01` and `## Findings` (`PR-001`), made session-scope fixture ordering explicit (`PR-002`), enumerated exact test targets and contracts across `E-02..E-04` (`PR-003`), replaced `N/A.` with `Not applicable.`, and completed the five-clause execution contract in `## Approval and execution gate` (`PR-004`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### Test isolation and hardening scope` | Plan had no Mermaid diagram despite modifying 8 related files and introducing a multi-stage fixture isolation flow | Added `flowchart LR` linking `_isolate_user_config`, `pubrun_state_isolation`, the 7 cache resets, `E-01..E-04`, and `E-05` | Satisfy technical writing standard Req 12(a)/(b) (`PR-004`) |
| `E-01` bullet 2, `## Project conventions discovered`, `## Findings` (`TEST-I4`), `V-01` | Cited non-existent `events._warned_invalid_durability`, `core._debug_enabled`, and `core._INACTIVE_POLICY_MEMO`, and omitted `packages._CACHED_INDEX` from `E-01` | Named all 7 verified modules, locks, and reset helpers (`signals._timed_out_locks`, `file_io._warned_invalid_algorithms` under `_warn_lock`, `writer._warned_invalid_durability` under `_durability_warn_lock`, `report.output.set_debug(None)`, `pubrun._reset_version_cache()`, `core._INACTIVE_POLICY_CACHE`/`_USER_CONFIG_PATH_MEMO`/`_LOCAL_CONFIG_PATHS_MEMO`, `packages.invalidate_package_cache()`) strictly via `sys.modules.get(...)` | Fix broken symbol citations and missing 7th reset (`PR-001`) |
| `E-01` bullets 1 & 3, `## Required tests / validation` Command 1 | Left `XDG_CONFIG_HOME`/`APPDATA` fixture scope unspecified, omitted `sys.platform == "win32"` / `caplog` details for `test_config.py`, and used bare `pytest` without `test_config_capture_modes.py` | Specified **session-scoped** `autouse=True` `_isolate_user_config(tmp_path_factory)` running before function-scoped `pubrun_state_isolation`, specified Windows `APPDATA` monkeypatch and malformed-TOML `caplog` assertion in `test_config.py`, and switched Command 1 to `python3 -m pytest` including `tests/test_config_capture_modes.py` | Prevent fixture-teardown env clobbering and verify `TestGlobalConfigDir` compatibility (`PR-002`) |
| `E-02`, `E-03`, `E-04` | Left `unflatten_manifest` collision shape, the `TEST-I10` assertion-free test list, and the `threading.Event` replacement mechanism for `tests/test_signals.py` lines 715/727 vague | Named the exact expected dict `{"a": {"b": 1}, "a.b.c": 2}`, listed all concrete `TEST-I10` tests and post-conditions across `test_api.py`, `test_signals.py`, `test_capture.py`, and `test_events.py`, and specified wrapping `write_startup_manifest`/`_check_section_failed` with `entering = threading.Event()` | Ensure modest executor can implement cleanly without guessing (`PR-003`) |
| `## Spec / documentation sync`, `V-01..V-05`, `## Approval and execution gate` | Used `N/A.`; omitted code-path reachability in `V-01`/`V-05` and execution-contract details (`--scope-reason`/`--scope-ack`, no `git add -A`/raw `git commit`, conditional runner vs manual `aw ipd finalize`) | Replaced `N/A.` with `Not applicable.`; named code paths and execution-time re-derivation in `V-01..V-05`; completed the 5-clause execution contract | Satisfy `technical-writing.md` Req 1, `r2-executability.md`, and `s7-finalize.md:31-46` (`PR-004`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 8`, `- Scope-Paths:` (`tests/conftest.py, tests/test_config.py, tests/test_api.py, tests/test_edge_cases.py, tests/test_import_modes.py, tests/test_signals.py, tests/test_capture.py, tests/test_events.py`), 5 E-items in 3 task groups, no `.spec.md` file.

1. Yes: modifies global autouse fixtures in `tests/conftest.py` that govern environment isolation and module-state resets for the entire test suite and every sibling child in Set `assess-bt`.
2. No: touches only test files under `tests/`, not production security/commit/sandbox code.
3. Yes: spans 8 test files across 3 task groups in the 10-child Set `assess-bt`.
4. Yes: `- Scope-Paths:` explicitly lists all 8 files.
5. Yes: an incorrect fixture scope ordering or eager lazy-module import in `tests/conftest.py` would break lazy-import and config-dir tests across the entire suite.

AW-TIER: complex

### Step R1

- Checked: every file, symbol, cache/latch, and test cited in `kgoymu` against the repository: `tests/conftest.py` (`_subprocess_pythonpath`, `isolated_cwd`, `clean_active_run`, `pubrun_state_isolation`), `src/pubrun/config.py` (`get_global_config_dir`, `load_user_config`, `_safe_load_toml`), `src/pubrun/_config_boot.py` (`_global_config_dir`), `src/pubrun/capture/signals.py` (`_timed_out_locks`, `_finalizing_active_run`, `finalization_lock`), `src/pubrun/capture/file_io.py` (`_warn_lock`, `_warned_invalid_algorithms`), `src/pubrun/writer.py` (`_durability_warn_lock`, `_warned_invalid_durability`), `src/pubrun/report/output.py` (`_debug_enabled`, `set_debug`), `src/pubrun/__init__.py` (`_cached_version`, `_reset_version_cache`), `src/pubrun/core.py` (`_INACTIVE_POLICY_CACHE`, `_USER_CONFIG_PATH_MEMO`, `_LOCAL_CONFIG_PATHS_MEMO`, `phase.__exit__`), `src/pubrun/capture/packages.py` (`_CACHED_INDEX`, `invalidate_package_cache`), `src/pubrun/analysis/diff.py` (`unflatten_manifest`), `tests/test_config.py`, `tests/test_config_capture_modes.py` (`TestGlobalConfigDir`), `tests/test_api.py`, `tests/test_edge_cases.py`, `tests/test_import_modes.py`, `tests/test_signals.py`, `tests/test_capture.py`, and `tests/test_events.py`.
- Verified: uncovered 4 concrete citation/completeness errors in `E-01` (`events._warned_invalid_durability` -> `writer._warned_invalid_durability`; `core._debug_enabled` -> `report.output._debug_enabled`; `core._INACTIVE_POLICY_MEMO` -> `_USER_CONFIG_PATH_MEMO` / `_LOCAL_CONFIG_PATHS_MEMO`; omitted `packages._CACHED_INDEX` / `invalidate_package_cache()`) and fixed all four in `PR-001`. Verified all remaining test names, line anchors, and behaviors match the current checkout.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability for `V-01`/`V-05` (Command 2), re-derivation convention (`r2-executability.md:65`), and the 5-clause execution contract in `## Approval and execution gate`.
- Verified: `PR-001`, `PR-002`, `PR-003`, and `PR-004` closed every executability, fixture-ordering, specification, and execution-contract gap.

### Step R3

- Checked: full security and privacy rubric (`r3-security.md` B).
- Verified: test-only edits; Command 2 creates a temporary directory via `tempfile.TemporaryDirectory()` (auto-cleaned) and never modifies the host user's real `~/.config/pubrun/config.toml`; session-scoped `XDG_CONFIG_HOME`/`APPDATA` isolation in `tests/conftest.py` prevents tests from reading real developer configuration or secrets from `~/.config/pubrun/config.toml`.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - A/C/D: resetting all 7 module caches strictly via `sys.modules.get(...)` preserves lazy-import isolation; session-scoped `_isolate_user_config` runs before function-scoped `pubrun_state_isolation` so `_env_snapshot` captures the isolated dir while keeping `tests/test_config_capture_modes.py::TestGlobalConfigDir` (`isolated_home`) green; `unflatten_manifest` exact collision assertion and `entering = threading.Event()` entry wrapper in `test_signals.py` test real behavioral contracts with zero code-pinning (`GUIDING_PRINCIPLES P16`).
  - E: Command 1 (`python3 -m pytest -p randomly` across all 8 suites including `tests/test_config_capture_modes.py`) and Command 2 (hostile `XDG_CONFIG_HOME`/`APPDATA` subprocess) validate every modified invariant.
  - Right-sizing: 5 E-items in 3 task groups across 8 Scope-Paths; each E-item is concise and focused.
  - `## Spec / documentation sync`: substantiated (test-only changes).

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught all 3 misnamed caches and missing 7th reset (`PR-001`) and enumerated all concrete `TEST-I10` assertion-free tests (`PR-003`).
  2. Testing and regression: caught `conftest.py` fixture scope/ordering trap and added `tests/test_config_capture_modes.py` to Command 1 (`PR-002`); specified deterministic `entering = threading.Event()` handshake for `test_signals.py` (`PR-003`).
  3. UI / UX: verified `report.output.set_debug(None)` reset prevents debug-logging state bleed across tests.
  4. Architect: verified zero eager imports in `conftest.py` resets (`sys.modules.get(...)`) and clean disjoint Scope-Paths across Set `assess-bt`.
  5. Software engineer: verified lock discipline (`_warn_lock`, `_durability_warn_lock`), Windows `APPDATA` platform monkeypatching in `test_config.py`, and exact `unflatten_manifest` return shape.
  6. Power user: verified developer `~/.config/pubrun/config.toml` settings (`profile = "deep"`, `on_inactive_annotate = "error"`) can no longer break local test runs.
  7. Novice: added Mermaid overview diagram and explicit concrete targets in `E-01..E-04` so any contributor can follow the isolation design on first read.
  8. Stakeholder: confirmed full coverage of `TEST-C7`, `TEST-I4`, `TEST-C8`, `TEST-C9` (`test_signals.py`), `TEST-I7` (`test_signals.py`), and `TEST-I10` assigned by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, 8 Scope-Paths, already Order 08 of 10-child Set `assess-bt`).
- Confirmed: each E-item targets a small, cohesive set of test-only edits (conftest + config, vacuous assertions, signals cleanup, capture/events post-conditions, validation). Splitting further would add Set overhead without reducing execution risk; no split is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt` (orchestrator `n6250e` and sibling children `wcjdbu`, `ndobra`, `thbepl`, `qum7gf`, `kk83rk`, `n39jh9`, `dqaj9a`, `4eo4z2`, `37sth0`) plus external pending plans `3u1xgk` and `8o6o83`.
- Verified: all 10 children in Set `assess-bt` have strictly disjoint `Scope-Paths`; neither `wcjdbu` nor `thbepl` renames any of the 7 module caches reset by `kgoymu`; `kgoymu` deliverables and `Item-Dependencies: none` align with `n6250e` E-08 and `## Child IPDs, sequence, and dependencies`. Outside Set `assess-bt`, pending plan `3u1xgk` touches a disjoint class in `tests/test_import_modes.py` (`TestModePep561AndColdStart`, lines 1488+) while `kgoymu` edits only `TestImportMetadataInManifest` (lines 483, 499), safely serialized by isolated worktrees and the merge-and-revalidate gate.

### Step S5

- Checked: `## Open questions` contains `None.`. All four findings (`PR-001` through `PR-004`) had `Low` overall Remediation Risk, were settled by repository code and documented workflow policy, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` A | `.aw/records/plans/pending/20261127-assess-bt-08-kgoymu-global-test-isolation-assertion-hardening-and-sleep-or-pinni.ipd.md:38,86` vs `src/pubrun/writer.py::_warned_invalid_durability:22`, `src/pubrun/report/output.py::_debug_enabled:50`, `src/pubrun/core.py:79-81`, `src/pubrun/capture/packages.py::invalidate_package_cache:745`, `src/pubrun/__init__.py::_reset_version_cache:240` | `E-01` cited three non-existent module/symbol locations (`events._warned_invalid_durability`, `core._debug_enabled`, `core._INACTIVE_POLICY_MEMO`) and omitted the 7th cache (`packages._CACHED_INDEX`) listed in `## Findings` `TEST-I4`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `E-01` bullet 2, `## Project conventions discovered`, `## Findings` `TEST-I4`, and `V-01` with the exact verified module paths, locks, and reset helpers for all 7 caches/latches accessed via `sys.modules.get(...)` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A, D | `.aw/records/plans/pending/20261127-assess-bt-08-kgoymu-global-test-isolation-assertion-hardening-and-sleep-or-pinni.ipd.md:37,39,113` vs `tests/conftest.py::pubrun_state_isolation:82-174`, `tests/test_config_capture_modes.py::TestGlobalConfigDir:61-84`, `src/pubrun/config.py::get_global_config_dir:62-77` | `E-01` left fixture scope/ordering for `XDG_CONFIG_HOME`/`APPDATA` isolation unspecified (a function-scoped fixture running after `pubrun_state_isolation` would be reverted by `_env_snapshot`), omitted Windows `sys.platform` monkeypatching and `caplog` warning checks for `tests/test_config.py`, and omitted `tests/test_config_capture_modes.py` from Command 1. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified a **session-scoped** `autouse=True` fixture `_isolate_user_config(tmp_path_factory)` running before `pubrun_state_isolation`, specified Windows `APPDATA` monkeypatch and malformed-TOML `caplog` assertions in `tests/test_config.py`, and added `tests/test_config_capture_modes.py` to Command 1 (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` E | `.aw/records/plans/pending/20261127-assess-bt-08-kgoymu-global-test-isolation-assertion-hardening-and-sleep-or-pinni.ipd.md:47-65` vs `src/pubrun/analysis/diff.py::unflatten_manifest:319-354`, `tests/test_api.py:44-48,89-93,148-152`, `tests/test_signals.py:24-37,389-396,704-728`, `tests/test_capture.py:404-421`, `tests/test_events.py:118-130,175-192` | `E-02` omitted the exact `unflatten_manifest` collision output, `E-02`/`E-03`/`E-04` left the concrete `TEST-I10` assertion-free tests and post-conditions unnamed, and `E-03` did not explain how to replace `time.sleep(0.05)` at lines 715/727 with `threading.Event` when `_bg()` blocks on `lock`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the exact `unflatten_manifest` collision structure `{"a": {"b": 1}, "a.b.c": 2}`, listed all concrete `TEST-I10` tests and observable post-conditions across the 4 test files, and specified the `entering = threading.Event()` entry-wrapper handshake for `write_startup_manifest` and `_check_section_failed` (recommendation strength: `strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `p-proofread.md` / `r2-executability.md` / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-bt-08-kgoymu-global-test-isolation-assertion-hardening-and-sleep-or-pinni.ipd.md:26-29,113,131,141-175` vs `.aw/system/workflows/technical-writing/technical-writing.md:29,40-46`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:65` | Plan lacked a Mermaid diagram for its 8-file multi-stage fixture isolation scope (Req 12), used `N/A.` and bare `pytest`, lacked explicit code-path reachability in `V-01`/`V-05`, and omitted required execution-contract clauses in `## Approval and execution gate` (`--scope-reason`/`--scope-ack`, no `git add -A`/raw `git commit`, conditional runner vs manual `aw ipd finalize`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added a Mermaid `flowchart LR`, replaced `N/A.` with `Not applicable.`, switched Command 1 to `python3 -m pytest`, added reachability/re-derivation wording to `V-01..V-05`, and expanded `## Approval and execution gate` to the complete 5-clause contract (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `kgoymu` | `complex` | `standard` | Modifies global autouse fixtures in `tests/conftest.py` affecting the whole suite and all sibling plans in 10-child Set `assess-bt` across 8 Scope-Paths; answers Yes to tier questions 1, 3, and 5 (`steps/t-tier.md`). | yes |
| D-2 | Fixture scope for host `XDG_CONFIG_HOME` / `APPDATA` isolation in `tests/conftest.py` | Session-scoped `autouse=True` fixture (`_isolate_user_config(tmp_path_factory)`) restoring prior values on session teardown | Function-scoped fixture or setting inside `pubrun_state_isolation` | `tests/conftest.py::pubrun_state_isolation:107,168-174` snapshots `os.environ` per test and restores it on teardown; session scope ensures `_env_snapshot` captures the clean empty directory while keeping per-test `monkeypatch.setenv`/`delenv` overrides (e.g. `tests/test_config_capture_modes.py::isolated_home`) intact. | yes |
| D-3 | How to replace `time.sleep(0.05)` in `tests/test_signals.py` lines 715 and 727 without a race | Wrap `run.writer.write_startup_manifest` / `run._check_section_failed` to set an `entering = threading.Event()` right before delegating, and `assert entering.wait(5)` after `assert ready.wait(5)` | Remove `time.sleep(0.05)` without a second event, or poll lock state | `tests/test_signals.py:704-728` holds `lock` on the main thread while `_bg()` holds `_run_lock` and then enters `write_startup_manifest` / `_check_section_failed`; an entry event deterministically proves `_bg()` reached the blocking call without any sleep. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; every revision (`PR-001` through `PR-004`) was swept across `## Goal`, the Mermaid diagram, `E-01..E-05`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
