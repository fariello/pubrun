# Review findings: ipd gzc672

- Subject-Id: gzc672
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-02-gzc672-mypy-type-check-repair-and-ci-type-gate.ipd.md` (front matter, Goal, diagram, E-01 to E-05, conventions, findings, proposed changes, deferral, scope check, required tests, documentation sync, open questions, V-01 to V-05, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Proofreading kept front-matter keys, the H2 heading list and order, existing E/V ids, checkbox states, Execution state values, and item field names. Substantive rewrites of E-items, V-items, the diagram, and the gate are recorded under Findings, not here.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence naming a "per-module legacy ratchet" and a "duplicate-module import" with no definitions | States what `mypy` is, what the import does at runtime and to `mypy`, and defines the ratchet as an explicit `ignore_errors` list that may only shrink | Define terms at first use; a reader new to the repository cannot act on undefined names. |
| Short-Description | "fix real TUI/report type bugs" | Names the four modules' type errors, the ratchet, and the blocking CI job | Match what the revised items do. |
| Project conventions | "`mypy --no-namespace-packages --ignore-missing-imports src/pubrun` found 175 errors" as an assessment-time note | Review measurements with tool versions, the per-file counts, the post-fix 111 errors in 20 modules, and the editable-install path caveat | The executor needs the measured baseline and the reason to run from the repository root. |
| Deferred | One T-19 deferral | Adds the per-platform check, the unpinned `mypy` version, and the push-gated CI run | Each is a known residual risk the executor and approver should see. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (6 entries before review, 9 after), E-01 to E-05 (7 E-items after review in 2 task groups), and the files each item touches.

1. Yes: the plan adds a `[tool.mypy]` configuration contract in `pyproject.toml` and a new CI job in `.github/workflows/ci.yml`, both shared with `bzi46m`, and changes no public API, CLI option, or manifest field.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. Partly: 7 E-items in 2 task groups, but all serve one invariant (the ratchet list matches the clean module set).
4. Yes: 9 files after review, matching the E-items.
5. Low: every source edit is a type-narrowing rewrite with the same runtime result, the existing TUI and reproducibility suites plus new regression tests catch a behavior change, and every change is a normal revertible commit.

AW-TIER: standard

### Step R1

- Checked: every cited path and symbol against lane HEAD `8ac3407`. `src/pubrun/__main__.py:2710` holds `from pubrun.__init__ import __version__` inside `_run_bug_report`; no other file in `src/` or `tests/` uses that import. `RunInProgressOrCrashedError.__init__`, `_run_cite`, `_parse_log_file`, and `_SubcommandAwareArgumentParser.error` hold the other four `__main__.py` errors (lines 67, 1144, 2517, 2763). `ActionsPanel.on_button_pressed`, `handle_deletion_result`, `ConfirmDeleteModal(ModalScreen[bool])`, and the three `self.app.RefreshSidebar()` posts exist in `actions.py`; `tui/app.py` imports `actions.py`, so `PubrunTUIApp` cannot be imported at module level there. `DiffView.run_difference` and `_is_select_empty` (from `pubrun.tui.widgets.config`) exist in `diff.py`. `_make_finding`, `_make_preflight_check`, `_resolve_input_local_path`, `_preflight_invocation`, and `compare_with_current_environment` exist in `reproducibility.py`.
- Baseline (`mypy` 2.3.1, Python 3.14.6, `textual` 8.2.8, run against a scratch copy of the lane `src/` and `pyproject.toml` under `/tmp/opencode`): `mypy src/pubrun` and `mypy --explicit-package-bases src/pubrun` exit 2 with `Source file found twice under different module names: "pubrun" and "pubrun.__init__"`. With only the import fixed, `mypy --ignore-missing-imports src/pubrun` gives `Found 175 errors in 24 files (checked 58 source files)`.
- PR-003: E-01's expected outcome named `mypy --explicit-package-bases src/pubrun` as proof of the fix. That flag does not avoid the duplicate-module abort (measured: still exit 2), and with only that flag the import fix gives 179 errors, not a passing run.
- PR-004: E-03 called `config.py` and `analysis/diff.py` "clean" modules that a deliberate error must fail. `config.py` has 1 error (line 117, `var-annotated`) and `analysis/diff.py` has 5 (lines 114, 118, 130, 139, 242), so both must be on the legacy list and the stated mutation check could not pass.
- PR-002: E-02 described the `reproducibility.py` work as "guard `None` before `+` arithmetic". The module has 49 errors, 3 of them `+` operators; most of the rest come from `d.get(k) if isinstance(d.get(k), T) else {}`, which `mypy` cannot narrow (21 occurrences by `grep`), plus `.strip()` on an un-narrowed `.get()` and `dict-item` errors from an inferred `Dict[str, str]` `details`. A plan-faithful executor would have stopped at 3 fixes and failed V-02.
- PR-006: `__main__.py` has 4 type errors besides the import, and the plan never said whether `pubrun.__main__` is fixed or listed.

### Step R2

- Checked: author-phase lint (`aw ipd lint --phase author --agent`: `clean`, exit 0, 0 findings), the E/V bijection, each V-item against what its E-item produces, and each E-item by prototype. The prototype ran in a scratch copy under `/tmp/opencode`, never in the lane.
- Prototype results: the E-02 edits removed all errors in `__main__.py` (4), `actions.py` (8), and `diff.py` (3). The E-06 helpers (`_dict_field`, `_list_field`, `_str_field`), the `_resolve_input_local_path` rewrite, the `mode_no_subprocess_patch` read, and the first-per-function `details: Dict[str, Any]` annotation removed all 49 `reproducibility.py` errors in about 100 changed lines; annotating every `details` assignment instead produced `no-redef` errors. After those edits, 111 errors remained in exactly the 20 modules E-03 lists. With the E-03 configuration, `mypy` and `mypy src/pubrun` both printed `Success: no issues found in 58 source files`, exit 0, also under `--python-version 3.10` and `3.12`. A targeted test run of `tests/test_tui.py`, `tests/test_tui_bugs.py`, `tests/test_timing_consumers.py`, the three reproducibility suites, `tests/test_cli.py`, `tests/test_checks_commands.py`, `tests/test_report_subpackage_integrity.py`, and `tests/test_templates.py` gave `1 failed, 284 passed`; the one failure was `FileNotFoundError` on `docs/research-use.md`, absent from the scratch copy, and the citation tests passed in the lane checkout (`4 passed`).
- PR-001: with `pubrun.__main__` on the `ignore_errors` list, restoring the `pubrun.__init__` import still gave `Success` (exit 0), because the override also suppresses the duplicate-module error. With `__main__` fixed and off the list, the same mutation gave exit 2. E-02 now fixes `__main__.py`, and E-03 forbids listing it.
- PR-005: V-02 ran `mypy` on three files and V-03 on `src/pubrun`, but no V-item showed that the gate fails on a regression. In the prototype, `_aw_mut: int = "x"` appended to `actions.py`, `diff.py`, `reproducibility.py`, or `report/methods.py` exited 1; a new file with that line exited 1; the same line in listed `tracker.py` exited 0; and the restored import exited 2. A stale `.mypy_cache/` once hid the duplicate-module error, so the procedure now deletes the cache before each run.
- PR-007: E-03 set `ignore_missing_imports = true` without saying it was per module, and omitted `tomli`. Under `--python-version 3.10`, `tomli` imports in `__init__.py` and `_config_boot.py` failed with `import-not-found`; adding `tomli` to the per-module override fixed it. Setting `python_version = "3.8"` made `mypy` 2.x refuse the configuration (`must be 3.10 or higher`), so E-03 now says not to set it.
- PR-008: no test caught the runtime effect of the duplicate import or a dropped `strip()` in the new helpers. At review, `_run_bug_report()` with the old import left `sys.modules["pubrun.__init__"]` set to a second module object, re-running `_execute_boot_sequence`. Changing `_str_field` to return the unstripped value left the three reproducibility suites at `42 passed`. A prototype `tests/test_type_repair_regressions.py` (4 tests) passed against the fix, failed 2 tests under the `strip()` mutation, and failed 1 under the restored import. E-05 now adds it.
- PR-009: E-02 gave no mechanism for the `RefreshSidebar` dispatch. `self.app` is typed `App[Any]`, which has no `RefreshSidebar`, and a module-level import of `PubrunTUIApp` is circular. A function-local import in a helper type-checks; with the helper returning a plain `Message()`, `tests/test_tui.py` and `tests/test_tui_bugs.py` failed 5 tests, so the existing suites guard it.

### Step R3

- Checked: the plan adds no network access, credential, or subprocess outside tests. The new regression test runs `sys.executable` with `webbrowser.open` replaced, so it opens no browser. The CI job installs only the declared `dev` and `tui` extras. No security finding.

### Step R4

- Checked: the `AGENTS.md` no-code-pinning rule (no item asks a test to read production source; E-05 asserts on `sys.modules` and on `compare_with_current_environment` output), right-sizing, sibling scopes, and the orchestrator `vdxiw8`. `bzi46m` also edits `pyproject.toml`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`, and `CHANGELOG.md`, and this plan already depends on `executed:bzi46m`. `bwoyan` edits `tui/widgets/details.py` and adds `tests/test_tui_widgets.py`; no other `test-audit` plan lists a file in this plan's scope.
- PR-010: E-04 offered "a job (or step on the Linux quality job)". No quality job exists in `ci.yml`, before or after `bzi46m`. E-04 now names a `typecheck` job on `ubuntu-latest` with Python 3.12, the `pip install -e ".[dev,tui]"` install (`textual` types are needed for the TUI widgets), `mypy --version`, and `mypy`. Running Linux only is correct: `mypy --platform win32` reported 7 POSIX-only errors in three unlisted modules.
- PR-011: the gate told the executor to "move this plan to `.aw/records/plans/executed/`" by hand, and lacked the scope declaration, the validation-honesty rule, and the runner and executor split for finalization. It now carries the five-element execution contract with `aw commit gzc672` and `aw ipd finalize gzc672`.
- PR-012: the documentation-sync N/A gave no evidence, yet the plan adds a contributor-facing blocking CI check. `grep -rln "mypy\|type-check" .aw/records/specs docs` found no match, and `CONTRIBUTING.md` "Development setup" documents only `python -m pytest`. E-07 adds the type-check command to `CONTRIBUTING.md` and a `CHANGELOG.md` entry.
- PR-013: the diagram showed a four-step line and the label "New/clean modules strictly checked", which did not name the 20-module list or the regression branch. It now shows each E-item, the dependency edges, and the pass and fail branches.
- PR-014: V-02 and V-03 ran `mypy` without saying where. The developer virtual environment's editable `pubrun` resolves to another checkout, and a `mypy --explicit-package-bases src/pubrun` run in the lane printed 5 lines with paths outside the lane. The conventions now say to run from the repository root with the E-03 `mypy_path = "src"` setting, which produced no outside path in the prototype.

