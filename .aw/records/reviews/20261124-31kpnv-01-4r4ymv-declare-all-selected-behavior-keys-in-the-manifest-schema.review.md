# Review findings: ipd 4r4ymv

- Subject-Id: 4r4ymv
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-31kpnv-01-4r4ymv-declare-all-selected-behavior-keys-in-the-manifest-schema.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `712a13b` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Concern and Goal | Said pubrun writes "six flags" without distinguishing the five base flags from `full`-only `force_console` | States pubrun writes five base flags in five modes and adds `force_console` in `full` | Requirement 5 (explicit meaning) and alignment with Findings. |
| Project conventions | Claimed "pubrun has no runtime dependencies" and cited `TestFullModeEndToEnd` | Notes conditional `tomli>=1.1.0; python_version < '3.11'` and cites `TestExistingModesConsoleOff` and `TestFullModeBehavior.test_full_wraps_console_end_to_end` | Factual accuracy and Section 11.1 citation rules (PR-002, PR-003). |
| Findings table, prose, and Mermaid diagram | Cited `RunTracker._get_import_metadata`, wrote "six boolean flags per mode" in diagram node A, and omitted backticks in `docs/manifest.md` headings | Uses `src/pubrun/tracker.py::Run._get_import_metadata`, names exact consumer symbols, updates diagram node A to match text, and aligns `docs/manifest.md` anchors and quote | Requirement 12(d)-(e) and Section 11.1 citations (PR-001, PR-003). |
| Proposed changes 1 | Showed compact single-line JSON with a prose note to reformat multi-line | Shows the exact 4-space multi-line JSON block matching `schemas/manifest.schema.json` | Requirement 5: removes formatting ambiguity (PR-003). |
| E-02, Required tests, and V-01..V-03 | Hardcoded six modes and "16 lines" test count bar, omitted trailing-comma removal in mutation checks, and used `grep -c` dash check | Parametrizes over `sorted(MODES)`, adds integer non-boolean case, rewrites V-01/V-02 to behavior-plus-mechanism with execution-time re-derivation, adds valid-JSON trailing-comma instructions to mutation checks, and replaces `grep -c` with a non-vacuous `python3 -c` exit-0 dash check | Check R2 executability, re-derivation convention, and requirement 6 (PR-004, PR-005, PR-006). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`schemas/manifest.schema.json`, `tests/test_manifest_schema.py`, `CHANGELOG.md`), 3 E-items in 2 task groups, `- Kind: child`.

1. Yes: `schemas/manifest.schema.json` is the published manifest JSON Schema contract that `docs/functional_spec.md` requires every manifest to adhere to, and the plan declares four properties and adds `additionalProperties: false` on `pubrun_imports.selected_behavior`.
2. No: edits only the JSON Schema, its pytest conformance suite, and `CHANGELOG.md`; touches no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 3 E-items across 2 task groups in 3 tightly coupled files.
4. Yes: `schemas/manifest.schema.json`, `tests/test_manifest_schema.py`, `CHANGELOG.md`.
5. Yes (bounded): an error in the published schema (such as making post-2026-06-20 flags required or omitting a valid flag under `additionalProperties: false`) would break schema validation of valid current or legacy manifests, though it is straightforward to revert before release.

AW-TIER: standard

### Step R1

