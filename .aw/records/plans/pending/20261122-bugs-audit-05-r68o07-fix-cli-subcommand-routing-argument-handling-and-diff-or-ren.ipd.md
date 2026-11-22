# IPD: Fix CLI subcommand routing, argument handling, and diff or render bugs

- Date: 2026-11-22
- Kind: child
- Concern: Bugs and correctness (CLI subcommand routing, exit codes, command flags, hashed-redaction manifest diffing, and diff rendering accuracy).
- Scope: `src/pubrun/__main__.py`, `src/pubrun/analysis/diff.py`, `src/pubrun/analysis/render.py`, and regression tests in `tests/test_cli_diff_bugs.py`.
- Scope-Paths: src/pubrun/__main__.py, src/pubrun/analysis/diff.py, src/pubrun/analysis/render.py, tests/test_cli_diff_bugs.py
- Item-Dependencies: executed:njn1up
- Status: to-review
- Short-Description: Fix CLI subcommands allowlist, exit codes, show/combined/diff/bench flags, hashed-redaction diff, and path/table rendering bugs
- Work-Kind: bug
- Priority: high
- Blocks-Release: next
- Set: bugs-audit
- Order: 5
- Highest E allocated: 05
- Author: Antigravity
- Id: r68o07

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md`, including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 draft (Antigravity): created from `/assess-bugs` audit.
- 2026-11-22 to-review (Antigravity): authored fix steps, citations, and falsifiable validation criteria.

## Goal

Fix 11 confirmed CLI and diff/render correctness bugs, including the incomplete `subcommands` allowlist that misroutes `pubrun inspect -f run` into `Popen`, misleading zero exit codes on failed/incomplete runs, ignored filter flags, broken hashed-redaction diffing, and path/table rendering defects, while surfacing `ValueError` from `status.filter_runs` (`njn1up`) cleanly with exit code 1.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item is one focused pass with its own V-item check (`IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: CLI subcommand routing, argument handling, and exit codes

- [ ] E-01 Fix `main` subcommand allowlist, `show`/`combined`/`diff` argument handling, and `ValueError` handling for `--older-than` in `src/pubrun/__main__.py`.
  - Depends on: none
  - Expected outcome: `subcommands` in `pubrun.__main__.main` includes every registered subcommand (`init`, `report-bug`, `feedback`, `self-check`, `inspect`, `bench`, and all existing commands/aliases) so `pubrun inspect -f run`, `pubrun help <cmd>`, `pubrun init help`, and `pubrun 1 inspect` route accurately; `pubrun combined` includes `-F`/`--not-filter` and `-S`/`--not-status` in `has_filters`; bare `pubrun show` defaults to the single most recent run rather than dumping every run; `pubrun diff` with one explicit path does not compare a run against itself; invalid `--older-than` values raising `ValueError` from `status.filter_runs` print a clear error to `stderr` and exit 1.
  - Execution state: pending

- [ ] E-02 Fix `_run_methods`, `_run_resources`, `_run_report`, `bench`, `_create_result_gist`, and `_run_tests` in `src/pubrun/__main__.py`.
  - Depends on: none
  - Expected outcome: `_run_methods` and `_run_resources` exit non-zero on crashed/in-progress lock-only runs lacking a manifest; `_run_report` skips lock-only runs cleanly without calling `sys.exit(0)` mid-loop during multi-run `show logs`; `pubrun bench` checks non-zero return codes for PBS/LSF/SGE job submissions and surfaces `_qsub_ambiguous()` warning where applicable; `_create_result_gist` handles non-JSON/HTTP failure cleanly without leaking an orphaned gist; `_run_tests` invokes `sys.executable` instead of hardcoded `"python"` and propagates the test runner's exit code.
  - Execution state: pending

### Task group 2: Manifest diff and rendering fixes

- [ ] E-03 Fix `analysis.diff._normalize_manifest`, `_is_path_var`, and `_should_ignore` in `src/pubrun/analysis/diff.py`.
  - Depends on: none
  - Expected outcome: `_normalize_manifest` preserves a distinct representation for `{"representation": "hashed", "hash_value": "..."}` (and redacted markers) instead of collapsing them to `""`, so changed hashed secrets appear in diffs and never alias empty plain strings; `_is_path_var` restricts `PATH`-style splitting to environment variable keys rather than manifest fields ending in `.path`/`.real_path`; `_should_ignore` requires exact key match or a dot boundary (`key.startswith(prefix + ".")`) instead of raw prefix matching.
  - Execution state: pending

- [ ] E-04 Fix `analysis.render` path-split ordering, `_render_table`, and `_render_inline` in `src/pubrun/analysis/render.py`.
  - Depends on: E-03
  - Expected outcome: `path_split` rendering detects and displays order-only `PATH` changes (same element set in a different order); `_render_table` respects both `same` (when requested) and `max_length` truncation; `_render_inline` preserves bool/int type tagging (`True` vs `1`).
  - Execution state: pending

### Task group 3: Regression test suite

- [ ] E-05 Add regression tests in `tests/test_cli_diff_bugs.py` and verify the full `pytest` suite passes.
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: `tests/test_cli_diff_bugs.py` exercises all 11 bugs plus CLI `--older-than` `ValueError` handling, and `pytest -q` passes with zero regressions.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Depends on `njn1up` (Order 01) for `status.filter_runs` raising `ValueError` on invalid `older_than` inputs.
- Pending IPD Sets `repro-check`, `timing-acc`, and `file-prov` also touch `src/pubrun/__main__.py`; keep edits strictly within the affected command functions and dispatch table.
- Tests must exercise CLI dispatch, `compare_manifests`, and renderer functions directly with real outputs and exit codes (no code-pinning).

