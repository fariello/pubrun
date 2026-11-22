# IPD: Safe Diagnostic Redaction and Hook Ownership Rollback Across Capture Engines

- Date: 2026-11-21
- Kind: child
- Concern: Bounded, redacted diagnostic error formatting and transactional install plus ownership-guarded uninstall across process-global hooks and background capture engines.
- Scope: Add `format_safe_error_detail()` in `src/pubrun/capture/redaction.py`; enforce transactional install, pre-existing wrapper chaining, and ownership-guarded rollback/uninstall in `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/console.py`, `src/pubrun/capture/signals.py`, and `src/pubrun/capture/resources.py`; sanitize fallback failure data in `src/pubrun/capture/invocation.py`; add behavioral ownership and rollback tests in `tests/test_hook_ownership_rollback.py`.
- Scope-Paths: src/pubrun/capture/redaction.py, src/pubrun/capture/subprocesses.py, src/pubrun/capture/console.py, src/pubrun/capture/signals.py, src/pubrun/capture/resources.py, src/pubrun/capture/invocation.py, tests/test_hook_ownership_rollback.py
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Add bounded redacted error formatting and transactional ownership-guarded install/uninstall for subprocess, console, signal, and resource engines
- Work-Kind: bug
- Priority: high
- From-Backlog: x21s6w
- Blocks-Release: next
- Set: cap-isolation
- Order: 1
- Highest E allocated: 05
- Author: agent
- Id: p6pon8
- Approval: 2026-11-22, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 approved (aw set): status set to approved
- 2026-11-22 /plan-review (Antigravity / Gemini): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-007, PR-008
- 2026-11-22 draft (agent): created.
- 2026-11-22 to-review (agent): authored review-ready child plan from backlog item `x21s6w`.

## Goal

Provide one shared, bounded, redacted error-formatting helper for capture diagnostics and make every global-hook and background capture engine (`SubprocessSpy`, `ConsoleInterceptor`, `SignalExitCapture`, and `ResourceWatcher`) install transactionally, preserve pre-existing and post-install third-party wrappers under explicit ownership rules, and tear down cleanly even when one cleanup step raises.

### Hook installation and ownership-guarded uninstall lifecycle

The text in `## Proposed changes (ordered, validatable)` is normative. These diagrams summarize the transactional install/uninstall state machine and the ownership relationships across capture engines.

```mermaid
flowchart TD
    A["Install requested with owner token"] --> B["Snapshot current global target as previous"]
    B --> C["Install pubrun wrapper bound to active flag and previous"]
    C --> D{"All targets in engine succeeded?"}
    D -->|No| E["Roll back only targets installed in this attempt"]
    E --> F["Mark engine failed with bounded redacted detail and leave globals restored"]
    D -->|Yes| G["Engine active and owned by caller"]
    G --> H["Uninstall or stop requested"]
    H --> I["Set wrapper active flag to False"]
    I --> J{"Current global target is still pubrun wrapper?"}
    J -->|Yes| K["Restore saved previous target"]
    J -->|No: Third-party wrapper installed later| L["Keep third-party wrapper intact; pubrun wrapper passes through passively"]
    K --> M["Run remaining independent cleanup steps"]
    L --> M
```

