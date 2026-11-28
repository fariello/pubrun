# Review findings: ipd dqaj9a

- Subject-Id: dqaj9a
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-07-dqaj9a-capture-resource-hardware-reproducibility-and-snapshot-test.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`). Expanded acronyms (`IPD`, `CPU`, `JSON`, `MB`, `ROCm`, `VRAM`, `NaN`, `Inf`, `QA`, `RSS`, `AMD`, `HPC`) on first use, standardized full repo-relative `path::Symbol` citations, verified no decorative Mermaid diagram is warranted for a test-only plan (requirement 12), and tightened all five execution-gate clauses (`PR-005`, `PR-006`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Concern`, `Goal`, `E-01`..`E-04`, `## Project conventions discovered`, `## Findings`, `V-01`..`V-04` | Left `IPD`, `CPU`, `JSON`, `MB`, `ROCm`, `VRAM`, `NaN`, `Inf`, `QA`, `RSS`, `AMD`, and `HPC` unexpanded and used short module names (`hardware.py`, `meta_snapshot.py`, `reproducibility.py`, `checks.py`, `methods.py`) | Expanded acronyms on first use and standardized full repo-relative `path::Symbol` citations | Satisfy technical writing standard requirement 7 and spec Section 11.1 (`PR-006`) |
| `E-03`, `## Project conventions discovered`, `V-03` | Demanded `meta_snapshot.py` lines `46-54` without a tuple-cycle case (leaving line `49` unreachable) and demanded corrupt JSON line coverage in `_has_recorded_seed_annotation` without noting the `b'"annotation"'` pre-filter at line `1194` | Added a tuple-via-list cycle test (`lst = []; tup = (lst,); lst.append(tup)`) covering `meta_snapshot.py:49` and specified a corrupt JSON line containing literal `"annotation"` covering `reproducibility.py:1198-1199` | Prevent unreachable coverage targets in `V-03` (`PR-001`) |
| `E-01`, `V-01` | Did not specify that testing `stop()` skipping final measurement after abort requires an actually started watcher (`self.ident is not None`) | Specified starting the watcher, waiting for `_stop_event.is_set()`, resetting the `_poll_rss` counter, and asserting `stop()` does not re-poll and `end_rss_bytes is None` | Prevent a vacuous unstarted-watcher test where `was_started=False` masks the `not aborted` branch (`PR-002`) |
| `E-02` | Did not specify mocking `subprocess.check_output` during `get_hardware` timeout tests, left direct `_parse_amd_smi_json`/`_parse_rocm_smi_json` malformed-JSON behavior (`json.JSONDecodeError` vs `_get_gpus` degradation) ambiguous, and omitted `sys.platform = "linux"` for AMD/ROCm timeout tests | Specified mocked subprocess probes, exact `json.JSONDecodeError` vs `_get_gpus` fallback contract, exact non-`(B)` ROCm key and integer-MB `vram_size` cases, and `sys.platform = "linux"` + `budget.timed_out is True` checks | Keep `E-02` deterministic off-host and prevent wrong malformed-JSON assertions (`PR-003`) |
| `E-04`, `## Project conventions discovered`, `V-04` | Omitted `os.cpu_count()` / `cwd` / `PUBRUN_OUTPUT_DIR` / local-import monkeypatch targets for `live_findings()`, omitted exact finding severities (`git_missing` is `"info"`, not `"warn"`), and did not specify contrasting manifests for `generate_report_multi` variance output | Named all isolation targets, exact finding codes and severities, exact `"and 2 additional packages (12 total)."` / `"(+2 more; 12 recorded)"` / `"(package capture disabled)"` strings, and contrasting multi-run inputs | Prevent host-core flakiness and ensure `_packages_of` variance lines `422` and `430` are rendered and asserted (`PR-004`) |
| `## Approval and execution gate` | Omitted `--scope-reason`/`--scope-ack`, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize dqaj9a` ownership | Hardened Clauses 2, 4, and 5 to match the repository execution contract | Satisfy mandatory execution-contract rules (`PR-005`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 7`, `- Scope-Paths:` (7 test files), 5 E-items in 3 task groups, `- Priority: high`.

