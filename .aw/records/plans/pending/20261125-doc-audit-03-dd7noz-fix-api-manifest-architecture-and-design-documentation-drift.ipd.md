# IPD: Fix API, manifest, architecture, and design documentation drift

- Date: 2026-11-25
- Kind: child
- Concern: `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, and `docs/design/` contain high-impact contract errors including a phantom top-level `profiling` manifest section, a mismatched `redacted_value` hashed format, `python.virtual_env` documented as a path, deprecated `profile=` API examples, a false `pubrun inspect --json` vs `assess_run()` claim, and stale module trees and Phase-0 design status.
- Scope: `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, `docs/design/file-io-provenance-evaluation.md`, and `docs/design/tomli-dependency-decision.md`.
- Scope-Paths: docs/api.md, docs/manifest.md, docs/architecture.md, docs/design/file-io-provenance-evaluation.md, docs/design/tomli-dependency-decision.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Fix phantom manifest sections, deprecated profile examples, API behavioral errors, architecture layout, and design banners
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 3
- Highest E allocated: 08
- Author: Antigravity
- Id: dd7noz
- Approval: 2026-11-26, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Claude Opus 5.5, OpenCode): APPROVE WITH REVISIONS APPLIED; PR-001..PR-012 all FIXED; review record `.aw/records/reviews/20261125-doc-audit-03-dd7noz-fix-api-manifest-architecture-and-design-documentation-drift.review.md`
- 2026-11-26 reviewed (aw set): plan-review complete; APPROVE WITH REVISIONS APPLIED
- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 5 documentation fixes (23 verified findings across API, manifest, architecture, and design docs)
- 2026-11-25 draft (Antigravity): created.

## Goal

Align `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, and `docs/design/` with the live Python API (`src/pubrun/__init__.py`, `core.py`, `tracker.py`), capture modules, and `schemas/manifest.schema.json` (honestly noting schema/runtime divergences where runtime and schema disagree).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix `docs/api.md`

Invariant for every E-item in this plan: do not add, remove, or change any Markdown heading line (`#` to `######`) in the five Scope-Paths files, except that E-02 removes ``## `profiling` `` from `docs/manifest.md` and E-07 adds ``### `hardware.gpus[]` ``. Inbound links depend on current anchors (`README.md` links `api.md#pubrunpaused--contextmanager`; other docs link `manifest.md#meta-snapshot`, `manifest.md#packages`, and `manifest.md#timing`), and the H1 and section headings of both `docs/design/` files contain em dashes that must stay. Write no em or en dash (`\u2013`, `\u2014`) on any added line. When you rewrite a non-heading line that already contains one, replace the dash too, because the dash check reads every added line.

- [ ] E-01 Fix the examples, the `assess_run()` claim, and the inactive-run policy in `docs/api.md` (with no em or en dashes in added or edited lines):
  - Replace every `profile=` example. `core.profile` has no effect and is deprecated; a non-default value only records a `profile_deprecated` entry in the manifest's `config.notices` (`src/pubrun/config.py::profile_deprecation_notice`, recorded by `src/pubrun/tracker.py`; it is never raised). Line 75 becomes `pubrun.start(output_dir="./custom_storage", console={"capture_mode": "standard"})`. In the `**Override syntax:**` block (lines 85 to 87), keep the `output_dir="./runs"` line and replace the two `profile` lines with `pubrun.start(core={"output_dir": "./runs"})` (explicit nested form) and `pubrun.start(capture={"file_io": {"level": "hash"}})` (any other section, nested). Line 256 becomes `@audit_run(console={"capture_mode": "standard"})`.
  - In the `Flat shortcuts:` sentence (line 95), keep the four names (`_CORE_SHORTCUTS` in `src/pubrun/config.py::_resolve_layers`) and state that `profile` is accepted only for compatibility, changes nothing, and records the `profile_deprecated` notice. Rewrite the precedence note (line 98) with `output_dir`: `start(core={"output_dir": "./a"}, output_dir="./b")` results in `output_dir = "./b"`.
  - Replace lines 539 to 541 ("The CLI additionally merges ..."). State that `assess_run()` itself reports the five `file_provenance_*` codes (`file_provenance_changed`, `file_provenance_hash_failed`, `file_provenance_over_budget`, `file_provenance_asserted_only`, `file_provenance_unverified_paths`) in the `inputs_outputs` category (`src/pubrun/report/reproducibility.py::assess_manifest_reproducibility`), and that `pubrun inspect --json` calls the same function (`src/pubrun/__main__.py::_assess_cli_run`), so both return the same findings for the same inputs.
  - Replace line 197 ("Phase calls are safe ... silent no-ops"). Without an active run, `phase()` times nothing and writes no event, and entering the block follows `[events].on_inactive_annotate`: `"ignore"` (default) does nothing, `"warn"` logs a warning, and `"error"` raises `RuntimeError` (`src/pubrun/core.py::phase.__enter__` calls `_handle_inactive`).
  - After the `[events]` TOML block in `## 3. Custom Annotations`, add one sentence: despite its name, `on_inactive_annotate` governs all seven functions that call `src/pubrun/core.py::_handle_inactive`, namely `annotate()`, `phase()`, `report()`, `artifact()`, `register_file()`, `register_input()`, and `register_output()`.
  - In the `register_file` `**Return value**` bullet (line 413), add that a call without an active run also follows `on_inactive_annotate` (so `"error"` raises `RuntimeError` instead of returning `None`).
  - In `## API Summary`, change the `phase(name)` row (line 562) to `Yes (configurable)` and the three `register_*` rows (lines 567 to 569) to ``Yes (configurable; returns `None`)``.
  - Depends on: none
  - Expected outcome: `docs/api.md` teaches no deprecated `profile` usage, states that `assess_run()` and `pubrun inspect --json` report the same `file_provenance_*` findings, and describes the inactive-run policy for every function that obeys it.
  - Execution state: pending

