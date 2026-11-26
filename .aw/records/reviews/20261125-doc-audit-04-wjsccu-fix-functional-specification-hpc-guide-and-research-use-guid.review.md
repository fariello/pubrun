# Review findings: ipd wjsccu

- Subject-Id: wjsccu
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Gemini 4 Neon (Antigravity)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete plan text against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 citation forms. No pre-review snapshot was needed: lane `HEAD` `da1fbe7` had a clean working tree and the plan was already committed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) before any edit. Requirement 12: no diagram is needed; the steps are bounded prose and table edits across three existing documentation files with no new multi-entity model, branch, loop, or lifecycle, and the plan now states this in `## Scope check`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Concern, S-05, E-04/E-06 | "8 missing/omitted primary CLI subcommands" | "10 omitted primary CLI subcommands" (`init`, `inspect`, `self-check`, `bench`, `res` [alias `resources`], `cpu`, `mem`, `ui` [aliases `tui`, `gui`], `report-bug`, `feedback`) plus global `--version`/`--no-color`/`help`/`pbr` | Matches live `python3 -m pubrun --help` (20 visible primary commands; 10 omitted) and includes the `resources` alias (PR-004). |
| Goal, Project conventions, E-03, V-03 | Called `aqb2bu` an "open backlog" item and instructed adding `PUBRUN_RUN_MODE_OVERRIDE` to Sections 10.2 and 10.3 | Notes `aqb2bu` is `done` (closed by executed plan `87qr8h`), preserves existing `PUBRUN_RUN_MODE_OVERRIDE` rows verbatim, and adds only `NO_COLOR` and `PUBRUN_DEBUG` | Avoids duplicate edits and a guaranteed V-03 diff mismatch (PR-001). |
| E-03, E-05, S-01, Proposed changes, V-03/V-05 | Referred to "Sections 1-10 and 12-17" and "Section 17 HPC `meta_ref`" | Refers to Sections 3, 5, 6, 7, 9, 10 (E-03) and Sections 12, 14, 16, 18 (E-05), explicitly leaving Section 17 (`Ghost Mode`) untouched | `docs/functional_spec.md` Section 17 is Ghost Mode; HPC Parent-Child Hydration is Section 18 (PR-002). |
| E-01, E-05, S-01 | Listed hydrating callers without `res`/`cpu`/`mem` | Adds `pubrun res` (`resources`/`cpu`/`mem`) to both `docs/hpc.md` and `docs/functional_spec.md` Section 18.3 | `src/pubrun/report/diagnostics.py::print_resources_report` calls `hydrate_manifest` (PR-003). |
| E-03, E-04 -> E-03, E-05, E-04, E-06 | Two dense E-items bundling 11 unrelated sections and 16 CLI subsections | Four focused E-items assigned via `aw ipd sync --apply` with linear dependencies on `docs/functional_spec.md` (`E-03 -> E-05 -> E-04 -> E-06`) | Right-sizing for modest executors (PR-005). |
| Required tests, V-01..V-06 | Unspecified dash/link checks and no test command for `docs/research-use.md` | Exact runnable Python dash, link/anchor, and CLI-coverage checks, single-quoted negative `grep` commands with pre-execution baselines, `TestCitationConsistency` pytest command, and heading invariant | Makes every V-item falsifiable and prevents anchor breakage (PR-006). |
| E-05 Section 14.1, 12.3, 16; E-04 Section 11 | Omitted seven-function `on_inactive_annotate`, `status --utc`/filters, `clean` filters, `show config`, `PUBRUN_IMPORT_MODE` in `--info`, and Section 12.3 optional files | Adds exact symbol-backed specifications for each | Complete alignment with `src/pubrun/` and siblings `pqcx6o` and `dd7noz` (PR-004, PR-008). |
| Approval gate items 1-5 | Stop-style "modify only" fence; unconditional `aw ipd finalize`; omitted never-claim-without-output clause | Scope-declaration wording with `--scope-reason`/`--scope-ack`, explicit validation-honesty rule, and conditional runner/executor finalize ownership | Matches repository execution contract and sibling plans (PR-007). |
| Scope check, Spec / documentation sync, Deferred | Minimal one-liners without sibling owners or Requirement 12 assessment | Names sibling owners (`0cjiv5`, `pqcx6o`, `dd7noz`, `77pdvl`, `2uwuiu`), `87qr8h`/`aqb2bu`, disjointness, and Requirement 12 exemption; notes deferred repo-wide dash sweep | Clear coordination and traceability (PR-009). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (three documentation paths), 4 E-items in 2 task groups at review start, `- Kind: child`, Set `doc-audit` sibling Scope-Paths, and other plans touching these paths (`87qr8h` already executed).

