# IPD: Fix CLI and configuration reference inaccuracies and drift

- Date: 2026-11-25
- Kind: child
- Concern: `docs/cli.md` and `docs/configuration.md` contain high-impact inaccuracies including non-existent `pubrun show` multi-directory syntax, a malformed GFM table dropping config descriptions, contradictory `[capture.resources].scope` claims, inert config keys documented as active, and a false `PUBRUN_IMPORT_MODE` precedence claim.
- Scope: `docs/cli.md` and `docs/configuration.md`.
- Scope-Paths: docs/cli.md, docs/configuration.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Fix docs/cli.md show/diff/filter/selection docs and docs/configuration.md table, scope, inert keys, and env precedence
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 2
- Highest E allocated: 08
- Author: Antigravity
- Id: pqcx6o
- Approval: 2026-11-26, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Claude Opus 5.5, OpenCode): APPROVE WITH REVISIONS APPLIED; PR-001..PR-010 all FIXED; review record `.aw/records/reviews/20261125-doc-audit-02-pqcx6o-fix-cli-and-configuration-reference-inaccuracies-and-drift.review.md`.
- 2026-11-25 reviewed (aw set): plan-review complete; APPROVE WITH REVISIONS APPLIED
- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 5 documentation fixes (19 verified findings across `docs/cli.md` and `docs/configuration.md`)
- 2026-11-25 draft (Antigravity): created.

## Goal

Bring `docs/cli.md` and `docs/configuration.md` into exact agreement with the live CLI parser (`src/pubrun/__main__.py`), status/diagnostics/diff renderers, configuration defaults (`src/pubrun/resources/default.toml`), and environment-variable resolution (`src/pubrun/_bootstrap.py`, `src/pubrun/_config_boot.py`, `src/pubrun/config.py`).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix `docs/cli.md` accuracy and completeness

Invariant for every E-item in this plan: do not edit any Markdown heading line (`#` to `######`) in `docs/cli.md` or `docs/configuration.md`. Twenty headings in these files contain an em dash, and their GitHub anchors are linked from other files (`docs/configuration.md` links `cli.md#show-config--inspect-resolved-configuration`; `docs/api.md` and `docs/hpc.md` link `cli.md#inspect--post-hoc-run-diagnosis`; `docs/performance.md` links `configuration.md#artifact-durability-policy`). Removing the dash changes the anchor and breaks those links. When you rewrite a non-heading line that already contains an em or en dash, replace the dash too, because the dash check reads every added line.

- [ ] E-01 Fix `show`/`report`, `diff`, and `Selecting a run` inaccuracies in `docs/cli.md` (with no em or en dashes in added or edited lines):
  - **`show` / `report`** (`### \`show\``): change the synopsis to `pubrun show [RUN_DIR] [logs|env|packages] [--basic|--standard|--deep] [--utc] [run filters] [-n N]`, and add the three `show config` forms (`show config`, `show run config [<id>]`, `show default config`) as a second synopsis line. Delete the bullet "Pass multiple directories to evaluate them sequentially." The existing filter bullet already explains multi-run display, so state there that `RUN_DIR` must be omitted for filters or `-n` to select several runs (`src/pubrun/__main__.py::main` iterates `filter_runs` results only when `run_dir` is empty). Document the `logs`, `env`, and `packages` section extracts (`src/pubrun/report/diagnostics.py::SHOW_SECTIONS`), including the shifted form `pubrun show env`, where a bare section name in the `RUN_DIR` position is treated as the section. Rewrite the alias line: hidden alias `report` accepts the same depth, `--utc`, filter, and `-n` flags but has no `--all` flag and no third positional, so `report run config <id>` is not accepted (`report_parser` defines only `run_dir` and `section`).
  - **`diff`** (`### \`diff\``): change the synopsis to `pubrun diff [RUN_DIR_A [RUN_DIR_B]] [OPTIONS]` and document the argument count: none compares the two most recent runs (matching the run filters when given); one compares that run with the most recent other run; two compares them; arguments after the second are ignored (`run_dirs` is `nargs="*"` and only `run_dirs[0]` and `run_dirs[1]` are read). In the `--basic` row, remove `packages` from the shown list and replace "packages-as-list" with "packages" in the hidden list (`default.toml` `[diff].ignore_basic` contains `"packages"`).
  - **`Selecting a run`** (`### Selecting a run`): add `combined` to the command list. State that `status` and `combined` accept only a recency index, a run-id prefix, or a unique substring of the run directory name, searched within `--dir` or the configured output directory (`src/pubrun/status.py::find_run`), and not an arbitrary path or a `manifest.json` path. State that `show`/`report`, `res`/`cpu`/`mem`, `methods`, `inspect`, `rerun`, and `diff` also accept a directory or `manifest.json` path (`src/pubrun/__main__.py::_get_manifest_path` falls back to `Path(run_dir)`). Add the directory-name substring form to the form table.
  - Depends on: none
  - Expected outcome: `show`, `diff`, and `Selecting a run` in `docs/cli.md` match `src/pubrun/__main__.py`, `src/pubrun/status.py::find_run`, and `src/pubrun/analysis/diff.py`.
  - Execution state: pending

