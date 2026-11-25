# Review findings: ipd 1kcrdn

- Subject-Id: 1kcrdn
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-rand-mypy-01-1kcrdn-enable-pytest-randomly-in-the-ci-test-matrix.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `dd770d3` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(b), (d), and (e) are satisfied by the Mermaid flowchart for the randomized CI failure-and-reproduction loop.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| E-01 (`extra-suites` bullet) | Said "append ` -p randomly` to the existing command" without quoting the command | Shows the exact before and after `pytest` command for `extra-suites` matching `.github/workflows/ci.yml` | Requirement 5 (explicit meaning) and parity with the other three E-01 bullets (PR-006). |
| E-02 Expected outcome, Required tests / validation, and V-04 (1) | Used `-q` for the negative local check and the four local random-order runs, and asked V-04 (1) for "the last two lines ... each with its seed header" | Uses `-v` for the E-02 negative check and default verbosity (no `-q`) for the four local runs, and asks V-04 (1) for the `Using --randomly-seed=` session header line, final summary line, and `exit=0` | Empirical check proved `-q` suppresses `Using --randomly-seed=` entirely and the seed header prints at the top, not in the last two lines (PR-001). |
| E-03 (`CHANGELOG.md` instruction) | Described the `CHANGELOG.md` entry without requiring `--randomly-seed`, while Expected outcome and V-03 grepped `randomly-seed` in both files | Instructs mentioning `pytest-randomly` and `-p randomly --randomly-seed=<N>` in the `CHANGELOG.md` entry | Resolves E-03/V-03 contradiction so `grep -n "randomly-seed" CONTRIBUTING.md CHANGELOG.md` matches both files (PR-003). |
| E-04, Project conventions, Required tests / validation, V-04 (2)-(3), Gate item 3 | Said "push the branch", claimed every CI job emits `Using --randomly-seed=`, referred to "any `typecheck` job", and sampled only Windows and macOS logs | Specifies pushing to `main` or opening a pull request targeting `main` (matching `ci.yml` triggers), distinguishes all 25 CI jobs from the 23 `pytest` jobs, names `typecheck` directly, covers all four edited CI commands in V-04 (3), and documents the `blocked` state when no push/PR is authorized | Aligns E-04/V-04 with `.github/workflows/ci.yml` and unattended runner constraints (PR-002). |
| V-02 and V-03 | Used `grep -c` (exits 1 on 0 matches and ignores pytest exit status) in V-02, non-portable `grep -nP` without a diff pipe in V-03, and omitted `exit=1` on the `TODO.md` no-match grep | Replaces V-02 and V-03 dash checks with portable, non-vacuous exit-0 `python3 -c` checks and notes `exit=1` for the `TODO.md` grep | Requirement 6 (verifiable evidence) and Check R2 validation robustness (PR-004). |
| Project conventions, E-03, OQ-01, Gate item 5 | Cited `tests/test_conftest_isolation.py` and `AGENTS.md` without `::`/`#` anchors, set `OQ-01` `- Owner: none`, and opened Gate item 5 with an unconditional `aw ipd finalize` instruction | Applies Section 11.1 citation anchors, sets `OQ-01` `- Owner: plan author`, and states conditional runner/executor finalization ownership in Gate item 5 | Section 11.1 citations, Check S5 owner convention, and Check S7 execution-contract rule (PR-005, PR-006). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`.github/workflows/ci.yml`, `pyproject.toml`, `CONTRIBUTING.md`, `CHANGELOG.md`, `TODO.md`), 4 E-items in 2 task groups, `- Kind: child`.

1. Yes (bounded): `.github/workflows/ci.yml` is the repository's CI quality-gate contract relied on by every pull request and push to `main`, and sibling plans in the `rand-mypy` Set also edit `.github/workflows/ci.yml`, `pyproject.toml`, `CONTRIBUTING.md`, and `CHANGELOG.md`.
2. No: touches no code guarding private data, commits, worktree isolation, merges to `main`, or the sandbox.
3. No: 4 focused E-items across 2 task groups in 5 small configuration and documentation files.
4. Yes: `.github/workflows/ci.yml`, `pyproject.toml`, `CONTRIBUTING.md`, `CHANGELOG.md`, `TODO.md`.
5. Yes (bounded): enabling `-p randomly` across unmeasured OS/Python matrix cells (Windows, macOS, Python 3.8-3.13, `no-tui`) could turn CI red on a latent order-dependent test until fixed or reverted, though it cannot lose data and is trivial to undo.

