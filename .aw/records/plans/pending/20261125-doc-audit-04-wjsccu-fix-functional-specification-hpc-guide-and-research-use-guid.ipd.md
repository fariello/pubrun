# IPD: Fix functional specification, HPC guide, and research-use guide inaccuracies

- Date: 2026-11-25
- Kind: child
- Concern: `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md` contain high-severity inaccuracies including an unrunnable HPC `PUBRUN_META_REF=meta.json` workflow, misattributed `system_memory`/`load_average`/`system_iowait_pct` metrics on `pubrun inspect`, removed `-f` short flag for `pubrun combined --force`, wrong `pubrun report`/`show`/`diff`/`methods` CLI specifications, and 10 omitted primary CLI subcommands.
- Scope: `docs/functional_spec.md`, `docs/hpc.md`, and `docs/research-use.md`.
- Scope-Paths: docs/functional_spec.md, docs/hpc.md, docs/research-use.md
- Item-Dependencies: none
- Status: approved
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
- Approval: 2026-11-26, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 approved (aw set): status set to approved
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

- [x] E-01 Fix all verified inaccuracies in `docs/hpc.md` (with no em or en dashes in added or edited lines):
  - **Parent-child hydration (`docs/hpc.md#Parent snapshots (meta_ref)`)**: Replace the unrunnable `pubrun meta --out meta.json` and `PUBRUN_META_REF=meta.json` workflow with a working shared-path example (`pubrun meta --out /shared/proj/meta.json` and `export PUBRUN_META_REF=/shared/proj/meta.json`) paired with configuring `[report].meta_ref_allowed_dirs = ["/shared/proj"]` (or `[report].allow_external_meta_ref = true`) in `.pubrun.toml`. Explain that relative `meta_ref` paths resolve against each child's run directory (`Path(manifest_path).parent`) and paths outside allowed directories are blocked by policy before file existence checks (`src/pubrun/report/utils.py::hydrate_manifest_with_report`, `src/pubrun/report/utils.py::_is_meta_ref_allowed`). Add `host` to the hydrated sections list (`src/pubrun/report/utils.py::HYDRABLE_SECTIONS`: `hardware`, `process`, `python`, `packages`, `environment`, `git`, `host`), clarify that `pubrun meta` writes 6 sections (`hardware`, `python`, `packages`, `git`, `environment`, `host` - not `process`; `src/pubrun/report/meta_snapshot.py::generate_meta_snapshot`), and list all hydrating callers: `pubrun show` (and hidden alias `report`), `pubrun res` (`resources`/`cpu`/`mem`), `pubrun methods` (including `--all`), `pubrun inspect`, `pubrun rerun --preflight`, `pubrun diff`, Python `pubrun.diff()`, and the TUI (`pubrun ui`/`tui`/`gui`).
  - **System metrics (`docs/hpc.md#Diagnosing a finished run`)**: Replace the claim starting `` `inspect` records, when available ``. Clarify that during a run, `pubrun` records `filesystem` (`src/pubrun/capture/filesystem.py::get_filesystem`) and, when `[capture.resources].depth != "off"` and `[capture.resources].system_metrics = true` (default), `resources.{system_memory, load_average, system_iowait_pct, io_counters}` (`src/pubrun/capture/resources.py::ResourceWatcher`) into `manifest.json`. After a run, `pubrun inspect` is read-only and evaluates recorded network filesystems, capture completeness, parent-snapshot checks, and optional `--preflight` checks; **`pubrun res`** displays `system_memory`, `load_average`, `system_iowait_pct` (node-wide, indicative only), and per-process `io_counters` (`src/pubrun/report/diagnostics.py::print_resources_report`); and `pubrun self-check` inspects live host filesystems, available memory, and load average (`src/pubrun/report/checks.py::live_findings`).
  - **File-I/O capture completeness (`docs/hpc.md#Capture-completeness`)**: Add `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` alongside `pubrun.open(...)` for libraries that do not use Python `open()`.
  - **Benchmarking on HPC (`docs/hpc.md#Running the benchmark suite on a cluster`)**: State that `pubrun bench` requires a source checkout (`git clone`; `benchmarks/harness.py` is not shipped in the pip wheel, `src/pubrun/__main__.py::_run_bench`). Clarify that `benchmarks/submit_bench.sh` queries `sinfo` and pins to a random idle Slurm node via `--nodelist` when idle nodes are available (falling back to unpinned scheduler placement when none are idle), whereas `submit_bench_pbs.sh`, `submit_bench_lsf.sh`, and `submit_bench_sge.sh` submit to the default queue and let the scheduler place the job. Document the Slurm login-node submit-and-wait flow (`--wait-timeout`, default about 1800s; `0` waits indefinitely) plus `--submit-file` for recovery or air-gapped compute nodes.
  - Depends on: none
  - Expected outcome: Every HPC command, hydration caller list, metric attribution, file-provenance note, and Slurm workflow in `docs/hpc.md` matches live code.
  - Execution state: performed

