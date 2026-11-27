# Review findings: ipd 2ge0ea

- Subject-Id: 2ge0ea
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-8l-08-2ge0ea-cli-ergonomics-dir-pubrun-output-dir-json-output-streaming-c.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 1` info `IPD-Z603`, `0` errors/warnings). Expanded acronyms (`CLI`, `JSON`, `RAM`, `TOML`, `UTF-8`, `SSH`, `RSS`, `HPC`) on first use, anchored all symbols with `path::Symbol`, replaced ambiguous `show config <run>` wording and underspecified JSON/streaming/seed-scan clauses with explicit contracts, updated the Mermaid `flowchart LR` diagram to include `python_runtime.py` and the three test suites, and added the five-clause execution contract.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-01`, `V-01` | Cited non-existent `python_runtime.py::_detect_env_kind()`, falsely marked all `[capture.hardware]` clock/precision keys (including implemented `capture_gpu_clock_speed`) as `# RESERVED (no effect)`, and omitted `PUBRUN_OUTPUT_DIR` whitespace stripping and `resolve_config_with_provenance()` parity | Corrected symbol to `src/pubrun/capture/python_runtime.py::environment_kind`, kept implemented `capture_gpu_clock_speed` active while marking only the 3 unimplemented hardware keys reserved, specified accurate `environment.mode`/`resources.scope` comments, stripped `PUBRUN_OUTPUT_DIR`, and applied `_expand_output_dir` identically in `resolve_config()` and `resolve_config_with_provenance()` | Fix non-existent symbol, prevent factual error in `default.toml`, and preserve `tests/test_show_config.py:99` (`PR-001`) |
| `E-03`, `V-03` | Omitted four explicit `m5s3g8` handoffs (`_emit_ambiguous_selector` `candidates`, `keep_manifest=False`, `render_verbose_list(..., all_runs=...)`, `AmbiguousRunSelectorError` in `_run_diff`), left `status --json` / `diff --json` schemas and `_run_combined` leading-untimestamped streaming algorithm unspecified, missed `--dir` on `_run_show_config("run", ...)` and `_run_report` crash fallback, left ad-hoc `use_color` checks, and misnamed `__main__.py` subprocesses as "CLI git subprocesses" | Specified all four `m5s3g8` handoffs plus `report/output.py::use_color`, defined concrete `status --json` and `diff --json` schemas (with `allow_nan=False`), specified `heapq.merge` + `ExitStack` leading-untimestamped ordering, added `--dir` to `_run_show_config` and `_run_report` fallback, and listed actual `__main__.py` `text=True` subprocesses (`_run_gh`, `squeue`/`sacct`, `_run_bench` submit, `_run_tests`) | Prevent `AttributeError` / broken output on `m5s3g8` prefix ambiguity and make `E-03` fully executable (`PR-002`, `PR-004`) |
| `E-02`, `V-02` | Left `reproducibility.py` seed-annotation source unspecified (annotations live in `events.jsonl`, not `manifest.json`) and omitted `unsupported_schema_version` finding metadata and `harness.py` `is not None` zero-check | Specified bounded `events.jsonl` scan (10,000 lines / 2 MiB cap, pre-filtered on `"annotation"`), exact `unsupported_schema_version` `WARN` metadata, and `is not None` checks in `harness.py` (`--iterations`/`--passes < 1` -> `ap.error`) | Make `E-02` concrete, bounded, and bug-free (`PR-004`) |
| `E-04`, `V-04` | Left `show config <run>` ambiguous ("redirect or print hint"), omitted `_run_bench` `is not None` zero-check, and omitted preserving `init, report-bug` primary ordering and subcommand `Examples:` | Chose explicit redirect with stderr info note (+ `show config default`), specified `is not None` validation in `_run_bench`, specified `feedback` as alias of `report-bug` preserving primary order and `Examples:`, and noted zero em/en dashes in added/edited CLI text | Eliminate ambiguity and protect existing CLI tests (`PR-005`) |
| `E-05`, `## Required tests / validation`, `V-05` | Omitted updating 11 affected existing tests in `tests/test_cli.py` (9 `mock_run_resources.assert_called_once_with`, `TestCliBugReport`, `test_empty_invocation_shows_help_and_run_count`) and ran only 4 test files | Added explicit alignment steps for all 11 existing `tests/test_cli.py` assertions and expanded validation to all 12 affected suites (`test_combined.py`, `test_show_config.py`, `test_config.py`, `test_methods_multi.py`, `test_diff_usability.py`, `test_cli_diff_bugs.py`, `test_reproducibility_assessment.py`, `test_hardware.py`) | Prevent guaranteed regressions in existing tests (`PR-003`) |
| `## Goal`, Mermaid diagram, `## Deferred / out of scope`, `## Approval and execution gate` | Unexpanded acronyms, incomplete Mermaid diagram, omitted `docs/configuration.md` (`PUBRUN_OUTPUT_DIR`) deferral note, and 2-line approval gate lacking five-clause execution contract | Expanded acronyms, aligned Mermaid diagram, noted `docs/configuration.md` deferral to `6y55x4`, and added five-clause execution contract | Satisfy technical-writing and execution-gate contracts (`PR-006`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-8l`, `- Order: 8`, `- Scope-Paths:` (9 files: `__main__.py`, `config.py`, `default.toml`, `report/reproducibility.py`, `_bench/harness.py`, `capture/python_runtime.py`, `tests/test_cli.py`, `tests/test_cli_negative_paths.py`, `tests/test_bench_command.py`), 5 E-items in 4 task groups.

1. Yes: adds public CLI options (`--dir` across 8 subcommands, `status --json`, `diff --json`, `res`/`cpu`/`mem --utc`, `clean --force-remote-locks`, `report-bug --no-browser`), adds `PUBRUN_OUTPUT_DIR` environment variable and path expansion, changes `pubrun methods` stdout/stderr framing and `[methods].format` default, and adds `unsupported_schema_version` reproducibility warning.
2. No: does not touch leak sanitizers, commit helpers, worktree isolation, merge locks, or host sandbox profiles.
3. Yes: spans 5 execution items across 4 task groups touching 6 source modules and 3 test suites, consuming handoff seams from 4 prior children (`1o1cua`, `l596kn`, `m5s3g8`, `caeqdz`).
4. Yes: `- Scope-Paths:` explicitly lists all 9 modified files.
5. Yes: mistakes in CLI option plumbing, `resolve_config_with_provenance()`, `AmbiguousRunSelectorError` handling, `default.toml` comments, or `heapq.merge` streaming can break existing CLI scripts, crash on ambiguous run IDs, or corrupt piped JSON/methods/log output.

AW-TIER: complex

### Step R1

- Checked: every file, symbol, config key, and test citation against the repository: `src/pubrun/config.py` (lines 1-264), `src/pubrun/resources/default.toml` (lines 1-523), `src/pubrun/capture/python_runtime.py` (lines 1-80), `src/pubrun/capture/environment.py` (lines 1-45), `src/pubrun/capture/hardware.py:187`, `src/pubrun/capture/resources.py:273-627`, `src/pubrun/report/meta_snapshot.py:15-31`, `src/pubrun/report/templates.py` (lines 1-46), `src/pubrun/report/output.py` (lines 1-116), `src/pubrun/report/reproducibility.py` (lines 1415-1510, 3170-3225, 4725-4859), `src/pubrun/_bench/harness.py` (lines 1-300, 740-842), `src/pubrun/__main__.py` (lines 1-3650), `src/pubrun/status.py:170-280`, `tests/test_cli.py` (lines 160-195, 385-420, 730-905, 1235-1360), `tests/test_cli_negative_paths.py:390-430`, `tests/test_show_config.py` (lines 1-133), `tests/test_combined.py` (lines 1-100), `tests/test_reproducibility_assessment.py:700-745`, and `tests/test_reproducibility_preflight.py:1025-1065`.
- Verified: caught non-existent symbol `python_runtime.py::_detect_env_kind()` (real symbol: `environment_kind()`), caught false reserved claim for actively implemented `capture_gpu_clock_speed` (`PR-001`), caught `m5s3g8` handoff gaps including `_emit_ambiguous_selector` `candidates` (`PR-002`), caught 11 existing `tests/test_cli.py` assertions affected by signature/TTY/`scandir` changes (`PR-003`), and caught misnamed `__main__.py` subprocesses (`PR-004`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness (all 9 files), `- Item-Dependencies: executed:1o1cua, executed:l596kn, executed:m5s3g8, executed:caeqdz`, runtime-demonstration reachability and concrete named units in every `V-*` item, non-tautological validation evidence, and the five-clause execution contract.
- Verified: every `V-*` item maps 1:1 to its `E-*` item, names exact test suites and behavioral assertions reachable through `E-01..E-05`, and `## Approval and execution gate` carries all five required clauses with conditional runner/executor finalize ownership and no forbidden "STOP and report" wording.

### Step R3

- Checked: trust-boundary inputs, subprocess invocation, and file I/O safety across `src/pubrun/config.py` (`PUBRUN_OUTPUT_DIR` stripping and `$VAR`/`~` expansion), `src/pubrun/__main__.py` (argv-only `subprocess.run` calls with explicit UTF-8 decoding, `ExitStack` handle cleanup in `_run_combined`, `O(1)` crash tail and 64 KiB log streaming in `_run_report`, strict `allow_nan=False` JSON output on `status`/`diff`), `src/pubrun/report/reproducibility.py` (bounded 10,000-line / 2 MiB `events.jsonl` scan and UTF-8 `_run_readonly_git`), and `src/pubrun/_bench/harness.py` (`json.dumps` TOML escaping and `>= 1` arg bounds).
- Verified: no shell injection, unbounded file reads, or unescaped TOML injection vectors remain; `clean --force-remote-locks` delegates to `m5s3g8`'s `safe_delete_run_dir` which still refuses symlinks, out-of-dir paths, unreadable locks, and active local PIDs.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - `PR-001` corrects `python_runtime.py::environment_kind`, keeps implemented `capture_gpu_clock_speed` accurately documented in `default.toml`, and keeps `resolve_config_with_provenance()[0] == resolve_config()`.
  - `PR-002` fulfills all four handoff obligations from `m5s3g8` (`_emit_ambiguous_selector` `candidates`, `keep_manifest=False`, `render_verbose_list(..., all_runs=...)`, `AmbiguousRunSelectorError` in `_run_diff`/`_run_combined`) plus `report/output.py::use_color`.
  - `PR-003` aligns all 11 affected existing assertions in `tests/test_cli.py` and expands validation to 12 suites.
  - `PR-004` nails down bounded `events.jsonl` seed scanning, `status`/`diff` `--json` schemas, `heapq.merge` + `ExitStack` leading-untimestamped ordering, `--dir` on `show run config`/`_run_report`, and exact UTF-8 subprocess sites.
  - `PR-005` eliminates `show config <run>` ambiguity, fixes `bench` `0`-arg falsiness, and preserves `test_cli_negative_paths.py:415` and `test_cli.py:734,1244-1253`.
  - `PR-006` completes the five-clause execution gate, expands acronyms, aligns the Mermaid diagram, and records `docs/configuration.md` (`PUBRUN_OUTPUT_DIR`) deferral to `6y55x4`.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught non-existent `_detect_env_kind()`, false reserved label on `capture_gpu_clock_speed`, `0`-arg falsiness in `harness.py` and `_run_bench`, and `m5s3g8` `candidates` mismatch in `_emit_ambiguous_selector()` (`PR-001`, `PR-002`, `PR-004`, `PR-005`).
  2. Testing and regression: caught 11 existing `tests/test_cli.py` assertions broken by `_run_resources` kwargs, non-TTY `report-bug`, and `os.scandir` bare-`pubrun`, and expanded validation to 12 suites (`PR-003`).
  3. UI / UX: resolved `show config <run>` to redirect cleanly with stderr note, moved decorative `methods` banners to stderr, grouped `bench` flags, humanized `reproducibility.py` summary tokens, and fixed `init` copy without em/en dashes (`PR-004`, `PR-005`).
  4. Architect: verified clean cross-plan handoff alignment across `1o1cua`, `l596kn`, `m5s3g8`, `caeqdz`, `2ge0ea`, and `6y55x4` with zero cycles and bounded `O(K)` streaming I/O (`PR-002`, `PR-004`).
  5. Software engineer: ensured `resolve_config_with_provenance()` stays byte-identical to `resolve_config()`, `ExitStack` closes all files on `BrokenPipeError`, and `events.jsonl` seed scanning is bounded (`PR-001`, `PR-004`).
  6. Power user: verified consistent `--dir`, `PUBRUN_OUTPUT_DIR`, strict `--json` on `status`/`diff`, `--utc` on `res`/`cpu`/`mem`, and non-rerunning `--prepare-submission` tip (`PR-004`, `PR-005`).
  7. Novice: ensured `default.toml` comments match reality, `run --help` explains `import pubrun` and all 6 modes, and bare `pubrun` prints a 3-line quick start (`PR-001`, `PR-005`).
  8. Stakeholder: confirmed backward compatibility of all existing CLI commands, aliases (`feedback`, `report`, `resources`, `tui`, `gui`), JSON keys in `reproducibility.py`, and `MARKDOWN_TEMPLATE`/`LATEX_TEMPLATE` headings.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 4 task groups, 9 Scope-Paths, Order 08 of 10-child Set `assess-8l`).
