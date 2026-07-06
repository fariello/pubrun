# advise (architect) — session summary

- Date: 2026-07-06
- Persona: architect
- Artifact: `.agents/plans/pending/20260705-scoped-pause-resume.md`
  (scoped in-code pause/resume of capture)
- Mode: interactive coaching (dialogue), edits applied with maintainer consent.

## What was examined

The pause/resume IPD, already plan-reviewed. The architect focused on the design
*shape* (boundaries, coupling, coherence, thread-scope), not re-finding
plan-review's mechanical faults.

## Key questions raised and how they resolved

1. **Is `paused()` one concept or three?** The IPD's own conclusion ("reuse the
   spy bypass + add a tee gate + gate events/resources, each with its own thread
   scope") read like a façade over three inconsistent mechanisms — a boundary
   smell.
   - **Resolved:** define ONE contract — thread-local, ref-counted,
     exception-safe `pause()`/`resume()` — implemented identically by each
     pausable engine; `pubrun.paused()` is a thin façade that walks them. The
     mental model is now uniform across engines.

2. **"tee pauses everyone" — is that intrinsic?** The architect claimed a tee
   pause would suppress all threads' recording.
   - **Maintainer pushback + correction:** that is only true of a *naive shared
     boolean*. A **thread-local** gate makes the tee suppress only the calling
     thread's recording; output still prints for all threads. The architect
     retracted the claim as an implementation artifact, not an inherent property.
     Thread scope = thread-local, confirmed.

3. **Is the tee even worth it / what is the use case?** The architect (reasoning
   as an engineer) suggested shipping only the cheap subprocess half.
   - **Maintainer pushback:** that conflates implementation cost with user value.
     The use case is one coherent, stupid-simple story: *capture everything,
     silence a noisy block, resume.* Dropping console pausing makes it incoherent.
   - **Architect conceded the objection was invalid** and recorded the correction.
     The tee IS in scope; the use case is real.

4. **Which engines get `pause()`/`resume()`?** Grounded in `tracker.py`'s five
   engines.
   - **Resolved by a principle:** only *synchronous, calling-thread, ambient*
     recorders are pausable → **subprocess spy + console tee** (with
     `print/open/popen` honoring the same flag). **Resource watcher OUT** (async,
     own thread; RAM/CPU are process-wide and should still count). **Event stream
     / annotate / phase OUT** (explicit user markers keep firing). Maintainer
     agreed 100%.

## Gaps / assumptions surfaced

- The only remaining genuine trade-off is the **per-write thread-local lookup on
  the tee's hot path** — now recorded as an explicit pre-merge benchmark gate
  (the `benchmarks/` harness exists to check it).
- Passthrough to the terminal is always process-global (one `sys.stdout`); only
  the *recording decision* is thread-scoped. Documented so no one expects
  thread-isolated terminal output.

## Improvements agreed + edits applied (with consent)

The maintainer asked me to update the IPD with all resolved context. Applied:
- New "Use case" and "Resolved design" sections (thread-local mute; per-engine
  `pause()`/`resume()` + façade; principled pausable boundary; passthrough note;
  selectivity deferred).
- "Mechanism" section (mute chosen over unpatch) with concrete implementation
  seams and a **Performance gate**.
- Open questions → "Decisions (resolved) + remaining open" (only API-surface and
  the perf gate remain).
- Sharpened Required tests (thread-isolation test; annotate/phase still fire;
  disable_spy coexistence; perf).
- Status/gate updated: design resolved; next step is a normal plan-review of the
  concrete design.
- Added this session record cross-reference.

## Open follow-ups the author still owes

- Decide API surface: context-manager-only (recommended) vs. also bare
  `pause()`/`resume()`.
- Run a normal `plan-review` on the now-concrete design, then approve to build.
- At build: benchmark the tee thread-local gate; settle the perf gate.
