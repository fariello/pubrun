# Review findings: ipd ihh27o

- Subject-Id: ihh27o
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, `Goal`, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261122-bugs-audit-06-ihh27o-fix-self-check-meta-snapshot-and-report-rendering-bugs.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal` and new `Self-check scheduler disambiguation and meta snapshot depth mapping` diagram | Dense 50-word goal sentence; unexpanded acronyms (`TOML`, `SGE`, `PBS`, `LSF`, `CWD`, `RSS`, `CPU`, `ARM64`, `CLI`); no Mermaid diagram for branching scheduler/depth flows | Split `Goal` into three direct sentences, expanded acronyms on first use, and added `flowchart TD` matching the normative text | Technical writing requirements 1, 2, 12(a), 12(b), 12(d), and 12(e) |
| Citations across `E-01`..`E-04`, `Project conventions`, `Findings`, `Proposed changes` | Bare module-dotted symbols (`report.checks._install_health_findings`), nonexistent config target `pyproject.toml`, stale `timing-acc` pending note, and stale `methods.py` live-bug claim | Standardized `path::Symbol` citations, replaced `pyproject.toml` with the 3 canonical `config.py` TOML paths, updated `timing-acc` (`vrr1fv` executed), and separated live `meta_snapshot.py` null-CPU bug from already-guarded `methods.py`/`diagnostics.py` | `steps/p-proofread.md` Section 11.1 and repository factual accuracy |
| `## Spec / documentation sync` | Bare unsubstantiated `N/A` | Cited verified `docs/cli.md`, `docs/functional_spec.md`, `docs/hpc.md`, `docs/manifest.md`, and `README.md` contracts | `steps/r4-engineering.md` spec/documentation sync rule |
| `## Approval and execution gate` | Missing honesty, never-push, scope-declaration, and conditional finalize clauses; vague manual-move wording | Replaced with compliant 5-item Execution contract using `--scope-reason`/`--scope-ack`, HARD MUST pasted-output rule, never-push, and conditional `aw ipd finalize ihh27o` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, `src/pubrun/report/checks.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/report/diagnostics.py`, `src/pubrun/report/methods.py`, `src/pubrun/report/utils.py`, `src/pubrun/config.py`, `src/pubrun/__main__.py`, `tests/test_reproducibility_assessment.py`, `tests/test_checks_commands.py`, `tests/test_reports.py`, and Set `bugs-audit` orchestrator `jqqvkh`.

1. Yes: changes `pubrun self-check` / `live_checks()` itemized output and `--strict` behavior on malformed TOML, wires `pubrun meta --basic/--standard/--deep` to active `capture.*` configuration, changes `print_resources_report` RSS chart series/title behavior, and adds `"host"` to `HYDRABLE_SECTIONS` (changing `HydrationReport.direct_sections`/`inherited_sections` consumed by `reproducibility.py` and `tests/test_reproducibility_assessment.py`).
2. No: does not touch private-data redaction engines, commit helpers, worktree isolation, or sandbox enforcement (though `meta_snapshot.py` must preserve `capture.environment.mode = "filtered"` so secrets remain redacted).
3. No: 5 focused E-items across 3 task groups in 4 report modules plus 2 test files (child 06 of 9 in Set `bugs-audit`).
4. Yes: `- Scope-Paths:` explicitly lists all modified files (updated during review to remove already-fixed `src/pubrun/report/methods.py` and add `tests/test_reproducibility_assessment.py`).
5. Yes: adding `"host"` to `HYDRABLE_SECTIONS` breaks `tests/test_reproducibility_assessment.py:179` if unaligned; concatenating `live_checks()` detail strings breaks `src/pubrun/__main__.py:1241` `--show-suggestions` matching; using `environment.mode = "full"` in `meta_snapshot.py` would leak secrets into `meta.json`; and naive SGE/PBS reordering breaks PBS compute nodes or SGE login nodes.

AW-TIER: complex

### Step R1