## Findings

| Bug ID | Severity | Remediation Risk | Location (symbol) | Defect |
|---|---|---|---|---|
| `BUG-11` | High | Low | `__main__.main` | `subcommands` allowlist omits `init`, `report-bug`, `feedback`, `self-check`, `inspect`, `bench`; causes `pubrun inspect -f run` to invoke `Popen(['inspect', '-f'])` and breaks `help` / run-first ordering. |
| `BUG-12` | High | Low | `analysis.diff._normalize_manifest` | Collapses `{"representation": "hashed", "hash_value": "..."}` to `""`, breaking hashed secret diffing and aliasing empty strings. |
| `BUG-42` | Medium | Low | `__main__._run_methods`, `__main__._run_resources` | Exit 0 on crashed/in-progress lock-only runs instead of non-zero. |
| `BUG-43` | Medium | Low | `__main__._run_combined` | `has_filters` ignores `-F`/`--not-filter` and `-S`/`--not-status`, truncating filtered results to 1 run. |
| `BUG-44` | Medium | Low | `__main__.main` (`show`), `__main__._run_report` | Bare `pubrun show` dumps all runs instead of most recent; `_run_report` calls `sys.exit(0)` mid-loop on lock-only `show logs`. |
| `BUG-45` | Medium | Low | `__main__._run_bench`, `__main__._qsub_ambiguous` | Ignores non-zero exit codes for PBS/LSF/SGE; `_qsub_ambiguous()` warning is unreachable dead code. |
| `BUG-50` | Medium | Low | `analysis.diff._is_path_var`, `analysis.render` | Misclassifies `.path`/`.real_path` manifest fields as `PATH` env vars; `path_split` hides order-only `PATH` changes. |
| `BUG-64` | Low | Low | `analysis.diff._should_ignore`, `analysis.render._render_table`, `_render_inline` | `_should_ignore` lacks dot boundary; `_render_table` ignores `same` and `max_length`; `_render_inline` drops bool/int type tagging. |
| `BUG-66` | Low | Low | `__main__._create_result_gist` | Can leak an orphaned gist or raise unhandled `JSONDecodeError` on failed response. |
| `BUG-67a` | Low | Low | `__main__._run_tests` | Hardcodes `"python"` instead of `sys.executable` and ignores subprocess exit code. |
| `BUG-68` | Low | Low | `__main__._run_diff` | Single-run `pubrun diff runs/X/manifest.json` compares the run against itself. |

## Proposed changes (ordered, validatable)

1. In `src/pubrun/__main__.py`: derive or maintain the complete `subcommands` set covering every registered subparser and alias; update `combined`'s `has_filters`; bound bare `show` to the latest run; avoid mid-loop `sys.exit(0)` in `_run_report`; exit non-zero in `_run_methods`/`_run_resources` on lock-only runs; surface `ValueError` from `filter_runs`/`clean_runs` as exit 1; check PBS/LSF/SGE exit codes and wire `_qsub_ambiguous()`; guard `_create_result_gist`; use `sys.executable` and return code in `_run_tests`; prevent self-comparison in single-argument `pubrun diff`.
2. In `src/pubrun/analysis/diff.py`: normalize hashed redaction dicts to a canonical non-empty sentinel carrying `hash_value` (e.g., `f"[HASHED:{hash_value}]"`), restrict `_is_path_var` to `environment.*` keys, and enforce exact-or-dot-prefix matching in `_should_ignore`.
3. In `src/pubrun/analysis/render.py`: report order-only differences in `path_split`, honor `same` and `max_length` in `_render_table`, and include bool/int type distinction in `_render_inline`.
4. Add `tests/test_cli_diff_bugs.py`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none.
- Under-scope: none.

## Required tests / validation

- Run `pytest tests/test_cli_diff_bugs.py -v` and paste actual output.
- Run full `pytest -q` and paste actual output confirming zero regressions.

## Spec / documentation sync

N/A: aligns CLI routing, exit codes, and manifest diffing with existing `--help` text and documented semantics.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `pytest tests/test_cli_diff_bugs.py -v` output confirming `pubrun inspect -f run` does not invoke `Popen`, `pubrun help init` / `pubrun init help` / `pubrun 1 inspect` route properly, `combined -S failed` retains all matching runs, bare `show` selects only the latest run, single-run `diff` does not self-compare, and invalid `--older-than` exits 1 with an error message.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `pytest tests/test_cli_diff_bugs.py -v` output confirming non-zero exits on lock-only `methods`/`resources`, full loop completion on multi-run `show logs`, non-zero exit handling + ambiguity warning in `bench`, safe error handling in `_create_result_gist`, and `sys.executable` + exit-code propagation in `_run_tests`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `pytest tests/test_cli_diff_bugs.py -v` output confirming `compare_manifests` detects changed `hash_value` dicts and distinguishes redacted values from `""`, leaves `.path`/`.real_path` unsplit, and enforces dot boundaries in `_should_ignore`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `pytest tests/test_cli_diff_bugs.py -v` output confirming order-only `PATH` changes render visibly, `_render_table` honors `same` and `max_length`, and `_render_inline` distinguishes `True` vs `1`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted full `pytest -q` summary confirming `tests/test_cli_diff_bugs.py` and the full test suite pass with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Wait for human approval (`- Status: approved`) before executing. Commit only files listed in `Scope-Paths` via `aw commit r68o07 -- src/pubrun/__main__.py src/pubrun/analysis/diff.py src/pubrun/analysis/render.py tests/test_cli_diff_bugs.py`, then move this plan to `.aw/records/plans/executed/` through the post-gate lifecycle transition.
