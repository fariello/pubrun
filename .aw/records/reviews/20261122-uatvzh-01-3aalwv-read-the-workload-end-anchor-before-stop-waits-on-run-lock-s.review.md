# Review findings: ipd 3aalwv

- Subject-Id: 3aalwv
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-uatvzh-01-3aalwv-read-the-workload-end-anchor-before-stop-waits-on-run-lock-s.ipd.md` (front matter, terms, Mermaid flowchart, E-01 to E-05, conventions, reproduction script and tables, deferrals, OQ-01, OQ-02, V-01 to V-05, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Terms are defined before use, and the flowchart matches the lock order in `Run.stop` and the nested `_collect_hardware`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning (PR-004). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (five files, no `.spec.md`), E-item and task-group counts (5 items, 5 groups).

1. No: no spec, CLI option, configuration key, or manifest field changes; `docs/architecture.md` and `docs/functional_spec.md` are prose descriptions that E-03 brings back in line with the code.
2. No: touches no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 5 E-items across five files, one code file with four small edits.
4. Yes: `- Scope-Paths:` lists all five files.
5. Yes: `Run.stop` and `Run._finalize_state` run at the end of every run, and the change alters lock-adjacent timing code shared with the `pubrun-hw` thread and the `atexit`/signal path.

AW-TIER: standard

### Step R1 (references)

- Checked: `src/pubrun/tracker.py` line 13 `from typing import Any, Dict, Optional`; lines 126 to 129 `ended_at_utc`, `_workload_end_mono`, `_finalize_end_mono`; `Run._finalize_state` (line 1097) sets `_finalized`, `_workload_end_mono = time.perf_counter()`, `ended_at_utc = time.time()` under `with _run_lock:` (lines 1104 to 1115), with the comment at line 1104 that E-01 updates; `Run.stop` (line 1374) takes `_run_lock`, decrements `ref_count`, returns early for nested stops, then calls `self._finalize_state()` at line 1399; nested `_collect_hardware` calls `writer.write_startup_manifest(is_refresh=True)` at line 674 under `_run_lock`. `ArtifactWriter.write_artifacts` (writer.py line 272) calls `self.run._finalize_state()` before `_write_lock`. `pubrun.core.start` increments `ref_count` on an active run (lines 130 to 137), which is the nested-stop case E-01 handles. `Run._build_timing_dict` clamps each interval with `max(0.0, ...)`. `docs/architecture.md` line 45 and `docs/functional_spec.md` line 797 are the only two docs lines that place `t2` under `_run_lock`. `tests/conftest.py` has autouse `isolated_cwd` and `clean_active_run`, so the new test's run directory lands in `tmp_path`. `CHANGELOG.md` has `## [Unreleased]` at line 9 and its `### Fixed` at line 105. Commit `276236b` exists and is an ancestor of the lane HEAD; among the files involved only `src/pubrun/writer.py` changed since (Windows `os.replace` retry), which does not affect this path.
- Plan `updt75` (Set `tmngjn`, reviewed earlier in this lane) edits the `from pubrun import _run_lock` lines in `Run.stop` and `Run._finalize_state`, which sit directly above where E-01 inserts its reads. The plans do not depend on each other's behavior, but a parallel run can produce an adjacent-line merge conflict. The plan did not say how to resolve it (PR-001).

### Step R2 (executability)

- Applied E-01 exactly as written to a scratch copy of `src/` and appended the E-02 helpers and test as specified (refresh stall of 0.40 s, workload 0.02 s, 0.2 s "still blocked" check, `finally` cleanup). Fixed copy: `tests/test_timing_accuracy.py` gave `17 passed in 1.48s`; `-k stalled` passed in five repeated runs. Base `src/`: both new cases FAILED with `assert 0.4199999999999591 == 0.02 ± 1.0e-09`, matching the plan.
- Neighboring suites from E-05: `214 passed, 2 skipped in 32.99s` with the fix and `2 failed, 212 passed, 2 skipped in 33.73s` on the base `src/`, matching the plan. (A first attempt printed 19 failures because my scratch copy lacked `schemas/`; that was a copy defect, not the fix.)
- Reproduction script, run directory on the repository disk: base `workload excess ms: median=27.82 max=134.58`, fixed `median=0.14 max=0.15`; finalization overhead rose from a 5.56 ms median to 22.07 ms with the fix, as the plan predicts.
- `examples/05_execution_phases.py` takes no output directory and writes to `runs/` under the current directory. From `/tmp/opencode` the base printed about 20.6 ms in all four runs, so the V-05 "below 40 ms" check would also pass on the unfixed code. From the repository root (gitignored `runs/` on the repository disk) the base printed 157.8, 25.9, 56.3, 74.1, 56.5, 39.7, 54.8, 134.6 ms and the fix printed 20.7 to 21.0 ms. The plan named neither the working directory nor `PYTHONPATH=src`, and did not say to delete the run directories it creates (PR-002). I deleted the 16 run directories my probes created under `runs/` (count back to 90).
- V-02 asked for a base-commit worktree run without commands or a removal check (PR-003). `pyproject.toml` sets `pythonpath = ["src"]`, so in a pre-fix worktree the test imports that worktree's unfixed `src/`; the method works and is now spelled out.
- Python 3.12 and 3.11 on this host have no `pytest`, so the cross-version check was not run; the CI-matrix deferral already covers it.
- Gate: has precondition, scope fence with `--scope-reason`/`--scope-ack`, honesty, `aw commit 3aalwv -- ...` with never-push, and runner-versus-executor `aw ipd finalize`. It lacked the pre-transition lint step and the OQ status (PR-004).
- Scratch files under `/tmp/opencode/3aalwv` were deleted.

