# IPD: Post-Change Overhead Comparison Documentation Sync and Whole-Set Verification

- Date: 2026-11-21
- Kind: child
- Concern: Post-change performance verification against the recorded baseline, specification and documentation reconciliation, and whole-Set regression validation.
- Scope: Run post-change local non-publishing benchmarks (`benchmarks/startup_breakdown.py` and `benchmarks/harness.py`) comparing default and opt-in durability policies against the `fthyv5` baseline, update `docs/performance.md`, `docs/configuration.md`, `docs/architecture.md`, `docs/functional_spec.md`, and `docs/manifest.md`, and run whole-Set verification.
- Scope-Paths: docs/performance.md, docs/configuration.md, docs/architecture.md, docs/functional_spec.md, docs/manifest.md
- Item-Dependencies: executed:fthyv5, executed:4il383, executed:tkmm5p
- Status: reviewed
- Readiness: go-pending-approval
- Review-Depth: complex
- Short-Description: Measure post-change overhead against baseline, reconcile documentation and specs, and run whole-Set validation
- Work-Kind: followup
- Priority: high
- From-Backlog: t1xqpw
- Set: startup-perf
- Order: 4
- Highest E allocated: 05
- Author: agent
- Id: ckc3vl

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 /plan-review (Antigravity / Gemini 4 Neon (High)): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004
- 2026-11-22 to-review (agent): authored review-ready child plan from backlog item `t1xqpw`.
- 2026-11-22 draft (agent): created.

## Goal

Measure post-change startup, import, capture, and finalization overhead against the `fthyv5` (startup and finalization overhead baseline measurement) pre-change baseline while keeping default `fsync` durability separated from opt-in durability policies. Synchronize all affected specifications and reference documentation (`docs/performance.md`, `docs/configuration.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`), and run full repository regression, benchmark, example, and path-hygiene verification.

### Post-change measurement, documentation, and verification pipeline

The text in `## Proposed changes (ordered, validatable)` is normative. This diagram summarizes the execution flow after `fthyv5`, `4il383`, and `tkmm5p` reach `executed`.

```mermaid
flowchart TD
    A["Run local non-publishing benchmarks (startup_breakdown.py across durability policies + harness.py to temp path)"] --> B["Compare against fthyv5 baseline and check derived targets; remove temp harness output"]
    B --> C["Update docs/performance.md and docs/configuration.md (zero em/en dashes)"]
    C --> D["Reconcile docs/architecture.md, docs/functional_spec.md, and docs/manifest.md (zero em/en dashes)"]
    D --> E["Run whole-Set checks (pytest tests/, benchmark tests, examples/verify_all.py, sanitize_paths.py)"]
    E --> F["Record CI matrix gate (.github/workflows/ci.yml) and verify clean git status"]
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Post-change performance measurement

- [ ] E-01 Run local, non-publishing post-change measurements using `benchmarks/startup_breakdown.py` (testing default `fsync` and opt-in `finalize`, `atomic`, and `strict` policies separately) and `benchmarks/harness.py`, compare every metric against the executed `fthyv5` baseline, and evaluate all baseline-derived numerical targets.
  - Depends on: none
  - Expected outcome: Post-change measurements capture operating system (OS), Python version, central processing unit (CPU) model and core count, filesystem type, git revision, workload, baseline, repetitions (`passes >= 3`, `iterations >= 15`), cold (pass 1) versus warm (pass N) distinctions, median, mean, 95th percentile (p95), standard deviation (stdev), and Interquartile Range (IQR). Results separate fixed startup cost from finalization cost, report absolute milliseconds (ms) and relative overhead percentages (%) for short (`noop.py`) and long (`cpu_burn.py`) workloads, report default `fsync` gains separately from opt-in durability policies, evaluate every baseline-derived target recorded in executed `fthyv5` `V-05`, include the local `benchmarks/harness.py` summary (including `startup-auto-default`), perform zero external submissions or scheduler jobs, and remove the temporary `--redacted-out` file so zero stray or unredacted files remain in `benchmarks/results/`.
  - Execution state: pending

### Task group 2: Documentation and specification reconciliation

- [ ] E-02 Update `docs/performance.md` with a clearly scoped, environment-labeled startup and finalization overhead breakdown and durability-policy comparison grounded strictly in the measured `fthyv5` versus `ckc3vl` results.
  - Depends on: E-01
  - Expected outcome: `docs/performance.md` preserves the multi-machine placeholder table (`docs/performance.md#Representative results`) without fabricating representative cross-machine numbers, documents the measured before-and-after startup and finalization breakdown with full environment, revision, workload, baseline, repetitions, cold/warm passes, and dispersion, explains local storage versus shared Network File System (NFS) or Lustre storage (referencing `benchmarks/startup_breakdown.py --workdir`), documents durability-policy trade-offs honestly, and introduces zero em dashes (U+2014) or en dashes (U+2013) in added or edited lines.
  - Execution state: pending