- [ ] E-02 Add a shared "Standard run filters" subsection to `docs/cli.md` and reference it from the commands that omit it (with no em or en dashes in added or edited lines):
  - Add a `### Standard run filters` subsection directly after `### Selecting a run`. It documents `-f/--filter`, `-F/--not-filter`, `-s/--status`, `-S/--not-status`, `--older-than`, `--exit-code`, and `-n/--limit`. It states that `-n/--limit` exists only on `clean`, `combined`, `methods`, `show`/`report`, and `status`, and not on `inspect`, `diff`, `rerun`, or `res`/`cpu`/`mem` (`src/pubrun/__main__.py::_add_run_filter_args` `include_limit`). A new heading is allowed; the heading invariant above covers only existing headings.
  - Add the filters (and `-n` where accepted) to the synopses of `status`, `clean`, `combined`, and `rerun`, each pointing to the new subsection. `show`, `methods`, `inspect`, `diff`, and `res` already document them.
  - Change the `clean --older-than 7d --yes` example comment to say it deletes every non-running run older than 7 days. Without `--status`, `clean` selects completed, failed, interrupted, broken pipe, crashed, and ghost runs (`src/pubrun/status.py::clean_runs`).
  - Depends on: E-01
  - Expected outcome: Every command that accepts the standard run filters documents them, `-n` appears only where the parser accepts it, and the `clean` example comment matches `clean_runs`.
  - Execution state: pending

- [ ] E-06 Fix the global CLI behavior sections of `docs/cli.md` (with no em or en dashes in added or edited lines):
  - **`### Output conventions`**: replace the claim that all color is suppressed when output is not a terminal and that colors are never dimmed. State that the status-line prefixes (`src/pubrun/report/output.py::_use_color`), `self-check`, and `inspect` drop color when output is not a terminal, while `show`, `status`, `res`/`cpu`/`mem`, and `diff` check only `NO_COLOR` and `--no-color`, and parts of the `status` summary, `show` report, and `diff` output use dim text (`src/pubrun/status.py::_render_summary`, `src/pubrun/report/diagnostics.py::print_report`, `src/pubrun/analysis/render.py::_render_inline`). Advise `--no-color` or `NO_COLOR=1` when piping those commands.
  - **Global `--no-color`**: document that it is accepted in any position, and that after `pubrun run` it is passed through to the child command instead of being consumed (`src/pubrun/__main__.py::_preprocess_argv`).
  - **Help and shorthand forms**: document `pubrun help [CMD]`, `pubrun <CMD> help`, the selector-first form `pubrun 1 cpu` (rewritten to `pubrun cpu 1`), and bare `pubrun`, which prints help plus the number of runs found.
  - **`### \`--info\``**: replace the description with what `_show_info` prints: an import-mode block (active mode, its behavior flags, and any `PUBRUN_IMPORT_MODE` override), then invocation details and hardware as JSON. Point to `--version` and `pubrun show config` for the version and configuration.
  - **`### Exit Codes`**: add rows for `pubrun run`: the child's exit code is returned; a child killed by signal N returns `128+N`; a command that cannot be executed returns `127`; Ctrl+C returns `130`. State that `pubrun bench` returns the benchmark harness's nonzero exit code (it has no `127`, `128+N`, or `130` mapping).
  - Depends on: E-02
  - Expected outcome: The output, flag, help, `--info`, and exit-code statements in `docs/cli.md` match `src/pubrun/__main__.py` and `src/pubrun/report/output.py`.
  - Execution state: pending

