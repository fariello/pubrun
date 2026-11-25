# IPD: Clear mypy errors in core and tracker and retire the ignore_errors override

- Date: 2026-11-24
- Kind: child
- Concern: Static type checking: `core.py` and `tracker.py`, the two central runtime modules, are the last entries on the `ignore_errors` override that plan `gzc672` adds, so a type error in the run lifecycle would not fail the CI `typecheck` job.
- Scope: `src/pubrun/core.py`, `src/pubrun/tracker.py`, a new `tests/test_tracker_console_migration.py`, the deletion of the then-empty `ignore_errors` override block in `pyproject.toml`, and the contributor documentation (`CONTRIBUTING.md`, `CHANGELOG.md`).
- Scope-Paths: src/pubrun/core.py, src/pubrun/tracker.py, tests/test_tracker_console_migration.py, pyproject.toml, CONTRIBUTING.md, CHANGELOG.md
- Item-Dependencies: executed:gzc672, executed:m66tfv, executed:f5yisk, executed:qe6dad, executed:k6fs5k
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Fix mypy errors in core.py and tracker.py, delete the empty ignore_errors override, and update contributor docs
- Work-Kind: chore
- Priority: low
- From-Backlog: qqwebg
- Set: rand-mypy
- Order: 5
- Highest E allocated: 05
- Author: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Id: 0uxy76
- Approval: 2026-11-25, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004
- 2026-11-24 to-review (aw set): authored from backlog qqwebg
- 2026-11-24 draft (uri/its_direct/pt3-claude-opus-5.5-1m-us): created.

## Goal

Fix the 29 `mypy` errors in `core.py` (11) and `tracker.py` (18), then delete the `ignore_errors` override block from `pyproject.toml`, which is empty once children `f5yisk`, `qe6dad`, and `k6fs5k` and this plan have removed their modules. After this plan, `mypy` checks every module of the package on Linux. Add a behavioral test for the one edited path the suite does not cover (console tee re-pointing after an output-directory migration), and update the contributor documentation that `gzc672` wrote about the override.

`core.py` holds the public API (`annotate`, the `phase` context manager, profiling). `tracker.py` holds the `Run` object; its `_merge_and_migrate` method moves an active run's directory when a later `pubrun.start(output_dir=...)` call changes the output directory, and re-opens the event stream and the console log files in the new place.

### Ratchet completion

```mermaid
flowchart TD
    A["f5yisk, qe6dad, k6fs5k executed: override lists only pubrun.core, pubrun.tracker"] --> B["E-01: narrow optional attributes in core.py"]
    A --> C["E-02: type Run attributes, bind locals in tracker._merge_and_migrate"]
    C --> D["E-03: test that console lines follow a migration"]
    B --> E["E-04: delete the ignore_errors override block"]
    D --> E
    E --> F{"mypy exits 0 with no override?"}
    F -->|yes| G["E-05: update CONTRIBUTING.md and CHANGELOG.md"]
    F -->|no| H["Fix the reported error; do not restore the override"]
    H --> F
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix the type errors

- [x] E-01 In `src/pubrun/core.py`, make `mypy` see the narrowing that the code already performs at runtime:
  - `src/pubrun/core.py::annotate`: replace `if current_run and getattr(current_run, "event_stream", None):` with the two lines `event_stream = getattr(current_run, "event_stream", None) if current_run else None` and `if event_stream:`, and replace `current_run.event_stream.emit("annotation", name=message, payload=payload)` with `event_stream.emit("annotation", name=message, payload=payload)`.
  - `src/pubrun/core.py::phase`: add the class attribute `_yappi_active: bool = False` as the first statement after the class docstring, and change `self._profiler = None` in `__init__` to `self._profiler: Any = None`. The attribute holds a `cProfile.Profile`, the string `"yappi"`, or `None`. `getattr(phase, "_yappi_active", False)` in `__enter__` already treats a missing attribute as `False`, so declaring it changes no result.
  - `src/pubrun/core.py::phase.__enter__`: the same pattern as `annotate`: `event_stream = getattr(self.run_tracker, "event_stream", None) if self.run_tracker else None`, then `if event_stream:` and `event_stream.emit("phase_start", name=self.name)`.
  - `src/pubrun/core.py::phase.__exit__`: replace `import yappi as yappi_mod  # type: ignore[import-not-found]` with `import yappi as _yappi_imported  # type: ignore[import-not-found]` followed by `yappi_mod = _yappi_imported`; keep `yappi_mod.stop()` on the next line. The import rebound a name already declared `yappi_mod: Any = None` (`no-redef`). Then replace `if self.run_tracker and getattr(self.run_tracker, "event_stream", None):` with `end_stream = getattr(self.run_tracker, "event_stream", None) if self.run_tracker else None` and `if end_stream:`, and `self.run_tracker.event_stream.emit(` with `end_stream.emit(`.
  - `src/pubrun/core.py::phase._emit_profile_saved`: `event_stream = getattr(self.run_tracker, "event_stream", None)`, then `if event_stream:` and `event_stream.emit(`.
  - Depends on: none
  - Expected outcome: The diff of `core.py` contains only these changes. `python3 -m pytest tests/test_api.py tests/test_events.py tests/test_core_lifecycle_bugs.py tests/test_new_features.py tests/test_pause_resume.py tests/test_file_registration.py -q` passes.
  - Execution state: performed

