# Review findings: ipd w24lw1

- Subject-Id: w24lw1
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-t55vh8-01-w24lw1-reuse-the-canonical-file-record-classifier-in-methods-report.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `f434c8f` had a clean working tree. `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(a), (b), (d), and (e) are satisfied by the Mermaid `classDiagram` and `flowchart TD` in `Findings`, both matching the normative prose.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Required tests / validation, V-04 (2), Gate item 2 | Saved mutation patch to host-specific `/tmp/opencode/w24lw1-methods.patch` without creating directory or cleaning up | Saves patch to gitignored `tmp/w24lw1-methods.patch` (`mkdir -p tmp`) and deletes it after re-applying | `/tmp/opencode/` does not exist outside `opencode` hosts and sits outside isolated worktrees/sandboxes (PR-001). |
| Required tests / validation, Deferred, V-04 (4)-(5) | Demanded serial `python3 -m pytest -q` (9 min) and unconditional networked `uv run --python 3.9 --with ...` | Uses `aw suite --no-cache` (fallback `python3 -m pytest -q`), and runs `uv run --offline ...` when cached offline or records unavailability plus `py_compile` | Prevents offline/sandbox gate failure on PyPI access and avoids 9-minute serial suite stall (PR-002). |
| Proposed changes item 4, Required tests, V-04 (6)-(7) | Hardcoded `mypy` count `59` without `exit=0`, omitted local `generate_report_multi` import and `XDG_CONFIG_HOME`/`APPDATA` isolation in child-process test, and noted two `F401` findings in `tests/test_reports.py` | Requires `mypy; echo "exit=$?"` with execution-time count re-derivation, notes `generate_report_multi` import and config isolation, and notes E-04 resolves `pytest`'s `F401` | Re-derivation compliance, config-file isolation, and accurate `ruff --select F` expectation (PR-003). |
| Project conventions, Deferred, Required tests, V-02 (2), V-03 (2), V-05 (2), Gate items 2 & 5 | Used `grep -c` expecting `0` (exits 1) and vacuous `CHANGELOG.md` dash check, omitted `--scope-ack`, opened Gate item 5 unconditionally, and used prose quotes for `AGENTS.md` headings | Uses portable exit-0 `python3 -c` dash check on added `CHANGELOG.md` lines, adds `\|\| true` on count-0 `grep -c` checks, adds `--scope-ack`, leads Gate item 5 with conditional runner/executor ownership, and uses Section 11.1 `AGENTS.md#...` citations | Non-vacuous exit-0 validation, Check S7 execution contract, and Section 11.1 citations (PR-004). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/report/file_evidence.py`, `src/pubrun/report/reproducibility.py`, `src/pubrun/report/methods.py`, `tests/test_reports.py`, `CHANGELOG.md`), 5 E-items in 2 task groups, `- Kind: child`, `- Blocks-Release: next`, `- From-Backlog: t55vh8`.