- [ ] E-07 Fix per-command omissions in `docs/cli.md` (with no em or en dashes in added or edited lines):
  - **`status`**: add `broken pipe` to the classification list in the intro paragraph. State that `pubrun status` closes out a crashed run that still has a `.pubrun.lock` file: it writes `manifest.json` and removes the lock (`src/pubrun/status.py::close_out_crashed_run`), so the command can modify run directories. State that `status --utc` prints `YYYY-MM-DD HH:MM` with a trailing `Z`.
  - **`show`**: state that `show --utc` keeps the `YYYY-MM-DD HH:MM:SS` form without a `Z` suffix (`src/pubrun/report/diagnostics.py::_format_report_timestamp`).
  - **`inspect` parent snapshots**: add `host` to the list of sections a `meta_ref` parent can fill (`src/pubrun/report/utils.py::HYDRABLE_SECTIONS`).
  - **`methods`**: replace "A very large or divergent set" with the actual triggers: the stderr note appears when more than 25 runs are aggregated (`_METHODS_LARGE_SET = 25`) or when at least one matching run had an unreadable manifest and was skipped.
  - **`ui`**: use the exact tab labels `Run Details`, `Console Logs`, `Resources`, `Semantic Diff`, `Actions & Citations`, and `TUI Settings` (`src/pubrun/tui/app.py`).
  - Depends on: none
  - Expected outcome: The `status`, `show`, `inspect`, `methods`, and `ui` sections of `docs/cli.md` match the cited code.
  - Execution state: pending

### Task group 2: Fix `docs/configuration.md` structure, accuracy, and environment variables

- [ ] E-03 Fix high-severity structural and behavioral errors in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Repair the malformed `[diff]` table: change the header to `| Key | Type | Default | Description |` and give every row four cells, so the `export_format`, `wrap`, and `max_string_length` descriptions render. Defaults: `ignore_basic`, `ignore_standard` "see `default.toml`"; `ignore_deep` `[]`; `show_same` `false`; `export_format` `"txt"`; `wrap` `true`; `max_string_length` `300` (`src/pubrun/resources/default.toml` `[diff]`).
  - Fix the `ignore_standard` bullet in the `[diff]` prose: at `--standard`, `subprocesses` is summarized (count and command identities), while `packages` is compared per package name at every depth that shows it (`src/pubrun/analysis/diff.py` flattens `packages.{name}` and summarizes only `subprocesses` below `--deep`).
  - Fix `[capture.resources].scope`: `scope = "tree"` adds tree RSS on Linux and macOS (`peak_tree_rss_bytes`, `end_tree_rss_bytes`, and `tree_rss_bytes` per sample) and tree CPU on Linux only (`peak_tree_cpu_percent`, and `tree_cpu_percent` per sample). Main-process CPU counts only the main process's own user and system time and excludes children (`src/pubrun/capture/resources.py::_poll_cpu`). Windows records no tree values.
  - Fix `[methods].format`: it sets the format of the `methods.md` or `methods.tex` file written when a run finalizes (`src/pubrun/writer.py::ArtifactWriter.write_artifacts`). The `pubrun methods` command does not read it and defaults to `markdown` unless `--format latex` is passed (`methods_parser` `default="markdown"`).
  - Depends on: none
  - Expected outcome: `[diff]`, `[capture.resources].scope`, and `[methods].format` in `docs/configuration.md` render with consistent table widths and match `resources.py`, `diff.py`, `writer.py`, and `__main__.py`.
  - Execution state: pending

