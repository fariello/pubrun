# IPD: Use monkeypatch in test_tui_missing_dependencies_prints_notice to restore sys.modules

- Date: 2026-11-24
- Kind: child
- Concern: Test isolation for `sys.modules["pubrun.tui.app"]` across TUI test modules
- Scope: Update `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` to remove `sys.modules["pubrun.tui.app"]` via pytest's `monkeypatch` fixture so the original module object is restored on teardown, and add a behavioral check confirming `sys.modules["pubrun.tui.app"]` identity is preserved across `tests/test_tui.py` and `tests/test_tui_widgets.py`.
- Scope-Paths: tests/test_tui.py
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: simple
- Short-Description: Restore sys.modules['pubrun.tui.app'] via monkeypatch in test_tui_missing_dependencies_prints_notice
- Work-Kind: bug
- Priority: low
- From-Backlog: o9c3gr
- Blocks-Release: next
- Set: o9c3gr
- Order: 1
- Highest E allocated: 02
- Author: Antigravity
- Id: lv41re
- Approval: 2026-11-25, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003
- 2026-11-25 to-review (Antigravity): graduated from backlog item `o9c3gr` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Prevent `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` from permanently deleting `sys.modules["pubrun.tui.app"]`, which otherwise forces later tests in the same pytest process to re-import a second `PubrunTUIApp` class object whose nested `RefreshSidebar` message class does not match handlers bound to the module collected by `tests/test_tui_widgets.py`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Restore sys.modules entry via monkeypatch

- [x] E-01 Update `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` to accept pytest's `monkeypatch` fixture, replace `if "pubrun.tui.app" in sys.modules: del sys.modules["pubrun.tui.app"]` with `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)`, and update the inline comment above it to explain that the entry is temporarily removed and restored on teardown.
  - Depends on: none
  - Expected outcome: `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` still simulates missing `textual` dependencies and asserts exit code 1 plus the friendly error notice on `stderr`, while pytest automatically restores any pre-existing `sys.modules["pubrun.tui.app"]` entry when the test finishes (and leaves `sys.modules` clean when the entry was absent, including in `no-tui` environments).
  - Execution state: performed

- [x] E-02 Add a behavioral regression test in `tests/test_tui.py` (guarded with `pytest.importorskip("textual")`) that pre-loads `pubrun.tui.app`, invokes `test_tui_missing_dependencies_prints_notice(capsys, inner_mp)` inside `with monkeypatch.context() as inner_mp:`, and asserts after exiting the context that `sys.modules["pubrun.tui.app"]`, `PubrunTUIApp`, and `PubrunTUIApp.RefreshSidebar` retain exact object identity; then verify `tests/test_tui.py` and `tests/test_tui_widgets.py` pass together in the same pytest process.
  - Depends on: E-01
  - Expected outcome: The new regression test in `tests/test_tui.py` skips cleanly when `textual` is absent (`pytest.importorskip("textual")`), fails if `test_tui_missing_dependencies_prints_notice` deletes `sys.modules["pubrun.tui.app"]` without restoring it on `monkeypatch` teardown, and passes when E-01 is in place; combined runs of `tests/test_tui.py` and `tests/test_tui_widgets.py` exit 0 in forward order, reversed file order, and shuffled order (`-p randomly --randomly-seed=1`).
  - Execution state: performed

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- In `tests/test_tui.py::test_tui_missing_dependencies_prints_notice`, the current body runs `if "pubrun.tui.app" in sys.modules: del sys.modules["pubrun.tui.app"]` under a stale `# Remove mock module if populated` comment without restoring the entry on teardown.
- `tests/test_tui.py::test_tui_cli_parser_and_run_leaves_real_tui_module` establishes the local pattern for guarding TUI module identity in `tests/test_tui.py`: start with `pytest.importorskip("textual")`, import `pubrun.tui.app as real_app_module`, exercise the test under check, and assert `sys.modules.get("pubrun.tui.app") is real_app_module` and `PubrunTUIApp is real_app_module.PubrunTUIApp`.
- `.github/workflows/ci.yml` (`no-tui` job) runs `pytest tests/ -v` without the `[tui]` extra installed, so every test in `tests/test_tui.py` that imports `pubrun.tui.*` must begin with `pytest.importorskip("textual")`.
- `tests/test_tui_widgets.py` imports `PubrunTUIApp` at module level during collection; if a sibling test permanently deletes `sys.modules["pubrun.tui.app"]`, subsequent re-imports create a distinct `PubrunTUIApp` class object and distinct `src/pubrun/tui/app.py::PubrunTUIApp.RefreshSidebar` message class.
- `pyproject.toml` (`[tool.pytest.ini_options]`) sets `addopts = "-p no:randomly"`, so default `pytest` invocations run in deterministic file order and `-p randomly --randomly-seed=1` opts into randomized order.
- Test outcomes, not code structure: tests must exercise runtime behavior (`sys.modules` object identity and CLI missing-dependency output) and must never inspect source text with `ast`, `inspect`, regex, or substring checks.

