# IPD: Fix functional specification, HPC guide, and research-use guide inaccuracies

- Date: 2026-11-25
- Kind: child
- Concern: `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md` contain high-severity inaccuracies including an unrunnable HPC `PUBRUN_META_REF=meta.json` workflow, misattributed `system_memory`/`load_average`/`system_iowait_pct` metrics on `pubrun inspect`, removed `-f` short flag for `pubrun combined --force`, wrong `pubrun report`/`show`/`diff`/`methods` CLI specifications, and 8 missing primary CLI subcommands.
- Scope: `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md`.
- Scope-Paths: docs/functional_spec.md, docs/hpc.md, docs/research-use.md
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix HPC meta_ref and inspect/res attribution, research-use input claims, and functional_spec.md CLI and behavior drift
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 4
- Highest E allocated: 04
- Author: Antigravity
- Id: wjsccu

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 4 documentation fixes (17 verified findings across `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md`)
- 2026-11-25 draft (Antigravity): created.

## Goal

Align `docs/hpc.md`, `docs/research-use.md`, and `docs/functional_spec.md` with the live runtime implementation (`src/pubrun/`) and JSON Schema (`schemas/manifest.schema.json`), including the `PUBRUN_RUN_MODE_OVERRIDE` environment-variable references tracked in open backlog `aqb2bu`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix `docs/hpc.md` and `docs/research-use.md`

- [ ] E-01 Fix all verified inaccuracies in `docs/hpc.md` (with no em or en dashes in added or edited lines):
  - **Parent-child hydration (`meta_ref`)**: replace the unrunnable `PUBRUN_META_REF=meta.json` example with a working shared-path example (`pubrun meta --out /shared/proj/meta.json` and `export PUBRUN_META_REF=/shared/proj/meta.json`) paired with configuring `[report].meta_ref_allowed_dirs = ["/shared/proj"]` (or `[report].allow_external_meta_ref = true`) in `.pubrun.toml`, explaining that relative paths resolve against each child's run directory and paths outside it are blocked by policy (`src/pubrun/report/utils.py::hydrate_manifest`, `_is_meta_ref_allowed`). Add `host` to hydrated sections (`HYDRABLE_SECTIONS`), clarify `pubrun meta` captures 6 sections (not `process`), and list all hydrating callers (`show`/`report`, `methods`, `inspect`, `rerun --preflight`, `diff`, Python `pubrun.diff()`, and TUI).
  - **System metrics (`inspect` vs `res`)**: correct the claim that `inspect` "records" `system_memory`, `load_average`, and `system_iowait_pct`: clarify that `pubrun` records these into `manifest.json` during the run (`ResourceWatcher` and `get_filesystem`), that `pubrun inspect` checks filesystem mounts and capture completeness (read-only), and that **`pubrun res`** displays `system_memory`, `load_average`, `system_iowait_pct`, and per-process I/O counters (while `pubrun self-check` inspects live host memory/load).
  - **File-I/O capture completeness**: mention `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` alongside `pubrun.open(...)` for libraries that do not use Python `open()`.
  - **Benchmarking on HPC**: state that `pubrun bench` requires a source checkout (`git clone`, not a pip wheel), clarify that `benchmarks/submit_bench.sh` picks a random idle Slurm node via `sinfo` when available (whereas PBS/LSF/SGE scripts let the scheduler place the job), and note the Slurm login-node submit-and-wait (`--wait-timeout`) plus `--submit-file` recovery/air-gapped workflow.
  - Depends on: none
  - Expected outcome: Every HPC command, metric attribution, file-provenance note, and Slurm workflow in `docs/hpc.md` matches live code.
  - Execution state: pending

