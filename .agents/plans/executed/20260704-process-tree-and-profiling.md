# IPD: Process-Tree Resource Capture and Phase-Scoped Profiling

- Date: 20260704
- Concern: feature / observability
- Scope: `capture/resources.py`, `core.py` (phase), config, manifest schema
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Add two complementary capabilities:

1. **Process-tree resource tracking**: Sum RSS and CPU across the entire process
   tree (parent + children), not just the main process. Essential for workloads
   using multiprocessing, Dask, Ray, or subprocess pipelines where the main
   process is a thin orchestrator.

2. **Phase-scoped profiling**: Capture cProfile data inside `pubrun.phase()`
   blocks and save per-phase profile files to the run directory. Phase-scoped
   only (not whole-run) because whole-run profiling adds 30-50% overhead and is
   trivially available via `python -m cProfile`.

Both are opt-in. Zero dependencies for the default backends.

## Project conventions discovered (Step 0)

- Pending-plans location: `.agents/plans/pending/` (YYYYMMDD-slug.md)
- Stack: Python 3.8+, zero runtime deps except tomli on <3.11
- Constraint: anything requiring a dependency MUST be opt-in only

## Part 1: Process-Tree Resource Capture

### Design

Config:
```toml
[capture.resources]
scope = "process"  # "process" (default, current behavior) | "tree"
```

When `scope = "tree"`, the ResourceWatcher polls RSS/CPU for the entire process
tree and reports both `tree_rss_bytes` and `process_rss_bytes` (so the single-
process metric remains available for comparison).

### Implementation strategy

**Linux (primary):**
- Read `/proc/<pid>/task/../children` recursively to discover child PIDs.
- Sum RSS from `/proc/<child_pid>/statm` for each live child.
- Alternative: if running inside a cgroup v2 (detectable via `/proc/self/cgroup`),
  read `memory.current` from the cgroup controller — single read, no races,
  includes all descendants. Preferred when available.
- CPU: sum user+system times from `/proc/<child_pid>/stat` for all children.

**macOS:**
- Use `pgrep -P <pid>` to list child PIDs, then sum via `ps -o rss= -p <pids>`.
- Or use ctypes to call `proc_listchildpids` (libproc) for a no-subprocess path.

**Windows:**
- Use `wmic process where ParentProcessId=<pid> get WorkingSetSize` or ctypes
  `CreateToolhelp32Snapshot` + `Process32First/Next` to enumerate children.

**Fallback:** If tree enumeration fails, fall back to `scope = "process"` silently
and set `capture_state.detail = "tree enumeration unavailable, fell back to process"`.

### Manifest output

```json
{
  "resources": {
    "scope": "tree",
    "peak_rss_bytes": 12345678,
    "end_rss_bytes": 10234567,
    "peak_tree_rss_bytes": 45678901,
    "end_tree_rss_bytes": 40234567,
    "peak_cpu_percent": 385.2,
    "peak_tree_cpu_percent": 785.4,
    "capture_state": {"status": "complete"}
  }
}
```

### Visualization

- `pubrun report` and TUI should display process-tree metrics as a separate
  series/graph from main-process metrics when present.
- `pubrun status` verbose mode shows tree RSS if available.

### Open design questions

1. Should `scope = "tree"` be available on bare `import pubrun` or only in
   explicit/deeper profiles? **Recommendation:** available in all modes but
   defaults to `"process"`. Users opt in via config.
2. Polling children has a race (child can exit between discovery and read).
   Accept best-effort with logged debug on failures? **Recommendation:** yes,
   same resilience pattern as current ResourceWatcher.
3. cgroups v2 path: should we auto-detect and prefer it, or make it a separate
   `scope = "cgroup"` value? **Recommendation:** auto-detect within `scope = "tree"`.

## Part 2: Phase-Scoped Profiling

### Design

Config:
```toml
[capture.profiling]
enabled = false          # opt-in only
backend = "cprofile"     # "cprofile" (stdlib) | "yappi" | "pyspy"
```

When enabled, `pubrun.phase().__enter__` enables the profiler and `__exit__`
disables it and dumps stats to `profile-<phase_name>.prof` in the run directory.

### Implementation

