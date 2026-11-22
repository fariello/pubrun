# Evidence - assess use-cases (20260708-231828)

Reproducible record of what was inspected so the assessment can be re-run.

## Documents read (full)

- `README.md` (all 475 lines) - purpose, features, CLI reference, monitoring/liveness, HPC
  hydration, config, redaction, roadmap, citation. Key: l.7 principles; l.263 `resources` alias
  claim; l.168 recency-index `#` column; l.319-327 run-status table; l.323/331 SIGHUP.
- `docs/functional_spec.md` (l.1-120) - purpose (1), non-goals (1.1), core model (2), import &
  activation model (3), import-mode matrix (3.4).
- `docs/research-use.md` (all 61 lines) - actors ("author + ~4-6 URI researchers"), current-use
  durable-record list, l.22-34 "public example workflow should be added under examples/".
- `.agents/workflows/assess/lenses/use-cases.md`, `assess.md`, `fix-decision-policy.md`,
  `templates/ipd.md`, `templates/run-report.md` - the controlling workflow instructions.

## Commands run

- `ls .agents/plans/pending/` -> empty; `ls .agents/plans/executed/` -> existing dated IPDs
  (confirmed lifecycle convention + terminal dir).
- `grep` for guiding-principle / KISS / zero-dependency across docs+AGENTS+CONTRIBUTING.
- `python -m pubrun resources` -> **exit with argparse error** "unknown command 'resources'
  (choose from: init, report-bug, ... res, run, show, status, ui)" - direct reproduction of U1.
- `python -m pubrun res --help` -> confirms `res` is the real subcommand.
- `grep "resources\|monitor\|chart\|stats"` in `docs/cli.md`, `tests/test_cli.py`,
  `tests/test_show_sections.py` - confirmed no doc/test guards the `resources` alias; README.md:263
  is the only place it's promised.

## Source inspected (targeted)

- `src/pubrun/__main__.py:2385-2414` - dispatch block; confirmed `res/resources/monitor/chart/
  stats/cpu/mem` handled at :2390 but only res/cpu/mem registered as subparsers.
- Recency-index resolution (`status.py:601,628-638`), `#` column (`status.py:844,873`) - confirmed
  via exploration agent, matches README.

## Delegated exploration (two `explore` agents, medium/thorough)

1. **CLI + examples + recency + Jupyter inventory** - enumerated all argparse subparsers
   (`__main__.py:1995-2316`), diagnostic flags (:1980-2336), the `examples/` tree (numbered
   00-11 + `verify_all.py` + `minimal-research-workflow/`), recency-index logic, and the Jupyter/
   non-TTY guards (`capture/console.py:36-83`, `resources/default.toml:99,105`). Established that
   the docs-requested public example already exists (U7) and the `resources` alias is broken (U1).
2. **Test-suite scenario coverage** - inventoried all 39 test files and mapped each rubric
   scenario to present/partial/absent with test-name + file:line. Established: strong coverage;
   gaps = `pubrun init` untested (U3), SIGHUP + real-SIGKILL crashed (U4), HPC e2e + dead
   `hpc_node.py` (U5), two-live-runs concurrency (U6). Listed all `skipif`/`pytest.skip` markers
   and reasons.

## Sampling / truncation notes

- `docs/functional_spec.md` read to line 120 of 818 (purpose/non-goals/import model - the
  use-case-relevant portion); deeper config-key sections not exhaustively read (owned by the
  configuration/documentation lenses).
- Test coverage was surveyed via a thorough exploration pass over all 39 files rather than
  reading each in full; findings that hinged on a specific claim (U1) were additionally
  reproduced directly at the shell.

## Out of review scope (not assessed as the project)

- `.agents/workflows/` (the framework itself) and `workflow-artifacts/` run records, per the
  release-review scope-exclusion rules referenced by the harness.