- [ ] E-06 Fix the outcome rules, exports, summary rows, threading table, and hook table in `docs/api.md` (with no em or en dashes in added or edited lines):
  - Replace the outcome list under `### pubrun.stop()` (lines 111 to 115) with the rules the code applies. Review confirmed each rule with a probe run (see `## Required tests / validation`):
    - An explicit `pubrun.stop()` records `"completed"`, even when called inside an `except` block, unless the run is already `"failed"` or `"ghost"`; those outcomes are kept (`src/pubrun/tracker.py::Run.stop` with its default `outcome="completed"`).
    - `tracked_run()` and `audit_run()` classify the exception leaving the block or call (`src/pubrun/core.py::_classify_exit_outcome`): none, `SystemExit(0)`, or `SystemExit(None)` gives `"completed"`; `KeyboardInterrupt` gives `"interrupted"`; any other exception or non-zero `SystemExit`, including `SystemExit(True)`, gives `"failed"`.
    - When no explicit stop ran, interpreter-exit finalization classifies the recorded exit (`src/pubrun/tracker.py::Run._finalize_state` and `_outcome_from_signal_capture`): a `KeyboardInterrupt` gives `"interrupted"`; a non-zero exit code (for example `sys.exit(3)`) or an unhandled exception other than `SystemExit` gives `"failed"`; anything else gives `"completed"`.
    - After classification, a `"completed"` run that received SIGINT, SIGTERM, or SIGHUP becomes `"interrupted"`.
    - Keep the `"ghost"` bullet.
  - Change the `tracked_run()` intro sentence (line 239) to point to these rules instead of saying every exception gives `"failed"`.
  - Under `### pubrun.audit_run(**overrides) → Decorator`, add one sentence and a two-line example: the decorator also works bare, `@audit_run` with no parentheses, which uses the resolved configuration (`audit_run(func=None, **kwargs)` in `src/pubrun/core.py`).
  - In `## API Summary`, add three rows: `paused()` (suspend recording in the calling thread; `Yes (no-op)`), `__version__` (installed package version string; `N/A (attribute)`), and `__commit__` (commit SHA of the running build, read from packaged build metadata or from live `HEAD` of a verified pubrun source checkout, or `None` when unknown; resolved on first access; `N/A (attribute)`) (`src/pubrun/__init__.py`). After the edit, every one of the 20 names in `pubrun.__all__` appears in the table.
  - Change the `subprocess.run(...)` row (line 570) to `subprocess.run(...)` / `subprocess.Popen(...)`, and change the `report.checks.should_fail_strict(a, fail_on)` row (line 576) to `report.checks.should_fail_strict(a, *, fail_on="warn")` (`src/pubrun/report/reproducibility.py::should_fail_strict`).
  - In `## Threading Model`, add a `paused()` row: safe from any thread; it suspends recording only in the calling thread (`src/pubrun/core.py::paused`).
  - In `### Third-Party Hook Ownership Rules`, add a `sys.exit` (`SignalExitCapture`) row. Install: wraps the current `sys.exit` and chains to it; it records the exit code and `SystemExit` only on the main thread, and recording never changes how the process exits (`src/pubrun/capture/signals.py::SignalExitCapture._install_sys_exit`). Teardown: restores the previous `sys.exit` only when `sys.exit` is still pubrun's wrapper (`_restore_sys_exit`).
  - Depends on: E-01
  - Expected outcome: The outcome rules in `docs/api.md` match the explicit-stop, wrapper, and interpreter-exit paths; bare `@audit_run` is documented; the summary covers all 20 exports with correct signatures; and the threading and hook tables include `paused()` and `sys.exit`.
  - Execution state: pending

### Task group 2: Fix `docs/manifest.md`

- [ ] E-02 Fix the high-severity contract errors in `docs/manifest.md` (with no em or en dashes in added or edited lines):
  - Delete the ``## `profiling` `` section (heading, intro, table, and its trailing `---`, lines 492 to 503). In `## Top-Level Fields`, after the table, add a note: phase profiling (`[capture.profiling].enabled`) adds no key to `manifest.json`; each profiled phase writes `profile-<phase>.prof` in the run directory and emits a `profile_saved` event with the file name in `events.jsonl` (`src/pubrun/core.py::phase`). Nothing links to `#profiling`.
  - Rewrite `### Redacted Values` (lines 586 to 605):
    - Replace the hashed example with what `src/pubrun/capture/redaction.py::redact_value` writes when `[redaction].representation = "hashed"`: `{"representation": "hashed", "hash_algorithm": "sha256", "hash_value": "<64 hex characters>"}`.
    - Add an `unavailable` example, `{"representation": "unavailable"}`, used when no value exists (for example `git.remote_url` with no remote, `src/pubrun/capture/git.py`).
    - State that `schemas/manifest.schema.json` (`$defs.redacted_value`) also allows `suppressed`, which pubrun never writes, and that the schema describes a hashed value as `hash: {algorithm, value}` with no other properties allowed. A hashed value written by the current code therefore does not validate against the schema. Reconciling the two is deferred (see `## Deferred / out of scope`).
  - Change `python.virtual_env` (line 186) to: the literal string `"venv"` when Python runs in a virtual environment (`sys.prefix` differs from `sys.base_prefix`, or `sys.real_prefix` exists), else `null`; it never holds a path. Point readers to `prefix` for the path and to `environment_kind` and `in_venv` for the classification (`src/pubrun/capture/python_runtime.py::get_python_runtime`).
  - Rewrite the `status.outcome` description (line 558):
    - Written values: `"running"` (startup and in-progress manifests), `"completed"`, `"failed"`, `"interrupted"`, and `"ghost"`.
    - `"crashed"` is written into an existing run directory by `pubrun status` and `pubrun show` when they find a stale lock file (`src/pubrun/status.py::close_out_crashed_run`). It is not yet in the schema enum.
    - `"partial"` and `"unknown"` are in the schema enum but pubrun never writes them; readers display `"unknown"` when the field is missing.
    - Link to the outcome rules in `docs/api.md` (`api.md#pubrunstop`) instead of repeating them.
  - Depends on: none
  - Expected outcome: `docs/manifest.md` has no phantom section and describes `redacted_value`, `python.virtual_env`, and `status.outcome` as the code writes them, naming each schema divergence.
  - Execution state: pending

