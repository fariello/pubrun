# Review findings: ipd fdqkrz

- Subject-Id: fdqkrz
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Antigravity / Gemini
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text, front matter, Mermaid diagram, E-01 through E-04, V-01 through V-04, Project conventions, Findings, Proposed changes, Deferred, Scope check, Spec/documentation sync, Open questions, and Approval and execution gate of `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Concern, E-01, Deferred | Unexpanded `URL` and `TUI`, and `PEP` first-use placement | Expanded `Python Enhancement Proposal (PEP)`, `Uniform Resource Locator (URL)`, and `Terminal User Interface (TUI)` on first use | Technical writing requirement 1 (expand acronyms on first use). |
| E-01, E-02 Expected outcomes | Dense single-sentence outcomes | Split into short, complete sentences | Technical writing requirement 2 (short, complete sentences). |
| Recursive transitive closure diagram | Keyed work queue on `(dist, active_extras=frozenset())` and omitted base+extra queueing and `version()` fallback | Updated nodes A, C, D, E, G, I, K, L, P to match `(normalized_name, active_extra)` keying and defensive fallback lookup | Technical writing requirements 12(d) and 12(e) (diagram must match normative text). |
| Proposed changes lines 139, 151 | Contained exclamation marks (`enqueue it!`, `excluded!`) | Replaced exclamation marks with periods | Technical writing requirement 8 (direct, non-promotional technical tone). |
| Project conventions, Deferred, Scope check, Spec sync, Gate item 1 | Informal code citations, bare IDs (`uil22c`, `ijipnx`, `iflqsl`, `w4hxkh`), and missing `- Carrier:` / `- Carrier-Declined:` lines | Standardized `path::Symbol` citations, attached descriptive labels, and added `- Carrier: ijipnx`, `- Carrier: iflqsl`, and `- Carrier-Declined:` | `steps/p-proofread.md` Section 11.1, technical writing requirement 1, and `check.ipd-uncarried-obligation`. |
| Validation and cross-check boilerplate | Two em dashes (`—as distinct from ... by construction—`) triggering `IPD-C802` | Replaced the two em dashes with parentheses | Zero `IPD-C802` advisories while preserving exact meaning. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md` front matter, `- Scope-Paths:`, E-items, and cross-plan interfaces with `uil22c`, `ijipnx`, and `iflqsl` in Set `dep-capture`.

1. Yes: introduces `src/pubrun/capture/_markers.py` (standard-library PEP 508/440 parser and evaluator) and changes `imported-transitive` resolution semantics and `unresolved` entries consumed by child plans `ijipnx` and `iflqsl`.
2. No: does not touch code guarding private data, repository commits, worktree isolation, merges to main, or the sandbox.
3. No: 4 E-items across 3 task groups and 4 focused Scope-Paths (`src/pubrun/capture/_markers.py`, `src/pubrun/capture/packages.py`, `tests/test_package_transitive.py`, `tests/test_new_features.py`).
4. Yes: `- Scope-Paths:` explicitly lists all 4 files modified or created.
5. Yes: `Blocks-Release: next`; defects in cycle termination, marker parsing/version comparisons, or fallback lookup would cause infinite loops, false partial/complete reports, or regressions in `tests/test_new_features.py::TestImportedTransitiveMode`.

AW-TIER: standard

### Step R1

- Checked: Every cited file, symbol, and sibling artifact against the repository: `src/pubrun/capture/packages.py` (`_parse_req_name`, `get_packages`), `tests/test_new_features.py::TestImportedTransitiveMode` (`test_transitive_deps_discovered`, `test_pep508_parser_edge_cases`), `.aw/records/backlog/graduated/20261121-pubrun-improve-01-w4hxkh-dependency-capture.backlog.md`, prerequisite child plan `uil22c`, and downstream child plan `ijipnx` (`$defs.unresolved_package_record`). Verified that `TestImportedTransitiveMode.test_transitive_deps_discovered` mocks `importlib.metadata.distribution("pubrun_fake_dep")` to raise `PackageNotFoundError` while `importlib.metadata.version("pubrun_fake_dep")` returns `"2.0.0"`, which would break without a `version()` fallback (PR-001).

