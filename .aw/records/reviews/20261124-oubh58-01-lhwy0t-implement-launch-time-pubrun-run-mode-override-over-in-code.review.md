# Review findings: ipd lhwy0t

- Subject-Id: lhwy0t
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-oubh58-01-lhwy0t-implement-launch-time-pubrun-run-mode-override-over-in-code.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md` Section 11.1 code citation rules, plus `src/pubrun/__main__.py` (`run_parser` and `elif args.command == "run":`), `src/pubrun/_bootstrap.py` (`select_mode`, `is_mode_submodule_import_in_progress`), `src/pubrun/_modes.py` (`MODES`, `VALID_MODES`, `get_mode_behavior`), `src/pubrun/core.py` (`_execute_boot_sequence`), `src/pubrun/full.py`, `src/pubrun/minimal.py`, `schemas/manifest.schema.json` (`properties.pubrun_imports`), `pyproject.toml` (`[[tool.mypy.overrides]]`), `tests/test_import_modes.py`, `tests/test_full_mode.py`, `CHANGELOG.md`, `docs/manifest.md`, `docs/cli.md`, `docs/functional_spec.md`, `.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md`, and `.aw/records/backlog/graduated/20261124-oubh58-01-oubh58-resolve-run-mode-vs-in-code-import-precedence-clai.backlog.md`. No pre-review snapshot was needed: lane `HEAD` `23fdc02` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(b), (d), and (e) are satisfied by the Mermaid flowchart in `## Findings` (updated to match E-02's subsequent-import rule).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Scope`, `- Scope-Paths:`, `E-04`, `Proposed changes` item 4, `Scope check`, `Spec / documentation sync`, `V-04`, Gate item 2 | Scoped doc updates to `CHANGELOG.md` only and claimed no other doc files needed sync | Added `docs/manifest.md`, `docs/cli.md`, and `docs/functional_spec.md` to sync `"cli:pubrun run --mode"` and `PUBRUN_RUN_MODE_OVERRIDE`, specified the top-most `### Fixed` under `## [Unreleased]`, and added a portable exit-0 Python zero-dash check on `git diff` | New manifest `selected_source`/`selected_by` value and CLI override env var contradicted `docs/manifest.md`, `docs/cli.md`, and `docs/functional_spec.md` (PR-001, PR-005). |
| `E-02`, `Findings` flowchart, `Proposed changes` item 2, `V-02` | Handled `PUBRUN_RUN_MODE_OVERRIDE` only when `_selected_mode is None` without distinguishing `cli_behavior` from caller `behavior` or handling subsequent imports under `"cli:pubrun run --mode"` | Explicitly specified `cli_behavior = get_mode_behavior(cli_mode)`, `import os`, and non-conflicting recording on subsequent imports when `_selected_source == "cli:pubrun run --mode"`, and synced the flowchart label | Prevents returning caller `behavior` instead of `cli_behavior` and prevents spurious conflict errors when `import pubrun` precedes `import pubrun.full` under `pubrun run --mode` (PR-002). |
| `Project conventions discovered`, `Required tests / validation`, `V-01`, `V-02` | Claimed `python3 -m mypy` validated `src/pubrun/_bootstrap.py` without noting `pyproject.toml` `ignore_errors = true`, and omitted `mypy` from `V-01` | Documented `pyproject.toml`'s `ignore_errors = true` on `pubrun._bootstrap`, added `python3 -m mypy` to `V-01` (`__main__.py` is checked), and added unit-test verification (`-k "Bootstrap or Conflict"`) to `V-02` | Honest type-check evidence and direct unit validation of `select_mode` (PR-003). |
| `E-03`, `Proposed changes` item 3, `V-03` | Omitted tests for `PUBRUN_RUN_MODE_OVERRIDE` env presence (`P3-R1`), invalid override fallback, subsequent non-conflicting imports, and `clean_bootstrap` isolation | Added test requirements (a), (f), (g) and named `clean_bootstrap` plus all child-env sanitization sites in `tests/test_import_modes.py` and `tests/test_full_mode.py` | Covers promised E-01/E-02 behavior and prevents host env leakage into unit and subprocess tests (PR-004). |
| `Project conventions discovered` | Cited `20260705-1828-01-full-capture-mode.md`, `tests/test_import_modes.py`, and `src/pubrun/tracker.py` without Section 11.1 anchors | Applied exact `#Design decisions (resolved in discussion 2026-07-05)`, `::TestPubrunRunCommand.test_run_sets_import_mode_env_var`, and `::Run` anchors | Section 11.1 citation compliance (PR-005). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (originally 5 files, expanded to 8 files including `src/pubrun/__main__.py`, `src/pubrun/_bootstrap.py`, `docs/manifest.md`, `docs/cli.md`, `docs/functional_spec.md`), 4 E-items in 2 task groups, `- Kind: child`.