- [ ] E-03 Update `docs/configuration.md` to document `[core].artifact_durability` (`"fsync"`, `"finalize"`, `"atomic"`, `"strict"`), `[capture.git].total_timeout`, and `[capture.hardware].total_timeout`.
  - Depends on: E-01
  - Expected outcome: `docs/configuration.md` documents the exact key names, types, defaults (`"fsync"`, `5`, `10`), valid values, single-warning `"fsync"` fallback on invalid durability values, `"finalize"` in-place `fsync` upgrade behavior for unchanged startup `config.resolved.json`, crash-durability versus atomic-visibility behavior, and platform limits for each setting, with zero em dashes (U+2014) or en dashes (U+2013) in added or edited lines.
  - Execution state: pending

- [ ] E-04 Reconcile `docs/architecture.md`, `docs/functional_spec.md`, and `docs/manifest.md` against the implemented commit-identity (`4il383`), snapshot-write coalescing, durability-policy, and capture-budget (`tkmm5p`) behavior.
  - Depends on: E-03
  - Expected outcome: `docs/manifest.md` documents `run.library_version` and `run.library_commit` resolution semantics (lazy Python Enhancement Proposal (PEP) 562 resolution, version-checked `_build_meta.json` with legacy `COMMIT` fallback only when `_build_meta.json` is absent for installed wheels, ownership-verified bounded live `HEAD` for source checkouts, `null` when unknown, timed out, nested, or stale), clarifies `config.resolved.json` persistence, and notes `git`/`hardware` `capture_state.status` `"partial"` and `"timeout"` budget outcomes. `docs/architecture.md` and `docs/functional_spec.md` document lazy commit identity and single-read boot configuration loading, config snapshot coalescing and mid-run `_merge_and_migrate()` updates, atomic visibility versus explicit durability (`fsync`, Portable Operating System Interface (POSIX) parent-directory sync limits on Linux/macOS `F_FULLFSYNC`/Windows `FlushFileBuffers`/NFS), and bounded synchronous Git (combined `rev-parse`) and background hardware capture budgets (explicitly noting source-state capture stays synchronous before user code runs), with zero em dashes (U+2014) or en dashes (U+2013) in added or edited lines.
  - Execution state: pending

### Task group 3: Whole-Set regression and hygiene verification

- [ ] E-05 Run whole-Set regression checks across the full test suite, benchmark conformance tests, examples verification, and path sanitizer, and record the remaining multi-OS and multi-Python Continuous Integration (CI) matrix gate.
  - Depends on: E-02, E-04
  - Expected outcome: `pytest tests/ -v` (including `tests/test_startup_benchmark.py`, `tests/test_commit_identity.py`, and `tests/test_startup_overhead_writes.py`), `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`, `python3 examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all` all exit `0` with complete actual runner output pasted into `V-05`, `git status -s` shows no stray temporary benchmark artifacts, and `V-05` explicitly records the required `.github/workflows/ci.yml` multi-OS and Python 3.8 through 3.14 CI matrix gate before completion.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `docs/performance.md#Representative results` intentionally keeps its cross-machine table as a placeholder until multi-machine submissions are aggregated; single-machine measurements must be clearly labeled with environment, revision, workload, baseline, repetitions, cold/warm passes, and dispersion.
- `docs/configuration.md` documents settings in section tables under `docs/configuration.md#### [core]`, `docs/configuration.md#### [capture.git]`, and `docs/configuration.md#### [capture.hardware]`.
- `docs/manifest.md### run` currently lists only `run_id` and `capture_state`, omitting `library_version` and `library_commit` even though `src/pubrun/tracker.py::Run.to_manifest_dict` and `schemas/manifest.schema.json` already emit both.
- `docs/architecture.md` organizes lifecycle, durability, and component documentation under `## 3. Run Lifecycle`, `## 14. Race Safety and Durability`, and `## 21. System Components`; `docs/functional_spec.md` organizes import and writer rules under `### 3.2 Lightweight Import Requirement` and `## 19. Writer and Finalization`.
- `benchmarks/harness.py` supports `--passes`, `--iterations`, and `--redacted-out REDACTED_OUT` for local non-publishing runs without writing to `benchmarks/results/`.
- Sibling Set `timing-acc` (child `3tvesf`, timing docs, examples, benchmark, and whole-Set verification) also updates `docs/performance.md`, `docs/manifest.md`, `docs/architecture.md`, and `docs/functional_spec.md` for monotonic timing fields; edits in this plan must merge additively into distinct subsections without removing or contradicting `timing-acc` documentation.
- `AGENTS.md` prohibits em dashes (U+2014) and en dashes (U+2013) in newly authored or edited user-facing prose (`docs/`).
- `examples/verify_all.py` runs all repository example scripts and verifies exit code `0`; `scripts/sanitize_paths.py --check --all` enforces absence of machine-local home paths and hostnames across tracked files.
- `.github/workflows/ci.yml` defines the supported OS/Python CI matrix (`ubuntu-latest`, `ubuntu-24.04`, `windows-latest`, `macos-latest` across Python 3.8 through 3.14).

