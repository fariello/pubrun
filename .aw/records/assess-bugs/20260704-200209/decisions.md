# Decisions - assess-bugs round 2 20260704-200209

## Scope
Assessed only code added today after the first bugs IPD was executed:
- `capture/console.py` (resolve_console_mode, _is_jupyter_kernel)
- `capture/resources.py` (_get_tree_rss_linux, _get_tree_rss_darwin, scope param)
- `core.py` (phase profiling hooks)
- `capture/packages.py` (imported-transitive mode)

## Key decisions
- BUG2-02 (Linux tree walk): confirmed correct on re-analysis. The recursive
  `pids_to_check` pattern correctly discovers all descendants.
- BUG2-05 (shared list reference): correct Python behavior, not a bug.
- BUG2-07 (isatty delegation): __getattr__ on TqdmSafeTee correctly delegates.
- The macOS tree issues (BUG2-01, BUG2-06) are real and should be fixed together
  by restructuring _get_tree_rss_darwin to always start with self RSS.