AW-TIER: standard

### Step R1

- Checked: `.github/workflows/ci.yml` (lines 1-153, exact `on:` triggers and all four `pytest` `run:` lines 38, 41, 54, 67, plus `packaging` lines 69-138 and `typecheck` lines 140-153); `pyproject.toml` (lines 52-60 `dev` extra `pytest-randomly>=3.0`, lines 80-90 `[tool.pytest.ini_options]` comment and `addopts = "-p no:randomly"`); `CONTRIBUTING.md` (lines 5-38 `## Development setup`); `CHANGELOG.md` (lines 9-100 `## [Unreleased]` / `### Changed`); `TODO.md` (lines 41-46 `### Enable pytest-randomly in CI`); `tox.ini` (lines 1-8); `tests/test_conftest_isolation.py` (lines 10-55); `.aw/records/plans/executed/20261123-test-audit-03-m66tfv-test-isolation-global-state-leaks-flaky-sleeps-and-code-pinn.ipd.md` (lines 86, 103-104, 292); `.aw/records/plans/executed/20261123-test-audit-02-gzc672-mypy-type-check-repair-and-ci-type-gate.ipd.md`; `.aw/records/backlog/graduated/20261123-test-audit-01-qqwebg-ci-randomly-and-legacy-mypy-debt.backlog.md`; `.aw/records/plans/pending/20261124-rand-mypy-00-srs7bs-randomized-ci-test-order-and-legacy-mypy-burn-down.ipd.md`; `AGENTS.md#Matrix-validation discipline`; `scripts/sanitize_paths.py`; `tests/test_config.py`; `git cat-file -t a4b7d12`; `grep -rln "randomly" .aw/records/specs docs`; and `grep -rn "pytest" .github/ README.md docs/`.
- Confirmed: exact four `pytest` commands in `.github/workflows/ci.yml`, `pytest-randomly>=3.0` and `addopts = "-p no:randomly"` in `pyproject.toml`, `pytester.makeini("[pytest]\naddopts = -p no:randomly\n")` in `tests/test_conftest_isolation.py:13`, `m66tfv` executed evidence (`1941 passed, 2 skipped` and T-19 carrier `qqwebg`), `pyyaml` and `pytest_randomly.pytest_report_header` available locally, `-p randomly` works cleanly alongside `--cov`, and zero references to `pytest-randomly` under `.aw/records/specs/` or `docs/`.
- PR-002 (reference mismatch): `.github/workflows/ci.yml:3-7` triggers only on `push` to `main` or `pull_request` targeting `main`, and `.github/workflows/ci.yml:69-153` defines `packaging` and `typecheck` jobs that do not run `pytest` (contrary to E-04 saying "push the branch" and "every job ... with a `Using --randomly-seed=` header", and V-04 saying "any `typecheck` job"). Fixed.
- PR-006: added exact before/after `extra-suites` command in E-01 and applied Section 11.1 citation anchors (`::` and `#`). Fixed.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-04` to `V-01`..`V-04`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:m66tfv`, runtime-demonstration reachability of V-02 (pytest reading `pyproject.toml` `addopts` with/without `-p randomly`) and V-04 (`.github/workflows/ci.yml` commands edited by E-01), empirical verification of `-q` vs default/`-v` output, E-03/V-03 consistency, portability and exit codes of V-02/V-03 commands, and all five execution-contract elements in the gate.
- PR-001: empirical run of `python3 -m pytest tests/test_config.py -p randomly --randomly-seed=1 -q -p no:cacheprovider` printed only dots and `35 passed in 1.83s` (no `Using --randomly-seed=` line), whereas default verbosity printed `Using --randomly-seed=1` at line 3 of the session header. Fixed E-02 Expected outcome, Required tests / validation, and V-04 (1) so negative checks use `-v`, local random runs drop `-q`, and V-04 (1) pastes the seed header line plus final summary line and `exit=0`.
- PR-002: fixed CI trigger wording (push to `main` or PR targeting `main`), distinguished all 25 CI jobs from the 23 `pytest` jobs, required CI seed-log evidence covering all four edited CI commands, and documented marking E-04/V-04 `blocked` if no push/PR is authorized yet.
- PR-003: updated E-03's `CHANGELOG.md` instruction to name `pytest-randomly` and `-p randomly --randomly-seed=<N>` so V-03's `grep -n "randomly-seed" CONTRIBUTING.md CHANGELOG.md` matches both files.
- PR-004: replaced `V-02`'s exit-1 `grep -c` check and `V-03`'s GNU-only `grep -nP` check with portable, non-vacuous exit-0 `python3 -c` checks, and noted `exit=1` for `TODO.md` no-match grep.
- PR-005: updated Gate item 5 to state conditional runner/executor ownership for `aw ipd finalize 1kcrdn`, and updated `OQ-01` `- Owner:` from `none` to `plan author`.

