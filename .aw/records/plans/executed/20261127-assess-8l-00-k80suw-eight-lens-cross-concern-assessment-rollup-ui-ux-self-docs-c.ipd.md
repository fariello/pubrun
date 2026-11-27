# IPD: Eight-lens cross-concern assessment rollup (UI/UX, self-docs, compat, edge-cases, functionality, perf, use-cases, memory)

- Date: 2026-11-27
- Kind: orchestrator
- Concern: Cross-concern `/assess-all` rollup across eight lenses (`ui-ux`, `self-documentation`, `compatibility`, `edge-cases`, `functionality`, `performance`, `use-cases`, `memory-resources`) on commit `2c87ae4` (post-v1.4.0 and post-`bej1qz`). The eight parallel audits surfaced 119 raw findings (de-duplicated to 37 actionable cross-concern items and 2 product-policy items routed to non-blocking open questions) covering host-script crash risks, Portable Operating System Interface (POSIX) `fork()` and `multiprocessing` `spawn` hazards, `O(N^2)` and unbounded growth in `file_io`, startup/package/run-scan performance bottlenecks, Windows/ARM64/AMD Radeon Open Compute (ROCm)/Python Enhancement Proposal 561 (PEP 561) compatibility defects, `methods`/diff/diagnostics correctness bugs, Command-Line Interface (CLI) `--dir`/JavaScript Object Notation (JSON)/self-documentation gaps, and Terminal User Interface (TUI) safety/hydration/responsiveness defects.
- Scope: Coordination of ten right-sized child plans for Set `assess-8l`: `1o1cua` (config, Current Working Directory (CWD), artifact-write safety, strict JSON, core API ergonomics), `76z7ww` (fork/spawn, signal, console, subprocess, and lifecycle resource safety), `l596kn` (`file_io` O(1) indexing, record cap, and streaming-hash fast path), `p4ueaj` (cold-start import, package-capture optimization, and PEP 561 mode parity), `ameehy` (cross-platform hardware, liveness, invocation, environment, git, filesystem, and redaction compatibility), `m5s3g8` (status, clean, and run-scanning safety, scalability, and terminal output), `caeqdz` (diff, methods, diagnostics, and meta-snapshot correctness and streaming), `2ge0ea` (CLI ergonomics, `--dir`/`PUBRUN_OUTPUT_DIR`, `--json`, streaming `combined`, self-documenting help, and config defaults), `3q5rd5` (TUI safety, `meta_ref` hydration, memory/responsiveness, and usability), and `6y55x4` (Continuous Integration (CI) matrix expansion, local scaling benchmarks, `README.md`/`docs/cli.md`/`docs/configuration.md` sync, and whole-Set verification). This orchestrator modifies no product code, tests, docs, or CI files.
- Scope-Paths: .aw/records/plans/pending/20261127-assess-8l-00-k80suw-eight-lens-cross-concern-assessment-rollup-ui-ux-self-docs-c.ipd.md
- Item-Dependencies: executed:1o1cua, executed:76z7ww, executed:l596kn, executed:p4ueaj, executed:ameehy, executed:m5s3g8, executed:caeqdz, executed:2ge0ea, executed:3q5rd5, executed:6y55x4
- Status: executed
- Readiness: go-pending-approval
- Coverage: pass
- Coverage-Fingerprint: 25079b0b41380c0183b119e140f7976e8d09da99f7e8b86a9a01dc2e8599db56
- Coverage-Checked: 2026-11-27 by uri/its_direct/pt3-claude-opus-5.5-1m-us
- Review-Depth: orchestrator
- Short-Description: Orchestrate the 10-child cross-concern hardening and performance IPD Set from the 8-lens /assess-all rollup
- Work-Kind: bug
- Priority: high
- Set: assess-8l
- Order: 0
- Highest E allocated: 10
- Author: Antigravity
- Id: k80suw

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md`, including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 executed (aw agy run model=Gemini-4-Neon-High): RETIRED as the orchestrator rollup step of a runner Set completion, not executed by an agent: every child of Set assess-8l reached executed, so the runner (run run-20261127T181739Z-3404307) retired this Order-0 plan as bookkeeping. Its own E-*/V-* items were NOT performed; the runner superseded them by enforcing the ordering, the isolation and the per-child merge gate. Justifying children: 1o1cua, 76z7ww, l596kn, p4ueaj, ameehy, m5s3g8, caeqdz, 2ge0ea, 3q5rd5, 6y55x4.
- 2026-11-27 approved (aw set): status set to approved
- 2026-11-27 coverage pass (aw oc run): fingerprint 25079b0b4138, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-27 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004
- 2026-11-27 coverage pass (aw oc run): fingerprint cbd3dc0be8a1, model uri/its_direct/pt3-claude-opus-5.5-1m-us
- 2026-11-27 /assess-all (Antigravity): rolled up ui-ux, self-documentation, compatibility, edge-cases, functionality, performance, use-cases, memory-resources; proposed 37 de-duplicated changes across 10 right-sized child plans (Set assess-8l; rollup record `.aw/workflow-artifacts/assess-all/20261127-092500/`).

## Goal

Deliver all 37 actionable, de-duplicated findings from the eight-lens `/assess-all` rollup (`ui-ux`, `self-documentation`, `compatibility`, `edge-cases`, `functionality`, `performance`, `use-cases`, `memory-resources`) through ten bounded, independently testable child plans with explicit dependency edges and serialized shared file scopes.

### Set dependency architecture

```mermaid
flowchart TD
    C1["01 1o1cua: Config, CWD, core API & strict JSON"]
    C2["02 76z7ww: Fork/spawn, signals, console & lifecycle"]
    C3["03 l596kn: file_io O(1) index, cap & hash fast path"]
    C4["04 p4ueaj: Cold-start, packages perf & PEP 561 parity"]
    C5["05 ameehy: Cross-platform capture & invocation"]
    C6["06 m5s3g8: Status, clean, scan scale & color"]
    C7["07 caeqdz: Diff, methods, diagnostics & meta"]
    C8["08 2ge0ea: CLI --dir/JSON, combined & self-docs"]
    C9["09 3q5rd5: TUI safety, hydration, memory & UX"]
    C10["10 6y55x4: CI matrix, scaling benches & verification"]
    ORCH["00 k80suw: Orchestrator retirement"]

    C1 --> C2
    C2 --> C3
    C1 --> C4
    C2 --> C4
    C3 --> C4
    C3 --> C5
    C6 --> C7
    C1 --> C8
    C3 --> C8
    C6 --> C8
    C7 --> C8
    C6 --> C9
    C7 --> C9
    C1 --> C10
    C2 --> C10
    C3 --> C10
    C4 --> C10
    C5 --> C10
    C6 --> C10
    C7 --> C10
    C8 --> C10
    C9 --> C10
    C10 --> ORCH
