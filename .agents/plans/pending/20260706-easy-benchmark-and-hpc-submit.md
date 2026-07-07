# IPD-C: easy benchmark runner + HPC auto-submit + opt-in manual result sharing

- Date: 2026-07-06
- Concern: usability / community data collection. Make it trivial for a user to run the
  benchmark suite, auto-detect an HPC (Slurm) environment and offer to submit to compute
  nodes, and then guide them to share results back — to build the multi-system dataset the
  JOSS paper needs.
- Scope: a new friendly entry point (a `pubrun bench` CLI command and/or a wrapper script)
  over the EXISTING `benchmarks/` harness + Slurm scripts; no change to `src/pubrun/`
  runtime behavior. The `[bench]` extra stays dev-only.
- Status: PENDING — plan-review, then execution on human approval. NOT auto-executed.
  Best sequenced AFTER IPD-A (so the richer per-pass/filesystem/Slurm fields are captured).
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

Today running the benchmarks requires knowing about `benchmarks/harness.py`,
`submit_bench.sh`, and a set of `PUBRUN_*` env vars (`run_bench.sbatch:26-30`,
`submit_bench.sh` node selection at `:30-64`). That is fine for the maintainer but too
much friction for a researcher who would otherwise contribute a data point. We want:
(1) one obvious command to run the suite locally; (2) automatic detection of Slurm (and
room for other schedulers) with an offer to submit to compute nodes; (3) a clear,
privacy-respecting path to send results back.

## Project conventions discovered (Step 0)

- Principles: zero runtime deps, KISS, honest docs, never intrude on host script.
- Existing benchmark tooling: `benchmarks/harness.py` (stdlib-only measurement core),
  `benchmarks/run_bench.sbatch`, `benchmarks/submit_bench.sh` (random idle node via
  `sinfo -h -t idle`), results in `benchmarks/results/<host>-<ts>.json`. The `[bench]`
  extra (matplotlib/pytest-benchmark) is dev-only and gated.
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Design decisions (agreed with maintainer)

- **Result sharing = MANUAL.** pubrun prints the results path and instructs the user to
  attach them to a GitHub issue/PR (URL provided). **No automatic transmission**, no
  server, no network dependency. Fully transparent; the user controls exactly what is
  shared. (Maintainer chose "Manual: print instructions to open a GitHub issue/PR".)
- **Measurement core stays stdlib-only**; the friendly runner adds no runtime dep. If it
  needs matplotlib for a summary chart, that stays behind the existing `[bench]` extra and
  degrades gracefully when absent.
- **HPC detection is best-effort and never coercive** — detect Slurm via `sinfo`/`sbatch`
  on PATH and `SLURM_*` env; if found, OFFER to submit (with a shown command) and, on
  confirmation, actually submit via the existing `submit_bench.sh`. Never auto-submit
  without explicit user confirmation. Architect the seam for other schedulers (PBS/LSF)
  but implement only Slurm now.

## Proposed changes

1. **New `pubrun bench` subcommand** (thin, friendly front-end over `benchmarks/harness.py`):
   - `pubrun bench` → run the suite locally with sensible defaults (the harness's existing
     two-pass design), print the results file path.
   - Auto-detects Slurm; if detected and not already on a compute node, prints the exact
     `submit_bench.sh` command and asks to submit (respects a `--yes`/non-interactive flag;
     never submits silently). Passes through partition/exclude/args.
   - On completion, prints the **manual share** guidance: results path + the GitHub issue/PR
     URL + a one-line summary of what the JSON contains (so users know what they'd share).
   - `--local` forces local even on HPC; `--submit` forces submit; `--json`/quiet options.
   - NOTE: the harness lives under `benchmarks/` which ships in the repo but may not be on
     an installed user's path — resolve its location robustly (packaged data vs repo
     checkout) or document that `pubrun bench` requires a source checkout. (Open question.)
2. **Small refactor of `submit_bench.sh`/`run_bench.sbatch`** only as needed to be callable
   from the new command with explicit args instead of only `PUBRUN_*` env vars (keep env
   vars working for backward compat).
3. **A `CONTRIBUTING`-style note / `benchmarks/README.md` section**: "How to contribute a
   benchmark data point" — run `pubrun bench`, then attach `benchmarks/results/<file>.json`
   to an issue at the given URL. State plainly what the JSON contains (host/hardware,
   timings, filesystem type, Slurm context) so contributors give informed consent.

## Anti-regression / invariants

- **Never auto-submit or auto-transmit.** Submission and sharing are both explicit,
  user-confirmed actions. Test that non-interactive default does NOT submit without `--yes`.
- **No new runtime dependency**; `pubrun bench` works with stdlib. Chart summary optional
  via `[bench]`, graceful when absent.
- **Existing scripts keep working** with their `PUBRUN_*` env-var interface (backward compat
  test / documented).
- **Honest data disclosure.** The share guidance accurately lists every field the result
  JSON contains (cross-check against IPD-A's schema/3).
- **Never crash on a locked-down node** (no scheduler, no network) — degrade to local run +
  print-path, with a clear message.

## Required tests / validation

- CLI: `pubrun bench --local` runs the harness and prints a results path (smoke; may be
  marked slow / few iterations in CI).
- Slurm detection unit test: given a fake PATH/env with/without `sbatch`/`SLURM_*`, the
  command reports detected/not-detected and, when detected, prints (does not execute) the
  submit command unless `--yes/--submit`.
- Non-interactive safety: default without `--yes` never submits.
- Share-guidance text lists the actual JSON fields (kept in sync with schema).
- Full suite green.

## Spec / documentation sync

`docs/cli.md` (`pubrun bench`), `benchmarks/README.md`, `docs/performance.md`,
`CHANGELOG.md`, and the contribute-a-data-point guidance. Run `/assess documentation`.

## Open questions (maintainer)

1. Should `pubrun bench` be a first-class CLI command (requires resolving where the harness
   lives for an installed user — package the harness as data, or require a source checkout?),
   or a documented wrapper script `benchmarks/bench.sh` that calls the harness? (Recommend:
   CLI command IF harness-location resolution is clean; else wrapper. Decide after checking
   packaging.)
2. Which GitHub URL for result submission — a dedicated issue template
   (`.github/ISSUE_TEMPLATE/benchmark-result.md`) so contributions are structured?
   (Recommend yes — add the template.)
3. Beyond Slurm, do you want the seam wired for PBS/LSF now, or Slurm-only with a documented
   extension point? (Recommend Slurm-only now, seam documented.)
4. Any fields in the result JSON you would NOT want contributors to share by default (e.g.
   hostname, username, sys_path which may leak home paths)? Consider a `--redact` option or
   redacting home paths in shared output. (Privacy — worth deciding.)

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.
