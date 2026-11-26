# Review findings: ipd ha769g

- Subject-Id: ha769g
- Subject-Type: ipd
- Reviewed-At: 2026-11-26
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261126-mz0erz-01-ha769g-remove-deprecated-profile-examples-from-src-pubrun.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules, plus `src/pubrun/__init__.py`, `src/pubrun/core.py`, `src/pubrun/resources/default.toml`, `src/pubrun/config.py`, `src/pubrun/_config_boot.py`, `src/pubrun/capture/hardware.py`, `src/pubrun/capture/packages.py`, `docs/configuration.md`, `docs/api.md`, `examples/10_hardware_probe.py`, `pyproject.toml`, `tests/test_config.py`, `tests/test_profile_deprecation.py`, `tests/test_cli.py`, and graduated backlog item `.aw/records/backlog/graduated/20261125-mz0erz-01-mz0erz-remove-deprecated-profile-examples-from-src-pubrun.backlog.md` (`mz0erz`). No pre-review snapshot was needed because the lane working tree was clean. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) and `aw ipd lint --phase author --citation-anchors --detail` reported `conforming` (exit `0`). Every cited symbol, path, quoted line, and environment variable matches repository evidence; requirement 12(a) Mermaid `classDiagram` uses exact file paths and symbol names matching the prose; acronyms (`API`, `TOML`) are expanded on first use; all proposed replacement docstring and comment strings contain no em or en dashes.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Required tests / validation` item 3 | `resolve_config(overrides)` called without clearing `PUBRUN_PROFILE` or stubbing `load_user_config` and `load_local_config` | Cleared `PUBRUN_PROFILE=` and stubbed `cfg.load_user_config` and `cfg.load_local_config` to `lambda ...: None` before calling `cfg.resolve_config(overrides)` | Prevents ambient host config or `PUBRUN_PROFILE` from causing spurious validation failures (`PR-002`) |
| `## Approval and execution gate` | Single paragraph unconditionally instructing the executing agent to run `aw ipd finalize` and omitting open-question precondition, `--scope-reason`/`--scope-ack`, and explicit no-`git add -A`/honesty wording | Structured five-clause execution contract with conditional runner vs non-runner `aw ipd finalize ha769g` ownership | Satisfies execution-contract requirements in `s7-finalize.md` and `r2-executability.md` (`PR-001`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/__init__.py, src/pubrun/core.py, src/pubrun/resources/default.toml`), 4 E-items in 3 task groups, `- Kind: child`.

1. No: updates only Python docstrings in `src/pubrun/__init__.py` and `src/pubrun/core.py` and header comments in `src/pubrun/resources/default.toml`; changes no executable code, CLI option, output format, file format, or TOML configuration key or value (`[core].profile = "default"` and its deprecation notice stay unchanged).
2. No: touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox; no executable lines change.
3. No: 4 small E-items across 3 related files for a single narrow docstring/comment cleanup chore (`mz0erz`).
4. Yes: `src/pubrun/__init__.py, src/pubrun/core.py, src/pubrun/resources/default.toml`.
5. No: docstring and comment edits only; cannot lose data or break existing behavior, any accidental TOML/Python syntax error is caught immediately by `load_default_config()`, `pytest`, and `mypy`, and the change is trivially reversible.

AW-TIER: simple

### Step Q

