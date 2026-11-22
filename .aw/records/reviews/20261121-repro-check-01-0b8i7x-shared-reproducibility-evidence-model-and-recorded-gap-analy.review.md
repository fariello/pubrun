# Review findings: ipd 0b8i7x

- Subject-Id: 0b8i7x
- Subject-Type: ipd
- Reviewed-At: 2026-11-21
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step T

1. Yes — introduces `HydrationReport` and `hydrate_manifest_with_report` in `src/pubrun/report/utils.py`, creates `src/pubrun/report/reproducibility.py` (consumed by sibling plans `tusvtd`, `3lqtlt`, and `sdg31l`), and changes `src/pubrun/report/checks.py::manifest_findings` and `assess_run`.
2. Yes — modifies `src/pubrun/report/utils.py`, which enforces `meta_ref` path-traversal and `.json` extension security (`_is_meta_ref_allowed`), and inspects redacted CLI arguments and environment variables.
3. No — 4 E-items across 4 cohesive files in `src/pubrun/report/` and `tests/`.
4. Yes — `- Scope-Paths:` lists all four files (`src/pubrun/report/utils.py`, `src/pubrun/report/reproducibility.py`, `src/pubrun/report/checks.py`, `tests/test_reproducibility_assessment.py`).
5. Yes — a regression in `hydrate_manifest` could weaken `meta_ref` path-traversal protection or break existing callers, and unintended `WARN` severities in `manifest_findings` would break existing `pubrun inspect --strict` callers.

AW-TIER: complex

### Step R1

- Checked: Verified every code, schema, test, backlog, and sibling-plan citation in `0b8i7x` against `src/pubrun/report/utils.py`, `src/pubrun/report/checks.py`, `src/pubrun/report/output.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/capture/git.py`, `src/pubrun/capture/packages.py`, `src/pubrun/capture/invocation.py`, `src/pubrun/capture/redaction.py`, `src/pubrun/capture/host.py`, `src/pubrun/capture/environment.py`, `src/pubrun/capture/python_runtime.py`, `src/pubrun/core.py`, `src/pubrun/__main__.py`, `schemas/manifest.schema.json`, `pyproject.toml`, `tests/test_checks_commands.py`, `tests/test_profile_deprecation.py`, `tests/test_reports.py`, `tests/test_quality.py`, `tests/test_hpc_hydration_e2e.py`, `.aw/records/backlog/graduated/20261121-pubrun-improve-01-q3bll1-repro-preflight.backlog.md`, and sibling plans in Sets `repro-check`, `dep-capture`, `file-prov`, and `cap-isolation`. Surfaced and fixed domain-count inconsistency (PR-001) and manifest key-nesting inaccuracies (PR-002).

### Step R2

- Checked: Verified 1:1 `E-*`/`V-*` bijection (`E-01..E-04` to `V-01..V-04`), `- Scope-Paths:` fence, `- Item-Dependencies: none`, concrete pasted-output demands in every `V-*`, runtime-demonstration reachability (all four V-items run `pytest` or a Python subprocess isolation check, reachable by construction), absence of hardcoded mutable record-tree counts, and execution contract in `## Approval and execution gate`. Surfaced and fixed missing execution-contract elements and unconditional finalize wording (PR-006), plus missing security and deprecation test suites in V-01/V-03/V-04 (PR-004).

### Step R3

- Checked: Reviewed `meta_ref` path-traversal and `.json` extension enforcement in `src/pubrun/report/utils.py::_is_meta_ref_allowed` and `tests/test_quality.py::TestMetaRefSecurity`, non-mutation of raw manifests, defensive JSON/dict validation, redaction handling (`src/pubrun/capture/redaction.py::redact_argv` and `redact_env_vars` plain-string heuristics), and `import pubrun` host-path isolation. Surfaced and fixed security check ordering and `TestMetaRefSecurity` coverage (PR-004) and heuristic `[REDACTED]` detection in plain environment values (PR-002).

### Step R4

