# IPD: Fix CLI and configuration reference inaccuracies and drift

- Date: 2026-11-25
- Kind: child
- Concern: `docs/cli.md` and `docs/configuration.md` contain high-impact inaccuracies including non-existent `pubrun show` multi-directory syntax, a malformed GFM table dropping config descriptions, contradictory `[capture.resources].scope` claims, inert config keys documented as active, and a false `PUBRUN_IMPORT_MODE` precedence claim.
- Scope: `docs/cli.md` and `docs/configuration.md`.
- Scope-Paths: docs/cli.md, docs/configuration.md
- Item-Dependencies: none
- Status: executed
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

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 executed (Antigravity): Verified in run-20261126T014957Z-3020938 (attempt 1); integrated after committing approved status [finalized WITHOUT a begin receipt (aw ipd begin was skipped); baseline c8db82c245c7; reason: Integrated verified lane aw/lane/pqcx6o from run-20261126T014957Z-3020938 after resolving dirty-tree approval block]
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

- [x] E-01 Fix `show`/`report`, `diff`, and `Selecting a run` inaccuracies in `docs/cli.md` (with no em or en dashes in added or edited lines):
  - **`show` / `report`** (`### \`show\``): change the synopsis to `pubrun show [RUN_DIR] [logs|env|packages] [--basic|--standard|--deep] [--utc] [run filters] [-n N]`, and add the three `show config` forms (`show config`, `show run config [<id>]`, `show default config`) as a second synopsis line. Delete the bullet "Pass multiple directories to evaluate them sequentially." The existing filter bullet already explains multi-run display, so state there that `RUN_DIR` must be omitted for filters or `-n` to select several runs (`src/pubrun/__main__.py::main` iterates `filter_runs` results only when `run_dir` is empty). Document the `logs`, `env`, and `packages` section extracts (`src/pubrun/report/diagnostics.py::SHOW_SECTIONS`), including the shifted form `pubrun show env`, where a bare section name in the `RUN_DIR` position is treated as the section. Rewrite the alias line: hidden alias `report` accepts the same depth, `--utc`, filter, and `-n` flags but has no `--all` flag and no third positional, so `report run config <id>` is not accepted (`report_parser` defines only `run_dir` and `section`).
  - **`diff`** (`### \`diff\``): change the synopsis to `pubrun diff [RUN_DIR_A [RUN_DIR_B]] [OPTIONS]` and document the argument count: none compares the two most recent runs (matching the run filters when given); one compares that run with the most recent other run; two compares them; arguments after the second are ignored (`run_dirs` is `nargs="*"` and only `run_dirs[0]` and `run_dirs[1]` are read). In the `--basic` row, remove `packages` from the shown list and replace "packages-as-list" with "packages" in the hidden list (`default.toml` `[diff].ignore_basic` contains `"packages"`).
  - **`Selecting a run`** (`### Selecting a run`): add `combined` to the command list. State that `status` and `combined` accept only a recency index, a run-id prefix, or a unique substring of the run directory name, searched within `--dir` or the configured output directory (`src/pubrun/status.py::find_run`), and not an arbitrary path or a `manifest.json` path. State that `show`/`report`, `res`/`cpu`/`mem`, `methods`, `inspect`, `rerun`, and `diff` also accept a directory or `manifest.json` path (`src/pubrun/__main__.py::_get_manifest_path` falls back to `Path(run_dir)`). Add the directory-name substring form to the form table.
  - Depends on: none
  - Expected outcome: `show`, `diff`, and `Selecting a run` in `docs/cli.md` match `src/pubrun/__main__.py`, `src/pubrun/status.py::find_run`, and `src/pubrun/analysis/diff.py`.
  - Execution state: performed

- [x] E-02 Add a shared "Standard run filters" subsection to `docs/cli.md` and reference it from the commands that omit it (with no em or en dashes in added or edited lines):
  - Add a `### Standard run filters` subsection directly after `### Selecting a run`. It documents `-f/--filter`, `-F/--not-filter`, `-s/--status`, `-S/--not-status`, `--older-than`, `--exit-code`, and `-n/--limit`. It states that `-n/--limit` exists only on `clean`, `combined`, `methods`, `show`/`report`, and `status`, and not on `inspect`, `diff`, `rerun`, or `res`/`cpu`/`mem` (`src/pubrun/__main__.py::_add_run_filter_args` `include_limit`). A new heading is allowed; the heading invariant above covers only existing headings.
  - Add the filters (and `-n` where accepted) to the synopses of `status`, `clean`, `combined`, and `rerun`, each pointing to the new subsection. `show`, `methods`, `inspect`, `diff`, and `res` already document them.
  - Change the `clean --older-than 7d --yes` example comment to say it deletes every non-running run older than 7 days. Without `--status`, `clean` selects completed, failed, interrupted, broken pipe, crashed, and ghost runs (`src/pubrun/status.py::clean_runs`).
  - Depends on: E-01
  - Expected outcome: Every command that accepts the standard run filters documents them, `-n` appears only where the parser accepts it, and the `clean` example comment matches `clean_runs`.
  - Execution state: performed

