# Robust Liveness Checking and Startup Metadata Persistence

This implementation plan details changes to resolve two critical issues:
1. **WSL2 Clock Drift False Crashed Runs**: Replacing the strict 60-second start-time tolerance check with process command-line verification (script name matching) and a generous 24-hour start-time tolerance fallback to prevent active processes from being incorrectly cleaned up and flagged as "crashed".
2. **"Flying Blind" on Crashed Runs**: Writing the initial manifest at startup so that all static metadata (packages, environment, host, hardware, git) is saved to disk immediately. If a crash (OOM, SIGKILL) occurs, `pubrun status` will update the existing manifest's status and timing rather than overwriting it with a blank template.

## User Review Required

> [!IMPORTANT]
> - **Liveness Check Change**: The process liveness check (`is_same_process`) will now verify that the process PID exists **and** that the command line matches the script name recorded in the lock file.
> - **Generous Tolerance Fallback**: If the command line cannot be checked (e.g. permission limits or platform restrictions), we fall back to checking if the process start time is within **24 hours** of the expected start time (up from 60 seconds).
> - **Startup Manifest I/O**: `pubrun` will now write the initial `manifest.json` and `config.resolved.json` files to disk immediately at startup (adding a ~70–500ms startup penalty depending on the package capture mode).

## Proposed Changes

### 1. Robust Liveness Engine

#### [MODIFY] [liveness.py](file://~/VC/pubrun/src/pubrun/capture/liveness.py)
- Modify `is_same_process(pid: int, expected_start_utc: float, expected_script: Optional[str] = None, tolerance: float = 86400.0) -> bool`:
  - If `expected_script` is provided:
    - On Linux, read `/proc/<pid>/cmdline` and verify it contains `expected_script`.
    - On macOS, run `ps -o command= -p <pid>` and verify it contains `expected_script`.
    - On Windows, run `wmic process where ProcessId=<pid> get CommandLine` and verify it contains `expected_script`.
  - Fall back to the start-time check with the generous `86400.0` (24 hours) default tolerance.

### 2. Status Classification and Fallback Manifest updates

#### [MODIFY] [status.py](file://~/VC/pubrun/src/pubrun/status.py)
- In `RunInfo._classify()`:
  - Prioritize `has_lock` check over `has_manifest` check so that active/crashed runs are processed via the lock file first.
  - If both lock and manifest files are present, call a new helper `_enrich_from_manifest()` to load all static metadata (packages, env vars, git, host, hardware) from the startup manifest.
  - Pass `expected_script=self.script` to `is_same_process()` during lock-file loading.
- In `close_out_crashed_run(run_dir: Path, lock_data: Optional[Dict[str, Any]])`:
  - If `manifest.json` already exists in the run directory, read its content.
  - Update only the `status.outcome` to `"crashed"`, set `timing.ended_at_utc` to current time, and calculate `timing.elapsed_seconds` relative to the original start time.
  - Rewrite the updated manifest back to disk, preserving all captured packages, environment variables, git, host, and hardware specs.

### 3. Startup Metadata Persistence

#### [MODIFY] [tracker.py](file://~/VC/pubrun/src/pubrun/tracker.py)
- In `Run.start()`:
  - Right after `self._initialize_capture()`, call `self.writer.write_artifacts()` to save the initial snapshot of `manifest.json` and `config.resolved.json` to the run directory immediately.
- Update `self._outcome` default/initial state to `"running"` (representing active execution), which will be written to the startup manifest. It will be updated to `"completed"`, `"failed"`, or `"interrupted"` during `stop()`.

---

## Verification Plan

### Automated Tests
- Run `PYTHONPATH=$(pwd)/src pytest` to verify all 546 unit tests continue to pass.
- Add new unit tests to `tests/test_liveness.py` to assert:
  - `is_same_process` correctly matches a running PID and command name.
  - `is_same_process` falls back gracefully to a generous start-time check when the command name cannot be inspected.
  - `is_same_process` returns `False` if the PID is dead.
- Add unit tests to verify that `start()` writes the initial manifest files and `close_out_crashed_run` updates the existing manifest correctly without clobbering it.

### Manual Verification
- Simulate a crashed run:
  1. Run a script that sleeps (e.g. `python -m pubrun run -- python -c "import time; time.sleep(10)"`).
  2. Kill the process forcefully (`kill -9 <pid>`).
  3. Verify that `manifest.json` was written at startup and contains all package list and env vars.
  4. Run `pubrun status` to trigger fallback closeout, and verify that the manifest's status updates to `"crashed"`, while preserving the packages and env vars list.