## Findings

`tests/test_tui.py::test_tui_missing_dependencies_prints_notice` mutates global `sys.modules` directly via `del sys.modules["pubrun.tui.app"]`. Under pytest runs combining `tests/test_tui.py` and `tests/test_tui_widgets.py` (especially under randomized order), deleting `sys.modules["pubrun.tui.app"]` without restoring it splits `PubrunTUIApp` and `PubrunTUIApp.RefreshSidebar` class identity across modules. Switching to `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` fixes the leak cleanly in one line.

## Proposed changes (ordered, validatable)

1. **`tests/test_tui.py` (E-01):** Change the signature of `test_tui_missing_dependencies_prints_notice(capsys)` to `test_tui_missing_dependencies_prints_notice(capsys, monkeypatch)`, replace the direct `del sys.modules["pubrun.tui.app"]` block with `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)`, and update the inline comment above it to explain that the entry is temporarily removed and restored on teardown.
2. **`tests/test_tui.py` (E-02):** Add a regression test (mirroring `tests/test_tui.py::test_tui_cli_parser_and_run_leaves_real_tui_module`) that calls `pytest.importorskip("textual")`, imports `pubrun.tui.app as real_app_module`, runs `test_tui_missing_dependencies_prints_notice(capsys, inner_mp)` inside `with monkeypatch.context() as inner_mp:` so teardown runs immediately on block exit (passing the outer `monkeypatch` directly would defer undo until after the assertions), and asserts `sys.modules.get("pubrun.tui.app") is real_app_module`, `PubrunTUIApp is real_app_module.PubrunTUIApp`, and `PubrunTUIApp.RefreshSidebar is real_app_module.PubrunTUIApp.RefreshSidebar`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Only `tests/test_tui.py` is modified.
- Under-scope: none. Both the `monkeypatch.delitem` fix and combined `test_tui.py` + `test_tui_widgets.py` verification from backlog item `o9c3gr` are covered.

## Required tests / validation

- Run `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -v`, `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py -v`, and `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -p randomly --randomly-seed=1 -v`.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