```

## Detailed Implementation Checklist (TODO)


> Its own E-*/V-* items were NOT performed; the runner superseded them by enforcing the ordering, the isolation and the per-child merge gate.

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each child plan stays bounded around 4 to 5 E-items and cohesive Scope-Paths. Accepted execution states: blocked, failed, pending, performed; terminal gate demands `performed`.

### Task group 1: Child plan execution confirmation

- [ ] E-01 CONFIRM 1o1cua REACHED executed
  - Depends on: none
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-01-1o1cua-config-cwd-artifact-write-safety-strict-json-and-core-api-er.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-02 CONFIRM 76z7ww REACHED executed
  - Depends on: E-01
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-02-76z7ww-fork-spawn-signal-console-subprocess-and-lifecycle-resource.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-03 CONFIRM l596kn REACHED executed
  - Depends on: E-02
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-03-l596kn-file-i-o-o-1-indexing-record-cap-and-streaming-hash-fast-pat.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-04 CONFIRM p4ueaj REACHED executed
  - Depends on: E-01, E-02, E-03
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-05 CONFIRM ameehy REACHED executed
  - Depends on: E-03
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-06 CONFIRM m5s3g8 REACHED executed
  - Depends on: none
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-06-m5s3g8-status-clean-and-run-scanning-safety-scalability-and-termina.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-07 CONFIRM caeqdz REACHED executed
  - Depends on: E-06
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-07-caeqdz-diff-methods-diagnostics-and-meta-snapshot-correctness-and-s.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-08 CONFIRM 2ge0ea REACHED executed
  - Depends on: E-01, E-03, E-06, E-07
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-08-2ge0ea-cli-ergonomics-dir-pubrun-output-dir-json-output-streaming-c.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-09 CONFIRM 3q5rd5 REACHED executed
  - Depends on: E-06, E-07
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-09-3q5rd5-tui-safety-meta-ref-hydration-memory-responsiveness-and-usab.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

- [ ] E-10 CONFIRM 6y55x4 REACHED executed
  - Depends on: E-01, E-02, E-03, E-04, E-05, E-06, E-07, E-08, E-09
  - Expected outcome: `.aw/records/plans/executed/20261127-assess-8l-10-6y55x4-ci-compatibility-matrix-scaling-benchmarks-and-whole-set-ver.ipd.md` exists with `- Status: executed`, all `E-*` performed, and all `V-*` passed.
  - Execution state: pending

## Child IPDs, sequence, and dependencies

| Order | Id | File | What it does | Depends on |
|---|---|---|---|---|
| 01 | `1o1cua` | `20261127-assess-8l-01-1o1cua-config-cwd-artifact-write-safety-strict-json-and-core-api-er.ipd.md` | Harden deleted-CWD, non-UTF-8/malformed Tom's Obvious Minimal Language (TOML), reserved artifact writes, strict JSON (`NaN`/`Inf`), manual subprocess wrappers, `phase` profiling/filenames, `_inactive_policy` crash guards (retaining `68iw9a` immediate file-change detection per resolved `1o1cua` `OQ-01`), cached `pubrun.print()` handle, `_config_version` caching, `CallableModule` docs, `tracked_run` properties, and `docs/api.md` sync. | none |
| 02 | `76z7ww` | `20261127-assess-8l-02-76z7ww-fork-spawn-signal-console-subprocess-and-lifecycle-resource.ipd.md` | Fix POSIX `fork()` File Descriptor (FD) flush/lock/`SubprocessSpy` hazards, `multiprocessing` `spawn`/`forkserver` run storms, `_merge_and_migrate` self-move and lock races, `TqdmSafeTee` `writelines`/perf/cleanup lock, lethal `SIGUSR1`/`SIGUSR2`, `signal.raise_signal`, `_signals_received` cap, Windows `shlex`, `ResourceWatcher` bounds, and `pubrun-hw` thread bound. | 01 |
| 03 | `l596kn` | `20261127-assess-8l-03-l596kn-file-i-o-o-1-indexing-record-cap-and-streaming-hash-fast-pat.ipd.md` | Replace `O(N^2)` linear scans in `capture/file_io.py` with `O(1)` indexes, add `[capture.file_io].max_tracked_files` cap (default `5000`) with `records_truncated` propagation in `tracker.py`, `schemas/manifest.schema.json`, `docs/configuration.md`, and `docs/manifest.md`, optimize zero-cap streaming hash fast path, and bound `_warned_invalid_algorithms`. | 02 |
| 04 | `p4ueaj` | `20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md` | Defer `__version__` via PEP 562 `__getattr__`, lazy-import `tracker` and capture engines, eliminate 3x `METADATA` reads and eager `RECORD` parsing in `packages.py`, fix PEP 561 `__all__`/`__commit__` parity across all 6 mode modules, fix `nopatch.py` docstring, and close pipes in `_resolve_checkout_commit`. | 01, 02, 03 |
| 05 | `ameehy` | `20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md` | Replace Windows `wmic` with `ctypes`/`winreg` in `hardware.py`, add ARM64 Central Processing Unit (CPU) and AMD ROCm Graphics Processing Unit (GPU) fallbacks, parse macOS Video Random-Access Memory (VRAM), cache Windows `WinDLL`/`Structure` and add `LC_ALL=C` in `liveness.py`, clamp `system_metrics.py`, fix `invocation.py` (`sys.executable`, `-m`, `--flag=path`, Jupyter `notebook`, `compute_md5` cap), harden `environment.py`, `git.py`, `filesystem.py`, and iterative `redaction.py`, and sync `docs/configuration.md` and `docs/manifest.md`. | 03 |
| 06 | `m5s3g8` | `20261127-assess-8l-06-m5s3g8-status-clean-and-run-scanning-safety-scalability-and-termina.ipd.md` | Fail closed on `limit <= 0` in `filter_runs`, add `--force-remote-locks` and shared safe-delete helper, validate `--status`/`-S`, fix completed-run event/log stats and onboarding copy, adopt `os.scandir()` + `keep_manifest=False` + `#1000+` alignment, and centralize TTY-aware `use_color` without `DIM` plus ASCII fallbacks. | none |
| 07 | `caeqdz` | `20261127-assess-8l-07-caeqdz-diff-methods-diagnostics-and-meta-snapshot-correctness-and-s.ipd.md` | Fix `methods.py` GPUs, non-highlighted packages, Zenodo Digital Object Identifier (DOI), and 10-char LaTeX escaping; fix cross-Operating-System (cross-OS) diff, compiled ignores, `O(N)` `_format_array_diff`, `NaN`/multiset, inline `(no differences)` & `-/+`; stream `show logs`, O(1) timeline & chart/duration guards, unknown section error; write `meta.json` atomically with setup instructions. | 06 |
| 08 | `2ge0ea` | `20261127-assess-8l-08-2ge0ea-cli-ergonomics-dir-pubrun-output-dir-json-output-streaming-c.ipd.md` | Add `--dir` across all run-reading subcommands + `PUBRUN_OUTPUT_DIR` + `$VAR`/`~` expansion, add `status --json`/`diff --json`, wire `[methods].format` + stderr banners, stream `_run_combined` with `heapq.merge` + `AmbiguousRunSelectorError` handling, fix `bench` tips/groups/bounds, sync `default.toml` comments, unify `RUN` help & bare-`pubrun` quick start, warn on future `schema_version`, and pass UTF-8 to subprocesses. | 01, 03, 06, 07 |
| 09 | `3q5rd5` | `20261127-assess-8l-09-3q5rd5-tui-safety-meta-ref-hydration-memory-responsiveness-and-usab.ipd.md` | Add confirmation modal and stderr capture on TUI `Execute Prune`, guard single-run delete with shared safe-delete helper, hydrate `meta_ref` across all detail panes, switch sidebar search to in-memory filtering, fix `LogViewer` double-read/unbounded-read/`Wrap Text`, make `ConfigPanel` atomic with regex check and clear labels, fix `DiffView` defaults/rendering, and fix 80x24 layout and keybindings. | 06, 07 |
| 10 | `6y55x4` | `20261127-assess-8l-10-6y55x4-ci-compatibility-matrix-scaling-benchmarks-and-whole-set-ver.ipd.md` | Expand CI for `<3.11` `no-tui`/`tomli`, Windows packaging wheel smoke, `[bench]` extra, downstream `mypy --strict --no-implicit-reexport` mode-module check, and `tomli`/`[tui]` audit; add share-safe stdlib local scaling benchmark script and `tests/test_compatibility.py`; sync `README.md`, `docs/cli.md`, and `docs/configuration.md`; run whole-Set verification. | 01, 02, 03, 04, 05, 06, 07, 08, 09 |

