# IPD: Dependency capture accuracy, late-import refresh, and transitive resolution

- Date: 2026-11-21
- Kind: orchestrator
- Concern: Accurate import-to-distribution identity resolution, recursive marker-aware transitive closure, startup-to-finalization package refresh and merge, performance benchmarking, and documentation sync.
- Scope: Coordinate four ordered child plans graduating backlog item `w4hxkh` across distribution identity resolution and caching, recursive marker-aware transitive resolution, startup-to-finalization manifest lifecycle and consumer integration, and benchmarking plus documentation and whole-Set validation.
- Scope-Paths: .aw/records/plans/pending/20261121-dep-capture-00-6s7k9e-dependency-capture-accuracy-late-import-refresh-and-transiti.ipd.md
- Item-Dependencies: executed:uil22c, executed:fdqkrz, executed:ijipnx, executed:iflqsl
- Status: to-review
- Coverage: pass
- Coverage-Fingerprint: 52d2930d50dd695a5de08442f6e2bab14dd53a336dd6daab5639e1d6e0261a68
- Coverage-Checked: 2026-11-22 by uri/its_direct/pt3-claude-opus-5.5-1m-us
- Short-Description: Coordinate distribution identity resolution, marker-aware transitive closure, startup/finalization refresh, benchmarking, and docs sync
- Work-Kind: bug
- Priority: high
- From-Backlog: w4hxkh
- Blocks-Release: next
- Set: dep-capture
- Order: 0
- Highest E allocated: 04
- Author: agent
- Id: 6s7k9e

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 coverage pass (aw oc run): fingerprint 52d2930d50dd, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-21 draft (agent): created.
- 2026-11-21 to-review (agent): authored review-ready orchestrator plan graduating backlog item `w4hxkh` into Set `dep-capture` with four child plans (`uil22c`, `fdqkrz`, `ijipnx`, `iflqsl`).

## Goal

Graduate open backlog item `w4hxkh` (`.aw/records/backlog/open/20261121-pubrun-improve-01-w4hxkh-dependency-capture.backlog.md`) into four bounded, independently verifiable child Implementation Plan Documents (IPDs). Together, the four child plans capture libraries imported after `import pubrun`, resolve import module names to installed Python distribution names on Python 3.8 through 3.14 using only the Python standard library, compute a truthful recursive marker-aware transitive closure, benchmark startup and finalization overhead separately in small and large environments, and synchronize the manifest schema and user documentation.

### Set structure and execution sequence

The child table and text below are normative. These diagrams summarize the execution sequence and artifact relationships in Set `dep-capture`.

```mermaid
flowchart TD
    C1["uil22c: Distribution identity resolution, caching, and module edge cases"] --> C2["fdqkrz: Recursive marker-aware transitive dependency resolution"]
    C2 --> C3["ijipnx: Startup-to-finalization package merge, manifest schema, and report integration"]
    C3 --> C4["iflqsl: Package capture benchmarking, documentation sync, and whole-Set verification"]
    C4 --> O0["6s7k9e: Set complete"]
```