- Checked: Verified every cited file, symbol, config path, collector key, and test assertion across `src/pubrun/report/checks.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/report/diagnostics.py`, `src/pubrun/report/methods.py`, `src/pubrun/report/utils.py`, `src/pubrun/report/reproducibility.py`, `src/pubrun/config.py`, `src/pubrun/resources/default.toml`, `src/pubrun/__main__.py`, `src/pubrun/capture/{hardware,packages,environment,git,host,python_runtime}.py`, `tests/test_checks_commands.py`, `tests/test_reports.py`, `tests/test_reproducibility_assessment.py`, `tests/test_hpc_hydration_e2e.py`, `docs/cli.md`, `docs/functional_spec.md`, `docs/manifest.md`, `docs/hpc.md`, `README.md`, orchestrator `jqqvkh`, and sibling plans `l7ko8p`, `r68o07`, `8ebjeg`. Caught wrong `pyproject.toml` config claim and missing `WARN`-only / `live_checks` `--show-suggestions` constraint (`PR-001`), broken SGE/PBS `SGE_ROOT` + naive-reorder logic and nonexistent-root writability gap (`PR-002`), missing concrete `meta_snapshot` depth-to-collector mapping + secret-redaction constraint (`PR-003`), already-fixed `methods.py`/`diagnostics.py` null-CPU claim vs live `meta_snapshot.py:50` defect + guaranteed `tests/test_reproducibility_assessment.py:179` breakage from `"host"` hydration (`PR-004`), and non-conforming execution gate / inverted E/V test dependencies (`PR-005`).

### Step R2

- Checked: Verified author lint preflight (`aw ipd lint --phase author --agent` exit 0, `clean`, 0 findings), 1:1 `E-01`..`E-05` to `V-01`..`V-05` bijection (co-locating per-bug test authoring inside `E-01`..`E-04`), updated 6-file `- Scope-Paths:` parity, `- Item-Dependencies: none` matching orchestrator `jqqvkh`, concrete behavioral evidence in every `V-*` (all reachable via local `pytest`, no code-pinning), and `## Approval and execution gate` (fixed in `PR-005`).

### Step R3

- Checked: Verified `meta_snapshot.py` keeps `capture.environment.mode = "filtered"` at `"standard"` and `"deep"` (never `"full"`, preventing unredacted secret dumps into shared HPC `meta.json`), confirmed `hydrate_manifest_with_report` retains `.json` extension and `_is_meta_ref_allowed` sandbox checks before disk reads while adding `"host"` to `HYDRABLE_SECTIONS`, and verified `checks.py` remains read-only and isolated from `import pubrun`.

### Step R4

