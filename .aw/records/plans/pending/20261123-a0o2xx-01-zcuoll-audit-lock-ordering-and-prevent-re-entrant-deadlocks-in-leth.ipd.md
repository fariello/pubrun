# IPD: Audit lock ordering and prevent re-entrant deadlocks in lethal-signal finalization

- Date: 2026-11-23
- Kind: child
- Concern: Concurrency safety and signal-handler deadlock prevention
- Scope: Make every lock acquire reached from `src/pubrun/capture/signals.py::_finalize_active_run` bounded while a lethal signal (`SIGTERM`, `SIGHUP`) is being finalized, with a lock-free fallback that still writes `manifest.json`. Covers the same-thread form (the interrupted main thread holds a plain lock that finalization needs) and the cross-thread form (the `pubrun-hw` thread holds `_run_lock` and waits on a lock the interrupted main thread holds). Source modules: `signals.py`, `tracker.py`, `writer.py`, `events.py`, `capture/file_io.py`, `capture/subprocesses.py`, and `capture/resources.py`; plus `tests/test_signals.py`, `docs/architecture.md`, and `CHANGELOG.md`.
- Scope-Paths: src/pubrun/capture/signals.py, src/pubrun/tracker.py, src/pubrun/writer.py, src/pubrun/events.py, src/pubrun/capture/file_io.py, src/pubrun/capture/subprocesses.py, src/pubrun/capture/resources.py, tests/test_signals.py, docs/architecture.md, CHANGELOG.md
- Item-Dependencies: executed:focjwv
- Status: reviewed
- Readiness: go-pending-approval
- Review-Depth: complex
- Work-Kind: followup
- Priority: medium
- From-Backlog: a0o2xx
- Set: a0o2xx
- Order: 1
- Highest E allocated: 09
- Author: Antigravity
- Id: zcuoll

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 /plan-review (uri/its_direct/pt3-claude-opus-5.5-1m-us): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-007, PR-008, PR-009, PR-010
- 2026-11-24 to-review (Antigravity): graduated from backlog item `a0o2xx` into a review-ready plan.
- 2026-11-24 draft (Antigravity): created.

## Goal

When `SIGTERM` or `SIGHUP` reaches a process that pubrun is tracking, pubrun's signal handler writes the final `manifest.json` (outcome `interrupted`) and then lets the signal kill the process. Today that handler can block forever on a lock, so the process hangs instead of exiting and the manifest stays at outcome `running`. After this plan:

1. A lethal signal always ends the process within a bounded time (the regression tests use 30 seconds), whichever pubrun lock the interrupted code holds.
2. The final `manifest.json` is still written, with outcome `interrupted` and the signal recorded.
3. Outside signal finalization, every lock behaves exactly as it does today.
4. `docs/architecture.md` states the signal-context lock rule next to the existing lock-ordering rule.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Bounded lock helper and its callers

- [ ] E-01 Add the bounded lock helper `finalization_lock` and the lock inventory comment to `src/pubrun/capture/signals.py`.
  - Depends on: none
  - Expected outcome: (1) A context manager `finalization_lock(lock, timeout)` yields `True` when it holds `lock` and `False` when it gave up; outside signal finalization it acquires with a normal blocking `with lock:` and always yields `True`. (2) During signal finalization (while the existing `_finalizing_active_run` latch is set) it calls `lock.acquire(timeout=timeout)`, and a lock that already timed out once in the current finalization is tried with `acquire(blocking=False)` only. (3) `_finalize_active_run` clears that timed-out set in its `finally` block. (4) A comment above `_finalize_active_run` lists every lock in the inventory table under "Findings", its type, and its signal-context behavior, including the locks this plan deliberately leaves unchanged. (5) `in_signal_finalization()` returns the latch value.
  - Execution state: pending