- [x] E-02 Fix verified inaccuracies in `docs/research-use.md` (with no em or en dashes in added or edited lines):
  - **Input-file capture nuance**: Qualify the opening paragraph and `Unversioned inputs` bullet so they distinguish automatic CLI-argument discovery from observed file-I/O provenance: bare `import pubrun` heuristically scans `sys.argv` for existing file paths (`invocation.inputs`, `src/pubrun/capture/invocation.py::get_invocation`), whereas observed file-I/O provenance and optional content digests for datasets read or written through libraries such as pandas, NumPy, or h5py use `pubrun.open(...)` or `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` (referencing `examples/12_external_file_provenance.py`).
  - **Example script range (`docs/research-use.md#Public example workflow`)**: Update `00_auto_start.py` through `11_cli_report.py` to `00_auto_start.py` through `12_external_file_provenance.py` (all 13 numbered scripts). Leave the Zenodo DOI line in `docs/research-use.md#How to cite pubrun` unchanged so `tests/test_cli.py::TestCitationConsistency` continues to pass.
  - Depends on: none
  - Expected outcome: `docs/research-use.md` accurately distinguishes automatic CLI-arg input capture from explicit file-I/O provenance, lists all 13 numbered examples, and preserves the Zenodo DOI line.
  - Execution state: performed

### Task group 2: Fix `docs/functional_spec.md`

- [x] E-03 Fix the header and Sections 3, 5, 6, 7, 9, and 10 of `docs/functional_spec.md` (with no em or en dashes in added or edited lines):
  - **Header**: Change `> Status: v1.0.0` to `> Status: Current (schema v1.0)`.
  - **Section 3.3 (`Auto-Start Behavior`)**: Update the CLI self-suppression bullet to match `src/pubrun/core.py::_is_pubrun_cli_invocation`: suppresses auto-start for `pubrun`, `pubrun.exe`, `pbr`, and `pbr.exe` (`sys.argv[0]` basename), an already-imported `pubrun.__main__`, a `__main__.__spec__.name` of `"pubrun"` or `"pubrun.__main__"`, and `python -m pubrun` via `runpy` stack frames (`mod_name == "pubrun"` or starting with `"pubrun."`).
  - **Section 3.5, Section 6, and Section 10.2 (`profile` deprecation)**: Mark `[core].profile` and `PUBRUN_PROFILE` in Section 6 (and the Section 10.3 `PUBRUN_PROFILE` row) as deprecated and inert: still accepted for compatibility, records a `profile_deprecated` notice in `config.notices` when set to any value other than `"default"` (`src/pubrun/config.py::profile_deprecation_notice`), and never controls capture depth. Replace `@pubrun.audit_run(profile="deep")` in Section 3.5 and `pubrun.start(profile="deep")` in Section 10.2 with active overrides (such as `@pubrun.audit_run(output_dir="./audit_runs")` and `pubrun.start(output_dir="./runs", console={"capture_mode": "standard"})`).
  - **Sections 5.1 and 5.3 (`Capture Categories`)**: In Section 5.1, add rows for `Filesystem` (`filesystem`, no config section, always captured), `Data files` (`data_files`, `[capture.file_io]`, levels `none`, `name`, `stat`, `realpath`, `hash`), `Import provenance` (`pubrun_imports`, `[imports]`, always captured), and `Profiling` (no top-level manifest key; writes `profile-<phase>.prof` files and emits `profile_saved` events, `[capture.profiling]`, `enabled`, `backend`). Add `"off"` to the Modes / Depth column for `packages` (`src/pubrun/capture/packages.py`) and `environment` (`src/pubrun/capture/environment.py`). In Section 5.3 (`Deferred (Future Work)`), remove `Artifacts` and note that file tracking is implemented via `data_files`, `pubrun.artifact()`, `pubrun.open()`, `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()`.
  - **Sections 7.1 and 9.1 (`Events` and `Capture State`)**: In Section 7.1, add the remaining emitted event types verified in `src/pubrun/`: `resource_sample` (`src/pubrun/capture/resources.py::ResourceWatcher._update_metrics`), `profile_saved` (`src/pubrun/core.py::phase._emit_profile_saved`), `input_dataset`, `output_artifact`, and `mixed_dataset` (`src/pubrun/capture/file_io.py::_event_type_for_role` and `ProvenanceFileProxy`), and `warning` (`src/pubrun/tracker.py` mid-run storage directory migration). In Section 9.1, add `timeout` and `pending` to the `capture_state.status` enum (`schemas/manifest.schema.json` `$defs.status_value`).
  - **Sections 10.2, 10.3, and 10.4 (`Configuration System`)**: Preserve the existing `PUBRUN_RUN_MODE_OVERRIDE` text in Section 10.2 and row in Section 10.3 verbatim (already landed by executed plan `87qr8h`, which closed backlog `aqb2bu`). Add `NO_COLOR` (disables ANSI color output in CLI/report/diff/status renderers; read by CLI and report modules, not `resolve_config()`) and `PUBRUN_DEBUG` (enables `[DEBUG]` diagnostic output in `src/pubrun/report/output.py::debug_enabled`; not read by `resolve_config()`) to Section 10.3. In Section 10.4, add report/hydration policy (`[report]`: `allow_external_meta_ref`, `meta_ref_allowed_dirs`) and mark `[logging].write_summary` as reserved and not yet implemented (`src/pubrun/resources/default.toml`).
  - Depends on: none
  - Expected outcome: The header and Sections 3, 5, 6, 7, 9, and 10 of `docs/functional_spec.md` match live code and schema, with existing `PUBRUN_RUN_MODE_OVERRIDE` rows preserved verbatim.
  - Execution state: performed

- [x] E-05 Fix Sections 12, 14, 16, and 18 of `docs/functional_spec.md` (with no em or en dashes in added or edited lines; leave Section 17 `Ghost Mode` untouched):
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
  - Execution state: performed

