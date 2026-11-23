# Review findings: ipd t336id

- Subject-Id: t336id
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-cp1jvn-01-t336id-keep-the-minimal-research-workflow-example-from-leaving-outp.ipd.md` (front matter, Mermaid flowchart, E-01 to E-04, V-01 to V-04, conventions, findings, deferrals, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal flowchart, node `DEF` | "directory of analysis.py / 'outputs'" | "DEFAULT_OUTPUT_DIR (outputs/ next to analysis.py)" | Requirement 12(e): the diagram must use the same term as E-01 (`DEFAULT_OUTPUT_DIR`). |
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning. |
| E-04 title and expected outcome, V-04 | "under `## [Unreleased]` / `### Fixed`" | "the first `### Fixed` heading under `## [Unreleased]`", plus bullet-format note | Requirement 5: `CHANGELOG.md` `## [Unreleased]` has several `### Fixed` headings (lines 105, 172, 199, 244, 518), so the target was ambiguous. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (4 files), E-item and task-group counts (4 items, 3 groups).

1. Yes: adds a public CLI option `--output-dir` to the example script and changes its default output location; no spec, schema, or package interface changes.
2. No: touches no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 4 E-items in 3 small task groups, all within one example and its test, README, and changelog.
4. Yes: `- Scope-Paths:` lists all four files.
5. No: an example script only; the default location is git-ignored and the change is trivially revertible.

AW-TIER: standard

### Step R1

- Checked: `examples/minimal-research-workflow/analysis.py::write_outputs` (`Path("outputs")` at line 165, `mkdir(exist_ok=True)`), `analysis.py::main` (`"Outputs written to ./outputs/"` at line 231), `analysis.py::parse_args`, `examples/verify_all.py::main` (`subprocess.run([sys.executable, script], capture_output=True, text=True)` at line 50, no `cwd`), `.gitignore` lines 10 (`runs/`) and 66 (`examples/minimal-research-workflow/outputs/`), `tests/test_example_minimal_research_workflow.py::test_minimal_research_workflow_runs` (line 45 assertion), `examples/minimal-research-workflow/README.md#Run the example` and the outputs paragraph (lines 50 to 54), `docs/research-use.md#Public example workflow` (no output location named), `.github/workflows/ci.yml` (3 OS by Python 3.8 to 3.14, `pip install -e ".[dev,tui]"`, `pytest tests/ -v`), `pyproject.toml` `addopts` (coverage flags, justifies `-o addopts=""`), commit `f632558` (resolves), backlog items `cp1jvn` (graduated), `wghq9s` and `g2434y` (both `done` on 2026-11-23 as duplicates of `cp1jvn` carried by `t336id`). Reproduced the `g2434y` symptom: `python3 verify_all.py --no-clear` run from a scratch copy of `examples/` exited 0 and left `examples/outputs/`.
- All code and doc citations resolve. One stale claim: the deferral rows said `wghq9s` and `g2434y` were open for the maintainer to resolve, but both are already `done` (PR-001).

### Step R2

- Checked: E/V bijection (E-01..E-04 to V-01..V-04), Scope-Paths completeness, `Item-Dependencies: none` (correct; no prerequisite plan), concreteness of each V-item, runtime-demonstration reachability, and the execution contract.
- V-01 reachability: the observed run is produced by `examples/verify_all.py::main` invoking `analysis.py::main` (named in V-01); reachable.
- V-01 covered only the repository-root working directory, while E-01's goal and backlog `g2434y` also name the `examples/` working directory (PR-002).
- V-02 used test function names as its bar, which the test-organization convention forbids (PR-003).
- Gate: execution contract carries resolved questions, a non-STOP scope fence with `--scope-reason`/`--scope-ack`, the honesty rule, path-scoped `aw commit` with never-push, and conditional runner/executor `aw ipd finalize` ownership. Conforming.

### Step R3

- Checked: `--output-dir` is a caller-supplied local path for a local example; the script writes only two fixed filenames into it under the caller's own permissions. No trust boundary, secrets, network, or private data. No findings.

### Step R4

- Checked: rubric A (single-process writes, `mkdir(parents=True, exist_ok=True)` idempotent), C (reuses `pathlib`, no new dependency), D (invariant: documented `cd examples/minimal-research-workflow` workflow keeps its output location; invariant: the example still writes inspectable outputs, README item 4), E (three subprocess behavior tests, CI matrix portability via `sys.executable` and `pathlib`), F (KISS: one constant and one option), right-sizing (each E-item one file, one concern), and spec/doc sync (`docs/research-use.md` checked; no spec governs the example).
- E-02 test (2) did not say to create the separate caller directory before using it as `cwd`, which `subprocess.run` requires (PR-004).
- E-03 did not say how a relative `--output-dir` is resolved; a user could reasonably expect it to be relative to the script, like the default (PR-005).

