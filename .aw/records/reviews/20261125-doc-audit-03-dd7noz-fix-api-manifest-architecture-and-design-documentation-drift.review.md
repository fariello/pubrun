# Review findings: ipd dd7noz

- Subject-Id: dd7noz
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Claude Opus 5.5 (OpenCode)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete plan text against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 citation forms. No pre-review snapshot was needed: lane `HEAD` `8054ab8` had a clean working tree and the plan was already committed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) before any edit. Requirement 12: no diagram is needed. The steps are independent edits to sections of five reference files. The one branching topic, outcome classification, is a four-rule list in E-06. The plan now says so in `## Scope check`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| E-01, E-06 | One E-item bundling examples, `assess_run()`, inactive policy, outcome rules, exports, signatures, threading, and hooks | E-01: examples, `assess_run()`, inactive policy. E-06: outcome rules, `@audit_run`, exports, summary rows, threading, hooks | Right-sizing (PR-003). |
| E-01 examples | "Replace ... with active overrides (`capture={"hardware": {"depth": "deep"}}`, ...)" | Exact replacement for lines 75, 85 to 87, 95, 98, and 256; no `depth` override offered | The original list offered three replacements without saying which example gets which, so the executor had to choose replacement text (PR-005). |
| E-01 inactive policy | "all four obey `[events].on_inactive_annotate`" | Names all seven `_handle_inactive` callers, the `phase()` line 197 text, the `register_file` return-value bullet, and the four summary rows | Seven functions obey the key; the plan named four (PR-004). |
| E-06 outcome rules | "automatic unhandled-exception and non-zero `sys.exit()` detection"; wrapper mapping | Separate rules for explicit `stop()`, the wrappers, interpreter-exit finalization, and the signal upgrade, each with its code path | An explicit `stop()` inside `except` records `completed`; the plan implied it records `failed` (PR-006). |
| E-02 `status.outcome` | "Add `running`, `crashed`, and `partial`" | `running` and `crashed` are written; `partial` and `unknown` are schema-only, and readers show `unknown` for a missing field | No code path writes `partial` (PR-007). |
| E-02 `redacted_value` | "document all five representations" | States which representations are written (`plain`, `redacted`, `hashed`, `unavailable`) and that `suppressed` is schema-only | `suppressed` is never written as a representation (PR-007). |
| E-03, E-07 | One E-item bundling eleven manifest sections | E-03: `capture`, `invocation.script`, `console`, Meta Snapshot. E-07: `cwd`, GPU records, nullability, provenance note, reserved keys | Right-sizing (PR-003). |
| E-03 Meta Snapshot | "mention `diff` and legacy `report` alongside `inspect`/`show`/`methods`/TUI" | Lists every hydration caller, including `rerun`, `res`/`cpu`/`mem`, and `pubrun.diff()` | The original omitted four callers (PR-008). |
| E-07 `cwd` | "populated only when `cwd=` was passed to `Popen`" | Spy records `cwd=` or `null`, `os.system` records `null`, the explicit wrappers omit the key; Lock File `cwd` row unchanged | `src/pubrun/core.py` wrappers write no `cwd` key, and the Lock File table also has a `cwd` row (PR-008). |
| E-04, E-08 | One E-item for the header and Sections 5, 6, 10, 13, 16, 18, 21 | E-04: header, Sections 5, 6, 10, 13. E-08: Sections 16, 18, 21 | Right-sizing (PR-003). |
| E-04 Section 13 | "list `.pubrun.lock` and `profile-<phase>.prof`" | Adds `report()` and `artifact()` outputs and the `./runs` fallback rule | `pubrun.report()` and `pubrun.artifact()` write into the run directory (PR-008). |
| E-08 Section 21 | "primary CLI commands (`show`, `inspect`, `self-check`, `bench`, ...)" | All twelve missing commands, including `feedback`, each written as `` `pubrun <command>` ``; Section 18 and 21 `pubrun report` mentions changed to `pubrun show` | `feedback` was missing; `report` is a hidden alias (PR-008). |
| Findings A-07, A-08 | A-07 omitted the outcome paths; A-08 cited Section 12 | A-07 names the explicit-stop, wrapper, and exit paths; A-08 cites Sections 5, 6, 10, 13, 16, 18, 21 | No E-item edits Section 12, and Section 6 and 13 gaps were uncited (PR-009). |
| E-05 | "add a top-of-file historical outcome banner"; "refresh the TOML call-site summary" | Banner directly below the H1 with the shipped and unshipped recommendations, the superseded knob, and the fixed proxy gaps; `pause()` corrected; five TOML functions named; README locations named | The H1 contains an em dash, and the original allowed a rewrite of a dated record (PR-002, PR-010). |
| Required tests, V-01 to V-08 | "Zero em/en dashes ... Link and anchor verification" with no commands; V-items demanded unspecific diffs | Exact dash, heading, table, link, coverage, outcome-probe, and inactive-policy-probe commands with pre-execution baselines; every V-item demands named hunks and a `grep ...; echo "exit=$?"` showing `exit=1` | The checks were not runnable or falsifiable (PR-001). |
| Approval gate items 1, 2, 3, 5 | "modify only"; unconditional `aw ipd finalize` | Declaration with `--scope-reason` and `--scope-ack`; conditional runner or executor ownership, no hand `git mv`; explicit pasted-output rule | Matches the wording reviewed into siblings `pqcx6o` and `0cjiv5` (PR-011). |
| Scope check, Spec sync, Deferred | "Under-scope: none"; one-line sync | Lists what review added; sibling disjointness; diagram exemption; sibling owners named; repo-wide dash sweep deferred to `86cd17` | Requirements 9 and 12, and coordination (PR-012). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (five paths), 5 E-items in 3 task groups at review start, `- Kind: child`, Set `doc-audit` sibling Scope-Paths, and other pending or approved plans declaring any of the five paths (none).