- [x] E-04 Fix existing Section 11 CLI subsections (`11.2`-`11.4`, `11.6`-`11.9`, `11.11`-`11.12`, and `11.14`) of `docs/functional_spec.md` (with no em or en dashes in added or edited lines):
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
  - Execution state: performed

- [x] E-06 Add subsections to Section 11 of `docs/functional_spec.md` for all 10 omitted primary CLI subcommands and global CLI options (with no em or en dashes in added or edited lines):
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
  - Execution state: performed

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

- [x] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/hpc.md` confirming the shared-path `PUBRUN_META_REF` + `[report].meta_ref_allowed_dirs` example, `host` + 6-section `pubrun meta` note + full hydrating caller list (including `res`/`cpu`/`mem`), corrected `inspect` vs `res` vs `self-check` attribution, `register_input()`/`register_output()`/`register_file()`, and `pubrun bench` source-checkout + Slurm `sinfo` idle-node + `--wait-timeout`/`--submit-file` mechanics; pasted `grep -nE 'PUBRUN_META_REF=meta\.json|`inspect` records' docs/hpc.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); plus pasted zero-dash check from Required tests item 1 exiting 0.
  - Observed evidence:
    ~~~~diff
    diff --git a/docs/hpc.md b/docs/hpc.md
    index 7f87550..ca66633 100644
    --- a/docs/hpc.md
    +++ b/docs/hpc.md
    @@ -45,13 +45,13 @@ pubrun inspect <run> -v           # full detail + suggestions
     pubrun inspect <run> --json       # machine-readable findings
     ```

    -`inspect` records, when available (see [Configuration](configuration.md) →
    -`[capture.resources].system_metrics`, on by default):
    +During a run, `pubrun` records the `filesystem` section (backing filesystem types) and, when `[capture.resources].depth != "off"` and `[capture.resources].system_metrics = true` (the default; see [Configuration](configuration.md)), records `resources.system_memory`, `resources.load_average`, `resources.system_iowait_pct`, and `resources.io_counters` into `manifest.json`.

    -- the **filesystem type** backing the run (flagging network filesystems),
    -- system **available memory** and **load average** over the run,
    -- a **node-wide iowait** hint (`system_iowait_pct`), *indicative only*; it reflects the
    -  whole node, not just your run (Linux `/proc/stat` iowait is a system-wide counter).
    +After a run:
    +
    +- **`pubrun inspect`** is read-only and evaluates recorded network filesystems, capture completeness, parent-snapshot checks, and optional `--preflight` checks.
    +- **`pubrun res`** (alias `resources`) displays the recorded `system_memory`, `load_average`, `system_iowait_pct` (a node-wide Linux `/proc/stat` counter, indicative only; it reflects the whole node rather than only your run), and per-process `io_counters` alongside memory and CPU charts.
    +- **`pubrun self-check`** inspects the live host for network filesystems, available memory, and load average.
    @@ -89,11 +89,27 @@ different-host banner, so prefer `--fail-on mismatch` for cross-node checks.

     ### Parent snapshots (`meta_ref`)

    -In the parent and child workflow, a login-node job writes `pubrun meta --out meta.json` and
    -array tasks set `PUBRUN_META_REF=meta.json` and switch off heavy capture. At report time,
    -`inspect`, `show`, and the TUI fill the child's missing sections (hardware, process, python,
    -packages, environment, git) from the parent snapshot, in memory only. They report those
    -sections as `inherited`, which is weaker evidence than what the child observed itself.
    +In the parent-child workflow, a setup step writes one shared parent snapshot to a cluster directory, configures the hydration allowlist, and points child tasks at that shared path while disabling heavy per-child capture:
    +
    +```bash
    +# 1. Parent snapshot on shared storage (default depth: --deep)
    +pubrun meta --out /shared/proj/meta.json
    +
    +# 2. Child tasks reference the shared path
    +export PUBRUN_META_REF=/shared/proj/meta.json
    +python train.py
    +```
    +
    +Add the shared directory to `[report].meta_ref_allowed_dirs` in `.pubrun.toml` (or set `[report].allow_external_meta_ref = true` to permit any external `.json` path):
    +
    +```toml
    +[report]
    +meta_ref_allowed_dirs = ["/shared/proj"]
    +```
    +
    +Relative `meta_ref` paths resolve against each child's run directory (`Path(manifest_path).parent`), not the current working directory. Before checking whether the file exists, `pubrun` checks the `.json` extension and directory policy; any path outside the run directory and configured allowlist is blocked by policy.
    +
    +At read time, `pubrun` fills missing or incomplete hydrable sections (`hardware`, `process`, `python`, `packages`, `environment`, `git`, `host`) from the parent snapshot in memory only, reporting inherited sections as weaker evidence than direct child capture. Note that `pubrun meta` writes 6 sections (`hardware`, `python`, `packages`, `git`, `environment`, `host`); it does not capture `process`. All hydrating callers use this same hydration path: `pubrun show` (and hidden alias `report`), `pubrun res` (`resources`, `cpu`, `mem`), `pubrun methods` (including `--all`), `pubrun inspect`, `pubrun rerun --preflight`, `pubrun diff`, Python `pubrun.diff()`, and the TUI (`pubrun ui`, `tui`, `gui`).
    @@ -117,8 +133,10 @@ can capture more:
    -- file-I/O provenance: pubrun does **not** patch `open()` globally, so record inputs/outputs
    -  by calling `pubrun.open(...)` instead of `open(...)`.
    +- file-I/O provenance: pubrun does **not** patch `open()` globally, so record inputs and
    +  outputs by calling `pubrun.open(...)` instead of `open(...)`, or use
    +  `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` for
    +  libraries (such as pandas, NumPy, or h5py) that do not use Python `open()`.
    @@ -128,16 +146,26 @@ The benchmark harness and scheduler submission scripts live under `benchmarks/`
    +`pubrun bench` requires a source checkout (`git clone`), because `benchmarks/harness.py` is
    +not shipped in the pip wheel. It auto-detects the batch scheduler (**Slurm, PBS/Torque,
    +LSF, or SGE/Grid Engine**, precedence Slurm > PBS > LSF > SGE) from environment variables
    +and submit tools on `PATH`, and **offers** to submit to a compute node (never without
    +confirmation). Because PBS and SGE both use `qsub`, an ambiguous environment is reported;
    +pick one with `--scheduler pbs|sge`.
    +
    +Scheduler placement differs by script: `benchmarks/submit_bench.sh` queries `sinfo` and
    +pins the Slurm job to a random idle node via `--nodelist` when idle nodes are available
    +(falling back to unpinned scheduler placement when none are idle), whereas
    +`submit_bench_pbs.sh`, `submit_bench_lsf.sh`, and `submit_bench_sge.sh` submit to the
    +default queue and let the scheduler place the job. Treat all submit scripts as **starting
    +points** and set your site's account, queue, and walltime (only the Slurm path is exercised
    +in CI).
    +
    +On a Slurm login node, `pubrun bench` runs a submit-and-wait flow that polls until the
    +compute-node job completes or `--wait-timeout` expires (default about 1800s; `0` waits
    +indefinitely). If the wait times out, or if you run on an air-gapped compute node (no
    +network or no `gh`), finish on the login node with
    +`pubrun bench --submit-file <result>.redacted.json`.
    ~~~~
    Grep check: `grep -nE 'PUBRUN_META_REF=meta\.json|`inspect` records' docs/hpc.md; echo "exit=$?"` -> `exit=1`.
    Zero-dash check: `dashes_in_added=0`, `exit=0`.
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/research-use.md` confirming qualified bare-import input capture (`sys.argv` vs `pubrun.open()`/`register_*()`, citing `examples/12_external_file_provenance.py`) and `00_auto_start.py` through `12_external_file_provenance.py`; pasted `grep -n '11_cli_report\.py' docs/research-use.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); pasted `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov` passing; plus pasted zero-dash check from Required tests item 1 exiting 0.
  - Observed evidence:
    ```diff
    diff --git a/docs/research-use.md b/docs/research-use.md
    index ec590af..cb2daac 100644
    --- a/docs/research-use.md
    +++ b/docs/research-use.md
    @@ -2,12 +2,12 @@

     # pubrun for provenance and reproducibility in scientific and ML work

    -**When a result has to be defensible, "the run finished" is not the same as "the run is trustworthy."** In model development, drug discovery, genomics, and any analysis whose methodology must hold up later, the questions that matter are: exactly which code, inputs, dependencies, and environment produced this checkpoint or figure, and can you reproduce it or explain why two runs differ. pubrun answers those by capturing the full run context automatically, with no code change beyond `import pubrun`, so provenance is not an afterthought you reconstruct from memory months later.
    +**When a result has to be defensible, "the run finished" is not the same as "the run is trustworthy."** In model development, drug discovery, genomics, and any analysis whose methodology must hold up later, the questions that matter are: exactly which code, inputs, dependencies, and environment produced this checkpoint or figure, and can you reproduce it or explain why two runs differ. With bare `import pubrun`, pubrun captures the code state, dependencies, runtime environment, and existing file paths discovered heuristically from `sys.argv` (`invocation.inputs`) automatically. When scripts read or write datasets through libraries such as pandas, NumPy, or h5py (or need observed file-I/O provenance and optional content digests), record them with `pubrun.open(...)` or `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` (see `examples/12_external_file_provenance.py`).

     Why this is not optional in high-stakes work:

     - **Silent environment drift.** A dependency or driver changes and results shift with no record of what moved. pubrun captures the dependency graph and environment for every run, so a run-to-run `diff` shows exactly what changed.
    -- **Unversioned inputs.** "Which data file produced this?" is unanswerable after the fact unless it was recorded at run time. pubrun records the invocation, inputs, and code state as the run happens.
    +- **Unversioned inputs.** "Which data file produced this?" is unanswerable after the fact unless it was recorded at run time. Bare `import pubrun` records the invocation, code state, and CLI-argument file paths (`invocation.inputs`) automatically; adding `pubrun.open(...)` or `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()` records observed file-I/O provenance and optional content digests for library-loaded datasets (see `examples/12_external_file_provenance.py`).
     - **Confidently-wrong outputs.** A run that completes can still be untrustworthy. pubrun records exit status, logs, and resource usage alongside the inputs, so a result is traceable back to the conditions that produced it.
    @@ -42,7 +42,8 @@ demonstrates the full round trip:

     It is exercised by `tests/test_example_minimal_research_workflow.py`, so it stays runnable as
     the code evolves. The `examples/` directory also holds focused single-feature scripts
    -(`00_auto_start.py` through `11_cli_report.py`) plus a `verify_all.py` harness.
    +(`00_auto_start.py` through `12_external_file_provenance.py`, all 13 numbered scripts) plus a
    +`verify_all.py` harness.
    ```
    Grep check: `grep -n '11_cli_report\.py' docs/research-use.md; echo "exit=$?"` -> `exit=1`.
    Citation test: `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov` -> `.... [100%] / 4 passed in 1.20s`, `exit=0`.
    Zero-dash check: `dashes_in_added=0`, `exit=0`.
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for header and Sections 3, 5, 6, 7, 9, and 10 confirming `Status: Current (schema v1.0)`, `_is_pubrun_cli_invocation()` (`pbr` and `python -m pubrun`), Section 5.1/5.3 categories and `"off"` modes, deprecated `[core].profile`/`PUBRUN_PROFILE` with active replacements in Sections 3.5 and 10.2, Section 7.1 events (`resource_sample`, `profile_saved`, `input_dataset`, `output_artifact`, `mixed_dataset`, `warning`), Section 9.1 `timeout`/`pending`, preserved `PUBRUN_RUN_MODE_OVERRIDE` rows, added `NO_COLOR`/`PUBRUN_DEBUG`, `[report]`, and reserved `[logging].write_summary`; pasted `grep -nE 'Status: v1\.0\.0|profile="deep"' docs/functional_spec.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`).
  - Observed evidence:
    ```diff
    @@ -2,7 +2,7 @@
    -> Status: v1.0.0
    +> Status: Current (schema v1.0)
    @@ -81,7 +81,7 @@
    -- The process is running the `pubrun` CLI itself (detected by checking `sys.argv[0]`).
    +- The process is running the `pubrun` CLI itself (`src/pubrun/core.py::_is_pubrun_cli_invocation`): `sys.argv[0]` basename is `pubrun`, `pubrun.exe`, `pbr`, or `pbr.exe`; `pubrun.__main__` is already imported in `sys.modules`; `__main__.__spec__.name` is `"pubrun"` or `"pubrun.__main__"`; or `python -m pubrun` is detected via `runpy` stack frames (`mod_name == "pubrun"` or starting with `"pubrun."`).
    @@ -144,7 +144,7 @@
    -@pubrun.audit_run(profile="deep")     # Decorator
    +@pubrun.audit_run(output_dir="./audit_runs")     # Decorator
    @@ -212,16 +212,20 @@
    -| Packages | `packages` | `[capture.packages]` | `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment` |
    -| Environment | `environment` | `[capture.environment]` | `allowlist`, `filtered`, `full` |
    +| Packages | `packages` | `[capture.packages]` | `off`, `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment` |
    +| Environment | `environment` | `[capture.environment]` | `off`, `allowlist`, `filtered`, `full` |
    +| Filesystem | `filesystem` | None | Always captured |
    +| Data files | `data_files` | `[capture.file_io]` | `none`, `name`, `stat`, `realpath`, `hash` |
    +| Import provenance | `pubrun_imports` | `[imports]` | Always captured |
    +| Profiling | None (writes `profile-<phase>.prof` files and emits `profile_saved` events) | `[capture.profiling]` | `enabled`, `backend` |
    @@ -231,10 +235,11 @@
    -- **Extensions** — Framework plugin model for custom capture engines.
    -- **Artifacts** — User-registered output file tracking.
    +- **Extensions**: Framework plugin model for custom capture engines.
    +File tracking is implemented via `data_files`, `pubrun.artifact()`, `pubrun.open()`, `pubrun.register_input()`, `pubrun.register_output()`, and `pubrun.register_file()`.
    @@ -242,20 +247,16 @@
    +`[core].profile` and `PUBRUN_PROFILE` are **deprecated and inert**. Accepted legacy values (`minimal`, `default`, `deep`) remain valid for backward compatibility so existing configurations and scripts do not break, but `profile` never controls capture depth.
    +When `[core].profile` (or `PUBRUN_PROFILE`) is set to any value other than `"default"`, `pubrun` records a `profile_deprecated` notice in `config.notices` (`src/pubrun/config.py::profile_deprecation_notice`) without raising or disrupting the host script.
    @@ -265,9 +266,13 @@
    +- `resource_sample`: Emitted by `ResourceWatcher` (`src/pubrun/capture/resources.py::ResourceWatcher._update_metrics`) on each resource sample with `rss_bytes`, `cpu_percent`, and (when `scope = "tree"`) `tree_rss_bytes` and `tree_cpu_percent`.
    +- `profile_saved`: Emitted when a profiled `pubrun.phase()` saves a `profile-<phase>.prof` file (`src/pubrun/core.py::phase._emit_profile_saved`).
    +- `input_dataset`, `output_artifact`, and `mixed_dataset`: Emitted by `pubrun.open()` (`ProvenanceFileProxy`) and `pubrun.register_file()`, `pubrun.register_input()`, and `pubrun.register_output()` according to file role (`src/pubrun/capture/file_io.py::_event_type_for_role`).
    +- `warning`: Emitted by `Run` (`src/pubrun/tracker.py`) on mid-run storage directory migration when a re-entrant `start(output_dir=...)` moves the run directory.
    @@ -318,11 +323,13 @@
    +- `timeout`: Capture exceeded its configured time budget.
    +- `pending`: Asynchronous capture started and not yet finalized (for example, background hardware inspection in a startup manifest).
    @@ -372,8 +379,8 @@
    -| 5 | Environment variables | `PUBRUN_PROFILE`, `PUBRUN_META_REF` |
    -| 6 (highest) | API overrides | `pubrun.start(profile="deep")` |
    +| 5 | Environment variables | `PUBRUN_PROFILE` (deprecated, inert), `PUBRUN_META_REF` |
    +| 6 (highest) | API overrides | `pubrun.start(output_dir="./runs", console={"capture_mode": "standard"})` |
    @@ -387,18 +394,20 @@
    -| `PUBRUN_PROFILE` | Overrides `[core].profile`. Consumed in `resolve_config()` between local config and API overrides. |
    +| `PUBRUN_PROFILE` | Deprecated and inert. Sets `[core].profile` in `resolve_config()` between local config and API overrides, records a `profile_deprecated` notice in `config.notices` when set to any value other than `"default"`, and never controls capture depth. |
    +| `NO_COLOR` | Disables ANSI color output in CLI, report, diff, and status renderers when set to a non-empty value. Read by CLI and report modules (not `resolve_config()`). |
    +| `PUBRUN_DEBUG` | Enables `[DEBUG]` diagnostic output in CLI and report output helpers when set to a non-empty value (`src/pubrun/report/output.py::debug_enabled`). Not read by `resolve_config()`. |
    @@ -408,7 +417,8 @@
    +- Report and hydration policy (`[report]`: `allow_external_meta_ref`, `meta_ref_allowed_dirs`)
    +- Logging (`[logging]`: `write_summary` is reserved and not yet implemented)
    ```
    Preservation check: `pubrun_run_mode_override_unchanged= True count=5`.
    Grep check: `grep -nE 'Status: v1\.0\.0|profile="deep"' docs/functional_spec.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for Section 11 intro and subsections `11.2`-`11.4`, `11.6`-`11.9`, `11.11`-`11.12`, and `11.14` confirming `pbr` alias, hidden/deprecated `--show-config`, corrected `--info` and `--run-tests`, `show` + hidden `report` + `show [run|default] config`, `methods` default `markdown` + `--all`, `rerun --preflight`/`--strict`/`--fail-on`/`--json`, `diff` default `--standard` + `--table`, `status --utc`/filters + `clean` filters, and `combined --force` (no `-f`); pasted `grep -nE 'report \[RUN_DIR|--basic` \(default\)|\[-f\|--force\]' docs/functional_spec.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`).
  - Observed evidence:
    ```diff
    @@ -426,7 +436,7 @@
    -The CLI is accessible via `pubrun <command>` or `python -m pubrun <command>`.
    +The CLI is accessible via `pubrun <command>`, `pbr <command>` (console script alias), or `python -m pubrun <command>`.
    @@ -440,15 +450,15 @@
    -Prints the complete default configuration to the terminal.
    +Hidden (`argparse.SUPPRESS`) and deprecated diagnostic flag. At runtime, it emits a deprecation warning to stderr pointing to `pubrun show default config`, while continuing to print the raw `default.toml` text to stdout.
    -Displays system capabilities, pubrun version, and environment details.
    +Displays active import-mode flags (plus `PUBRUN_IMPORT_MODE` when set) and JSON for `invocation` and `hardware` (`src/pubrun/__main__.py::_show_info`). It does not print the `pubrun` version (use `--version`) or general environment variables.
    -Executes the built-in pytest test suite to verify the installation.
    +Runs an embedded end-to-end mock script in a temporary directory to verify runtime capture and manifest generation (`src/pubrun/__main__.py::_run_tests`). When executed inside a source checkout (`tests/` and `tox.ini` present), it also runs `pytest tests/ -q`.
    @@ -462,57 +472,71 @@
    -### 11.6 Run Diagnostics (`report`)
    +### 11.6 Run Diagnostics (`show`)
    +pubrun show [RUN_DIR] [logs|env|packages] [--basic|--standard|--deep] [--utc] [FILTERS]
    +pubrun show config [--all]
    +pubrun show default config
    +pubrun show run config [RUN_ID] [--all]
    +- `report` remains a hidden compatibility alias for `show`, omitting `--all` and the optional third positional `RUN_ID` in `show run config <id>`.
    +pubrun methods [RUN_DIR] [--format markdown|latex] [--all] [FILTERS]
    +- CLI `--format` defaults to `markdown`. The `[methods].format` configuration key controls only the auto-generated `methods.md` or `methods.tex` file written at run finalization (`src/pubrun/writer.py::ArtifactWriter.write_artifacts`).
    +pubrun rerun [RUN_DIR] [--preflight] [--strict] [--fail-on warn|mismatch|unknown] [--json] [FILTERS]
    +pubrun diff [RUN_DIR_A] [RUN_DIR_B] [OPTIONS]
    +- `--basic` / `--standard` (default) / `--deep`: Controls filtering via `[diff].ignore_*` lists.
    +- `--table`: Render a compact aligned table instead of the default git-style `+`/`-`/`~` lines.
    @@ -529,25 +553,28 @@
    +pubrun status [RUN_ID] [--dir PATH] [-v|--verbose] [--utc] [FILTERS]
    +pubrun clean [--dir PATH] [-y|--yes] [--dry-run] [FILTERS]
    @@ -571,15 +598,109 @@
    -pubrun combined [RUN_IDS ...] [--dir PATH] [--output FILE] [-y|--yes] [-f|--force]
    +pubrun combined [RUN_IDS ...] [--dir PATH] [--output FILE] [-y|--yes] [--force] [FILTERS]
    +- Size thresholds: warns at 250 MB (skipped via `--yes`), aborts at 500 MB (overridden via `--force`; `-f` is `--filter QUERY`, not force).
    ```
    Grep check: `grep -nE 'report \[RUN_DIR|--basic` \(default\)|\[-f\|--force\]' docs/functional_spec.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for Sections 12, 14, 16, and 18 (and confirming zero diff lines in Section 17 `Ghost Mode`) verifying `<output_dir>/pubrun-.../` and Section 12.3 optional files, Section 14.1 (`annotate(message=None, ...)`, seven-function `on_inactive_annotate`, `tracked_run()`/`audit_run()` exit-outcome rules, `diff(..., ignores=None)`, `print()` skip conditions, `register_file(..., role="input_output")`), Section 16 (Win32 `ctypes` + `wmic` fallback, `/proc/<pid>/task/<tid>/children`, Linux-only tree CPU, `poll_timeout`, `system_metrics`, `peak_tree_cpu_percent`, `system_memory`, `load_average`, `system_iowait_pct`, `io_counters`, `capture_state`), and Section 18 (shared-path `PUBRUN_META_REF` + `[report].meta_ref_allowed_dirs`, `host`, 6-section `pubrun meta`, full hydrating caller list including `res`/`cpu`/`mem`); pasted `grep -nE '<base_dir>/runs/pubrun-|PUBRUN_META_REF=meta\.json' docs/functional_spec.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`).
  - Observed evidence:
    ```diff
    @@ -587,9 +708,11 @@
    -<base_dir>/runs/pubrun-<script>-<timestamp>-<pid>-<run_id>/
    +<output_dir>/pubrun-<script>-<timestamp>-<pid>-<run_id>/
    +`<output_dir>` is `[core].output_dir` (defaulting to `./runs` when empty, per `src/pubrun/tracker.py::Run.__init__`).
    @@ -605,7 +728,7 @@
    -Optional: `stdout.log`, `stderr.log`, `events.jsonl`, `methods.md`/`methods.tex`.
    +Optional: `stdout.log`, `stderr.log`, `events.jsonl`, `methods.md`/`methods.tex`, `profile-<phase>.prof` (when `[capture.profiling].enabled = true`), files written by `pubrun.report()` and `pubrun.artifact()`, and transient `.pubrun.lock` during active execution.
    @@ -631,21 +754,21 @@
    +| `annotate(message=None, **kwargs)` | Returns `None` | Emits an `annotation` event (`message` is optional). When no run is active, `[events].on_inactive_annotate` (`ignore` default, `warn`, or `error`) governs behavior across all seven inactive-guarded functions: `annotate()`, `phase()`, `report()`, `artifact()`, `register_file()`, `register_input()`, and `register_output()` (`src/pubrun/core.py::_handle_inactive`). |
    +| `tracked_run(**overrides)` | Context manager | Wraps `start()`/`stop()`. Exit outcome (`_classify_exit_outcome`, `_stop_for_exit`): `KeyboardInterrupt` sets `"interrupted"`, `SystemExit(0)` or `SystemExit(None)` sets `"completed"`, and other exceptions or non-zero `SystemExit` set `"failed"`; `SystemExit` also records its exit code on signal capture. |
    +| `audit_run(func=None, **overrides)` | Decorator | Wraps a function in `start()`/`stop()` and preserves return value. Applies the same exit-outcome rules as `tracked_run()` (`KeyboardInterrupt` -> `"interrupted"`, `SystemExit(0)` or `SystemExit(None)` -> `"completed"`, other exceptions or non-zero `SystemExit` -> `"failed"`, recording `SystemExit` exit code on signal capture), then re-raises. |
    +| `diff(run_dir_a, run_dir_b, ignores=None)` | Returns `dict` | Compares two run directories after hydrating both manifests (`src/pubrun/core.py::diff`). `ignores` is optional and defaults to `[diff].ignore_standard` (or legacy `[diff].ignore` when `ignore_standard` is absent). Returns `{"added": ..., "removed": ..., "modified": ..., "same": ...}`. |
    +| `print(*args, **kwargs)` | Returns `None` | Calls the builtin `print()` and appends the text to `stdout.log`, skipping direct append when `file=` is not `sys.stdout`, inside `pubrun.paused()`, or when the run's active console tee on `sys.stdout` already records stdout (`src/pubrun/core.py::_should_log_pubrun_print`). |
    +| `register_file(path, role="input", *, label, digest, digest_algorithm, level, verify_digest, defer, metadata)` | Returns `dict \| None` | Records an external file read or written by other code (for example a library) into `data_files.inputs`, `outputs`, or `mixed` without wrapping its I/O. Accepts `role="input" \| "output" \| "input_output"` (`"input_output"` records into `data_files.mixed`). A caller digest is recorded as asserted unless `verify_digest=True`. Outputs may be registered before they exist and are completed at finalization. Subject to `[events].on_inactive_annotate` when no run is active; returns `None` with no active run or at level `none`. |
    @@ -710,21 +833,30 @@
    +- `scope` (default `"process"`): `"process"` monitors only the main process; `"tree"` sums RSS across the entire process tree on Linux and macOS (Windows falls back to process) and sums tree CPU on Linux only.
    +- `poll_timeout` (default `3`s): Per-poll timeout in seconds for macOS/Windows sampling subprocesses (`ps` and `wmic`).
    +- `system_metrics` (default `true`): When enabled (and `[capture.resources].depth != "off"`), also samples host `system_memory`, `load_average`, Linux node-wide `system_iowait_pct`, and Linux per-process `io_counters`.
    +| Linux | `/proc/self/statm` | `/proc/<pid>/task/<tid>/children` recursive walk across all threads (`_get_linux_child_pids`) |
    +| Windows | Win32 `K32GetProcessMemoryInfo` / `psapi.GetProcessMemoryInfo` via `ctypes`, with `wmic` subprocess fallback (`_get_rss_windows`) | Not yet implemented (falls back to process) |
    +Tree CPU (`_poll_tree_cpu`) is Linux-only and computes percentage utilization from `/proc/<pid>/stat` cumulative jiffy deltas across the process tree.
    +The `resources` manifest section contains: `scope`, `peak_rss_bytes`, `end_rss_bytes`, `peak_cpu_percent`, and `capture_state`. When `scope = "tree"`, it also includes `peak_tree_rss_bytes`, `end_tree_rss_bytes`, and `peak_tree_cpu_percent` (Linux-only, `% of one core`, `null` where unmeasured). When `system_metrics = true` and available on the host, it also includes: `system_memory`, `load_average`, `system_iowait_pct`, `io_counters`.
    @@ -769,15 +901,16 @@
    +1. **Parent**: `pubrun meta --out /shared/proj/meta.json --deep`
    +2. **Allowlist configuration**: add `[report].meta_ref_allowed_dirs = ["/shared/proj"]` (or `[report].allow_external_meta_ref = true`) to `.pubrun.toml` (see Section 18.5).
    +3. **Children**: `export PUBRUN_META_REF=/shared/proj/meta.json && python script.py`
    +When `meta_ref` is set and any hydrating caller runs (`pubrun show` and hidden alias `report`, `pubrun res`/`resources`/`cpu`/`mem`, `pubrun methods` including `--all`, `pubrun inspect`, `pubrun rerun --preflight`, `pubrun diff`, Python `pubrun.diff()`, and the TUI `pubrun ui`/`tui`/`gui`):
    +- For each of the 7 sections in `HYDRABLE_SECTIONS` (`[hardware, process, python, packages, environment, git, host]`): if the child section is missing or has `capture_state.status` in `[suppressed, off, unavailable, unknown, partial]`, it is replaced in memory with the parent section when present. Note that `pubrun meta` captures 6 sections (`hardware`, `python`, `packages`, `git`, `environment`, `host`); it does not capture `process`.
    ```
    Section 17 check: `section_17_unchanged= True`.
    Grep check: `grep -nE '<base_dir>/runs/pubrun-|PUBRUN_META_REF=meta\.json' docs/functional_spec.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-06 validates E-06
  - Required evidence: Pasted `git diff -- docs/functional_spec.md` hunks for the added Section 11 subsections covering all 10 omitted primary subcommands (`init`, `inspect`, `self-check`, `bench`, `res` [alias `resources`]/`cpu`/`mem`, `ui` [aliases `tui`, `gui`], `report-bug`/`feedback`) and global flags (`--version`, `--no-color`, `help`, `pbr`); pasted CLI command coverage check from Required tests item 5 showing `commands=20 missing=[]` and exiting 0; pasted zero-dash check from Required tests item 1 exiting 0 (`dashes_in_added=0`); pasted internal link and anchor check from Required tests item 2 exiting 0 (`broken=0`); and pasted `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
    ```diff
    +### 11.15 Project Initialization (`init`)
    +pubrun init [DEST]
    +### 11.16 Post-Hoc Reproducibility Assessment (`inspect`)
    +pubrun inspect [RUN_DIR] [-v|--show-suggestions] [--preflight] [--json] [--strict] [--fail-on warn|mismatch|unknown] [FILTERS]
    +### 11.17 Live Machine Health Check (`self-check`)
    +pubrun self-check [-v|--show-suggestions] [--json] [--strict] [-q|--quiet]
    +### 11.18 Overhead Benchmarks (`bench`)
    +pubrun bench [--quick|--full|--rigorous] [--no-baseline] [--iterations N] [--passes N] [--local|--submit] [--scheduler auto|slurm|pbs|lsf|sge|local] [-y|--yes] [--unredacted] [--json] [--contribute|--no-contribute] [--prepare-submission] [--submit-file FILE] [--wait-timeout SECONDS] [--no-submit] [--gh-repo OWNER/NAME]
    +### 11.19 Resource Utilization Charts (`res`, `cpu`, `mem`)
    +pubrun res [RUN_DIR] [--average] [-l|--last WINDOW] [-w|--width COLS] [FILTERS] (`res` alias `resources`), `pubrun cpu`, `pubrun mem`
    +### 11.20 Interactive Dashboard (`ui`)
    +pubrun ui [--dir PATH] (aliases `tui`, `gui`)
    +### 11.21 Issue Reporting and Feedback (`report-bug`, `feedback`)
    +pubrun report-bug / pubrun feedback
    +### 11.22 Global CLI Options and Aliases
    +`--version`, `--no-color`, `help` translation, run-selector reordering, `pbr` alias
    ```
    CLI command coverage check: `commands=20 missing=[]`, `exit=0`.
    Zero-dash check: `dashes_in_added=0`, `exit=0`.
    Internal link and anchor check: `broken=0`, `exit=0`.
    Path leak sanitizer: `python3 scripts/sanitize_paths.py --check --all` -> `exit=0`.
  - Result: pass


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
