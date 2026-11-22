# Review findings: ipd 4gpguy

- Subject-Id: 4gpguy
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, Mermaid flowchart, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Goal` & `E-01`..`E-05` | Multi-clause 60-115 word sentences and unexpanded acronyms (`CSV`, `I/O`, `OS`, `CPU`, `CI`, `CLI`, `JSON`, `SHA-256`, `API`) | Split into concise complete sentences, expanded acronyms on first use, and standardized `python3` across validation commands | Technical writing requirements 1, 2, and 4 |
| `- Scope-Paths:`, `E-02`, `Proposed changes`, `V-02` | Omitted `benchmarks/aggregate.py`, omitted lazy `pubrun` import rule in `file_read.py`, omitted `_off_plus({"capture": {"file_io": {"level": ...}}})` scenario config, and ran `pytest benchmarks/test_benchmarks.py -v` without `-o addopts=""` or `benchmarks/test_share_safety.py` | Added `benchmarks/aggregate.py` (`_HOTPATH_BASELINE`, keeping legacy `hotpath-open-pubrun`), specified lazy `pubrun` import for `baseline` isolation and temp cleanup in `--measure-detail`, and updated benchmark pytest invocation with `-o addopts=""` and `benchmarks/test_share_safety.py` | Correctness and anti-regression (Check R1/R4) |
| `E-03`, `E-04`, `E-05`, `V-03`..`V-05` | Omitted `docs/performance.md#Representative results` placeholder protection, concurrent sibling-Set preservation, full `$defs.file_provenance_record` field list, `scripts/sanitize_paths.py --check --all`, `git status --short`, and diff-scoped dash checks | Added explicit `#Representative results` preservation + dedicated single-machine subsection, sibling-Set additive preservation, full `$defs.file_provenance_record` field coverage, `python3 scripts/sanitize_paths.py --check --all`, `git status --short`, and diff-scoped Python `U+2014`/`U+2013` checks | Cross-plan consistency, security/hygiene, and evidence feasibility (Check R2/R3/R7) |
| `Deferred / out of scope`, `Open questions`, `Validation and cross-check` | Deferred items lacked `- Carrier-Declined:` lines (`check.ipd-uncarried-obligation`), `Open questions` omitted reference to approved `vtkkn1` `OQ-01`/`OQ-02`, and line 152 contained two em dashes (`IPD-C802`) | Added `- Carrier-Declined:` lines, noted maintainer approval in `vtkkn1` `OQ-01`/`OQ-02`, and replaced the two em dashes on line 152 with parentheses | `steps/s5-questions.md` and zero `IPD-C802` advisories |
| `Approval and execution gate` | Single paragraph lacking structured 5-point execution contract and conditional runner vs standalone `aw ipd finalize` ownership | Replaced with complete 5-point Execution contract matching sibling reviewed plans (`xxi3nc`, `52dl55`, `98j0a3`, `hm32d9`) | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

1. Yes: updates `docs/functional_spec.md` public API contract, updates `benchmarks/scenarios.py` and `benchmarks/aggregate.py` benchmark scenario catalog consumed by `benchmarks/harness.py` and `schemas/benchmark.schema.json`, and reconciles `docs/api.md`, `docs/configuration.md`, `docs/manifest.md`, and `docs/performance.md`.
2. No: does not touch code guarding private data, commits, worktree isolation, merges to main, or the sandbox (benchmark environment disclosure hygiene is still verified under R3 via `scripts/sanitize_paths.py --check --all` and `benchmarks/test_share_safety.py`).
3. Yes: spans 5 execution items across 4 task groups and 9 Scope-Paths (`examples/`, `benchmarks/`, and 5 `docs/` files) plus whole-Set verification.
4. Yes: declares explicit `- Scope-Paths:` (updated from 8 to 9 paths to include `benchmarks/aggregate.py`).
5. Yes: missing `_HOTPATH_BASELINE` pairings drop overhead computation in `benchmarks/aggregate.py`, eager `pubrun` import in `file_read.py` corrupts `hotpath-open-baseline`, and overwriting `docs/performance.md#Representative results` or sibling-Set doc sections causes cross-Set regression.

AW-TIER: complex

### Step R1