### Step R2

- Checked: E/V 1:1 bijection (`E-01`..`E-04` to `V-01`..`V-04`), Scope-Paths completeness (4 files), `Item-Dependencies: executed:uil22c`, runtime-demonstration reachability of all `V-*` items (requiring non-zero collected tests on `-k` filters in V-01/V-02), and `## Approval and execution gate` compliance against `steps/r2-executability.md` and `steps/s7-finalize.md`. Caught and fixed prohibited scope-fence STOP wording and unconditional executor-side finalize instruction (PR-004).

### Step R3

- Checked: Zero external/network calls, zero third-party packages, pure standard-library parsing (no `eval()`), bounded non-backtracking recursive-descent marker grammar, and strict no-import invariant (never imports target distributions to inspect metadata).

### Step R4

- Checked: Engineering rubric A (correctness/data integrity), C (architecture/operability), D (anti-regression/domain invariants), E (testing/verification), F (KISS/principles), right-sizing/conceptual density (4 focused E-items across 4 Scope-Paths), and `## Spec / documentation sync` (deferred cleanly to `ijipnx` and `iflqsl`). Caught and fixed `TestImportedTransitiveMode` `version()` fallback regression (PR-001), PEP 508/440 marker edge cases (`.*` wildcards, `~=` semantics, trailing zeros, `===`, `in`/`not in` non-version string semantics, normalized `extra` comparisons, 6 legacy PEP 508 aliases, URL `;` handling) (PR-002), and `(normalized_name, active_extra)` base+extra expansion plus `ijipnx`-matching `"candidates": []` shape (PR-003).

### Step S5

