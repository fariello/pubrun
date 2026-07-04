# IPD: Assess Performance - Runtime and Import Overhead Optimization

- Date: 2026-07-04
- Concern: performance
- Scope: whole project (src/pubrun/)
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Reduce pubrun's overhead on user scripts — specifically import-time latency,
per-write hot-path cost in the console tee, event stream serialization, the
`ProvenanceFileProxy` on every file I/O, and `pubrun status` scan time when
the runs directory grows large. Pubrun's promise is "zero-footprint telemetry"
so measurable overhead in any of these paths directly contradicts the project's
value proposition for latency-sensitive workloads (ML training loops, HPC
pipelines, real-time inference).

## Project conventions discovered (Step 0)

- Guiding principles: No explicit `GUIDING_PRINCIPLES.md`; universal fallback
  applied (KISS, solve the general case, honest docs, intuitive/self-documenting).
- Pending-plans location/format used: `plans/pending/` (existing `plans/` dir
  discovered with one prior plan; `pending/` subdirectory created for this IPD).
- Contributor/spec-sync contract: `AGENTS.md` references agent workflows; no
  formal CONTRIBUTING doc beyond the file. N/A for performance.
- Stack: Pure Python 3.8+, zero runtime deps except `tomli` on <3.11. Build:
  hatchling. Tests: pytest. CI: GitHub Actions matrix 3.8-3.14, three OSes.

## Findings

Severity is impact if left alone; Remediation Risk is the Fix-Bar gate for
whether to act now. Persona = which reviewer perspective surfaced it.

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| PERF-01 | Medium | Low | Engineer/Architect | Import startup | `get_packages()` iterates ALL installed distributions on every `import pubrun` (when mode is `full-environment`). In a large venv (500+ packages) this can add 50-200ms of import latency. | `capture/packages.py:37-55` — `importlib.metadata.distributions()` is fully iterated and each dist's `locate_file("")` and `read_text("direct_url.json")` are called. |
| PERF-02 | Medium | Low | Engineer/Power-user | Import startup | `get_hardware()` spawns external subprocesses (`nvidia-smi`, `sysctl`, `system_profiler`, `wmic`) synchronously during import. GPU detection alone can take 200-500ms. | `capture/hardware.py:78-145` — `subprocess.check_output` calls with no caching across runs on the same machine. |
| PERF-03 | Medium | Low | Engineer | Import startup | `get_git()` spawns 4 sequential `git` subprocess calls (rev-parse, status --porcelain, remote get-url) each with 1s timeout. On network-mounted repos or large repos, `git status --porcelain` can be slow. | `capture/git.py:31-65` — 4 sequential `_run_git()` calls. |
| PERF-04 | Medium | Low | Engineer/Architect | Import startup | `get_invocation()` hashes the entire script file with SHA-256 (read in 8KB chunks) on every import. For large scripts or Jupyter notebooks converted to .py, this blocks startup. | `capture/invocation.py:67-73` — `hashlib.sha256()` over full file. |
| PERF-05 | Low | Low | Engineer | Console hot-path | `TqdmSafeTee.write()` calls `datetime.now(timezone.utc).strftime(...)` on every line when timestamped mode is active. In tight print loops (ML epoch logging), this is per-line datetime formatting overhead. | `capture/console.py:57-60` — inside the inner loop over `lines`. |
| PERF-06 | Low | Low | Engineer | Event stream | `EventStream.emit()` calls `json.dumps()` + `file.write()` + `file.flush()` under a threading lock for every event. The lock + flush-per-event becomes a serialization bottleneck for high-frequency resource samples. | `events.py:62-77` — `self._lock` held during `json.dumps` + write + flush. |
| PERF-07 | Medium | Low | Power-user/Architect | ProvenanceFileProxy | `ProvenanceFileProxy._register_provenance()` re-reads the ENTIRE file to compute SHA-256 on close, even though it already hashed data incrementally during read. The full-file re-hash is redundant for read-mode files. | `core.py:354-362` — opens file in "rb" and hashes 64KB chunks, duplicating the incremental `self._hash`. |
| PERF-08 | Low | Low | Engineer | ProvenanceFileProxy | Every `read()` / `readline()` / `__next__()` call conditionally encodes to UTF-8 bytes for hashing, even when the file is already opened in binary mode (data is already bytes). The `isinstance` check + unnecessary `.encode()` runs on every I/O call. | `core.py:297-302` — `chunk = data if isinstance(data, bytes) else data.encode(...)`. |
| PERF-09 | Medium | Low | Power-user/Architect | pubrun status | `scan_runs()` instantiates `RunInfo` for every directory, and `RunInfo._classify()` does synchronous file I/O (read JSON manifest or lock file) for each. For a user with 1000+ runs, this is O(n) sequential JSON parses with no caching or pagination. | `status.py:284-296` — `for entry in base.iterdir(): runs.append(RunInfo(entry))`. |
| PERF-10 | Low | Low | Engineer | pubrun status | `RunInfo._load_from_lock()` counts event lines by reading the entire `events.jsonl` (potentially megabytes) just to show an event count in status output. | `status.py:223-227` — `sum(1 for _ in f)` on potentially large file. |
| PERF-11 | Low | Low | Architect | Startup I/O | `config.resolve_config()` reads up to 3 TOML files (default.toml from package resources, user config, local config) plus does a `copy.deepcopy` + 3 `_deep_merge` passes on every `Run()` creation. The default.toml never changes at runtime. | `config.py:95-131` — `load_default_config()` called fresh each time. |
| PERF-12 | Low | Low | Engineer | SubprocessSpy | `redact_argv()` is called inside `_patched_popen_init` (under lock), recompiling the secret regex on every subprocess spawn via `_get_secret_pattern()` which calls `re.compile()` each time. | `capture/redaction.py:16-24` — `re.compile(pattern_str)` called per invocation; `subprocesses.py:123` calls `redact_argv` per Popen. |
| PERF-13 | Low | Low | Engineer | Environment capture | `redact_env_vars()` calls `is_secret_key()` for every env var, and `is_secret_key()` calls `_get_secret_pattern()` which re-compiles the regex each time — O(n) regex compilations for n env vars. | `capture/redaction.py:142-170` combined with `:16-24`. |
| PERF-14 | Low | Low | Engineer | ResourceWatcher | On Windows and macOS, `_poll_rss()` spawns a subprocess (`wmic` / `ps`) on every sample interval (default 15s). Over a long run this is hundreds of process spawns for a single integer. | `capture/resources.py:14-30` (Windows), `43-52` (macOS). |