- Checked: Verified every cited path, symbol, and convention against `.aw/records/backlog/graduated/20261121-pubrun-improve-01-x6alw4-file-provenance.backlog.md`, orchestrator `vtkkn1`, reviewed sibling plans `xxi3nc`, `52dl55`, `98j0a3`, and `hm32d9`, `examples/verify_all.py`, `examples/07_file_capture.py`, `benchmarks/workloads/file_read.py`, `benchmarks/scenarios.py`, `benchmarks/aggregate.py` (`_HOTPATH_BASELINE` lines 90-94), `benchmarks/harness.py` (`_build_child_command` lines 210-240), `benchmarks/test_benchmarks.py` (lines 1-13 `-o addopts=""` rule), `benchmarks/test_share_safety.py`, `schemas/benchmark.schema.json`, `pyproject.toml` (line 89 `addopts`), `tests/test_bench_command.py`, `docs/functional_spec.md` (section 14.1/14.3 lines 580-625), `docs/performance.md` (lines 19-24, 50-73), `docs/api.md`, `docs/configuration.md`, `docs/manifest.md`, and `src/pubrun/__init__.py` (`__all__`). Caught missing `benchmarks/aggregate.py` pairing, missing `-o addopts=""`, and `docs/performance.md#Representative results` placeholder contract (PR-001, PR-002, PR-003).

### Step R2

- Checked: Executed `aw ipd lint --phase author --agent` (exit 0, 0 errors, 0 warnings, 2 `IPD-C802` advisories cleared by PR-006), checked 1:1 `E-01`..`E-05` -> `V-01`..`V-05` bijection, `- Scope-Paths:` completeness, `- Item-Dependencies: executed:98j0a3, executed:hm32d9`, runtime-demonstration reachability (every runtime check is produced by `E-01`..`E-05` or existing `benchmarks/harness.py` / `examples/verify_all.py` / `scripts/sanitize_paths.py`), and `## Approval and execution gate`. Caught missing 5-point execution contract and uncarried deferred items (PR-004, PR-005).

### Step R3

- Checked: Full security and privacy rubric against `examples/12_external_file_provenance.py`, `benchmarks/workloads/file_read.py`, `benchmarks/scenarios.py`, `benchmarks/aggregate.py`, and `docs/*.md`.
  - No secrets, hardcoded credentials, network calls, benchmark uploads (`--contribute`/Gists), or HPC scheduler submissions.
  - Added explicit `python3 scripts/sanitize_paths.py --check --all`, `benchmarks/test_share_safety.py`, `git status --short`, and temp-file cleanup requirements (`--redacted-out /tmp/...` deletion and zero files left in `benchmarks/results/`) so local hostnames, usernames, and home paths cannot leak into `docs/performance.md` or tracked benchmark artifacts (PR-002).
  - Verified example and benchmarks operate exclusively on temporary local files cleaned up after execution and never patch `builtins.open`.

### Step R4

- Checked: Engineering rubric (Correctness, Architecture/Operability, Anti-regression, Testing/Verification, KISS/UX, Right-sizing, Spec/Doc sync).
  - **Correctness & Anti-regression:** Caught missing `benchmarks/aggregate.py::_HOTPATH_BASELINE` pairings (keeping legacy `"hotpath-open-pubrun"` so older `/5` accepted results still aggregate), lazy `pubrun` import requirement in `file_read.py` so `hotpath-open-baseline` stays unpolluted, and `-o addopts=""` requirement for `pytest benchmarks/test_benchmarks.py` (PR-001, PR-002).
  - **Spec & Doc sync:** Verified all five docs (`docs/api.md`, `docs/configuration.md`, `docs/manifest.md`, `docs/functional_spec.md`, `docs/performance.md`) cover every `$defs.file_provenance_record` field, `[capture.file_io]` budget key, section 14.1/14.3 API change, and single-machine benchmark subsection while preserving `## Representative results` and sibling-Set doc updates (PR-003).
  - **Right-sizing:** All 5 E-items map cleanly to distinct focused passes (example, benchmark suite + run, 3 reference docs, 2 spec/perf docs, whole-Set validation) with zero `src/pubrun/` edits.

### Step R5