1. Yes (bounded): changes user-visible file-provenance breakdown output in `methods.md`, `methods.tex`, `pubrun methods`, and `pubrun methods --all` (no longer counting digestless `completed`/`verified_content` records as independently verified; aligning legacy `md5`-only records with `reproducibility.py`), and creates `src/pubrun/report/file_evidence.py` which downstream plan `l2s67v` (`unf79v`) depends on.
2. No: touches file-provenance classification for methods reports and reproducibility assessment only; does not touch code guarding private data, commits, worktree isolation, merges to `main`, or the sandbox.
3. No: 5 focused E-items across 2 task groups in 5 Scope-Paths, all centered on the `pubrun.report` classifier.
4. Yes: `src/pubrun/report/file_evidence.py`, `src/pubrun/report/reproducibility.py`, `src/pubrun/report/methods.py`, `tests/test_reports.py`, `CHANGELOG.md`.
5. Yes (bounded): `src/pubrun/report/methods.py` runs during `ArtifactWriter.write_artifacts`; accidentally importing `pubrun.report.reproducibility` or breaking `pubrun.report` callable-subpackage semantics would regress runtime capture isolation, guarded by `tests/test_report_subpackage_integrity.py`, `tests/test_reproducibility_assessment.py`, and E-04's child-process test.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/report/reproducibility.py` (lines 1-28, 853-940: `_record_is_asserted`, `_is_caller_digest_mismatch`, `_has_nonempty_digest_value`, `_classify_file_record`, `_assess_inputs_outputs`); `src/pubrun/report/methods.py` (lines 1-450: `_classify_file_record`, `_summarize_manifest_data_files`, `_format_file_provenance_note`, `generate_report`, `generate_report_multi`, single `reproducibility` comment at line 283); `src/pubrun/report/__init__.py` (`CallableModule`); `src/pubrun/noauto.py` (exports `start`, `stop`, `register_input`); `src/pubrun/writer.py:319-328` (calls `pubrun.report.methods.generate_report`); `tests/test_reports.py` (lines 1-30, 725-835: `TestMethodsFileProvenanceDistinction`, `_base_manifest`); `tests/test_report_subpackage_integrity.py`; `tests/test_reproducibility_assessment.py:1090`; `CHANGELOG.md:120` (`### Fixed`); `.aw/records/backlog/graduated/20261124-t55vh8-...backlog.md` and `unf79v`; `ruff check` baseline (`Found 275 errors.` across `reproducibility.py` and `methods.py`; `ruff check --select F` reports `F401` on `pytest` and `Path` in `tests/test_reports.py` only).
- Verified no other caller in `src/` or `tests/` imports `_is_caller_digest_mismatch`, `_has_nonempty_digest_value`, or `_classify_file_record` from `reproducibility.py` or `methods.py`.
- Verified `sed -n '/^def _is_caller_digest_mismatch/,/^    return "identified_only"$/p'` matches lines 866-924 cleanly (line 917 has 8-space indent, line 924 has 4-space indent).

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-05` to `V-01`..`V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, `- Blocks-Release: next` inherited from backlog `t55vh8`, runtime-demonstration reachability (`V-03 (3)` probe through `methods.py::generate_report`/`generate_report_multi`; `V-04 (1)` child-process test through `writer.py::ArtifactWriter.write_artifacts`), mutation check in `V-04 (2)`, and all five execution-contract elements in the gate.
- PR-001: moved mutation patch from host-specific `/tmp/opencode/w24lw1-methods.patch` to gitignored `tmp/w24lw1-methods.patch` with `mkdir -p tmp` and cleanup.
- PR-002: updated full-suite validation to `aw suite --no-cache` (with `python3 -m pytest -q` fallback) and made the Python 3.9 `uv run` check offline-safe with a `py_compile` fallback when `uv` or cached Python 3.9/wheels are unavailable.
- PR-003: required `mypy; echo "exit=$?"` with execution-time file-count re-derivation, added `generate_report_multi` import note and `XDG_CONFIG_HOME`/`APPDATA` isolation in E-04, and clarified that E-04 resolves `pytest`'s pre-existing `F401`.
- PR-004: replaced `V-05 (2)`'s `grep -c` dash check with a portable, non-vacuous exit-0 `python3 -c` check, added `|| true` on count-0 `grep -c` checks in `V-02`/`V-03`, added `--scope-ack` to Gate item 2, and led Gate item 5 with conditional runner/executor finalization ownership.

### Step R3

- Checked: all five bullets of Check R3 full form. The new module `src/pubrun/report/file_evidence.py` uses only `typing` (stdlib-only, pure dictionary inspection, no I/O, no subprocesses, no secrets or network calls). E-04's subprocess test invokes `[sys.executable, "-c", script]` with an argv list (no shell) in `tmp_path` with isolated `XDG_CONFIG_HOME`/`APPDATA`. Mutation patch stays inside gitignored `tmp/` (PR-001). V-05 runs `python3 scripts/sanitize_paths.py --check --all`. No remaining security finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (5 focused single-concern E-items across 2 task groups in 5 Scope-Paths, each executable in one focused pass); Python 3.8 compatibility (`from typing import Any, Dict`); anti-regression (preserves `reproducibility.py` isolation off the runtime capture path, verified by `V-01 (3)`, `test_report_subpackage_integrity.py`, `test_reproducibility_assessment.py`, and E-04's child-process test; mutation check proves new tests catch the original bug); spec and documentation sync (`CHANGELOG.md` updated in E-05 with dash-free prose; no `.spec.md` exists; `docs/cli.md` wording remains accurate; `diagnostics.py` copy properly deferred to carrier `unf79v`). No additional findings beyond PR-001..PR-004.

### Step S5

