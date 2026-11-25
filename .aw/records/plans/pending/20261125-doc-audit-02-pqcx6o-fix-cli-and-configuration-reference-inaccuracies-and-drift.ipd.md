# IPD: Fix CLI and configuration reference inaccuracies and drift

- Date: 2026-11-25
- Kind: child
- Concern: `docs/cli.md` and `docs/configuration.md` contain high-impact inaccuracies including non-existent `pubrun show` multi-directory syntax, a malformed GFM table dropping config descriptions, contradictory `[capture.resources].scope` claims, inert config keys documented as active, and a false `PUBRUN_IMPORT_MODE` precedence claim.
- Scope: `docs/cli.md` and `docs/configuration.md`.
- Scope-Paths: docs/cli.md, docs/configuration.md
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix docs/cli.md show/diff/filter/selection docs and docs/configuration.md table, scope, inert keys, and env precedence
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 2
- Highest E allocated: 05
- Author: Antigravity
- Id: pqcx6o

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 5 documentation fixes (19 verified findings across `docs/cli.md` and `docs/configuration.md`)
- 2026-11-25 draft (Antigravity): created.

## Goal

Bring `docs/cli.md` and `docs/configuration.md` into exact agreement with the live CLI parser (`src/pubrun/__main__.py`), status/diagnostics/diff renderers, configuration defaults (`src/pubrun/resources/default.toml`), and environment-variable resolution (`src/pubrun/_bootstrap.py`, `src/pubrun/_config_boot.py`, `src/pubrun/config.py`).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix `docs/cli.md` accuracy and completeness

- [ ] E-01 Fix `show`/`report`, `diff`, and `Selecting a run` inaccuracies in `docs/cli.md` (with no em or en dashes in added or edited lines):
  - **`show` / `report`**: change synopsis to `pubrun show [RUN_DIR] [logs|env|packages] [--basic|--standard|--deep] [--utc] [run filters] [-n N]` (plus the `show [run|default] config` forms); remove "Pass multiple directories to evaluate them sequentially" (explain that multi-run display uses filters/`-n` with `RUN_DIR` omitted); document the `logs`, `env`, and `packages` section extracts (including shifted `pubrun show env` form); note that legacy hidden alias `report` omits `--all` and `run config <id>`.
  - **`diff`**: change synopsis to `pubrun diff [RUN_DIR_A] [RUN_DIR_B] [OPTIONS]` and document 0-, 1-, and 2-argument semantics; remove `packages` from the `--basic` "what it shows" list (`"packages"` is in `ignore_basic` in `default.toml`).
  - **`Selecting a run`**: state explicitly that `status` and `combined` resolve recency index, run-id prefix, or run-directory basename within `--dir`/`output_dir` (not arbitrary filesystem or `manifest.json` paths), while `show`/`report`, `res`/`cpu`/`mem`, `methods`, `inspect`, `rerun`, and `diff` accept arbitrary paths too; add `combined` to the command list.
  - Depends on: none
  - Expected outcome: `show`, `diff`, and `Selecting a run` in `docs/cli.md` match `src/pubrun/__main__.py` and `src/pubrun/analysis/diff.py`.
  - Execution state: pending

- [ ] E-02 Add a shared "Standard run filters" subsection and fix remaining CLI documentation omissions and nits in `docs/cli.md` (with no em or en dashes in added or edited lines):
  - Add a "Standard run filters" subsection near the top (next to "Selecting a run") documenting `-f/--filter`, `-F/--not-filter`, `-s/--status`, `-S/--not-status`, `--older-than`, `--exit-code`, and `-n/--limit` (noting which commands accept `-n/--limit` vs non-limit filters), and reference it in `status`, `clean`, `show`, `combined`, and `rerun` synopses/tables.
  - Fix `clean --older-than 7d --yes` comment (default selects all non-running statuses, not only `completed`).
  - Fix `--info` description (prints import-mode flags, invocation details, and hardware JSON; point to `--version` and `show config` for version/config).
  - Scope Output Conventions non-TTY/no-DIM statement to status-line prefixes, `self-check`, and `inspect`, advising `--no-color` or `NO_COLOR=1` when piping `show`, `status`, `res`, or `diff`.
  - Add missing details: global `--no-color` flag (including passthrough after `pubrun run`), `pubrun help [CMD]` / `<CMD> help` / `pubrun 1 cpu` shorthand / bare `pubrun`, `run` and `bench` exit-code propagation (`127`, `128+N`, `130`), `status` crashed-run closeout side effect, `host` in `meta_ref` hydrable sections, `broken pipe` in `status` intro, `methods --all` stderr note trigger (`> 25` runs or skipped unreadable manifests), `show --utc` omitting `Z` vs `status --utc`, and TUI tab names (`"Actions & Citations"` and `"TUI Settings"`).
  - Depends on: E-01
  - Expected outcome: Every documented CLI command, flag, filter, exit code, and output rule in `docs/cli.md` matches live behavior.
  - Execution state: pending

