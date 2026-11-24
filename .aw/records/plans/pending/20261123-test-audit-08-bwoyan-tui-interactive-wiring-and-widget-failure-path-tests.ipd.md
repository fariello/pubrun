# IPD: TUI interactive wiring and widget failure-path tests

- Date: 2026-11-23
- Kind: child
- Concern: Testing rigor and completeness (TUI end-to-end sidebar-to-workspace wiring, interactive flows, and error and degraded states across the TUI widgets), plus three production defects the review measured on the same paths: the run details pane exits the TUI or drops text for some manifest `git` values, the Archive action exits the TUI or fails silently when the archive folder cannot be made or the run folder is gone, and Save Settings writes a `.pubrun.toml` that pubrun then refuses to load.
- Scope: `src/pubrun/tui/widgets/details.py`, `src/pubrun/tui/widgets/actions.py`, `src/pubrun/tui/widgets/config.py`, `CHANGELOG.md`, and new `tests/test_tui_widgets.py`.
- Scope-Paths: src/pubrun/tui/widgets/details.py, src/pubrun/tui/widgets/actions.py, src/pubrun/tui/widgets/config.py, CHANGELOG.md, tests/test_tui_widgets.py
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Fix TUI git-pane crash and markup loss, Archive crash and silent no-op, and invalid TOML from Save Settings; add Textual Pilot tests for TUI wiring and widget failure paths
- Work-Kind: bug
- Priority: high
- Set: test-audit
- Order: 8
- Highest E allocated: 18
- Author: Antigravity
- Id: bwoyan
- Approval: 2026-11-24, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 approved (aw set): status set to approved
- 2026-11-23 /plan-review (uri/its_direct/pt3-claude-opus-5.5-1m-us): APPROVE WITH REVISIONS APPLIED; PR-001..PR-018 fixed (PR-001 git pane crash and PR-002 markup loss: E-06; PR-003 Archive crash and silent no-op: E-07; PR-004 Save Settings writes unloadable TOML: E-08); review record `.aw/records/reviews/20261123-test-audit-08-bwoyan-tui-interactive-wiring-and-widget-failure-path-tests.review.md`.
- 2026-11-23 to-review (Antigravity): authored from `/assess-testing` findings T-16 and T-17.
- 2026-11-23 draft (Antigravity): created.

## Goal

Make the pubrun terminal user interface (TUI, `pubrun ui`, built on the Textual library) fail its tests when the wiring between its panes or the error handling in its widgets breaks, and fix the three defects the review measured on those paths.

Today no test selects a run in the sidebar tree and checks the four workspace panes, and the Actions panel's archive, citation copy, delete dialog, and dry-run prune paths have no tests. The tests in this plan drive the real app with Textual's test harness (`App.run_test()`, which returns a `Pilot` that presses keys and waits for the screen to settle) and assert on the rendered text, the notifications, and the files on disk.

Writing those tests exposed three defects. Each was reproduced at review on Textual 8.2.8 and Python 3.14.6:

1. **Run details pane, git section.** `RunDetailsView.update_general_pane` (in `src/pubrun/tui/widgets/details.py`) reads `git.get('remote_url', {}).get('value')`. When a manifest stores `remote_url` as `null` or as a plain string, this raises `AttributeError`. Selecting such a run in the sidebar ends the whole TUI with exit code 1. The same block also inserts `commit`, `branch`, and the remote URL into Textual markup without escaping, so `[REDACTED]` inside a redacted remote URL (the form `src/pubrun/capture/redaction.py` `_redact_value_string_heuristics` writes for `https://user:password@host`) is shown as `https://user:@h/r.git`, and a branch containing `[/bad]` raises `MarkupError`. A `git` value that is not an object (for example `null`) raises `AttributeError` when it reaches the pane, which happens when a lock file and a startup manifest are both present.
2. **Archive action.** `ActionsPanel.archive_selected_run` (in `src/pubrun/tui/widgets/actions.py`) calls `archive_dir.mkdir(exist_ok=True)` before its `try` block. When `runs/archive` is a file, or the runs folder is read-only, the `FileExistsError` or `PermissionError` ends the TUI with exit code 1. When the run folder was deleted after the run was selected, the method returns without any message.
3. **Save Settings.** `dict_to_toml` (in `src/pubrun/tui/widgets/config.py`) escapes only backslashes and double quotes in strings, and writes lists with `json.dumps`, which escapes a character outside the Basic Multilingual Plane (for example an emoji) as a surrogate pair (`\ud83d\ude00`). TOML forbids raw newlines and control characters in a basic string and forbids surrogate escapes. At review, a `.pubrun.toml` whose `[diff] ignore_basic` list contained an emoji was rewritten by Save Settings into a file that `pubrun.config.load_local_config` then ignored with the warning `ignoring malformed config file ... Escaped character is not a Unicode scalar value`, so every local setting was lost.

### Work plan