## Findings

- **F-01 (Unverified post-change performance without structured comparison):** Without running the exact pre-change benchmark tool (`fthyv5`) and `benchmarks/harness.py` after `4il383` (build-stamped and deferred commit identity) and `tkmm5p` (snapshot write coalescing, durability policy, and bounded capture) execute, any overhead reduction claim would be unsupported.
- **F-02 (Documentation drift on commit identity, writes, durability, and capture budgets):** `docs/configuration.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`, and `docs/performance.md` do not yet document `run.library_version` / `run.library_commit` lazy build-stamped resolution, single-read boot configuration parsing, config write coalescing, explicit durability policies and platform `fsync` limits, or total capture timeout budgets (`partial`/`timeout` outcomes).

## Proposed changes (ordered, validatable)

1. **Post-change local benchmark execution (no production code edits):**
   - Run `python3 benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1 --durability-policies fsync,finalize,atomic,strict`.
   - Run a local non-publishing `python3 benchmarks/harness.py --passes 3 --iterations 15 --redacted-out <temp_path>` (capturing the summary including `startup-auto-default` added by `fthyv5`, then deleting `<temp_path>` afterward so `benchmarks/results/` and the working tree stay clean).
   - Compare every scenario side by side against the executed `fthyv5` baseline and explicitly evaluate each baseline-derived target recorded in `fthyv5` `V-05`:
     - Installed and checkout `minimal` / `noauto` (and `installed-nested`) import time (ms) and `git` subprocess count (confirming zero `git` spawns on installed imports).
     - Fixed startup cost versus finalization cost (ms) separately.
     - Short workload (`noop.py`) and long workload (`cpu_burn.py`) absolute overhead (ms) and relative overhead (%).
     - `config.resolved.json` atomic write and `fsync` counts (confirming drop from 2-3 writes to 1 for unchanged config, and in-place `fsync` upgrade without rewrite in `"finalize"` mode).
     - Separate durability-policy rows (`fsync` default vs `finalize` vs `atomic` vs `strict`) so default-durability gains are never conflated with opt-in `fsync` relaxation.
     - Cold (pass 1) versus warm (pass 3) medians, mean, p95, stdev, and IQR, plus full environment, git revision, and filesystem type.
2. **`docs/performance.md`:**
   - Add a dedicated, environment-scoped subsection (`### Startup, finalization, and artifact durability overhead`) under `## Notes` (or after `## Representative results` without altering the cross-machine placeholder table) reporting the measured before-and-after table, distinguishing cold/warm passes, short/long workloads, local versus shared storage considerations (pointing to `benchmarks/startup_breakdown.py --workdir`), and separate durability-policy measurements.
3. **`docs/configuration.md`:**
   - Under `### [core]`: document `artifact_durability` (string, default `"fsync"`, valid values `"fsync"`, `"finalize"`, `"atomic"`, `"strict"`, single-warning fallback to `"fsync"` on invalid value), explicitly distinguishing atomic visibility from crash durability, explaining `"finalize"` in-place `fsync` upgrade for unchanged startup `config.resolved.json`, and noting platform `fsync` and directory-sync limits (Linux `fsync(2)`, macOS `fsync(2)` versus `F_FULLFSYNC`, Windows `FlushFileBuffers` without directory sync, and NFS/Lustre writeback/remote procedure call (RPC) costs).
   - Under `### [capture.git]`: document `total_timeout` (int/number, default `5`, total monotonic wall-clock budget across all Git subprocess calls in one capture, reporting `"timeout"` or `"partial"` when exhausted).
   - Under `### [capture.hardware]`: document `total_timeout` (int/number, default `10`, total monotonic wall-clock budget across hardware subprocess probes, reporting `"timeout"` when zero probed fields succeed or `"partial"` when at least one succeeds).
