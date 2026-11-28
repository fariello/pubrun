# Review findings: ipd kk83rk

- Subject-Id: kk83rk
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-05-kk83rk-cli-selectors-combined-streaming-diff-array-rendering-and-di.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`). Expanded acronyms (`CLI`, `IPD`, `ANSI`, `SGR`, `RAM`, `EOF`, `CWD`, `UTC`, `JSON`, `POSIX`, `OS`, `QA`, `HPC`, `TUI`) on first use, standardized full repo-relative `path::Symbol` citations, replaced en dashes with ASCII hyphens, and updated the Mermaid `flowchart` to match `E-01` (`PR-008`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### CLI selector and bounded streaming flow` | Flowchart omitted `docs/cli.md` sync, `show` double-section `exit 2`, and `combined` `leading_buffer` cap | Added `docs/cli.md` sync, double-section `exit 2`, and `leading_buffer <= 50 lines -> fallback_ts` branch | Keep Mermaid flowchart consistent with `E-01` (`PR-008`) |
| `Concern`, `Goal`, `E-01`..`E-05`, `## Findings`, `## Deferred / out of scope` | Left `CLI`, `IPD`, `ANSI`, `SGR`, `RAM`, `EOF`, `CWD`, `UTC`, `JSON`, `POSIX`, `OS`, `QA`, `HPC`, `TUI` unexpanded and used mixed citations (`analysis/render.py`, `diff.py`, `main`) | Expanded acronyms on first use and standardized full repo-relative `path::Symbol` citations | Satisfy technical writing standard requirement 7 and spec Section 11.1 (`PR-008`) |
| `E-02`, `E-03`, `## Project conventions discovered`, `V-02` | Specified `DiagnosticsError(..., exit_code=2)` for malformed `--last` and claimed that was the repo convention | Preserved the existing `DiagnosticsError(..., exit_code=1)` contract asserted by three test suites while moving `parse_duration(last)` validation upfront | Prevent breaking 8 existing test cases across `tests/test_diagnostics_seams.py`, `tests/test_cli_negative_paths.py`, and `tests/test_cli_seams.py` (`PR-001`) |
| `Scope`, `Scope-Paths`, `E-01`, `## Project conventions discovered`, `## Spec / documentation sync`, `V-01`, `## Approval and execution gate` | Marked `## Spec / documentation sync` as `N/A` and omitted `docs/cli.md` even though `docs/cli.md:43-49` explicitly states `status` and `combined` reject directory paths | Added `docs/cli.md` to `Scope-Paths`, added `docs/cli.md:43-49` sync to `E-01` and `V-01`, updated `## Spec / documentation sync`, and recorded `- Size assessment: exception` with cohesion rationale | Prevent leaving `docs/cli.md` contradicting `--help` and runtime behavior (`PR-002`) |
| `E-01`, `E-02`, `E-03`, `E-04`, `V-04` | Left `_run_status --json` direct-path `index` matching, log-only `combined` prefix fallback, `_stream_log_entries` triggering-line yield, `show` double-section exit code, `_run_report` `runs` parameter wiring, `_format_array_diff` common-first multiset algorithm and 7-arg signature preservation, ANSI-safe truncation `use_color=False` guard, two-stage `TimeoutExpired` seam sequence, and `V-04` `win32` skip handling unspecified | Made every one of those behavioral contracts explicit in `E-01`..`E-04` and `V-04` | Eliminate executor ambiguity and subtle off-by-one/regression traps (`PR-003`, `PR-004`, `PR-005`) |
| `## Required tests / validation` | Omitted `tests/test_cli_seams.py`, `tests/test_bench_command.py`, and `tests/test_resources.py` | Added all three test files to the targeted `pytest -p randomly` command | Exercise every seam and command test covering modified functions (`PR-006`) |
| `## Approval and execution gate` | Omitted `--scope-reason`/`--scope-ack`, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize kk83rk` ownership | Hardened Clauses 2, 4, and 5 to match the repository execution contract | Satisfy mandatory execution-contract rules (`PR-007`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 5`, `- Scope-Paths:` (8 files originally, 9 after adding `docs/cli.md`), 5 E-items in 3 task groups, `- Priority: high`.

