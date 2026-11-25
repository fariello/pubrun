# IPD: Fix performance, benchmarks, and changelog documentation drift

- Date: 2026-11-25
- Kind: child
- Concern: `benchmarks/README.md` inverts `harness.py`'s redacted-only default output behavior and has multiple stale script/gitignore claims; `docs/performance.md` reports an already-fixed timing bug (`uatvzh`) as active and embeds internal plan/backlog IDs; `CHANGELOG.md` `## [Unreleased]` has duplicated sections and superseded intermediate claims contradicting live code; and `CITATION.cff` has a release-date mismatch with tag `v1.3.1`.
- Scope: `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff`.
- Scope-Paths: benchmarks/README.md, docs/performance.md, CHANGELOG.md, CITATION.cff
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix benchmarks/README.md redacted-default inversion, docs/performance.md stale bug/IDs, CHANGELOG consolidation, and CITATION date
- Work-Kind: chore
- Priority: medium
- Set: doc-audit
- Order: 5
- Highest E allocated: 04
- Author: Antigravity
- Id: 77pdvl

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 4 documentation and metadata fixes (4 grouped findings across benchmarks, performance, changelog, and citation metadata)
- 2026-11-25 draft (Antigravity): created.

## Goal

Ensure `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff` accurately reflect the live benchmark harness, resolved timing defects, net `[Unreleased]` state on `main`, and release metadata.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix benchmark and performance documentation

- [ ] E-01 Fix all verified inaccuracies in `benchmarks/README.md` (with no em or en dashes in added or edited lines):
  - **Default output behavior**: correct the inverted default description (`results/<hostname>-<UTC-timestamp>.unredacted.json` + `--redacted-out`) to state that `harness.py` writes ONLY `benchmarks/results/pubrun-bench-<hash>-<UTC-timestamp>.redacted.json` by default, and writes `<hostname>-<UTC-timestamp>.unredacted.json` only when `--unredacted` (or `--out <path>`) is explicitly passed.
  - **Slurm & other schedulers**: update the Slurm output path (`benchmarks/results/pubrun-bench-${NODE}-${STAMP}.redacted.json` by default, matching `benchmarks/run_bench.sbatch`), fix the default pass count comment (3 measured passes + 1 baseline pass, not 2-pass), and note accurately that PBS/LSF/SGE scripts (`submit_bench_{pbs,lsf,sge}.sh`) currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"` (rather than claiming "Never a bare `*.json`" across all scripts).
  - **Scenarios, `.gitignore`, and paths**: replace `patched open() vs builtins.open` under `hotpath` with `pubrun.open()` and `pubrun.register_input()` vs `builtins.open()`; add `io_baseline` group and `io_sink` workload to the design inventory; fix `results/` git-tracking prose (`benchmarks/results/.gitignore` ignores everything except `.gitignore` and `*.redacted.json`, while committed summaries live in `benchmarks/data/summary.csv` and `benchmarks/data/summary.md`); normalize relative example paths to repo-root `benchmarks/results/...`.
  - Depends on: none
  - Expected outcome: Every output path, flag, scenario, workload, and `.gitignore` statement in `benchmarks/README.md` matches `benchmarks/harness.py`, `benchmarks/run_bench.sbatch`, `benchmarks/scenarios.py`, and `benchmarks/results/.gitignore`.
  - Execution state: pending

- [ ] E-02 Fix stale bug status, redacted-default ambiguity, and leaked internal IDs in `docs/performance.md` (with no em or en dashes in added or edited lines):
  - Clarify under output files that `harness.py` writes only the `.redacted.json` file by default (`.unredacted.json` is opt-in via `--unredacted` / `--out`) and align the filename note with `benchmarks/README.md`.
  - Update the `Known exception (backlog uatvzh)` passage to state that this exception applied to measured revision `af36c852` and has since been fixed (`src/pubrun/tracker.py::_finalize_state` records `end_mono`/`end_utc` before acquiring `_run_lock`, so wait time is attributed to `finalization_overhead_seconds`).
  - Replace opaque internal plan/backlog IDs (`fthyv5`, `ckc3vl`, `uatvzh`, `p6pon8`, `26euz0`, `4gpguy`) in user-facing prose with plain descriptions or git commit hashes where helpful.
  - Depends on: none
  - Expected outcome: `docs/performance.md` contains no stale active-bug claim for `uatvzh` and no opaque internal workflow IDs.
  - Execution state: pending

