# IPD: Assess Documentation - Factual Accuracy and Completeness

- Date: 20260704
- Concern: documentation (accuracy, completeness, consistency)
- Scope: all docs/ files, README.md, CHANGELOG.md
- Status: PENDING (partially executed — doc fixes committed; remaining items below)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Ensure all documentation accurately reflects the current implementation. Every
claim about defaults, behavior, config keys, and CLI commands must match the
actual source code.

## Project conventions discovered (Step 0)

- Pending-plans location: `.agents/plans/pending/`
- Docs live in `docs/*.md` + `README.md` + `CHANGELOG.md`
- Canonical source of truth for defaults: `src/pubrun/resources/default.toml`
- Canonical source of truth for CLI: `__main__.py` argparse definitions

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Status |
|----|----------|------------------|---------|------|---------|--------|
| DOC-01 | High | Low | Novice | api.md | Claimed capture tees by default — wrong (now "off") | FIXED |
| DOC-02 | High | Low | Novice | README.md | Same stale claim about default tee behavior | FIXED |
| DOC-03 | High | Low | Engineer | configuration.md | capture_mode default listed as "standard" — wrong | FIXED |
| DOC-04 | Medium | Low | Engineer | configuration.md | Missing 6 new config keys (non_tty_mode, jupyter_mode, scope, check_dirty, flush_interval, profiling) | FIXED |
| DOC-05 | Medium | Low | Engineer | configuration.md | write_summary default listed as "true" — wrong (now false) | FIXED |
| DOC-06 | Medium | Low | Novice | cli.md | Missing `pubrun init` command | FIXED |
| DOC-07 | Medium | Low | Power-user | cli.md | `resources` command should be `res` (aliases dropped in 1.3.0) | FIXED |
| DOC-08 | Medium | Low | Power-user | cli.md | `report` command should be `show` (renamed in 1.3.0) | FIXED |
| DOC-09 | Medium | Low | Novice | cli.md | Missing status summary line documentation | FIXED |
| DOC-10 | Medium | Low | Engineer | functional_spec.md | Missing `imported-transitive` package mode | FIXED |
| DOC-11 | Medium | Low | Engineer | functional_spec.md | ResourceWatcher missing scope/tree docs | FIXED |
| DOC-12 | Medium | Low | Engineer | functional_spec.md | Missing phase-scoped profiling section | FIXED |
| DOC-13 | Medium | Low | Engineer | manifest.md | Missing `imported-transitive` in packages.mode | FIXED |
| DOC-14 | Medium | Low | Engineer | architecture.md | Missing `imported-transitive` in packages modes | FIXED |
| DOC-15 | Medium | Low | Novice | api.md | Missing print/open/subprocess/popen from API docs | FIXED |
| DOC-16 | High | Low | Stakeholder | CHANGELOG.md | No [Unreleased] entries for today's substantial changes | FIXED |
| DOC-17 | Low | Low | Novice | README.md | "thirteen commands" should be "fourteen" (init added) | FIXED |
| DOC-18 | Low | Low | Engineer | functional_spec.md | Section 3.2 says "MUST NOT wrap stdout unless configured" — now correct (was ahead of code; code caught up) | N/A (already correct) |

## Remaining items (not yet addressed)

| ID | Severity | Area | Finding |
|----|----------|------|---------|
| DOC-19 | Low | docs/architecture.md | System components list (Section 21) missing: `resolve_console_mode`, `capture/profiling` concept, `_get_tree_rss_*` functions |
| DOC-20 | Low | docs/cli.md | `cpu` and `mem` commands not documented as standalone sections (only mentioned under `res`) |
| DOC-21 | Low | docs/manifest.md | Missing `profiling` manifest section, `data_files` section, `pubrun_imports` section fields, `resources.scope`/tree fields |

## Approval and execution gate

DOC-01 through DOC-18 were already fixed (docs-only, Low remediation risk).
DOC-19 through DOC-21 remain pending — approve to execute these remaining items.
