# IPD: Bench env isolation filesystem live probing scaling scrub and submission retag

- Date: 2026-11-27
- Kind: child
- Concern: Fix four benchmark/capture bugs (`BUG-E5`, `BUG-E6`, `BUG-E7`, `BUG-E8`) and close benchmark test-suite performance and collection-isolation gaps (`TEST-I5` benchmarks, `TEST-I6` redundant harness runs).
- Scope: Fix `src/pubrun/_bench/harness.py`, `src/pubrun/capture/filesystem.py`, `benchmarks/scaling_bench.py`, and `benchmarks/pull_submissions.py`, and add regression tests plus fixture caching / `sys.path` cleanup in `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, and `tests/test_capture_engines.py`.
- Scope-Paths: src/pubrun/_bench/harness.py, src/pubrun/capture/filesystem.py, benchmarks/scaling_bench.py, benchmarks/pull_submissions.py, benchmarks/test_benchmarks.py, benchmarks/test_share_safety.py, benchmarks/test_pull_submissions.py, tests/test_capture_engines.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix bench PUBRUN_* leakage, mount-point live probing, scaling_bench scrub key mismatch, pull_submissions retag, and benchmark suite caching
- Work-Kind: bug
- Priority: medium
- Set: assess-bt
- Order: 6
- Highest E allocated: 05
- Author: Antigravity
- Id: n39jh9

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 to-review (Antigravity): Authored review-ready child IPD from parallel `/assess bugs` and `/assess testing` audits on HEAD `512ee68` / `8f2aacd`.
- 2026-11-27 draft (Antigravity): created.

## Goal

Prevent ambient `PUBRUN_*` environment variables from polluting `pubrun bench` child runs, probe mounted filesystems by mount point rather than uncreated child paths in `filesystem.probe_paths_live`, align `scaling_bench.py` share-safety skip keys and workdir needle guards, fix `pull_submissions.py` re-tagging of previously rejected issues, and eliminate ~10x redundant harness executions and collection-time `sys.path` leaks in the benchmark test suite.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix packaged bench isolation and filesystem mount probing

- [ ] E-01 Fix `src/pubrun/_bench/harness.py` (`BUG-E5`) and `src/pubrun/capture/filesystem.py` (`BUG-E7`):
  - In `src/pubrun/_bench/harness.py::_child_env_with_checkout_src`, strip all ambient `PUBRUN_*` keys from the copied child environment before scenarios apply explicit `scn.env` and `PUBRUN_IMPORT_MODE`; in `_run_pass`, set `env["PUBRUN_PROFILE"] = "default"` unconditionally so ambient `PUBRUN_OUTPUT_DIR`, `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_PROFILE`, and `PUBRUN_BENCH_IO_TARGET` cannot pollute benchmark runs.
  - In `src/pubrun/capture/filesystem.py::probe_paths_live`, launch the live `statvfs` / `GetDiskFreeSpaceExW` probe against `mp` (the mount point deduplication key) whenever `entry.get("mount_point")` is present, falling back to `entry.get("path")` only when `mount_point` is absent.
  - Depends on: none
  - Expected outcome: Benchmark child runs are isolated from ambient `PUBRUN_*` overrides; an uncreated `results_dir` sharing a mounted filesystem never poisons live probe results for sibling paths on that mount.
  - Execution state: pending

### Task group 2: Fix `scaling_bench.py` share-safety validation and `pull_submissions.py` retag

- [ ] E-02 Fix `benchmarks/scaling_bench.py` (`BUG-E6`) and `benchmarks/pull_submissions.py` (`BUG-E8`):
  - In `benchmarks/scaling_bench.py::_validate_share_safety`, validate JSON needle leaks using `scaling_bench._SCRUB_SKIP_KEYS` (covering `"mode"`, `"workdir_kind"`, `"workdir_fstype"`, `"python_implementation"`, `"schema_version"`, `"git_revision"`, `"started_at_utc"`, `"finished_at_utc"`) instead of delegating to `startup_breakdown._SCRUB_SKIP_KEYS`; in `main`, guard raw `args.workdir` with `if "/" in args.workdir or "\\" in args.workdir:` before adding it to `extra_needles` alongside `str(Path(args.workdir).resolve())`.
  - In `benchmarks/pull_submissions.py::_retag` (and `_process_issue`), include `["--add-label", add, "--remove-label", remove]` before `["--add-label", add]` (and/or filter `--remove-label` flags against `current_labels=issue["labels"]`) so re-submitted issues labeled `status:needs-fix` (without `status:pending`) cleanly swap `status:needs-fix` for `status:accepted`.
  - Depends on: none
  - Expected outcome: `scaling_bench.py` does not false-fail share-safety on `--mode quick` / `--workdir quick` or matching usernames/hostnames; `pull_submissions.py` never leaves re-accepted issues dual-labeled `status:accepted` + `status:needs-fix`.
  - Execution state: pending

### Task group 3: Add regression tests, cache benchmark harness fixtures, and validate

- [ ] E-03 Add regression tests and harness caching / import isolation in `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, and `benchmarks/test_pull_submissions.py` (`BUG-E5`, `BUG-E6`, `BUG-E8`, `TEST-I5`, `TEST-I6`):
  - In `benchmarks/test_benchmarks.py`: add regression test for `BUG-E5` setting `PUBRUN_OUTPUT_DIR`, `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_PROFILE`, `PUBRUN_AUTO_START`, and `PUBRUN_BENCH_IO_TARGET` via `monkeypatch` and verifying `_build_child_command` strips them while keeping scenario `scn.env` / `PUBRUN_IMPORT_MODE`; refactor read-only harness output tests to share a module-scoped cached benchmark run fixture so the suite does not invoke the full harness ~10 times redundantly (`TEST-I6`); replace collection-time `sys.path` mutation with scoped/restored loading (`TEST-I5`).
  - In `benchmarks/test_share_safety.py`: add regression test for `BUG-E6` running `scaling_bench._scrub_obj` + `scaling_bench._validate_share_safety` with `extra_needles=["quick"]` and simulated username `"ext4"` / `"temporary"`, asserting `ok is True` and `result["mode"] == "quick"` intact; clean up collection-time `sys.path` mutation (`TEST-I5`).
  - In `benchmarks/test_pull_submissions.py`: add regression test for `BUG-E8` mocking `_run_gh` to fail whenever `--remove-label` names an absent label on an issue initially labeled `{"type:benchmark-submission", "status:needs-fix"}`, asserting final labels contain `"status:accepted"` and not `"status:needs-fix"`; clean up collection-time `sys.path` mutation (`TEST-I5`).
  - Depends on: E-01, E-02
  - Expected outcome: All benchmark script bugs have deterministic regression tests, extra-suite runtime drops dramatically via fixture reuse, and collection-time `sys.path` leaks are removed.
  - Execution state: pending