### Task group 2: Fix `docs/configuration.md` structure, accuracy, and environment variables

- [ ] E-03 Fix high-severity structural and behavioral errors in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Repair the malformed `[diff]` table by converting it to the standard 4-column `| Key | Type | Default | Description |` format so `export_format`, `wrap`, and `max_string_length` descriptions render in GFM.
  - Fix `[diff]` `--standard` prose to state that `--standard` summarizes `subprocesses` (counts and command identities) while expanding `packages` by package name.
  - Fix `[capture.resources].scope` to state that `scope = "tree"` captures tree RSS on Linux and macOS (`peak_tree_rss_bytes`, `end_tree_rss_bytes`, `tree_rss_bytes`) AND tree CPU on Linux (`peak_tree_cpu_percent`, `tree_cpu_percent`), and that main-process CPU measures only the main process's own user+system time (excluding children).
  - Fix `[methods].format` to state that it controls the format of the auto-generated `methods.md` / `methods.tex` file written at run finalization (`src/pubrun/writer.py::ArtifactWriter.write_artifacts`), while the `pubrun methods` CLI defaults to `markdown` unless `--format latex` is passed.
  - Depends on: none
  - Expected outcome: `[diff]`, `[capture.resources].scope`, and `[methods].format` in `docs/configuration.md` render cleanly and match `resources.py`, `diff.py`, `writer.py`, and `__main__.py`.
  - Execution state: pending

- [ ] E-04 Mark inert/reserved keys and fix missing/misleading settings and quick-start examples in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Mark `[imports].record_provenance`, `provenance_depth`, `provenance_path_mode`, `max_requests`, `[capture.packages].depth`, `[capture.subprocesses].depth`, `[capture.hardware].capture_gpu_fp_precision`, `capture_cpu_clock_speed`, `capture_cpu_fp_precision`, and `[capture.determinism].depth` explicitly as reserved / not yet implemented (clarifying `packages` uses `mode` and `subprocesses` uses `enabled`); correct `capture_gpu_clock_speed` to reference `nvidia-smi` rather than NVML.
  - Add `[core].meta_ref` to the `[core]` table, and update the API shortcut note to list the exact four flattened keys (`profile`, `output_dir`, `auto_start`, `meta_ref`), noting that `artifact_durability` requires `core={"artifact_durability": ...}`.
  - Update `[capture.environment].mode` to include `"off"` and clarify that redaction in `"filtered"`, `"full"`, and `"allowlist"` is governed by `[redaction].env_enabled`.
  - Clarify `[console].jupyter_mode` (and `non_tty_mode`) only take effect when `capture_mode` is not `"off"` (or under `import pubrun.full`).
  - Add `SIGPIPE` to `[capture.signals]`, mention `phase()` under `on_inactive_annotate`, add `io_counters` (Linux) under `system_metrics`, broaden `[report]` scope to all hydrating commands (`show`/`report`, `methods`, `inspect`, `rerun --preflight`, `diff`, `res`, `ui`), and replace deprecated `profile="deep"` / `pubrun --show-config` quick-start examples with active equivalents (`output_dir`, `pubrun show default config`, `pubrun init`).
  - Depends on: E-03
  - Expected outcome: Every config table and example in `docs/configuration.md` accurately distinguishes active vs reserved settings and avoids deprecated defaults.
  - Execution state: pending

- [ ] E-05 Fix the Environment Variables table in `docs/configuration.md` (with no em or en dashes in added or edited lines):
  - Correct `PUBRUN_IMPORT_MODE` (remove false "Takes highest precedence" claim) and state the exact import-mode precedence order: `PUBRUN_RUN_MODE_OVERRIDE` > in-code `import pubrun.<mode>` > `PUBRUN_IMPORT_MODE` > `PUBRUN_AUTO_START` > config files > `"auto"`.
  - Add `PUBRUN_RUN_MODE_OVERRIDE` (coordinating with open backlog `aqb2bu`), `PUBRUN_DEBUG`, and `NO_COLOR` to the Environment Variables table.
  - Depends on: E-04
  - Expected outcome: The Environment Variables table lists every active `PUBRUN_*` and `NO_COLOR` variable with truthful precedence.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`docs/cli.md`, `docs/configuration.md`).