- [ ] E-02 Fix verified inaccuracies in `docs/research-use.md` (with no em or en dashes in added or edited lines):
  - Qualify automatic input-file capture under bare `import pubrun`: explain that bare `import pubrun` heuristically scans `sys.argv` for existing file paths (`invocation.inputs`), whereas observed file-I/O provenance and content digests for datasets read through libraries like pandas/NumPy/h5py use `pubrun.open(...)` or `pubrun.register_input()`/`register_output()`/`register_file()` (referencing `examples/12_external_file_provenance.py`).
  - Update the example script range from `00_auto_start.py` through `11_cli_report.py` to `00_auto_start.py` through `12_external_file_provenance.py`.
  - Depends on: none
  - Expected outcome: `docs/research-use.md` accurately distinguishes automatic CLI-arg input capture from explicit file-I/O provenance and lists all 13 numbered examples.
  - Execution state: pending

### Task group 2: Fix `docs/functional_spec.md`

- [ ] E-03 Fix Sections 1-10 and 12-17 of `docs/functional_spec.md` (with no em or en dashes in added or edited lines):
  - Update the header status (`Status: v1.0.0`) to reflect the current codebase (`Status: Current (schema v1.0)`).
  - Section 3.3: note `_is_pubrun_cli_invocation()` also suppresses auto-start for `pbr` and `python -m pubrun` (via `pubrun.__main__`, `__main__.__spec__.name`, and `runpy` frames), not only `sys.argv[0]`.
  - Section 5.1 / 5.3: add `filesystem`, `data_files`, `pubrun_imports`, and `profiling` (noting `profiling` emits `profile-*.prof` and `profile_saved` events rather than a top-level manifest key), add `"off"` to `packages` and `environment`, and remove `Artifacts` from Section 5.3 Deferred (cross-referencing `data_files`, `artifact()`, `register_output()`, `register_file()`).
  - Section 6 (and examples in Sections 3/10): mark `[core].profile` and `PUBRUN_PROFILE` as deprecated and inert (emits `profile_deprecated` notice), and replace `profile="deep"` examples with active overrides.
  - Section 7.1 & 9.1: add remaining emitted event types (`resource_sample`, `profile_saved`, `input_dataset`, `output_artifact`, `mixed_dataset`, `warning`) to Section 7.1, and add `"timeout"` and `"pending"` to the `capture_state.status` enum in Section 9.1.
  - Section 10.2 / 10.3 / 10.4: add `PUBRUN_RUN_MODE_OVERRIDE` (satisfying the `functional_spec.md` portion of open backlog `aqb2bu`), `NO_COLOR`, and `PUBRUN_DEBUG` to Sections 10.2/10.3 (noting `pubrun run --mode` sets `PUBRUN_RUN_MODE_OVERRIDE` as well as `PUBRUN_IMPORT_MODE`), add `[report]` (`allow_external_meta_ref`, `meta_ref_allowed_dirs`) to Section 10.4, and mark `[logging].write_summary` as reserved/unimplemented.
  - Section 12.1: fix the run directory path template from `<base_dir>/runs/pubrun-.../` to `<output_dir>/pubrun-.../` (noting `<output_dir>` defaults to `./runs`).
  - Section 14.1: fix `pubrun.print()` (skips direct `stdout.log` write when active console tee already captures `sys.stdout`, when `file=` is not stdout, or inside `paused()`), fix `tracked_run()`/`audit_run()` (`KeyboardInterrupt` -> `"interrupted"`, `SystemExit(0)`/`None` -> `"completed"`, other exceptions / non-zero `SystemExit` -> `"failed"`), and note `annotate(message=None, ...)`, `diff(a, b, ignores=None)`, and `register_file(..., role="input_output")`.
  - Section 16 & Section 17: update Resource Watcher (Windows uses Win32 `GetProcessMemoryInfo` via `ctypes` with `wmic` fallback; Linux tree walks all `/proc/<pid>/task/<tid>/children`; tree CPU is Linux-only; add `poll_timeout`, `system_metrics`, `peak_tree_cpu_percent`, `system_memory`, `load_average`, `system_iowait_pct`, `io_counters`, `capture_state`); fix Section 17 HPC `meta_ref` workflow to use a shared path + `[report].meta_ref_allowed_dirs`, add `host`, clarify 6 meta-snapshot sections, and list all hydrating commands.
  - Depends on: none
  - Expected outcome: Sections 1-10 and 12-17 of `docs/functional_spec.md` match live code and schema.
  - Execution state: pending

