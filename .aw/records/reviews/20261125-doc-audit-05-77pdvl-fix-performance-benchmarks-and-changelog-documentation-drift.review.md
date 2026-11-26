# Review findings: ipd 77pdvl

- Subject-Id: 77pdvl
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Gemini 4 Neon (Antigravity)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete plan text against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 through 12 and spec Section 11.1 citation forms. No pre-review snapshot was needed: the lane working tree was clean and the plan was already committed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) before any edit. Requirement 12: no diagram is needed because the plan edits four existing documentation and metadata files with no new multi-entity data model, branch, loop, or status lifecycle; this rationale is now stated in `## Scope check`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| E-01, Project conventions, V-01 | Did not distinguish local gitignored `benchmarks/results/summary.{csv,md}` from committed `benchmarks/data/summary.{csv,md}`; omitted that PBS/LSF/SGE `--out` implies `--unredacted` (writing an unredacted bare `.json` alongside `.redacted.json`), Slurm `PUBRUN_UNREDACTED`/`PUBRUN_REDACTED_OUT`, and `--redacted-out` path override in line 278 | States all four explicitly and matches `benchmarks/harness.py::main`, `benchmarks/run_bench.sbatch`, `benchmarks/submit_bench_{pbs,lsf,sge}.sh`, `benchmarks/aggregate.py::main`, `benchmarks/results/.gitignore`, and `benchmarks/data/README.md` | Accurate privacy and path guidance (PR-001). |
| E-02, V-02 | Did not scope "Neither is ever a bare `*.json`" to match `benchmarks/README.md`, omitted fix commit `cb1b6d1`, and did not guard the inbound anchor heading | Scopes bare-`.json` wording consistently, cites `src/pubrun/tracker.py::Run._finalize_state` and commit `cb1b6d1`, and preserves `## Package capture startup and finalization overhead (single-machine local measurements)` | Cross-file accuracy and inbound-anchor safety (PR-002). |
| Concern, E-03, P-04, V-03 | Missed `patched open()` (L618), `file_io` hash "at close" (L551), attach-only `--submit-file` "no longer transmits" (L59), overstated "never a bare `*.json`" (L303), superseded `core.profile` "separate design decision" (L391-392), and internal IPD mentions (L355, L377); wrote "Optionally add" for `v1.0.1`-`v1.0.3` | Reconciles all missed `CHANGELOG.md` contradictions against live `main` and replaces ambiguous "Optionally" with a dedicated, deterministic execution item | Eliminates remaining contradictions and ambiguity (PR-003). |
| E-03 -> E-03, E-05; E-04 | Bundled 675-line `[Unreleased]` consolidation and historical `v1.0.1`-`v1.0.3` insertion into one E-item; left dangling `(see the same IPD, Open Questions #1/#4)` comment in `CITATION.cff` | Split into E-03 (`## [Unreleased]` consolidation/reconciliation) and E-05 (`v1.0.1`-`v1.0.3` historical entries, `Depends on: E-03`) via `aw ipd sync --apply`; added `CITATION.cff` comment cleanup to E-04 | Right-sizing for modest executors and clean user-facing metadata (PR-004). |
| Required tests, V-01..V-05 | Unnamed zero-dash and Python `CHANGELOG` checks, missing link/anchor check required by orchestrator `86cd17`, missing `TestCitationConsistency` in V-04, and missing negative `grep` baselines | Embedded runnable Python dash, link/anchor, and `CHANGELOG.md` scripts; added `TestCitationConsistency` to V-04; added falsifiable `grep` checks with verified pre-execution baselines across V-01, V-02, and V-05 | Makes every V-item directly runnable and falsifiable (PR-005). |
| Approval gate items 1-5 | Stop-style "modify only" fence; omitted no-blocking-questions note and never-claim-without-output clause; unclear conditional runner/executor finalize ownership and no ban on hand-run `git mv` | Rewrote items 1 to 5 to match the repository execution contract and sibling plans in Set `doc-audit` | Conformance with execution contract and maintainer scope-fence ruling (PR-006). |
| Scope check, Spec / documentation sync, Deferred, citations | Omitted sibling Set owners, disjointness confirmation, deferred repo-wide dash sweep, Requirement 12 rationale, and symbol-anchored citations | Added full sibling ownership, disjointness, deferred dash sweep, Requirement 12 exemption, and Section 11.1 symbol/heading citations | Cross-plan traceability and technical writing compliance (PR-007). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (four documentation/metadata paths), 4 E-items in 2 task groups at review start (5 E-items after splitting `CHANGELOG.md` historical entries), `- Kind: child`, and Set `doc-audit` sibling Scope-Paths.

