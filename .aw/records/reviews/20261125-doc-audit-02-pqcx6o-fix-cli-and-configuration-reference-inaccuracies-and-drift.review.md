# Review findings: ipd pqcx6o

- Subject-Id: pqcx6o
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Claude Opus 5.5 (OpenCode)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete plan text against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 citation forms. No pre-review snapshot was needed: lane `HEAD` `ed3cde0` had a clean working tree and the plan was already committed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) before any edit. Requirement 12: no diagram is needed. The steps are independent edits to sections of two reference files, with no entity relationships, branch, loop, or lifecycle, and the plan now says so in `## Scope check`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| E-01 `show` | "explain that multi-run display uses filters/`-n`"; "legacy hidden alias `report` omits `--all` and `run config <id>`" | Names the existing filter bullet to extend; states exactly which flags and positionals `report` lacks, with the parser cited | Makes the edit locatable and checkable (requirement 6). |
| E-01 `diff` | "document 0-, 1-, and 2-argument semantics" | States each case's behavior, including arguments after the second being ignored | The executor no longer has to rediscover the semantics (PR-005). |
| E-01 `Selecting a run` | "run-directory basename" | "unique substring of the run directory name" | `find_run` step 3 is a substring match, not a basename match (PR-006). |
| E-02, E-06, E-07 | One E-item listing eleven unrelated CLI edits | Three E-items: filters and `clean`; global behavior; per-command omissions | Right-sizing (PR-003). |
| E-04, E-08 | One E-item listing inert keys and nine unrelated sections | Two E-items: inert keys; other settings and examples | Right-sizing (PR-003). |
| E-05 | "coordinating with open backlog `aqb2bu`" | Use plan `87qr8h` item 3 text verbatim, with a rule for either execution order | `aqb2bu` is already graduated into a pending plan that writes the same rows (PR-001). |
| E-06 Output conventions | "Scope ... to status-line prefixes, `self-check`, and `inspect`" | Names which commands check only `NO_COLOR` and which render dim text, with functions cited | Makes the replacement text verifiable (requirement 6). |
| E-08 Quick start | "replace ... with active equivalents (`output_dir`, `pubrun show default config`, `pubrun init`)" | Exact replacement for each example; `--create-config` left unchanged | The original list offered three replacements for two examples and implied `--create-config` is deprecated, which it is not (PR-009). |
| Approval gate items 1, 2, 3, 5 | "modify only"; unconditional `aw ipd finalize` | Declaration with `--scope-reason` and `--scope-ack`; conditional runner or executor ownership, no hand `git mv`; explicit pasted-output rule | Matches the scope-fence wording rule and the lifecycle contract (PR-008). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (two paths), 5 E-items in 2 task groups at review start, `- Kind: child`, Set `doc-audit` sibling Scope-Paths, and other pending plans declaring either path.

1. No: documentation only. No spec, CLI option, output format, or configuration key changes; the plan describes existing behavior.
2. No: no code guarding private data, commits, worktree isolation, merges, or the sandbox. Two edits describe privacy-relevant behavior (environment redaction and import provenance paths), so they must be accurate, but they change no code.
3. Somewhat: two files, but E-02 and E-04 each bundled eight or more unrelated sections.
4. Yes: both paths are declared. Pending plan `87qr8h` outside the Set also declares `docs/configuration.md`.
5. No: text edits are reversible with `git revert`.

AW-TIER: standard

### Step R1