## Completion criteria (the whole Set is done only when)

- Config, CWD, artifact-write safety, strict JSON, subprocess wrapper guards, `phase` profiling safety, `_inactive_policy` crash guards (preserving `68iw9a` immediate file-change detection per resolved `1o1cua` `OQ-01`), `_config_version` caching, `CallableModule` docs, `tracked_run` properties, and `docs/api.md` sync are implemented and tested. Owner: `1o1cua`.
- POSIX `fork()`, `multiprocessing` `spawn`/`forkserver`, `_merge_and_migrate`, `TqdmSafeTee`, lethal signals (`SIGUSR1`/`SIGUSR2`/`raise_signal`), Windows `shlex`, `ResourceWatcher` bounds, and `pubrun-hw` concurrency bounds are implemented and tested. Owner: `76z7ww`.
- `file_io` uses `O(1)` dedup/pending indexes, enforces `[capture.file_io].max_tracked_files` with `records_truncated` propagation in `tracker.py`, `schemas/manifest.schema.json`, `docs/configuration.md`, and `docs/manifest.md`, and fast-paths uncapped streaming hashes. Owner: `l596kn`.
- Cold-start `import pubrun.minimal`, package capture `METADATA`/`RECORD` reads, PEP 561 mode-submodule exports (`mypy --strict --no-implicit-reexport`), `nopatch.py` docstring, and `_resolve_checkout_commit` pipe cleanup are implemented and verified. Owner: `p4ueaj`.
- Cross-platform capture (`hardware`, `liveness`, `system_metrics`, `invocation` including Jupyter and `-m`, `environment`, `git`, `filesystem`, `redaction`) works without Windows `wmic`, supports ARM64 CPU and ROCm GPU fallbacks, handles non-UTF-8 locales and deeply nested JSON, and syncs `docs/configuration.md` and `docs/manifest.md`. Owner: `ameehy`.
- `status.py` and `report/output.py` enforce fail-closed `limit <= 0`, remote-lock clean safety with `--force-remote-locks`, `VALID_STATUSES`, completed-run event/log counts, `os.scandir()`/`keep_manifest=False`, `#1000+` consistency, TTY-aware color without `DIM`, and ASCII fallbacks. Owner: `m5s3g8`.
- `diff.py`, `render.py`, `methods.py`, `diagnostics.py`, `meta_snapshot.py`, and `report/utils.py` fix GPUs/stdlib/DOI/LaTeX in methods, cross-OS and `O(N)` diffing, streaming logs and O(1) timelines, numeric chart/duration guards, and atomic `meta.json` with setup guidance. Owner: `caeqdz`.
- CLI (`__main__.py`, `config.py`, `default.toml`, `reproducibility.py`, `_bench/harness.py`, `capture/python_runtime.py`) delivers consistent `--dir`/`PUBRUN_OUTPUT_DIR`, `status`/`diff` `--json`, streaming `combined`, fixed `bench` tips/validation, synced `default.toml` comments, self-documenting help/errors, and future `schema_version` warnings. Owner: `2ge0ea`.
- TUI delivers confirmed bulk prune, guarded single-run delete, hydrated `meta_ref` across all views, in-memory search, single bounded log reads with working wrap toggle, atomic validated `ConfigPanel`, standard `DiffView`, and responsive 80x24 layout. Owner: `3q5rd5`.
- CI matrix, share-safe local scaling benchmarks, `README.md`/`docs/cli.md`/`docs/configuration.md` accuracy updates (zero em/en dashes), full `pytest` with coverage, extra script/benchmark suites, three-OS `mypy`, downstream `mypy --strict --no-implicit-reexport` mode check, wheel/sdist build + `twine check --strict` + cleanliness check, and `scripts/sanitize_paths.py --check --all` all pass. Owner: `6y55x4`.