- Confirmed: `2ge0ea` is already a bounded child plan within Set `assess-8l` with cohesive CLI/config/UX ownership sharing `src/pubrun/__main__.py`. No further splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-8l`: orchestrator `k80suw` (Order 00), `1o1cua` (Order 01), `l596kn` (Order 03), `m5s3g8` (Order 06), `caeqdz` (Order 07), and `6y55x4` (Order 10).
- Verified:
  - `src/pubrun/config.py` is serialized (`1o1cua -> 2ge0ea`, via `executed:1o1cua`); `_expand_output_dir` uses `1o1cua`'s `_section(config, "core")`.
  - `src/pubrun/resources/default.toml` is serialized (`l596kn -> 2ge0ea`, via `executed:l596kn`).
  - `tests/test_cli_negative_paths.py` is serialized (`caeqdz -> 2ge0ea`, via `executed:caeqdz`).
  - All handoffs declared by `m5s3g8:144-145` and `caeqdz:148` with `- Carrier: 2ge0ea` are explicitly satisfied in `E-03` and `E-04`.
  - Zero other siblings touch `src/pubrun/__main__.py`, `src/pubrun/report/reproducibility.py`, `src/pubrun/_bench/harness.py`, `src/pubrun/capture/python_runtime.py`, `tests/test_cli.py`, or `tests/test_bench_command.py`.
  - Child 10 (`6y55x4`) already depends on `executed:2ge0ea` and carries external doc sync (`README.md`, `docs/cli.md`, `docs/configuration.md`).

### Step S5

- Checked: `## Open questions` contains `None.`. All six findings (`PR-001` through `PR-006`) have `Low` overall Remediation Risk, are settled by repository code, tests, and sibling Set `assess-8l` contracts, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A | `src/pubrun/capture/python_runtime.py::environment_kind:6,26`, `src/pubrun/capture/hardware.py:187`, `src/pubrun/report/meta_snapshot.py:15,23,31`, `src/pubrun/config.py:148-233`, `tests/test_show_config.py:99` | `E-01` cited non-existent `python_runtime.py::_detect_env_kind()`, falsely marked actively implemented `capture_gpu_clock_speed` as `# RESERVED (no effect)` in `default.toml`, and omitted stripping empty `PUBRUN_OUTPUT_DIR` and keeping `resolve_config_with_provenance()[0] == resolve_config()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected symbol to `src/pubrun/capture/python_runtime.py::environment_kind`, kept `capture_gpu_clock_speed` active while marking only the 3 unimplemented hardware flags reserved, synced `environment.mode`/`resources.scope` comments, stripped `PUBRUN_OUTPUT_DIR`, and applied `_expand_output_dir` identically in `resolve_config()` and `resolve_config_with_provenance()` (recommendation strength: `very strong`). |
| PR-002 | BLOCKER | UNDER-SCOPE | `r7-cross-plan.md` / `r4-engineering.md` A | `.aw/records/plans/pending/20261127-assess-8l-06-m5s3g8-...ipd.md:71,76,144-145`, `src/pubrun/__main__.py:25-33,689,1029,1182,1228,1322,2310,2333,2418` | `2ge0ea` omitted four explicit `m5s3g8` handoff obligations: updating `_emit_ambiguous_selector()` to render `e.candidates` (avoiding broken output when `e.by_recency` is `None`), passing `keep_manifest=False` in CLI `scan_runs()` calls, passing `all_runs=all_runs` to `render_verbose_list()`, and catching `AmbiguousRunSelectorError` in `_run_diff()`, plus delegating ad-hoc `use_color` checks to `report/output.py::use_color`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added all four `m5s3g8` handoffs and `report/output.py::use_color` migration explicitly in `E-03` and `V-03` (recommendation strength: `very strong`). |
| PR-003 | BLOCKER | IN-SCOPE | `r4-engineering.md` D, E (Anti-regression and test coverage) | `tests/test_cli.py:739-767,1277-1290,1303-1520` | Adding `output_dir`/`utc` kwargs to `_run_resources`, non-TTY skipping `webbrowser.open()` in `report-bug`, and `os.scandir()` replacing `scan_runs()` in bare `pubrun` break 11 existing tests in `tests/test_cli.py`, and `## Required tests / validation` omitted 8 affected test suites (`test_combined.py`, `test_show_config.py`, `test_config.py`, `test_methods_multi.py`, `test_diff_usability.py`, `test_cli_diff_bugs.py`, `test_reproducibility_assessment.py`, `test_hardware.py`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added explicit test-alignment steps for all 11 affected `tests/test_cli.py` assertions in `E-05` and expanded `## Required tests / validation` to all 12 affected suites (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A, C | `src/pubrun/report/reproducibility.py:1427-1468`, `src/pubrun/_bench/harness.py:788-791`, `src/pubrun/__main__.py:854-955,1070-1098,1742,1953,1962,2171,2479-2545,2637` | `E-02` left `reproducibility.py` seed-annotation source unspecified (`events.jsonl`, not `manifest.json`) and omitted `harness.py` `is not None` zero-check; `E-03` lacked concrete `status --json`/`diff --json` schemas, `_run_combined` leading-untimestamped streaming algorithm and `ExitStack` cleanup, `--dir` on `_run_show_config`/`_run_report`, and misnamed `__main__.py` subprocesses as "CLI git subprocesses". | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified bounded `events.jsonl` seed scanning and `unsupported_schema_version` metadata in `E-02`, concrete `status --json`/`diff --json` schemas, `heapq.merge` + `ExitStack` leading-untimestamped ordering, `--dir` on `_run_show_config`/`_run_report`, and exact `__main__.py` UTF-8 subprocess sites in `E-03` (recommendation strength: `very strong`). |
| PR-005 | HIGH | IN-SCOPE | `r4-engineering.md` D, F (Unambiguous CLI UX and test preservation) | `src/pubrun/__main__.py:1570,2127-2130,2231-2234,2859-2870,3263-3275,3585`, `tests/test_cli_negative_paths.py:415`, `tests/test_cli.py:734,1244-1253` | `E-04` left `show config <run>` ambiguous ("redirect or print hint"), omitted `_run_bench` `is not None` zero-check (`--iterations 0`/`--passes 0`), and omitted preserving `init, report-bug` primary ordering and subcommand `Examples:` formatting. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `show config <run>` redirect with stderr info note (+ `show config default`), `is not None` bounds checks in `_run_bench`, `feedback` as alias of `report-bug` preserving primary order and `Examples:`, and zero em/en dashes in added/edited CLI prose (recommendation strength: `very strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `p-proofread.md` / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-8l-08-2ge0ea-cli-ergonomics-dir-pubrun-output-dir-json-output-streaming-c.ipd.md:5-6,32-39,120-122,171-173` | `## Approval and execution gate` omitted the five-clause execution contract, acronyms were unexpanded, code citations lacked `path::Symbol` anchors, the Mermaid diagram omitted `python_runtime.py` and test files, and `## Deferred / out of scope` omitted `docs/configuration.md` (`PUBRUN_OUTPUT_DIR`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added five-clause execution contract, expanded acronyms, anchored citations with `path::Symbol`, aligned Mermaid diagram, and noted `docs/configuration.md` deferral to `6y55x4` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `2ge0ea` | `complex` | `standard` | Adds public CLI flags (`--dir`, `--json`, `--utc`, `--force-remote-locks`, `--no-browser`), adds `PUBRUN_OUTPUT_DIR` + expansion, changes `methods` stdout/stderr framing, and integrates handoffs from 4 prior children; answers Yes to tier questions 1, 3, and 5 in `steps/t-tier.md`. | yes |
| D-2 | Behavior for `pubrun show config <arg>` | Redirect `show config default` -> `show default config` and `show config <run>` -> `show run config <run>` with an informational stderr note | Error with exit `1` printing a hint | Directly fulfills user intent without extra round-trips while teaching the canonical `show run config <run>` syntax; zero existing tests in `tests/test_show_config.py` assert an error on `show config <arg>`. | yes |
| D-3 | Top-level JSON shape for `pubrun status --json` and `pubrun diff --json` | JSON object (`{"total_runs", "matched_runs", "runs"}` / `{"run"}` for `status`; `{"run_a", "run_b", "depth", "diff"}` for `diff`, strict `allow_nan=False`) | Bare top-level JSON array for `status --json` | Matches every other `--json` command in `src/pubrun/__main__.py` (`self-check`, `inspect`, `rerun --preflight`, `bench`), all of which emit top-level JSON objects. | yes |
| D-4 | How to preserve `tests/test_cli.py::TestCliBugReport` while adding non-TTY / headless guard to `report-bug` | Add `_can_open_browser(no_browser)` checking `--no-browser`, `isatty()`, Linux display, and SSH-without-display, and update `TestCliBugReport` in `tests/test_cli.py` to simulate an interactive TTY with display alongside new `--no-browser`/non-TTY/SSH tests | Skip the non-TTY guard | Keeps the headless/CI safety fix from `ROLL-35` while keeping interactive browser launch thoroughly tested in `tests/test_cli.py` (already in `- Scope-Paths:`). | yes |

### Step S6

- Checked: Round 1 did not add or remove `E-*`/`V-*` items, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and resolved all six findings cleanly with zero remaining ambiguities. Ready for Step S7 finalization (`APPROVE WITH REVISIONS APPLIED`, `go-pending-approval`).

AW-REVIEW: DONE