- [ ] E-02 Route the finalization-path acquires in `src/pubrun/tracker.py` through `finalization_lock`, with a lock-free fallback.
  - Depends on: E-01
  - Expected outcome: The `_run_lock` acquires inside `Run._finalize_state` (2.0-second bound) and the `_errors_lock` and `_data_files_lock` acquires in `Run._check_section_failed`, `Run._store_capture_error_detail`, and `Run.to_manifest_dict` (0.25-second bound) use the helper. When the helper yields `False`, the code does the same work without the lock: it reads snapshots with `list(...)`, `dict(...)`, and `set(...)` copies and writes with single `append`, `add`, or attribute assignments. It never skips `_finalize_state` or the manifest write.
  - Execution state: pending

- [ ] E-03 Bound the `_write_lock` acquire in `src/pubrun/writer.py::ArtifactWriter.write_artifacts`.
  - Depends on: E-01
  - Expected outcome: `write_artifacts` takes `_write_lock` through `finalization_lock(self._write_lock, 2.0)`. When the helper yields `False`, it still runs the same body (config persistence, `_mark_finalization_end`, `to_manifest_dict`, the atomic `manifest.json` write) without the lock. `write_startup_manifest` and `sync_config_if_changed` keep their current blocking `with self._write_lock:`.
  - Execution state: pending

- [ ] E-04 Bound the `EventStream._lock` acquires in `src/pubrun/events.py`.
  - Depends on: E-01
  - Expected outcome: `EventStream.emit` and `EventStream.close` take `_lock` through `finalization_lock(self._lock, 0.25)`. When the helper yields `False`, `emit` drops the event and `close` returns without closing; the operating system closes the file when the process exits. Outside signal finalization both methods behave as today.
  - Execution state: pending

- [ ] E-05 Bound the `_data_files_lock` and `FileIoBudgetTracker._lock` acquires reached during finalization in `src/pubrun/capture/file_io.py`.
  - Depends on: E-01
  - Expected outcome: `finalize_pending_registrations` (both of its lock blocks), `get_or_create_budget_tracker`, and every `FileIoBudgetTracker` method (`check_before_hash`, `check_stream_progress`, `consume_chunk`, `commit_stream_hash`, `record_outcome`, `to_summary_dict`) take their lock through `finalization_lock(lock, 0.25)`. When the helper yields `False`, each one does its work lock-free: copy and clear the pending list, create the tracker if the attribute is still `None`, or read and update the counters directly.
  - Execution state: pending

- [ ] E-06 Bound the `SubprocessSpy._lock` acquires in `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all` and `::SubprocessSpy.uninstall`.
  - Depends on: E-01
  - Expected outcome: Every `with cls._lock:` block inside those two methods, whatever shape the methods have at execution time, takes the lock through `finalization_lock(cls._lock, 0.25)`. When the helper yields `False`, `finalize_all` iterates over `list(cls._records)` and `uninstall` restores the patched targets without the lock. The patched `Popen` and `os.system` wrappers keep their blocking acquires.
  - Execution state: pending

- [ ] E-07 Bound the `ResourceWatcher._lock` acquires and the thread join in `src/pubrun/capture/resources.py::ResourceWatcher.stop` and `::ResourceWatcher.to_manifest_dict`.
  - Depends on: E-01
  - Expected outcome: Each `with self._lock:` block in those two methods takes the lock through `finalization_lock(self._lock, 0.25)` and reads or writes the fields lock-free when the helper yields `False`. During signal finalization, `stop` joins the sampler thread for at most 0.5 seconds instead of up to 5 seconds. The sampler thread methods (`_update_metrics`, `_sample_system_metrics`) keep blocking acquires.
  - Execution state: pending

### Task group 2: Regression tests and documentation

- [ ] E-08 Add the helper unit tests and the real-signal regression tests to `tests/test_signals.py`.
  - Depends on: E-02, E-03, E-04, E-05, E-06, E-07
  - Expected outcome: The new classes `TestFinalizationLock` and `TestLethalSignalWhileLockHeld` exist, with every test named in "Proposed changes" item 8. Each held-lock case runs in a child Python process that receives a real `SIGTERM`, so an unfixed deadlock fails the test by timeout instead of hanging pytest.
  - Execution state: pending