4. **`docs/architecture.md`, `docs/functional_spec.md`, and `docs/manifest.md`:**
   - In `docs/manifest.md`:
     - Under `## run`: document `library_version` and `library_commit` (including lazy PEP 562 resolution, version-checked `_build_meta.json` with legacy `COMMIT` fallback only when `_build_meta.json` is absent for installed wheels, ownership-verified live `HEAD` under a `1.0`s timeout for source checkouts, and `null` for unknown, timed-out, nested, or stale cases).
     - Under `## config`: clarify that `config.resolved.json` is written at startup and rewritten only when effective configuration changes or `run_dir` migrates.
     - Under `## git` and `## hardware`: note that `capture_state.status` records `"timeout"` or `"partial"` when `total_timeout` budgets expire.
   - In `docs/architecture.md` (`## 3. Run Lifecycle`, `## 14. Race Safety and Durability`, `## 21. System Components`) and `docs/functional_spec.md` (`### 3.2 Lightweight Import Requirement`, `## 19. Writer and Finalization`):
     - Document lazy `__commit__` resolution (zero Git subprocesses on installed imports) and single-read boot `.pubrun.toml` parsing.
     - Document atomic visibility (always on via unique temporary file + `os.replace`) versus explicit durability policy (`[core].artifact_durability`), including `"finalize"` in-place `fsync` upgrade and platform durability limits (POSIX parent-directory `fsync` in `"strict"` mode, macOS `F_FULLFSYNC` distinction, Windows `FlushFileBuffers` without directory sync, NFS/Lustre costs).
     - Document config snapshot coalescing, mid-run `_merge_and_migrate()` updates, hardware-off synchronous collection without thread spawn, and `_artifacts_written` idempotency.
     - Document bounded total Git (combined `rev-parse`) and background hardware capture budgets, explicitly noting that Git and script source-state capture stays synchronous before user code runs.
   - Verify via a Python diff check that zero em dashes (U+2014) or en dashes (U+2013) were introduced in added lines across all five documentation files.
5. **Whole-Set verification:**
   - Run `pytest tests/ -v`, `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`, `python3 examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all`.
   - Record full actual runner output and exit codes in `V-05`, verify `git status -s` contains no stray temporary benchmark files, and record the GitHub Actions CI matrix gate (`.github/workflows/ci.yml`: Ubuntu, Windows, macOS across Python 3.8 through 3.14) required before release or closure.

## Deferred / out of scope (with reason)

- Running the GitHub Actions multi-OS and Python 3.8 through 3.14 CI matrix requires GitHub Actions runners on pull request or push; local verification covers the host OS/Python and records the CI matrix gate explicitly.
  - Carrier-Declined: executed automatically by GitHub Actions CI (.github/workflows/ci.yml) on pull request or push; unavailable in a single local Linux worktree
- External benchmark submission, Gist creation, or high-performance computing (HPC) scheduler job submission is prohibited without explicit maintainer authorization.
  - Carrier-Declined: explicitly prohibited by backlog item t1xqpw Acceptance Criterion 6 without maintainer authorization
- Unrelated backlog items (`6hp1zu`, `w4hxkh`, `x21s6w`, `x6alw4`, `q3bll1`) are out of scope.
  - Carrier: 6hp1zu

## Scope check

- Over-scope: none. Touches only the five documentation files (5 Scope-Paths, 5 E-items).
- Under-scope: none. Covers before-and-after measurement verification (`startup_breakdown.py` and `harness.py`), baseline target evaluation, durability and platform-limit documentation, specification reconciliation, em/en-dash hygiene, and whole-Set regression checks required by backlog item `t1xqpw` and orchestrator `9ppa0r`.

## Required tests / validation

Run inside the repository root and capture actual runner output and exit codes:

```bash
python3 benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1 --durability-policies fsync,finalize,atomic,strict
python3 benchmarks/harness.py --passes 3 --iterations 15 --redacted-out /tmp/pubrun-post-change-harness.redacted.json && rm -f /tmp/pubrun-post-change-harness.redacted.json
pytest tests/ -v
pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v
python3 examples/verify_all.py
python3 scripts/sanitize_paths.py --check --all
```

## Spec / documentation sync

This plan is the specification and documentation synchronization plan for Set `startup-perf`.

## Open questions

### OQ-01: Coordinating `docs/` edits with sibling Set `timing-acc` (`3tvesf`)