- [x] E-02 In `src/pubrun/tracker.py` (`ConsoleInterceptor` and `EventStream` are already imported at module top level alongside `ArtifactWriter`, so no `TYPE_CHECKING` import or block is needed):
  - `src/pubrun/tracker.py::Run.__init__`: `self.console_interceptor = None` becomes `self.console_interceptor: Optional[ConsoleInterceptor] = None`, and `self.event_stream = None` becomes `self.event_stream: Optional[EventStream] = None` (matching `self.writer: Optional[ArtifactWriter] = None`).
  - `src/pubrun/tracker.py::Run._merge_and_migrate`, in the block under the comment `# Close open files before moving the directory (required on Windows)`: bind `event_stream = self.event_stream` and `interceptor = self.console_interceptor` once, then use those locals for every later `self.event_stream` and `self.console_interceptor` reference in the close block and in the reopen block under `# Reopen or migrate the files to the active run_dir`. Replace each truthiness test `getattr(self, "event_stream", None)`, `getattr(self, "console_interceptor", None)`, `getattr(self.console_interceptor, "stdout_log", None)`, and `getattr(self.console_interceptor, "stderr_log", None)` with the matching `is not None` test on the local. Keep `getattr(event_stream, "_file", None)` unchanged (it reads a private attribute). Keep every assignment, including `interceptor.stdout_log = None`, `interceptor.stdout_tee.log_file = interceptor.stdout_log`, and the stderr pair.
  - Depends on: none
  - Expected outcome: The diff of `tracker.py` contains only these changes. `EventStream`, `ConsoleInterceptor`, and file objects define no `__bool__` or `__len__`, so `is not None` gives the same result as the old truthiness tests for every value these attributes take. `python3 -m pytest tests/test_tracker.py tests/test_events.py tests/test_core_lifecycle_bugs.py -q` passes.
  - Execution state: performed

