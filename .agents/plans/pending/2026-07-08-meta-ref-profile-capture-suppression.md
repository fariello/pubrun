# IPD: Should `PUBRUN_META_REF` / `core.profile` auto-suppress heavy capture?

- Date: 2026-07-08
- Concern: functionality / architecture (design decision)
- Scope: `src/pubrun/tracker.py`, `src/pubrun/capture/*`, `src/pubrun/config.py`,
  `src/pubrun/tui/widgets/config.py` (the profile selector), `docs/configuration.md`, HPC docs
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
  explicit `capture.<engine>.depth/mode = "off"` keys. **No capture engine reads `core.profile`**
  (verified: `grep profile src/pubrun/capture/*.py` returns only unrelated macOS `system_profiler`
  hits and a host docstring).

**The inert-`profile` trap is worse than a single display line — three surfaces actively promise a
capture-depth effect that does not exist (verified during plan-review):**

1. **Docs:** `docs/configuration.md:47` documents `profile` as *"Master capture depth … Controls
   default depth for all categories unless overridden."* — false.
2. **TUI:** `src/pubrun/tui/widgets/config.py:59-60` renders a selector labeled *"Profile Mode
   (Controls telemetry depth)"* with Default/Minimal/Deep, and writes the choice to
   `core.profile` (`config.py:128-129`) — a user-facing control with no effect.
3. **Display:** `report/diagnostics.py:407` prints the profile value (harmless).

Other `profile` surfaces that any decision must account for (verified): the `PUBRUN_PROFILE` env
var (`config.py:156-158`), the `start(profile=...)` / decorator kwarg shortcut
(`config.py:169` `_CORE_SHORTCUTS`), the `examples/`/README API snippets, and `meta_snapshot.py:25`
(which passes `profile` into config but then explicitly overrides `capture.packages.mode`, so profile
still does not gate its capture).

The use-cases plan took the in-scope path: **test real behavior + make the README honest** (the
README HPC claim is fixed; `docs/configuration.md:47` and the TUI label are NOT yet fixed and are in
scope for whichever option is chosen here). This IPD captures the deeper product question it deferred.

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
  `deep` map to concrete `capture.*` default tiers, overridable by explicit `capture.*` keys (so the
  precedence stays: explicit key > profile tier > built-in default). This is what `default.toml:21`'s
  own comment ("Master profile controlling capture depth across all categories, unless...") already
  *promises*. Fixes the inert-profile surprise **and** makes the docs/TUI labels true; keeps
  `meta_ref` orthogonal (record + hydrate only). Must also: keep the TUI selector
  (`tui/widgets/config.py:59-60`) — now honest — and update `docs/configuration.md:47`. Remediation
  Risk: Medium (functionality — changes what a `profile` value captures; needs characterization tests
  pinning current per-profile manifests first, then the new intended behavior, plus doc sync).

  *Draft tier mapping (starting point for the decision — the maintainer confirms the exact values):*

  | `capture.*` key | built-in default | `minimal` | `default` | `deep` |
  |---|---|---|---|---|
  | `hardware.depth` | `basic` | `off` | `basic` | `deep` |
  | `packages.mode` | `imported-only` | `off` | `imported-only` | `full-environment` |
  | `environment.depth` | `standard` | `basic` | `standard` | `deep` |
  | `process.depth` / `python.depth` / `git.depth` / `host.depth` | `standard` | `basic` | `standard` | `deep` |
  | `resources.depth` | `standard` | `off` | `standard` | `deep` |
  | `subprocesses.depth` | `basic` | `off` | `basic` | `deep` |

- **B — `meta_ref` implies light child.** When `meta_ref` is set and the engine is at its default,
  auto-lower heavy engines. Remediation Risk: Medium-High (functionality + usability — implicit
  capture gaps are hard to debug; violates "no surprising silent behavior"). **Recommend against.**
- **C — Keep explicit-only (status quo).** NOTE: this is **not** a pure no-op — `docs/configuration.md:47`
  and the TUI label (`tui/widgets/config.py:59`) still falsely promise a capture-depth effect, so even
  C requires doc/label corrections to be honest. Leaves `core.profile` inert but truthfully described.
  Remediation Risk: Low.