- Blocking: no
- Status: resolved
- Owner: plan author (binding upon plan approval)
- Resolution or deferral rationale: Both `3tvesf` (Set `timing-acc`) and `ckc3vl` (Set `startup-perf`) update `docs/performance.md`, `docs/manifest.md`, `docs/architecture.md`, and `docs/functional_spec.md`. Keep edits in `ckc3vl` strictly additive to distinct sections (commit identity, durability policy, config snapshot coalescing, capture budgets, and startup/finalization breakdown measurements) and preserve any timing-accuracy text present on disk when executing.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition) (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted redacted output of `python3 benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1 --durability-policies fsync,finalize,atomic,strict` (exit code 0), summary output of local non-publishing `python3 benchmarks/harness.py --passes 3 --iterations 15 --redacted-out <temp_path>` (including `startup-auto-default`, with `<temp_path>` deleted afterwards), a before-versus-after comparison table against executed `fthyv5` evaluating every baseline-derived target (showing environment, git revision, filesystem type, cold/warm passes, median, mean, p95, stdev, IQR, separate fixed startup and finalization ms, short/long workload absolute ms and relative overhead %, subprocess/write/fsync counts, default `fsync` versus opt-in durability policies), and `git status -s` confirming no stray or unredacted files remain.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Diff of `docs/performance.md` showing environment-scoped measured startup/finalization breakdown and durability comparison matching `V-01`, intact cross-machine placeholder table, local-versus-shared storage guidance, plus output of a Python check over added lines of `git diff -- docs/performance.md` confirming zero em dashes (U+2014) or en dashes (U+2013).
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Diff of `docs/configuration.md` showing `[core].artifact_durability` (including invalid-value fallback and `"finalize"` in-place sync), `[capture.git].total_timeout`, and `[capture.hardware].total_timeout` with defaults, options, and platform durability limits, plus output of a Python check over added lines of `git diff -- docs/configuration.md` confirming zero em dashes (U+2014) or en dashes (U+2013).
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Diff of `docs/architecture.md`, `docs/functional_spec.md`, and `docs/manifest.md` showing reconciled `run.library_version` / `run.library_commit` resolution, single-read boot config loading, config write coalescing, atomic visibility versus durability policy, platform `fsync`/directory-sync limits, and bounded synchronous/background capture semantics (`partial`/`timeout`), plus output of a Python check over added lines of `git diff -- docs/architecture.md docs/functional_spec.md docs/manifest.md` confirming zero em dashes (U+2014) or en dashes (U+2013).
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted actual runner output and exit code 0 for `pytest tests/ -v` (confirming `test_startup_benchmark.py`, `test_commit_identity.py`, and `test_startup_overhead_writes.py` pass alongside the full suite), `pytest benchmarks/test_benchmarks.py benchmarks/test_share_safety.py -o addopts="" -v`, `python3 examples/verify_all.py`, and `python3 scripts/sanitize_paths.py --check --all`, `git status -s` confirming no stray temporary benchmark artifacts, plus an explicit note recording the `.github/workflows/ci.yml` multi-OS and Python 3.8 through 3.14 CI matrix gate required before completion.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Open questions: all open questions (`OQ-01`) are resolved for review; do not execute until prerequisites `fthyv5` (baseline measurement), `4il383` (build-stamped and deferred commit identity), and `tkmm5p` (snapshot write coalescing, durability policy, and bounded capture) are `executed` and a human approves this plan (`- Status: approved`).
2. Scope fence: restrict edits to `- Scope-Paths:` (`docs/performance.md`, `docs/configuration.md`, `docs/architecture.md`, `docs/functional_spec.md`, `docs/manifest.md`). If an out-of-scope edit is genuinely required, justify it with `--scope-reason` at finalization; if a declared path needs no edit, acknowledge it with `--scope-ack`. Stop and report only for genuinely unsafe conditions (such as an unresolvable concurrent-edit conflict or missing prerequisite baseline/implementation).
3. Honesty rule (HARD MUST): paste actual runner output and exit codes for `benchmarks/startup_breakdown.py`, `benchmarks/harness.py`, `pytest`, `examples/verify_all.py`, and `scripts/sanitize_paths.py` into each `V-*` `Observed evidence:` field; never claim unmeasured speedups or unrun tests.
4. Commit and push discipline: commit only the files changed for this plan using `aw commit ckc3vl -- <paths>`; never use `git add -A`, `git add .`, or `git commit -a`; never push or publish benchmark results without explicit human authorization.
5. Lifecycle transition: this plan must reach `.aw/records/plans/executed/` with `- Status: executed` through `aw ipd finalize` once all `E-*` are `performed` and all `V-*` are `pass`. In a runner-managed lane, the runner owns `aw ipd finalize`; in standalone execution, run `aw ipd lint --phase pre-transition` and finalize directly through `aw ipd finalize`. Never hand-roll a raw `git mv` to `executed/`.
