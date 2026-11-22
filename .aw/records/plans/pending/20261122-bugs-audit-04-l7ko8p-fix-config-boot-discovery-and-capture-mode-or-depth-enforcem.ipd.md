# IPD: Fix config boot discovery and capture mode or depth enforcement bugs

- Date: 2026-11-22
- Kind: child
- Concern: Bugs and correctness (configuration discovery parity at boot, non-mutating config resolution, environment allowlist mode, and per-collector `depth = "off"` enforcement).
- Scope: `src/pubrun/_config_boot.py`, `src/pubrun/config.py`, `src/pubrun/capture/environment.py`, `src/pubrun/capture/git.py`, `src/pubrun/capture/host.py`, `src/pubrun/capture/process.py`, `src/pubrun/capture/python_runtime.py`, and regression tests in `tests/test_config_capture_modes.py`.
- Scope-Paths: src/pubrun/_config_boot.py, src/pubrun/config.py, src/pubrun/capture/environment.py, src/pubrun/capture/git.py, src/pubrun/capture/host.py, src/pubrun/capture/process.py, src/pubrun/capture/python_runtime.py, tests/test_config_capture_modes.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Honor environment allowlist mode, per-collector depth=off, XDG/global boot config files, and non-mutating config resolution
- Work-Kind: bug
- Priority: medium
- Blocks-Release: next
- Set: bugs-audit
- Order: 4
- Highest E allocated: 04
- Author: Antigravity
- Id: l7ko8p

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md`, including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 draft (Antigravity): created from `/assess-bugs` audit.
- 2026-11-22 to-review (Antigravity): authored fix steps, citations, and falsifiable validation criteria.

## Goal

Align boot-time configuration discovery with full `config.resolve_config` precedence, prevent `resolve_config` from mutating caller override dicts or treating empty `XDG_CONFIG_HOME` as a relative path, and make capture collectors honor documented `[capture.environment].mode = "allowlist"` and `[capture.*].depth = "off"` settings.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item is one focused pass with its own V-item check (`IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Config discovery and resolution parity

- [ ] E-01 Fix `config.py` (`XDG_CONFIG_HOME` fallback and deep-copying caller `overrides`) and `_config_boot.py` (user global/project config discovery and `PUBRUN_AUTO_START` truthy/falsy values).
  - Depends on: none
  - Expected outcome: When `XDG_CONFIG_HOME=""` (empty string), `config.py` falls back to `~/.config/pubrun/config.toml` instead of `./pubrun/config.toml`; `resolve_config(overrides)` deep-copies `overrides` before mutating nested sections like `"core"`; `_config_boot.py` reads `~/.config/pubrun/config.toml` (honoring non-empty `XDG_CONFIG_HOME`) and `./.config/pubrun/config.toml` in the same precedence order as `config.py`, and parses `PUBRUN_AUTO_START` for `"0"`/`"1"`/`"no"`/`"yes"`/`"false"`/`"true"` (case-insensitive).
  - Execution state: pending

### Task group 2: Environment allowlist mode and `depth = "off"` enforcement

- [ ] E-02 Fix `capture.environment.get_environment` to honor `mode = "allowlist"` and `depth = "off"`.
  - Depends on: none
  - Expected outcome: Setting `[capture.environment].depth = "off"` skips environment collection and returns a minimal disabled marker consistent with other disabled collectors; setting `[capture.environment].mode = "allowlist"` captures only variables matching the configured allowlist (never dumping all environment variables).
  - Execution state: pending

- [ ] E-03 Fix `capture.git.get_git`, `capture.host.get_host`, `capture.process.get_process`, and `capture.python_runtime.get_python_runtime` to honor `[capture.<section>].depth = "off"`.
  - Depends on: none
  - Expected outcome: Each collector checks its section's `depth` setting at entry and returns an empty/disabled result without invoking subprocesses (`git`, etc.) or collecting metadata when `depth == "off"`.
  - Execution state: pending

### Task group 3: Regression test suite

- [ ] E-04 Add regression tests in `tests/test_config_capture_modes.py` and verify the full `pytest` suite passes.
  - Depends on: E-01, E-02, E-03
  - Expected outcome: `tests/test_config_capture_modes.py` verifies `XDG_CONFIG_HOME=""`, non-mutated caller override dicts, `_config_boot` global/local config discovery + `PUBRUN_AUTO_START` values, `environment` allowlist mode, and `depth = "off"` across all five collectors, and `pytest -q` passes with zero regressions.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `_config_boot.py` must stay lightweight (stdlib only, no heavy imports) because it runs at `import pubrun` time; keep config parsing minimal using `tomllib`/`tomli` fallback already present in `_config_boot.py`.
