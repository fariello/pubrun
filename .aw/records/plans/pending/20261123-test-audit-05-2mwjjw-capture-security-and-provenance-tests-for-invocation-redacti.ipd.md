# IPD: Capture security and provenance tests for invocation, redaction, and file I/O

- Date: 2026-11-23
- Kind: child
- Concern: Testing rigor and completeness (high-risk security and provenance capture paths in `invocation.py`, `redaction.py`, `file_io.py`, core/capture fallbacks, and `test_sanitize_paths.py`).
- Scope: `src/pubrun/capture/invocation.py`, `tests/test_invocation.py`, `tests/test_redaction.py`, `tests/test_file_io_provenance.py`, `tests/test_explicit_api.py`, and `tests/test_sanitize_paths.py`.
- Scope-Paths: src/pubrun/capture/invocation.py, tests/test_invocation.py, tests/test_redaction.py, tests/test_file_io_provenance.py, tests/test_explicit_api.py, tests/test_sanitize_paths.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Add behavioral tests for invocation hashing/inputs, redaction JSON/token heuristics, file_io edge methods, and core fallbacks
- Work-Kind: chore
- Priority: high
- Set: test-audit
- Order: 5
- Highest E allocated: 05
- Author: Antigravity
- Id: 2mwjjw

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-23 to-review (Antigravity): authored from `/assess-testing` findings T-08 (`test_sanitize_paths.py`), T-10, T-11, and T-12.
- 2026-11-23 draft (Antigravity): created.

## Goal

Add deterministic behavioral tests for untested security-sensitive and provenance-critical capture code (`invocation.py` entrypoint/hashing/input discovery, `redaction.py` recursive JSON-in-string and token heuristics, `file_io.py` proxy edge methods and `truncate()` budget recovery, and core/capture fallback paths) while removing dead pre-redaction code in `invocation.py` and the silent TOML skip in `test_sanitize_paths.py`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item addresses one concern executable in one focused pass. Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Invocation cleanup and behavioral tests