1. Yes: modifies CLI selector contracts across `status`, `combined`, `diff`, `show`, `bench`, and `res`/`cpu`/`mem`, diff rendering in `src/pubrun/analysis/render.py`, and CLI selector documentation in `docs/cli.md`.
2. No: does not touch private-data redaction, git commits, worktree isolation, merges to main, or sandbox guards.
3. Yes: 5 E-items across 3 task groups spanning 3 production modules, 1 documentation file, and 5 test files covering 11 findings (`BUG-U3`, `BUG-U5` CLI, `BUG-U6`..`BUG-U12`, `TEST-U4`, `TEST-U9`).
4. Yes: `- Scope-Paths:` explicitly lists all 9 modified files.
5. Yes: an exit-code change on `--last` breaks 3 existing test suites, naive multiset counter consumption in `_format_array_diff` mislabels the first duplicate instead of the excess duplicate, and forgetting to yield the 51st line on `leading_buffer` flush silently drops log lines.

AW-TIER: complex

### Step R1

- Checked: every file, symbol, line range, test assertion, and documentation statement cited by `kk83rk`:
  - `src/pubrun/__main__.py`: `_resolve_output_base_dir` (L31-40), `_get_manifest_path` (L144-225), `_resolve_direct_manifest_path` (L739-755), `_run_diff` (L757-860), `_run_resources` (L924-973), `_run_show_config` (L1050-1118), `_run_report` (L1121-1289), `_prepare_submission` (L1763), `_run_bench` (L2211-2459), `_run_status` (L2461-2548), `_run_combined` / `_stream_log_entries` (L2597-2793), `_apply_global_flags` (L3042-3054), `main` `show`/`report` shifting and filtered loop (L3635-3721), `main` `pubrun run` signal forwarding and `KeyboardInterrupt` escalation (L3925-3990).
  - `src/pubrun/analysis/render.py`: `_format_array_diff` (L38-94), `_fmt` (L102-109), `_render_inline` (L112-191).
  - `src/pubrun/analysis/diff.py`: `compare_manifests` multiset list diffing (L393-429).
  - `src/pubrun/report/diagnostics.py`: `_format_report_timestamp` (L315-328), `DiagnosticsError` (L350-357), `print_report` unknown section `exit_code=2` (L611), `parse_duration` (L1153-1180), `print_resources_report` (L1414-1729).
  - `src/pubrun/status.py`: `RunInfo.__init__` (L199-240), `find_run` (L993-1080), `_format_timestamp` (L1149-1169), `render_inspect` (L1442-1550).
  - Tests and docs: `tests/test_cli_diff_bugs.py`, `tests/test_combined.py`, `tests/test_render.py`, `tests/test_diagnostics_seams.py`, `tests/test_cli_negative_paths.py`, `tests/test_cli_seams.py`, `tests/test_show_sections.py`, `tests/test_diff_usability.py`, `tests/test_cli.py`, and `docs/cli.md` (L33-65, L455-495).
