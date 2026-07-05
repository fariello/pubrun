# Evidence - assess edge-cases 20260705-002318

Reproducibility record: what was inspected and how.

## Baseline verification (read-only)

- `git status --short` -> clean (only untracked `opencode-recovery/`).
- `git log --oneline -15`, `git describe --tags` -> `v1.3.1-61-g0f2e34b`.
- `.agents/plans/pending/` -> only `.gitkeep`.
- `pyproject.toml` -> `version = "1.3.1"`.
- Full suite: `~/venv/p3.14/bin/python -m pytest tests/ -q`
  -> 599 passed, 2 skipped, 1 failed (`test_real_sigpipe_via_pipe`).
  Re-ran the failing test in isolation -> passed (confirmed known flaky, per restart
  context; not a regression).

## Files read directly (line-by-line) by the lead agent

- `src/pubrun/writer.py` (full) — atomic write, tmp-path collision note.
- `src/pubrun/events.py` (full) — buffered writes, serialization guard, close/migrate.
- `src/pubrun/config.py` (full) — unguarded `tomllib.loads` in local/user config load.
- `src/pubrun/capture/packages.py` (full) — confirmed EC-08: `sorted().lower()` outside
  the try; `None` dist name path.
- `src/pubrun/core.py:450-499, 660-788` — confirmed EC-21 (`sep.join` before try; print
  not installed in builtins), EC-09 (uncapped `manual_subprocess_records`), EC-24/EC-25.
- `src/pubrun/status.py:180-269, 460-559` — confirmed EC-01/02/03/04: narrow
  `except (json.JSONDecodeError, OSError)`, per-entry `RunInfo` in `scan_runs` with no
  guard, `sort(key=...or 0)`, `_format_timestamp` guarding only None (local tz).
- `src/pubrun/tracker.py:40-114` — confirmed EC-14 library path is guarded (config
  fallback), ghost-mode setup.
- `src/pubrun/capture/signals.py:150-249` — confirmed EC-15 (excepthook restore without
  identity check) and EC-27 (finalization inside signal handler).
- `src/pubrun/capture/git.py:18-50` — confirmed EC-13 (hardcoded `timeout=1`,
  timeout collapses to "Not a git repository").

## Grep / search commands

- `grep 'builtins\.(print|open|__import__)\s*='` in `src/**` -> **no matches** -> proved
  `pubrun.print`/`pubrun.open` are not installed into builtins (basis for downgrading
  EC-21 from golden-rule violation to library-API edge).
- `grep 'resolve_config|load_local_config|TOMLDecodeError'` in `src/pubrun/**` -> mapped
  all `resolve_config()` call sites; confirmed unguarded ones (`status.py:477`,
  `events.py:30`, several `__main__.py`) vs the guarded `tracker.py:54`.
- `find src/pubrun -name '*.py'` -> full module inventory (49 source files).

## Parallel read-only audit lanes (explore agents)

Two `explore` subagents did line-by-line reads and returned candidate findings
(temporary IDs, no official IDs, no edits, no commits — per the parallel-lane rules):

- **Lane A** — `status.py`, `__main__.py`, `capture/liveness.py`, `analysis/diff.py`,
  `analysis/render.py`. Produced 30 candidates covering the reader crash paths,
  liveness wrong-decision paths, diff export collisions, and timezone inconsistency.
- **Lane B** — `core.py`, `tracker.py`, `capture/resources.py`, `subprocesses.py`,
  `console.py`, `signals.py`, `packages.py`, `git.py`, `hardware.py`. Produced 38
  candidates covering golden-rule surfaces, thread/handle lifecycle, unbounded growth,
  concurrency races, and external-command failure handling.

The lead agent synthesized both lanes, deduplicated, re-verified the high-severity
claims against the source, assigned official IDs EC-01..EC-27, set severity +
Remediation Risk, and adjusted several severities down after direct reading (see
`decisions.md`).

## Truncation / sampling notes

- The full-suite pytest output was long; only the summary line and the single failure
  were retained. Coverage numbers were incidental (pytest-cov is configured in
  `pyproject.toml`).
- The two lane reports were comprehensive; findings judged Low and non-reachable or
  already-guarded (e.g. verified-correct guards) were folded into the "not defects"
  note in `decisions.md` rather than recorded as findings.
