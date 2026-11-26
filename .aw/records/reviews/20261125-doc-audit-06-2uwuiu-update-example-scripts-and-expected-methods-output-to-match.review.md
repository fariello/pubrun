# Review findings: ipd 2uwuiu

- Subject-Id: 2uwuiu
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Gemini 4 Neon (Antigravity)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete plan text against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 through 12 and spec Section 11.1 citation forms. No pre-review snapshot was needed: the lane working tree was clean and the plan was already committed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) before any edit. Requirement 12: no diagram is needed because the plan edits existing example scripts and one short sample Markdown file with no new multi-entity data model, branch, loop, or status lifecycle (Requirement 12(c)); this rationale is now stated in `## Scope check`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Front matter (`- Scope-Paths:`, `- Concern:`, `- Short-Description:`), Approval gate | Broad `- Scope-Paths: examples/` covering 18 files (8 untouched); omitted `PUBRUN_AUTO_START` and `11_cli_report.py` docstring drift in Concern; `- Cohesion rationale: not required` | Lists exact 10 modified files in `- Scope-Paths:`, adds explicit cohesion rationale (10 tiny files in one example-suite deliverable, ~50 lines total diff), and aligns Concern and Short-Description | Precise scope fence and accurate concern summary (PR-004, PR-006). |
| E-01, E-02 | Hedged `PUBRUN_AUTO_START` replacement ("where appropriate", "where compatible with `tests/test_examples_smoke.py`"), omitted `10_hardware_probe.py` from `pubrun.noauto` switch, omitted removing unused `import os` in `09`/`11`, and omitted updating `11_cli_report.py`'s docstring | Deterministic instructions across all 9 targeted scripts (`01`-`05`, `08`-`11`) verified against `src/pubrun/noauto.py`, `src/pubrun/core.py::_is_pubrun_cli_invocation`, and `tests/test_examples_smoke.py`; drops unused `import os` in `09`/`11` and updates `11_cli_report.py`'s docstring | Removes hedging and prevents stale docstring or unused imports (PR-001, PR-002). |
| E-03 | Did not specify exact `generate_report` details (`Cpython`, `Standard library dependencies were utilized.`, 8-char Git commit, `References` line) or clarify that `test_example_minimal_research_workflow.py` tests `analysis.py`; omitted `--no-cov` and `-p no:cacheprovider` | Specifies exact `MARKDOWN_TEMPLATE`/`generate_report` structure for `analysis.py`, requires redacted placeholders, aligns pytest command with Required tests (`--no-cov -p no:cacheprovider`), and lists all validation steps | Accurate template mirror and consistent verification command (PR-002, PR-003). |
| Required tests / validation, V-01..V-03 | Omitted runtime zero-`profile_deprecated` manifest check, omitted orchestrator-mandated relative/anchor Markdown link check, omitted runnable zero-dash script, and lacked negative `grep` baselines | Embeds runnable Python checks for zero dashes, relative/anchor links, and runtime zero-`profile_deprecated` manifest notices; adds negative `grep` checks with verified pre-execution baselines across V-01..V-03 | Proves Goal/E-01 runtime claim and satisfies orchestrator `86cd17` Cross-IPD validation (PR-003). |
| Approval and execution gate items 1-5 | Stop-style "modify only files under `examples/`" fence; omitted no-blocking-questions note and never-claim-without-output clause; vague `examples/...` commit paths; did not forbid hand-run `git mv` or distinguish runner vs executor finalize ownership | Rewrote items 1 to 5 to match the repository execution contract and sibling plans in Set `doc-audit` | Conformance with execution contract and maintainer scope-fence ruling (PR-005). |
| Project conventions, Findings, Deferred, Scope check, Spec / documentation sync | Bare file-path citations; `Deferred: None.`; omitted sibling Set `doc-audit` owners, disjointness confirmation, fallback principles note, and Requirement 12 rationale | Added Section 11.1 symbol-anchored citations, explicit deferred notes (`06`/`07`/`12` `PUBRUN_AUTO_START`, `11_cli_report.py` filename retention, repo-wide dash sweep), sibling ownership and disjointness, fallback principles, and Requirement 12 rationale | Cross-plan traceability and technical writing compliance (PR-006). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (broad `examples/` tightened to exact 10 files under `examples/`), 3 E-items in 2 task groups, `- Kind: child`, and Set `doc-audit` sibling Scope-Paths.

