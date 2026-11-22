# IPD: External file registration and explicit hashing guarantees

- Date: 2026-11-21
- Kind: orchestrator
- Concern: Explicit external file registration, explicit hashing outcomes and budgets, file-change detection, streaming-hash evaluation, report honesty, and benchmarks for backlog item `x6alw4`
- Scope: Orchestrate five child plans implementing the core file-provenance engine and proxy hardening, explicit external file registration, import-mode application programming interface (API) parity, report and check evidence distinction, and example, benchmark, documentation, and whole-Set verification for backlog item `x6alw4`.
- Scope-Paths: .aw/records/plans/pending/20261121-file-prov-00-vtkkn1-external-file-registration-and-explicit-hashing-guarantees.ipd.md
- Item-Dependencies: executed:xxi3nc, executed:52dl55, executed:98j0a3, executed:hm32d9, executed:4gpguy
- Status: reviewed
- Readiness: go-pending-approval
- Review-Depth: orchestrator
- Coverage: pass
- Coverage-Fingerprint: e8fd48e6a8949ccf1d54b6d1104a9301ffc5a1f988f1d87f883cbff76a11bd6b
- Coverage-Checked: 2026-11-22 by uri/its_direct/pt3-claude-opus-5.5-1m-us
- Short-Description: Orchestrate file provenance engine, explicit registration API, mode parity, report honesty, and benchmarks/docs
- Work-Kind: feature
- Priority: medium
- From-Backlog: x6alw4
- Set: file-prov
- Order: 0
- Highest E allocated: 05
- Author: agent
- Id: vtkkn1

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 /plan-review (Gemini 4 Neon (High)): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004
- 2026-11-22 coverage pass (aw oc run): fingerprint e8fd48e6a894, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-22 coverage pass (aw oc run): fingerprint 594ad82ba254, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-21 to-review (agent): authored orchestrator plan `vtkkn1` for Set `file-prov` graduating backlog item `x6alw4`.

## Goal

Deliver graduated backlog item `x6alw4` (`.aw/records/backlog/graduated/20261121-pubrun-improve-01-x6alw4-file-provenance.backlog.md`) through five ordered, independently verifiable child plans. Together, these plans let users register external input and output files without replacing library input/output (I/O), and record explicit hashing outcomes, budgets, evidence strength, and file-change detection across both `pubrun.open()` and explicit registration. They also distinguish identified paths from verified content in reports and validate overhead with reproducible benchmarks. All five child plans preserve one-import adoption, the Python 3.8+ standard-library runtime, optional capture, host-program behavior and exceptions, redaction, all six import modes, offline operation, and no global `builtins.open` monkeypatch.

### Plan Set dependency flow

This diagram summarizes the execution order of the five child plans. The text and table below are normative.

