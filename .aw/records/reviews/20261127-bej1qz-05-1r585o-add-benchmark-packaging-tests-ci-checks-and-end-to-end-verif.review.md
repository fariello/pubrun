# Review findings: ipd 1r585o

- Subject-Id: 1r585o
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `errors: 0`, `warnings: 0`, `info: 2` boilerplate `IPD-C802`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` with only the same two non-blocking advisories on line 186 boilerplate. Expanded `HPC`, `JSON`, `PBS`, `LSF`, and `SGE` on first use; Mermaid diagram entities and steps match the plan prose.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `- Concern:`, `E-01`, `E-02`, `## Findings` (`F-01`), `## Project conventions discovered`, `## Proposed changes` | Claimed `TestSubmissionVerifier` still targeted deleted `_verify_redacted` and `TestHarnessResolution` asserted errors without a checkout; omitted `TestBenchCLI::test_bench_quick_local_json` `share_safety` file-path loader and `sys.modules` cleanup for `E-01` shim parity test | Reconciled with `mfeptf` (Order 03) which already migrates `TestSubmissionVerifier` to `_share_check`; directed `E-02` to verify/extend `TestSubmissionVerifier` (non-object JSON, `OSError`), update the stale module docstring and `test_bench_quick_local_json`, and directed `E-01` to load `benchmarks/share_safety.py` under a unique temporary module name | Eliminate cross-plan contradiction with `mfeptf` and prevent stale loaders or `sys.modules` leaks (`PR-001`) |
| `E-02`, `E-03` | Ran POSIX `bash` stub-scheduler tests unconditionally in `tests/test_bench_command.py`, hardcoded `src/pubrun/_bench/scripts/`, and omitted Windows venv paths, Python < 3.11 `tomli` handling, `--no-isolation` when `hatchling` is present, ambient `PUBRUN_*` stripping, and `pubrun.__file__` venv assertion in wheel test | Guarded POSIX `bash` stub tests with `skipif(win32 or no bash)` while keeping CLI dispatch tests cross-platform, compared against `get_submit_script_path(...)`, and hardened the wheel test for Windows paths, Python < 3.11 vs 3.11+ `--no-deps`, `hatchling` isolation detection, `PYTHONPATH` + `PUBRUN_*` stripping, and `pubrun.__file__` + no-`runs/` checks | Prevent `windows-latest` CI matrix breakage and offline/env-contaminated wheel test failures (`PR-002`) |
| `E-04`, `V-04` | Used shared `$WORK_DIR/bench-cwd` across both `check_wheel "direct"` and `check_wheel "from-sdist"` calls, checked only `workloads/noop.py` (omitting other workloads and `__init__.py`), omitted `test_share_safety.py` from forbidden list, omitted `--no-deps` and `check_share_safe_text` check | Switched to per-label `$WORK_DIR/bench-cwd-$label` with exact-one file check, no-`runs/` check, and venv `check_share_safe_text` check; checked all 16 required `_bench` files and all 10 forbidden paths; added `--no-deps` on Python 3.12 | Eliminate false-positive `from-sdist` wheel smoke pass and enforce full wheel cleanliness and zero-dependency requirements (`PR-003`) |
| `E-05`, `## Required tests / validation` (Commands 1 and 2) | Imported `pubrun._bench.share_safety` in outer `python3 -c` without `PYTHONPATH=src` or `import pubrun.minimal`, used bare `tempfile.mkdtemp`, kept ambient `PUBRUN_*`, and passed `--no-submit` in Command 1 | Used `TemporaryDirectory`, stripped `PYTHONPATH` + `PUBRUN_*`, ran `pubrun bench --quick --local` verbatim with `stdin=DEVNULL` (verifying `SAFE TO SUBMIT`, `PASSED`, printed path, no `runs/`, and `check_share_safe_text` inside the venv Python), checked sdist for `.aw/`, and added `sys.path` + `import pubrun.minimal` in Command 2 | Prevent worktree `ModuleNotFoundError`, `pubrun` auto-start stray `runs/`, leaked temp dirs, and match `bej1qz` AC-1 verbatim (`PR-004`) |
| `## Approval and execution gate`, `V-01..V-05`, acronyms (`HPC`, `JSON`, `PBS`, `LSF`, `SGE`) | Single gate paragraph missing blocking-OQ precondition, `--scope-reason`/`--scope-ack`, validation honesty, no-`git add -A`/raw `git commit`, and conditional finalize ownership; `V-01..V-05` pinned test class names and omitted runtime code paths; unexpanded acronyms | Replaced with five-clause execution contract matching sibling plans; rewrote `V-01..V-05` around required behaviors, mechanisms, and runtime-demonstration code paths; expanded acronyms on first use | Satisfy execution-contract, re-derivation, reachability, and technical-writing rules (`PR-005`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: bej1qz`, `- Order: 5`, `- Item-Dependencies: executed:29nsim, executed:c1zz3x, executed:mfeptf, executed:cuboum`, `- Scope-Paths:` (`tests/test_bench_command.py, tests/test_benchmark_intake_bugs.py, .github/workflows/ci.yml`), 5 E-items in 4 task groups.

1. No public API or specification change; updates CI packaging gates in `.github/workflows/ci.yml` and acts as the final cross-plan acceptance gate for Set `bej1qz`.
2. Yes: tests `pubrun._bench.share_safety` and `pubrun.__main__::_share_check` (the privacy/PII redaction gate) and adds CI wheel exclusion guards preventing `.aw/` and local benchmark results from shipping in release wheels.
3. Yes: 5 E-items across 4 task groups spanning 3 files (`tests/test_bench_command.py`, `tests/test_benchmark_intake_bugs.py`, `.github/workflows/ci.yml`) and integrating/verifying all four predecessor plans (`29nsim`, `c1zz3x`, `mfeptf`, `cuboum`) in Set `bej1qz`.
4. Yes: `- Scope-Paths:` explicitly lists `tests/test_bench_command.py, tests/test_benchmark_intake_bugs.py, .github/workflows/ci.yml`.
5. Yes: unguarded POSIX bash tests break `windows-latest` CI across 7 Python versions; a shared `$WORK_DIR/bench-cwd` in `ci.yml` masks `from-sdist` wheel failures; worktree-unsafe validation commands fail or create stray `runs/` directories during Set verification.

AW-TIER: complex

### Step R1

- Checked: `tests/test_bench_command.py` (all 885 lines including `_load_harness`, `TestRedaction`, `TestHarnessResolution`, `TestSchedulerSubmitSafety`, `TestBenchCLI`, `TestIoBaselineScenarios`, `TestSubmissionVerifier`, `TestHarnessRedactedOnlyDefault`, `TestBenchTiers`, `TestBenchNoBaselineFlag`), `tests/test_benchmark_intake_bugs.py` (all 659 lines including `_load`, `TestShareSafetyNone`, `TestHarnessSelfCheckGate`), `.github/workflows/ci.yml` (all 170 lines including `test`, `extra-suites`, `no-tui`, `packaging`, `typecheck`), `tests/conftest.py`, `pyproject.toml`, `hatch_build.py`, `src/pubrun/__main__.py` (`_find_bench_harness`, `_share_check`, `_contribute`, `_run_bench`), `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `tests/test_report_subpackage_integrity.py`, `benchmarks/submit_bench_{pbs,lsf,sge}.sh`, graduated backlog item `bej1qz`, orchestrator `s3y296`, and reviewed sibling plans `29nsim`, `c1zz3x`, `mfeptf`, and `cuboum`.
- Verified: every cited file and symbol exists at the referenced path; cross-checking against `mfeptf` surfaced the stale `_verify_redacted` premise and missed `test_bench_quick_local_json` loader (`PR-001`), and checking `.github/workflows/ci.yml` surfaced the Windows CI matrix (`PR-002`) and dual `check_wheel` call (`PR-003`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:29nsim, executed:c1zz3x, executed:mfeptf, executed:cuboum`, live-artifact vs behavior validation bars, runtime-demonstration reachability for `V-05`, worktree-safe validation commands, and the execution gate contract.
- Verified: `PR-004` fixed worktree/auto-start/cleanup defects in Commands 1 and 2; `PR-005` completed the five-clause execution contract and added explicit behavioral bars and runtime code-path citations to `V-01..V-05`.

### Step R3

- Checked: privacy/PII redaction tests (`_share_check`, `check_share_safe_text`, non-echoing failure messages), shell-injection testing of PBS/LSF/SGE scripts (`PUBRUN_QUEUE` metacharacters), non-TTY `pubrun bench --quick --local` never prompting or transmitting to GitHub (`src/pubrun/__main__.py::_contribute:1935-1946`), and CI wheel/sdist exclusion of `.aw/`, `benchmarks/results/`, and `benchmarks/data/`.
- Verified: `PR-003` and `PR-004` strengthen both CI and local verification to check `check_share_safe_text` on real clean-venv wheel output and assert zero `.aw/` or non-runtime benchmark artifacts in sdist and wheels.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified: `PR-002` ensures cross-platform CI compatibility (`windows-latest`, `macos-latest`, `ubuntu-latest`, Python 3.8 through 3.14) and zero code-pinning source-text checks; `PR-003` prevents false-positive `from-sdist` smoke passes in `ci.yml`; `PR-004` makes whole-Set verification deterministic and self-cleaning; `## Spec / documentation sync` truthfully defers documentation updates to `cuboum` (Order 04).

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught shared `$WORK_DIR/bench-cwd` false positive in `ci.yml` (`PR-003`) and worktree/auto-start/temp-leak bugs in Commands 1 and 2 (`PR-004`).
  2. Testing and regression: caught `windows-latest` POSIX bash hazard (`PR-002`), stale `TestSubmissionVerifier` premise and missed `test_bench_quick_local_json` loader (`PR-001`), and `sys.modules["share_safety"]` leakage risk (`PR-001`).
  3. UI / UX: confirmed Command 1 runs verbatim `pubrun bench --quick --local` (non-TTY) and checks `"SAFE TO SUBMIT"`, `"PASSED"`, and the printed redacted file path (`PR-004`).
  4. Architect: verified clean direct imports of `pubrun._bench` and single-source `share_safety` alongside checkout shim parity tests (`PR-001`, `PR-002`).
  5. Software engineer: checked Python 3.8–3.10 `tomli` vs Python 3.11+ `--no-deps`, Windows venv executable paths, and `hatchling` `--no-isolation` handling (`PR-002`).
  6. Power user: verified `PUBRUN_RESULTS_DIR`, `PUBRUN_UNREDACTED`, and all four HPC schedulers are tested without a checkout (`PR-002`).
  7. Novice: verified clean-venv `pip install` + `pubrun bench --quick --local` works out of the box from any directory with zero extra dependencies (`PR-003`, `PR-004`).
  8. Stakeholder: confirmed full alignment with all five acceptance criteria of backlog item `bej1qz`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 4 task groups, 3 Scope-Paths, Order 05 of 5-child Set `bej1qz`).
- Confirmed: each E-item targets one focused concern/file or the final whole-Set verification pass; no further splitting warranted.

### Step R7

- Checked: cross-plan consistency across Set `bej1qz` (`s3y296`, `29nsim`, `c1zz3x`, `mfeptf`, `cuboum`, `1r585o`).
- Verified: `1r585o` depends on `executed:29nsim, executed:c1zz3x, executed:mfeptf, executed:cuboum`, tests every file and contract created by `29nsim` (core `_bench` modules, 5 workloads, checkout shims), `c1zz3x` (5 packaged HPC scripts, `import pubrun.minimal, pubrun._bench.harness`, `-m pubrun._bench.harness`, `PUBRUN_RESULTS_DIR`), and `mfeptf` (`_find_bench_harness`, `_find_bench_submit_script`, `_run_bench`, `_share_check`, `TestSubmissionVerifier`), and fulfills every cross-IPD validation and completion criterion assigned to `1r585o` in orchestrator `s3y296`. `PR-001` reconciled `TestSubmissionVerifier` ownership between `mfeptf` and `1r585o`, and `PR-003` aligned the 16 required wheel files with `29nsim` + `c1zz3x`.

### Step S5

- Checked: `## Open questions` contains `None.`. All five findings (`PR-001` through `PR-005`) had `Low` overall Remediation Risk and were fixed in place from repository evidence, leaving zero open or deferred findings and zero unresolved human decisions. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r7-cross-plan.md` / `r1-references.md` (Cross-plan consistency and stale test loaders) | `.aw/records/plans/pending/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md:5,53-66,124` vs `.aw/records/plans/pending/20261127-bej1qz-03-mfeptf-wire-pubrun-bench-cli-to-packaged-runtime-and-single-source.ipd.md:58-63` and `tests/test_bench_command.py::TestBenchCLI.test_bench_quick_local_json:306-311` | `1r585o` assumed `TestSubmissionVerifier` still targeted deleted `_verify_redacted` (already migrated in reviewed sibling `mfeptf` E-01), misstated `TestHarnessResolution` behavior (while overlooking the stale module docstring at line 5), missed migrating `test_bench_quick_local_json`'s file-path loader of `benchmarks/share_safety.py`, and did not guard `E-01`'s `benchmarks/share_safety.py` parity test against `sys.modules["share_safety"]` leakage. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reconciled `- Concern:`, `E-02`, `F-01`, `## Project conventions discovered`, and `V-02` with `mfeptf` (extending `TestSubmissionVerifier` for non-object JSON and `OSError`), added module docstring and `test_bench_quick_local_json` migration in `E-02`, and required temporary-name loading with `finally` cleanup in `E-01` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r4-engineering.md` A, E (Cross-platform CI and wheel-test portability) | `.aw/records/plans/pending/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md:67,76-82` vs `.github/workflows/ci.yml:18-45` and `pyproject.toml:40-61` | Running POSIX `bash` stub-scheduler tests unconditionally in `tests/test_bench_command.py` breaks the `windows-latest` CI matrix; `E-03` hardcoded `src/pubrun/_bench/scripts/` instead of `get_submit_script_path(...)`; and `E-03`'s wheel test omitted Windows venv executable paths, Python < 3.11 `tomli` handling vs Python 3.11+ `--no-deps`, `hatchling` `--no-isolation` detection, ambient `PUBRUN_*` stripping, and `pubrun.__file__` / no-`runs/` assertions. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split `E-03`'s HPC tests into cross-platform CLI dispatch checks (using `get_submit_script_path` and checking `PUBRUN_UNREDACTED`) plus `skipif(win32 or no bash)` POSIX stub execution (also applied in `E-02`), and hardened `E-03`'s wheel test with `pytest.importorskip("build")`, `hatchling` `--no-isolation` detection, cross-platform venv paths, Python-version-aware `--no-deps`, `PYTHONPATH` + `PUBRUN_*` stripping, and `pubrun.__file__` + no-`runs/` assertions (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` A, E / `r3-security.md` (CI wheel check isolation and completeness) | `.aw/records/plans/pending/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md:88-93` vs `.github/workflows/ci.yml:111-151` | `check_wheel` in `.github/workflows/ci.yml` runs twice (`direct` and `from-sdist`), so sharing `$WORK_DIR/bench-cwd` lets `from-sdist` pass on `direct`'s leftover `*.redacted.json`; `E-04` also checked only `workloads/noop.py` (omitting 4 workloads and 2 `__init__.py` files), omitted `test_share_safety.py` from forbidden paths, omitted `--no-deps` on Python 3.12, and did not run `check_share_safe_text` or assert no `runs/` dir on clean-venv output. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-04` and `V-04` to use per-label `$WORK_DIR/bench-cwd-$label` with exact-one `*.redacted.json` check, no-`runs/` check, and venv `check_share_safe_text` verification, check all 16 required `pubrun/_bench/` files and all 10 forbidden entries, and pass `--no-deps` to `pip install` on Python 3.12 (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` E (Worktree-safe, auto-start-safe, self-cleaning validation) | `.aw/records/plans/pending/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md:99-105,146-156` vs `src/pubrun/__main__.py::_contribute:1935-1946` and `tests/conftest.py::_subprocess_pythonpath:18-39` | Validation Commands 1 and 2 imported `pubrun._bench.share_safety` in outer `python3 -c` without `PYTHONPATH=src` (importing the main checkout in worktrees and failing with `ModuleNotFoundError`) and without `import pubrun.minimal` (triggering `pubrun` auto-start and stray `runs/`), leaked temp dirs via bare `tempfile.mkdtemp` on failure, failed to strip ambient `PUBRUN_*`, and passed `--no-submit` in Command 1 instead of running `bej1qz` AC-1's `pubrun bench --quick --local` with `stdin=DEVNULL`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote Commands 1 and 2 with `TemporaryDirectory`, `PYTHONPATH` + `PUBRUN_*` stripping, verbatim `pubrun bench --quick --local` with `stdin=DEVNULL` (verifying `SAFE TO SUBMIT`, `PASSED`, printed path, no `runs/`, `pubrun.__file__` inside venv, and `check_share_safe_text` via venv Python + sdist `.aw/` check), and worktree `src/` + `import pubrun.minimal` in Command 2; reconciled `E-05` and `V-05` (recommendation strength: `very strong`). |
| PR-005 | MEDIUM | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` (Execution contract, validation-bar rules, and technical writing) | `.aw/records/plans/pending/20261127-bej1qz-05-1r585o-add-benchmark-packaging-tests-ci-checks-and-end-to-end-verif.ipd.md:5,65,67,188-218` | `## Approval and execution gate` omitted the blocking-open-question precondition, `--scope-reason`/`--scope-ack` scope declaration, hard-MUST validation honesty rule, explicit prohibition of `git add -A`/`git add .`/raw `git commit`, and conditional runner vs manual `aw ipd finalize 1r585o` ownership; `V-01..V-05` pinned test class names without stating behaviors/mechanisms and omitted runtime code paths in `V-05`; `HPC`, `JSON`, `PBS`, `LSF`, and `SGE` were unexpanded on first use. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with the five-clause execution contract, rewrote `V-01..V-05` with explicit behavior/mechanism bars and runtime code-path citations, and expanded `HPC`, `JSON`, `PBS`, `LSF`, and `SGE` on first use (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `1r585o` | `complex` | `standard` | Order 05 of 5-child Set `bej1qz`, tests privacy/redaction gates and CI wheel exclusions, and serves as the whole-Set cross-plan acceptance gate integrating `29nsim`, `c1zz3x`, `mfeptf`, and `cuboum`; answers Yes to tier questions 2, 3, and 5. | yes |
| D-2 | How to handle POSIX `bash` stub-scheduler tests in `tests/test_bench_command.py` on Windows CI | Split into cross-platform CLI dispatch tests (mocked `subprocess.run`) plus `@pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, ...)` for live bash script execution | Run bash stubs unconditionally (breaks `windows-latest` CI) or keep source-text scanning (violates `AGENTS.md` no-code-pinning rule) | `.github/workflows/ci.yml:18-45`, `AGENTS.md` (no code-pinning tests), and existing POSIX skip patterns (`tests/test_quality.py:527`, `tests/test_capture_engine_bugs.py:202`). | yes |
| D-3 | Whether Validation Command 1 should run `pubrun bench --quick --local` without `--no-submit` | Run `pubrun bench --quick --local` with `stdin=subprocess.DEVNULL` (no `--no-submit`) | Keep `--no-submit` (skips `_print_safe_file_block` and `_share_check` inside the installed wheel) | Backlog `bej1qz` acceptance criterion 1 and `src/pubrun/__main__.py::_contribute:1935-1946` (non-TTY never prompts or transmits). | yes |

### Step S6

- Checked: Round 1 made surgical in-place revisions to existing items `E-01..E-05`, `V-01..V-05`, validation commands, and the execution gate without adding or removing `E-*`/`V-*` items, without changing `- Scope-Paths:` or `- Item-Dependencies:`, and without introducing new open questions or structural ambiguities. Full cross-section consistency was verified. No additional pass is needed.

AW-REVIEW: DONE