1. Yes: changes the public CLI launch-time override contract (`pubrun run --mode <mode>` vs. in-code `import pubrun.<mode>`), introduces `PUBRUN_RUN_MODE_OVERRIDE`, and emits a new `"cli:pubrun run --mode"` value in manifest `pubrun_imports.selected_source` and `selected_by`.
2. No: touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 4 focused E-items across 2 task groups in 8 tightly related files (within `IPD-Z603` guidance).
4. Yes: all modified paths are declared in `- Scope-Paths:`.
5. Yes (bounded): a mistake in `src/pubrun/_bootstrap.py::select_mode` could break import-mode precedence or conflict detection across all six mode submodules and root `import pubrun`, though it cannot lose data and is reversible.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/__main__.py:3045-3054` (`run_parser`, `--mode` choices), `src/pubrun/__main__.py:3440-3476` (`elif args.command == "run":`, `child_env`), `src/pubrun/_bootstrap.py:9-15,172-254` (`select_mode`, missing top-level `import os`), `src/pubrun/_modes.py:19-68` (`MODES`, `VALID_MODES`), `src/pubrun/core.py:645-689` (`_execute_boot_sequence`), `src/pubrun/full.py:16-55`, `src/pubrun/minimal.py:19-48`, `schemas/manifest.schema.json:111-170` (`properties.pubrun_imports`), `pyproject.toml:115-141` (`[[tool.mypy.overrides]]` listing `pubrun._bootstrap` under `ignore_errors = true`), `tests/test_import_modes.py` (`clean_bootstrap` line 233, `TestPubrunRunCommand.test_run_sets_import_mode_env_var` line 483, env helpers at lines 208, 547-644, 794, 825, 1035), `tests/test_full_mode.py` (env helpers at lines 96, 132, 208, 235, 254, 272), `docs/manifest.md:521-549`, `docs/cli.md:731-756`, `docs/functional_spec.md:543-557`, `CHANGELOG.md:9-125`, `.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md:31-48`, and backlog item `oubh58`.
- Confirmed: baseline `python3 -m pytest tests/test_import_modes.py -k "run" -v --no-cov -p no:cacheprovider` passed (`26 passed, 52 deselected in 9.24s`); `schemas/manifest.schema.json` allows any string for `selected_by` and `selected_source`; `docs/api.md:45`, `docs/configuration.md:81,98`, `docs/functional_spec.md:129`, `README.md:153`, and `src/pubrun/full.py:16` already document launch-time `pubrun run --mode` overriding in-code imports.
- PR-001 (doc sync contradiction): `docs/manifest.md:529-530` enumerates `selected_source` values without `"cli:pubrun run --mode"`, and `docs/cli.md:733` and `docs/functional_spec.md:545,551` state `pubrun run` sets only `PUBRUN_IMPORT_MODE`. Fixed by adding those three files to `- Scope-Paths:`, `E-04`, `Spec / documentation sync`, `V-04`, and Gate item 2.
- PR-003 (`mypy` scope): `pyproject.toml:119` lists `"pubrun._bootstrap"` under `ignore_errors = true`, so `python3 -m mypy` checks `src/pubrun/__main__.py` and skips `src/pubrun/_bootstrap.py`. Fixed in `Project conventions discovered`, `Required tests / validation`, `V-01`, and `V-02`.
- PR-005 (citations and `CHANGELOG.md` headings): fixed Section 11.1 anchors and noted the top-most `### Fixed` under `## [Unreleased]`.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-04` to `V-01`..`V-04`), `- Scope-Paths:` completeness (8 paths), `- Item-Dependencies: none`, runtime-demonstration reachability of `V-01`..`V-04` (all grounded in `src/pubrun/__main__.py`, `src/pubrun/_bootstrap.py::select_mode`, and real subprocess tests in `E-03`), re-derivation convention (no hardcoded test counts or mandatory test names as V-item bars), and all five execution-contract items in the gate.
- PR-003, PR-004, PR-001: strengthened `V-01` (`mypy`), `V-02` (direct `Bootstrap or Conflict` unit test run plus honest `ignore_errors` note), `V-03` (invalid override, both env vars, subsequent non-conflicting imports), and `V-04` (portable exit-0 Python zero-dash check across all four edited doc files).