```mermaid
flowchart TD
    subgraph TG1["Task group 1: production fixes"]
        E06["E-06: details.py git block: shape guards and markup escaping"]
        E07["E-07: actions.py archive: mkdir inside try, vanished-dir error"]
        E08["E-08: config.py dict_to_toml: JSON-escaped strings and lists"]
        E09["E-09: CHANGELOG.md Fixed entries"]
        E06 --> E09
        E07 --> E09
        E08 --> E09
    end
    subgraph TG2["Task group 2: test module and app wiring"]
        E01["E-01: module skeleton and helpers"]
        E02["E-02: tree selection updates all four panes; toggle sidebar"]
        E10["E-10: RunsSidebar search and scan failure"]
    end
    subgraph TG3["Task group 3: ActionsPanel"]
        E03["E-03: archive"]
        E11["E-11: citation copy and no-selection guard"]
        E12["E-12: ConfirmDeleteModal"]
        E13["E-13: dry-run prune"]
        E14["E-14: copy_to_clipboard per platform"]
    end
    subgraph TG4["Task group 4: other widgets"]
        E04["E-04: DiffView"]
        E15["E-15: LogViewer"]
        E05["E-05: ConfigPanel and dict_to_toml types"]
        E18["E-18: dict_to_toml escaping and Save Settings round trip"]
        E16["E-16: RunDetailsView git section and degraded states"]
        E17["E-17: RunResourcesView"]
    end
    E01 --> E02 & E10 & E03 & E11 & E12 & E13 & E14 & E04 & E15 & E05 & E18 & E16 & E17
    E06 --> E02 & E16
    E07 --> E03
    E08 --> E18
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item addresses one concern executable in one focused pass. Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

All new tests go in `tests/test_tui_widgets.py`. Every Pilot test uses the E-01 helper `_run_app(runs, body, monkeypatch)`, which starts `PubrunTUIApp(output_dir=str(runs))` under `app.run_test()`, records every `app.notify` call as a `(message, severity)` tuple in `notes`, awaits `body(app, pilot, notes)`, and returns `{"running": app.is_running, "return_code": app.return_code}`. Tests must use Python 3.8 syntax (`requires-python = ">=3.8"`).

### Task group 1: Production fixes

- [ ] E-06 In `src/pubrun/tui/widgets/details.py`, add a module-level helper `_format_remote_url(remote: Any) -> str` directly before `_format_os_text`, with the docstring `"""Return the display text for a manifest ``git.remote_url`` value."""`. When `remote` is a dict it uses `remote.get("value")`; it returns that value (or `remote` itself) when it is a non-empty `str`, and `"-"` otherwise. In `RunDetailsView.update_general_pane`, under `=== REPOSITORY PROVENANCE (GIT) ===`, replace `if r.manifest and "git" in r.manifest:` and `git = r.manifest["git"]` with `git = r.manifest.get("git") if isinstance(r.manifest, dict) else None` followed by `if isinstance(git, dict):`. In that branch wrap the commit, branch, and remote values as `_escape_markup(str(git.get('commit') or '-'))`, `_escape_markup(str(git.get('branch') or '-'))`, and `_escape_markup(_format_remote_url(git.get('remote_url')))`. In the `elif r.lock_data:` branch wrap `r.git_commit` and `r.cwd` the same way (`_escape_markup(str(r.git_commit or '-'))`, `_escape_markup(str(r.cwd or '-'))`). Leave the `Repo Dirty:` line (`str(git.get('dirty'))`) unchanged.
  - Depends on: none
  - Expected outcome: A run whose `git.remote_url` is `null`, a string, `{"representation": "unavailable"}`, or `{"representation": "plain", "value": <url>}` renders `  Remote URL:     -` or the URL text exactly. `[REDACTED]`, `[wip]`, `[bold]`, and `[/bad]` in commit, branch, remote URL, or lock `cwd` are shown literally and raise nothing. A `git` value that is not a dict uses the lock fallback (`  Commit Hash:   -`, `  Working Cwd:   <cwd>`). The OS line, the CPU line, and every other section are unchanged. Sibling `67hcid` edits the CPU line in the same function; the runner gives each plan its own worktree, and the two edits touch different lines.
  - Execution state: pending

- [ ] E-07 In `src/pubrun/tui/widgets/actions.py` `ActionsPanel.archive_selected_run`, split the guard `if not r or not r.run_dir.exists(): return` into `if not r: return` and `if not r.run_dir.exists():`, where the second branch calls `self.app.notify(f"Archive failed: run directory {r.run_dir.name} no longer exists.", severity="error")` and returns. Move `archive_dir.mkdir(exist_ok=True)` from before the `try:` to its first statement, so the existing `except Exception as e:` handler (`self.app.notify(f"Archive failed: {e}", severity="error")`) reports a folder-creation failure. Keep `zip_path = archive_dir / f"{r.run_id or r.run_dir.name}.zip"` before the `try:`. Do not touch the `self.app.post_message(self.app.RefreshSidebar())` call in this method; sibling `gzc672` replaces it with `_refresh_sidebar_message()` for type checking, and either form posts the same message.
  - Depends on: none
  - Expected outcome: When `runs/archive` is a file, pressing `#btn-archive-run` gives one `error` notification starting `Archive failed: `, the TUI keeps running, and the run folder is kept even with `#check-delete-raw` checked. When the run folder was removed after selection, it gives exactly `("Archive failed: run directory pubrun-<run_id> no longer exists.", "error")` and creates no `runs/archive` folder. The success path is unchanged (`Created archive: <run_id>.zip`).
  - Execution state: pending

- [ ] E-08 In `src/pubrun/tui/widgets/config.py`, add a module-level helper directly before `dict_to_toml`: `def _toml_scalar_or_list(value: Any) -> str:` with the docstring `"""Return a string or list as TOML, escaping quotes, backslashes, and control characters."""` and the body `return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")`. In `dict_to_toml`, replace the `str` branch (the `# Double escape backslashes and quotes in strings` comment and its two lines) and the `list` branch (`val_str = json.dumps(v)`) with `val_str = _toml_scalar_or_list(v)`. A JSON string with `ensure_ascii=False` is a valid TOML basic string for every escape JSON emits (`\"`, `\\`, `\n`, `\t`, `\uXXXX` for other C0 controls) except that JSON leaves U+007F raw, which TOML forbids; the `.replace` covers it.
  - Depends on: none
  - Expected outcome: `tomllib.loads(dict_to_toml({"core": {"k": v}}))` returns `v` unchanged for `'say "hi"'`, `"C:\\path\\to"`, `"line1\nline2"`, `"tab\there"`, `"bell\x07"`, `"del\x7f"`, and `"caf\u00e9 \U0001F600"`, and the same holds for the lists `["a\nb", "\U0001F600"]` and `["x\x7f"]`. Booleans, numbers, empty-section skipping, and the existing `tests/test_tui.py::test_tui_toml_serialization` output (`profile = "default"`, `auto_start = true`) are unchanged.
  - Execution state: pending

- [ ] E-09 In `CHANGELOG.md` `## [Unreleased]`, under the existing `### Fixed` subsection, add three entries in the file's style (a bold one-sentence lead, then plain prose): (1) the `pubrun ui` run details pane no longer closes the TUI when a manifest's `git.remote_url` is empty or a plain string, or its `git` section is not an object, and it now shows bracketed text in the commit, branch, remote URL, and working directory literally (a redacted remote URL keeps its `[REDACTED]` marker); (2) the Actions tab's Archive button now reports an error instead of closing the TUI when the `archive` folder cannot be created, and reports an error instead of doing nothing when the run folder no longer exists; (3) Save Settings now writes string and list values that contain newlines, control characters, or characters such as emoji in a form that pubrun can read back, instead of writing a `.pubrun.toml` that pubrun ignores as malformed. Follow the `AGENTS.md` dash rule: no em or en dashes in this prose.
  - Depends on: E-06, E-07, E-08
  - Expected outcome: `git diff CHANGELOG.md` shows only the three new entries under `## [Unreleased]` `### Fixed`.
  - Execution state: pending

### Task group 2: Test module and app wiring

