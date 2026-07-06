# TODO

Known issues and deferred improvements for future releases.

---

## Deferred ideas (need their own design pass / IPD)

### Scoped in-code pause/resume of capture

A context manager to temporarily suspend capture for a block, e.g.:

```python
with pubrun.paused():            # or pubrun.suppress(console=True, ...)
    noisy_untracked_work()
# capture resumes here
```

Desirable ergonomic, but **not trivial and not low-risk**, so it is deferred to its
own IPD rather than bundled with other work:

- The console tee and subprocess spy are **process-global monkeypatches** on
  `sys.stdout`/`subprocess`. Pausing means unwrapping and later re-wrapping them; if
  other code (or another thread) touches `sys.stdout` in the window, streams can be
  lost or double-wrapped — a correctness hazard.
- It is **not thread-safe by nature**: a "pause" on the main thread would also blind a
  worker thread's output during the window (shared global state).
- The resource watcher / event stream can be paused cleanly; the monkeypatch engines
  (console, subprocess) are the risky ones and need characterization tests.

Orthogonal to import modes — wanted regardless of which mode is active. Any
implementation IPD must address the concurrency/global-state hazards explicitly.

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

### Process-tree resource capture and profiling

Two related capabilities that are currently missing:

**1. Total process-tree RAM and CPU usage**

The current `ResourceWatcher` tracks only the main process (`os.getpid()`). For
workloads that spawn child workers (multiprocessing, Dask, Ray, subprocess pipelines),
the reported peak RSS drastically underestimates actual resource usage.

Proposed:
- Walk `/proc/<pid>/task/` or use platform APIs to sum RSS/CPU across the process tree.
- On Linux: iterate `/proc/<pid>/children` recursively or use cgroups v2 `memory.current`.
  (Prefer whichever is more performant; cgroups is single-read but only works if the
  process is in its own cgroup. /proc walk is universal but racy.)
- On macOS: `pgrep -P <pid>` or `proc_listchildpids` via ctypes.
- Config: `[capture.resources].scope = "process" | "tree"` (default `"process"`).
- Must work with zero dependencies using only stdlib + /proc / platform APIs.

Open design questions (need discussion before implementation):
- Should `scope = "tree"` be available on bare `import pubrun` or only in explicit
  modes / deeper profiles?
- Visualization: tree-level data should be graphed separately from main-process data
  in `pubrun report` (e.g., "Process RSS" vs "Process Tree RSS" as distinct series).
- Need a way to view this in `pubrun status` and the TUI when present.

**2. Profiling integration (phase-scoped)**

Allow pubrun to capture profiling data for specific `pubrun.phase()` blocks and save
it to the run directory. Phase-scoped only (not whole-run) because:
- Whole-run profiling adds 30-50% overhead, violating "zero footprint."
- Whole-run cProfile is trivially available via `python -m cProfile script.py`.
- Phase-scoped profiling tied to pubrun's timeline is genuinely new and useful.

Proposed:
- `[capture.profiling].enabled = false` (opt-in only).
- `[capture.profiling].backend = "cprofile" | "pyspy" | "yappi"` etc.
- When enabled, `pubrun.phase().__enter__` calls `cProfile.enable()` and
  `__exit__` calls `disable()` + dumps to `profile-<phase_name>.prof`.
- `cprofile` backend uses stdlib — zero dependencies.
- External backends (pyspy, yappi) require user to install the tool;
  pubrun detects availability at runtime and logs a clear error if missing.
- **Any backend that requires a dependency MUST be opt-in only** — never auto-install,
  never fail the run if the tool is absent (just log and skip).
- Viewable via `pubrun report` alongside the phase timeline.

### Runs directory index for fast `pubrun status` (PERF-09)

When a user accumulates 500+ runs, `pubrun status` gets slow because it reads and
parses `manifest.json` (or `.pubrun.lock`) from every single run directory. A
lightweight index file (`.pubrun-index.json`) in the runs directory could cache the
key metadata (run_id, status, started_at, script, exit_code) so status queries are
O(1) instead of O(n).

Deferred because: most users clean regularly and won't hit 500 runs. Implement only
after benchmarking confirms >1s scan time at realistic run counts.

### Transitive/full package capture modes

The current `imported-only` mode (default) records only packages loaded in
`sys.modules`. This misses indirect dependencies (e.g., your script imports `pandas`
but you'd also want to know the exact `numpy` version pandas is using).

Two modes to add:
- `imported-transitive`: for each imported package, also record its declared
  dependencies (read from dist metadata). Still fast — no full env scan.
- `full-environment`: already supported as opt-in config, iterates all installed
  distributions (slower, ~50-200ms in large venvs).

### `summary.txt` Generation (`[logging].write_summary`)

**Removed.** A human-readable glance file was planned but is superseded by:

- `pubrun status <run-id>` — Shows the same information interactively.
- `pubrun report --basic` — Produces a full diagnostic summary.
- `manifest.json` — Machine-readable and more complete.

Writing a redundant text file to every run directory adds disk I/O, increases the
run directory footprint, and provides no information not already available via the
CLI. The config key is retained as "not yet implemented / reserved" for users who
may want it in the future.