### Step R3

- Checked: all five bullets of Check R3 full form.
  - Identity and authorization: `pubrun run` is a local CLI process wrapper using argv lists (`subprocess.Popen(cmd_args, env=child_env)`, no shell); no auth boundary changes.
  - Secrets and trust-boundary inputs: `PUBRUN_RUN_MODE_OVERRIDE` is validated against the closed 6-entry allowlist `MODES` via `.strip().lower()`; invalid or untrusted values are ignored and never executed, interpolated, or stored as a selected mode. `args.mode` is constrained by `argparse` `choices`.
  - Queries, commands, files, uploads, outbound calls: no new command execution path, shell invocation, file write, or network call.
  - Sensitive data collection, logging, exposure, retention, and errors: `selected_by` and `selected_source` record only the constant string `"cli:pubrun run --mode"`; mode preset names are non-secret configuration values.
  - Privileged bypasses and abuse controls: the CLI override implements the maintainer-approved launch-time operator override (`oubh58` decision 2026-11-25) and preserves `[redaction]` and `[console]` Jupyter and non-TTY safety guards. No security finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (4 single-concern E-items across 2 task groups and 8 Scope-Paths, each executable in one focused pass; no splitting warranted); anti-regression (ordinary `PUBRUN_IMPORT_MODE` still yields to explicit `import pubrun.<mode>`, `PUBRUN_IMPORT_MODE` remains populated in `child_env` for `P3-R1`, and all existing env-sanitization helpers plus `clean_bootstrap` strip `PUBRUN_RUN_MODE_OVERRIDE`); spec and documentation sync (fixed via PR-001).
- PR-002 (correctness in `select_mode`): specified `cli_behavior = get_mode_behavior(cli_mode)` distinct from caller `behavior`, top-level `import os`, and non-conflicting handling for subsequent imports when `_selected_source == "cli:pubrun run --mode"`.
- PR-004 (testing completeness): added coverage for both env vars set by `pubrun run --mode`, invalid `PUBRUN_RUN_MODE_OVERRIDE=bogus`, subsequent overridden imports under `PUBRUN_IMPORT_CONFLICT=error`, and `clean_bootstrap` plus all child-env helper isolation.

### Step S5