1. No: documentation only. No runtime contract, CLI option, output format, or JSON Schema changes; `docs/functional_spec.md` is synchronized to match already-shipped code and `schemas/manifest.schema.json`.
2. No: touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox. E-01 and E-05 document `[report].meta_ref_allowed_dirs` and `allow_external_meta_ref` security policy, so accuracy was verified against `src/pubrun/report/utils.py`.
3. Somewhat: three documentation files, and pre-review E-03 bundled 11 topics across ~700 lines of `docs/functional_spec.md`.
4. Yes: all three paths are declared in `- Scope-Paths:`.
5. No: documentation edits are reversible with `git revert`.

AW-TIER: standard

### Step R1

- Checked every material citation against live repository code, schema, and tests:
  - `src/pubrun/report/utils.py::HYDRABLE_SECTIONS`: 7 sections (`hardware`, `process`, `python`, `packages`, `environment`, `git`, `host`). `hydrate_manifest_with_report` resolves relative `meta_ref` against `Path(manifest_path).parent`, checks `.json` extension and `_is_meta_ref_allowed()` before existence checks.
  - `src/pubrun/report/meta_snapshot.py::generate_meta_snapshot`: captures 6 sections (`hardware`, `python`, `packages`, `git`, `environment`, `host` — not `process`).
  - `hydrate_manifest` / `hydrate_manifest_with_report` callers across `src/pubrun/`: `report/diagnostics.py::print_report` (`show`/`report`), `report/diagnostics.py::print_resources_report` (`res`/`resources`/`cpu`/`mem`), `__main__.py::_run_methods` & `_run_methods_aggregate` (`methods`), `__main__.py::_run_inspect` (`inspect`), `__main__.py::_run_rerun` (`rerun --preflight`), `__main__.py::_run_diff` (`diff`), `core.py::diff` (Python `pubrun.diff()`), and `tui/widgets/{actions,details,diff}.py` (TUI).
  - `src/pubrun/capture/filesystem.py::get_filesystem`, `src/pubrun/capture/resources.py::ResourceWatcher` (`_get_rss_windows` Win32 `K32GetProcessMemoryInfo`/`psapi.GetProcessMemoryInfo` via `ctypes` + `wmic` fallback; `_get_linux_child_pids` walking `/proc/<pid>/task/<tid>/children`; `_poll_tree_cpu` Linux-only `/proc/<pid>/stat` jiffy deltas; `poll_timeout`, `system_metrics`, `peak_tree_cpu_percent`, `system_memory`, `load_average`, `system_iowait_pct`, `io_counters`, `capture_state`), `src/pubrun/report/diagnostics.py::print_resources_report`, `src/pubrun/report/reproducibility.py`, and `src/pubrun/report/checks.py::live_findings`.
  - `benchmarks/submit_bench.sh` (queries `sinfo -h -t idle -o "%n"`, pins via `--nodelist` when idle nodes exist, else unpinned) vs `benchmarks/submit_bench_{pbs,lsf,sge}.sh` (default queue, scheduler places job); `src/pubrun/__main__.py::_run_bench` (requires source checkout `benchmarks/harness.py`, Slurm submit-and-wait `--wait-timeout`, `--submit-file`).
  - `src/pubrun/capture/invocation.py::get_invocation` (`sys.argv` heuristic into `invocation.inputs`), `examples/` (`00_auto_start.py` through `12_external_file_provenance.py`, 13 numbered files), and `tests/test_cli.py::TestCitationConsistency::test_doi_agrees_across_surfaces` (reads `docs/research-use.md`, passed 4/4 in 0.98s).
  - `src/pubrun/core.py`: `_is_pubrun_cli_invocation` (`pubrun`/`pubrun.exe`/`pbr`/`pbr.exe`, `pubrun.__main__`, `__main__.__spec__.name`, `runpy` frames), `_handle_inactive` (7 callers: `annotate`, `phase`, `report`, `artifact`, `register_file`, `register_input`, `register_output`), `_classify_exit_outcome` / `_stop_for_exit`, `_should_log_pubrun_print`, `diff(run_dir_a, run_dir_b, ignores=None)`, `register_file` (`role` in `("input", "output", "input_output")`).
  - `src/pubrun/config.py::profile_deprecation_notice` (`profile_deprecated`), `src/pubrun/resources/default.toml` (`[report]`, reserved `[logging].write_summary`), `src/pubrun/report/output.py::debug_enabled` (`PUBRUN_DEBUG`, `NO_COLOR`), `src/pubrun/tracker.py::Run.__init__` (`<output_dir>/pubrun-.../`), `schemas/manifest.schema.json` (`$defs.status_value` includes `"timeout"`, `"pending"`), and all `.emit(` sites in `src/pubrun/` (`phase_start`, `phase_end`, `annotation`, `resource_sample`, `profile_saved`, `input_dataset`, `output_artifact`, `mixed_dataset`, `warning`).
  - Live `python3 -m pubrun --help` and `src/pubrun/__main__.py`: 20 visible primary commands (`bench`, `cite`, `clean`, `combined`, `cpu`, `diff`, `feedback`, `init`, `inspect`, `mem`, `meta`, `methods`, `report-bug`, `rerun`, `res` [alias `resources`], `run`, `self-check`, `show`, `status`, `ui` [aliases `tui`, `gui`]) plus hidden `report`, deprecated `--show-config`, `_show_info`, `_run_tests`, global `--version`/`--no-color`, and `pbr`.
  - `.aw/records/backlog/done/20261125-aqb2bu-01-aqb2bu-document-pubrun-run-mode-override-in-functional-sp.backlog.md`: `Status: done` (closed by executed plan `87qr8h`); `docs/functional_spec.md` lines 382 and 388 already contain `PUBRUN_RUN_MODE_OVERRIDE`.
  - `docs/functional_spec.md` headings: Section 17 (line 748) is Ghost Mode; Section 18 (line 764) is HPC Parent-Child Hydration.