- [ ] E-04 Mark inert configuration keys in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Mark these keys as reserved and currently without effect: `[imports].record_provenance`, `provenance_depth`, `provenance_path_mode`, `max_requests`, `[capture.packages].depth`, `[capture.subprocesses].depth`, `[capture.hardware].capture_gpu_fp_precision`, `capture_cpu_clock_speed`, `capture_cpu_fp_precision`, and `[capture.determinism].depth`. No code under `src/pubrun/` reads them.
  - For the `[imports]` provenance keys, state what happens instead: the import-mode request records the caller's file name exactly as Python reports it (often an absolute path), its line number, and its function, regardless of `provenance_path_mode` or `record_provenance` (`src/pubrun/_bootstrap.py::_get_caller_info`), and at most 50 requests are kept (`_max_requests` is hard-coded to `50`).
  - Point `[capture.packages]` readers to `mode` and `[capture.subprocesses]` readers to `enabled` as the keys that control those sections.
  - Change `capture_gpu_clock_speed` to say it adds `clocks.max.sm` to the `nvidia-smi` query (`src/pubrun/capture/hardware.py`); it does not use NVML.
  - Depends on: E-03
  - Expected outcome: Every key listed above is marked reserved in `docs/configuration.md`, the provenance keys state the actual recording behavior, and `capture_gpu_clock_speed` names `nvidia-smi`.
  - Execution state: pending

- [ ] E-08 Fix missing and misleading settings and quick-start examples in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - **`[core]`**: add a `meta_ref` row (string path to a parent `meta.json`; also set by `PUBRUN_META_REF`; no default). Change the shortcut note after the `[capture.*]` example to list the four keys `pubrun.start()` flattens into `[core]` (`profile`, `output_dir`, `auto_start`, `meta_ref`; `src/pubrun/config.py::_CORE_SHORTCUTS`) and to say `artifact_durability` must be passed as `core={"artifact_durability": ...}`.
  - **`[capture.environment].mode`**: add `"off"` (section suppressed). State that `"filtered"`, `"full"`, and `"allowlist"` all pass values through the secret redaction controlled by `[redaction].env_enabled`, so `"full"` and `"filtered"` currently produce the same values (`src/pubrun/capture/environment.py::get_environment`, `src/pubrun/capture/redaction.py::redact_env_vars`). Remove "raw dump (unsafe)".
  - **`[console]`**: state that `jupyter_mode` and `non_tty_mode` apply only when the base capture mode is not `"off"`: `capture_mode` is not `"off"`, or `import pubrun.full` forces the base to `"standard"` (`src/pubrun/capture/console.py::resolve_console_mode`).
  - **`[capture.signals]`**: add `SIGPIPE` to the handled signal list (`src/pubrun/capture/signals.py::_TARGET_SIGNALS`).
  - **`[events].on_inactive_annotate`**: state that the policy applies to every call made without an active run: `annotate()`, `phase()`, `report()`, `artifact()`, `register_file()`, `register_input()`, and `register_output()` (`src/pubrun/core.py::_handle_inactive` callers).
  - **`[capture.resources].system_metrics`**: add `io_counters` (Linux only; cumulative bytes from `/proc/self/io`) to the list of added manifest fields.
  - **`[report]`**: change the intro to say these keys govern `meta_ref` hydration in every command that hydrates a manifest: `show`/`report`, `methods`, `inspect`, `rerun --preflight`, `diff`, `res`/`cpu`/`mem`, `ui`, and the `pubrun.diff()` API.
  - **Quick start**: in the precedence table, replace `pubrun.start(profile="deep")` with `pubrun.start(output_dir="./my_runs")` (`profile` is deprecated and inert). Under `### Viewing the Default Configuration`, replace `pubrun --show-config` with `pubrun show default config`. Leave the `--create-config` examples unchanged; that flag is not deprecated.
  - Depends on: E-04
  - Expected outcome: The `[core]`, `[capture.environment]`, `[console]`, `[capture.signals]`, `[events]`, `[capture.resources]`, and `[report]` sections and the quick-start examples match the cited code and use no deprecated example.
  - Execution state: pending