- `config.resolve_config` defines the canonical config file search order: user global config (`$XDG_CONFIG_HOME/pubrun/config.toml` or `~/.config/pubrun/config.toml`), project `.config/pubrun/config.toml`, `.pubrun.toml`, and `pyproject.toml`.

## Findings

| Bug ID | Severity | Remediation Risk | Location (symbol) | Defect |
|---|---|---|---|---|
| `BUG-39` | Medium | Low | `capture.environment.get_environment`, `capture.git.get_git`, `capture.host.get_host`, `capture.process.get_process`, `capture.python_runtime.get_python_runtime` | Documented `[capture.environment].mode = "allowlist"` and `[capture.*].depth = "off"` settings are silently ignored, leaking unrequested env vars or executing disabled collectors. |
| `BUG-40` | Medium | Low | `_config_boot.load_boot_config` (module-level boot helpers) | Ignores `~/.config/pubrun/config.toml` and `./.config/pubrun/config.toml` for `[imports]`/`[core].auto_start`, and ignores `PUBRUN_AUTO_START=0`/`1`/`no`/`yes`. |
| `BUG-63` | Low | Low | `config.resolve_config`, `config._user_config_path` | Empty `XDG_CONFIG_HOME=""` resolves to relative `./pubrun`; shallow copy mutates caller's nested `"core"` dict in place. |

## Proposed changes (ordered, validatable)

1. In `src/pubrun/config.py`: treat empty/whitespace `XDG_CONFIG_HOME` as unset (`os.environ.get("XDG_CONFIG_HOME") or ...`), and use `copy.deepcopy(overrides)` before merging/normalizing so caller dictionaries are never mutated.
2. In `src/pubrun/_config_boot.py`: include `~/.config/pubrun/config.toml` (or non-empty `$XDG_CONFIG_HOME/pubrun/config.toml`) and `./.config/pubrun/config.toml` in the boot config chain, and parse `PUBRUN_AUTO_START` booleans consistently (`"1"`, `"true"`, `"yes"`, `"on"` vs `"0"`, `"false"`, `"no"`, `"off"`).
3. In `src/pubrun/capture/environment.py`: enforce `depth == "off"` early return and `mode == "allowlist"` filtering against configured allowlist keys/patterns.
4. In `src/pubrun/capture/git.py`, `src/pubrun/capture/host.py`, `src/pubrun/capture/process.py`, and `src/pubrun/capture/python_runtime.py`: add early return when `depth == "off"` before collecting host/git/process/runtime data.
5. Add `tests/test_config_capture_modes.py` exercising all scenarios.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none.
- Under-scope: none.

## Required tests / validation

- Run `pytest tests/test_config_capture_modes.py -v` and paste actual output.
- Run full `pytest -q` and paste actual output confirming zero regressions.

## Spec / documentation sync

N/A: these configuration keys (`mode = "allowlist"`, `depth = "off"`, `XDG_CONFIG_HOME`, `PUBRUN_AUTO_START`) are already documented; this plan fixes implementation conformance.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `pytest tests/test_config_capture_modes.py -v` output confirming `XDG_CONFIG_HOME=""` resolves under home, `resolve_config(overrides)` leaves `overrides` unmodified, and `_config_boot` honors `~/.config/pubrun/config.toml`, `./.config/pubrun/config.toml`, and `PUBRUN_AUTO_START=0/1/no/yes`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `pytest tests/test_config_capture_modes.py -v` output confirming `get_environment` returns only allowlisted variables when `mode = "allowlist"` and skips capture when `depth = "off"`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `pytest tests/test_config_capture_modes.py -v` output confirming `get_git`, `get_host`, `get_process`, and `get_python_runtime` each skip collection (and `get_git` invokes no subprocess) when configured with `depth = "off"`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted full `pytest -q` output showing `tests/test_config_capture_modes.py` and the full test suite pass with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Wait for human approval (`- Status: approved`) before executing. Commit only files listed in `Scope-Paths` via `aw commit l7ko8p -- src/pubrun/_config_boot.py src/pubrun/config.py src/pubrun/capture/environment.py src/pubrun/capture/git.py src/pubrun/capture/host.py src/pubrun/capture/process.py src/pubrun/capture/python_runtime.py tests/test_config_capture_modes.py`, then move this plan to `.aw/records/plans/executed/` through the post-gate lifecycle transition.
