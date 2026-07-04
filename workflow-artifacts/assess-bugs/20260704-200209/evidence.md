# Evidence - assess-bugs round 2 20260704-200209

## Files inspected
- `src/pubrun/capture/console.py:1-55` (resolve_console_mode, _is_jupyter_kernel)
- `src/pubrun/capture/resources.py:62-265` (tree RSS functions, ResourceWatcher scope)
- `src/pubrun/core.py:243-304` (phase profiling hooks)
- `src/pubrun/capture/packages.py:60-119` (imported-transitive mode)

## Verification
- Linux tree walk traced manually: pids_to_check pattern correctly recurses.
- macOS pgrep -P verified via man page: "-P ppid: Restrict matches to processes
  with a parent process ID in the given list" — single level only.
- cProfile.Profile.enable()/disable() verified: remains active until disable().
- required_by shared-list pattern verified: appends to same list object, which is
  also referenced by the record. Mutations propagate correctly.
