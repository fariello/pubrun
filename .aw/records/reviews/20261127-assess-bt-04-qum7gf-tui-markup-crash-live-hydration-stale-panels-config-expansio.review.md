# Review findings: ipd qum7gf

- Subject-Id: qum7gf
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-04-qum7gf-tui-markup-crash-live-hydration-stale-panels-config-expansio.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`). Expanded acronyms (`TUI`, `TOML`, `URL`, `CI`, `QA`, `CLI`) and operating-system phrasing on first use, standardized `path::Symbol` code citations, and updated the Mermaid `flowchart` to match `E-01` and `E-02` (`PR-004`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### TUI live-run completion and empty-run refresh flow` | Flowchart omitted `actions-view.display_run(None)`/`clear()` method names and narrowed non-running statuses to `completed/failed` | Named exact reset calls (`details-view.show_onboarding()`, `logs-view.clear()`, `resources-view.clear()`, `actions-view.display_run(None)`) and checked `refreshed.status == STATUS_RUNNING?` | Keep Mermaid flowchart consistent with `E-01` and `E-02` (`PR-004`) |
| `Concern`, `E-03`, `E-04`, `E-05`, `## Project conventions discovered`, `## Findings`, `## Deferred / out of scope`, `V-05` | Left `TUI`, `TOML`, `URL`, `CI`, `QA`, `CLI`, and `3-OS` unexpanded and used mixed citation style (`details.py::refresh_live_metrics`) | Expanded acronyms on first use and standardized `path::Symbol` citations | Satisfy technical writing standard requirement 1 and spec Section 11.1 (`PR-004`) |
| `E-02`, `## Findings` (`BUG-U2`/`TEST-U2`) | Omitted resetting `select_widget.value = _SELECT_EMPTY_VALUE` in `LogViewer` and restoring default prompt in `RunResourcesView`; stated `refresh_live_metrics` had 0% coverage | Specified full reset behavior in `LogViewer.clear()` and `RunResourcesView.clear()`, and corrected `BUG-U2`/`TEST-U2` finding to state the running-to-terminal transition path had 0% coverage | Prevent stale `Select` value reuse and keep finding claims factually accurate (`PR-003`) |
| `E-03`, `E-04`, `V-03`, `V-04`, `V-05` | Targeted only `save_settings()` (leaving `load_settings()` expanding `#cfg-output-dir` and `save_settings()` comparing raw vs expanded paths), omitted `PUBRUN_OUTPUT_DIR` fixture cleanup and precedence/re-save tests, omitted `"running"` status filter in `TEST-U5`, and omitted `.pubrun.lock` removal in `BUG-U2` | Updated `E-03` to cover both `load_settings()` and resolved-path comparison in `save_settings()`; updated `E-04` and `V-03..V-05` to isolate `PUBRUN_OUTPUT_DIR`, test precedence/re-save, include `"running"` in `TEST-U5` so the `STATUS_RUNNING` guard executes, remove `.pubrun.lock` in `BUG-U2`, and guard Windows symlink creation in `TEST-U1` | Fix portable-path clobbering and spurious refresh bugs (`PR-001`) and guarantee every targeted security/coverage branch executes cleanly (`PR-002`) |
| `## Approval and execution gate` | Omitted `--scope-reason`/`--scope-ack`, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize qum7gf` ownership | Tightened all five execution-contract clauses to match `r2-executability.md` and `s7-finalize.md` | Satisfy mandatory execution-contract rules (`PR-004`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 4`, `- Scope-Paths:` (7 files: `actions.py`, `details.py`, `app.py`, `viewer.py`, `resources.py`, `config.py`, `tests/test_tui_widgets.py`), 5 E-items in 2 task groups.

