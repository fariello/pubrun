# IPD: Use monkeypatch in test_tui_missing_dependencies_prints_notice to restore sys.modules

- Date: 2026-11-24
- Kind: child
- Concern: Test isolation for `sys.modules["pubrun.tui.app"]` across TUI test modules
- Scope: Update `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` to remove `sys.modules["pubrun.tui.app"]` via pytest's `monkeypatch` fixture so the original module object is restored on teardown, and add a behavioral check confirming `sys.modules["pubrun.tui.app"]` identity is preserved across `tests/test_tui.py` and `tests/test_tui_widgets.py`.
- Scope-Paths: tests/test_tui.py
- Item-Dependencies: none
- Status: to-review
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

- 2026-11-25 to-review (Antigravity): graduated from backlog item `o9c3gr` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Prevent `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` from permanently deleting `sys.modules["pubrun.tui.app"]`, which otherwise forces later tests in the same pytest process to re-import a second `PubrunTUIApp` class object whose nested `RefreshSidebar` message class does not match handlers bound to the module collected by `tests/test_tui_widgets.py`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Restore sys.modules entry via monkeypatch

- [ ] E-01 Update `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` to accept pytest's `monkeypatch` fixture and replace `if "pubrun.tui.app" in sys.modules: del sys.modules["pubrun.tui.app"]` with `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)`.
  - Depends on: none
  - Expected outcome: `test_tui_missing_dependencies_prints_notice` still simulates missing `textual` dependencies and asserts exit code 1 plus the friendly error notice on `stderr`, while pytest automatically restores any pre-existing `sys.modules["pubrun.tui.app"]` entry when the test finishes.
  - Execution state: pending

- [ ] E-02 Add a behavioral regression check in `tests/test_tui.py` confirming that running `test_tui_missing_dependencies_prints_notice` when `pubrun.tui.app` is already loaded leaves `sys.modules["pubrun.tui.app"]` pointing to the exact same module object after teardown, and verify `tests/test_tui.py` and `tests/test_tui_widgets.py` pass together in the same pytest process.
  - Depends on: E-01
  - Expected outcome: A test in `tests/test_tui.py` (or a two-phase fixture/test check exercising `test_tui_missing_dependencies_prints_notice` behavior without reading source code) proves `sys.modules["pubrun.tui.app"]` object identity is preserved across the missing-dependency check, and `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py` exits 0 in both forward and reversed file order.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- In `tests/test_tui.py::test_tui_missing_dependencies_prints_notice`, the current body runs `if "pubrun.tui.app" in sys.modules: del sys.modules["pubrun.tui.app"]` without restoring the entry on teardown.
- `tests/test_tui_widgets.py` imports `PubrunTUIApp` at collection time; if a sibling test deletes `sys.modules["pubrun.tui.app"]`, subsequent re-imports create a distinct `PubrunTUIApp` class object and distinct `PubrunTUIApp.RefreshSidebar` message class.
- Test outcomes, not code structure: tests must exercise runtime behavior (`sys.modules` object identity and CLI missing-dependency output) and must never inspect source text with `ast`, `inspect`, regex, or substring checks.

## Findings

`tests/test_tui.py::test_tui_missing_dependencies_prints_notice` mutates global `sys.modules` directly via `del sys.modules["pubrun.tui.app"]`. Under pytest runs combining `tests/test_tui.py` and `tests/test_tui_widgets.py` (especially under randomized order), deleting `sys.modules["pubrun.tui.app"]` without restoring it splits `PubrunTUIApp` class identity across modules. Switching to `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` fixes the leak cleanly in one line.

## Proposed changes (ordered, validatable)

1. **`tests/test_tui.py` (E-01):** Change the signature of `test_tui_missing_dependencies_prints_notice(capsys)` to `test_tui_missing_dependencies_prints_notice(capsys, monkeypatch)` and replace the direct `del sys.modules["pubrun.tui.app"]` block with `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)`.
2. **`tests/test_tui.py` (E-02):** Verify module identity preservation (for example by running `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py` and `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py`, plus a behavioral test that records `before = sys.modules.get("pubrun.tui.app")` via a pytest `monkeypatch.context()` or test-order check confirming `PubrunTUIApp` identity is intact after the missing-dependency path runs).

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Only `tests/test_tui.py` is modified.
- Under-scope: none. Both the `monkeypatch.delitem` fix and combined `test_tui.py` + `test_tui_widgets.py` verification from backlog item `o9c3gr` are covered.

## Required tests / validation

- Run `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -v` and `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py -v`.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

N/A. Test-only isolation bug fix with no runtime, CLI, or user-facing documentation change.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff tests/test_tui.py` showing `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` in `test_tui_missing_dependencies_prints_notice` and paste output of `python3 -m pytest tests/test_tui.py -k test_tui_missing_dependencies_prints_notice -v` showing pass.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste actual output of `python3 -m pytest tests/test_tui.py tests/test_tui_widgets.py -v` and `python3 -m pytest tests/test_tui_widgets.py tests/test_tui.py -v` showing all tests passing (including verification that `sys.modules["pubrun.tui.app"]` identity is preserved across `test_tui_missing_dependencies_prints_notice`), plus `python3 scripts/sanitize_paths.py --check --all` exiting 0.
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