1. Yes: spans 7 test files covering 6 production modules across capture and report subsystems.
2. No: test-only plan; makes zero production code, CLI, schema, or security-boundary changes.
3. Yes: Order 7 of 10-child Set `assess-bt` (5 E-items across 3 task groups covering `TEST-C3`, `TEST-C4`, `TEST-U6`, `TEST-U7`, `TEST-U10`).
4. Yes: `- Scope-Paths:` explicitly lists all 7 modified test files.
5. Yes: subtle coverage traps (`meta_snapshot.py:49` tuple cycle, `reproducibility.py:1194` `b'"annotation"'` pre-filter, `resources.py:702` `was_started` guard, and `checks.py:246` host `os.cpu_count()`) would silently leave targeted branches uncovered or flaky without explicit plan preconditions.

AW-TIER: complex

### Step R1

- Checked: every production module, symbol, line range, error message, and existing test file cited by `dqaj9a`:
  - `src/pubrun/capture/resources.py`: `_poll_cpu` clamp (L471-509), `_update_metrics` (L606-675), `stop` (L676-719), `to_manifest_dict` partial/failed strings (L720-752).
  - `src/pubrun/capture/hardware.py`: `_parse_windows_reg_vram` (L116-128), `_parse_amd_smi_json` (L263-325), `_parse_rocm_smi_json` (L328-385), `_parse_positive_timeout` / `_parse_nonnegative_timeout` (L388-411), `_CaptureBudget` (L414-437), `_get_gpus` AMD/ROCm timeouts (L655-706), `get_hardware` (L786-849).
  - `src/pubrun/report/meta_snapshot.py`: `_sanitize_json_value` (L18-55), `generate_meta_snapshot` / `_gather` (L87-129).
  - `src/pubrun/report/reproducibility.py`: `_SEED_SCAN_MAX_LINES`, `_SEED_SCAN_MAX_BYTES`, `_has_recorded_seed_annotation` (L1172-1211).
  - `src/pubrun/report/checks.py`: `_live_fs_health_findings` (L88-118), `_install_health_findings` (L151-213), `live_findings` (L216-258), `live_checks` (L277-304).
  - `src/pubrun/report/methods.py` & `src/pubrun/report/templates.py`: `generate_report` (L240-375), `_packages_of` (L417-431), `generate_report_multi` (L446-470), `MARKDOWN_TEMPLATE` (`Python {python_version} ({python_impl})`).
  - Existing tests: `tests/test_resources.py` (unused `_get_rss_windows` import at L6, guarded `peak_rss_bytes` at L46-47), `tests/test_hardware.py`, `tests/test_hpc_hydration_e2e.py`, `tests/test_reproducibility_assessment.py`, `tests/test_checks_commands.py`, `tests/test_reports.py` (`test_empty_python_version` at L201-206), `tests/test_methods_multi.py`.
- Verified:
  - `PR-001`: `meta_snapshot.py:49` is only reachable via a tuple containing a mutable container referencing the tuple; `reproducibility.py:1198-1199` is gated by `if b'"annotation"' not in raw_line: continue` at line `1194`.
  - `PR-002`: `resources.py:702` gates final measurement on `was_started and not self.is_alive() and not aborted`.
  - `PR-003`: `_parse_amd_smi_json` (L265) and `_parse_rocm_smi_json` (L330) raise `json.JSONDecodeError` on malformed JSON (caught in `_get_gpus` at L675/L704).
  - `PR-004`: `checks.py:209` emits `git_missing` at `INFO` (`"info"`), `checks.py:246-247` scales `high_load` by `os.cpu_count()`, and `methods.py:422,430` are only rendered in `generate_report_multi` when runs differ on `_packages_of`.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability, non-tautological evidence, and execution-gate contract.
- Verified: `PR-001` through `PR-004` guarantee every coverage line demanded by `V-01`..`V-04` is genuinely reachable by the specified tests in `E-01`..`E-04`; `PR-005` completed all five execution-gate clauses.

### Step R3