- [ ] E-05 Fix the Environment Variables table in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Pending plan `87qr8h` (Set `aqb2bu`, graduated from backlog item `aqb2bu`) writes the same two rows. Use its text so both plans converge on identical lines in any order. If the table already contains a `PUBRUN_RUN_MODE_OVERRIDE` row, `87qr8h` has executed: leave that row and the `PUBRUN_IMPORT_MODE` row unchanged. Otherwise, replace the `PUBRUN_IMPORT_MODE` row with the two rows given verbatim in `87qr8h` `## Proposed changes` item 3, `PUBRUN_RUN_MODE_OVERRIDE` first. Do not reword them. Together they state the order `PUBRUN_RUN_MODE_OVERRIDE`, then in-code `import pubrun.<mode>`, then `PUBRUN_IMPORT_MODE`, then `PUBRUN_AUTO_START`, then config files, then `"auto"` (`src/pubrun/_bootstrap.py::select_mode`, `src/pubrun/_config_boot.py::resolve_import_mode`).
  - Append rows for `PUBRUN_DEBUG` (any non-empty value shows `[DEBUG]` lines; `src/pubrun/report/output.py::debug_enabled`) and `NO_COLOR` (any non-empty value disables ANSI color; `--no-color` sets it) after the last existing row.
  - Depends on: E-08
  - Expected outcome: The Environment Variables table contains `PUBRUN_RUN_MODE_OVERRIDE` before `PUBRUN_IMPORT_MODE` with the `87qr8h` text, no "Takes highest precedence" claim on `PUBRUN_IMPORT_MODE`, and rows for `PUBRUN_DEBUG` and `NO_COLOR`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`docs/cli.md`, `docs/configuration.md`).