- Drift found: PR-001 (`aqb2bu` already done), PR-002 (Section 17 vs Section 18), PR-003 (`res`/`cpu`/`mem` hydration caller), PR-004 (10 omitted commands vs 8 + `resources` alias + `show config`/`--info`/`status`/`clean`), PR-008 (seven-function `on_inactive_annotate` and Section 12.3 optional files).

### Step R2

- Checked: E/V bijection (6 E-items and 6 V-items after `aw ipd sync --apply`); `- Scope-Paths:` disjoint from Set `doc-audit` siblings (`0cjiv5`, `pqcx6o`, `dd7noz`, `77pdvl`, `2uwuiu`) and from executed plan `87qr8h`; `- Item-Dependencies: none`; concrete, falsifiable commands in every V-item; inbound anchor check (`docs/research-use.md:15` -> `hpc.md#where-pubrun-fits-alongside-mlflow-weights-and-biases-and-dvc`, `docs/cli.md:248` -> `hpc.md#diagnosing-a-finished-run`, zero inbound anchors into `docs/functional_spec.md` or `docs/research-use.md`); and zero em/en dashes in existing headings across all three files.
- No V-item demands an unreachable runtime observation; all V-items inspect diffs, negative greps, link/dash/CLI-coverage scripts, `sanitize_paths.py`, and `TestCitationConsistency`.

### Step R3

- Checked: the plan modifies no security, auth, or sandbox code. E-01 and E-05 document `[report].meta_ref_allowed_dirs` and `[report].allow_external_meta_ref` security policy; verified against `src/pubrun/report/utils.py::_is_meta_ref_allowed` and `hydrate_manifest_with_report` that `.json` extension and directory allowlist checks run before file existence probes, and that the recommended HPC workflow uses the directory allowlist (`meta_ref_allowed_dirs`) rather than defaulting to `allow_external_meta_ref = true`.
- `python3 scripts/sanitize_paths.py --check --all` exits `0` on the current tree.

### Step R4

