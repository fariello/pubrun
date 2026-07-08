# Decisions & assumptions — assess documentation (20260708-150038)

## Concern / scope
- Concern: documentation, accuracy-first (`lenses/documentation.md`).
- Scope: whole project docs; concentrated on the surfaces the 2026-07-07 CLI/UX batch touched
  (README CLI section, `docs/cli.md`, `docs/configuration.md`, `CHANGELOG.md`).

## Project conventions discovered
- `AGENTS.md` doc-sync discipline mandates this assessment after user-visible behavior changes.
- Lifecycle `.agents/plans/pending/` → `executed/`; assess IPD naming `YYYY-MM-DD-assess-<concern>.md`.
- Validation interpreter is `~/venv/p3.11.8` (the `p3.14` venv is gone this session); pubrun is
  installed editable there. Real behavior checked via `python -m pubrun <cmd> -h`.
- README is intentionally a condensed CLI index that links to `docs/cli.md` (keep it that way).

## Key decisions
- **Accuracy before completeness** (lens): ordered the two genuine behavior/accuracy defects
  (D1 `--passes` help, D2 `--no-baseline` CHANGELOG claim) ahead of the README-lag items.
- **D1 and D2 are self-inflicted by the batch** (my own IPD-G): the `--passes` help kept its
  pre-tier "(default 2)" string, and the CHANGELOG advertised a `--no-baseline` flag I only
  added to the harness. Both are honestly attributed and prioritized.
- Every finding is fix-by-default (all Low remediation risk). Nothing deferred on risk grounds.
- Explicitly NOT proposing (Complexity axis): duplicating the full `docs/cli.md` into the
  README; inlining the long rebuilt `[diff]` ignore lists verbatim (prefer prose + point at
  `default.toml`). One structural nit (duplicate `## pubrun_imports` heading in `manifest.md`)
  is out of scope (predates the batch) — noted for a later general cleanup.

## Verified accurate (and thus NOT proposed for change)
- `docs/manifest.md` — fully covers the batch's new fields (`resources.peak_tree_cpu_percent`
  + per-sample `tree_cpu_percent`; `python.environment_kind`/`in_venv`/`sys_path_len`).
- Nav-link integrity (README header/footer + CHANGELOG) — all resolve.
- CHANGELOG `[Unreleased]` covers the whole batch (only the D2 `--no-baseline` line is wrong).
- Roadmap "Future" items (Sphinx/MkDocs, plugin model, `register_artifact`, `register_metadata`)
  are genuinely unimplemented — accurate.
- `docs/configuration.md` `[capture.resources]` / `[capture.file_io]` defaults match `default.toml`.

## Open questions for the user
1. D2: expose `--no-baseline` on `pubrun bench` (forward to the harness — makes the CHANGELOG
   true + gives a useful skip toggle) vs. just correct the CHANGELOG? (Leaning: expose it.)
2. D8: inline the full rebuilt `[diff]` ignore lists in `configuration.md` vs. a concise
   per-level prose description pointing at `default.toml`? (Leaning: prose.)
