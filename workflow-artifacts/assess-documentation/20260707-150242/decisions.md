# Decisions & assumptions — assess documentation (20260707-150242)

## Concern / scope assessed
- Concern: documentation, accuracy-first (per `lenses/documentation.md`).
- Scope: whole project docs; concentrated on the user-facing surface most likely to have
  drifted after this session's 1.4.0-era changes: `README.md`, `docs/cli.md`, `CHANGELOG.md`.

## Project conventions discovered
- Guiding principles: `AGENTS.md` (doc-sync discipline mandates `/assess documentation`
  after user-visible behavior changes; honest docs). KISS / zero-dep / condensed-README
  ethos observed across the doc set.
- Lifecycle: `.agents/plans/pending/` → `.agents/plans/executed/`, dated IPDs. Assess IPDs
  use `YYYY-MM-DD-assess-<concern>.md` (prior examples in `executed/`).
- `docs/cli.md` is the exhaustive CLI reference; README carries a condensed CLI index. This
  division is intentional and is preserved in the plan (no README bloat).

## Key decisions
- **Accuracy before completeness** (lens emphasis): the plan orders inaccuracy fixes
  (removed/renamed commands, wrong counts, shipped-as-future roadmap) ahead of the
  completeness gap (missing README CLI entries) and consistency polish (dup License/citation,
  nav).
- **Every finding is fix-by-default** — all are documentation-only, Low Remediation Risk.
  Nothing deferred on risk grounds.
- **D14 (design note not in nav) is a deliberate no-op**, not a deferral: it is an internal
  `docs/design/` note, not part of the user-facing index.
- **Explicitly NOT proposed (Complexity axis):** (a) duplicating the full `docs/cli.md` into
  the README; (b) auto-generating the command list from `-h` at build time (adds a build
  dependency the zero-dep project avoids). The plan keeps the README a hand-maintained
  condensed index.

## What was verified accurate (and thus NOT proposed for change)
- All README nav links resolve; `docs/cli.md` nav complete.
- Roadmap items 1/3/4/5 (Sphinx/MkDocs, plugin model, `register_artifact`,
  `register_metadata`) are genuinely unimplemented (`grep` in `src/pubrun` found none) — they
  are correctly listed as future and are left alone.
- `docs/configuration.md` accurately documents `[capture.file_io].level="stat"` (default),
  `[capture.resources].system_metrics`, and correctly omits any `[capture.filesystem]` key —
  matching the data-quality IPD's decision that the live probe is CLI/diagnostic-only.

## Open questions for the user
1. Count phrasing: non-brittle wording vs. stating the exact number (20)? (Assumption:
   non-brittle.)
2. Shipped roadmap items: delete vs. a short "Recently shipped (see CHANGELOG)" note?
   (Assumption: a one-line shipped note.)
3. Confirm README CLI stays a condensed index linking to `docs/cli.md` (Complexity axis).