- [ ] E-09 Document the signal-context lock rule in `docs/architecture.md` and add a `### Fixed` entry to `CHANGELOG.md`.
  - Depends on: E-08
  - Expected outcome: The "Lock ordering" bullet in `docs/architecture.md` gains the rule that, during lethal-signal finalization, every lock acquire on the finalization path is bounded and falls back to lock-free work. `CHANGELOG.md` `## [Unreleased]` `### Fixed` gains one entry describing the fixed hang in plain language.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by symbol (`path::Name`), Markdown by heading (`path#Heading text`), or by a quoted content string. A line number may follow one of those as a hint, but never stands alone (`IPD-C801`).
- Commit `94e504a` changed `src/pubrun/capture/signals.py::SignalExitCapture.get_records` to call `self._lock.acquire(blocking=False)` and to take its snapshot lock-free when the lock is busy. Its docstring names the cross-thread mechanism: "A background manifest refresh calls this while holding `pubrun.core._run_lock`; if the main thread holds `_lock` and a lethal signal makes it finalize (which takes `_run_lock`), a blocking acquire here would deadlock both threads." That commit left backlog item `a0o2xx` to cover the remaining locks.
- `src/pubrun/capture/signals.py::SignalExitCapture._make_handler` calls `_finalize_active_run()` on the main thread for a lethal signal whose previous handler was `SIG_DFL`, then restores `SIG_DFL` and re-sends the signal with `os.kill`. `_finalize_active_run` sets the module latch `_finalizing_active_run` for the duration of the call and calls `run.writer.write_artifacts()` inside `try/except Exception`.
- `src/pubrun/tracker.py::Run.__init__` installs the signal handlers (in `_bootstrap_engines`) before it writes the startup manifest, so a signal can arrive during that first write.
- The `pubrun-hw` thread (`Run._bootstrap_engines`, nested `_collect_hardware`) holds `_run_lock` across `ArtifactWriter.write_startup_manifest(is_refresh=True)`, which takes `_write_lock` and then calls `Run.to_manifest_dict`. The code comment there reads "Always acquire _run_lock before _write_lock."
- `README.md` promises that pubrun "never alters, slows, or crashes the program it observes".
- Test outcomes, not code structure: tests must exercise runtime behavior (holding locks, delivering signals, reading the manifest) and must not inspect source code with `ast`, `inspect`, regex, or substring matching. Tests that start a child Python process pass `cwd=tmp_path` and use a stdout handshake rather than a fixed `time.sleep` (conventions from sibling plan `m66tfv`).
- `tests/conftest.py` prepends this checkout's `src` to `PYTHONPATH` for child processes.
- Run pytest from the repository root; `pyproject.toml` adds coverage options, so targeted runs pass `--no-cov`.

## Findings

A lethal signal runs pubrun's handler on the main thread, between two bytecodes of whatever the main thread was doing. If that code was inside a `with lock:` block of a plain `threading.Lock`, and finalization needs the same lock, the handler waits for a lock that its own thread holds. The process never exits. A second form needs two threads. The `pubrun-hw` thread holds `_run_lock` and waits on a lock the main thread holds, while the handler on the main thread waits on `_run_lock`.

Lock inventory. Each "Probe" result is from a review-time script under `/tmp/opencode` (Linux, CPython 3.14): a daemon thread held the lock and called `_finalize_active_run()`, and "hangs" means it was still blocked after 4 seconds.