- Checked: Pre-existing `OQ-01`, deferred carrier obligations, and all review findings. All 6 findings had Low remediation risk and were fixed in place with zero remaining unresolved or deferred findings and zero blocking human questions. Fixed `OQ-01` owner provenance per `steps/s5-questions.md` rule 5, added structured `- Carrier:` / `- Carrier-Declined:` lines to all three deferred rows (PR-005), and recorded reversible decisions `D-1` and `D-2` below.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R1 / R4.D (`TestImportedTransitiveMode` fallback regression) | `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:134-135`; `tests/test_new_features.py::TestImportedTransitiveMode.test_transitive_deps_discovered:49-71` | Proposed changes #2 only fell back to `importlib.metadata.distribution(parsed.name)` when a target is absent from `_DistributionIndex`, and did not fall back to `importlib.metadata.version(parsed.name)`. In `test_transitive_deps_discovered`, `mock_distribution("pubrun_fake_dep")` raises `PackageNotFoundError` while `mock_version("pubrun_fake_dep")` returns `"2.0.0"`, which would falsely classify `pubrun_fake_dep` as `missing_transitive_dependency` and break the test. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required defensive fallback in `_resolve_transitive_closure()` matching `uil22c`: look up parent `requires` via canonical `parent_name`, and resolve missing-from-index targets via `distribution(parsed.name)` then `version(parsed.name)` before classifying as `missing_transitive_dependency` (recommendation strength: very strong). |
| PR-002 | high | IN-SCOPE | R4.A (PEP 508 / PEP 440 marker evaluation edge cases) | `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:109-119` | Several real-world PEP 508/440 cases were unspecified or error-prone: `.*` prefix wildcards on `==`/`!=` (`python_version == "3.11.*"`), exact `~=` compatible-release semantics, trailing-zero equivalence (`"3.10" == "3.10.0"`), strict string semantics for `===` and `in`/`not in` on version variables (`python_version in "3.8 3.9"`), PEP 503 normalization of `extra` literals (`extra == "dev_tools"` vs `dep[dev-tools]`), and the 6 PEP 508 legacy aliases (`os.name`, `sys.platform`, etc.). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified all six PEP 508/440 rules explicitly in E-01, Proposed changes #1, E-03, and V-01 (recommendation strength: very strong). |
| PR-003 | medium | IN-SCOPE | R4.A / R7 (Base+extra queue expansion and `ijipnx` `unresolved` schema parity) | `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:124-141`; `ijipnx:133`; `uil22c:131,163` | Keying `expanded_states` by `(target_key, parsed_extras_frozenset)` could skip base requirements (`extra != "fast"`) when a target is first reached via `dep[fast]` and risked subset duplication across multiple callers; also `unresolved` entries omitted `"candidates": []` expected by `uil22c` and `ijipnx`, and unparseable non-blank requirement strings lacked a specified `ijipnx`-valid `reason` enum value. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Keyed `expanded_states` by `(normalized_name, active_extra)` (always enqueueing base `""` plus each normalized extra individually), included `"candidates": []` on all `unresolved` entries, and mapped unparseable non-blank requirement strings to `reason = "unparseable_marker"` (recommendation strength: strong). |
| PR-004 | high | IN-SCOPE | R2 / S7 (Execution contract policy) | `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:217,220`; `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`; `.aw/system/workflows/plan-review/steps/r2-executability.md:59-60` | Execution contract item 2 contained prohibited "if execution seems to need more files, STOP and report" wording, and item 5 unconditionally instructed the executor to run the `aw ipd` transition rather than conditional direct-vs-runner `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Rewrote gate item 2 as a scope declaration with `--scope-reason`/`--scope-ack` guidance (noting `--scope-ack` for unmodified `tests/test_new_features.py` if it passes unchanged, reserving STOP for genuinely unsafe conditions) and gate item 5 with conditional direct-vs-runner `aw ipd finalize fdqkrz` ownership (recommendation strength: very strong). |
| PR-005 | low | IN-SCOPE | S5 (Open-question owner provenance and uncarried deferred obligations) | `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:157-161,183`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21,79-91` | `OQ-01` recorded `- Owner: maintainer (confirmed upon plan approval)` on an author-resolved question, and all three deferred rows lacked structured `- Carrier:` / `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Updated `OQ-01` `- Owner:` to `plan author (binding upon plan approval)`, recorded reversible decision `D-1`, and added `- Carrier: ijipnx`, `- Carrier: iflqsl`, and `- Carrier-Declined:` to the three deferred rows (recommendation strength: very strong). |
| PR-006 | low | IN-SCOPE | Check P (Technical writing, diagram parity, and `IPD-C802` hygiene) | `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:5,36-60,70,77,94-97,139,151,159-175,188` | `URL` and `TUI` were unexpanded; E-01/E-02 Expected outcomes were dense run-on sentences; lines 139 and 151 had exclamation marks; bare IDs lacked descriptive labels; code references lacked `path::Symbol` form; diagram lagged updated `(normalized_name, active_extra)` queue; and line 188 had two em dashes (`IPD-C802`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Expanded acronyms, split run-on sentences, removed exclamation marks, added descriptive labels, standardized `path::Symbol` citations, aligned the Mermaid diagram, and replaced line 188 em dashes with parentheses (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Top-level optional extra inference in `imported-transitive` mode (`OQ-01`) and owner provenance | Evaluate root imported distributions with `active_extra=""` (never guessing unrequested optional extras) and propagate explicit `pkg[extra]` edges, with `- Owner: plan author (binding upon plan approval)` | Prompt maintainer before review completion; include all installed optional extras (violates `w4hxkh` extra-honesty requirement) | `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:179-184`; backlog `w4hxkh`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | Transitive expansion queue state representation | Key `expanded_states` by `(normalized_name, active_extra)` (always enqueueing base `""` plus each individual normalized extra) | Key by `(normalized_name, frozenset_of_extras)` (can skip base requirements when first reached via `dep[extra]` and duplicates work across extra subsets) | PEP 508 single-extra evaluation model; `.aw/records/plans/pending/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md:118,125,139` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and all revised sections (`Goal`, diagram, `E-01`..`E-04`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred`, `Scope check`, `Required tests`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-04`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
