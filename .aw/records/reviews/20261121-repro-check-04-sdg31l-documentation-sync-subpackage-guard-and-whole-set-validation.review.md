# Review findings: ipd sdg31l

- Subject-Id: sdg31l
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, Mermaid diagram, `E-01`..`E-04`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-04`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-repro-check-04-sdg31l-documentation-sync-subpackage-guard-and-whole-set-validation.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Goal`, `E-01`..`E-04` | Long multi-clause sentences, equivocal `E-02` helper wording (`if surfaced`), and no Mermaid diagram across 6 related files/components | Split into concise sentences, made helper documentation definitive (`assess_run`, `should_fail_strict`, `hydrate_manifest_with_report`), labeled prerequisite IDs, and added an `erDiagram` | Technical writing requirements 2, 5, 6, and 12(a) |
| `Project conventions`, `Proposed changes`, `Deferred`, `OQ-01` | Informal doc references, missing `- Carrier-Declined:` lines on both deferred items, and `OQ-01` `- Owner: none` | Standardized `path#Heading` / `path::Symbol` citations, added `- Carrier-Declined:` lines to both deferred items, and set `OQ-01` `- Owner: plan author (confirmed by evidence 2026-11-21)` | `steps/p-proofread.md` Section 11.1, `check.ipd-uncarried-obligation`, and `steps/s5-questions.md` rule 5 |
| `Validation and cross-check` boilerplate and `V-01`/`V-02` | Literal em/en dashes (`IPD-C802`) | Replaced line 130 em dashes with parentheses and referenced `U+2014` / `U+2013` code points in `V-01`/`V-02` | Zero `IPD-C802` advisories while preserving exact meaning |
| `Approval and execution gate` | One-line paragraph missing `--scope-reason`/`--scope-ack` fence, `never git add -A/-a`/`never push`, and giving an unconditional lifecycle-transition instruction | Replaced with complete 5-item Execution contract with compliant scope declaration, HARD MUST honesty rule, path-scoped commit/never-push, and conditional runner/standalone `aw ipd finalize` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-04`, and cross-plan/cross-Set contracts across `docs/cli.md`, `docs/hpc.md`, `docs/manifest.md`, `docs/api.md`, `tests/test_report_subpackage_integrity.py`, `tests/test_reproducibility_e2e.py`, Set `repro-check` (`osjxbz`, `0b8i7x`, `tusvtd`, `3lqtlt`), and concurrent sibling Sets (`hm32d9`, `4gpguy`, `iflqsl`, `3tvesf`, `ckc3vl`, `zp2yyu`).

1. Yes — updates four public reference docs (`docs/cli.md`, `docs/hpc.md`, `docs/manifest.md`, `docs/api.md`), extends the subpackage import-integrity guard, adds all eight `q3bll1` end-to-end acceptance scenarios, and serves as the whole-Set verification gate for Set `repro-check` (`osjxbz`).
2. No — documentation and tests only (no production code guarding private data, commits, worktree isolation, or sandbox).
3. No — 4 focused E-items across 3 task groups and 6 Scope-Paths, child 04 of 4 in Set `repro-check`.
4. Yes — `- Scope-Paths:` explicitly lists all 6 modified/created files.
5. Yes — inaccurate CLI exit-code/JSON documentation (`pubrun rerun` exit code `2` and `--fail-on` strict activation) misleads pipeline callers, missing six-mode import-isolation checks leave `osjxbz`'s cross-IPD contract unverified, and uncoordinated edits could clobber sibling-Set docs.

AW-TIER: complex

### Step R1

- Checked: Verified every cited file, heading, symbol, and sibling plan against `docs/cli.md`, `docs/hpc.md`, `docs/manifest.md`, `docs/api.md`, `tests/test_report_subpackage_integrity.py`, `.github/workflows/ci.yml`, backlog `q3bll1`, orchestrator `osjxbz`, and reviewed prerequisites `0b8i7x`, `tusvtd`, and `3lqtlt`. Caught post-review `3lqtlt` CLI/TUI doc omissions (`rerun` exit code `2`, lock-file fallback, `inspect` 10-key JSON schema, `--fail-on` implicit strict activation, `docs/cli.md### ui`, and `docs/api.md` equivocal helper wording) plus `osjxbz` line 94's six-mode import-isolation requirement (PR-001, PR-002).