- [ ] E-03 Fix the `capture`, `invocation.script`, `console`, and Meta Snapshot sections in `docs/manifest.md` (with no em or en dashes in added or edited lines):
  - `capture.console_capture_mode` (line 514): it records the configured `[console].capture_mode` (default `"off"`), read before import-mode forcing (`full`, `noconsole`) and the Jupyter and non-TTY guards (`src/pubrun/tracker.py::Run.to_manifest_dict`). The mode actually used is `console.capture_mode`.
  - `### invocation.script` (lines 104 to 114), per `src/pubrun/capture/invocation.py`:
    - `path` is `sys.argv[0]` as given, so it can be relative.
    - Add `real_path` (the resolved absolute path) and `ctime`.
    - `sha256` is computed only for scripts up to 1,048,576 bytes. A larger script has no `sha256` key and carries `sha256_skipped: "file exceeds 1MB"`, which the schema does not yet define (deferred).
    - When `sys.argv[0]` is not a file (for example `python -c`), `script` is `{}`.
  - `## console` (lines 116 to 133), per `src/pubrun/capture/console.py::ConsoleInterceptor.stop`:
    - `stdout`, `stderr`, and the missing `combined` are each `{"captured": bool, "path": string | null, "lines_captured": int | null}`.
    - `combined` is always `{"captured": false, "path": null, "lines_captured": null}`, because pubrun writes only the split logs.
    - Besides `pending` and `complete`, the final `capture_state.status` can be `partial` (detail `"console log write failed during execution"`) or `failed` (the interceptor could not start).
  - `## Meta Snapshot` (line 646):
    - Replace "do not include run-specific fields (timing, ...)". A snapshot holds `manifest_type`, `timing.started_at_utc` (used for the parent-age check during hydration), `hardware`, `python`, `packages`, `git`, `environment`, and `host`, and no `schema_version`, `process`, `invocation`, `status`, `console`, or `resources` (`src/pubrun/report/meta_snapshot.py`).
    - In the `**What is filled:**` bullet, add `host` to the hydrable sections (`src/pubrun/report/utils.py::HYDRABLE_SECTIONS`).
    - In the intro sentence naming the commands that hydrate, list every caller of `hydrate_manifest` or `hydrate_manifest_with_report`: `pubrun show` (and its hidden alias `report`), `inspect`, `methods`, `rerun`, `diff`, `res`/`cpu`/`mem`, the TUI, and `pubrun.diff()`.
  - Depends on: E-02
  - Expected outcome: The `capture`, `invocation.script`, `console`, and Meta Snapshot descriptions match what the code writes and reads.
  - Execution state: pending

- [ ] E-07 Fix field typing, nullability, GPU records, and reserved keys in `docs/manifest.md` (with no em or en dashes in added or edited lines):
  - `subprocesses[].cwd` (line 148): type `string | null`. The global spy records the `cwd=` argument passed to `subprocess.Popen` (else `null`) and `null` for `os.system` (`src/pubrun/capture/subprocesses.py`); the explicit `pubrun.subprocess` and `pubrun.popen` wrappers omit the key. Leave the Lock File `cwd` row (line 619) unchanged.
  - Add a ``### `hardware.gpus[]` `` table directly after ``### `hardware.cpu` ``, per `src/pubrun/capture/hardware.py`:
    - `vendor`: `"NVIDIA"` from `nvidia-smi`, `"Generic"` from Windows WMI, `"Apple / Generic"` from macOS `system_profiler`.
    - `model`.
    - `memory_total_bytes`: `int | null`; `null` on macOS.
    - `driver_version`: `string | null`; absent on macOS.
    - `clock_speed_mhz`: `nvidia-smi` only, when `[capture.hardware].capture_gpu_clock_speed = true`.
    - State that the schema's `floating_point_precision` (`$defs.gpu_record`) is never written.
  - Add `| null` to these types:
    - `process.user.uid` and `gid` (lines 170 and 171).
    - `git.repo_root`, `commit`, `branch` (`string | null`) and `dirty` (`bool | null`) (lines 269 to 272; `src/pubrun/capture/git.py`).
    - `resources.peak_rss_bytes` and `end_rss_bytes` (`int | null`) and `peak_cpu_percent` (`float | null`), which are `null` when no positive sample was taken (lines 413 to 415; `src/pubrun/capture/resources.py`).
  - In the `capture.file_provenance_available` row (line 516), state that `data_files` is filled only by `pubrun.open()` and by `pubrun.register_file()`, `register_input()`, and `register_output()`. The row contains an em dash; replace it.
  - In `## Top-Level Fields`, add a note that the schema also defines `artifacts`, `determinism`, and `extensions`, which pubrun does not write (`[capture.determinism]` is not yet implemented, `src/pubrun/resources/default.toml`), and that every key pubrun writes has its own section below.
  - Depends on: E-03
  - Expected outcome: Field types, nullability, GPU record keys, and reserved top-level keys in `docs/manifest.md` match `src/pubrun/` and `schemas/manifest.schema.json`.
  - Execution state: pending

### Task group 3: Fix `docs/architecture.md` and `docs/design/`

- [ ] E-04 Update the header and Sections 5, 6, 10, and 13 of `docs/architecture.md` (with no em or en dashes in added or edited lines):
  - Change line 5 from `> Status: v1.0.0` to `> Status: Current (schema v1.0)`, the wording sibling plan `wjsccu` uses for `docs/functional_spec.md`.
  - Section 5 skeleton: add `"filesystem": {}` after `"host"`, and `"pubrun_imports": {}` and `"data_files": {}` after `"signals"`, matching the key order of `src/pubrun/tracker.py::Run.to_manifest_dict`.
  - Section 6: rewrite the `type` bullet (it contains an em dash) to list the nine event types and their sources:
    - `annotation` (`pubrun.annotate()`, also emitted by `pubrun.report()` and `pubrun.artifact()`).
    - `phase_start` and `phase_end` (`pubrun.phase()`).
    - `profile_saved` (phase profiling).
    - `resource_sample` (`src/pubrun/capture/resources.py`).
    - `input_dataset`, `output_artifact`, and `mixed_dataset` (`src/pubrun/capture/file_io.py`).
    - `warning` (storage migration, `src/pubrun/tracker.py`).
  - Section 6: rewrite the throttling sentence (line 107) per `src/pubrun/events.py`:
    - The critical types `phase_start`, `phase_end`, and `annotation` are written and flushed at once and are capped separately at `max(10000, 10 * max_tracked_events)`.
    - Other types are buffered, flushed every `[events].flush_interval_events` (default 100), and dropped once `[events].max_tracked_events` is reached.
  - Section 10 table:
    - Add `off` to the Packages and Environment mode lists (`src/pubrun/capture/packages.py`, `src/pubrun/capture/environment.py`).
    - Add a Filesystem row: key `filesystem`; no configuration key; classified alongside hardware and host capture.
    - Add a File I/O row: key `data_files`; `[capture.file_io].level` is `none`, `name`, `stat` (default), `realpath`, or `hash`.
    - Add a Profiling row: no manifest key (writes `profile-<phase>.prof` files and `profile_saved` events); `[capture.profiling].enabled` with backend `cprofile` or `yappi`.
  - Section 13:
    - Replace `<base_dir>/runs/pubrun-<script>-<timestamp>-<pid>-<run_id>/` with `<output_dir>/pubrun-<script>-<timestamp>-<pid>-<run_id>/`, and state that `<output_dir>` is `[core].output_dir`, or `./runs` under the current directory when that key is empty (the default; `src/pubrun/tracker.py`).
    - Add to the contents list:
      - `.pubrun.lock`: present while the run is active and removed on normal finalization.
      - `profile-<phase>.prof`: one per profiled phase, with the phase name reduced to `[A-Za-z0-9_-]`.
      - `<name>.json` or `<name>.txt`: written by `pubrun.report()`.
      - Files written by `pubrun.artifact()`.
  - Depends on: none
  - Expected outcome: The header, manifest skeleton, event model, capture categories, and run directory model in `docs/architecture.md` match the code.
  - Execution state: pending

