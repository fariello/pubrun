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
- Status: PENDING — design RESOLVED via plan-review (2026-07-05) and
  `/advise architect` (2026-07-06). Ready for a normal `plan-review` of the
  now-concrete design, then execution on approval. Not auto-executed.
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

### Use case (the plain end-user story)

A researcher captures everything most of the time, but is about to call a method
or subprocess whose output is noisy / useless / not wanted in the record. They
want to NOT capture that part, then resume capturing everything:

```python
import pubrun  # capturing stdout, subprocesses, etc.

do_normal_work()             # captured
with pubrun.paused():
    call_something_noisy()   # runs and prints normally, but NOT recorded
resume_normal_work()         # captured again
```

Mental model (stated so it is true across every engine `paused()` touches):
**"`paused()` stops pubrun from *recording* my program's ambient output and
subprocesses on this thread; it does not stop my program, does not stop output
going to my terminal, does not stop my explicit annotations, and does not stop
resource sampling."**

## Resolved design (plan-review + /advise architect)

- **Thread-local suspension of RECORDING.** `paused()` suspends *recording* on
  the **calling thread only**. Output still goes to the real terminal and
  subprocesses still run; other threads keep being captured. This is per-thread
  because that is the least-surprising semantic and matches the subprocess spy's
  existing behavior. (For a typical single-threaded research script, per-thread
  and process-global are indistinguishable; per-thread is chosen so multi-threaded
  scripts are not silently mis-captured.)
- **Per-engine `pause()`/`resume()` + a thin façade (NOT a shared flag).** Each
  pausable engine owns its own thread-local, ref-counted, exception-safe gate.
  `pubrun.paused()` is a context manager that calls each engine's `pause()` on
  enter and `resume()` on exit (in a `finally`). No cross-boundary
  `run._capture_paused` flag (plan-review already killed that; the tee cannot
  reach the run anyway).
- **The pausable set is decided by a principle, not a list:** only capture
  engines that record **synchronously, on the calling thread, of ambient program
  activity** are pausable. That rule yields exactly:
  - **Subprocess spy** — IN. Reuse its existing thread-local seam
    (`_spy_local.bypass` / `disable_spy`), wrapped as ref-counted `pause()`/
    `resume()`.
  - **Console tee** — IN. Add a matching thread-local gate to
    `TqdmSafeTee.write`.
  - `pubrun.print`/`open`/`popen` — honor the same thread-local flag for
    consistency (near-free; they already run on the calling thread). They are
    conveniences over the same paths, not separate engines.
  - **Resource watcher** — OUT, by the same principle: it samples
    **asynchronously on its own background thread**, so "pause on the calling
    thread" is meaningless for it — and that is correct, because RAM/CPU are
    process-wide facts (the noisy subprocess still used real memory; you want it
    in the peak).
  - **Event stream / `annotate()` / `phase()`** — OUT (deliberate): these are the
    user's *explicit* markers, not ambient capture. Silencing an `annotate()` the
    user chose to call would be surprising. They keep firing inside `paused()`.
- **Passthrough is always process-global.** There is one `sys.stdout`; only the
  *recording decision* is thread-scoped. So a `paused()` block still shows output
  on the terminal for all threads — only *this thread's* recording is suspended.
  (Documented so no one expects thread-isolated terminal output.)
- **Selectivity deferred (KISS).** v1 pauses ALL pausable engines (spy + tee); no
  per-engine kwargs (`paused(console=..., subprocess=...)`) until a concrete need
  appears. Adding them later is non-breaking (just choose which engines' `pause()`
  to call).

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

## Mechanism: "mute" (chosen), not "unpatch"

The "Resolved design" above uses the **mute** approach: keep all monkeypatches
installed and gate *recording* per-engine at each engine's own thread-local seam.
Pausing sets the gates; the wrappers still pass real output through to the
terminal / still let subprocesses run, but skip *recording*. No global
unwrap/rewrap of `sys.stdout`/`subprocess`, so the interleaving hazard (a third
party replacing `sys.stdout` mid-block, then a naive restore clobbering it) does
not arise. The only cost is that the wrappers remain in the call path while
paused (a cheap per-write thread-local check on the tee — see the Performance
gate below).

The rejected alternative — **true unpatch/repatch** (restore the original
`sys.stdout`/`subprocess` for the block, re-install after) — would give the block
a pristine original `sys.stdout` object, but carries the full interleaving +
identity-guarded-restore + ref-counted-nesting hazards for no benefit the use
case needs. Not in scope; revisit only if a concrete need for a truly-pristine
stdout during the block appears.

### Concrete implementation seams

- **Subprocess spy** (`subprocesses.py`): promote the existing thread-local
  bypass into a public, **ref-counted** `pause()`/`resume()` pair on the pausable
  contract. `_spy_local.bypass` is a boolean today; the public pause must
  ref-count (per thread) so that (a) nested `paused()` blocks compose, and (b) it
  coexists with the internal `disable_spy()` uses (git/hardware/resources capture)
  without one clobbering the other. `disable_spy()` should be re-expressed in
  terms of the same ref-counted primitive.
- **Console tee** (`console.py`): add a thread-local gate that
  `TqdmSafeTee.write` consults at the top; when paused for the calling thread,
  pass `data` through to `original_stream` but skip the log-write branch. The gate
  lives with the interceptor/tee (each owns its state); ref-counted per thread.
