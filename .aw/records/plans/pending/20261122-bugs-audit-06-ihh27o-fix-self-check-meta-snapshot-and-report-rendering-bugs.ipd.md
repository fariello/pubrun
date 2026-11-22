# IPD: Fix self-check, meta snapshot, and report rendering bugs

- Date: 2026-11-22
- Kind: child
- Concern: Bugs and correctness (diagnostic self-checks, meta snapshot depth handling, resource report labeling, null-safe CPU formatting, and manifest hydration).
- Scope: `src/pubrun/report/checks.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/report/diagnostics.py`, `src/pubrun/report/methods.py`, `src/pubrun/report/utils.py`, and regression tests in `tests/test_report_checks_bugs.py`.
- Scope-Paths: src/pubrun/report/checks.py, src/pubrun/report/meta_snapshot.py, src/pubrun/report/diagnostics.py, src/pubrun/report/methods.py, src/pubrun/report/utils.py, tests/test_report_checks_bugs.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix malformed TOML detection in self-check, meta depth flags, SGE/PBS check precedence, multi-mount reporting, and manifest hydration bugs
- Work-Kind: bug
- Priority: high
- Blocks-Release: next
- Set: bugs-audit
- Order: 6
- Highest E allocated: 05
- Author: Antigravity
- Id: ihh27o

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md`, including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 draft (Antigravity): created from `/assess-bugs` audit.
- 2026-11-22 to-review (Antigravity): authored fix steps, citations, and falsifiable validation criteria.

## Goal

Fix 8 confirmed diagnostic and reporting bugs so `pubrun self-check` detects malformed TOML configs, preserves all filesystem findings, distinguishes SGE compute nodes from PBS login nodes, and never infinite-loops on non-existent drives; `pubrun meta --basic/--standard/--deep` actually controls capture depth; and resource/methods/hydration reports format data accurately.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item is one focused pass with its own V-item check (`IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: `report/checks.py` diagnostic accuracy and termination

- [ ] E-01 Fix `report.checks._install_health_findings` and `report.checks.live_checks` to report malformed `.pubrun.toml` / config files as failing checks and preserve all filesystem findings.
  - Depends on: none
  - Expected outcome: `_install_health_findings` explicitly parses discovered config TOML files (or inspects `config` parse errors) and emits an error/warn finding when `.pubrun.toml` or `pyproject.toml` has invalid TOML so `self-check --strict` exits non-zero; `live_checks` returns every filesystem finding rather than dropping all entries after the first.
  - Execution state: pending

- [ ] E-02 Fix `report.checks._hpc_login_node_findings` and output-directory writability traversal in `src/pubrun/report/checks.py`.
  - Depends on: none
  - Expected outcome: `_hpc_login_node_findings` checks SGE compute-node variables (`JOB_ID`/`SGE_ROOT`) before PBS login-node heuristics so SGE compute jobs are not misidentified as PBS login nodes; output-dir writability resolves relative paths against CWD and terminates cleanly when `parent == current` (preventing infinite loops on nonexistent Windows drive letters).
  - Execution state: pending

### Task group 2: Meta snapshot depth and report rendering fixes

- [ ] E-03 Fix `report.meta_snapshot.generate_meta_snapshot` to translate `depth` (`basic`/`standard`/`deep`) into active capture configuration keys instead of deprecated `core.profile`.
  - Depends on: none
  - Expected outcome: Passing `--basic`, `--standard`, or `--deep` to `generate_meta_snapshot` produces visibly distinct capture depth configuration for hardware/git/environment/packages collectors instead of acting as a no-op.
  - Execution state: pending

- [ ] E-04 Fix `report.diagnostics.print_resources_report`, `report.methods` / `report.diagnostics` null CPU formatting, and `report.utils.hydrate_manifest`.
  - Depends on: none
  - Expected outcome: `print_resources_report` labels main-process `rss` data accurately (and only prints `(process tree)` when displaying tree-scoped RSS data); `methods.py` and `diagnostics.py` omit or replace `None` gracefully when ARM64 `cpu.model` is `null` instead of rendering literal `"None"`; `hydrate_manifest` hydrates `"host"` from meta snapshots alongside other environment sections.
  - Execution state: pending

### Task group 3: Regression test suite