- [ ] E-08 Update Sections 16, 18, and 21 of `docs/architecture.md` (with no em or en dashes in added or edited lines):
  - Section 16: add rows for the twelve exports the table lacks: `paused()`, `report()`, `artifact()`, `print()`, `open()`, `register_file()`, `register_input()`, `register_output()`, `subprocess`, `popen()`, `__version__`, and `__commit__`. After the table, add a sentence linking `api.md#api-summary` for signatures and inactive-run behavior.
  - Section 18:
    - Add `sys.exit` to the hook list in the `Independent cleanup and hook ownership` bullet (line 266).
    - In the `Honest consumers` bullet (line 267), change `pubrun report` to `pubrun show`; `report` is a hidden alias (`src/pubrun/__main__.py`).
  - Section 21:
    - Change the `**Diagnostics Analyzer** (`pubrun report`)` bullet to name `pubrun show`, noting `report` as its hidden alias. The bullet contains an em dash; use a colon.
    - Add bullets, each using a colon rather than a dash, for:
      - The six mode modules (`auto.py`, `full.py`, `minimal.py`, `noauto.py`, `noconsole.py`, `nopatch.py`).
      - The CLI entry point (`__main__.py`).
      - Run status, lock files, and crashed-run close-out (`status.py`).
      - The diff engine (`analysis/`).
      - Post-hoc reports and assessment (`report/`).
      - The Textual dashboard (`tui/`).
    - Add bullets for the CLI commands the section lacks, writing each as `` `pubrun <command>` `` so the coverage check finds it: `pubrun inspect`, `pubrun self-check`, `pubrun bench`, `pubrun ui`, `pubrun init`, `pubrun combined`, `pubrun res`, `pubrun cpu`, `pubrun mem`, `pubrun cite`, `pubrun report-bug`, and `pubrun feedback`. This is the full `python -m pubrun --help` command list minus the commands Section 21 already names.
  - Depends on: E-04
  - Expected outcome: Sections 16, 18, and 21 of `docs/architecture.md` list every export, every global hook, every top-level module and package, and every CLI command.
  - Execution state: pending

- [ ] E-05 Update the two design records under `docs/design/` (with no em or en dashes in added or edited lines). These are dated historical records: add an outcome banner and correct only stale references, and do not rewrite the H1, other headings, the analysis, or the `- Status:` line.
  - `docs/design/file-io-provenance-evaluation.md`:
    - Add a blockquote banner directly below the H1, headed `Outcome as of 2026-11-25`:
      - Recommendation 1 shipped as `resources.io_counters` (Linux `/proc/self/io`, `src/pubrun/capture/system_metrics.py::get_proc_io`).
      - Recommendation 2 shipped as `pubrun.open()` with `ProvenanceFileProxy` (now in `src/pubrun/capture/file_io.py`) and `pubrun.register_file()`, `register_input()`, and `register_output()`, with `[capture.file_io].level` ordered `none < name < stat < realpath < hash` and default `stat`.
      - The "Proposed config knob" section's `level = "none"` default and order, and its `mode` and `exclude` keys, are superseded. The shipped keys are `level`, `max_hash_bytes`, `max_total_hash_bytes`, `max_total_hash_seconds`, and `hash_algorithm`.
      - The proxy correctness gaps the analysis lists were addressed: it now intercepts `read1`, `readinto`, `readinto1`, and `seek`, and text-mode hashes are computed from the on-disk bytes.
      - Recommendation 3 (`sys.addaudithook`) is not implemented, and the Recommendation 4 rejection stands.
      - The `core.py` line references describe the code as of 2026-07-06.
      - Link `../api.md`, `../manifest.md`, and `../configuration.md`.
    - Change `pause()` to `pubrun.paused()` on lines 32 and 100 (`src/pubrun/core.py::paused`; there has never been a bare `pause()`).
  - `docs/design/tomli-dependency-decision.md`:
    - Replace lines 19 to 24 (the bullets contain em dashes) with the five functions that parse TOML today, named by module and function:
      - `src/pubrun/config.py::load_default_config` (bundled defaults).
      - `src/pubrun/config.py::_safe_load_toml` (user and local config files, including `TOMLDecodeError` handling).
      - `src/pubrun/_config_boot.py::_load_toml_file` (boot-time import-mode config; returns `None` when `tomli` is missing on 3.8-3.10).
      - `src/pubrun/__init__.py::_pyproject_declares_pubrun` (reads `pyproject.toml` while resolving `__commit__`, with a fallback parser when neither module imports).
      - `src/pubrun/report/checks.py::_config_file_findings` (`pubrun self-check` config-file findings).
    - Replace `README.md:9`, `README.md:19` (lines 98 and 99, which contain an en dash) with the current locations: footnote `[^1]`, the note under `## Installation`, and the "Zero runtime dependencies" bullet under `## Built to be Trustworthy`.
  - Depends on: none
  - Expected outcome: Readers of `docs/design/` see what shipped and what remains deferred, and every symbol reference resolves to current code.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`docs/*.md`, `docs/design/*.md`).
