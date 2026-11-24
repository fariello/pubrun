# Review findings: ipd bwoyan

- Subject-Id: bwoyan
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-08-bwoyan-tui-interactive-wiring-and-widget-failure-path-tests.ipd.md` (front matter, Goal, diagram, E-01 to E-05, conventions, findings, proposed changes, deferral, scope check, required tests, documentation sync, V-01 to V-05, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. No pre-review snapshot was needed: lane HEAD `fcdc3d2` is clean, the plan is unchanged since `78ed358`, and `aw ipd lint --phase author --agent` reported `clean`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence citing coverage percentages and "guarding `git.remote_url = None`" | Says what the tests drive (Textual `App.run_test()` and `Pilot`) and what they assert, then explains each of the three measured defects in numbered steps (what the code does, what input triggers it, what the user sees) | Requirement 1 (explain before naming) and the communication contract: a reader new to the repository needs the mechanism. |
| Goal | Diagram of the app's message flow only | Mermaid work plan: four task groups, the 18 E-items, and their dependency edges | Requirement 12 (diagrams for multi-part plans). |
| E-01 to E-05 | Lettered sub-clauses (a) to (e) in one item; outcomes such as "All interactive and failure paths of `actions.py` are verified" | One concern per E-item (E-01 to E-18), each naming the test, its inputs, and the exact expected strings | An executor cannot check an outcome that names no value. |
| Project conventions | "Pending approved plans `whacr3` ..., `46fixy` ..., and open backlog `0mnekm`"; unmeasured coverage percentages | `whacr3` and `46fixy` are executed; `0mnekm` graduated to plan `67hcid`; percentages removed; adds the `--no-cov`, `RichLog` tab, lock-classification, and non-dict `git` reachability facts | Stale and unverified facts mislead the executor. |
| Spec / documentation sync | "N/A with reason: ... do not alter documented user-facing behavior" | Cites the spec search, the `docs/cli.md` `ui` section, and the `CHANGELOG.md` entries (E-09) | The plan now fixes user-visible behavior. |
| Gate | One paragraph telling the executor to move the plan by hand | Size exception with cohesion rationale and the five-element execution contract | Lifecycle transition belongs to `aw ipd finalize`; the contract elements were missing. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (2 entries before review, 5 after), E-01 to E-05 (18 E-items in 4 task groups after review), and the files each item touches.

1. Yes: after review the plan changes production behavior of `pubrun ui` in three places (the run details git section, the Archive button, and Save Settings). No public API, CLI option, or manifest field changes.
2. No: no private-data guard, commit, worktree, merge, or sandbox code. The git section displays already-redacted values; escaping keeps the `[REDACTED]` marker visible and changes no redaction.
3. Partly: 18 E-items in 4 task groups, all serving one subject (the TUI widget tests named by T-16 and T-17).
4. Yes: 5 files, three of them production modules.
5. Low: each production fix is a few lines inside one function (shape guards plus the existing `_escape_markup`; one `mkdir` moved inside the existing `try` plus one notification; one serializer helper). Every other change is a new test module.

AW-TIER: standard

### Step R1

- Checked: every cited path, symbol, and string against lane HEAD `fcdc3d2`, using Textual Pilot probes (Textual 8.2.8, Python 3.14.6) and a scratch copy under `/tmp/opencode` (never the lane). A 70-test prototype of the revised `tests/test_tui_widgets.py` gave `70 passed` on the fixed source and `17 failed, 53 passed` on HEAD; every HEAD failure is one of the defects below.
- PR-001: a manifest whose `git.remote_url` is `null` or a plain string makes `update_general_pane` raise `AttributeError` at `git.get('remote_url', {}).get('value')`. Selecting that run in `#runs-tree` ended the app with return code 1. A non-dict `git` raises the same way, but only reaches the pane through the lock path (PR-011).
- PR-002: the same block inserts `commit`, `branch`, remote URL, and lock `cwd` into Textual markup unescaped. Probe output: `  Branch:        feat/` for `feat/[wip]` and `  Remote URL:     https://user:@h/r.git` for the redacted form `src/pubrun/capture/redaction.py` `_redact_value_string_heuristics` writes (`\1://\2:[REDACTED]@\4`). A branch `[/bad]` raised `MarkupError`.
- PR-003: `archive_selected_run` calls `archive_dir.mkdir(exist_ok=True)` before its `try:`. With a file at `runs/archive` the app exited with `FileExistsError`; with a read-only runs folder, `PermissionError`. A run folder removed after selection returned with no notification.
- PR-004: `dict_to_toml` escapes only `\` and `"`, and writes lists with `json.dumps` (ASCII mode, so `😀` becomes `\ud83d\ude00`). `tomllib.loads` rejected `line1\nline2`, `bell\x07`, and `del\x7f` (`Illegal character`) and the surrogate escape (`Escaped character is not a Unicode scalar value`). A TUI save of a `.pubrun.toml` holding `ignore_basic = ["café 😀"]` produced a file that `load_local_config` ignored (`ignoring malformed config file`), so every local setting was lost.
- PR-005: Step 0 called `whacr3` and `46fixy` pending and `0mnekm` an open backlog item. Both plans are executed, and `0mnekm` graduated to plan `67hcid` (reviewed, pending), which edits the CPU line of `update_general_pane` and `tests/test_tui_bugs.py`.
- PR-006: E-01 placed the guard in `RunDetailsView.display_run`; the git block is in `update_general_pane`, which `display_run` calls.
- PR-007: Step 0 stated coverage percentages (`actions.py` 67% and others) with no command or run. They were not re-measured (this lane runs no coverage) and were removed; nothing in the plan depends on them.