```python
# In core.py phase class:
class phase:
    def __enter__(self):
        # ... existing phase_start emit ...
        if self._profiling_enabled:
            import cProfile
            self._profiler = cProfile.Profile()
            self._profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._profiler:
            self._profiler.disable()
            prof_path = self.run_tracker.run_dir / f"profile-{self.name}.prof"
            self._profiler.dump_stats(str(prof_path))
            if self.run_tracker.event_stream:
                self.run_tracker.event_stream.emit(
                    "profile_saved", name=self.name,
                    payload={"path": str(prof_path)}
                )
        # ... existing phase_end emit ...
```

### Backends

| Backend | Dependency | Overhead | Output | Phase-scoped? |
|---------|-----------|----------|--------|---------------|
| `cprofile` | None (stdlib) | ~30-50% within phase | `.prof` (pstats) | Yes |
| `yappi` | `yappi` (pip) | ~10-20% | `.prof` or `.callgrind` | Yes |
| `pyspy` | `py-spy` (system binary) | ~5% (sampling) | `.svg` flamegraph | Requires separate invocation; not phase-scoped |

- `cprofile`: default, zero-dep, works everywhere.
- `yappi`: detected at runtime via `import yappi`; if missing, log warning and skip.
- `pyspy`: requires external binary; better suited as a separate tool, not integrated
  into phase(). Defer or document as "use externally."

### Manifest output

```json
{
  "profiling": {
    "enabled": true,
    "backend": "cprofile",
    "profiles": [
      {"phase": "training", "path": "profile-training.prof", "calls": 145023},
      {"phase": "evaluation", "path": "profile-evaluation.prof", "calls": 8921}
    ],
    "capture_state": {"status": "complete"}
  }
}
```

### Viewing

- `pubrun report <run>` lists available profiles with basic stats (top 10 functions).
- Users can load `.prof` files with `snakeviz`, `pstats`, or `flameprof` externally.

## Proposed changes (ordered)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Add `[capture.resources].scope` config key to default.toml | `resources/default.toml` | Low | Config resolution test |
| 2 | Implement `_get_tree_rss_linux()` using /proc walk + cgroups v2 auto-detect | `capture/resources.py` | Low | Unit test with mock /proc tree |
| 3 | Implement `_get_tree_rss_darwin()` using pgrep or ctypes | `capture/resources.py` | Low | Platform-skip test |
| 4 | Update ResourceWatcher to poll tree metrics when scope="tree" | `capture/resources.py` | Low | Integration test with multiprocessing |
| 5 | Update `to_manifest_dict()` with tree fields | `tracker.py` | Low | Manifest schema test |
| 6 | Add `[capture.profiling]` config section to default.toml | `resources/default.toml` | Low | Config test |
| 7 | Add profiling hooks to `phase.__enter__`/`__exit__` in core.py | `core.py` | Low | Phase profiling test |
| 8 | Add yappi backend detection (optional) | `core.py` or new `capture/profiling.py` | Low | Test with yappi absent (skip) and present (mock) |
| 9 | Update manifest schema with `profiling` section | `schemas/manifest.schema.json` | Low | Schema validation |
| 10 | Update docs: configuration.md, manifest.md | docs | Low | Human review |

## Deferred / out of scope

| Item | Reason |
|------|--------|
| py-spy integration | Requires external binary, not phase-scoped, better used standalone |
| Windows tree capture via CreateToolhelp32Snapshot | Implement after Linux/macOS validated; lower user priority |
| Whole-run profiling | 30-50% overhead violates zero-footprint; trivially available via `python -m cProfile` |

## Required tests / validation

1. Tree RSS on Linux: mock `/proc/<pid>/task/../children` structure; verify sum.
2. cgroups v2 detection: mock `/proc/self/cgroup` and cgroup fs; verify single-read.
3. Fallback: verify graceful degradation to scope="process" when tree fails.
4. Phase profiling: enable profiling, run a phase, verify `.prof` file exists and loads.
5. Missing backend: enable yappi when not installed; verify warning + skip.
6. Full regression: 583+ tests green.

## Spec / documentation sync

- `docs/configuration.md`: document `scope` and `[capture.profiling]` section.
- `docs/manifest.md`: document new manifest fields.
- `CHANGELOG.md`: new feature entry.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed.