- `schemas/manifest.schema.json` enforces `"additionalProperties": false` at the top level and has no `profiling` property.
- `src/pubrun/__init__.py::__all__` exports 20 public symbols including `__version__`, `__commit__`, `paused`, `register_file`, `register_input`, `register_output`, `subprocess`, `popen`.
- `src/pubrun/report/utils.py::HYDRABLE_SECTIONS` includes `"host"`.
- Design records under `docs/design/` are dated decision records. Corrections there are banners and reference fixes, not rewrites.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| A-01 | High | Low | Operator | `docs/manifest.md` `## profiling` vs `src/pubrun/tracker.py::Run.to_manifest_dict` & `schemas/manifest.schema.json` | Documents phantom top-level `profiling` manifest section that is never emitted and violates `additionalProperties: false`. |
| A-02 | High | Low (doc part) | Operator | `docs/manifest.md` `redacted_value` vs `src/pubrun/capture/redaction.py::redact_value` & `schemas/manifest.schema.json` | Hashed representation disagrees with both live code (`hash_algorithm`/`hash_value`) and JSON Schema (`hash: {algorithm, value}`); omits `unavailable` (written) and `suppressed` (schema-only). |
| A-03 | High | Low | Novice / Operator | `docs/manifest.md` `python.virtual_env` vs `src/pubrun/capture/python_runtime.py` | Documented as a path, but emits literal `"venv"` or `null`. |
| A-04 | High | Low | Novice | `docs/api.md` primary examples vs `src/pubrun/config.py` & `default.toml` | Teaches deprecated, inert `profile="deep"` / `profile="basic"` without warning. |
| A-05 | High | Low | Operator | `docs/api.md` `assess_run()` vs `src/pubrun/report/reproducibility.py::assess_manifest_reproducibility` & `__main__.py::_assess_cli_run` | Falsely claims `pubrun inspect --json` merges `file_provenance_*` findings omitted by `assess_run()`. |
| A-06 | Medium | Low | Operator / Novice | `docs/manifest.md` (`console_capture_mode`, `invocation.script`, `console`, `Meta Snapshot`, `status.outcome`) vs `src/pubrun/` | Field-level inaccuracies and omissions: `running` and `crashed` outcomes are written but undocumented, `partial` and `unknown` are schema-only, and `host`, `real_path`, `ctime`, `captured`, and `combined` are missing. |
| A-07 | Medium | Low | Novice / Operator | `docs/api.md` (`phase`, `register_*`, `stop`, `tracked_run`, `audit_run`, `__all__`, `should_fail_strict`) vs `src/pubrun/core.py`, `tracker.py` & `reproducibility.py` | Calls inactive `phase()` a silent no-op and gives `register_*` a fixed `None` result, although all four obey `on_inactive_annotate`; misstates which path sets which outcome (explicit `stop()`, wrappers, interpreter exit); omits bare `@audit_run`, `__version__`/`__commit__`, `paused()` in the summary and threading tables, and the keyword-only `*` in `should_fail_strict`. |
| A-08 | Medium | Low | Operator | `docs/architecture.md` Sections 5, 6, 10, 13, 16, 18, 21 & `docs/design/file-io-provenance-evaluation.md` | Omits live manifest sections, event types, capture categories, exports, modules, and CLI commands; misstates the run directory path as `<base_dir>/runs/`; the Phase-0 file-I/O design record lacks an outcome banner and keeps a superseded default. |
| A-09 | Low | Low | Operator / Novice | `docs/manifest.md` (`subprocesses[].cwd`, `gpus[]`, nullability), `docs/api.md` & `docs/architecture.md` (`sys.exit`, header status), `docs/design/tomli-dependency-decision.md` | Minor field typing/nullability omissions, missing `sys.exit` hook entry, stale header `v1.0.0`, and stale TOML and README line citations. |

## Proposed changes (ordered, validatable)

1. Fix `docs/api.md` examples, the `assess_run()` claim, and the inactive-run policy (E-01; Remediation Risk: Low).
2. Fix `docs/api.md` outcome rules, exports, summary rows, threading table, and hook table (E-06; Remediation Risk: Low).
3. Fix `docs/manifest.md` top-level `profiling`, `redacted_value`, `python.virtual_env`, and `status.outcome` (E-02; Remediation Risk: Low).
4. Fix `docs/manifest.md` `capture.console_capture_mode`, `invocation.script`, `console`, and Meta Snapshot (E-03; Remediation Risk: Low).
5. Fix `docs/manifest.md` `subprocesses[].cwd`, `hardware.gpus[]`, nullability, the provenance note, and reserved keys (E-07; Remediation Risk: Low).
6. Update `docs/architecture.md` header and Sections 5, 6, 10, and 13 (E-04; Remediation Risk: Low).
7. Update `docs/architecture.md` Sections 16, 18, and 21 (E-08; Remediation Risk: Low).
8. Add an outcome banner to `docs/design/file-io-provenance-evaluation.md` and refresh references in both design records (E-05; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Reconciling `redacted_value` hashed schema vs `src/pubrun/capture/redaction.py`, adding `"crashed"` to `status.outcome` in `schemas/manifest.schema.json`, and adding `sha256_skipped` to `invocation.script` in `schemas/manifest.schema.json` are deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality).
  - Carrier-Declined: Schema/runtime contract changes outside documentation-only scope; recorded in orchestrator `86cd17`.
- Removing existing em and en dashes from lines this plan does not edit (for example the H1 and section headings of both `docs/design/` files) is tracked by orchestrator `86cd17` as a separate repo-wide sweep.
  - Carrier-Declined: Pre-existing cleanup; editing headings would also change anchors.

## Scope check

- Over-scope: none. Only the five documentation files in `- Scope-Paths:` are modified.
- Under-scope: none after review. Review added the other inactive-policy callers, the explicit-stop and interpreter-exit outcome paths, the `__commit__` and `__version__` summary rows, the `combined` console stream, the full hydration caller list, the Section 6 and 13 architecture gaps, and the `feedback` command. It also corrected the claim that `partial` is a written outcome.
- No other pending or approved plan declares any of the five paths. Sibling Scope-Paths are disjoint: `0cjiv5` (`README.md`, `CONTRIBUTING.md`, `.pre-commit-config.yaml`), `pqcx6o` (`docs/cli.md`, `docs/configuration.md`), `77pdvl` (`CHANGELOG.md`, `CITATION.cff`), `wjsccu` (`docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`), and `2uwuiu` (`examples/`). Plan `87qr8h` (Set `aqb2bu`) mentions `docs/manifest.md` only as already up to date and does not edit it.
- Diagram (technical-writing requirement 12): not added. The steps are independent edits to sections of five reference files. The one branching topic, outcome classification, is a short decision list in E-06 and gains nothing from a diagram.

## Required tests / validation