- Checked: rubric A through F, right-sizing, and spec/documentation sync.
- Right-sizing: split pre-review E-03 (11 topics across ~700 lines) into E-03 and E-05, and pre-review E-04 (existing Section 11 fixes plus 10 new commands) into E-04 and E-06 via `aw ipd sync --apply`, with clean linear dependencies on `docs/functional_spec.md` (`E-03 -> E-05 -> E-04 -> E-06`).
- Test coverage: `tests/test_cli.py::TestCitationConsistency` reads `docs/research-use.md`; added to Required tests and V-02 (passes 4/4).
- Spec and documentation sync names all five sibling owners in Set `doc-audit` plus executed plan `87qr8h`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | coordination | `.aw/records/backlog/done/20261125-aqb2bu-01-aqb2bu-document-pubrun-run-mode-override-in-functional-sp.backlog.md` `- Status: done`; `docs/functional_spec.md:382,388` | Goal, Project conventions, E-03, and V-03 treated `aqb2bu` as an open backlog item and demanded adding `PUBRUN_RUN_MODE_OVERRIDE` to Sections 10.2 and 10.3, even though executed plan `87qr8h` already landed both locations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Goal, Project conventions, E-03, V-03, and Spec sync to reflect `aqb2bu`/`87qr8h` completion, preserve existing `PUBRUN_RUN_MODE_OVERRIDE` text verbatim, and add only `NO_COLOR` and `PUBRUN_DEBUG`. |
| PR-002 | HIGH | IN-SCOPE | evidence | `docs/functional_spec.md:748` (`## 17. Ghost Mode`) vs `docs/functional_spec.md:764` (`## 18. HPC Parent-Child Hydration`) | E-03, S-01, Proposed changes, and V-03 cited Section 17 for HPC `meta_ref` hydration. Section 17 is Ghost Mode; HPC Parent-Child Hydration is Section 18 (and 18.5 already covers `[report]` policy). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected all references to Section 18 (`18.2` and `18.3`, cross-referencing `18.5`), and explicitly protected Section 17 (`Ghost Mode`) in E-05 and V-05. |
| PR-003 | MEDIUM | UNDER-SCOPE | completeness | `src/pubrun/report/diagnostics.py::print_resources_report:1311` calls `hydrate_manifest` | E-01 and E-03 omitted `pubrun res` (`resources`/`cpu`/`mem`) from the list of commands that hydrate `meta_ref`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `pubrun res` (`resources`/`cpu`/`mem`) to the hydrating caller lists in E-01, E-05, S-01, V-01, and V-05, matching sibling `dd7noz`. |
| PR-004 | MEDIUM | IN-SCOPE | correctness | `python3 -m pubrun --help`; `src/pubrun/__main__.py::main` lines 2806-3188; `_show_info` lines 2505-2544 | Concern, E-04, S-05, and V-04 counted 8 omitted primary subcommands (actual count is 10: `init`, `inspect`, `self-check`, `bench`, `res`, `cpu`, `mem`, `ui`, `report-bug`, `feedback`), omitted the `resources` alias, omitted `show config` / `status --utc` / `status` & `clean` filters, and said `--info` prints no env vars (it prints `PUBRUN_IMPORT_MODE` when set). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated counts to 10 omitted primary subcommands (20 total visible), added `resources`, `show config`, `status --utc`/filters, `clean` filters, accurate `--info` behavior, and a live `pubrun --help` coverage check in V-06. |
| PR-005 | MEDIUM | IN-SCOPE | right-sizing | Pre-review E-03 (11 distinct topics across ~700 lines) and E-04 (existing Section 11 fixes + 10 new commands) | Bundling so many unrelated sections into two E-items risked dropped sub-edits and coarse V-item verification for a modest executor. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split E-03 into E-03 and E-05 and E-04 into E-04 and E-06 via `aw ipd sync --apply`, with linear dependencies `E-03 -> E-05 -> E-04 -> E-06` and 1:1 falsifiable V-items. |
| PR-006 | MEDIUM | IN-SCOPE | evidence | Pre-review Required tests and V-01..V-04 ("zero-dash check ... exiting 0", "link/anchor check", missing `TestCitationConsistency`) | Validation checks lacked runnable commands, implied a grep zero-dash check exits 0, omitted `tests/test_cli.py::TestCitationConsistency` (which reads `docs/research-use.md`), and lacked negative `grep` checks and a heading invariant. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added runnable Python dash, link/anchor, and CLI-coverage scripts, single-quoted negative `grep` checks with pre-execution baselines, `TestCitationConsistency` in V-02, and a heading invariant protecting inbound anchors. |
| PR-007 | MEDIUM | IN-SCOPE | execution contract | `## Approval and execution gate` items 2, 3, and 5 pre-review | Item 2 used stop-style "modify only" wording, item 3 omitted the never-claim-without-output clause, and item 5 did not specify conditional runner/executor ownership or forbid hand-run `git mv`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote items 1 to 5 to match the repository execution contract and sibling plans `0cjiv5`, `pqcx6o`, and `dd7noz`. |
| PR-008 | MEDIUM | UNDER-SCOPE | completeness | `src/pubrun/core.py::_handle_inactive` (7 callers); `src/pubrun/tracker.py` `.pubrun.lock`; `src/pubrun/core.py::report`, `artifact` | E-03/Section 14.1 did not update `on_inactive_annotate` beyond `annotate()` (all 7 functions obey it), and Section 12.3 omitted `profile-<phase>.prof`, `report()`/`artifact()` files, and transient `.pubrun.lock`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added all seven `on_inactive_annotate` functions and Section 12.3 optional files to E-05 and V-05. |
| PR-009 | LOW | IN-SCOPE | coordination | `## Scope check` and `## Spec / documentation sync` pre-review | Omitted sibling Set owners, disjointness confirmation, executed `87qr8h`/`aqb2bu` note, deferred repo-wide dash sweep, and Requirement 12 diagram assessment. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `## Scope check`, `## Spec / documentation sync`, and `## Deferred / out of scope` with complete cross-plan ownership and Requirement 12 rationale. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` (rejected: three reference/spec docs with security policy and 20-command CLI surface); `complex` (rejected: no runtime code, schema, or contract changes) | Step T answers | yes |
| D-2 | How to handle `PUBRUN_RUN_MODE_OVERRIDE` / backlog `aqb2bu`? | Preserve existing Sections 10.2 and 10.3 text from executed plan `87qr8h` verbatim and add only `NO_COLOR` and `PUBRUN_DEBUG` | Rewrite the existing rows (rejected: unnecessary churn against already-verified `87qr8h` text); drop Section 10.3 edit entirely (rejected: `NO_COLOR` and `PUBRUN_DEBUG` are still missing) | `.aw/records/backlog/done/20261125-aqb2bu-01-aqb2bu-document-pubrun-run-mode-override-in-functional-sp.backlog.md` and `docs/functional_spec.md:382,388` | yes |
| D-3 | Split `wjsccu` into more child plans or split E-03/E-04 in place? | Split E-03 into E-03/E-05 and E-04 into E-04/E-06 inside `wjsccu` (6 E-items total) | Split into separate child plans (rejected: all four `functional_spec.md` items edit the same file, so separate children would introduce merge conflict risk) | `IPD-Z603` guidance (6 E-items is near 5 and passes `aw ipd lint` clean); `docs/functional_spec.md` single-file cohesion | yes |

### Step S5

- Checked: `## Open questions` is `None.` Repository evidence resolved every question raised during review (D-1 to D-3). Every finding (PR-001 through PR-009) is `FIXED`, so no finding requires escalation and no open question is added. Every decision is reversible (`Reversible: yes`). The lane outcome JSON carries `questions: []`.

### Step S6

- Checked: Round 1 added E-05 and E-06 with V-05 and V-06 via `aw ipd sync --apply`, so Rule 1 required a second pass. Re-read the entire revised plan and verified:
  - Proposed changes 1 to 6 map 1:1 to E-01, E-02, E-03, E-05, E-04, and E-06.
  - Dependency chain on `docs/functional_spec.md` is strictly linear (`E-03 -> E-05 -> E-04 -> E-06`); E-01 and E-02 are independent (`Depends on: none`); no `E-NEW` remains.
  - Every stale reference (`Sec 17`, `aqb2bu` open, `8 missing/omitted`) was swept across Concern, Goal, E-items, Project conventions, Findings, Proposed changes, Scope check, Spec sync, and V-items.
  - Every embedded validation command (dash check, link/anchor check, CLI coverage check, negative greps, `sanitize_paths.py`, `TestCitationConsistency`) was run on the current tree and verified for syntax and expected baseline output.
  - `aw ipd lint --phase review-finalize --agent` exits `0` (`outcome: clean`).

AW-REVIEW: DONE