| Lock | Type | Reached during finalization by | Probe | This plan |
|---|---|---|---|---|
| `src/pubrun/core.py` `_run_lock` | `RLock` | `Run._finalize_state` | Same thread: re-enters. Cross-thread with `pubrun-hw`: hangs (with `_errors_lock` and with `_write_lock`) | E-02, 2.0 s bound |
| `src/pubrun/writer.py::ArtifactWriter._write_lock` | `RLock` | `ArtifactWriter.write_artifacts` | Same thread: re-enters. Cross-thread: `pubrun-hw` can hold it inside `_run_lock` | E-03, 2.0 s bound |
| `src/pubrun/tracker.py::Run._errors_lock` | `Lock` | `Run._check_section_failed`, `Run._store_capture_error_detail`, `Run.to_manifest_dict` | Hangs. A real `SIGTERM` to a child holding it: no exit after 3 s, manifest outcome `running` | E-02 |
| `src/pubrun/tracker.py::Run._data_files_lock` | `Lock` | `Run.to_manifest_dict`, `src/pubrun/capture/file_io.py::finalize_pending_registrations` | Hangs | E-02, E-05 |
| `src/pubrun/capture/file_io.py::FileIoBudgetTracker._lock` | `Lock` | `FileIoBudgetTracker.to_summary_dict` (from `Run.to_manifest_dict`) | Hangs | E-05 |
| `src/pubrun/events.py::EventStream._lock` | `Lock` | `EventStream.close` (teardown step 5 in `Run._rollback_owned_hooks`) | Hangs | E-04 |
| `src/pubrun/capture/subprocesses.py::SubprocessSpy._lock` | `Lock` (class) | `SubprocessSpy.finalize_all`, `SubprocessSpy.uninstall` | Hangs (when the run owns the spy) | E-06 |
| `src/pubrun/capture/resources.py::ResourceWatcher._lock` | `Lock` | `ResourceWatcher.stop`, `ResourceWatcher.to_manifest_dict` | Hangs | E-07 |
| `src/pubrun/__init__.py` `_commit_lock` | `Lock` | `Run.to_manifest_dict` via `from pubrun import __commit__` | Returns: the startup manifest write caches the commit before the run is published as the active run, so `_get_commit` returns the cached value without the lock. It hangs only after the test helper `pubrun._reset_commit_cache()` | None, documented |
| `src/pubrun/capture/signals.py::SignalExitCapture._lock` | `RLock` | `SignalExitCapture.get_records`, `SignalExitCapture.record_exit_code` | Already fixed by `94e504a` | None |
| `src/pubrun/capture/console.py::TqdmSafeTee._lock` | `RLock` | Not taken by `ConsoleInterceptor.stop` | Not reached | None |
| `src/pubrun/capture/packages.py` `_CACHE_LOCK` and `_DistributionIndex._files_lock` | `Lock` | `Run._refresh_packages_at_finalization` | Hangs in the probe, but the main thread holds it only at startup (before the handlers are installed) or inside `_finalize_state` after `_finalized` is latched, and a nested `_finalize_state` then returns at once | None, documented |
| `src/pubrun/writer.py` `_durability_warn_lock`, `src/pubrun/capture/file_io.py` `_warn_lock` | `Lock` | Only when a configuration value is invalid | Returns | None, documented |
| `src/pubrun/_bootstrap.py` `_lock`, `src/pubrun/core.py` `_start_lock`, `_pubrun_log_lock` | `Lock` | Not reached (`_bootstrap.get_import_metadata` takes no lock) | Returns | None, documented |

Making the plain locks re-entrant (`RLock`) would fix only the same-thread form. The cross-thread form needs every wait on the finalization path to be bounded. So this plan bounds each acquire during signal finalization and falls back to lock-free work, the pattern commit `94e504a` used. Lock-free work is safe here for three reasons. Single `list.append`, `set.add`, `list(...)`, and attribute assignments are atomic under the GIL. The other lock holder is either blocked or about to be killed with the process. `manifest.json` is written through a temporary file and `os.replace`, so a reader never sees a partial file.

```mermaid
flowchart TD
    S[Lethal signal arrives on main thread] --> H[SignalExitCapture handler]
    H --> F[_finalize_active_run sets the finalizing latch]
    F --> W[write_artifacts and _finalize_state]
    W --> L{finalization_lock acquires within its bound?}
    L -->|acquired| A[Work under the lock]
    L -->|timed out| B[Same work without the lock]
    A --> M[manifest.json written with outcome interrupted]
    B --> M
    M --> R[Restore SIG_DFL and re-send the signal]
```

## Proposed changes (ordered, validatable)

