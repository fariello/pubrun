# IPD: Package benchmark core runtime and checkout shims

- Date: 2026-11-27
- Kind: child
- Concern: Backlog item `bej1qz` requirements 1, 2, 3, 4, and 5: the core runtime benchmark modules (`benchmarks/harness.py`, `benchmarks/scenarios.py`, `benchmarks/share_safety.py`, and `benchmarks/workloads/`) live outside `src/pubrun/`, so `hatchling` excludes them from the wheel. Moving them into `src/pubrun/_bench/` requires removing checkout-only assumptions (`_REPO_ROOT / "src"`, `_HERE / "results"`, unconditional Git invocation), preserving Python 3.8+ compatibility and `mypy` cleanliness across Linux, Windows, and macOS, and keeping source-checkout entry points working without triggering `pubrun` auto-start side effects.
- Scope: Create the internal standard-library subpackage `src/pubrun/_bench/` (`__init__.py`, `share_safety.py`, `scenarios.py`, `harness.py`, and `workloads/`), convert `benchmarks/share_safety.py`, `benchmarks/scenarios.py`, `benchmarks/harness.py`, and `benchmarks/workloads/` into checkout shims, and update `benchmarks/startup_breakdown.py` to locate the canonical packaged workloads.
- Scope-Paths: src/pubrun/_bench, benchmarks/share_safety.py, benchmarks/scenarios.py, benchmarks/harness.py, benchmarks/workloads, benchmarks/startup_breakdown.py
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: complex
- Short-Description: Create src/pubrun/_bench core runtime modules and workloads and add checkout shims under benchmarks/
- Work-Kind: bug
- Priority: high
- From-Backlog: bej1qz
- Blocks-Release: g2qtg5
- Set: bej1qz
- Order: 1
- Highest E allocated: 05
- Author: Antigravity
- Id: 29nsim
- Approval: 2026-11-27, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 approved (aw set): status set to approved
- 2026-11-27 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006; review record `.aw/records/reviews/20261127-bej1qz-01-29nsim-package-benchmark-core-runtime-and-checkout-shims.review.md`.
- 2026-11-27 to-review (aw set): demoted approved -> to-review: APPROVAL WITHDRAWN: Demote to to-review so /plan-review writes Readiness attestations before execution
- 2026-11-27 approved (aw set): status set to approved
- 2026-11-27 to-review (aw set): Authored review-ready child plan from backlog item bej1qz
- 2026-11-27 draft (Antigravity): created.

## Goal

Package the Python standard-library benchmark runtime (`share_safety.py`, `scenarios.py`, `harness.py`, and `workloads/`) inside `src/pubrun/_bench/` so wheel installations include it automatically via `pyproject.toml`, while keeping every direct source-checkout invocation (`benchmarks/harness.py`, `benchmarks/share_safety.py`, `benchmarks/scenarios.py`, `benchmarks/workloads/`, `benchmarks/startup_breakdown.py`, and `.github/scripts/validate_benchmark_submission.py`) working with a single canonical implementation and no unintended `pubrun` auto-start.

### Packaged runtime and checkout shim layout