### Step R2

- Checked: author-phase lint (`clean`), the E/V bijection, and each V-item against what its E-item produces.
- PR-008: E-03, E-04, and E-05 each bundled four to six concerns with outcomes no executor could check ("All interactive and failure paths ... are verified"). Split into single-concern items with exact inputs and expected strings, all taken from the prototype run.
- PR-009: every V-item demanded only a passing `-k` selection (for example `-k "diff or viewer or log"`). A pass cannot show that a test detects a regression. Each V-item now names its selector and count, and one or more mutation checks or a fix-reverted check that must fail. All 43 named mutations were applied one at a time in the scratch copy and each gave at least 1 failure; the fix-reverted counts (details.py 10, actions.py 2, config.py 5) were measured. A mutation-check procedure paragraph was added.
- PR-010: four traps would make a correct-looking test fail or pass vacuously: a `RichLog` records lines only after its tab is shown; a lock from another host younger than 48 hours is classified running without a pid check, while a local pid may be alive; patching the global `sys.platform` affects pytest itself; `ctrl+s` is the sidebar binding. Each is now stated in the conventions or in the E-item that needs it.
- PR-011: E-05 asked for a "malformed `git`" details test. A manifest alone with a non-dict `git` never reaches the pane: `RunInfo._load_from_manifest` fails and `scan_runs` lists the run as crashed. E-16 builds the reachable case (startup manifest plus lock).
- PR-012: Required tests ran `pytest ... -v` without `--no-cov`, but `pyproject.toml` `addopts` adds coverage, and only one runner was named. Both `python3 -m pytest` and `pytest` are now required with `--no-cov`, plus the skip check without `textual`.

### Step R3

- Checked: the new tests write only under `tmp_path`, set `XDG_CONFIG_HOME` and `APPDATA` there, unset `PUBRUN_PROFILE` and `PUBRUN_META_REF`, start no real clipboard process (`subprocess` is replaced at module level), and use no network. `scripts/sanitize_paths.py --check` exited 0 on the prototype files. No finding.

### Step R4

- Checked: the `AGENTS.md` no-code-pinning rule (every new test drives a widget, the app, or a function and asserts on rendered text, notifications, or files); sibling scopes; doc sync; Python 3.8 syntax (`ast.parse` with `feature_version=(3, 8)` on all prototype files). Overlap with `67hcid` (`details.py` CPU line, `tests/test_tui_bugs.py`) and `gzc672` (`actions.py` `on_button_pressed`, `handle_deletion_result`, and the `RefreshSidebar` posts) is not a hazard: each runner lane has its own worktree and returns through the merge-and-revalidate gate, and the edits touch different lines. V-03 names both forms of the `RefreshSidebar` line.
- PR-013: the plan did not name what `tests/test_tui_bugs.py` already covers, so an executor could repeat it. E-01 and the per-class items now name the existing classes (`TestRefreshSidebarRouting`, `TestActionsPanel`, `TestConfigPanel`, `TestDiffView`, `TestRunDetailsGpu`, `TestRunDetailsOsLine`, `TestLogViewer`) and the cases not to repeat.
- PR-014: with three production fixes, "N/A: test-only" no longer held and `Work-Kind: chore` was wrong. E-09 adds `CHANGELOG.md` `### Fixed` entries (V-09 checks the dash rule); `Work-Kind` is `bug`. The `docs/cli.md` `ui` section describes none of the changed behavior, and no spec mentions the TUI.
- PR-015: the gate told the executor to "move this plan to `.aw/records/plans/executed/`" by hand and lacked the scope declaration, the validation-honesty rule, and the runner and executor split. It now carries the five-element execution contract, including the temporary mutation edits to out-of-scope files that must not be committed.
- PR-016: the diagram showed the app's message flow, not the plan's work. Replaced with a work-plan diagram.

