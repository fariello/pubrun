# Review findings: ipd uil22c

- Subject-Id: uil22c
- Subject-Type: ipd
- Reviewed-At: 2026-11-21
- Reviewer: Antigravity/Gemini
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R4.A / R4.D | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:121`, `tests/test_edge_cases.py::TestPackagesNullName.test_none_name_yields_partial_not_crash:101-120` | `_environment_fingerprint()` did not include `importlib.metadata.distributions` identity, so monkeypatching `importlib.metadata.distributions` in tests without changing `sys.path` or mtimes would hit a stale cache; minimal mocks like `FakeDist` also lack `.files` and `.requires`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `id(importlib.metadata.distributions)` to `_environment_fingerprint()` and required defensive `getattr` access for optional `Distribution` attributes inside per-distribution `try/except`. |
| PR-002 | HIGH | IN-SCOPE | R4.A / R4.C | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:75,127,171` | Proposed changes suggested calling `packages_distributions()` alongside the `_DistributionIndex` pass over `distributions()`, which scans site-packages twice on Python 3.10+ and violates E-01's single-scan invariant; naive `dist.files` parsing also failed to exclude `..` traversal entries (present in `pubrun`'s own editable `RECORD`), `.pth` files, and multi-suffix extension tags, and did not deduplicate duplicate or symlinked `sys.path` entries or preserve first-wins precedence in `by_normalized_name`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified a single pass over `importlib.metadata.distributions()` on Python 3.8 through 3.14 mirroring CPython's `top_level.txt` then `dist.files`/`inspect.getmodulename` inference, deduplicating identical distributions, preserving first-wins `sys.path` precedence via `setdefault`, and verifying parity with `packages_distributions()` plus resilience when it is absent. |
| PR-003 | HIGH | IN-SCOPE | R4.A / R4.D | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:116,124,157`, `schemas/manifest.schema.json` (`$defs.capture_state:261`, `$defs.package_record:842`) | `schemas/manifest.schema.json` requires `package_record.name` and `capture_state.detail` to be non-nullable strings (`"type": "string"`). Emitting `name: None` for corrupt metadata or `detail: None` in `capture_state` would fail `tests/test_manifest_schema.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required omitting `Name is None` distributions from `records` (recording them in `unresolved` and `capture_state.warnings` with `status="partial"`, while keeping the null-safe sort key) and omitting `"detail"` from `capture_state` unless a non-empty string is set. |
| PR-004 | HIGH | IN-SCOPE | R1 / R4.D | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:102,150,189,220,225`, `tests/test_new_features.py::TestImportedTransitiveMode.test_transitive_deps_discovered:55-71` | `TestImportedTransitiveMode` monkeypatches `importlib.metadata.distribution` with `MockDist` defining only `.requires` alongside mocked `version()`, so reading `.metadata` or `.version` without fallback would raise `AttributeError`; `tests/test_new_features.py` was also omitted from `Required tests / validation`, `V-03`, and `V-04`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified defensive fallback in direct `distribution(top)` / `version(top)` lookup and added `tests/test_new_features.py` to `Required tests / validation`, `V-03`, and `V-04`. |
| PR-005 | HIGH | UNDER-SCOPE | R2 / R4.E | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:87,154-155,161-174,220` | `E-03` implements new `top-level-installed` root filtering and `V-03` claims to verify it, but no test in `tests/test_capture_engines.py` or `E-04` exercised `top-level-installed`; the algorithm also did not exclude self-requirements (`pkg[all]`) or extra-gated requirements. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified self-requirement and extra-marker exclusion for `top-level-installed`, added a dedicated `top-level-installed` fixture test in `E-04` and Proposed changes #4, and included it in `V-03`. |
| PR-006 | HIGH | IN-SCOPE | R2 / S7 | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:236,239` | Execution contract item 2 instructed the executor to `STOP and report` if more files were needed (violating the 2026-09-01 scope-fence ruling), and item 5 unconditionally instructed the executor to run the lifecycle transition without distinguishing runner-owned finalization from manual execution. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote Execution contract items 2 and 5 to use finalize-time scope justification (`--scope-reason`/`--scope-ack`) and conditional runner/executor finalize ownership (`aw ipd finalize`, never hand-rolled `git mv`). |
| PR-007 | MEDIUM | IN-SCOPE | R4.A | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:125,134-148,171` | Underspecified edge cases: generated standard-library modules (`_sysconfigdata__*`) are absent from `sys.stdlib_module_names` on Python 3.10+ (requiring path checks on all versions with boundary-safe `os.path.commonpath` and `frozen`/`built-in` origin checks); `_is_site_packages_path` needed exact path-component checks; PEP 420 disambiguation needed concrete `__file__`/`__spec__.origin` priority over shared `_NamespacePath`; lazy module proxies needed `_safe_getattr`; `direct_url.json` parsing needed `isinstance(data, dict)`; and mtime invalidation testing needed `os.utime` for determinism. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified all five runtime safeguards and deterministic `os.utime` mtime testing in Proposed changes #2, #3, and #4 and `E-04`. |
| PR-008 | MEDIUM | IN-SCOPE | R3 | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:125,148,152` | PEP 610 `direct_url.json` `"url"` fields can contain embedded VCS or archive credentials; the plan did not prohibit emitting or logging raw `url` strings. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added an explicit security requirement in Proposed changes #2, `E-02`, and `E-04` forbidding echoing `direct_url.json` `"url"` values into `location`, `detail`, or `warnings`. |
| PR-009 | MEDIUM | IN-SCOPE | R7 | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:103,104,116,124,178-180`, `ijipnx:133`, `fdqkrz:97,123`, `tusvtd:58-60` | Cross-plan contract mismatches: line 104 named the snapshot helper `capture_packages_snapshot()` instead of `resolve_packages_snapshot()`, Proposed changes #1 declared unused parameters (`resolver=None, include_extended_fields=True`), `missing_metadata`/`metadata_error` unresolved entries lacked the exact dictionary shape required by `ijipnx`, upgrade-in-place behavior if `tusvtd` lands first was unstated, and the three deferred rows lacked explicit `- Carrier: <id6>` lines (`check.ipd-uncarried-obligation`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Standardized on `resolve_packages_snapshot(config)` and `_get_distribution_index(use_cache=True)`, specified exact `unresolved` record fields matching `ijipnx`, documented upgrade-in-place compatibility if `tusvtd` lands first, and added `- Carrier: fdqkrz`, `- Carrier: ijipnx`, and `- Carrier: iflqsl` to the three deferred rows. |
| PR-010 | MEDIUM | IN-SCOPE | S5 | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:202` | `OQ-01` carried `- Status: resolved` with `- Owner: maintainer (confirmed upon plan approval)` despite no human answer having been recorded, violating `steps/s5-questions.md` rule 5. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Changed `OQ-01` `- Owner:` to `plan author` and recorded reversible decision `D-1` in `### Decisions`. |
| PR-011 | LOW | IN-SCOPE | Check P | `.aw/records/plans/pending/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md:38-65,87,99-102,127,137,207` | Technical writing and diagram drift: flowchart routed uncached fallback to cached metadata read and used `stdlib` shorthand; ER diagram used `DIST_ENTRY` instead of `DIST_INFO`/`_DistInfo`; informal code references instead of `path::Symbol`; exclamation marks in technical prose; and two `IPD-C802` em-dash advisories on line 207. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Synchronized diagrams with normative text, normalized code citations to `path::Symbol`, removed shorthand and exclamation marks, and eliminated the two `IPD-C802` em-dash advisories. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should `top-level-installed` compute top-level installed distributions without shelling out to `pip` or `conda` (`OQ-01`)? | Compute installed distributions not required by any other installed distribution via `importlib.metadata.distributions()`, excluding self-requirements and `extra ==` marker requirements, with `Owner: plan author` (binding on human approval). | Keep `top-level-installed` identical to `full-environment` (untruthful alias); shell out to `pip`/`conda` (violates `w4hxkh` offline/lightweight stdlib constraint and existing `src/pubrun/capture/packages.py:111`). | `w4hxkh` Context and execution boundary; `src/pubrun/capture/packages.py::get_packages:18-26,109-130`; no existing caller or test depends on the prior alias behavior. | yes |

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Flowchart (`## Goal`) | Routed direct metadata lookup fallback (`J`) to `F` ("Read cached distribution metadata") and used `stdlib` shorthand. | Routed `J` to uncached fallback node `J1`, aligned labels with `_DistributionIndex` / `_DistInfo`, and replaced `stdlib` with `standard-library`. | Technical writing requirements 4 and 12(d)/(e): diagram must match normative text and use identical terminology. |
| ER diagram (`## Goal`) | Named entities `CACHE_FINGERPRINT`, `DIST_ENTRY`, `MODULE_MAPPING`. | Renamed to `ENVIRONMENT_FINGERPRINT`, `DIST_INFO`, `MODULE_TO_DISTS` matching `_environment_fingerprint`, `_DistInfo`, and `module_to_dists`. | Technical writing requirement 12(e): consistent entity naming between diagram and text. |
| `## Project conventions discovered` | Referred to `capture_packages_snapshot()` and used informal symbol references (`test_edge_cases.TestPackagesNullName`). | Standardized on `resolve_packages_snapshot()` and canonical `path::Symbol` citations (`tests/test_edge_cases.py::TestPackagesNullName.test_none_name_yields_partial_not_crash`, etc.). | Technical writing requirement 4 and `p-proofread.md` Section 11.1 code citation rules. |
| `## Proposed changes` & `## Validation and cross-check` | Contained exclamation marks (lines 127, 137) and two em dashes in the validation note (line 207, `IPD-C802`). | Replaced exclamation marks with periods and replaced the em dashes with parentheses. | Technical writing requirement 8 (direct tone) and zero `IPD-C802` lint advisories. |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | All material ambiguities found during proofreading were resolved directly from repository evidence and fixed in place. | None | None | strong |

