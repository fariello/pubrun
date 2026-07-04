# IPD: Console Capture Default Behavior and Context-Aware Overrides

- Date: 20260704
- Concern: usability / correctness / default behavior
- Scope: `[console]` config, `capture/console.py`, `default.toml`, Jupyter detection
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Change the default `capture_mode` from `"standard"` to `"off"` so that a bare
`import pubrun` does NOT wrap `sys.stdout`/`sys.stderr` unless the user opts in.
Add context-aware overrides (Jupyter auto-disable, non-TTY differentiation) so
that when capture IS enabled, it behaves correctly in every environment.

This addresses the "zero footprint" promise: a library that replaces sys.stdout
on import without being asked is surprising and can break interactive workflows,
piped pipelines, and notebook environments.

## Project conventions discovered (Step 0)

- Pending-plans location: `.agents/plans/pending/` (YYYYMMDD-slug.md)
- Stack: Python 3.8+, zero runtime deps except tomli on <3.11
- Existing behavior: `capture_mode = "standard"` wraps stdout/stderr with
  `TqdmSafeTee` that tees to `stdout.log`/`stderr.log` with timestamps.
- User base: small, intimate, known to the author. Author knows all current users.

## Background and design rationale

### Why the tee operates on strings (not bytes)

`sys.stdout` in Python 3 is a `TextIOWrapper` — it only accepts `str`. The
binary layer (`sys.stdout.buffer`) is a separate object that pubrun does not
wrap. This is architecturally correct:

- The tee inherits the type contract of `sys.stdout.write(data: str)`.
- Binary output (via `sys.stdout.buffer.write()`) bypasses the tee entirely.
- The `\r`/`\n` splitting, timestamp prefixing, and log writes all operate on
  `str` because that's what the text layer receives.
- This means piped binary consumers still work — the passthrough calls
  `original_stream.write(data)` unchanged.

No change proposed to this architecture. It is correct.

### Why default should be "off"

1. **Surprise principle**: Most observability libraries don't replace sys.stdout
   on import. Users who didn't ask for capture are surprised to find their
   stdout is being tee'd to disk.
2. **Interactive breakage risk**: `input()`, pdb, IPython, curses — anything
   expecting raw terminal interaction could behave oddly with a proxy.
3. **Performance**: Every print() goes through extra function calls + string
   splitting + file write. Measurable in ML epoch logging with millions of lines.
4. **Redundancy in CI**: CI systems already capture stdout. Tee to file is
   double-writing for no benefit.
5. **The value is still available**: Users who want it set one config key.

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| CON-01 | Medium | Low | Novice/Power-user | default.toml | Default `capture_mode = "standard"` wraps stdout on bare import without user consent | `resources/default.toml:83` |
| CON-02 | Medium | Low | Engineer | Jupyter | No detection of IPython/Jupyter kernel — tee wraps Jupyter's custom stdout wrapper, risking double-wrapping or output corruption | `capture/console.py:125-130` — always wraps regardless of context |
| CON-03 | Low | Low | Power-user | Config | No way to differentiate capture behavior between TTY and non-TTY contexts | No config key exists for context-specific behavior |
| CON-04 | Low | Low | Novice | Docs/CHANGELOG | Changing the default is a user-visible behavior change that needs clear migration guidance | N/A — documentation gap |

## Proposed changes (ordered, validatable)

| Step | Source | Change | Files | Remediation Risk | Validation |
|------|--------|--------|-------|------------------|------------|
| 1 | CON-01 | Change `capture_mode` default from `"standard"` to `"off"` in `default.toml`. | `src/pubrun/resources/default.toml` | Low | `import pubrun` no longer wraps stdout; verify with `assert sys.stdout is original_stdout` after import. Existing tests that depend on capture must pass config override. |
| 2 | CON-02 | Add Jupyter/IPython detection in `ConsoleInterceptor.start()`. If `IPython` is in `sys.modules` and has a running kernel, skip tee installation even if `capture_mode != "off"` — unless the user explicitly set capture_mode (not just the default). | `src/pubrun/capture/console.py` | Low | Test: mock IPython kernel detection, verify tee is not installed. Test: explicit `capture_mode = "standard"` in config overrides detection. |
| 3 | CON-03 | Add `[console].non_tty_mode` config key: `"inherit"` (default, same as capture_mode), `"off"`, or `"basic"`. When stdout is not a TTY and non_tty_mode is set, use that mode instead of capture_mode. | `src/pubrun/resources/default.toml`, `src/pubrun/capture/console.py` | Low | Test: mock `isatty() = False`, verify non_tty_mode is applied. |
| 4 | CON-02 | Add `[console].jupyter_mode` config key: `"off"` (default) or any valid capture_mode. This is what's used when Jupyter is detected. Users who want capture in notebooks set `jupyter_mode = "standard"`. | `src/pubrun/resources/default.toml`, `src/pubrun/capture/console.py` | Low | Test: with Jupyter detected and `jupyter_mode = "standard"`, verify capture activates. |
| 5 | CON-04 | Update CHANGELOG.md with the default change. Add migration note: "If you relied on automatic stdout/stderr capture, add `capture_mode = \"standard\"` to your `.pubrun.toml`." | `CHANGELOG.md` | Low | Human review. |
| 6 | CON-04 | Update `docs/configuration.md` with the new `non_tty_mode` and `jupyter_mode` keys and the rationale for the default change. | `docs/configuration.md` | Low | Human review. |