- [ ] E-04 Add `probe_paths_live` mount-point regression test in `tests/test_capture_engines.py` (`BUG-E7`):
  - Pass an `fs_data` dict containing a non-existent `results_dir` path and an existing `install_dir` path sharing `mount_point`, call `probe_paths_live(fs_data)`, and assert both entries receive `live["status"] == "complete"` with valid capacity metrics.
  - Depends on: E-01
  - Expected outcome: `BUG-E7` is covered by a deterministic behavioral regression test.
  - Execution state: pending

- [ ] E-05 Run targeted `pytest -p randomly` and 3-OS `mypy` validation and record complete output (including benchmark suite runtime):
  - Run all commands listed in `## Required tests / validation` and verify exit `0`.
  - Depends on: E-03, E-04
  - Expected outcome: All benchmark and capture tests pass under `-p randomly` and 3-OS `mypy` exits `0`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `benchmarks/startup_breakdown.py` already strips ambient `PUBRUN_*` keys when spawning isolated children and guards bare relative `args.workdir` with `if "/" in args.workdir or "\\" in args.workdir:`.
- `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, and `benchmarks/test_pull_submissions.py` are run as extra suites alongside `tests/` (empirically 346.52s on baseline `512ee68` due to redundant harness invocations in `benchmarks/test_benchmarks.py`).

## Findings

| ID | Concerns | Severity | Remediation Risk | Persona | Summary |
|---|---|---|---|---|---|
| `BUG-E5` | bugs | Medium | Low (`functionality`) | QA / Software Engineer | `src/pubrun/_bench/harness.py` does not strip ambient `PUBRUN_*` variables (`PUBRUN_OUTPUT_DIR`, `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_PROFILE`, `PUBRUN_BENCH_IO_TARGET`). |
| `BUG-E6` | bugs | Medium | Low (`functionality`) | QA / Software Engineer | `benchmarks/scaling_bench.py::_validate_share_safety` uses `startup_breakdown._SCRUB_SKIP_KEYS` (missing 8 keys) and appends bare relative `args.workdir` to `extra_needles`. |
| `BUG-E7` | bugs | Medium | Low (`functionality`) | QA / Software Engineer | `filesystem.probe_paths_live` deduplicates by `mount_point` but probes `entry["path"]`, so an uncreated `results_dir` poisons all sibling paths on that mount. |
| `BUG-E8` | bugs | Medium | Low (`functionality`) | QA / Software Engineer | `benchmarks/pull_submissions.py::_retag` omits `[--add-label add, --remove-label remove]`, leaving re-submitted accepted issues dual-labeled with `status:needs-fix`. |
| `TEST-I5` (benchmarks) | testing | Medium | Low (`complexity`) | Testing Expert | Collection-time `sys.path`/`sys.modules` mutations in `benchmarks/test_*.py`. |
| `TEST-I6` (benchmarks) | testing | Medium | Low (`complexity`) | Testing / CI Engineer | `benchmarks/test_benchmarks.py` invokes the full benchmark harness ~10x redundantly (~346s runtime). |

## Proposed changes (ordered, validatable)

1. `E-01` (`src/pubrun/_bench/harness.py`, `src/pubrun/capture/filesystem.py`): Strip `PUBRUN_*` in bench child env and probe `mount_point` in `probe_paths_live`.
2. `E-02` (`benchmarks/scaling_bench.py`, `benchmarks/pull_submissions.py`): Align scrub skip keys / workdir needle guard and fix `_retag` label transitions.
3. `E-03` (`benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`): Add regression tests, share read-only harness fixture, and remove collection-time `sys.path` leaks.
4. `E-04` (`tests/test_capture_engines.py`): Add `probe_paths_live` regression test.
5. `E-05` (validation): Run randomized pytest on benchmark/capture suites and 3-OS `mypy`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Strictly scoped to the four affected bench/filesystem modules and four directly paired test files.
- Under-scope: none. Every finding listed in `## Findings` has a concrete fix and behavioral regression test.

