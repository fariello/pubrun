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

**Plan-review correction (verified against source):** the capture engines do NOT
fall into a clean "global patches vs safe" split. There are actually **three
different gating realities**, and treating them as one class is the mistake that
makes a "uniform `run._capture_paused` flag" (see Tier 1 below) not work as first
written:

1. **Subprocess spy — already gated, thread-local.** `SubprocessSpy`
   (`subprocesses.py`) patches `subprocess.Popen.__init__`/`os.system`, but the
   `_patched_popen_init` **first checks `getattr(_spy_local, "bypass", False)`**
   (`subprocesses.py:99`) and passes straight through if set. `_spy_local` is a
   `threading.local()` (`subprocesses.py:10`), and the existing `disable_spy()`
   context manager (`subprocesses.py:13-21`) flips it. So the spy's pause is
   **already built, and it is thread-LOCAL** — pausing on the main thread does
   NOT blind worker threads (the opposite of what an earlier draft claimed). A
   public pause can reuse exactly this seam for the subprocess half.

2. **Console tee — the genuinely hard one; no gate, no run reference.** The tee
   object `TqdmSafeTee` (`console.py:56`) replaces `sys.stdout`/`sys.stderr`. Its
   `write()` (`console.py:70`) references only `self.original_stream` and
   `self.log_file` — it does **not** call `get_current_run()` and has **no pause
   gate at all**. It also intercepts *all* stdout writes, including a plain
   `print()`, which is exactly the noise a user wants to pause. So the tee needs
   a **new** gate added (a mutable flag the tee holds a reference to, or a
   module/thread-local check in `write()`), and there is a real thread-scope
   decision: `sys.stdout` is process-global, so muting the tee mutes ALL threads'
   output during the window unless the gate is thread-local (which requires the
   tee to consult a `threading.local()` on each write). This is the crux of the
   whole feature.

3. **Run-routed explicit wrappers — trivially gatable, but low value.**
   `pubrun.print`/`open`/`subprocess.run`/`popen` all call `get_current_run()`
   (`core.py`), so a `run`-level flag would gate them. But these are *explicit*
   API calls the user already fully controls (they can simply not call them), so
   pausing them adds little.

4. **Non-patch engines — safe to pause.** Resource watcher (`resources.py:279`
   `stop()`, a thread; restart/peak-carry-over needs a decision) and event stream
   (`events.py:114` `close()`; or a cheap emit-time flag) have no global side
   effect and are the easy part.

**Shared hazards for the patch engines (1 and 2):**
- **Interleaving (Tier 2 only):** if true unpatch/repatch is used and other code
  replaced `sys.stdout` while paused, resume must identity-guard the restore (the
  pattern `console.py`/`signals.py` already use) or it loses the third party's
  stream. Tier 1 (mute) avoids this entirely.
- **Thread scope:** must be an explicit, documented decision per engine — the spy
  is already thread-local; the tee's gate scope is a design choice.
- **Re-entrancy / nesting:** nested `with pubrun.paused()` (or a pause inside a
  `phase()`) must ref-count so an inner exit does not resume early.

Net: a public pause/resume is **not** a uniform mechanism. Realistically it is
"reuse the thread-local spy bypass + add a matching gate to the tee + optionally
gate events/resources," each with its own thread-scope decision.

## Proposed direction (to be refined in plan-review / advise-architect)

Not committing to a final shape yet — the point of this IPD is to make the
design questions explicit. Candidate approaches, cheapest/safest first:

- **Tier 1 (low risk): "mute", not "unpatch".** Keep all monkeypatches installed
  and gate them per-engine at their existing seams (NOT via one shared
  `run._capture_paused` flag — the tee does not route through the run, so a
  run-level flag cannot reach it):
  - **Subprocess spy:** reuse the existing thread-local `_spy_local.bypass`
    (`disable_spy()`), the seam already present at `subprocesses.py:99`.
  - **Console tee:** add a NEW pause gate to `TqdmSafeTee.write` (`console.py:70`)
    — the tee has none today and holds no run reference. Give the tee a mutable
    "paused" holder (or have `write()` consult a module-level / thread-local flag
    at the top and short-circuit the log-write branch, still passing data through
    to `original_stream`). Thread scope of this gate is the key design choice
    (process-global mute is simple but silences all threads; thread-local matches
    the spy but requires a per-write `threading.local()` check).
  - **Events / resources:** cheap emit-time flag / thread stop-restart as noted.

  Pausing sets the gates; the wrappers pass real output through but skip
  recording. No global unwrap/rewrap, so the interleaving hazard is avoided.
  Downside: wrappers stay in the call path (tiny overhead while paused) and this
  does NOT give the block a pristine original `sys.stdout` object.
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
- **Must not disturb the existing internal `disable_spy()` usage.** git and
  hardware capture already wrap their own subprocess calls in `disable_spy()`
  (`with disable_spy():` in `capture/git.py`, `capture/hardware.py`,
  `capture/resources.py`). If the public pause reuses `_spy_local.bypass`, a
  characterization test must confirm those internal spans still bypass correctly
  and that a user `paused()` does not leave `_spy_local.bypass` stuck True after
  an exception (the `finally` restore in `disable_spy` is the pattern to mirror).

