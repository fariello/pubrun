# Review findings: ipd 8ebjeg

- Subject-Id: 8ebjeg
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, `Goal`, Mermaid flowchart, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal` and Mermaid flowchart | Single sentence mentioning fixed `BUG-13` as broken; flowchart omitted `LogViewer` and said `DiffView` "forwards depth" | Split `Goal` into two direct sentences accurately describing live defects plus `rerun_command` preservation; updated Mermaid flowchart to include `LogViewer`, `Select.NULL` depth fallback, and hydration warnings after clear | Technical writing requirements 2, 12(d), and 12(e) |
| Citations across `Goal`, `E-01`..`E-05`, `Findings`, `Proposed changes` | Bare module-dotted symbols (`tui.app.PubrunTUIApp.on_refresh_sidebar`, wrong `RunDetailsView.display_run`) | Standardized `path::Symbol` citations and corrected `RunDetailsView.update_general_pane` | `steps/p-proofread.md` Section 11.1 and factual accuracy |
| Acronyms (`TUI`, `GPU`, `TOML`) | Used unexpanded acronyms on first occurrence | Expanded acronyms on first occurrence | Technical writing requirement 1 |
| `## Approval and execution gate` | Missing honesty/never-push/scope-declaration clauses and vague manual move to `executed/` | Replaced with compliant 5-item Execution contract using `--scope-reason`/`--scope-ack`, HARD MUST pasted output rule, never-push, and conditional runner vs standalone `aw ipd finalize 8ebjeg` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, `src/pubrun/tui/app.py`, `src/pubrun/tui/widgets/actions.py`, `src/pubrun/tui/widgets/config.py`, `src/pubrun/tui/widgets/diff.py`, `src/pubrun/tui/widgets/details.py`, `src/pubrun/tui/widgets/viewer.py`, `src/pubrun/tui/widgets/sidebar.py`, `src/pubrun/tui/widgets/resources.py`, `src/pubrun/capture/hardware.py`, `schemas/manifest.schema.json`, `tests/test_tui.py`, live Textual `8.2.8` API probe, and sibling plans in Set `bugs-audit` (`jqqvkh`, `njn1up`, `r68o07`, `ihh27o`).

1. Yes: consumes `njn1up`'s `status.clean_runs` `ValueError` and `d`/`h`/`m`/`s` duration contract in Bulk Prune (`src/pubrun/tui/widgets/actions.py`), hardens `.pubrun.toml` persistence (`src/pubrun/tui/widgets/config.py`), and preserves `ActionsPanel.rerun_command` pinned by `tests/test_tui.py`.
2. Yes: `src/pubrun/tui/widgets/config.py` persists `[redaction]` settings to `.pubrun.toml` (guarding against `"Select.NULL"` corruption), and `src/pubrun/tui/widgets/actions.py` executes permanent directory deletion via `shutil.rmtree` and `clean_runs`.
3. No: bounded child 07 of 9 in Set `bugs-audit`, scoped to 6 TUI source files and one new test file across 5 focused E-items.
4. Yes: `- Scope-Paths:` explicitly lists all 7 modified files.
5. Yes: mistakes in `ActionsPanel` deletion or Bulk Prune could lose run data, mistakes in `ConfigPanel` corrupt `.pubrun.toml` and crash `pubrun ui` on startup, and following the unreviewed plan's `Select.BLANK` or `_rerun_command` instructions would crash Textual 8.2.8 and break `tests/test_tui.py`.

AW-TIER: complex

### Step R1