- Checked: test isolation, determinism, and cross-platform safety (Linux/macOS/Windows).
- Verified: `E-01` preserves the `win32` guard on `test_resources_watcher_threads` while making non-Windows `peak_rss_bytes > 0` unconditional; `E-02` mocks `subprocess.check_output` and `sys.platform = "linux"` so tests never spawn real host GPU tools or depend on host OS; `E-04` isolates `cwd`, `PUBRUN_OUTPUT_DIR`, `os.cpu_count()`, `shutil.which`, `system_metrics`, and `filesystem` probes so `live_findings()`/`live_checks()` tests are 100% deterministic on any host.

### Step R4

- Checked: correctness (A), anti-regression (D), testing and verification (E), KISS/clarity (F), right-sizing (5 E-items, 7 Scope-Paths, `- Size assessment: standard`), and `## Spec / documentation sync` (`N/A`, test-only).
- Verified: zero production code edits needed; every targeted branch exists in the current workspace and has exact contract strings verified against source.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md` and the no-code-pinning testing contract:
  1. QA / QC: caught unreachable `meta_snapshot.py:49` tuple cycle and `reproducibility.py:1194` `b'"annotation"'` pre-filter (`PR-001`) and `was_started` guard on `ResourceWatcher.stop()` (`PR-002`).
  2. Testing and regression: verified every test calls real production functions/threads and asserts observable outputs/exceptions/coverage (zero AST/regex/source-inspection tests), and pinned `os.cpu_count()` and subprocess mocks against host flakiness (`PR-003`, `PR-004`).
  3. UI / UX: verified exact user-visible methods strings (`"Python unknown (Unknown)"`, `"and 2 additional packages (12 total)."`, `"(+2 more; 12 recorded)"`, `"(package capture disabled)"`) (`PR-004`).
  4. Architect: confirmed zero production code churn and clean alignment with existing module contracts.
  5. Software engineer: disambiguated `_parse_amd_smi_json`/`_parse_rocm_smi_json` `json.JSONDecodeError` vs `_get_gpus` fallback (`PR-003`).
  6. Power user: verified `live_findings()`/`live_checks()` test exact `low_memory`/`high_load`/`fs_hung_*`/`fs_slow_*`/`git_missing` codes and severities (`PR-004`).
  7. Novice: verified `test_resources_watcher_threads` fails loudly on non-Windows sampling timeouts instead of silently masking `None` (`E-01`).
  8. Stakeholder: confirmed full coverage of all five testing findings (`TEST-C3`, `TEST-C4`, `TEST-U6`, `TEST-U7`, `TEST-U10`) assigned to Order 07 by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, 7 Scope-Paths, Order 07 of 10-child Set `assess-bt`).
- Confirmed: each E-item is focused and executable in one pass with no over-density or split warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt` (`n6250e` and sibling children `wcjdbu`, `ndobra`, `thbepl`, `qum7gf`, `kk83rk`, `n39jh9`, `kgoymu`, `4eo4z2`, `37sth0`) plus standalone pending plans `8o6o83` and `3u1xgk`.
- Verified: all 7 `Scope-Paths` in `dqaj9a` are strictly disjoint from every other pending plan (`kk83rk` and `3u1xgk` only execute `tests/test_resources.py`, `tests/test_reports.py`, and `tests/test_methods_multi.py` read-only in validation). `- Item-Dependencies: none` is valid.

### Step S5

