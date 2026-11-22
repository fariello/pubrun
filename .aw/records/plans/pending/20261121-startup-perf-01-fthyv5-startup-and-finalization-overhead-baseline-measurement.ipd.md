# IPD: Startup and Finalization Overhead Baseline Measurement

- Date: 2026-11-21
- Kind: child
- Concern: Reproducible pre-change measurement of import, startup capture, finalization, subprocess spawn, serialization, and synchronization costs.
- Scope: Add a stdlib-only, non-publishing startup and finalization breakdown benchmark (`benchmarks/startup_breakdown.py`), add installed-layout and short-versus-long workload coverage in `benchmarks/scenarios.py` and `benchmarks/README.md`, add behavioral tests in `tests/test_startup_benchmark.py`, and execute the pre-change baseline to establish baseline-derived numerical targets.
- Scope-Paths: benchmarks/startup_breakdown.py, benchmarks/scenarios.py, benchmarks/README.md, tests/test_startup_benchmark.py
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Add startup/finalization breakdown benchmark and record pre-change baseline measurements and derived targets
- Work-Kind: followup
- Priority: high
- From-Backlog: t1xqpw
- Set: startup-perf
- Order: 1
- Highest E allocated: 05
- Author: agent
- Id: fthyv5
- Approval: 2026-11-22, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 approved (aw set): status set to approved
- 2026-11-22 /plan-review (Antigravity / Gemini): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-007
- 2026-11-22 draft (agent): created.
- 2026-11-22 to-review (agent): authored review-ready child plan from backlog item `t1xqpw`.

## Goal

Measure `pubrun` startup, import, capture, finalization, subprocess creation, serialization, and synchronization overhead before modifying any production code, and establish baseline-derived numerical targets that later plans in Set `startup-perf` verify against: `4il383` (build-stamped and deferred commit identity), `tkmm5p` (snapshot write coalescing, durability policy, and bounded capture work), and `ckc3vl` (post-change overhead comparison and documentation sync).

### Baseline measurement workflow

The text in `## Proposed changes (ordered, validatable)` is normative. This diagram summarizes the local, non-publishing measurement flow in `benchmarks/startup_breakdown.py`.

```mermaid
flowchart TD
    A["Capture environment metadata (OS, Python, CPU, git commit, filesystem type)"] --> B["Create ephemeral subdir under --workdir (or temp dir), isolated site-packages copy, and temp Git repo cwd"]
    B --> C["Run Pass 1 (cold) through Pass N (warm) fresh child processes with isolated config env"]
    C --> D{"Scenario category"}
    D -->|Import-only| E["Measure pubrun.minimal and pubrun.noauto (checkout, installed, installed-nested; clean timing + git spawn counter)"]
    D -->|Short workload| F["Measure bare-python-noop, auto-noop-default, and phased noauto/start/noop/stop (phase ms, counters, absolute ms, relative %)"]
    D -->|Long workload| G["Measure bare-python-cpu-burn, auto-cpu-burn-default, and phased noauto/start/cpu_burn/stop (phase ms, counters, absolute ms, relative %)"]
    E --> H["Compute median, mean, p95, stdev, and IQR per pass; validate share-safety and emit redacted JSON/Markdown"]
    F --> H
    G --> H
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Measurement harness and scenario coverage

- [x] E-01 Create `benchmarks/startup_breakdown.py` to measure import-only, auto-start, startup capture, workload, finalization, subprocess spawns, serialization, and synchronization costs in fresh child processes.
  - Depends on: none
  - Expected outcome: `benchmarks/startup_breakdown.py` uses Python standard library modules only (compatible with Python 3.8 through 3.14) and supports `--iterations`, `--passes`, `--warmup`, `--workdir`, `--durability-policies`, and `--out` with explicit CLI input validation. It creates and cleans up only a dedicated ephemeral subdirectory inside `--workdir`, isolates child `PUBRUN_*` and user-config environment variables, and never invokes GitHub, Gist, or scheduler commands. It runs clean uninstrumented timing probes alongside dedicated instrumented counter/serialization probes so `subprocess`/`json` wrappers do not distort wall-clock timings, separates import, startup capture, workload, and finalization costs, counts spawned `git` processes, `manifest.json`/`config.resolved.json` atomic writes, and `os.fsync` calls, compares source-checkout layout against isolated installed-package and nested-user-repo layouts (verifying `pubrun.__file__`), and reports Pass 1 (cold) through Pass N (warm) median, mean, 95th percentile (p95), standard deviation (stdev), and Interquartile Range (IQR) in milliseconds alongside absolute overhead (ms) and relative overhead (%) for short (`noop.py`) and long (`cpu_burn.py`) workloads. All emitted JSON and Markdown output omits raw paths, scrubs hostname, username, home directory, `--workdir`, and repository root substrings, and passes `benchmarks/share_safety.py::check_share_safe` before emission.
  - Execution state: performed

- [x] E-02 Update `benchmarks/scenarios.py` to add a realistic default-config startup scenario (`startup-auto-default`, measuring `auto` with default config rather than `_ALL_OFF` only) while preserving full `pubrun-benchmark/5` schema conformance and existing scenario names.
  - Depends on: E-01
  - Expected outcome: `benchmarks/scenarios.py::all_scenarios` retains all existing scenarios unchanged and adds `startup-auto-default` in group `"startup"` so `benchmarks/harness.py` tracks default auto-start overhead alongside `_ALL_OFF` `import-auto`. `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, and `tests/test_bench_command.py` pass without error.
  - Execution state: performed

- [x] E-03 Update `benchmarks/README.md` to document `benchmarks/startup_breakdown.py`, how to run it locally or on a shared filesystem via `--workdir`, how cold versus warm passes and dispersion metrics are reported, and that no submission or scheduler job is executed automatically.
  - Depends on: E-02
  - Expected outcome: `benchmarks/README.md` documents the breakdown script flags, output schema, and local-versus-shared filesystem testing instructions without em or en dashes in newly added prose.
  - Execution state: performed

### Task group 2: Behavioral tests and pre-change baseline capture