## Cross-IPD validation

- Every shared `- Scope-Paths:` file across all ten children is strictly serialized along explicit `- Item-Dependencies:` edges (zero unserialized pairs):
  - `src/pubrun/config.py`: `1o1cua` -> `2ge0ea`
  - `src/pubrun/core.py`: `1o1cua` -> `p4ueaj`
  - `src/pubrun/tracker.py`: `76z7ww` -> `l596kn` -> `p4ueaj`
  - `src/pubrun/resources/default.toml`: `l596kn` -> `2ge0ea`
  - `docs/configuration.md`: `l596kn` -> `ameehy` -> `6y55x4`
  - `docs/manifest.md`: `l596kn` -> `ameehy`
  - `tests/test_cli_negative_paths.py`: `caeqdz` -> `2ge0ea`
- Interface consumers (`caeqdz`, `2ge0ea`, `3q5rd5` consuming `m5s3g8` `status.py` and `report/output.py`, and `2ge0ea`/`3q5rd5` consuming `caeqdz` report/analysis seams) are likewise ordered behind `executed:m5s3g8` and `executed:caeqdz`.
- Child `6y55x4` (Order 10) runs the full repository test suite, extra script/benchmark suites, three-OS `mypy`, downstream PEP 561 `mypy --strict --no-implicit-reexport`, wheel/sdist build + `twine check --strict` + archive cleanliness check, local scaling benchmarks, user-facing dash check, and `scripts/sanitize_paths.py --check --all` on the combined state of children 01 through 09.

