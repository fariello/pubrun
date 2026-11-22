# IPD: Fix sanitizer script, build hook, and benchmark hotpath workload bugs

- Date: 2026-11-22
- Kind: child
- Concern: Bugs and correctness (path-sanitizer binary handling, staged `--fix` data loss, glob/home-user/IPv6 matching, non-git tarball wheel builds, and benchmark hotpath workload accuracy).
- Scope: `scripts/sanitize_paths.py`, `scripts/update_commit_file.py`, `hatch_build.py`, `pyproject.toml`, `benchmarks/scenarios.py`, `benchmarks/workloads/file_read.py`, and regression tests in `tests/test_repo_scripts_bugs.py`.
- Scope-Paths: scripts/sanitize_paths.py, scripts/update_commit_file.py, hatch_build.py, pyproject.toml, benchmarks/scenarios.py, benchmarks/workloads/file_read.py, tests/test_repo_scripts_bugs.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix sanitize_paths binary crash, staged --fix data loss, glob/home-user/IPv6 bugs, non-git tarball build hook, and hotpath-open-pubrun workload
- Work-Kind: bug
- Priority: high
- Blocks-Release: next
- Set: bugs-audit
- Order: 9
- Highest E allocated: 05
- Author: Antigravity
- Id: kqzd15

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md`, including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 draft (Antigravity): created from `/assess-bugs` audit.
- 2026-11-22 to-review (Antigravity): authored fix steps, citations, and falsifiable validation criteria.

## Goal

Fix 6 confirmed bug groups across repository tooling and packaging: prevent `scripts/sanitize_paths.py` from crashing on staged binary files, destroying unstaged working-tree edits under `--fix`, or misfiring on glob/`home-user`/IPv6 rules; fix `hatch_build.py` / `pyproject.toml` / `scripts/update_commit_file.py` so builds succeed from non-git source tarballs; and make `hotpath-open-pubrun` actually exercise `pubrun.open()`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item is one focused pass with its own V-item check (`IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: `scripts/sanitize_paths.py` correctness and safety

- [ ] E-01 Fix binary staged-file reading, `--repo-root` forwarding to git helpers, and staged `--fix` safety in `scripts/sanitize_paths.py`.
  - Depends on: none
  - Expected outcome: `_read_staged` reads raw bytes (`text=False`), skips binary files containing `b"\x00"` or invalid UTF-8 without raising `UnicodeDecodeError`; `_staged_files`, `_tracked_files`, `_read_staged`, and `git add` pass `cwd=repo_root` so `--repo-root` works from any directory; `--fix` on staged files refuses to clobber files that have unstaged working-tree modifications (warning clearly instead of overwriting the working tree with the staged index blob).
  - Execution state: pending

- [ ] E-02 Fix `glob` blacklist translation, `home-user` boundary/tail matching, and `_IPV6_RE` compressed address matching in `scripts/sanitize_paths.py`.
  - Depends on: none
  - Expected outcome: `glob` blacklist rules compile without `fnmatch.translate`'s end-of-string `\Z` / `(?s:...)` newline-eating anchor so inline matches trigger and `*` stops at line/token boundaries; `home-user` matches the full path with a path boundary (`(?:/|$)`) and preserves the subpath tail (so a short prefix home directory like `HOME` ending in `al` never corrupts a longer username like `alice` into `~ice/work`, and `<home>/*` whitelists work identically for `home-user` and `home-any`); `_IPV6_RE` matches compressed IPv6 literals (`::1`, `fe80::1`, `2001:db8::1`).
  - Execution state: pending

### Task group 2: Build hook and commit metadata script fixes

- [ ] E-03 Fix `scripts/update_commit_file.py`, `hatch_build.py`, and `pyproject.toml` for gitignored `src/pubrun/COMMIT` and non-git source tarballs.
  - Depends on: none
  - Expected outcome: `scripts/update_commit_file.py` wraps file writes inside `try/except` and stops calling `git add` on gitignored `src/pubrun/COMMIT`; `hatch_build.py` dynamically registers `src/pubrun/COMMIT` in `build_data["force_include"]` only when created (or writes an `"unknown"` fallback outside git repos) while removing the fragile static `force-include` entry from `pyproject.toml` so `pip wheel` / `hatch build` succeeds cleanly from a non-git source tarball.
  - Execution state: pending

### Task group 3: Benchmark hotpath file-open workload fix

- [ ] E-04 Fix `benchmarks/workloads/file_read.py` and `benchmarks/scenarios.py` so `hotpath-open-pubrun` exercises `pubrun.open()` instead of unpatched `builtins.open()`.
  - Depends on: none
  - Expected outcome: Under `pubrun` mode (`hotpath-open-pubrun`), `file_read.py` opens files through `pubrun.open()` (while `hotpath-open-baseline` continues using `builtins.open()`), actually measuring pubrun's file-open overhead rather than a no-op.
  - Execution state: pending

### Task group 4: Regression test suite and sanitizer verification

- [ ] E-05 Add regression tests in `tests/test_repo_scripts_bugs.py`, run `python3 scripts/sanitize_paths.py --check --all`, and verify the full `pytest` suite passes.
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: `tests/test_repo_scripts_bugs.py` verifies all sanitizer, build-hook, and workload fixes; `python3 scripts/sanitize_paths.py --check --all` exits 0; full `pytest -q` passes with zero regressions.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `scripts/sanitize_paths.py` is stdlib-only and runs in CI and pre-commit; verify `python3 scripts/sanitize_paths.py --check --all` passes after changing rule matching so no unintended false positives break existing repo files.
- `benchmarks/data/` already contains a baseline submission for `hotpath-open-pubrun`; see `OQ-01` below (non-blocking) on whether to keep the existing scenario name or add a versioned name.