- [x] E-04 Create `tests/test_startup_benchmark.py` with behavioral tests exercising `benchmarks/startup_breakdown.py` end-to-end on small iteration counts.
  - Depends on: E-03
  - Expected outcome: Tests execute `benchmarks/startup_breakdown.py` via Python function calls and subprocess CLI (`--iterations 2 --passes 2 --warmup 0`, plus `--iterations 1` edge case and invalid CLI argument rejection). They verify phase breakdown keys (import, startup, workload, finalization), `git`/write/`fsync`/serialization counters, installed-layout and nested-repo scenarios, cold-versus-warm pass arrays, dispersion statistics (median, mean, p95, stdev, IQR), absolute ms and relative overhead %, environment/filesystem metadata, redaction of home paths, hostnames, and custom `--workdir` paths (validated via `check_share_safe`), and preservation of pre-existing sibling files inside `--workdir` after cleanup.
  - Execution state: performed

- [x] E-05 Run `tests/test_startup_benchmark.py`, `tests/test_bench_command.py`, `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, and the pre-change baseline measurement (`python benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1`) against unmodified `src/pubrun/`, record the full baseline summary and proposed baseline-derived targets in `V-05`, and leave no stray unredacted files in the working tree.
  - Depends on: E-04
  - Expected outcome: All targeted test suites exit 0. The redacted pre-change baseline output is pasted in `V-05` with environment, git revision, filesystem type, repetitions, cold/warm pass medians, mean, p95, stdev, IQR, subprocess/write/fsync/serialization counters, absolute milliseconds, and relative overhead percentages for short and long workloads. `V-05` records concrete baseline-derived improvement targets for `4il383` (commit identity) and `tkmm5p` (write coalescing, durability, and capture budgets) proposed for maintainer agreement, and `git status -s` is clean of stray or unredacted result files.
  - Execution state: performed

## Project conventions discovered (Step 0)

- `benchmarks/harness.py` is stdlib-only and runs each scenario in a fresh child subprocess across an uncaptured baseline pass plus N measured passes (`pubrun-benchmark/5`), recording `machine.filesystem` via `src/pubrun/capture/filesystem.py::get_filesystem` and redacting hostnames, usernames, and home paths via `benchmarks/harness.py::redact_result` (note: `redact_result` scrubs `~` and `getpass.getuser()` substrings and `_REDACT_KEYS` fields, but does not substring-scrub `platform.node()` or arbitrary non-home `--workdir` paths, so `startup_breakdown.py` must apply stricter redaction and run `benchmarks/share_safety.py::check_share_safe`).
- `benchmarks/scenarios.py::all_scenarios` currently sets `config=_ALL_OFF` (`benchmarks/scenarios.py::_ALL_OFF`) on `import-auto`, `import-nopatch`, and `import-noconsole`, which hides default startup capture costs (such as Git capture and background hardware capture).
- `benchmarks/test_benchmarks.py` validates `pubrun-benchmark/5` results against `schemas/benchmark.schema.json` and is run explicitly with `pytest benchmarks/test_benchmarks.py -o addopts="" -v`; `tests/test_bench_command.py` also imports `benchmarks/scenarios.py::all_scenarios`.
- `benchmarks/workloads/noop.py` provides a near-zero short workload and `benchmarks/workloads/cpu_burn.py` provides a deterministic CPU-bound longer workload.
- `src/pubrun/__init__.py` executes `_resolve_commit()` and `_execute_boot_sequence()` synchronously during `import pubrun`, while `src/pubrun/capture/git.py::get_git` spawns up to five `git` subprocesses only when the working directory is inside a Git repository and `src/pubrun/config.py::resolve_config` loads `~/.config/pubrun/config.toml` (via `XDG_CONFIG_HOME`/`APPDATA`) and `PUBRUN_*` environment variables.
- Existing committed results under `benchmarks/results/` and `benchmarks/data/` are historical single-machine measurements and cannot serve as the baseline for backlog item `t1xqpw` (startup overhead bounding and artifact write coalescing).
- `AGENTS.md` prohibits em dashes and en dashes in user-facing documentation and requires testing observable behavior rather than code structure; `pyproject.toml` supports Python `>=3.8` through `3.14`.

## Findings

- **F-01 (No phase-level startup/finalization breakdown):** `benchmarks/harness.py` times only total child-process wall time. It does not separate Python startup, `import pubrun`, `Run.__init__` capture, user workload, `stop()`/writer finalization, Git subprocess count, serialization time, or artifact write/`fsync` counts.
- **F-02 (No installed-package vs source-checkout comparison):** `benchmarks/harness.py::_build_child_command` injects `PYTHONPATH=<repo>/src`, so it only measures the editable source-checkout path and never isolates an installed-wheel layout (where `pubrun` lives outside a Git checkout or inside a nested user repository).
- **F-03 (Default auto-start startup scenario absent):** `benchmarks/scenarios.py::all_scenarios` measures `import-auto` with `_ALL_OFF`, omitting default capture overhead at startup.

## Proposed changes (ordered, validatable)

1. **`benchmarks/startup_breakdown.py` (new stdlib-only measurement script, Python 3.8+ compatible):**
   - **CLI flags and validation:** Provide `--iterations` (int >= 1, default `15`), `--passes` (int >= 1, default `3`), `--warmup` (int >= 0, default `1`), `--workdir` (optional parent directory for testing local storage or a user-specified shared filesystem mount), `--durability-policies` (comma-separated subset of `default,fsync,finalize,atomic,strict`, defaulting to `"default"` so pre-change code runs cleanly, and supporting `"fsync,finalize,atomic,strict"` once `tkmm5p` lands), and `--out` (optional path for writing a redacted JSON report; stdout prints a concise redacted Markdown summary table). Reject invalid policy names or out-of-range numeric flags with a clear error message and non-zero exit code.
   - **Non-publishing invariant:** Never call `gh`, `git push`, Gist APIs, or batch schedulers (`sbatch`, `qsub`, `bsub`).
   - **Safe workdir handling and child-environment isolation:**
     - Create a dedicated ephemeral subdirectory via `tempfile.TemporaryDirectory(prefix="pubrun-startup-bench-", dir=workdir)` (creating `workdir` only if it does not yet exist, and verifying writability). Clean up ONLY that ephemeral subdirectory on exit so `--workdir` and any pre-existing files inside it are never deleted.
     - Strip inherited `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, `PUBRUN_PROFILE`, and `PUBRUN_META_REF` from child process environments, and point `XDG_CONFIG_HOME` (POSIX) and `APPDATA` (Windows) to an empty directory inside the ephemeral workdir so user-level `~/.config/pubrun/config.toml` never contaminates measurements.
     - For `--durability-policies`: `"default"` writes no `.pubrun.toml` override (measuring built-in defaults); each explicit policy (`"fsync"`, `"finalize"`, `"atomic"`, `"strict"`) writes `[core]\nartifact_durability = "<policy>"\n` into the child scenario's temporary `.pubrun.toml`.
   - **Run context and strict redaction:**
     - Capture run context using `src/pubrun/capture/filesystem.py::get_filesystem({}, paths)` for `workdir`, `tmpdir`, and `pubrun` install location, recording ONLY `fstype` and `is_network` (never emitting raw `path` or `mount_point` fields), alongside OS name/release, Python version, CPU model/core count, and current git commit SHA.
     - Redact all emitted JSON and Markdown text by omitting raw path fields, scrubbing `"hostname"`, `"username"`, `"workdir"`, and all `_REDACT_KEYS` fields, and deep-scrubbing substrings for `platform.node()`, `getpass.getuser()`, `os.path.expanduser("~")`, the resolved `--workdir` path, and the repository root path.
     - Run `benchmarks/share_safety.py::check_share_safe` on the redacted result before writing `--out` or printing stdout; fail closed (non-zero exit, write nothing to `--out`) if the self-check reports any violation.
   - **Isolated layouts and deterministic Git-repo working directory:**
     - **Source-checkout layout:** strip any other `pubrun` path from `PYTHONPATH` and prepend `<repo>/src`.
     - **Installed-package layout:** copy `src/pubrun` into `<ephemeral_workdir>/installed/site-packages/pubrun` with a valid synthetic 40-hex `COMMIT` file and NO `.git` directory in its ancestor chain (verified when `workdir` itself is outside a Git tree; otherwise note ancestor `.git` presence in metadata).
     - **Installed-nested layout:** initialize a small temporary user Git repository at `<ephemeral_workdir>/nested_repo/` (one commit) and copy `src/pubrun` into `<ephemeral_workdir>/nested_repo/.venv/site-packages/pubrun` with a distinct synthetic `COMMIT` file to measure the enclosing-repository import case.
     - **Child layout guard:** each child probe verifies `Path(pubrun.__file__).resolve()` lives under the expected root (`<repo>/src/pubrun` vs the intended isolated `site-packages/pubrun`) and exits non-zero if an editable install shadowed the intended layout.
     - **Auto-run working directory:** initialize a small deterministic temporary Git repository at `<ephemeral_workdir>/sample_repo/` (one tracked file, one commit, one local origin URL) and run `auto-noop-default`, `auto-cpu-burn-default`, and their phased equivalents with `cwd` inside that repository so `src/pubrun/capture/git.py::get_git` executes its real repository path (measuring all pre-change `git` subprocesses) rather than short-circuiting on a non-Git directory.
   - **Clean timing probes vs dedicated instrumented counter probes:**
     - Run wall-clock timing iterations in **uninstrumented** fresh child processes (no pre-imported `subprocess` or `json` wrappers) so instrumentation never masks pre-change `subprocess` import cost or inflates wall-clock timings.
     - Run a dedicated **instrumented counter probe** (per scenario, outside the timed samples) that wraps `subprocess.Popen`, `os.replace`, `os.fsync`, and `json.dump`/`json.dumps` (recording serialization calls attributed to `pubrun.writer`) to collect exact counts and serialization time:
       - `git` subprocess invocations
       - `manifest.json` atomic writes (`os.replace` targeting `manifest.json`)
       - `config.resolved.json` atomic writes (`os.replace` targeting `config.resolved.json`)
       - `os.fsync` calls during startup and finalization
       - JSON serialization time (ms) inside `pubrun.writer`
     - **Scenarios measured across Pass 1 (cold) through Pass N (warm) with `warmup` discarded iterations per pass:**
       1. `bare-python-noop` and `bare-python-cpu-burn`: bare Python running `benchmarks/workloads/noop.py` and `benchmarks/workloads/cpu_burn.py` (cost floors).
       2. `import-minimal-checkout`, `import-minimal-installed`, and `import-minimal-installed-nested`: `import pubrun.minimal` only; records clean wall time (ms) and instrumented `git` subprocess count.
       3. `import-noauto-checkout`, `import-noauto-installed`, and `import-noauto-installed-nested`: `import pubrun.noauto` only; records clean wall time (ms) and instrumented `git` subprocess count.
       4. `auto-noop-default` (short workload) and `auto-cpu-burn-default` (long workload), run per requested durability policy: measures clean end-to-end child wall time for `import pubrun` + workload + exit, AND runs matched phased probes (`import pubrun.noauto` -> `pubrun.start()` -> workload body -> `pubrun.stop()`) using `time.perf_counter()` around each phase to separate (a) package import, (b) startup capture and startup manifest write (`Run.__init__`), (c) workload body, and (d) finalization (`pubrun.stop()`), while recording additive `manifest["timing"]` fields when present (coordinating cleanly with sibling Set `timing-acc`, orchestrator `nr63qr`).
   - **Statistics, small-`n` safety, and failure handling:**
     - For each scenario and each pass (Pass 1 cold through Pass N warm), compute `n`, `failures`, `median_ms`, `mean_ms`, `p95_ms`, `stdev_ms`, and `iqr_ms` (`Q3 - Q1`). Handle small sample counts safely without raising `StatisticsError` (`n == 0` -> `None`; `n == 1` -> `stdev_ms = 0.0`, `iqr_ms = 0.0`, `p95_ms = s[0]`; `n >= 2` -> deterministic sorted percentile/quartile calculation).
     - For `auto-noop-default` and `auto-cpu-burn-default` (per durability policy), compute absolute overhead (ms above matched `bare-python-*` baseline) and relative overhead (% of matched baseline).
     - Record failed child invocations in `failures` and exit non-zero with a clear diagnostic if any scenario finishes a pass with `n == 0` successful samples.
