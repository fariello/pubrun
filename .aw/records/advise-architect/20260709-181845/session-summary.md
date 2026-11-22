# Advise session - architect

- Persona: **architect** (`.agents/workflows/advise/personas/architect.md`)
- Artifact: `.agents/plans/pending/2026-07-08-meta-ref-profile-capture-suppression.md`
- Date / run ID: 20260709-181845 (UTC)
- Outcome: **Decision reached — Option D** (remove `core.profile` with a soft, non-disruptive
  deprecation). IPD updated in place with consent.

## What was examined

The design-decision IPD asking whether `PUBRUN_META_REF` / `core.profile` should auto-suppress
heavy capture. Options on the table: A (wire `profile` to real capture tiers), B (`meta_ref` implies
light child), C (keep inert, fix docs/TUI honesty only), D (remove/deprecate `profile`).

## Key questions raised (architect) and the author's answers/decisions

1. **"Where is the source of truth for capture depth, and does A create two masters?"** — Established
   that A adds a second input (`profile`) over the existing explicit `capture.*` keys, raising a
   resolution-order question. Author initially did not follow Option A; the agent re-explained it in
   plain terms (profile = a master dial meant to turn the per-engine knobs down; the bug is the dial
   isn't wired).
2. **"What future change does each option make cheap/expensive?"** — The master-dial fans-out-to-N
   design is a drift magnet (adding an engine means updating the tier map or it silently half-works —
   the very way this bug was born). D deletes the coupling; A only manages it.
3. **"Does A even fix the originating problem?"** — No: A keeps `meta_ref` orthogonal, so HPC children
   are not automatically lighter under A. A was oversold as "makes the HPC story true."
4. **Author's pivot — "if we kept the promise, how do we handle conflicts without disrupting the
   imported script, and is config captured as metadata?"** — Answered:
   - Config **is** already captured per run as `config.resolved.json` (`writer.py:73`, ref
     `tracker.py:633`); only *resolution provenance* is missing.
   - Non-disruption invariant: a conflict must be **data, not an event** — recorded in the manifest,
     never raised / never a host-visible warning (mirrors ghost mode).
   - Resolution rule (if A kept): specific-wins, `profile` expands at the **bottom** of the 5-layer
     stack (built-in → profile → user → local → env → API).
   - This *reinforces D*: honest conflict-surfacing needs value-provenance machinery; D makes
     conflicts impossible (one source of truth), so there is nothing to surface.
5. **Deciding question — "has anyone ever actually wanted a one-line capture-depth dial?"** — No
   demonstrated demand identified → D.

## Gaps / assumptions / risks surfaced

- **Assumption corrected:** author assumed config was not captured; it is (`config.resolved.json`).
- **Honesty violation is broader than one line:** three surfaces promise a capture effect that does
  not exist — `docs/configuration.md:47`, the TUI selector label, and `default.toml:21`'s comment.
- **CLI-grammar collision risk** flagged for the future `show config` work: `show <run> <section>` vs.
  `show <keyword> config`.
- **Risk of picking D for the wrong reason:** choose D because the abstraction isn't earning its keep,
  not merely because it is less work than A.

## Improvements agreed (edits applied with consent)

- IPD `2026-07-08-meta-ref-profile-capture-suppression.md`: updated Status, Recommendation
  (D + soft deprecation; A/B/C recorded as considered-and-not-chosen), added an "Architect session
  outcome" section (conflict-handling reasoning), and rewrote the execution gate for D (accept-but-
  inert + non-raising deprecation notice; fix `default.toml:21`, the TUI selector, docs).
- `TODO.md` ("Deferred ideas"): added the `profile`-independent **`pubrun show config` family**
  spinoff (`show config` / `show run config [<id>]` / `show default config`, each highlighting config
  ambiguities and their resolution), with the CLI-grammar collision noted.

## Open follow-ups the author still owes

- **Approve execution of Option D** (this IPD is decided but not executed).
- Optional: a `domain-expert` session could still overturn toward A if HPC users are shown to want the
  light-child dial — absent that signal, D stands.
- The `pubrun show config` / config-provenance feature needs its own IPD when prioritized.
