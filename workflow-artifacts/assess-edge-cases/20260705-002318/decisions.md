# Decisions and assumptions - assess edge-cases 20260705-002318

## Concern / scope assessed

- Concern: edge-cases (boundary conditions, malformed/unusual inputs, failure modes).
- Scope: whole `src/pubrun/` package, weighted toward the two highest-risk surfaces for
  edge cases: (a) the manifest/lock **readers** in `status.py`/`diff.py`/`liveness.py`
  (they consume untrusted-shaped JSON that a killed/hand-edited/foreign-version process
  can produce), and (b) the **external-command capture** in `hardware.py`/`git.py`/
  `resources.py` (slow/hung/garbage-returning subprocesses). Also covered the
  monkeypatched surfaces (`core.py`, `console.py`, `signals.py`), config loading
  (`config.py`), packages (`packages.py`), events (`events.py`), writer (`writer.py`).

## Project conventions discovered

- No `GUIDING_PRINCIPLES.md`; principles live in `README.md`/`AGENTS.md`: zero runtime
  deps (`tomli` only <3.11), "golden rule" never crash the host script, ghost-mode
  degradation on FS failure, no `rich`, "stupidly simple" tone. Applied these plus the
  universal fallback principles.
- Plans: `.agents/plans/pending/` and `.agents/plans/executed/`, naming
  `YYYYMMDD-<slug>.md`. IPD written to `.agents/plans/pending/20260705-assess-edge-cases.md`.
- Contributor contract: `AGENTS.md` doc-sync discipline (run `/assess documentation`
  after user-visible behavior changes; keep CHANGELOG `[Unreleased]` current).
- Version 1.3.1 (pyproject.toml). The recovery-context session title said "0.3.0" but
  `git describe` = `v1.3.1-61-g0f2e34b`; treated 1.3.1 as authoritative.

## Key decisions

1. **Fix-by-default applied.** 26 of 27 findings have Low Remediation Risk and are
   proposed for action. Only EC-27 is deferred, with a named axis (see below).
2. **Verified before recording.** Two parallel read-only explore lanes produced
   candidate findings; I then re-read the actual cited code for the highest-severity
   claims (EC-01/02/03 in status.py, EC-08 packages.py, EC-09 core.py subprocess
   wrappers, EC-14 config+tracker, EC-15 signals excepthook, EC-13 git) to confirm each
   is real and reachable before writing it into the IPD. Downgrades made after reading:
   - The lane's "patched print/open golden-rule violation" was reclassified: `pubrun.print`/
     `pubrun.open` are **not** installed into `builtins` (grep confirmed no
     `builtins.print =` assignment), so EC-21 is a library-API edge (user must call
     `pubrun.print`), not a global golden-rule violation. Severity Low.
   - EC-14: `Run.__init__` **does** catch config errors and fall back to defaults
     (tracker.py:55-61), so the library path is safe; the real exposure is unguarded
     CLI call sites like `scan_runs`. Scoped the fix to `config.py` (source).
3. **EC-27 deferred (the only deferral).** Running finalization (JSON writes, hashing,
   a 2s thread join, lock acquisition) inside the SIGTERM/SIG_DFL signal handler
   (`signals.py:176-190`) is not async-signal-safe and can deadlock/hang shutdown. The
   correct fix is a redesign (self-pipe/flag drained on the main thread, or minimal
   atomic-write-only in signal context) with real regression risk to the crash-safety
   mechanism itself. Remediation Risk Medium-High on **Functionality** and
   **Complexity** -> deferred to a dedicated design pass + its own IPD with
   cross-platform characterization tests. Not bundled with the low-risk hardening.
4. **Liveness tightening flagged as the one Low-Medium item.** EC-06/EC-07 fixes could
   flip an unusual "running" edge (e.g. `-c` scripts, generic interpreter names) to
   "crashed". Proposed the conservative direction (prefer correctness + tests) but
   raised it as open question #4 for human confirmation given the known macOS
   PID-liveness flakes recorded in the restart context.

## Assumptions (marked for confirmation)

- Default timeouts proposed: hardware 5s, git 3s, resource poll 2s (open question #2).
- `status.py` should standardize on UTC to match `diff.py` and the manifest epochs
  (open question #1).
- `full-environment`/`top-level-installed` are the only package modes exposed to the
  EC-08 `None`-name crash; default `imported-only` uses `sys.modules` keys (always str)
  and is safe. Confirmed by reading `packages.py`.

## What was intentionally NOT proposed and why

- **EC-27 signal finalization** — deferred (Medium-High Remediation Risk, above).
- No new dependencies, no `rich`, no new abstractions — respecting KISS and the
  zero-dep principle. The Complexity axis kept the diff type-tagging (EC-19) and the
  liveness heuristic (EC-06) minimal rather than a general rewrite.
- Did not propose changing the deliberate epoch-float timing design (documented in
  `tracker.py:70-76`); EC-23 only notes the negative-under-clock-skew limitation.

## Open questions for the user

See the IPD "Open questions" section (UTC standardization, default timeout values,
EC-27 deferral confirmation, liveness-strictness direction).

## Notable correct guards verified (not defects)

- `resources.py:202` CPU div-by-zero guard; `perf_counter` used for CPU wall delta.
- `console.py:200-203` identity-checked stream restore (the pattern EC-15 should copy).
- `subprocesses.py` records-lock discipline + clear-on-uninstall; failed-outcome
  stickiness (`tracker.py:522`); ghost-mode short-circuit via `_finalized`.
- `writer.py` atomic JSON write (temp + os.replace) with tmp cleanup on failure.
- `Run.__init__` config-resolution fallback to defaults (tracker.py:55-61).