2. **`benchmarks/scenarios.py`:**
   - Add `Scenario("startup-auto-default", "startup", "auto", "noop.py", config={})` right after the `import-<mode>` loop in `benchmarks/scenarios.py::all_scenarios` (Group 1) so `benchmarks/harness.py` tracks default auto-start startup cost without altering any existing scenario definition or breaking `pubrun-benchmark/5` validation.
3. **`benchmarks/README.md`:**
   - Add a concise subsection describing `benchmarks/startup_breakdown.py`, its CLI flags (`--iterations`, `--passes`, `--warmup`, `--workdir`, `--durability-policies`, `--out`), how to test local versus shared storage via `--workdir /path/to/shared/tmp`, cold/warm pass and dispersion reporting, and noting that it is strictly local and non-publishing (with zero em or en dashes in added prose).
4. **`tests/test_startup_benchmark.py`:**
   - Exercise `benchmarks/startup_breakdown.py` with small parameters (`--iterations 2 --passes 2 --warmup 0`, plus `--iterations 1` and invalid CLI flags) and assert on real structured output:
     - Presence of environment metadata (`os`, `python_version`, `git_commit`, `filesystem`) with no raw home path, hostname, or custom `--workdir` path leaked in redacted output, verified by `benchmarks/share_safety.py::check_share_safe`.
     - Presence of cold (pass 1) and warm (pass 2) per-pass statistics (`median_ms`, `mean_ms`, `p95_ms`, `stdev_ms`, `iqr_ms`) and safe handling of `--iterations 1`.
     - Presence of separate import, startup, workload, and finalization timings plus `git` spawn, config write, manifest write, `fsync`, and serialization counters across checkout, installed, and installed-nested layouts.
     - Presence of absolute overhead (ms) and relative overhead (%) for both short (`noop.py`) and long (`cpu_burn.py`) workloads.
     - `--workdir` creates temporary artifacts inside an ephemeral subdirectory under the requested directory, cleans up that subdirectory on exit, and leaves pre-existing sibling files inside `--workdir` intact.
     - Invalid `--durability-policies` or non-positive `--iterations`/`--passes` exit non-zero cleanly.