- Checked: `OQ-01` and `OQ-02` in `## Open questions` are both `Blocking: no`, `Status: resolved`, `Owner: plan author`, and grounded in repository evidence (`reproducibility.py` docstring, `writer.py`, and backlog `t55vh8`). All four review findings (PR-001..PR-004) have Overall Remediation Risk `Low` and were fixed in place. No unresolved human decision remains, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R2 / R3 (host-specific `/tmp/opencode/` path in mutation check) | Plan `Required tests / validation` (line 257), `Approval and execution gate` item 2 (line 324) | Mutation check wrote to `/tmp/opencode/w24lw1-methods.patch` without `mkdir -p` or cleanup; `/tmp/opencode/` does not exist outside `opencode` hosts and sits outside isolated worktrees/sandboxes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Changed mutation patch path to gitignored `tmp/w24lw1-methods.patch` with `mkdir -p tmp` and `rm -f tmp/w24lw1-methods.patch` cleanup afterwards. |
| PR-002 | MEDIUM | IN-SCOPE | R2 (unconditional networked `uv run --python 3.9` and 9-minute serial full suite) | Plan `Required tests / validation` (lines 259-260), `V-04` (4)-(5) (line 308) | `V-04 (5)` demanded `uv run --no-project --python 3.9 --with pytest --with tomli` without `--offline` or fallback (fails in offline/sandboxed lanes), and `V-04 (4)` demanded serial `python3 -m pytest -q` (537.76s) instead of `aw suite --no-cache`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `V-04 (4)` to `aw suite --no-cache` (fallback `python3 -m pytest -q`) and `V-04 (5)` to `uv run --offline ...` with explicit offline-unavailability recording plus `py_compile`. |
| PR-003 | MEDIUM | IN-SCOPE | R2 / R4 (hardcoded `mypy` count `59`, E-04 test import/config isolation, `ruff --select F` count) | `tests/test_reports.py:4-7,743`; Plan `Proposed changes` item 4 (lines 212-229), `Required tests` (lines 261-262), `V-04` (6)-(7) (line 308) | `V-04 (6)` hardcoded `59 source files` without `exit=0` or execution-time re-derivation; `Proposed changes` item 4 omitted the local `generate_report_multi` import and `XDG_CONFIG_HOME`/`APPDATA` isolation in the subprocess test; `Required tests` expected two `F401` findings in `tests/test_reports.py` even though E-04 uses `pytest`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required `mypy; echo "exit=$?"` with re-derived count, added `generate_report_multi` import note and `XDG_CONFIG_HOME`/`APPDATA` isolation in E-04, and clarified that E-04 resolves `pytest`'s `F401`. |
| PR-004 | LOW | IN-SCOPE | Check S7 / Check P (`grep -c` exit-1 checks, Gate items 2 & 5, Section 11.1 citations) | Plan `Project conventions` (lines 72-73), `Deferred` (line 243), `Required tests` (line 263), `V-02` (2), `V-03` (2), `V-05` (2), `Approval and execution gate` items 2 & 5 (lines 324, 327) | `grep -c` returns exit 1 on count 0 and `CHANGELOG.md` diff dash check passes vacuously on empty diff; Gate item 2 omitted `--scope-ack`; Gate item 5 opened unconditionally; `AGENTS.md` headings omitted Section 11.1 `path#Heading` form. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `V-05 (2)` dash check with portable non-vacuous exit-0 `python3 -c` check, added `\|\| true` to count-0 `grep -c` commands, added `--scope-ack` to Gate item 2, reordered Gate item 5 for conditional runner/executor ownership, and applied Section 11.1 citations. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Changes user-visible methods-report output, introduces a new module imported on the runtime capture path, carries `- Blocks-Release: next`, and has 5 focused E-items in 5 Scope-Paths. | yes |
| D-2 | Keep `src/pubrun/report/diagnostics.py::_classify_file_record_display` out of scope | Defer to carrier `unf79v` (`l2s67v`) | Fix `diagnostics.py` in this plan | `diagnostics.py` returns display badge names and is edited by pending plans `qe6dad` and `mvbbny`; backlog `unf79v` / plan `l2s67v` already carries it cleanly after `w24lw1`. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All four findings (PR-001..PR-004) were fixed in place with Low remediation risk and swept across the plan. `aw ipd lint --phase review-finalize --agent` will be verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