## Proposed changes (ordered, validatable)

Fix by default; each item should be safe, well-scoped, and verifiable. Note
the Remediation Risk and the validation for each.

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|-------------------|--------|-------|------------------|------------|
| 1 | PERF-11, PERF-12, PERF-13 | Cache `load_default_config()` result at module level (it never changes). Cache the compiled secret regex in a module-level `_CACHED_PATTERN` (compile once, reuse). | `config.py`, `capture/redaction.py` | Low | `pytest` passes; add microbenchmark: `timeit` import + `resolve_config()` before/after. |
| 2 | PERF-07 | In `ProvenanceFileProxy._register_provenance()`, for read-mode files use `self._hash.hexdigest()` (the incrementally computed hash) instead of re-reading the entire file. Only do the full-file re-hash for write-mode files where the proxy didn't see all data. | `core.py` | Low | Existing provenance tests pass; add test asserting hash matches for a read-only file. |
| 3 | PERF-01 | Make `get_packages()` default mode `imported-only` instead of `full-environment` in `default.toml`. Users who need the full list can opt in via config. `imported-only` filters `sys.modules` keys (typically <100) vs iterating all distributions (often 300-1000). | `resources/default.toml`, `capture/packages.py` docstring | Low | Existing tests pass (they test both modes). Document change in CHANGELOG. Measure: `time python -c "import pubrun"` before/after. |
| 4 | PERF-02 | Defer `get_hardware()` to a background thread (or lazy property) so it does not block `Run.__init__()`. Hardware doesn't change during a run; results can be collected at `stop()` time or via a Future. | `tracker.py` (`_bootstrap_engines`) | Medium (Functionality: manifest write at startup won't include hardware; crash-safety manifest will be incomplete for hardware field) | Tests pass; startup time benchmark. Verify startup manifest has `hardware: {capture_state: {status: "pending"}}` initially. |
| 5 | PERF-03 | Run the 4 git commands in parallel using `subprocess.Popen` + gather, or at minimum run them concurrently with hardware detection (if step 4 moves hardware to background, git can share that thread). At minimum, skip `git status --porcelain` when `capture.git.check_dirty = false` in config. | `capture/git.py` | Low | Git tests pass. Add config key `check_dirty` defaulting to `true`. Measure on a large repo. |
| 6 | PERF-05 | Pre-format the timestamp prefix once per `write()` call (outside the inner line loop) rather than calling `datetime.now()` per line. A single `write("a\nb\nc\n")` currently formats 3 timestamps; it should format 1. | `capture/console.py` | Low | Console capture tests pass. Add microbenchmark for 10K-line write. |
| 7 | PERF-06 | Buffer events and flush periodically (e.g. every 100 events or every 1s) instead of per-event `flush()`. Add `flush()` in `close()` to guarantee no data loss. Move `json.dumps()` outside the lock (prepare the string, then lock-write-unlock). | `events.py` | Low (durability tradeoff: crash within 1s window may lose up to 100 events vs current zero-loss) | Event tests pass. Add config key `events.flush_interval_events` defaulting to 100. Document the durability tradeoff. |
| 8 | PERF-09 | Add a lightweight index file (`.pubrun-index.json`) in the runs directory that caches run metadata (run_id, status, started_at, script). Rebuild it lazily on `pubrun status` if stale. This avoids O(n) JSON parses on every status call. | `status.py` (new index logic) | Medium (Complexity: introduces a new file to maintain/invalidate. Risk of stale index showing wrong data.) | Existing status tests pass. Add test with 100 synthetic runs comparing indexed vs non-indexed performance. |
| 9 | PERF-04 | Gate script SHA-256 hashing behind a config flag `capture.invocation.hash_script` defaulting to `true` for scripts < 1MB, `false` (log warning) for scripts >= 1MB. | `capture/invocation.py` | Low | Invocation tests pass. No behavior change for normal scripts. |
| 10 | PERF-10 | For event count in status display, read only the file size and estimate line count (file_size / avg_line_length), or read only the last few KB to count newlines and extrapolate. Alternatively, maintain a line count in the lock file or a `.events-count` sidecar. | `status.py` | Low | Status tests pass. Verify count is accurate within 5% for real event files. |
| 11 | PERF-14 | On macOS, use `os.getrusage(os.RUSAGE_SELF).ru_maxrss` (no subprocess needed) for RSS polling. On Windows, consider using `ctypes` to call `GetProcessMemoryInfo` directly instead of spawning wmic. | `capture/resources.py` | Low | Resource watcher tests pass. Verify on macOS and Windows. |
| 12 | PERF-08 | In `ProvenanceFileProxy`, detect binary vs text mode at construction time and skip the `isinstance` branch for the known mode, or use a specialized read method. | `core.py` | Low | Provenance tests pass. |