## Findings

| Bug ID | Severity | Remediation Risk | Location (symbol) | Defect |
|---|---|---|---|---|
| `BUG-25` | High | Low | `scripts.sanitize_paths._read_staged` | Uses `text=True` (strict UTF-8) and crashes with `UnicodeDecodeError` on any staged binary file before `_looks_binary()`. |
| `BUG-26` | High | Low | `scripts.sanitize_paths.main`, `_staged_files`, `_tracked_files`, `_read_staged` | `--fix` on staged files overwrites the working tree with the staged index blob (destroying unstaged edits); git helpers ignore `--repo-root`. |
| `BUG-27` | High | Low | `scripts.sanitize_paths.build_rules` | `fnmatch.translate()` anchors glob blacklists to `\Z` and eats trailing newlines; `home-user` lacks path boundary/tail, breaking `<home>/*` whitelists and corrupting a prefix-sharing user path (e.g. `al` vs `alice`) to `~ice`. |
| `BUG-57` | Medium | Low | `benchmarks.scenarios.default_scenarios`, `benchmarks/workloads/file_read.py` | `hotpath-open-pubrun` calls `builtins.open()` instead of `pubrun.open()`, never exercising pubrun's file-open path. |
| `BUG-58` | Medium | Low | `scripts.sanitize_paths._IPV6_RE` | Fails to match compressed (`::`) IPv6 addresses (`::1`, `2001:db8::1`, `fe80::1`). |
| `BUG-59` | Medium | Medium | `scripts.update_commit_file`, `hatch_build.py`, `pyproject.toml` | `git add` on gitignored `src/pubrun/COMMIT` always fails (and write is outside `try/except`); static `force-include` breaks builds from non-git GitHub source tarballs. |

## Proposed changes (ordered, validatable)

1. In `scripts/sanitize_paths.py`: read raw bytes in `_read_staged`, detect binary via `b"\x00"` / decode fallback, pass `cwd=repo_root` to all git subprocess calls, refuse `--fix` on staged files with unstaged working-tree diffs (`git diff --name-only`), translate `glob` rules cleanly without `\Z`/`(?s:...)`, anchor `home-user` with a subpath tail and boundary matching `_HOME_ANY_RE`, and update `_IPV6_RE` to recognize compressed `::` IPv6 addresses.
2. In `scripts/update_commit_file.py`, `hatch_build.py`, and `pyproject.toml`: remove `git add` on gitignored `COMMIT`, wrap writes in `try/except`, move `src/pubrun/COMMIT` force-include into `hatch_build.py`'s `build_data["force_include"]` when the file exists, and verify building from a copied non-git directory.
3. In `benchmarks/workloads/file_read.py` and `benchmarks/scenarios.py`: use `pubrun.open` when running under `pubrun` mode in `hotpath-open-pubrun`.
4. Add `tests/test_repo_scripts_bugs.py`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none.
- Under-scope: none.

## Required tests / validation

- Run `pytest tests/test_repo_scripts_bugs.py -v` and paste actual output.
- Run `python3 scripts/sanitize_paths.py --check --all` and paste actual output.
- Run full `pytest -q` and paste actual output confirming zero regressions.

## Spec / documentation sync

N/A: fixes internal scripts, packaging hook, and benchmark workload accuracy.

## Open questions

### OQ-01: Should `hotpath-open-pubrun` keep its current scenario name after switching to `pubrun.open()`?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: Fix `hotpath-open-pubrun` in place to call `pubrun.open()` so the scenario measures what its name claims, and note the semantic change in benchmark release notes (prior `benchmarks/data/` entries measured unpatched `builtins.open()`). Human plan approval confirms keeping the scenario name rather than renaming to `hotpath-pubrun-open` before execution.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `pytest tests/test_repo_scripts_bugs.py -v` output confirming staged binary files are skipped cleanly, `--repo-root` works from a different CWD, and `--fix` does not clobber unstaged edits in a partially staged file.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `pytest tests/test_repo_scripts_bugs.py -v` output confirming inline `glob` blacklists match without eating newlines, a prefix-sharing `HOME` (`al`) does not corrupt a longer username (`alice`) into `~ice/work`, `<home>/*` whitelists work under `home-user`, and `_IPV6_RE` matches `::1`, `fe80::1`, and `2001:db8::1`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `pytest tests/test_repo_scripts_bugs.py -v` output confirming `hatch_build.py` and `update_commit_file.py` succeed cleanly in a temporary directory with no `.git` folder and never call `git add` on gitignored `COMMIT`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `pytest tests/test_repo_scripts_bugs.py -v` output confirming `benchmarks/workloads/file_read.py` invokes `pubrun.open` under pubrun mode and `builtins.open` under baseline mode.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted output from `python3 scripts/sanitize_paths.py --check --all` (exit 0) and full `pytest -q` showing `tests/test_repo_scripts_bugs.py` and all pre-existing tests pass with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Wait for human approval (`- Status: approved`) before executing. Commit only files listed in `Scope-Paths` via `aw commit kqzd15 -- scripts/sanitize_paths.py scripts/update_commit_file.py hatch_build.py pyproject.toml benchmarks/scenarios.py benchmarks/workloads/file_read.py tests/test_repo_scripts_bugs.py`, then move this plan to `.aw/records/plans/executed/` through the post-gate lifecycle transition.
