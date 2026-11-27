# Review findings: ipd 3q5rd5

- Subject-Id: 3q5rd5
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-8l-09-3q5rd5-tui-safety-meta-ref-hydration-memory-responsiveness-and-usab.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`clean`, 0 errors, 0 warnings, 1 info `IPD-Z603`). Expanded acronyms (`TUI`, `CLI`, `TOML`, `HPC`, `PID`, `RSS`, `CPU`, `EOF`, `OOM`, `RAM`, `CSS`) on first use, anchored symbols with `path::Symbol`, replaced ambiguous `"or synchronize/warn"` wording with concrete `[imports].mode` widget behavior, and updated the Mermaid `flowchart TD` diagram to include `load_manifest()` and all three TUI test files.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `- Scope:`, `- Scope-Paths:`, `E-04`, `E-05`, `## Required tests / validation`, `V-04`, `V-05` | Omitted `tests/test_tui_widgets.py` from `- Scope-Paths:` and omitted `tests/test_timing_consumers.py` from validation despite 11 existing test sites directly affected by `E-01`..`E-04` (including `Elapsed` `width=18` pin in `test_timing_consumers.py:723`) | Added `tests/test_tui_widgets.py` to `- Scope-Paths:`, added `tests/test_timing_consumers.py` to `## Required tests / validation` and `V-05`, pinned `subprocesses-table` `"Elapsed"` `width=18`, and specified exact updates for all affected existing tests in `E-05` | Prevent blocker test regressions across `test_tui_widgets.py`, `test_tui_bugs.py`, and `test_timing_consumers.py` (`PR-001`) |
| `E-01`, `E-02`, `V-01`, `V-02` | Switched `RunsSidebar` to `scan_runs(..., keep_manifest=False)` without updating `RunDetailsView`, `ActionsPanel`, and `RunResourcesView` to call `run_info.load_manifest()` on demand | Required `run_info.load_manifest()` on demand in `RunDetailsView`, `ActionsPanel`, and `RunResourcesView` and specified `RunInfo(run_dir, keep_manifest=False)` in `refresh_live_metrics()` | Prevent silent blank detail/actions/resources panes once `keep_manifest=False` drops `RunInfo.manifest` (`PR-002`) |
| `E-01`, `V-01` | Left `archive_selected_run()` `delete_raw` on raw `shutil.rmtree`; did not specify `base_dir` for `safe_delete_run_dir()` or `ConfirmBulkPruneModal` vs direct `run_bulk_prune()` separation; cited nonexistent `_build_rerun_command()` in `actions.py` | Routed both `handle_deletion_result()` and archive `delete_raw` through `safe_delete_run_dir(run_dir, base_dir)` using configured `output_dir`, pushed `ConfirmBulkPruneModal` from `#btn-prune-execute` while keeping direct `run_bulk_prune()` callable, and specified extracting Windows-safe `_build_rerun_command()` | Close confinement/deletion security gap and keep `test_tui_bugs.py:202-258` green (`PR-003`) |
| `E-04`, `V-04` | Left `ConfigPanel` `[imports].mode` choice ambiguous (`"or synchronize/warn"`), omitted `None`-value omission and key quoting in `dict_to_toml()`, `<3.11` `tomli` fallback, temp-file cleanup/Windows retry, and first-notification ordering (`test_tui_widgets.py:1036`) | Specified `#cfg-imports-mode` `Select` alongside `core.auto_start`, `None` omission + key quoting + `tomllib`/`tomli` validation in `dict_to_toml()`, atomic temp-file cleanup + Windows retry, and preserving `"Configuration saved to: .pubrun.toml"` as first notification | Prevent invalid TOML writes and `test_tui_bugs.py`/`test_tui_widgets.py` regressions (`PR-004`) |
| `E-02`, `E-03`, `V-02`, `V-03` | `LogViewer` wording `"skip nonexistent console.log"` risked breaking legacy `console.log` tests; `RunResourcesView` fallback risked breaking empty-run assertions; single-char bindings (`1`-`6`, `/`, `?`) lacked explicit non-priority rule | Prioritized `stdout.log` -> `stderr.log` -> existing legacy `console.log` with `prevent(Select.Changed)`, preserved `"No resource samples recorded for this run ..."` when both `events.jsonl` and `manifest.resources` are empty, and required `priority=False` on single-char bindings | Prevent breaking legacy logs, empty-resource tests, and focused `Input` widgets (`PR-005`) |
| `## Goal`, Mermaid diagram, `## Approval and execution gate` | Missing five-clause execution contract, unexpanded acronyms, incomplete Mermaid diagram | Added five-clause execution gate, expanded acronyms on first use, and updated Mermaid diagram | Satisfy execution-contract and technical-writing rules (`PR-006`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-8l`, `- Order: 9`, `- Scope-Paths:` (12 files: `app.py`, `style.css`, 7 widget modules, and 3 test files), 5 E-items in 4 task groups, `- Item-Dependencies: executed:m5s3g8, executed:caeqdz`.

1. Yes: changes interactive TUI behavior, `DiffView` default depth (`basic` -> `standard`), `ConfigPanel` `.pubrun.toml` serialization and `[imports].mode`, and `ActionsPanel` bulk-prune confirmation flow.
2. Yes: `ActionsPanel` single-run delete, archive `delete_raw`, and bulk prune perform destructive directory removal guarded by `safe_delete_run_dir()` (symlink, parent-directory confinement, active/remote lock checks), and `ConfigPanel` atomically writes `.pubrun.toml` including redaction regex settings.
3. Yes: spans `ROLL-06` and `ROLL-19` across 9 TUI production files and 3 test suites (`tests/test_tui*.py`).
4. Yes: `- Scope-Paths:` explicitly lists all 12 modified files.
5. Yes: bugs in `safe_delete_run_dir()` base-dir confinement, `ConfigPanel` TOML serialization, or `keep_manifest=False` manifest loading could delete unintended directories, corrupt `.pubrun.toml`, or leave TUI panes blank.

AW-TIER: complex

### Step R1

- Checked: every cited source file, sibling plan, and test file against the repository:
  - Production code: `src/pubrun/tui/app.py:1-128`, `src/pubrun/tui/css/style.css:1-255`, `src/pubrun/tui/widgets/actions.py:1-389`, `src/pubrun/tui/widgets/config.py:1-219`, `src/pubrun/tui/widgets/details.py:1-452`, `src/pubrun/tui/widgets/diff.py:1-213`, `src/pubrun/tui/widgets/resources.py:1-45`, `src/pubrun/tui/widgets/sidebar.py:1-89`, `src/pubrun/tui/widgets/viewer.py:1-104`.
  - Supporting code: `src/pubrun/status.py:140-310`, `src/pubrun/__main__.py:340-410`, `src/pubrun/capture/invocation.py:1-187`.
  - Tests: `tests/test_tui.py:1-424`, `tests/test_tui_bugs.py:1-721`, `tests/test_tui_widgets.py:1-1244`, `tests/test_timing_consumers.py:669-800`.
  - Sibling plans: `k80suw` (Order 00), `m5s3g8` (Order 06), `caeqdz` (Order 07), `2ge0ea` (Order 08).
- Verified: `actions.py` had no `_build_rerun_command()` function yet (`PR-003`), `archive_selected_run()` used raw `shutil.rmtree` (`PR-003`), `RunsSidebar` switching to `keep_manifest=False` breaks `details.py`/`actions.py`/`resources.py` unless they call `load_manifest()` (`PR-002`), and 11 existing test sites across `test_tui_widgets.py`, `test_tui_bugs.py`, and `test_timing_consumers.py` directly interact with the proposed changes (`PR-001`, `PR-004`, `PR-005`).

### Step R2

- Checked: strict 1:1 `E-01..E-05` <-> `V-01..V-05` bijection, `- Highest E allocated: 05`, `- Scope-Paths:` completeness (all 12 modified files), `- Item-Dependencies: executed:m5s3g8, executed:caeqdz`, concrete named `path::Symbol` units in every `V-*` item, non-tautological behavioral pilot/unit evidence, and the five-clause execution contract.
- Verified: every `E-*` maps cleanly to an observable `V-*` and all four TUI test suites exist and are included in `## Required tests / validation`.

### Step R3

- Checked: destructive-deletion security boundaries in `ActionsPanel` (`ConfirmBulkPruneModal` before bulk prune, `safe_delete_run_dir(run_dir, base_dir)` using configured `output_dir` rather than `run_dir.parent` on both `handle_deletion_result()` and archive `delete_raw`), atomic TOML writes with `re.compile()` validation and `tomllib` round-trip verification before replacing `.pubrun.toml`, bounded 2 MiB / 5,000-line log reads preventing OOM denial-of-service, and `timeout=5` on clipboard subprocesses.
- Verified: `PR-003` and `PR-004` close every deletion-confinement and config-corruption gap.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing, and `## Spec / documentation sync`.
- Verified: `PR-001` aligns all existing TUI test suites; `PR-002` completes the `keep_manifest=False` + `load_manifest()` migration across all three detail panels; `PR-003` locks down bulk-prune confirmation, `safe_delete_run_dir()` confinement, and `_build_rerun_command()`; `PR-004` locks down `dict_to_toml()` and `ConfigPanel`; `PR-005` closes `LogViewer`, `RunResourcesView`, and non-priority keybinding edge cases; `PR-006` adds the five-clause execution gate and technical-writing fixes.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `keep_manifest=False` blanking out `RunDetailsView`/`ActionsPanel`/`RunResourcesView` (`PR-002`) and `dict_to_toml()` serializing `None` as `"None"` (`PR-004`).
  2. Testing and regression: caught 11 existing test interactions in `test_tui_widgets.py`, `test_tui_bugs.py`, and `test_timing_consumers.py:723` (`PR-001`, `PR-005`).
  3. UI / UX: enforced non-priority `1`–`6`/`/`/`?` bindings so text inputs aren't hijacked, responsive 80x24 CSS + `ScrollableContainer` on `ActionsPanel`, `"Wrap: ON"`/`"Wrap: OFF"` feedback, and `"Project Config"` tab clarity (`PR-004`, `PR-005`).
  4. Architect: ensured `ActionsPanel`, `RunDetailsView`, and `RunResourcesView` consume `m5s3g8`'s `safe_delete_run_dir()` and `load_manifest()` cleanly with zero file overlap against siblings (`PR-002`, `PR-003`).
  5. Software engineer: separated `#btn-prune-execute` modal from direct `run_bulk_prune()` calls, extracted pure `_build_rerun_command()`, used `prevent(Select.Changed)` in `LogViewer`, and mirrored `writer.py` atomic-write hygiene in `ConfigPanel` (`PR-003`, `PR-004`, `PR-005`).
  6. Power user: added Wayland `wl-copy` + clipboard timeout, in-memory sidebar search across `args`/`status`, lazy tabs, `DiffView` `"standard"` default + auto-preselect, and keyboard navigation (`PR-001`, `PR-005`).
  7. Novice: added bulk-prune confirmation with run count and disk size, accurate 0-run onboarding, empty-log `capture_mode` hint, valid status/age placeholders, and `?` keybind help (`PR-003`, `PR-005`).
  8. Stakeholder: maintained 100% backward compatibility with legacy `console.log` runs, existing `.pubrun.toml` files, and `test_timing_consumers.py` timing views (`PR-001`, `PR-004`, `PR-005`).

### Step R6

- Checked: decomposition and sizing across `E-01..E-05` (5 E-items, 4 task groups, Order 09 of 10-child Set `assess-8l`).
- Confirmed: cohesive, right-sized child plan owning `src/pubrun/tui/` and `tests/test_tui*.py` exclusively. No splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-8l`: orchestrator `k80suw` (Order 00), `m5s3g8` (Order 06 — provides `safe_delete_run_dir()`, `scan_runs(..., keep_manifest=False)`, and `RunInfo.load_manifest()`, explicitly listed in `m5s3g8` `## Deferred / out of scope` with `Carrier: 3q5rd5`), `caeqdz` (Order 07 — provides hardened `diff.py` and `report/utils.py`), `2ge0ea` (Order 08 — zero file overlap), and `6y55x4` (Order 10 — depends on `executed:3q5rd5`).
- Verified: zero file overlap with any sibling (including newly added `tests/test_tui_widgets.py`) and zero dependency cycles.

### Step S5

- Checked: `## Open questions` contains `None.`. All six findings (`PR-001` through `PR-006`) had `Low` overall Remediation Risk, were settled by repository code, sibling-plan, and test evidence, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` D, E | `tests/test_tui_widgets.py:151-179,249-263,587-644,839-892`, `tests/test_tui_bugs.py:360-422`, `tests/test_timing_consumers.py:721-723`, `.aw/records/plans/pending/20261127-assess-8l-09-3q5rd5-tui-safety-meta-ref-hydration-memory-responsiveness-and-usab.ipd.md:7,128` | `tests/test_tui_widgets.py` was omitted from `- Scope-Paths:` and `tests/test_timing_consumers.py` was omitted from validation despite existing tests directly broken by lazy tab rendering, `keep_manifest=False` kwarg on `scan_runs`, `copy_to_clipboard` kwargs/`wl-copy`, `LogViewer` empty-log hint, `DiffView` `"standard"` default + pre-selection, and `Elapsed` `width=18` pin. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `tests/test_tui_widgets.py` to `- Scope-Paths:`, added `tests/test_timing_consumers.py` to `## Required tests / validation` and `V-05`, preserved `Elapsed` `width=18`, and specified exact updates for all affected existing tests in `E-05` (recommendation strength: `very strong`). |
| PR-002 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A, D / `r7-cross-plan.md` | `src/pubrun/tui/widgets/details.py:244-449`, `src/pubrun/tui/widgets/actions.py:168-245`, `src/pubrun/tui/widgets/resources.py:30-45`, `src/pubrun/tui/widgets/sidebar.py:39` | Switching `RunsSidebar` to `scan_runs(..., keep_manifest=False)` sets `RunInfo.manifest = None`, which would blank out `RunDetailsView`, `ActionsPanel`, and `RunResourcesView` unless all three load manifests on demand via `run_info.load_manifest()`; `refresh_live_metrics()` also needed explicit `RunInfo(run_dir, keep_manifest=False)` to stay lightweight while preserving `test_tui_widgets.py:1152-1198`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required `run_info.load_manifest()` on demand in `RunDetailsView`, `ActionsPanel`, and `RunResourcesView` and specified `RunInfo(run_dir, keep_manifest=False)` in `refresh_live_metrics()` in `E-01` and `E-02` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D | `src/pubrun/tui/widgets/actions.py:173-190,306-389`, `tests/test_tui_bugs.py:116-147,202-258`, `tests/test_tui_widgets.py:530-550` | `archive_selected_run()` `delete_raw` still used raw `shutil.rmtree` without parent-directory confinement; `safe_delete_run_dir()` needed explicit configured `output_dir` as `base_dir` (never `run_dir.parent`); `#btn-prune-execute` confirmation needed separation from direct `run_bulk_prune()` test calls; and `actions.py` had no `_build_rerun_command()` helper yet. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Routed both `handle_deletion_result()` and archive `delete_raw` through `safe_delete_run_dir(run_dir, base_dir)` using configured `output_dir`, pushed `ConfirmBulkPruneModal` from `#btn-prune-execute` while preserving direct `run_bulk_prune()` calls, and specified extracting Windows-safe `_build_rerun_command()` in `E-01` and `V-01` (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D, F | `src/pubrun/tui/widgets/config.py:53-92,184-219`, `tests/test_tui_bugs.py:274-347`, `tests/test_tui_widgets.py:921-1043` | `ConfigPanel` `[imports].mode` handling was ambiguous; `dict_to_toml()` serialized `None` as literal `"None"` and lacked key quoting and `<3.11` `tomli` fallback; atomic save needed temp cleanup, Windows retry, and preserving `"Configuration saved to: .pubrun.toml"` as first notification (`test_tui_widgets.py:1036`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `#cfg-imports-mode` `Select` alongside `core.auto_start`, `None` omission + key quoting + `tomllib`/`tomli` validation in `dict_to_toml()`, atomic temp cleanup + Windows retry, and preserved first notification in `E-04` and `V-04` (recommendation strength: `very strong`). |
| PR-005 | HIGH | IN-SCOPE | `r4-engineering.md` D, F | `src/pubrun/tui/widgets/viewer.py:61-104`, `src/pubrun/tui/widgets/resources.py:30-45`, `src/pubrun/tui/app.py:31-36`, `tests/test_tui.py:184-194`, `tests/test_tui_bugs.py:684-720`, `tests/test_tui_widgets.py:173-175,864-890,1207-1223` | Skipping `console.log` outright would break legacy log tests; `RunResourcesView` fallback needed to preserve `"No resource samples recorded for this run ..."` when both `events.jsonl` and `manifest.resources` are empty; single-character bindings (`1`–`6`, `/`, `?`) lacked explicit `priority=False` to avoid hijacking focused `Input` widgets. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Prioritized `stdout.log` -> `stderr.log` -> existing legacy `console.log` with `prevent(Select.Changed)`, preserved empty-run resource message when neither source has data, and required `priority=False` on single-char bindings in `E-02` and `E-03` (recommendation strength: `very strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `.aw/records/plans/pending/20261127-assess-8l-09-3q5rd5-tui-safety-meta-ref-hydration-memory-responsiveness-and-usab.ipd.md:26-43,168-170` | `## Approval and execution gate` lacked the five-clause execution contract; acronyms were unexpanded on first use; Mermaid diagram omitted `load_manifest()` and the test suites. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the five-clause execution gate, expanded acronyms on first use, and updated the Mermaid diagram (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `3q5rd5` | `complex` | `standard` | Touches destructive deletion security boundaries (`ActionsPanel`), atomic `.pubrun.toml` writing (`ConfigPanel`), and 9 TUI production files + 3 test suites; answers Yes to all five tier questions in `steps/t-tier.md`. | yes |
| D-2 | Handling `ConfirmBulkPruneModal` vs direct `panel.run_bulk_prune(dry_run=False)` unit tests | Push `ConfirmBulkPruneModal` from `on_button_pressed("#btn-prune-execute")` after validating criteria and computing count/bytes, calling `run_bulk_prune(dry_run=False)` on confirmation | Block inside `run_bulk_prune()` itself (breaks direct unit calls in `tests/test_tui_bugs.py:227,252`) | Guarantees interactive UI safety while keeping `tests/test_tui_bugs.py` direct method tests green. | yes |
| D-3 | Handling `[imports].mode` vs `[core].auto_start` in `ConfigPanel` | Add explicit `#cfg-imports-mode` `Select` (`auto`, `full`, `minimal`, `noauto`, `nopatch`, `off`) with precedence note while keeping `core.auto_start` persisted | Drop `core.auto_start` (breaks `tests/test_tui_bugs.py:296`) or leave `[imports].mode` hidden (fails `ROLL-19`) | Aligns with `2ge0ea`'s `default.toml` precedence documentation and preserves `tests/test_tui_bugs.py:296`. | yes |

### Step S6

- Checked: Round 1 added `tests/test_tui_widgets.py` to `- Scope-Paths:` and tightened `E-01`..`E-05` and `V-01`..`V-05`. Per `steps/s6-rereview.md` rule 1, a second pass (Round 2) is required to verify the revised Scope-Paths, contracts, cross-references, and lint conformance.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised `.aw/records/plans/pending/20261127-assess-8l-09-3q5rd5-tui-safety-meta-ref-hydration-memory-responsiveness-and-usab.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. Confirmed all acronyms are expanded on first use, all `E-01..E-05` and `V-01..V-05` items cite concrete `path::Symbol` units with observable criteria, and the Mermaid `flowchart TD` covers all 9 TUI production files, `load_manifest()`, and all 3 TUI test files.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R2

- Checked: verified `- Highest E allocated: 05` matches `E-01..E-05` and `V-01..V-05` (strict 1:1 bijection); verified `- Scope-Paths:` lists all 12 modified files accurately; verified `- Item-Dependencies: executed:m5s3g8, executed:caeqdz` matches all upstream dependencies; verified the five-clause execution gate states conditional runner/executor finalize ownership with no forbidden "STOP and report" scope-fence wording.

### Step R7

- Checked: verified zero file overlap with any sibling in Set `assess-8l` (including newly added `tests/test_tui_widgets.py`), confirmed `m5s3g8` provides `safe_delete_run_dir()`, `scan_runs(..., keep_manifest=False)`, and `RunInfo.load_manifest()`, and confirmed `caeqdz` provides the diff/hydration contracts consumed by `DiffView` and `RunDetailsView`.

### Step S5

- Checked: `## Open questions` contains `None.`; all six findings (`PR-001` through `PR-006`) are `FIXED`; zero blocking questions or irreversible decisions remain; lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` D, E | `tests/test_tui_widgets.py`, `tests/test_tui_bugs.py`, `tests/test_timing_consumers.py:723` | Missing `tests/test_tui_widgets.py` Scope-Path, missing `tests/test_timing_consumers.py` validation, and 11 affected existing test sites. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `tests/test_tui_widgets.py` is in `- Scope-Paths:`, `tests/test_timing_consumers.py` is in validation, `Elapsed` `width=18` is preserved, and all test alignments are reconciled in `E-05`/`V-05` (recommendation strength: `very strong`). |
| PR-002 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A, D / `r7-cross-plan.md` | `src/pubrun/tui/widgets/{details,actions,resources,sidebar}.py` | `keep_manifest=False` in `RunsSidebar` needed `load_manifest()` on demand in `RunDetailsView`, `ActionsPanel`, and `RunResourcesView` plus `keep_manifest=False` in `refresh_live_metrics()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `load_manifest()` and lightweight `refresh_live_metrics()` are reconciled across `E-01`, `E-02`, `V-01`, and `V-02` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D | `src/pubrun/tui/widgets/actions.py` | Archive `delete_raw` confinement, `safe_delete_run_dir` `base_dir`, `ConfirmBulkPruneModal` vs `run_bulk_prune()`, and `_build_rerun_command()` extraction. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-01` and `V-01` specify all deletion confinement, modal separation, and rerun-builder requirements (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D, F | `src/pubrun/tui/widgets/config.py` | Ambiguous `[imports].mode`, `dict_to_toml()` `None`/key escaping/`tomli`, atomic cleanup/retry, and notification order. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-04` and `V-04` specify `#cfg-imports-mode`, hardened `dict_to_toml()`, atomic writes, and notification preservation (recommendation strength: `very strong`). |
| PR-005 | HIGH | IN-SCOPE | `r4-engineering.md` D, F | `src/pubrun/tui/widgets/{viewer,resources}.py`, `src/pubrun/tui/app.py` | Legacy `console.log` preservation, `RunResourcesView` empty-state preservation, and non-priority single-char bindings. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-02` and `E-03` reconcile log priority, `prevent(Select.Changed)`, empty-resource messaging, and `priority=False` bindings (recommendation strength: `very strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `3q5rd5` | Missing five-clause execution gate, unexpanded acronyms, and incomplete Mermaid diagram. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: five-clause execution gate, acronym expansions, and updated Mermaid diagram are reconciled across the plan (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `3q5rd5` | `complex` | `standard` | Touches destructive deletion security boundaries, atomic `.pubrun.toml` writing, and 9 TUI production files + 3 test suites; answers Yes to all five tier questions in `steps/t-tier.md`. | yes |
| D-2 | Handling `ConfirmBulkPruneModal` vs direct `panel.run_bulk_prune(dry_run=False)` unit tests | Push `ConfirmBulkPruneModal` from `#btn-prune-execute` after validation/preview, calling `run_bulk_prune(dry_run=False)` on confirm | Block inside `run_bulk_prune()` itself | Guarantees UI safety while preserving direct `test_tui_bugs.py:227,252` unit calls. | yes |
| D-3 | Handling `[imports].mode` vs `[core].auto_start` in `ConfigPanel` | Add explicit `#cfg-imports-mode` `Select` with precedence note while keeping `core.auto_start` persisted | Drop `core.auto_start` or hide `[imports].mode` | Aligns with `2ge0ea` `default.toml` precedence and preserves `test_tui_bugs.py:296`. | yes |

### Step S6

- Checked: Round 2 introduced no further edits, no new findings, and no structural changes. All revisions from Round 1 are internally consistent and reconciled across all sections. Ready for Step S7 finalization (`APPROVE WITH REVISIONS APPLIED`, `go-pending-approval`).

AW-REVIEW: DONE