### Task group 2: Consolidate `CHANGELOG.md` `[Unreleased]` and align `CITATION.cff`

- [ ] E-03 Consolidate `## [Unreleased]` in `CHANGELOG.md` without dropping any user-facing change or breaking-change callout (with no em or en dashes in added or edited lines):
  - Merge the duplicated Keep-a-Changelog headings inside `## [Unreleased]` (`### Added` 5x, `### Changed` 4x, `### Fixed` 5x, `### Documentation` 2x, `### Deprecated` 2x) into one single ordered set of headings (`### Added`, `### Changed`, `### Deprecated`, `### Fixed`, `### Documentation`, `### Security` if present).
  - Reconcile superseded intermediate `[Unreleased]` entries against live `main` so no entry contradicts current code: fold old `pubrun bench` flags (`pubrun-benchmarks`, `--no-redact`, `--submit-method`, `--gh-token`, `--print-submission`) into the shipped `fariello/pubrun` / redacted-only / `--unredacted` / `--contribute` / `--prepare-submission` behavior; update `update_commit_file.py` `post-commit` note to the shipped `hatch_build.py` / `_build_meta.json` build-time stamping; fix `imported-transitive` ("one level deep" -> recursive, cycle-safe closure); drop superseded `10.5281/zenodo.PENDING`, `pubrun-benchmark/3`, `pubrun-benchmark/4`, intermediate `[tool.mypy]` ratchet addition, and pending `xfail` manifest-schema note in favor of the shipped net state (`10.5281/zenodo.20801582`, `pubrun-benchmark/5`, full 3-platform mypy without `ignore_errors`, completed schema reconciliation); fix the duplicated copyright name string ("Gabriele Fariello").
  - Optionally add brief historical entries for tagged patch releases `v1.0.1` (`2026-06-20`), `v1.0.2` (`2026-06-20`), and `v1.0.3` (`2026-06-21`) from `git log` so the changelog has no silent version gap between `1.0.0` and `1.1.0`.
  - Depends on: none
  - Expected outcome: `## [Unreleased]` has each Keep-a-Changelog subsection at most once and contains zero claims contradicted by live `main`.
  - Execution state: pending

- [ ] E-04 Align `CITATION.cff` `date-released` for version `1.3.1` with git tag `v1.3.1` and `CHANGELOG.md` (`2026-06-24`, currently `2026-07-05`).
  - Depends on: none
  - Expected outcome: `CITATION.cff` `version` (`1.3.1`) and `date-released` (`2026-06-24`) agree with `git show -s --format=%cs v1.3.1` and `CHANGELOG.md`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`).
- `benchmarks/harness.py` sets `want_unredacted = bool(args.unredacted or args.out)` and writes `pubrun-bench-<hash>-<stamp>.redacted.json` by default.
- `benchmarks/run_bench.sbatch` writes `pubrun-bench-${NODE}-${STAMP}.redacted.json` by default; `submit_bench_{pbs,lsf,sge}.sh` pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`.
- `src/pubrun/tracker.py::_finalize_state` fixes the `workload_seconds` lock-wait bug (`end_mono`/`end_utc` recorded before `_run_lock`).
- `git tag -l v1.0.*` confirms `v1.0.1`, `v1.0.2`, `v1.0.3`, and `v1.3.1` (`2026-06-24`).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| P-01 | High | Low | Benchmark Contributor / Security | `benchmarks/README.md` & `docs/performance.md` vs `benchmarks/harness.py` | Inverts `harness.py`'s redacted-only default output behavior, contradicting the privacy section in the same file. |
| P-02 | Medium | Low | Benchmark Runner / HPC Operator | `benchmarks/README.md` vs `benchmarks/run_bench.sbatch`, `submit_bench_*.sh`, `scenarios.py`, `results/.gitignore` | Stale Slurm filename and pass count, false `patched open()` claim, missing `io_baseline`/`io_sink`, wrong `results/` tracking note, inconsistent relative paths. |
| P-03 | Medium | Low | Performance Reader | `docs/performance.md` vs `src/pubrun/tracker.py::_finalize_state` | Reports already-fixed `uatvzh` timing defect as active and leaks 6 opaque internal plan/backlog IDs. |
| P-04 | Medium | Low | Upgrader / Release Reviewer | `CHANGELOG.md` `## [Unreleased]` & `CITATION.cff` vs `src/pubrun/` and git tags | Duplicated `[Unreleased]` sections, 7 superseded/contradictory claims vs live code, missing `v1.0.1`-`v1.0.3` entries, and `CITATION.cff` `1.3.1` date mismatch (`2026-07-05` vs `2026-06-24`). |