1. No: documentation only. No spec, API, manifest field, schema, or configuration key changes; the plan describes existing behavior and names each schema divergence for the deferred reconciliation in orchestrator `86cd17`.
2. No: no code guarding private data, commits, worktree isolation, merges, or the sandbox. The `redacted_value` edit describes redaction output, so it must be accurate, and review verified it by running `redact_value`.
3. Somewhat: five files, but E-01, E-03, and E-04 each bundled seven or more unrelated sections.
4. No: all five paths are declared, and no other pending or approved plan declares any of them.
5. No: text edits are reversible with `git revert`.

AW-TIER: standard

### Step R1

- Checked every material citation against the repository:
  - `src/pubrun/config.py`: `_CORE_SHORTCUTS = {"profile", "output_dir", "auto_start", "meta_ref"}`; `profile_deprecation_notice` produces a `config.notices` entry, recorded by `src/pubrun/tracker.py`, never raised. `docs/api.md` has `profile` examples at lines 75, 85, 87, 98, and 256.
  - `src/pubrun/report/reproducibility.py::assess_run` calls `assess_manifest_reproducibility`, which emits the five `file_provenance_*` codes. `src/pubrun/report/checks.py` re-exports `assess_run`; `src/pubrun/__main__.py::_assess_cli_run` only calls it. The `docs/api.md:539-541` merge claim is false.
  - `src/pubrun/core.py::_handle_inactive` callers: `annotate`, `phase.__enter__`, `report`, `artifact`, `register_file`, `register_input`, `register_output`. Probe with `on_inactive_annotate = "error"`: `phase=RuntimeError register_file=RuntimeError register_input=RuntimeError register_output=RuntimeError`.
  - Outcome probe: `stop_in_except=completed unhandled_exception=failed sys_exit_3=failed tracked_run_keyboardinterrupt=interrupted tracked_run_systemexit0=completed`. Code: `Run.stop` defaults `outcome="completed"` and keeps `failed`/`ghost`; `core.py::_classify_exit_outcome`; `Run._finalize_state` classifies only `running`/`unknown` and upgrades `completed` to `interrupted` on SIGINT, SIGTERM, SIGHUP.
  - `src/pubrun/__init__.py::__all__` has 20 names; `__version__` from metadata; `__commit__` resolved lazily by module `__getattr__`, possibly `None`. `should_fail_strict(a, *, fail_on="warn")`. `audit_run(func=None, **kwargs)`.
  - `src/pubrun/capture/redaction.py::redact_value` with `representation = "hashed"` returns keys `['hash_algorithm', 'hash_value', 'representation']` (run live). Schema `$defs.redacted_value` has `hash: {algorithm, value}` and enum including `suppressed`, which no code writes. `git.py` writes `unavailable`.
  - `python_runtime.py`: `virtual_env` is `"venv" if is_venv else None`.
  - `status.outcome`: `running` (`tracker.py` startup), `ghost` (`_enter_ghost_mode`), `crashed` (`status.py::close_out_crashed_run`, called from `__main__.py::_run_report` and `_run_status`). `partial` has no writer; `unknown` is the reader fallback.
  - `invocation.py`: `path`, `real_path`, `ctime`, `sha256` up to 1,048,576 bytes, else `sha256_skipped`. `console.py::ConsoleInterceptor.stop`: `combined` is always the dummy record; `partial` and `failed` statuses exist. `tracker.py::Run.to_manifest_dict` writes `console_capture_mode` from config.
  - `meta_snapshot.py` keys; `report/utils.py::HYDRABLE_SECTIONS` includes `host`; `hydrate_manifest` and `hydrate_manifest_with_report` callers as E-03 lists.
  - `subprocesses.py` `cwd` handling; `hardware.py` GPU keys; schema `$defs.gpu_record.floating_point_precision` has no writer; `git.py` and `resources.py` nullable fields; `default.toml` `[capture.determinism]` "Not yet implemented".
  - `docs/architecture.md`: coverage check output lists the Section 5, 6, 10, 13, 16, 18, and 21 gaps E-04 and E-08 fix. `events.py` critical set `{"phase_start", "phase_end", "annotation"}`. `tracker.py` `LOCK_FILENAME = ".pubrun.lock"`; `core.py::_safe_phase_filename`. `python -m pubrun --help` command list.
  - `docs/design/file-io-provenance-evaluation.md`: `ProvenanceFileProxy` now at `src/pubrun/capture/file_io.py` with `read1`, `readinto`, `readinto1`, `seek`; no `errors="ignore"` remains (`grep` exit `1`). `system_metrics.py::get_proc_io` exists. `default.toml` `[capture.file_io]` keys and default `stat`. `pubrun.paused()` was added in commit `60132c7`; no `pause()` ever existed.
  - `docs/design/tomli-dependency-decision.md`: five TOML parse sites today (`config.py` 58 and 89-90, `_config_boot.py` 93, `__init__.py` 83, `report/checks.py` 141-142). README footnote, `## Installation` note, and the trust bullet are at the locations E-05 names.