### Step S5

- Checked: open questions (none); deferrals (the T-19 `Carrier: qqwebg` entry, which exists in `.aw/records/backlog/open/`; a second `Carrier: qqwebg` entry for per-platform checking; two `Carrier-Declined` entries added at review, for the unpinned `mypy` version and the push-gated CI run). Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so the lane outcome carries no question.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R2 (gate cannot catch the regression it exists for) | Prototype: restored `pubrun.__init__` import with `pubrun.__main__` listed gave exit 0; unlisted gave exit 2 | Listing `__main__` with `ignore_errors` hides the duplicate-module error, so reverting E-01 would pass CI. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02(a) fixes the 4 `__main__.py` errors; E-03 forbids listing `pubrun.__main__`; V-03 checks the restored import exits 2. |
| PR-002 | high | IN-SCOPE | R1 (work understated) | `reproducibility.py`: 49 errors, 3 `+` operators, 21 un-narrowable `.get()` patterns | "Guard `None` before `+`" covered 3 of 49 errors, so V-02 could not pass as written. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-06 specifies `_dict_field`, `_list_field`, `_str_field`, the `_resolve_input_local_path` rewrite, and the `details` annotation rule; prototype reached 0 errors. |
| PR-003 | medium | IN-SCOPE | R1 (wrong verification command) | `mypy --explicit-package-bases src/pubrun`: exit 2 before the fix, 179 errors after | E-01's outcome cited a command that neither avoids the abort nor passes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 cites `grep` for the import and `mypy src/pubrun` under the E-03 configuration, plus the runtime effect. |
| PR-004 | medium | IN-SCOPE | R1 (false claim) | `config.py:117`; `analysis/diff.py:114,118,130,139,242` | E-03 named two modules with errors as clean mutation targets. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Both are on the 20-module list; the mutation targets are the four fixed modules and `report/methods.py`. |
| PR-005 | high | IN-SCOPE | R2 (evidence cannot prove the change) | Prototype mutation results; stale `.mypy_cache/` once hid the abort | No V-item showed that the gate fails on a type regression. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03 and V-03 list seven mutation checks with expected exit codes, and a cache-clearing procedure. |
| PR-006 | medium | IN-SCOPE | R1 (unstated decision) | `__main__.py` errors at lines 67, 1144, 2517, 2763 | The plan did not say whether `__main__` is fixed or listed. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02(a) fixes all four with the prototype edits. |
| PR-007 | medium | IN-SCOPE | R2 (configuration incomplete) | `--python-version 3.10`: `tomli` `import-not-found`; `python_version = "3.8"` refused by `mypy` 2.x | `ignore_missing_imports` scope was unstated, `tomli` was missing, and no Python target guidance was given. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03 gives the exact configuration, per-module `ignore_missing_imports` including `tomli`, and says not to set `python_version`. |
| PR-008 | medium | IN-SCOPE | R2 (missing test) | `_str_field` without `strip()`: `42 passed`; old import leaves `sys.modules["pubrun.__init__"]` | No test caught the duplicate package load or a dropped `strip()` in the refactor. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-05 adds `tests/test_type_repair_regressions.py` (4 tests); V-05 checks both mutations fail it. |
| PR-009 | low | IN-SCOPE | R2 (unspecified technique) | `App[Any]` has no `RefreshSidebar`; `tui/app.py` imports `actions.py` | "Typed `RefreshSidebar` message dispatch" gave no mechanism, and the obvious import is circular. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02(b) specifies the function-local `_refresh_sidebar_message` helper; existing tests failed 5 under a broken helper. |
| PR-010 | medium | IN-SCOPE | R4 (nonexistent CI target) | `ci.yml` has only `test`; `bzi46m` adds `extra-suites`, `no-tui`, `packaging` | E-04 referred to a "Linux quality job" that does not exist and gave no runner, Python version, or install. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04 names the `typecheck` job, runner, Python 3.12, install, and steps; V-04 runs them in a fresh 3.12 environment. |
| PR-011 | medium | IN-SCOPE | S7 (execution contract) | Gate text "move this plan to `.aw/records/plans/executed/`" | The gate told the executor to move the plan by hand and lacked three contract elements. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Replaced with the five-element contract and `aw ipd finalize gzc672`. |
| PR-012 | low | IN-SCOPE | R4 (doc sync) | `grep` over specs and `docs/`: no match; `CONTRIBUTING.md` lists only `pytest` | The N/A had no evidence, and a new blocking CI check was undocumented for contributors. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-07 updates `CONTRIBUTING.md` and `CHANGELOG.md`; the sync section cites the search. |
| PR-013 | low | IN-SCOPE | P (diagram) | Diagram labels vs. revised items | The diagram omitted the legacy list, the regression branch, and the new items. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Redrawn with each E-item, its dependencies, and the pass and fail branches. |
| PR-014 | low | IN-SCOPE | R2 (environment trap) | Lane `mypy --explicit-package-bases src/pubrun` printed 5 paths outside the lane | Without a run location, V-evidence could check a different checkout. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Conventions require running from the repository root with `mypy_path = "src"`. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Shared configuration and CI contract; no spec, security, or public API surface | yes |
| D-2 | Fix `reproducibility.py` now or list it? | Fix it (E-06) | Add `pubrun.report.reproducibility` to the list | The Goal and orchestrator row 02 require it fixed; the prototype showed about 100 behavior-preserving lines, guarded by existing suites and E-05 | yes |
| D-3 | Ratchet mechanism | Per-module `ignore_errors = true` | Per-module `disable_error_code`; global `ignore_missing_imports` | `ignore_errors` is the only override that silences every legacy error without hiding new modules; a global missing-import ignore would hide a missing first-party module | yes |
| D-4 | Keep `pubrun.__main__` off the list? | Yes, fix its 4 errors | List it | Listing it hides the E-01 regression (PR-001) | yes |
| D-5 | Pin `mypy` in CI? | No; print `mypy --version` | Pin in the job or in the `dev` extra | The project pins no development tool; a pin would change the `dev` extra shared with `bzi46m` | yes |
| D-6 | Split the plan after `IPD-Z603` advisories (7 E-items, 9 Scope-Paths)? | Keep one plan, with a recorded cohesion rationale | Split E-06 into its own plan | The ratchet list is valid only for the combined clean set; a split needs a temporary list entry and a second `pyproject.toml` edit | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. E-06 and E-07 with V-06 and V-07 were added (`Highest E allocated: 07`). `- Scope-Paths:` gained `tests/test_type_repair_regressions.py`, `CONTRIBUTING.md`, and `CHANGELOG.md`. `- Item-Dependencies:` is unchanged (`executed:bzi46m`). A re-review pass is required.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: re-read the revised plan in full against lane HEAD `8ac3407`. One citation was wrong after Round 1: E-02(a) named `_get_citation`; the function holding `from pubrun import __version__ as _ver` is `_run_cite` (line 1132). Corrected in place as a citation fix. Every other symbol in the rewritten items resolves: `RunInProgressOrCrashedError` (58), `_parse_log_file` (2516), `_run_bug_report` (2704), `_SubcommandAwareArgumentParser` (2762), `ActionsPanel.on_button_pressed` (184), `handle_deletion_result` (269), `DiffView.run_difference` (78), `_make_finding` (146), `_resolve_input_local_path` (3608), `_preflight_invocation` (4079), the `mode_no_subprocess_patch` finding (1233), the `recorded_working_directory` and `entrypoint_script` check records, `report/methods.py`, and the three `tomli` imports. Every expected value in E-01 to E-07 matches a prototype result.

### Step R2

- Checked: `aw ipd lint --phase review-finalize --agent`: `clean`, exit 0, 2 `IPD-Z603` info advisories (7 E-items against guidance 5; 9 Scope-Paths against guidance 8), answered by the gate's cohesion rationale (D-6). E-01 to E-07 map 1:1 to V-01 to V-07. Dependencies are acyclic: E-02, E-06 need E-01; E-05 needs E-01 and E-06; E-03 needs E-02 and E-06; E-04 needs E-03; E-07 needs E-04. `- Scope-Paths:` matches the Scope line, the gate's scope declaration, and the files the E-items edit.

### Step R4

- Checked: the added scope paths are disjoint from every sibling except `bzi46m`, which this plan already follows. E-07's prose falls under the `AGENTS.md` dash rule, and V-07 checks it.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-015 | low | IN-SCOPE | R1 (citation) | `src/pubrun/__main__.py:1132` `def _run_cite` | E-02(a) named a nonexistent function `_get_citation`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Renamed to `_run_cite`. |

### Step S6

- Checked: Round 2 changed one function name and added the cohesion rationale; the E/V id set, `- Scope-Paths:`, and `- Item-Dependencies:` are unchanged since Round 1's S6. No new structural finding. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