```mermaid
erDiagram
    SAFE_DIAGNOSTIC_FORMATTER ||--o{ CAPTURE_ENGINE : "sanitizes error detail for"
    CAPTURE_ENGINE ||--|| OWNER_TOKEN : "tracks ownership per install"
    CAPTURE_ENGINE ||--o{ GLOBAL_HOOK_TARGET : "chains previous and guards restore"
    CONSOLE_INTERCEPTOR ||--o| FAULTHANDLER_STATE : "preserves prior enabled state"
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Safe error redaction and global-hook ownership rollback

- [ ] E-01 Add `format_safe_error_detail()` to `src/pubrun/capture/redaction.py` and harden the fallback exception path in `src/pubrun/capture/invocation.py`.
  - Depends on: none
  - Expected outcome: `format_safe_error_detail(exc, config=None, max_len=240)` returns a single-line, redacted, length-bounded `"ExcType: message"` string (or `ExcType` when the message is empty) without tracebacks or sensitive values, falling back to default-pattern redaction and then `type(exc).__name__` if redaction raises. `get_invocation()` fallback redacts `argv` safely (or falls back to `[]` if redaction fails) and uses `format_safe_error_detail()` for `capture_state.detail`.
  - Execution state: pending

- [ ] E-02 Refactor `SubprocessSpy` in `src/pubrun/capture/subprocesses.py` to capture live pre-existing targets at `install()` time, chain to them, roll back partial installs transactionally, and enforce owner- and identity-guarded `uninstall()`.
  - Depends on: E-01
  - Expected outcome: `SubprocessSpy.install()` accepts an optional `owner` token, snapshots current `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` at install time, chains to those saved pre-existing targets, and rolls back any already-patched target if a later patch fails. Each install generation tags spawned `Popen` instances with its state object (and holds a direct record reference in `os.system`) so post-uninstall calls and concurrent uninstalls never corrupt a newer run's records or raise `IndexError`, and failed subprocess `capture_state.detail` values use `format_safe_error_detail()`. `SubprocessSpy.uninstall(owner=None)` restores each target independently only when it still equals the wrapper `SubprocessSpy` installed, leaving later third-party wrappers intact while deactivating recording into passive passthrough.
  - Execution state: pending

- [ ] E-03 Refactor `ConsoleInterceptor` and `TqdmSafeTee` in `src/pubrun/capture/console.py` to roll back partial `start()` failures honestly, preserve prior `faulthandler` state, run cleanup steps independently in `stop()`, and bound runtime log-write warnings without recursion.
  - Depends on: E-01
  - Expected outcome: `ConsoleInterceptor.start()` snapshots live `sys.stdout`, `sys.stderr`, and `faulthandler.is_enabled()`, rolls back opened files, replaced streams, and owned `faulthandler` state on any setup error, and records honest failed state (`stdout.captured = False`, `stderr.captured = False`, `capture_state.status = "failed"`, bounded redacted `detail`) instead of falsely reporting `"complete"`. `ConsoleInterceptor.stop()` is idempotent, detaches `tee.log_file = None`, restores or disables `faulthandler` strictly according to prior ownership before closing `stderr_log`, and runs every cleanup step independently. `TqdmSafeTee` detaches broken `log_file` handles on write or flush failure, guards `original_stream.flush()` on closed streams, and avoids recursive logging into a wrapped `sys.stderr`.
  - Execution state: pending

- [ ] E-04 Refactor `SignalExitCapture` in `src/pubrun/capture/signals.py` and `ResourceWatcher` in `src/pubrun/capture/resources.py` for identity-guarded signal restoration, transactional rollback, independent cleanup, and honest failure states.
  - Depends on: E-01
  - Expected outcome: `SignalExitCapture` records each installed shim in `_installed_handlers[signum]`, preserves expected per-signal `(OSError, ValueError)` skipping off the main thread (`capture_state.status = "partial"`), rolls back already-registered signal handlers on unexpected install or excepthook errors, restores each signal handler in `_restore_signal_handlers()` only when `signal.getsignal(signum) is shim`, and runs signal restore and `sys.excepthook` restore independently. Both `_make_handler()` and `_excepthook()` capture their prior handler/hook in local closure variables and check `_active`, forwarding passively without recording, calling `_finalize_active_run()`, or reinstalling on `SIG_DFL` after `uninstall()`, while redacting active `_exit_exception` messages via `format_safe_error_detail()`. `ResourceWatcher.stop()` is idempotent, skips `join()` and final polling on unstarted or already self-aborted threads, isolates poll and `event_stream.emit()` exceptions, stops emitting events after stop, and reports honest `"partial"` or `"failed"` `capture_state` after consecutive poll failures trigger self-abort.
  - Execution state: pending

### Task group 2: Behavioral ownership and rollback verification

- [ ] E-05 Create `tests/test_hook_ownership_rollback.py` covering safe error redaction, pre-existing and post-install third-party wrappers, transactional partial-install rollback, `faulthandler` preservation, and second-cleanup-failure resilience across all four hook/worker engines, then run the targeted test suite.
  - Depends on: E-02, E-03, E-04
  - Expected outcome: `pytest tests/test_hook_ownership_rollback.py tests/test_signals.py tests/test_capture.py tests/test_resources.py tests/test_redaction.py tests/test_quality.py tests/test_edge_cases.py tests/test_pause_resume.py -v` and `pytest tests/test_cli.py -k "faulthandler or excepthook" -v` exit 0 with all tests passing.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `src/pubrun/capture/redaction.py` caches compiled secret regexes in `_PATTERN_CACHE` and exposes `is_secret_key()`, `redact_argv()`, `redact_env_vars()`, and `_redact_value_string_heuristics()`.
- `src/pubrun/capture/subprocesses.py` captures `_original_popen_init`, `_original_popen_wait`, and `_original_os_system` once at module import time, unconditionally restores them in `src/pubrun/capture/subprocesses.py::SubprocessSpy.uninstall`, stores raw `str(e)` in `capture_state.detail` on failure, and indexes `cls._records[idx]` after `_original_os_system(command)` returns.
- `src/pubrun/capture/console.py::ConsoleInterceptor.stop` already uses an identity check (`if sys.stdout is self.stdout_tee`) before restoring `sys.stdout`/`sys.stderr` (verified by `tests/test_quality.py::TestConsoleRestoreSafety.test_stop_preserves_third_party_wrapper`), but `src/pubrun/capture/console.py::ConsoleInterceptor.start` unconditionally enables `faulthandler.enable(file=self.stderr_log)` and `stop()` unconditionally calls `faulthandler.disable()` without checking `faulthandler.is_enabled()`.
- `src/pubrun/capture/console.py::ConsoleInterceptor.start` catches setup exceptions, calls `self.stop()`, and returns silently without recording failure state, so `stop()` later reports `capture_state: {"status": "complete"}` and `captured: True`.
- `src/pubrun/capture/signals.py::SignalExitCapture._restore_excepthook` uses identity-guarded restoration (`sys.excepthook is installed`, tested in `tests/test_edge_cases.py::TestExcepthookRestore`), but clears `self._previous_excepthook = None` even when a third-party wrapper remains pointing at `_excepthook`, and `SignalExitCapture._restore_signal_handlers` unconditionally calls `signal.signal(signum, handler)` without checking whether the current handler is still `pubrun`'s shim.
- `tests/test_signals.py::TestSignalNonMainThread.test_warns_on_non_main_thread` expects `signal.signal()` raising `ValueError` for all signals to skip without raising and emit the `"signal capture unavailable"` warning; `tests/test_signals.py` also asserts `records["exit_exception"] == "SystemExit(42)"` and `"ValueError: test error" in records["exit_exception"]`.
- `src/pubrun/capture/resources.py::ResourceWatcher.stop` calls `self.join(...)` unconditionally (raising `RuntimeError` on an unstarted thread) and runs `self._update_metrics()`/`self._poll_rss()` without exception isolation; `tests/test_resources.py::test_resource_watcher_to_manifest_dict_zeros` asserts an unstarted watcher without poll failures reports `capture_state.status == "complete"`.
- `src/pubrun/capture/invocation.py::get_invocation` returns raw unredacted `sys.argv` and unbounded `str(e)` in its `except Exception` fallback.
- Tests must exercise real runtime behavior and assert on observable outcomes, return values, global state, and file handles (no source-inspecting or code-pinning tests).

## Findings

- **F-01 (Unredacted and unbounded error strings):** Capture fallbacks store raw `str(e)` (in `get_invocation`, `SubprocessSpy`, and `SignalExitCapture._excepthook`), and `get_invocation` returns unredacted `sys.argv` on failure, which can leak credentials embedded in command arguments, Uniform Resource Identifiers (URIs), or exception messages and bloat manifests.
- **F-02 (SubprocessSpy clobbers third-party wrappers and has cross-run/concurrent-uninstall races):** Module-import-time snapshotting in `SubprocessSpy` bypasses wrappers installed between import and `install()`, unguarded restoration in `uninstall()` destroys wrappers installed after `install()`, `Popen.wait` can overwrite a later run's record index after re-install, and `os.system` indexing `cls._records[idx]` can raise `IndexError` if `uninstall()` clears `_records` concurrently.
- **F-03 (ConsoleInterceptor hides setup failure and corrupts pre-existing `faulthandler` state):** Failed log-file setup returns silently and later reports `"complete"`; `stop()` disables `faulthandler` even when the user or test runner enabled it before `pubrun`; an exception in `stdout_tee.flush()` skips closing `stdout_log` and `stderr_log`; `TqdmSafeTee` retries broken log handles and can recurse through `sys.stderr`.
- **F-04 (SignalExitCapture clobbers later signal handlers, lacks partial-install rollback, and breaks third-party `excepthook` chains):** `_restore_signal_handlers()` overwrites any third-party signal handler installed after `install()`, an exception during `_install_excepthook()` leaves signal handlers installed without rollback, and `_restore_excepthook()` clearing `self._previous_excepthook = None` breaks any post-install third-party `excepthook` still chaining through `_excepthook`.
- **F-05 (ResourceWatcher teardown fragility):** Calling `ResourceWatcher.stop()` on an unstarted thread raises `RuntimeError`, final polling inside `stop()` is unguarded and runs even on unstarted/aborted watchers, `event_stream.emit()` is unguarded in `_update_metrics()`, and self-abort after `max_consecutive_failures` still reports `capture_state.status == "complete"`.

## Proposed changes (ordered, validatable)

1. **Safe diagnostic formatter (`src/pubrun/capture/redaction.py`, `src/pubrun/capture/invocation.py`):**
   - Add `format_safe_error_detail(exc: BaseException, config: Optional[Dict[str, Any]] = None, max_len: int = 240) -> str` in `src/pubrun/capture/redaction.py`:
     - Extract `exc_type = type(exc).__name__` and raw message `str(exc)`.
     - Collapse newlines and carriage returns into single spaces and strip surrounding whitespace. If the collapsed message is empty, return `exc_type` truncated to `max_len`.
     - Redact credentials using `_redact_value_string_heuristics()` plus a key-value token pass covering `key=value`, `--flag=value`, `key: value`, `--flag value` (quoted or unquoted), and prefixed API keys (`sk-...` including hyphens/underscores) whenever the key matches `_get_secret_pattern(config)`.
     - Format as `f"{exc_type}: {redacted_msg}"` and truncate safely to `max_len` characters (preserving an `"..."` suffix when `max_len > 3`, or slicing to `max_len` when `max_len <= 3`) so no traceback or unbounded message can enter manifests or warnings.
     - Guard redaction in `try/except`: if redaction with custom `config` raises (e.g., invalid user regex), retry with `config=None` (default pattern), and if even that raises, fall back to `exc_type` so the formatter never raises or leaks raw text.
   - In `src/pubrun/capture/invocation.py::get_invocation` (fallback `except Exception as e`):
     - Redact `sys.argv` via `redact_argv(sys.argv, config)` inside a guarded block (falling back to `[]` if redaction fails) and set `capture_state` to `{"status": "failed", "detail": format_safe_error_detail(e, config)}`.

2. **Transactional and ownership-guarded `SubprocessSpy` (`src/pubrun/capture/subprocesses.py`):**
   - Keep `disable_spy()`, `pause_spy()`, `resume_spy()`, `SubprocessSpy.get_records()`, `SubprocessSpy.finalize_all()`, and `SubprocessSpy._records`/`_truncated`/`_installed` attributes backward compatible.
   - Add ownership and live-target tracking on `SubprocessSpy`:
     - `_owner: Optional[object] = None`
     - `_active_state: Optional[Dict[str, Any]] = None` (holding `{"active": True, "config": config, "prev_popen_init": ..., "prev_popen_wait": ..., "prev_os_system": ...}` per install generation)
     - `_installed_popen_init`, `_installed_popen_wait`, `_installed_os_system` (unique closure wrappers created per install generation so identity checks distinguish our wrapper from any other install or third-party wrapper).
   - In `SubprocessSpy.install(cls, max_records: int = 5000, config: Optional[Dict[str, Any]] = None, owner: Optional[object] = None) -> bool`:
     - Under `cls._lock`: if already installed, return `False` (caller does not own the existing install and must not uninstall it later).
     - Snapshot live `prev_popen_init = subprocess.Popen.__init__`, `prev_popen_wait = subprocess.Popen.wait`, `prev_os_system = os.system`.
     - Build generation-scoped wrappers that check `state["active"]` and `_spy_bypassed()` and delegate to `state["prev_*"]` (never directly to stale import-time originals). When `state["active"]` is `False`, each wrapper acts as a zero-side-effect passthrough to `state["prev_*"]`.
     - In the `Popen.__init__` wrapper: attach both `self._pubrun_state = state` and `self._pubrun_rec = rec` (in addition to appending `rec` to `cls._records`), and format failed-init `capture_state.detail` via `format_safe_error_detail(e, state["config"])`.
     - In the `Popen.wait` wrapper: update `rec` under `cls._lock` ONLY when `state["active"]` is `True` AND `getattr(self, "_pubrun_state", None) is state`, preventing a deactivated or previous-generation process from mutating a newer run's records.
     - In the `os.system` wrapper: hold a direct local reference to `rec` instead of re-indexing `cls._records[idx]` after `prev_os_system(command)` returns (preventing `IndexError` on concurrent `uninstall()`), update `rec` under `cls._lock` only when `state["active"]` is `True`, and format failed-call `capture_state.detail` via `format_safe_error_detail(e, state["config"])`.
     - Patch targets sequentially, tracking each patched target in a local list. If patching any target raises, immediately restore only the targets patched so far (when still identical to our wrapper), set `state["active"] = False`, leave `cls._installed = False`, `cls._owner = None`, and re-raise so the caller (`Run`) can isolate and record the failure.
     - Set `cls._installed = True`, `cls._owner = owner`, and return `True`.
   - In `SubprocessSpy.uninstall(cls, owner: Optional[object] = None) -> None`:
     - Under `cls._lock`: if not `cls._installed`, return. If `owner is not None and cls._owner is not None and owner is not cls._owner`, return (do not touch another run's hooks).
     - Flip `state["active"] = False` first so any wrapper remaining under a later third-party wrapper stops recording immediately.
     - Restore `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` independently (each in its own `try/except`), restoring a target ONLY if the current attribute `is` the wrapper stored for this install.
     - Clear `cls._installed = False`, `cls._owner = None`, `cls._active_state = None`, `cls._records = []`, `cls._truncated = False`.

3. **Transactional `ConsoleInterceptor` with `faulthandler` ownership and non-recursive `TqdmSafeTee` (`src/pubrun/capture/console.py`):**
   - In `TqdmSafeTee`:
     - Track `self._log_write_failed = False` and `self._in_error_log = False`.
     - If writing to `self.log_file` fails (e.g., storage lost or read-only), continue passing output through to `self.original_stream`, mark `self._log_write_failed = True`, detach `self.log_file = None` (preventing repeated failing syscalls on every `print()`), and guard any single debug/warning log with `self._in_error_log` so it never recursively writes through a wrapped `sys.stderr`.
     - In `flush()`: guard `self.original_stream.flush()` against `(BrokenPipeError, OSError, ValueError)` (matching `write()`), and wrap the `self.log_file` buffer flush in `try/except` (marking `self._log_write_failed = True` and detaching `self.log_file = None` on error) so a broken log handle never breaks `sys.stdout.flush()` or `ConsoleInterceptor.stop()`.
   - In `ConsoleInterceptor`:
     - Track `self._started = False`, `self._failed_detail: Optional[str] = None`, `self._faulthandler_owned = False`, `self._faulthandler_was_enabled = False`, `self._cached_result: Optional[Dict[str, Any]] = None`, and `self._config: Optional[Dict[str, Any]] = config` (optional keyword argument defaulting to `None` for backward compatibility with `ConsoleInterceptor(run_dir, mode)`).
     - In `start(self) -> bool`:
       - If `self.mode == "off"`, return `True`.
       - Reset `self._cached_result = None` and capture live `self.original_stdout = sys.stdout` and `self.original_stderr = sys.stderr` at `start()` time.
       - Open `stdout.log` and `stderr.log`, wrap `sys.stdout` and `sys.stderr` with `TqdmSafeTee`, and check `faulthandler.is_enabled()` BEFORE touching `faulthandler`:
         - Record `self._faulthandler_was_enabled = bool(faulthandler.is_enabled())`.
         - Enable `faulthandler.enable(file=self.stderr_log)` ONLY if `not self._faulthandler_was_enabled` (do not hijack an already-enabled user or test-runner `faulthandler`), setting `self._faulthandler_owned = True` only when `faulthandler.enable(...)` succeeded.
       - If ANY step in `start()` raises: record `self._failed_detail = format_safe_error_detail(e, self._config)`, call `self._cleanup_resources()` to roll back only the streams, files, and `faulthandler` state created in this attempt, set `self._started = False`, and return `False` (never silently pretending setup succeeded).
       - Set `self._started = True` and return `True`.
     - In `stop(self) -> Dict[str, Any]`:
       - If `self._cached_result is not None`, return a copy of `self._cached_result` (idempotent).
       - Run every cleanup step independently (each in its own `try/except`, never letting one cleanup failure skip the next):
         1. Restore `sys.stdout` if `self.stdout_tee is not None and sys.stdout is self.stdout_tee`.
         2. Restore `sys.stderr` if `self.stderr_tee is not None and sys.stderr is self.stderr_tee`.
         3. Flush `self.stdout_tee`, capture `line_count` and `_log_write_failed`, and detach `self.stdout_tee.log_file = None`.
         4. Flush `self.stderr_tee`, capture `line_count` and `_log_write_failed`, and detach `self.stderr_tee.log_file = None`.
         5. Restore `faulthandler` BEFORE closing `self.stderr_log`: call `faulthandler.disable()` ONLY when `self._faulthandler_owned` is `True` (and reset `self._faulthandler_owned = False`). Never disable a pre-existing user `faulthandler`.
         6. Close `self.stdout_log` and set `self.stdout_log = None`.
         7. Close `self.stderr_log` and set `self.stderr_log = None`.
       - Build, store in `self._cached_result`, and return the final console result dict:
         - If `self._failed_detail` is set (startup failed): `stdout.captured = False`, `stderr.captured = False`, `path = None`, `lines_captured = None`, and `capture_state = {"status": "failed", "detail": self._failed_detail}`.
         - Else if `self.mode == "off"`: `captured = False`, `path = None`, `lines_captured = None`, `capture_state = {"status": "complete"}`.
         - Else if runtime log writes failed (`tee._log_write_failed`): `capture_state = {"status": "partial", "detail": "console log write failed during execution"}`.
         - Else: `capture_state = {"status": "complete"}`.

4. **Ownership-guarded `SignalExitCapture` and resilient `ResourceWatcher` (`src/pubrun/capture/signals.py`, `src/pubrun/capture/resources.py`):**
   - In `SignalExitCapture`:
     - Accept optional `config: Optional[Dict[str, Any]] = None` in `__init__` (default `None` for full backward compatibility).
     - Add `self._installed_handlers: Dict[int, Callable] = {}`, `self._active: bool = False`, `self._signals_unavailable: bool = False`, and `self._install_error: Optional[str] = None`.
     - In `install()`:
       - Set `self._active = True`.
       - In `_install_signal_handlers()`: keep per-signal `(OSError, ValueError)` handling (non-main-thread / unsettable signal) as an expected skip rather than an install abort; if all signals were skipped, set `self._signals_unavailable = True` and emit the existing `"signal capture unavailable"` warning. For each successfully registered signal, record both `self._previous_handlers[signum] = previous` and `self._installed_handlers[signum] = shim`.
       - Then call `self._install_excepthook()`. If `_install_excepthook()` or any unexpected non-`(OSError, ValueError)` error during signal setup raises, immediately call `self._restore_signal_handlers()` and `self._restore_excepthook()` independently, set `self._active = False` and `self._installed = False`, record `self._install_error = format_safe_error_detail(e, self._config)`, and re-raise so `Run` isolates the failure cleanly.
       - Set `self._installed = True` only after install succeeds.
     - In `_make_handler()`:
       - If `not self._active`: skip recording, skip `_finalize_active_run()`, forward directly to the closure-captured `previous_handler`, and if `previous_handler is signal.SIG_DFL`, never re-install `_handler` on survival.
     - In `_install_excepthook()`:
       - Capture `prev_hook = sys.excepthook` in a local closure variable (also saving `self._previous_excepthook = prev_hook` for `_restore_excepthook()`).
       - At the top of `_excepthook`: if `not _self._active`, forward directly to `prev_hook(exc_type, exc_value, exc_tb)` (if not `None`) and return without mutating `_exit_code`, mutating `_exit_exception`, or flushing streams. This ensures that when `_restore_excepthook()` clears `self._previous_excepthook = None` while a post-install third-party `excepthook` still wraps `_excepthook`, unhandled exceptions still chain cleanly to `prev_hook`.
       - When active: preserve `"SystemExit(42)"` formatting for integer/`None` `SystemExit` codes (maintaining `tests/test_signals.py` parity), and format non-int `SystemExit` strings and other unhandled exceptions through `format_safe_error_detail(exc_value, _self._config)` (which formats `ValueError("test error")` as `"ValueError: test error"` while redacting embedded secrets and bounding length).
     - In `_restore_signal_handlers()`:
       - For each `(signum, previous)` in `list(self._previous_handlers.items())`, independently in `try/except`: check `installed_shim = self._installed_handlers.get(signum)` and restore `signal.signal(signum, previous)` ONLY when `signal.getsignal(signum) is installed_shim`. Clear both dicts.
     - In `uninstall()`:
       - Set `self._active = False` and `self._installed = False`.
       - Run `_restore_signal_handlers()` and `_restore_excepthook()` in separate `try/except` blocks so a failure in one never skips the other.
     - In `get_records()`:
       - If `self._install_error`: return `capture_state = {"status": "failed", "detail": self._install_error}`.
       - If `self._signals_unavailable`: return `capture_state = {"status": "partial", "detail": "signal handlers unavailable off main thread"}`.
       - Otherwise return `capture_state = {"status": "complete"}`.
   - In `ResourceWatcher`:
     - Track `self._aborted_due_to_failures = False`, `self._successful_samples = 0`, and `self._stopped = False`.
     - In `_update_metrics()`: increment `self._successful_samples` when `readable` is `True`; when `self._consecutive_failures >= self.max_failures`, set `self._aborted_due_to_failures = True`; before emitting to `event_stream`, check `not self._stop_event.is_set()` and wrap `event_stream.emit(...)` in `try/except` so an event-stream error never kills the polling thread.
     - In `stop()`:
       - Set `self._stop_event.set()`. Under guard, if `self._stopped`, return immediately (idempotent).
       - Check `was_started = self.ident is not None`. Call `self.join(timeout=min(self.interval + 1, 5))` ONLY if `was_started` (avoiding `RuntimeError` on unstarted threads).
       - Run the final `_update_metrics()` / `_poll_rss()` / `_poll_tree_rss()` measurement ONLY if `was_started and not self.is_alive() and not self._aborted_due_to_failures`, wrapped completely in `try/except` so a poll failure during shutdown never escapes `stop()`.
       - Set `self._stopped = True`.
     - In `to_manifest_dict()`:
       - If `self._aborted_due_to_failures`: report `capture_state = {"status": "partial", "detail": "resource polling stopped after consecutive failures"}` if `self._successful_samples > 0` else `{"status": "failed", "detail": "resource polling failed on every sample"}`. Otherwise preserve `capture_state = {"status": "complete"}` (preserving `tests/test_resources.py::test_resource_watcher_to_manifest_dict_zeros`).

5. **Behavioral tests (`tests/test_hook_ownership_rollback.py`):**
   - Test `format_safe_error_detail()` with secrets (`--api-key=...`, `--token secret`, `password: secret`, `https://user:pass@host`, `Bearer tok`, `sk-proj-...`), empty messages, multiline messages, long messages (`> 240` chars), small `max_len`, invalid custom regex config fallback, and broken redaction fallback.
   - Test `get_invocation()` failure fallback returns redacted `argv` and bounded redacted `detail`.
   - Test `SubprocessSpy`:
     - Pre-existing third-party `Popen.__init__` / `os.system` wrapper installed before `install()` is chained during run and restored on `uninstall()`.
     - Post-install third-party wrapper installed after `install()` remains intact after `uninstall()`, while `SubprocessSpy` stops recording and passes through cleanly.
     - Re-installing `SubprocessSpy` for a second run after a prior run leaves a `Popen` un-waited does not allow the old `Popen.wait()` to overwrite the new run's records; concurrent `uninstall()` during `os.system()` does not raise `IndexError`.
     - Failed `Popen.__init__` / `os.system` records redact secrets via `format_safe_error_detail()`.
     - Mid-install failure (e.g., patching `os.system` fails) rolls back `Popen.__init__` and `Popen.wait` cleanly and leaves `_installed == False`.
     - Wrong `owner` token cannot uninstall another run's active `SubprocessSpy`.
   - Test `ConsoleInterceptor`:
     - Failure opening `stderr.log` after `stdout.log` opened closes `stdout.log`, leaves `sys.stdout`/`sys.stderr` untouched, and reports `capture_state.status == "failed"` with `captured == False`.
     - Pre-existing `faulthandler.enable()` stays enabled after `ConsoleInterceptor.start()` and `stop()`; when `faulthandler` is explicitly disabled before `start()` (restoring prior pytest `faulthandler` state in `finally`), `pubrun` enables it on `start()` and disables it on `stop()`.
     - Third-party wrapper installed over `sys.stdout` or `sys.stderr` after `start()` survives `stop()` and continues writing without errors after `stdout.log`/`stderr.log` are closed.
     - Failure inside `stdout_tee.flush()` during `stop()` still flushes `stderr_tee`, restores `faulthandler`, and closes both log handles; calling `stop()` twice is idempotent and preserves `lines_captured`.
     - Runtime `OSError` on log write or flush preserves passthrough to `original_stream` without raising, detaches the broken handle, and avoids recursive stderr writes.
   - Test `SignalExitCapture`:
     - Post-install third-party signal handler on `SIGUSR1` (Unix) or `SIGINT` survives `uninstall()` untouched; pre-existing handler is restored when still owned.
     - Chaining through a deactivated `pubrun` signal shim after `uninstall()` forwards to the prior handler without recording new signals or calling `_finalize_active_run()`.
     - Post-install third-party `sys.excepthook` wrapping `pubrun`'s `_excepthook` continues chaining to the original `prev_hook` after `uninstall()` without recording `_exit_code`/`_exit_exception`.
     - Active `_excepthook` redacts secret values in unhandled exception messages while keeping `"SystemExit(42)"` intact.
     - Failure in `_install_excepthook()` rolls back already-registered signal handlers.
     - Failure in `_restore_signal_handlers()` still restores `sys.excepthook`.
   - Test `ResourceWatcher`:
     - Calling `stop()` on an unstarted `ResourceWatcher` does not raise and does not poll; calling `stop()` twice is idempotent; a poll exception during `stop()` or an `event_stream.emit()` exception in `_update_metrics()` does not escape; consecutive poll failures yield honest `"failed"` or `"partial"` `capture_state`.