- Checked: every occurrence of `profile=`, `PUBRUN_PROFILE`, and `master profile` across `src/pubrun/` (confirmed all 8 baseline matches across the three target files and verified that `src/pubrun/core.py::_inactive_policy`, `src/pubrun/config.py::_resolve_layers`, `src/pubrun/config.py::resolve_config`, `src/pubrun/config.py::profile_deprecation_notice`, `src/pubrun/tracker.py`, `src/pubrun/status.py`, `src/pubrun/tui/widgets/config.py`, and `src/pubrun/report/diagnostics.py` are runtime/internal references rightly kept unchanged); verified that no test reads the `Resolution Order` or `[capture]` header comments in `default.toml`; verified that `PUBRUN_IMPORT_MODE="noauto"` and `PUBRUN_META_REF="path.json"` are canonical non-deprecated environment variables in `src/pubrun/_config_boot.py::resolve_import_mode` and `src/pubrun/config.py::_resolve_layers`; verified that `capture={"hardware": {"depth": "deep"}}`, `capture={"hardware": {"depth": "basic"}}`, and `capture={"packages": {"mode": "off"}}` are valid non-deprecated overrides consistent with `examples/10_hardware_probe.py` and `docs/configuration.md`; verified all six test files, `scripts/sanitize_paths.py`, `pytest`, and `mypy` exist and are runnable; checked validation snippet determinism (`PR-002`) and the execution gate contract (`PR-001`).
- Confirmed: after fixing `PR-001` (conditional runner/executor `aw ipd finalize` ownership and complete five-clause execution contract) and `PR-002` (isolating validation snippet 3 from ambient `PUBRUN_PROFILE` and host config files), all `E-*`/`V-*` items align 1:1 with non-vacuous, deterministic verification commands and zero runtime-behavior risk.

### Step S5

- Checked: `## Open questions` contains `None.`. Both findings (`PR-001`, `PR-002`) had `Low` remediation risk and were fixed in place from repository policy and code evidence, leaving zero open or deferred findings and zero unresolved human decisions. The lane outcome JSON carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | `s7-finalize.md` / `r2-executability.md` (Execution contract) | `.aw/records/plans/pending/20261126-mz0erz-01-ha769g-remove-deprecated-profile-examples-from-src-pubrun.ipd.md:234` (`## Approval and execution gate`) | The gate unconditionally instructed the executing agent to run `aw ipd finalize` instead of stating conditional runner/executor ownership, and omitted the open-question precondition, `--scope-reason`/`--scope-ack` scope declaration, explicit no-`git add -A`/raw `git commit` rule, and explicit no-`pass`-without-output honesty rule. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the gate paragraph with the complete five-clause execution contract stating conditional runner (`aw oc run`/`aw agy run`) vs non-runner `aw ipd finalize ha769g` ownership, scope declaration (`--scope-reason`/`--scope-ack`), validation honesty, and commit discipline (recommendation strength: `strong`). |
| PR-002 | MEDIUM | IN-SCOPE | `q-quick-risk.md` / `r4-engineering.md` E (Validation determinism) | `.aw/records/plans/pending/20261126-mz0erz-01-ha769g-remove-deprecated-profile-examples-from-src-pubrun.ipd.md:155-176` (`## Required tests / validation` item 3) vs `src/pubrun/config.py::_resolve_layers:148-167` | Validation snippet 3 invoked `resolve_config(overrides)` without clearing `PUBRUN_PROFILE` or stubbing `load_user_config` and `load_local_config`, so an ambient `PUBRUN_PROFILE` or host user/local config setting a non-default `core.profile` would cause `assert profile_deprecation_notice(resolved) is None` to fail spuriously. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated validation item 3 to unset `PUBRUN_PROFILE=` and stub `cfg.load_user_config` and `cfg.load_local_config` to return `None`, matching `tests/test_profile_deprecation.py::TestProfileDoesNotGateCapture.test_minimal_and_deep_profiles_capture_identically` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `simple` | `standard` | Docstring and TOML comment edits only across 3 declared files (`Scope-Paths` listed), 4 small E-items, zero executable code or config key/value changes; all risk questions in `steps/t-tier.md` answered No. | yes |
| D-2 | How to isolate validation snippet 3 from ambient host config | Clear `PUBRUN_PROFILE=` and stub `cfg.load_user_config` and `cfg.load_local_config` to return `None` | Leave `resolve_config(overrides)` unisolated or run in a temporary `HOME`/`cwd` | `src/pubrun/config.py::_resolve_layers:148-167` and `tests/test_profile_deprecation.py::TestProfileDoesNotGateCapture.test_minimal_and_deep_profiles_capture_identically:28-30` | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; the two in-place revisions (`PR-001` gate contract, `PR-002` validation snippet isolation) were swept against `E-04` and `V-04` and introduce no new questions, findings, or ambiguities. No second pass is needed.

AW-REVIEW: DONE