### Step R2

- Checked: Verified 1:1 `E-*`/`V-*` bijection (`E-01`..`E-04` to `V-01`..`V-04`), 6-file `- Scope-Paths:`, `- Item-Dependencies: executed:3lqtlt` matching orchestrator `osjxbz`, concrete per-item validation evidence, runtime-demonstration reachability (all `V-*` demand `git diff`, Python checks, `pytest`, or `sanitize_paths.py` output, reachable by construction), carrier obligations on deferred items, and `## Approval and execution gate`. Fixed incomplete gate with unconditional finalize instruction (PR-003), missing six-mode isolation check, isolated `git init` config, and `sanitize_paths.py` / `python3` consistency (PR-002), and missing `- Carrier-Declined:` tags (PR-004).

### Step R3

- Checked: Verified offline/read-only/no-replay CLI side-effect test in `tests/test_reproducibility_e2e.py` (confirming a recorded sentinel script is never executed and `tmp_path` is never modified), added `python3 scripts/sanitize_paths.py --check --all` in `E-04`/`V-04`, and verified six-mode host-path import isolation (`pubrun.report.checks` and `pubrun.report.reproducibility` never loaded by `import pubrun.<mode>`) (PR-002).

### Step R4

- Checked: Evaluated engineering rubric sections A (documentation accuracy vs reviewed `0b8i7x`, `tusvtd`, `3lqtlt` contracts), C (cross-Set additive coexistence on shared docs), D (anti-regression across all six import modes, callable `pubrun.report()`, `schemas/manifest.schema.json`, and full test suite), E (concrete behavioral tests for all eight `q3bll1` scenarios, isolated `git init` user config, offline/no-replay guard, diff-scoped `U+2014`/`U+2013` checks), F (KISS, clear user docs), right-sizing (4 focused E-items across 6 Scope-Paths), and `## Spec / documentation sync` (this plan IS the documentation sync plan for Set `repro-check`).

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught `3lqtlt` post-review CLI details missing from `docs/cli.md` (exit code `2`, lock-file fallback, 10-key JSON schema, `--fail-on` strict activation, `ui` tab updates) and missing six-mode import-isolation assertion required by `osjxbz` (PR-001, PR-002).
  2. **Testing and regression expert:** Caught missing `git -c user.name=... -c user.email=...` isolation for CI `git init` tests, missing offline/no-replay sentinel test specification in `tests/test_reproducibility_e2e.py`, missing `test_report_call_and_submodule_coexist_same_process` check for `reproducibility`, and missing `sanitize_paths.py` in `E-04`/`V-04` (PR-002).
  3. **UI / UX expert:** Verified `docs/cli.md` documents `pubrun show` and `pubrun ui` reproducibility views and redacted-command advisories clearly without em/en dashes (PR-001).
  4. **Systems and software architect:** Added explicit cross-Set additive coexistence rules on shared docs (`docs/cli.md`, `docs/manifest.md`, `docs/api.md`) and definitive `docs/api.md` helper contracts (`assess_run`, `should_fail_strict`, `hydrate_manifest_with_report`) (PR-001).
  5. **Software engineer:** Fixed incomplete gate and unconditional finalize wording (PR-003).
  6. **Sophisticated power user:** Confirmed `pubrun rerun | bash` safety, `rerun --preflight --strict` / `--fail-on` exit codes, and HPC cluster `meta_ref` diagnostics are accurately documented (PR-001).
  7. **Complete novice:** Added `erDiagram`, split dense sentences, and clarified `docs/hpc.md` and `docs/manifest.md` parent-snapshot inheritance limits (PR-004).
  8. **Stakeholder:** Confirmed all eight `q3bll1` acceptance scenarios, `osjxbz` cross-IPD contracts, and the `.github/workflows/ci.yml` CI matrix gate are covered end-to-end.

### Step R6