### Step S5

- Checked: deferrals (seams `Carrier: riulkx`, kept; two `Carrier-Declined` entries added at review: the `Repo Dirty: None` display, characterized and not pinned, and Textual 0.x, Windows, and macOS coverage, which only the CI matrix can give after a human push). Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so the plan needs no blocking question and the lane outcome carries none.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R1 (production defect) | Pilot probe: selecting a run with `remote_url: null` exited the app with return code 1 | `null` or string `remote_url`, or a non-dict `git`, closes the TUI. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-06 `_format_remote_url` and `isinstance(git, dict)` guard; V-06 and V-16. |
| PR-002 | medium | IN-SCOPE | R1 (production defect) | Probe text `https://user:@h/r.git`, `feat/`; `MarkupError` for `[/bad]` | Unescaped markup drops redaction markers and bracketed names, or raises. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-06 wraps commit, branch, remote URL, and lock fields in `_escape_markup`. |
| PR-003 | high | IN-SCOPE | R1 (production defect) | File at `runs/archive`: app exited with `FileExistsError`; vanished run: `notes == []` | Archive closes the TUI or fails silently. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-07 moves `mkdir` into the `try` and notifies for a vanished folder; V-07. |
| PR-004 | high | IN-SCOPE | R1 (production defect) | `load_local_config` returned `None` after a TUI save of an emoji list | Save Settings writes TOML pubrun ignores, losing every local setting. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-08 `_toml_scalar_or_list`; V-08 and V-18. |
| PR-005 | medium | IN-SCOPE | R1 (stale convention) | `whacr3`, `46fixy` in `executed/`; `0mnekm` graduated to `67hcid` | Step 0 misstated sibling state. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Conventions name the current state and the sibling edits. |
| PR-006 | low | IN-SCOPE | R1 (wrong symbol) | git block is in `update_general_pane` | E-01 named `display_run`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-06 names `update_general_pane` and the exact lines. |
| PR-007 | low | IN-SCOPE | R1 (unverified claim) | No command or run behind the coverage percentages | Step 0 stated coverage figures nobody can reproduce from the plan. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Removed; no item depends on them. |
| PR-008 | medium | IN-SCOPE | R2 (unexecutable items) | Outcomes such as "All interactive and failure paths ... are verified" | Bundled items had outcomes no executor could check. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Single-concern E-items with exact strings from the prototype run. |
| PR-009 | high | IN-SCOPE | R2 (evidence cannot prove the change) | 43 mutations each caught; fix-reverted counts 10, 2, 5 | Suite-pass-only V-items could not show the tests detect regressions. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Each V-item names selector, count, and mutation or fix-reverted checks. |
| PR-010 | medium | IN-SCOPE | R2 (test traps) | `RichLog` empty before tab shown; 48-hour lock rule; global `sys.platform` | Correct-looking tests would fail or pass vacuously. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Conventions and E-items state each rule and the technique. |
| PR-011 | medium | IN-SCOPE | R2 (unreachable case) | Manifest-only non-dict `git` listed as crashed by `scan_runs` | The requested test could not reach the pane. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-16 uses a startup manifest plus a lock. |
| PR-012 | low | IN-SCOPE | R2 (validation command) | `pyproject.toml` `addopts` `--cov=src` | Required tests omitted `--no-cov` and the second runner. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Both runners with `--no-cov`; V-01 skip check. |
| PR-013 | low | IN-SCOPE | R4 (duplication) | `tests/test_tui_bugs.py` classes | The plan did not name existing coverage to avoid. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-items name the classes and cases not to repeat. |
| PR-014 | low | IN-SCOPE | R4 (doc sync) | Three user-visible fixes; spec `grep` empty | "N/A" and `Work-Kind: chore` no longer held. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-09 `CHANGELOG.md`; `Work-Kind: bug`. |
| PR-015 | medium | IN-SCOPE | S7 (execution contract) | Gate text "move this plan to `.aw/records/plans/executed/`" | Hand lifecycle move; contract elements missing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Five-element execution contract with `aw ipd finalize bwoyan`. |
| PR-016 | low | IN-SCOPE | P (diagram) | Diagram showed message flow only | Requirement 12 not met for the plan's work. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Mermaid work plan under the Goal. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Three small production fixes plus tests; no spec, security, or public API surface | yes |
| D-2 | Fix the three defects here or defer them? | Fix here (E-06, E-07, E-08) | Backlog items; separate plans | The tests the original E-03 and E-05 asked for cannot pass without them, and they sit on the code those tests exercise | yes |
| D-3 | How to make `dict_to_toml` output valid TOML | `json.dumps(ensure_ascii=False)` plus a U+007F escape | Hand-written TOML escaper; a `tomli_w` dependency | Every JSON escape is a valid TOML basic-string escape except raw U+007F; the module is zero-dependency by design; plain ASCII output is unchanged | yes |
| D-4 | `Repo Dirty: None` when `git.dirty` is absent | Characterize only, not pinned | Show `-` or `unknown` | The value is a recorded tri-state; choosing a display word is a UX decision outside a test plan | yes |
| D-5 | Split the plan after `IPD-Z603` (18 E-items)? | Keep one plan with a cohesion rationale | Split by widget | The orchestrator `vdxiw8` assigns T-16 and T-17 to this plan as one row; splitting changes its child table | yes |
| D-6 | Python 3.8 / Textual 0.x, Windows, macOS coverage | `Carrier-Declined`; CI matrix after a human push | Local multi-version runs | Only Textual 8.2.8 on Python 3.14 is available locally; tests avoid version-specific APIs | yes |
| D-7 | Share helpers with `tests/test_tui_bugs.py`? | Define them in the new module | Import from `tests/test_tui_bugs.py` | Importing between test modules couples them, and sibling `67hcid` edits that file | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. E-06 to E-17 with V-06 to V-17 were added (`Highest E allocated: 17`, assigned by `aw ipd sync --apply`). `- Scope-Paths:` gained `src/pubrun/tui/widgets/actions.py`, `src/pubrun/tui/widgets/config.py`, and `CHANGELOG.md`. `- Item-Dependencies:` is unchanged (`none`). A re-review pass is required.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: re-read the revised plan in full against lane HEAD `fcdc3d2`. Each of the 41 mutation and fix target strings in the E- and V-items was counted in its source file; one was ambiguous (PR-018). The V-05 mutations were re-measured with the narrower selector `"TestConfigPanelStates or TestDictToToml"` (1 failure each) and the V-08 U+007F mutation with `TestTomlEscaping` (2 failures). The fix-reverted `config.py` check with all three classes gave `5 failed, 8 passed`, all five in `TestTomlEscaping`.
- PR-018: V-11 said to remove `"btn-archive-run", ` from the no-selection guard, but that text also matches the `Button("Archive Run (ZIP)", id="btn-archive-run", variant="success")` line in `compose`. V-11 now quotes the guard-tuple text, which occurs once.