- [x] E-06 Fix the global CLI behavior sections of `docs/cli.md` (with no em or en dashes in added or edited lines):
  - **`### Output conventions`**: replace the claim that all color is suppressed when output is not a terminal and that colors are never dimmed. State that the status-line prefixes (`src/pubrun/report/output.py::_use_color`), `self-check`, and `inspect` drop color when output is not a terminal, while `show`, `status`, `res`/`cpu`/`mem`, and `diff` check only `NO_COLOR` and `--no-color`, and parts of the `status` summary, `show` report, and `diff` output use dim text (`src/pubrun/status.py::_render_summary`, `src/pubrun/report/diagnostics.py::print_report`, `src/pubrun/analysis/render.py::_render_inline`). Advise `--no-color` or `NO_COLOR=1` when piping those commands.
  - **Global `--no-color`**: document that it is accepted in any position, and that after `pubrun run` it is passed through to the child command instead of being consumed (`src/pubrun/__main__.py::_preprocess_argv`).
  - **Help and shorthand forms**: document `pubrun help [CMD]`, `pubrun <CMD> help`, the selector-first form `pubrun 1 cpu` (rewritten to `pubrun cpu 1`), and bare `pubrun`, which prints help plus the number of runs found.
  - **`### \`--info\``**: replace the description with what `_show_info` prints: an import-mode block (active mode, its behavior flags, and any `PUBRUN_IMPORT_MODE` override), then invocation details and hardware as JSON. Point to `--version` and `pubrun show config` for the version and configuration.
  - **`### Exit Codes`**: add rows for `pubrun run`: the child's exit code is returned; a child killed by signal N returns `128+N`; a command that cannot be executed returns `127`; Ctrl+C returns `130`. State that `pubrun bench` returns the benchmark harness's nonzero exit code (it has no `127`, `128+N`, or `130` mapping).
  - Depends on: E-02
  - Expected outcome: The output, flag, help, `--info`, and exit-code statements in `docs/cli.md` match `src/pubrun/__main__.py` and `src/pubrun/report/output.py`.
  - Execution state: performed

- [x] E-07 Fix per-command omissions in `docs/cli.md` (with no em or en dashes in added or edited lines):
  - **`status`**: add `broken pipe` to the classification list in the intro paragraph. State that `pubrun status` closes out a crashed run that still has a `.pubrun.lock` file: it writes `manifest.json` and removes the lock (`src/pubrun/status.py::close_out_crashed_run`), so the command can modify run directories. State that `status --utc` prints `YYYY-MM-DD HH:MM` with a trailing `Z`.
  - **`show`**: state that `show --utc` keeps the `YYYY-MM-DD HH:MM:SS` form without a `Z` suffix (`src/pubrun/report/diagnostics.py::_format_report_timestamp`).
  - **`inspect` parent snapshots**: add `host` to the list of sections a `meta_ref` parent can fill (`src/pubrun/report/utils.py::HYDRABLE_SECTIONS`).
  - **`methods`**: replace "A very large or divergent set" with the actual triggers: the stderr note appears when more than 25 runs are aggregated (`_METHODS_LARGE_SET = 25`) or when at least one matching run had an unreadable manifest and was skipped.
  - **`ui`**: use the exact tab labels `Run Details`, `Console Logs`, `Resources`, `Semantic Diff`, `Actions & Citations`, and `TUI Settings` (`src/pubrun/tui/app.py`).
  - Depends on: none
  - Expected outcome: The `status`, `show`, `inspect`, `methods`, and `ui` sections of `docs/cli.md` match the cited code.
  - Execution state: performed

### Task group 2: Fix `docs/configuration.md` structure, accuracy, and environment variables

- [x] E-03 Fix high-severity structural and behavioral errors in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Repair the malformed `[diff]` table: change the header to `| Key | Type | Default | Description |` and give every row four cells, so the `export_format`, `wrap`, and `max_string_length` descriptions render. Defaults: `ignore_basic`, `ignore_standard` "see `default.toml`"; `ignore_deep` `[]`; `show_same` `false`; `export_format` `"txt"`; `wrap` `true`; `max_string_length` `300` (`src/pubrun/resources/default.toml` `[diff]`).
  - Fix the `ignore_standard` bullet in the `[diff]` prose: at `--standard`, `subprocesses` is summarized (count and command identities), while `packages` is compared per package name at every depth that shows it (`src/pubrun/analysis/diff.py` flattens `packages.{name}` and summarizes only `subprocesses` below `--deep`).
  - Fix `[capture.resources].scope`: `scope = "tree"` adds tree RSS on Linux and macOS (`peak_tree_rss_bytes`, `end_tree_rss_bytes`, and `tree_rss_bytes` per sample) and tree CPU on Linux only (`peak_tree_cpu_percent`, and `tree_cpu_percent` per sample). Main-process CPU counts only the main process's own user and system time and excludes children (`src/pubrun/capture/resources.py::_poll_cpu`). Windows records no tree values.
  - Fix `[methods].format`: it sets the format of the `methods.md` or `methods.tex` file written when a run finalizes (`src/pubrun/writer.py::ArtifactWriter.write_artifacts`). The `pubrun methods` command does not read it and defaults to `markdown` unless `--format latex` is passed (`methods_parser` `default="markdown"`).
  - Depends on: none
  - Expected outcome: `[diff]`, `[capture.resources].scope`, and `[methods].format` in `docs/configuration.md` render with consistent table widths and match `resources.py`, `diff.py`, `writer.py`, and `__main__.py`.
  - Execution state: performed

- [x] E-04 Mark inert configuration keys in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Mark these keys as reserved and currently without effect: `[imports].record_provenance`, `provenance_depth`, `provenance_path_mode`, `max_requests`, `[capture.packages].depth`, `[capture.subprocesses].depth`, `[capture.hardware].capture_gpu_fp_precision`, `capture_cpu_clock_speed`, `capture_cpu_fp_precision`, and `[capture.determinism].depth`. No code under `src/pubrun/` reads them.
  - For the `[imports]` provenance keys, state what happens instead: the import-mode request records the caller's file name exactly as Python reports it (often an absolute path), its line number, and its function, regardless of `provenance_path_mode` or `record_provenance` (`src/pubrun/_bootstrap.py::_get_caller_info`), and at most 50 requests are kept (`_max_requests` is hard-coded to `50`).
  - Point `[capture.packages]` readers to `mode` and `[capture.subprocesses]` readers to `enabled` as the keys that control those sections.
  - Change `capture_gpu_clock_speed` to say it adds `clocks.max.sm` to the `nvidia-smi` query (`src/pubrun/capture/hardware.py`); it does not use NVML.
  - Depends on: E-03
  - Expected outcome: Every key listed above is marked reserved in `docs/configuration.md`, the provenance keys state the actual recording behavior, and `capture_gpu_clock_speed` names `nvidia-smi`.
  - Execution state: performed