- Checked: Evaluated engineering rubric sections A (`config.py` canonical 3-path TOML parsing via Python 3.8+ `tomllib`, one check dict per finding matching `__main__.py:1241`, compute-allocation short-circuit + `qsub` marker disambiguation, `os.path.abspath` + `next_probe == probe` writability termination, lockstep `--last` filtering for `tree_rss` vs `rss`, and non-mutating `"host"` hydration preserving direct child `"host"`), C (reusing `config.tomllib`, `config.get_global_config_dir`, active `capture.*` collector keys without depending on sibling `l7ko8p`), D (preserving `tests/test_checks_commands.py`, `tests/test_reports.py`, `tests/test_hpc_hydration_e2e.py`, and updating `tests/test_reproducibility_assessment.py:179`), E (concrete behavioral tests in `tests/test_report_checks_bugs.py` + targeted suite + full `pytest -q`), F (KISS, `_out.info` for intentionally suppressed `--basic` sections, preventing silent malformed-config OK and silent suggestion drops), right-sizing (5 focused E-items without inverted `E-05`/`V-01`..`V-04` test dependency), and `## Spec / documentation sync`.

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught `pyproject.toml` false target (`PR-001`), `SGE_ROOT`-on-login-node and PBS-compute-node regressions (`PR-002`), nonexistent-root false OK (`PR-002`), live `meta_snapshot.py:50` `"None"` bug (`PR-004`), and `tests/test_reproducibility_assessment.py:179` breakage (`PR-004`).
  2. **Testing and regression expert:** Fixed inverted `V-01`..`V-04` dependency on `E-05`, added `tests/test_reproducibility_assessment.py` to `- Scope-Paths:`, pinned already-guarded `methods.py`/`diagnostics.py` null-CPU behavior in `tests/test_report_checks_bugs.py`, and verified full `pytest -q` in `V-05` (`PR-004`, `PR-005`).
  3. **UI / UX expert:** Preserved `--show-suggestions` exact-message matching and accurate warning counts in `pubrun self-check` (`PR-001`), avoided spurious `[WARN ]` lines for intentionally suppressed `--basic` meta sections (`PR-003`), and ensured RSS chart titles always match the plotted series (`PR-004`).
  4. **Systems and software architect:** Aligned `_hpc_login_node_findings` `qsub` disambiguation with `src/pubrun/__main__.py:1422-1472`, kept `meta_snapshot.py` depth mapping strictly on active collector keys independent of sibling `l7ko8p`, and aligned `HYDRABLE_SECTIONS` with `meta_snapshot.py` and `_compare_parent_child_identity` (`PR-002`, `PR-003`, `PR-004`).
  5. **Software engineer:** Removed unneeded `src/pubrun/report/methods.py` from `- Scope-Paths:` to avoid no-op edits or `--scope-ack`, removed dead `by_prefix` in `live_checks`, and hardened the execution-contract gate (`PR-001`, `PR-004`, `PR-005`).
  6. **Sophisticated power user:** Confirmed multi-mount NFS/hung/slow warnings all appear in `pubrun self-check`, SGE and PBS clusters behave accurately on both login and compute nodes, and `pubrun meta --basic/--standard/--deep` gives real speed/depth control (`PR-001`, `PR-002`, `PR-003`).
  7. **Complete novice:** Added the scheduler/depth Mermaid flowchart, split the dense `Goal`, expanded acronyms, and documented exact `config.toml` / `.pubrun.toml` paths (`PR-001`, `PR-005`).
  8. **Stakeholder:** Confirmed all 8 diagnostic and reporting bugs assigned to `ihh27o` in Set `bugs-audit` (`jqqvkh`) are covered cleanly with zero silent deferrals.

### Step R6

- Checked: Evaluated decomposition across `E-01`..`E-05`. `ihh27o` is already child 06 of 9 in Set `bugs-audit`, covering 4 cohesive `report/` modules and 2 test files across 4 focused implementation passes plus 1 full-suite verification pass. No split recommended.

### Step R7

- Checked: Verified alignment with Set `bugs-audit` orchestrator `jqqvkh` and sibling child plans (`njn1up`..`kqzd15`). Confirmed `- Item-Dependencies: none` matches `jqqvkh`, `meta_snapshot.py` depth overrides rely only on already-active collector keys so `ihh27o` does not depend on `l7ko8p`, updated `- Scope-Paths:` (`checks.py`, `meta_snapshot.py`, `diagnostics.py`, `utils.py`, `tests/test_reproducibility_assessment.py`, `tests/test_report_checks_bugs.py`) remains completely disjoint from all 8 sibling child plans in `bugs-audit`, and `src/pubrun/tui/widgets/details.py` stays with sibling `8ebjeg`.

### Step S5