## Deferred / out of scope (with reason)

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| (none) | — | — | All findings Low remediation risk. | — |

## Scope check

- Over-scope: None.
- Under-scope: A `[console].ci_mode` (auto-detect CI via `CI=true` env var) was
  considered but deferred — users in CI can set `capture_mode = "off"` in their
  CI config or via `PUBRUN_PROFILE`. Adding yet another context key is over-scope
  for now. Revisit if users ask for it.

## Implementation notes

### Jupyter detection logic

```python
def _is_jupyter_kernel() -> bool:
    """Detect if running inside a Jupyter/IPython kernel."""
    try:
        if "IPython" not in sys.modules:
            return False
        from IPython import get_ipython
        ip = get_ipython()
        if ip is None:
            return False
        # ZMQInteractiveShell = Jupyter kernel; TerminalInteractiveShell = IPython CLI
        return ip.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False
```

### Config resolution for console mode

```python
def _resolve_console_mode(config: dict) -> str:
    """Resolve the effective console capture mode considering context."""
    base_mode = config.get("console", {}).get("capture_mode", "off")
    
    if base_mode == "off":
        return "off"
    
    # Jupyter override
    if _is_jupyter_kernel():
        jupyter_mode = config.get("console", {}).get("jupyter_mode", "off")
        return jupyter_mode
    
    # Non-TTY override
    if not sys.stdout.isatty():
        non_tty_mode = config.get("console", {}).get("non_tty_mode", "inherit")
        if non_tty_mode != "inherit":
            return non_tty_mode
    
    return base_mode
```

## Required tests / validation

1. **Default behavior test**: `import pubrun` → `sys.stdout` is NOT wrapped.
2. **Explicit opt-in test**: `pubrun.start(capture_mode="standard")` → stdout IS wrapped.
3. **Jupyter detection test**: mock IPython kernel → capture skipped.
4. **Jupyter override test**: `jupyter_mode = "standard"` → capture active in Jupyter.
5. **Non-TTY test**: mock `isatty() = False` + `non_tty_mode = "off"` → no capture.
6. **Non-TTY inherit test**: `non_tty_mode = "inherit"` → uses capture_mode as-is.
7. **Existing capture tests**: must pass with explicit `capture_mode = "standard"` override.
8. **Full regression**: 583+ tests green.

## Spec / documentation sync

- `docs/configuration.md`: document new keys, explain defaults and rationale.
- `CHANGELOG.md`: breaking change note with migration path.
- `README.md`: if it mentions automatic output capture, update.
- Module docstring in `__init__.py`: currently lists import modes but may
  mention stdout capture behavior.

## Open questions

1. **Version bump**: This is technically a breaking change for users who rely on
   the implicit capture. Does this warrant a minor bump (1.4.0) or a major (2.0)?
   Recommendation: minor, with clear CHANGELOG migration note, since the fix is
   one line in `.pubrun.toml`.
2. **Should `import pubrun.auto` (explicit auto mode) also default to "off"
   for capture?** Recommendation: yes — the import mode controls auto-start and
   hooks, not capture depth. Capture depth is always controlled by `[console]`.
3. **Should we emit a one-time info log** when capture_mode is "off" suggesting
   users can enable it? Recommendation: no — that's spammy and violates
   zero-footprint. Users who want it will find it in docs.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed. Recommended next steps:

1. Review this IPD (optionally run the `plan-review` workflow to harden it).
2. On approval, execute the ordered changes, run the validation, and sync docs.
3. Only then move this IPD out of `pending/` per the project's lifecycle convention.