- **Façade** (`core.py`): `pubrun.paused()` context manager (+ optional
  `pubrun.pause()`/`pubrun.resume()` — see Q5) that calls `pause()` on each
  registered pausable on enter and `resume()` on exit in a `finally`. A tiny
  registry or explicit list of pausables; adding a future ambient-synchronous
  engine means implementing the contract, not editing the façade.

### Performance gate (the one real trade-off)

Thread-local suspension means `TqdmSafeTee.write` does a `threading.local()`
lookup on **every** stdout write (tight loops, progress bars). It is cheap but
non-zero. **Before merge, benchmark the tee write path with the gate present vs.
absent** (the `benchmarks/` harness now exists — add or reuse the `print_loop`
hot-path scenario) and confirm the overhead is negligible. If it is not, fall
back to a cheaper representation, but do not abandon thread-local semantics
without recording why.

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

## Decisions (resolved) and remaining open questions

**Resolved** (plan-review 2026-07-05; `/advise architect` 2026-07-06, maintainer
confirmed):

1. **Semantics: MUTE, not unpatch.** Gate recording; keep patches installed.
2. **Thread scope: THREAD-LOCAL** for both spy and tee (recording is suspended on
   the calling thread only; passthrough stays process-global). Least surprising;
   matches the spy's existing behavior.
3. **Pausable set: subprocess spy + console tee ONLY** (the ambient,
   synchronous, calling-thread recorders). `print`/`open`/`popen` honor the same
   flag. **Resource watcher OUT** (async, own thread; RAM/CPU are process-wide
   and should still count). **Event stream / `annotate` / `phase` OUT** (explicit
   user markers still fire inside `paused()`).
4. **Resource watcher on resume: N/A** — it is not paused, so peaks carry over by
   definition (it never stopped).
5. **Worth building: YES.** The use case (capture everything, silence a noisy
   block, resume) is a single coherent stupid-simple story; dropping the tee half
   would make it incoherent. Not deferred.
6. **Selectivity: deferred** — v1 pauses all pausable engines; no per-engine
   kwargs yet (non-breaking to add later).

**Remaining open (small; settle at implementation / next plan-review):**

- **API surface:** context manager `with pubrun.paused():` is required (it
  guarantees `resume` even on exception). Also expose bare `pubrun.pause()` /
  `pubrun.resume()`? Risk: unbalanced calls leaving capture off. Recommend
  context-manager-only in v1; add explicit calls only if a real need appears.
  CONFIRM at implementation.
- **Performance:** the tee hot-path thread-local cost must be benchmarked before
  merge (see the Performance gate). Not a design question, but a merge gate.

## Required tests / validation

- **Before/during/after state** for tee + spy on the **calling thread**: active →
  suspended → active, including the **exception path** (`__exit__`/`finally`
  restores).
- **Nested `paused()`** (and a `paused()` inside a `phase()`) ref-count correctly:
  the inner exit does not resume early.
- **Thread isolation:** with the gate present, a `paused()` on thread A does NOT
  suspend recording on thread B (spawn a second thread that writes/spawns during
  A's `paused()` block and assert its output/subprocess IS still recorded).
- **`annotate()`/`phase()` still fire** inside `paused()` (they are NOT paused);
  **resource sampling continues** (peaks unaffected).
- **`disable_spy()` coexistence:** internal git/hardware/resources spans still
  bypass correctly; a user `paused()` (or its exception) never leaves the spy or
  tee stuck suspended (ref-count returns to zero).
- **Performance:** tee write path with vs. without the thread-local gate
  (benchmarks harness), overhead negligible.
- Full suite green.

## Spec / documentation sync

New public API → `docs/api.md`, README (mention as an advanced escape hatch),
`docs/functional_spec.md`, `CHANGELOG`. Run `/assess documentation` after.

## Approval and execution gate

The design is now RESOLVED (plan-review + `/advise architect`, maintainer
confirmed). The recommended next step is a normal `plan-review` of this concrete
design, then human approval. It MUST be human-approved before execution and is
NOT auto-executed. On approval: implement (calling-thread state + ref-counted
per-engine `pause()`/`resume()` + façade), validate with the tests above
(including the performance gate), sync docs, and move to
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

## /advise architect session (2026-07-06)

An architect-persona dialogue with the maintainer resolved the remaining design
questions; the "Resolved design" and "Decisions" sections above are its output.
Key points from the session:

- **Coherence (the architect's central concern):** `paused()` was in danger of
  being a façade over three mechanisms with different scopes/locations. Resolved
  by defining ONE contract — thread-local, ref-counted, exception-safe
  `pause()`/`resume()` — implemented identically by each pausable engine, with the
  façade just walking them. The user's mental model is now true across every
  engine it touches.
- **Pausable boundary is a principle, not a list:** only engines that record
  *synchronously, on the calling thread, of ambient program activity* are
  pausable → spy + tee IN; resource watcher OUT (async/own thread; RAM/CPU are
  process-wide) and event markers OUT (explicit user signals). A contributor can
  apply this rule to any future engine.
- **Value confirmed and the tee kept in scope:** the architect initially
  questioned whether the tee (the hard part) was worth it; the maintainer
  corrected that this conflated implementation cost with user value — the use
  case (capture all, silence a noisy block, resume) is one coherent stupid-simple
  story, and dropping console pausing would make it incoherent. The tee is IN.
- **Thread-local confirmed** as the semantic (output still prints for all threads;
  only the calling thread's *recording* pauses). The one real trade-off — the
  per-write thread-local check on the tee — is now an explicit pre-merge
  benchmark gate rather than an assumption.

Session summary: `workflow-artifacts/advise-architect/<RUN_ID>/session-summary.md`.
