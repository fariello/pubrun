# Review findings: ipd lv41re

- Subject-Id: lv41re
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-o9c3gr-01-lv41re-use-monkeypatch-in-test-tui-missing-dependencies-prints-noti.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md` Section 11.1 code citation rules, plus `tests/test_tui.py` (all 411 lines, including `test_tui_cli_parser_and_run_leaves_real_tui_module` and `test_tui_missing_dependencies_prints_notice`), `tests/test_tui_widgets.py` (top-level imports and `RefreshSidebar` assertions), `src/pubrun/__main__.py` (`ui`/`tui`/`gui` command branch), `src/pubrun/tui/widgets/actions.py` (`RefreshSidebar` helper), `src/pubrun/tui/app.py` (`PubrunTUIApp.RefreshSidebar`), `.github/workflows/ci.yml` (`no-tui` job), `pyproject.toml` (`[tool.pytest.ini_options]`), `.aw/records/backlog/graduated/20261124-o9c3gr-01-o9c3gr-use-monkeypatch-in-tests-test-tui-py-test-tui-miss.backlog.md`, and executed sibling review `.aw/records/reviews/20261122-pgcmea-01-whacr3-confirm-the-pubrun-tui-app-sys-modules-restore-and-add-a-reg.review.md`. No pre-review snapshot was needed: lane `HEAD` `107fbce` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(c) applies (single test file, linear 2-step edit; no diagram should be added).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-01` and `Proposed changes` item 1 | Replaced lines 46-47 without addressing the stale `# Remove mock module if populated` comment on line 45 | Instructs updating the inline comment alongside `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` | Removes stale pre-`whacr3` comment (PR-003). |
| `E-02`, `Project conventions discovered`, `Proposed changes` item 2, `Required tests / validation`, `V-02` | Left `E-02` regression test mechanics vague ("or a two-phase fixture/test check"), omitted `pytest.importorskip("textual")`, did not check `PubrunTUIApp.RefreshSidebar` identity, and omitted randomized-order verification | Requires `pytest.importorskip("textual")`, specifies invoking `test_tui_missing_dependencies_prints_notice(capsys, inner_mp)` inside `with monkeypatch.context() as inner_mp:` and asserting `sys.modules["pubrun.tui.app"]`, `PubrunTUIApp`, and `PubrunTUIApp.RefreshSidebar` identity, and adds `-p randomly --randomly-seed=1` to `Required tests / validation` and `V-02` | Prevents `no-tui` CI failure, prevents outer-`monkeypatch` teardown failure, and matches `Findings` and Section 11.1 citations (PR-001, PR-002, PR-003). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`tests/test_tui.py`), 2 E-items in 1 task group, `- Kind: child`.

1. No: test-only isolation fix in `tests/test_tui.py`; changes no spec, CLI option, output format, file format, or configuration key.
2. No: test code only; touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 2 E-items in 1 task group, 1 test file (`tests/test_tui.py`).
4. Yes: `tests/test_tui.py`.
5. No: test-only edit in one file, trivially reversible, cannot lose data or break production behavior.

AW-TIER: simple

### Step Q

- Checked: what editing `tests/test_tui.py` could break; whether any other test in `tests/` mutates `sys.modules["pubrun.tui.app"]` (`grep -rn "pubrun\.tui" tests/ | grep "sys\.modules"` returned only `tests/test_tui.py` lines 18, 30, 36, 46-47); whether `no-tui` CI job runs `tests/test_tui.py` without `textual` installed (yes, `.github/workflows/ci.yml:56-68` installs `.[dev]` only and runs `pytest tests/ -v`); baseline targeted run `python3 -m pytest tests/test_tui.py -k "test_tui_missing_dependencies_prints_notice or test_tui_cli_parser_and_run" -v --no-cov -p no:cacheprovider` (`3 passed, 9 deselected in 0.68s`); and whether `monkeypatch.delitem(sys.modules, "pubrun.tui.app", raising=False)` is safe both when `pubrun.tui.app` is already loaded and when it is absent (yes, `raising=False` is a safe no-op when absent and restores the exact original module object on `undo()` when present).
- PR-001: `E-02` added a test importing `pubrun.tui.app` in `tests/test_tui.py` without `pytest.importorskip("textual")`, which would fail the `no-tui` CI job in `.github/workflows/ci.yml:56-68`. Fixed across `E-02`, `Project conventions discovered`, `Proposed changes` item 2, and `V-02`.
- PR-002: `E-02` left teardown mechanics ambiguous; passing the outer test's `monkeypatch` directly into `test_tui_missing_dependencies_prints_notice` defers `undo()` until after assertions run, causing a false failure. Fixed by specifying `with monkeypatch.context() as inner_mp:` (mirroring `test_tui_cli_parser_and_run_leaves_real_tui_module`), asserting `sys.modules["pubrun.tui.app"]`, `PubrunTUIApp`, and `PubrunTUIApp.RefreshSidebar` identity, and adding `-p randomly --randomly-seed=1` to `Required tests / validation` and `V-02`.
- PR-003: `E-01` left the stale `# Remove mock module if populated` comment on line 45 unaddressed and `Project conventions discovered` omitted Section 11.1 citations for `test_tui_cli_parser_and_run_leaves_real_tui_module`, `PubrunTUIApp.RefreshSidebar`, `.github/workflows/ci.yml`, and `pyproject.toml`. Fixed.