## Deferred / out of scope (with reason)

- Changing default `[core].artifact_durability` from `"fsync"` to `"finalize"` (`PERF-8` / `ROLL-38`) carries Medium-High usability/durability-expectation risk; `_config_version` caching ships in `1o1cua` while the default durability switch awaits maintainer decision (`OQ-02`).
  - Carrier-Declined: Product policy decision (`OQ-02`); no autonomous change authorized without explicit maintainer choice.
- Additive v1.5.0 feature expansions (`ROLL-39`: zero-touch `sitecustomize.py` injection in `pubrun run`, CLI `pubrun export`/`archive --redacted`/`--requirements`, `--newer-than`/`--commit`/run tagging, structured Slurm/PBS/LSF/SGE job fields & `PUBRUN_RANK_ZERO_ONLY`, Jupyter `%%pubrun` cell magics, optional `git diff` capture, container cgroup quotas) carry Medium-High usability/scope risk and await maintainer scope selection (`OQ-01`, `OQ-05`).
  - Carrier-Declined: Product scope decision (`OQ-01`, `OQ-05`); maintainer will file targeted backlog items only for selected features.

## Scope check

- Over-scope: none. Every child plan maps directly to concrete, evidence-verified findings from the 2026-11-27 eight-lens `/assess-all` rollup (untracked session artifact `.aw/workflow-artifacts/assess-all/20261127-092500/findings.csv`), and all product-policy choices are routed to non-blocking Open Questions with recorded carriers rather than assumed.
- Under-scope: none. Every one of the 37 actionable cross-concern items (`ROLL-01`..`ROLL-37`) is assigned to an explicit child plan in `## Child IPDs, sequence, and dependencies`, and every sibling handoff (`- Carrier:`) is accounted for.