## Proposed changes (ordered, validatable)

1. Fix `benchmarks/README.md` default output, Slurm/scheduler behavior, scenarios, `.gitignore`, and paths (E-01; Remediation Risk: Low).
2. Fix `docs/performance.md` output-file defaults, resolved `uatvzh` bug status, and internal ID leaks (E-02; Remediation Risk: Low).
3. Consolidate `CHANGELOG.md` `## [Unreleased]` subsections and reconcile superseded claims (E-03; Remediation Risk: Low).
4. Align `CITATION.cff` `date-released` with tag `v1.3.1` (E-04; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Updating `benchmarks/submit_bench_{pbs,lsf,sge}.sh` to drop `--out ...json` and use the redacted-only default is deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality for a documentation plan).
  - Carrier-Declined: Runtime HPC script change outside documentation-only scope; recorded in orchestrator `86cd17`.

## Scope check

- Over-scope: none. Only `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff` are modified.
- Under-scope: none.

## Required tests / validation

- Diff inspection of all four files.
- Programmatic check of `CHANGELOG.md` `## [Unreleased]` confirming zero duplicated `###` headings and zero occurrences of retired flags (`--no-redact`, `--submit-method`, `--gh-token`, `--print-submission`, `zenodo.PENDING`).
- Programmatic check of `docs/performance.md` confirming zero occurrences of internal workflow IDs (`fthyv5`, `ckc3vl`, `uatvzh`, `p6pon8`, `26euz0`, `4gpguy`).
- Zero em/en dashes (`\u2013`, `\u2014`) in added lines of `benchmarks/README.md`, `docs/performance.md`, and `CHANGELOG.md`.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- Pure documentation and metadata cleanup; no runtime behavior changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- benchmarks/README.md` confirming redacted-only default output, accurate Slurm/PBS/LSF/SGE notes, `pubrun.open()`/`register_input()`, `io_baseline`/`io_sink`, `results/.gitignore`, and normalized paths; plus pasted zero-dash check on added lines exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/performance.md`, pasted `grep -En "fthyv5|ckc3vl|uatvzh|p6pon8|26euz0|4gpguy" docs/performance.md; echo "exit=$?"` showing `exit=1`, and pasted zero-dash check on added lines exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted Python check on `CHANGELOG.md` `## [Unreleased]` printing the `###` headings (each occurring once) and confirming zero matches for `--no-redact`, `--submit-method`, `--gh-token`, `--print-submission`, `zenodo.PENDING`, and `pubrun-benchmarks`, plus pasted zero-dash check on added lines of `CHANGELOG.md` exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- CITATION.cff` showing `date-released: "2026-06-24"` matching `git show -s --format=%cs v1.3.1`, and pasted output of `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`).
2. Scope declaration: modify only `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff`.
3. Validation honesty: run every required validation command and paste actual output into each `V-*` item.
4. Commit discipline: commit through `aw commit 77pdvl -- benchmarks/README.md docs/performance.md CHANGELOG.md CITATION.cff`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: finalize through `aw ipd finalize 77pdvl` (or the runner) once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
