# Review findings: ipd 4cy3ft

- Subject-Id: 4cy3ft
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-zdkdyg-01-4cy3ft-prepend-the-repository-src-directory-to-pythonpath-for-test.ipd.md` (front matter, Mermaid flowchart, E-01 to E-04, V-01 to V-04, conventions, findings, proposed changes, deferrals, scope check, required tests, spec sync, OQ-01, OQ-02, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches the normative text of E-01 (the `is_dir()` guard, prepend with `os.pathsep`, restore or delete after the session).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation and cross-check boilerplate | Two em dashes around the "as distinct from" clause (`IPD-C802` advisory twice) | Commas and parentheses | Clears both `IPD-C802` advisories; meaning unchanged. |
| Project conventions, Deferred | `tests/test_commit_identity.py::_run_python` | `tests/test_commit_identity.py::_run_python_isolated` | Requirement 3 (exact identifiers): no function named `_run_python` exists. |
| Proposed changes, final paragraph | "at least three files" | "at least three files that do not prepend today" | Requirement 6: names which files the count refers to. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (2 files), 4 E-items in 3 task groups.

1. No: it changes only the test harness; no spec, CLI option, output format, file format, or configuration key changes.
2. No: it does not touch code that guards private data, commits, worktree isolation, merges, or the sandbox; it makes tests correct inside worktrees but changes no isolation code.
3. No: 4 E-items, one edited file and one new file.
4. Yes: both files are listed.
5. Moderately: a session-scoped autouse fixture affects every one of the 1821 collected tests, so a mistake could break or falsely pass the whole suite. It is easy to undo.

AW-TIER: standard

### Step R1

- Checked: `pyproject.toml` `[tool.pytest.ini_options]` (`pythonpath = ["src"]`, `addopts` with `--cov` and `-p no:randomly`); `tests/conftest.py::isolated_cwd`, `::clean_active_run`, `::pubrun_state_isolation` (snapshot `dict(os.environ)` before the test, exact restore after); `tests/test_report_subpackage_integrity.py::_run` (no `env=`); `tests/test_bench_command.py::run_pubrun` (`dict(os.environ)`, no prepend); `tests/test_import_modes.py` lines 222 and 794 (`env={**os.environ, ...}`) and `TestModeAliasApiParity._clean_env` (prepend); `tests/test_capture_isolation.py::_worktree_env`; `tests/test_commit_identity.py::_run_python_isolated` and `::_clean_git_env`; `tests/test_package_lifecycle.py` (decoy `site_dir` placed before `src`); every file in `tests/` that mentions `PYTHONPATH` (13 files); `.github/workflows/ci.yml` (`pip install -e`, `pytest tests/ -v`); `tox.ini`; `src/pubrun/resources/default.toml` `auto_start = true`; commit `5283dee` resolves; backlog `zdkdyg` acceptance criteria 1 and 2.
- Reproduced `## Findings` row 2 on this lane at `9edd0b6`: the probe command printed `79 passed in 52.29s`, and the log held 10 lines naming this lane's `src/pubrun/__init__.py` and 37 naming the main checkout's. The plan's numbers match.
- Baseline full suite: `python3 -m pytest -q -p no:cacheprovider --no-cov` gave `1819 passed, 2 skipped in 481.27s`.
- Simulated the fix without editing code by exporting the value the fixture would set: `PYTHONPATH="<lane>/src:$PYTHONPATH" python3 -m pytest -q --no-cov` gave `1819 passed, 2 skipped in 487.50s`, and `env -u PYTHONPATH PYTHONPATH="<lane>/src" python3 -m pytest -q --no-cov` gave `1819 passed, 2 skipped in 520.68s`. With 2 `pytest-xdist` workers the two probe files gave `79 passed`. No test depends on a child importing an installed `pubrun` instead of `src`.
- Errors in the plan: `_run_python` is really `_run_python_isolated`, and the list of helpers that already prepend omits `tests/test_cli.py`, `tests/test_cli_diff_bugs.py`, and `tests/test_reproducibility_e2e.py`, so "eight test files" is eleven (PR-003).

### Step R2

- Checked: E/V bijection (E-01..E-04 to V-01..V-04), Scope-Paths completeness, `Item-Dependencies: none`, concreteness and reachability of each V-item, and the execution contract.
- V-02's pre-fix half needed a temporary `git worktree` and an editable install pointing at another checkout, and it fell back to a `blocked` result otherwise. The terminal gate demands `pass` for every V-item, so in CI or on any machine without a second checkout V-02 could never pass (PR-002).
- Reachability: V-03 observes child processes through the probe; the producing code path is the E-01 fixture, as the item states. Reachable.
- Gate: resolved questions, a non-STOP scope fence with `--scope-reason`/`--scope-ack`, the honesty rule, path-scoped `aw commit` with never-push, and conditional runner/executor `aw ipd finalize` ownership. Conforming.