## Required tests / validation

This orchestrator executes no commands directly. Children `1o1cua` through `3q5rd5` run their targeted tests and three-OS `mypy`, and child `6y55x4` runs the whole-Set verification suite (`pytest tests/ -p randomly --cov=src --cov-fail-under=78`, `pytest .github/scripts/ benchmarks/test_*.py tests/test_compatibility.py -v -p randomly`, `mypy` across Linux/`win32`/`darwin`, downstream `mypy --strict --no-implicit-reexport`, wheel/sdist build + `twine check --strict` + archive cleanliness check, local scaling benchmarks, zero-dash check, and `scripts/sanitize_paths.py --check --all`).

## Open questions

### OQ-01: Should `pubrun run -- python script.py` inject `pubrun` into scripts lacking `import pubrun` via a temporary chaining `sitecustomize.py`, or stay strictly an import-mode override wrapper?

- Blocking: no
- Status: open
- Owner: maintainer
- Carrier-Declined: Product scope decision (`ROLL-39`); Set `assess-8l` fixes misleading onboarding copy and help text now (`m5s3g8`, `2ge0ea`, `6y55x4`) without adding `sitecustomize.py` injection unless the maintainer later opens a targeted backlog item.
- Recommended answer: Keep `pubrun run` strictly as an import-mode override wrapper in Set `assess-8l` and evaluate zero-touch injection separately in v1.5.0 (recommendation strength: `strong`).

### OQ-02: Should default `[core].artifact_durability` switch from `"fsync"` (4 fsyncs/run) to `"finalize"` (1-2 fsyncs/run)?

- Blocking: no
- Status: open
- Owner: maintainer
- Carrier-Declined: Product policy decision (`PERF-8`/`ROLL-38`); Set `assess-8l` keeps `"fsync"` default and ships `_config_version` caching in `1o1cua` without changing durability defaults autonomously.
- Recommended answer: Keep `"fsync"` as the default durability policy until the maintainer explicitly approves relaxing startup-snapshot durability (recommendation strength: `strong`).

### OQ-03: Should `_is_meta_ref_allowed()` trust `manifest_dir.parent / "meta.json"` automatically, or keep strict `manifest_dir`-only confinement?

- Blocking: no
- Status: open
- Owner: maintainer
- Carrier-Declined: Security confinement default retained in `caeqdz` alongside copy-pasteable `PUBRUN_META_REF` and `[report]` instructions; no follow-up required unless the maintainer requests relaxing confinement.
- Recommended answer: Keep strict `manifest_dir`-only confinement by default (recommendation strength: `strong`).

### OQ-04: Should `[core].auto_start` be deprecated in favor of `[imports].mode` and reserved keys dropped from `default.toml`?

- Blocking: no
- Status: open
- Owner: maintainer
- Carrier-Declined: Backward-compatible `[core].auto_start` and accurate `# RESERVED (no effect)` comments are retained in `2ge0ea`; no breaking config deprecation is scheduled in 1.x.
- Recommended answer: Keep backward-compatible defaults and accurate comments in `default.toml` during 1.x (recommendation strength: `strong`).

### OQ-05: Which additive v1.5.0 features (`pubrun export --redacted`/`--requirements`, `--newer-than`/`--commit`/tags, `PUBRUN_RANK_ZERO_ONLY`/scheduler fields, Jupyter `%%pubrun`, `[capture.git].capture_diff`, container cgroup quotas) should be filed as follow-up backlog items?

