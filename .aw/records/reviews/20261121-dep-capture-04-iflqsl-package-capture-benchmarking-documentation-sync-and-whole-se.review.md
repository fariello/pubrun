# Review findings: ipd iflqsl

- Subject-Id: iflqsl
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, Mermaid diagrams, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal`, `E-01`..`E-05`, `Proposed changes` | Long run-on sentences, unexpanded acronyms (`OS`, `CPU`, `p95`, `PEP`, `JSON`), and bare artifact IDs (`uil22c`, `fdqkrz`, `ijipnx`, `w4hxkh`) | Split dense sentences, expanded acronyms on first use, and attached descriptive labels to referenced artifact IDs | Technical writing requirements 1, 2, and reference clarity rule |
| `Benchmarking, documentation, and verification workflow` | `flowchart TD` only (missing `top-level-installed` and CI gate); no entity/component diagram across 8 Scope-Paths | Updated `flowchart TD` and added `erDiagram` connecting benchmark, tests, config, and synchronized docs | Technical writing requirements 12(a), 12(d), and 12(e) |
| `Project conventions`, `Deferred`, `OQ-01` | Informal `docs/architecture.md` heading pointer (`Lifecycle / step 1`), missing `- Carrier-Declined:` lines on all three deferred items, and `OQ-01` `- Owner: maintainer (confirmed upon plan approval)` | Standardized `path#Heading` / `path::Symbol` citations, added `- Carrier-Declined:` lines, and updated `OQ-01` owner to `plan author (binding upon plan approval)` | `steps/p-proofread.md` Section 11.1, `check.ipd-uncarried-obligation`, and `steps/s5-questions.md` rule 5 |
| `Validation and cross-check` boilerplate | Two em dashes triggering `IPD-C802` advisories | Replaced both em dashes with parentheses and referenced `U+2014` / `U+2013` code points | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | Prohibited `"if execution seems to need more files, STOP and report"` scope-fence clause and unconditional manual lifecycle move | Replaced with `--scope-reason`/`--scope-ack` scope declaration and conditional runner-lane vs standalone `aw ipd finalize` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, and cross-plan/cross-Set contracts across `benchmarks/package_capture_bench.py`, `benchmarks/scenarios.py`, `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `src/pubrun/resources/default.toml`, `docs/manifest.md`, `docs/configuration.md`, `docs/architecture.md`, `docs/performance.md`, `docs/functional_spec.md`, `.github/workflows/ci.yml`, Set `dep-capture` (`6s7k9e`, `uil22c`, `fdqkrz`, `ijipnx`), and concurrent sibling Sets (`ckc3vl`, `3tvesf`, `4gpguy`, `zp2yyu`).

1. Yes — updates four public reference docs, `default.toml`, and `benchmarks/scenarios.py`, and serves as the whole-Set verification gate for release-blocking Set `dep-capture` (`6s7k9e`).
2. No — local non-publishing benchmark script, benchmark scenario/test, config comments, and docs only (runs `scripts/sanitize_paths.py --check --all` as a read-only hygiene check).
3. No — 5 focused E-items across 3 task groups and 8 Scope-Paths, child 04 of 4 in Set `dep-capture`.
4. Yes — `- Scope-Paths:` explicitly lists all 8 modified/created files.
5. Yes — benchmarking `get_packages(stage="final")` without `include_transitive=False` would misrepresent `ijipnx`'s actual finalization cost, overwriting `docs/performance.md#Representative results` would violate its multi-machine placeholder policy, unredacted paths/hostnames could leak local identity, and uncoordinated edits to shared docs/scenarios could clobber sibling Sets.

AW-TIER: complex

### Step R1

- Checked: Verified every cited file, heading, script, flag, and sibling plan against `benchmarks/scenarios.py`, `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `src/pubrun/resources/default.toml`, `src/pubrun/capture/filesystem.py`, `docs/configuration.md`, `docs/manifest.md`, `docs/architecture.md`, `docs/performance.md`, `docs/functional_spec.md`, `examples/verify_all.py`, `scripts/sanitize_paths.py --help`, `pyproject.toml`, `.github/workflows/ci.yml`, backlog `w4hxkh`, orchestrator `6s7k9e`, reviewed prerequisites `uil22c`, `fdqkrz`, and `ijipnx`, and concurrent Order-04 plans `ckc3vl` and `3tvesf`. Caught `get_packages(stage="final")` double-transitive mismatch with `ijipnx`, missing `get_filesystem({}, ...)` two-arg signature, stale `docs/manifest.md` `version` type (`string` vs `string | null`), inaccurate `docs/architecture.md` heading reference, and `docs/performance.md#Representative results` placeholder rule (PR-001, PR-002).