## Open questions (must be answered before this is executable)

1. **Semantics: mute (Tier 1) vs true unpatch (Tier 2)?** Recommend Tier 1
   default. (Complexity/functionality — this is the central decision.)
2. **Thread scope (now the hardest question, given the code reality):** the
   subprocess spy's existing bypass is **thread-local** (`_spy_local`), but the
   console tee replaces the process-global `sys.stdout`. So there is a genuine
   *consistency* tension: a naive "process-global pause" would make the tee mute
   all threads while the spy bypass only affects the calling thread — two
   different scopes under one `paused()` call, which is exactly the kind of
   surprise this feature is supposed to avoid. Options:
   (a) **All thread-local:** reuse `_spy_local` for the spy and add a
   `threading.local()` gate the tee checks per write. Consistent and least
   surprising, but adds a per-write thread-local lookup to the tee's hot path and
   cannot make `sys.stdout` itself thread-specific (only the *recording* is
   thread-scoped; passthrough is always global). (b) **All process-global:**
   simplest for the tee, but then the spy pause must also be made process-global
   for consistency, changing `disable_spy()`'s current semantics. (c) Document
   the split and accept it (worst for the "stupid simple" principle).
   Recommend: **(a) thread-local for both**, documented, since it is the least
   surprising and the spy is already there — but confirm the tee hot-path cost is
   acceptable. This decision blocks implementation.
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
needs its open questions resolved and should go through `/advise architect` on
the concurrency model before any code. It MUST be human-approved before
execution and is NOT auto-executed. On approval of a resolved design: implement,
validate (with the anti-regression tests above), sync docs, and move to
`.agents/plans/executed/`.

## Plan-review revisions (2026-07-05)

Verdict: **APPROVE WITH REVISIONS APPLIED** (as an early proposal — it correctly
remains NOT execution-ready; the revisions sharpen its design accuracy so the
eventual architect pass and implementation start from true premises).

Reviewed against the actual seams (`subprocesses.py:10,13-21,97-110` `_spy_local`
+ `disable_spy`; `console.py:56,70` `TqdmSafeTee.write`; `core.py` run-routed
wrappers; `resources.py:279`; `events.py:114`). Findings:

- **PR-P1 (HIGH, functionality/accuracy):** the IPD framed the engines as a clean
  "process-global patches vs safe" split and proposed one shared
  `run._capture_paused` flag "the tee/spy/event-emit check." Verified FALSE: (a)
  `TqdmSafeTee.write` holds no run reference and has no gate, so a run-level flag
  cannot reach the tee — the main use case; (b) the subprocess spy is **already
  gated and thread-LOCAL** via `_spy_local`/`disable_spy()`, so it does not have
  the "blinds worker threads" hazard the draft attributed to it. Rewrote the "Why
  this is riskier" section into the three real gating realities and corrected the
  Tier 1 description to per-engine seams (reuse `_spy_local`; ADD a new gate to
  the tee).
- **PR-P2 (HIGH, functionality):** the thread-scope question was under-weighted.
  Because the spy is thread-local but the tee is process-global, a naive
  "process-global pause" gives **two different scopes under one call** — a
  consistency violation of the "stupid simple" principle. Rewrote Open question #2
  to make thread scope the blocking decision, with three concrete options and a
  recommendation (thread-local for both).
- **PR-P3 (MEDIUM, anti-regression D):** added an invariant/test that the public
  pause must not disturb the existing internal `disable_spy()` spans (git/
  hardware/resources capture) and must not leave `_spy_local.bypass` stuck after
  an exception.
- **PR-P4 (LOW):** removed the redundant "should go through plan-review" from the
  gate (this review is that pass); the remaining recommended step is
  `/advise architect` on the concurrency model.

Not changed (correctly deferred): whether to build it at all (Open question #6,
the KISS/stakeholder gate) — that is the maintainer's call and the IPD rightly
poses it rather than presuming. The mute-vs-unpatch choice (Q1) and selectivity
(Q3) remain open by design; this is an early proposal.