## Deferred / out of scope (with reason)

- `Run` per-engine isolation, narrow ghost-mode rollback orchestration, `ArtifactWriter`/`EventStream` runtime failure handling, and manifest schema extensions belong to child plan `ed0yds` (tracker per-engine failure isolation, narrow ghost mode, and independent finalization).
- Downstream consumer updates (`pubrun report`, `pubrun inspect`, `pubrun methods`) belong to child plan `26euz0` (partial manifest diagnostics, inspect findings, and methods honesty).
- Overhead benchmarking and documentation updates belong to child plan `zp2yyu` (isolation overhead measurement, documentation reconciliation, and whole-Set verification).

## Scope check

- Over-scope: none. Touches only the six capture engine modules and one new focused test module (7 Scope-Paths, 5 E-items).
- Under-scope: none. Covers every engine-level ownership, transactional install/rollback, `faulthandler`, and diagnostic redaction requirement from backlog item `x21s6w` (isolate capture failures and roll back partially installed hooks).

## Required tests / validation

Run inside the repository root and capture actual runner output and exit code:

```bash
pytest tests/test_hook_ownership_rollback.py tests/test_signals.py tests/test_capture.py tests/test_resources.py tests/test_redaction.py tests/test_quality.py tests/test_edge_cases.py tests/test_pause_resume.py -v
pytest tests/test_cli.py -k "faulthandler or excepthook" -v
```

