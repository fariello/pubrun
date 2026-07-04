# TODO

Known issues and deferred improvements for future releases.

---

## Removed from Roadmap

### Determinism Tracking (`[capture.determinism]`)

**Removed.** Recording pseudorandom seeds (`random.getstate()`, `numpy.random.get_state()`,
`torch.manual_seed()`) was considered but rejected for the following reasons:

1. **Fragile detection**: Detecting which RNG libraries are in use requires probing
   optional imports (numpy, torch, tensorflow, jax) at runtime. Each has a different
   API surface, and versions change frequently.
2. **Locking seeds is harmful**: Overwriting user seeds would break scripts that
   intentionally use randomness for exploration. Recording-only is the only safe option.
3. **Recording-only has limited value**: If the user didn't explicitly set a seed,
   recording the internal RNG state is useless for reproduction — the state is opaque
   and not portable across library versions.
4. **Better solved by the user**: A single `pubrun.annotate(seed=42)` call is more
   explicit, safer, and requires no magic detection.

The `[capture.determinism].depth = "off"` config key is retained for forward compatibility
but documented as "not yet implemented / reserved."

---

## Needs Assessment

### Default `import pubrun` behavior — STDIN/STDOUT capture

Assess whether the default behavior of a bare `import pubrun` (auto mode) is correct
and user-friendly with respect to STDIN/STDOUT interception. Specifically:

- Is console tee (`capture_mode = "standard"`) the right default for all users, or
  should it default to `"off"` and require opt-in?
- Does wrapping `sys.stdout`/`sys.stderr` break interactive prompts, `input()`, REPL
  sessions, debuggers (pdb), or piped workflows?
- Are there edge cases where the tee silently corrupts output (encoding, binary pipes,
  non-UTF-8 streams)?
- Should `import pubrun` in a Jupyter/IPython notebook behave differently than in a
  script?

This should be a dedicated `/assess-*` pass (likely assess-bugs or assess-ui-ux) focused
on the STDIN/STDOUT surface before the next release.

### `summary.txt` Generation (`[logging].write_summary`)

**Removed.** A human-readable glance file was planned but is superseded by:

- `pubrun status <run-id>` — Shows the same information interactively.
- `pubrun report --basic` — Produces a full diagnostic summary.
- `manifest.json` — Machine-readable and more complete.

Writing a redundant text file to every run directory adds disk I/O, increases the
run directory footprint, and provides no information not already available via the
CLI. The config key is retained as "not yet implemented / reserved" for users who
may want it in the future.
