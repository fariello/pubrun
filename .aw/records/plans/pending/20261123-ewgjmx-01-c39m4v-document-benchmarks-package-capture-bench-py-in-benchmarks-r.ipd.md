# IPD: Document benchmarks/package_capture_bench.py in benchmarks/README.md

- Date: 2026-11-23
- Kind: child
- Concern: Benchmark suite documentation completeness
- Scope: Add a design bullet and a running subsection in `benchmarks/README.md` documenting `benchmarks/package_capture_bench.py`, its CLI flags, measurement profiles/modes, cold-versus-warm methodology, and local redacted output.
- Scope-Paths: benchmarks/README.md
- Item-Dependencies: none
- Status: to-review
- Work-Kind: chore
- Priority: low
- From-Backlog: ewgjmx
- Set: ewgjmx
- Order: 1
- Highest E allocated: 02
- Author: Antigravity
- Id: c39m4v

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 draft (Antigravity): created.
- 2026-11-24 to-review (Antigravity): graduated from backlog item `ewgjmx` into a review-ready plan.

## Goal

Document `benchmarks/package_capture_bench.py` in `benchmarks/README.md` with the same structure and detail used for `benchmarks/startup_breakdown.py` so contributors can discover and run the package-capture benchmark from the benchmark guide.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Document package_capture_bench.py in benchmarks/README.md

- [ ] E-01 Add a `package_capture_bench.py` bullet under `## Design` in `benchmarks/README.md`.
  - Depends on: none
  - Expected outcome: `## Design` lists `package_capture_bench.py` alongside `harness.py` and `startup_breakdown.py`, explaining that it is a stdlib-only, local, non-publishing benchmark measuring `startup` versus `finalization` package capture across all five package-capture modes and synthetic plus ambient profiles. Added prose contains zero em or en dashes.
  - Execution state: pending

- [ ] E-02 Add a `### Package capture benchmark` subsection under `## Running` in `benchmarks/README.md`.
  - Depends on: E-01
  - Expected outcome: `## Running` includes a `### Package capture benchmark` subsection matching the style of `### Startup and finalization breakdown`, with an example invocation, all six CLI flags and their defaults (`--small-count` default `10`, `--large-count` default `300`, `--repetitions` default `10`, `--cold-runs` default `3`, `--workdir`, `--json-out`), the five capture modes (`off`, `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment`), the three environment profiles (`small`, `large`, `ambient`), cold fresh-process versus warm cached passes, and the redacted local JSON output (`pubrun-package-capture-bench/1`). Added prose contains zero em or en dashes.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- Authoritative benchmark script `benchmarks/package_capture_bench.py` defines:
  - `SCHEMA_VERSION = "pubrun-package-capture-bench/1"`.
  - Capture modes: `off`, `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment`.
  - Profiles: `small`, `large`, `ambient`, each evaluated with cold (fresh subprocess) and warm (cached) passes across `startup` and `finalization` timing points.
  - `argparse` CLI flags in `main` / `_parse_args`: `--small-count` (default `10`), `--large-count` (default `300`), `--repetitions` (default `10`), `--cold-runs` (default `3`), `--workdir`, and `--json-out`.
  - Redaction and share-safety checks using `share_safety` helpers; script is local and never publishes.
- `benchmarks/README.md` already documents `startup_breakdown.py` with one bullet in `## Design` and a `### Startup and finalization breakdown` subsection under `## Running`.
- Agent execution contract: user-facing documentation (`benchmarks/README.md`) must contain zero em or en dashes in authored or edited prose.

## Findings

`benchmarks/package_capture_bench.py` exists and is tested, but `benchmarks/README.md` lists only `harness.py` and `startup_breakdown.py` under `## Design` and `## Running`. Contributors reading `benchmarks/README.md` have no guidance on how to run `package_capture_bench.py` or what flags and profiles it supports.

## Proposed changes (ordered, validatable)

1. **`benchmarks/README.md` (`## Design`, E-01):** Add one bullet for `package_capture_bench.py` right below the `startup_breakdown.py` bullet describing its role, stdlib-only local execution, and `share_safety` redaction.
2. **`benchmarks/README.md` (`## Running`, E-02):** Add a `### Package capture benchmark` subsection right after `### Startup and finalization breakdown` documenting:
   - Command example: `python3 benchmarks/package_capture_bench.py --json-out benchmarks/results/package-capture.json`
   - All six CLI flags and defaults verified directly against `python3 benchmarks/package_capture_bench.py --help`
   - The five modes (`off`, `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment`), three profiles (`small`, `large`, `ambient`), `startup` versus `finalization` timing points, and cold versus warm passes
   - Local redacted JSON output format (`pubrun-package-capture-bench/1`).

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Only `benchmarks/README.md` is edited.
- Under-scope: none. Every CLI flag, mode, profile, and output detail of `benchmarks/package_capture_bench.py` is documented.

## Required tests / validation

- Run `python3 benchmarks/package_capture_bench.py --help` and compare every documented flag and default in `benchmarks/README.md` against the actual help output.
- Confirm zero em or en dashes in the added lines of `benchmarks/README.md`.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

This plan is the documentation update for `benchmarks/package_capture_bench.py` in `benchmarks/README.md`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff benchmarks/README.md` showing the new `package_capture_bench.py` bullet under `## Design` with zero em or en dashes in added lines.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste `git diff benchmarks/README.md` showing the new `### Package capture benchmark` subsection under `## Running` with zero em or en dashes in added lines, paste the output of `python3 benchmarks/package_capture_bench.py --help` confirming every documented flag and default matches, and paste the output of `python3 scripts/sanitize_paths.py --check --all`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after this plan reaches `approved`. Execute `E-01` and `E-02`, verify `V-01` and `V-02` with pasted evidence, commit only `benchmarks/README.md` through `aw commit`, and complete the post-gate lifecycle transition under `ipd-lifecycle`.