- Blocking: no
- Status: open
- Owner: maintainer
- Carrier-Declined: Product scope decision (`ROLL-39`); excluded from this hardening Set pending maintainer selection.
- Recommended answer: Keep all additive v1.5.0 features out of Set `assess-8l` and file separate backlog items only for maintainer-selected capabilities (recommendation strength: `strong`).

### OQ-06: Keep `requires-python = ">=3.8"` across `1.x` and add major-version upper bounds on `[tui]` (`textual<9`, `rich<16`)?

- Blocking: no
- Status: open
- Owner: maintainer
- Carrier-Declined: Maintainer dependency-policy choice; Set `assess-8l` keeps `>=3.8`, documents the `[tui]` `>=3.8.1` floor, and expands CI matrix verification in `6y55x4`.
- Recommended answer: Keep `requires-python = ">=3.8"` across 1.x and verify `[tui]` + Python `<3.11` in CI via `6y55x4` (recommendation strength: `medium`).

### OQ-07: Retain `[Y/n]` on `pubrun bench` GitHub contribution prompt (2026-07-22 decision) or flip to `[y/N]`?

- Blocking: no
- Status: open
- Owner: maintainer
- Carrier-Declined: Existing 2026-07-22 maintainer decision retained in `2ge0ea`; no change required unless the maintainer reverses that decision.
- Recommended answer: Retain `[Y/n]` per the recorded 2026-07-22 maintainer decision (recommendation strength: `strong`).

## Validation and cross-check (verify before reporting the Set complete)

Validation-state rule: inspect evidence in a separate pass. Accepted validation results: blocked, failed, pass, pending; terminal gate demands `pass`.

- [ ] V-01 validates E-01
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-01-1o1cua-config-cwd-artifact-write-safety-strict-json-and-core-api-er.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-02-76z7ww-fork-spawn-signal-console-subprocess-and-lifecycle-resource.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-03-l596kn-file-i-o-o-1-indexing-record-cap-and-streaming-hash-fast-pat.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-06 validates E-06
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-06-m5s3g8-status-clean-and-run-scanning-safety-scalability-and-termina.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-07 validates E-07
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-07-caeqdz-diff-methods-diagnostics-and-meta-snapshot-correctness-and-s.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-08 validates E-08
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-08-2ge0ea-cli-ergonomics-dir-pubrun-output-dir-json-output-streaming-c.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-09 validates E-09
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-09-3q5rd5-tui-safety-meta-ref-hydration-memory-responsiveness-and-usab.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

- [ ] V-10 validates E-10
  - Required evidence: Pasted confirmation that `.aw/records/plans/executed/20261127-assess-8l-10-6y55x4-ci-compatibility-matrix-scaling-benchmarks-and-whole-set-ver.ipd.md` exists with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

1. **Open questions and approval:** This orchestrator and its ten child plans are proposals with zero blocking open questions (`OQ-01` through `OQ-07` are non-blocking and carry `- Carrier-Declined:`). None of the plans execute automatically: each plan MUST be reviewed (`/plan-review` or `aw agy review`) and explicitly approved by a human (`aw set plan approved ... --by-human`) before execution.
2. **Scope declaration:** `- Scope-Paths:` declares only this orchestrator file (`.aw/records/plans/pending/20261127-assess-8l-00-k80suw-eight-lens-cross-concern-assessment-rollup-ui-ux-self-docs-c.ipd.md`); this orchestrator modifies no product code, tests, docs, or CI files. If finalization records any delta from `- Scope-Paths:`, justify it with `--scope-reason` or `--scope-ack`.
3. **Validation honesty (hard MUST):** Every `V-01` through `V-10` item MUST record actual confirmation that its child plan reached `.aw/records/plans/executed/` with `- Status: executed`, all `E-*` performed, all `V-*` passed, and `aw ipd lint --phase post-transition` passing.
4. **Commits and push policy:** Any lifecycle commit uses `aw commit` path-scoped to only the changed plan files (never `git add -A`, bare `git add`, `git commit -a`, or raw `git commit`). Never push, tag, or publish.
5. **Lifecycle finalization:** On completion, this orchestrator MUST be retired to `.aw/records/plans/executed/` only after all ten children (`1o1cua` through `6y55x4`) reach `executed` on disk and orchestrator coverage passes. When run under `aw oc run` or `aw agy run`, the runner automatically retires this orchestrator without spending an agent turn; when finalized manually outside a runner, the executor runs `aw ipd finalize k80suw` (never hand-roll `git mv` to `executed/`).