- `src/pubrun/__main__.py::_add_run_filter_args` attaches standard filter flags with `include_limit=True` on `clean`, `combined`, `show`, `status`, `methods`, and `include_limit=False` on `rerun`, `inspect`, `diff`, `res`/`cpu`/`mem`.
- `src/pubrun/config.py::_CORE_SHORTCUTS` is `{"profile", "output_dir", "auto_start", "meta_ref"}`.
- `src/pubrun/_bootstrap.py::select_mode` reads `PUBRUN_RUN_MODE_OVERRIDE` above explicit `import pubrun.<mode>` and `PUBRUN_IMPORT_MODE`.
- Open backlog item `aqb2bu` tracks adding `PUBRUN_RUN_MODE_OVERRIDE` to `docs/configuration.md` and `docs/functional_spec.md` sections 10.2/10.3; E-05 covers the `docs/configuration.md` portion so the table is internally consistent.

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
2. Add "Standard run filters" and fix remaining CLI options, output conventions, and omissions in `docs/cli.md` (E-02; Remediation Risk: Low).
3. Repair `[diff]` table and fix `[capture.resources].scope` and `[methods].format` in `docs/configuration.md` (E-03; Remediation Risk: Low).
4. Mark reserved/inert keys and fix `[core]`, `[capture.environment]`, `[console]`, `[capture.signals]`, `[report]`, and quick-start examples in `docs/configuration.md` (E-04; Remediation Risk: Low).
5. Fix Environment Variables precedence and add missing env vars in `docs/configuration.md` (E-05; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Wiring `pubrun methods` CLI to read `[methods].format` and changing non-TTY color/DIM rendering in `show`/`status`/`res`/`diff` are runtime behavior changes deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality).
  - Carrier-Declined: Runtime CLI changes outside documentation-only scope; recorded in orchestrator `86cd17`.

## Scope check

- Over-scope: none. Only `docs/cli.md` and `docs/configuration.md` are modified.
- Under-scope: none.

## Required tests / validation

- Diff inspection of `docs/cli.md` and `docs/configuration.md`.
- Programmatic GFM table column-count validation on `docs/configuration.md` confirming every table row matches its header column count.
- Zero em/en dashes (`\u2013`, `\u2014`) in added lines of `docs/cli.md` and `docs/configuration.md`.
- Internal link and anchor validation on `docs/cli.md` and `docs/configuration.md`.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- Pure documentation synchronization with live code; no runtime behavior changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for `Selecting a run`, `diff`, and `show`/`report` confirming single-run + section-extract grammar, filter-based multi-run note, `--basic` excluding `packages`, 0/1/2-arg `diff`, and `status`/`combined` selector semantics.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/cli.md` hunks for the new Standard run filters section, command filter references, `clean` comment, `--info`, Output Conventions, `--no-color`, `help` forms, exit codes, `status` closeout, `host` in `meta_ref`, `broken pipe`, `methods --all`, `show --utc`, and TUI tabs; plus pasted zero-dash check on added lines of `docs/cli.md` exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks for `[diff]`, `[capture.resources].scope`, and `[methods].format`, plus pasted output of a Python table-column check on `docs/configuration.md` confirming every Markdown table row has the same column count as its header (`exit=0`).
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunks confirming reserved markers on all inert keys, `nvidia-smi` for `capture_gpu_clock_speed`, `[core].meta_ref` and exact 4 `_CORE_SHORTCUTS`, `[capture.environment].mode`, `[console].jupyter_mode` precondition, `SIGPIPE`, `phase()`/`io_counters`/`[report]`, and updated quick-start commands.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted `git diff -- docs/configuration.md` hunk for the Environment Variables table showing exact precedence and `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_DEBUG`, `NO_COLOR`; pasted zero-dash check on added lines of `docs/configuration.md` exiting 0; pasted link/anchor check across both files exiting 0; and pasted `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`).
2. Scope declaration: modify only `docs/cli.md` and `docs/configuration.md`.
3. Validation honesty: run every required validation command and paste actual output into each `V-*` item.
4. Commit discipline: commit through `aw commit pqcx6o -- docs/cli.md docs/configuration.md`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: finalize through `aw ipd finalize pqcx6o` (or the runner) once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
