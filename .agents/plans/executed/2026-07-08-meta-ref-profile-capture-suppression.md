# IPD: Should `PUBRUN_META_REF` / `core.profile` auto-suppress heavy capture?

- Date: 2026-07-08
- Concern: functionality / architecture (design decision)
- Scope: `src/pubrun/tracker.py`, `src/pubrun/capture/*`, `src/pubrun/config.py`,
  `src/pubrun/tui/widgets/config.py` (the profile selector), `docs/configuration.md`, HPC docs
- Status: EXECUTED 2026-07-09 (Option D, soft deprecation). Full suite green (877 passed, 2 skipped).
  Execution surfaced + fixed a pre-existing `pubrun.report` subpackage-shadowing bug (scope expanded
  with maintainer approval). See "Execution notes" below.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Execution notes (2026-07-09)

Executed after `/advise architect` settled Option D and the maintainer approved skipping a redundant
plan-review. Deprecation notice surfacing was chosen **manifest-only** (never `warnings.warn`/raise,
per the non-disruption invariant), then surfaced in the human-facing commands so it is not buried.

- **`core.profile` deprecated + inert (as designed).** New `profile_deprecation_notice()`
  (`config.py`) returns a machine-readable notice for a non-default `profile`; the tracker records it
  in `manifest.config.notices` (`tracker.py`), never raising into the host (mirrors ghost mode).
- **Surfaced in `pubrun show`** (diagnostics `[WARN ]` line), **`pubrun inspect`** (a
  `profile_deprecated` finding via `report/checks.py`, so `--json` too), **`pubrun status <id>`**
  (a Notices block via `RunInfo.config_notices` + `render_inspect`), and a discovery hint in the
  **`pubrun status`** list footer.
- **Honesty fixes:** `default.toml` comment, the TUI selector label (`tui/widgets/config.py`),
  `docs/configuration.md` (`profile` row + `PUBRUN_PROFILE` + the example), and README `profile=`
  snippets. `profile`/`PUBRUN_PROFILE`/`start(profile=)` are still accepted (no breakage).
- **Characterization test** pins the pre-existing reality (profile does not gate capture).

### Scope expansion (maintainer-approved): pre-existing `pubrun.report` shadowing bug

Executing the surfacing tests surfaced an **unrelated, pre-existing** defect: every import-mode module
and the deferred `__init__` did `_pkg.report = report`, overwriting the `pubrun.report` **subpackage**
(a CallableModule) with the plain `report()` function. In some import orders this left `pubrun.report`
as a function, so `import pubrun.report.diagnostics` (`.output`/`.checks`) raised `ImportError`. The
maintainer approved fixing it in this IPD **with deep tests for the bug class**.

- **Fix:** import the `pubrun.report` subpackage (keeping the CallableModule — callable *and*
  submodule-bearing) instead of assigning the function, across all 6 mode modules + `__init__.py`.
  `pubrun.report(...)` remains callable AND `import pubrun.report.<submodule>` works.
- **Deep tests** (`tests/test_report_subpackage_integrity.py`): `report` is callable + all report
  submodules import under **every** import mode (auto/noauto/full/nopatch/noconsole/minimal, each in a
  fresh subprocess); a same-process call+submodule coexistence test; and a **generalized guard** that
  no mode module shadows *any* `pubrun` subpackage (catches the whole class, not just `report`).

### Environment note

Dev/validate moved to `~/venv/p3.14` (the only venv now present; `p3.11.8` is gone). Installed
`pytest==8.2.2` there. CI command `pytest tests/ -v` unaffected.

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

**Decision (2026-07-08, after `/advise architect`): Option D — remove `profile`, with a soft
deprecation.** Stop offering a dial that never worked; accept `profile=`/`PUBRUN_PROFILE` for a
release but ignore it for capture and emit a non-disruptive notice that it was removed because it
never took effect (use `capture.*` keys instead). Rationale below (Architect session outcome).

Alternatives considered and not chosen:
- **A (wire `profile` to capture tiers):** only justified with positive evidence that users want a
  one-line convenience dial — no such demand was identified. A also signs the project up for tracking
  value-provenance through config resolution to surface conflicts honestly (see below), i.e. real
  machinery to prop up a feature of unproven value.
- **C (keep inert, fix docs/TUI only):** the cheap holding position, but leaves a dead knob in the
  config that does nothing — its own small dishonesty — and defers the decision indefinitely.