- Checked every material citation against the repository:
  - `src/pubrun/__main__.py::_add_run_filter_args`: `include_limit=True` on `clean`, `combined`, `methods`, `report`, `show`, `status`; `False` on `inspect`, `cpu`, `diff`, `mem`, `rerun`, `res`. Live `pubrun show --help` and `pubrun report --help` usage lines match.
  - `show_parser`: `run_dir`, `section`, `config_extra`, `--utc`, `--all`. `report_parser`: `run_dir`, `section`, `--utc`; no `--all`, no third positional. `SHOW_SECTIONS = ("logs", "env", "packages")`; a bare section in the `run_dir` slot is shifted into `section`.
  - `diff`: `run_dirs` is `nargs="*"`; 0, 1, and 2 or more arguments behave as E-01 now states. `default.toml` `[diff].ignore_basic` contains `"packages"`. `src/pubrun/analysis/diff.py` flattens `packages.{name}` and summarizes only `subprocesses` below `--deep`.
  - `docs/configuration.md` `[diff]` table: 3-column header, three 4-column rows (table check `mismatched=3`).
  - `src/pubrun/status.py::find_run`: recency index, id prefix, then directory-name substring. `status` and `combined` call it with `--dir`. `_get_manifest_path` falls back to `Path(run_dir)` for the other commands.
  - `src/pubrun/capture/resources.py::_poll_cpu` (own time only), `_poll_tree_rss` (Linux, macOS), `_poll_tree_cpu` (Linux only), `peak_tree_cpu_percent`, `tree_cpu_percent`, `io_counters`.
  - `src/pubrun/writer.py::ArtifactWriter.write_artifacts` reads `[methods].format`; `methods_parser` `--format` default is `"markdown"`.
  - Inert keys: no reference under `src/pubrun/` for the three provenance keys, the three hardware keys, or the three `depth` keys named. `_bootstrap.py` hard-codes `_max_requests: int = 50`. `capture_gpu_clock_speed` appends `clocks.max.sm` to the `nvidia-smi` query.
  - `config.py::_CORE_SHORTCUTS` and `tracker.py::_CORE_SHORTCUTS`: `profile`, `output_dir`, `auto_start`, `meta_ref`.
  - `capture/environment.py::get_environment` supports `"off"`; every mode calls `redaction.py::redact_env_vars`, which honors `[redaction].env_enabled`.
  - `capture/console.py::resolve_console_mode` returns `"off"` before the Jupyter and non-TTY overrides.
  - `capture/signals.py::_TARGET_SIGNALS` includes `SIGPIPE`.
  - `_bootstrap.py::select_mode` honors `PUBRUN_RUN_MODE_OVERRIDE` first; `_config_boot.py::resolve_import_mode` orders `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, config files, `"auto"`.
  - `report/output.py::debug_enabled` reads `PUBRUN_DEBUG`; `NO_COLOR` is read in `output.py`, `diagnostics.py`, `render.py`, `status.py`, and `__main__.py`.
  - `_show_info`, `_METHODS_LARGE_SET = 25`, `close_out_crashed_run`, `report/utils.py::HYDRABLE_SECTIONS` (includes `host`), the TUI `TabPane` labels, and both `--utc` formats match the plan.
  - `pubrun run` exit codes, run live: `./nonexistent-cmd-xyz` gave `rc=127`; `sh -c 'kill -TERM $$'` gave `rc=143`.
- Drift found:
  - `on_inactive_annotate` is applied by `core.py::_handle_inactive`, which seven functions call. The plan named only `phase()` (PR-004).
  - Backlog item `aqb2bu` is `graduated`, not open. Pending plan `87qr8h` already writes the same two Environment Variables rows (PR-001).
  - `bench` has no `127`, `128+N`, or `130` mapping; it returns the harness's nonzero code (PR-007).
  - `find_run` matches a directory-name substring, not a basename (PR-006).

### Step R2

- Checked: the E/V bijection; Scope-Paths against every file the steps edit; `- Item-Dependencies: none` against Set siblings `0cjiv5`, `dd7noz`, `wjsccu`, `77pdvl`, and `2uwuiu`, all with disjoint Scope-Paths; plans outside the Set that declare either path; and each V-item for concrete, non-tautological evidence and reachability.
- Results:
  - V-02 and V-05 required a dash check "exiting 0", but the natural `grep` dash check exits `1` when there is no match, and no command was given. V-03 named "a Python table-column check" and V-05 a "link/anchor check" without commands (PR-002). Review ran all three. Before execution the dash check reported `exit=1`, the table check `mismatched=3`, and the link check `broken=0`.
  - Plan `87qr8h` (Set `aqb2bu`) declares `docs/configuration.md` and replaces the same `PUBRUN_IMPORT_MODE` row. The two plans' Item-Dependencies cannot see each other across Sets. If they write different text, the second plan's merge conflicts or the table loses one version (PR-001).
  - V-06 now demands a runtime demonstration of the `run` exit codes; it names the producing code path (`src/pubrun/__main__.py::main` `run` branch), which exists today.

### Step R3

- Checked: the plan touches no authentication, secrets, or trust-boundary code. Two edits describe privacy-relevant behavior, and review checked both against the code:
  - `[capture.environment]` called `"full"` a "raw dump (unsafe)". The code redacts in every mode unless `[redaction].env_enabled = false`. The doc therefore overstated the risk, not understated it. E-08 states the actual behavior.
  - `[imports].provenance_path_mode = "relative"` implies caller paths are made relative. `_get_caller_info` records `frame.f_code.co_filename` unchanged, usually an absolute path that can include a home directory. Marking the key reserved without saying so would leave a reader believing paths are relative (PR-010).
- `python3 scripts/sanitize_paths.py --check --all` exits `0` on the current tree.

### Step R4

- Checked: rubric A through F, right-sizing, and spec and documentation sync.
- Results:
  - E-02 bundled eleven unrelated CLI sections and E-04 bundled ten keys plus nine sections. Review split them into E-02, E-06, and E-07, and E-04 and E-08, with ids assigned by `aw ipd sync --apply` (PR-003). Eight E-items trigger the advisory `IPD-Z603` note at info severity. Review accepted that rather than splitting the plan, because each item is a local prose edit and two sibling plans editing the same two files would add merge risk.
  - Twenty headings in the two files contain an em dash, and four other docs link their anchors. A literal reading of the no-dash rule could lead the executor to edit a heading and break those links. Review added a heading invariant and a heading check (PR-002).
  - No test reads either file (`grep -rln "cli\.md\|configuration\.md" tests/ .github/scripts/` exits `1`), so no test command is required.
  - The spec and documentation sync line now names the sibling owners and plan `87qr8h`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | coordination | `.aw/records/plans/pending/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md` `## Proposed changes` item 3; `.aw/records/backlog/` item `aqb2bu` `- Status: graduated` | E-05 called `aqb2bu` an "open backlog" item to coordinate with. It has graduated into pending plan `87qr8h`, which replaces the same `PUBRUN_IMPORT_MODE` row with its own exact text. Two independently worded rewrites of one row would conflict at merge or leave the table carrying one plan's text while the other plan's V-item fails. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-05 uses the `87qr8h` rows verbatim and skips them if they already exist. V-05 adds a command that checks both rows match `87qr8h` (`same=2`). `## Scope check` and `## Spec / documentation sync` name the overlap. |