N/A. Test-only isolation bug fix with no runtime, CLI, or user-facing documentation change.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Paste `git diff tests/test_tui.py` showing `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` and the updated comment in `tests/test_tui.py::test_tui_missing_dependencies_prints_notice`, and paste output of `python3 -m pytest tests/test_tui.py -k test_tui_missing_dependencies_prints_notice -v` showing pass.
  - Observed evidence:
    1. `git diff tests/test_tui.py`:
    ```diff
    diff --git a/tests/test_tui.py b/tests/test_tui.py
    index b80d76f..845ad46 100644
    --- a/tests/test_tui.py
    +++ b/tests/test_tui.py
    @@ -38,13 +38,12 @@ def test_tui_cli_parser_and_run_leaves_real_tui_module():
         assert PubrunTUIApp is real_app_module.PubrunTUIApp


    -def test_tui_missing_dependencies_prints_notice(capsys):
    +def test_tui_missing_dependencies_prints_notice(capsys, monkeypatch):
         """Verify that when TUI dependencies are missing, a friendly explanation is printed and exits 1."""
         from pubrun.__main__ import main

    -    # Remove mock module if populated
    -    if "pubrun.tui.app" in sys.modules:
    -        del sys.modules["pubrun.tui.app"]
    +    # Temporarily remove pubrun.tui.app so pytest restores any pre-existing module on teardown.
    +    monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)

         with mock.patch("sys.argv", ["pubrun", "ui"]):
             # Mock import to raise ImportError
    @@ -66,6 +65,20 @@ def test_tui_missing_dependencies_prints_notice(capsys):
                 assert "Run `pip install textual rich`" in captured.err


    +def test_tui_missing_dependencies_leaves_real_tui_module(capsys, monkeypatch):
    +    """Running the missing-dependency test must restore the real pubrun.tui.app module on teardown."""
    +    pytest.importorskip("textual")
    +    import pubrun.tui.app as real_app_module
    +
    +    with monkeypatch.context() as inner_mp:
    +        test_tui_missing_dependencies_prints_notice(capsys, inner_mp)
    +
    +    assert sys.modules.get("pubrun.tui.app") is real_app_module
    +    from pubrun.tui.app import PubrunTUIApp
    +    assert PubrunTUIApp is real_app_module.PubrunTUIApp
    +    assert PubrunTUIApp.RefreshSidebar is real_app_module.PubrunTUIApp.RefreshSidebar
    +
    +
     def test_tui_toml_serialization():
         """Verify that the dict_to_toml helper serializes configurations correctly."""
         pytest.importorskip("textual")
    ```
    2. `python3 -m pytest tests/test_tui.py -k test_tui_missing_dependencies_prints_notice -v` (exit code `0`):
    ```text
    collected 13 items / 12 deselected / 1 selected

    tests/test_tui.py::test_tui_missing_dependencies_prints_notice PASSED    [100%]

    ======================= 1 passed, 12 deselected in 0.37s =======================
    ```
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Paste `git diff tests/test_tui.py` showing the new `pytest.importorskip("textual")`-guarded regression test exercising `test_tui_missing_dependencies_prints_notice` inside `monkeypatch.context()` and asserting `sys.modules["pubrun.tui.app"]`, `PubrunTUIApp`, and `PubrunTUIApp.RefreshSidebar` identity; paste actual output of `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -v`, `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py -v`, and `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -p randomly --randomly-seed=1 -v` showing all tests passing with zero failures; and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
    1. `git diff tests/test_tui.py` (new regression test hunk):
    ```diff
    +def test_tui_missing_dependencies_leaves_real_tui_module(capsys, monkeypatch):
    +    """Running the missing-dependency test must restore the real pubrun.tui.app module on teardown."""
    +    pytest.importorskip("textual")
    +    import pubrun.tui.app as real_app_module
    +
    +    with monkeypatch.context() as inner_mp:
    +        test_tui_missing_dependencies_prints_notice(capsys, inner_mp)
    +
    +    assert sys.modules.get("pubrun.tui.app") is real_app_module
    +    from pubrun.tui.app import PubrunTUIApp
    +    assert PubrunTUIApp is real_app_module.PubrunTUIApp
    +    assert PubrunTUIApp.RefreshSidebar is real_app_module.PubrunTUIApp.RefreshSidebar
    ```
    2. `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -v` (exit code `0`):
    ```text
    collected 83 items

    tests/test_tui.py::test_tui_cli_parser_and_run PASSED                    [  1%]
    tests/test_tui.py::test_tui_cli_parser_and_run_leaves_real_tui_module PASSED [  2%]
    tests/test_tui.py::test_tui_missing_dependencies_prints_notice PASSED    [  3%]
    tests/test_tui.py::test_tui_missing_dependencies_leaves_real_tui_module PASSED [  4%]
    tests/test_tui.py::test_tui_toml_serialization PASSED                    [  6%]
    tests/test_tui.py::TestResourceDigest::test_summary_and_sparklines PASSED [  7%]
    tests/test_tui.py::TestResourceDigest::test_empty_series_message PASSED  [  8%]
    tests/test_tui.py::TestResourceDigest::test_tree_metrics_shown_when_present PASSED [  9%]
    tests/test_tui.py::TestTuiResourceView::test_resource_view_populates_and_degrades PASSED [ 10%]
    tests/test_tui.py::TestReproducibilityTuiHelpers::test_format_redacted_rerun_advisory PASSED [ 12%]
    tests/test_tui.py::TestReproducibilityTuiHelpers::test_format_reproducibility_summary_pure_python PASSED [ 13%]
    tests/test_tui.py::TestTuiReproducibilityAndActions::test_details_reproducibility_markup_safety_running_and_no_live_preflight PASSED [ 14%]
    tests/test_tui.py::TestTuiReproducibilityAndActions::test_actions_panel_redacted_advisory_clearing_and_clean_clipboard PASSED [ 15%]
    tests/test_tui_widgets.py::TestAppWiring::test_tree_selection_updates_details_logs_resources_and_actions PASSED [ 16%]
    tests/test_tui_widgets.py::TestAppWiring::test_tree_selection_of_run_with_null_remote_url_keeps_app_running PASSED [ 18%]
    tests/test_tui_widgets.py::TestAppWiring::test_toggle_sidebar_binding_and_action PASSED [ 19%]
    tests/test_tui_widgets.py::TestRunsSidebar::test_search_filters_by_script_and_run_id_case_insensitively PASSED [ 20%]
    tests/test_tui_widgets.py::TestRunsSidebar::test_scan_failure_is_shown_as_a_tree_leaf PASSED [ 21%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_creates_zip_and_keeps_raw_dir PASSED [ 22%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_with_delete_raw_removes_dir_and_refreshes_sidebar PASSED [ 24%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_of_vanished_run_dir_reports_error PASSED [ 25%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_dir_creation_failure_reports_error_and_keeps_app PASSED [ 26%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_copies_generated_report[btn-copy-md-markdown] PASSED [ 27%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_copies_generated_report[btn-copy-latex-latex] PASSED [ 28%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_clipboard_failure_warns PASSED [ 30%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_without_manifest_reports_unavailable PASSED [ 31%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-rerun] PASSED [ 32%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-md] PASSED [ 33%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-latex] PASSED [ 34%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-archive-run] PASSED [ 36%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-delete-selected] PASSED [ 37%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_typing_gates_confirm_and_cancel_keeps_run PASSED [ 38%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_typed_yes_and_confirm_deletes_run PASSED [ 39%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_delete_error_is_reported_and_run_kept PASSED [ 40%]
    tests/test_tui_widgets.py::TestBulkPruneDryRun::test_dry_run_lists_candidates_and_deletes_nothing PASSED [ 42%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_darwin_uses_pbcopy PASSED [ 43%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_win32_uses_clip PASSED [ 44%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_uses_xclip_first PASSED [ 45%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_falls_back_to_xsel PASSED [ 46%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_both_missing_returns_false PASSED [ 48%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_darwin_failure_returns_false PASSED [ 49%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_same_run_guard PASSED [ 50%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_missing_manifest[a] PASSED [ 51%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_missing_manifest[b] PASSED [ 53%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_corrupt_manifest_reports_error PASSED [ 54%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_execute_then_clear PASSED [ 55%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_render_diff_report_branches PASSED [ 56%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_show_same_checkbox_populates_unchanged_section PASSED [ 57%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_populate_dropdowns_keeps_valid_selection_and_drops_stale_one PASSED [ 59%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_missing_dir_and_dir_without_logs PASSED [ 60%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_select_switches_file_and_wrap_toggles PASSED [ 61%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_missing_and_unreadable_log_file PASSED [ 62%]
    tests/test_tui_widgets.py::TestConfigPanelStates::test_reset_reloads_resolved_values PASSED [ 63%]
    tests/test_tui_widgets.py::TestConfigPanelStates::test_write_error_is_reported PASSED [ 65%]
    tests/test_tui_widgets.py::TestDictToToml::test_scalar_types_and_sections_round_trip PASSED [ 66%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[say "hi"] PASSED [ 67%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[C:\\path\\to] PASSED [ 68%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[line1\nline2] PASSED [ 69%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[tab\there] PASSED [ 71%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[bell\x07] PASSED [ 72%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[del\x7f] PASSED [ 73%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[caf\xe9 \U0001f600] PASSED [ 74%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_string_lists_round_trip[value0] PASSED [ 75%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_string_lists_round_trip[value1] PASSED [ 77%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_save_keeps_unrelated_non_bmp_list_value_loadable PASSED [ 78%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[None--] PASSED [ 79%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[https://example.com/repo-https://example.com/repo] PASSED [ 80%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url2--] PASSED [ 81%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url3--] PASSED [ 83%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url4-git@host:r.git] PASSED [ 84%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url5-https://user:[REDACTED]@h/r.git] PASSED [ 85%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url6-https://h/[/x]] PASSED [ 86%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_missing_remote_url_key PASSED [ 87%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_branch_and_commit_markup_is_shown_literally PASSED [ 89%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_unbalanced_closing_tag_in_branch_does_not_raise PASSED [ 90%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[None] PASSED [ 91%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[git_val1] PASSED [ 92%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[abc] PASSED [ 93%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_degraded_run_without_manifest_or_lock PASSED [ 95%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_assess_run_failure_falls_back PASSED [ 96%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_refresh_live_metrics_reloads_running_run_only PASSED [ 97%]
    tests/test_tui_widgets.py::TestRunResourcesStates::test_corrupt_events_file_shows_no_samples PASSED [ 98%]
    tests/test_tui_widgets.py::TestRunResourcesStates::test_reader_exception_is_rendered_not_raised PASSED [100%]

    ============================= 83 passed in 40.00s ==============================
    ```
    3. `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py -v` (exit code `0`):
    ```text
    collected 83 items

    tests/test_tui_widgets.py::TestAppWiring::test_tree_selection_updates_details_logs_resources_and_actions PASSED [  1%]
    tests/test_tui_widgets.py::TestAppWiring::test_tree_selection_of_run_with_null_remote_url_keeps_app_running PASSED [  2%]
    tests/test_tui_widgets.py::TestAppWiring::test_toggle_sidebar_binding_and_action PASSED [  3%]
    tests/test_tui_widgets.py::TestRunsSidebar::test_search_filters_by_script_and_run_id_case_insensitively PASSED [  4%]
    tests/test_tui_widgets.py::TestRunsSidebar::test_scan_failure_is_shown_as_a_tree_leaf PASSED [  6%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_creates_zip_and_keeps_raw_dir PASSED [  7%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_with_delete_raw_removes_dir_and_refreshes_sidebar PASSED [  8%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_of_vanished_run_dir_reports_error PASSED [  9%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_dir_creation_failure_reports_error_and_keeps_app PASSED [ 10%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_copies_generated_report[btn-copy-md-markdown] PASSED [ 12%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_copies_generated_report[btn-copy-latex-latex] PASSED [ 13%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_clipboard_failure_warns PASSED [ 14%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_without_manifest_reports_unavailable PASSED [ 15%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-rerun] PASSED [ 16%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-md] PASSED [ 18%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-latex] PASSED [ 19%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-archive-run] PASSED [ 20%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-delete-selected] PASSED [ 21%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_typing_gates_confirm_and_cancel_keeps_run PASSED [ 22%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_typed_yes_and_confirm_deletes_run PASSED [ 24%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_delete_error_is_reported_and_run_kept PASSED [ 25%]
    tests/test_tui_widgets.py::TestBulkPruneDryRun::test_dry_run_lists_candidates_and_deletes_nothing PASSED [ 26%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_darwin_uses_pbcopy PASSED [ 27%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_win32_uses_clip PASSED [ 28%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_uses_xclip_first PASSED [ 30%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_falls_back_to_xsel PASSED [ 31%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_both_missing_returns_false PASSED [ 32%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_darwin_failure_returns_false PASSED [ 33%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_same_run_guard PASSED [ 34%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_missing_manifest[a] PASSED [ 36%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_missing_manifest[b] PASSED [ 37%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_corrupt_manifest_reports_error PASSED [ 38%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_execute_then_clear PASSED [ 39%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_render_diff_report_branches PASSED [ 40%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_show_same_checkbox_populates_unchanged_section PASSED [ 42%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_populate_dropdowns_keeps_valid_selection_and_drops_stale_one PASSED [ 43%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_missing_dir_and_dir_without_logs PASSED [ 44%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_select_switches_file_and_wrap_toggles PASSED [ 45%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_missing_and_unreadable_log_file PASSED [ 46%]
    tests/test_tui_widgets.py::TestConfigPanelStates::test_reset_reloads_resolved_values PASSED [ 48%]
    tests/test_tui_widgets.py::TestConfigPanelStates::test_write_error_is_reported PASSED [ 49%]
    tests/test_tui_widgets.py::TestDictToToml::test_scalar_types_and_sections_round_trip PASSED [ 50%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[say "hi"] PASSED [ 51%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[C:\\path\\to] PASSED [ 53%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[line1\nline2] PASSED [ 54%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[tab\there] PASSED [ 55%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[bell\x07] PASSED [ 56%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[del\x7f] PASSED [ 57%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[caf\xe9 \U0001f600] PASSED [ 59%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_string_lists_round_trip[value0] PASSED [ 60%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_string_lists_round_trip[value1] PASSED [ 61%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_save_keeps_unrelated_non_bmp_list_value_loadable PASSED [ 62%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[None--] PASSED [ 63%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[https://example.com/repo-https://example.com/repo] PASSED [ 65%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url2--] PASSED [ 66%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url3--] PASSED [ 67%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url4-git@host:r.git] PASSED [ 68%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url5-https://user:[REDACTED]@h/r.git] PASSED [ 69%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url6-https://h/[/x]] PASSED [ 71%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_missing_remote_url_key PASSED [ 72%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_branch_and_commit_markup_is_shown_literally PASSED [ 73%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_unbalanced_closing_tag_in_branch_does_not_raise PASSED [ 74%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[None] PASSED [ 75%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[git_val1] PASSED [ 77%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[abc] PASSED [ 78%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_degraded_run_without_manifest_or_lock PASSED [ 79%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_assess_run_failure_falls_back PASSED [ 80%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_refresh_live_metrics_reloads_running_run_only PASSED [ 81%]
    tests/test_tui_widgets.py::TestRunResourcesStates::test_corrupt_events_file_shows_no_samples PASSED [ 83%]
    tests/test_tui_widgets.py::TestRunResourcesStates::test_reader_exception_is_rendered_not_raised PASSED [ 84%]
    tests/test_tui.py::test_tui_cli_parser_and_run PASSED                    [ 85%]
    tests/test_tui.py::test_tui_cli_parser_and_run_leaves_real_tui_module PASSED [ 86%]
    tests/test_tui.py::test_tui_missing_dependencies_prints_notice PASSED    [ 87%]
    tests/test_tui.py::test_tui_missing_dependencies_leaves_real_tui_module PASSED [ 89%]
    tests/test_tui.py::test_tui_toml_serialization PASSED                    [ 90%]
    tests/test_tui.py::TestResourceDigest::test_summary_and_sparklines PASSED [ 91%]
    tests/test_tui.py::TestResourceDigest::test_empty_series_message PASSED  [ 92%]
    tests/test_tui.py::TestResourceDigest::test_tree_metrics_shown_when_present PASSED [ 93%]
    tests/test_tui.py::TestTuiResourceView::test_resource_view_populates_and_degrades PASSED [ 95%]
    tests/test_tui.py::TestReproducibilityTuiHelpers::test_format_redacted_rerun_advisory PASSED [ 96%]
    tests/test_tui.py::TestReproducibilityTuiHelpers::test_format_reproducibility_summary_pure_python PASSED [ 97%]
    tests/test_tui.py::TestTuiReproducibilityAndActions::test_details_reproducibility_markup_safety_running_and_no_live_preflight PASSED [ 98%]
    tests/test_tui.py::TestTuiReproducibilityAndActions::test_actions_panel_redacted_advisory_clearing_and_clean_clipboard PASSED [100%]

    ============================= 83 passed in 43.92s ==============================
    ```
    4. `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -p randomly --randomly-seed=1 -v` (exit code `0`):
    ```text
    Using --randomly-seed=1
    collected 83 items

    tests/test_tui.py::test_tui_cli_parser_and_run PASSED                    [  1%]
    tests/test_tui.py::test_tui_missing_dependencies_leaves_real_tui_module PASSED [  2%]
    tests/test_tui.py::test_tui_toml_serialization PASSED                    [  3%]
    tests/test_tui.py::test_tui_missing_dependencies_prints_notice PASSED    [  4%]
    tests/test_tui.py::test_tui_cli_parser_and_run_leaves_real_tui_module PASSED [  6%]
    tests/test_tui.py::TestResourceDigest::test_summary_and_sparklines PASSED [  7%]
    tests/test_tui.py::TestResourceDigest::test_tree_metrics_shown_when_present PASSED [  8%]
    tests/test_tui.py::TestResourceDigest::test_empty_series_message PASSED  [  9%]
    tests/test_tui.py::TestTuiReproducibilityAndActions::test_details_reproducibility_markup_safety_running_and_no_live_preflight PASSED [ 10%]
    tests/test_tui.py::TestTuiReproducibilityAndActions::test_actions_panel_redacted_advisory_clearing_and_clean_clipboard PASSED [ 12%]
    tests/test_tui.py::TestTuiResourceView::test_resource_view_populates_and_degrades PASSED [ 13%]
    tests/test_tui.py::TestReproducibilityTuiHelpers::test_format_redacted_rerun_advisory PASSED [ 14%]
    tests/test_tui.py::TestReproducibilityTuiHelpers::test_format_reproducibility_summary_pure_python PASSED [ 15%]
    tests/test_tui_widgets.py::TestConfigPanelStates::test_write_error_is_reported PASSED [ 16%]
    tests/test_tui_widgets.py::TestConfigPanelStates::test_reset_reloads_resolved_values PASSED [ 18%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_degraded_run_without_manifest_or_lock PASSED [ 19%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_assess_run_failure_falls_back PASSED [ 20%]
    tests/test_tui_widgets.py::TestRunDetailsStates::test_refresh_live_metrics_reloads_running_run_only PASSED [ 21%]
    tests/test_tui_widgets.py::TestDictToToml::test_scalar_types_and_sections_round_trip PASSED [ 22%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url6-https://h/[/x]] PASSED [ 24%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url3--] PASSED [ 25%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[git_val1] PASSED [ 26%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url4-git@host:r.git] PASSED [ 27%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[None--] PASSED [ 28%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url5-https://user:[REDACTED]@h/r.git] PASSED [ 30%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_branch_and_commit_markup_is_shown_literally PASSED [ 31%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_missing_remote_url_key PASSED [ 32%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[https://example.com/repo-https://example.com/repo] PASSED [ 33%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_remote_url_shapes[remote_url2--] PASSED [ 34%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[abc] PASSED [ 36%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_unbalanced_closing_tag_in_branch_does_not_raise PASSED [ 37%]
    tests/test_tui_widgets.py::TestRunDetailsGit::test_non_dict_git_section_falls_back_to_lock_fields[None] PASSED [ 38%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_show_same_checkbox_populates_unchanged_section PASSED [ 39%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_corrupt_manifest_reports_error PASSED [ 40%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_populate_dropdowns_keeps_valid_selection_and_drops_stale_one PASSED [ 42%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_missing_manifest[a] PASSED [ 43%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_render_diff_report_branches PASSED [ 44%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_missing_manifest[b] PASSED [ 45%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_same_run_guard PASSED [ 46%]
    tests/test_tui_widgets.py::TestDiffViewStates::test_execute_then_clear PASSED [ 48%]
    tests/test_tui_widgets.py::TestRunsSidebar::test_scan_failure_is_shown_as_a_tree_leaf PASSED [ 49%]
    tests/test_tui_widgets.py::TestRunsSidebar::test_search_filters_by_script_and_run_id_case_insensitively PASSED [ 50%]
    tests/test_tui_widgets.py::TestRunResourcesStates::test_reader_exception_is_rendered_not_raised PASSED [ 51%]
    tests/test_tui_widgets.py::TestRunResourcesStates::test_corrupt_events_file_shows_no_samples PASSED [ 53%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-md] PASSED [ 54%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_copies_generated_report[btn-copy-md-markdown] PASSED [ 55%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_clipboard_failure_warns PASSED [ 56%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-latex] PASSED [ 57%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_without_manifest_reports_unavailable PASSED [ 59%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-copy-rerun] PASSED [ 60%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-archive-run] PASSED [ 61%]
    tests/test_tui_widgets.py::TestActionsCitations::test_run_buttons_without_selection_ask_for_a_run[btn-delete-selected] PASSED [ 62%]
    tests/test_tui_widgets.py::TestActionsCitations::test_copy_methods_copies_generated_report[btn-copy-latex-latex] PASSED [ 63%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_select_switches_file_and_wrap_toggles PASSED [ 65%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_missing_dir_and_dir_without_logs PASSED [ 66%]
    tests/test_tui_widgets.py::TestLogViewerStates::test_missing_and_unreadable_log_file PASSED [ 67%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_falls_back_to_xsel PASSED [ 68%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_uses_xclip_first PASSED [ 69%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_darwin_failure_returns_false PASSED [ 71%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_darwin_uses_pbcopy PASSED [ 72%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_win32_uses_clip PASSED [ 73%]
    tests/test_tui_widgets.py::TestCopyToClipboard::test_linux_both_missing_returns_false PASSED [ 74%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[C:\\path\\to] PASSED [ 75%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_save_keeps_unrelated_non_bmp_list_value_loadable PASSED [ 77%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[tab\there] PASSED [ 78%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[bell\x07] PASSED [ 79%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[line1\nline2] PASSED [ 80%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_string_lists_round_trip[value1] PASSED [ 81%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[caf\xe9 \U0001f600] PASSED [ 83%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_string_lists_round_trip[value0] PASSED [ 84%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[say "hi"] PASSED [ 85%]
    tests/test_tui_widgets.py::TestTomlEscaping::test_strings_round_trip[del\x7f] PASSED [ 86%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_typing_gates_confirm_and_cancel_keeps_run PASSED [ 87%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_typed_yes_and_confirm_deletes_run PASSED [ 89%]
    tests/test_tui_widgets.py::TestConfirmDeleteModal::test_delete_error_is_reported_and_run_kept PASSED [ 90%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_of_vanished_run_dir_reports_error PASSED [ 91%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_dir_creation_failure_reports_error_and_keeps_app PASSED [ 92%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_creates_zip_and_keeps_raw_dir PASSED [ 93%]
    tests/test_tui_widgets.py::TestActionsArchive::test_archive_with_delete_raw_removes_dir_and_refreshes_sidebar PASSED [ 95%]
    tests/test_tui_widgets.py::TestAppWiring::test_tree_selection_updates_details_logs_resources_and_actions PASSED [ 96%]
    tests/test_tui_widgets.py::TestAppWiring::test_tree_selection_of_run_with_null_remote_url_keeps_app_running PASSED [ 97%]
    tests/test_tui_widgets.py::TestAppWiring::test_toggle_sidebar_binding_and_action PASSED [ 98%]
    tests/test_tui_widgets.py::TestBulkPruneDryRun::test_dry_run_lists_candidates_and_deletes_nothing PASSED [100%]

    ============================= 83 passed in 41.10s ==============================
    ```
    5. `python3 scripts/sanitize_paths.py --check --all`: exit code `0` (zero findings).
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`).

Execution contract:
1. **Open-questions precondition:** Zero blocking open questions remain before execution (`## Open questions` is empty).
2. **Scope declaration:** `- Scope-Paths:` declares `tests/test_tui.py`. If execution requires editing another file or leaving a declared file unchanged, make the change and justify it with `--scope-reason` or `--scope-ack` at finalize.
3. **Validation honesty (HARD MUST):** Paste the actual `pytest` and `sanitize_paths.py` runner output observed after the final edit into `V-01` and `V-02`; never claim tests pass without running them.
4. **Path-scoped commit and never-push:** Commit only the modified path through `aw commit lv41re -- tests/test_tui.py`; never use `git add -A` or `-a`, and never push without explicit human instruction.
5. **Lifecycle transition (conditional runner vs. standalone ownership):** When executed inside `aw oc run` / `aw agy run`, the runner owns the lifecycle move after the merge-and-revalidate gate; when executed standalone outside the runner, run `aw ipd finalize lv41re` (never a hand-rolled `git mv` to `executed/`).