1. **`src/pubrun/capture/signals.py` (E-01).**
   - Add `finalization_lock(lock, timeout)` as a `contextlib.contextmanager`. Outside signal finalization (`_finalizing_active_run` is false) it runs `with lock: yield True`. Inside, it calls `lock.acquire(blocking=False)` when `id(lock)` is in a module set `_timed_out_locks`, otherwise `lock.acquire(timeout=timeout)`. On failure it adds `id(lock)` to `_timed_out_locks` and yields `False`; on success it yields `True` and releases in `finally`.
   - Clear `_timed_out_locks` in the `finally` block of `_finalize_active_run`, next to the reset of `_finalizing_active_run`.
   - Add the lock inventory comment above `_finalize_active_run`: one line per row of the "Findings" table, with the rule "during signal finalization, never block without a bound; on timeout, do the work lock-free and still write the manifest".
   - The latch is process-wide, so a `pubrun-hw` or sampler thread that reaches the helper during the finalization window also gets a bounded acquire. That is intended: it can only shorten a wait, and the window ends when the process is killed.
   - Add `in_signal_finalization()`, which returns the latch value, for callers that need it outside a lock (E-07).
   - The helper and the timed-out set use only the standard library, so every caller can import it without an import cycle (`signals.py` imports no pubrun module at top level). `Lock.acquire(timeout=...)` exists on every supported Python (3.8 to 3.14).