- [ ] E-01 Create `tests/test_tui_widgets.py` with the module docstring `"""Textual Pilot tests for TUI wiring and widget failure paths (IPD bwoyan, Set test-audit)."""`, then `pytest.importorskip("textual")` before any `textual` or `pubrun.tui` import (so an install without the `tui` extra skips the module), `from pubrun.tui.widgets.config import _SELECT_EMPTY_VALUE` (the empty `Select` value on both Textual 0.x and 8.x; see Project conventions), and `try: import tomllib` / `except ImportError: import tomli as tomllib`. Add these module helpers: an autouse fixture `_isolated_config` that sets `XDG_CONFIG_HOME` and `APPDATA` under `tmp_path`, sets `NO_COLOR=1`, and deletes `PUBRUN_PROFILE` and `PUBRUN_META_REF`; `_write_run(runs, run_id, script="train.py", age=60.0, extra=None, logs=None)`, which writes `runs/pubrun-<run_id>/manifest.json` with `run.run_id`, a completed `status`, `timing.started_at_utc = time.time() - age`, `invocation.script.basename`, and `invocation.rerun_command = f"python {script}"`, merges `extra` at the top level, and writes each `logs` entry as a file; `_capture_notifications(app, monkeypatch)`; `_capture_posts(app, monkeypatch)`, which records `type(msg).__name__` for every `app.post_message`; `_log_lines(log)` returning `[line.text for line in log.lines]`; `_general_text(app)` returning `str(app.query_one("#lbl-general-info").render())`; `_tree_labels(app)` returning the labels of `#runs-tree` root children; `async _show_tab(app, pilot, tab_id)`, which sets `#workspace-tabs` `TabbedContent.active` and pauses twice (a `RichLog` records lines only after its tab has been shown); and `_run_app` as described above. These helpers mirror the ones in `tests/test_tui_bugs.py`; define them in the new module rather than importing from another test module, and do not repeat any test listed under Project conventions.
  - Depends on: none
  - Expected outcome: `python3 -m pytest tests/test_tui_widgets.py --collect-only -q --no-cov` collects the module without error; with `textual` unimportable the module reports `1 skipped`.
  - Execution state: pending

- [ ] E-02 Add class `TestAppWiring` with three tests. `test_tree_selection_updates_details_logs_resources_and_actions`: write runs `aaaa1111` (`train.py`, `age=10`, `console.log` = `"train log\n"`) and `bbbb2222` (`eval.py`, `age=20`, `console.log` = `"eval log\n"`); assert `_tree_labels(app) == ["train.py [aaaa1111] • COMPLETED", "eval.py [bbbb2222] • COMPLETED"]`; call `tree.select_node(tree.root.children[1])` and pause twice; assert `app.selected_run_info.run_id == "bbbb2222"`, `"  Run ID:        bbbb2222"` is a line of `_general_text(app)`, the `#logs-view` `log_files` names are `["console.log"]`, `#resources-body` text starts with `"No resource samples recorded for this run"`, and `#actions-view` `rerun_command == "python eval.py"`; then assert `return_code in (None, 0)`. `test_tree_selection_of_run_with_null_remote_url_keeps_app_running`: one run with `extra={"git": {"commit": "c" * 40, "remote_url": None}}`, select it, assert `"  Remote URL:     -"` is a line of `_general_text(app)`, `running is True`, and `return_code in (None, 0)`. `test_toggle_sidebar_binding_and_action`: assert `#sidebar` `display` is `True`, press `ctrl+s` and assert `False`, call `app.action_toggle_sidebar()` and assert `True`.
  - Depends on: E-01, E-06
  - Expected outcome: The three tests pass. Without E-06, the null-remote test fails because selecting the run raises `AttributeError` and the app exits (measured at review: `_general_text` was `Select a run to view details.`).
  - Execution state: pending

- [ ] E-10 Add class `TestRunsSidebar` with two tests. `test_search_filters_by_script_and_run_id_case_insensitively`: with runs `aaaa1111` (`train.py`) and `bbbb2222` (`eval.py`), set `#runs-search` `Input.value` to `"TRAIN"` and assert `_tree_labels(app) == ["train.py [aaaa1111] • COMPLETED"]`; set `"bbbb"` and assert `["eval.py [bbbb2222] • COMPLETED"]`; set `"zzz"` and assert `["No runs found"]` with that leaf's `data is None`; set `""` and assert two labels. `test_scan_failure_is_shown_as_a_tree_leaf`: monkeypatch `pubrun.tui.widgets.sidebar.scan_runs` to raise `RuntimeError("disk on fire")`; assert `_tree_labels(app) == ["Scan failed: disk on fire"]`, `#sidebar` `all_runs == []`, and `running is True`.
  - Depends on: E-01
  - Expected outcome: Both tests pass.
  - Execution state: pending

### Task group 3: `ActionsPanel`

- [ ] E-03 Add class `TestActionsArchive` with four tests. Each calls `panel.display_run(RunInfo(run_dir))` on `#actions-view` and presses `#btn-archive-run`. `test_archive_creates_zip_and_keeps_raw_dir`: a run `arch0001` with `console.log` and `sub/x.txt`; assert `notes == [("Created archive: arch0001.zip", "information")]`, `"RefreshSidebar"` not in `_capture_posts`, the zip at `runs/archive/arch0001.zip` has names `["console.log", "manifest.json", "sub/x.txt"]`, and the run folder still exists. `test_archive_with_delete_raw_removes_dir_and_refreshes_sidebar`: set `#check-delete-raw` to `True`; assert `("Deleted original uncompressed directory.", "information")` and `("Runs database and cache refreshed.", "information")` are in `notes`, `#sidebar` `all_runs == []`, the run folder is gone, and the zip exists. `test_archive_of_vanished_run_dir_reports_error`: `shutil.rmtree(run_dir)` after `display_run`; assert `notes == [("Archive failed: run directory pubrun-gone0001 no longer exists.", "error")]` and no `runs/archive`. `test_archive_dir_creation_failure_reports_error_and_keeps_app`: write a file at `runs/archive`, set `#check-delete-raw` to `True`; assert the severities are `["error"]`, the message starts with `"Archive failed: "`, `running is True`, and the run folder exists.
  - Depends on: E-01, E-07
  - Expected outcome: All four pass. Without E-07, the last two fail (measured at review: the vanished-folder test got `notes == []`, and the creation-failure test ended the app with `FileExistsError`).
  - Execution state: pending