- Checked: Evaluated decomposition and conceptual density across `E-01`..`E-04` and 6 Scope-Paths. `sdg31l` is child 04 of 4 in Set `repro-check` with 4 cohesive E-items (`docs/cli.md`+`docs/hpc.md`, `docs/manifest.md`+`docs/api.md`, subpackage guard + E2E suite, whole-Set validation). No split recommended.

### Step R7

- Checked: Cross-plan consistency across Set `repro-check` (`osjxbz`, `0b8i7x`, `tusvtd`, `3lqtlt`, `sdg31l`) and concurrent sibling Sets (`hm32d9`, `4gpguy`, `iflqsl`, `3tvesf`, `ckc3vl`, `zp2yyu`). Confirmed `- Item-Dependencies: executed:3lqtlt` matches `osjxbz`; closed the six-mode import-isolation gap between `osjxbz` line 94 and `sdg31l`; reconciled all `3lqtlt`/`tusvtd`/`0b8i7x` public flags, JSON shapes, exit codes, and helper names into `sdg31l`'s doc sync; and required additive doc updates preserving sibling Sets.

### Step S5

- Checked: Audited `OQ-01` (already resolved by evidence on 2026-11-21; updated `- Owner: none` to `- Owner: plan author (confirmed by evidence 2026-11-21)`), both deferred items (added `- Carrier-Declined:` lines), and all 4 review findings. All 4 findings had Low remediation risk and were fixed in place. Recorded reversible decisions `D-1`..`D-3` below. Zero blocking or uncarried questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | UNDER-SCOPE | R1/R4.A/R7 | `.aw/records/plans/pending/20261121-repro-check-04-sdg31l-documentation-sync-subpackage-guard-and-whole-set-validation.ipd.md:36-44,75-83`, `.aw/records/plans/pending/20261121-repro-check-03-3lqtlt-cli-and-tui-integration-for-reproducibility-assessment-and-p.ipd.md:62,67,74,108-146`, `docs/cli.md:673-700,759-765` | Doc sync omitted post-review `3lqtlt` contracts: `inspect` `meta_ref` hydration, 10-key JSON schema (`schema_version`, `mode`, `summary`), and `--fail-on` implicitly activating strict exit; `rerun` exit code `2` on invalid flag combinations without `--preflight`, `--preflight --json` shape (`rerun_command`, `executable_as_printed`, `assessment`), and lock-file fallback; `docs/cli.md### ui` TUI updates and `## Exit Codes` exit `2`; equivocal `docs/api.md` helper wording (`if surfaced`); and cross-Set additive doc coexistence rules. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Synced all `3lqtlt`/`tusvtd`/`0b8i7x` flags, JSON schemas, lock-file fallback, exit code `2`, and `ui` summary into `docs/cli.md`, made `docs/api.md` helper documentation definitive (`assess_run`, `should_fail_strict`, `hydrate_manifest_with_report`), and required additive doc coexistence with sibling Sets (`D-1`, recommendation strength: very strong). |
| PR-002 | HIGH | UNDER-SCOPE | R1/R2/R4.E/R7 | `.aw/records/plans/pending/20261121-repro-check-04-sdg31l-documentation-sync-subpackage-guard-and-whole-set-validation.ipd.md:48-58,84-96,142-149`, `.aw/records/plans/pending/20261121-repro-check-00-osjxbz-reproducibility-gap-assessment-and-rerun-preflight.ipd.md:94-95`, `tests/test_report_subpackage_integrity.py:21,33-64,99-120` | Orchestrator `osjxbz` cross-IPD validation requires `sdg31l` to prove all six import modes never import `pubrun.report.checks` or `pubrun.report.reproducibility` on import, whereas `sdg31l` checked only bare `import pubrun`. Proposed changes #5 also omitted specifying isolated `git` user config for CI `git init` tests, the sentinel offline/no-replay CLI test in `tests/test_reproducibility_e2e.py`, `reproducibility` in `test_report_call_and_submodule_coexist_same_process`, `sanitize_paths.py`, and `python3` consistency in `V-04`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added six-mode pre-import isolation assertion and single-process coexistence check in `tests/test_report_subpackage_integrity.py`, specified isolated `git` config and sentinel no-replay/read-only CLI test in `tests/test_reproducibility_e2e.py`, added `python3 scripts/sanitize_paths.py --check --all` and Set test-file checks in `E-04`/`V-04`, and standardized on `python3` (`D-2`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-repro-check-04-sdg31l-documentation-sync-subpackage-guard-and-whole-set-validation.ipd.md:157`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | `## Approval and execution gate` was a single sentence missing compliant `--scope-reason`/`--scope-ack` scope declaration, `never git add -A/-a` / `never push`, HARD MUST honesty wording, and giving an unconditional lifecycle-transition instruction rather than conditional runner-lane vs standalone `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced gate prose with a complete 5-item Execution contract matching `steps/r2-executability.md`, `steps/s7-finalize.md`, and reviewed siblings `0b8i7x`, `tusvtd`, and `3lqtlt` (recommendation strength: very strong). |
| PR-004 | MEDIUM | IN-SCOPE | Check P/S5/R2 | `.aw/records/plans/pending/20261121-repro-check-04-sdg31l-documentation-sync-subpackage-guard-and-whole-set-validation.ipd.md:28,98-102,125,130,133,138`, `.aw/system/workflows/technical-writing/technical-writing.md:40-45` | Missing Mermaid diagram across 6 target files (requirement 12(a)); both deferred items lacked `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`); `OQ-01` carried `- Owner: none`; lines 130, 133, and 138 carried literal em/en dashes (`IPD-C802`); and prose had dense sentences and informal doc citations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `erDiagram`, added `- Carrier-Declined:` to both deferred items (`D-3`), updated `OQ-01` `- Owner: plan author (confirmed by evidence 2026-11-21)`, replaced all literal em/en dashes with parentheses and `U+2014`/`U+2013` code points, split dense sentences, and standardized `path#Heading` / `path::Symbol` citations (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Whether `docs/api.md` should definitively document `assess_run`, `should_fail_strict`, and `hydrate_manifest_with_report` (vs `E-02`'s equivocal `"if surfaced"`) | Document all three helpers definitively as read-only offline diagnostic APIs (never imported by `import pubrun`) alongside `docs/cli.md### ui` and `## Exit Codes` exit `2` | Leave `"if surfaced"` ambiguous (risks executor skipping `docs/api.md` helper docs or leaving `docs/cli.md` out of sync with `3lqtlt`) | `.aw/records/plans/pending/20261121-repro-check-01-0b8i7x-shared-reproducibility-evidence-model-and-recorded-gap-analy.ipd.md:131`, `.aw/records/plans/pending/20261121-repro-check-02-tusvtd-read-only-offline-rerun-preflight-comparison-engine.ipd.md:169`, `.aw/records/plans/pending/20261121-repro-check-03-3lqtlt-cli-and-tui-integration-for-reproducibility-assessment-and-p.ipd.md:67,74` | yes |
| D-2 | Where to verify six-mode import isolation required by orchestrator `osjxbz` line 94 | Add the pre-import `sys.modules` assertion for `pubrun.report.checks` and `pubrun.report.reproducibility` directly inside `tests/test_report_subpackage_integrity.py::test_report_is_callable_and_subpackage_under_every_mode` (already in `- Scope-Paths:`) | Add a separate new test file (expands `- Scope-Paths:` unnecessarily) or check only bare `import pubrun` (leaves five modes unverified against `osjxbz`) | `.aw/records/plans/pending/20261121-repro-check-00-osjxbz-reproducibility-gap-assessment-and-rerun-preflight.ipd.md:94`, `tests/test_report_subpackage_integrity.py:33-64` | yes |
| D-3 | How to close the two deferred items (`check.ipd-uncarried-obligation`) and `OQ-01` owner field | Add `- Carrier-Declined:` to both deferred items (CI matrix enforced by `.github/workflows/ci.yml`; performance speedup benchmarks N/A for read-only CLI-only diagnostics) and set `OQ-01` `- Owner: plan author (confirmed by evidence 2026-11-21)` | Leave deferred items uncarried (triggers `check.ipd-uncarried-obligation`) or retain `- Owner: none` | `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91`, `.github/workflows/ci.yml:1-37` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Workflow history`, `Goal`, `erDiagram`, `E-01`..`E-04`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-04`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