### Step R2

- Checked: Verified 1:1 `E-*`/`V-*` bijection (`E-01`..`E-05` to `V-01`..`V-05`), 8-file `- Scope-Paths:`, `- Item-Dependencies: executed:ijipnx` matching orchestrator `6s7k9e`, concrete per-item validation evidence, runtime-demonstration reachability (all `V-*` run local commands/tests or inspect diffs, reachable by construction), carrier obligations on deferred items, and `## Approval and execution gate`. Fixed prohibited `"STOP and report"` scope-fence clause and unconditional manual lifecycle move (PR-003), mixed `python`/`python3` commands and missing `git status --short` / Set test-file checks in `V-05` (PR-004), and missing `- Carrier-Declined:` tags (PR-005).

### Step R3

- Checked: Verified strict non-publishing and non-HPC-submission invariants on `benchmarks/package_capture_bench.py`, zero raw hostnames or home/workdir paths in benchmark Markdown/JSON summaries and `docs/performance.md`, temporary workdir cleanup, and `python3 scripts/sanitize_paths.py --check --all` enforcement in `E-05`/`V-05`. Strengthened `E-01`, `E-02`, `E-04`, `V-02`, and `V-05` to verify zero leaked paths/hostnames and zero stray untracked benchmark files (PR-001, PR-002, PR-004).

### Step R4