- [x] E-08 Fix missing and misleading settings and quick-start examples in `docs/configuration.md` (with no em or en dashes in added or edited lines):
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
  - Execution state: performed

- [x] E-05 Fix the Environment Variables table in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Pending plan `87qr8h` (Set `aqb2bu`, graduated from backlog item `aqb2bu`) writes the same two rows. Use its text so both plans converge on identical lines in any order. If the table already contains a `PUBRUN_RUN_MODE_OVERRIDE` row, `87qr8h` has executed: leave that row and the `PUBRUN_IMPORT_MODE` row unchanged. Otherwise, replace the `PUBRUN_IMPORT_MODE` row with the two rows given verbatim in `87qr8h` `## Proposed changes` item 3, `PUBRUN_RUN_MODE_OVERRIDE` first. Do not reword them. Together they state the order `PUBRUN_RUN_MODE_OVERRIDE`, then in-code `import pubrun.<mode>`, then `PUBRUN_IMPORT_MODE`, then `PUBRUN_AUTO_START`, then config files, then `"auto"` (`src/pubrun/_bootstrap.py::select_mode`, `src/pubrun/_config_boot.py::resolve_import_mode`).
  - Append rows for `PUBRUN_DEBUG` (any non-empty value shows `[DEBUG]` lines; `src/pubrun/report/output.py::debug_enabled`) and `NO_COLOR` (any non-empty value disables ANSI color; `--no-color` sets it) after the last existing row.
  - Depends on: E-08
  - Expected outcome: The Environment Variables table contains `PUBRUN_RUN_MODE_OVERRIDE` before `PUBRUN_IMPORT_MODE` with the `87qr8h` text, no "Takes highest precedence" claim on `PUBRUN_IMPORT_MODE`, and rows for `PUBRUN_DEBUG` and `NO_COLOR`.
  - Execution state: performed

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