- `src/pubrun/__main__.py::_add_run_filter_args` attaches standard filter flags with `include_limit=True` on `clean`, `combined`, `show`, `status`, `methods`, and `include_limit=False` on `rerun`, `inspect`, `diff`, `res`/`cpu`/`mem`.
- `src/pubrun/config.py::_CORE_SHORTCUTS` is `{"profile", "output_dir", "auto_start", "meta_ref"}`.
- `src/pubrun/_bootstrap.py::select_mode` reads `PUBRUN_RUN_MODE_OVERRIDE` above explicit `import pubrun.<mode>` and `PUBRUN_IMPORT_MODE`.
- Backlog item `aqb2bu` is `graduated` into pending plan `87qr8h` (Set `aqb2bu`, `- Status: to-review`), whose Scope-Paths include `docs/configuration.md` and whose `## Proposed changes` item 3 gives the exact `PUBRUN_RUN_MODE_OVERRIDE` and `PUBRUN_IMPORT_MODE` rows for the Environment Variables table. E-05 reuses that text verbatim so the two plans produce identical lines whichever executes first.
- Twenty Markdown headings in `docs/cli.md` and `docs/configuration.md` contain an em dash, and cross-file links depend on their anchors (`docs/configuration.md`, `docs/api.md`, `docs/hpc.md`, `docs/performance.md`). The plan therefore leaves every existing heading line unchanged.
- No test under `tests/` or `.github/scripts/` reads `docs/cli.md` or `docs/configuration.md` (`grep -rln "cli\.md\|configuration\.md" tests/ .github/scripts/` exits `1`).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| C-01 | High | Low | Operator / Novice | `docs/cli.md` `show` vs `src/pubrun/__main__.py` `show_parser` & `report_parser` | Documents non-existent `[RUN_DIR ...]` multi-run syntax, omits `logs`/`env`/`packages` section extracts, and overstates `report` alias parity. |
| C-02 | High | Low | Operator | `docs/configuration.md` `[capture.resources].scope` vs `src/pubrun/capture/resources.py::_poll_cpu` & tree CPU | Falsely says `scope` affects RSS only and that main-process CPU includes reaped children; contradicts `docs/cli.md`. |
| C-03 | High | Low | Operator / Novice | `docs/configuration.md` `[methods].format` vs `src/pubrun/__main__.py::main` (`methods_parser`) & `src/pubrun/writer.py::ArtifactWriter.write_artifacts` | Claims `[methods].format` sets default for `pubrun methods` CLI, which actually hardcodes `default="markdown"`. |
| C-04 | High | Low | Novice / Operator | `docs/configuration.md` `[diff]` table | 3-column header with 4-column rows drops descriptions of `export_format`, `wrap`, and `max_string_length`. |
| C-05 | High | Low | Operator | `docs/configuration.md` `[imports]`, `[capture.packages]`, `[capture.subprocesses]`, `[capture.hardware]`, `[capture.determinism]` vs `src/pubrun/` | Multiple inert/unimplemented keys documented as active; `capture_gpu_clock_speed` misattributed to NVML instead of `nvidia-smi`. |
| C-06 | High | Low | Operator / Novice | `docs/configuration.md` Environment Variables table vs `src/pubrun/_bootstrap.py::select_mode` & `src/pubrun/report/output.py` | `PUBRUN_IMPORT_MODE` falsely claims highest precedence; `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_DEBUG`, and `NO_COLOR` omitted. |
| C-07 | Medium | Low | Operator | `docs/cli.md` `diff` & `docs/configuration.md` `[diff]` vs `src/pubrun/resources/default.toml` & `src/pubrun/analysis/diff.py` | `--basic` hides `packages`; `--standard` summarizes only `subprocesses`; `diff` accepts 0, 1, or 2 args. |
| C-08 | Medium | Low | Novice / Operator | `docs/cli.md` `status`, `clean`, `show`, `combined`, `rerun` vs `src/pubrun/__main__.py::_add_run_filter_args` | Standard run-filter flags omitted from command references; `clean --older-than 7d` comment inaccurate. |
| C-09 | Medium | Low | Novice / Operator | `docs/cli.md` `Selecting a run` vs `src/pubrun/status.py::find_run` | Falsely claims `status` accepts arbitrary directory paths and omits `combined`. |
| C-10 | Medium | Low | Operator / Novice | `docs/configuration.md` `[capture.environment]`, `[core]`, `[console].jupyter_mode`, quick-start vs `src/pubrun/` | Omits `environment.mode = "off"`, misstates `"full"` redaction, omits `[core].meta_ref`, overstates `_CORE_SHORTCUTS`, omits `jupyter_mode` precondition, recommends deprecated `--show-config`/`profile="deep"`. |
| C-11 | Medium | Low | Operator | `docs/cli.md` Output Conventions & `--info` vs `src/pubrun/report/diagnostics.py`, `status.py`, `render.py`, `__main__.py::_show_info` | Overpromises non-TTY color suppression and no-DIM across all commands; misstates `--info` output. |
| C-12 | Low | Low | Operator / Novice | `docs/cli.md` & `docs/configuration.md` minor omissions | Omits `host` in `meta_ref`, `SIGPIPE`, `broken pipe`, `phase()`/`io_counters`/`[report]` breadth, `--no-color`, `help` forms, `run`/`bench` exit codes, `status` closeout side effect, `methods --all` trigger, `show --utc` format, and TUI tab labels. |

## Proposed changes (ordered, validatable)

1. Fix `docs/cli.md` `show`/`report`, `diff`, and `Selecting a run` (E-01; Remediation Risk: Low).
2. Add "Standard run filters" to `docs/cli.md` and reference it from `status`, `clean`, `combined`, and `rerun`; fix the `clean` example comment (E-02; Remediation Risk: Low).
3. Fix the global CLI behavior sections of `docs/cli.md`: output conventions, `--no-color`, help forms, `--info`, and exit codes (E-06; Remediation Risk: Low).
4. Fix per-command omissions in `docs/cli.md`: `status`, `show --utc`, `inspect` parent sections, `methods --all`, and `ui` tab labels (E-07; Remediation Risk: Low).
5. Repair the `[diff]` table and fix `[capture.resources].scope` and `[methods].format` in `docs/configuration.md` (E-03; Remediation Risk: Low).
6. Mark inert configuration keys in `docs/configuration.md` (E-04; Remediation Risk: Low).
7. Fix `[core]`, `[capture.environment]`, `[console]`, `[capture.signals]`, `[events]`, `[capture.resources].system_metrics`, `[report]`, and quick-start examples in `docs/configuration.md` (E-08; Remediation Risk: Low).
8. Fix the Environment Variables table in `docs/configuration.md`, converging with plan `87qr8h` (E-05; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Wiring `pubrun methods` CLI to read `[methods].format` and changing non-TTY color/DIM rendering in `show`/`status`/`res`/`diff` are runtime behavior changes deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality).
  - Carrier-Declined: Runtime CLI changes outside documentation-only scope; recorded in orchestrator `86cd17`.