- Diff inspection across all five files.
- Dash check. For each edited file `<f>`, run the command below. It must print nothing and report `exit=1` (grep found no em or en dash on an added line):

  ```sh
  git diff -U0 -- <f> | grep '^+' | grep -v '^+++' | grep -nP '[\x{2013}\x{2014}]'; echo "exit=$?"
  ```

- Heading check. The command below must print nothing and report `exit=1` (no heading line was added, removed, or changed except the two the plan names):

  ```sh
  git diff -U0 -- docs/api.md docs/manifest.md docs/architecture.md docs/design/file-io-provenance-evaluation.md docs/design/tomli-dependency-decision.md | grep -E '^[-+]#{1,6} ' | grep -vxF -e '-## `profiling`' -e '+### `hardware.gpus[]`'; echo "exit=$?"
  ```

- Table check. The command below must print `mismatched=0`. It counts the cells of every Markdown table row outside code fences, ignoring pipes inside backticks, and compares each row with its header. It reports `mismatched=0` before execution:

  ```sh
  python3 - docs/api.md docs/manifest.md docs/architecture.md docs/design/file-io-provenance-evaluation.md docs/design/tomli-dependency-decision.md <<'PY'
  import re, sys, pathlib
  bad = 0
  for f in sys.argv[1:]:
      lines = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), pathlib.Path(f).read_text(encoding="utf-8"), flags=re.S).split("\n")
      width = None
      for n, line in enumerate(lines, 1):
          s = line.strip()
          if not s.startswith("|"):
              width = None; continue
          cells = len(re.split(r"(?<!\\)\|", re.sub(r"`[^`]*`", "x", s).strip("|")))
          if width is None:
              width = cells
          elif cells != width:
              bad += 1; print("MISMATCH %s:%d header=%d row=%d" % (f, n, width, cells))
  print("mismatched=%d" % bad)
  PY
  ```

- Link and anchor check. The command below must print `broken=0`. It checks every relative link in `README.md`, `CONTRIBUTING.md`, `docs/*.md`, and `docs/design/*.md`, including cross-file `#anchor` links into the edited files. It reports `broken=0` before execution:

  ```sh
  python3 - README.md CONTRIBUTING.md docs/*.md docs/design/*.md <<'PY'
  import re, sys, pathlib
  def load(p):
      body = re.sub(r"```.*?```", "", p.read_text(encoding="utf-8"), flags=re.S)
      return body, {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#{1,6} +(.+?) *$", body, flags=re.M)}
  bad = 0
  for f in sys.argv[1:]:
      p = pathlib.Path(f); body, own = load(p)
      for t in re.findall(r"\]\(([^)\s]+)\)", body):
          if t.startswith(("http://", "https://", "mailto:")):
              continue
          path, _, anchor = t.partition("#")
          target = p.parent / path if path else p
          if path.startswith("file:") or not target.exists():
              bad += 1; print("BROKEN", f, t); continue
          if anchor and target.suffix == ".md" and anchor not in (own if not path else load(target)[1]):
              bad += 1; print("BROKEN", f, t)
  print("broken=%d" % bad)
  PY
  ```

- Coverage check. The command below compares the docs with the live package, schema, and CLI. After execution every list must be empty and `manifest_profiling_section=0`. Before execution it prints `arch_skeleton_missing=['data_files', 'filesystem', 'pubrun_imports']`, six missing event types, three missing categories, three missing run directory items, twelve missing Section 16 exports, `['`sys.exit`']` twice, thirteen missing CLI commands, eleven missing modules, `api_summary_missing=['paused', '__version__', '__commit__']`, `api_threading_missing=['`paused()`']`, `manifest_hydrable_missing=['host']`, three missing reserved keys, and `manifest_profiling_section=1`:

  ```sh
  PYTHONPATH=src PUBRUN_IMPORT_MODE=noauto python3 - <<'PY'
  import json, re, subprocess, sys, pathlib
  import pubrun
  from pubrun.report.utils import HYDRABLE_SECTIONS
  def sec(f, a, b):
      t = pathlib.Path(f).read_text(encoding="utf-8")
      return t[t.index(a):t.index(b, t.index(a))]
  A = "docs/architecture.md"
  schema = json.load(open("schemas/manifest.schema.json"))["properties"]
  skel = json.loads(re.search(r"```json\n(.*?)```", sec(A, "\n## 5. ", "\n## 6. "), re.S).group(1))
  print("arch_skeleton_missing=%s" % sorted(set(schema) - {"artifacts", "determinism", "extensions"} - set(skel)))
  events = ["annotation", "phase_start", "phase_end", "profile_saved", "resource_sample", "input_dataset", "output_artifact", "mixed_dataset", "warning"]
  print("arch_events_missing=%s" % [e for e in events if "`%s`" % e not in sec(A, "\n## 6. ", "\n## 7. ")])
  s10 = sec(A, "\n## 10. ", "\n## 11. ")
  print("arch_categories_missing=%s" % [k for k in ("`filesystem`", "`data_files`", "`[capture.profiling]") if k not in s10])
  s13 = sec(A, "\n## 13. ", "\n## 14. ")
  print("arch_rundir_missing=%s" % [k for k in ("<output_dir>/pubrun-<script>-<timestamp>-<pid>-<run_id>/", ".pubrun.lock", "profile-<phase>.prof") if k not in s13])
  s16 = sec(A, "\n## 16. ", "\n## 17. ")
  print("arch_api_missing=%s" % [n for n in pubrun.__all__ if not re.search(r"`(pubrun\.)?%s[`(.]" % re.escape(n), s16)])
  print("arch_hooks_missing=%s" % [k for k in ("`sys.exit`",) if k not in sec(A, "\n## 18. ", "\n## 19. ")])
  helptext = subprocess.run([sys.executable, "-m", "pubrun", "--help"], capture_output=True, text=True).stdout
  s21 = sec(A, "\n## 21. ", "\n## 22. ")
  print("arch_cli_missing=%s" % [c for c in re.findall(r"^    ([a-z][a-z-]*)", helptext, re.M) if "`pubrun %s`" % c not in s21])
  print("arch_modules_missing=%s" % [m for m in ("analysis/", "report/", "tui/", "status.py", "__main__.py", "auto.py", "full.py", "minimal.py", "noauto.py", "noconsole.py", "nopatch.py") if "`%s`" % m not in s21])
  D = "docs/api.md"
  summ = sec(D, "\n## API Summary", "\n## Threading Model")
  print("api_summary_missing=%s" % [n for n in pubrun.__all__ if not re.search(r"`(pubrun\.)?%s[`(. ]" % re.escape(n), summ)])
  print("api_threading_missing=%s" % [k for k in ("`paused()`",) if k not in sec(D, "\n## Threading Model", "\n---")])
  print("api_hooks_missing=%s" % [k for k in ("`sys.exit`",) if k not in sec(D, "\n### Third-Party Hook Ownership Rules", "\n---")])
  M = "docs/manifest.md"
  filled = sec(M, "**What is filled:**", "**`is_hydrated`:**")
  print("manifest_hydrable_missing=%s" % [s for s in HYDRABLE_SECTIONS if "`%s`" % s not in filled])
  top = sec(M, "\n## Top-Level Fields", "\n## `run`")
  print("manifest_reserved_missing=%s" % [k for k in ("artifacts", "determinism", "extensions") if "`%s`" % k not in top])
  print("manifest_profiling_section=%d" % len(re.findall(r"^## `profiling`$", pathlib.Path(M).read_text(encoding="utf-8"), re.M)))
  PY
  ```

- Outcome probe. The command below drives the explicit-stop, interpreter-exit, and wrapper code paths (`src/pubrun/tracker.py::Run.stop` and `Run._finalize_state`, `src/pubrun/core.py::_stop_for_exit`) in temporary directories and prints the recorded outcomes. It printed `stop_in_except=completed unhandled_exception=failed sys_exit_3=failed tracked_run_keyboardinterrupt=interrupted tracked_run_systemexit0=completed` during review, and the E-06 rules must agree with every value:

  ```sh
  PYTHONPATH=src PUBRUN_IMPORT_MODE=noauto python3 - <<'PY'
  import glob, json, subprocess, sys, tempfile
  cases = {
      "stop_in_except": "pubrun.start(output_dir=D)\ntry:\n    raise ValueError('x')\nexcept ValueError:\n    pubrun.stop()",
      "unhandled_exception": "pubrun.start(output_dir=D)\nraise ValueError('x')",
      "sys_exit_3": "pubrun.start(output_dir=D)\nsys.exit(3)",
      "tracked_run_keyboardinterrupt": "with pubrun.tracked_run(output_dir=D):\n    raise KeyboardInterrupt",
      "tracked_run_systemexit0": "with pubrun.tracked_run(output_dir=D):\n    sys.exit(0)",
  }
  out = []
  for name, body in cases.items():
      with tempfile.TemporaryDirectory() as d:
          subprocess.run([sys.executable, "-c", "import sys, pubrun\nD = sys.argv[1]\n" + body, d], capture_output=True)
          out.append("%s=%s" % (name, json.load(open(glob.glob(d + "/*/manifest.json")[0]))["status"]["outcome"]))
  print(" ".join(out))
  PY
  ```

- Inactive-policy probe. The command below sets `[events].on_inactive_annotate = "error"` in a temporary project and calls each function E-01 documents without an active run (`src/pubrun/core.py::_handle_inactive`). It printed `phase=RuntimeError register_file=RuntimeError register_input=RuntimeError register_output=RuntimeError` during review:

  ```sh
  PYTHONPATH=src PUBRUN_IMPORT_MODE=noauto python3 - <<'PY'
  import os, subprocess, sys, tempfile
  code = """
  import pubrun
  res = []
  for name, fn in [("phase", lambda: pubrun.phase("p").__enter__()), ("register_file", lambda: pubrun.register_file("x")), ("register_input", lambda: pubrun.register_input("x")), ("register_output", lambda: pubrun.register_output("x"))]:
      try:
          fn(); res.append(name + "=no-raise")
      except RuntimeError:
          res.append(name + "=RuntimeError")
  print(" ".join(res))
  """
  with tempfile.TemporaryDirectory() as d:
      open(os.path.join(d, ".pubrun.toml"), "w").write('[events]\non_inactive_annotate = "error"\n')
      env = dict(os.environ, PYTHONPATH=os.path.abspath("src"))
      print(subprocess.run([sys.executable, "-c", code], cwd=d, env=env, capture_output=True, text=True).stdout.strip())
  PY
  ```

- `python3 scripts/sanitize_paths.py --check --all` exits 0 (it exits 0 before execution).
- No test or `.github/scripts/` file reads any of the five files, so no test command is required.

## Spec / documentation sync

- Pure documentation synchronization with live code and schema; no runtime or schema files change. No spec governs these five files. Matching drift in other documents is owned by sibling plans: `pqcx6o` (`docs/cli.md`, `docs/configuration.md`, including the same seven-function `on_inactive_annotate` statement and `"off"` for `[capture.environment].mode`), `wjsccu` (`docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`, with the same header wording), `0cjiv5` (`README.md`), and `77pdvl` (`CHANGELOG.md`). Documentation-only fixes need no `CHANGELOG.md` entry.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/api.md` hunks for lines 75, 85 to 98, and 256 (no `profile` example; `profile` marked deprecated with the `profile_deprecated` notice), the replacement of lines 539 to 541, the `phase()` inactive sentence, the seven-function sentence in `## 3. Custom Annotations`, the `register_file` return-value bullet, and the four API Summary rows. Pasted inactive-policy probe output `phase=RuntimeError register_file=RuntimeError register_input=RuntimeError register_output=RuntimeError` (code path `src/pubrun/core.py::_handle_inactive`). Pasted output of the command below showing `exit=1`:

    ```sh
    grep -nE 'profile="(deep|basic|minimal)"|"profile": "(deep|minimal)"|can list file-provenance findings|become silent no-ops|^\| `(phase|register_(file|input|output))\(.*\| Yes \((silent no-op|returns `None`)\) \|$' docs/api.md; echo "exit=$?"
    ```

  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/manifest.md` hunks for the removed ``## `profiling` `` section and the new profiling note in `## Top-Level Fields`, `### Redacted Values` (the `hash_algorithm`/`hash_value` example, `unavailable`, `suppressed` as schema-only, and the schema-divergence statement), `python.virtual_env`, and `status.outcome` (`running` and `crashed` written; `partial` and `unknown` schema-only). Pasted output of `PYTHONPATH=src PUBRUN_IMPORT_MODE=noauto python3 -c "from pubrun.capture.redaction import redact_value; print(sorted(redact_value('x', {'redaction': {'representation': 'hashed'}})))"` showing `['hash_algorithm', 'hash_value', 'representation']` (code path `src/pubrun/capture/redaction.py::redact_value`). Pasted output of the command below showing `exit=1`:

    ```sh
    grep -nE '^## `profiling`$|"value": "sha256:|Path to the active virtual environment' docs/manifest.md; echo "exit=$?"
    ```

  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/manifest.md` hunks for `capture.console_capture_mode`, `### invocation.script` (`real_path`, `ctime`, the 1,048,576-byte `sha256` limit with `sha256_skipped`, and `{}` for non-file `argv[0]`), `## console` (`captured`, `combined`, `partial`, `failed`), and `## Meta Snapshot` (the snapshot key list, `host` in the hydrable list, and the full hydration caller list). Pasted coverage check line `manifest_hydrable_missing=[]`. Pasted output of the command below showing `exit=1`:

    ```sh
    grep -nE 'The effective console mode|Absolute path to the entry-point script|do not include run-specific fields \(timing' docs/manifest.md; echo "exit=$?"
    ```

  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/architecture.md` hunks for the header, the Section 5 skeleton, the Section 6 `type` bullet and throttling sentence, the Section 10 rows, and Section 13. Pasted coverage check lines `arch_skeleton_missing=[]`, `arch_events_missing=[]`, `arch_categories_missing=[]`, and `arch_rundir_missing=[]`. Pasted output of `grep -nE '<base_dir>/runs/|Status: v1\.0\.0' docs/architecture.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted `git diff -- docs/design/file-io-provenance-evaluation.md docs/design/tomli-dependency-decision.md` showing the banner directly below the unchanged H1, the two `pubrun.paused()` corrections, the five TOML call sites, and the README location fix. Because E-05 is the last item, also paste, run after all eight E-items: the dash check output for each of the five files (each `exit=1`), the heading check output (`exit=1`), the table check output (`mismatched=0`), the link and anchor check output (`broken=0`), the full coverage check output (every list empty and `manifest_profiling_section=0`), and `python3 scripts/sanitize_paths.py --check --all; echo "exit=$?"` showing `exit=0`. Pasted output of the command below showing `exit=1`:

    ```sh
    grep -nE '`pause\(\)`|README\.md:(9|19)|exactly four places' docs/design/file-io-provenance-evaluation.md docs/design/tomli-dependency-decision.md; echo "exit=$?"
    ```

  - Observed evidence:
  - Result: pending
- [ ] V-06 validates E-06
  - Required evidence: Pasted `git diff -- docs/api.md` hunks for the outcome rules under `### pubrun.stop()`, the `tracked_run()` intro sentence, the bare `@audit_run` sentence and example, the three new API Summary rows, the `subprocess.Popen(...)` and `should_fail_strict(a, *, fail_on="warn")` rows, the `paused()` Threading Model row, and the `sys.exit` hook row. Pasted outcome probe output `stop_in_except=completed unhandled_exception=failed sys_exit_3=failed tracked_run_keyboardinterrupt=interrupted tracked_run_systemexit0=completed` (code paths `src/pubrun/tracker.py::Run.stop`, `Run._finalize_state`, and `src/pubrun/core.py::_stop_for_exit`), with each value matching a rule in the diff. Pasted coverage check lines `api_summary_missing=[]`, `api_threading_missing=[]`, and `api_hooks_missing=[]`. Pasted output of the command below showing `exit=1`:

    ```sh
    grep -nF -e 'set by `tracked_run` / `audit_run`' -e 'If an exception occurs, the run is finalized with `outcome = "failed"`' -e 'should_fail_strict(a, fail_on)' docs/api.md; echo "exit=$?"
    ```

  - Observed evidence:
  - Result: pending

- [ ] V-07 validates E-07
  - Required evidence: Pasted `git diff -- docs/manifest.md` hunks for the `subprocesses[].cwd` row, the new ``### `hardware.gpus[]` `` table (with `floating_point_precision` named as schema-only), the `| null` changes for `uid`, `gid`, `repo_root`, `commit`, `branch`, `dirty`, `peak_rss_bytes`, `end_rss_bytes`, and `peak_cpu_percent`, the `capture.file_provenance_available` row, and the reserved-keys note in `## Top-Level Fields`. Pasted coverage check line `manifest_reserved_missing=[]`. Pasted output of the command below showing `exit=1` (it matches lines 148, 170, 171, 269 to 272, and 413 to 415 before execution):

    ```sh
    grep -nE '^\| `cwd` \| string \| Working directory of the subprocess|^\| `(uid|gid)` \| int \||^\| `(repo_root|commit|branch)` \| string \||^\| `dirty` \| bool \||^\| `(peak_rss_bytes|end_rss_bytes)` \| int \||^\| `peak_cpu_percent` \| float \|' docs/manifest.md; echo "exit=$?"
    ```

  - Observed evidence:
  - Result: pending

- [ ] V-08 validates E-08
  - Required evidence: Pasted `git diff -- docs/architecture.md` hunks for the twelve Section 16 rows and the `api.md#api-summary` link, the Section 18 `sys.exit` hook entry and `pubrun show` change, and the Section 21 module, package, and CLI command bullets. Pasted coverage check lines `arch_api_missing=[]`, `arch_hooks_missing=[]`, `arch_cli_missing=[]`, and `arch_modules_missing=[]`. Pasted output of the command below showing `exit=1` (it matches lines 267 and 302 before execution):

    ```sh
    grep -nF '`pubrun report`' docs/architecture.md; echo "exit=$?"
    ```

  - Observed evidence:
  - Result: pending


## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`). No blocking open questions exist.
2. Scope declaration: `- Scope-Paths:` declares the five paths this plan changes. If an out-of-scope edit proves necessary, make it and justify it at finalize (`--scope-reason <path>=<why>`); acknowledge any declared path left unmodified (`--scope-ack`).
3. Validation honesty: run every command in `## Required tests / validation` after the final edit and paste the actual output into each `V-*` item. Never claim a check passed without pasting its output.
4. Commit discipline: commit through `aw commit dd7noz -- docs/api.md docs/manifest.md docs/architecture.md docs/design/file-io-provenance-evaluation.md docs/design/tomli-dependency-decision.md`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: the plan must reach `executed/` through `aw ipd finalize dd7noz`, never a hand-run `git mv`. When a runner (`aw oc run` or `aw agy run`) drives execution, the runner finalizes; otherwise the executor runs it. Finalize only once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