1. No: edits only example scripts under `examples/` and sample Markdown `examples/minimal-research-workflow/expected_methods.md`. No spec, runtime API, CLI option, config key, or manifest schema changes.
2. No: touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 3 small E-items across 2 task groups touching 10 tiny files (all part of the example suite, total diff under ~50 lines).
4. Partially at review start (`- Scope-Paths: examples/` covered 18 files including 8 untouched files); tightened during review to the exact 10 modified files.
5. No: example scripts and sample Markdown are trivially reversible via `git revert`, and regressions are caught immediately by `examples/verify_all.py` and `tests/test_examples_smoke.py`.

AW-TIER: standard

### Step R1

- Checked every material citation against live repository code, scripts, and tests:
  - `examples/01_minimal_start_stop.py` through `examples/12_external_file_provenance.py`: confirmed exactly 8 scripts (`01`, `02`, `03` x2, `04`, `05`, `08` x2, `09`, `11`; 10 total calls) pass `profile=`, all 12 non-auto-start scripts (`01`-`12`) set `os.environ["PUBRUN_AUTO_START"] = "false"`, `09_cli_methods.py` and `11_cli_report.py` import `os` solely for that env var, `10_hardware_probe.py:2,4` docstring says "Hardware capture with deep profile" / "deep-profile run", and `11_cli_report.py:4,20` cites and invokes `pubrun report`.
  - `src/pubrun/config.py::profile_deprecation_notice` (lines 240-264) and `src/pubrun/resources/default.toml` (lines 21-27): confirms `core.profile` is deprecated and inert, emitting `profile_deprecated` notice in `manifest["config"]["notices"]` for any non-empty value other than `"default"`.
  - `src/pubrun/noauto.py` (lines 1-81): confirms `import pubrun.noauto as pubrun` exports `start`, `stop`, `tracked_run`, `audit_run`, `annotate`, `phase`, `diff`, `get_current_run`, and populates the parent `pubrun` module namespace so `from pubrun.tracker import get_current_run` in `03_audit_decorator.py` also works unchanged.
  - `src/pubrun/_config_boot.py::resolve_import_mode` (lines 11, 173-176): confirms `PUBRUN_AUTO_START` is a legacy alias.
  - `src/pubrun/core.py::_is_pubrun_cli_invocation` and `_execute_boot_sequence` (lines 619-696): confirms `python -m pubrun ...` CLI subprocesses (as used in `09_cli_methods.py` and `11_cli_report.py`) suppress auto-start automatically without `PUBRUN_AUTO_START="false"`.
  - `src/pubrun/__main__.py::main` (lines 3058-3074, 3129-3148, 3177-3180, 3218-3241) and `src/pubrun/report/diagnostics.py` (lines 642-650): confirms `show` is primary, `report` is a hidden legacy alias (`help=argparse.SUPPRESS`), and both emit `PUBRUN DIAGNOSTICS` and `Run ID`.
  - `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE` (lines 17-28) and `src/pubrun/report/methods.py::generate_report` (lines 174-285): confirmed exact rendered structure (`### Computational Methods`, OS/CPU/RAM, `Python <version> (Cpython)` via `python_impl.capitalize()`, `Standard library dependencies were utilized.` for stdlib-only `analysis.py`, 8-char Git commit, `pubrun v<version>` [1], and `**References:**`).
  - `examples/minimal-research-workflow/expected_methods.md` (lines 1-17) and `examples/minimal-research-workflow/analysis.py` (lines 1-263): confirmed line 5 contains divergent freeform prose ("synthetic dataset generated with a fixed random seed").
  - `examples/verify_all.py::main` (lines 17-103), `tests/test_examples_smoke.py::test_example_runs_and_creates_manifest` (lines 16-54), and `tests/test_example_minimal_research_workflow.py` (lines 18-135): confirmed `test_examples_smoke.py` asserts only `returncode == 0`, `"[PASS]" in stdout`, and `runs/*/manifest.json`; `test_example_minimal_research_workflow.py` tests `analysis.py` only.
  - Verified pre-execution baselines: `grep -rn "profile="` -> 10 matches (`exit=0`), `grep -rn "PUBRUN_AUTO_START"` on 9 files -> 9 matches (`exit=0`), `deep profile|deep-profile` in `10_hardware_probe.py` -> 2 matches (`exit=0`), `"report"` in `11_cli_report.py` -> 1 match (`exit=0`), `"fixed random seed"` in `expected_methods.md` -> 1 match (`exit=0`), link check -> `broken=0`, `python3 scripts/sanitize_paths.py --check --all` -> `exit=0`, `pytest --collect-only` -> 16 tests collected.
- Drift found: PR-001, PR-002, PR-003, PR-004, PR-005, PR-006.

### Step R2