- Drift found:
  - Seven functions obey `on_inactive_annotate`; the plan named four (PR-004).
  - Explicit `stop()` and interpreter-exit outcomes were described as one rule (PR-006).
  - `partial` and `suppressed` were implied to be written (PR-007).
  - Four hydration callers, the `feedback` command, the wrapper `cwd` omission, and the `report()`/`artifact()` run-directory files were missing (PR-008).
  - A-08 cited Section 12, which no E-item touches (PR-009).

### Step R2

- Checked: the E/V bijection; Scope-Paths against every file the steps edit; `- Item-Dependencies: none` against Set siblings `0cjiv5`, `pqcx6o`, `77pdvl`, `wjsccu`, and `2uwuiu`, all with disjoint Scope-Paths; plan `87qr8h` (Set `aqb2bu`), which does not edit `docs/manifest.md`; inbound anchors into the five files.
- Results:
  - No command existed for the dash, link, or table checks, and the V-items demanded "a diff confirming" lists of changes with no falsifiable marker (PR-001). Review added each command, ran each, and recorded its pre-execution result: dash check `exit=1`, heading check `exit=1`, table check `mismatched=0`, link check `broken=0`, coverage check with the expected non-empty lists, and each V-item `grep` matching the stale lines (`exit=0`) so it can fail.
  - Inbound anchors `api.md#pubrunpaused--contextmanager`, `manifest.md#meta-snapshot`, `#packages`, and `#timing` must survive. The design doc H1 and five section headings contain em dashes. Review added the heading invariant and the heading check (PR-002).
  - V-06 and V-01 demand runtime demonstrations; each names the producing code path, which exists today.

### Step R3

- Checked: the plan touches no authentication, secrets, or trust-boundary code. The `### Redacted Values` edit describes redaction output. Review ran `redact_value` with the hashed representation and confirmed the plan's example keys; V-02 repeats that run. The `unavailable` example carries no value.
- `python3 scripts/sanitize_paths.py --check --all` exits `0` on the current tree.

### Step R4