- Checked: `schemas/manifest.schema.json` (`properties.pubrun_imports.properties.selected_behavior`, lines 111-170); `src/pubrun/_modes.py::MODES` and `get_mode_behavior`; `src/pubrun/_bootstrap.py::select_mode`, `get_import_metadata`, `get_selected_behavior`; all six mode submodules (`src/pubrun/auto.py`, `noauto.py`, `nopatch.py`, `noconsole.py`, `minimal.py`, `full.py`); `src/pubrun/tracker.py::Run._bootstrap_engines`, `Run._merge_and_migrate`, `Run._get_import_metadata`; `src/pubrun/core.py::_execute_boot_sequence`; `src/pubrun/__main__.py` (doctor import-mode block); `src/pubrun/report/reproducibility.py::_assess_capture_completeness`; `tests/test_manifest_schema.py`; `tests/test_full_mode.py`; `tests/conftest.py::_subprocess_pythonpath`; `tests/fixtures/sample_manifest.json`; `docs/manifest.md` (lines 521-542); `docs/functional_spec.md` (lines 153-163); `CHANGELOG.md` (lines 1-150, 264); `pyproject.toml`; `.aw/records/backlog/graduated/` (`31kpnv`, `kiir0y`, `szf342`); `.aw/records/specs/`; and `git log -- src/pubrun/_modes.py` plus commits `142672074b` and `3c6ae50`.
- Confirmed: exact six boolean keys in `MODES` (five base flags plus `force_console` in `full` only), git history commits `6ff6837` (2026-06-04), `6bd3284` (2026-06-20), and `d3f77c1` (2026-07-05), sibling backlog carriers `kiir0y` and `szf342`, `tests/fixtures/sample_manifest.json` omits `pubrun_imports`, all test fixtures using `selected_behavior` use only declared keys, and `.aw/records/specs/` has no `.spec.md` file.
- PR-001: plan cited `src/pubrun/tracker.py::RunTracker._get_import_metadata` in three places, but `src/pubrun/tracker.py:103` defines `class Run` (`Run._get_import_metadata` at line 1426). Fixed in all three places and added exact consumer symbols in Findings.
- PR-002: Project conventions cited `tests/test_full_mode.py::TestFullModeEndToEnd`, which does not exist. Fixed to cite `tests/test_full_mode.py::TestExistingModesConsoleOff` and `tests/test_full_mode.py::TestFullModeBehavior.test_full_wraps_console_end_to_end`.
- PR-003: fixed four minor factual/formatting inaccuracies (`pyproject.toml` conditional `tomli` runtime dependency for Python < 3.11; five base flags vs `full`-only sixth flag in Goal and Mermaid node A; exact backticked headings and quote in `docs/manifest.md`; exact 4-space multi-line JSON layout in Proposed changes item 1).

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-03` to `V-01`..`V-03`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability of V-02 (`src/pubrun/tracker.py::Run._get_import_metadata` invoked by E-02 child subprocesses), re-derivation convention, mutation checks, dash check command, and all five execution-contract elements in the gate.
- PR-004: V-02 required a fixed collected test count ("16 lines") and treated test function names as the bar (same in V-01 for `test_schema_is_valid_draft`), violating `steps/r2-executability.md` re-derivation convention; hardcoding six mode names in E-02 would also miss a future mode added to `MODES`. Fixed E-02 to parametrize over `sorted(MODES)`, check exact `selected_behavior` equality, use explicit UTF-8 reading, and include the integer non-boolean case `{"force_console": 1}`; rewrote V-01 and V-02 around pinned behaviors, mechanisms, non-binding test-name pointers, and execution-time re-derivation.
- PR-005: both mutation checks instructed deleting the last property/keyword line in `selected_behavior` without removing the preceding trailing comma, which would produce invalid JSON (`JSONDecodeError`) instead of `jsonschema.ValidationError`; restoration also checked only `git diff --stat`. Fixed both checks to remove the preceding trailing comma so mutated JSON remains valid, and required verifying restoration against the E-01 diff plus re-running `tests/test_manifest_schema.py`.
- PR-006: `git diff -U0 -- CHANGELOG.md | grep '^+[^+]' | grep -c '[—–]'` exits 1 when count is 0 and passes vacuously with `0` if `CHANGELOG.md` has no working-tree diff. Replaced with a `python3 -c` check that asserts at least one added `CHANGELOG.md` line exists and exits 0 iff zero em/en dashes appear.

### Step R3

- Checked: all five bullets of Check R3 full form. No authentication or authorization surfaces; no secrets introduced; schema validation tightens trust-boundary checking on `pubrun_imports.selected_behavior`; E-02 child subprocess runs `[sys.executable, "-c", script, mode]` with an argv list (no shell), `timeout=60`, isolated `tmp_path`, and no network calls; V-03 runs `python3 scripts/sanitize_paths.py --check --all` to prevent local path leaks. No finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (3 single-concern E-items across 3 files; no splitting warranted); spec and documentation sync (`docs/manifest.md` already documents all six flags under `` ## `pubrun_imports` ``; `docs/functional_spec.md` names no individual field; no other `docs/` file mentions `selected_behavior`; `.aw/records/specs/` has no `.spec.md` file); and cross-platform compatibility of E-02 (`Path` + explicit `encoding="utf-8"`, argv subprocess list, `jsonschema>=4.0` compatible subschema). No additional findings beyond PR-001..PR-006.

### Step S5

- Checked: pre-existing open questions `OQ-01` and `OQ-02` (both `- Blocking: no`, `- Status: resolved`, `- Owner: plan author`) are backed by verified repository evidence (git history of `src/pubrun/_modes.py` and existing `additionalProperties: false` drift-guard pattern in `schemas/manifest.schema.json`). Every review finding PR-001..PR-006 had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | R1 (nonexistent symbol) | `src/pubrun/tracker.py:103` (`class Run`), `src/pubrun/tracker.py:1426` (`Run._get_import_metadata`) | Plan cited `src/pubrun/tracker.py::RunTracker._get_import_metadata` in Findings, Deferred, and V-02, but `src/pubrun/tracker.py` defines `Run`, not `RunTracker`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced all three citations with `src/pubrun/tracker.py::Run._get_import_metadata` and cited exact consumer symbols in Findings. |
| PR-002 | MEDIUM | IN-SCOPE | R1 (nonexistent symbol) | `tests/test_full_mode.py:65` (`TestExistingModesConsoleOff`), `tests/test_full_mode.py:147,214` (`TestFullModeBehavior.test_full_wraps_console_end_to_end`) | Project conventions cited `tests/test_full_mode.py::TestFullModeEndToEnd`, which does not exist in `tests/test_full_mode.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated Project conventions to cite `TestExistingModesConsoleOff` and `TestFullModeBehavior.test_full_wraps_console_end_to_end`. |
| PR-003 | LOW | IN-SCOPE | R1 / Proofreading (inaccurate facts and anchors) | `pyproject.toml:39-41` (`tomli`), `src/pubrun/_modes.py:19-66` (`MODES`), `docs/manifest.md:521,528,537`, `schemas/manifest.schema.json:121-134` | Conventions omitted conditional `tomli` runtime dependency for Python < 3.11; Goal and diagram node A said six flags per mode instead of five base plus `full`-only `force_console`; `docs/manifest.md` headings lacked backticks and misquoted line 528; Proposed changes 1 showed compact single-line JSON. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected the dependency note, Goal, Mermaid node A, `docs/manifest.md` citations, and formatted Proposed changes 1 in 4-space multi-line JSON. |
| PR-004 | MEDIUM | IN-SCOPE | R2 (re-derivation convention) | Plan `V-01`, `V-02`, and `E-02`; `steps/r2-executability.md` re-derivation rule | V-02 demanded a hardcoded collected test count ("16 lines") and treated test function names as bars (same in V-01); hardcoding six mode names in E-02 would also miss a future mode added to `MODES`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Parametrized E-02 over `sorted(MODES)`, asserted exact `selected_behavior` dict equality, added integer case `{"force_console": 1}` and UTF-8 read, and rewrote V-01/V-02 around pinned behaviors, mechanisms, non-binding pointers, and execution-time re-derivation. |
| PR-005 | MEDIUM | IN-SCOPE | R2 (invalid JSON mutation checks) | Plan `Required tests / validation` mutation checks; `schemas/manifest.schema.json:121-134` | Deleting `"additionalProperties": false` or `"force_console"` without removing the preceding trailing comma leaves invalid JSON (`JSONDecodeError`) instead of triggering the intended `ValidationError`; `git diff --stat` alone does not verify exact restoration. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added explicit trailing-comma removal instructions to both mutation checks and required diff verification plus re-running `tests/test_manifest_schema.py` after restoring. |
| PR-006 | LOW | IN-SCOPE | R2 (exit-1 and vacuous dash check) | Plan `Required tests / validation` and `V-03` (`grep -c '[—–]'`) | `grep -c` exits 1 when count is 0 and prints `0` vacuously when `CHANGELOG.md` has no working-tree diff. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `grep -c` with a `python3 -c` check asserting at least one added line in `CHANGELOG.md` and exiting 0 only when `dashes=0`. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Changes the published `schemas/manifest.schema.json` contract (`docs/functional_spec.md:158`) with 3 small, single-concern E-items across 3 files. | yes |
| D-2 | Keep `OQ-01` (`additionalProperties: false`) and `OQ-02` (no `required` list) resolved without parking for human input | Keep resolved; plan remains gated by human approval (`go-pending-approval`) | Reopen `OQ-01` as `Blocking: yes` | Every historical flag in `git log -- src/pubrun/_modes.py` is declared; `schemas/manifest.schema.json` already uses `additionalProperties: false` as its drift-guard standard; no schema change executes until human approval. | yes |
| D-3 | Parametrize E-02 conformance over `sorted(MODES)` instead of a hardcoded six-mode list | `sorted(MODES)` | Hardcoded list of six mode names | Aligns with Goal item 2 and R2 re-derivation so a seventh mode added to `src/pubrun/_modes.py::MODES` is automatically checked; all six current modes have `src/pubrun/<mode>.py` submodules. | yes |
| D-4 | Leave CI matrix execution in Deferred / out of scope with `Carrier-Declined` | Keep deferred with V-02 recording OS/Python and non-execution of CI matrix | Add a push-and-watch-CI E-item | `AGENTS.md` forbids pushing without explicit human authorization, so no agent-executable plan may mandate a push; GitHub Actions runs the matrix on push/PR. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All six findings were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