| PR-002 | MEDIUM | IN-SCOPE | evidence | V-02 and V-05 "zero-dash check ... exiting 0"; V-03 "a Python table-column check"; V-05 "link/anchor check" | The checks had no commands, and the dash check's stated exit code was wrong for a `grep` with no match. Twenty existing headings contain em dashes, so an executor applying the dash rule could rename a heading and break cross-file anchors. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added exact dash, heading, table, and link commands with expected results and pre-execution baselines. Added a heading invariant before Task group 1. |
| PR-003 | MEDIUM | IN-SCOPE | right-sizing | E-02 pre-review text (eleven sub-edits); E-04 pre-review text (ten keys and nine sections) | Two E-items each required one V-item to verify many unrelated edits, so a small executor could lose a sub-edit and the V-item could still look complete. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split into E-02, E-06, E-07 (`docs/cli.md`) and E-04, E-08 (`docs/configuration.md`) via `aw ipd sync --apply`. Each new V-item names its hunks and one negative `grep` for removed text. |
| PR-004 | MEDIUM | UNDER-SCOPE | completeness | `src/pubrun/core.py::_handle_inactive` callers: `annotate`, `phase`, `report`, `artifact`, `register_file`, `register_input`, `register_output` | E-04 said to "mention `phase()` under `on_inactive_annotate`". Six other functions apply the same policy, so the fix would still under-document it. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-08 lists all seven functions; V-08 checks them. |
| PR-005 | LOW | UNDER-SCOPE | completeness | `src/pubrun/__main__.py` `diff` dispatch reads only `run_dirs[0]` and `run_dirs[1]` | `diff` silently ignores a third and later argument. The plan asked for 0, 1, and 2 argument semantics without saying what happens past two. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-01 states each case and that extra arguments are ignored. |
| PR-006 | LOW | IN-SCOPE | correctness | `src/pubrun/status.py::find_run` step 3, `run_id_or_prefix in r.run_dir.name` | E-01 said `status` and `combined` resolve a "run-directory basename". The code matches any unique substring of the directory name. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-01 says "unique substring of the run directory name" and adds that form to the table. |
| PR-007 | LOW | IN-SCOPE | correctness | `src/pubrun/__main__.py::_run_bench` returns the harness `rc`; only the `run` branch maps `127`, `128+N`, `130` | E-02 grouped `run` and `bench` under one exit-code mapping. `bench` has no such mapping. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-06 separates the two. V-06 demands a live demonstration of `run` (review observed `rc=127` and `rc=143`). |
| PR-008 | MEDIUM | IN-SCOPE | execution contract | `## Approval and execution gate` items 2, 3, and 5 | Item 2 said "modify only" (a stop-style fence). Item 5 told the executor to finalize unconditionally. Item 3 lacked the explicit never-claim-without-output rule. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote items 1, 2, 3, and 5 to the scope-declaration, validation-honesty, and conditional lifecycle wording used by sibling `0cjiv5`. |
| PR-009 | LOW | IN-SCOPE | correctness | `docs/configuration.md:34-35` `--create-config` examples; `src/pubrun/__main__.py` `--create-config` is not hidden or deprecated | E-04 listed `pubrun init` among replacements for deprecated quick-start examples, which invited the executor to replace the non-deprecated `--create-config` block too. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-08 gives one exact replacement per deprecated example and says to leave `--create-config` unchanged. |
| PR-010 | MEDIUM | UNDER-SCOPE | privacy accuracy | `src/pubrun/_bootstrap.py::_get_caller_info` records `frame.f_code.co_filename`; `default.toml` `provenance_path_mode = "relative"` | Marking `provenance_path_mode` reserved without stating what is recorded would still let a reader believe caller paths are relative. The manifest records the path unchanged, often an absolute path. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-04 states the actual recording behavior and the hard-coded 50-request cap. Changing the code to honor the key is outside this docs-only plan and is not proposed here. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` (rejected: two large reference files and a cross-Set overlap); `complex` (rejected: no contract or security code) | Step T answers | yes |
| D-2 | How to resolve the overlap with plan `87qr8h`? | Reuse its rows verbatim, skip them if present | Remove the rows from this plan and depend on `87qr8h` (rejected: Item-Dependencies across Sets would gate `doc-audit` on an unreviewed plan, and `PUBRUN_DEBUG` and `NO_COLOR` still belong here); write different text (rejected: guaranteed conflict) | `87qr8h` `## Proposed changes` item 3 is exact text; both plans are `to-review` or later | yes |
| D-3 | Should the heading em dashes be removed? | No; leave every existing heading unchanged | Rename headings and update links (rejected: `docs/api.md`, `docs/hpc.md`, `docs/performance.md` are owned by siblings `dd7noz`, `wjsccu`, and nobody, so this plan cannot update their links) | Link check of `README.md` and `docs/*.md`; sibling Scope-Paths | yes |
| D-4 | Split the plan for `IPD-Z603` (eight E-items)? | Keep one plan | Split each file into its own child (rejected: E-05 depends on E-08, and two children editing the same file add merge risk without benefit) | `aw ipd lint --phase review-finalize` reports `IPD-Z603` at info severity only | yes |
| D-5 | Should E-04 propose making `provenance_path_mode` work? | No; document the current behavior | Add a code fix (rejected: outside the documentation-only scope recorded by orchestrator `86cd17`) | Plan `- Scope:` and orchestrator `86cd17` deferral pattern | yes |

### Step S5

- Checked: `## Open questions` is `None.` The repository answered every question review raised (D-2 to D-5). Every finding is FIXED, so no finding is escalated and no new open question is needed. No decision is irreversible. The lane outcome carries `questions: []`.

### Step S6

- Checked: this pass added E-06, E-07, and E-08 with V-06, V-07, and V-08, and rewrote every V-item, so rule 1 called for a second pass. Review re-read every item against the revised text:
  - Proposed changes 1 to 8 map to E-01, E-02, E-06, E-07, E-03, E-04, E-08, and E-05.
  - E-05 depends on E-08; no item depends on an unassigned `E-NEW`.
  - Every flag, function, and section the pre-review E-02 and E-04 named appears in exactly one revised E-item.
  - Every command embedded in `## Required tests / validation` and V-05 was extracted from the plan text and run. Results: dash check `exit=1`, heading check `exit=1`, table check `mismatched=3`, link check `broken=0`, `87qr8h` row check `same=0` (expected `same=2` after execution).
  - `aw ipd lint --phase review-finalize --agent` exits `0` with only the info-level `IPD-Z603`.
- The second pass found one wording gap: the E-06 dim-text statement named no functions. Review fixed it in place and raised no new finding.

AW-REVIEW: DONE