- **B (`meta_ref` implies light child):** rejected — implicit, hard-to-debug capture gaps.

Keep `meta_ref` suppression explicit regardless. A `domain-expert` session could still overturn this
toward A if HPC users turn out to want the light-child dial, but absent that signal, D is the call.

## Architect session outcome (2026-07-08)

Recorded from the `/advise architect` session that settled the A-vs-D fork.

- **The originating problem (HPC light-child) is separable from `profile`.** Option A would *not* make
  `meta_ref` children automatically lighter (A keeps `meta_ref` orthogonal); it only fixes the
  `profile` honesty bug. So A was oversold as "makes the HPC story true by design" — it does not.
- **The master-dial abstraction is a drift magnet.** `profile` is broken today precisely because a
  one-dial-fans-out-to-N-settings design rots when someone adds an engine and forgets the tier map.
  A *manages* that coupling (and must prevent the map drifting out of sync with the engine set); D
  *deletes* it. D makes the failure mode impossible rather than merely handled — the stronger
  structural choice, and aligned with the project's KISS / "stupidly simple" principle.
- **Conflict handling (if A were kept) — the invariant that constrains it:** a config conflict must be
  **data, not an event**. Never raise, never `logging.warning` into the host; a conflict degrades to a
  *recorded fact* in the manifest (mirroring ghost mode), so the imported script is never disrupted.
- **Conflict resolution rule (if A were kept):** the more specific setting wins, silently, at the
  resolution layer — `profile` expands to per-category defaults at the **bottom** of the stack
  (built-in → profile expansion → user → local → env → API explicit keys), so any explicit
  `capture.*` at any layer overrides it. This is the only ordering explainable in one sentence.
- **Why this reinforces D:** surfacing conflicts *well* requires tracking each key's profile-implied
  value through the merge and diffing it at the end — real provenance machinery to support a
  low-demand feature. **D makes conflicts impossible (one source of truth), so there is nothing to
  surface.** The conflict-handling requirement is therefore an argument *for* D, not for keeping A.
- **Config is already captured (corrects an assumption):** the fully-resolved config is written per
  run as `config.resolved.json` (`writer.py:73`, referenced at `tracker.py:633`). What is missing is
  only *resolution provenance* (which layer won a given key).
- **Valuable spinoff, `profile`-independent:** recording config *override provenance* in the manifest
  (e.g. "local config overrode home config's `capture.packages.mode`") is useful reproducibility
  metadata regardless of A/C/D, and it makes D *easier* (you get the "tell me why my config isn't what
  I expected" benefit without the drift-prone dial). Captured as a future idea in `TODO.md` under
  "Deferred ideas" as the **`pubrun show config` family** (`show config` / `show run config [<id>]` /
  `show default config`, each highlighting ambiguities and how they resolved). That work carries a
  known CLI-grammar collision to design deliberately (`show <run> <section>` vs. `show <keyword>
  config`).

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

Decision made (Option D). Requires approval to **execute**. On approval, execution for D would:

1. **Characterization test first (rubric D):** add a test pinning the CURRENT reality — `profile`
   does **not** gate capture (`profile="minimal"` vs `"deep"` produce identical `capture_state`
   outcomes). There is currently no such test; it is the anti-regression baseline that documents the
   pre-removal behavior deliberately.
2. **Implement D (soft deprecation, non-disruptive):**
   - `config.py` — continue to *accept* `profile` (config key, `PUBRUN_PROFILE` env at `:156-158`,
     `start(profile=)` shortcut at `:169`) so no import breaks, but treat it as inert-by-design and
     emit a **recorded, non-raising** deprecation notice (never an exception into the host; the
     manifest is the surface, mirroring ghost mode).
   - `src/pubrun/resources/default.toml:21` — remove/repair the false "Master profile controlling
     capture depth" comment.
   - `tui/widgets/config.py:59-60` — remove the "Profile Mode (Controls telemetry depth)" selector or
     relabel it to stop promising a capture effect.
3. **Spec/doc sync:** `docs/configuration.md:47` and `:326` (drop/deprecate the capture-depth claim),
   README/`__init__.py`/examples `profile=` snippets, and a CHANGELOG entry (deprecation + "never
   worked" note).
4. Move this IPD to `.agents/plans/executed/`.

Note: the config-provenance / `pubrun show config` spinoff is **out of scope for D** and tracked
separately in `TODO.md` ("Deferred ideas"); it needs its own IPD.
