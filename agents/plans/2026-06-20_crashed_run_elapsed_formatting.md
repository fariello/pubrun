# Implementation Plan - Elapsed Timing Formatting and Crashed Run Timing Fallback

This plan details the design and implementation changes to:
1. **Timing fallback for crashed runs**: Update `close_out_crashed_run` in `src/pubrun/status.py` to set `ended_at_utc` and `elapsed_seconds` to `None` in fallback manifests (since the exact crash timing is unknown), and make the fallback manifest fully JSON schema compliant.
2. **Elapsed time formatting**: Update `_format_elapsed` in `src/pubrun/status.py` to format elapsed times as `HH:MM:SS` (or `Xd HH:MM:SS` if $\ge$ 24h) and return `"unknown"` if the elapsed time is `None`.
3. **Unit Tests**:
   - Update `test_format_elapsed` in `tests/test_status.py` to check the new `HH:MM:SS`, `Xd HH:MM:SS`, and `"unknown"` formatting.
   - Add a test verifying that when a crashed run gets closed out and listed via `pubrun status`, its elapsed time shows up as `"unknown"`.
4. **Version bump**: Bump the version to `1.0.1` in `pyproject.toml` since `1.0.0` has already been published.

## User Review Required

> [!NOTE]
> Since version `1.0.0` was published, this release will be version `1.0.1`. We will update the project metadata version and generate new package builds.

---

## Proposed Changes

### [Component] Telemetry and Usability

#### [MODIFY] [status.py](file://~/VC/pubrun/src/pubrun/status.py)
- Update `close_out_crashed_run` to:
  - Write `None` for `"ended_at_utc"` and `"elapsed_seconds"` under `"timing"`.
  - Include missing required schema fields (`capture` section, `capture_state` fields) to ensure fallback manifests strictly validate against `schemas/manifest.schema.json`.
- Update `_format_elapsed` to:
  - Return `"unknown"` if `seconds is None`.
  - Format elapsed seconds as `HH:MM:SS` (and `Xd + HH:MM:SS` if the duration is $\ge$ 24 hours).
  - Handle negative seconds gracefully.

#### [MODIFY] [pyproject.toml](file://~/VC/pubrun/pyproject.toml)
- Bump version from `"1.0.0"` to `"1.0.1"`.

---

### [Component] Tests

#### [MODIFY] [test_status.py](file://~/VC/pubrun/tests/test_status.py)
- Update `test_format_elapsed` assertions.
- Add `test_crashed_run_elapsed_time_unknown` to:
  - Simulate a crashed run by creating a stale `.pubrun.lock` file.
  - Scan and trigger the status close-out.
  - Verify that the closed-out run shows `"unknown"` for its elapsed time in the status rendering.

---

## Verification Plan

### Automated Tests
- Run `pytest` to execute all 522 unit and integration tests.

### Manual Verification
- Simulate a crashed run (with a lock file and dead PID), execute `pubrun status`, and verify it gets closed out and printed with the elapsed column set to `"unknown"`.
- Run a successful command and verify that its elapsed time prints in `HH:MM:SS` format.