- [ ] E-05 Add regression tests in `tests/test_report_checks_bugs.py` and verify the full `pytest` suite passes.
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: `tests/test_report_checks_bugs.py` verifies all 8 defects above, and `pytest -q` passes with zero regressions.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `config.resolve_config` intentionally warns and continues on malformed TOML during normal user scripts so instrumentation never breaks a user's workload; therefore `report.checks._install_health_findings` must explicitly validate config TOML syntax itself (or consume recorded config parse notices).
- Pending IPD Set `timing-acc` touches `report/diagnostics.py`; keep edits strictly scoped to `print_resources_report` and null CPU formatting.

## Findings

| Bug ID | Severity | Remediation Risk | Location (symbol) | Defect |
|---|---|---|---|---|
| `BUG-16` | High | Low | `report.checks._install_health_findings` | Relies on `resolve_config()`, which swallows `TOMLDecodeError`, so malformed `.pubrun.toml` prints `[ OK  ]` and exits 0 even under `--strict`. |
| `BUG-17` | High | Low | `report.meta_snapshot.generate_meta_snapshot` | Passes deprecated inert `{"core": {"profile": depth}}`, making `pubrun meta --basic/--standard/--deep` a no-op. |
| `BUG-46` | Medium | Low | `report.checks._hpc_login_node_findings` | SGE compute nodes match PBS login-node check first, making the SGE branch unreachable. |
| `BUG-47` | Medium | Low | `report.checks.live_checks` | Drops all filesystem findings after the first in default `pubrun self-check`. |
| `BUG-48` | Medium | Low | `report.checks._install_health_findings` (writability loop) | Loops infinitely on nonexistent Windows drive root and skips CWD check on relative output paths. |
| `BUG-49` | Medium | Low | `report.diagnostics.print_resources_report` | Titles main-process `rss` data as `"Memory (RSS) History (process tree)"`. |
| `BUG-64a` | Low | Low | `report.methods`, `report.diagnostics` | Renders literal `"None"` when ARM64 `cpu.model` is `null`. |
| `BUG-65` | Low | Low | `report.utils.hydrate_manifest` | Omits `"host"` when hydrating manifests from meta snapshots. |

## Proposed changes (ordered, validatable)

1. In `src/pubrun/report/checks.py`: validate discovered TOML files directly in `_install_health_findings` and emit a non-OK finding on `TOMLDecodeError`; return all filesystem findings from `live_checks`; reorder SGE detection ahead of PBS login-node fallback in `_hpc_login_node_findings`; resolve relative `output_dir` via `.resolve()` and guard `parent == current` in the writability walk.
2. In `src/pubrun/report/meta_snapshot.py`: map `depth` (`basic`/`standard`/`deep`) onto concrete `capture.*` depth/mode overrides recognized by `resolve_config`.
3. In `src/pubrun/report/diagnostics.py`, `src/pubrun/report/methods.py`, and `src/pubrun/report/utils.py`: fix the RSS header label based on whether tree RSS or main-process RSS is plotted, guard `cpu.model` against `None`, and include `"host"` in `hydrate_manifest`.
4. Add `tests/test_report_checks_bugs.py`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none.
- Under-scope: none.

## Required tests / validation

- Run `pytest tests/test_report_checks_bugs.py -v` and paste actual output.
- Run full `pytest -q` and paste actual output confirming zero regressions.

## Spec / documentation sync

N/A: fixes diagnostic accuracy and documented `--basic`/`--standard`/`--deep` flags without altering CLI interfaces.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `pytest tests/test_report_checks_bugs.py -v` output confirming malformed `.pubrun.toml` produces a non-OK finding in `_install_health_findings` and `live_checks` preserves multiple filesystem findings.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `pytest tests/test_report_checks_bugs.py -v` output confirming SGE compute-node env vars are not misclassified as PBS login node and writability check handles relative paths and non-existent roots without looping.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `pytest tests/test_report_checks_bugs.py -v` output confirming `generate_meta_snapshot` with `basic`, `standard`, and `deep` configures distinct collector depths.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `pytest tests/test_report_checks_bugs.py -v` output confirming `print_resources_report` RSS title matches scope, `cpu.model = None` does not print `"None"`, and `hydrate_manifest` populates `"host"`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted full `pytest -q` summary confirming `tests/test_report_checks_bugs.py` and the full test suite pass with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Wait for human approval (`- Status: approved`) before executing. Commit only files listed in `Scope-Paths` via `aw commit ihh27o -- src/pubrun/report/checks.py src/pubrun/report/meta_snapshot.py src/pubrun/report/diagnostics.py src/pubrun/report/methods.py src/pubrun/report/utils.py tests/test_report_checks_bugs.py`, then move this plan to `.aw/records/plans/executed/` through the post-gate lifecycle transition.