- Checked: rubric A through F, right-sizing, and spec and documentation sync.
- Results:
  - E-01, E-03, and E-04 each bundled seven or more unrelated edits. Review split them into E-01 and E-06, E-03 and E-07, and E-04 and E-08, with ids assigned by `aw ipd sync --apply` (PR-003). Eight E-items trigger the advisory `IPD-Z603` note only.
  - The design records are dated decisions. Review limited E-05 to a banner and reference fixes so the analysis stays as written (PR-010).
  - No test or `.github/scripts/` file reads any of the five files, so no test command is required.
  - The spec and documentation sync line now names sibling owners `pqcx6o`, `wjsccu`, `0cjiv5`, and `77pdvl`, and states that no spec governs these files.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | evidence | `## Required tests / validation` pre-review ("Zero em/en dashes ...", "Link and anchor verification"); V-01 to V-05 pre-review | The checks had no commands, and every V-item accepted an unspecific diff, so an executor could mark a partial edit `pass`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the dash, heading, table, link, coverage, outcome-probe, and inactive-policy-probe commands with baselines. Every V-item names its hunks and a `grep` showing `exit=1`; V-05 also demands the cross-file checks and the sanitizer. |
| PR-002 | MEDIUM | IN-SCOPE | anchor stability | `README.md` link `api.md#pubrunpaused--contextmanager`; links to `manifest.md#meta-snapshot`, `#packages`, `#timing`; em dashes in `docs/design/file-io-provenance-evaluation.md` headings at lines 1, 65, 92, 122, 134, 140, 189 and `docs/design/tomli-dependency-decision.md` line 1 | A literal reading of the no-dash rule could lead the executor to edit a heading and break inbound links. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the heading invariant (only the two named heading changes) and the heading check; deferred heading dash removal to the `86cd17` sweep. |
| PR-003 | MEDIUM | IN-SCOPE | right-sizing | E-01 (seven topics), E-03 (eleven sections), E-04 (seven sections) pre-review | One V-item had to verify many unrelated edits, so a small executor could drop a sub-edit unnoticed. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split into E-01/E-06, E-03/E-07, and E-04/E-08 with matching V-items. |
| PR-004 | MEDIUM | UNDER-SCOPE | completeness | `src/pubrun/core.py::_handle_inactive` callers: `annotate`, `phase`, `report`, `artifact`, `register_file`, `register_input`, `register_output` | E-01 named four functions; `report()` and `artifact()` also obey the key, and the `register_file` return-value bullet still promised `None`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-01 adds the seven-function sentence, the `phase()` line 197 rewrite, the return-value bullet, and the four summary rows; matches sibling `pqcx6o`. |
| PR-005 | LOW | IN-SCOPE | correctness | `docs/api.md` lines 75, 85 to 87, 95, 98, 256 | E-01 offered three possible replacements for five examples without mapping one to another, and gave no rewrite for the line 98 precedence note, which uses `profile`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-01 gives the exact replacement for each line and uses `output_dir`, `console`, and `capture.file_io.level`. |
| PR-006 | MEDIUM | IN-SCOPE | correctness | Outcome probe `stop_in_except=completed`; `src/pubrun/tracker.py::Run.stop`, `Run._finalize_state`; `src/pubrun/core.py::_classify_exit_outcome` | The plan described one exception-to-outcome rule. An explicit `stop()` inside `except` records `completed`, and finalization only classifies `running`/`unknown` runs. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-06 states the explicit-stop, wrapper, interpreter-exit, and signal-upgrade rules; V-06 reruns the probe. |
| PR-007 | MEDIUM | IN-SCOPE | correctness | No writer of `"partial"` for `status.outcome` or `"suppressed"` for `representation` in `src/pubrun/`; `status.py` reader fallback `unknown` | E-02 said to add `partial` as an outcome and to document all five representations, implying both are written. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-02 separates written values from schema-only values for both fields. |
| PR-008 | LOW | UNDER-SCOPE | completeness | `hydrate_manifest` callers in `__main__.py`, `report/diagnostics.py`, `core.py::diff`; `core.py` wrappers omit `cwd`; `core.py::report` and `artifact` write to `run_dir`; `python -m pubrun --help` lists `feedback` | The hydration caller list, the wrapper `cwd` case, two run-directory file kinds, and the `feedback` command were missing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added to E-03, E-07, E-04, and E-08; the coverage check enforces the CLI list. |
| PR-009 | LOW | IN-SCOPE | traceability | Findings row A-08 cited Section 12; no E-item edits Section 12 | A finding cited a section the plan does not change, and omitted Sections 6, 13, and 18, which it does change. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | A-08 now cites Sections 5, 6, 10, 13, 16, 18, 21; A-06 and A-07 wording matches PR-006 and PR-007. |
| PR-010 | LOW | IN-SCOPE | correctness | `docs/design/file-io-provenance-evaluation.md` lines 32, 100 (`pause()`), 189 to 205 (knob default `none`); commit `60132c7` added `paused()` | E-05 did not correct the nonexistent `pause()` name or the superseded knob, and allowed a rewrite of a dated record. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-05 adds a banner below the unchanged H1, corrects `pause()`, and leaves the analysis and headings unchanged. |
| PR-011 | MEDIUM | IN-SCOPE | execution contract | `## Approval and execution gate` items 2, 3, and 5 | Item 2 said "modify only" (a stop-style fence). Item 5 told the executor to finalize unconditionally. Item 3 lacked the never-claim-without-output rule. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote items 1 to 5 to the wording reviewed into siblings `pqcx6o` and `0cjiv5`. |
| PR-012 | LOW | IN-SCOPE | coordination | `## Scope check` "Under-scope: none"; `## Spec / documentation sync` one line | The plan named no sibling owners for matching drift, no disjointness evidence, and no diagram decision. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Scope check lists review additions, sibling Scope-Paths, and the diagram exemption; sync names the sibling owners. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` (rejected: five reference files and outcome semantics that needed probes); `complex` (rejected: no code, schema, or security change) | Step T answers | yes |
| D-2 | Should the manifest doc describe the schema or the runtime where they diverge? | The runtime, naming each divergence | Describe the schema (rejected: readers parse real manifests); fix the schema here (rejected: orchestrator `86cd17` defers schema and runtime reconciliation) | `86cd17` deferral; plan `- Scope:` | yes |
| D-3 | Should the design records be rewritten to current behavior? | No; banner and reference fixes only | Rewrite the analysis (rejected: they are dated decision records; a rewrite loses the reasoning trail) | `docs/design/` headers are dated and carry `- Status:` lines | yes |
| D-4 | Should the heading em dashes be removed? | No; leave every existing heading unchanged | Rename headings (rejected: changes anchors; the repo-wide sweep is owned by `86cd17`) | Inbound links listed in PR-002 | yes |
| D-5 | Split the plan for `IPD-Z603` (eight E-items)? | Keep one plan | One child per file (rejected: E-06, E-07, and E-08 depend on items in the same file, and separate children editing one file add merge risk) | `aw ipd lint --phase review-finalize` reports `IPD-Z603` at info severity only | yes |

### Step S5

- Checked: `## Open questions` is `None.` The repository answered every question review raised (D-2 to D-5). Every finding is FIXED, so no finding is escalated and no new open question is needed. No decision is irreversible. The lane outcome carries `questions: []`.

