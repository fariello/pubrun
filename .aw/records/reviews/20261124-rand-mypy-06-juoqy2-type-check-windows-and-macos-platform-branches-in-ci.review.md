# Review findings: ipd juoqy2

- Subject-Id: juoqy2
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-rand-mypy-06-juoqy2-type-check-windows-and-macos-platform-branches-in-ci.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `8976f53` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(b), (d), and (e) are satisfied by the Mermaid platform-guards and CI-runs flowchart.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| E-01 and Rejected alternatives | Claimed every `os.sysconf` call site already catches `AttributeError` or `Exception` | Distinguishes `resources.py` (catches `AttributeError` or `Exception`) from `liveness.py` (`_get_start_time_linux` and `_get_cpu_linux` are Linux-dispatched and catch `(OSError, IndexError, ValueError)` / `ZeroDivisionError`), noting `getattr(os, "sysconf")` preserves exact `AttributeError` behavior | Corrects false statement against `src/pubrun/capture/liveness.py:328,372` (PR-001). |
| E-04, Scope check, Required tests / validation, V-03 (3), V-04, Gate item 3 | Omitted `sanitize_paths.py` and combined pytest from V-04, left `V-04 (5)` push trigger and `blocked` handling under-specified, hardcoded `58 source files` without re-derivation, lacked `--no-incremental`/`exit=1` on mypy checks, used GNU-only vacuous `grep -nP` for the dash check, and did not verify `continue-on-error` absence in `yaml.safe_load` | Adds combined pytest and `sanitize_paths.py --check --all` to V-04, aligns E-04/V-04/Gate item 3 on `.github/workflows/ci.yml` `main` push/PR trigger and `blocked` handling (plus cross-platform `test` matrix check per `AGENTS.md#Matrix-validation discipline`), re-derives `<N> source files`, adds `--no-incremental` and `exit=1`, replaces `grep -nP` with portable non-vacuous exit-0 `python3 -c`, and prints `continue-on-error` in `yaml.safe_load` | Aligns E-04/V-04 with `Required tests / validation`, `AGENTS.md`, and cross-platform portability (PR-002). |
| E-03, Required tests / validation, V-03 (2) | Omitted `raising=False` on `os.sysconf` deletion in `test_resource_watcher_clock_ticks_zero_without_os_sysconf`, omitted Python 3.8 syntax note, and omitted repeated `-p randomly` runs from Required tests and V-03 | Adds `raising=False`, notes Python 3.8-compatible syntax, and adds a 3-run fail-closed `-p randomly` loop to Required tests and V-03 (2) | Prevents Windows CI failure where `os.sysconf` does not exist and satisfies orchestrator `srs7bs` Cross-IPD `-p randomly` requirement (PR-003). |
| E-04 and Project conventions | Described `gzc672` as `approved` and attributed the 7-vs-10 gap solely to `resources.py`; E-04 did not name `Run mypy` or instruct replacing `CONTRIBUTING.md`'s Linux-only phrasing | Reflects executed `gzc672` (which listed both `pubrun.capture.resources` and `pubrun.capture.subprocesses`, leaving 3 win32 errors at current HEAD until `k6fs5k` removes all six capture entries), names `Run mypy`, and instructs updating the Linux-only wording in `CONTRIBUTING.md#Development setup` | Matches current `pyproject.toml:115-141`, `.github/workflows/ci.yml:140-153`, and `CONTRIBUTING.md:33-38` (PR-004). |
| E-01..E-04, Project conventions, Findings, Gate item 5 | Opened Gate item 5 unconditionally with `aw ipd finalize juoqy2` and omitted Section 11.1 `path::Symbol` / `path#Heading` citation forms | Leads Gate item 5 with conditional runner/executor finalization ownership and applies Section 11.1 citation forms | Check S7 execution-contract rule and Section 11.1 citation rules (PR-005). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/capture/liveness.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/system_metrics.py`, `src/pubrun/capture/subprocesses.py`, `tests/test_platform_type_guards.py`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`, `CHANGELOG.md`), 4 E-items in 2 task groups, `- Kind: child`, `- Item-Dependencies: executed:gzc672, executed:m66tfv, executed:k6fs5k, executed:0uxy76`.