- [x] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for `### Selecting a run` (`combined` in the command list, the name-substring form, and the `status`/`combined` path restriction), `diff` (synopsis `pubrun diff [RUN_DIR_A [RUN_DIR_B]] [OPTIONS]`, the 0, 1, and 2 argument rules, extra arguments ignored, `packages` absent from the `--basic` shown list), and `show` (new synopsis, `show config` forms, `logs`/`env`/`packages` extracts, the `report` alias limits). Pasted `grep -n "Pass multiple directories" docs/cli.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
    `git diff -- docs/cli.md` hunks (`Selecting a run`, `diff`, `show`):
    ```diff
     ### Selecting a run

     Every command that takes a run (`show`/`report`, `res`/`cpu`/`mem`, `methods`, `inspect`,
    -`rerun`, `diff`, `status`) accepts the run argument in three interchangeable forms:
    +`rerun`, `diff`, `status`, and `combined`) accepts run selectors from the forms below:

     | Form | Example | Meaning |
     |---|---|---|
    -| **Recency index** | `pubrun show 1` | `1` = most recent run, `2` = second most recent, … (1-based). A bare positive integer (≤ 999). |
    +| **Recency index** | `pubrun show 1` | `1` = most recent run, `2` = second most recent, and so on (1-based). A bare positive integer (<= 999). |
     | **Run id / prefix** | `pubrun show 8b9dc889` | The full run id or a unique leading prefix. |
    -| **Directory path** | `pubrun show ./runs/pubrun-…` | A run directory (or its `manifest.json`). |
    +| **Directory-name substring** | `pubrun show train-20260509` | A unique substring of the run directory name. |
    +| **Directory path** | `pubrun show ./runs/pubrun-20260509` | A run directory or its `manifest.json` path (not accepted by `status` or `combined`). |
    +
    +`status` and `combined` accept only a recency index, a run-id prefix, or a unique substring of
    +the run directory name, searched within `--dir` or the configured output directory. They do not
    +accept an arbitrary directory path or a `manifest.json` path. `show`/`report`, `res`/`cpu`/`mem`,
    +`methods`, `inspect`, `rerun`, and `diff` accept those three selector forms and also accept a
    +run directory path or a `manifest.json` path directly.
    @@ -442,14 +477,14 @@
     ```bash
    -pubrun diff RUN_DIR_A RUN_DIR_B [OPTIONS]
    +pubrun diff [RUN_DIR_A [RUN_DIR_B]] [OPTIONS]
     ```
    -| `--basic` | The user-facing, high-signal differences only: script/argv, packages, python, git, user config. Hides volatile fields and the high-volume sections (subprocesses, packages-as-list, environment, hardware, resources). A single `argv` change is reported once (not also as `command_line`/`rerun_command`, which are derived from it). |
    +| `--basic` | The user-facing, high-signal differences only: script/argv, python, git, user config. Hides volatile fields and the high-volume sections (process, hardware, resources, environment, subprocesses, packages). A single `argv` change is reported once (not also as `command_line`/`rerun_command`, which are derived from it). |
    @@ -465,9 +500,13 @@
    -When no run directories are given, `diff` compares the two most recent runs in the
    -(optionally filtered) set. If a filter matches fewer than two runs, `diff` reports a clear
    -error and exits non-zero rather than silently ignoring the filter.
    +**Run arguments:** `diff` accepts zero, one, or two run arguments:
    +- **Zero arguments:** compares the two most recent runs with a `manifest.json` (drawn from runs matching the standard run filters when given).
    +- **One argument:** compares that run with the most recent other run that has a `manifest.json` (matching the standard run filters when given).
    +- **Two arguments:** compares `RUN_DIR_A` and `RUN_DIR_B`.
    +- **More than two arguments:** arguments after the second are ignored.
    +
    +If a filter matches fewer than two runs (or no other run when one argument is given), `diff` reports a clear error and exits non-zero rather than silently ignoring the filter.
    @@ -537,18 +576,23 @@
     ```bash
    -pubrun show [RUN_DIR ...] [--basic|--standard|--deep] [--utc]
    +pubrun show [RUN_DIR] [logs|env|packages] [--basic|--standard|--deep] [--utc] [run filters] [-n N]
    +pubrun show config [--all] | show run config [<id>] [--all] | show default config
     ```
    -**Alias:** `report` (backward-compatible) — `report` accepts the same flags, including `--utc`.
    +**Alias:** `report` (hidden backward-compatible alias). `report` accepts the same depth flags (`--basic`, `--standard`, `--deep`), `--utc`, [Standard run filters](#standard-run-filters), and `-n`/`--limit`, as well as `logs`/`env`/`packages` section extracts. It does not accept `--all` and has no third positional argument, so `pubrun report run config <id>` is not accepted.
    -- Pass multiple directories to evaluate them sequentially.
    -- With no run directory, filter, or `-n`/`--limit`, `pubrun show` reports the single most recent run.
    -  Passing any run filter (`-f`, `-F`, `-s`, `-S`, `--older-than`, `--exit-code`) prints a separate
    -  report for every matching run, and `-n N` limits that to the N most recent matches.
    +- With no `RUN_DIR`, run filter, or `-n`/`--limit`, `pubrun show` reports the single most recent run.
    +  When `RUN_DIR` is omitted, passing any run filter (`-f`, `-F`, `-s`, `-S`, `--older-than`, `--exit-code`)
    +  or `-n`/`--limit` prints a separate report for every matching run (up to `N` most recent matches when
    +  `-n N` is given). `RUN_DIR` must be omitted for filters or `-n` to select several runs.
    +- **Section extracts (`logs`, `env`, `packages`):** pass `logs`, `env`, or `packages` after `RUN_DIR` to
    +  print only that section (captured console logs, environment variables, or recorded packages). A bare
    +  section name in the `RUN_DIR` position (for example `pubrun show env`) selects the most recent matching
    +  run and prints that section.
    ```
    `grep -n "Pass multiple directories" docs/cli.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for the new `### Standard run filters` subsection (all seven flags, and the `-n` commands listed as `clean`, `combined`, `methods`, `show`/`report`, `status`), the `status`, `clean`, `combined`, and `rerun` synopses, and the `clean` example comment. Pasted `grep -n "delete completed runs" docs/cli.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
    `git diff -- docs/cli.md` hunks (`Standard run filters`, `clean`, `combined`, `rerun`, `status`):
    ```diff
    +### Standard run filters
    +
    +Commands that scan or select runs share a common set of run-filter flags:
    +
    +| Flag | Description |
    +|---|---|
    +| `-f QUERY`, `--filter QUERY` | Include only runs whose script name, arguments, or run id contain `QUERY`. |
    +| `-F QUERY`, `--not-filter QUERY` | Exclude runs whose script name, arguments, or run id contain `QUERY`. |
    +| `-s STATUS`, `--status STATUS` | Include only runs with one of the comma-separated statuses (for example `completed,failed`). |
    +| `-S STATUS`, `--not-status STATUS` | Exclude runs with one of the comma-separated statuses. |
    +| `--older-than AGE` | Include only runs older than `AGE` (for example `7d`, `24h`, `30m`, `90s`, or `30` for 30 days). |
    +| `--exit-code CODE` | Include only runs whose exit code equals the integer `CODE`. |
    +| `-n N`, `--limit N` | Limit selection to the `N` most recent matching runs. |
    +
    +`-n`/`--limit` is accepted only by `clean`, `combined`, `methods`, `show`/`report`, and `status`.
    +It is not accepted by `inspect`, `diff`, `rerun`, or `res`/`cpu`/`mem`.
    @@ -377,7 +411,7 @@
    -pubrun clean [--dir PATH] [--older-than AGE] [--status STATUS] [-y|--yes] [--dry-run]
    +pubrun clean [--dir PATH] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE] [-n N] [-y|--yes] [--dry-run]
    @@ -397,7 +432,7 @@
    -pubrun clean --older-than 7d --yes        # Non-interactive: delete completed runs > 7 days
    +pubrun clean --older-than 7d --yes        # Non-interactive: delete every non-running run older than 7 days
    @@ -409,7 +444,7 @@
    -pubrun combined [RUN_ID ...] [--dir PATH] [--output FILE] [-y|--yes] [--force] [-f|--filter QUERY]
    +pubrun combined [RUN_ID ...] [--dir PATH] [--output FILE] [-y|--yes] [--force] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE] [-n N]
    @@ -604,7 +648,7 @@
    -pubrun rerun [RUN_DIR] [--preflight [--strict] [--fail-on {warn,mismatch,unknown}] [--json]]
    +pubrun rerun [RUN_DIR] [--preflight [--strict] [--fail-on {warn,mismatch,unknown}] [--json]] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE]
    @@ -758,10 +803,10 @@
    -pubrun status [RUN_ID] [--dir PATH] [-v|--verbose] [--utc]
    +pubrun status [RUN_ID] [--dir PATH] [-v|--verbose] [--utc] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE] [-n N]
    ```
    `grep -n "delete completed runs" docs/cli.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks for the `[diff]` table and prose, `[capture.resources].scope`, and `[methods].format`. Pasted table check output `mismatched=0`. Pasted `grep -n "already-reaped" docs/configuration.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
    `git diff -- docs/configuration.md` hunks (`[capture.resources].scope`, `[methods].format`, `[diff]`):
    ```diff
    -| `scope` | string | `"process"` | What RSS to measure: `"process"` (main process only) or `"tree"` (sum resident memory across the whole process tree — parent plus all descendant processes). Tree mode is useful for multiprocessing/Dask/Ray workloads where the main process is a thin orchestrator. **Affects memory (RSS) only** — CPU is always measured for the current process (via `os.times()`, which includes already-reaped children). Tree RSS is captured on **Linux and macOS**; Windows falls back to process scope. When enabled, adds `peak_tree_rss_bytes`/`end_tree_rss_bytes` to the manifest and `tree_rss_bytes` to each `resource_sample` event. |
    +| `scope` | string | `"process"` | What process scope to measure: `"process"` (main process only) or `"tree"` (main process plus all descendant processes). Tree mode is useful for multiprocessing, Dask, and Ray workloads where the main process is a thin orchestrator. On Linux and macOS, `scope = "tree"` adds tree RSS (`peak_tree_rss_bytes` and `end_tree_rss_bytes` in the manifest, and `tree_rss_bytes` per `resource_sample` event). On Linux only, `scope = "tree"` also adds tree CPU (`peak_tree_cpu_percent` in the manifest and `tree_cpu_percent` per `resource_sample` event). Main-process CPU counts only the main process's own user and system time and excludes children. Windows records no tree values. |
    @@ -321,7 +323,7 @@
    -| `format` | string | `"markdown"` | Default output format for `pubrun methods`: `"markdown"` or `"latex"`. |
    +| `format` | string | `"markdown"` | Output format for the `methods.md` or `methods.tex` file written when a run finalizes (`"markdown"` or `"latex"`). The `pubrun methods` CLI command does not read this key and defaults to `markdown` unless `--format latex` is passed. |
    @@ -332,25 +334,26 @@
    -- **`ignore_standard`** — hides volatile / always-different fields: timestamps (`*_utc`), run
    -  ids, PIDs, per-run absolute paths (`filesystem.*.path`/`mount_point`, `capture.run_dir`),
    -  and import-request timestamps. Keeps meaningful signals like `fstype`/`is_network`. At
    -  `--standard`, list-valued sections (subprocesses, packages) are **summarized** (counts +
    -  identities) rather than diffed element-by-element.
    +- **`ignore_standard`**: hides volatile or always-different fields, including timestamps
    +  (`*_utc`), run ids, PIDs, per-run absolute paths (`filesystem.*.path`/`mount_point`,
    +  `capture.run_dir`), and import-request timestamps, while keeping meaningful signals such as
    +  `fstype` and `is_network`. At `--standard`, `subprocesses` is **summarized** (count and
    +  command identities) rather than diffed element-by-element, while `packages` is compared per
    +  package name at every depth that shows it (`--standard` and `--deep`).
    -| Key | Type | Description |
    -|---|---|---|
    -| `ignore_basic` | list | Keys ignored at `--basic` depth (see above; the largest list). |
    -| `ignore_standard` | list | Keys ignored at `--standard` depth (see above). |
    -| `ignore_deep` | list | Keys ignored at `--deep` depth — `[]` by default. |
    -| `show_same` | bool (`false`) | Show unchanged values in diff output. |
    +| Key | Type | Default | Description |
    +|---|---|---|---|
    +| `ignore_basic` | list | see `default.toml` | Keys ignored at `--basic` depth (see above; the largest list). |
    +| `ignore_standard` | list | see `default.toml` | Keys ignored at `--standard` depth (see above). |
    +| `ignore_deep` | list | `[]` | Keys ignored at `--deep` depth. |
    +| `show_same` | bool | `false` | Show unchanged values in diff output. |
     | `export_format` | string | `"txt"` | Output format for `--export`: `"txt"` or `"json"`. |
     | `wrap` | bool | `true` | Wrap long strings instead of truncating with ellipsis. |
    -| `max_string_length` | int | `300` | Maximum characters per value before wrapping/truncation. |
    +| `max_string_length` | int | `300` | Maximum characters per value before wrapping or truncation. |
    ```
    Table check output: `mismatched=0`.
    `grep -n "already-reaped" docs/configuration.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks showing a reserved marker on each of the ten keys E-04 lists, the caller-recording and 50-request statement for `[imports]`, and `nvidia-smi` for `capture_gpu_clock_speed`. Pasted `grep -n "requires NVML" docs/configuration.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
    `git diff -- docs/configuration.md` hunks (`[imports]`, `[capture.packages]`, `[capture.subprocesses]`, `[capture.hardware]`, `[capture.determinism]`):
    ```diff
    -| `record_provenance` | bool | `true` | Record import-mode provenance (caller file, line) in the manifest. |
    -| `provenance_depth` | int | `3` | Number of external caller frames to capture for diagnostics. |
    -| `provenance_path_mode` | string | `"relative"` | How paths appear in provenance: `"absolute"`, `"relative"`, `"basename"`, or `"redacted"`. |
    -| `max_requests` | int | `50` | Maximum import-mode requests to retain in metadata. |
    +| `record_provenance` | bool | `true` | **Reserved (currently without effect).** Intended to toggle import-mode provenance recording. Regardless of this setting, `pubrun` always records the caller's file name exactly as Python reports it (often an absolute path), its line number, and its function name. |
    +| `provenance_depth` | int | `3` | **Reserved (currently without effect).** Intended to set the number of external caller frames captured for diagnostics. |
    +| `provenance_path_mode` | string | `"relative"` | **Reserved (currently without effect).** Intended to control how caller paths appear in provenance (`"absolute"`, `"relative"`, `"basename"`, or `"redacted"`). Regardless of this setting, `pubrun` records the caller's file name exactly as Python reports it (often an absolute path), its line number, and its function name. |
    +| `max_requests` | int | `50` | **Reserved (currently without effect).** Intended to configure the maximum number of import-mode requests retained in metadata. Currently, at most 50 requests are kept (hard-coded). |
    @@ -152,7 +153,7 @@
    -| `depth` | string | `"standard"` | Capture depth for this category. |
    +| `depth` | string | `"standard"` | **Reserved (currently without effect).** Use `mode` above to control package capture. |
    @@ -161,7 +162,7 @@
    -| `depth` | string | `"basic"` | Capture depth for this category. |
    +| `depth` | string | `"basic"` | **Reserved (currently without effect).** Use `enabled` above to control subprocess capture. |
    @@ -204,10 +205,10 @@
    -| `capture_gpu_clock_speed` | bool | `false` | Query GPU clock speeds (requires NVML; slow). |
    -| `capture_gpu_fp_precision` | bool | `false` | Query GPU floating-point precision support. |
    -| `capture_cpu_clock_speed` | bool | `false` | Query CPU clock speeds (reads `/proc`). |
    -| `capture_cpu_fp_precision` | bool | `false` | Query CPU floating-point precision support. |
    +| `capture_gpu_clock_speed` | bool | `false` | Add `clocks.max.sm` to the `nvidia-smi` query to record maximum GPU SM clock speeds (does not use NVML). |
    +| `capture_gpu_fp_precision` | bool | `false` | **Reserved (currently without effect).** Intended to query GPU floating-point precision support. |
    +| `capture_cpu_clock_speed` | bool | `false` | **Reserved (currently without effect).** Intended to query CPU clock speeds. |
    +| `capture_cpu_fp_precision` | bool | `false` | **Reserved (currently without effect).** Intended to query CPU floating-point precision support. |
    @@ -290,19 +292,19 @@
    -| `depth` | string | `"off"` | Track/lock pseudorandom seeds (Python `random`, numpy). Currently off by default. |
    +| `depth` | string | `"off"` | **Reserved (currently without effect).** Intended to track or lock pseudorandom seeds (Python `random`, numpy). |
    ```
    `grep -n "requires NVML" docs/configuration.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-05 validates E-05
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
    Plan `87qr8h` already executed (`.aw/records/plans/executed/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md`), so `PUBRUN_RUN_MODE_OVERRIDE` and `PUBRUN_IMPORT_MODE` were left unchanged and `PUBRUN_DEBUG` and `NO_COLOR` were appended:
    ```diff
    @@ -364,6 +367,8 @@
     | `PUBRUN_AUTO_START` | Legacy alias for import mode. `"1"`, `"true"`, `"yes"`, or `"on"` maps to `auto`; `"0"`, `"false"`, `"no"`, or `"off"` maps to `noauto` (case-insensitive). Other values are ignored. |
     | `PUBRUN_META_REF` | Path to a parent `meta.json` for HPC hydration. Child runs will reference this. |
     | `PUBRUN_IMPORT_CONFLICT` | Override `[imports].on_conflict`. Set to `"ignore"`, `"warn"`, or `"error"`. |
    +| `PUBRUN_DEBUG` | Any non-empty value shows `[DEBUG]` CLI diagnostic lines. |
    +| `NO_COLOR` | Any non-empty value disables ANSI color output across CLI commands. Passing `--no-color` sets this variable internally. |
    ```
    `grep -n "PUBRUN_RUN_MODE_OVERRIDE" docs/configuration.md`:
    `364:| `PUBRUN_RUN_MODE_OVERRIDE` | Launch-time import-mode override: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Takes precedence over explicit in-code `import pubrun.<mode>` imports, `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, and config files (`[imports].mode`, `[core].auto_start`). `pubrun run --mode` sets it alongside `PUBRUN_IMPORT_MODE` in the child process. It records `"cli:pubrun run --mode"` as manifest provenance and suppresses import-mode conflicts under `[imports].on_conflict` and `PUBRUN_IMPORT_CONFLICT`. Matching ignores case and surrounding whitespace; any other value is ignored. Consumed during the boot sequence (not in `resolve_config()`). |`
    `365:| `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Overrides `PUBRUN_AUTO_START` and config files (`[imports].mode`, `[core].auto_start`). `PUBRUN_RUN_MODE_OVERRIDE` and explicit in-code `import pubrun.<mode>` imports take precedence over it. Matching ignores case and surrounding whitespace; any other value is ignored. Consumed during the boot sequence (not in `resolve_config()`). |`
    Verbatim `87qr8h` check: `same=2`.
    `grep -n "Takes highest precedence" docs/configuration.md; echo "exit=$?"` -> `exit=1`.
    Dash check `docs/cli.md`: `exit=1`.
    Dash check `docs/configuration.md`: `exit=1`.
    Heading check: `exit=1`.
    Link check: `broken=0`.
    `python3 scripts/sanitize_paths.py --check --all; echo "exit=$?"` -> `exit=0`.
  - Result: pass

