# Review findings: ipd whacr3

- Subject-Id: whacr3
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-pgcmea-01-whacr3-confirm-the-pubrun-tui-app-sys-modules-restore-and-add-a-reg.ipd.md` (front matter, Mermaid flowchart, E-01 to E-03, P-01 to P-04, findings, deferrals, OQ-01, V-01 to V-03, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart omitted the cleanup branch that decides whether the leak becomes a failure (see PR-001).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Findings flowchart | Unrestored entry always leads to the Mock being imported | Adds a decision node: a later `test_tui_missing_dependencies_prints_notice` deletes the entry first, or not | The diagram must match the mechanism measured at review (PR-001). |
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning (PR-005). |
| F-05 | "`vv4vdd` ... pending ... leaves backlog item `pgcmea` open" | `vv4vdd` is `reviewed` and names this plan as `Carrier: whacr3`; `pgcmea` is graduated to `whacr3` | Stale record state (PR-004). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`tests/test_tui.py` only, no `.spec.md`), E-item and task-group counts (3 items, 2 groups).

1. No: adds one test function; no spec, CLI option, output format, file format, or configuration key.
2. No: test code only; touches no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 3 E-items in 2 task groups, one file.
4. Yes: `- Scope-Paths:` lists `tests/test_tui.py`.
5. No: a test-only addition, easy to revert.

AW-TIER: simple

### Step Q

- Checked: `tests/test_tui.py` (`test_tui_cli_parser_and_run` with `mock.patch.dict(sys.modules, {"pubrun.tui.app": mock_module})`; `test_tui_missing_dependencies_prints_notice` "Remove mock module if populated", which deletes `sys.modules["pubrun.tui.app"]`); `git show 25dd11b` (replaces the bare assignment with `mock.patch.dict`); `pyproject.toml` `testpaths = ["tests"]`, `pythonpath = ["src"]`, `addopts = "... -p no:randomly"`; backlog `pgcmea` (graduated to `whacr3`); plan `vv4vdd` (reviewed, `Carrier: whacr3`). Host: Linux, Python 3.14.6, pytest 8.2.2, `pytest-randomly` 4.1.0, `pytest-xdist` 3.8.0, `textual` 8.2.8.
- Reproduced on a scratch copy of `25dd11b^:tests/test_tui.py` (deleted afterwards): with `-p no:xdist -o addopts="" -p no:randomly` it printed `11 passed`, so the pre-fix copy does NOT fail in file order. The pair `test_tui_cli_parser_and_run` then `TestTuiResourceView` printed `1 failed, 1 passed`. With `-p randomly` seeds `1` to `5`: `11 passed`, `11 passed`, `1 failed, 10 passed`, `1 failed, 10 passed`, `11 passed`.
- Observed that `-o addopts=""` without `-p no:randomly` prints `Using --randomly-seed=1149987071` and shuffles; so the authored "file order" command (P-03 run 1) is actually a random order, and so is the authoring run behind F-02's `3 failed, 8 passed` (PR-001, PR-002).
- Prototyped P-02 on scratch copies (deleted): fixed copy printed `12 passed` in file order, `12 passed` for seeds `1` to `5`, and `12 passed` with `-n 2 --dist loadfile`. Leak copy: the guard alone printed `1 failed` with `AssertionError: assert <Mock id='...'> is <module 'pubrun.tui.app' from '.../src/pubrun/tui/app.py'>`; the whole leak copy in file order printed `1 failed, 11 passed` (only the guard fails), confirming that the guard catches what whole-file runs miss.
- On HEAD: the pair printed `2 passed`; file order, seeds `1` and `2`, and `-n 2 --dist loadfile` printed `11 passed`.
- What could break: nothing outside the test file. The guard calls another test function directly; it runs that function's assertions a second time, which is harmless. A scratch file named `_pgcmea_leak_probe.py` is outside the default `test_*.py` collection pattern, so a forgotten copy would not enter `aw suite`; E-03 still deletes it.
- Gate: the plan had approval, scope, commit, and lint-before-move text, but no `--scope-reason` fence and no runner-versus-executor `aw ipd finalize` ownership, and it described the move to `executed/` as the executor's own act (PR-003).

### Step S5

- Checked: OQ-01 (resolved, non-blocking, basis commit `25dd11b` and backlog `pgcmea` text accepting either restore form; re-confirmed by the review runs above). CI-matrix and production-code deferrals carry `Carrier-Declined` with reasons. All findings have Low remediation risk and are fixed. No question needs the human; no finding is OPEN or DEFERRED.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | medium | IN-SCOPE | R1 (evidence contradicts claim) | Plan F-02 "The pre-fix copy fails in plain file order"; review run of `25dd11b^:tests/test_tui.py` with `-p no:xdist -o addopts="" -p no:randomly` printed `11 passed`; `tests/test_tui.py::test_tui_missing_dependencies_prints_notice` "Remove mock module if populated" | F-02 claimed the pre-fix copy fails in file order. It does not: the next test in file order deletes the leaked entry. The authoring run cleared `addopts`, which re-enabled `pytest-randomly`, so it ran shuffled. The flowchart omitted the cleanup branch. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote F-02 with the measured mechanism and review evidence, added the cleanup decision node to the flowchart, and extended F-03 with the review runs (recommendation strength: very strong). |
| PR-002 | medium | UNDER-SCOPE | R4 E (validation that cannot detect the defect) | P-03 run 1 `-o addopts=""` without `-p no:randomly` prints `Using --randomly-seed=...`; pre-fix copy passes whole-file file order and xdist `loadfile` | P-03 run 1 was labelled file order but shuffled at random, and none of P-03 runs 1 to 3 reliably exposes the leak; only the targeted pair does (pre-fix: `1 failed, 1 passed`). E-03 could pass on a regressed file through luck of the seed. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `-p no:randomly` to P-03 runs 1 and 3 and to P-04, added P-03 run 4 (the targeted pair), documented the `addopts` interaction under Step 0 conventions, and updated E-03, Required tests, and V-03 (V-03 now requires no `Using --randomly-seed=` line in run 1 and both pair tests `PASSED`) (recommendation strength: strong). |
| PR-003 | low | UNDER-SCOPE | R2 gate (execution contract) | `steps/r2-executability.md` "An execution contract in the gate: ... scope fence ... lifecycle transition (unconditional finalize obligation with conditional runner/executor ownership ...)" | The gate lacked the `--scope-reason` fence and runner-versus-executor `aw ipd finalize` ownership, and framed the move to `executed/` as a manual act; it also used a `<this plan>` placeholder in the commit command. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the gate paragraph with a five-part execution contract: precondition, scope fence, validation honesty, `aw commit whacr3 -- tests/test_tui.py` with never-push, and `aw ipd finalize whacr3` owned by the runner in a lane or by the executor outside one (recommendation strength: strong). |
| PR-004 | low | IN-SCOPE | R1 (stale records) | `.aw/records/plans/pending/20261122-ivpkar-01-vv4vdd-*.ipd.md` (`- Status: reviewed`, `- Carrier: whacr3`); `.aw/records/backlog/graduated/20261122-pgcmea-01-pgcmea-*.backlog.md` "graduated by run run-20261123T005542Z-1001883: whacr3" | F-05 said `vv4vdd` was pending and left `pgcmea` open; `vv4vdd` is reviewed and names this plan as the carrier, and `pgcmea` is graduated to this plan. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote F-05 to the current record state (recommendation strength: strong). |
| PR-005 | low | IN-SCOPE | Check P (writing, `IPD-C802`) | `aw ipd lint --phase author` reported 2 `IPD-C802` info diagnostics at the validation boilerplate | Two em dashes in the runtime-demonstration reachability rule. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced with commas and parentheses; `aw ipd lint --phase review-finalize` now reports 0 findings (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Which run should prove that the restore holds, given that whole-file runs pass on the pre-fix copy? | Add the targeted pair (`test_tui_cli_parser_and_run` then `TestTuiResourceView`) in a fixed order, keep the whole-file runs and the guard | Rely on the guard alone; add more random seeds | Pre-fix pair printed `1 failed, 1 passed` while the whole file in file order printed `11 passed`; seeds fail or pass depending on node ids | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined E-03, P-03, P-04, findings, the flowchart, Required tests, V-03, and the gate. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