### Step S5

- Checked: `## Open questions` is `None.`. `## Deferred / out of scope (with reason)` is `None.`. All three review findings (PR-001, PR-002, PR-003) have Overall Remediation Risk `Low` and were fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | UNDER-SCOPE | Check Q / R2 (`no-tui` CI breakage) | `.github/workflows/ci.yml:56-68` (`no-tui` job); `tests/test_tui.py:31,71,152,237,326` (`pytest.importorskip("textual")`); Plan `E-02` (lines 43-45) and `Proposed changes` item 2 (line 62) | `E-02` adds a test in `tests/test_tui.py` that imports `pubrun.tui.app` without requiring `pytest.importorskip("textual")`. Because `.github/workflows/ci.yml` runs `pytest tests/ -v` in `no-tui` without `[tui]` installed, omitting `importorskip` causes `ModuleNotFoundError` in CI. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required `pytest.importorskip("textual")` at the start of the new E-02 regression test in `E-02`, `Project conventions discovered`, `Proposed changes` item 2, and `V-02` (recommendation strength: very strong). |
| PR-002 | MEDIUM | IN-SCOPE | Check Q / R2 (teardown mechanics and validation coverage) | Plan `E-02` (lines 43-45), `Proposed changes` item 2 (line 62), `Required tests / validation` (line 75), `V-02` (line 96); `tests/test_tui.py:29-38` (`test_tui_cli_parser_and_run_leaves_real_tui_module`) | `E-02` left how to verify teardown vague. Because `monkeypatch.delitem` restores on `undo()`, passing the outer test's `monkeypatch` directly causes post-call identity assertions to fail. `E-02`/`V-02` also omitted `PubrunTUIApp.RefreshSidebar` identity and randomized-order verification (`-p randomly`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `with monkeypatch.context() as inner_mp:` around `test_tui_missing_dependencies_prints_notice(capsys, inner_mp)` in `E-02` and `Proposed changes` item 2, added `PubrunTUIApp.RefreshSidebar` identity assertion, and added `-p randomly --randomly-seed=1` to `Required tests / validation` and `V-02` (recommendation strength: strong). |
| PR-003 | LOW | IN-SCOPE | Check P / Section 11.1 (stale comment and citations) | `tests/test_tui.py:45` (`# Remove mock module if populated`); `src/pubrun/tui/app.py:38` (`PubrunTUIApp.RefreshSidebar`); `pyproject.toml:87` (`addopts = "-p no:randomly"`); Plan `E-01` (line 38), `Project conventions discovered` (lines 50-53) | `E-01` did not update the stale `# Remove mock module if populated` comment on line 45, and `Project conventions discovered` lacked Section 11.1 citations to sibling `test_tui_cli_parser_and_run_leaves_real_tui_module`, `PubrunTUIApp.RefreshSidebar`, `.github/workflows/ci.yml`, and `pyproject.toml`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-01` and `Proposed changes` item 1 to update the inline comment, and added the missing Section 11.1 citations and `addopts` convention in `Project conventions discovered` (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `simple` | `standard` | Test-only isolation fix in one file (`tests/test_tui.py`) with 2 E-items in 1 task group; all five tier risk questions answered No (Scope-Paths declared); matches sibling plan `whacr3`. | yes |
| D-2 | How should `E-02` verify `monkeypatch` teardown without false failures? | Use `with monkeypatch.context() as inner_mp:` inside a `pytest.importorskip("textual")`-guarded regression test | Rely only on two-file test ordering or pass the outer `monkeypatch` fixture | `monkeypatch.delitem` restores on `undo()` (not on function return); `monkeypatch.context()` exercises teardown deterministically inside one test and catches regressions regardless of collection order, while `importorskip` keeps `no-tui` CI green. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All three findings (PR-001, PR-002, PR-003) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified before committing. No second review pass is needed.

AW-REVIEW: DONE
