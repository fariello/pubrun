# IPD: Scoped in-code pause/resume of capture (`with pubrun.paused(): ...`)

- Date: 2026-07-05
- Concern: functionality / API design (new public API) — **design-heavy, higher
  risk than it looks**
- Scope: a context manager (and/or explicit calls) letting a script temporarily
  suspend some or all pubrun capture for a block, then resume it:
  ```python
  with pubrun.paused():            # suspend capture for this block
      noisy_untracked_work()
  # capture resumes here
  ```
  Orthogonal to import modes — wanted regardless of which mode is active.
- Status: PENDING (early proposal — NOT ready to execute; open design questions
  must be resolved and this should go through `plan-review` and probably an
  `/advise architect` pass first).
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Related: split out of the `full`-mode discussion (2026-07-05) as its own IPD
  because it is orthogonal and materially riskier. A short pointer lives in
  `TODO.md`.

## Goal

Give users a clean, in-code way to say "don't capture this part." Real needs:
a noisy third-party call whose subprocess/console output floods the logs; a
block that spawns many short-lived helpers the user doesn't want recorded; a
region where the user temporarily wants their real stdout untouched.

This is an ergonomic convenience, not a correctness feature. It must never
compromise the golden rule (never crash the host) or leave capture in a broken
state after the block.

## Why this is riskier than it looks (the core problem)

pubrun's capture engines fall into two classes with very different pause safety:

1. **Process-global monkeypatches — the dangerous ones:**
   - **Console tee** (`ConsoleInterceptor`, `console.py:151` — has `start()`/
     `stop()`) replaces `sys.stdout`/`sys.stderr` with a tee wrapper.
   - **Subprocess spy** (`SubprocessSpy`, `subprocesses.py` — has class-level
     `install()`/`uninstall()`, plus an existing internal `disable_spy()`
     context manager used during git/hardware capture) patches
     `subprocess.Popen.__init__`/`os.system`.

   Pausing these means unwrapping and later re-wrapping global state. Hazards:
   - **Interleaving:** if other code (or a library) replaced `sys.stdout` while
     paused, resume must not clobber it or restore a stale wrapper — the same
     identity-guard problem already handled for restore elsewhere
     (`console.py`/`signals.py` do identity checks). Naive save/restore can lose
     a third party's stream.
   - **Thread-safety:** these are process-global. A "pause on the main thread"
     also blinds a **worker thread's** output/subprocesses during the window —
     surprising and hard to reason about. `disable_spy()` today is only used for
     brief, main-thread, internal spans; a user-facing pause invites concurrent
     use it was not designed for.
   - **Re-entrancy / nesting:** nested `with pubrun.paused()` blocks, or a pause
     inside a `phase()`, must ref-count correctly and not resume early.

2. **Non-patch engines — safe(r) to pause:**
   - **Resource watcher** (`resources.py:279` `stop()`; a thread) — can stop/
     restart, though restart semantics (peak carry-over) need a decision.
   - **Event stream** (`events.py:114` `close()`) — can gate emits with a flag
     cheaply; no global side effect.

The existing `disable_spy()` context manager (`subprocesses.py:13`) is a useful
precedent for the subprocess half, but it is (a) internal, (b) main-thread-only
in practice, and (c) does not touch the console tee. A public, general
pause/resume is a superset with real concurrency exposure.

## Proposed direction (to be refined in plan-review / advise-architect)

Not committing to a final shape yet — the point of this IPD is to make the
design questions explicit. Candidate approaches, cheapest/safest first:

- **Tier 1 (low risk): "mute", not "unpatch".** Keep all monkeypatches installed
  but add a per-run boolean gate the tee/spy/event-emit check on each call
  (e.g. `run._capture_paused`). Pausing sets the flag; the wrappers pass through
  without recording. No global unwrap/rewrap, so the interleaving hazard largely
  disappears. Downside: the wrappers are still in the call path (tiny overhead
  while paused) and this does not "unpatch" for someone who literally needs
  `sys.stdout` to be the original object during the block.
- **Tier 2 (higher risk): true unpatch/repatch.** Actually restore
  `sys.stdout`/`subprocess` for the block and re-install after. Gives a truly
  pristine stdout during the block but carries the full interleaving/thread
  hazards above; needs identity-guarded restore and ref-counted nesting.

Recommendation to evaluate: **Tier 1 (mute)** as the default `pubrun.paused()`
semantics (covers the common "don't record this" need at low risk), and treat
true unpatch (Tier 2) as a separate, explicitly-flagged option only if a real
need emerges. Selective pause (`pubrun.paused(console=True, subprocess=False)`)
is a nice-to-have to decide on.

## Anti-regression / invariants to preserve (rubric D)

- After ANY `paused()` block (normal exit OR exception), capture MUST resume to
  exactly its prior state — verified by characterization tests that assert the
  tee/spy are active and recording before, inactive during, active after, incl.
  the exception path (the context manager must restore in `__exit__`/`finally`).
- Nested/re-entrant pauses ref-count correctly (inner exit does not resume).
- The golden rule: a failure inside pause/resume must never propagate to the
  host; degrade to "capture stays on" rather than crash.
- Must not weaken the existing identity-guarded restore behavior in
  `console.py`/`signals.py`.

## Open questions (must be answered before this is executable)

1. **Semantics: mute (Tier 1) vs true unpatch (Tier 2)?** Recommend Tier 1
   default. (Complexity/functionality — this is the central decision.)
2. **Thread scope:** is pause explicitly documented as process-global (affects
   all threads), or scoped to the calling thread? Process-global is simpler and
   matches how the patches actually work; thread-scoped is what users may naively
   expect but is much harder (thread-local stdout is not a thing pubrun controls).
   Recommend: process-global, clearly documented, with a warning in the docstring.
3. **Which engines pause?** All, or a selectable subset
   (`paused(console=..., subprocess=..., resources=..., events=...)`)? Recommend
   start with "all capture" for simplicity; add selectivity only if needed.
4. **Resource-watcher semantics on resume:** does peak RSS/CPU carry over across
   the pause, or reset? (Recommend carry-over — pausing recording shouldn't lose
   the run's peak.)
5. **API surface:** context manager only (`with pubrun.paused():`), or also
   explicit `pubrun.pause()`/`pubrun.resume()`? Recommend context manager only
   (guarantees resume even on exception); explicit calls invite unbalanced state.
6. **Is this worth building at all** given the risk, vs. documenting that users
   should structure code to avoid capturing noisy blocks, or use `noconsole`/
   config? (Stakeholder/KISS check — the deferral bar.)

## Required tests / validation (once a design is chosen)

- Before/during/after state for tee + spy (active → inactive → active), incl. the
  exception path; nested pauses; thread interaction documented and tested to the
  extent feasible; event emits suppressed during pause; resource peak behavior
  per decision #4. Full suite green.

## Spec / documentation sync

New public API → `docs/api.md`, README (mention as an advanced escape hatch),
`docs/functional_spec.md`, `CHANGELOG`. Run `/assess documentation` after.

## Approval and execution gate

This IPD is an **early proposal and is explicitly not ready to execute.** It
needs its open questions resolved and should go through `plan-review` (and likely
`/advise architect` on the concurrency model) before any code. It MUST be
human-approved before execution and is NOT auto-executed. On approval of a
resolved design: implement, validate (with the anti-regression tests above),
sync docs, and move to `.agents/plans/executed/`.