- Checked: Audited pre-existing `## Open questions` (`None`), `## Deferred / out of scope` (`None`), and all 5 review findings (`PR-001`..`PR-005`). All 5 findings had Low remediation risk and were fixed in place. Recorded reversible evidence-based decisions `D-1`..`D-5` below. Zero unresolved or blocking human questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-06-ihh27o-fix-self-check-meta-snapshot-and-report-rendering-bugs.ipd.md:39`, `src/pubrun/config.py:62-130`, `src/pubrun/report/checks.py:30-31,230-260`, `src/pubrun/__main__.py:1229-1251` | `E-01` wrongly named `pyproject.toml` (which `pubrun.config` never loads) instead of the 3 canonical config TOML files (`get_global_config_dir() / "config.toml"`, `.config/pubrun/config.toml`, `.pubrun.toml`), said "error/warn" when `checks.py` only defines `WARN`/`INFO` (`--strict` checks `severity == "warn"`), and omitted that `src/pubrun/__main__.py:1241` matches `--show-suggestions` via exact `f.get("message") == detail` equality (so `live_checks` must emit one check entry per matched finding, not concatenate messages). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified explicit `pubrun.config.tomllib.loads` parsing across the 3 canonical `config.py` paths emitting `WARN` `"config_invalid"`, and required `live_checks` to remove dead `by_prefix` and emit one check record per matched finding preserving exact `detail` (`D-1`, recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R1/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-06-ihh27o-fix-self-check-meta-snapshot-and-report-rendering-bugs.ipd.md:44,86`, `src/pubrun/report/checks.py:144-157,262-296`, `src/pubrun/__main__.py:1422-1472` | `E-02` treated `SGE_ROOT` as a compute-node marker (it is set on SGE login nodes too) and Proposed changes #1 naively reordered SGE ahead of PBS in the `seen`-gated loop (which would misclassify PBS compute nodes as SGE login nodes); and the writability fix used `.resolve()` without specifying `output_not_writable` when the ancestor walk terminates at a nonexistent root (`next_probe == probe`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required short-circuiting `_hpc_login_node_findings` on any compute allocation var (`SLURM_JOB_ID`, `PBS_JOBID`, `LSB_JOBID`, `JOB_ID`, `PE_HOSTFILE`), disambiguating `qsub` login labels via `SGE_ROOT`/`SGE_O_HOST` vs `PBS_ENVIRONMENT`/`PBS_O_HOST`, and anchoring writability via `os.path.abspath` with `next_probe == probe` emitting `WARN` `"output_not_writable"` when no existing ancestor exists (`D-2`, recommendation strength: very strong). |
| PR-003 | HIGH | UNDER-SCOPE | R2/R3/R4.A | `.aw/records/plans/pending/20261122-bugs-audit-06-ihh27o-fix-self-check-meta-snapshot-and-report-rendering-bugs.ipd.md:49-52,87`, `src/pubrun/report/meta_snapshot.py:24-46`, `src/pubrun/__main__.py:3042-3046`, `src/pubrun/capture/{hardware,git,environment,packages}.py` | `E-03` did not specify the concrete `basic`/`standard`/`deep` `capture.*` override mapping (forcing the executor to invent it and risking either `environment.mode = "full"` secret leaks or relying on unimplemented `depth = "off"` checks from sibling `l7ko8p`), omitted invalid-depth handling, and left `_gather` emitting `[WARN ]` for intentionally suppressed `--basic` sections. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified the exact active `capture.*` override table for `"basic"`, `"standard"`, and `"deep"` (keeping `environment.mode = "filtered"` at `"standard"`/`"deep"`), required `ValueError` on invalid depth, and specified `_out.info` for intentionally `"suppressed"` sections (`D-3`, recommendation strength: very strong). |
| PR-004 | HIGH | IN-SCOPE | R1/R4.D/R2 | `.aw/records/plans/pending/20261122-bugs-audit-06-ihh27o-fix-self-check-meta-snapshot-and-report-rendering-bugs.ipd.md:6-7,54-57,69,81-82,88`, `src/pubrun/report/methods.py:236-237,339-341`, `src/pubrun/report/diagnostics.py:875,1460-1565`, `src/pubrun/report/meta_snapshot.py:50`, `src/pubrun/report/utils.py:13-20`, `tests/test_reproducibility_assessment.py:79-84,179` | `methods.py` and `diagnostics.py:875` already guard `cpu.model = None` (landed in `26euz0`, commit `d5f7af0`), whereas `src/pubrun/report/meta_snapshot.py:50` still prints literal `"None"` via `.get("model", "unknown")`; adding `"host"` to `HYDRABLE_SECTIONS` will break `tests/test_reproducibility_assessment.py:179` (missing from `- Scope-Paths:`); `print_resources_report` lacked lockstep `--last` filtering / length-alignment rules for `tree_rss` vs `rss`; and `Project conventions` had a stale note that `timing-acc` is still pending on `diagnostics.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Moved the live null-CPU fix to `meta_snapshot.py:50` (`E-03`), removed already-fixed `src/pubrun/report/methods.py` from `- Scope-Paths:` (keeping regression tests for `methods.py` and `diagnostics.py` in `E-04`), added `tests/test_reproducibility_assessment.py` to `- Scope-Paths:` and `E-04`, specified exact `tree_rss` selection/filtering in `print_resources_report`, and corrected the `timing-acc` note (`D-4`, `D-5`, recommendation strength: very strong). |
| PR-005 | HIGH | IN-SCOPE | R2/S7/Check P | `.aw/records/plans/pending/20261122-bugs-audit-06-ihh27o-fix-self-check-meta-snapshot-and-report-rendering-bugs.ipd.md:22-65,105-147`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | `## Approval and execution gate` omitted the HARD MUST pasted-output honesty rule, never-push rule, `--scope-reason`/`--scope-ack` scope declaration, and conditional runner vs standalone `aw ipd finalize ihh27o` ownership; `Workflow history` was oldest-first; `V-01`..`V-04` depended on `tests/test_report_checks_bugs.py` created only in `E-05`; `Spec / documentation sync` was unsubstantiated `N/A`; and the plan lacked a Mermaid diagram (Requirement 12(b)), `path::Symbol` citations, and acronym expansions. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract, reordered `Workflow history` newest-first, co-located per-bug test authoring inside `E-01`..`E-04`, added the scheduler/depth Mermaid flowchart, substantiated `Spec / documentation sync`, standardized `path::Symbol` citations, and expanded acronyms (recommendation strength: very strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Which TOML files should `_install_health_findings` parse and how should `live_checks` return multiple findings per check? | Parse the 3 canonical `config.py` paths (`get_global_config_dir() / "config.toml"`, `.config/pubrun/config.toml`, `.pubrun.toml`) via `pubrun.config.tomllib.loads` emitting `WARN` `"config_invalid"`, and emit one check dict per matched finding in `live_checks()` preserving exact `detail` strings. | Parse `pyproject.toml` (never loaded by `pubrun.config`) or concatenate finding messages into one `detail` string (breaks `src/pubrun/__main__.py:1241` `--show-suggestions` matching and undercounts warnings). | `src/pubrun/config.py:62-130`, `src/pubrun/report/checks.py:30-31,230-260`, `src/pubrun/__main__.py:1229-1251` | yes |
| D-2 | How should `_hpc_login_node_findings` disambiguate `qsub` across SGE and PBS, and how should the writability check handle nonexistent roots? | Short-circuit on any compute allocation variable (`SLURM_JOB_ID`, `PBS_JOBID`, `LSB_JOBID`, `JOB_ID`, `PE_HOSTFILE`) first, then label `qsub` login nodes via `SGE_ROOT`/`SGE_O_HOST` vs `PBS_ENVIRONMENT`/`PBS_O_HOST`; anchor writability with `os.path.abspath`, stop on `next_probe == probe`, and emit `WARN` `"output_not_writable"` when no existing ancestor exists. | Reorder SGE ahead of PBS in the existing `seen` loop or treat `SGE_ROOT` as a compute-node marker (breaks PBS compute nodes and SGE login nodes); treat nonexistent root as OK (false positive). | `src/pubrun/report/checks.py:143-157,262-296`, `src/pubrun/__main__.py:1422-1472`, `tests/test_checks_commands.py:96-120` | yes |
| D-3 | What concrete `capture.*` overrides should `generate_meta_snapshot` apply for `"basic"`, `"standard"`, and `"deep"`? | Map `"basic"` to `hardware.depth="basic"`, `git.check_dirty=False`, `environment.mode="off"`, `packages.mode="off"`; `"standard"` to `hardware.depth="standard"`, `git.check_dirty=True`, `environment.mode="filtered"`, `packages.mode="top-level-installed"`; `"deep"` to `hardware.depth="deep"`, `capture_gpu_clock_speed=True`, `git.check_dirty=True`, `environment.mode="filtered"`, `packages.mode="full-environment"`; validate `depth` and log `"suppressed"` via `_out.info`. | Leave mapping unspecified (executor guesswork), use `environment.mode="full"` at `"deep"` (leaks unredacted secrets), or rely on `depth="off"` across collectors not yet updated by `l7ko8p`. | `src/pubrun/report/meta_snapshot.py:24-61`, `src/pubrun/__main__.py:3042-3046`, `src/pubrun/resources/default.toml`, `src/pubrun/capture/{hardware,git,environment,packages}.py` | yes |
| D-4 | How should `ihh27o` handle `BUG-64a` (`cpu.model = None`) given `methods.py` and `diagnostics.py` are already guarded? | Remove already-fixed `src/pubrun/report/methods.py` from `- Scope-Paths:`, fix the live `"None"` bug in `src/pubrun/report/meta_snapshot.py:50`, keep `methods.py`/`diagnostics.py` null-CPU regression pins in `tests/test_report_checks_bugs.py`, and leave `src/pubrun/tui/widgets/details.py` with sibling plan `8ebjeg`. | Keep `methods.py` in `- Scope-Paths:` (causes no-op edit or unnecessary `--scope-ack`) or expand scope into `tui/widgets/details.py` (violates `bugs-audit` disjoint file partitioning). | `src/pubrun/report/methods.py:236-237,339-341`, `src/pubrun/report/diagnostics.py:875`, `src/pubrun/report/meta_snapshot.py:50`, `git show d5f7af0`, `jqqvkh:126-127` | yes |
| D-5 | Should `tests/test_reproducibility_assessment.py` be updated in `ihh27o` when adding `"host"` to `HYDRABLE_SECTIONS`? | Add `tests/test_reproducibility_assessment.py` to `- Scope-Paths:` and update line 179 expected `direct_sections` set to include `"host"`. | Omit `tests/test_reproducibility_assessment.py` from `- Scope-Paths:` (guaranteed `pytest` failure on line 179 because `_adequate_manifest()` includes `"host"`). | `src/pubrun/report/utils.py:13-20,236-238`, `tests/test_reproducibility_assessment.py:79-84,179` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against Round 1 edits. Round 1 modified `- Scope-Paths:` (removing already-fixed `src/pubrun/report/methods.py` and adding `tests/test_reproducibility_assessment.py`), so a Round 2 re-review pass is required before finalization.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: Re-read the entire revised `.aw/records/plans/pending/20261122-bugs-audit-06-ihh27o-fix-self-check-meta-snapshot-and-report-rendering-bugs.ipd.md` after Round 1 edits. Verified every `path::Symbol` citation against `src/pubrun/report/checks.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/report/diagnostics.py`, `src/pubrun/report/methods.py`, `src/pubrun/report/utils.py`, `src/pubrun/config.py`, `src/pubrun/__main__.py`, and `tests/test_reproducibility_assessment.py`. Swept the plan for superseded tokens (`pyproject.toml`, `error/warn`, `Pending IPD Set timing-acc`, `core.profile` left wired, manual-move wording): zero stale occurrences remain.