### Step T

1. Yes: the plan changes `src/pubrun/capture/packages.py` public and shared contracts (`get_packages`, `resolve_packages_snapshot`, `normalize_package_name`, `invalidate_package_cache`, `get_installed_distribution_versions`) relied upon by sibling plans `fdqkrz`, `ijipnx`, `iflqsl` (Set `dep-capture`) and `tusvtd` (Set `repro-check`).
2. No: it does not touch leak-sanitizer, commit, worktree-isolation, merge-to-main, or sandbox guard code (though `direct_url.json` privacy is still audited in R3).
3. No: 4 E-items across 3 task groups and 3 `Scope-Paths` (1 production file and 2 test files), though it anchors a 4-child Set and coordinates across two Sets.
4. Yes: `- Scope-Paths:` explicitly lists `src/pubrun/capture/packages.py, tests/test_capture_engines.py, tests/test_package_resolution.py`.
5. Yes: regressions in `get_packages()` can crash `Run._bootstrap_engines()` (demoting runs to ghost mode), violate `schemas/manifest.schema.json` (`additionalProperties: false`), trigger unintended module imports, or break downstream `dep-capture` and `repro-check` plans.

AW-TIER: complex

### Step R1

- Checked: `src/pubrun/capture/packages.py`, `schemas/manifest.schema.json` (`$defs.capture_state`, `$defs.package_record`, `$defs.packages_section`), `pyproject.toml`, `tests/test_capture_engines.py`, `tests/test_edge_cases.py`, `tests/test_new_features.py`, `tests/test_manifest_schema.py`, `src/pubrun/report/meta_snapshot.py`, `src/pubrun/resources/default.toml`, `docs/configuration.md`, `.aw/records/backlog/graduated/20261121-pubrun-improve-01-w4hxkh-dependency-capture.backlog.md`, and live Python 3.14 `importlib.metadata` behavior (`packages_distributions`, `_top_level_inferred`, `_get_toplevel_name`, `pubrun`'s editable `RECORD`, and `sys.modules` vs `sys.stdlib_module_names`).
- Verified findings PR-001 through PR-004 directly against `tests/test_edge_cases.py`, `tests/test_new_features.py`, `schemas/manifest.schema.json`, and CPython's `importlib.metadata` source.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-04` to `V-01..V-04`), `- Scope-Paths:`, `- Item-Dependencies: none`, concrete non-tautological evidence in every `V-*`, runtime-demonstration reachability (all `V-*` items are test-result demands reachable via `E-04` and existing test suites), and `## Approval and execution gate` execution contract.
- Fixed missing `tests/test_new_features.py` and `top-level-installed` test coverage (PR-004, PR-005) and fixed scope-fence `STOP` wording and unconditional finalize wording (PR-006).

### Step R3

- Checked: trust-boundary inputs (`dist.metadata`, `direct_url.json`, `RECORD`, `sys.modules` lazy proxies), no secrets hardcoded, no network or subprocess calls, no dynamic imports, and error/warning minimization.
- Added explicit prohibition against emitting or logging raw `direct_url.json` `"url"` strings to prevent accidental credential leakage from private VCS/archive installs (PR-008).

### Step R4

- Checked: correctness and data integrity (concurrency, deduplication, precedence, schema non-nullable types), architecture and operability (single-pass caching, no dead parameters, Python 3.8 through 3.14 stdlib-only parity), anti-regression (`TestPackagesNullName`, `TestImportedTransitiveMode`, `TestPackages`, `test_manifest_schema`), testing completeness, KISS and fallback guiding principles, right-sizing and conceptual density (4 cohesive E-items across 1 small module and 2 test files; no split needed), and `## Spec / documentation sync` truthfulness (schema delegated to `ijipnx`, docs to `iflqsl`).
- Resolved PR-001, PR-002, PR-003, PR-005, and PR-007 in place.

### Step R5

- Checked: all eight reviewer personas against `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`.
  - QA/QC: surfaced cache-bypass on monkeypatched `distributions`, `MockDist` fallback hazard, non-nullable schema fields, `..` in editable `RECORD`, and `_sysconfigdata__*` stdlib-path gap on Python 3.10+.
  - Testing/regression: surfaced missing `tests/test_new_features.py` and `top-level-installed` validation and deterministic `os.utime` mtime testing.
  - UI/UX: ensured warnings and unresolved `detail` strings stay concise and name modules and candidate distributions clearly.
  - Architect: eliminated double-scan of `distributions()` + `packages_distributions()`, removed dead `resolver` parameter, enforced first-wins `sys.path` precedence and duplicate path deduplication, and documented `tusvtd` upgrade-in-place compatibility.
  - Software engineer: added `_safe_getattr`, `_path_is_within`, `Path.parts` site-packages checks, `isinstance(data, dict)` guard on `direct_url.json`, and self-requirement exclusion in `top-level-installed`.
  - Power user: preserved low-overhead fingerprinted cache, explicit `invalidate_package_cache()`, and zero-import custom finder support.
  - Novice: confirmed standard-library and local script modules never falsely degrade `capture_state` to `partial`.
  - Stakeholder: verified full alignment with `w4hxkh` constraints (zero runtime dependencies, Python 3.8 through 3.14, offline, no import hook, host crash immunity).

### Step R6

- Checked: decomposition and sizing of `uil22c`.
- Verdict: no split needed. `uil22c` is already Child 01 of the 4-child Set `dep-capture` (`6s7k9e`), modifies 1 production module (`src/pubrun/capture/packages.py`) plus 2 test files, and partitions cleanly into 4 sequential, single-concern E-items (`E-01` indexing/caching, `E-02` edge-case resolution, `E-03` `get_packages()` mode wiring, `E-04` deterministic fixture tests).

### Step R7

- Checked: Set `dep-capture` orchestrator `6s7k9e`, sibling children `fdqkrz` (`Order: 2`), `ijipnx` (`Order: 3`), `iflqsl` (`Order: 4`), and cross-Set consumer `repro-check` child `tusvtd` (`Order: 2`).
- Reconciled `resolve_packages_snapshot()` and `_get_distribution_index()` naming with `fdqkrz`, aligned `unresolved` entry dictionaries with `ijipnx`'s `$defs.unresolved_package_record`, and documented upgrade-in-place compatibility with `tusvtd` (PR-009). Note: `uil22c` runs a superset of the test files listed in orchestrator `6s7k9e` line 122 (adding `tests/test_manifest_schema.py` and `tests/test_new_features.py`), which strengthens validation without altering `6s7k9e` (out of this review's scope ledger).

### Step S5

- Checked: `OQ-01` and all review findings PR-001 through PR-011.
- All 11 findings were fixed in place (Low Remediation Risk); zero `OPEN` or `DEFERRED` findings remain. Fixed `OQ-01` `- Owner:` from `maintainer (confirmed upon plan approval)` to `plan author` and recorded reversible decision `D-1` (`Reversible: yes`) in `### Decisions` (PR-010). No blocking human decisions remain.