- Verified: `src/pubrun/report/diagnostics.py:1626` raises `DiagnosticsError(f"Invalid duration for --last: {e}")` with default `exit_code=1` (NOT `2`), pinned by `tests/test_diagnostics_seams.py:366`, `tests/test_cli_negative_paths.py:109` (6 cases), and `tests/test_cli_seams.py:313` (`PR-001`); `docs/cli.md:43-49` explicitly says `status` and `combined` reject directory paths and `manifest.json` paths, contradicting `--help` (`src/pubrun/__main__.py:3322, 3571`) and `BUG-U3` (`PR-002`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability, non-tautological evidence, and execution-gate contract.
- Verified: `PR-003` removed ambiguities in `E-01` (`_resolve_run_selector_or_path` `~`/`$VAR` expansion and `--json` `index` matching, log-only `combined` prefix fallback, triggering-line yield after `leading_buffer` flush, `show` double-section `exit 2`, and `_run_report(..., runs=...)` wiring); `PR-004` pinned `_format_array_diff`'s 7-arg signature, common-first multiset counter consumption, and `use_color=False` ANSI safety; `PR-005` fixed the two-stage `TimeoutExpired` seam sequence in `E-04` and `win32` skip honesty in `V-04`; `PR-007` hardened all five clauses of `## Approval and execution gate`.

### Step R3

- Checked: CLI selector resolution, streaming memory bounds, signal supervision, and error exit paths.
- Verified: `_resolve_run_selector_or_path` calls `find_run(...)` first so recency selectors win over CWD folders and non-run directories still fail cleanly; `_is_direct_run_path` guards `diff` against CWD `./1`/`./2` hijacking; `print_resources_report` validates `--last` before opening `events.jsonl` or writing output while preserving `exit_code=1`; `pubrun run` `SIGTERM` forwarding and `KeyboardInterrupt` escalation tests exercise real process and seam paths without modifying production signal logic.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified: `PR-001` prevents an unintended CLI exit-code regression across 8 existing tests; `PR-002` eliminates `docs/cli.md` drift; `PR-006` adds `tests/test_cli_seams.py`, `tests/test_bench_command.py`, and `tests/test_resources.py` to `## Required tests / validation`; `- Size assessment: exception` documents the 9-path cohesion rationale for including the 6-line `docs/cli.md` sync.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md` and the no-code-pinning testing contract:
  1. QA / QC: caught `--last` exit-code regression (`PR-001`), `leading_buffer` 51st-line drop trap (`PR-003`), and two-stage `KeyboardInterrupt` wait sequence (`PR-005`).
  2. Testing and regression: verified all new tests are purely behavioral (no AST/regex/source inspection) and added missing seam/command suites to `## Required tests / validation` (`PR-006`).
  3. UI / UX: verified `docs/cli.md` matches `--help` (`PR-002`), `show env logs` exits `2` cleanly (`PR-003`), and ANSI truncation resets styles cleanly before `[TRUNCATED]` (`PR-004`).
  4. Architect: verified `_format_array_diff` preserves its tested 7-arg signature and mirrors `src/pubrun/analysis/diff.py`'s `Counter` multiset model (`PR-004`).
  5. Software engineer: specified exact `_run_report(..., runs=...)` wiring preserving existing monkeypatch signatures and `~`/`$VAR` expansion in `_resolve_run_selector_or_path` (`PR-003`).
  6. Power user: verified `status <dir_path> --json` preserves recency `index` for runs inside `output_dir` and yields `null` for external paths (`PR-003`).
  7. Novice: verified `show <section> <run>` works naturally while double-section invocations emit a clear exit-2 error (`PR-003`).
  8. Stakeholder: confirmed full coverage of all 9 bugs (`BUG-U3`, `BUG-U5` CLI, `BUG-U6`..`BUG-U12`) and both testing gaps (`TEST-U4`, `TEST-U9`) assigned to Order 05 by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, 9 Scope-Paths, Order 05 of 10-child Set `assess-bt`).