### Step R2

- Checked: `aw ipd sync --apply` appended 12 `TODO` V-skeletons duplicating V-06 to V-17; the duplicates were removed. `aw ipd lint --phase review-finalize` then reported PR-017.
- PR-017: `IPD-Z603` (line 160): E-05 named 9 distinct units, and `IPD-C802`: an em dash in the documentation-sync line quoting the `docs/cli.md` heading. E-05 was split into E-05 (`TestConfigPanelStates`, `TestDictToToml`) and E-18 (`TestTomlEscaping`), V-05 and the new V-18 were rewritten with measured counts, and the heading is described instead of quoted. After the fix, lint reports only the plan-level `IPD-Z603` advisory answered by D-5.

### Step R4

- Checked: the scope paths are unchanged since Round 1. E-18 depends on E-08 and the diagram edge moved from E-05 to E-18. The cohesion rationale counts 18 E-items.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-017 | low | IN-SCOPE | R2 (lint) | `IPD-Z603` on E-05; `IPD-C802` em dash | E-05 bundled nine units; one quoted heading carried an em dash. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05 split into E-05 and E-18 with V-18; heading described. |
| PR-018 | low | IN-SCOPE | R1 (ambiguous mutation target) | `"btn-archive-run", ` occurs twice in `actions.py` | One mutation instruction did not identify one edit. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-11 quotes the guard-tuple text, which occurs once. |

### Step S6

- Checked: Round 2 removed duplicate skeletons, added E-18 and V-18 (`Highest E allocated: 18`, assigned by `aw ipd sync --apply`), described one heading, and clarified one mutation target. `- Scope-Paths:` and `- Item-Dependencies:` are unchanged since Round 1's S6. `aw ipd lint --phase review-finalize` reports only the plan-level `IPD-Z603` advisory. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