2. **`src/pubrun/tracker.py` (E-02).** Replace `with _run_lock:` in `Run._finalize_state` (three blocks) with `with finalization_lock(_run_lock, 2.0) as _held:`. The bound matches the existing `_hardware_future_done.wait(timeout=2.0)`, because `pubrun-hw` legitimately holds `_run_lock` across a durable manifest write. Replace the `_errors_lock` blocks in `Run._check_section_failed`, `Run._store_capture_error_detail`, and `Run.to_manifest_dict`, and the `_data_files_lock` block in `Run.to_manifest_dict`, with `finalization_lock(lock, 0.25)`. The body is the same in both branches; only the acquire changes. No branch skips work.
3. **`src/pubrun/writer.py` (E-03).** In `ArtifactWriter.write_artifacts`, replace `with self._write_lock:` with `with finalization_lock(self._write_lock, 2.0):` and keep the body unchanged. The `_finalize_state` call stays before the lock, which preserves the `_run_lock`-before-`_write_lock` order.
4. **`src/pubrun/events.py` (E-04).** In `EventStream.emit`, when the helper yields `False`, return without writing. In `EventStream.close`, when it yields `False`, return without touching `_file` or `_buffer`. Buffered non-critical events can be lost in that case; critical events are flushed when they are emitted.
5. **`src/pubrun/capture/file_io.py` (E-05).** Apply the helper with a 0.25-second bound to `finalize_pending_registrations` (both lock blocks), `get_or_create_budget_tracker`, and every `with self._lock:` block in `FileIoBudgetTracker`. The lock-free branch copies and clears the pending list, creates the tracker when `run_instance._file_io_budget` is still `None`, or reads and updates the counters directly.
6. **`src/pubrun/capture/subprocesses.py` (E-06).** Apply the helper with a 0.25-second bound to each `with cls._lock:` block in `SubprocessSpy.finalize_all` and `SubprocessSpy.uninstall`. Plan `focjwv` rewrites `finalize_all` into several lock phases, and `- Item-Dependencies: executed:focjwv` makes this plan run after it, so the helper is applied to the final shape of every lock block. Do not change the lock-free `Popen.__del__` hook that `focjwv` adds.
7. **`src/pubrun/capture/resources.py` (E-07).** Apply the helper with a 0.25-second bound to each `with self._lock:` block in `ResourceWatcher.stop` and `ResourceWatcher.to_manifest_dict`. In `stop`, call `self.join(timeout=0.5)` when the finalizing latch is set; otherwise keep `min(self.interval + 1, 5)`. Read the latch through `in_signal_finalization()` (E-01), so no module reads the private global directly.
8. **`tests/test_signals.py` (E-08).**
   - `TestFinalizationLock` (in-process, no signal): each test sets and resets `pubrun.capture.signals._finalizing_active_run` in `try/finally`, and any lock it holds is held by a helper thread that the test releases afterwards.
     - `test_blocks_normally_outside_signal_finalization`: with the latch false, a lock released by another thread after 0.3 s is acquired and the helper yields `True`.
     - `test_gives_up_within_bound_during_signal_finalization`: with the latch true and the lock held by another thread, the helper yields `False` within `timeout + 1.0` seconds.
     - `test_skips_wait_for_lock_that_already_timed_out`: a second use of the same busy lock yields `False` in under 0.1 seconds.
     - `test_finalize_active_run_clears_timed_out_locks`: after `_finalize_active_run()` returns, the timed-out set is empty and the latch is false.
   - `TestLethalSignalWhileLockHeld` (POSIX only, `skipif(sys.platform == "win32")`): `test_sigterm_finalizes_while_lock_held` is parametrized over the cases below. The test writes a child script to `tmp_path` and starts it with `subprocess.Popen(..., cwd=tmp_path)`. The child calls `pubrun.start(events={"enabled": True})`, waits on `run._hardware_future_done.wait(5)`, prints `run.run_dir`, takes the case's lock, prints `held`, and sleeps 60 seconds while holding it. The parent reads both lines, sends `SIGTERM`, and calls `proc.wait(timeout=30)`. On `TimeoutExpired` it kills the child and fails with "process hung after SIGTERM while holding <case>". It then asserts `proc.returncode == -signal.SIGTERM`, `manifest["status"]["outcome"] == "interrupted"`, and `"SIGTERM"` among `manifest["signals"]["signals_received"][*]["signal_name"]`.
     - `errors_lock`: `run._errors_lock`.
     - `data_files_lock`: `run._data_files_lock`.
     - `file_io_budget_lock`: `get_or_create_budget_tracker(run)._lock`.
     - `event_stream_lock`: `run.event_stream._lock` (the child asserts `run.event_stream is not None` first).
     - `subprocess_spy_lock`: `SubprocessSpy._lock` (the child asserts `run._spying_subprocesses` first).
     - `resource_watcher_lock`: `run.resource_watcher._lock` (the child asserts `run.resource_watcher is not None` first).
     - `write_lock_vs_hw_refresh`: the child holds `run.writer._write_lock`, sets `run.writer._startup_included_hardware = False`, and starts a thread that takes `pubrun.core._run_lock`, sets an `Event`, and calls `run.writer.write_startup_manifest(is_refresh=True)`. The child waits on the `Event` before printing `held`.
     - `errors_lock_vs_hw_refresh`: the same shape, with the child holding `run._errors_lock` and the thread calling `run._check_section_failed("hardware", {"capture_state": {"status": "failed"}})` under `_run_lock`.
   - Keep `TestLethalSignalFinalization::test_lethal_signal_finalization_sigterm` as the uncontended check that a plain `SIGTERM` still writes an `interrupted` manifest.
9. **`docs/architecture.md` and `CHANGELOG.md` (E-09).** Extend the "Lock ordering" bullet in `docs/architecture.md` with the signal-context rule from E-01. Add a `CHANGELOG.md` entry under `## [Unreleased]` `### Fixed`, written for users with no em or en dashes, for example: "A SIGTERM or SIGHUP no longer hangs the process when it arrives while pubrun is recording a file, an error, a subprocess, an event, or a resource sample. pubrun now waits a bounded time for its own locks while finalizing after a signal, so the run still finalizes as `interrupted` and the process exits."

## Deferred / out of scope (with reason)

- Running the new tests on the GitHub Actions matrix (3 OS x Python 3.8 to 3.14). `AGENTS.md` "Matrix-validation discipline" applies to behavior that varies by OS, and signal delivery is POSIX-only (the new signal tests skip on Windows). A push needs an explicit human instruction, so this plan validates on Linux only and V-08 records which OS and Python version ran.
  - Carrier-Declined: a push needs explicit human authorization, so no plan can carry it; GitHub Actions runs the matrix automatically on the next push or pull request to `main`.