## Required tests / validation

1. Targeted randomized pytest run across benchmark suites and capture engines:
   ```sh
   pytest -p randomly benchmarks/test_benchmarks.py benchmarks/test_share_safety.py benchmarks/test_pull_submissions.py tests/test_capture_engines.py -v
   ```
2. Three-OS static type check:
   ```sh
   mypy && mypy --platform win32 && mypy --platform darwin
   ```

## Spec / documentation sync

N/A. Fixes align benchmark isolation, live filesystem probing, share-safety validation, and submission re-tagging with existing documented behavior.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result (which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- src/pubrun/_bench/harness.py src/pubrun/capture/filesystem.py` and passing pytest output exercising `_build_child_command` env stripping and `probe_paths_live` mount-point probing.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- benchmarks/scaling_bench.py benchmarks/pull_submissions.py` and passing pytest output from `benchmarks/test_share_safety.py` and `benchmarks/test_pull_submissions.py`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- benchmarks/test_benchmarks.py benchmarks/test_share_safety.py benchmarks/test_pull_submissions.py` confirming fixture caching and scoped module loading, plus passing pytest output naming the new regression tests and elapsed time.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `pytest -v` output from `tests/test_capture_engines.py` confirming the new `probe_paths_live` test passes.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted complete output of both commands in `## Required tests / validation`, both exiting `0` with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Open questions and approval:** Do not execute until explicit human approval is recorded (`aw ipd set approved n39jh9 --by-human` or `aw set approved assess-bt --by-human`).
2. **Scope declaration:** Modify only the eight declared `Scope-Paths`.
3. **Validation honesty:** Paste actual command outputs from this workspace for every `V-*` item.
4. **Commits and push policy:** Commit only files modified for this plan through `aw commit n39jh9 -- <paths>`. Never push, tag, or publish.
5. **Lifecycle finalization:** Finalize via `aw ipd finalize n39jh9` (or let the runner finalize) only after every `E-*` is `performed` and every `V-*` is `pass`.