1. Yes: modifies TUI configuration loading/saving contracts (`$VAR`/`~` preservation and `PUBRUN_OUTPUT_DIR` precedence alongside sibling `BUG-U5` plans `wcjdbu` and `kk83rk`), `PubrunTUIApp.action_refresh_all` empty-run state, `LogViewer`/`RunResourcesView` reset APIs, and `ActionsPanel`/`RunDetailsView` rendering/hydration behavior.
2. No: does not touch private-data redaction, git commits, worktree isolation, merges to main, or sandbox guards (adds test coverage for archive symlink/traversal and bulk-prune safety guards).
3. Yes: 5 E-items across 2 task groups spanning 6 TUI modules and `tests/test_tui_widgets.py` across 7 findings (`BUG-U1`, `BUG-U2`/`TEST-U2`, `BUG-U4`, `BUG-U5`, `TEST-U1`, `TEST-U5`, `TEST-U8`).
4. Yes: `- Scope-Paths:` explicitly lists all 7 modified files.
5. Yes: mistakes in `ConfigPanel.load_settings()`/`save_settings()` can silently overwrite portable `$VAR`/`~` values in `.pubrun.toml` or break `PUBRUN_OUTPUT_DIR` precedence, and an unreached `STATUS_RUNNING` branch in `TEST-U5` would leave bulk-prune safety partially unverified.

AW-TIER: complex

### Step R1

- Checked: every file, symbol, template, and test citation against the repository: `src/pubrun/tui/widgets/actions.py` (`ActionsPanel.display_run`, `_preview_prune_candidates`, `archive_selected_run`, `handle_deletion_result`, `run_bulk_prune`), `src/pubrun/tui/widgets/details.py` (`RunDetailsView.show_onboarding`, `display_run`, `refresh_live_metrics`, `update_general_pane`, `update_packages_pane`, `update_subprocesses_pane`), `src/pubrun/tui/app.py` (`PubrunTUIApp.on_mount`, `_select_run`, `_render_tab`, `update_output_dir`, `action_refresh_all`), `src/pubrun/tui/widgets/viewer.py` (`LogViewer.display_run_logs`, `on_button_pressed`), `src/pubrun/tui/widgets/resources.py` (`RunResourcesView.display_run`), `src/pubrun/tui/widgets/config.py` (`_toml_value`, `dict_to_toml`, `ConfigPanel.load_settings`, `save_settings`), `src/pubrun/tui/widgets/sidebar.py`, `src/pubrun/tui/widgets/diff.py`, `src/pubrun/report/methods.py` (`generate_report`), `src/pubrun/report/templates.py` (`MARKDOWN_TEMPLATE`), `tests/test_tui_widgets.py`, `tests/test_tui_bugs.py`, `tests/test_tui.py`, and `docs/`.
- Verified: `MARKDOWN_TEMPLATE` literally contains `[Computer software]` and renders `git.remote_url` (`methods.py:284`, `templates.py:24,27`); `tests/test_tui_widgets.py:1183-1229` already covers non-transition branches of `refresh_live_metrics` (`PR-003`); `ConfigPanel.load_settings()` expands `#cfg-output-dir` via `resolve_config()` (`PR-001`); `ActionsPanel` default `#input-clean-status` excludes `"running"` upstream of `_preview_prune_candidates` line 373 (`PR-002`); `docs/` contains no references to these internal TUI widget methods.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability, non-tautological evidence, and execution-gate contract.
- Verified: all `V-*` items demand concrete diffs, named pytest output, coverage confirmation, and 3-OS `mypy` output reachable by construction; `PR-002` ensured `V-05`'s coverage demand on `actions.py` prune guards is actually reachable by including `"running"` in `TEST-U5`; `PR-004` completed all five execution-gate clauses.

### Step R3