1. Yes (bounded): extends the blocking CI `typecheck` job in `.github/workflows/ci.yml` (shared CI quality-gate contract for every PR and push to `main`) and updates contributor docs (`CONTRIBUTING.md`, `CHANGELOG.md`).
2. No: touches only POSIX platform guards in capture modules, a unit test file, CI `typecheck` steps, and contributor docs; touches no code guarding private data, commits, worktree isolation, merges to `main`, or the sandbox.
3. No: 4 focused E-items across 2 task groups in 8 Scope-Paths, all scoped to cross-platform `mypy` checking.
4. Yes: `src/pubrun/capture/liveness.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/system_metrics.py`, `src/pubrun/capture/subprocesses.py`, `tests/test_platform_type_guards.py`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`, `CHANGELOG.md`.
5. Yes (bounded): a mistake in `liveness.py`, `resources.py`, `system_metrics.py`, or `subprocesses.py` could break process liveness, RSS/CPU capture, load-average reporting, or `os.system` wait-status decoding, and a bad CI step could break `typecheck`; all changes are small, mutation-tested, and trivial to revert.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/capture/liveness.py` (lines 7-15, 52-65, 283-375: `_PLATFORM`, `_get_start_time_linux`, `_get_cpu_linux` `os.sysconf` at lines 316 and 359, `except` clauses at lines 328 and 372); `src/pubrun/capture/resources.py` (lines 1-11, 90-100, 145-171, 266-319: `logger`, `os.sysconf` at lines 96, 162, 293, `except` clauses at lines 97, 168, 294); `src/pubrun/capture/system_metrics.py` (lines 14-20, 46-54: `sys` imported, `get_load_average` calling `os.getloadavg` at line 49); `src/pubrun/capture/subprocesses.py` (lines 1-12, 71-95: `sys` imported, `_decode_wait_status` `# Python 3.8 fallback.` at line 86 and `os.WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`/`WTERMSIG` at lines 88-91); `.github/workflows/ci.yml` (lines 1-153: `on:` triggers on `main`, `typecheck` job at lines 140-153 with `Run mypy`); `CONTRIBUTING.md` (lines 33-38 `## Development setup` `mypy` paragraph); `CHANGELOG.md` (lines 9-74 `## [Unreleased]` / `### Changed`); `pyproject.toml` (lines 106-141); `tests/test_liveness.py:308-348`; `tests/test_capture_engine_bugs.py:219-230`; `tests/test_env_capture.py:248-253`; existence of all 5 referenced test files and `scripts/sanitize_paths.py`; `grep -rln "randomly\|mypy" .aw/records/specs docs` (no match); full-package `mypy` diff between `--platform linux`, `--platform win32` (exactly 10 extra errors across the 4 named files), and `--platform darwin` (0 extra errors across all 58 source files).
- PR-001: `src/pubrun/capture/liveness.py:328` catches `(OSError, IndexError, ValueError)` and line 372 catches `(OSError, IndexError, ValueError, ZeroDivisionError)` — neither catches `AttributeError` or `Exception`, contradicting E-01's claim. Fixed in E-01 and Rejected alternatives.
- PR-004: `gzc672` is now `executed` and placed both `pubrun.capture.resources` and `pubrun.capture.subprocesses` on `pyproject.toml:127-128`'s `ignore_errors` list (so current HEAD shows 3 `--platform win32` errors until `k6fs5k` removes all six capture entries). Updated Project conventions and aligned E-04 with `Run mypy` and `CONTRIBUTING.md#Development setup`.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-04` to `V-01`..`V-04`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:gzc672, executed:m66tfv, executed:k6fs5k, executed:0uxy76`, runtime-demonstration reachability of V-03 (3) (two guard mutants against E-03 tests and `mypy --platform win32 --no-incremental`) and V-04 (6) (GitHub Actions run of `.github/workflows/ci.yml` edited by E-04), alignment with `Required tests / validation` and orchestrator `srs7bs`, and all five execution-contract elements in the gate.
- PR-002: added missing combined pytest and `scripts/sanitize_paths.py --check --all` checks to V-04; aligned E-04, V-04 (6), and Gate item 3 on `.github/workflows/ci.yml`'s `main` push/PR trigger, `blocked` handling when no push/PR is authorized, and cross-platform `test` matrix check; switched `58 source files` to `<N> source files` re-derived at execution time; added `--no-incremental` and `exit=1` to mypy checks; replaced `V-04 (4)`'s GNU-only vacuous `grep -nP` with portable non-vacuous exit-0 `python3 -c`; and added `continue-on-error` verification to the `yaml.safe_load` check.
- PR-003: added `raising=False` to `test_resource_watcher_clock_ticks_zero_without_os_sysconf` so it passes on Windows, noted Python 3.8 syntax compatibility, and added the 3-run fail-closed `-p randomly` check to Required tests and V-03 (2).
- PR-005: led Gate item 5 with conditional runner/executor finalization ownership and applied Section 11.1 citation forms.

