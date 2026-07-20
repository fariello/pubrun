# Decisions & assumptions - assess documentation (20260719-230705)

## Concern / scope

- Concern: **documentation** (lens `.agents/workflows/assess/lenses/documentation.md`), accuracy-first.
- Scope: whole project, concentrated on the CLI/config/manifest surface that the recent `show config`
  family + schema work touched or exposed (README, docs/cli.md, docs/configuration.md,
  docs/manifest.md, schemas/manifest.schema.json). Triggered by the `AGENTS.md` doc-sync discipline
  after `show config` shipped this session.

## Project conventions discovered

- No `GUIDING_PRINCIPLES.md`; principles from README/AGENTS/CONTRIBUTING (zero-dep, honest docs,
  never-intrude, doc-sync + matrix-validation disciplines).
- Five-state plan lifecycle (`pending/executed/superseded/not-executed/reusable/`), filename
  `YYYYMMDD-HHMM-NN-<slug>.md`, `Status:` front-matter born `to-review`. Followed for this IPD
  (`.agents/plans/pending/20260719-2307-01-assess-documentation.md`).

## Key decisions

- **Verdict: adequate.** The docs shipped THIS session (show config in cli.md, the configuration.md
  cross-link, manifest.md notices/pending/timeout) are accurate - verified line-by-line. The findings
  are a small set of real inaccuracies on ADJACENT surfaces, so the doc set is healthy, not broken.
- **Fixed-by-default, inaccuracies first.** All 4 findings are Low remediation risk; none deferred.
  Ordered accuracy-first per the lens ("prefer fixing inaccuracies before filling gaps").
- **Re-opened the evidence.** Did not trust the exploration agent's report on the load-bearing
  findings: independently confirmed D1 (README has zero `show config` mentions; `--show-config` row
  at README.md:301 has no deprecation), D2 (source_files object-vs-string), and D4 (code supports
  `imported-transitive` at packages.py:41; schema enum omits it).
- **D4 kept in-scope despite being schema-not-prose.** It is a genuine accuracy defect (code+doc say
  a mode exists; the contract schema would reject it) surfaced by the doc sweep, and it matches this
  repo's contract-honesty + matrix-validation discipline. Recorded as a finding rather than dropped;
  flagged as a contract change requiring CI-matrix validation. Open question #2 offers splitting it
  to its own tiny IPD if the maintainer prefers.

## What was intentionally NOT proposed (and why)

- **README pub/research reframe** - a separate, already-drafted decision (the pending README-reframe
  IPD). Pre-empting it here would collide with that work; explicitly out of scope.
- **Prose-style polish** - belongs to the `prose` lens, not the accuracy-focused documentation lens.
- **The show-config docs themselves** - verified accurate this run; nothing to change.
- **A broad schema audit beyond D4** - the `imported-transitive` gap was the one packages-mode drift;
  a full schema re-audit is out of this run's scope (the conformance gate + prior reconciliation cover
  the rest).

## Open questions for the user

Carried into the IPD: (1) README `show config` prominence (one line vs. subsection - recommend one
line); (2) fix D4's schema enum here vs. a separate contract IPD (recommend here).
