# Review findings: ipd updt75

- Subject-Id: updt75
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-tmngjn-01-updt75-import-run-lock-from-pubrun-core-so-mode-module-background-c.ipd.md` (front matter, Mermaid flowchart, E-01 to E-04, conventions, reproduction script, observation table, deferrals, OQ-01, V-01 to V-04, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches the observed import order (`auto.py` calls `_execute_boot_sequence` before `_pkg._run_lock = _run_lock`) and both failure branches reproduce.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning (PR-004). |
| Findings, fix trial | "`suppressed` hardware with an active run in all six modes with `depth = \"off\"`" | Says the four auto-starting modes auto-start, and `noauto`/`minimal` get their run from an explicit `pubrun.start()` | Review run showed `noauto` and `minimal` have no active run after import, by design (PR-004). |
| Proposed changes item 2; E-03 | "six modes" / "covers all six mode modules" | Adds plain `pubrun` to the test coverage text | Matches the PR-001 control case. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/tracker.py`, `tests/test_import_modes.py`, `CHANGELOG.md`, no `.spec.md`), E-item and task-group counts (4 items, 4 groups).

1. No: no spec, CLI option, output format, file format, or configuration key changes; the manifest schema is unchanged and `pubrun._run_lock` stays bound for external callers.
2. No: touches no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 4 E-items in 4 small groups across three files, one of them six identical import lines.
4. Yes: `- Scope-Paths:` lists all three files.
5. Yes: the six imports sit on the start, finalize, and stop path of every run in every import mode; a wrong edit (for example a module-level `pubrun.core` import, which is circular) would break tracking for all users.

AW-TIER: standard

### Step R1 (references)

- Checked: `src/pubrun/tracker.py` lines 276 (`Run.__init__` rollback), 483 (`_collect_hardware_section`), 512 (`_collect_host_and_filesystem`), 652 (nested `_collect_hardware` in `_bootstrap_engines`), 1108 (`_finalize_state`), 1385 (`stop`): six `from pubrun import _run_lock`, matching E-01's list; line 1447 `from pubrun import __version__, __commit__` in `to_manifest_dict`. `src/pubrun/core.py` line 22 `from pubrun.tracker import Run, get_current_run` and line 26 `_run_lock = threading.RLock()` (confirms the circular-import reason). `src/pubrun/auto.py` imports `_run_lock` and `_execute_boot_sequence` from `pubrun.core`, calls the boot, then assigns `_pkg._run_lock` (line 77); the same late assignment is in `full.py`, `nopatch.py`, `noconsole.py`, `noauto.py`, `minimal.py`, and `src/pubrun/__init__.py` line 390 (`_ensure_core_loaded`). `src/pubrun/__init__.py` line 46/48 binds `__version__` before mode routing (line 319) and line 277 defines `__getattr__`. `tests/test_capture_isolation.py::_worktree_env` drops `PUBRUN_IMPORT_MODE`/`PUBRUN_AUTO_START` and prepends `src`. `grep -rn "_run_lock" tests` finds only a docstring. `CHANGELOG.md` has `## [Unreleased]` with `### Fixed` at line 105. Commit `00636a1` exists and is an ancestor of the lane HEAD.
- Pending plan `3aalwv` (Set `uatvzh`) also edits `src/pubrun/tracker.py` (`Run.stop`, `Run._finalize_state`). Its E-01 says it leaves the `_run_lock` import lines as they are and does not depend on which form is present. The worktree merge gate handles the textual overlap. The plan did not mention the overlap, so I recorded it in Findings (PR-004).

### Step R2 (executability)

- Reproduced with the plan's script (extended to print `filesystem` and the `stop()` duration): `auto`, `full`, `nopatch`, `noconsole` printed `hardware=pending host=pending fs=pending stop=2.01` with `ImportError(_run_lock)` in stderr; `noauto` and `minimal` printed `complete` with `stop=0.02`. Direct stderr: `Exception in thread pubrun-hw:` then `ImportError: cannot import name '_run_lock' from 'pubrun' (...)`, so both strings E-02 asserts on occur. With `depth = "off"`, the four auto-starting modes printed `pubrun auto-start failed (tracking disabled): cannot import name '_run_lock' from 'pubrun'` and had no active run.
- Applied E-01 to a scratch copy of `src/` with `sed` (`grep -c` printed `6`): all six modes printed `complete` for all three sections, `stop=0.02`, clean stderr, under Python 3.14.6, 3.12, and 3.11. With `depth = "off"`, the four auto-starting modes had an active run with `suppressed` hardware.
- Prototyped the E-02 class as specified (poll loop, 20 s cap, guarded `depth = "off"` script) plus a plain-`pubrun` control: base `src/` gave `8 failed, 4 passed` (exactly the four auto-starting modes of both tests failed); fixed `src/` gave `12 passed in 26.32s`, and `12 passed` again with `-n 6`. The original ten-case version gave `8 failed, 2 passed` and `10 passed`.
- V-02 originally asked for a base-commit worktree run but gave no commands. In that worktree, the test's `parents[1] / "src"` resolves to the worktree's own unfixed `src/`, so the method works; the commands are now spelled out (PR-002).
- Full suite on the unmodified lane tree, measured at the previous review in this lane: `1819 passed, 2 skipped in 517.10s`.
- Gate: has precondition, scope fence with `--scope-reason`/`--scope-ack`, honesty, `aw commit updt75 -- ...` with never-push, and runner-versus-executor `aw ipd finalize`. It lacked the pre-transition lint step and the OQ-01 status (PR-003).
- Scratch files under `/tmp/opencode/updt75` and the one run directory my direct probe left in `/tmp/runs` were deleted.