- Checked: Evaluated engineering rubric sections A (correctness and measurement fidelity: matching `ijipnx`'s `include_transitive=False` finalization call, synthetic fixture design, `top-level-installed` inclusion, and exact schema enums in `docs/manifest.md`), C (architecture and operability: additive cross-Set coexistence on shared docs/scenarios/config), D (anti-regression across full test suite, benchmark tests, examples, and `Representative results` placeholder), E (concrete validation commands including diff-scoped Python em/en-dash checks and `python3` standardization), F (KISS, principles, clear docs), right-sizing (5 bounded E-items across 8 Scope-Paths), and `## Spec / documentation sync` (verified `docs/functional_spec.md:191` needs no edit).

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught `get_packages(stage="final")` double-counting transitive traversal vs `ijipnx`'s `include_transitive=False`, omitted `top-level-installed` mode in the benchmark, and missing `version: string | null` / `mode = "off"` / 6-value `reason` enum in `docs/manifest.md` (PR-001, PR-002).
  2. **Testing and regression expert:** Added diff-scoped Python `U+2014`/`U+2013` checks in `V-03`/`V-04`, `python3` consistency, `git status --short` cleanliness, and explicit Set test-file confirmation in `V-05` (PR-002, PR-004).
  3. **UI / UX expert:** Verified clear documentation of `mode = "off"`, root vs parent-requested extras, and honest single-machine vs multi-machine presentation in `docs/performance.md` (PR-002).
  4. **Systems and software architect:** Added explicit cross-Set additive coexistence guidance across shared docs, `default.toml`, and `benchmarks/scenarios.py` with `ckc3vl`, `3tvesf`, `4gpguy`, and `zp2yyu` (PR-002).
  5. **Software engineer:** Fixed prohibited `"STOP and report"` scope-fence clause and unconditional manual lifecycle move in `## Approval and execution gate` (PR-003).
  6. **Sophisticated power user:** Confirmed reproducible local `--workdir` shared-storage benchmarking, cold vs warm cache separation, and all five modes (`off`, `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment`) measured separately at startup and finalization (PR-001).
  7. **Complete novice:** Expanded acronyms (`OS`, `CPU`, `p95`, `PEP`, `JSON`, `NFS`, `IQR`, `HPC`, `CI`), split dense sentences, and added an `erDiagram` alongside the workflow flowchart (PR-005).
  8. **Stakeholder:** Confirmed every benchmarking, documentation, hygiene, and CI-matrix disclosure requirement in backlog `w4hxkh` and orchestrator `6s7k9e` is satisfied honestly.

### Step R6

- Checked: Evaluated decomposition and conceptual density across `E-01`..`E-05` and 8 Scope-Paths. `iflqsl` is child 04 of 4 in Set `dep-capture` with 5 cohesive E-items partitioned cleanly into benchmark creation (`E-01`), benchmark test + measurement run (`E-02`), config/doc sync (`E-03`), performance doc update (`E-04`), and whole-Set verification (`E-05`). No split recommended.

### Step R7

- Checked: Cross-plan consistency across Set `dep-capture` (`6s7k9e`, `uil22c`, `fdqkrz`, `ijipnx`, `iflqsl`) and concurrent sibling Sets (`ckc3vl`, `3tvesf`, `4gpguy`, `zp2yyu`). Confirmed `- Item-Dependencies: executed:ijipnx` matches `6s7k9e`; aligned finalization benchmark path with `ijipnx`'s `include_transitive=False` + `merge_package_snapshots()` contract; synced all additive schema fields, enums, and `fdqkrz` extra semantics into `docs/manifest.md` and `docs/configuration.md`; and ensured additive coexistence with concurrent Sets on shared files.

### Step S5

- Checked: Audited `OQ-01`, all three deferred items, and all 5 review findings. Changed `OQ-01` `- Owner:` from `maintainer (confirmed upon plan approval)` to `plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5, added `- Carrier-Declined:` to all three deferred items (`check.ipd-uncarried-obligation`), and recorded reversible decisions `D-1`..`D-4` below. All 5 review findings had Low remediation risk and were fixed in place. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R4.A/R7 | `.aw/records/plans/pending/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md:55,101-104`, `.aw/records/plans/pending/20261121-dep-capture-03-ijipnx-startup-to-finalization-package-merge-manifest-schema-and-re.ipd.md:177,202`, `src/pubrun/capture/filesystem.py:207` | Benchmark plan called `get_packages(cfg, stage="final")` with default `include_transitive=True` before `merge_package_snapshots(...)`, double-counting transitive traversal relative to `ijipnx`'s `Run._finalize_state()` (`include_transitive=False` in `imported-transitive` mode); omitted `top-level-installed` from the mode sweep; under-specified synthetic fixture isolation (`PYTHONPATH`, `.dist-info`, `invalidate_package_cache()`) and `get_filesystem({}, {"workdir": ...})` two-arg signature; and did not prohibit raw hostnames alongside home paths in Markdown/JSON summaries. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Aligned finalization measurement with `ijipnx`'s `include_transitive=(mode != "imported-transitive")` call, added `top-level-installed` to the benchmark and tests, specified synthetic fixture isolation, `get_filesystem({}, {"workdir": ...})`, workdir cleanup, and zero-hostname/zero-home-path sanitization (`D-1`, recommendation strength: very strong). |
| PR-002 | HIGH | UNDER-SCOPE | R1/R4.A/R7 | `.aw/records/plans/pending/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md:65-72,85-87,113-122`, `docs/manifest.md:155-175`, `docs/configuration.md:130-136`, `docs/architecture.md:29-42`, `docs/performance.md:50-73` | Doc sync missed `docs/manifest.md` `version: string` (now `string` or `null`), `mode = "off"` (`suppressed` with `"mode"` omitted), the `$defs.unresolved_package_record` table and 6-value `reason` enum, and `observed_at`/`snapshot_stage` enums from `ijipnx`; cited a non-existent `docs/architecture.md` heading (`Lifecycle / step 1`); did not guard `docs/performance.md#Representative results` placeholder policy or cross-Set additive coexistence with `ckc3vl`/`3tvesf`/`4gpguy`/`zp2yyu`; and lacked diff-scoped Python em/en-dash checks over added (`+`) lines. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified every `ijipnx`/`fdqkrz` field and enum for `docs/manifest.md`, `docs/configuration.md`, and `default.toml`, corrected `docs/architecture.md## 3. Run Lifecycle` headings, guarded `docs/performance.md## Representative results` as untouched placeholder, added cross-Set additive coexistence rules, and required diff-scoped Python `U+2014`/`U+2013` checks in `V-03` and `V-04` (`D-2`, `D-3`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md:196,199`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60` | Gate item 2 carried the prohibited `"if execution seems to need more files, STOP and report"` clause for out-of-scope edits, and gate item 5 gave an unconditional manual lifecycle-transition instruction instead of conditional runner-lane vs standalone `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract using `--scope-reason`/`--scope-ack`, HARD MUST honesty wording, and conditional runner/standalone `aw ipd finalize` ownership (forbidding raw `git mv`) (recommendation strength: very strong). |
| PR-004 | MEDIUM | IN-SCOPE | R1/R2/R4.E | `.aw/records/plans/pending/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md:79,141,144,165,170,185` | Commands mixed `python` and `python3`; `V-05` did not confirm `git status --short` cleanliness (guarding against stray benchmark JSONs) or explicitly verify the Set's new test files (`test_package_resolution.py`, `test_package_transitive.py`, `test_package_lifecycle.py`, `test_package_benchmark.py`, `test_manifest_schema.py`) passed inside `pytest tests/ -v`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Standardized all Python CLI commands on `python3`, added `git status --short` cleanliness check and explicit Set test-file confirmation in `E-05`/`V-05`, and strengthened `V-02` to verify sanitized benchmark output (recommendation strength: strong). |
| PR-005 | MEDIUM | IN-SCOPE | Check P/S5/R2 | `.aw/records/plans/pending/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md:23-26,30,36-45,128-132,153-158,162` | `Workflow history` was oldest-first; `OQ-01` carried `- Owner: maintainer (confirmed upon plan approval)` for an author-resolved default; all three deferred items lacked `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`); line 162 had two em dashes (`IPD-C802`); an `erDiagram` was missing; and prose contained long sentences, unexpanded acronyms, and bare IDs. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reordered `Workflow history` newest-first, updated `OQ-01` owner to `plan author (binding upon plan approval)` (`D-4`), added `- Carrier-Declined:` lines to all three deferred items, replaced line 162 em dashes with parentheses, added an `erDiagram`, expanded acronyms, split dense sentences, and labeled artifact IDs (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How `benchmarks/package_capture_bench.py` should measure `imported-transitive` finalization and whether to include `top-level-installed` | Call `get_packages(cfg, stage="final", include_transitive=(mode != "imported-transitive"))` followed by `merge_package_snapshots(...)` to match `Run._finalize_state()` exactly, and include `top-level-installed` alongside `off`, `imported-only`, `imported-transitive`, and `full-environment` | Call `get_packages(cfg, stage="final")` with default `include_transitive=True` (double-counts transitive traversal) or omit `top-level-installed` (leaves one of the four modes unmeasured) | `.aw/records/plans/pending/20261121-dep-capture-03-ijipnx-startup-to-finalization-package-merge-manifest-schema-and-re.ipd.md:177,202`, `src/pubrun/resources/default.toml:180-183` | yes |
| D-2 | Where to record single-machine package-capture benchmark numbers in `docs/performance.md` | Keep `## Representative results` untouched as a multi-machine placeholder and add a clearly labeled single-machine subsection (additive alongside sibling Sets `ckc3vl`, `3tvesf`, `4gpguy`) | Overwrite `_TBD_` rows in `## Representative results` with single-machine numbers (violates placeholder policy at `docs/performance.md:50-58`) | `docs/performance.md:50-58`, reviewed sibling plans `ckc3vl` and `3tvesf` | yes |
| D-3 | How to enforce the zero-em/en-dash rule on edited `docs/*.md` files that already contain pre-existing em dashes | Require a concrete Python check over added (`+`) lines of `git diff -U0 -- <docs>` in `V-03` and `V-04` | Scan whole files (false-fails on untouched pre-existing lines) or rely on manual visual inspection | `docs/configuration.md:134`, `docs/performance.md:19,42`, reviewed sibling plans `ckc3vl` and `3tvesf` | yes |
| D-4 | Ownership label for `OQ-01` (synthetic distribution counts `10` / `300`) and carrier disposition for the three deferred items | Set `OQ-01` `- Owner: plan author (binding upon plan approval)` per `steps/s5-questions.md` rule 5 and add `- Carrier-Declined:` to all three policy/already-accurate deferred items | Retain `- Owner: maintainer` (violates `s5-questions.md` rule 5) or leave deferred items uncarried (triggers `check.ipd-uncarried-obligation`) | `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91`, `docs/functional_spec.md:191`, `.aw/records/plans/pending/20261121-dep-capture-00-6s7k9e-dependency-capture-accuracy-late-import-refresh-and-transiti.ipd.md:110` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Workflow history`, `Goal`, diagrams, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