```mermaid
classDiagram
    class bench_init["src/pubrun/_bench/__init__.py"] {
        +find_checkout_root()
        +_package_checkout_root()
        +default_results_dir()
        +get_workload_path(name)
        +get_submit_script_path(name)
    }
    class bench_share["src/pubrun/_bench/share_safety.py"] {
        +SHARE_SAFETY_VERSION
        +check_share_safe(result)
        +check_share_safe_text(text)
    }
    class bench_scenarios["src/pubrun/_bench/scenarios.py"] {
        +Scenario
        +all_scenarios()
    }
    class bench_harness["src/pubrun/_bench/harness.py"] {
        +run(...)
        +redact_result(result)
        +main()
    }
    class bench_workloads["src/pubrun/_bench/workloads/"] {
        noop.py
        cpu_burn.py
        file_read.py
        io_sink.py
        print_loop.py
    }
    class checkout_shims["benchmarks/ checkout shims"] {
        harness.py
        scenarios.py
        share_safety.py
        workloads/
    }
    class startup_breakdown["benchmarks/startup_breakdown.py"] {
        noop_path
        cpu_burn_path
    }
    bench_harness --> bench_init : resolves results dir and checkout root
    bench_harness --> bench_scenarios : imports scenarios
    bench_harness --> bench_share : runs redaction self-check
    bench_harness --> bench_workloads : executes per-scenario scripts
    checkout_shims --> bench_harness : proxies CLI and helpers after pubrun.minimal
    checkout_shims --> bench_share : loads by file path without pubrun boot
    checkout_shims --> bench_scenarios : loads by file path without pubrun boot
    checkout_shims --> bench_workloads : loads by file path without pubrun boot
    startup_breakdown --> bench_workloads : locates canonical packaged workloads
    startup_breakdown --> checkout_shims : imports share_safety shim
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Create packaged helpers, share-safety, scenarios, and workloads

- [ ] E-01 Create `src/pubrun/_bench/__init__.py`, `src/pubrun/_bench/share_safety.py`, and `src/pubrun/_bench/scenarios.py`:
  - In `src/pubrun/_bench/__init__.py`, keep imports standard-library only and side-effect free (must never import `pubrun.core` or select an import mode, so `tests/test_report_subpackage_integrity.py::test_no_mode_module_shadows_a_pubrun_subpackage` passes under every import mode). Provide typed helpers using Python 3.8-compatible `typing` annotations:
    - `find_checkout_root(start: Optional[Path] = None) -> Optional[Path]`: inspect `start` (default `Path.cwd()`) and its parent directories, returning the first directory that contains `benchmarks/harness.py` and a `pyproject.toml` declaring `name = "pubrun"` (verified lazily via `pubrun._pyproject_declares_pubrun`). Return `None` when `start` is outside a verified checkout, even if `pubrun` itself is imported from an editable `<repo>/src/pubrun` checkout.
    - `_package_checkout_root() -> Optional[Path]`: check whether the `pubrun` package directory (`Path(__file__).resolve().parents[1]`) lives inside a verified `pubrun` source checkout (via `pubrun._is_verified_source_checkout`), returning `None` for wheel installations in `site-packages`.
    - `default_results_dir(cwd: Optional[Path] = None) -> Path`: honor the `PUBRUN_RESULTS_DIR` environment variable when set and non-empty; otherwise call `find_checkout_root(cwd)` and return `<checkout_root>/benchmarks/results` when a checkout root is found and `(checkout_root / "benchmarks").is_dir()`; otherwise return `(cwd or Path.cwd()) / "pubrun-bench-results"`.
    - `get_workload_path(filename: str) -> Path`: return `Path(__file__).resolve().parent / "workloads" / filename`.
    - `get_submit_script_path(filename: str) -> Path`: return `Path(__file__).resolve().parent / "scripts" / filename`.
  - Move the canonical structural validator from `benchmarks/share_safety.py` into `src/pubrun/_bench/share_safety.py`, keeping it standard-library only, Python 3.8+ compatible, and `mypy`-clean, and updating its module docstring to reflect that it is packaged inside `pubrun._bench` and shared by the command-line interface (CLI) and the GitHub Actions intake validator.
  - Move the canonical scenario definitions from `benchmarks/scenarios.py` into `src/pubrun/_bench/scenarios.py`, keeping it standard-library only, Python 3.8+ compatible, and `mypy`-clean.
  - Depends on: none
  - Expected outcome: `src/pubrun/_bench/__init__.py`, `src/pubrun/_bench/share_safety.py`, and `src/pubrun/_bench/scenarios.py` exist, import cleanly with zero third-party dependencies, implement working-directory vs package-checkout separation accurately, and pass `mypy`.
  - Execution state: pending

- [ ] E-02 Move the five runtime workloads into `src/pubrun/_bench/workloads/`:
  - Create empty `src/pubrun/_bench/workloads/__init__.py`.
  - Copy `noop.py`, `cpu_burn.py`, `file_read.py`, `io_sink.py`, and `print_loop.py` from `benchmarks/workloads/` into `src/pubrun/_bench/workloads/`.
  - Keep `noop.py` completely free of imports (`if __name__ == "__main__": pass`) and ensure all five files remain Python 3.8+ compatible, standard-library only (with lazy `import pubrun` in `file_read.py` only for non-baseline modes), and `mypy`-clean across Linux, `win32`, and `darwin` (annotating mutated dict/optional locals such as `path: Optional[str]`, `record: Optional[Dict[str, Any]]`, and `result: Dict[str, Any]` in `file_read.py::measure_detail` where needed).
  - Depends on: E-01
  - Expected outcome: All five workloads live under `src/pubrun/_bench/workloads/` alongside `__init__.py` and pass `mypy` on all three platforms.
  - Execution state: pending

### Task group 2: Create packaged benchmark harness

- [ ] E-03 Create `src/pubrun/_bench/harness.py` from `benchmarks/harness.py` and remove source-checkout assumptions:
  - Import `platform` at module top level (fixing the unimported `platform.node()` call in `redact_result` so hostname scrubbing works and `mypy` passes).
  - Replace the `sys.path.insert` sibling imports with `from pubrun._bench import scenarios as _scenarios`, `from pubrun._bench import share_safety as _ss`, and `from pubrun._bench import _package_checkout_root, default_results_dir, find_checkout_root, get_workload_path`.
  - In `_build_child_command` and `_run_baseline_pass`, resolve `workload_path = get_workload_path(scn.workload)`. Prepend `<checkout_root>/src` to child `PYTHONPATH` only when `(_package_checkout_root() or find_checkout_root())` returns a path whose `src/` directory exists; in a wheel installation outside a checkout, inherit the caller's environment without adding a bogus `PYTHONPATH` entry.
  - In `_git_commit()`, run `git rev-parse --short HEAD` only when `find_checkout_root()` returns a path; return `None` with zero `git` subprocess spawns outside a checkout or in a wheel installation.
  - Update `_filesystem_context(results_dir: Optional[Path] = None)` to probe the actual target `results_dir` (defaulting to `default_results_dir()`) instead of `Path(__file__).resolve().parent / "results"`. Add an optional `results_dir: Optional[Path] = None` parameter to `run()` (defaulting to `Path(out_path).parent` when `out_path` is provided, else `None`), and in `main()` compute `red_path` before calling `run(...)` so `main()` passes `results_dir=red_path.parent` to `run(...)`.
  - Update `_default_out()` to place default output under `default_results_dir()` rather than `_HERE / "results"`, and update the module docstring and `--redacted-out` CLI help text to document `python -m pubrun._bench.harness` and the default writable results directory rather than `benchmarks/harness.py`, `pip install -e .`, and `results/`.
  - In `main()`, always execute `_ss.check_share_safe(redacted)` directly (no optional `ImportError` bypass) and verify `python -m pubrun._bench.harness` exits `0` from any working directory without auto-starting a tracked run (already guarded by `src/pubrun/core.py::_is_pubrun_cli_invocation` because `mod_name` starts with `"pubrun."`).
  - Ensure all type annotations are `mypy`-clean on Linux, `win32`, and `darwin` (and compatible with Python 3.8 via `from __future__ import annotations` and `typing` imports, including `result: Dict[str, Any]` in `run()`).
  - Depends on: E-01, E-02
  - Expected outcome: `src/pubrun/_bench/harness.py` runs via `python3 -m pubrun._bench.harness` from any working directory, writes a share-safe redacted JavaScript Object Notation (JSON) file to `default_results_dir()` (or `--redacted-out`), probes the real target results directory, and passes `mypy`.
  - Execution state: pending

### Task group 3: Convert checkout files to shims and update startup breakdown

- [ ] E-04 Convert `benchmarks/share_safety.py`, `benchmarks/scenarios.py`, `benchmarks/harness.py`, and `benchmarks/workloads/` into source-checkout compatibility shims and update `benchmarks/startup_breakdown.py`:
  - `benchmarks/share_safety.py`: load `src/pubrun/_bench/share_safety.py` directly by file path (`importlib.util.spec_from_file_location`) or reuse `sys.modules["pubrun._bench.share_safety"]` when already loaded. Do NOT trigger `import pubrun` in this shim, so `.github/scripts/validate_benchmark_submission.py` (which runs in Continuous Integration (CI) with only `jsonschema` installed and without `pubrun` installed), `benchmarks/startup_breakdown.py`, and `benchmarks/test_share_safety.py` work with zero auto-start side effects. When `sys.modules.get(__name__)` is registered, attach a `types.ModuleType` proxy subclass that forwards `__getattr__`, `__setattr__`, `__delattr__`, and `__dir__` to the canonical target module and exposes a `_rebind_shim_target(mod)` helper; when not registered in `sys.modules`, populate `globals()` with the target's non-dunder attributes (including `_HOME_PATH_RE`, `SHARE_SAFETY_VERSION`, `REDACTED`, `check_share_safe`, `check_share_safe_text`).
  - `benchmarks/scenarios.py`: load `src/pubrun/_bench/scenarios.py` directly by file path (or reuse `sys.modules["pubrun._bench.scenarios"]` when already loaded) without triggering `import pubrun`, re-exporting `Scenario`, `all_scenarios`, and module helpers (registering the temporary module in `sys.modules` during `exec_module` so Python 3.12+ `@dataclass` resolves `cls.__module__`).
  - `benchmarks/harness.py`: preserve executable mode where present; at module top level prepend `_REPO_ROOT / "src"` to `sys.path` if `pubrun` is not already importable and immediately run `if "pubrun" not in sys.modules: import pubrun.minimal` **before** importing `pubrun._bench.harness` or `pubrun._bench.share_safety`, so neither `python benchmarks/harness.py` nor importing the shim ever triggers `pubrun` auto-start. If `sys.modules.get("share_safety")` is the checkout shim exposing `_rebind_shim_target`, call `_rebind_shim_target(pubrun._bench.share_safety)` so `monkeypatch.setattr(ss, "check_share_safe", ...)` in `tests/test_benchmark_intake_bugs.py::TestHarnessSelfCheckGate` targets the same module object that `pubrun._bench.harness.main()` calls. When `__name__ != "__main__"` and `sys.modules.get(__name__)` is registered, attach a `types.ModuleType` proxy subclass forwarding `__getattr__`, `__setattr__`, `__delattr__`, and `__dir__` to `pubrun._bench.harness` so `monkeypatch.setattr(h, "run", ...)` and `monkeypatch.setattr(h, "redact_result", ...)` target `pubrun._bench.harness` directly; when not registered in `sys.modules` (such as `tests/test_bench_command.py::_load_harness`), copy non-dunder attributes (including `run`, `redact_result`, `_stats`, `_TIERS`, `_scrub_pii_substrings`, `main`, `_default_out`, `_default_redacted_out`) into `globals()`. Inside `if __name__ == "__main__":`, call `pubrun._bench.harness.main()`.
  - `benchmarks/workloads/`: keep `noop.py` as the zero-import `if __name__ == "__main__": pass` stub; convert `cpu_burn.py`, `file_read.py`, `io_sink.py`, and `print_loop.py` to thin checkout shims (preserving executable mode where present) that load `src/pubrun/_bench/workloads/<name>.py` directly by file path (`importlib.util.spec_from_file_location`, without importing `pubrun`), copy its non-dunder attributes into `globals()`, and forward `if __name__ == "__main__":` execution (`sys.exit(main())` for `file_read.py`, `_work()` for the others) so both direct CLI execution (such as `file_read.py --measure-detail`) and `importlib` loading of `_work()` / `measure_detail()` work with zero unintended `pubrun` boot.
  - `benchmarks/startup_breakdown.py`: resolve `noop_path` and `cpu_burn_path` from `_SRC_ROOT / "pubrun" / "_bench" / "workloads"` (with fallback to `_HERE / "workloads"`) so breakdown measurements execute the canonical packaged workloads directly.
  - Depends on: E-01, E-02, E-03
  - Expected outcome: Single canonical source in `src/pubrun/_bench/`; direct checkout invocations, existing test suites (`tests/test_benchmark_intake_bugs.py`, `tests/test_bench_command.py`, `tests/test_startup_benchmark.py`, `benchmarks/test_benchmarks.py`), and CI validation scripts without `pubrun` installed all work without auto-starting a tracked run.
  - Execution state: pending

### Task group 4: Verify core runtime, shims, typing, and integrity tests

- [ ] E-05 Run all verification checks listed in `## Required tests / validation`:
  - Run `mypy`, `mypy --platform win32`, and `mypy --platform darwin`.
  - Run `pubrun._bench` helper unit check (`find_checkout_root`, `_package_checkout_root`, `default_results_dir` under `PUBRUN_RESULTS_DIR`, checkout cwd, and outside-checkout cwd, plus `get_workload_path` and `get_submit_script_path`) and workload shim check (`benchmarks/workloads/file_read.py --measure-detail` in `baseline` mode without importing `pubrun`).
  - Run targeted regression tests covering subpackage integrity, `share_safety`, CI intake validator, intake bug regression tests (`TestHarnessSelfCheckGate`), security hardening, startup breakdown, package benchmark scenarios, and non-slow `benchmarks/test_benchmarks.py` / `tests/test_bench_command.py` suites.
  - Verify `benchmarks/share_safety.py` loads in an isolated Python subprocess with `PYTHONPATH=""` and without `pubrun` imported (`"pubrun" not in sys.modules`), matching `.github/workflows/benchmark-intake.yml`.
  - Run a smoke invocation of `python3 -m pubrun._bench.harness --iterations 1 --passes 1 --no-baseline` from a temporary directory outside the repository (with ambient `PUBRUN_*` stripped) and confirm it writes a share-safe redacted JSON file under `<tmp>/pubrun-bench-results/` without creating a `runs/` directory in `<tmp>` or writing into `<repo>/benchmarks/results/`.
  - Run a smoke invocation of `python3 benchmarks/harness.py --iterations 1 --passes 1 --no-baseline --redacted-out <tmp>/checkout.redacted.json` (with ambient `PUBRUN_*` stripped and `cwd` isolated) and verify it exits `0`, writes a share-safe file, and creates no `runs/` directory.
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: Every check exits `0` with expected behavior, zero regressions, and zero stray temporary directories or checkout artifacts.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `pyproject.toml` sets `[tool.hatch.build.targets.wheel] packages = ["src/pubrun"]`, so every file inside `src/pubrun/_bench/` is automatically included in both the wheel and sdist (`[tool.hatch.build.targets.sdist]` includes `"/src"`), while `benchmarks/` remains outside the wheel.
- `pyproject.toml` configures `[tool.mypy] files = ["src/pubrun"]`, and `.github/workflows/ci.yml` runs `mypy`, `mypy --platform win32`, and `mypy --platform darwin`; every `.py` module placed under `src/pubrun/_bench/` must therefore pass cross-platform `mypy`.
- `tests/test_report_subpackage_integrity.py::test_no_mode_module_shadows_a_pubrun_subpackage` discovers every subpackage via `pkgutil.iter_modules(pubrun.__path__)` and imports `pubrun.<name>` under all six import modes (`auto`, `noauto`, `full`, `nopatch`, `noconsole`, `minimal`); `src/pubrun/_bench/__init__.py` must remain lightweight and side-effect free.
- `src/pubrun/core.py::_is_pubrun_cli_invocation` already returns `True` when invoked via `python -m <mod>` for any module name starting with `"pubrun."` (`_is_pubrun_module_name`), preventing auto-start for `python -m pubrun._bench.harness`, whereas direct script execution (`python benchmarks/harness.py`) is not recognized as a `-m pubrun.*` invocation and therefore requires `if "pubrun" not in sys.modules: import pubrun.minimal` before importing `pubrun._bench.harness`.
- `.github/workflows/benchmark-intake.yml` installs only `jsonschema` (not `pubrun`) and runs `.github/scripts/validate_benchmark_submission.py`, which imports `benchmarks/share_safety.py` via `sys.path.insert(0, str(_REPO / "benchmarks"))`.
- `benchmarks/startup_breakdown.py` imports `share_safety` (accessing `check_share_safe` and `_HOME_PATH_RE`) and executes `workloads/noop.py` and `workloads/cpu_burn.py`.
- `tests/test_benchmark_intake_bugs.py::TestHarnessSelfCheckGate` loads `benchmarks/share_safety.py` (`ss`) and `benchmarks/harness.py` (`h`) via `spec_from_file_location` and monkeypatches `h.run`, `h.redact_result`, and `ss.check_share_safe`; keeping the checkout shims transparent to `setattr` keeps this suite green before Order 05 (`1r585o`) updates it.
- `benchmarks/harness.py::redact_result` currently references `platform.node()` without a top-level `import platform` (silently swallowed by `except Exception: pass`); moving it under `src/pubrun/` surfaces this under `mypy` and fixing it restores hostname substring scrubbing.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| F-01 | High | Medium | End User | `pyproject.toml` (`[tool.hatch.build.targets.wheel]`) vs `benchmarks/harness.py` | Runtime benchmark files live in `benchmarks/`, which is excluded from the wheel. |
| F-02 | Medium | Low | Maintainer | `benchmarks/harness.py::_build_child_command`, `_git_commit`, `_filesystem_context`, `_default_out` | Harness assumes a writable checkout tree (`_REPO_ROOT / "src"`, `_HERE / "results"`, Git repo at `_REPO_ROOT`). |
| F-03 | Medium | Low | Security / CI | `.github/workflows/benchmark-intake.yml` vs `.github/scripts/validate_benchmark_submission.py` | Intake CI imports `benchmarks/share_safety.py` without installing `pubrun`, so the checkout shim must not require `import pubrun`. |
| F-04 | Low | Low | Maintainer | `benchmarks/harness.py::redact_result` | `platform.node()` is called without top-level `import platform`, which silently fails at runtime and fails `mypy` inside `src/pubrun/`. |