- [ ] E-04 Fix Section 11 (CLI) of `docs/functional_spec.md` (with no em or en dashes in added or edited lines):
  - Replace the inaccurate `report [RUN_DIR ...]` section with primary `pubrun show [RUN_DIR] [logs|env|packages]` (noting hidden compatibility alias `report`), documenting `--utc`, filter-based multi-run display, and `show [run|default] config [--all]`.
  - Fix `pubrun combined`: change `[-f|--force]` to `[--force]` (`-f` is `--filter QUERY`) and note standard run-filter options.
  - Fix `pubrun diff`: change synopsis to `[RUN_DIR_A] [RUN_DIR_B] [OPTIONS]`, mark `--standard` as the default (not `--basic`), and add `--table` and run-filter options.
  - Fix `pubrun methods`: state `--format` defaults to `markdown` in the CLI (`[methods].format` controls the auto-generated file at finalization) and add `--all` and run-filter options.
  - Fix `pubrun rerun`: add `--preflight`, `--strict`, `--fail-on`, `--json`, and run-filter options.
  - Mark `--show-config` as hidden/deprecated in favor of `pubrun show default config`, fix `--info` (import-mode flags + invocation/hardware JSON, not version/env vars) and `--run-tests` (embedded mock test plus pytest only in a source checkout), and add concise entries for the 8 omitted primary subcommands (`init`, `inspect`, `self-check`, `bench`, `res`/`cpu`/`mem`, `ui`/`tui`/`gui`, `report-bug`/`feedback`, plus global `--version`, `--no-color`, and `pbr` alias).
  - Depends on: E-03
  - Expected outcome: Section 11 of `docs/functional_spec.md` accurately documents the full shipped CLI surface.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`).
- `src/pubrun/report/utils.py::HYDRABLE_SECTIONS` has 7 sections including `"host"`, and `hydrate_manifest` resolves relative `meta_ref` against `Path(manifest_path).parent` and enforces `_is_meta_ref_allowed()`.
- `src/pubrun/__main__.py` binds `-f` to `--filter` on `combined`, `--format` default `"markdown"` on `methods`, default `depth="standard"` on `diff`, and `nargs="?"` positionals on `show`/`report`.
- Open backlog item `aqb2bu` tracks adding `PUBRUN_RUN_MODE_OVERRIDE` to `docs/functional_spec.md` sections 10.2/10.3 and `docs/configuration.md`; E-03 covers the `docs/functional_spec.md` portion (and sibling `pqcx6o` covers `docs/configuration.md`).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| S-01 | High | Low | HPC Operator / Novice | `docs/functional_spec.md` Sec 17 & `docs/hpc.md` vs `src/pubrun/report/utils.py::hydrate_manifest` & `meta_snapshot.py` | Unrunnable `PUBRUN_META_REF=meta.json` workflow; omits `[report].meta_ref_allowed_dirs`, `host` section, and hydrating callers. |
| S-02 | High | Low | HPC Operator | `docs/hpc.md` vs `src/pubrun/report/reproducibility.py` & `diagnostics.py` | Misattributes `system_memory`, `load_average`, and `system_iowait_pct` to `pubrun inspect` (and says `inspect` records them) instead of `pubrun res`. |
| S-03 | High | Low | Operator | `docs/functional_spec.md` Sec 11 `combined` vs `src/pubrun/__main__.py` | Documents removed `-f` short flag for `--force`; `-f` is now `--filter`. |
| S-04 | High | Low | Novice / Operator | `docs/functional_spec.md` Sec 11 `report` vs `src/pubrun/__main__.py` `show_parser` | Documents non-existent `report [RUN_DIR ...]` and omits primary `show` command and `show config`. |
| S-05 | Medium | Low | Operator / Novice | `docs/functional_spec.md` Sec 11 (`diff`, `methods`, `rerun`, `--show-config`, `--info`, `--run-tests`, 8 missing subcommands) | Wrong `diff` default (`--basic` vs `--standard`), false `methods` config claim, and 8 omitted primary subcommands. |
| S-06 | Medium | Low | Novice / Operator | `docs/functional_spec.md` Secs 5, 6, 7.1, 9.1, 12.1, 14.1, 16 vs `src/pubrun/` | Deprecated `[core].profile` described as active, erroneous `/runs/` in `output_dir` template, missing categories/events/statuses, stale `print()`/`tracked_run()`/ResourceWatcher details. |
| S-07 | Medium | Low | HPC Operator / Novice | `docs/hpc.md` benchmarking section vs `benchmarks/submit_bench.sh` & `src/pubrun/__main__.py` | Misstates Slurm `submit_bench.sh` idle-node placement and omits `pubrun bench` source-checkout prerequisite and Slurm login-node wait. |
| S-08 | Low | Low | Novice / Operator | `docs/research-use.md`, `docs/hpc.md`, `docs/functional_spec.md` minor omissions | Overstates bare `import pubrun` input capture, omits `12_external_file_provenance.py`, omits `register_*()` in `hpc.md`, and omits `NO_COLOR`/`PUBRUN_DEBUG`/`[report]`/`python -m pubrun` in `functional_spec.md`. |

## Proposed changes (ordered, validatable)

1. Fix `docs/hpc.md` `meta_ref`, `inspect`/`res`, `register_*()`, and HPC benchmarking sections (E-01; Remediation Risk: Low).
2. Fix `docs/research-use.md` input-capture nuance and `00`-`12` example list (E-02; Remediation Risk: Low).
3. Fix `docs/functional_spec.md` Sections 1-10 and 12-17 (E-03; Remediation Risk: Low).
4. Fix `docs/functional_spec.md` Section 11 CLI reference (E-04; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Wiring `pubrun methods` CLI to consult `[methods].format` is deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality).
  - Carrier-Declined: Runtime CLI behavior change outside documentation-only scope; recorded in orchestrator `86cd17`.

## Scope check

- Over-scope: none. Only `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md` are modified.
- Under-scope: none.

## Required tests / validation

- Diff inspection of `docs/hpc.md`, `docs/research-use.md`, and `docs/functional_spec.md`.
- Zero em/en dashes (`\u2013`, `\u2014`) in added lines of all three files.
- Internal link and anchor validation across all three files.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- Pure documentation synchronization with live code; no runtime behavior changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/hpc.md` confirming working `PUBRUN_META_REF` + `[report].meta_ref_allowed_dirs` + `host`, `inspect` vs `res` attribution, `register_*()`, and `pubrun bench` checkout/Slurm mechanics; plus pasted zero-dash check on added lines exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/research-use.md` confirming qualified bare-import input capture (`sys.argv` vs `pubrun.open()`/`register_*()`) and `00_auto_start.py` through `12_external_file_provenance.py`; plus pasted zero-dash check on added lines exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for Sections 1-10 and 12-17 confirming header update, `python -m pubrun` detection, Section 5 categories, deprecated `[core].profile`, Section 7.1 events, Section 9.1 `timeout`/`pending`, Sections 10.2-10.4 (`PUBRUN_RUN_MODE_OVERRIDE`, `NO_COLOR`, `PUBRUN_DEBUG`, `[report]`, `[logging]`), Section 12.1 `<output_dir>/pubrun-.../`, Section 14.1 `print()`/`tracked_run()`/`audit_run()`, Section 16 Resource Watcher, and Section 17 HPC `meta_ref`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for Section 11 confirming `show` + hidden `report`, `combined --force` (no `-f`), `diff` default `--standard`, `methods` default + `--all`, `rerun --preflight`, deprecated `--show-config`, `--info`/`--run-tests`, and the 8 added primary subcommands; pasted zero-dash check on added lines of `docs/functional_spec.md` exiting 0; pasted link/anchor check across all three files exiting 0; and pasted `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`).
2. Scope declaration: modify only `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md`.
3. Validation honesty: run every required validation command and paste actual output into each `V-*` item.
4. Commit discipline: commit through `aw commit wjsccu -- docs/functional_spec.md docs/hpc.md docs/research-use.md`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: finalize through `aw ipd finalize wjsccu` (or the runner) once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