- Checked: pre-existing open question `OQ-01` (`- Blocking: yes`, `- Status: resolved`, `- Owner: maintainer`) matches the 2026-11-25 `/askme` decision recorded in backlog item `oubh58`. Every review finding PR-001..PR-005 had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | UNDER-SCOPE | R4 (Spec / documentation sync) | `docs/manifest.md:529-530` (`selected_by`, `selected_source`); `docs/cli.md:733`; `docs/functional_spec.md:545,551`; Plan `Scope check` (line 96), `Spec / documentation sync` (line 107) | E-02 introduces a new manifest provenance value `"cli:pubrun run --mode"` and E-01 introduces `PUBRUN_RUN_MODE_OVERRIDE`, but the plan updated only `CHANGELOG.md`, leaving `docs/manifest.md`'s enumerated `selected_source` list and `docs/cli.md` / `docs/functional_spec.md` `run` descriptions out of sync. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `docs/manifest.md`, `docs/cli.md`, and `docs/functional_spec.md` to `- Scope-Paths:`, `Scope`, `E-04`, `Proposed changes` item 4, `Scope check`, `Spec / documentation sync`, `V-04`, and Gate item 2 (recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R4 A & D (`select_mode` override and subsequent-import semantics) | `src/pubrun/_bootstrap.py:172-254` (`select_mode`); Plan `E-02` (lines 43-45), `Proposed changes` item 2 (line 86) | E-02 handled `PUBRUN_RUN_MODE_OVERRIDE` only when `_selected_mode is None`, did not distinguish `cli_behavior = get_mode_behavior(cli_mode)` from caller `behavior`, and omitted `import os`. If a child under `pubrun run --mode minimal` runs `import pubrun` followed by `import pubrun.full` (or two differing submodule imports) with `PUBRUN_IMPORT_CONFLICT=error`, the second import enters the `_selected_mode is not None` branch and spuriously raises a conflict error. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02`, `Findings` flowchart, `Proposed changes` item 2, and `V-02` to import `os`, compute `cli_behavior = get_mode_behavior(cli_mode)` separately from caller `behavior`, and record subsequent imports as `selected: False, conflict: False` without warning or raising when `_selected_source == "cli:pubrun run --mode"` (recommendation strength: very strong). |
| PR-003 | MEDIUM | IN-SCOPE | R1 / R2 (`mypy` coverage gap on `_bootstrap.py`) | `pyproject.toml:115-141` (`[[tool.mypy.overrides]]`, line 119 `"pubrun._bootstrap"` under `ignore_errors = true`); Plan `E-02` (line 45), `V-02` (line 128) | `V-02` relied on `python3 -m mypy` to validate `src/pubrun/_bootstrap.py`, but `pyproject.toml` currently sets `ignore_errors = true` on `pubrun._bootstrap`, making `mypy` silently skip that file while actively checking `src/pubrun/__main__.py` (which `V-01` omitted). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Documented the `pyproject.toml` `ignore_errors` entry in `Project conventions discovered` and `Required tests / validation`, added `python3 -m mypy` to `V-01`, and added direct `Bootstrap or Conflict` unit-test evidence plus an explicit `ignore_errors` note to `V-02` (recommendation strength: strong). |
| PR-004 | MEDIUM | IN-SCOPE | R4 E (edge-case tests and `clean_bootstrap` isolation) | `tests/test_import_modes.py:233-239` (`clean_bootstrap`), lines 208, 483, 547-644, 794, 825, 1035; `tests/test_full_mode.py:96,132,208,235,254,272`; Plan `E-03` (lines 50-52), `V-03` (line 133) | `E-03` did not isolate `clean_bootstrap` (used by in-process `select_mode` tests) from `PUBRUN_RUN_MODE_OVERRIDE`, did not enumerate the existing child-env sites, and omitted test cases for `pubrun run --mode` setting both env vars, invalid `PUBRUN_RUN_MODE_OVERRIDE=bogus` fallback, and subsequent non-conflicting imports under `PUBRUN_IMPORT_CONFLICT=error`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-03`, `Proposed changes` item 3, and `V-03` to cover all three additional cases, isolate `clean_bootstrap`, and name the existing child-env sanitization sites in both test files (recommendation strength: strong). |
| PR-005 | LOW | IN-SCOPE | R1 / Check P (citations, `CHANGELOG.md` target, and dash check) | `.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md:31`; `CHANGELOG.md:120,263,290,335,609`; Plan lines 55, 63-65, 138 | Citations to `20260705-1828-01-full-capture-mode.md`, `tests/test_import_modes.py`, and `src/pubrun/tracker.py` lacked Section 11.1 anchors; `CHANGELOG.md` has multiple `### Fixed` sections under `## [Unreleased]`; and `V-04` lacked a concrete zero-dash check across the edited doc files. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Section 11.1 anchors in `Project conventions discovered`, specified the top-most `### Fixed` under `## [Unreleased]` in `E-04`, and added a portable exit-0 Python zero-dash diff check to `V-04` (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Changes public CLI override precedence, introduces `PUBRUN_RUN_MODE_OVERRIDE`, and emits a new manifest `selected_source` value across 4 E-items and 8 files. | yes |
| D-2 | Include `docs/manifest.md`, `docs/cli.md`, and `docs/functional_spec.md` sync in `lhwy0t` vs. defer to follow-up | Include in `E-04` (total 8 `Scope-Paths`, within `IPD-Z603`) | Defer doc sync to a separate backlog item | `plan-review.md` and `AGENTS.md#Doc-sync discipline` require synchronizing documentation when behavior and manifest values change; all three updates are 1-2 line edits directly tied to E-01/E-02. | yes |
| D-3 | Suppress conflict warnings/errors on subsequent in-code imports when `_selected_source == "cli:pubrun run --mode"` | Suppress (`conflict: False`) on subsequent imports under active CLI override | Suppress only on the first import (`_selected_mode is None`) | Keeps `import pubrun` followed by `import pubrun.full` (or multi-module imports) consistent with single-submodule override under `PUBRUN_IMPORT_CONFLICT=error` while leaving all non-CLI conflict tests untouched. | yes |