### Step S5

- Checked: `OQ-01` (resolved, non-blocking, owner `plan author`, basis cited), deferral carriers, and all findings. All findings have Low remediation risk and are fixed. No question needs the human. No finding is OPEN or DEFERRED, so none needs escalation.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | medium | IN-SCOPE | R1 (stale evidence) / S5 (carriers) | `.aw/records/backlog/done/20261122-wghq9s-01-wghq9s-examples-verify-all-py-runs-minimal-research-workf.backlog.md` "Duplicate of cp1jvn (carried by root-cause plan t336id)"; same line in `.aw/records/backlog/done/20261122-g2434y-01-g2434y-verify-all-leaves-examples-outputs.backlog.md` | The deferral rows said `wghq9s` and `g2434y` stay open for the maintainer to resolve and named them as `- Carrier:`. Both were already closed `done` as duplicates that name this plan as their carrier, so the carrier pointed in a circle. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote both rows to state the closure and replaced `- Carrier:` with `- Carrier-Declined:` pointing at the V-01 parts that check each symptom (recommendation strength: strong). |
| PR-002 | medium | UNDER-SCOPE | R2 (validation coverage) | `examples/verify_all.py::main` line 50 (no `cwd`); backlog `g2434y` (symptom with `examples/` as cwd); reproduction in Step R1 | V-01 checked only the repository-root working directory. The `examples/` working directory named by `g2434y`, which this plan now discharges, was not verified. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added V-01 part (e) and a matching Required-tests bullet: run `(cd examples && python3 verify_all.py --no-clear)` and show `examples/outputs` absent and no untracked `outputs/` path (recommendation strength: strong). |
| PR-003 | low | IN-SCOPE | R2 (evidence bar uses test names) | `steps/r2-executability.md` "a test function name is permitted only as a non-binding pointer"; plan V-02 | V-02's bar was three named tests `PASSED`, an artifact of test organization. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | V-02 now demands zero failures plus the re-derived test lines pinning each of the three behaviors via subprocess runs; E-02 names stay as pointers (recommendation strength: strong). |
| PR-004 | low | IN-SCOPE | R4.E (test executability) | Plan E-02 test (2); `subprocess.run(cwd=...)` raises when the directory is missing | Test (2) runs with `cwd=<tmp_path>/caller` without saying to create that directory. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-02 now says to create `<tmp_path>/caller/` and to assert exit code 0 (recommendation strength: medium). |
| PR-005 | low | UNDER-SCOPE | R4.F (UX, honest docs) | Plan E-01 (`output_dir = Path(--output-dir)`); `examples/minimal-research-workflow/README.md` lines 50 to 54 | The default is anchored to the script, but a relative `--output-dir` resolves against the working directory. The README edit did not state this, so a reader could guess wrong. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-03 now requires the README to say a relative `--output-dir` is resolved against the current working directory (recommendation strength: medium). |
| PR-006 | low | IN-SCOPE | Check P (writing, diagram parity, `IPD-C802`) | `CHANGELOG.md` `### Fixed` at lines 105, 172, 199, 244, 518 under `## [Unreleased]`; plan flowchart node `DEF`; plan validation boilerplate | E-04 and V-04 named an ambiguous `### Fixed` target; the flowchart used a different term from E-01's `DEFAULT_OUTPUT_DIR`; two em dashes raised `IPD-C802` advisories. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Named the first `### Fixed` heading, aligned the node label, and replaced the em dashes (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should a relative `--output-dir` be resolved? | Against the current working directory (standard CLI behavior, as E-01 already specifies with `Path(--output-dir)`), documented in the README | Resolve relative to the script directory like the default | Plan E-01 expected outcome; ordinary `argparse`/`pathlib` CLI convention; E-02 tests pass absolute `tmp_path` paths so either works | yes |
| D-2 | Which carrier do the closed duplicates `wghq9s` and `g2434y` take? | `- Carrier-Declined:` citing the closure and the V-01 part that checks each symptom | Keep `- Carrier: <id6>` (circular, since both name `t336id`); reopen the items | Backlog workflow-history lines "Duplicate of cp1jvn (carried by root-cause plan t336id)" | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined existing items. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