## Deferred / out of scope (with reason)

Deferral requires Medium-High or higher Remediation Risk; name the axis
(complexity / usability / security / functionality). Where possible, the safe
portion is proposed above and only the risky remainder is deferred here.

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| PERF-08 (full) | Medium-High | Complexity | Splitting `ProvenanceFileProxy` into `BinaryProvenanceFileProxy` and `TextProvenanceFileProxy` with different method implementations would double the class surface area for a negligible per-call `isinstance` saving. The simple branch-at-construction proposed in Step 12 captures most of the benefit. | Profile in a real workload; if still hot, introduce specialized classes. |

## Scope check

- Over-scope (untraceable to a need; propose removal/deferral): Step 8 (runs
  index file) adds architectural complexity. If runs count rarely exceeds ~200
  in practice, the current O(n) scan is acceptable. Proposed with a "measure
  first" caveat — implement only if benchmarks prove it matters above 500 runs.
- Under-scope (needed capability missing; propose adding): No benchmarking
  infrastructure exists. Propose adding a `benchmarks/` directory with
  `bench_import.py` and `bench_status.py` scripts that measure import time and
  status scan time, so optimizations are validatable rather than speculative.

## Required tests / validation

1. **Import time benchmark**: `time python -c "import pubrun"` and
   `python -m timeit -n 1 -r 5 "import pubrun"` — target < 100ms on a
   typical dev machine (currently estimated 200-500ms with GPU/packages).
2. **Status scan benchmark**: `bench_status.py` with 100/500/1000 synthetic
   run directories — target < 1s for 500 runs.
3. **Console throughput benchmark**: `bench_console.py` writing 100K lines
   through TqdmSafeTee — measure lines/sec before and after step 6.
4. **Event throughput benchmark**: `bench_events.py` emitting 100K events —
   measure events/sec before and after step 7.
5. **Regression test suite**: All 473+ existing tests must remain green.
6. **ProvenanceFileProxy hash correctness**: Test that SHA-256 produced by
   incremental read matches the file's actual hash.

## Spec / documentation sync

- If Step 3 changes `get_packages()` default from `full-environment` to
  `imported-only`, update `docs/configuration.md` and `CHANGELOG.md`.
- If Step 7 introduces flush buffering, document the durability tradeoff
  (up to N events or 1s of data may be lost on hard crash) in
  `docs/configuration.md` under `[events]`.
- If Step 8 is implemented, document the `.pubrun-index.json` file and its
  invalidation behavior.

## Open questions

1. **Step 4 (deferred hardware)**: Is it acceptable that the crash-safety
   manifest written at startup will lack hardware data? The field would show
   `capture_state: pending` until stop(). If a crash happens before hardware
   collection completes, the manifest will have no hardware info. Acceptable?
2. **Step 7 (event buffering)**: What is the acceptable data loss window?
   100 events or 1 second is proposed. Some users may require zero-loss
   semantics (current behavior). Should this be configurable?
3. **Step 8 (index file)**: What is the actual distribution of run counts in
   practice? If most users have < 100 runs, the index adds complexity for
   marginal benefit. Should we measure first and implement only if needed?
4. **Step 3 (packages default)**: Changing the default from `full-environment`
   to `imported-only` could surprise existing users who depend on the full
   package list without explicit config. Is a CHANGELOG note + minor version
   bump sufficient, or should this wait for 2.0?

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed. Recommended next steps:

1. Review this IPD (optionally run the `plan-review` workflow to harden it).
2. On approval, execute the ordered changes, run the validation, and sync
   specs/docs.
3. Only then move this IPD out of `pending/` per the project's lifecycle
   convention.