### Step S6

- Checked: Round 1 added three paths (`docs/manifest.md`, `docs/cli.md`, `docs/functional_spec.md`) to `- Scope-Paths:` to resolve PR-001. Under Step S6 Rule 1, a `- Scope-Paths:` change requires a second review pass before finalizing.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised plan (lines 1-159) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and Section 11.1 code citations. Polished the `docs/manifest.md` heading reference to exact ``## `pubrun_imports` `` in `E-04`, `Project conventions discovered`, and `Proposed changes` item 4. Mermaid flowchart matches E-02 text verbatim. Zero em or en dashes in edited prose.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-04`, `Project conventions discovered`, `Proposed changes` item 4 | Cited `docs/manifest.md#pubrun_imports` and concatenation prose | Cited `docs/manifest.md` (``## `pubrun_imports` ``) matching the exact heading in `docs/manifest.md:521` | Section 11.1 heading-anchor accuracy. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R1

- Checked: verified all 8 paths in `- Scope-Paths:` match `Scope`, `E-01`..`E-04`, `Proposed changes` 1-4, `Scope check`, `Spec / documentation sync`, `V-01`..`V-04`, and Gate item 2 with zero drift. Verified exact headings in `docs/manifest.md:521`, `docs/cli.md:731`, `docs/functional_spec.md:543`, and `CHANGELOG.md:9,120`.

### Step R2

- Checked: E-01..E-04 map 1:1 to V-01..V-04; all four V-items demand concrete, non-vacuous, reachable evidence; 4 E-items and 8 Scope-Paths stay within `IPD-Z603` guidance; Gate items 1-5 satisfy the execution contract.

### Step R3

- Checked: Round 1 edits added documentation sync (`docs/manifest.md`, `docs/cli.md`, `docs/functional_spec.md`) and test cases only; no new security or privacy surface was introduced.

### Step R4

- Checked: Round 1 edits resolved all correctness, type-check honesty, test coverage, and documentation-sync findings without introducing scope creep or contradictions.

### Step S5

- Checked: `OQ-01` remains `resolved` (`Owner: maintainer`); zero new findings or open questions in Round 2; lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 made only a heading-anchor polish with zero changes to `E-*`/`V-*` count, `- Scope-Paths:`, or `- Item-Dependencies:`, and introduced zero new findings or open questions. `aw ipd lint --phase review-finalize --agent` will be verified before committing.

AW-REVIEW: DONE