- Confirmed: each E-item maps cleanly to a bounded pass (`E-01` CLI handlers + 6-line `docs/cli.md` sync, `E-02` render + diagnostics, `E-03` CLI/stream/render/diagnostics tests, `E-04` `pubrun run` signal tests, `E-05` validation). Keeping the 6-line `docs/cli.md` sync in `E-01` prevents intermediate doc drift and is justified under `- Size assessment: exception`.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt`: orchestrator `n6250e` (Order 00) and sibling children `wcjdbu`, `ndobra`, `thbepl`, `qum7gf`, `n39jh9`, `dqaj9a`, `kgoymu`, `4eo4z2`, and `37sth0`, plus pending plans `8o6o83` and `3u1xgk`.
- Verified: all 9 `Scope-Paths` (including `docs/cli.md`) are strictly disjoint from every sibling child and every other pending plan (`grep -rn "docs/cli.md" .aw/records/plans/pending/` had zero hits prior to this revision). `BUG-U5` CLI `--dir` expansion in `kk83rk` complements `wcjdbu` (`status._resolve_output_dir`) and `qum7gf` (`ConfigPanel`) with no ordering dependency (`- Item-Dependencies: none`).

### Step S5

- Checked: `## Open questions` contains `None.`. All eight findings (`PR-001` through `PR-008`) had `Low` overall Remediation Risk, were settled by repository code, tests, and commit `9d79ed4`, and were fixed in place with zero unfixed, deferred, or open findings and zero human-decision questions. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` D (Anti-regression) | `src/pubrun/report/diagnostics.py:353,611,1626`, `tests/test_diagnostics_seams.py:358-370`, `tests/test_cli_negative_paths.py:82-111`, `tests/test_cli_seams.py:283-316` | `E-02` and `## Project conventions discovered` specified `DiagnosticsError(..., exit_code=2)` for malformed `--last`, contradicting `diagnostics.py:1626` (`exit_code=1`) and breaking 8 existing test assertions across three test files (including `tests/test_cli_seams.py`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02`, `E-03`, `## Project conventions discovered`, and `V-02` to preserve `DiagnosticsError(..., exit_code=1)` while validating `parse_duration(last)` upfront before opening `events.jsonl` or printing output (recommendation strength: `very strong`). |
| PR-002 | HIGH | UNDER-SCOPE | `r1-references.md` / `r4-engineering.md` (Docs sync) | `docs/cli.md:43-49`, `src/pubrun/__main__.py:3322,3571`, commit `9d79ed4` | `docs/cli.md:43-49` explicitly states `status` and `combined` do not accept directory paths or `manifest.json` paths, contradicting `--help` and `BUG-U3`, while `## Spec / documentation sync` claimed `N/A`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `docs/cli.md` to `Scope-Paths`, added `docs/cli.md:43-49` sync to `E-01`, `V-01`, and `## Spec / documentation sync`, and recorded `- Size assessment: exception` with cohesion rationale (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A (Correctness) | `src/pubrun/__main__.py:1121-1133,2490-2497,2718-2741,2760,3668-3673,3702-3711`, `tests/test_cli_diff_bugs.py:146-147` | `E-01` left `~`/`$VAR` expansion and `--json` `index` matching in `_resolve_run_selector_or_path`, log-only `combined` prefix fallback, triggering-line yield on `leading_buffer` 50-line flush, `show` double-section exit code (`2`), and `_run_report(..., runs=...)` wiring unspecified. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Made all five behavioral contracts explicit in `E-01` and added matching coverage in `E-03` (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A (Correctness) | `src/pubrun/analysis/render.py:38-191`, `src/pubrun/analysis/diff.py:393-429`, `tests/test_render.py:338-362` | `E-02` did not pin `_format_array_diff`'s directly tested 7-parameter signature, did not specify common-first `Counter` consumption + `(tag, occurrence_idx)` keys (risking mislabeling the first duplicate instead of the excess trailing duplicate), and did not guard `use_color=False` against emitted ANSI resets on truncation. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified 7-parameter signature preservation, common-first multiset matching mirroring `src/pubrun/analysis/diff.py`, `(tag, occurrence_idx)` keys, and ANSI-safe truncation guarding `use_color=False` in `E-02` and `E-03` (recommendation strength: `very strong`). |
| PR-005 | MEDIUM | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` E (Testing) | `src/pubrun/__main__.py:3970-3983`, `kk83rk` `E-04`, `V-04` | `E-04` described a single `TimeoutExpired` raise in the fake `Popen` `KeyboardInterrupt` test, whereas `pubrun run` executes two `TimeoutExpired` waits (`3.0s` -> `terminate()`, `5.0s` -> `kill()`, then final reap `wait()`), and `V-04` demanded `PASSED` for both tests without accounting for `win32` skipping the POSIX-only `SIGTERM` subprocess test. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-04` with the exact two-stage `TimeoutExpired` sequence and updated `V-04` to state `PASSED` on POSIX or `SKIPPED` on `win32` for the POSIX-only `SIGTERM` test (recommendation strength: `strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r4-engineering.md` E (Testing and verification) | `tests/test_cli_seams.py:283-316`, `tests/test_bench_command.py`, `tests/test_resources.py` | `## Required tests / validation` omitted `tests/test_cli_seams.py`, `tests/test_bench_command.py`, and `tests/test_resources.py`, which directly test modified handlers (`_run_resources`, `_run_bench`, `print_resources_report`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added all three test files to the targeted `pytest -p randomly` command in `## Required tests / validation` and referenced `tests/test_cli_seams.py` in `V-02` (recommendation strength: `strong`). |
| PR-007 | LOW | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` | `kk83rk` `## Approval and execution gate` | Execution gate omitted `--scope-reason`/`--scope-ack` for out-of-scope edits, explicit `git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize kk83rk` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Hardened Clauses 2, 4, and 5 of `## Approval and execution gate` (recommendation strength: `strong`). |
| PR-008 | LOW | IN-SCOPE | `p-proofread.md` / `technical-writing.md` | `kk83rk` full text | Plan left 14 acronyms unexpanded on first use, used mixed code citation styles (`analysis/render.py`, `diff.py`, `main`), and omitted `docs/cli.md`, double-section `exit 2`, and `leading_buffer` cap from the Mermaid diagram. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Expanded all acronyms on first use, normalized code citations to full repo-relative `path::Symbol`, ensured ASCII hyphens only, and updated the Mermaid diagram (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `kk83rk` | `complex` | `standard` | Order 05 of 10-child Set `assess-bt`; modifies CLI contracts across 6 subcommands, diff rendering, diagnostics, and `docs/cli.md`; answers Yes to tier questions 1, 3, 4, and 5 in `steps/t-tier.md`. | yes |
| D-2 | Exit code for malformed `--last` in `print_resources_report` (`PR-001`) | Preserve existing `exit_code=1` while moving validation upfront | Change to `exit_code=2` and update 3 test files | `src/pubrun/report/diagnostics.py:1626` already uses default `exit_code=1` and 8 assertions across `tests/test_diagnostics_seams.py`, `tests/test_cli_negative_paths.py`, and `tests/test_cli_seams.py` pin `exit_code=1`. | yes |
| D-3 | Include `docs/cli.md` sync in `kk83rk` (`PR-002`) | Add `docs/cli.md` to `Scope-Paths` with `- Size assessment: exception` | Defer `docs/cli.md` to a follow-up plan | `docs/cli.md:43-49` directly contradicts `--help` and `BUG-U3`; no other pending plan touches `docs/cli.md`, and syncing 6 lines in `E-01` prevents doc drift between commits. | yes |

### Step S6

- Triggered Round 2 re-review because Round 1 added `docs/cli.md` to `- Scope-Paths:` and materially tightened `E-01`..`E-04`.

## Round 2

### Step R1

- Checked: revised `Scope-Paths` (9 files including `docs/cli.md`), `E-01`..`E-05`, `V-01`..`V-05`, `## Project conventions discovered`, `## Required tests / validation`, `## Spec / documentation sync`, and `## Approval and execution gate`.
- Verified: every updated path, line range, symbol, and test expectation aligns with the workspace.

### Step R7

- Checked: `docs/cli.md` against all other pending IPDs in Set `assess-bt` (`n6250e` and all 9 sibling children) and standalone pending plans (`8o6o83`, `3u1xgk`).
- Verified: strictly disjoint; zero overlap introduced by adding `docs/cli.md`.

### Step S6

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Size assessment: exception` cohesion rationale, technical writing compliance (zero unexpanded acronyms, zero em/en dashes, uniform citations, consistent Mermaid diagram), and zero remaining ambiguities or open questions. Ready to finalize.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

AW-REVIEW: DONE