## Scope check

- Over-scope: none. Only `docs/cli.md` and `docs/configuration.md` are modified.
- Under-scope: none after review. Review added the other callers of the `on_inactive_annotate` policy, the provenance keys' actual recording behavior, the `report` alias limits, and `diff` ignoring extra arguments.
- No other plan in Set `doc-audit` declares either path. Pending plan `87qr8h` (Set `aqb2bu`) also declares `docs/configuration.md` and edits the same two Environment Variables rows; E-05 uses its exact text, so the edits converge and the runner's merge-and-revalidate gate sees identical lines.
- Diagram (technical-writing requirement 12): not added. The steps are independent edits to sections of two reference files, with no entity relationships, branches, loops, or lifecycle to depict.

## Required tests / validation

- Diff inspection of `docs/cli.md` and `docs/configuration.md`.
- Dash check. For each edited file `<f>`, run the command below. It must print nothing and report `exit=1` (grep found no em or en dash on an added line):

  ```sh
  git diff -U0 -- <f> | grep '^+' | grep -v '^+++' | grep -nP '[\x{2013}\x{2014}]'; echo "exit=$?"
  ```

- Heading check. The command below must print nothing and report `exit=1` (no heading line was added, removed, or changed except the new `### Standard run filters`):

  ```sh
  git diff -U0 -- docs/cli.md docs/configuration.md | grep -E '^[-+]#{1,6} ' | grep -v '^+### Standard run filters$'; echo "exit=$?"
  ```