- Checked: E/V bijection (3 E-items and 3 V-items; `Highest E allocated: 03`); `- Scope-Paths:` tightened from broad `examples/` to the exact 10 modified files, strictly disjoint from all five Set `doc-audit` siblings (`0cjiv5`, `pqcx6o`, `dd7noz`, `wjsccu`, `77pdvl`) and orchestrator `86cd17`; `- Item-Dependencies: none`; intra-plan dependency `E-01, E-02 -> E-03`; concrete, runnable, falsifiable commands with verified pre-execution baselines in every V-item; no hardcoded counts of mutable record trees; runtime-demonstration reachability verified (Required tests item 4 executes the 9 example scripts in a temp dir via `src/pubrun/config.py::profile_deprecation_notice` and `src/pubrun/tracker.py` to observe `manifest["config"]["notices"]`, reachable by construction after E-01 and E-02).

### Step R3

- Checked: the plan modifies no security, auth, redaction, commit, worktree, or sandbox code. Verified that `expected_methods.md` must use redacted/placeholder machine details (no machine-local paths or hostnames) and `V-03` gates on `python3 scripts/sanitize_paths.py --check --all` exiting 0 (verified baseline `exit=0`).

### Step R4

- Checked: rubric A through F, right-sizing, and spec/documentation sync.
- Right-sizing: 3 E-items in 2 task groups (E-01: mechanical edits to `01`-`05`; E-02: mechanical edits + docstrings/`show` in `08`-`11`; E-03: 17-line `expected_methods.md` rewrite + whole-example verification). Total diff is ~50 lines across tiny scripts; cohesion rationale is recorded for the 10 explicit Scope-Paths.
- Test coverage: `examples/verify_all.py`, `tests/test_examples_smoke.py`, `tests/test_example_minimal_research_workflow.py`, runtime zero-`profile_deprecated` manifest notice check, negative greps, zero-dash check, relative/anchor link check, and `scripts/sanitize_paths.py --check --all`.
- Spec and documentation sync names all five sibling owners in Set `doc-audit` and explicitly documents why `06`/`07`/`12` `PUBRUN_AUTO_START` and `11_cli_report.py`'s filename remain unchanged.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | completeness | `examples/01_minimal_start_stop.py:7`..`examples/11_cli_report.py:8`; `src/pubrun/noauto.py`; `src/pubrun/core.py::_is_pubrun_cli_invocation:619-649`; `tests/test_examples_smoke.py:21-54` | E-01 and E-02 hedged replacing `PUBRUN_AUTO_START="false"` with `import pubrun.noauto as pubrun` ("where appropriate", "where compatible with `tests/test_examples_smoke.py`"), omitted `10_hardware_probe.py` from the switch, and omitted removing now-unused `import os` in `09_cli_methods.py` and `11_cli_report.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified `pubrun.noauto`, `_is_pubrun_cli_invocation`, and `test_examples_smoke.py`; replaced hedging with deterministic instructions across all 9 targeted scripts (`01`-`05`, `08`-`11`) and explicit removal of unused `import os` in `09` and `11`. |
| PR-002 | MEDIUM | IN-SCOPE | accuracy | `examples/11_cli_report.py:2-6,20`; `examples/minimal-research-workflow/expected_methods.md:5`; `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE:17-28`; `src/pubrun/report/methods.py::generate_report:174-265`; `tests/test_example_minimal_research_workflow.py:18-135` | E-02 omitted updating `11_cli_report.py`'s docstring (which names `pubrun report`) and hedged on `show` compatibility; E-03 omitted exact `generate_report` details (`Cpython`, `Standard library dependencies were utilized.`, 8-char Git commit, `**References:**`) and implied `test_example_minimal_research_workflow.py` reads `expected_methods.md`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated E-02 to align both code and docstring in `11_cli_report.py` with `pubrun show` (retaining filename and assertions) and expanded E-03 and Project conventions with verified `MARKDOWN_TEMPLATE`/`generate_report` details and accurate test coverage description. |
| PR-003 | MEDIUM | UNDER-SCOPE | evidence | Pre-review Goal, E-01, Required tests, V-01..V-03; orchestrator `86cd17` `## Cross-IPD validation` | Plan claimed zero `profile_deprecated` manifest notices in Goal and E-01 without any runtime check inspecting `manifest["config"]["notices"]`; omitted orchestrator-mandated relative/anchor Markdown link check and runnable zero-dash script; omitted pre-execution `grep` baselines; pytest flags differed between E-03 and V-03. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Embedded runnable Python scripts for zero dashes, relative/anchor links, and runtime zero-`profile_deprecated` manifest notices in `## Required tests / validation`; added negative `grep` checks with verified pre-execution baselines and unified pytest flags (`-v --no-cov -p no:cacheprovider`) across E-03, Required tests, and V-01..V-03. |
| PR-004 | MEDIUM | IN-SCOPE | scope | Pre-review `- Scope-Paths: examples/` (line 7) vs `examples/` (18 files, 8 untouched) | Broad directory `- Scope-Paths: examples/` covered 8 untouched files (`00`, `06`, `07`, `12`, `verify_all.py`, `analysis.py`, `README.md`, `manifest_excerpt.json`), weakening the scope fence compared to all five Set `doc-audit` siblings. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Tightened `- Scope-Paths:` to the exact 10 modified files and added a cohesion rationale in `## Approval and execution gate`. |
| PR-005 | MEDIUM | IN-SCOPE | execution contract | Pre-review `## Approval and execution gate` items 1-5 | Item 1 omitted confirming no blocking open questions; item 2 used stop-style "modify only" wording instead of scope-declaration wording (`--scope-reason`/`--scope-ack`); item 3 omitted the never-claim-without-output clause; item 4 used vague `examples/...` and omitted `-a`; item 5 did not forbid hand-run `git mv` or cleanly separate runner vs executor finalize ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote items 1 to 5 to match the repository execution contract and sibling plans in Set `doc-audit`. |
| PR-006 | LOW | IN-SCOPE | coordination | Pre-review `## Project conventions`, `## Findings`, `## Deferred / out of scope`, `## Scope check`, `## Spec / documentation sync` | Used bare file-path citations without symbols; omitted sibling Set `doc-audit` owners, disjointness confirmation, fallback principles note, Requirement 12 diagram rationale, and explicit out-of-scope notes (`06`/`07`/`12` `PUBRUN_AUTO_START`, `11_cli_report.py` filename retention, repo-wide dash sweep). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added Section 11.1 symbol citations, explicit deferred notes, fallback principles note, sibling Set ownership/disjointness, and Requirement 12(c) rationale. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` (rejected: broad `- Scope-Paths:` at start, 10 files across 2 task groups, runtime notice verification gap, and execution-contract fixes); `complex` (rejected: no runtime code, schema, or contract changes) | Step T answers | yes |
| D-2 | Should `examples/06_subprocess_spy.py`, `07_file_capture.py`, and `12_external_file_provenance.py` also be switched from `PUBRUN_AUTO_START="false"` to `pubrun.noauto`? | Keep `06`, `07`, and `12` out of scope and document the deferral explicitly | Widen scope to 13 files (rejected: those three scripts do not pass `profile=`, `PUBRUN_AUTO_START` remains a supported legacy alias, and orchestrator `86cd17` explicitly scopes `2uwuiu` to the 10 `/assess-documentation` files) | Orchestrator `86cd17` `## Child IPDs`, `src/pubrun/_config_boot.py::resolve_import_mode` | yes |
| D-3 | Should `examples/11_cli_report.py` be renamed to `11_cli_show.py` when switching its subprocess call to `pubrun show`? | Keep the filename `examples/11_cli_report.py` unchanged and update its code and docstring to `pubrun show` (noting `report` as a hidden legacy alias) | Rename to `11_cli_show.py` (rejected: `docs/research-use.md` and sibling plan `wjsccu` reference `11_cli_report.py`) | `docs/research-use.md:45`, Set `doc-audit` sibling `wjsccu` | yes |