```mermaid
erDiagram
    BACKLOG_W4HXKH ||--|| ORCHESTRATOR_6S7K9E : graduates_to
    ORCHESTRATOR_6S7K9E ||--|| CHILD_UIL22C : coordinates
    ORCHESTRATOR_6S7K9E ||--|| CHILD_FDQKRZ : coordinates
    ORCHESTRATOR_6S7K9E ||--|| CHILD_IJIPNX : coordinates
    ORCHESTRATOR_6S7K9E ||--|| CHILD_IFLQSL : coordinates
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Confirm child IPD execution

- [ ] E-01 CONFIRM uil22c REACHED executed
  - Depends on: none
  - Expected outcome: Child plan `uil22c` (`20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-02 CONFIRM fdqkrz REACHED executed
  - Depends on: E-01
  - Expected outcome: Child plan `fdqkrz` (`20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-03 CONFIRM ijipnx REACHED executed
  - Depends on: E-02
  - Expected outcome: Child plan `ijipnx` (`20261121-dep-capture-03-ijipnx-startup-to-finalization-package-merge-manifest-schema-and-re.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

- [ ] E-04 CONFIRM iflqsl REACHED executed
  - Depends on: E-03
  - Expected outcome: Child plan `iflqsl` (`20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md`) is in `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` items marked `performed`, and all `V-*` items marked `pass`.
  - Execution state: pending

## Child IPDs, sequence, and dependencies

| Order | Id | File | What it does | Depends on |
|---|---|---|---|---|
| 01 | `uil22c` | `20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md` | Implements Python Enhancement Proposal (PEP) 503 normalization, an environment-fingerprinted distribution index and cache with Python 3.8 through 3.14 support, safe concurrent `sys.modules` snapshotting without importing modules, shared lookup helpers compatible with `repro-check`, explicit handling of mismatched import/distribution names, namespace packages, ambiguous distributions, standard-library modules, local-only modules, editable installs, and missing metadata, plus deterministic fixture tests. | none |
| 02 | `fdqkrz` | `20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md` | Adds a Python standard-library PEP 508 requirement and environment-marker evaluator (`src/pubrun/capture/_markers.py`), refactors `imported-transitive` mode to compute a recursive, cycle-safe, extra-honest closure that exposes missing dependencies and unsupported markers as partial capture, and adds transitive behavioral tests. | 01 |
| 03 | `ijipnx` | `20261121-dep-capture-03-ijipnx-startup-to-finalization-package-merge-manifest-schema-and-re.ipd.md` | Extends `schemas/manifest.schema.json` additively, implements startup-to-finalization package snapshot merging that retains removed startup modules without a global import hook, wires finalization refresh into `Run._finalize_state()`, updates `methods.py`, `diagnostics.py`, and `tui/widgets/details.py`, and adds lifecycle and schema tests. | 02 |
| 04 | `iflqsl` | `20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md` | Adds a local, non-publishing startup-versus-finalization benchmark across small, large, and ambient environments (`benchmarks/package_capture_bench.py`), extends `benchmarks/scenarios.py`, records measured results and remaining limits in `docs/performance.md`, reconciles `default.toml`, `docs/manifest.md`, `docs/configuration.md`, and `docs/architecture.md`, and runs full-Set validation. | 03 |

## Completion criteria (the whole Set is done only when)

- Modules whose import name differs from their installed distribution name resolve accurately using standard metadata facilities with a Python 3.8 and 3.9 fallback, cached per environment fingerprint with defined invalidation, without importing target libraries or crashing the host; namespace, ambiguous, standard-library, local-only, editable, missing-metadata, and concurrent `sys.modules` mutation cases produce deterministic, truthful outcomes and degrade to `partial` capture with explicit reasons when resolution fails or stays ambiguous. Owner: `uil22c`.
- `imported-transitive` mode computes a recursive, cycle-safe closure of applicable PEP 508 declared dependencies using a pure standard-library marker evaluator, handles optional extras without mislabeling unrequested installed extras as required, propagates parent-requested extras, exposes missing applicable transitive dependencies or unparseable markers as `partial` capture rather than `complete`, and does not change the default capture mode (`imported-only`). Owner: `fdqkrz`.
- Importing `pubrun` before loading a synthetic distribution records that distribution in the final manifest while keeping the startup snapshot truthful, retains distributions observed at startup even if deleted from `sys.modules` before finalization, avoids installing a global import hook by default, validates against `schemas/manifest.schema.json` alongside legacy v1.0 manifests, and updates `methods.py`, `diagnostics.py`, and TUI details rendering safely. Owner: `ijipnx`.
- Local, non-publishing benchmarks measure startup and finalization package capture separately in small and large synthetic environments (plus ambient environment and optional shared-storage `--workdir`), record environment, revision, workload, baseline, repetitions, cold/warm distinctions, and dispersion in `docs/performance.md`, reconcile `default.toml`, `docs/manifest.md`, `docs/configuration.md`, and `docs/architecture.md`, and pass whole-Set regression verification. Owner: `iflqsl`.

## Cross-IPD validation

- Identity-to-transitive contract: child `uil22c` establishes canonical distribution resolution, PEP 503 normalization (`normalize_package_name`), and shared lookup (`get_installed_distribution_versions`) consumed by both `fdqkrz` (recursive transitive closure) and sibling Set `repro-check` (`tusvtd`), verified by running `tests/test_package_resolution.py` alongside `tests/test_package_transitive.py` in `fdqkrz`. Owner: `fdqkrz`.
- Capture-to-manifest-and-report contract: child `ijipnx` integrates the resolver from `uil22c` and transitive closure from `fdqkrz` into `Run._bootstrap_engines()` and `Run._finalize_state()`, validating both startup and final manifests against `schemas/manifest.schema.json` and verifying late-imported highlighted distributions appear in `methods.md` and `pubrun show packages`. Owner: `ijipnx`.
- Whole-Set regression, benchmark, and hygiene verification: child `iflqsl` executes `pytest tests/ -v`, `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`, `python examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all` after `uil22c`, `fdqkrz`, and `ijipnx` complete. Owner: `iflqsl`.

## Deferred / out of scope (with reason)

- Default global import hook (`sys.meta_path` or `builtins.__import__` patching): explicitly excluded by `w4hxkh` to preserve host-program behavior and zero-overhead import paths; transient mid-run import-then-delete limitations are documented honestly instead.
- Mandatory third-party `packaging` dependency or scientific-framework dependencies (`scikit-learn`, `Pillow`, `numpy`): explicitly prohibited by `w4hxkh`; all resolution, marker evaluation, and tests use the Python standard library and deterministic local fixtures.
- Reproducibility preflight assessment logic: owned by sibling Set `repro-check` (`osjxbz`, backlog item `q3bll1`), which consumes `normalize_package_name` and `get_installed_distribution_versions` from `src/pubrun/capture/packages.py` rather than building a second package resolver.
- External benchmark submission, GitHub Gist creation, GitHub Issue posting, and High-Performance Computing (HPC) scheduler job submission: out of scope and prohibited without explicit maintainer authorization.
- Multi-operating-system and multi-Python Continuous Integration (CI) matrix execution (`ubuntu-latest`, `ubuntu-24.04`, `windows-latest`, `macos-latest` across Python 3.8 through 3.14 in `.github/workflows/ci.yml`): cannot run inside a single local Linux worktree and must pass on pull request or push before release; noted explicitly by `iflqsl`.

## Scope check

- Over-scope: none. Every child plan addresses only the dependency capture, identity resolution, caching, transitive closure, startup/finalization refresh, benchmarking, schema, and documentation requirements of `w4hxkh`.
- Under-scope: none. All five implementation guidance items, all six acceptance criteria, and all shared validation and documentation requirements in `w4hxkh` are assigned to child plans `uil22c`, `fdqkrz`, `ijipnx`, and `iflqsl`.

## Required tests / validation

This orchestrator plan runs no tests directly. Whole-Set validation is performed by its child plans:

- Child `uil22c` runs `pytest tests/test_package_resolution.py tests/test_capture_engines.py tests/test_edge_cases.py -v`.
- Child `fdqkrz` runs `pytest tests/test_package_transitive.py tests/test_package_resolution.py tests/test_new_features.py tests/test_capture_engines.py tests/test_edge_cases.py -v`.
- Child `ijipnx` runs `pytest tests/test_package_lifecycle.py tests/test_manifest_schema.py tests/test_tracker.py tests/test_reports.py tests/test_show_sections.py tests/test_methods_multi.py tests/test_tui.py tests/test_quality.py -v`.
- Child `iflqsl` runs `python benchmarks/package_capture_bench.py`, `pytest tests/test_package_benchmark.py -v`, `pytest tests/ -v`, `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`, `python examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all`.

## Open questions

### OQ-01: Proposed additive manifest field names under `packages`

- Blocking: no
- Status: resolved
- Owner: maintainer (confirmed upon plan approval)
- Resolution or deferral rationale: Backlog item `w4hxkh` notes that new manifest and API field names are proposals rather than pre-approved contracts. Child `ijipnx` proposes additive optional fields in `schemas/manifest.schema.json`: `snapshot_stage`, `unresolved`, `local_modules`, and `coverage_notes` on `$defs.packages_section`, and `import_names` and `observed_at` on `$defs.package_record`. All existing required fields remain unchanged so legacy v1.0 manifests stay valid. The maintainer may rename any proposed field during review before approving `ijipnx`.

### OQ-02: Shared-storage benchmark availability during local execution

- Blocking: no
- Status: resolved
- Owner: maintainer (confirmed upon plan approval)
- Resolution or deferral rationale: Local developer machines and CI runners normally expose only local storage (such as `ext4` or `tmpfs`), while shared Network File System (NFS) or Lustre storage is available only on cluster nodes. Child `iflqsl` records the detected filesystem type via `pubrun.capture.filesystem.get_filesystem()`, documents local-storage scope honestly, and provides an optional `--workdir` argument on `benchmarks/package_capture_bench.py` so the maintainer can re-run the identical benchmark on shared storage without code changes.

## Validation and cross-check (verify before reporting the Set complete)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition)—as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction—name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Path `.aw/records/plans/executed/20261121-dep-capture-01-uil22c-distribution-identity-resolution-caching-and-module-edge-cas.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Path `.aw/records/plans/executed/20261121-dep-capture-02-fdqkrz-recursive-marker-aware-transitive-dependency-resolution.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Path `.aw/records/plans/executed/20261121-dep-capture-03-ijipnx-startup-to-finalization-package-merge-manifest-schema-and-re.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Path `.aw/records/plans/executed/20261121-dep-capture-04-iflqsl-package-capture-benchmarking-documentation-sync-and-whole-se.ipd.md` exists, shows `- Status: executed`, has all `E-*` items `performed` and all `V-*` items `pass`, and `aw ipd lint --phase post-transition` exits 0 on it.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

This orchestrator plan coordinates Set `dep-capture` (`uil22c`, `fdqkrz`, `ijipnx`, `iflqsl`) and executes no application code directly.

Execution contract:
1. All open questions (OQ-01, OQ-02) are resolved for review and become binding upon human approval of this Set (`- Status: approved`).
2. Scope fence: this orchestrator modifies only its own plan file during lifecycle retirement; do not expand scope or add non-confirmation steps to this orchestrator.
3. Honesty rule: confirm child completion only by inspecting the executed child plan files on disk and running `aw ipd lint --phase post-transition`; never claim a child reached `executed` without verifying its file state.
4. Commit discipline: retire this orchestrator via `aw commit` path-scoped to its moved plan file; never use `git add -A`, `git add .`, or `git commit -a`; never push without explicit human instruction.
5. Lifecycle move on completion: after all four child plans (`uil22c`, `fdqkrz`, `ijipnx`, `iflqsl`) reach `executed` on disk, move this orchestrator from `.aw/records/plans/pending/` to `.aw/records/plans/executed/`, set `- Status: executed`, and append a dated `## Workflow history` line.