- [x] V-06 validates E-06
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for `### Output conventions` (non-TTY scope and dim-text exceptions), `--no-color` placement and `pubrun run` passthrough, the help and shorthand forms, `### \`--info\``, and `### Exit Codes` (`127`, `128+N`, `130`, and the `bench` statement). Pasted output of `python3 -m pubrun run -- ./nonexistent-cmd-xyz; echo "rc=$?"` showing `rc=127` and `python3 -m pubrun run -- sh -c 'kill -TERM $$'; echo "rc=$?"` showing `rc=143` (128+15), produced by existing code path `src/pubrun/__main__.py::main` (`run` branch).
  - Observed evidence:
    `git diff -- docs/cli.md` hunks (`Help/shorthand/--no-color`, `Output conventions`, `--info`, `Exit Codes`):
    ```diff
    +**Help, shorthand, and global flags:**
    +- `pubrun help [CMD]` and `pubrun <CMD> help` print top-level or subcommand help.
    +- Bare `pubrun` (with no subcommand or flag) prints top-level help followed by the number of runs found in the output directory.
    +- **Selector-first shorthand:** you can place a run selector (index, run-id prefix, or path) before the subcommand, for example `pubrun 1 cpu` (rewritten to `pubrun cpu 1`).
    +- **Global `--no-color`:** accepted in any position on the command line (sets `NO_COLOR=1` internally). When placed after `pubrun run`, `--no-color` is not consumed by `pubrun` and is passed through to the child command instead.
    @@ -17,21 +23,32 @@
    -Color is optional reinforcement only: the textual label is authoritative, colors are never
    -dimmed, and all color is suppressed when `NO_COLOR` is set, `--no-color` is passed, or output
    -is not a terminal. If you parse pubrun output in a script, match on the level word (e.g.
    -`WARN`), not the exact bracketing.
    +Color is optional reinforcement only, and the textual label is authoritative. The status-line
    +prefixes (`[INFO ]`, `[ OK  ]`, `[WARN ]`, `[ERROR]`, `[DEBUG]`, `[FAIL ]`), `self-check`, and
    +`inspect` disable color when `NO_COLOR` is set, `--no-color` is passed, or the output stream is
    +not a terminal. By contrast, `show`, `status`, `res`/`cpu`/`mem`, and `diff` check only
    +`NO_COLOR` and `--no-color` (not whether stdout is a terminal), and parts of the `status`
    +summary, `show` report, and `diff` output use dim text. Pass `--no-color` or set `NO_COLOR=1`
    +when piping or redirecting output from those commands. If you parse pubrun output in a script,
    +match on the level word (for example `WARN`), not the exact bracketing.
    @@ -891,7 +937,7 @@
    -Displays system capabilities, pubrun version, and environment details.
    +Prints an import-mode diagnostic block (the active mode, its behavior flags `auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, and `signal_hooks`, and any `PUBRUN_IMPORT_MODE` environment override), followed by invocation details and hardware probe output as JSON. Use `pubrun --version` for the installed version and `pubrun show config` for the resolved configuration.
    @@ -914,6 +960,12 @@
    +| child exit code | For `pubrun run`, returns the child process's exit code directly |
    +| `127` | For `pubrun run`, the child command could not be executed (not found or permission denied) |
    +| `128+N` | For `pubrun run`, the child process was terminated by signal `N` (for example `143` for `SIGTERM`, signal 15) |
    +| `130` | For `pubrun run`, interrupted by `Ctrl+C` (`KeyboardInterrupt`) |
    +
    +`pubrun bench` returns the benchmark harness's nonzero exit code directly; it does not apply the `127`, `128+N`, or `130` exit-code mappings used by `pubrun run`.
    ```
    Runtime verification (`src/pubrun/__main__.py::main`, `run` branch):
    - `python3 -m pubrun run -- ./nonexistent-cmd-xyz; echo "rc=$?"`:
      `[ERROR] Cannot execute command: [Errno 2] No such file or directory: './nonexistent-cmd-xyz'`
      `rc=127`
    - `python3 -m pubrun run -- sh -c 'kill -TERM $$'; echo "rc=$?"`:
      `rc=143`
  - Result: pass

- [x] V-07 validates E-07
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for `status` (`broken pipe` in the intro, crashed-run close-out side effect, `--utc` with `Z`), `show --utc` without `Z`, `host` in the `inspect` parent-snapshot section list, the `methods --all` triggers (more than 25 runs, or skipped unreadable manifests), and the six `ui` tab labels. Pasted `grep -n "or divergent set" docs/cli.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
    `git diff -- docs/cli.md` hunks (`inspect`, `methods`, `show`, `status`, `ui`):
    ```diff
    @@ -239,7 +273,7 @@
     **Parent snapshots (`meta_ref`):** when the manifest names a parent `meta.json`, `inspect`
     fills sections the child did not capture (hardware, process, python, packages, environment,
    -git) from the parent, in memory only; `manifest.json` is never modified. Inherited sections
    +git, host) from the parent, in memory only; `manifest.json` is never modified. Inherited sections
    @@ -520,7 +559,7 @@
    -- A very large or divergent set prints a suggestion to stderr, **clearly marked as not part of the methods section** (so it can never be pasted into a paper); it respects `NO_COLOR`.
    +- When more than 25 runs are aggregated (the built-in threshold) or when at least one matching run had an unreadable or missing manifest and was skipped, `pubrun methods --all` prints a note to stderr, **clearly marked as not part of the methods section** (so it cannot be pasted into a paper). This note respects `NO_COLOR`.
    @@ -549,2 +590,2 @@
    -- Timestamps display in **local time** by default; pass `--utc` for UTC. They are shown in a
    -  compact `YYYY-MM-DD HH:MM:SS` form.
    +- Timestamps display in **local time** by default; pass `--utc` for UTC. Both local and `--utc`
    +  timestamps use the compact `YYYY-MM-DD HH:MM:SS` form without a trailing `Z` suffix.
    @@ -758,10 +803,10 @@
    -Lists all runs in the output directory with their current status, or inspects a specific run in detail. Classifies runs as completed, failed, interrupted, running, crashed, or ghost via lock-file PID liveness checks.
    +Lists all runs in the output directory with their current status, or inspects a specific run in detail. Classifies runs as completed, failed, interrupted, broken pipe, running, crashed, or ghost via lock-file PID liveness checks. When a crashed run still has a `.pubrun.lock` file (its process is no longer alive), `pubrun status` closes it out by writing or updating `manifest.json` and removing `.pubrun.lock`, so this command can modify run directories.
    @@ -778,7 +823,8 @@
    -| `--utc` | Display timestamps in UTC (with a `Z` suffix) instead of the default local time. Timestamps are always stored as UTC epochs; this only affects display. Also available on `pubrun show`. |
    +| `--utc` | Display timestamps in UTC (`YYYY-MM-DD HH:MM` with a trailing `Z` suffix) instead of local time. Timestamps are always stored as UTC epochs; this only affects display. Also available on `pubrun show` (which omits the `Z` suffix). |
    @@ -816,7 +862,7 @@
    -Launches the terminal user interface (TUI) dashboard to browse, inspect, and manage run records interactively. Tabs include Run Details, Console Logs, **Resources** (CPU/memory usage), Semantic Diff, Actions, and Settings.
    +Launches the terminal user interface (TUI) dashboard to browse, inspect, and manage run records interactively. Tabs are `Run Details`, `Console Logs`, `Resources` (CPU/memory usage), `Semantic Diff`, `Actions & Citations`, and `TUI Settings`.
    ```
    `grep -n "or divergent set" docs/cli.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

- [x] V-08 validates E-08
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks for the `[core].meta_ref` row and four-key shortcut note, `[capture.environment].mode` (`"off"` added, redaction statement), the `[console]` precondition, `SIGPIPE`, all seven `on_inactive_annotate` functions, `io_counters`, the `[report]` intro, and the quick-start examples. Pasted `grep -nE 'profile="deep"|pubrun --show-config|raw dump' docs/configuration.md; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
    `git diff -- docs/configuration.md` hunks:
    ```diff
    @@ -12,7 +12,7 @@
    -| 1 (highest) | API overrides | `pubrun.start(profile="deep")` |
    +| 1 (highest) | API overrides | `pubrun.start(output_dir="./my_runs")` |
    @@ -38,7 +38,7 @@
    -pubrun --show-config
    +pubrun show default config
    @@ -55,6 +55,7 @@
    +| `meta_ref` | string | *(none)* | Path to a parent `meta.json` snapshot for HPC hydration. Also set by `PUBRUN_META_REF` or `pubrun.start(meta_ref=...)`. |
    @@ -104,8 +105,8 @@
    -| `non_tty_mode` | string | `"inherit"` | Override capture behavior when stdout is not a TTY (piped/redirected): `"inherit"` (use capture_mode as-is), `"off"`, or `"basic"`. |
    -| `jupyter_mode` | string | `"off"` | Override capture behavior when running inside Jupyter/IPython. Default `"off"` auto-disables capture in notebooks. Set to `"standard"` to force capture in Jupyter. |
    +| `non_tty_mode` | string | `"inherit"` | Override capture behavior when stdout is not a TTY (piped or redirected): `"inherit"` (use the base mode as-is), `"off"`, or `"basic"`. Applies only when the base capture mode is not `"off"` (that is, `capture_mode` is not `"off"`, or `import pubrun.full` forces the base mode to `"standard"`). |
    +| `jupyter_mode` | string | `"off"` | Override capture behavior when running inside Jupyter/IPython. Default `"off"` auto-disables capture in notebooks; set to `"standard"` to keep capture active in Jupyter. Applies only when the base capture mode is not `"off"` (that is, `capture_mode` is not `"off"`, or `import pubrun.full` forces the base mode to `"standard"`). |
    @@ -116,7 +117,7 @@
    -| `on_inactive_annotate` | string | `"ignore"` | Behavior when `annotate()` is called with no active run: `"ignore"`, `"warn"`, or `"error"`. |
    +| `on_inactive_annotate` | string | `"ignore"` | Behavior when an active-run API function is called with no active run: `"ignore"`, `"warn"`, or `"error"`. Applies to `annotate()`, `phase()`, `report()`, `artifact()`, `register_file()`, `register_input()`, and `register_output()`. |
    @@ -143,7 +144,7 @@
    -| `mode` | string | `"filtered"` | `"allowlist"` — only permitted vars; `"filtered"` — all vars with secret redaction; `"full"` — raw dump (unsafe). |
    +| `mode` | string | `"filtered"` | `"off"`: suppress the section (`capture_state.status = "suppressed"`); `"allowlist"`: capture only variables matching `allowlist`; `"filtered"`: capture all variables; `"full"`: capture all variables. `"filtered"`, `"full"`, and `"allowlist"` all pass values through the secret redaction controlled by `[redaction].env_enabled`, so `"full"` and `"filtered"` currently produce the same values. |
    @@ -220,1 +221,1 @@
    -| `system_metrics` | bool | `true` | Also sample **system-wide** dynamic metrics alongside per-process RSS/CPU: available memory, load average, and (Linux only) node iowait. These make post-hoc I/O / contention diagnosis possible (e.g. "was this run starved for RAM or on a busy node?"). Cheap (single `/proc` reads) and only sampled when the watcher is running (`depth != "off"`). Adds `system_memory`/`load_average`/`system_iowait_pct` to the `resources` manifest section. Note: `system_iowait_pct` is **node-wide, indicative only** (not run-scoped). Set `false` to omit. |
    +| `system_metrics` | bool | `true` | Also sample **system-wide** dynamic metrics and per-process I/O counters alongside per-process RSS/CPU: available memory, load average, and (Linux only) node iowait and cumulative I/O bytes from `/proc/self/io`. These make post-hoc I/O and contention diagnosis possible (for example whether a run was starved for RAM or on a busy node). Cheap (single `/proc` reads) and only sampled when the watcher is running (`depth != "off"`). Adds `system_memory`, `load_average`, `system_iowait_pct`, and (Linux only) `io_counters` to the `resources` manifest section. Note: `system_iowait_pct` is **node-wide, indicative only** (not run-scoped). Set `false` to omit. |
    @@ -249,9 +250,10 @@
    -The `pubrun.start(profile=..., output_dir=...)` shorthand only flattens the top-level
    -`[core]` keys; every `[capture.*]` setting must be passed as the nested dict shown
    -above.
    +`pubrun.start()` flattens only four `[core]` shortcut keys: `profile`, `output_dir`,
    +`auto_start`, and `meta_ref`. Other `[core]` keys such as `artifact_durability` must be
    +passed as `core={"artifact_durability": ...}`, and every `[capture.*]` setting must be
    +passed as the nested dict shown above.
    @@ -290,19 +292,19 @@
    -| `enabled` | bool | `true` | Install non-intrusive signal handlers (`SIGINT`, `SIGTERM`, `SIGHUP`, `SIGUSR1`, `SIGUSR2`, `SIGBREAK` where available) that record received signals and the process exit code. Handlers chain to any pre-existing handlers without disrupting the importing script. Disable to skip the `"signals"` manifest section entirely. |
    +| `enabled` | bool | `true` | Install non-intrusive signal handlers (`SIGINT`, `SIGTERM`, `SIGHUP`, `SIGPIPE`, `SIGUSR1`, `SIGUSR2`, `SIGBREAK` where available) that record received signals and the process exit code. Handlers chain to any pre-existing handlers without disrupting the importing script. Disable to skip the `"signals"` manifest section entirely. |
    -Controls for `pubrun report` and `pubrun methods` manifest hydration.
    +Controls `meta_ref` parent-snapshot hydration in every command and API that hydrates a manifest: `show`/`report`, `methods`, `inspect`, `rerun --preflight`, `diff`, `res`/`cpu`/`mem`, `ui`, and the `pubrun.diff()` API.
    ```
    `grep -nE 'profile="deep"|pubrun --show-config|raw dump' docs/configuration.md; echo "exit=$?"` -> `exit=1`.
  - Result: pass

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
