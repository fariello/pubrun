# IPD: Use monkeypatch in test_tui_missing_dependencies_prints_notice to restore sys.modules

- Date: 2026-11-24
- Kind: child
- Concern: Test isolation for `sys.modules["pubrun.tui.app"]` across TUI test modules
- Scope: Update `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` to remove `sys.modules["pubrun.tui.app"]` via pytest's `monkeypatch` fixture so the original module object is restored on teardown, and add a behavioral check confirming `sys.modules["pubrun.tui.app"]` identity is preserved across `tests/test_tui.py` and `tests/test_tui_widgets.py`.
- Scope-Paths: tests/test_tui.py
- Item-Dependencies: none
- Status: reviewed
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

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003
- 2026-11-25 to-review (Antigravity): graduated from backlog item `o9c3gr` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Prevent `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` from permanently deleting `sys.modules["pubrun.tui.app"]`, which otherwise forces later tests in the same pytest process to re-import a second `PubrunTUIApp` class object whose nested `RefreshSidebar` message class does not match handlers bound to the module collected by `tests/test_tui_widgets.py`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Restore sys.modules entry via monkeypatch

- [ ] E-01 Update `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` to accept pytest's `monkeypatch` fixture, replace `if "pubrun.tui.app" in sys.modules: del sys.modules["pubrun.tui.app"]` with `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)`, and update the inline comment above it to explain that the entry is temporarily removed and restored on teardown.
  - Depends on: none
  - Expected outcome: `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` still simulates missing `textual` dependencies and asserts exit code 1 plus the friendly error notice on `stderr`, while pytest automatically restores any pre-existing `sys.modules["pubrun.tui.app"]` entry when the test finishes (and leaves `sys.modules` clean when the entry was absent, including in `no-tui` environments).
  - Execution state: pending

- [ ] E-02 Add a behavioral regression test in `tests/test_tui.py` (guarded with `pytest.importorskip("textual")`) that pre-loads `pubrun.tui.app`, invokes `test_tui_missing_dependencies_prints_notice(capsys, inner_mp)` inside `with monkeypatch.context() as inner_mp:`, and asserts after exiting the context that `sys.modules["pubrun.tui.app"]`, `PubrunTUIApp`, and `PubrunTUIApp.RefreshSidebar` retain exact object identity; then verify `tests/test_tui.py` and `tests/test_tui_widgets.py` pass together in the same pytest process.
  - Depends on: E-01
  - Expected outcome: The new regression test in `tests/test_tui.py` skips cleanly when `textual` is absent (`pytest.importorskip("textual")`), fails if `test_tui_missing_dependencies_prints_notice` deletes `sys.modules["pubrun.tui.app"]` without restoring it on `monkeypatch` teardown, and passes when E-01 is in place; combined runs of `tests/test_tui.py` and `tests/test_tui_widgets.py` exit 0 in forward order, reversed file order, and shuffled order (`-p randomly --randomly-seed=1`).
  - Execution state: pending

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

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff tests/test_tui.py` showing `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` and the updated comment in `tests/test_tui.py::test_tui_missing_dependencies_prints_notice`, and paste output of `python3 -m pytest tests/test_tui.py -k test_tui_missing_dependencies_prints_notice -v` showing pass.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste `git diff tests/test_tui.py` showing the new `pytest.importorskip("textual")`-guarded regression test exercising `test_tui_missing_dependencies_prints_notice` inside `monkeypatch.context()` and asserting `sys.modules["pubrun.tui.app"]`, `PubrunTUIApp`, and `PubrunTUIApp.RefreshSidebar` identity; paste actual output of `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -v`, `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py -v`, and `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -p randomly --randomly-seed=1 -v` showing all tests passing with zero failures; and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

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