- Table check. The command below must print `mismatched=0`. It counts the cells of every Markdown table row outside code fences, ignoring pipes inside backticks, and compares each row with its header. Before execution it reports `mismatched=3` (`docs/configuration.md` `[diff]` rows `export_format`, `wrap`, and `max_string_length`):

  ```sh
  python3 - docs/cli.md docs/configuration.md <<'PY'
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

- Link and anchor check. The command below must print `broken=0`. It checks every relative link in `README.md` and `docs/*.md`, including cross-file `#anchor` links into the two edited files. It reports `broken=0` before execution:

  ```sh
  python3 - README.md docs/*.md <<'PY'
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

- `python3 scripts/sanitize_paths.py --check --all` exits 0.
- No test reads either file, so no test command is required.

## Spec / documentation sync

- Pure documentation synchronization with live code; no runtime behavior changes. No spec governs these two files. The matching drift in other documents is owned by sibling plans: `wjsccu` (`docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`), `dd7noz` (`docs/api.md`, `docs/manifest.md`, `docs/architecture.md`), `0cjiv5` (`README.md`), and `77pdvl` (`CHANGELOG.md`). Plan `87qr8h` (Set `aqb2bu`) owns the same `PUBRUN_RUN_MODE_OVERRIDE` rows in `docs/functional_spec.md` and `docs/configuration.md`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for `### Selecting a run` (`combined` in the command list, the name-substring form, and the `status`/`combined` path restriction), `diff` (synopsis `pubrun diff [RUN_DIR_A [RUN_DIR_B]] [OPTIONS]`, the 0, 1, and 2 argument rules, extra arguments ignored, `packages` absent from the `--basic` shown list), and `show` (new synopsis, `show config` forms, `logs`/`env`/`packages` extracts, the `report` alias limits). Pasted `grep -n "Pass multiple directories" docs/cli.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for the new `### Standard run filters` subsection (all seven flags, and the `-n` commands listed as `clean`, `combined`, `methods`, `show`/`report`, `status`), the `status`, `clean`, `combined`, and `rerun` synopses, and the `clean` example comment. Pasted `grep -n "delete completed runs" docs/cli.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks for the `[diff]` table and prose, `[capture.resources].scope`, and `[methods].format`. Pasted table check output `mismatched=0`. Pasted `grep -n "already-reaped" docs/configuration.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks showing a reserved marker on each of the ten keys E-04 lists, the caller-recording and 50-request statement for `[imports]`, and `nvidia-smi` for `capture_gpu_clock_speed`. Pasted `grep -n "requires NVML" docs/configuration.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunk for `## Environment Variables` showing the `PUBRUN_RUN_MODE_OVERRIDE` row before the `PUBRUN_IMPORT_MODE` row and the `PUBRUN_DEBUG` and `NO_COLOR` rows; or, if `87qr8h` executed first, the hunk with only the two appended rows plus pasted `grep -n "PUBRUN_RUN_MODE_OVERRIDE" docs/configuration.md` output. Pasted output of the command below showing `same=2` (both rows match `87qr8h` item 3 verbatim). Pasted `grep -n "Takes highest precedence" docs/configuration.md; echo "exit=$?"` showing `exit=1`. Pasted dash check output `exit=1` for both files, heading check output `exit=1`, link check output `broken=0`, and `python3 scripts/sanitize_paths.py --check --all; echo "exit=$?"` showing `exit=0`.

    ```sh
    python3 - <<'PY'
    import glob, pathlib
    src = pathlib.Path(glob.glob(".aw/records/plans/*/20261125-aqb2bu-01-87qr8h-*.ipd.md")[0]).read_text(encoding="utf-8")
    item3 = src[src.index("3. **`docs/configuration.md`, `## Environment Variables` table"):]
    want = [l.strip() for l in item3.splitlines() if l.strip().startswith(("| `PUBRUN_RUN_MODE_OVERRIDE`", "| `PUBRUN_IMPORT_MODE`"))][:2]
    have = {l.strip() for l in pathlib.Path("docs/configuration.md").read_text(encoding="utf-8").splitlines()}
    print("same=%d" % sum(w in have for w in want))
    PY
    ```

  - Observed evidence:
  - Result: pending

- [ ] V-06 validates E-06
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for `### Output conventions` (non-TTY scope and dim-text exceptions), `--no-color` placement and `pubrun run` passthrough, the help and shorthand forms, `### \`--info\``, and `### Exit Codes` (`127`, `128+N`, `130`, and the `bench` statement). Pasted output of `python3 -m pubrun run -- ./nonexistent-cmd-xyz; echo "rc=$?"` showing `rc=127` and `python3 -m pubrun run -- sh -c 'kill -TERM $$'; echo "rc=$?"` showing `rc=143` (128+15), produced by existing code path `src/pubrun/__main__.py::main` (`run` branch).
  - Observed evidence:
  - Result: pending

- [ ] V-07 validates E-07
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for `status` (`broken pipe` in the intro, crashed-run close-out side effect, `--utc` with `Z`), `show --utc` without `Z`, `host` in the `inspect` parent-snapshot section list, the `methods --all` triggers (more than 25 runs, or skipped unreadable manifests), and the six `ui` tab labels. Pasted `grep -n "or divergent set" docs/cli.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
  - Result: pending

- [ ] V-08 validates E-08
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks for the `[core].meta_ref` row and four-key shortcut note, `[capture.environment].mode` (`"off"` added, redaction statement), the `[console]` precondition, `SIGPIPE`, all seven `on_inactive_annotate` functions, `io_counters`, the `[report]` intro, and the quick-start examples. Pasted `grep -nE 'profile="deep"|pubrun --show-config|raw dump' docs/configuration.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`). No blocking open questions exist.
2. Scope declaration: `- Scope-Paths:` declares the two paths this plan changes. If an out-of-scope edit proves necessary, make it and justify it at finalize (`--scope-reason <path>=<why>`); acknowledge any declared path left unmodified (`--scope-ack`).
3. Validation honesty: run every command in `## Required tests / validation` after the final edit and paste the actual output into each `V-*` item. Never claim a check passed without pasting its output.
4. Commit discipline: commit through `aw commit pqcx6o -- docs/cli.md docs/configuration.md`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: the plan must reach `executed/` through `aw ipd finalize pqcx6o`, never a hand-run `git mv`. When a runner (`aw oc run` or `aw agy run`) drives execution, the runner finalizes; otherwise the executor runs it. Finalize only once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