## Spec / documentation sync

Deferred to child plan `zp2yyu` (isolation overhead measurement, documentation reconciliation, and whole-Set verification), which updates `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`, `docs/api.md`, and `docs/performance.md` after `p6pon8`, `ed0yds`, and `26euz0` execute.

## Open questions

### OQ-01: `faulthandler` policy when already enabled before `pubrun` starts

- Blocking: no
- Status: resolved
- Owner: plan author (confirmable upon plan approval)
- Resolution or deferral rationale: Python's standard-library `faulthandler` module exposes `is_enabled()` but does not expose the file object previously passed to `faulthandler.enable(file=...)`. Re-enabling `faulthandler` onto `stderr.log` when it was already enabled would make exact restoration impossible and would disable a user's or test runner's `faulthandler` on `stop()`. Therefore `ConsoleInterceptor.start()` enables `faulthandler` on `stderr.log` only when `faulthandler.is_enabled()` is `False`, and `stop()` disables `faulthandler` only when this interceptor enabled it.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition)—as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction—name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Diff of `src/pubrun/capture/redaction.py` and `src/pubrun/capture/invocation.py` showing `format_safe_error_detail()` (bounded, single-line, redacted, empty-message and invalid-regex fallback-safe) and redacted `get_invocation()` fallback, plus pasted `pytest tests/test_redaction.py -v` output (exit code 0).
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Diff of `src/pubrun/capture/subprocesses.py` showing live target snapshotting at `install()`, transactional rollback on partial patch failure, owner-guarded and identity-guarded `uninstall()`, generation-tagged `Popen` records, direct record reference in `os.system`, redacted failure details, and passive passthrough when deactivated.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Diff of `src/pubrun/capture/console.py` showing transactional `start()` rollback with honest `"failed"` `capture_state`, prior `faulthandler.is_enabled()` ownership preservation, idempotent independent cleanup steps in `stop()`, and non-recursive bounded `TqdmSafeTee` log-write/flush error handling.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Diff of `src/pubrun/capture/signals.py` and `src/pubrun/capture/resources.py` showing `_installed_handlers` identity-guarded signal restoration, preserved non-main-thread `(OSError, ValueError)` partial behavior, transactional `install()` rollback, independent `uninstall()` cleanup, closure-captured `prev_hook` and `_active` deactivation on both signal shims and `_excepthook`, redacted `_exit_exception`, and safe idempotent `ResourceWatcher.stop()` (skipping join/poll on unstarted or aborted watchers) with honest self-abort `capture_state`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted `pytest tests/test_hook_ownership_rollback.py tests/test_signals.py tests/test_capture.py tests/test_resources.py tests/test_redaction.py tests/test_quality.py tests/test_edge_cases.py tests/test_pause_resume.py -v` and `pytest tests/test_cli.py -k "faulthandler or excepthook" -v` output showing exit code 0 and zero failures across all ownership, rollback, third-party wrapper, `faulthandler`, and second-cleanup-failure tests.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Open question OQ-01 is resolved for review; do not execute until a human approves this plan (`- Status: approved`).
2. Scope fence: this plan declares `src/pubrun/capture/redaction.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/console.py`, `src/pubrun/capture/signals.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/invocation.py`, and `tests/test_hook_ownership_rollback.py` as its Scope-Paths. Any unavoidable out-of-scope edit or unmodified declared path must be justified at finalization via `--scope-reason` or `--scope-ack`; stop and report only for genuinely unsafe conditions (such as an unresolvable concurrent-edit conflict or missing prerequisite).
3. Honesty rule: paste the actual `pytest` runner output and exit code into each `V-*` `Observed evidence:` field; never claim tests passed without running them.
4. Commit discipline: commit only the files changed for this plan using `aw commit p6pon8 -- <paths>`; never use `git add -A`, `git add .`, or `git commit -a`; never push without explicit human instruction.
5. Lifecycle transition on completion: when running under an `aw` runner, the runner owns the lifecycle transition via `aw ipd finalize`; when executing manually outside a runner, run `aw ipd lint --phase pre-transition` and, once it passes, finalize through `aw ipd finalize` (never a hand-rolled `git mv` to `executed/`).