- **D — Remove/deprecate `core.profile`** to stop implying a capability that does not exist.
  Remediation Risk: Low-Medium (API/compat surface). Must handle the full profile surface (see
  inventory below): the TUI selector, `PUBRUN_PROFILE`, the `start(profile=)` kwarg shortcut, the
  README/examples snippets, `docs/configuration.md`, and `meta_snapshot`'s `profile` passthrough.

### Profile surface inventory (what A or D must touch — verified during plan-review)

| Surface | Evidence | A (wire) | D (remove/deprecate) |
|---|---|---|---|
| Config key + comment | `default.toml:21`, `config.py:169` | make comment true | remove key + comment |
| Env var `PUBRUN_PROFILE` | `config.py:156-158` | keep (now effective) | deprecate w/ warning |
| API kwarg `start(profile=)` | `config.py:169` `_CORE_SHORTCUTS`; `core.py:124,210,240` docstrings | keep | deprecate w/ warning |
| TUI selector "Controls telemetry depth" | `tui/widgets/config.py:59-60,128-129` | keep (honest) | remove or relabel |
| Docs | `docs/configuration.md:47,326`; `README`/`__init__.py` snippets | correct wording | remove/deprecate note |
| Meta snapshot passthrough | `meta_snapshot.py:25` | reconcile w/ its explicit `packages.mode` override | leave (uses explicit override) |

## Recommendation to the maintainer

Decide A vs. C vs. D: either **make `profile` mean something** (A), **keep it inert but describe it
honestly** (C, docs+TUI corrections only), or **stop offering it** (D). All three fix the "honest
docs" violation; the real fork is whether `profile` becomes a real feature (A) or is retired (D), with
C as the minimal honest holding position. Keep `meta_ref` suppression explicit (avoid B) unless there
is strong demand. This IPD does not execute; it needs a human design decision, ideally via
`/advise architect` (compat surface of A vs. D) or `/advise domain-expert` (do HPC users want the
light-child story enough to justify A).

## Plan-review revisions (2026-07-08)

Hardened by the `plan-review` workflow (re-opening the source, not trusting the plan's self-
description). No deferrals (all Remediation Risk Low). Revisions:

- **P1 (High, accuracy):** the claim "`profile` read at exactly one place, display only" was
  incomplete. Verified two more surfaces that actively promise a capture-depth effect —
  `docs/configuration.md:47` ("Controls default depth for all categories") and the TUI selector
  `tui/widgets/config.py:59` ("Profile Mode (Controls telemetry depth)"). Corrected the Origin
  section; the trap is a real honest-docs violation across three surfaces, not one inert line.
- **P2 (High, under-scope):** Options A and D did not name the TUI selector or `docs/configuration.md`
  as required targets. Added them to Scope and to both options.
- **P3 (Medium, under-scope):** concretized the characterization-test baseline (there is currently
  NO test of profile's effect on capture; step 1 pins the current no-effect behavior first) and added
  the full profile-surface inventory (`PUBRUN_PROFILE`, `start(profile=)` kwarg, meta_snapshot passthrough).
- **P4 (Medium, decision-quality):** added a concrete draft capture-tier table for Option A and a
  surface-by-surface A-vs-D inventory, so the maintainer can actually decide rather than choose blind.
- **P5 (Low, spec-sync):** made the doc/label sync list explicit in the execution gate; clarified that
  even Option C is not a no-op (docs/TUI must be corrected to be honest).

## Approval and execution gate

Proposal only. Requires human decision before any execution. On approval, a follow-up execution would:

1. **Characterization tests first (rubric D):** add tests pinning the CURRENT per-profile manifests —
   i.e. assert that today `profile="minimal"`/`"deep"` produce identical `capture_state` outcomes (no
   effect) — so the intended change is provable as a deliberate behavior diff, not an accident. There
   is currently **no** test asserting profile's effect (or non-effect) on capture; this is the anti-
   regression baseline. (For C/D, the characterization test instead pins "profile does not gate
   capture" as intended.)
2. Implement the chosen option (wire tiers / correct docs+label / remove-deprecate).
3. **Spec/doc sync:** `docs/configuration.md:47` and `:326`, the TUI selector label, README/examples
   `profile=` snippets, and a CHANGELOG entry (behavior change for A; doc/deprecation for C/D).
4. Move this IPD to `.agents/plans/executed/`.