- Checked: security and safety guards in `ActionsPanel.archive_selected_run` (symlink exclusion, `resolved_zip.parent != resolved_archive`, `safe_stem` sanitization, `relative_to(resolved_run_dir)`), `ActionsPanel._preview_prune_candidates` (`STATUS_RUNNING` and `lock_state == "remote"` exclusion), `ActionsPanel.display_run` (Textual markup injection safety via `rich.text.Text`), and `ConfigPanel.save_settings` (atomic write, TOML validation, regex validation, no `PUBRUN_OUTPUT_DIR` leak into `.pubrun.toml`).
- Verified: `PR-001` prevents `PUBRUN_OUTPUT_DIR` from being persisted accidentally into `.pubrun.toml`; `PR-002` ensures both archive security guards and both bulk-prune safety guards are genuinely exercised in tests.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified: `PR-001` closes both the `load_settings()` clobbering bug and the raw-vs-expanded refresh comparison bug; `PR-002` closes ambient `PUBRUN_OUTPUT_DIR` test pollution, unreachable prune guard coverage, and missing precedence/re-save tests; `PR-003` closes `LogViewer` `Select.value` reset and `RunResourcesView` prompt restoration; `## Spec / documentation sync` is truthfully `N/A`.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `ActionsPanel._preview_prune_candidates` `STATUS_RUNNING` branch being shadowed by default `#input-clean-status` (`PR-002`) and stale `Select.value` in `LogViewer.clear()` (`PR-003`).
  2. Testing and regression: caught missing `PUBRUN_OUTPUT_DIR` cleanup in `_isolated_config`, missing `PUBRUN_OUTPUT_DIR` precedence and re-save tests, missing `.pubrun.lock` removal step in `BUG-U2` test, and Windows symlink guard in `TEST-U1` (`PR-002`).
  3. UI / UX: confirmed `RunResourcesView.clear()` restores the default helpful prompt and `ConfigPanel` preserves portable `$VAR`/`~` text in `#cfg-output-dir` (`PR-001`, `PR-003`).
  4. Architect: confirmed `resolve_config()` remains the single source of truth for `$VAR`/`~` expansion and `PUBRUN_OUTPUT_DIR` precedence via `updater(None)` (`PR-001`).
  5. Software engineer: caught `load_settings()` overwriting raw local `core.output_dir` and raw-vs-expanded comparison in `save_settings()` (`PR-001`).
  6. Power user: verified `PUBRUN_OUTPUT_DIR` and `--dir` pinning both survive `ConfigPanel.save_settings()` without corrupting portable `.pubrun.toml` paths (`PR-001`, `PR-002`).
  7. Novice: verified empty-run state clears all four run tabs cleanly without stale deleted-run artifacts (`PR-003`).
  8. Stakeholder: confirmed full coverage of all four TUI bugs and all three TUI testing gaps assigned to Order 04 by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 2 task groups, 7 Scope-Paths, already Order 04 of 10-child Set `assess-bt`).