- Checked: Applied engineering rubric sections A (correctness/data integrity), C (architecture/operability), D (anti-regression/domain invariants), E (testing/verification), F (KISS, fallback principles, accessibility), right-sizing/conceptual density, and spec/documentation sync (deferred honestly to `sdg31l`; `schemas/manifest.schema.json` unchanged). Surfaced and fixed ambiguous finding severities, undefined parent-snapshot staleness rule, and `--strict` regression risk (PR-003), plus accessibility alignment with `src/pubrun/report/output.py` (PR-005).

### Step R5

- Checked: Evaluated through all eight reviewer personas (`QA/QC`, `Testing & regression`, `UI/UX`, `Architect`, `Software engineer`, `Power user`, `Novice`, `Stakeholder`). QA/QC and Software engineer surfaced schema-path errors, numeric timestamp checks, redacted-dict `hostname` handling, and ambiguous severities; Testing & regression surfaced missing `TestMetaRefSecurity` and `test_profile_deprecation.py` coverage; Architect surfaced `assess_run` definition ownership across `0b8i7x` and `tusvtd`; UI/UX surfaced `NO_COLOR`/no-`DIM` formatter alignment; Power user, Novice, and Stakeholder confirmed `q3bll1` fitness, configurable staleness threshold, zero numerical scores, and explicit non-guarantee disclaimer.

### Step R6

- Checked: Evaluated decomposition and conceptual density for `E-01` through `E-04`. `0b8i7x` is already child 01 of 4 in Set `repro-check`, with 4 E-items mapped 1:1 to 4 cohesive files (`utils.py`, `reproducibility.py`, `checks.py`, `tests/test_reproducibility_assessment.py`). With the explicit severity rules and field paths added in this review, each E-item is executable in one focused pass without inventing architecture; no further split is warranted.

### Step R7

- Checked: Verified cross-plan consistency across Set `repro-check` (`osjxbz`, `0b8i7x`, `tusvtd`, `3lqtlt`, `sdg31l`) and defensive alignment with concurrent pending Sets `dep-capture` (`ijipnx`), `file-prov` (`hm32d9`), and `cap-isolation` (`26euz0`). Reconciled 7-category alignment with `osjxbz`, aligned `assess_run` ownership in `reproducibility.py` (re-exported in `checks.py`) with `tusvtd` E-03, added `"counts": {}` to the default `preflight` dict, and added defensive handling for `data_files.mixed`, `hash_status`, `packages.unresolved`/`snapshot_stage`, and `errors.records` (PR-001, PR-005).

### Step S5

