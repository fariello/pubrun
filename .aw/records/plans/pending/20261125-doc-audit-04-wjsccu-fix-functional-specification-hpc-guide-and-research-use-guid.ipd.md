# IPD: Fix functional specification, HPC guide, and research-use guide inaccuracies

- Date: 2026-11-25
- Kind: child
- Concern: `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md` contain high-severity inaccuracies including an unrunnable HPC `PUBRUN_META_REF=meta.json` workflow, misattributed `system_memory`/`load_average`/`system_iowait_pct` metrics on `pubrun inspect`, removed `-f` short flag for `pubrun combined --force`, wrong `pubrun report`/`show`/`diff`/`methods` CLI specifications, and 10 omitted primary CLI subcommands.
- Scope: `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md`.
- Scope-Paths: docs/functional_spec.md, docs/hpc.md, docs/research-use.md
- Item-Dependencies: none
- Status: reviewed
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Fix HPC meta_ref and inspect/res attribution, research-use input claims, and functional_spec.md CLI and behavior drift
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 4
- Highest E allocated: 06
- Author: Antigravity
- Id: wjsccu

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 /plan-review (Gemini 4 Neon, Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001..PR-009 all FIXED; review record `.aw/records/reviews/20261125-doc-audit-04-wjsccu-fix-functional-specification-hpc-guide-and-research-use-guid.review.md`.
- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 4 documentation fixes (17 verified findings across `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md`)
- 2026-11-25 draft (Antigravity): created.

## Goal

Align `docs/hpc.md`, `docs/research-use.md`, and `docs/functional_spec.md` with the live runtime implementation (`src/pubrun/`) and JSON Schema (`schemas/manifest.schema.json`), preserving the `PUBRUN_RUN_MODE_OVERRIDE` documentation already landed in `docs/functional_spec.md` by executed plan `87qr8h` (closed backlog `aqb2bu`).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

Heading invariant: preserve all existing Markdown headings in `docs/hpc.md`, `docs/research-use.md`, and `docs/functional_spec.md` unchanged except renaming `### 11.6 Run Diagnostics (`report`)` to `### 11.6 Run Diagnostics (`show`)` in `docs/functional_spec.md` (no inbound anchor targets `#116-run-diagnostics-report`) and adding new Section 11 subsections in `E-06`. In particular, preserve `docs/hpc.md#Where pubrun fits (alongside MLflow, Weights and Biases, and DVC)` and `docs/hpc.md#Diagnosing a finished run`, which are linked from `docs/research-use.md` and `docs/cli.md`. Do not introduce em or en dashes (`\u2013`, `\u2014`) in any added or edited line.

### Task group 1: Fix `docs/hpc.md` and `docs/research-use.md`

- [ ] E-01 Fix all verified inaccuracies in `docs/hpc.md` (with no em or en dashes in added or edited lines):
  - **Parent-child hydration (`docs/hpc.md#Parent snapshots (meta_ref)`)**: Replace the unrunnable `pubrun meta --out meta.json` and `PUBRUN_META_REF=meta.json` workflow with a working shared-path example (`pubrun meta --out /shared/proj/meta.json` and `export PUBRUN_META_REF=/shared/proj/meta.json`) paired with configuring `[report].meta_ref_allowed_dirs = ["/shared/proj"]` (or `[report].allow_external_meta_ref = true`) in `.pubrun.toml`. Explain that relative `meta_ref` paths resolve against each child's run directory (`Path(manifest_path).parent`) and paths outside allowed directories are blocked by policy before file existence checks (`src/pubrun/report/utils.py::hydrate_manifest_with_report`, `src/pubrun/report/utils.py::_is_meta_ref_allowed`). Add `host` to the hydrated sections list (`src/pubrun/report/utils.py::HYDRABLE_SECTIONS`: `hardware`, `process`, `python`, `packages`, `environment`, `git`, `host`), clarify that `pubrun meta` writes 6 sections (`hardware`, `python`, `packages`, `git`, `environment`, `host` - not `process`; `src/pubrun/report/meta_snapshot.py::generate_meta_snapshot`), and list all hydrating callers: `pubrun show` (and hidden alias `report`), `pubrun res` (`resources`/`cpu`/`mem`), `pubrun methods` (including `--all`), `pubrun inspect`, `pubrun rerun --preflight`, `pubrun diff`, Python `pubrun.diff()`, and the TUI (`pubrun ui`/`tui`/`gui`).
  - **System metrics (`docs/hpc.md#Diagnosing a finished run`)**: Replace the claim starting `` `inspect` records, when available ``. Clarify that during a run, `pubrun` records `filesystem` (`src/pubrun/capture/filesystem.py::get_filesystem`) and, when `[capture.resources].depth != "off"` and `[capture.resources].system_metrics = true` (default), `resources.{system_memory, load_average, system_iowait_pct, io_counters}` (`src/pubrun/capture/resources.py::ResourceWatcher`) into `manifest.json`. After a run, `pubrun inspect` is read-only and evaluates recorded network filesystems, capture completeness, parent-snapshot checks, and optional `--preflight` checks; **`pubrun res`** displays `system_memory`, `load_average`, `system_iowait_pct` (node-wide, indicative only), and per-process `io_counters` (`src/pubrun/report/diagnostics.py::print_resources_report`); and `pubrun self-check` inspects live host filesystems, available memory, and load average (`src/pubrun/report/checks.py::live_findings`).
  - **File-I/O capture completeness (`docs/hpc.md#Capture-completeness`)**: Add `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` alongside `pubrun.open(...)` for libraries that do not use Python `open()`.
  - **Benchmarking on HPC (`docs/hpc.md#Running the benchmark suite on a cluster`)**: State that `pubrun bench` requires a source checkout (`git clone`; `benchmarks/harness.py` is not shipped in the pip wheel, `src/pubrun/__main__.py::_run_bench`). Clarify that `benchmarks/submit_bench.sh` queries `sinfo` and pins to a random idle Slurm node via `--nodelist` when idle nodes are available (falling back to unpinned scheduler placement when none are idle), whereas `submit_bench_pbs.sh`, `submit_bench_lsf.sh`, and `submit_bench_sge.sh` submit to the default queue and let the scheduler place the job. Document the Slurm login-node submit-and-wait flow (`--wait-timeout`, default about 1800s; `0` waits indefinitely) plus `--submit-file` for recovery or air-gapped compute nodes.
  - Depends on: none
  - Expected outcome: Every HPC command, hydration caller list, metric attribution, file-provenance note, and Slurm workflow in `docs/hpc.md` matches live code.
  - Execution state: pending

- [ ] E-02 Fix verified inaccuracies in `docs/research-use.md` (with no em or en dashes in added or edited lines):
  - **Input-file capture nuance**: Qualify the opening paragraph and `Unversioned inputs` bullet so they distinguish automatic CLI-argument discovery from observed file-I/O provenance: bare `import pubrun` heuristically scans `sys.argv` for existing file paths (`invocation.inputs`, `src/pubrun/capture/invocation.py::get_invocation`), whereas observed file-I/O provenance and optional content digests for datasets read or written through libraries such as pandas, NumPy, or h5py use `pubrun.open(...)` or `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` (referencing `examples/12_external_file_provenance.py`).
  - **Example script range (`docs/research-use.md#Public example workflow`)**: Update `00_auto_start.py` through `11_cli_report.py` to `00_auto_start.py` through `12_external_file_provenance.py` (all 13 numbered scripts). Leave the Zenodo DOI line in `docs/research-use.md#How to cite pubrun` unchanged so `tests/test_cli.py::TestCitationConsistency` continues to pass.
  - Depends on: none
  - Expected outcome: `docs/research-use.md` accurately distinguishes automatic CLI-arg input capture from explicit file-I/O provenance, lists all 13 numbered examples, and preserves the Zenodo DOI line.
  - Execution state: pending

### Task group 2: Fix `docs/functional_spec.md`

- [ ] E-03 Fix the header and Sections 3, 5, 6, 7, 9, and 10 of `docs/functional_spec.md` (with no em or en dashes in added or edited lines):
  - **Header**: Change `> Status: v1.0.0` to `> Status: Current (schema v1.0)`.
  - **Section 3.3 (`Auto-Start Behavior`)**: Update the CLI self-suppression bullet to match `src/pubrun/core.py::_is_pubrun_cli_invocation`: suppresses auto-start for `pubrun`, `pubrun.exe`, `pbr`, and `pbr.exe` (`sys.argv[0]` basename), an already-imported `pubrun.__main__`, a `__main__.__spec__.name` of `"pubrun"` or `"pubrun.__main__"`, and `python -m pubrun` via `runpy` stack frames (`mod_name == "pubrun"` or starting with `"pubrun."`).
  - **Section 3.5, Section 6, and Section 10.2 (`profile` deprecation)**: Mark `[core].profile` and `PUBRUN_PROFILE` in Section 6 (and the Section 10.3 `PUBRUN_PROFILE` row) as deprecated and inert: still accepted for compatibility, records a `profile_deprecated` notice in `config.notices` when set to any value other than `"default"` (`src/pubrun/config.py::profile_deprecation_notice`), and never controls capture depth. Replace `@pubrun.audit_run(profile="deep")` in Section 3.5 and `pubrun.start(profile="deep")` in Section 10.2 with active overrides (such as `@pubrun.audit_run(output_dir="./audit_runs")` and `pubrun.start(output_dir="./runs", console={"capture_mode": "standard"})`).
  - **Sections 5.1 and 5.3 (`Capture Categories`)**: In Section 5.1, add rows for `Filesystem` (`filesystem`, no config section, always captured), `Data files` (`data_files`, `[capture.file_io]`, levels `none`, `name`, `stat`, `realpath`, `hash`), `Import provenance` (`pubrun_imports`, `[imports]`, always captured), and `Profiling` (no top-level manifest key; writes `profile-<phase>.prof` files and emits `profile_saved` events, `[capture.profiling]`, `enabled`, `backend`). Add `"off"` to the Modes / Depth column for `packages` (`src/pubrun/capture/packages.py`) and `environment` (`src/pubrun/capture/environment.py`). In Section 5.3 (`Deferred (Future Work)`), remove `Artifacts` and note that file tracking is implemented via `data_files`, `pubrun.artifact()`, `pubrun.open()`, `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()`.
  - **Sections 7.1 and 9.1 (`Events` and `Capture State`)**: In Section 7.1, add the remaining emitted event types verified in `src/pubrun/`: `resource_sample` (`src/pubrun/capture/resources.py::ResourceWatcher._update_metrics`), `profile_saved` (`src/pubrun/core.py::phase._emit_profile_saved`), `input_dataset`, `output_artifact`, and `mixed_dataset` (`src/pubrun/capture/file_io.py::_event_type_for_role` and `ProvenanceFileProxy`), and `warning` (`src/pubrun/tracker.py` mid-run storage directory migration). In Section 9.1, add `timeout` and `pending` to the `capture_state.status` enum (`schemas/manifest.schema.json` `$defs.status_value`).
  - **Sections 10.2, 10.3, and 10.4 (`Configuration System`)**: Preserve the existing `PUBRUN_RUN_MODE_OVERRIDE` text in Section 10.2 and row in Section 10.3 verbatim (already landed by executed plan `87qr8h`, which closed backlog `aqb2bu`). Add `NO_COLOR` (disables ANSI color output in CLI/report/diff/status renderers; read by CLI and report modules, not `resolve_config()`) and `PUBRUN_DEBUG` (enables `[DEBUG]` diagnostic output in `src/pubrun/report/output.py::debug_enabled`; not read by `resolve_config()`) to Section 10.3. In Section 10.4, add report/hydration policy (`[report]`: `allow_external_meta_ref`, `meta_ref_allowed_dirs`) and mark `[logging].write_summary` as reserved and not yet implemented (`src/pubrun/resources/default.toml`).
  - Depends on: none
  - Expected outcome: The header and Sections 3, 5, 6, 7, 9, and 10 of `docs/functional_spec.md` match live code and schema, with existing `PUBRUN_RUN_MODE_OVERRIDE` rows preserved verbatim.
  - Execution state: pending

- [ ] E-05 Fix Sections 12, 14, 16, and 18 of `docs/functional_spec.md` (with no em or en dashes in added or edited lines; leave Section 17 `Ghost Mode` untouched):
  - **Sections 12.1 and 12.3 (`Run Directory`)**: Fix Section 12.1 template from `<base_dir>/runs/pubrun-<script>-<timestamp>-<pid>-<run_id>/` to `<output_dir>/pubrun-<script>-<timestamp>-<pid>-<run_id>/` (noting `<output_dir>` is `[core].output_dir`, defaulting to `./runs`, per `src/pubrun/tracker.py::Run.__init__`). In Section 12.3 (`Contents`), add `profile-<phase>.prof` (when profiling is enabled), files written by `pubrun.report()` / `pubrun.artifact()`, and transient `.pubrun.lock` during active execution to the optional contents list.
  - **Section 14.1 (`Implemented Functions`)**:
    - Update `annotate(message=None, **kwargs)` signature (`message` optional) and note that `[events].on_inactive_annotate` applies to all seven inactive-guarded functions (`annotate()`, `phase()`, `report()`, `artifact()`, `register_file()`, `register_input()`, `register_output()`; `src/pubrun/core.py::_handle_inactive`).
    - Update `tracked_run(**overrides)` and `audit_run(func=None, **overrides)` outcome rules (`src/pubrun/core.py::_classify_exit_outcome`, `_stop_for_exit`): `KeyboardInterrupt` -> `"interrupted"`, `SystemExit(0)` or `SystemExit(None)` -> `"completed"`, other exceptions or non-zero `SystemExit` -> `"failed"` (and `SystemExit` records its exit code on signal capture).
    - Update `diff(run_dir_a, run_dir_b, ignores=None)` (`ignores` optional, defaults to `[diff].ignore_standard` or legacy `[diff].ignore`, hydrates both manifests; `src/pubrun/core.py::diff`).
    - Update `print(*args, **kwargs)` (`src/pubrun/core.py::_should_log_pubrun_print`): skips direct append to `stdout.log` when `file=` is not `sys.stdout`, inside `pubrun.paused()`, or when the run's active console tee on `sys.stdout` already records stdout.
    - Clarify `register_file` accepts `role="input" | "output" | "input_output"` (where `"input_output"` records into `data_files.mixed`).
  - **Section 16 (`Resource Watcher`)**: In Section 16.2, note that tree RSS runs on Linux and macOS (Windows falls back to process) while tree CPU is Linux-only, and add `poll_timeout` (default `3`s) and `system_metrics` (default `true`). In Section 16.3, update Linux tree walk to `/proc/<pid>/task/<tid>/children` across all threads (`src/pubrun/capture/resources.py::_get_linux_child_pids`), update Windows process RSS to Win32 `K32GetProcessMemoryInfo` / `psapi.GetProcessMemoryInfo` via `ctypes` with `wmic` subprocess fallback (`_get_rss_windows`), and note that tree CPU (`_poll_tree_cpu`) is Linux-only (`/proc/<pid>/stat` jiffy deltas). In Section 16.4, add `capture_state`, `peak_tree_cpu_percent` (for `scope = "tree"`, Linux-only, `% of one core`), and the optional `system_metrics` fields: `system_memory`, `load_average`, `system_iowait_pct` (Linux node-wide, indicative only), and `io_counters` (Linux `/proc/self/io` per-process `start`/`last`/`delta`).
  - **Section 18 (`HPC Parent-Child Hydration`)**: In Section 18.2, replace `export PUBRUN_META_REF=meta.json` with a matching shared absolute path (`pubrun meta --out /shared/proj/meta.json --deep` and `export PUBRUN_META_REF=/shared/proj/meta.json`) and note configuring `[report].meta_ref_allowed_dirs = ["/shared/proj"]` in `.pubrun.toml` (cross-referencing Section 18.5). In Section 18.3, add `host` to `HYDRABLE_SECTIONS` (all 7 sections: `hardware`, `process`, `python`, `packages`, `environment`, `git`, `host`), clarify that `pubrun meta` captures 6 sections (excluding `process`), and replace "a report/methods command" with all hydrating callers: `show`/`report`, `res`/`resources`/`cpu`/`mem`, `methods`, `inspect`, `rerun --preflight`, `diff`, Python `pubrun.diff()`, and the TUI.
  - Depends on: E-03
  - Expected outcome: Sections 12, 14, 16, and 18 of `docs/functional_spec.md` match live code and schema, and Section 17 (`Ghost Mode`) is untouched.
  - Execution state: pending

- [ ] E-04 Fix existing Section 11 CLI subsections (`11.2`-`11.4`, `11.6`-`11.9`, `11.11`-`11.12`, and `11.14`) of `docs/functional_spec.md` (with no em or en dashes in added or edited lines):
  - **Section 11 intro**: Note the `pbr` console script alias alongside `pubrun` and `python -m pubrun`.
  - **Section 11.2 (`--show-config`)**: Mark `--show-config` as hidden (`argparse.SUPPRESS`) and deprecated (emits a stderr deprecation notice pointing to `pubrun show default config`, while continuing to print `default.toml` to stdout; `src/pubrun/__main__.py::main`).
  - **Section 11.3 (`--info`)**: Fix description to match `src/pubrun/__main__.py::_show_info`: displays active import-mode flags (plus `PUBRUN_IMPORT_MODE` when set) and JSON for `invocation` and `hardware` (does not print `pubrun` version or general environment variables).
  - **Section 11.4 (`--run-tests`)**: Fix description to match `src/pubrun/__main__.py::_run_tests`: runs an embedded end-to-end mock script in a temporary directory, and runs `pytest tests/ -q` only when executed in a source checkout (`tests/` and `tox.ini` present).
  - **Section 11.6 (`report` -> `show`)**: Rename to `### 11.6 Run Diagnostics (`show`)` and replace the nonexistent `pubrun report [RUN_DIR ...]` multi-positional syntax with `pubrun show [RUN_DIR] [logs|env|packages] [--basic|--standard|--deep] [--utc] [FILTERS]` plus the config subforms (`pubrun show config [--all]`, `pubrun show default config`, `pubrun show run config [RUN_ID] [--all]`). Document filter-based multi-run display (`-f`, `-F`, `-s`, `-S`, `--older-than`, `--exit-code`, `-n`/`--limit`) and note that `report` remains a hidden compatibility alias (omitting `--all` and the third positional `RUN_ID` in `show run config <id>`).
  - **Section 11.7 (`methods`)**: State that CLI `--format` defaults to `markdown` (`src/pubrun/__main__.py` `methods_parser`; `[methods].format` controls only the auto-generated `methods.md`/`methods.tex` file at run finalization in `src/pubrun/writer.py::ArtifactWriter.write_artifacts`), and add `--all` (multi-run aggregation) and shared run-filter options (including `-n`/`--limit`).
  - **Section 11.8 (`rerun`)**: Add `--preflight`, `--strict`, `--fail-on {warn,mismatch,unknown}`, `--json` (all requiring `--preflight`; human-mode diagnostics go to stderr), and shared run-filter options (without `-n`/`--limit`).
  - **Section 11.9 (`diff`)**: Fix synopsis to `pubrun diff [RUN_DIR_A] [RUN_DIR_B] [OPTIONS]` (0, 1, or 2+ positionals; extra arguments beyond two are ignored), mark `--standard` as the default (not `--basic`), and add `--table` and shared run-filter options (without `-n`/`--limit`).
  - **Sections 11.11 (`status`) and 11.12 (`clean`)**: Add `--utc` and shared run-filter options (`-f`, `-F`, `-s`, `-S`, `--older-than`, `--exit-code`, `-n`/`--limit`) to `status`, and shared run-filter options (`-f`, `-F`, `-s`, `-S`, `--exit-code`, `-n`/`--limit`) to `clean`.
  - **Section 11.14 (`combined`)**: Change `[-f|--force]` to `[--force]` (`-f` is `--filter QUERY`, an intentional breaking change) and add shared run-filter options (including `-n`/`--limit`).
  - Depends on: E-05
  - Expected outcome: Every existing Section 11 subsection in `docs/functional_spec.md` matches `src/pubrun/__main__.py`.
  - Execution state: pending

- [ ] E-06 Add subsections to Section 11 of `docs/functional_spec.md` for all 10 omitted primary CLI subcommands and global CLI options (with no em or en dashes in added or edited lines):
  - Following `### 11.14 Log Interleaving (`combined`)`, add concise subsections covering every remaining primary subcommand shown by `python3 -m pubrun --help` (`src/pubrun/__main__.py::main`):
    - `init [DEST]`: creates `.pubrun.toml` (default `./.pubrun.toml`, refuses overwrite) and prints getting-started guidance.
    - `inspect [RUN_DIR]`: post-hoc reproducibility assessment and optional offline preflight (`--show-suggestions`/`-v`, `--preflight`, `--json`, `--strict`, `--fail-on {warn,mismatch,unknown}`, shared run filters without `-n`/`--limit`).
    - `self-check`: live machine health and filesystem/RAM/load check (`--show-suggestions`/`-v`, `--json`, `--strict`, `--quiet`/`-q`).
    - `bench`: overhead benchmark front-end requiring a source checkout (`--quick`/`--full`/`--rigorous`, `--no-baseline`, `--iterations`, `--passes`, `--local`/`--submit`, `--scheduler`, `-y`/`--yes`, `--unredacted`, `--json`, `--contribute`/`--no-contribute`, `--prepare-submission`, `--submit-file`, `--wait-timeout`, `--no-submit`, `--gh-repo`).
    - `res` (alias `resources`), `cpu`, and `mem`: resource utilization summary and ASCII charts (`[RUN_DIR]`, `--average`, `-l`/`--last`, `-w`/`--width`, shared run filters without `-n`/`--limit`; `res` also renders `system_memory`, `load_average`, `system_iowait_pct`, and per-process `io_counters`).
    - `ui` (aliases `tui`, `gui`): interactive Textual dashboard (`--dir PATH`, optional `pubrun[tui]` extra).
    - `report-bug` and `feedback`: two distinct primary subcommands that print environment diagnostics and open the GitHub issue tracker URL.
  - Document global CLI options (`--version`, `--no-color` accepted anywhere before `run`'s target command, plus `help` translation and `pbr` alias).
  - Depends on: E-04
  - Expected outcome: Section 11 of `docs/functional_spec.md` documents all 20 visible primary CLI subcommands, their aliases (`resources`, `tui`, `gui`, hidden `report`), and global flags.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`).
- `src/pubrun/report/utils.py::HYDRABLE_SECTIONS` has 7 sections including `"host"`, `src/pubrun/report/meta_snapshot.py::generate_meta_snapshot` writes 6 sections (not `"process"`), and `hydrate_manifest_with_report` resolves relative `meta_ref` against `Path(manifest_path).parent` and enforces `_is_meta_ref_allowed()` before existence checks.
- `src/pubrun/__main__.py` registers 20 visible primary subcommands (plus hidden alias `report`, aliases `resources`, `tui`, `gui`, and global `--version`/`--no-color`), binds `-f` to `--filter` on `combined`, sets `--format` default `"markdown"` on `methods`, sets default `depth="standard"` on `diff`, and uses `nargs="?"` positionals on `show`/`report`.
- Backlog item `aqb2bu` is already `done` (closed by executed plan `87qr8h`), which already added `PUBRUN_RUN_MODE_OVERRIDE` to `docs/functional_spec.md` Sections 10.2 and 10.3; E-03 preserves those rows verbatim.
- `tests/test_cli.py::TestCitationConsistency::test_doi_agrees_across_surfaces` reads `docs/research-use.md` and asserts the Zenodo DOI from `CITATION.cff` is present.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| S-01 | High | Low | HPC Operator / Novice | `docs/functional_spec.md#18.2 Workflow`, `docs/functional_spec.md#18.3 Hydration Rules`, and `docs/hpc.md#Parent snapshots (meta_ref)` vs `src/pubrun/report/utils.py::hydrate_manifest_with_report` and `src/pubrun/report/meta_snapshot.py::generate_meta_snapshot` | Unrunnable `PUBRUN_META_REF=meta.json` workflow; omits `[report].meta_ref_allowed_dirs` in workflow examples, omits `host` section and 6-section meta-snapshot clarification, and omits hydrating callers (`res`/`cpu`/`mem`, `methods`, `rerun --preflight`, `diff`, `pubrun.diff()`). |
| S-02 | High | Low | HPC Operator | `docs/hpc.md#Diagnosing a finished run` vs `src/pubrun/report/reproducibility.py` and `src/pubrun/report/diagnostics.py::print_resources_report` | Misattributes `system_memory`, `load_average`, and `system_iowait_pct` to `pubrun inspect` (and says `inspect` records them) instead of run-time capture displayed by `pubrun res`. |
| S-03 | High | Low | Operator | `docs/functional_spec.md#11.14 Log Interleaving (combined)` vs `src/pubrun/__main__.py` `combined_parser` | Documents removed `-f` short flag for `--force`; `-f` is now `--filter`. |
| S-04 | High | Low | Novice / Operator | `docs/functional_spec.md#11.6 Run Diagnostics (report)` vs `src/pubrun/__main__.py` `show_parser` | Documents nonexistent `report [RUN_DIR ...]` and omits primary `show` command and `show [run|default] config`. |
| S-05 | Medium | Low | Operator / Novice | `docs/functional_spec.md#11. CLI Tools` (`diff`, `methods`, `rerun`, `status`, `clean`, `--show-config`, `--info`, `--run-tests`, 10 omitted primary subcommands) vs `src/pubrun/__main__.py::main` | Wrong `diff` default (`--basic` vs `--standard`), false `methods` config claim, inaccurate `--info`/`--run-tests`, and 10 omitted primary subcommands (`init`, `inspect`, `self-check`, `bench`, `res`, `cpu`, `mem`, `ui`, `report-bug`, `feedback`). |
| S-06 | Medium | Low | Novice / Operator | `docs/functional_spec.md` Sections 3.3, 5, 6, 7.1, 9.1, 12.1, 14.1, 16 vs `src/pubrun/` and `schemas/manifest.schema.json` | Deprecated `[core].profile` described as active, erroneous `/runs/` in `output_dir` template, missing categories/events/statuses, stale `print()`/`tracked_run()`/`audit_run()`/`on_inactive_annotate`/ResourceWatcher details. |
| S-07 | Medium | Low | HPC Operator / Novice | `docs/hpc.md#Running the benchmark suite on a cluster` vs `benchmarks/submit_bench.sh` and `src/pubrun/__main__.py::_run_bench` | Misstates Slurm `submit_bench.sh` idle-node placement and omits `pubrun bench` source-checkout prerequisite and Slurm login-node submit-and-wait (`--wait-timeout`). |
| S-08 | Low | Low | Novice / Operator | `docs/research-use.md`, `docs/hpc.md`, `docs/functional_spec.md` minor omissions | Overstates bare `import pubrun` input capture, omits `12_external_file_provenance.py`, omits `register_*()` in `hpc.md`, and omits `NO_COLOR`/`PUBRUN_DEBUG`/`[report]`/`python -m pubrun` in `functional_spec.md`. |

## Proposed changes (ordered, validatable)

1. Fix `docs/hpc.md` `meta_ref`, `inspect`/`res`, `register_*()`, and HPC benchmarking sections (E-01; Remediation Risk: Low).
2. Fix `docs/research-use.md` input-capture nuance and `00`-`12` example list (E-02; Remediation Risk: Low).
3. Fix `docs/functional_spec.md` header and Sections 3, 5, 6, 7, 9, and 10 (E-03; Remediation Risk: Low).
4. Fix `docs/functional_spec.md` Sections 12, 14, 16, and 18 (E-05; Remediation Risk: Low).
5. Fix `docs/functional_spec.md` Section 11 existing CLI subsections (E-04; Remediation Risk: Low).
6. Add `docs/functional_spec.md` Section 11 subsections for the 10 omitted primary subcommands and global CLI options (E-06; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Wiring `pubrun methods` CLI to consult `[methods].format` is deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality).
  - Carrier-Declined: Runtime CLI behavior change outside documentation-only scope; recorded in orchestrator `86cd17`.
- Repo-wide em/en-dash cleanup in untouched historical paragraphs is deferred in orchestrator `86cd17` (this plan enforces zero dashes in added or edited lines only).
  - Carrier-Declined: Pre-existing repo-wide cleanup deferred separately in orchestrator `86cd17`.

## Scope check

- Over-scope: none. Only `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md` are declared and modified; these paths are strictly disjoint from Set `doc-audit` siblings (`0cjiv5`, `pqcx6o`, `dd7noz`, `77pdvl`, `2uwuiu`) and from executed plan `87qr8h` (`aqb2bu`).
- Under-scope: resolved during review (`pubrun res`/`cpu`/`mem` added to hydration caller lists; `Section 18` fixed from `Section 17`; `aqb2bu`/`87qr8h` overlap reconciled; 10 omitted primary subcommands plus `resources` alias and `status`/`clean` filter flags added; seven-function `on_inactive_annotate` scope and `TestCitationConsistency` test added).
- Requirement 12 (diagrams): no diagram is required. Every E-item applies bounded prose and table corrections to three existing documentation files without introducing a new multi-entity model, branch, loop, or lifecycle.

## Required tests / validation

Run and paste actual output for all of the following:

1. **Zero em/en dashes in added lines** (must exit 0 with `dashes_in_added=0`):

   ```sh
   python3 - <<'PY'
   import subprocess, sys
   diff = subprocess.check_output(
       ["git", "diff", "--unified=0", "--", "docs/hpc.md", "docs/research-use.md", "docs/functional_spec.md"],
       text=True,
   )
   hits = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++") and ("\u2013" in l or "\u2014" in l)]
   for h in hits:
       print("DASH:", h)
   print(f"dashes_in_added={len(hits)}")
   sys.exit(1 if hits else 0)
   PY
   ```

2. **Internal link and anchor validation** across all three edited files (baseline `broken=0`; must exit 0 with `broken=0`):

   ```sh
   python3 - <<'PY'
   import pathlib, re, sys
   def slugs_for(path):
       txt = path.read_text(encoding="utf-8")
       return {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#{1,6} +(.+?) *$", txt, flags=re.M)}
   bad = 0
   for f in ("docs/hpc.md", "docs/research-use.md", "docs/functional_spec.md"):
       p = pathlib.Path(f)
       body = p.read_text(encoding="utf-8")
       own = slugs_for(p)
       for t in re.findall(r"\]\(([^)\s]+)\)", body):
           if t.startswith(("http://", "https://", "mailto:")):
               continue
           if t.startswith("#"):
               ok = t[1:] in own
           else:
               rel, _, frag = t.partition("#")
               target = p.parent / rel
               ok = (not t.startswith("file:")) and target.exists()
               if ok and frag and target.is_file():
                   ok = frag in slugs_for(target)
           if not ok:
               bad += 1
               print("BROKEN", f, t)
   print(f"broken={bad}")
   sys.exit(1 if bad else 0)
   PY
   ```

3. **Path leak sanitizer**: `python3 scripts/sanitize_paths.py --check --all` (must exit 0).
4. **Citation consistency test** (reads `docs/research-use.md`): `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov` (must pass).
5. **CLI command coverage check** against live `python3 -m pubrun --help` (must exit 0 with `missing=[]`):

   ```sh
   python3 - <<'PY'
   import pathlib, re, subprocess, sys
   help_out = subprocess.check_output([sys.executable, "-m", "pubrun", "--help"], text=True)
   m = re.search(r"<command>\n(.*?)\n\nUse ", help_out, flags=re.S)
   cmds = re.findall(r"^    ([a-z][a-z0-9-]*)", m.group(1), flags=re.M)
   spec = pathlib.Path("docs/functional_spec.md").read_text(encoding="utf-8")
   sec11 = re.search(r"^## 11\. CLI Tools\b(.*?)^## 12\.", spec, flags=re.M | re.S).group(1)
   missing = [c for c in cmds if f"`{c}`" not in sec11 and f"pubrun {c}" not in sec11]
   print(f"commands={len(cmds)} missing={missing}")
   sys.exit(1 if missing else 0)
   PY
   ```

## Spec / documentation sync

- Pure documentation synchronization with live code (`src/pubrun/`) and JSON Schema (`schemas/manifest.schema.json`); no runtime behavior or schema contract changes.
- Sibling `doc-audit` plans own the matching fixes in the rest of the repository (`0cjiv5`: root docs and templates; `pqcx6o`: `docs/cli.md` and `docs/configuration.md`; `dd7noz`: `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, `docs/design/`; `77pdvl`: `docs/performance.md`, `benchmarks/README.md`, `CHANGELOG.md`, `CITATION.cff`; `2uwuiu`: `examples/`). Executed plan `87qr8h` (`aqb2bu`) already updated `PUBRUN_RUN_MODE_OVERRIDE` in `docs/functional_spec.md` Sections 10.2 and 10.3.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/hpc.md` confirming the shared-path `PUBRUN_META_REF` + `[report].meta_ref_allowed_dirs` example, `host` + 6-section `pubrun meta` note + full hydrating caller list (including `res`/`cpu`/`mem`), corrected `inspect` vs `res` vs `self-check` attribution, `register_input()`/`register_output()`/`register_file()`, and `pubrun bench` source-checkout + Slurm `sinfo` idle-node + `--wait-timeout`/`--submit-file` mechanics; pasted `grep -nE 'PUBRUN_META_REF=meta\.json|`inspect` records' docs/hpc.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); plus pasted zero-dash check from Required tests item 1 exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/research-use.md` confirming qualified bare-import input capture (`sys.argv` vs `pubrun.open()`/`register_*()`, citing `examples/12_external_file_provenance.py`) and `00_auto_start.py` through `12_external_file_provenance.py`; pasted `grep -n '11_cli_report\.py' docs/research-use.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); pasted `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov` passing; plus pasted zero-dash check from Required tests item 1 exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for header and Sections 3, 5, 6, 7, 9, and 10 confirming `Status: Current (schema v1.0)`, `_is_pubrun_cli_invocation()` (`pbr` and `python -m pubrun`), Section 5.1/5.3 categories and `"off"` modes, deprecated `[core].profile`/`PUBRUN_PROFILE` with active replacements in Sections 3.5 and 10.2, Section 7.1 events (`resource_sample`, `profile_saved`, `input_dataset`, `output_artifact`, `mixed_dataset`, `warning`), Section 9.1 `timeout`/`pending`, preserved `PUBRUN_RUN_MODE_OVERRIDE` rows, added `NO_COLOR`/`PUBRUN_DEBUG`, `[report]`, and reserved `[logging].write_summary`; pasted `grep -nE 'Status: v1\.0\.0|profile="deep"' docs/functional_spec.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`).
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for Section 11 intro and subsections `11.2`-`11.4`, `11.6`-`11.9`, `11.11`-`11.12`, and `11.14` confirming `pbr` alias, hidden/deprecated `--show-config`, corrected `--info` and `--run-tests`, `show` + hidden `report` + `show [run|default] config`, `methods` default `markdown` + `--all`, `rerun --preflight`/`--strict`/`--fail-on`/`--json`, `diff` default `--standard` + `--table`, `status --utc`/filters + `clean` filters, and `combined --force` (no `-f`); pasted `grep -nE 'report \[RUN_DIR|--basic` \(default\)|\[-f\|--force\]' docs/functional_spec.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`).
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for Sections 12, 14, 16, and 18 (and confirming zero diff lines in Section 17 `Ghost Mode`) verifying `<output_dir>/pubrun-.../` and Section 12.3 optional files, Section 14.1 (`annotate(message=None, ...)`, seven-function `on_inactive_annotate`, `tracked_run()`/`audit_run()` exit-outcome rules, `diff(..., ignores=None)`, `print()` skip conditions, `register_file(..., role="input_output")`), Section 16 (Win32 `ctypes` + `wmic` fallback, `/proc/<pid>/task/<tid>/children`, Linux-only tree CPU, `poll_timeout`, `system_metrics`, `peak_tree_cpu_percent`, `system_memory`, `load_average`, `system_iowait_pct`, `io_counters`, `capture_state`), and Section 18 (shared-path `PUBRUN_META_REF` + `[report].meta_ref_allowed_dirs`, `host`, 6-section `pubrun meta`, full hydrating caller list including `res`/`cpu`/`mem`); pasted `grep -nE '<base_dir>/runs/pubrun-|PUBRUN_META_REF=meta\.json' docs/functional_spec.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`).
  - Observed evidence:
  - Result: pending

- [ ] V-06 validates E-06
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for the added Section 11 subsections covering all 10 omitted primary subcommands (`init`, `inspect`, `self-check`, `bench`, `res` [alias `resources`]/`cpu`/`mem`, `ui` [aliases `tui`, `gui`], `report-bug`/`feedback`) and global flags (`--version`, `--no-color`, `help`, `pbr`); pasted CLI command coverage check from Required tests item 5 showing `commands=20 missing=[]` and exiting 0; pasted zero-dash check from Required tests item 1 exiting 0 (`dashes_in_added=0`); pasted internal link and anchor check from Required tests item 2 exiting 0 (`broken=0`); and pasted `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending


## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`). No blocking open questions exist.
2. Scope declaration: `- Scope-Paths:` declares the three paths this plan changes (`docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`). If an out-of-scope edit proves necessary, make it and justify it at finalize (`--scope-reason <path>=<why>`); acknowledge any declared path left unmodified (`--scope-ack`).
3. Validation honesty: run every required validation command and paste the actual output into each `V-*` item. Never claim a check passed without pasting its output.
4. Commit discipline: commit through `aw commit wjsccu -- docs/functional_spec.md docs/hpc.md docs/research-use.md`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: the plan must reach `executed/` through `aw ipd finalize wjsccu`, never a hand-run `git mv`. When a runner (`aw oc run` or `aw agy run`) drives execution, the runner finalizes; otherwise the executor runs it. Finalize only once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