- Checked: Evaluated through all eight reviewer personas (`QA/QC`, `Testing/Regression`, `UI/UX`, `Architect`, `Software Engineer`, `Power User`, `Novice`, `Stakeholder`) by reference to `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`.
  - **QA/QC & Testing/Regression:** Flagged missing `-o addopts=""` on `benchmarks/test_benchmarks.py`, missing `benchmarks/test_share_safety.py`, missing `scripts/sanitize_paths.py --check --all`, and un-paired hotpath scenarios in `benchmarks/aggregate.py` (PR-001, PR-002).
  - **Architect & Software Engineer:** Enforced lazy `pubrun` import in `file_read.py` for clean baseline isolation and additive doc updates compatible with concurrent Sets (`ckc3vl`, `3tvesf`, `zp2yyu`, `iflqsl`, `sdg31l`) (PR-001, PR-003).
  - **Novice & Power User:** Verified `examples/12_external_file_provenance.py` clearly contrasts verified vs caller-asserted vs pending-output registration without third-party dependencies, and `docs/api.md` separates `pubrun.artifact()` from `pubrun.register_*()`.
  - **Stakeholder:** Verified `docs/performance.md#Representative results` stays an honest multi-machine placeholder with single-machine numbers clearly labeled and zero unmeasured speedup claims (PR-003).

### Step R6

- Checked: Decomposition assessment. `4gpguy` is already Order 05 of Set `file-prov`, touches zero `src/pubrun/` application files, and has 5 cohesive E-items (example, benchmark, 3 reference docs, 2 spec/perf docs, whole-Set validation) across 9 tightly related Scope-Paths. Splitting further would create artificial overhead without reducing risk. No split recommended.

### Step R7

- Checked: Cross-plan consistency across Set `file-prov` (`vtkkn1`, `xxi3nc`, `52dl55`, `98j0a3`, `hm32d9`, `4gpguy`) and concurrent Sets touching `docs/` (`startup-perf`/`ckc3vl`, `timing-acc`/`3tvesf`, `cap-isolation`/`zp2yyu`, `dep-capture`/`iflqsl`, `repro-check`/`sdg31l`).
  - `- Item-Dependencies: executed:98j0a3, executed:hm32d9` matches `vtkkn1` Order 05 and transitively ensures `xxi3nc` and `52dl55` are executed.
  - All API signatures (`register_file`, `register_input`, `register_output`), config keys (`[capture.file_io].max_total_hash_bytes`, `max_total_hash_seconds`, `hash_algorithm`), and manifest fields (`$defs.file_provenance_record`, `data_files.mixed`, `data_files.hashing_summary`) align with reviewed plans `xxi3nc`, `52dl55`, `98j0a3`, and `hm32d9` (PR-003).
  - Concurrent-Set additive doc preservation rules added explicitly to `E-03` and `E-04` (PR-003).

### Step S5

