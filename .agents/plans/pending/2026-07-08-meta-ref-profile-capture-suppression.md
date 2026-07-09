# IPD: Should `PUBRUN_META_REF` / `core.profile` auto-suppress heavy capture?

- Date: 2026-07-08
- Concern: functionality / architecture (design decision)
- Scope: `src/pubrun/tracker.py`, `src/pubrun/capture/*`, `src/pubrun/config.py`, HPC docs
- Status: PENDING (awaiting human decision; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Origin

Surfaced while executing `2026-07-08-assess-use-cases.md` Step 4 (the HPC hydration e2e test).
Verification found a **doc/behavior mismatch**, since corrected in the README by the honest-docs
option:

- The README previously claimed *"Child scripts automatically skip heavy footprint tracking"* when
  `PUBRUN_META_REF` is set.
- In reality (verified), neither `core.meta_ref` nor `core.profile` suppresses **any** capture at
  runtime. `meta_ref` is only recorded into `manifest["meta_ref"]` (`tracker.py:607`) and consumed
  at **report time** by `hydrate_manifest` (`report/utils.py:50`). Capture is suppressed only by
  explicit `capture.<engine>.depth/mode = "off"` keys. `core.profile` is read at exactly one place
  in `src/` — `report/diagnostics.py:407` (display only) — and wired to no capture engine.

The use-cases plan took the in-scope path: **test real behavior + make the docs honest**. This IPD
captures the deeper product question it deferred.

## The question

Should pubrun make the HPC "light child" story true by design, so a child that references a parent
snapshot (and/or selects a lightweight `profile`) automatically skips the heavy, redundant capture
(hardware probe, full package enumeration, dependency graph) — the exact work the parent snapshot
already holds?

Two coupled sub-questions:

1. **`core.profile` wiring:** should `profile = "minimal"` actually map to reduced
   `capture.*.depth/mode` defaults (currently it is inert outside diagnostics)? This is a latent
   surprise: users setting `profile="minimal"` reasonably expect less capture and get none of it.
2. **`meta_ref`-driven suppression:** should the mere presence of `meta_ref` imply "the parent has
   the heavy context, so the child may default the heavy engines down"? Or should suppression stay
   fully explicit (current behavior) to avoid surprising, hard-to-debug capture gaps?

## Options (not yet chosen)

- **A — Wire `profile` to capture defaults (recommended starting point).** Make `minimal`/`default`/
  `deep` map to concrete `capture.*` default tiers, overridable by explicit keys. Fixes the inert-
  profile surprise; keeps `meta_ref` orthogonal (record + hydrate only). Remediation Risk: Medium
  (functionality — changes what a `profile` value captures; needs characterization tests pinning
  current per-profile manifests first, then the new intended behavior, plus doc sync).
- **B — `meta_ref` implies light child.** When `meta_ref` is set and the engine is at its default,
  auto-lower heavy engines. Remediation Risk: Medium-High (functionality + usability — implicit
  capture gaps are hard to debug; violates "no surprising silent behavior").
- **C — Keep explicit-only (status quo), rely on docs.** The README now documents the explicit
  `capture.*` recipe. Remediation Risk: Low, but leaves `core.profile` inert/misleading.
- **D — Remove/deprecate `core.profile`** if it is not going to drive capture, to stop implying a
  capability that does not exist. Remediation Risk: Low-Medium (API/compat surface).

## Recommendation to the maintainer

Decide A vs. C-with-D: either **make `profile` mean something** (A) or **stop implying it does** (D),
because the current inert `profile` is the real trap. Keep `meta_ref` suppression explicit (avoid B)
unless there is strong demand. This IPD does not execute; it needs a human design decision, ideally
via `/advise architect` or `/advise domain-expert`.

## Approval and execution gate

Proposal only. Requires human decision before any execution. On approval, a follow-up execution
would add characterization tests first (pin current per-profile capture), then implement the chosen
option, then sync docs/CHANGELOG, then move this IPD to `.agents/plans/executed/`.