### Step R3 (security, full form)

- Checked: the change moves two clock reads ahead of a lock acquisition and adds one private attribute written under `_run_lock`. The lock order (`_run_lock` before `_write_lock`), the `_finalized` latch, the hardware write window, and the set of files written are unchanged. No new data is captured or exposed. The test writes only under `tmp_path` and joins every thread it starts in a `finally` block. No security findings.

### Step R4 (engineering)

- Checked: `_stop_anchor` is set only by the outermost `stop()` and only once, so a nested `stop()` or a repeated `stop()` cannot move `t2`; `_finalize_state()` falls back to its own pre-lock reading on the `atexit` and signal paths. A pre-lock read can precede `t1` only if `stop()` races `start()` on another thread, and `_build_timing_dict` clamps that to `0.0`; this is no worse than today. OQ-01 (move `t2` rather than the refresh write) is a sound choice: the alternative needs a new overwrite guard in `ArtifactWriter`. OQ-02 (the `stop()` reading wins) matches the `ended_at_utc` definition in `docs/manifest.md`.
- Tests: drive real `Run` objects with the existing fake clock, block on events rather than sleeps (except the 0.2 s "still blocked" probe, which only fails toward a false failure if the machine stalls), and assert on manifest values. No source inspection.
- CI matrix deferral: consistent with sibling plans and `AGENTS.md`.

### Step S5

- Checked: OQ-01 and OQ-02 (both resolved, non-blocking, with evidence). The three deferrals carry `Carrier-Declined` with reasons. All findings have Low remediation risk and are fixed. No question needs the human; no finding is OPEN or DEFERRED.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | low | UNDER-SCOPE | R1 (cross-plan overlap) | E-01 "this plan does not depend on which form is present"; plan `updt75` E-01 edits the import lines in `Run.stop` and `Run._finalize_state` | E-01 inserts lines directly below import lines that `updt75` rewrites, so a parallel run can conflict at merge, and the plan gave no resolution rule. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-01 now says to insert the reads between the import line and `with _run_lock:` whatever the import form, and on conflict to keep `updt75`'s import and this plan's reads; Findings records the overlap (recommendation strength: medium). |
| PR-002 | low | IN-SCOPE | R2 (validation discriminates) | Review run: example from `/tmp/opencode` printed about 20.6 ms on the base; from the repository root 25.9 to 157.8 ms on the base, 20.7 to 21.0 ms fixed | V-05's "eight runs below 40 ms" check passes on the unfixed code unless the example runs from the repository root, which the plan did not require; it also left the run directories behind. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-05, Required tests, and V-05 now require `PYTHONPATH=src python3 examples/05_execution_phases.py` from the repository root and deleting the run directories it created (recommendation strength: strong). |
| PR-003 | low | IN-SCOPE | R2 (evidence concreteness) | Required tests "create a temporary `git worktree` of the base commit" | The pre-fix run gave no commands and no removal check. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Named `git worktree add /tmp/opencode/3aalwv-prefix HEAD`, the removal command, and pasted `git worktree list`; V-02 names the expected `0.42 == 0.02` failure (recommendation strength: medium). |
| PR-004 | low | IN-SCOPE | Check P (`IPD-C802`); R2 gate; R1 (evidence) | `aw ipd lint --phase author` reported 2 `IPD-C802` info diagnostics; gate item 5 | Two em dashes in the validation boilerplate; the gate lacked `aw ipd lint --phase pre-transition` and the OQ status; Findings had no review re-check. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the dashes, added the pre-transition lint step and OQ status, and added a re-check paragraph with the review's measurements (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should V-05 make the example check fail on the unfixed code? | Run the example from the repository root so `runs/` is on the slow disk | Drop the example check; add an `output_dir` argument to the example | Review measurements show the root-directory run discriminates; no new scope path needed | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined E-01, E-05, Findings, Required tests, V-02, V-05, the boilerplate, and the gate. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