- Confirmed: each E-item is small, focused, and executable in one pass (`E-01` 2 tiny widget fixes, `E-02` empty-run panel reset, `E-03` `ConfigPanel` load/save fix, `E-04` headless Textual tests, `E-05` validation). No further splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt`: orchestrator `n6250e` (Order 00) and sibling children `wcjdbu`, `ndobra`, `thbepl`, `kk83rk`, `n39jh9`, `dqaj9a`, `kgoymu`, `4eo4z2`, and `37sth0`.
- Verified: all 7 `Scope-Paths` in `qum7gf` are strictly disjoint from all nine sibling children and pending plans `8o6o83` and `3u1xgk`; `BUG-U5` TUI half (`ConfigPanel` delegating to `resolve_config()` via `updater(None)`) aligns cleanly with `wcjdbu` (`status._resolve_output_dir` expansion) and `kk83rk` (CLI `--dir` expansion), with no ordering dependency required (`- Item-Dependencies: none`).

### Step S5

- Checked: `## Open questions` contains `None.`. All four findings (`PR-001` through `PR-004`) had `Low` overall Remediation Risk, were settled by repository code and test evidence, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r4-engineering.md` A (Correctness) / `r2-executability.md` | `src/pubrun/tui/widgets/config.py::ConfigPanel.load_settings:256-274`, `src/pubrun/tui/widgets/config.py::ConfigPanel.save_settings:324-381` | `E-03` targeted only `save_settings()`, but `load_settings()` (called on mount and inside `save_settings()`) populates `#cfg-output-dir` from expanded `resolve_config()` (clobbering portable `$VAR`/`~` and leaking `PUBRUN_OUTPUT_DIR` into `.pubrun.toml`), and `save_settings()` line 374 compares raw `new_output_dir` against expanded `prev_output_dir` (causing spurious refreshes on unrelated saves). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-03` to prefer raw `str` `core.output_dir` from `load_local_config()` inside `load_settings()`, compare resolved `core.output_dir` before vs after `load_settings()` in `save_settings()`, and call `updater(None)` on resolved-dir change when not pinned (recommendation strength: `very strong`). |
| PR-002 | HIGH | UNDER-SCOPE | `r4-engineering.md` E (Testing and verification) / `r2-executability.md` | `src/pubrun/tui/widgets/actions.py::ActionsPanel.compose:296-299`, `ActionsPanel._preview_prune_candidates:361-379`, `tests/test_tui_widgets.py::_isolated_config:40-48`, `tests/test_tui_widgets.py::TestBulkPruneConfirmationAndStderr:1284-1361` | Default `#input-clean-status` excludes `"running"` upstream of `_preview_prune_candidates` line 373 (leaving the `STATUS_RUNNING` guard uncovered under `V-05`); `E-04` omitted `PUBRUN_OUTPUT_DIR` precedence and second-save `$VAR` preservation tests; `_isolated_config` did not clear ambient `PUBRUN_OUTPUT_DIR`; `BUG-U2` test omitted removing `.pubrun.lock`; `TEST-U1` omitted Windows symlink-restriction handling. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-04` and `V-03..V-05` to clear `PUBRUN_OUTPUT_DIR` in `_isolated_config`, include `"running"` (or `""`) in `#input-clean-status` plus a >48h remote-locked run in `TEST-U5`, add `PUBRUN_OUTPUT_DIR` precedence and second-save preservation assertions in `BUG-U5`, explicitly remove `.pubrun.lock` in `BUG-U2`, and guard Windows symlink creation in `TEST-U1` (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r4-engineering.md` A, F (Correctness, UX) / `r1-references.md` | `src/pubrun/tui/widgets/viewer.py::LogViewer:78-120,145-157`, `src/pubrun/tui/widgets/resources.py::RunResourcesView:115-123`, `tests/test_tui_widgets.py::TestRunDetailsStates.test_refresh_live_metrics_reloads_running_run_only:1183-1230` | `E-02` did not specify resetting `select_widget.value = _SELECT_EMPTY_VALUE` in `LogViewer.clear()` or restoring the default prompt in `RunResourcesView.clear()`, and `## Findings` row `BUG-U2`/`TEST-U2` inaccurately claimed `refresh_live_metrics` had 0% coverage (only the running-to-terminal transition path had 0% coverage). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `select_widget.value = _SELECT_EMPTY_VALUE` under `prevent(Select.Changed)` in `LogViewer`, default prompt restoration in `RunResourcesView`, matching assertions in `E-04`/`V-02`, and corrected the `BUG-U2`/`TEST-U2` finding summary (recommendation strength: `strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `.aw/records/plans/pending/20261127-assess-bt-04-qum7gf-tui-markup-crash-live-hydration-stale-panels-config-expansio.ipd.md:1,5,28,30-39,70,80,89,96,114,127,169-178` | `## Approval and execution gate` omitted `--scope-reason`/`--scope-ack`, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize qum7gf` ownership; prose left `TUI`, `TOML`, `URL`, `CI`, `QA`, `CLI`, and `3-OS` unexpanded and used mixed citation style; Mermaid diagram did not name exact reset methods or generalize non-running status. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Tightened all five clauses of `## Approval and execution gate`, expanded acronyms on first use, standardized `path::Symbol` citations, and aligned the Mermaid flowchart with `E-01` and `E-02` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `qum7gf` | `complex` | `standard` | Order 04 of 10-child Set `assess-bt`; spans 6 TUI source modules plus `tests/test_tui_widgets.py` and modifies user-facing config load/save and run-hydration contracts; answers Yes to tier questions 1, 3, and 5 in `steps/t-tier.md`. | yes |
| D-2 | How `ConfigPanel` should preserve portable `$VAR`/`~` and detect effective `output_dir` changes (`PR-001`) | Read raw local `core.output_dir` string in `load_settings()` and compare resolved `core.output_dir` before vs after `load_settings()` in `save_settings()`, calling `updater(None)` on change | Patch only `save_settings()` without touching `load_settings()` | `src/pubrun/tui/widgets/config.py:256-274,324-381`, `src/pubrun/config.py::resolve_config:205-230`, and existing tests in `tests/test_tui_widgets.py:953-970,1052-1074,1711-1779`. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; every revision (`PR-001` through `PR-004`) was swept across front matter, Mermaid diagram, `E-01..E-05`, `## Findings`, `## Proposed changes`, `V-01..V-05`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