- Checked: Verified pre-existing `OQ-01` (already resolved by the maintainer on 2026-11-21 via `/askme`, updated `- Owner: maintainer`). Recorded three reversible evidence-backed design decisions (`D-1`, `D-2`, `D-3`) in `### Decisions` below. No blocking or irreversible human decision remains open.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal & E-02 | Stated "six provenance domains" / "six recorded evidence domains" | Stated "seven structured evidence categories" naming all seven | Resolved internal contradiction with Proposed changes #2, V-02, and `osjxbz` (Req 4, 11) |
| Goal Mermaid `erDiagram` | Included `INHERITED_SECTION` and omitted `HYDRATION_REPORT` -> `ASSESSMENT` link | Removed mismatched entity and added `HYDRATION_REPORT \|\|--o{ ASSESSMENT : informs` | Aligned diagram entities and relationships with normative text (Req 12(d), 12(e)) |
| Proposed changes #2 | Misplaced `entrypoint_type` under `invocation.script`; used bare `argv`/`rerun_command`/`working_directory`/`subprocesses_enabled`; omitted `"running"` outcome | Corrected to `invocation.entrypoint_type`, `invocation.argv`, `invocation.rerun_command`, `invocation.working_directory`, `capture.subprocesses_enabled`, and included `"running"` | Fixed factual schema-path inaccuracies verified against code and schema (Req 5, 7) |
| Proposed changes #2 | Left finding severities unspecified or ambiguous (`INFO/WARN`) and left "stale" parent snapshot undefined | Specified explicit per-finding severities and configurable `DEFAULT_STALE_PARENT_SECONDS = 86400.0` | Made requirements verifiable and eliminated `--strict` regression ambiguity (Req 5, 6, 10) |
| Project conventions & OQ-01 | Used unanchored function references and `- Owner: none` on maintainer-resolved OQ-01 | Cited `path::Symbol` anchors, expanded "high-performance computing (HPC)", set `- Owner: maintainer` | Improved citation precision and requirement 1 clarity |
| Approval and execution gate | Omitted explicit scope-fence/never-push terms and issued unconditional finalize command | Added full 5-part execution contract with conditional runner/executor finalize ownership | Conformed to plan-review execution-contract requirements |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R4/R7 | `.aw/records/plans/pending/20261121-repro-check-01-0b8i7x-shared-reproducibility-evidence-model-and-recorded-gap-analy.ipd.md:28` (`Goal`, `E-02`) vs `osjxbz:84` | Goal and `E-02` said "six" evidence domains while Proposed changes #2, `V-02`, and orchestrator `osjxbz` specify seven categories (`source`, `runtime`, `dependencies`, `inputs_outputs`, `capture_completeness`, `parent_metadata`, `invocation`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Goal and `E-02` to state all seven structured categories consistently across the plan and Set. Recommendation strength: very strong. |
| PR-002 | HIGH | IN-SCOPE | R1/R4 | `src/pubrun/capture/invocation.py::get_invocation:176-184`, `schemas/manifest.schema.json:443-652`, `src/pubrun/capture/redaction.py::redact_env_vars:176-181` | Proposed changes #2 nested `entrypoint_type` under `invocation.script`, used bare keys for `invocation.argv`/`invocation.rerun_command`/`invocation.working_directory`/`capture.subprocesses_enabled`, omitted `"running"` from non-completed `status.outcome`, and omitted heuristic `[REDACTED]` inside `plain` environment values. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected all manifest key paths, added `"running"` to non-completed `status.outcome` values, and specified detecting both `redacted`/`hashed` representations and `[REDACTED]` inside `plain` environment strings. Recommendation strength: very strong. |
| PR-003 | HIGH | IN-SCOPE | R2/R4 | `src/pubrun/report/checks.py::manifest_findings:302-424`, `src/pubrun/__main__.py::_run_inspect:1017`, `tests/test_checks_commands.py::TestManifestFindings:121-187` | New finding severities were ambiguous (`packages_editable_present` listed as `INFO/WARN`) or omitted, and "stale" parent snapshot lacked a defined condition, creating `pubrun inspect --strict` regression risk and forcing the executor to invent thresholds. | C:Low; U:Low; S:Low; F:Medium; Overall:Medium | FIXED | Specified explicit severities preserving existing `--strict` contracts and defined stale parent snapshots via `script_modified_after_parent` (`warn`), `age_seconds < 0` (`warn`), and configurable `DEFAULT_STALE_PARENT_SECONDS = 86400.0` (`info`). Recorded as `D-1`/`D-2`. Recommendation strength: strong. |
| PR-004 | MEDIUM | IN-SCOPE | R3/R4 | `src/pubrun/report/utils.py::hydrate_manifest:50-127`, `tests/test_quality.py::TestMetaRefSecurity:375-476`, `tests/test_profile_deprecation.py:101-118` | `E-01`/Proposed changes #1 did not pin the security check order (`.json` -> `_is_meta_ref_allowed` -> `exists` -> read), defensive non-dict/numeric-timestamp/redacted-hostname guards, or `TestMetaRefSecurity` and `test_profile_deprecation.py` regression test coverage. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified exact pre-read security check order, deep-copy and type/numeric guards, redacted `hostname` unwrapping, and added `tests/test_quality.py` (`TestMetaRefSecurity`) and `tests/test_profile_deprecation.py` to `Required tests / validation`, `V-01`, `V-03`, and `V-04`. Recommendation strength: very strong. |
| PR-005 | MEDIUM | IN-SCOPE | R7 | `20261121-repro-check-02-tusvtd...ipd.md:72`, `src/pubrun/report/output.py:16-20`, `20261121-file-prov-04-hm32d9...ipd.md:51` | `0b8i7x` omitted `assess_run` from `reproducibility.py` (which `tusvtd` E-03 extends there), omitted `"counts": {}` in default `preflight`, omitted defensive support for `data_files.mixed`/`hash_status` and `errors.records`, and did not align `format_reproducibility_detail` with `output.py` no-`DIM`/`NO_COLOR` rules. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Defined `assess_run` in `reproducibility.py` and re-exported it in `checks.py` (`D-3`), added `"counts": {}` to default `preflight`, added defensive handling for sibling Set optional fields, clarified `invocation.inputs`-only behavior, and aligned formatter accessibility with `output.py`. Recommendation strength: very strong. |
| PR-006 | MEDIUM | UNDER-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-repro-check-01-0b8i7x-shared-reproducibility-evidence-model-and-recorded-gap-analy.ipd.md:181-186` (`Approval and execution gate`) | `## Approval and execution gate` omitted explicit resolved-OQ confirmation, scope-fence justification rules (`--scope-reason`/`--scope-ack`), `never push`, and conditional runner/executor ownership of `aw ipd finalize`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced gate prose with the complete five-part execution contract including conditional runner/executor lifecycle ownership and compliant scope-fence wording. Recommendation strength: very strong. |
| PR-007 | LOW | IN-SCOPE | P/R2 | `.aw/records/plans/pending/20261121-repro-check-01-0b8i7x-shared-reproducibility-evidence-model-and-recorded-gap-analy.ipd.md:34-42,78-84,154` | Mermaid `erDiagram` used mismatched `INHERITED_SECTION` entity and omitted `HYDRATION_REPORT` -> `ASSESSMENT`; conventions used unanchored symbol names and unexpanded `HPC`; maintainer-resolved `OQ-01` carried `- Owner: none`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Aligned Mermaid diagram with normative text, updated citations to `path::Symbol`, expanded `HPC`, and set `OQ-01` `- Owner: maintainer`. Recommendation strength: strong. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | What severities should new recorded-manifest findings (`packages_editable_present`, `git_unavailable`, `packages_empty`, `script_unhashed`, `determinism`, `env_vars_redacted` vs capture failures and incomplete outcomes) use so `pubrun inspect --strict` stays backward compatible? | Use `info` for `packages_editable_present`, `git_unavailable`, `packages_empty`, `script_unhashed`, `determinism`, `env_vars_redacted`, and `no_file_provenance`; use `warn` for `git_dirty_unrecorded` (per OQ-01), `git_timeout`/`git_failed`, `packages_partial`/`packages_failed`, non-completed `status.outcome`, failed/partial/timeout `capture_state`, `rerun_command_redacted`, and broken/mismatched/post-dated/script-drifted `meta_ref`. | Make `packages_editable_present` or `git_unavailable` `warn`, which would fail `pubrun inspect --strict` on standard editable dev installs and non-git directories. | `src/pubrun/report/checks.py::manifest_findings`, `src/pubrun/__main__.py::_run_inspect:1017`, `tests/test_checks_commands.py::TestManifestFindings`, and maintainer-resolved `OQ-01`. | yes |
| D-2 | What exact condition defines a "stale" parent `meta_ref` snapshot? | Treat `script_modified_after_parent is True` and `age_seconds < 0` (post-dated) as `warn`, and `age_seconds > stale_parent_seconds` (configurable parameter defaulting to `DEFAULT_STALE_PARENT_SECONDS = 86400.0`, 24 hours) as `info` (`parent_metadata_stale`). | Hardcode a `warn` age threshold (risks breaking `--strict` on long-queued HPC array jobs) or leave "stale" undefined for the executor to guess. | `src/pubrun/report/utils.py::hydrate_manifest:100-110`, backlog `q3bll1` item 5, and fallback KISS/configurable principle. | yes |
| D-3 | Should `assess_run` be defined in `src/pubrun/report/reproducibility.py` and re-exported in `src/pubrun/report/checks.py`, or defined directly in `checks.py`? | Define `assess_run` in `src/pubrun/report/reproducibility.py` and re-export it from `src/pubrun/report/checks.py`. | Define a separate wrapper in `checks.py` that `tusvtd` would have to replace. | Sibling plan `tusvtd` E-03 (`20261121-repro-check-02-tusvtd-read-only-offline-rerun-preflight-comparison-engine.ipd.md:72`) and `3lqtlt` E-01. | yes |