### Step R3

- Checked: all five bullets of Check R3 full form. No authentication, authorization, or secret-handling surfaces are touched. `.github/workflows/ci.yml` adds only a static CLI flag `-p randomly` to four existing `pytest` commands (no new external dependencies, no workflow permissions changes, no untrusted input interpolation). `Using --randomly-seed=<N>` logs only an integer RNG seed (no sensitive data). E-04 explicitly preserves the `AGENTS.md` never-push-without-human-instruction boundary, and V-03 runs `python3 scripts/sanitize_paths.py --check --all` to prevent machine-local path leaks. No finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (4 single-concern E-items across 2 task groups; each is executable in one focused pass; no splitting warranted); anti-regression (`addopts = "-p no:randomly"` preserves deterministic local and `tox` runs; `tests/test_conftest_isolation.py` inner `pytester` session keeps fixed order via its own `makeini`); spec and documentation sync (no `.spec.md` or `docs/` file mentions `pytest-randomly`, verified with `grep`; `CONTRIBUTING.md`, `CHANGELOG.md`, and `TODO.md` are updated by E-03). No additional findings beyond PR-001..PR-006.

### Step S5

- Checked: pre-existing open question `OQ-01` (`- Blocking: no`, `- Status: resolved`, updated `- Owner: plan author`) is backed by verified evidence (`pytest_randomly.pytest_report_header` prints `Using --randomly-seed=N` per job, and 21 independent orders catch more cross-test state leaks than one shared order). Every review finding PR-001..PR-006 had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R2 (unsatisfiable and vacuous `-q` validation) | Plan `E-02` (line 64), `Required tests / validation` (lines 130-132), `V-04` (line 170); measured via `python3 -m pytest tests/test_config.py -p randomly --randomly-seed=1 -q -p no:cacheprovider` | `-q` suppresses `Using --randomly-seed=` completely, making E-02's `-q` negative check vacuous and making V-04 (1)'s demand for "the last two lines ... each with its seed header" impossible (the header also prints at the top of the session, not in the last two lines). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Changed E-02 Expected outcome and Required tests negative check to `-v`, dropped `-q` from the four local random runs so default verbosity prints the seed header, and updated V-04 (1) to paste the `Using --randomly-seed=` header line, final summary line, and `exit=0`. |
| PR-002 | HIGH | IN-SCOPE | R2 (CI workflow trigger and job-set mismatch) | `.github/workflows/ci.yml:3-7` (`push`/`pull_request` branches `[main]`), `.github/workflows/ci.yml:69-153` (`packaging`, `typecheck`); Plan `E-04` (lines 74-76), `V-04` (line 170), Gate item 3 (line 182) | E-04 asked to "push the branch", which does not trigger `ci.yml` unless pushed to `main` or opened as a PR targeting `main`; E-04 Expected outcome claimed every CI job prints `Using --randomly-seed=` (`packaging` and `typecheck` do not run `pytest`); V-04 (2) said "any `typecheck` job" (already live) and V-04 (3) left `ubuntu-latest` 3.12 coverage-gate, `no-tui`, and `extra-suites` unverified in CI logs; E-04/Gate omitted the `blocked` state when no push/PR is authorized. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified pushing to `main` or opening a PR targeting `main`, distinguished all 25 CI jobs from the 23 `pytest` jobs, named `typecheck` directly, required CI seed-log lines covering all four edited CI commands, and documented marking E-04/V-04 `blocked` when no push/PR is authorized yet. |
| PR-003 | MEDIUM | IN-SCOPE | R2 (E-03 vs V-03 `CHANGELOG.md` mismatch) | Plan `E-03` (lines 67-69), `V-03` (line 165) | E-03's `CHANGELOG.md` instruction did not require including `--randomly-seed`, contradicting E-03 Expected outcome and V-03's demand that `grep -n "randomly-seed" CONTRIBUTING.md CHANGELOG.md` match both files. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated E-03 to instruct mentioning `pytest-randomly` and `-p randomly --randomly-seed=<N>` in `CHANGELOG.md` so the grep matches both files. |
| PR-004 | MEDIUM | IN-SCOPE | R2 (exit-1, non-portable, and vacuous validation commands) | Plan `V-02` (line 160), `V-03` (line 165) | V-02's `grep -c` exits 1 on 0 matches and ignores pytest exit status; V-03's `grep -nP` is GNU-only, lacked a diff pipe, exits 1 on 0 matches, and is vacuous on an empty diff; V-03's `TODO.md` grep did not note expected `exit=1`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced V-02 and V-03 dash checks with portable, non-vacuous exit-0 `python3 -c` checks and documented `exit=1` for the `TODO.md` no-match grep. |
| PR-005 | LOW | IN-SCOPE | S7 / S5 (gate finalize ownership and `OQ-01` owner) | Plan `OQ-01` (line 147), Gate item 5 (line 184); `steps/s5-questions.md:21`, `steps/s7-finalize.md:33-36` | Gate item 5 opened with an unconditional `aw ipd finalize 1kcrdn` instruction without stating runner ownership inside `aw oc run` / `aw agy run`; `OQ-01` carried `- Owner: none` despite being resolved by the plan author. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Gate item 5 to state conditional runner/executor finalization ownership explicitly and changed `OQ-01` `- Owner:` to `plan author`. |
| PR-006 | LOW | IN-SCOPE | Check P / Section 11.1 (exact `extra-suites` target and citation anchors) | Plan `E-01` (line 56), `Project conventions` (lines 84, 87); `.github/workflows/ci.yml:54`, `tests/test_conftest_isolation.py:10` | E-01 omitted the exact before/after command for `extra-suites`, and citations to `tests/test_conftest_isolation.py`, `CONTRIBUTING.md`, and `AGENTS.md` did not use Section 11.1 `::` / `#` anchor syntax. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the exact before/after `extra-suites` command in E-01 and updated citations to Section 11.1 forms. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Changes the CI test-gate contract in `.github/workflows/ci.yml` across 23 `pytest` jobs (including unmeasured OS/Python cells) with 4 small, focused E-items across 5 files. | yes |
| D-2 | Keep `OQ-01` (per-job random seed vs shared seed) resolved with `- Owner: plan author` | Keep resolved (`each job draws its own seed`) | Reopen `OQ-01` as `Blocking: yes` | Verified `pytest_randomly.pytest_report_header` prints `Using --randomly-seed=N` per job; 21 distinct orders per push catch more order-dependent tests than one shared order without losing reproducibility. | yes |
| D-3 | Retain E-04 / V-04 full CI matrix gate (marking `blocked` if no push/PR is authorized yet) | Keep E-04 / V-04 gated on CI matrix run | Defer CI matrix run to `Deferred / out of scope` | `AGENTS.md#Matrix-validation discipline` mandates full OS x Python CI matrix validation before moving cross-platform work to `executed/`, while `AGENTS.md` agent execution contract forbids pushing without human instruction. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All six findings (PR-001..PR-006) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