- Checked: Verified every cited file, symbol, Textual 8.2.8 API, schema field, existing test, and sibling plan against `src/pubrun/tui/app.py`, `src/pubrun/tui/widgets/{actions,config,diff,details,viewer,sidebar,resources}.py`, `src/pubrun/capture/hardware.py`, `schemas/manifest.schema.json`, `tests/test_tui.py`, orchestrator `jqqvkh`, prerequisite `njn1up`, and siblings `r68o07` and `ihh27o`. Live Python inspection of Textual `8.2.8` caught two BLOCKER defects: `Select.BLANK` inherits `textual.widget.Widget.BLANK == False` (not a `NoSelection` sentinel, so `getattr(Select, "BLANK", Select.NULL)` returns `False` and assigning `Select.BLANK` raises `InvalidSelectValueError`, `PR-001`), and `BUG-13` (`Static.renderable`) was already fixed via public `self.rerun_command` pinned by `tests/test_tui.py:374,390` (`PR-002`). Also caught misstated `DiffView` depth root cause (`depth=depth` is already passed; `value or "basic"` fails on truthy `Select.NULL`), unmentioned `LogViewer` `#btn-refresh-log` `Select.NULL` bug, `ConfirmDeleteModal.compose` + `handle_deletion_result` dual `None[:8]` crash, duplicated age parsing in `run_bulk_prune`, and wrong `RunDetailsView.display_run` citation (`PR-003`).

### Step R2

- Checked: Verified structural author preflight (`aw ipd lint --phase author --agent` exit 0, `clean`, 0 findings), 1:1 `E-01`..`E-05` to `V-01`..`V-05` bijection (co-locating per-widget regression tests in `E-01`..`E-04` and keeping `E-05` for full `tests/test_tui_bugs.py`, `tests/test_tui.py`, and `pytest -q` verification), `- Scope-Paths:` completeness (all 7 files), `- Item-Dependencies: executed:njn1up` matching orchestrator `jqqvkh`, concrete non-tautological behavioral evidence in every `V-*` (all reachable by construction via Textual `app.run_test()` Pilot and `pytest`), and `## Approval and execution gate` (fixed in `PR-004`).

### Step R3

- Checked: Verified `ConfigPanel` never writes `"Select.NULL"` into `[redaction].representation` (which would break secret redaction/startup on next launch), `ActionsPanel` Bulk Prune delegates directly to `njn1up`'s fail-closed `clean_runs` so invalid ages delete nothing and running jobs remain protected, `ConfirmDeleteModal` still requires typing `"yes"` before `shutil.rmtree`, and `RunDetailsView.update_general_pane` escapes bracketed GPU strings via `_escape_markup`.

### Step R4