### Step R3

- Checked: the change runs only inside the test session. It adds a local directory to the front of `PYTHONPATH` for child processes, restores it after the session, and reaches no network or secrets. No findings.

### Step R4

- Checked: rubric A (the fixture restores the previous value or deletes the key; `pubrun_state_isolation` keeps the value between tests), C (no new dependency; `os.pathsep` covers Windows), D (invariant: every inheriting child imports this checkout's `pubrun`), E (behavioral subprocess tests), F (one fixture instead of per-helper edits), right-sizing, and spec/doc sync (no spec covers the test harness; no user doc mentions `PYTHONPATH`).
- PR-001: E-02's main test only detects the defect where the installed `pubrun` comes from another checkout. In CI the editable install is the checkout under test, so the test passes with or without the fixture and guards nothing where the suite usually runs. A decoy package appended to `PYTHONPATH` makes the defect visible everywhere. Measured in a scratch copy under `/tmp/opencode/vt` with the E-01 fixture and three tests: with the conftest, `3 passed`; with `--noconftest`, `3 failed` (the decoy test printed the decoy path). Both results held with the shell's `PYTHONPATH` and with it unset.
- Measured that `import pubrun` with the default `auto_start = true` writes `runs/` into the child's working directory. Under `--noconftest` the `isolated_cwd` fixture is absent, so a child without `cwd=tmp_path` would write into the repository root; the revised E-02 sets `cwd` on every child (part of PR-002).

### Step S5

- Checked: OQ-01 and OQ-02 (resolved, non-blocking, basis cited), the three `Carrier-Declined` deferrals, and all findings. Each finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED. No question needs the human.
- OQ-01 and OQ-02 recorded `- Owner: none` on questions the plan author resolved; changed to `plan author` (part of PR-003).

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | UNDER-SCOPE | R4.E (the regression test must fail without the fix) | Plan E-02; `.github/workflows/ci.yml` (`pip install -e`); scratch run under `/tmp/opencode/vt` (`3 passed` with conftest, `3 failed` with `--noconftest`) | The planned regression test passes without the fix wherever the installed `pubrun` is the checkout under test, including CI, so it cannot catch a regression there. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added a third E-02 test that appends a decoy `pubrun` to the child's `PYTHONPATH` and asserts the child still imports this checkout's `src` (recommendation strength: very strong). |
| PR-002 | medium | IN-SCOPE | R2 (V-item reachable in every environment) and R4.A (no writes into the repository) | Plan V-02; plan `## Approval and execution gate` (terminal gate demands `pass`); `src/pubrun/resources/default.toml` `auto_start = true` | V-02's pre-fix proof needed a temporary worktree and a second checkout and otherwise ended `blocked`, which the terminal gate rejects. Children without `cwd` could write `runs/` into the repository root when the conftest is skipped. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-02 now demands a `--noconftest` run, which reproduces the pre-fix condition anywhere, showing the decoy test failing; V-02 demands behaviors with test names as pointers; every E-02 child runs with `cwd=str(tmp_path)` and the reason is stated (recommendation strength: strong). |
| PR-003 | low | IN-SCOPE | R1 (citation accuracy) and S5 (owner provenance) | `tests/test_commit_identity.py:143` `_run_python_isolated`; `tests/test_cli.py:18`, `tests/test_cli_diff_bugs.py:25`, `tests/test_reproducibility_e2e.py:32`; plan OQ-01, OQ-02; validation boilerplate | Wrong helper name `_run_python`; three prepending helpers missing and the count "eight" wrong; `Owner: none` on author-resolved questions; two em dashes raised `IPD-C802`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Corrected the name, listed the three helpers, changed the count to eleven, set Owner to `plan author`, and removed the dashes (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should V-02 prove the regression test fails without the fix? | Run the test file with `--noconftest` | A temporary `git worktree` of the pre-fix commit (needs a second checkout; `blocked` otherwise); editing `tests/conftest.py` temporarily | `--noconftest` skips the session fixture, which is the only change; the scratch run failed as expected with and without an inherited `PYTHONPATH` | yes |
| D-2 | Where should the decoy go on the child's `PYTHONPATH`? | Appended after the inherited value | Prepended (would beat `src` and fail even with the fix) | `PYTHONPATH` entries precede the `.pth` entry on `sys.path`, so an appended decoy wins only when `src` is absent | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; E-02 and V-02 were refined in place. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