### Step R2

- Checked: Re-verified 1:1 `E-01`..`E-05` to `V-01`..`V-05` bijection, `- Highest E allocated: 05`, 6-file `- Scope-Paths:` parity across `Scope`, `Scope-Paths`, `Scope check`, `Proposed changes`, and Execution contract items 2 and 4, `- Item-Dependencies: none`, compliant 5-item Execution contract in `## Approval and execution gate`, and `aw ipd lint --phase review-finalize --agent` clean disposition.

### Step R7

- Checked: Re-verified cross-plan alignment with Set `bugs-audit` orchestrator `jqqvkh` and sibling plans (`njn1up`..`kqzd15`). Confirmed updated `- Scope-Paths:` (`src/pubrun/report/checks.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/report/diagnostics.py`, `src/pubrun/report/utils.py`, `tests/test_reproducibility_assessment.py`, `tests/test_report_checks_bugs.py`) remains completely disjoint from all 8 sibling child plans in `bugs-audit`, and `meta_snapshot.py` depth overrides depend only on already-active collector keys (independent of `l7ko8p`).

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 re-review pass confirmed zero new findings, zero changes to `E-*`/`V-*` counts, `- Scope-Paths:`, or `- Item-Dependencies:` in Round 2, and full cross-section consistency across front matter, workflow history, flowchart, checklist, findings, proposed changes, doc sync, validation items, and execution gate.

AW-REVIEW: DONE