- [ ] E-11 Add class `TestActionsCitations`. `test_copy_methods_copies_generated_report`, parametrized over `("btn-copy-md", "markdown")` and `("btn-copy-latex", "latex")`: monkeypatch `pubrun.tui.widgets.actions.copy_to_clipboard` to record its argument and return `True`; compute the expected text with `generate_report(hydrate_manifest(str(manifest_path), manifest)[0], fmt)`; assert `notes == [(f"Methods ({fmt}) copied to clipboard.", "information")]` and the recorded text equals the expected text. `test_copy_methods_clipboard_failure_warns`: `copy_to_clipboard` returns `False`; assert `notes == [("Failed to copy. Copy text manually.", "warning")]`. `test_copy_methods_without_manifest_reports_unavailable`: a folder `runs/pubrun-lock0001` with only `.pubrun.lock` (`pid` 999999, `hostname` `elsewhere-host`, `started_at_utc` now); press `#btn-copy-latex`; assert `notes == [("Citations not available.", "error")]`. `test_run_buttons_without_selection_ask_for_a_run`, parametrized over `btn-copy-rerun`, `btn-copy-md`, `btn-copy-latex`, `btn-archive-run`, and `btn-delete-selected`: press with no run displayed; assert `notes == [("Please select a run first.", "error")]` and no `runs/archive`.
  - Depends on: E-01
  - Expected outcome: All nine test cases pass.
  - Execution state: pending

- [ ] E-12 Add class `TestConfirmDeleteModal` with helper `_open_modal(app, run_dir)` (display the run on `#actions-view`, press `#btn-delete-selected`). `test_typing_gates_confirm_and_cancel_keeps_run`: assert `app.screen` is a `ConfirmDeleteModal` and `#btn-confirm-del` is disabled; set `#input-confirm-yes` to `"no"` (still disabled), `" YES "` (enabled), `"yess"` (disabled); press `#btn-cancel-del`; assert the modal closed, `notes == []`, and the run folder exists. `test_typed_yes_and_confirm_deletes_run`: type `"yes"`, press `#btn-confirm-del`; assert `("Successfully deleted run dele0002", "information")` is in `notes`, the panel's `run_info is None`, and the folder is gone. `test_delete_error_is_reported_and_run_kept`: with the modal open, monkeypatch `pubrun.tui.widgets.actions.shutil.rmtree` to raise `PermissionError("read-only volume")`, call `app.screen.dismiss(True)`; assert `notes == [("Deletion failed: read-only volume", "error")]`, `run_info is not None`, and the folder exists. `tests/test_tui_bugs.py` already covers deleting a run whose `run_id` is `None`; do not repeat it.
  - Depends on: E-01
  - Expected outcome: All three pass.
  - Execution state: pending

- [ ] E-13 Add class `TestBulkPruneDryRun` with `test_dry_run_lists_candidates_and_deletes_nothing`: write run `old00001` with `age=40 * 86400`; call `_show_tab(app, pilot, "tab-actions")`, start `_capture_posts`, press `#btn-prune-dry`, pause twice; assert the `#cleanup-log-output` lines start with `"Scanning runs for pruning (dry_run=True)..."` and contain `"1 run(s) eligible for removal."`, `"[INFO ] Dry run: no files were deleted."`, and a line starting `"1   old00001"`; assert `"RefreshSidebar"` was not posted, `notes == []`, and the run folder exists. `tests/test_tui_bugs.py` already covers invalid and canonical age units; do not repeat them.
  - Depends on: E-01
  - Expected outcome: The test passes.
  - Execution state: pending

- [ ] E-14 Add class `TestCopyToClipboard` (no app) with helper `_patch(monkeypatch, platform, outcomes)` that replaces `pubrun.tui.widgets.actions.sys` with `types.SimpleNamespace(platform=platform)` and `pubrun.tui.widgets.actions.subprocess` with a namespace whose `run` records `(cmd, input, text, check)` and raises `outcomes.get(cmd[0])` when set, and whose `CalledProcessError` is `subprocess.CalledProcessError`. Patch the module attributes, not the global `sys.platform`, so pytest itself is unaffected. Tests: `test_darwin_uses_pbcopy` (`calls == [(["pbcopy"], "hi", True, True)]`, returns `True`); `test_win32_uses_clip` (`[(["clip"], "hi", True, True)]`); `test_linux_uses_xclip_first` (one call, `["xclip", "-selection", "clipboard"]`); `test_linux_falls_back_to_xsel` (`xclip` raises `FileNotFoundError`; commands are xclip then `["xsel", "--clipboard", "--input"]`; returns `True`); `test_linux_both_missing_returns_false` (`xclip` raises `FileNotFoundError`, `xsel` raises `CalledProcessError`; returns `False` after two calls); `test_darwin_failure_returns_false`.
  - Depends on: E-01
  - Expected outcome: All six pass on every operating system.
  - Execution state: pending

### Task group 4: Other widgets

- [ ] E-04 Add class `TestDiffViewStates`. A helper writes runs `diffa001` (`extra={"custom": {"x": 1}}`) and `diffb002` (`{"custom": {"x": 2}}`); another sets `#select-diff-a` and `#select-diff-b` values to the two run folder strings. Every test first calls `_show_tab(app, pilot, "tab-diff")`, except the dropdown test. Tests: `test_same_run_guard` (both selects on A, press `#btn-execute-diff`; `#diff-output-area` lines `== ["Warning: Cannot compare a run against itself."]` and `notes == [("Selected the same run for both parameters.", "warning")]`); `test_missing_manifest`, parametrized over `"a"` and `"b"` (delete that run's `manifest.json`, call `run_difference()`; lines `== [f"Error: Manifest {X} not found at {path}"]`); `test_corrupt_manifest_reports_error` (B's manifest is `{not json`; line 0 `"Computing semantic difference..."`, line 1 starts `"Error computing diff: Expecting property name"`); `test_execute_then_clear` (lines start `"=== PUBRUN SEMANTIC DIFFERENCE ==="` and include `"MODIFIED KEYS (~):"`, `"  ~ custom.x:"`, `"      - Old: 1"`, `"      + New: 2"`; pressing `#btn-clear-diff` empties the log); `test_render_diff_report_branches` (call `render_diff_report` with one added, one removed, one `path_split` modified key with added `/opt/bin` and removed `/usr/old`, one modified key with `note` `"minor bump"`, one same key, and `warnings=["parent missing"]`; line 0 is `"[Warning] parent missing"` and the lines include every section header, `"      + /opt/bin"`, `"      - /usr/old"`, `"      ! Note: minor bump"`, and `"  = run.id: x"`; a report whose only entries are `same` ends with `"No differences detected between the selected runs."`); `test_show_same_checkbox_populates_unchanged_section` (`"UNCHANGED KEYS (=):"` absent, then present after setting `#check-show-same` to `True`); `test_populate_dropdowns_keeps_valid_selection_and_drops_stale_one` (after `populate_dropdowns(all_runs)` both values are kept; after removing run B, A is kept and B equals `_SELECT_EMPTY_VALUE`). `tests/test_tui_bugs.py` `TestDiffView` already covers blank selections and the depth fallback; do not repeat them.
  - Depends on: E-01
  - Expected outcome: All eight test cases pass.
  - Execution state: pending

