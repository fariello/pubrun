# Review findings: ipd vv4vdd

- Subject-Id: vv4vdd
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-ivpkar-01-vv4vdd-make-the-parallel-test-suite-pass-fix-test-expected-script-m.ipd.md` (front matter, Mermaid flowchart, E-01 to E-03, P-01 to P-03, findings, deferrals, open questions, V-01 to V-03, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches `pubrun.capture.liveness.is_same_process` and `_match_script_in_tokens` (True, False, None branches; None falls through to the start-time comparison).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning (PR-004). |
| OQ-02 heading | "Does plan `4h2qwz` on branch `aw/lane/12rcu8` make this plan redundant?" | "Does plan `4h2qwz` make this plan redundant?" | The branch qualifier is stale; the plan is now on this tree as superseded (PR-001). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`tests/test_liveness.py` only, no `.spec.md`), E-item and task-group counts (3 items, 2 groups).

1. No: changes one test function; no spec, CLI option, output format, file format, or configuration key.
2. No: test code only; touches no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 3 E-items in 2 task groups, one file.
4. Yes: `- Scope-Paths:` lists `tests/test_liveness.py`.
5. No: a test-only change with no production edit, easy to revert.

AW-TIER: simple

### Step Q

- Checked: `pubrun.capture.liveness` (`is_same_process` with default `tolerance=86400.0`, `_match_script_in_tokens`, `_script_is_generic`, `_GENERIC_SCRIPT_TOKENS`, `_check_command_linux`, `_check_command_macos`, `_check_command_windows` via `wmic`); `tests/test_liveness.py` (module imports, `TestIsSameProcess`, `test_wrong_start_time_does_not_match` using `- 172800`); `tests/test_status.py` `subprocess.Popen` precedent; `tests/test_tui.py` (`mock.patch.dict(sys.modules, ...)` from commit `25dd11b`); `aw suite --help` (narrowed selections refused with exit 2); `pyproject.toml` `addopts`; backlog items `ivpkar`, `12rcu8`, `sd7kvt`, `pgcmea`; plans `4h2qwz`, `ig2etn` (superseded), `whacr3` (pending).
- Reproduced on this tree: `python3 -m pytest -n 2 -p no:cacheprovider --no-cov -q tests/test_liveness.py` printed `FAILED tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches` and `1 failed, 26 passed`; serially `27 passed`. `aw suite --no-cache` printed `1 failed, 1820 passed in 137.54s` with the same single failure (exit 1), so no other failure would block V-03.
- Ran P-02 on this tree: the `-p no:xdist` run and the `-n 2 --dist loadfile` run each printed `11 passed` with both `TestTuiReproducibilityAndActions` tests `PASSED`; the `-p randomly` runs for seeds 1, 2, and 3 each printed `11 passed` and exited 0. The commands are runnable as written (`pytest-xdist` 3.8.0, `textual` 8.2.8, `pytest-randomly` installed).
- Prototyped the P-01 body in a scratch file outside the repo: it passed serially and with `-n 2`, a sibling check with `expected_script="other_probe_script.py"` returned `False`, and no `liveness_probe_script` process remained afterwards.
- Found that with `time.time()` as the expected start the assertion is not falsifiable for the behavior it names: a generic `-c` child gave `is_same_process(..., expected_script="python")` `True` with `time.time()` (inconclusive script check, start-time fallback within tolerance) and `False` with `time.time() - 172800`. The prototype with `- 172800` and the probe script still passed under `-n 2` (PR-002).
- What could break: nothing outside the test. Matrix risk: on Windows the check uses `wmic`, which returns `None` where unavailable, and the plan keeps the skip on `None`; the plan's deferral records that the CI matrix needs a push.
- Records: F-07 and OQ-02 described `4h2qwz` as present only on branch `aw/lane/12rcu8` and `12rcu8` as `open`; on this tree `12rcu8` and `sd7kvt` are `done` ("Duplicate of ivpkar (carried by plan vv4vdd)"), `4h2qwz` and `ig2etn` are superseded by `vv4vdd`, and `pgcmea` is graduated to `whacr3` (PR-001).
- Gate: the plan had approval, scope, commit, and lint-before-move text, but no scope-reason/scope-ack fence and no `aw ipd finalize` ownership (runner versus executor), and it described the move as the executor's own act (PR-003).

### Step S5

- Checked: OQ-01 (resolved, non-blocking, basis commit `25dd11b` and the P-02 runs above), OQ-02 (resolved, non-blocking; rationale corrected under PR-001), deferral carriers (two `Carrier-Declined` with reasons, `pgcmea` row now `Carrier: whacr3`, CI-matrix row `Carrier-Declined` because a push is a human act). All findings have Low remediation risk and are fixed. No question needs the human. No finding is OPEN or DEFERRED.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | low | IN-SCOPE | Q (stale records) | `.aw/records/backlog/done/20261122-12rcu8-01-12rcu8-*.backlog.md` and `...sd7kvt...` ("Duplicate of ivpkar (carried by plan vv4vdd)"); `.aw/records/plans/superseded/20261122-12rcu8-01-4h2qwz-*.ipd.md` and `...ig2etn...` ("Superseded by vv4vdd (ivpkar)"); `.aw/records/plans/pending/20261122-pgcmea-01-whacr3-*.ipd.md` | F-07, OQ-02, and the `tests/test_tui.py` deferral said `4h2qwz` lived only on another branch, `12rcu8`, `sd7kvt`, and `pgcmea` were open, and closing `pgcmea` was a maintainer act. All of that has since been reconciled on this tree. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote F-07 and OQ-02 to the current records and changed the `pgcmea` deferral to `Carrier: whacr3`. E-01 keeps its check-before-edit guard (recommendation strength: strong). |
| PR-002 | medium | IN-SCOPE | Q (falsifiable test) | `is_same_process` falls back to start-time comparison when the script check returns `None` (default `tolerance=86400.0`); review probe: generic `-c` child with `time.time()` returned `True`, with `time.time() - 172800` returned `False` | The planned assertion `is_same_process(child.pid, time.time(), ...) is True` would also pass when the command-line check is inconclusive, so it did not prove that the script match returns `True`, which is the test's stated purpose. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-01, P-01 step 4, and V-01 now use `time.time() - 172800` (the offset `test_wrong_start_time_does_not_match` already uses), so only a confirmed script match can make the assertion pass. Prototype passes serially and under `-n 2` (recommendation strength: strong). |
| PR-003 | low | UNDER-SCOPE | R2 gate (execution contract) | `steps/r2-executability.md` "An execution contract in the gate: ... scope fence ... lifecycle transition (unconditional finalize obligation with conditional runner/executor ownership ...)" | The gate lacked the `--scope-reason`/`--scope-ack` fence and the runner-versus-executor `aw ipd finalize` ownership, and framed the move to `executed/` as a manual lifecycle act. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the gate paragraph with a five-part execution contract: precondition, scope fence, validation honesty, `aw commit vv4vdd -- tests/test_liveness.py` with never-push, and `aw ipd finalize vv4vdd` owned by the runner in a lane or by the executor outside one (recommendation strength: strong). |
| PR-004 | low | IN-SCOPE | Check P (writing, `IPD-C802`); V-03 reachability | `aw ipd lint --phase author` reported 2 `IPD-C802` info diagnostics; V-03 demanded observed runs without naming the path or the CI gate | Two em dashes in the validation boilerplate; V-03 did not name its reachability path or record that the CI matrix remains the gate. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the dashes; V-03 now names the path (the E-01 test calls `is_same_process`, which calls `_check_command_linux` on Linux) and requires one line recording that the `.github/workflows/ci.yml` matrix remains the gate after the maintainer pushes (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Which expected start time should the rewritten test pass? | `time.time() - 172800` | `time.time()` (as authored); the child's real start time from `get_process_start_time` | Only an out-of-tolerance start isolates the script-match branch; the offset matches the existing `test_wrong_start_time_does_not_match`; prototype passes under xdist | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined existing items, findings, an open-question rationale, a deferral carrier, and the gate. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