5. **Pre-change baseline execution and baseline-derived target table:**
   - Run `python benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1` on the unmodified codebase.
   - Paste the complete redacted measurement summary into `V-05`, and record concrete proposed numerical targets derived directly from the measured baseline for maintainer agreement (per backlog item `t1xqpw` Acceptance Criterion #5: structural invariants such as zero `git` spawns on installed `minimal`/`noauto` import and `config.resolved.json` write count dropping from 2-3 to 1 for unchanged config, plus millisecond/percentage reduction targets anchored to the measured baseline rather than invented universal budgets).

## Deferred / out of scope (with reason)

- Modifying any file under `src/pubrun/`, `hatch_build.py`, or `pyproject.toml` is strictly out of scope for this plan so the baseline is guaranteed to reflect unmodified production code (`4il383` owns build-stamped/deferred commit identity and `tkmm5p` owns snapshot write coalescing, durability policy, and bounded capture work).
- Submitting benchmark results to GitHub Issues/Gists or running HPC scheduler scripts (`benchmarks/submit_bench*.sh`) is prohibited without explicit maintainer authorization.
- Updating `docs/performance.md` with before/after tables belongs to child plan `ckc3vl` (post-change overhead comparison and documentation sync) after `4il383` and `tkmm5p` land.

## Scope check

- Over-scope: none. Touches only benchmark measurement tooling, benchmark documentation, and its direct behavioral test file (4 Scope-Paths, 5 E-items).
- Under-scope: none. Covers every pre-change measurement dimension required by backlog item `t1xqpw` (startup overhead bounding and artifact write coalescing), Implementation guidance #1 and Acceptance Criteria #5 and #6.

## Required tests / validation

Run inside the repository root and capture actual runner output and exit codes:

```bash
pytest tests/test_startup_benchmark.py tests/test_bench_command.py -v
pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v
python benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1
```

## Spec / documentation sync

Updates `benchmarks/README.md` for the new measurement script. User-facing performance documentation (`docs/performance.md`) is synchronized by child plan `ckc3vl` (post-change overhead comparison and documentation sync) once post-change measurements are available.

## Open questions

### OQ-01: Default iteration count for local pre-change and post-change breakdown runs

- Blocking: no
- Status: resolved
- Owner: plan author (overridable via CLI flags or upon plan approval)
- Resolution or deferral rationale: Defaulting `benchmarks/startup_breakdown.py` to 3 passes x 15 iterations (+1 discarded warmup per pass) balances statistical stability (capturing pass-1 cold vs pass-3 warm behavior plus stdev and IQR) with reasonable local runtime (~1-2 minutes), while `--iterations` and `--passes` allow larger sweeps on demand.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition)—as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction—name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Diff or file inspection confirming `benchmarks/startup_breakdown.py` is stdlib-only (Python 3.8+ safe), non-publishing, separates clean wall-clock timing probes from instrumented counter/serialization probes, separates import, startup capture, workload, and finalization phases, covers checkout, installed, and installed-nested layouts with `pubrun.__file__` verification and temp Git-repo cwd for auto scenarios, isolates child `PUBRUN_*` and config env vars, cleans up only an ephemeral subdirectory under `--workdir`, runs `benchmarks/share_safety.py::check_share_safe`, and validates CLI flags, plus pasted `python benchmarks/startup_breakdown.py --help` output (exit code 0).
  - Observed evidence:
    Inspected `benchmarks/startup_breakdown.py`: uses stdlib modules only (`from __future__ import annotations`, `typing` generics, Python 3.8+ compatible), performs zero GitHub/Gist/push/scheduler calls, separates uninstrumented wall-clock and phased timing probes from dedicated instrumented counter probes (`subprocess.Popen.__init__`, `os.replace`, `os.fsync`, `json.dump`/`json.dumps` attributed to `pubrun.writer`), verifies `pubrun.__file__` under expected layout roots (`checkout`, `installed`, `installed-nested`), initializes a deterministic temporary Git repo (`sample_repo`) for auto/phased scenarios, strips `PUBRUN_*` and `GIT_*` env vars and isolates `XDG_CONFIG_HOME`/`APPDATA`, creates and removes only `tempfile.TemporaryDirectory(prefix="pubrun-startup-bench-", dir=workdir)`, redacts keys and substrings, validates via `benchmarks/share_safety.py::check_share_safe` failing closed on violations, and validates all CLI flags.
    `python benchmarks/startup_breakdown.py --help` (exit code 0):
    ```text
    usage: startup_breakdown.py [-h] [--iterations ITERATIONS] [--passes PASSES]
                                [--warmup WARMUP] [--workdir WORKDIR]
                                [--durability-policies DURABILITY_POLICIES]
                                [--out OUT]

    Local, non-publishing startup and finalization overhead breakdown benchmark
    for pubrun.

    options:
      -h, --help            show this help message and exit
      --iterations ITERATIONS
                            Measured iterations per scenario per pass (integer >=
                            1, default: 15).
      --passes PASSES       Number of measured passes from Pass 1 (cold) to Pass N
                            (warm) (integer >= 1, default: 3).
      --warmup WARMUP       Discarded warmup iterations before each pass (integer
                            >= 0, default: 1).
      --workdir WORKDIR     Optional parent directory for ephemeral benchmark
                            files (useful for testing local storage vs a shared
                            filesystem mount). Only a dedicated ephemeral
                            subdirectory inside --workdir is created and removed.
      --durability-policies DURABILITY_POLICIES
                            Comma-separated subset of
                            default,fsync,finalize,atomic,strict (default:
                            default).
      --out OUT             Optional path to write the redacted JSON breakdown
                            report.
    ```
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Diff of `benchmarks/scenarios.py` showing `startup-auto-default` added without modifying existing scenarios, plus pasted `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v` and `pytest tests/test_bench_command.py -v` output (exit code 0).
  - Observed evidence:
    `git diff -- benchmarks/scenarios.py`:
    ```diff
    --- a/benchmarks/scenarios.py
    +++ b/benchmarks/scenarios.py
    @@ -82,6 +82,7 @@ def all_scenarios() -> List[Scenario]:
         for mode in ("auto", "noauto", "nopatch", "noconsole", "minimal"):
             S.append(Scenario(f"import-{mode}", "startup", mode, "noop.py",
                               config=_ALL_OFF if mode in ("auto", "nopatch", "noconsole") else {}))
    +    S.append(Scenario("startup-auto-default", "startup", "auto", "noop.py", config={}))
    ```
    `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v` (exit code 0):
    ```text
    collected 26 items
    benchmarks/test_share_safety.py::test_windows_userprofile_path_rejected PASSED [  3%]
    benchmarks/test_share_safety.py::test_unredacted_python_executable_rejected PASSED [  7%]
    benchmarks/test_share_safety.py::test_version_is_exposed PASSED          [ 11%]
    benchmarks/test_share_safety.py::test_text_wrapper_parse_failure PASSED  [ 15%]
    benchmarks/test_share_safety.py::test_redacted_result_is_safe PASSED     [ 19%]
    benchmarks/test_share_safety.py::test_missing_field_is_not_unsafe PASSED [ 23%]
    benchmarks/test_share_safety.py::test_home_path_anywhere_rejected PASSED [ 26%]
    benchmarks/test_share_safety.py::test_text_wrapper_non_object PASSED     [ 30%]
    benchmarks/test_share_safety.py::test_unredacted_hostname_rejected PASSED [ 34%]
    benchmarks/test_benchmarks.py::TestSchema5AggregateParity::test_aggregate_reads_both_versions PASSED [ 38%]
    benchmarks/test_benchmarks.py::TestSchema5AggregateParity::test_parity_from_same_timings PASSED [ 42%]
    benchmarks/test_benchmarks.py::test_bench_pubrun_print SKIPPED (requ...) [ 46%]
    benchmarks/test_benchmarks.py::test_bench_import_pubrun_cost SKIPPED     [ 50%]
    benchmarks/test_benchmarks.py::test_bench_builtin_open_read SKIPPED      [ 53%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_both_timestamps_present PASSED [ 57%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_baseline_same_compact_shape PASSED [ 61%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_schema_is_v5 PASSED [ 65%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_no_stored_stats PASSED [ 69%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_round_trips PASSED [ 73%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_timings_rounded_6dp_and_grouped_by_pass PASSED [ 76%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_scenario_defs_present_and_no_top_scenarios PASSED [ 80%]
    benchmarks/test_benchmarks.py::TestSchema5Shape::test_compact_no_indent PASSED [ 84%]
    benchmarks/test_benchmarks.py::TestSchema5Conformance::test_committed_redacted_sample_conforms PASSED [ 88%]
    benchmarks/test_benchmarks.py::TestSchema5Conformance::test_broken_result_is_rejected PASSED [ 92%]
    benchmarks/test_benchmarks.py::TestSchema5Conformance::test_fresh_result_and_redaction_conform PASSED [ 96%]
    benchmarks/test_benchmarks.py::TestSchema5Conformance::test_schema_is_well_formed PASSED [100%]
    ================== 23 passed, 3 skipped in 240.73s (0:04:00) ===================
    ```
    `pytest tests/test_bench_command.py -v` (exit code 0):
    ```text
    collected 63 items
    tests/test_bench_command.py (63/63 PASSED, including TestRedaction, TestHarnessResolution, TestSlurmSafety, TestSchedulerDetection, TestSchedulerSubmitSafety, TestBenchCLI, TestIoBaselineScenarios, TestSubmissionVerifier, TestAttachFlowSubmitFile, TestAttachFlowClient, TestHarnessRedactedOnlyDefault, TestGistInlineContribution, TestSchema5RawTimings, TestBenchTiers)
    ======================== 63 passed in 125.38s (0:02:05) ========================
    ```
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Diff of `benchmarks/README.md` showing usage documentation for `benchmarks/startup_breakdown.py`, `--workdir` shared-filesystem instructions, cold/warm and dispersion explanation, non-publishing notice, and zero em or en dashes in added lines.
  - Observed evidence:
    `git diff -- benchmarks/README.md` adds the `startup_breakdown.py` bullet under `## Design` and the `### Startup and finalization breakdown` subsection under `## Running` covering CLI flags (`--iterations`, `--passes`, `--warmup`, `--workdir`, `--durability-policies`, `--out`), shared-filesystem `--workdir` usage and ephemeral cleanup, cold/warm passes and dispersion statistics (`median_ms`, `mean_ms`, `p95_ms`, `stdev_ms`, `iqr_ms`), output schema (`pubrun-startup-breakdown/1`), `share_safety.py::check_share_safe` validation, and the explicit local/non-publishing notice.
    Em/en dash check over added lines of `git diff -- benchmarks/README.md` exited 0 with `em/en dashes in README diff: 0`.
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted `pytest tests/test_startup_benchmark.py -v` output showing exit code 0 and all behavioral tests passing (phase breakdown, counters, checkout/installed/nested layouts, cold/warm passes, dispersion stats including `--iterations 1`, redaction and `check_share_safe`, `--workdir` ephemeral cleanup preserving sibling files, and invalid CLI argument rejection).
  - Observed evidence:
    `pytest tests/test_startup_benchmark.py -v` (exit code 0):
    ```text
    collected 15 items
    tests/test_startup_benchmark.py::TestStartupAutoDefaultScenario::test_startup_auto_default_registered PASSED [  6%]
    tests/test_startup_benchmark.py::TestBreakdownStatisticsAndRedaction::test_compute_stats_handles_empty_single_and_multi PASSED [ 13%]
    tests/test_startup_benchmark.py::TestBreakdownStatisticsAndRedaction::test_redact_breakdown_scrubs_home_host_user_workdir_and_repo PASSED [ 20%]
    tests/test_startup_benchmark.py::TestBreakdownStatisticsAndRedaction::test_validate_redacted_output_rejects_leaked_home_path PASSED [ 26%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_invalid_flags_exit_nonzero[extra_args0] PASSED [ 33%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_invalid_flags_exit_nonzero[extra_args1] PASSED [ 40%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_invalid_flags_exit_nonzero[extra_args2] PASSED [ 46%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_invalid_flags_exit_nonzero[extra_args3] PASSED [ 53%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_invalid_flags_exit_nonzero[extra_args4] PASSED [ 60%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_invalid_flags_exit_nonzero[extra_args5] PASSED [ 66%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_invalid_flags_exit_nonzero[extra_args6] PASSED [ 73%]
    tests/test_startup_benchmark.py::TestBreakdownCLIValidation::test_workdir_regular_file_rejected PASSED [ 80%]
    tests/test_startup_benchmark.py::TestBreakdownEndToEnd::test_cli_two_passes_two_iterations_and_workdir_cleanup PASSED [ 86%]
    tests/test_startup_benchmark.py::TestBreakdownEndToEnd::test_cli_single_iteration_and_explicit_durability_policy PASSED [ 93%]
    tests/test_startup_benchmark.py::TestBreakdownEndToEnd::test_cli_does_not_autostart_pubrun_in_caller_cwd_and_accepts_short_relative_workdir PASSED [100%]
    ============================= 15 passed in 38.57s ==============================
    ```
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: Pasted full redacted output of `python benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1` (exit code 0) containing environment, git revision, filesystem type, cold/warm pass medians, mean, p95, stdev, IQR, subprocess/write/fsync/serialization counts, absolute ms and relative overhead % for short (`noop.py`) and long (`cpu_burn.py`) workloads, plus concrete baseline-derived numerical targets proposed for `4il383` and `tkmm5p` and `git status -s` confirming no stray or unredacted result artifacts remain.
  - Observed evidence:
    `python3 benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1` (exit code 0, unmodified `src/pubrun/`, parent process isolated via `pubrun.minimal`):
    ```markdown
    # pubrun Startup and Finalization Breakdown

    ## Environment

    - Schema: `pubrun-startup-breakdown/1`
    - Generated (UTC): `2026-11-22T07:22:00.401613+00:00`
    - Git revision: `d1ba84b55997d9d6cad99830570aadd9b8c41b00`
    - pubrun version: `1.3.1`
    - OS: `Linux 6.8.0-149-generic` (`linux`)
    - Python: `3.14.6`
    - CPU: `Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz` (12 logical cores, `x86_64`)
    - Repetitions: `3` pass(es) x `15` iterations (+`1` warmup per pass)
    - Durability policies: `default`
    - Installed layout ancestor `.git` present: `False`
    - Filesystem (workdir): `ext4` (network=`False`)
    - Filesystem (tmpdir): `ext4` (network=`False`)
    - Filesystem (pubrun_install): `ext4` (network=`False`)

    ## Scenario Wall-Clock Timings (ms)

    | Scenario | Pass | n | Fail | Median (ms) | Mean (ms) | p95 (ms) | Stdev (ms) | IQR (ms) |
    |---|---|---:|---:|---:|---:|---:|---:|---:|
    | `bare-python-noop` | 1 (cold) | 15 | 0 | 15.58 | 16.02 | 18.31 | 1.49 | 2.65 |
    | `bare-python-noop` | 2 (warm) | 15 | 0 | 17.29 | 17.70 | 20.89 | 1.70 | 1.87 |
    | `bare-python-noop` | 3 (warm) | 15 | 0 | 17.34 | 18.22 | 22.75 | 2.48 | 3.40 |
    | `bare-python-cpu-burn` | 1 (cold) | 15 | 0 | 227.57 | 228.73 | 242.22 | 8.37 | 5.30 |
    | `bare-python-cpu-burn` | 2 (warm) | 15 | 0 | 223.63 | 225.90 | 235.46 | 6.92 | 7.16 |
    | `bare-python-cpu-burn` | 3 (warm) | 15 | 0 | 227.82 | 229.07 | 240.08 | 7.06 | 6.08 |
    | `import-minimal-checkout` | 1 (cold) | 15 | 0 | 112.36 | 114.29 | 126.28 | 6.64 | 9.12 |
    | `import-minimal-checkout` | 2 (warm) | 15 | 0 | 112.41 | 113.33 | 120.36 | 5.12 | 9.72 |
    | `import-minimal-checkout` | 3 (warm) | 15 | 0 | 111.19 | 111.65 | 119.32 | 4.32 | 5.72 |
    | `import-minimal-installed` | 1 (cold) | 15 | 0 | 112.19 | 112.78 | 119.75 | 4.22 | 5.76 |
    | `import-minimal-installed` | 2 (warm) | 15 | 0 | 112.47 | 113.00 | 118.92 | 4.05 | 6.74 |
    | `import-minimal-installed` | 3 (warm) | 15 | 0 | 116.59 | 117.43 | 128.67 | 7.24 | 9.79 |
    | `import-minimal-installed-nested` | 1 (cold) | 15 | 0 | 117.75 | 119.22 | 132.70 | 8.08 | 6.22 |
    | `import-minimal-installed-nested` | 2 (warm) | 15 | 0 | 110.60 | 112.52 | 126.95 | 7.05 | 6.80 |
    | `import-minimal-installed-nested` | 3 (warm) | 15 | 0 | 112.88 | 114.07 | 124.84 | 6.54 | 6.87 |
    | `import-noauto-checkout` | 1 (cold) | 15 | 0 | 113.92 | 113.65 | 118.38 | 4.21 | 6.36 |
    | `import-noauto-checkout` | 2 (warm) | 15 | 0 | 112.16 | 112.94 | 119.90 | 4.38 | 5.04 |
    | `import-noauto-checkout` | 3 (warm) | 15 | 0 | 117.27 | 116.17 | 122.98 | 5.14 | 5.83 |
    | `import-noauto-installed` | 1 (cold) | 15 | 0 | 112.14 | 115.26 | 129.84 | 7.05 | 6.39 |
    | `import-noauto-installed` | 2 (warm) | 15 | 0 | 117.20 | 116.35 | 124.17 | 5.33 | 7.08 |
    | `import-noauto-installed` | 3 (warm) | 15 | 0 | 111.54 | 112.94 | 121.70 | 5.30 | 7.06 |
    | `import-noauto-installed-nested` | 1 (cold) | 15 | 0 | 114.97 | 114.60 | 121.42 | 4.39 | 4.40 |
    | `import-noauto-installed-nested` | 2 (warm) | 15 | 0 | 110.77 | 111.66 | 117.68 | 4.18 | 6.64 |
    | `import-noauto-installed-nested` | 3 (warm) | 15 | 0 | 115.41 | 115.51 | 125.63 | 6.67 | 8.80 |
    | `auto-noop-default` | 1 (cold) | 15 | 0 | 495.17 | 496.21 | 515.40 | 9.96 | 8.91 |
    | `auto-noop-default` | 2 (warm) | 15 | 0 | 491.24 | 492.19 | 506.01 | 10.58 | 9.72 |
    | `auto-noop-default` | 3 (warm) | 15 | 0 | 490.10 | 491.30 | 504.07 | 8.64 | 10.42 |
    | `phased-noop-default` | 1 (cold) | 15 | 0 | 509.63 | 514.57 | 554.72 | 17.40 | 9.97 |
    | `phased-noop-default` | 2 (warm) | 15 | 0 | 511.52 | 513.88 | 536.89 | 12.27 | 9.22 |
    | `phased-noop-default` | 3 (warm) | 15 | 0 | 512.10 | 511.91 | 537.99 | 14.26 | 14.27 |
    | `auto-cpu-burn-default` | 1 (cold) | 15 | 0 | 707.40 | 707.15 | 725.54 | 14.69 | 24.95 |
    | `auto-cpu-burn-default` | 2 (warm) | 15 | 0 | 702.11 | 709.38 | 750.75 | 20.19 | 24.66 |
    | `auto-cpu-burn-default` | 3 (warm) | 15 | 0 | 705.09 | 706.37 | 736.98 | 15.92 | 12.42 |
    | `phased-cpu-burn-default` | 1 (cold) | 15 | 0 | 716.79 | 720.22 | 751.33 | 18.80 | 20.56 |
    | `phased-cpu-burn-default` | 2 (warm) | 15 | 0 | 722.11 | 725.21 | 747.93 | 15.48 | 20.67 |
    | `phased-cpu-burn-default` | 3 (warm) | 15 | 0 | 717.41 | 720.06 | 747.49 | 13.71 | 9.93 |

    ## Phase Breakdown (median / IQR in ms)

    | Scenario | Pass | Import (ms) | Startup (ms) | Workload (ms) | Finalization (ms) | In-Process (ms) |
    |---|---|---:|---:|---:|---:|---:|
    | `phased-noop-default` | 1 (cold) | 84.27 / 2.71 | 350.32 / 8.02 | 0.01 / 0.00 | 21.61 / 4.24 | 456.69 / 8.20 |
    | `phased-noop-default` | 2 (warm) | 84.51 / 3.45 | 351.56 / 3.93 | 0.01 / 0.00 | 22.29 / 2.54 | 460.26 / 8.10 |
    | `phased-noop-default` | 3 (warm) | 83.69 / 4.50 | 352.56 / 6.46 | 0.01 / 0.00 | 20.03 / 4.17 | 456.08 / 11.28 |
    | `phased-cpu-burn-default` | 1 (cold) | 82.62 / 4.71 | 351.37 / 6.31 | 215.67 / 8.14 | 15.09 / 5.54 | 665.43 / 17.02 |
    | `phased-cpu-burn-default` | 2 (warm) | 81.78 / 5.17 | 352.17 / 14.71 | 218.09 / 6.00 | 17.96 / 2.69 | 674.26 / 17.59 |
    | `phased-cpu-burn-default` | 3 (warm) | 80.89 / 5.85 | 350.69 / 6.79 | 218.43 / 6.49 | 17.09 / 3.58 | 667.86 / 10.37 |

    ## Instrumented Subprocess, Write, Synchronization, and Serialization Counters

    | Scenario | git spawns | total procs | manifest writes (S/F) | config writes (S/F) | fsync total (S/F) | fsync (ms) | writer JSON calls | writer JSON (ms) |
    |---|---:|---:|---|---|---|---:|---:|---:|
    | `import-minimal-checkout` | 1 | 1 | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0.00 | 0 | 0.00 |
    | `import-minimal-installed` | 1 | 1 | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0.00 | 0 | 0.00 |
    | `import-minimal-installed-nested` | 1 | 1 | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0.00 | 0 | 0.00 |
    | `import-noauto-checkout` | 1 | 1 | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0.00 | 0 | 0.00 |
    | `import-noauto-installed` | 1 | 1 | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0.00 | 0 | 0.00 |
    | `import-noauto-installed-nested` | 1 | 1 | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0.00 | 0 | 0.00 |
    | `auto-noop-default` | 6 | 7 | 2 (1/1) | 2 (1/1) | 4 (2/2) | 24.44 | 4 | 2.69 |
    | `phased-noop-default` | 6 | 7 | 2 (1/1) | 2 (1/1) | 4 (2/2) | 19.52 | 4 | 3.03 |
    | `auto-cpu-burn-default` | 6 | 7 | 3 (2/1) | 3 (1/2) | 6 (3/3) | 34.47 | 6 | 6.17 |
    | `phased-cpu-burn-default` | 6 | 7 | 3 (2/1) | 3 (2/1) | 6 (4/2) | 40.57 | 6 | 3.64 |

    ## Short vs Long Workload Overhead Summary

    | Policy | Workload | Pass | Baseline (ms) | Auto (ms) | Abs Overhead (ms) | Rel Overhead (%) | Import (ms) | Startup (ms) | Finalize (ms) |
    |---|---|---|---:|---:|---:|---:|---:|---:|---:|
    | `default` | `noop.py` (short) | 1 (cold) | 15.58 | 495.17 | 479.59 | 3078.2% | 84.27 | 350.32 | 21.61 |
    | `default` | `noop.py` (short) | 2 (warm) | 17.29 | 491.24 | 473.95 | 2741.8% | 84.51 | 351.56 | 22.29 |
    | `default` | `noop.py` (short) | 3 (warm) | 17.34 | 490.10 | 472.77 | 2726.9% | 83.69 | 352.56 | 20.03 |
    | `default` | `cpu_burn.py` (long) | 1 (cold) | 227.57 | 707.40 | 479.83 | 210.8% | 82.62 | 351.37 | 15.09 |
    | `default` | `cpu_burn.py` (long) | 2 (warm) | 223.63 | 702.11 | 478.48 | 214.0% | 81.78 | 352.17 | 17.96 |
    | `default` | `cpu_burn.py` (long) | 3 (warm) | 227.82 | 705.09 | 477.26 | 209.5% | 80.89 | 350.69 | 17.09 |

    Total benchmark wall time: `165.086` s
    ```

    Proposed baseline-derived numerical targets for maintainer agreement (anchored to Pass 3 warm medians on this Linux ext4 host):

    | Metric | Pre-change baseline (Pass 3 warm) | Proposed target | Owner plan |
    |---|---|---|---|
    | `git_spawns` on `import-{minimal,noauto}-{installed,installed-nested}` | `1` | `0` (exact structural invariant; also `0` on `checkout` before lazy `__commit__` access) | `4il383` |
    | Warm wall median on `import-{minimal,noauto}-{installed,installed-nested}` | `111.54` to `116.59 ms` | `<= 110.0 ms` (reduce by `>= 2 ms` on local ext4 with zero regression; larger gains on Windows/NFS) | `4il383` |
    | `config_writes` for unchanged config (`auto-noop-default` / `auto-cpu-burn-default`) | `2` / `3` | `1` / `1` (exact structural invariant: zero rewrites at hardware refresh or finalization) | `tkmm5p` |
    | `fsync_total` under default `"fsync"` (`auto-noop-default` / `auto-cpu-burn-default`) | `4` / `6` | `3` (`-25%`) / `4` (`-33.3%`) | `tkmm5p` |
    | `writer_json_calls` under default `"fsync"` (`auto-noop-default` / `auto-cpu-burn-default`) | `4` / `6` | `3` / `4` | `tkmm5p` |
    | `git_spawns` on `auto-*` / `phased-*` (source checkout in Git repo) | `6` | `<= 4` (combined `rev-parse` in `get_git` plus lazy `__commit__`) | `4il383` + `tkmm5p` |
    | Finalization median under default `"fsync"` (`phased-noop-default` / `phased-cpu-burn-default`) | `20.03 ms` / `17.09 ms` | `<= 16.0 ms` / `<= 13.7 ms` (`>= 20%` reduction from removing redundant config write + `fsync`) | `tkmm5p` |
    | End-to-end absolute auto overhead under default `"fsync"` (`auto-noop-default` / `auto-cpu-burn-default`) | `472.77 ms` / `477.26 ms` | `<= 457 ms` / `<= 462 ms` (`>= 15 ms` / `>= 3%` reduction on local ext4 without relaxing default durability) | `4il383` + `tkmm5p` |
    | Opt-in `"finalize"` durability `fsync_total` (`fsync_startup` / `fsync_finalization`) | `4` (`2`/`2`) to `6` (`4`/`2`) | `2` (`0`/`2`; `-50%` to `-66.7%`, with in-place `fsync` upgrade of unchanged `config.resolved.json`) | `tkmm5p` |
    | Opt-in `"atomic"` durability `fsync_total` / `fsync_ms` | `4` to `6` / `19.52` to `40.57 ms` | `0` / `0.00 ms` (atomic `os.replace` visibility preserved) | `tkmm5p` |
    | Opt-in `"strict"` durability `fsync_total` | n/a (new) | `>= 4` (file + POSIX parent-directory `fsync`; measured and reported separately) | `tkmm5p` |

    `git status -s` shows only the four declared Scope-Paths (and this plan file) with zero stray or unredacted benchmark files (`benchmarks/README.md`, `benchmarks/scenarios.py`, `benchmarks/startup_breakdown.py`, `tests/test_startup_benchmark.py`), and `python3 scripts/sanitize_paths.py --check --all` exited 0.
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. All open questions (OQ-01) are resolved for review; do not execute until a human approves this plan (`- Status: approved`).
2. Scope fence: this plan declares `benchmarks/startup_breakdown.py`, `benchmarks/scenarios.py`, `benchmarks/README.md`, and `tests/test_startup_benchmark.py` as its Scope-Paths, and keeps `src/pubrun/`, `hatch_build.py`, and `pyproject.toml` unmodified so measurements reflect the pre-change baseline. Any unavoidable out-of-scope edit or unmodified declared path must be justified at finalization via `--scope-reason` or `--scope-ack`; stop and report only for genuinely unsafe conditions (such as an unresolvable concurrent-edit conflict or missing prerequisite).
3. Honesty rule: paste actual runner output and exit codes for `pytest` and `benchmarks/startup_breakdown.py` into `V-*` `Observed evidence:`; never invent measurements or claim speedups.
4. Commit discipline: commit only the files changed for this plan using `aw commit fthyv5 -- <paths>`; never use `git add -A`, `git add .`, or `git commit -a`; never push or submit benchmarks externally without explicit human instruction.
5. Lifecycle transition on completion: when running under an `aw` runner, the runner owns the lifecycle transition via `aw ipd finalize`; when executing manually outside a runner, run `aw ipd lint --phase pre-transition` and, once it passes, finalize through `aw ipd finalize` (never a hand-rolled `git mv` to `executed/`).