- Checked: Audited `Open questions` (none; API/config/manifest names approved by maintainer on 2026-11-21 in `vtkkn1` `OQ-01`/`OQ-02`), both deferred items, and all 6 review findings. Every finding had Low remediation risk and was fixed in place. Added `- Carrier-Declined:` lines to both deferred items (clearing `check.ipd-uncarried-obligation`). Zero open or blocking questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | UNDER-SCOPE | R4/R1/R7 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:7,58-61,107-116`, `benchmarks/aggregate.py:90-94`, `benchmarks/harness.py:210-240` | Replacing `hotpath-open-pubrun` in `benchmarks/scenarios.py` with five new `hotpath-*` scenarios without updating `benchmarks/aggregate.py::_HOTPATH_BASELINE` leaves all five scenarios with `overhead_ms = None` and `overhead_pct = None`. In addition, `E-02` did not specify lazy `pubrun` import in `benchmarks/workloads/file_read.py` (required so `hotpath-open-baseline` never imports `pubrun`), `_off_plus({"capture": {"file_io": {"level": ...}}})` scenario configs, or temporary directory cleanup in `--measure-detail`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `benchmarks/aggregate.py` to `- Scope-Paths:`, `E-02`, `Proposed changes`, and `V-02` (pairing all five new scenarios to `hotpath-open-baseline` while keeping legacy `"hotpath-open-pubrun"`), and specified lazy `pubrun` import, `_off_plus` scenario configs, and temp cleanup in `--measure-detail` (recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R2/R3/R4 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:60,77-80,138,160,165,170,175`, `benchmarks/test_benchmarks.py:8-13`, `pyproject.toml:89` | Benchmark tests omitted `-o addopts=""` (needed to clear `pyproject.toml` `--cov=src` addopts) and `benchmarks/test_share_safety.py`; whole-Set validation omitted `python3 scripts/sanitize_paths.py --check --all`, `git status --short`, and temp `--redacted-out` cleanup / non-publishing guard; and `V-03`/`V-04` lacked a diff-scoped Python check over added (`+`) lines for `U+2014`/`U+2013` dashes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02`, `E-05`, `Required tests / validation`, and `V-02`..`V-05` to run `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`, `python3 scripts/sanitize_paths.py --check --all`, `git status --short`, temp `--redacted-out` cleanup, and diff-scoped Python dash checks (recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R7/R4 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:67,72,118-120`, `docs/performance.md:23,50-73`, `.aw/records/plans/pending/20261121-file-prov-01-xxi3nc-file-provenance-engine-hashing-guarantees-and-proxy-hardenin.ipd.md:137-138` | `E-04` did not preserve `docs/performance.md#Representative results` as a multi-machine `_TBD_` placeholder, `E-03`/`E-04` did not guard additive coexistence with concurrent sibling Sets editing the same five docs (`ckc3vl`, `3tvesf`, `zp2yyu`, `iflqsl`, `sdg31l`), and `E-03` omitted several `$defs.file_provenance_record` fields defined in `xxi3nc` (`role`, `label`, `open_disposition`, `registration_source`, `entry_type`, `hash_status_detail`, `hash_algorithm`, `change_details`, `registration_count`, `registered_before_creation`, `metadata`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-03`, `E-04`, `Proposed changes`, `V-03`, and `V-04` to keep `#Representative results` as `_TBD_` with a dedicated single-machine subsection, require additive preservation of sibling-Set doc sections, and enumerate all `$defs.file_provenance_record` fields (recommendation strength: very strong). |
| PR-004 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:179-184`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-36` | `## Approval and execution gate` was a single paragraph lacking the required 5-point execution contract (prerequisite gate, scope declaration with `--scope-reason`/`--scope-ack`, HARD MUST honesty rule, path-scoped `aw commit` + never-push, and conditional runner vs standalone `aw ipd finalize 4gpguy` forbidding raw `git mv`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the complete 5-point Execution contract matching reviewed sibling plans `xxi3nc`, `52dl55`, `98j0a3`, and `hm32d9` (recommendation strength: very strong). |
| PR-005 | MEDIUM | IN-SCOPE | S5/R2 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:125-128,146-148`, `.aw/system/workflows/plan-review/steps/s5-questions.md:79-91` | Both items in `## Deferred / out of scope (with reason)` lacked `- Carrier-Declined:` lines (flagged by `check.ipd-uncarried-obligation`), and `## Open questions` did not cross-reference maintainer approval in `vtkkn1` `OQ-01`/`OQ-02`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `- Carrier-Declined:` lines to both deferred items and cited `vtkkn1` `OQ-01`/`OQ-02` maintainer approval in `## Open questions` (recommendation strength: very strong). |
| PR-006 | LOW | IN-SCOPE | Check P/R1 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:28,53,60,67,72,79,152` | `Goal` and `E-01`..`E-05` used 60-115 word sentences, acronyms (`CSV`, `I/O`, `OS`, `CPU`, `CI`, `CLI`, `JSON`, `SHA-256`, `API`) were unexpanded on first use, commands mixed `python` and `python3`, and line 152 contained two em dashes (`IPD-C802`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split long sentences, expanded acronyms on first use, standardized `python3`, and replaced the two em dashes on line 152 with parentheses (recommendation strength: strong). |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against Round 1 edits. Because `- Scope-Paths:` was updated to add `benchmarks/aggregate.py` (PR-001), a second pass (`Round 2`) is required per `steps/s6-rereview.md` rule 1 before finalizing.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: Re-read the complete revised `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12). Confirmed the Mermaid diagram matches `E-01`..`E-05` (including `benchmarks/aggregate.py` in `E-02` and `sanitize_paths.py` in `E-05`), all acronyms are expanded on first use, and zero `IPD-C802` em/en dash advisories remain.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| (none) | - | No further edits needed in Round 2. | All Round 1 revisions verified clean. |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain. | None | None | very strong |

### Step R1

- Checked: Verified `benchmarks/aggregate.py` addition across `- Scope:`, `- Scope-Paths:`, Mermaid diagram, `E-02`, `Project conventions`, `Findings`, `Proposed changes`, `Scope check`, `V-02`, and `Approval and execution gate` item 2. All references are consistent and grounded in `benchmarks/aggregate.py:90-94`.

### Step R2

- Checked: Verified `aw ipd lint --phase review-finalize --agent` exits 0 with 0 findings on the revised plan, `- Scope-Paths:` lists all 9 modified/created files consistently across front matter and execution gate, `E-01`..`E-05` map 1:1 to `V-01`..`V-05`, and `check.ipd-uncarried-obligation` is clear.

### Step R7

- Checked: Verified revised `4gpguy` aligns cleanly with `vtkkn1` and reviewed sibling plans `xxi3nc`, `52dl55`, `98j0a3`, and `hm32d9`, and preserves additive coexistence with concurrent documentation plans (`ckc3vl`, `3tvesf`, `zp2yyu`, `iflqsl`, `sdg31l`).

### Step S5

- Checked: Zero new open questions, ambiguities, or uncarried obligations introduced by Round 1 edits.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | UNDER-SCOPE | R4/R1/R7 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:7,58-61,107-116`, `benchmarks/aggregate.py:90-94`, `benchmarks/harness.py:210-240` | Missing `benchmarks/aggregate.py::_HOTPATH_BASELINE` pairings, lazy `pubrun` import rule in `file_read.py`, `_off_plus` scenario configs, and `--measure-detail` temp cleanup. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Fixed in Round 1 and verified swept across all plan sections in Round 2 (recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R2/R3/R4 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:60,77-80,138,160,165,170,175`, `benchmarks/test_benchmarks.py:8-13`, `pyproject.toml:89` | Missing `-o addopts=""`, `benchmarks/test_share_safety.py`, `scripts/sanitize_paths.py --check --all`, `git status --short`, temp `--redacted-out` cleanup, and diff-scoped dash checks. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Fixed in Round 1 and verified in Round 2 (recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R7/R4 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:67,72,118-120`, `docs/performance.md:23,50-73`, `.aw/records/plans/pending/20261121-file-prov-01-xxi3nc-file-provenance-engine-hashing-guarantees-and-proxy-hardenin.ipd.md:137-138` | Missing `#Representative results` placeholder protection, concurrent sibling-Set preservation, and complete `$defs.file_provenance_record` field enumeration. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Fixed in Round 1 and verified in Round 2 (recommendation strength: very strong). |
| PR-004 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:179-184`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-36` | Incomplete single-paragraph execution gate missing 5-point execution contract and conditional `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Fixed in Round 1 and verified in Round 2 (recommendation strength: very strong). |
| PR-005 | MEDIUM | IN-SCOPE | S5/R2 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:125-128,146-148`, `.aw/system/workflows/plan-review/steps/s5-questions.md:79-91` | Uncarried deferred items (`check.ipd-uncarried-obligation`) and missing reference to maintainer approval in `vtkkn1` `OQ-01`/`OQ-02`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Fixed in Round 1 and verified in Round 2 (recommendation strength: very strong). |
| PR-006 | LOW | IN-SCOPE | Check P/R1 | `.aw/records/plans/pending/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md:28,53,60,67,72,79,152` | Long run-on sentences, unexpanded acronyms, mixed `python`/`python3`, and two `IPD-C802` em dashes on line 152. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Fixed in Round 1 and verified in Round 2 (recommendation strength: strong). |

### Step S6

- Checked: Round 2 required zero further edits; no `E-*` or `V-*` items, `- Scope-Paths:`, or `- Item-Dependencies:` changed in Round 2, and all findings are `FIXED`.

AW-REVIEW: DONE
