# TODO

Known issues and deferred improvements for future releases.

---

## Release-time actions (MUST do when publishing the next PyPI release)

### Yank all BSD-3-Clause versions from PyPI after the next release is up

pubrun ≤ 1.3.0 was published under **BSD-3-Clause**; the project relicensed to
**Apache-2.0** afterward. When the next Apache-2.0 release (currently targeted as
**1.4.0**) is published to PyPI, **yank every BSD-era release** so no one keeps
installing the old-licensed code.

Steps (maintainer / operator — done at release time):
1. Publish the new Apache-2.0 version to PyPI first (so a valid install target exists;
   never leave the package with zero installable versions).
2. Yank the BSD-3-Clause versions: on PyPI → project → "Manage" → each old release →
   "Options" → **Yank** (or `pip`-side, there's no yank; use the web UI or the PyPI API).
   Yank — do NOT delete — so existing pinned installs still resolve but new installs skip
   them.
3. Confirm `pip install pubrun` resolves to the new Apache-2.0 version and that the
   yanked versions show the "yanked" banner on PyPI.

Ties in with the pending Zenodo DOI / v1.4.0 release work (concept DOI
`10.5281/zenodo.20801582` currently points at the old v1.2.0 archive; the new release
re-points it — see the citation-DOI executed IPD).

---

## Deferred ideas (need their own design pass / IPD)

### Benchmark result JSON is too big for the GitHub submission path (needs re-evaluation)

The `pubrun bench` redacted result JSON is roughly **2.5x or more over what the GitHub
issue-submission flow allows** (GH issue bodies cap around 65 KB; a recent redacted result is
~200 KB on disk, ~128 KB serialized). The community-contribution flow submits this JSON via a GitHub
issue, so it currently will not fit. We can very likely cut it to **less than half without losing
data**; needs a follow-up design pass / IPD.

Where the size goes (measured on `benchmarks/results/<host>-20260711T004237Z.redacted.json`,
~128 KB serialized):

- `pass_results` 60%, `scenarios` 20%, `baseline` 17% - almost all of it is the raw per-iteration
  **`timings` arrays** (each scenario keeps a `timings` list of ~30 floats, across 23 scenarios x 3
  passes + baseline).
- Each timing float is stored at full `repr` precision (e.g. `0.019290073003503494`, ~18 sig figs),
  which is meaningless for wall-clock timings and inflates every number ~3x.

Candidate reductions (the IPD decides; all preserve analytical value):

1. **Round timings** to a sane precision (e.g. microseconds / 6-9 sig figs). Alone this likely cuts
   the raw-timing bytes ~2-3x with zero loss of usable signal.
2. **Reconsider storing raw per-iteration `timings` at all in the SUBMITTED file** - the per-scenario
   summary stats (`n/min/median/mean/p95/max/stdev`) are already computed and stored; the raw arrays
   may be kept in the LOCAL full result but omitted (or heavily downsampled) from the redacted
   submission. This is the biggest lever.
3. Deduplicate structure repeated per pass (`scenarios` config/group/mode/workload repeat identically
   across passes and baseline).

Constraints/notes: keep the schema versioned (bump it), keep the local full result complete (only the
SUBMITTED/redacted artifact must fit GH), and update `pubrun bench`'s submit guidance + any size check.
Cross-ref the bench command in `src/pubrun/__main__.py` and the schema in the bench tooling.

### Scoped in-code pause/resume of capture

A context manager to temporarily suspend capture for a block
(`with pubrun.paused(): ...`). Desirable ergonomic, but not low-risk — the console
tee and subprocess spy are process-global monkeypatches, so pausing them raises
interleaving/thread-safety hazards. Captured as an early proposal IPD (with the
design questions spelled out) at
`.agents/plans/pending/20260705-scoped-pause-resume.md` — not yet ready to execute.

### `pubrun show config` family — inspect resolved config for three contexts

Add a `config` view to `pubrun show` that renders the resolved configuration for three
distinct contexts, so users can see exactly what settings are (or were) in effect:

- **`pubrun show config`** — the config that *would* be in effect right now if the user
  ran `import pubrun` in the current directory (i.e. resolve the full 5-layer hierarchy —
  built-in → user → local → env → API-less — as of now). Answers "what will pubrun do if
  I import it here?"
- **`pubrun show run config [<run identifier>]`** — the config as it was *actually
  resolved for a past run*. Reuse the standard run-selection criteria (recency index /
  id prefix / path; default to the most recent run when the identifier is omitted). This
  is already durable per run as `config.resolved.json` in the run dir
  (`writer.py:73`, referenced from the manifest at `tracker.py:633`), so this view mostly
  reads and renders that file.
- **`pubrun show default config`** — the shipped built-in defaults only
  (`src/pubrun/resources/default.toml`), i.e. what you get with zero user/local/env/API
  input. (Overlaps the existing `--show-config` flag; unify or cross-reference.)

Requirement across all three: **highlight any ambiguities and how they were resolved**
— e.g. a local-config key that overrode a home-config key, or (if `profile` is kept) a
`profile`-implied default that an explicit `capture.*` key overrode. The stretch goal is
a design where *no* ambiguity is possible (single source of truth), in which case this
view simply confirms "no conflicts." This ties directly to the config-provenance idea
raised in the meta-ref/profile decision (recording override provenance in the manifest is
useful independent of the `profile` outcome). Needs its own design pass / IPD:
CLI grammar (`show config` vs. `show <run> config` disambiguation with the existing
`show <run> <section>` form), and the ambiguity-detection/rendering.

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