1. No: pure documentation and citation metadata cleanup (`benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, `CITATION.cff`). No runtime code, CLI option, JSON schema, or public contract is modified; `CITATION.cff` `date-released` is aligned to existing tag `v1.3.1`.
2. No: modifies no code guarding private data, commits, worktree isolation, merges to main, or the sandbox. E-01, E-02, and E-03 document redacted-only default output and share-safety behavior, so accuracy was verified against `benchmarks/harness.py`, `benchmarks/run_bench.sbatch`, and `benchmarks/submit_bench_{pbs,lsf,sge}.sh`.
3. Somewhat: four files across two task groups, including reconciling ~675 lines of duplicated `CHANGELOG.md` `## [Unreleased]` entries against live `main`.
4. Yes: all four paths are declared in `- Scope-Paths:`.
5. No: documentation edits are reversible via `git revert`, though inaccurate redaction/privacy docs could mislead users into sharing unredacted files and a malformed `CITATION.cff` edit could fail `tests/test_cli.py::TestCitationConsistency`.

AW-TIER: standard

### Step R1

- Checked every material citation against live repository code, scripts, git history, and tests:
  - `benchmarks/harness.py::main` (lines 687-750), `_TIERS` (lines 55-59: `quick=(15, 2)`, `default=(30, 3)`, `rigorous=(50, 5)`), `_default_out`, `_default_redacted_out`: `want_unredacted = bool(args.unredacted or args.out)`; always writes compact `pubrun-bench-<hash>-<UTC-timestamp>.redacted.json` (overridable via `--redacted-out`) and writes `<hostname>-<UTC-timestamp>.unredacted.json` only when `--unredacted` or `--out` is passed.
  - `benchmarks/run_bench.sbatch` (lines 37-72) and `benchmarks/submit_bench.sh` (lines 52-80): default `REDACTED_OUT="${PUBRUN_REDACTED_OUT:-$RESULTS_DIR/pubrun-bench-${NODE}-${STAMP}.redacted.json}"`, opt-in `PUBRUN_UNREDACTED` writes `${NODE}-${STAMP}.unredacted.json`.
  - `benchmarks/submit_bench_pbs.sh:43,51`, `benchmarks/submit_bench_lsf.sh:41,49`, `benchmarks/submit_bench_sge.sh:48,56`: each passes `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, which implies `--unredacted` and writes both an unredacted bare `.json` (gitignored) and the default `.redacted.json`.
  - `benchmarks/scenarios.py::all_scenarios` (lines 77-144) and `benchmarks/workloads/`: 4 groups (`startup`, `feature`, `hotpath`, `io_baseline`) and 5 workloads (`noop.py`, `cpu_burn.py`, `file_read.py`, `print_loop.py`, `io_sink.py`). `hotpath` benchmarks `pubrun.open()` and `pubrun.register_input()` vs `builtins.open()`, never patched `open()`.
  - `benchmarks/results/.gitignore` (`*`, `!.gitignore`, `!*.redacted.json`), `benchmarks/aggregate.py::main:235-236` (defaults `--csv`/`--md` to local gitignored `benchmarks/results/summary.{csv,md}`), and `benchmarks/data/README.md` (committed summaries in `benchmarks/data/summary.{csv,md}`).
  - `src/pubrun/tracker.py::Run._finalize_state` (lines 1100-1115) and commit `cb1b6d1`: reads `end_mono = time.perf_counter()` and `end_utc = time.time()` before acquiring `_run_lock`, resolving the `af36c852` lock-wait exception (closed backlog `uatvzh` / executed plan `3aalwv`).
  - `docs/performance.md`: scanned for internal IDs; confirmed exact 6 (`fthyv5`, `ckc3vl`, `uatvzh`, `p6pon8`, `26euz0`, `4gpguy`) at lines 96, 199, 213, 215, 218, 220, and 338. Verified inbound anchor from `benchmarks/README.md:186` to `docs/performance.md#package-capture-startup-and-finalization-overhead-single-machine-local-measurements` (line 256).
  - `CHANGELOG.md` `## [Unreleased]` (lines 9-687): 18 `###` headings across 5 unique names (`### Added` 5x, `### Changed` 4x, `### Fixed` 5x, `### Documentation` 2x, `### Deprecated` 2x), plus `#### Other fixes` (L665) and `#### Edge-case / failure-mode hardening` (L674). Verified live code against every claim: `src/pubrun/__main__.py:2902-2937` (`pubrun bench` flags; absent in `v1.3.1`), `hatch_build.py::CustomBuildHook` + `src/pubrun/__init__.py::_read_packaged_commit` + no-op `scripts/update_commit_file.py`, `src/pubrun/capture/packages.py::_resolve_transitive_closure` (recursive closure), `src/pubrun/capture/file_io.py::ProvenanceFileProxy` (streamed hashing with fallback at close), `pyproject.toml` `[tool.mypy]` (no `ignore_errors`), `tests/test_manifest_schema.py` (no `xfail`).
  - `git tag` and `git log`: `v1.0.1` (`2026-06-20`, `88fe38b`), `v1.0.2` (`2026-06-20`, `a015c14`), `v1.0.3` (`2026-06-21`, `98058ec`), and `v1.3.1` (`2026-06-24`, `881ae65`). `CITATION.cff:17` currently has `date-released: "2026-07-05"` and line 26 has `(see the same IPD, Open Questions #1/#4)`.
  - `tests/test_cli.py::TestCitationConsistency` passed 4/4 in 0.82s; `python3 scripts/sanitize_paths.py --check --all` exited 0; Markdown link/anchor check baseline `broken=0`.
- Drift found: PR-001, PR-002, PR-003, PR-004, PR-005.

### Step R2

- Checked: E/V bijection (5 E-items and 5 V-items after `aw ipd sync --apply` allocated E-05/V-05 and advanced `Highest E allocated: 05`); `- Scope-Paths:` strictly disjoint from all five Set `doc-audit` siblings (`0cjiv5`, `pqcx6o`, `dd7noz`, `wjsccu`, `2uwuiu`) and orchestrator `86cd17`; `- Item-Dependencies: none`; linear intra-plan dependency `E-03 -> E-05` on `CHANGELOG.md`; concrete, runnable, falsifiable commands with verified pre-execution baselines in every V-item; no hardcoded counts of mutable record trees; no V-item demands an unreachable runtime observation (all V-items inspect diffs, negative greps, runnable Python scripts, `sanitize_paths.py`, and `TestCitationConsistency`).

### Step R3

- Checked: the plan modifies no security, auth, or sandbox code. E-01, E-02, and E-03 document privacy-critical benchmark redaction behavior. Verified against `benchmarks/harness.py::main`, `benchmarks/run_bench.sbatch`, and `benchmarks/submit_bench_{pbs,lsf,sge}.sh` that E-01 explicitly warns users that PBS/LSF/SGE scripts currently write an unredacted bare `.json` file (which must not be shared) alongside the default `.redacted.json` file, and that `harness.py` / `pubrun bench` / Slurm default to redacted-only output. `python3 scripts/sanitize_paths.py --check --all` exits `0`.

### Step R4

- Checked: rubric A through F, right-sizing, and spec/documentation sync.
- Right-sizing: split `CHANGELOG.md` work into E-03 (`## [Unreleased]` consolidation and contradiction reconciliation) and E-05 (historical `v1.0.1`-`v1.0.3` entries, `Depends on: E-03`) via `aw ipd sync --apply`, keeping the plan at 5 focused E-items across 4 Scope-Paths (within `IPD-Z603` guidance).
- Test coverage: added `tests/test_cli.py::TestCitationConsistency` to V-04 and the orchestrator-required link/anchor check to Required tests and V-03.
- Spec and documentation sync names all five sibling owners in Set `doc-audit` and cross-file alignment across the four edited files.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | correctness | `benchmarks/README.md:32-33,198,249,278`; `benchmarks/harness.py::main:709-724`; `benchmarks/run_bench.sbatch:42-43`; `benchmarks/submit_bench_{pbs,lsf,sge}.sh`; `benchmarks/aggregate.py::main:235-236` | E-01 did not distinguish `aggregate.py`'s local gitignored `benchmarks/results/summary.{csv,md}` from committed `benchmarks/data/summary.{csv,md}`, did not note that PBS/LSF/SGE `--out ...json` implies `--unredacted` (writing a non-shareable unredacted bare `.json` alongside `.redacted.json`), omitted Slurm `PUBRUN_UNREDACTED`/`PUBRUN_REDACTED_OUT`, and omitted fixing line 278 (`--redacted-out results/shareable.redacted.json`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Expanded E-01, Project conventions, and V-01 with all four verified details so `benchmarks/README.md` gives accurate path and privacy guidance. |
| PR-002 | MEDIUM | IN-SCOPE | consistency | `docs/performance.md:37-40,199,256`; `benchmarks/README.md:186`; `src/pubrun/tracker.py::Run._finalize_state:1100-1115` (commit `cb1b6d1`) | E-02 did not scope "Neither is ever a bare `*.json`" to match `benchmarks/README.md`, omitted fix commit `cb1b6d1`, and did not explicitly guard the heading linked by `benchmarks/README.md:186`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated E-02 and V-02 to align the bare-`.json` qualification with `benchmarks/README.md`, cite `src/pubrun/tracker.py::Run._finalize_state` and commit `cb1b6d1`, and preserve the linked heading verbatim. |
| PR-003 | HIGH | UNDER-SCOPE | completeness | `CHANGELOG.md:51-65,303,355,377,391-392,551-552,618`; `src/pubrun/__main__.py:2929-2931`; `src/pubrun/capture/file_io.py::ProvenanceFileProxy` | E-03 missed six contradictions/leaks in `CHANGELOG.md` `## [Unreleased]` (`patched open()` at L618, `file_io` hash "at close" at L551 vs streamed hashing at L656, attach-only `--submit-file` "no longer transmits" at L59 vs L31, overstated "never a bare `*.json`" at L303, superseded `core.profile` "separate design decision" at L391-392, and internal IPD mentions at L355 and L377) and used ambiguous "Optionally add" wording for `v1.0.1`-`v1.0.3` despite listing them in P-04. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added all six missed reconciliations to E-03 and V-03 and turned `v1.0.1`-`v1.0.3` into a definite commit-backed item (E-05/V-05). |
| PR-004 | MEDIUM | IN-SCOPE | right-sizing | Pre-review E-03 (`CHANGELOG.md` lines 9-687 plus lines 762-763) and E-04 (`CITATION.cff:26`) | Bundling the ~675-line `[Unreleased]` consolidation/reconciliation with separate historical `v1.0.1`-`v1.0.3` insertion overloaded one E-item, and E-04 left a dangling internal `(see the same IPD, Open Questions #1/#4)` comment in `CITATION.cff`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split `v1.0.1`-`v1.0.3` into E-05 (`Depends on: E-03`) with matching V-05 via `aw ipd sync --apply` (5 E-items total), and added `CITATION.cff` trailing-comment cleanup to E-04/V-04. |
| PR-005 | MEDIUM | IN-SCOPE | evidence | Pre-review Required tests and V-01..V-04; orchestrator `86cd17` `## Cross-IPD validation`; `tests/test_cli.py::TestCitationConsistency` | Validation lacked runnable Python scripts for dash and `CHANGELOG.md` checks, omitted the orchestrator-mandated relative/anchor link check, omitted `tests/test_cli.py::TestCitationConsistency` in V-04, and lacked negative `grep` checks with pre-execution baselines. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added runnable Python dash, link/anchor, and `CHANGELOG.md` scripts in `## Required tests / validation`, added `TestCitationConsistency` to V-04, and added falsifiable `grep` checks with verified pre-execution baselines in V-01, V-02, and V-05. |
| PR-006 | MEDIUM | IN-SCOPE | execution contract | Pre-review `## Approval and execution gate` items 1, 2, 3, and 5 | Item 1 omitted confirming no blocking open questions; item 2 used stop-style "modify only" wording instead of scope-declaration wording (`--scope-reason`/`--scope-ack`); item 3 omitted the never-claim-without-output clause; item 5 did not distinguish runner vs executor finalize ownership or forbid hand-run `git mv`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote items 1 to 5 to match the repository execution contract and sibling plans in Set `doc-audit`. |
| PR-007 | LOW | IN-SCOPE | coordination | Pre-review `## Scope check`, `## Spec / documentation sync`, `## Deferred / out of scope` | Omitted sibling Set owners, disjointness confirmation, deferred repo-wide dash sweep, Requirement 12 diagram assessment, and Section 11.1 symbol citations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `## Scope check`, `## Spec / documentation sync`, `## Deferred / out of scope`, and code/doc citations across the plan. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` (rejected: privacy-sensitive benchmark redaction docs plus ~675-line changelog reconciliation against live code); `complex` (rejected: no runtime code, schema, or contract changes) | Step T answers | yes |
| D-2 | Should `v1.0.1`-`v1.0.3` historical changelog entries remain "Optional" inside E-03 or become a definite split item? | Make them a definite commit-backed item E-05 (`Depends on: E-03`) with V-05 | Leave "Optional" inside E-03 (rejected: contradicts P-04 finding, leaves execution non-deterministic, and bundles two disjoint regions of `CHANGELOG.md`); drop them (rejected: leaves silent tag gap between `1.0.0` and `1.1.0`) | `git log v1.0.0..v1.0.3`, `IPD-Z603` right-sizing, Technical Writing Standard Req 7 | yes |
| D-3 | Should `CHANGELOG.md` `## [Unreleased]` validation ban `pubrun-benchmark/4` as a raw substring? | Do not ban raw `pubrun-benchmark/4`; check the 12 unambiguous retired/contradictory strings instead | Ban `pubrun-benchmark/4` (rejected: `aggregate.py` legitimately reads `/4` and `/5` files, so a blind substring check would cause false failures) | `benchmarks/aggregate.py::_scenarios_view` and `CHANGELOG.md:299` | yes |

### Step S5

- Checked: `## Open questions` is `None.` Repository evidence settled every finding and decision (D-1 through D-3). Every finding (PR-001 through PR-007) is `FIXED`, so no finding requires escalation and no open question is added. Every decision is reversible (`Reversible: yes`). The lane outcome JSON carries `questions: []`.

### Step S6

- Checked: Round 1 added E-05 and V-05 via `aw ipd sync --apply`, so Rule 1 required a second verification pass. Re-read the entire revised plan and verified:
  - Proposed changes 1 to 5 map 1:1 to E-01, E-02, E-03, E-05, and E-04.
  - Intra-plan dependency on `CHANGELOG.md` is linear (`E-03 -> E-05`); E-01, E-02, and E-04 are independent (`Depends on: none`); no `E-NEW` or `TODO` placeholder remains.
  - Every superseded claim and optional phrasing was swept consistently across Concern, Goal, E-items, Project conventions, Findings, Proposed changes, Scope check, Spec / documentation sync, Required tests, and V-items.
  - Every embedded validation command (zero-dash check, link/anchor check, `CHANGELOG.md` check, negative greps, `TestCitationConsistency`, `sanitize_paths.py`) was verified for syntax and pre-execution baseline on the current tree.
  - `aw ipd lint --phase review-finalize --agent` exits `0` (`outcome: clean`).

AW-REVIEW: DONE