- Checked: Evaluated engineering rubric sections A (version-safe `_is_select_empty` avoiding `Widget.BLANK = False`, dual `None` guards in `ConfirmDeleteModal` + `handle_deletion_result`, clearing `self.run_info` after deletion), C (delegating Bulk Prune duration parsing directly to `status.clean_runs(older_than=...)` instead of duplicating parser logic, reusing `@on(RefreshSidebar)` and `_escape_markup`), D (preserving `ActionsPanel.rerun_command` pinned by `tests/test_tui.py:374,390`, keeping `DiffView` compatible with `r68o07`'s additive `path_split` keys), E (live Textual Pilot tests in `tests/test_tui_bugs.py` plus `tests/test_tui.py` and full `pytest -q`), F (KISS, clear error/warning toasts, zero silent config corruption), right-sizing (5 focused E-items eliminating `V-01`..`V-04` test-ordering inversion with zero `IPD-Z603` advisories), and `## Spec / documentation sync` (substantiated no-doc-change claim against `docs/cli.md`, `docs/functional_spec.md`, and `njn1up`).

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught `Select.BLANK == False` crash/misclassification in Textual 8.2.8 (`PR-001`), dual `None[:8]` crash in `ConfirmDeleteModal.compose` + `handle_deletion_result` (`PR-003`), `LogViewer` `#btn-refresh-log` `Select.NULL` bug (`PR-003`), and `DiffView` blank-depth `Select.NULL` fallback bug (`PR-003`).
  2. **Testing and regression expert:** Caught `self._rerun_command` breaking `tests/test_tui.py:374,390` (`PR-002`), co-located per-widget tests inside `E-01`..`E-04`, and required `pytest tests/test_tui_bugs.py tests/test_tui.py -v` plus full `pytest -q` in `V-05` (`PR-005`).
  3. **UI / UX expert:** Verified hydration warnings survive `output.clear()` in `DiffView`, unknown config values notify clearly without crashing startup, deleting a run clears stale selection in `ActionsPanel`, and GPU models display instead of `None` (`PR-003`).
  4. **Systems and software architect:** Eliminated duplicated age parsing in `ActionsPanel.run_bulk_prune` by delegating `older_than` directly to `status.clean_runs` (`njn1up`), shared `_is_select_empty` cleanly across `config.py`/`diff.py`/`viewer.py`, and fixed nested message routing via `@on(RefreshSidebar)` (`PR-001`, `PR-003`).
  5. **Software engineer:** Fixed missing execution-contract clauses and vague manual-move wording in `## Approval and execution gate` (`PR-004`) and corrected `RunDetailsView.update_general_pane` citation (`PR-003`).
  6. **Sophisticated power user:** Confirmed Bulk Prune supports `m`/`s` durations alongside `d`/`h`/bare days via `njn1up`, `PUBRUN_PROFILE=standard` env var no longer crashes `pubrun ui`, and Refresh in `LogViewer` handles empty runs cleanly (`PR-001`, `PR-003`).
  7. **Complete novice:** Verified blank `DiffView` dropdowns show `"Please select both Run A and Run B"` instead of `"Cannot compare a run against itself"` or a crash, and updated the Mermaid diagram to match the text accurately (`PR-003`, `PR-006`).
  8. **Stakeholder:** Confirmed all 6 TUI audit bugs (`BUG-13`..`BUG-15`, `BUG-51`..`BUG-53`) plus `njn1up`'s Bulk Prune `ValueError` contract are cleanly resolved with zero regressions.

### Step R6

- Checked: Evaluated decomposition and conceptual density across `E-01`..`E-05`. `8ebjeg` is already child 07 of 9 in Set `bugs-audit`, scoped to 6 small TUI modules (`app.py` + 5 widgets) and `tests/test_tui_bugs.py` across 5 focused E-items with zero `IPD-Z603` advisories. No split into a separate Plan Set is needed.

### Step R7

- Checked: Verified alignment with Set `bugs-audit` orchestrator `jqqvkh`, prerequisite `njn1up` (Order 01), and siblings `r68o07` (Order 05) and `ihh27o` (Order 06). Confirmed `- Item-Dependencies: executed:njn1up` matches `jqqvkh`, `8ebjeg` fulfills `njn1up`'s deferred carrier obligation (`Carrier: 8ebjeg` for Bulk Prune `ValueError` handling), all 7 `- Scope-Paths:` remain completely disjoint from all 8 sibling child plans in Set `bugs-audit`, and `DiffView` remains compatible with `r68o07`'s additive `path_split` keys.

### Step S5

- Checked: Audited pre-existing `## Open questions` (`None`), `## Deferred / out of scope` (`None`), and all 6 review findings (`PR-001`..`PR-006`). All 6 findings had Low remediation risk and were fixed in place. Recorded reversible evidence-based decisions `D-1`..`D-4` below. Zero unresolved or blocking human questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | R1/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md:60-63,67,80,97`, live Textual `8.2.8` probe (`Select.BLANK is False` from `textual.widget.Widget.BLANK`; `Select.value = Select.BLANK` raises `InvalidSelectValueError`) | Plan treated `Select.BLANK` as an empty sentinel equivalent to `Select.NULL` and suggested assigning `Select.BLANK` as a fallback. On Textual 8.2.8, `Select` does not define `BLANK`; `getattr(Select, "BLANK", Select.NULL)` returns `Widget.BLANK` (`False`), causing `_is_select_empty` to misclassify `False`/`0` as empty and assigning `Select.BLANK` to crash with `InvalidSelectValueError`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `_is_select_empty` using `Select.__dict__.get("BLANK")` (never inheriting `Widget.BLANK = False`) and specified `Select.NULL` (never `Select.BLANK`) as the fallback value for unknown config values in `E-03`, `E-04`, `Project conventions`, `Proposed changes`, and `V-03` (`D-1`, recommendation strength: very strong). |
| PR-002 | BLOCKER | IN-SCOPE | R1/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md:53-55,86,96,133`, `src/pubrun/tui/widgets/actions.py:91,135,161,189`, `tests/test_tui.py:374,390` | `BUG-13` (`Static.renderable`) was already fixed on `main` using public attribute `self.rerun_command` (pinned by `tests/test_tui.py:374,390`). `E-02` instructed storing `self._rerun_command`, which would break `tests/test_tui.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `Goal`, `E-02`, `Project conventions`, `Findings`, `Proposed changes #2`, and `V-02` to preserve `self.rerun_command` intact and keep a Textual 8.x regression test in `tests/test_tui_bugs.py` (`D-2`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R1/R4.A | `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md:55,67,89-91,96,98`, `src/pubrun/tui/widgets/diff.py:82-97,120-149`, `src/pubrun/tui/widgets/viewer.py:91-102`, `src/pubrun/tui/widgets/actions.py:51-60,225-228,265-334`, `src/pubrun/tui/widgets/details.py:291-305` | `DiffView.run_difference` already passes `depth=depth` (the live bug is `value or "basic"` failing on truthy `Select.NULL`); `LogViewer` `#btn-refresh-log` shares the same `Select.NULL` bug as `on_select_changed`; `BUG-53` crashes in both `ConfirmDeleteModal.compose` and `handle_deletion_result`; `run_bulk_prune` duplicates incomplete age parsing instead of passing `older_than` to `clean_runs`; and `Findings` cited `RunDetailsView.display_run` instead of `RunDetailsView.update_general_pane`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected all four mechanisms and symbol citations across `E-02`, `E-04`, `Findings`, `Proposed changes`, and `V-02`/`V-04` (`D-3`, recommendation strength: very strong). |
| PR-004 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md:152-157`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | `## Approval and execution gate` omitted the resolved-open-questions precondition, `--scope-reason`/`--scope-ack` scope declaration, HARD MUST pasted-output honesty rule, never-push rule, and conditional runner vs standalone `aw ipd finalize 8ebjeg` ownership, and used vague manual-move wording. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract (recommendation strength: very strong). |
| PR-005 | MEDIUM | UNDER-SCOPE | R2/R4.Right-sizing/R4.Spec-doc-sync | `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md:48-75,115-117,127-150` | `V-01`..`V-04` demanded `pytest tests/test_tui_bugs.py -v` output before `E-05` created `tests/test_tui_bugs.py`, and `## Spec / documentation sync` gave an unsubstantiated `N/A`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Co-located per-widget regression tests inside `E-01`..`E-04`, dedicated `E-05`/`V-05` to `tests/test_tui_bugs.py` + `tests/test_tui.py` + full `pytest -q`, and substantiated `## Spec / documentation sync` against `docs/cli.md`, `docs/functional_spec.md`, and `njn1up` (`D-4`, recommendation strength: strong). |
| PR-006 | MEDIUM | IN-SCOPE | Check P/R1/Tech-Writing | `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md:22-40,48-98`, `.aw/system/workflows/technical-writing/technical-writing.md:29-62`, `.aw/system/workflows/plan-review/steps/p-proofread.md:19-28` | `Workflow history` was oldest-first, code references lacked `path::Symbol` format, acronyms (`TUI`, `GPU`, `TOML`) were unexpanded on first use, and the Mermaid diagram omitted `LogViewer` and inaccurately claimed `DiffView` did not forward depth. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reordered `Workflow history` newest-first, standardized `path::Symbol` citations, expanded acronyms on first use, and synchronized the Mermaid flowchart with the corrected text (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should `_is_select_empty` and `ConfigPanel.load_settings` handle empty `Select` sentinels on Textual 8.x? | Check `val is None or val == Select.NULL or ((blank := Select.__dict__.get("BLANK")) is not None and val == blank)`, and fall back to `Select.NULL` (never `Select.BLANK`) with a warning notification on unknown config values. | Use `getattr(Select, "BLANK", Select.NULL)` or assign `Select.BLANK` (inherits `Widget.BLANK == False` on Textual 8.2.8, misclassifying `False`/`0` and raising `InvalidSelectValueError`). | Live Textual `8.2.8` probe (`Select.__dict__`, `Widget.BLANK == False`, `Select.NULL` is `NoSelection`), `src/pubrun/tui/widgets/config.py:95-145` | yes |
| D-2 | Should `ActionsPanel` rename `self.rerun_command` to `self._rerun_command` for `BUG-13`? | Preserve public `self.rerun_command` (which already replaced `Static.renderable` on `main`) and add a regression check in `tests/test_tui_bugs.py`. | Rename to `self._rerun_command` (breaks `tests/test_tui.py:374,390`). | `src/pubrun/tui/widgets/actions.py:91,135,161,189`, `tests/test_tui.py:374,390` | yes |
| D-3 | Should `ActionsPanel.run_bulk_prune` keep its local `d`/`h`/float age parser or pass `older_than` directly to `status.clean_runs`? | Pass `older_than=older_val or None` directly to `src/pubrun/status.py::clean_runs` (removing duplicated local parsing) and catch `ValueError` to log and notify with `severity="error"`. | Keep local parser (misses `m`/`s` units added in `njn1up` and lets negative/`nan`/`inf` floats pass until `clean_runs`). | `src/pubrun/tui/widgets/actions.py:281-334`, `.aw/records/plans/pending/20261122-bugs-audit-01-njn1up-fix-status-clean-runs-and-filter-runs-data-loss-and-closeout.ipd.md:62-65` | yes |
| D-4 | How should `8ebjeg` fix the `V-01`..`V-04` test-ordering inversion while staying within 5 E-items? | Co-locate each widget group's tests in `E-01`..`E-04` and dedicate `E-05`/`V-05` to running `tests/test_tui_bugs.py`, `tests/test_tui.py`, and full `pytest -q`. | Keep all test authoring deferred to trailing `E-05` (leaves `V-01`..`V-04` unsatisfiable before `E-05`). | `.aw/system/workflows/plan-review/steps/r4-engineering.md:45-54` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against Round 1 edits. Round 1 resolved two BLOCKER factual defects (`PR-001`, `PR-002`) and substantially rewrote `E-01`..`E-05`/`V-01`..`V-05`, so a Round 2 re-review pass is required before finalization.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: Re-read the entire revised `.aw/records/plans/pending/20261122-bugs-audit-07-8ebjeg-fix-tui-widget-crashes-select-null-handling-and-sidebar-refr.ipd.md` after Round 1 edits. Verified every `path::Symbol` citation against `src/pubrun/tui/app.py`, `src/pubrun/tui/widgets/{actions,config,diff,details,viewer}.py`, `src/pubrun/capture/hardware.py`, `schemas/manifest.schema.json`, and `tests/test_tui.py`. Swept the plan for superseded wording (`_rerun_command`, `getattr(Select, "BLANK"`, `RunDetailsView.display_run`, `compare_manifests defaults to "basic"`, manual-move wording): zero stale occurrences remain.

### Step R2

- Checked: Re-verified 1:1 `E-01`..`E-05` to `V-01`..`V-05` bijection, `- Highest E allocated: 05`, 7-file `- Scope-Paths:` parity across `Scope`, `Scope check`, `Proposed changes`, and gate item 2, `- Item-Dependencies: executed:njn1up`, compliant 5-item Execution contract in `## Approval and execution gate`, and `aw ipd lint --phase review-finalize --agent` clean disposition with zero findings and zero advisories.

### Step R7

- Checked: Re-verified cross-plan alignment with orchestrator `jqqvkh`, prerequisite `njn1up`, and siblings `r68o07` and `ihh27o`. Confirmed `8ebjeg` file scope remains completely disjoint from all 8 sibling child plans in Set `bugs-audit`, fulfills `njn1up`'s `Carrier: 8ebjeg` obligation, and preserves `DiffView` compatibility with `r68o07`'s additive `path_split` keys.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 re-review pass confirmed zero new findings, zero changes to `E-*`/`V-*` counts, `- Scope-Paths:`, or `- Item-Dependencies:` in Round 2, and full cross-section sweep consistency across front matter, workflow history, Mermaid flowchart, checklist, findings, proposed changes, doc sync, validation items, and execution gate.

AW-REVIEW: DONE