### Step S6

- Checked: this pass added E-06, E-07, and E-08 with V-06, V-07, and V-08, and rewrote every V-item, so rule 1 called for a second pass. Review re-read every item against the revised text:
  - Proposed changes 1 to 8 map to E-01, E-06, E-02, E-03, E-07, E-04, E-08, and E-05.
  - E-06 depends on E-01, E-07 on E-03, E-08 on E-04; no item depends on an unassigned `E-NEW`, and the heading invariant names E-07 by id.
  - Every topic the pre-review E-01, E-03, and E-04 named appears in exactly one revised E-item.
  - Every command embedded in `## Required tests / validation` and the V-items was extracted from the plan text and run. Results: dash check `exit=1`, heading check `exit=1`, table check `mismatched=0`, link check `broken=0`, coverage check with the expected pre-execution lists, outcome probe and inactive-policy probe matching the recorded values, `redact_value` keys `['hash_algorithm', 'hash_value', 'representation']`, and each V-item `grep` matching the stale lines (`exit=0` now, `exit=1` required after execution).
  - `aw ipd lint --phase review-finalize --agent` exits `0` with only the info-level `IPD-Z603`.
- The second pass found one gap: rewriting V-05 had dropped the original demand for the link check and sanitizer output, and no V-item demanded the dash, heading, or table checks. Review added all of them to V-05, the last item, and raised no new finding.

AW-REVIEW: DONE