## Proposed changes (ordered, validatable)

1. Create `src/pubrun/_bench/__init__.py` (separating working-directory `find_checkout_root()` from package-install `_package_checkout_root()`), `src/pubrun/_bench/share_safety.py`, and `src/pubrun/_bench/scenarios.py` (E-01; Remediation Risk: Low).
2. Move runtime workloads into `src/pubrun/_bench/workloads/` with `__init__.py` and cross-platform `mypy` cleanliness (E-02; Remediation Risk: Low).
3. Create `src/pubrun/_bench/harness.py` with checkout-free runtime resolution, writable default output directory, propagated `_filesystem_context(results_dir)`, top-level `import platform`, updated CLI help/docstring, and direct `share_safety` import (E-03; Remediation Risk: Medium).
4. Convert `benchmarks/{share_safety,scenarios,harness}.py` and `benchmarks/workloads/` into monkeypatch-transparent, auto-start-safe checkout shims and update `benchmarks/startup_breakdown.py` (E-04; Remediation Risk: Low).
5. Verify with cross-platform `mypy`, helper and workload shim checks, targeted regression suites, `share_safety` isolation check, and both module and checkout harness smoke runs (E-05; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Packaging the five high-performance computing (HPC) submission scripts (`run_bench.sbatch`, `submit_bench*.sh`) is deferred to child `c1zz3x` (Order 02) to keep Scope-Paths bounded.
  - Carrier: c1zz3x
- Wiring `src/pubrun/__main__.py` to `src/pubrun/_bench` and removing `_verify_redacted` is deferred to child `mfeptf` (Order 03).
  - Carrier: mfeptf
- Updating documentation is deferred to child `cuboum` (Order 04).
  - Carrier: cuboum
- Updating `tests/test_bench_command.py`, `tests/test_benchmark_intake_bugs.py`, `.github/workflows/ci.yml`, and running end-to-end wheel tests is deferred to child `1r585o` (Order 05).
  - Carrier: 1r585o

## Scope check

- Over-scope: none. Only the core runtime subpackage `src/pubrun/_bench/` and its direct checkout shims (`benchmarks/{share_safety,scenarios,harness}.py`, `benchmarks/workloads/`, `benchmarks/startup_breakdown.py`) are touched.
- Under-scope: none. All Python runtime benchmark files named in backlog item `bej1qz` requirement 1 are packaged here, and non-runtime files in `benchmarks/` stay out of `src/pubrun/`.

## Required tests / validation

1. **Cross-platform static type checking** (must exit `0` with 0 errors):

   ```sh
   mypy && mypy --platform win32 && mypy --platform darwin
   ```

2. **Packaged helper behavior and workload checkout shim check** (must exit `0` and print `ok`):

   ```sh
   PYTHONPATH=src python3 -c 'import json, os, subprocess, sys, tempfile; from pathlib import Path; import pubrun.minimal; import pubrun._bench as b; repo = Path.cwd().resolve(); assert b.find_checkout_root(repo) == repo; assert b._package_checkout_root() == repo; assert b.get_workload_path("noop.py").is_file(); assert b.get_submit_script_path("submit_bench.sh").name == "submit_bench.sh"; os.environ.pop("PUBRUN_RESULTS_DIR", None); assert b.default_results_dir(repo) == repo / "benchmarks" / "results"; td_ctx = tempfile.TemporaryDirectory(prefix="pubrun-bench-helpers-"); td = Path(td_ctx.name); assert b.find_checkout_root(td) is None; assert b.default_results_dir(td) == td / "pubrun-bench-results"; os.environ["PUBRUN_RESULTS_DIR"] = str(td / "custom"); assert b.default_results_dir(repo) == td / "custom"; os.environ.pop("PUBRUN_RESULTS_DIR", None); proc = subprocess.run([sys.executable, "benchmarks/workloads/file_read.py", "--measure-detail"], env={**{k: v for k, v in os.environ.items() if not k.startswith("PUBRUN_")}, "PUBRUN_BENCH_FILE_MODE": "baseline", "PUBRUN_BENCH_FILE_BYTES": "65536"}, capture_output=True, text=True, check=True); data = json.loads(proc.stdout); assert data["mode"] == "baseline" and data["file_bytes"] == 65536; td_ctx.cleanup(); print("ok")'
   ```

3. **Subpackage integrity, share-safety, intake validator, startup breakdown, and benchmark shim regression tests** (must exit `0`):

   ```sh
   pytest tests/test_report_subpackage_integrity.py tests/test_benchmark_intake_bugs.py tests/test_security_hardening.py tests/test_startup_benchmark.py::TestStartupAutoDefaultScenario tests/test_startup_benchmark.py::TestBreakdownStatisticsAndRedaction tests/test_startup_benchmark.py::TestBreakdownEndToEnd::test_cli_single_iteration_and_explicit_durability_policy tests/test_package_benchmark.py tests/test_bench_command.py::TestRedaction tests/test_bench_command.py::TestIoBaselineScenarios tests/test_bench_command.py::TestSchema5RawTimings benchmarks/test_share_safety.py benchmarks/test_benchmarks.py .github/scripts/ -m "not slow" -v
   ```

4. **Zero-`pubrun`-import checkout shim check for `benchmarks/share_safety.py`** (must exit `0` and print `ok`):

   ```sh
   PYTHONPATH="" python3 -c 'import sys; sys.path.insert(0, "benchmarks"); import share_safety; assert "pubrun" not in sys.modules; ok, reasons = share_safety.check_share_safe({"machine": {"host": {"hostname": "<redacted>"}}}); assert ok and not reasons; print("ok")'
   ```

5. **Non-checkout packaged harness execution check** (run from a temporary directory outside the repository with ambient `PUBRUN_*` stripped; must exit `0`, create `<tmp>/pubrun-bench-results/*.redacted.json`, pass `check_share_safe_text`, not create `<tmp>/runs`, and clean up `<tmp>`):

   ```sh
   python3 -c 'import os, subprocess, sys, tempfile; from pathlib import Path; src = str(Path("src").resolve()); sys.path.insert(0, src); import pubrun.minimal; from pubrun._bench.share_safety import check_share_safe_text; env = {k: v for k, v in os.environ.items() if not k.startswith("PUBRUN_")}; env["PYTHONPATH"] = src; td_ctx = tempfile.TemporaryDirectory(prefix="pubrun-bench-smoke-"); td = Path(td_ctx.name); proc = subprocess.run([sys.executable, "-m", "pubrun._bench.harness", "--iterations", "1", "--passes", "1", "--no-baseline"], cwd=str(td), env=env, capture_output=True, text=True, timeout=180); print("rc=", proc.returncode); print(proc.stderr[-500:]); files = list((td / "pubrun-bench-results").glob("*.redacted.json")); print("files=", [f.name for f in files]); print("runs_exists=", (td / "runs").exists()); assert proc.returncode == 0 and len(files) == 1 and not (td / "runs").exists(); ok, reasons = check_share_safe_text(files[0].read_text(encoding="utf-8")); print("share_safe=", ok, reasons); assert ok and not reasons; td_ctx.cleanup()'
   ```

6. **Direct source-checkout `benchmarks/harness.py` smoke check** (with ambient `PUBRUN_*` stripped and isolated `cwd`; must exit `0`, write a share-safe redacted file, create no `runs/` directory, and clean up `<tmp>`):

   ```sh
   python3 -c 'import os, subprocess, sys, tempfile; from pathlib import Path; harness = str(Path("benchmarks/harness.py").resolve()); src = str(Path("src").resolve()); sys.path.insert(0, src); import pubrun.minimal; from pubrun._bench.share_safety import check_share_safe_text; env = {k: v for k, v in os.environ.items() if not k.startswith("PUBRUN_")}; env.pop("PYTHONPATH", None); td_ctx = tempfile.TemporaryDirectory(prefix="pubrun-checkout-smoke-"); td = Path(td_ctx.name); out = td / "out.redacted.json"; proc = subprocess.run([sys.executable, harness, "--iterations", "1", "--passes", "1", "--no-baseline", "--redacted-out", str(out)], cwd=str(td), env=env, capture_output=True, text=True, timeout=180); print("rc=", proc.returncode, "exists=", out.is_file(), "runs_exists=", (td / "runs").exists()); assert proc.returncode == 0 and out.is_file() and not (td / "runs").exists(); ok, reasons = check_share_safe_text(out.read_text(encoding="utf-8")); print("share_safe=", ok, reasons); assert ok and not reasons; td_ctx.cleanup()'
   ```

## Spec / documentation sync

N/A for this child plan; child `cuboum` (Order 04) updates all user-facing and benchmark documentation after `c1zz3x` and `mfeptf` land.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition)—as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction—name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted file listing of `src/pubrun/_bench/{__init__,share_safety,scenarios}.py`, pasted output of validation command 1 (`mypy && mypy --platform win32 && mypy --platform darwin`) and `pytest tests/test_report_subpackage_integrity.py -v` exiting `0`, plus pasted output of validation command 2 confirming `pubrun._bench` helper behavior (`find_checkout_root`, `_package_checkout_root`, `default_results_dir`, `get_workload_path`, `get_submit_script_path`, created by E-01).
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted file listing of `src/pubrun/_bench/workloads/` showing `__init__.py` and all five workload scripts (`noop.py`, `cpu_burn.py`, `file_read.py`, `io_sink.py`, `print_loop.py`), pasted content of `src/pubrun/_bench/workloads/noop.py` confirming zero imports, and pasted output of validation command 1 (`mypy` across all three platforms) exiting `0`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted output of validation command 5 (`python3 -m pubrun._bench.harness --iterations 1 --passes 1 --no-baseline` run from an outside temp dir via `src/pubrun/_bench/harness.py::main`, created by E-03) showing `rc= 0`, one `*.redacted.json` file under `pubrun-bench-results/`, `runs_exists= False`, and `share_safe= True []`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted output of validation commands 2, 3, 4, and 6 showing the `benchmarks/workloads/file_read.py --measure-detail` shim passing, `benchmarks/test_share_safety.py`, `benchmarks/test_benchmarks.py`, `tests/test_benchmark_intake_bugs.py`, `tests/test_startup_benchmark.py` (including `benchmarks/startup_breakdown.py` updated by E-04), and `.github/scripts/` passing, `benchmarks/share_safety.py` loading with `PYTHONPATH=""` and `"pubrun" not in sys.modules`, and `python3 benchmarks/harness.py` (delegating to `src/pubrun/_bench/harness.py::main` created by E-03/E-04) exiting `0` with `runs_exists= False` and `share_safe= True []`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted output of all six commands in `## Required tests / validation` exiting `0`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Preconditions:** Execute E-01 through E-05 only after this plan carries `- Status: approved` and all blocking open questions are resolved.
2. **Scope declaration:** `- Scope-Paths:` declares the authorized file set (`src/pubrun/_bench, benchmarks/share_safety.py, benchmarks/scenarios.py, benchmarks/harness.py, benchmarks/workloads, benchmarks/startup_breakdown.py`). If execution requires modifying a path outside `- Scope-Paths:` or leaving a declared path unmodified, justify each exception explicitly with `--scope-reason` or `--scope-ack` at finalize rather than silently deviating.
3. **Validation honesty:** Every `V-*` item MUST paste the actual command runner output captured during execution; never mark any `V-*` item `pass` without running the corresponding command and observing its exit code and output.
4. **Commit and push discipline:** Commit only paths modified for this plan through `aw commit 29nsim -- <paths>`. Never use `git add -A`, bare `git add .`, or raw `git commit`, and never push, tag, or publish without explicit human authorization.
5. **Lifecycle transition:** After all `E-*` items are `performed` and all `V-*` items are `pass`, the plan MUST complete the post-gate transition to `.aw/records/plans/executed/`. When executing under an automated runner (`aw oc run` or `aw agy run`), leave finalization to the runner's post-turn finalize step; in a manual or interactive execution outside a runner, run `aw ipd finalize 29nsim` (never hand-roll `git mv` to `executed/`).