### Step R3

- Checked: all five bullets of Check R3 full form. No authentication, authorization, secret handling, network calls, or untrusted input parsing are introduced. `.github/workflows/ci.yml` adds only two static `mypy --platform` invocations to the existing `ubuntu-latest` `typecheck` job with no new permissions or dependencies. `E-03` tests run strictly in-process with `monkeypatch`. `E-04` preserves the `AGENTS.md` never-push-without-human-instruction boundary and adds no `continue-on-error` or `# type: ignore`. `V-04` runs `python3 scripts/sanitize_paths.py --check --all`. No finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (4 focused E-items across 2 task groups in 8 Scope-Paths, each executable in one focused pass); Python 3.8 compatibility (`int(getattr(os, "sysconf")(name))`, `sys.platform == "win32"`, Python 3.8 test syntax); anti-regression (call-time `getattr(os, "sysconf")` preserves `monkeypatch.setattr(liveness.os, "sysconf", ...)` and exact `AttributeError` semantics; E-03 tests both helpers and both guards with mutation verification); spec and documentation sync (no `.spec.md` or `docs/` file mentions `mypy`; `CONTRIBUTING.md#Development setup` and `CHANGELOG.md` updated in E-04 with verified dash-free prose). No additional findings beyond PR-001..PR-005.

### Step S5