- [ ] E-15 Add class `TestLogViewerStates`; each test first calls `_show_tab(app, pilot, "tab-logs")`. `test_missing_dir_and_dir_without_logs`: `display_run_logs(tmp_path / "does-not-exist")` leaves `log_files == []` and the `#log-content-area` empty; a run folder with no log files gives lines `== ["No log files found in this run directory."]`. `test_select_switches_file_and_wrap_toggles`: a run with `console.log` (`"from console\n"`) and `stderr.txt` (`"from stderr\n"`); `#select-log-file` defaults to `console.log`; setting it to `stderr.txt` shows `"from stderr"` and not `"from console"`; `wrap` starts `False`, and each press of `#btn-toggle-wrap` flips it. `test_missing_and_unreadable_log_file`: `load_log_file` on a missing path gives `["Selected log file does not exist."]`; on a folder named `a_directory.log` gives one line starting `"Failed to load log file: "`. `tests/test_tui_bugs.py` `TestLogViewer` already covers blank selections; do not repeat it.
  - Depends on: E-01
  - Expected outcome: All three pass on every operating system (the unreadable case uses a folder, not file permissions).
  - Execution state: pending

- [ ] E-05 Add classes `TestConfigPanelStates` and `TestDictToToml`. `TestConfigPanelStates.test_reset_reloads_resolved_values`: set `#cfg-output-dir` to `"./elsewhere/"`, press `#btn-reset-config`; assert the value is `""` again, `notes == [("Settings reloaded to current resolved values.", "information")]`, and no `.pubrun.toml` was written. `TestConfigPanelStates.test_write_error_is_reported`: make `tmp_path / ".pubrun.toml"` a folder, press `#btn-save-config`; assert severities `["error"]`, the message starts `"Failed to write configuration: "`, and `running is True`. `TestDictToToml.test_scalar_types_and_sections_round_trip`: `dict_to_toml({"a": 1.5, "b": [1, "x", True], "f": False, "n": 3, "empty": {}, "g": {"h": {"i": 1}, "e": {}}})` starts with the lines `["a = 1.5", 'b = [1, "x", true]', "f = false", "n = 3"]`, has `[g.h]` but neither `[empty]` nor `[g.e]`, and `tomllib.loads` of it equals the input without the empty sections. `tests/test_tui_bugs.py` `TestConfigPanel` already covers `Select.NULL` handling; do not repeat it.
  - Depends on: E-01
  - Expected outcome: All three pass on the current `dict_to_toml` and after E-08.
  - Execution state: pending

- [ ] E-18 Add class `TestTomlEscaping`. `test_strings_round_trip` and `test_string_lists_round_trip`, parametrized over the values listed in E-08's expected outcome, assert `tomllib.loads(dict_to_toml(...))` returns the input. `test_save_keeps_unrelated_non_bmp_list_value_loadable`: write `.pubrun.toml` with `[core] output_dir = "./myruns"` and `[diff] ignore_basic = ["caf\u00e9 \U0001F600"]` (TOML escapes written literally), press `#btn-save-config`; assert `notes[0] == ("Configuration saved to: .pubrun.toml", "information")`, then `load_local_config(tmp_path)["diff"]["ignore_basic"] == ["caf\u00e9 \U0001F600"]` and `["core"]["output_dir"] == "./myruns"`.
  - Depends on: E-01, E-08
  - Expected outcome: All ten test cases pass. Without E-08, five cases fail (measured at review: `line1\nline2`, `bell\x07`, `del\x7f`, the emoji list, and the save test, where `load_local_config` returned `None`).
  - Execution state: pending

- [ ] E-16 Add classes `TestRunDetailsGit` and `TestRunDetailsStates`, with a module helper `_render_details(tmp_path, run_dir, monkeypatch)` that calls `#details-view` `display_run(RunInfo(run_dir))` inside `_run_app` and returns `_general_text(app)`. `TestRunDetailsGit.test_remote_url_shapes`, parametrized over `(None, "-")`, `("https://example.com/repo", "https://example.com/repo")`, `({"representation": "unavailable"}, "-")`, `({"representation": "plain", "value": None}, "-")`, `({"representation": "plain", "value": "git@host:r.git"}, "git@host:r.git")`, `({"representation": "plain", "value": "https://user:[REDACTED]@h/r.git"}, "https://user:[REDACTED]@h/r.git")`, and `({"representation": "plain", "value": "https://h/[/x]"}, "https://h/[/x]")`, asserts the lines include `"  Remote URL:     " + expected` and `"  Commit Hash:   " + "c" * 40`. `test_missing_remote_url_key` asserts `"  Remote URL:     -"`. `test_branch_and_commit_markup_is_shown_literally` (commit `"[bold]c0ffee"`, branch `"feat/[wip]"`) asserts both are shown verbatim. `test_unbalanced_closing_tag_in_branch_does_not_raise` (branch `"[/bad]"`) asserts `"  Branch:        [/bad]"`. `test_non_dict_git_section_falls_back_to_lock_fields`, parametrized over `None`, `["x"]`, and `"abc"`, writes a manifest with that `git` value plus a `.pubrun.lock` (`pid` 999999, `hostname` `elsewhere-host`, `cwd` `"/tmp/[work]"`, `started_at_utc` now) and asserts the two lines after `"=== REPOSITORY PROVENANCE (GIT) ==="` are `["  Commit Hash:   -", "  Working Cwd:   /tmp/[work]"]`. `TestRunDetailsStates.test_degraded_run_without_manifest_or_lock`: an empty run folder shows `"  Status:        CRASHED"`, `"  (No resource metadata recorded)"`, and `"  (No git information available)"`. `test_assess_run_failure_falls_back`: monkeypatch `pubrun.report.reproducibility.assess_run` to raise; the line after `"=== REPRODUCIBILITY & EVIDENCE ==="` is `"  (Reproducibility assessment unavailable for this run)"`. `test_refresh_live_metrics_reloads_running_run_only`: a lock-only run `live0001` (`hostname` `elsewhere-host`, `started_at_utc` now, `argv` `["--step", "1"]`), which `RunInfo` classifies running because it cannot check a process id on another host younger than 48 hours; assert `"  Arguments:     --step 1"`, rewrite the lock with `["--step", "2"]`, call `refresh_live_metrics()`, assert `"  Arguments:     --step 2"`; then monkeypatch `pubrun.tui.widgets.details.RunInfo` to record its argument and raise `OSError`, call again, and assert one call and unchanged text; then set `run_info` to a completed run and assert `refresh_live_metrics()` makes no call. `tests/test_tui_bugs.py` already covers the GPU and OS lines, and sibling `67hcid` covers the CPU line; do not repeat them.
  - Depends on: E-01, E-06
  - Expected outcome: All sixteen test cases pass. Without E-06, ten fail (measured at review: `AttributeError` for `None`, string, and non-dict `git`; `MarkupError` for `[/x]` and `[/bad]`; `[REDACTED]` and `[bold]` dropped from the text).
  - Execution state: pending

