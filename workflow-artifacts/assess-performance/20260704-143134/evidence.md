# Evidence - assess-performance 20260704-143134

## Files inspected (complete source reads)

| File | Lines | Relevance |
|------|-------|-----------|
| `src/pubrun/__init__.py` | 146 | Import router, boot sequence trigger |
| `src/pubrun/core.py` | 670 | Public API, ProvenanceFileProxy, print(), open(), subprocess wrappers |
| `src/pubrun/tracker.py` | 569 | Run init, _bootstrap_engines(), manifest construction |
| `src/pubrun/events.py` | 112 | EventStream emit/close/migrate |
| `src/pubrun/writer.py` | 103 | ArtifactWriter, atomic JSON writes |
| `src/pubrun/status.py` | 1021 | RunInfo classification, scan_runs, filter_runs, clean_runs |
| `src/pubrun/config.py` | 140 | Config resolution, deep merge, TOML loading |
| `src/pubrun/_bootstrap.py` | 281 | Import mode state, conflict detection |
| `src/pubrun/_config_boot.py` | 87 | Lightweight boot-time config resolver |
| `src/pubrun/capture/console.py` | 190 | TqdmSafeTee write/flush |
| `src/pubrun/capture/signals.py` | 258 | Signal handler installation, chaining |
| `src/pubrun/capture/resources.py` | 163 | ResourceWatcher thread, RSS/CPU polling |
| `src/pubrun/capture/subprocesses.py` | 204 | SubprocessSpy monkeypatches |
| `src/pubrun/capture/git.py` | 70 | Git provenance (4 subprocess calls) |
| `src/pubrun/capture/packages.py` | 71 | Package enumeration |
| `src/pubrun/capture/hardware.py` | 181 | CPU/RAM/GPU detection (subprocesses) |
| `src/pubrun/capture/environment.py` | 27 | Env var capture + redaction |
| `src/pubrun/capture/invocation.py` | 184 | Invocation context + script hashing |
| `src/pubrun/capture/redaction.py` | 219 | Regex-based redaction |
| `src/pubrun/capture/liveness.py` | 457 | Cross-platform PID liveness, RSS, CPU |
| `src/pubrun/__main__.py` | 1559 (first 100 read) | CLI entry point |

## Commands run

- `git status --short` — confirmed clean working tree
- `git log --oneline -5` — confirmed HEAD at `1b90858`
- `git tag -l 'v0.3*'` — confirmed `v0.3.0` tag exists
- `date -u '+%Y%m%d-%H%M%S'` — generated run ID `20260704-143134`
- `ls plans/` — discovered existing plans directory
- `ls .agents/` — confirmed workflows directory

## Analysis methodology

1. **Static analysis of hot paths:** Identified the import-time call chain
   (`__init__.py` -> `_execute_boot_sequence` -> `Run.__init__` ->
   `_bootstrap_engines`) and traced every synchronous operation.

2. **Complexity reasoning:** For each finding, reasoned about algorithmic
   complexity (O(n) iterations, subprocess spawns, regex compilations) and
   multiplied by realistic inputs (500 packages, 1000 runs, 100K print lines).

3. **I/O cost analysis:** Identified synchronous file reads and subprocess
   spawns on the critical import path and estimated their wall-clock cost
   based on known latencies (subprocess spawn ~5-50ms, file read ~1-10ms,
   nvidia-smi ~200-500ms).

4. **Lock contention analysis:** Identified the `threading.Lock` in
   EventStream.emit() and SubprocessSpy as serialization points under
   concurrent access.

## Sampling and truncation notes

- `__main__.py` was only read to line 100 (CLI dispatch); the remaining 1459
  lines are rendering and argument parsing, not performance-critical paths.
- `_bootstrap.py` was partially truncated in initial read but the critical
  `select_mode` logic was captured.
- No profiling was run (assessment is static analysis only). The IPD proposes
  creating benchmarks to validate findings empirically before/after changes.