```mermaid
flowchart TD
    C1["xxi3nc: File provenance engine, budgets, change detection, schema, and proxy hardening"] --> C2["52dl55: Explicit external file registration API and lifecycle semantics"]
    C2 --> C3["98j0a3: Import-mode API parity across all six modes"]
    C2 --> C4["hm32d9: Report, inspect, and methods evidence distinction"]
    C3 --> C5["4gpguy: Example, stat-vs-hash benchmarks, docs sync, and whole-Set verification"]
    C4 --> C5
    C5 --> O0["vtkkn1: Set complete"]
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Confirm child IPD execution

- [ ] E-01 CONFIRM xxi3nc REACHED executed
  - Depends on: none
  - Expected outcome: Child plan `xxi3nc` (`20261121-file-prov-01-xxi3nc-file-provenance-engine-hashing-guarantees-and-proxy-hardenin.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-02 CONFIRM 52dl55 REACHED executed
  - Depends on: E-01
  - Expected outcome: Child plan `52dl55` (`20261121-file-prov-02-52dl55-explicit-external-file-registration-api-and-lifecycle-semant.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-03 CONFIRM 98j0a3 REACHED executed
  - Depends on: E-02
  - Expected outcome: Child plan `98j0a3` (`20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-04 CONFIRM hm32d9 REACHED executed
  - Depends on: E-02
  - Expected outcome: Child plan `hm32d9` (`20261121-file-prov-04-hm32d9-report-inspect-and-methods-file-provenance-evidence-distinct.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-05 CONFIRM 4gpguy REACHED executed
  - Depends on: E-03, E-04
  - Expected outcome: Child plan `4gpguy` (`20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

## Child IPDs, sequence, and dependencies

| Order | Id | File | What it does | Depends on |
|---|---|---|---|---|
| 01 | `xxi3nc` | `20261121-file-prov-01-xxi3nc-file-provenance-engine-hashing-guarantees-and-proxy-hardenin.ipd.md` | Builds `src/pubrun/capture/file_io.py`, adds run-wide hashing budgets in `src/pubrun/resources/default.toml`, fixes and extends `data_files` in `schemas/manifest.schema.json`, hardens `ProvenanceFileProxy` with change detection, mixed-mode classification, lazy Python Enhancement Proposal (PEP) 562 loading, and safe sequential-binary streaming evaluation, and adds unit and schema tests. | none |
| 02 | `52dl55` | `20261121-file-prov-02-52dl55-explicit-external-file-registration-api-and-lifecycle-semant.ipd.md` | Adds `pubrun.register_file()`, `pubrun.register_input()`, and `pubrun.register_output()` with logical labels, asserted versus verified caller digests (`verify_digest=True` match, mismatch, and unsupported algorithm handling), pending pre-creation outputs, `level="name"` no-stat handling, deduplication, Ghost Mode and edge-case handling, and tests while keeping `pubrun.artifact()` unchanged. | 01 |
| 03 | `98j0a3` | `20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md` | Re-exports `register_file`, `register_input`, and `register_output` across all six import-mode modules (`auto`, `full`, `noauto`, `nopatch`, `noconsole`, `minimal`) with both alias and parent-package parity, preserves `pubrun.report` subpackage integrity and lazy `file_io` import, and extends `tests/test_import_modes.py` parity and hook-free subprocess tests. | 02 |
| 04 | `hm32d9` | `20261121-file-prov-04-hm32d9-report-inspect-and-methods-file-provenance-evidence-distinct.ipd.md` | Updates `src/pubrun/report/checks.py`, `src/pubrun/report/diagnostics.py`, `src/pubrun/report/methods.py`, `docs/cli.md`, and report tests so `pubrun inspect`, `pubrun show`, and `pubrun methods` distinguish identified paths, asserted digests, verified hashes (including non-Secure Hash Algorithm 256-bit (SHA-256) digests), pending outputs, over-budget skips, failures, and changed files with `NO_COLOR` accessibility and sibling-Set coexistence. | 02 |
| 05 | `4gpguy` | `20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md` | Adds dependency-free example `examples/12_external_file_provenance.py`, updates `benchmarks/workloads/file_read.py`, `benchmarks/scenarios.py`, and `benchmarks/aggregate.py` for stat-versus-hash latency and extra-bytes-read measurements, reconciles API/config/manifest/functional-spec/performance docs (preserving `docs/performance.md#Representative results` as `_TBD_` with zero added em or en dashes), and runs whole-Set validation. | 03, 04 |

## Completion criteria (the whole Set is done only when)

- Every `data_files` record produced by `pubrun.open()` carries explicit `hash_status`, `hash_status_detail`, `hash_algorithm`, `digest`, `observation_time`, `evidence_source`, `evidence_strength`, `role`, and `change_detected` fields, and validates against `schemas/manifest.schema.json`. It honors per-file and run-wide byte/time hashing budgets (proven with a large sparse fixture or mocked reader without creating large files), detects observable identity/metadata changes between open, close, and hash, classifies `r+`/`w+`/`a+`/`x+` as mixed access (`data_files.mixed`), evaluates streaming hashing only for sequential binary streams without substituting a stream-of-reads hash for a whole-file digest, and preserves host exceptions without patching `builtins.open`. Owner: `xxi3nc`
- Explicit external file registration (`pubrun.register_file()`, `pubrun.register_input()`, `pubrun.register_output()`) records local paths with role, optional logical label, and optional caller-supplied digest (treated as asserted evidence unless explicitly verified via `verify_digest=True`). It supports pre-creation and post-creation output registration, deterministic deduplication, and honest handling of missing files, directories, symlinks, special files, Ghost Mode, and out-of-scope remote Uniform Resource Identifiers (URIs) while keeping `pubrun.artifact()` unchanged as a run-internal file writer and adding zero third-party runtime dependencies. Owner: `52dl55`
- All six import-mode modules (`auto`, `full`, `noauto`, `nopatch`, `noconsole`, `minimal`) expose `register_file`, `register_input`, and `register_output` on both the mode alias and parent `pubrun` package namespace identically to root `import pubrun`, preserve `pubrun.report` subpackage integrity and lazy `pubrun.capture.file_io` import, and add no global `builtins.open` patch. Owner: `98j0a3`
- `src/pubrun/report/checks.py`, `src/pubrun/report/diagnostics.py`, `src/pubrun/report/methods.py`, and `docs/cli.md` clearly distinguish verified content hashes (including non-SHA-256 digests) from caller-asserted digests, path/metadata-only registrations, pending outputs, over-budget skips, failed or unavailable hashes, and changed files, with `NO_COLOR` accessibility, byte-identical `methods` output for empty `data_files`, and `import pubrun` isolated from `pubrun.report.checks`. Owner: `hm32d9`
- Dependency-free example `examples/12_external_file_provenance.py` and updated stat-versus-hash benchmarks (`benchmarks/workloads/file_read.py`, `benchmarks/scenarios.py`, `benchmarks/aggregate.py`) report close-time or registration latency and extra bytes read with full environment, revision, workload, baseline, repetitions, cold/warm passes, and dispersion. Reconciled documentation (`docs/api.md`, `docs/configuration.md`, `docs/manifest.md`, `docs/functional_spec.md`, `docs/performance.md`, preserving `#Representative results` as `_TBD_` with zero added em or en dashes), `python3 scripts/sanitize_paths.py --check --all`, and the full test, example, and benchmark-test suites pass with captured output. Owner: `4gpguy`

## Cross-IPD validation

- Verify that `data_files` records written by `pubrun.open()` (`xxi3nc`) and by `pubrun.register_file()` / `register_input()` / `register_output()` (`52dl55`) share one canonical record structure, share the run's thread-safe hashing budget tracker, and conform to `schemas/manifest.schema.json`. Owner: `52dl55`
- Verify that all six import modes (`auto`, `full`, `noauto`, `nopatch`, `noconsole`, `minimal`) expose the external file registration APIs on both mode alias and parent `pubrun` package identically to root `import pubrun` without patching `builtins.open` or eagerly importing `pubrun.capture.file_io`. Owner: `98j0a3`
- Verify that `pubrun inspect`, `pubrun show`, and `pubrun methods` consume the new `data_files` fields (and degrade honestly on legacy manifests) without overstating path-only, stat-only, pending, or caller-asserted records as verified content. Owner: `hm32d9`
- Verify that the full repository test suite (`pytest tests/ -v`), all examples (`python3 examples/verify_all.py`), benchmark tests (`pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`), path sanitization (`python3 scripts/sanitize_paths.py --check --all`), and import-isolation checks pass together after all children merge. Owner: `4gpguy`

## Deferred / out of scope (with reason)

- Remote object-store inspection and hashing (`s3://`, `gs://`, `abfs://`, `http://`, `https://`): explicitly out of scope per `x6alw4` ("Start with local files; remote object-store support can remain explicitly out of scope") and `pubrun`'s offline, standard-library-only runtime constraint. Remote URIs passed to `register_*()` are recorded honestly as `entry_type = "unsupported_remote_uri"` and `hash_status = "unavailable"` (or `"asserted"` when a caller digest is supplied with `verify_digest=False`) without network access.
  - Carrier-Declined: explicitly out of scope per backlog item x6alw4 and pubrun's offline, standard-library-only runtime constraint.
- Global `builtins.open` monkeypatching or automatic `sys.addaudithook` interception: explicitly rejected by `x6alw4` and `docs/design/file-io-provenance-evaluation.md`.
  - Carrier-Declined: explicitly rejected by backlog item x6alw4 and docs/design/file-io-provenance-evaluation.md.
- Mandatory scientific-framework dependencies (`pandas`, `pyarrow`, `h5py`), hosted services, schedulers, dashboards, or automatic replay: explicitly prohibited by `x6alw4`.
  - Carrier-Declined: explicitly prohibited by backlog item x6alw4.
- Multi-operating-system (OS) and multi-Python continuous integration (CI) matrix execution (`ubuntu-latest`, `ubuntu-24.04`, `windows-latest`, `macos-latest` across Python 3.8 through 3.14 in `.github/workflows/ci.yml`): cannot run inside a single local Linux worktree and must pass on pull request or push before release; noted explicitly by `4gpguy`.
  - Carrier-Declined: executed automatically by GitHub Actions CI (.github/workflows/ci.yml) on pull request or push; unavailable in a single local Linux worktree.

## Scope check

- Over-scope: none. Every child plan maps directly to requirements in `x6alw4` without introducing global I/O patching, third-party runtime dependencies, or unrequested services.
- Under-scope: none. All six implementation guidance items, all five acceptance criteria, and all shared validation, benchmark, schema, and documentation requirements in `x6alw4` are assigned to child plans `xxi3nc`, `52dl55`, `98j0a3`, `hm32d9`, and `4gpguy`.

## Required tests / validation

This orchestrator plan runs no tests directly. Whole-Set validation is performed by its child plans:

- Child `xxi3nc` runs `pytest tests/test_file_io_provenance.py tests/test_manifest_schema.py tests/test_config.py tests/test_explicit_api.py tests/test_new_features.py tests/test_tracker.py -v` and a fresh-subprocess lazy-import and unpatched `builtins.open` check.
- Child `52dl55` runs `pytest tests/test_file_registration.py tests/test_file_io_provenance.py tests/test_explicit_api.py tests/test_api.py tests/test_manifest_schema.py -v` and a fresh-subprocess export and lazy-import check.
- Child `98j0a3` runs `pytest tests/test_import_modes.py tests/test_report_subpackage_integrity.py -v`.
- Child `hm32d9` runs `pytest tests/test_checks_commands.py tests/test_reports.py tests/test_show_sections.py tests/test_methods_multi.py tests/test_templates.py tests/test_example_minimal_research_workflow.py -v` and checks `git diff -- docs/cli.md` for zero newly added em or en dashes.
- Child `4gpguy` runs `python3 examples/12_external_file_provenance.py`, `python3 examples/verify_all.py`, `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`, controlled local non-publishing stat-versus-hash benchmarks, `pytest tests/ -v`, `python3 scripts/sanitize_paths.py --check --all`, `git status --short`, the diff-scoped em/en dash check, and fresh-subprocess import-isolation verification.

## Open questions

### OQ-01: Approval of proposed public API and manifest field names

- Blocking: no
- Status: resolved
- Owner: maintainer
- Resolution or deferral rationale: Backlog item `x6alw4` notes that names for new API and configuration fields are proposals, not yet approved contracts. This Set proposes `pubrun.register_file()`, `pubrun.register_input()`, `pubrun.register_output()`, configuration keys `[capture.file_io].max_total_hash_bytes`, `[capture.file_io].max_total_hash_seconds`, and `[capture.file_io].hash_algorithm`, and manifest fields `data_files.mixed`, `data_files.hashing_summary`, `hash_status`, `evidence_source`, `evidence_strength`, `observation_time`, `digest`, and `caller_digest`. Human approval of this plan Set confirms those contracts before any code is executed. RESOLVED 2026-11-21 by the user via /askme: Approved the proposed public API names (`register_file`, `register_input`, `register_output`), configuration keys (`[capture.file_io].max_total_hash_bytes`, `max_total_hash_seconds`, `hash_algorithm`), and manifest field names (`data_files.mixed`, `data_files.hashing_summary`, `hash_status`, `evidence_source`, `evidence_strength`, `observation_time`, `digest`, `caller_digest`). No reason was given.

### OQ-02: Coordination with pending sibling Set `repro-check` (`0b8i7x`)

- Blocking: no
- Status: resolved
- Owner: maintainer
- Resolution or deferral rationale: Pending sibling plan `0b8i7x` (from backlog item `q3bll1`) checks `data_files` entries defensively for `evidence_source == "asserted"` and `hash_status`. This Set adopts those exact field names so both Sets compose cleanly in either execution order without creating a cross-Set execution dependency. RESOLVED 2026-11-21 by the user via /askme: Confirmed adopting `evidence_source` and `hash_status` (settled with OQ-01) so `file-prov` and `repro-check` (`0b8i7x`) compose in either execution order without a cross-Set dependency. No reason was given.

## Validation and cross-check (verify before reporting the Set complete)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition) (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Confirm `.aw/records/plans/executed/20261121-file-prov-01-xxi3nc-file-provenance-engine-hashing-guarantees-and-proxy-hardenin.ipd.md` exists with `- Status: executed`, all `E-*` items marked `performed`, all `V-*` items marked `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Confirm `.aw/records/plans/executed/20261121-file-prov-02-52dl55-explicit-external-file-registration-api-and-lifecycle-semant.ipd.md` exists with `- Status: executed`, all `E-*` items marked `performed`, all `V-*` items marked `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Confirm `.aw/records/plans/executed/20261121-file-prov-03-98j0a3-import-mode-api-parity-for-file-registration.ipd.md` exists with `- Status: executed`, all `E-*` items marked `performed`, all `V-*` items marked `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Confirm `.aw/records/plans/executed/20261121-file-prov-04-hm32d9-report-inspect-and-methods-file-provenance-evidence-distinct.ipd.md` exists with `- Status: executed`, all `E-*` items marked `performed`, all `V-*` items marked `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Confirm `.aw/records/plans/executed/20261121-file-prov-05-4gpguy-external-file-example-stat-vs-hash-benchmarks-docs-sync-and.ipd.md` exists with `- Status: executed`, all `E-*` items marked `performed`, all `V-*` items marked `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

This orchestrator plan coordinates Set `file-prov` (`xxi3nc`, `52dl55`, `98j0a3`, `hm32d9`, `4gpguy`) and executes no application code directly.

Execution contract:
1. Open questions: all open questions (`OQ-01` and `OQ-02`) were resolved by the maintainer on 2026-11-21; execution of this Set requires explicit human approval (`- Status: approved`).
2. Scope declaration: this orchestrator declares only its own plan file as `- Scope-Paths:` for lifecycle retirement; it executes no application code directly and adds no non-confirmation checklist items.
3. Honesty rule (HARD MUST): confirm child completion only by inspecting the executed child plan files on disk and running `aw ipd lint --phase post-transition`, pasting actual runner output and exit codes into each `V-*` `Observed evidence:` field; never claim a child reached `executed` without verifying its file state.
4. Commit and push discipline: retire this orchestrator via `aw commit` path-scoped to its moved plan file (or let the `aw` runner retire it); never use `git add -A`, `git add .`, or `git commit -a`; never push without explicit human authorization.
5. Lifecycle transition on completion: once all five child plans (`xxi3nc`, `52dl55`, `98j0a3`, `hm32d9`, `4gpguy`) reach `executed` on disk, this orchestrator must reach `.aw/records/plans/executed/` with `- Status: executed` through `aw ipd finalize`. Under an `aw` runner, the runner automatically retires the orchestrator once every child is `executed` and coverage passes; in standalone execution, run `aw ipd finalize vtkkn1` directly. Never hand-roll a raw `git mv` to `.aw/records/plans/executed/`.