- [ ] E-17 Add class `TestRunResourcesStates`. `test_corrupt_events_file_shows_no_samples`: a run whose `events.jsonl` is `"{broken\nnot json at all\n"`; after `#resources-view` `display_run`, `#resources-body` text starts with `"No resource samples recorded for this run"`. `test_reader_exception_is_rendered_not_raised`: monkeypatch `pubrun.report.diagnostics.read_resource_series` to raise `RuntimeError("bad series")`, with an empty `events.jsonl` present; the body text is exactly `"Could not render resource usage: RuntimeError: bad series"`.
  - Depends on: E-01
  - Expected outcome: Both pass.
  - Execution state: pending

## Project conventions discovered (Step 0)

- CI runs `pytest tests/ -v` after `pip install -e ".[dev,tui]"` on 3 operating systems and Python 3.8 to 3.14 (`.github/workflows/ci.yml`, step "Run tests"). The `tui` extra pins `textual>=0.80.0` (`pyproject.toml` `[project.optional-dependencies] tui`).
- Python 3.8 resolves to a Textual 0.x release and Python 3.9+ to Textual 8.x. The empty `Select` value is `Select.BLANK` on 0.x and `Select.NULL` on 8.x; `src/pubrun/tui/widgets/config.py` `_SELECT_EMPTY_VALUE` resolves the right one (commit `c3734e7`, "Fix cross-platform and Python 3.8-3.11 CI failures"). Tests compare against `_SELECT_EMPTY_VALUE`, never a literal.
- `pyproject.toml` `addopts` adds coverage (`--cov=src ...`); targeted validation runs pass `--no-cov`.
- The autouse fixture `tests/conftest.py` `isolated_cwd` changes directory to `tmp_path` and patches `pathlib.Path.cwd`, so `ConfigPanel.save_settings` writes `tmp_path / ".pubrun.toml"`.
- A Textual `RichLog` records written lines only after its tab has been shown; tests that read `#diff-output-area`, `#log-content-area`, or `#cleanup-log-output` call `_show_tab` first. `tests/test_tui_bugs.py` `_show_tab` documents the same rule.
- `RunInfo._load_from_lock` (`src/pubrun/status.py`) classifies a lock from another host as running when it is younger than 48 hours (`if age > 172800:  # 48 hours`), without checking the process id. Tests that need a running run use `hostname` `elsewhere-host`, not the current pid.
- A manifest alone with a non-dict `git` never reaches the details pane: `RunInfo._load_from_manifest` calls `git.get("commit")` and fails, and `scan_runs` catches the error and lists the run as crashed. The pane sees such a manifest only through the lock path (a running run's startup manifest), which is what `test_non_dict_git_section_falls_back_to_lock_fields` builds.
- Existing TUI tests live in `tests/test_tui.py` (plans `whacr3` and others, executed) and `tests/test_tui_bugs.py` (`TestRefreshSidebarRouting`, `TestActionsPanel`, `TestConfigPanel`, `TestDiffView`, `TestRunDetailsGpu`, `TestRunDetailsOsLine` from executed plan `46fixy`, `TestLogViewer`). This plan adds only the new module and repeats none of their cases.
- Sibling plans touching the same production files: `gzc672` (reviewed, pending) edits `src/pubrun/tui/widgets/actions.py` `on_button_pressed`, `handle_deletion_result`, and the three `RefreshSidebar` posts for type checking; `67hcid` (reviewed, pending, from backlog `0mnekm`) edits the CPU line of `details.py` `update_general_pane` and `tests/test_tui_bugs.py`. The runner gives each plan its own worktree and merges through its revalidation gate; the edits touch different lines.
- Tests must use Python 3.8 syntax (`requires-python = ">=3.8"`).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| T-16 | High | Low | QA engineer / UX reviewer | `src/pubrun/tui/widgets/actions.py`; `src/pubrun/tui/app.py` `on_tree_node_selected`; `src/pubrun/tui/widgets/sidebar.py` | Archive, clipboard, Markdown and LaTeX copy, delete dialog typing and cancel, dry-run prune, four-pane tree-selection wiring, sidebar toggle, and sidebar search and errors have no tests. |
| T-17 | Medium | Low | QA engineer / UX reviewer | `src/pubrun/tui/widgets/diff.py`, `viewer.py`, `config.py`, `details.py`, `resources.py` | Error and interactive states across five widgets are untested, and `details.py` raises `AttributeError` when `git.remote_url` is `None`. |
| PR-001 (review) | High | Low | QA engineer | `details.py` `update_general_pane` `git.get('remote_url', {}).get('value')`; Pilot probe: selecting the run exited the app with return code 1 | A `null` or string `git.remote_url`, or a non-dict `git` reaching the pane, closes the TUI. |
| PR-002 (review) | Medium | Low | UX reviewer | Same block interpolates `commit`, `branch`, remote URL, `cwd` unescaped; probe showed `https://user:@h/r.git` and `feat/` | Redaction markers and bracketed names disappear, and `[/bad]` raises `MarkupError`. |
| PR-003 (review) | High | Low | QA engineer | `actions.py` `archive_selected_run` `archive_dir.mkdir(exist_ok=True)` before `try:` | A file at `runs/archive` or a read-only runs folder closes the TUI; a vanished run folder gives no message. |
| PR-004 (review) | High | Low | QA engineer | `config.py` `dict_to_toml`; probe: Save Settings rewrote an emoji list as `\ud83d\ude00`, then `load_local_config` returned `None` | Save Settings writes TOML that pubrun ignores as malformed, losing every local setting. |

## Proposed changes (ordered, validatable)

1. Guard the git section's value shapes and escape its markup in `RunDetailsView` (E-06; Remediation Risk: Low, because only the git block changes and every new branch renders `-` or the escaped text).
2. Report archive folder and vanished-run failures through the existing `Archive failed:` notification (E-07; Remediation Risk: Low, because the success path is unchanged).
3. Serialize TOML strings and lists through `json.dumps(ensure_ascii=False)` with a U+007F escape (E-08; Remediation Risk: Low, because the output for plain ASCII strings is byte-identical, and the round-trip tests cover the rest).
4. Record the three fixes in `CHANGELOG.md` (E-09; Remediation Risk: Low).
5. Add `tests/test_tui_widgets.py` with the helper skeleton, app wiring, and sidebar tests (E-01, E-02, E-10; Remediation Risk: Low).
6. Add `ActionsPanel` tests: archive, citations and guard, delete dialog, dry-run prune, clipboard (E-03, E-11 to E-14; Remediation Risk: Low).
7. Add `DiffView`, `LogViewer`, `ConfigPanel` and `dict_to_toml`, `RunDetailsView`, and `RunResourcesView` tests (E-04, E-05, E-15 to E-18; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Optional injectable seams for `ConfigPanel.save_settings` and `ActionsPanel.run_bulk_prune` stdout capture: deferred alongside the CLI and diagnostics testable seams, because Pilot tests drive the real widgets.
  - Carrier: riulkx
- The `Repo Dirty:` line prints `None` when `git.dirty` was not captured (`check_dirty = false`, or `git status` failed). This plan leaves that line as it is, because the value is a recorded tri-state and choosing a display word is a UX decision outside a test plan.
  - Carrier-Declined: characterized only; no test pins the `None` text, so a later display change needs no test edit.
- Local validation covers Textual 8.2.8 on Python 3.14 only. The Textual 0.x branch (Python 3.8) and Windows and macOS are exercised only by the CI matrix, which needs a push that only a human may request.
  - Carrier-Declined: the matrix run happens when the maintainer pushes; the tests avoid version-specific APIs (`_SELECT_EMPTY_VALUE`, `Tree.select_node`, module-level patching instead of `sys.platform`).

## Scope check

- Over-scope: none.
- Under-scope: none after review. Review added the archive fix (E-07), the TOML fix (E-08), the markup escaping in E-06, and the `CHANGELOG.md` entry (E-09), because the tests the original plan asked for in E-03 and E-05 cannot pass without them, and the original E-01 guard alone left the pane dropping `[REDACTED]` from real redacted remote URLs.

## Required tests / validation

- Run both `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py tests/test_tui_bugs.py -v --no-cov` and `pytest tests/test_tui_widgets.py -v --no-cov`: 0 failures, and no `SKIPPED` line when the `tui` extra is installed.
- The fix-reverted and mutation checks named in each `V-*` item.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- `grep -rln -i "tui\|dict_to_toml\|remote_url\|archive" .aw/records/specs` found no spec at review; no spec change.
- The `docs/cli.md` section for the `ui` command lists the tabs and the `tui` extra and describes none of the changed behavior; no change.
- `CHANGELOG.md` records the three fixes (E-09).

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

Mutation-check procedure: copy the production file aside, apply the one change, run the named tests with `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_tui_widgets.py -q --no-cov -p no:cacheprovider -k <selector>`, paste the summary line, restore the file from the copy, and confirm `git diff --stat` shows only this plan's intended edits. A fix-reverted check is the same procedure with the file's E-06, E-07, or E-08 edit reverted to `git show HEAD:<path>`. Never commit a mutated file.

- [ ] V-01 validates E-01
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py --collect-only -q --no-cov` (70 tests at review), and of `python3 -c "import sys, pytest; sys.modules['textual'] = None; sys.exit(pytest.main(['--no-cov', '-q', 'tests/test_tui_widgets.py']))"` reporting `1 skipped`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestAppWiring -v --no-cov` with 3 passed; the fix-reverted check for `details.py` with selector `null_remote_url` (1 failure); and three mutation checks in `src/pubrun/tui/app.py`, each giving at least 1 failure with selector `TestAppWiring`: delete the line `self.query_one("#logs-view", LogViewer).display_run_logs(r_info.run_dir)`; delete the line `self.query_one("#resources-view", RunResourcesView).display_run(r_info)`; replace `sidebar.display = not sidebar.display` with `pass` (each measured at review: 1 failure).
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestActionsArchive -v --no-cov` with 4 passed; the fix-reverted check for `actions.py` with selector `TestActionsArchive` (2 failures at review); and three mutation checks in `src/pubrun/tui/widgets/actions.py` `archive_selected_run`, each at least 1 failure: replace `if delete_raw:` with `if False:`; replace `r.run_dir.rglob("*")` with `r.run_dir.glob("*")`; replace the `self.app.post_message(self.app.RefreshSidebar())` line in this method (or `_refresh_sidebar_message()` if `gzc672` merged first) with `pass`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestDiffViewStates -v --no-cov` with 8 passed, and six mutation checks in `src/pubrun/tui/widgets/diff.py`, each at least 1 failure with selector `TestDiffViewStates`: replace `if run_dir_a == run_dir_b:` with `if False:`; replace `for p_sub in mod.get("removed", []):` with `for p_sub in []:`; replace `if note:` with `if False:`; replace `show_same = self.query_one("#check-show-same", Checkbox).value` with `show_same = False`; replace `select_a.value = prev_a` with `pass`; replace `self.query_one("#diff-output-area", RichLog).clear()` with `pass`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py -k "TestConfigPanelStates or TestDictToToml or toml_serialization" -v --no-cov` with 4 passed (3 in `tests/test_tui_widgets.py` plus `test_tui_toml_serialization`), and four mutation checks in `src/pubrun/tui/widgets/config.py`, each at least 1 failure with selector `"TestConfigPanelStates or TestDictToToml"`: in `dict_to_toml` replace `if v:` with `if True:`; replace `val_str = "true" if v else "false"` with `val_str = str(int(v))`; in `ConfigPanel.on_button_pressed` delete the `self.load_settings()` line under `btn-reset-config`; in `save_settings` replace `self.app.notify(f"Failed to write configuration: {e}", severity="error")` with `pass`.
  - Observed evidence:
  - Result: pending

- [ ] V-06 validates E-06
  - Required evidence: Pasted `git diff -- src/pubrun/tui/widgets/details.py` showing only the new `_format_remote_url` helper and the git block of `update_general_pane`; pasted output of `python3 -m pytest tests/test_tui_widgets.py tests/test_tui_bugs.py -k "TestRunDetails or null_remote_url" -v --no-cov` with 0 failures; and two mutation checks, each at least 1 failure with selector `TestRunDetailsGit`: replace `git = r.manifest.get("git") if isinstance(r.manifest, dict) else None` and `if isinstance(git, dict):` with the old `if r.manifest and "git" in r.manifest:` and `git = r.manifest["git"]` (3 failures at review); delete the two `isinstance(remote, dict)` lines of `_format_remote_url` (3 failures at review).
  - Observed evidence:
  - Result: pending

- [ ] V-07 validates E-07
  - Required evidence: Pasted `git diff -- src/pubrun/tui/widgets/actions.py` showing only the split guard and the moved `mkdir` in `archive_selected_run`; pasted output of `python3 -m pytest tests/test_tui_widgets.py -k "vanished or creation_failure" -v --no-cov` with 2 passed; and two mutation checks with selector `TestActionsArchive`, each at least 1 failure: move `archive_dir.mkdir(exist_ok=True)` back before `try:`; delete the `notify` line containing `no longer exists.`.
  - Observed evidence:
  - Result: pending

- [ ] V-08 validates E-08
  - Required evidence: Pasted `git diff -- src/pubrun/tui/widgets/config.py` showing only `_toml_scalar_or_list` and the two replaced branches of `dict_to_toml`; pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestTomlEscaping -v --no-cov` with 10 passed (also required by V-18); and one mutation check: replace the helper body with `return json.dumps(value, ensure_ascii=False)` (at least 1 failure with selector `TestTomlEscaping`, the `del\x7f` cases).
  - Observed evidence:
  - Result: pending

- [ ] V-09 validates E-09
  - Required evidence: Pasted `git diff -- CHANGELOG.md` showing the three entries under `## [Unreleased]` `### Fixed` and nothing else, and pasted output of `git diff -U0 -- CHANGELOG.md | grep -nP '^\+.*[\x{2013}\x{2014}]'` with no match.
  - Observed evidence:
  - Result: pending

- [ ] V-10 validates E-10
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestRunsSidebar -v --no-cov` with 2 passed, and three mutation checks in `src/pubrun/tui/widgets/sidebar.py` `load_runs`, each at least 1 failure with selector `TestRunsSidebar`: delete `filter_text = filter_text.lower()`; replace `(r.script and filter_text in r.script.lower())` with `False`; replace `Text(f"Scan failed: {e}"` with `Text("Scan failed"`.
  - Observed evidence:
  - Result: pending

- [ ] V-11 validates E-11
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestActionsCitations -v --no-cov` with 9 passed, and three mutation checks in `src/pubrun/tui/widgets/actions.py` `ActionsPanel.on_button_pressed`, each at least 1 failure with selector `TestActionsCitations`: replace `fmt = "markdown" if event.button.id == "btn-copy-md" else "latex"` with `fmt = "markdown"`; change `severity="warning"` on the `Failed to copy. Copy text manually.` notification to `severity="information"`; in the no-selection guard tuple replace `"btn-copy-latex", "btn-archive-run", "btn-delete-selected"` with `"btn-copy-latex", "btn-delete-selected"`.
  - Observed evidence:
  - Result: pending

- [ ] V-12 validates E-12
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestConfirmDeleteModal -v --no-cov` with 3 passed, and three mutation checks in `src/pubrun/tui/widgets/actions.py`, each at least 1 failure with selector `TestConfirmDeleteModal`: in `ConfirmDeleteModal.on_input_changed` replace `event.value.strip().lower()` with `event.value.lower()`; replace the `btn-cancel-del` branch's `self.dismiss(False)` with `self.dismiss(True)`; in `handle_deletion_result` replace `self.app.notify(f"Deletion failed: {e}", severity="error")` with `pass`.
  - Observed evidence:
  - Result: pending

- [ ] V-13 validates E-13
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestBulkPruneDryRun -v --no-cov` with 1 passed, and two mutation checks in `ActionsPanel.run_bulk_prune`, each 1 failure: replace `if not dry_run:` with `if True:`; replace the `dry_run=dry_run` argument of `clean_runs` with `dry_run=False`.
  - Observed evidence:
  - Result: pending

- [ ] V-14 validates E-14
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestCopyToClipboard -v --no-cov` with 6 passed, and two mutation checks in `copy_to_clipboard`, each at least 1 failure: remove `, ["xsel", "--clipboard", "--input"]` from the Linux command list; replace `subprocess.run(["clip"]` with `subprocess.run(["pbcopy"]`.
  - Observed evidence:
  - Result: pending

- [ ] V-15 validates E-15
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestLogViewerStates -v --no-cov` with 3 passed, and three mutation checks in `src/pubrun/tui/widgets/viewer.py`, each at least 1 failure: in `on_button_pressed` replace `log_content.wrap = not log_content.wrap` with `pass`; in `on_select_changed` replace `if event.select.id == "select-log-file" and` with `if False and`; replace the text `"No log files found in this run directory."` with `"No logs."`.
  - Observed evidence:
  - Result: pending

- [ ] V-16 validates E-16
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k "TestRunDetailsGit or TestRunDetailsStates" -v --no-cov` with 16 passed; the fix-reverted check for `details.py` with selector `TestRunDetailsGit` (10 failures at review); and three mutation checks in `src/pubrun/tui/widgets/details.py`, each at least 1 failure with selector `TestRunDetailsStates`: in `refresh_live_metrics` replace `self.run_info = refreshed` and the following `self.update_general_pane()` with `pass`; replace `if self.run_info and self.run_info.status == STATUS_RUNNING:` with `if self.run_info:`; replace the text `(Reproducibility assessment unavailable for this run)` with `(unavailable)`.
  - Observed evidence:
  - Result: pending

- [ ] V-17 validates E-17
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestRunResourcesStates -v --no-cov` with 2 passed, and one mutation check in `src/pubrun/tui/widgets/resources.py`: replace `f"Could not render resource usage: {type(e).__name__}: {e}"` with `f"Could not render resource usage: {e}"` (1 failure).
  - Observed evidence:
  - Result: pending
- [ ] V-18 validates E-18
  - Required evidence: Pasted output of `python3 -m pytest tests/test_tui_widgets.py -k TestTomlEscaping -v --no-cov` with 10 passed, and the fix-reverted check for `config.py` with selector `TestTomlEscaping` (5 failures at review: `test_strings_round_trip` for `line1\nline2`, `bell\x07`, and `del\x7f`; `test_string_lists_round_trip` for the emoji list; and `test_save_keeps_unrelated_non_bmp_list_value_loadable`).
  - Observed evidence:
  - Result: pending


## Approval and execution gate

- Size assessment: exception
- Cohesion rationale: 18 E-items exceed the 5-item guidance (`IPD-Z603`); the 5 Scope-Paths are within it. Each E-item is one focused edit, and the plan has one subject: the TUI widget tests named by findings T-16 and T-17, which the orchestrator `vdxiw8` assigns to this plan as one row (Order 08). The three production fixes and the `CHANGELOG.md` entry are included because tests the original E-03 and E-05 asked for cannot pass without them, and they sit on the code those tests exercise. Splitting would add new Set members and change the orchestrator's child table, which this plan cannot do.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no open question.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries (`src/pubrun/tui/widgets/details.py`, `src/pubrun/tui/widgets/actions.py`, `src/pubrun/tui/widgets/config.py`, `CHANGELOG.md`, `tests/test_tui_widgets.py`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`. The mutation checks temporarily edit `src/pubrun/tui/app.py`, `sidebar.py`, `diff.py`, `viewer.py`, and `resources.py`; restore each one, and do not commit them.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit bwoyan -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize bwoyan`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize bwoyan` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
