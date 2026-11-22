- Id: 86p7x3
- Status: open
- Set: bugs-audit
- Work-Kind: followup
- Priority: low
- Summary: SubprocessSpy records no exit for a Popen child reaped only by subprocess internals (_cleanup/__del__ via _internal_poll) or never waited, so such records stay exit_code None
- Short-Description: SubprocessSpy records no exit for a Popen child reaped only by subprocess internals (_cleanup/__del__ via _internal_poll) or never waited, so such records stay exit_code None

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-22 created (aw backlog): SubprocessSpy records no exit for a Popen child reaped only by subprocess internals (_cleanup/__del__ via _internal_poll) or never waited, so such records stay exit_code None

## Detail

`src/pubrun/capture/subprocesses.py::SubprocessSpy` records a child's exit code when the host calls `Popen.wait()` or `Popen.poll()` (`poll` was added by IPD `m780uj`, BUG-38). CPython also reaps children through `Popen._internal_poll()` directly, from the module-level `subprocess._cleanup()` (run on each new `Popen`) and from `Popen.__del__`. A child that the host never waits on or polls, and that is reaped only along those internal paths, keeps `exit_code: None` and `capture_state.status: "running"` in the manifest.

Found while executing `m780uj`; out of that plan's scope, because patching the private `_internal_poll` touches a CPython implementation detail and needs its own decision.

## Acceptance criteria

- Either a child reaped only by `subprocess._cleanup()` / `Popen.__del__` records its exit code and end time, or the manifest marks the record as unreaped (a distinct status), and a behavioral test covers the chosen outcome.