- `pubrun._commit_lock`, `packages._CACHE_LOCK`, `_DistributionIndex._files_lock`, `_durability_warn_lock`, `file_io._warn_lock`, `_bootstrap._lock`, `_start_lock`, and `_pubrun_log_lock` stay unchanged. The inventory table in "Findings" gives the evidence for each: the main thread does not hold them where a signal can trigger a finalization that needs them.
  - Carrier-Declined: no deadlock path was found for these locks; E-01's inventory comment records why, so a later change that adds a path can see it.
- A `pubrun-hw` refresh that has already passed its `not self._finalized` check can replace `manifest.json` after a lock-free final write, if it finishes before the re-sent signal kills the process. That needs a thread that is neither blocked nor finished during the few milliseconds between the final write and `os.kill`.
  - Carrier-Declined: the window is a few milliseconds, the refreshed manifest is still a complete file, and closing it would need a cross-thread write fence that adds a new blocking point to signal handling.
- File hashing done by `finalize_pending_registrations` during signal finalization is bounded only by the user's `[capture.file_io]` budgets (default `max_total_hash_seconds = 0.0`, unlimited). That is slow, not a deadlock.
  - Carrier-Declined: no report exists of slow signal exits from hashing, and the existing budgets already let a user bound it.

## Scope check

- Over-scope: none. Every Scope-Paths file either holds a lock from the "Findings" inventory that this plan changes, holds the tests, or documents the changed behavior.
- Under-scope: none after review. The review added `src/pubrun/events.py` and `src/pubrun/capture/file_io.py` (locks the original plan missed), the cross-thread form with `pubrun-hw`, `docs/architecture.md` (lock-ordering contract), and `CHANGELOG.md`.

## Required tests / validation