### Step R3 (security, full form)

- Checked: the change swaps the module a lock is imported from; the lock object is identical (`pubrun._run_lock` is always bound from `pubrun.core._run_lock`), so locking order (`_run_lock` before `_write_lock`) and the hardware write window (`_hardware_write_closed`) are unchanged. The new tests write only under `tmp_path`. No new data is captured or exposed; the fix restores capture that the config already enables. No security findings.

### Step R4 (engineering)

- Checked: `pubrun.core` is fully imported whenever a `Run` exists (core imports tracker, and `Run` is constructed through core), so the function-local `from pubrun.core import _run_lock` cannot hit a partially initialized module. Choosing the `pubrun.core` import over reordering six mode modules is the smaller change and also covers `_ensure_core_loaded` (OQ-01 basis holds).
- Tests: subprocess-based, assert on stderr and manifest content, read no source. The default-config test polls up to 20 s and accepts any non-`pending` status, which tolerates slow hardware probes. The CHANGELOG claim "plain `import pubrun` was not affected" had no test; a plain `pubrun` control case now pins it (PR-001).
- CI matrix deferral: consistent with sibling plans `2e6xfq` and `3aalwv`, which carry the same `Carrier-Declined` text.

### Step S5

- Checked: OQ-01 (resolved, non-blocking; the backlog acceptance allows either fix, re-confirmed by the review fix trial). Both deferrals carry `Carrier-Declined` with reasons. All findings have Low remediation risk and are fixed. No question needs the human; no finding is OPEN or DEFERRED.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | low | UNDER-SCOPE | R4 D (claim without a test) | E-03 "plain `import pubrun` was not affected"; prototype with a `pubrun` case passed on both the base and the fixed `src/` | The changelog asserts plain `import pubrun` is unaffected, but E-02 tested only the six mode modules, so a regression in the root import path would pass unnoticed. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added plain `pubrun` as a control case to both parametrized tests (12 cases); updated Required tests, V-02 (exact eight FAILED and four PASSED on the pre-fix code), Proposed changes, and E-03 (recommendation strength: strong). |
| PR-002 | low | IN-SCOPE | R2 (evidence concreteness) | Required tests "copy the new `tests/test_import_modes.py` into a temporary `git worktree` of the base commit"; V-02 "at least the `auto`, `full`, `nopatch`, and `noconsole` cases" | The pre-fix run gave no commands or removal check, and "at least" let V-02 pass even if a non-auto-starting case failed. The `depth = "off"` script did not say how it behaves when no run exists on the base. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Named `git worktree add /tmp/opencode/updt75-prefix HEAD`, the removal command, and pasted `git worktree list`; V-02 now requires exactly the eight auto-starting cases FAILED and four PASSED; E-02 says the `depth = "off"` script stops the run only when one is active, so the base fails on the "run is active" assertion (recommendation strength: strong). |
| PR-003 | low | UNDER-SCOPE | R2 gate (execution contract) | Gate item 5 "finalize this plan with `aw ipd finalize updt75`" | The lifecycle step did not require `aw ipd lint --phase pre-transition` to conform after all E/V items, and the precondition did not state OQ-01's status. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added both (recommendation strength: medium). |
| PR-004 | low | IN-SCOPE | Check P (writing, `IPD-C802`); R1 (evidence, cross-plan) | `aw ipd lint --phase author` reported 2 `IPD-C802` info diagnostics; fix-trial sentence "an active run in all six modes with `depth = \"off\"`"; plan `3aalwv` E-01 | Two em dashes in the validation boilerplate. The fix-trial sentence implied `noauto` and `minimal` auto-start. Findings lacked a review re-check, the green-suite baseline, and the overlap with pending plan `3aalwv` in `src/pubrun/tracker.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the dashes, corrected the fix-trial sentence, and added a re-check paragraph (reproduction, fix trial on 3.14/3.12/3.11, prototype results, `1819 passed, 2 skipped` baseline) and a `3aalwv` independence note (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should the tests pin the "plain `import pubrun` unaffected" claim? | Add `pubrun` as a parametrized control case in both tests | A separate test; drop the claim from the changelog | The same script works unchanged with `import pubrun as pubrun`; the prototype passed on base and fix; one parameter adds about 2 s | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined E-02, E-03, Findings, Proposed changes, Required tests, V-02, the boilerplate, and the gate. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