- Checked: `## Open questions` is `None.`. Every review finding (PR-001..PR-005) had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision remains, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | R1 / R4 (inaccurate `liveness.py` exception-handling claim) | `src/pubrun/capture/liveness.py:328,372`; Plan `E-01` (line 59), `Rejected alternatives` (line 121) | E-01 claimed every `os.sysconf` call site already sits in a `try` that catches `AttributeError` or `Exception`, whereas `liveness.py::_get_start_time_linux` and `::_get_cpu_linux` catch only `(OSError, IndexError, ValueError)` (and `ZeroDivisionError`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected E-01 and Rejected alternatives to distinguish `resources.py`'s `AttributeError`/`Exception` handlers from `liveness.py`'s Linux-dispatched helpers, noting `getattr(os, "sysconf")` preserves exact `AttributeError` behavior. |
| PR-002 | HIGH | IN-SCOPE | R2 / R4 (V-04 gaps: missing `sanitize_paths`/combined pytest, CI trigger & matrix alignment, hardcoded count, `--no-incremental`, vacuous `grep -nP`, `continue-on-error` check) | `.github/workflows/ci.yml:3-7,140-153`; `AGENTS.md#Matrix-validation discipline`; Plan `E-04` (lines 84-86), `Required tests` (lines 137-140), `V-03` (line 166), `V-04` (line 171), Gate item 3 (line 183) | `V-04` omitted `scripts/sanitize_paths.py --check --all` and the combined pytest run from `Required tests / validation`, left the CI trigger/matrix/blocked behavior under-specified across E-04/V-04/Gate, hardcoded `58 source files`, omitted `--no-incremental`/`exit=1` on mypy checks, used GNU-only vacuous `grep -nP` for the dash check, and did not verify `continue-on-error` absence. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added combined pytest and `sanitize_paths.py --check --all` to V-04, aligned E-04/V-04/Gate item 3 on `.github/workflows/ci.yml`'s `main` push/PR trigger, cross-platform `test` matrix, and `blocked` state, re-derived `<N> source files`, added `--no-incremental`/`exit=1`, replaced `grep -nP` with portable non-vacuous exit-0 `python3 -c`, and checked `continue-on-error` in `yaml.safe_load`. |
| PR-003 | MEDIUM | IN-SCOPE | R2 / R4 (Windows portability bug in E-03 and missing `-p randomly` check) | Plan `E-03` (line 77), `Required tests` (lines 137-140), `V-03` (line 166); `.aw/records/plans/pending/20261124-rand-mypy-00-srs7bs-randomized-ci-test-order-and-legacy-mypy-burn-down.ipd.md:141` | `test_resource_watcher_clock_ticks_zero_without_os_sysconf` deleted `os.sysconf` without `raising=False`, which fails on Windows where `os.sysconf` does not exist; `Required tests` and `V-03` also omitted the repeated `-p randomly` check required by orchestrator `srs7bs`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `raising=False` and Python 3.8 syntax note to E-03, and added a 3-run fail-closed `-p randomly` loop to Required tests and V-03 (2). |
| PR-004 | LOW | IN-SCOPE | R1 (stale `gzc672` status/ignore-list note and `CONTRIBUTING.md` Linux-only wording) | `pyproject.toml:115-141`; `.github/workflows/ci.yml:152-153`; `CONTRIBUTING.md:33-38`; Plan `E-04` (line 84), `Project conventions` (lines 91-92) | Project conventions described `gzc672` as unexecuted and attributed the 7-vs-10 gap solely to `resources.py` (omitting `pubrun.capture.subprocesses` added at `gzc672` execution); E-04 did not name `Run mypy` or instruct replacing `CONTRIBUTING.md`'s Linux-only phrasing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Project conventions for executed `gzc672` (both `resources.py` and `subprocesses.py` hidden until `k6fs5k`), named `Run mypy`, and explicitly instructed updating `CONTRIBUTING.md#Development setup`'s Linux-only wording. |
| PR-005 | LOW | IN-SCOPE | Check S7 / Check P (Gate item 5 unconditional finalize and Section 11.1 citations) | Plan `E-01`..`E-04`, `Project conventions`, `Findings`, Gate item 5 (line 185); `steps/s7-finalize.md:33-36` | Gate item 5 opened unconditionally with `aw ipd finalize juoqy2` without stating runner ownership first; code, test, and doc references omitted Section 11.1 `path::Symbol` / `path#Heading` forms. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Led Gate item 5 with conditional runner/executor finalization ownership and applied Section 11.1 citation forms. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Extends the blocking `.github/workflows/ci.yml` `typecheck` contract, edits four cross-platform capture modules, and updates contributor docs across 4 focused E-items. | yes |
| D-2 | Keep E-04 / V-04 gated on a human-authorized GitHub Actions run (marking `blocked` if no push/PR is authorized yet) | Keep CI observation gate and include cross-platform `test` matrix check | Defer CI observation to `Deferred / out of scope` | `AGENTS.md#Matrix-validation discipline` requires full CI matrix validation for cross-platform capture changes before moving to `executed/`, matching sibling `1kcrdn` and preserving the plan author's existing V-04 gate while respecting the never-push rule. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All five findings (PR-001..PR-005) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