- `pytest tests/test_signals.py --no-cov -q -v` passes, including every test named in "Proposed changes" item 8 (on Linux and macOS; the `TestLethalSignalWhileLockHeld` cases skip on Windows).
- `pytest tests/test_signals.py tests/test_tracker.py tests/test_writer.py tests/test_events.py tests/test_file_registration.py tests/test_file_io_provenance.py tests/test_capture.py tests/test_resources.py tests/test_hook_ownership_rollback.py tests/test_core_lifecycle_bugs.py tests/test_capture_isolation.py --no-cov -q` passes. These suites exercise the changed lock sites on the normal path.
- The full suite (`aw suite --no-cache`) has no failure that also passes on unmodified `HEAD`.
- Mutation check: temporarily change the signal-finalization branch of `finalization_lock` to a plain blocking `lock.acquire()` that yields `True`, then run `pytest tests/test_signals.py -k "errors_lock or write_lock_vs_hw_refresh" --no-cov -q`. Each case must fail with the "process hung after SIGTERM" message. Restore the file and confirm `git diff --stat` matches the intended edit.
- `git diff -U0 -- docs/architecture.md CHANGELOG.md | grep '^+[^+]' | grep -c '[—–]'` prints `0`.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- `docs/architecture.md` (E-09) documents the lock-ordering contract, and this plan adds the signal-context rule to it.
- `CHANGELOG.md` (E-09) records the user-visible fix.
- `docs/functional_spec.md` describes the normal `stop()` and `_finalize_state()` order, which does not change, so it is not edited.
- No manifest field, CLI option, or configuration key changes.
- No `.spec.md` file under `.aw/records/specs/` describes signal finalization, so none is touched.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- src/pubrun/capture/signals.py`, and for each of E-01 outcomes 1 to 5 name the added lines that satisfy it. (2) Paste the four `TestFinalizationLock` result lines from the V-08 run (E-08 creates them), each `PASSED`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: (1) Paste `git diff -- src/pubrun/tracker.py`, and name each changed acquire in `Run._finalize_state`, `Run._check_section_failed`, `Run._store_capture_error_detail`, and `Run.to_manifest_dict`. (2) Paste the `errors_lock`, `data_files_lock`, and `errors_lock_vs_hw_refresh` result lines of `test_sigterm_finalizes_while_lock_held` from the V-08 run, each `PASSED`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: (1) Paste `git diff -- src/pubrun/writer.py`, showing that only the `_write_lock` acquire in `ArtifactWriter.write_artifacts` changed. (2) Paste the `write_lock_vs_hw_refresh` result line from the V-08 run, `PASSED`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: (1) Paste `git diff -- src/pubrun/events.py`, and name the changed acquires in `EventStream.emit` and `EventStream.close`. (2) Paste the `event_stream_lock` result line from the V-08 run, `PASSED`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: (1) Paste `git diff -- src/pubrun/capture/file_io.py`, and name the changed acquires in `finalize_pending_registrations`, `get_or_create_budget_tracker`, and each `FileIoBudgetTracker` method. (2) Paste the `file_io_budget_lock` and `data_files_lock` result lines from the V-08 run, each `PASSED`.
  - Observed evidence:
  - Result: pending

- [ ] V-06 validates E-06
  - Required evidence: (1) Paste `git diff -- src/pubrun/capture/subprocesses.py`, and name each changed acquire in `SubprocessSpy.finalize_all` and `SubprocessSpy.uninstall`. (2) Paste the `subprocess_spy_lock` result line from the V-08 run, `PASSED`.
  - Observed evidence:
  - Result: pending

- [ ] V-07 validates E-07
  - Required evidence: (1) Paste `git diff -- src/pubrun/capture/resources.py`, and name each changed acquire and the join timeout in `ResourceWatcher.stop` and `ResourceWatcher.to_manifest_dict`. (2) Paste the `resource_watcher_lock` result line from the V-08 run, `PASSED`, and its duration from `--durations=0`, which must be under 10 seconds.
  - Observed evidence:
  - Result: pending

- [ ] V-08 validates E-08
  - Required evidence: (1) Paste the `pytest tests/test_signals.py --no-cov -q -v --durations=0` result lines for every test named in "Proposed changes" item 8, each `PASSED`. (2) Paste the summary line of the eleven-file related-suites run from "Required tests / validation". (3) Paste the full-suite summary line, and for any failure paste the same test's result on unmodified `HEAD`. (4) Paste the failing result lines from the mutation check, then `git diff --stat` after restoring. (5) State which OS and Python version ran the tests, and that the CI matrix was not run.
  - Observed evidence:
  - Result: pending

- [ ] V-09 validates E-09
  - Required evidence: (1) Paste `git diff -- docs/architecture.md CHANGELOG.md`, showing the extended "Lock ordering" bullet and the entry under `## [Unreleased]` `### Fixed`. (2) Paste the output of `git diff -U0 -- docs/architecture.md CHANGELOG.md | grep '^+[^+]' | grep -c '[—–]'`, which must print `0`. (3) Paste the output and exit code of `python3 scripts/sanitize_paths.py --check --all`, which must be 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: 9 E-items and 10 Scope-Paths exceed the `IPD-Z603` guidance (5 and 8). Each E-item is one step on one file. They stay in one plan because they deliver one invariant (a lethal signal never hangs the process), and the cross-thread regression cases in E-08 pass only when E-02 and E-03 both land; E-04 to E-07 each depend only on the E-01 helper. A split into a Set (helper with `tracker.py` and `writer.py`; then `events.py` with `file_io.py`; then `subprocesses.py` with `resources.py`) is recorded in the review record as a non-blocking alternative.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no open questions.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries (`src/pubrun/capture/signals.py`, `src/pubrun/tracker.py`, `src/pubrun/writer.py`, `src/pubrun/events.py`, `src/pubrun/capture/file_io.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/resources.py`, `tests/test_signals.py`, `docs/architecture.md`, `CHANGELOG.md`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`. The mutation check edits `src/pubrun/capture/signals.py` only temporarily and must restore it.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit zcuoll -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize zcuoll`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize zcuoll` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