- [x] E-03 Create `tests/test_tracker_console_migration.py` with one test, `test_console_lines_after_migration_land_in_migrated_logs`, skipped on Windows with the reason used by `tests/test_tracker.py::TestMergeAndMigrate.test_migrate_moves_directory` (`"Open file handles prevent shutil.move on Windows"`). It writes `tmp_path / ".pubrun.toml"` containing `[console]` with `capture_mode = "basic"` and `non_tty_mode = "basic"`, and a child script that imports `pubrun`, prints `before-out` to stdout and `before-err` to stderr (both with `flush=True`), calls `pubrun.start(output_dir="moved")`, then prints `after-out` and `after-err` the same way. It runs the script with `subprocess.run([sys.executable, script], cwd=tmp_path, capture_output=True, text=True, timeout=60)` and an environment built like `tests/test_core_lifecycle_bugs.py::_child_env` (this checkout's `src` first on `PYTHONPATH`; `HOME`, `USERPROFILE`, `APPDATA`, and `XDG_CONFIG_HOME` under `tmp_path`; `PUBRUN_DISABLE`, `PUBRUN_AUTO_START`, `PUBRUN_IMPORT_MODE`, `PUBRUN_PROFILE`, and `PUBRUN_META_REF` removed). It asserts the exit code is 0, that exactly one run directory under `tmp_path / "moved"` holds a `stdout.log`, that its `stdout.log` contains both `before-out` and `after-out`, and that its `stderr.log` contains both `before-err` and `after-err`.
  - Depends on: E-02
  - Expected outcome: The test passes with and without E-02 (it characterizes the migration), and fails when either tee re-point line in `_merge_and_migrate` is replaced by `pass` (V-03).
  - Execution state: performed

### Task group 2: Retire the override

- [x] E-04 In `pyproject.toml`, delete the whole `[[tool.mypy.overrides]]` block that sets `ignore_errors = true`, including its `module` list (which now holds only `pubrun.core` and `pubrun.tracker`) and the comment lines above it that say the list may only shrink and point at backlog items `qqwebg` and `z5xr49`. Keep `[tool.mypy]` and the `ignore_missing_imports` override for `IPython`, `yappi`, and `tomli`. Change nothing else.
  - Depends on: E-01, E-02
  - Expected outcome: `grep -n "ignore_errors" pyproject.toml` finds no match. `rm -rf .mypy_cache && mypy` prints `Success: no issues found in <N> source files` (`58` at review; re-derive at execution time if modules were added) and exits 0. Appending `_aw_mut: int = "x"` to `tracker.py`, which exited 0 under the override at `gzc672` review, now makes `mypy --no-incremental` exit 1.
  - Execution state: performed

- [x] E-05 Update the contributor documentation that `gzc672` E-07 wrote:
  - `CONTRIBUTING.md#Development setup`: in the paragraph about `mypy`, replace the statement that CI fails on a type error "in any module not listed in the `ignore_errors` override in `pyproject.toml`" with a statement that CI fails on a type error in any module of the package. Remove any other sentence that refers to the override or to its module list.
  - `CHANGELOG.md` `## [Unreleased]`: add one `### Changed` entry (create the subsection if it does not exist) stating that `mypy` now checks every module of the package and that the per-module `ignore_errors` exemption list has been removed.
  - Follow `AGENTS.md#Agent execution contract`: no em or en dashes in the added prose.
  - Depends on: E-04
  - Expected outcome: `grep -n "ignore_errors" CONTRIBUTING.md` finds no match, and `CHANGELOG.md` `## [Unreleased]` has the new entry.
  - Execution state: performed

## Project conventions discovered (Step 0)

- Plan `gzc672` (now `executed`; `approved` at authoring) E-03 added the `ignore_errors` override with 21 legacy modules (the original 20 plus `pubrun.capture.subprocesses`, added during `gzc672` execution; comment cites backlog items `qqwebg` and `z5xr49`) and a comment that the list may only shrink; E-04 added the blocking Linux `typecheck` CI job; E-07 wrote the `CONTRIBUTING.md` paragraph and the `CHANGELOG.md` entry about the override. This plan edits all three results, hence `Item-Dependencies: executed:gzc672`.
- Children `f5yisk` (7 modules), `qe6dad` (6 modules), and `k6fs5k` (6 modules, including `pubrun.capture.subprocesses`) remove the other 19 modules from the list. This plan deletes the block, so it must run after all three. `k6fs5k` is also a type dependency: `tracker.py`'s 18 errors include `TextIOWrapper` assignments that stay errors until `k6fs5k` E-01 annotates `ConsoleInterceptor.stdout_log` and `stderr_log`. At authoring, applying this plan's `core.py` and `tracker.py` edits to `gzc672`'s tree without `k6fs5k`'s edits left `tracker.py` errors on the two lines that re-open `stdout.log` and `stderr.log` (`variable has type "None"`).
- `tests/test_core_lifecycle_bugs.py::_child_env` and `::_run_script` show the subprocess pattern for testing a whole run; `tests/test_tracker.py::TestMergeAndMigrate` holds the in-process migration tests and the Windows skip.
- `CHANGELOG.md` follows Keep a Changelog with an `## [Unreleased]` section. `AGENTS.md#Agent execution contract` forbids em and en dashes in user-facing prose such as `CONTRIBUTING.md` and `CHANGELOG.md`.

## Findings

| ID | Severity | Remediation Risk | Evidence | Finding |
|---|---|---|---|---|
| M-10 | Low | Low | `mypy` with no override on `gzc672`'s tree: `core.annotate`, `phase.__enter__`, `phase.__exit__`, `phase._emit_profile_saved`: `Item "None" of "Any \| None" has no attribute "emit"  [union-attr]` (5); `phase.__enter__`: `Incompatible types in assignment (expression has type "Profile", variable has type "None")`, `"None" has no attribute "enable"`, `"type[phase]" has no attribute "_yappi_active"`; `phase.__exit__`: `Name "yappi_mod" already defined` | 11 errors: `mypy` cannot follow a `getattr` truthiness test into the following attribute access, and two attributes are typed by their first `None` assignment. |
| M-11 | Low | Low | `tracker.Run._merge_and_migrate`: `Item "None" of "Any \| None" has no attribute "close"`, `"stdout_log"`, `"stderr_log"`, `"migrate_directory"`, `"emit"`, `"mode"`, `"stdout_tee"`, `"stderr_tee"` (18) | `console_interceptor` and `event_stream` are typed by their first `None` assignment and narrowed only by `getattr`. |
| M-12 | Medium | Low | Prototype with every edit in this Set applied: replacing both `interceptor.stdout_tee.log_file = interceptor.stdout_log` and the stderr line with `pass` left the full suite green (`2052 passed`) | No existing test checks that console output written after a migration reaches the migrated log files, so a broken E-02 refactor of those lines would pass CI. E-03 adds that test. |

Authoring measurements (lane HEAD `a4b7d12`, `mypy` 2.3.1, Python 3.14.6, Linux):

- A scratch tree with `gzc672`'s fixes, child `k6fs5k`'s six capture edits, and this plan's `core.py` and `tracker.py` edits, with `pubrun.core` and `pubrun.tracker` removed from the override: `Success: no issues found in 58 source files`. With every edit in this Set applied and no override block at all: `Success: no issues found in 58 source files` on Linux and with `--platform darwin`; `--platform win32` reports the errors child `juoqy2` fixes.
- E-03 prototype: passed against the edited `tracker.py` and against HEAD's `tracker.py`. Replacing the stdout re-point with `pass` failed it with `AssertionError: before-out` (the migrated `stdout.log` lacked `after-out`); replacing the stderr re-point failed it with `AssertionError: before-err`.
- Mutations the existing suite catches (prototype, `tests/test_api.py tests/test_events.py tests/test_core_lifecycle_bugs.py tests/test_new_features.py tests/test_pause_resume.py tests/test_file_registration.py`, 185 tests): disabling the `annotation` emit: `6 failed, 179 passed`; disabling the `phase_end` emit: `6 failed, 179 passed`; disabling the `profile_saved` emit: `2 failed, 183 passed`; dropping `yappi_mod.stop()`: `1 failed, 184 passed`; disabling the `phase_start` emit failed 3 tests. With `tests/test_tracker.py` added, disabling `event_stream.migrate_directory(new_dir)` failed `1 failed, 204 passed`.
- Disabling `event_stream.close()` in `_merge_and_migrate` left those 205 tests green. This is not a coverage gap on POSIX: `EventStream.migrate_directory` itself flushes and closes the open file before reopening, so on Linux the earlier `close()` has no observable effect. It matters on Windows, where `shutil.move` cannot move an open file, and the migration tests are skipped there. E-02 keeps the call unchanged.

## Proposed changes (ordered, validatable)

1. Bind the optional event stream to a local before use in `core.py`, declare `phase._yappi_active` and `phase._profiler`, and rename the `yappi` import (E-01; Remediation Risk: Low).
2. Type `Run.console_interceptor` and `Run.event_stream`, and bind them to locals in `_merge_and_migrate` (E-02; Remediation Risk: Low).
3. Add a subprocess test for console output after a migration (E-03; Remediation Risk: Low).
4. Delete the empty `ignore_errors` override (E-04; Remediation Risk: Low).
5. Update `CONTRIBUTING.md` and `CHANGELOG.md` (E-05; Remediation Risk: Low).

Rejected alternatives:

- Leaving an `ignore_errors` override with an empty `module` list: it documents nothing and invites re-adding modules, which the ratchet forbids.
- `assert self.event_stream is not None` before each use: it adds runtime checks (and would change behavior under `python -O`), where binding a local states the same narrowing without changing execution.

## Deferred / out of scope (with reason)

- Errors that appear only under `mypy --platform win32` and adding `--platform` runs to CI: owned by child `juoqy2`, which runs after this plan and edits `CONTRIBUTING.md` and `CHANGELOG.md` again for the platform runs.
  - Carrier: juoqy2
- Pinning the `mypy` version: deferred by `gzc672` for the reason recorded there (it would change the `dev` extra contract).
  - Carrier-Declined: Deliberate non-goal (changing the dev extra contract was deferred by gzc672).

## Scope check

- Over-scope: none. The new test file covers the one edited path no test reaches.
- Under-scope: none.

## Required tests / validation

- `rm -rf .mypy_cache && mypy; echo "exit=$?"`: `Success: no issues found in <N> source files` (`58` at review; re-derive at execution time if modules were added), `exit=0`.
- Mutation checks of the gate, each restored before the next: append `_aw_mut: int = "x"` to `src/pubrun/tracker.py`, then to `src/pubrun/core.py`; each `mypy --no-incremental; echo "exit=$?"` run prints an `error:` line for that file and `exit=1`.
- Mutation checks of E-03 (V-03).
- Full suite (`aw suite --no-cache`, or `python3 -m pytest -q` if `aw suite` is unavailable): exit 0.
- `python3 scripts/sanitize_paths.py --check --all`: exit 0.

## Spec / documentation sync

- No `.spec.md` under `.aw/records/specs/` and no file under `docs/` mentions `mypy` (checked at authoring with `grep -rln "randomly\|mypy" .aw/records/specs docs`: no match). No spec is amended.
- `CONTRIBUTING.md` and `CHANGELOG.md` are updated by E-05.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: (1) Pasted `git diff src/pubrun/core.py` showing only the changes listed in E-01. (2) The last line of `python3 -m pytest tests/test_api.py tests/test_events.py tests/test_core_lifecycle_bugs.py tests/test_new_features.py tests/test_pause_resume.py tests/test_file_registration.py -q` showing all passed. (3) Mutation: replace `event_stream.emit("annotation", name=message, payload=payload)` with `pass`, rerun that command, paste its last line showing at least one failure, restore, and paste `git diff --stat src/pubrun/core.py`.
  - Observed evidence:
    (1) `git diff src/pubrun/core.py`:
    ```diff
    diff --git a/src/pubrun/core.py b/src/pubrun/core.py
    index bc9b226..9634e4e 100644
    --- a/src/pubrun/core.py
    +++ b/src/pubrun/core.py
    @@ -163,9 +163,10 @@ def annotate(message: Optional[str] = None, **kwargs: Any) -> None:
             >>> pubrun.annotate("Model Configured", layers=50, optimizer="adamw")
         """
         current_run = get_current_run()
    -    if current_run and getattr(current_run, "event_stream", None):
    +    event_stream = getattr(current_run, "event_stream", None) if current_run else None
    +    if event_stream:
             payload = kwargs.copy()
    -        current_run.event_stream.emit("annotation", name=message, payload=payload)
    +        event_stream.emit("annotation", name=message, payload=payload)
         else:
             _handle_inactive("pubrun.annotate()")

    @@ -461,10 +462,12 @@ class phase:
             >>> with pubrun.phase("data_ingestion"):
             ...     df = pd.read_csv("huge.csv")
         """
    +    _yappi_active: bool = False
    +
         def __init__(self, name: str) -> None:
             self.name = name
             self.run_tracker: Optional[Run] = None
    -        self._profiler = None
    +        self._profiler: Any = None
             self._started_yappi = False
             self._start_mono: Optional[float] = None

    @@ -472,8 +475,9 @@ class phase:
             # Bind at entry, not construction, so a phase object created before
             # start() (or reused across runs) logs to the run active when it runs.
             self.run_tracker = get_current_run()
    -        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
    -            self.run_tracker.event_stream.emit("phase_start", name=self.name)
    +        event_stream = getattr(self.run_tracker, "event_stream", None) if self.run_tracker else None
    +        if event_stream:
    +            event_stream.emit("phase_start", name=self.name)
             else:
                 _handle_inactive(f"pubrun.phase('{self.name}')")
             # Phase-scoped profiling (opt-in via [capture.profiling].enabled)
    @@ -521,7 +525,8 @@ class phase:
                 # run stopped inside the phase, so later phases can profile again.
                 yappi_mod: Any = None
                 try:
    -                import yappi as yappi_mod  # type: ignore[import-not-found]
    +                import yappi as _yappi_imported  # type: ignore[import-not-found]
    +                yappi_mod = _yappi_imported
                     yappi_mod.stop()
                 except Exception as prof_err:
                     logging.getLogger("pubrun").debug(f"pubrun: yappi stop failed: {prof_err}")
    @@ -561,7 +566,8 @@ class phase:
                             pass
                 self._profiler = None

    -        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
    +        end_stream = getattr(self.run_tracker, "event_stream", None) if self.run_tracker else None
    +        if end_stream:
                 end_payload: Dict[str, Any] = {}
                 if self._start_mono is not None:
                     end_payload["elapsed_seconds"] = max(0.0, end_mono - self._start_mono)
    @@ -570,7 +576,7 @@ class phase:
                     end_payload["error"] = (
                         exc_val.__class__.__name__ if exc_val is not None else exc_type.__name__
                     )
    -            self.run_tracker.event_stream.emit(
    +            end_stream.emit(
                     "phase_end",
                     name=self.name,
                     payload=end_payload if end_payload else None,
    @@ -578,8 +584,9 @@ class phase:

         def _emit_profile_saved(self, prof_name: str) -> None:
             """Emit a ``profile_saved`` event so the saved profile is discoverable."""
    -        if getattr(self.run_tracker, "event_stream", None):
    -            self.run_tracker.event_stream.emit(
    +        event_stream = getattr(self.run_tracker, "event_stream", None)
    +        if event_stream:
    +            event_stream.emit(
                     "profile_saved", name=self.name, payload={"path": prof_name}
                 )
    ```
    (2) `python3 -m pytest tests/test_api.py tests/test_events.py tests/test_core_lifecycle_bugs.py tests/test_new_features.py tests/test_pause_resume.py tests/test_file_registration.py -q`:
    ```text
    185 passed in 16.05s
    exit=0
    ```
    (3) Mutation replacing `event_stream.emit("annotation", name=message, payload=payload)` with `pass`:
    ```text
    6 failed, 179 passed in 18.06s
    exit=1
    ```
    After restore, `git diff --stat src/pubrun/core.py`:
    ```text
     src/pubrun/core.py | 27 +++++++++++++++++----------
     1 file changed, 17 insertions(+), 10 deletions(-)
    ```
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `git diff src/pubrun/tracker.py` showing only the two annotated attributes (`self.console_interceptor` and `self.event_stream`) and the `_merge_and_migrate` local bindings and `is not None` tests; and the last line of `python3 -m pytest tests/test_tracker.py tests/test_events.py tests/test_core_lifecycle_bugs.py -q` showing all passed.
  - Observed evidence:
    `git diff src/pubrun/tracker.py`:
    ```diff
    diff --git a/src/pubrun/tracker.py b/src/pubrun/tracker.py
    index f429103..415db01 100644
    --- a/src/pubrun/tracker.py
    +++ b/src/pubrun/tracker.py
    @@ -207,8 +207,8 @@ class Run:
             self._pending_file_registrations: list = []
             self.manual_subprocess_records: list = []
             self._active_profilers: list = []
    -        self.console_interceptor = None
    -        self.event_stream = None
    +        self.console_interceptor: Optional[ConsoleInterceptor] = None
    +        self.event_stream: Optional[EventStream] = None
             self.resource_watcher = None
             self.signal_capture = None
             self._hardware_thread: Optional[threading.Thread] = None
    @@ -860,24 +860,26 @@ class Run:
                         done.wait(timeout=5)

                     # Close open files before moving the directory (required on Windows)
    -                if getattr(self, "event_stream", None):
    -                    self.event_stream.close()
    +                event_stream = self.event_stream
    +                interceptor = self.console_interceptor
    +                if event_stream is not None:
    +                    event_stream.close()

    -                if getattr(self, "console_interceptor", None):
    -                    if getattr(self.console_interceptor, "stdout_log", None):
    +                if interceptor is not None:
    +                    if interceptor.stdout_log is not None:
                             try:
    -                            self.console_interceptor.stdout_log.flush()
    -                            self.console_interceptor.stdout_log.close()
    +                            interceptor.stdout_log.flush()
    +                            interceptor.stdout_log.close()
                             except Exception:
                                 pass
    -                        self.console_interceptor.stdout_log = None
    -                    if getattr(self.console_interceptor, "stderr_log", None):
    +                        interceptor.stdout_log = None
    +                    if interceptor.stderr_log is not None:
                             try:
    -                            self.console_interceptor.stderr_log.flush()
    -                            self.console_interceptor.stderr_log.close()
    +                            interceptor.stderr_log.flush()
    +                            interceptor.stderr_log.close()
                             except Exception:
                                 pass
    -                        self.console_interceptor.stderr_log = None
    +                        interceptor.stderr_log = None

                     try:
                         import shutil
    @@ -897,28 +899,28 @@ class Run:
                         old_dir_str = str(self.run_dir)

                     # Reopen or migrate the files to the active run_dir
    -                if getattr(self, "event_stream", None):
    -                    self.event_stream.migrate_directory(new_dir)
    +                if event_stream is not None:
    +                    event_stream.migrate_directory(new_dir)
                         # BUG-10: Only emit if the stream successfully reopened.
                         if new_dir != Path(old_dir_str):
    -                        if getattr(self.event_stream, "_file", None):
    -                            self.event_stream.emit("warning", payload={"message": f"Storage directory changed mid-execution from {old_dir_str} to {new_dir}"})
    +                        if getattr(event_stream, "_file", None):
    +                            event_stream.emit("warning", payload={"message": f"Storage directory changed mid-execution from {old_dir_str} to {new_dir}"})
                             else:
                                 logging.getLogger("pubrun").warning(
                                     "pubrun: storage migrated to %s but event stream failed to reopen",
                                     new_dir,
                                 )

    -                if getattr(self, "console_interceptor", None):
    -                    if self.console_interceptor.mode != "off":
    +                if interceptor is not None:
    +                    if interceptor.mode != "off":
                             try:
    -                            self.console_interceptor.stdout_log = open(new_dir / "stdout.log", "a", encoding="utf-8")
    -                            if self.console_interceptor.stdout_tee:
    -                                self.console_interceptor.stdout_tee.log_file = self.console_interceptor.stdout_log
    +                            interceptor.stdout_log = open(new_dir / "stdout.log", "a", encoding="utf-8")
    +                            if interceptor.stdout_tee:
    +                                interceptor.stdout_tee.log_file = interceptor.stdout_log

    -                            self.console_interceptor.stderr_log = open(new_dir / "stderr.log", "a", encoding="utf-8")
    -                            if self.console_interceptor.stderr_tee:
    -                                self.console_interceptor.stderr_tee.log_file = self.console_interceptor.stderr_log
    +                            interceptor.stderr_log = open(new_dir / "stderr.log", "a", encoding="utf-8")
    +                            if interceptor.stderr_tee:
    +                                interceptor.stderr_tee.log_file = interceptor.stderr_log
                             except Exception as reopen_err:
                                 logging.getLogger("pubrun").debug(
                                     "Failed to reopen console logs after migration: %s", reopen_err
    ```
    `python3 -m pytest tests/test_tracker.py tests/test_events.py tests/test_core_lifecycle_bugs.py -q`:
    ```text
    97 passed in 11.51s
    exit=0
    ```
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: (1) Pasted content of `tests/test_tracker_console_migration.py`. (2) The last line of `python3 -m pytest tests/test_tracker_console_migration.py -q` showing `1 passed`. (3) For each of the two mutants, applied one at a time and restored before the next, replace `interceptor.stdout_tee.log_file = interceptor.stdout_log` (then `interceptor.stderr_tee.log_file = interceptor.stderr_log`) with `pass`, rerun the test, and paste the failing assertion and `1 failed`. (4) `git diff --stat src/pubrun/tracker.py` after the last restore, matching V-02.
  - Observed evidence:
    (1) `tests/test_tracker_console_migration.py`:
    ```python
    """Subprocess test for console tee re-pointing after output-directory migration."""
    import os
    import subprocess
    import sys
    import textwrap
    from pathlib import Path

    import pytest

    SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


    def _child_env(tmp_path: Path) -> dict:
        env = dict(os.environ)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        env["HOME"] = str(tmp_path)
        env["USERPROFILE"] = str(tmp_path)
        env["APPDATA"] = str(tmp_path / ".appdata")
        env["XDG_CONFIG_HOME"] = str(tmp_path / ".xdg")
        for key in (
            "PUBRUN_DISABLE",
            "PUBRUN_AUTO_START",
            "PUBRUN_IMPORT_MODE",
            "PUBRUN_PROFILE",
            "PUBRUN_META_REF",
        ):
            env.pop(key, None)
        return env


    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Open file handles prevent shutil.move on Windows",
    )
    def test_console_lines_after_migration_land_in_migrated_logs(tmp_path: Path) -> None:
        """Console output written before and after output_dir migration reaches migrated logs."""
        (tmp_path / ".pubrun.toml").write_text(
            textwrap.dedent(
                """\
                [console]
                capture_mode = "basic"
                non_tty_mode = "basic"
                """
            ),
            encoding="utf-8",
        )
        script = tmp_path / "child_script.py"
        script.write_text(
            textwrap.dedent(
                """\
                import sys
                import pubrun

                print("before-out", flush=True)
                print("before-err", file=sys.stderr, flush=True)
                pubrun.start(output_dir="moved")
                print("after-out", flush=True)
                print("after-err", file=sys.stderr, flush=True)
                """
            ),
            encoding="utf-8",
        )

        res = subprocess.run(
            [sys.executable, str(script)],
            cwd=tmp_path,
            env=_child_env(tmp_path),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert res.returncode == 0, res.stderr

        stdout_logs = sorted((tmp_path / "moved").glob("*/stdout.log"))
        assert len(stdout_logs) == 1, f"expected one migrated run with stdout.log, found {stdout_logs}"
        run_dir = stdout_logs[0].parent

        stdout_text = stdout_logs[0].read_text(encoding="utf-8")
        stderr_text = (run_dir / "stderr.log").read_text(encoding="utf-8")
        assert "before-out" in stdout_text, stdout_text
        assert "after-out" in stdout_text, stdout_text
        assert "before-err" in stderr_text, stderr_text
        assert "after-err" in stderr_text, stderr_text
    ```
    (2) `python3 -m pytest tests/test_tracker_console_migration.py -q`:
    ```text
    1 passed in 1.36s
    exit=0
    ```
    (3) Mutant 1 (`interceptor.stdout_tee.log_file = interceptor.stdout_log` -> `pass`):
    ```text
    >       assert "after-out" in stdout_text, stdout_text
    E       AssertionError: before-out
    E
    E       assert 'after-out' in 'before-out\n'
    FAILED tests/test_tracker_console_migration.py::test_console_lines_after_migration_land_in_migrated_logs
    1 failed in 1.37s
    exit=1
    ```
    Mutant 2 (`interceptor.stderr_tee.log_file = interceptor.stderr_log` -> `pass`):
    ```text
    >       assert "after-err" in stderr_text, stderr_text
    E       AssertionError: before-err
    E
    E       assert 'after-err' in 'before-err\n'
    FAILED tests/test_tracker_console_migration.py::test_console_lines_after_migration_land_in_migrated_logs
    1 failed in 1.26s
    exit=1
    ```
    (4) `git diff --stat src/pubrun/tracker.py` after restore:
    ```text
     src/pubrun/tracker.py | 52 ++++++++++++++++++++++++++-------------------------
     1 file changed, 27 insertions(+), 25 deletions(-)
    ```
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: (1) Pasted `git diff pyproject.toml` showing only the deleted override block and its comment. (2) Pasted output of `grep -n "ignore_errors" pyproject.toml; echo "exit=$?"` showing `exit=1` (no match). (3) Pasted output of `rm -rf .mypy_cache && mypy; echo "exit=$?"` showing `Success: no issues found in <N> source files` (`58` at review; re-derive at execution time if modules were added) and `exit=0`. (4) Pasted output of the two `mypy --no-incremental; echo "exit=$?"` gate mutation checks, each with an `error:` line for the mutated file and `exit=1`, then `git diff --stat src/pubrun` showing only E-01 and E-02 files. (5) The last line of `aw suite --no-cache` (or `python3 -m pytest -q` if `aw suite` is unavailable) and `exit=0`. (6) `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
    (1) `git diff pyproject.toml`:
    ```diff
    diff --git a/pyproject.toml b/pyproject.toml
    index 2f1e11a..50da3ea 100644
    --- a/pyproject.toml
    +++ b/pyproject.toml
    @@ -111,12 +111,3 @@ files = ["src/pubrun"]
     [[tool.mypy.overrides]]
     module = ["IPython", "IPython.*", "yappi", "tomli"]
     ignore_missing_imports = true
    -
    -[[tool.mypy.overrides]]
    -# Legacy type-check ratchet: this list may only shrink, never grow.
    -# Remove each module as its existing errors are fixed (backlog item qqwebg).
    -module = [
    -    "pubrun.core",
    -    "pubrun.tracker",
    -]
    -ignore_errors = true
    ```
    (2) `grep -n "ignore_errors" pyproject.toml; echo "exit=$?"`:
    ```text
    exit=1
    ```
    (3) `rm -rf .mypy_cache && mypy; echo "exit=$?"`:
    ```text
    Success: no issues found in 59 source files
    exit=0
    ```
    (4) Gate mutation checks (`mypy --no-incremental; echo "exit=$?"`):
    Tracker mutant (`_aw_mut: int = "x"` appended to `src/pubrun/tracker.py`):
    ```text
    src/pubrun/tracker.py:1638: error: Incompatible types in assignment (expression has type "str", variable has type "int")  [assignment]
    Found 1 error in 1 file (checked 59 source files)
    exit=1
    ```
    Core mutant (`_aw_mut: int = "x"` appended to `src/pubrun/core.py`):
    ```text
    src/pubrun/core.py:1366: error: Incompatible types in assignment (expression has type "str", variable has type "int")  [assignment]
    Found 1 error in 1 file (checked 59 source files)
    exit=1
    ```
    After restore, `git diff --stat src/pubrun`:
    ```text
     src/pubrun/core.py    | 27 ++++++++++++++++----------
     src/pubrun/tracker.py | 52 ++++++++++++++++++++++++++-------------------------
     2 files changed, 44 insertions(+), 35 deletions(-)
    ```
    (5) `aw suite --no-cache`:
    ```text
    ======================= 2260 passed in 141.85s (0:02:21) =======================
    exit=0
    ```
    (6) `python3 scripts/sanitize_paths.py --check --all`:
    ```text
    exit=0
    ```
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: Pasted `git diff CONTRIBUTING.md CHANGELOG.md`; pasted output of `grep -n "ignore_errors" CONTRIBUTING.md; echo "exit=$?"` showing `exit=1`; and pasted output of `python3 -c 'import subprocess; diff = subprocess.check_output(["git", "diff", "-U0", "--", "CONTRIBUTING.md", "CHANGELOG.md"], text=True); added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]; assert added, "no added doc lines"; bad = [l for l in added if "\u2013" in l or "\u2014" in l]; assert not bad, bad; print(f"OK: {len(added)} added line(s), 0 en/em dashes")'` printing `OK: ... 0 en/em dashes` and exiting 0.
  - Observed evidence:
    `git diff CONTRIBUTING.md CHANGELOG.md`:
    ```diff
    diff --git a/CHANGELOG.md b/CHANGELOG.md
    index d2e7bcc..9814e62 100644
    --- a/CHANGELOG.md
    +++ b/CHANGELOG.md
    @@ -65,6 +65,9 @@ The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
       pass/fail receipt. Archival/aggregation is a later, separately gated phase.

     ### Changed
    +- **Full-package static type checking with `mypy`.** Static type checking with `mypy` now checks
    +  every module of the `pubrun` package on Linux. The per-module `ignore_errors` exemption list has
    +  been removed from `pyproject.toml`.
     - **Testable entry points.** `pubrun.__main__.main()` now accepts an optional argument list without
       modifying `sys.argv`, and `print_report` and `print_resources_report` in
       `pubrun.report.diagnostics` accept a keyword-only `out` stream and raise `DiagnosticsError`
    diff --git a/CONTRIBUTING.md b/CONTRIBUTING.md
    index bbc3201..3e4b964 100644
    --- a/CONTRIBUTING.md
    +++ b/CONTRIBUTING.md
    @@ -30,7 +30,7 @@ To run the intake-script and benchmark contract suites that live outside `tests/
     python -m pytest .github/scripts/ benchmarks/test_share_safety.py benchmarks/test_pull_submissions.py benchmarks/test_benchmarks.py
     ```

    -Run static type checks locally before opening a pull request. The GitHub Actions CI `typecheck` job runs the same check on Linux and fails on a type error in any module not listed in the `ignore_errors` override in `pyproject.toml`:
    +Run static type checks locally before opening a pull request. The GitHub Actions CI `typecheck` job runs the same check on Linux and fails on a type error in any module of the package:

     ```bash
     python -m pip install -e ".[dev,tui]"
    ```
    `grep -n "ignore_errors" CONTRIBUTING.md; echo "exit=$?"`:
    ```text
    exit=1
    ```
    Dash check:
    ```text
    OK: 4 added line(s), 0 en/em dashes
    exit=0
    ```
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question, and for plans `gzc672`, `m66tfv`, `f5yisk`, `qe6dad`, and `k6fs5k` to be `executed`, before you change any file.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries. If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit 0uxy76 -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: inside `aw oc run` / `aw agy run`, the runner owns finalization once every `E-*` item is `performed` and every `V-*` item is `pass`. Outside a runner, after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`, finalize this plan with `aw ipd finalize 0uxy76` (never with a hand-written `git mv`).