- [ ] E-01 Clean dead pre-redaction `rerun_command` computation in `src/pubrun/capture/invocation.py:get_invocation` (and extract small internal helpers `_inspect_script` and `_discover_argv_inputs` without changing `get_invocation`'s public contract) and create `tests/test_invocation.py` testing: every `entrypoint_type` (`script`, `-m`, `-c`, empty `argv`, missing `argv[0]`), script SHA-256 below 1 MiB vs `sha256_skipped` above 1 MiB, `sys.argv` dataset discovery (`inputs.enabled=False`, `-`/`--` flags, case-insensitive `ignore_extensions`, file vs dir metadata, `compute_md5=True` digest + warning log), and `sys.platform == "win32"` `command_line`/`rerun_command` formatting.
  - Depends on: none
  - Expected outcome: Dead pre-redaction `rerun_command` code is gone and all `invocation.py` branches are verified by deterministic unit tests.
  - Execution state: pending

### Task group 2: Security redaction tests

- [ ] E-02 Expand `tests/test_redaction.py` to test recursive JSON-in-string redaction (`_redact_dict_keys`, `_redact_any`, and JSON handling in `_redact_value_string_heuristics`) for nested objects and arrays inside non-secret env vars and argv values, invalid-JSON fallthrough to URI/token regexes, `sk-...` and `Bearer ...` heuristics through `redact_env_vars()` and `redact_argv()`, non-secret `--flag=value` heuristic redaction, and non-string `argv` entries (such as `Path`).
  - Depends on: none
  - Expected outcome: All redaction heuristic and recursive JSON branches are pinned against secret-leak regressions.
  - Execution state: pending

### Task group 3: File I/O proxy edge methods and budget recovery

- [ ] E-03 Expand `tests/test_file_io_provenance.py` to test `ProvenanceFileProxy.read1`, `readinto1`, binary `readlines(hint=...)` (confirming `hint > 0` does not falsely set EOF while `hint <= 0` does), `truncate()` after exceeding `max_hash_bytes` (confirming post-close hashing recovers rather than short-circuiting as `over_budget`), and `pubrun.open(..., mode="xb")` streaming digest plus `FileExistsError` propagation.
  - Depends on: none
  - Expected outcome: All proxy edge I/O methods, truncate budget recovery, and exclusive-create `xb` behavior are verified.
  - Execution state: pending

### Task group 4: Core/capture fallbacks and sanitizer TOML assertion

- [ ] E-04 Expand `tests/test_explicit_api.py` with targeted unit tests for untested fallback branches in `src/pubrun/core.py` (`report`/`artifact` inactive-run policy, list-data `summary={"items": len(data)}`, write-failure logging without raising, `phase` nested/concurrent `yappi` guard and unknown profiling backend warning), `src/pubrun/capture/process.py` (`getpass.getuser()` failure fallback to `"unknown"`, missing `os.getuid`/`os.getgid`), `src/pubrun/capture/host.py` (empty `platform.node()` fallback to `socket.gethostname()`, exception -> `capture_state.status == "failed"`), and `src/pubrun/capture/python_runtime.py` (`conda-meta`, `sys.real_prefix` `"virtualenv"`, `sys.frozen` `"frozen"`, `PYENV_VERSION` `"pyenv"`).
  - Depends on: none
  - Expected outcome: Each minor fallback path is verified by deterministic unit assertions.
  - Execution state: pending

- [ ] E-05 Update `tests/test_sanitize_paths.py:test_config_toggles_ip_and_lists` to assert `sp._toml is not None` instead of calling `pytest.skip` when the mandatory `tomllib`/`tomli` parser fails to load.
  - Depends on: none
  - Expected outcome: A broken TOML import in `scripts/sanitize_paths.py` fails the test immediately instead of skipping silently.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Measured coverage baseline: `src/pubrun/capture/invocation.py` is at `70%` (31 missed statements), `src/pubrun/capture/python_runtime.py` at `78%`, `src/pubrun/capture/file_io.py` at `82%` (proxy edge methods `read1`/`readinto1`/`readlines`/`truncate` all uncovered).
- `pyproject.toml` declares `tomli>=1.1.0; python_version < '3.11'` as a mandatory dependency, so TOML parsing is always available on Python 3.8 through 3.14.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| T-10 | High | Low | Testing expert / Security reviewer | `src/pubrun/capture/invocation.py:get_invocation` (70% coverage) | Entrypoint classification, `>1MB` `sha256_skipped`, argv input discovery, `ignore_extensions`, `compute_md5`, and `win32` `rerun_command` have zero tests; dead pre-redaction `rerun_command` remains. |
| T-11 | High | Low | Security reviewer / Testing expert | `src/pubrun/capture/redaction.py:_redact_dict_keys`, `_redact_any`, `_redact_value_string_heuristics` | Recursive JSON-in-string redaction and direct env/argv `sk-`/`Bearer` heuristics have zero tests. |
| T-12 | Medium | Low | Testing expert | `src/pubrun/capture/file_io.py:ProvenanceFileProxy`; `src/pubrun/core.py`; `process.py`; `host.py`; `python_runtime.py` | Proxy `read1`/`readinto1`/`readlines`/`truncate`/`xb` and core/capture fallbacks are untested. |
| T-08 (part) | High | Low | Testing expert | `tests/test_sanitize_paths.py:test_config_toggles_ip_and_lists` | Skips silently if `sp._toml is None` despite mandatory TOML dependency. |

## Proposed changes (ordered, validatable)

1. Remove dead pre-redaction code in `src/pubrun/capture/invocation.py` and add `tests/test_invocation.py` (Remediation Risk: Low).
2. Add JSON-in-string and token-heuristic tests to `tests/test_redaction.py` (Remediation Risk: Low).
3. Add proxy edge-method, `truncate` budget-recovery, and `xb` tests to `tests/test_file_io_provenance.py` (Remediation Risk: Low).
4. Add core/process/host/python_runtime fallback tests to `tests/test_explicit_api.py` (Remediation Risk: Low).
5. Replace the silent TOML skip in `tests/test_sanitize_paths.py` with a hard assertion (Remediation Risk: Low).

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none.
- Under-scope: none.

## Required tests / validation

- Run `pytest tests/test_invocation.py tests/test_redaction.py tests/test_file_io_provenance.py tests/test_explicit_api.py tests/test_sanitize_paths.py tests/test_capture.py -v`.
- Run `python3 scripts/sanitize_paths.py --check --all`.

## Spec / documentation sync

N/A with reason: internal helper cleanup and test additions do not change public contracts.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted output of `pytest tests/test_invocation.py tests/test_capture.py -v` showing all invocation branches passing and diff of `src/pubrun/capture/invocation.py` confirming dead pre-redaction code removal.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted output of `pytest tests/test_redaction.py -v` showing all new recursive JSON and `sk-`/`Bearer`/non-string argv tests passing.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted output of `pytest tests/test_file_io_provenance.py -v` showing `read1`, `readinto1`, `readlines`, `truncate` budget recovery, and `xb` tests passing.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted output of `pytest tests/test_explicit_api.py -v` showing all core, process, host, and `python_runtime` fallback tests passing.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted output of `pytest tests/test_sanitize_paths.py -v` with 0 skips and `python3 scripts/sanitize_paths.py --check --all` exit 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

This plan must be reviewed and explicitly approved by a human (`- Status: approved`) before execution. During execution, commit only the scoped files through `aw commit`, never push without explicit human instruction, and move this plan to `.aw/records/plans/executed/` only after all `E-*` items are `performed`, all `V-*` items are `pass`, and `aw ipd lint` reports `conforming`.