- Checked: `## Open questions` contains `None.`. All six findings (`PR-001` through `PR-006`) had `Low` overall Remediation Risk, were settled directly by production source code and existing tests, and were fixed in place with zero unfixed, deferred, or open findings and zero human-decision questions. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` | `src/pubrun/report/meta_snapshot.py:45-54`, `src/pubrun/report/reproducibility.py:1194-1204`, `dqaj9a` `E-03`, `V-03` | `V-03` required covering `meta_snapshot.py:46-54` and `reproducibility.py:1198-1199`, but `E-03` omitted a tuple-via-list cycle (leaving `meta_snapshot.py:49` unreachable) and did not require the corrupt JSON line to contain literal `"annotation"` (needed to pass the `b'"annotation"'` pre-filter at `reproducibility.py:1194`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the tuple-via-list cycle case (`lst = []; tup = (lst,); lst.append(tup)`) and the literal `"annotation"` requirement on the corrupt JSON line in `E-03`, `## Project conventions discovered`, and `V-03` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r1-references.md` / `r4-engineering.md` E (Testing) | `src/pubrun/capture/resources.py:687-702`, `dqaj9a` `E-01` | `E-01` did not specify that testing `ResourceWatcher.stop()` skipping final measurement after abort requires an actually started watcher (`self.ident is not None`); on an unstarted watcher, `was_started=False` short-circuits before `not aborted`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified starting the watcher, waiting for `_stop_event.is_set()`, resetting the `_poll_rss` counter, calling `stop()`, and asserting zero re-polls and `end_rss_bytes is None` in `E-01` and `V-01` (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r1-references.md` / `r2-executability.md` | `src/pubrun/capture/hardware.py:265,306-307,330,365-369,655-706,807-838`, `dqaj9a` `E-02` | `E-02` did not mock `subprocess.check_output` during `get_hardware` timeout tests (risking real host tool invocations), left malformed-JSON parser behavior ambiguous (`_parse_*_json` raises `json.JSONDecodeError`, while `_get_gpus` degrades to `[]`), and omitted `sys.platform = "linux"` and `budget.timed_out` assertions for AMD/ROCm timeout tests. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified subprocess mocking, exact `json.JSONDecodeError` vs `_get_gpus` fallback contract, concrete integer-MB `vram_size` and non-`(B)` ROCm key inputs, and `sys.platform = "linux"` + `budget.timed_out is True` in `E-02` (recommendation strength: `strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `r1-references.md` / `r4-engineering.md` E (Testing) | `src/pubrun/report/checks.py:105,112,208-209,220,235,240,246-248,277-304`, `src/pubrun/report/methods.py:302-308,422,430` | `E-04` omitted deterministic isolation targets (`cwd`, `PUBRUN_OUTPUT_DIR`, `os.cpu_count()`, local-import module targets) and exact finding severities (`git_missing` is `"info"`, not `"warn"`), and did not specify contrasting manifests for `generate_report_multi` so `_packages_of` variance lines `422` and `430` actually render. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Named all isolation targets, exact finding codes/severities, exact expected substrings, and contrasting multi-run inputs in `E-04`, `## Project conventions discovered`, and `V-04` (recommendation strength: `strong`). |
| PR-005 | LOW | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` | `dqaj9a` `## Approval and execution gate` | Execution gate omitted `--scope-reason`/`--scope-ack` for out-of-scope edits, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize dqaj9a` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Hardened Clauses 2, 4, and 5 of `## Approval and execution gate` (recommendation strength: `strong`). |
| PR-006 | LOW | IN-SCOPE | `p-proofread.md` / `technical-writing.md` | `dqaj9a` full text | Plan left 12 acronyms unexpanded on first use and used short module filenames instead of full repo-relative `path::Symbol` citations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Expanded all acronyms on first use and normalized all code citations to full repo-relative `path::Symbol` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `dqaj9a` | `complex` | `standard` | Order 07 of 10-child Set `assess-bt`; spans 7 test files across 6 production modules with `Priority: high` and subtle coverage reachability preconditions; answers Yes to tier questions 1, 3, 4, and 5 in `steps/t-tier.md`. | yes |
| D-2 | How to cover `meta_snapshot.py:49` (`PR-001`) | Add a tuple-via-list cycle (`lst = []; tup = (lst,); lst.append(tup)`) in `E-03` | Drop line `49` from `V-03`'s coverage expectation | `src/pubrun/report/meta_snapshot.py:48-49` is genuinely reachable via a mutable container inside a tuple and tests a real circular-reference guard. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` (7 test files) and `- Item-Dependencies: none` are unchanged; all six findings (`PR-001` through `PR-006`) were swept across front matter, `E-01..E-05`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `V-01..V-05`, and `## Approval and execution gate` with zero remaining contradictions, open questions, or unreachable coverage demands. No second pass is needed.

AW-REVIEW: DONE