### Step S5

- Checked: `## Open questions` is `None.` Repository evidence settled every finding and decision (D-1 through D-3). Every finding (PR-001 through PR-006) is `FIXED`, so no finding requires escalation and no open question is added. Every decision is reversible (`Reversible: yes`). The lane outcome JSON carries `questions: []`.

### Step S6

- Checked: Round 1 tightened `- Scope-Paths:` from `examples/` to the exact 10 modified files, so Rule 1 required a second verification pass. Re-read the entire revised plan and verified:
  - All 10 declared `- Scope-Paths:` match `## Scope`, E-01 (`01`-`05`), E-02 (`08`-`11`), E-03 (`expected_methods.md`), `## Approval and execution gate` items 2 and 4, and V-01..V-03 consistently.
  - Every hedged phrase (`where appropriate`, `where compatible`, `or keeping compatibility`) was swept across Concern, Goal, E-items, Findings, Proposed changes, Scope check, Required tests, and V-items.
  - All embedded validation commands (negative greps, zero-dash check, link/anchor check, runtime notice check, `verify_all.py`, pytest, `sanitize_paths.py`) were checked for syntax, reachability, and baseline behavior.
  - `aw ipd lint --phase review-finalize --agent` exits `0` (0 errors, 0 warnings; advisory `IPD-Z603` info for 10 explicit Scope-Paths addressed by `- Cohesion rationale:`).

AW-REVIEW: DONE
