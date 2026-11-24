# Review findings: ipd ic6z4s

- Subject-Id: ic6z4s
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-07-ic6z4s-cli-status-diagnostics-and-render-negative-paths-and-asserti.ipd.md` (front matter, Goal, E-01 to E-05, conventions, findings, proposed changes, deferral, scope check, required tests, documentation sync, OQ-01, V-01 to V-05, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12, at lane HEAD `66a7328`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence listing pattern categories ("exit-0-only, tautological, time-dependent, and leaky") | States what the weak tests miss, then explains the live-run defect in numbered steps (what the lock records, what the liveness check reads, what `status` and `clean` then do) and the `--create-config` defect | A reader new to the repository needs the mechanism before the fix; requirement 1 (say what a thing does before naming it). |
| Goal | No diagram | Mermaid work plan: six task groups, the E-items, their dependency edges, and the pass and fail branch of the live-run check | Requirement 12 (diagrams for multi-part plans). |
| E-01, E-02, E-05 | Lettered sub-clauses (a) to (f) in one item, outcomes such as "validates real observable output" and "covers all `status.py` fallback/error paths" | One concern per E-item (E-01 to E-18), each naming the test, the input, and the exact string, exit code, or value it asserts | Each item must be executable and checkable in one pass; `IPD-Z602` flagged E-01 and E-02. |
| Project conventions | "Pending approved plan `4cy3ft` also addresses `PYTHONPATH=src`" | `4cy3ft` is executed and `tests/conftest.py` `_subprocess_pythonpath` already sets `PYTHONPATH` session-wide; adds the `isolated_cwd`, CI runner, `NO_COLOR`, 48-hour, and sibling-ownership facts | The old note was stale and sent the executor to redo finished work. |
| Spec / documentation sync | "N/A with reason: test-only hardening" | Cites the docs that already state the restored behavior, the spec search, and the `CHANGELOG.md` entry | The plan now changes user-visible behavior. |
| Gate | One paragraph telling the executor to move the plan by hand | Size exception with cohesion rationale and the five-element execution contract | Lifecycle transition belongs to `aw ipd finalize`. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (7 entries before review, 10 after), E-01 to E-05 (18 E-items in 6 task groups after review), and the files each item touches.

1. Yes: after review the plan changes production behavior of `pubrun status` and `pubrun clean` for live `python -m <package>` runs (E-06) and of `pubrun --create-config` at end of input (E-07). No public API, CLI option, or manifest field changes.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. Partly: 18 E-items in 6 task groups, all serving one subject (the CLI and status tests named by T-08, T-14, and T-15).
4. Yes: 10 files, two of them production modules.
5. Low: each production fix is one line that widens an existing behavior (an inconclusive name check falls back to the start-time check already used for `python` and `-m`; one more exception type at a prompt). Every other change is a test.

AW-TIER: standard

### Step R1

- Checked: every cited path, symbol, line, and string against lane HEAD `66a7328`, using CLI probes and a scratch copy under `/tmp/opencode` (never the lane).
- PR-001: `test_scan_running_run` and `test_clean_does_not_delete_running` skip under `python3 -m pytest` and pass under `pytest`. The reason is a production defect. `Tracker` records the lock script as `Path(sys.argv[0]).stem` (`src/pubrun/tracker.py`), which is `__main__` for `python -m <package>`; `/proc/<pid>/cmdline` does not contain `__main__`, so `_check_command_linux` returns a confirmed mismatch. Against a live `python -m livepkg` child, `pubrun status` printed `[INFO ] Closed out crashed run 'pubrun-__main__-...' (process dead). Updated manifest.json.` and `pubrun clean -y` printed `Deleted 1 run(s).`. `docs/cli.md` says "Running processes are never deleted". Adding `"__main__"` to `_GENERIC_SCRIPT_TOKENS` fixed both; `tests/test_status.py`, `tests/test_liveness.py`, and `tests/test_status_bugs.py` gave `143 passed` in the scratch copy. `python -m pkg.module` records `module`, which already returns inconclusive (`_match_script_in_tokens("worker", ["python3", "-m", "livepkg.worker"])` gave `None`).
- PR-004: `pubrun --create-config` with `stdin=DEVNULL` exits 1 with an uncaught `EOFError` traceback. The prompt catches only `KeyboardInterrupt`; the other `input()` prompts in `__main__.py` and `status.py` catch `(EOFError, KeyboardInterrupt)`.
- PR-005: Step 0 called `4cy3ft` a pending plan; it is executed, and `tests/conftest.py` `_subprocess_pythonpath` already prepends `src` to `PYTHONPATH` for every child process. The `PYTHONPATH` edits in E-01, E-02, and E-03 were redundant.
- PR-006: E-01(b) proposed "relative `time.time()` offsets" for the crashed-lock fixtures. Two fixtures use hostname `localhost`, which pubrun treats as crashed only when older than 48 hours (`RunInfo._load_from_lock`, `if age > 172800`), so a recent offset makes them `running`. Two use the current host with pid `99999`, which can be a live process. The prototype uses `time.time() - 3 * 86400` for `localhost` and a spawned-and-reaped pid for the current host; 8 tests passed under both runners. A function-local `import time` in one test caused `UnboundLocalError` once a module-level `import time` was used, so E-01 removes it.
- PR-018: OQ-01 claimed the unknown-section behavior from reading only, with `Owner: none`. Measured: `show <run> bogus_section` exits 0 with stdout byte-identical to `show <run>`.

### Step R2

- Checked: author-phase lint (`aw ipd lint --phase author --agent`: `clean`, 2 `IPD-Z602` advisories on E-01 and E-02), the E/V bijection, and each V-item against what its E-item produces. Every revised E-item was prototyped in `/tmp/opencode/icp/tests/test_proto_*.py` and each named mutation was run.
- PR-002: removing the skips alone does not give a working test. `test_scan_running_run` asserts only `pid == os.getpid()`, so the status is never checked; and an in-process `Run()` records pytest's own script name, so the result still depends on how pytest was started. With the skips removed and no fix, only `test_clean_does_not_delete_running` failed (`assert 1 == 0`). E-09 replaces the in-process run with a `Popen` child modeled on `TestConcurrentLiveRuns`, asserting `[(r.script, r.status, r.pid)] == [("livechild", STATUS_RUNNING, child.pid)]`; making `is_same_process` always return `False` failed both live tests.
- PR-003: every V-item demanded only a suite pass under `pytest`. A suite pass cannot show that a strengthened assertion catches a regression, and the skip defect is visible only under `python3 -m pytest`. Each V-item now runs both runners where relevant and names a mutation that must fail; all were measured (for example, the `_run_combined` stream prefix change failed 6 tests in the revised `tests/test_combined.py` and 0 in the current one).
- PR-007: E-01, E-02, and E-05 each bundled three to six concerns with outcomes that cannot be checked ("covers all `status.py` fallback/error paths"). Split into E-01 to E-18 with exact values.
- PR-008: E-03 proposed "tiny 1-line real files" for `tests/test_combined.py`; `create_mock_run` already writes them. The sentinel `open()` patch is what stops `_run_combined` before it prints. E-03 removes it and asserts `["[stdout] line", "[stderr] line"]`.
- PR-009: E-03 bundled `tests/test_report_subpackage_integrity.py`. With `TMPDIR` set to an empty directory, the current file left 7 directories there and the `cwd=tmp_path` version left 0. Split into E-15 with that measurement as its V-item.
- PR-012: E-05 asked for "non-zero exit and clear error output" without naming either. Probes gave the exact messages, and showed that `--last` is parsed only when samples exist, so a fixture with no samples would exit 0 and hide the check.
- PR-013: E-05(d) listed `--max-length` without noting that wrapping is on by default: `--max-length 3` alone prints the full value, and only `--max-length 3 --no-wrap` prints `[TRUNCATED]`. E-16 names both cases.
- PR-014: E-05(d) listed the `status` ambiguous selector and crashed close-out without expected results. E-17 names the current message (including its `2th` wording, characterized, not fixed), the exit codes, and the on-disk close-out result.

### Step R3

- Checked: the new tests start only `sys.executable` children under `tmp_path`, read no credentials, and use no network. The `--create-config` answer `2` test sets `XDG_CONFIG_HOME` and `APPDATA` to `tmp_path`, so it never writes the real user configuration. No security finding.

### Step R4

- Checked: the `AGENTS.md` no-code-pinning rule (every new test drives a function or the CLI and asserts on output, exit code, or files); sibling scopes (`7y0gmc` owns `tests/test_liveness.py`, so the E-06 regression test is in `tests/test_status.py`; `gzc672` also edits `src/pubrun/__main__.py` at other lines; `gzc672` and `bzi46m` also edit `CHANGELOG.md`; the runner isolates each plan in its own worktree); the orchestrator `vdxiw8` row 07; and the T-18 carrier `riulkx` (exists, status `open`).
- PR-010: T-14 names loose `or` assertions, but the plan addressed them only in `tests/test_reports.py`. `tests/test_cli.py` has them at lines 107, 119, 682, 768, 775, 1202, and 1242, and `test_dead_dispatch_aliases_error_cleanly` checks only `code != 0`. E-13 replaces each with the exact string measured at review.
- PR-011: the `TestPrintReportUnit` `or` assertions needed exact lines, and `print_report` colors its output unless `NO_COLOR` is set. E-14 sets it and names the lines.
- PR-015: with the two production fixes, the plan changes user-visible behavior, so "N/A: test-only" no longer held. E-08 adds `CHANGELOG.md` entries; `docs/cli.md` and `docs/functional_spec.md` already state the restored behavior; a spec search found nothing to change.
- PR-016: the gate told the executor to "move this plan to `.aw/records/plans/executed/`" by hand and lacked the scope declaration, the validation-honesty rule, and the runner and executor split. It now carries the five-element contract with `aw commit ic6z4s` and `aw ipd finalize ic6z4s`, and says the mutation checks must not be committed.
- PR-017: the plan had no diagram. Added under the Goal.

### Step S5

- Checked: OQ-01 (resolved, now with measured evidence and an owner); deferrals (T-18 `Carrier: riulkx`; a `Carrier-Declined` entry, added at review, for Windows live-child tests, since the fix is platform-independent and the `wmic` path is covered by `7y0gmc`). Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so the plan needs no blocking question and the lane outcome carries none.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R1 (production defect hidden by a skip) | Live `python -m livepkg` child: `status` closed it out as crashed, `clean -y` printed `Deleted 1 run(s).` | The lock records `__main__`, which never appears in the command line, so a live run is classified `crashed` and deleted. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-06 adds `"__main__"` to `_GENERIC_SCRIPT_TOKENS` with a `python -m` regression test; V-06 shows it fails without the fix. |
| PR-002 | high | IN-SCOPE | R2 (test cannot detect the regression) | `test_scan_running_run` asserts only the pid; in-process `Run()` script name depends on the runner | Removing the skips alone would leave the status unchecked and runner-dependent. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-09 uses a child-process fixture and asserts script, status, and pid; V-09 runs both runners and a liveness mutation. |
| PR-003 | high | IN-SCOPE | R2 (evidence cannot prove the change) | Prefix mutation: 0 failures in current `test_combined.py`, 6 in the revised file | Suite-pass-only V-items under one runner could not show that any strengthened test catches a regression. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Each V-item names measured mutation checks and, where it matters, both `python3 -m pytest` and `pytest`; a mutation procedure paragraph was added. |
| PR-004 | medium | IN-SCOPE | R1 (production defect) | `--create-config` with `stdin=DEVNULL`: exit 1 with `EOFError` traceback | The prompt catches only `KeyboardInterrupt`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-07 catches `(KeyboardInterrupt, EOFError)` with a subprocess regression test. |
| PR-005 | medium | IN-SCOPE | R1 (stale convention) | `4cy3ft` in `executed/`; `tests/conftest.py` `_subprocess_pythonpath` | The plan asked for `PYTHONPATH` handling the session fixture already provides. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Conventions corrected; E-02, E-12, E-15 add no `PYTHONPATH` handling. |
| PR-006 | medium | IN-SCOPE | R1 (fixture would break) | `RunInfo._load_from_lock` 48-hour rule; pid `99999` | Recent timestamps make the `localhost` locks `running`; a fixed pid can be live. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 uses `-3 * 86400` for `localhost`, a reaped pid and `-60` for the current host, the `argv` key, and exact stderr lines. |
| PR-007 | medium | IN-SCOPE | R2 (unexecutable items) | `IPD-Z602` on E-01 and E-02; outcomes such as "covers all fallback/error paths" | Bundled items had outcomes no executor could check. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Split into 18 single-concern E-items with exact expected values. |
| PR-008 | medium | IN-SCOPE | R2 (wrong technique) | `create_mock_run` already writes the logs; sentinel `open()` patch stops output | E-03 proposed creating files that exist and kept no output assertion. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03 removes the sentinel and asserts the exact combined lines. |
| PR-009 | low | IN-SCOPE | R2 (unmeasured leak) | Current file left 7 directories in `TMPDIR`, revised file 0 | The leak fix had no check that it stops the leak. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-15 with V-15 counting `TMPDIR` entries. |
| PR-010 | medium | IN-SCOPE | R4 (under-scope) | `tests/test_cli.py` lines 107, 119, 682, 768, 775, 1202, 1242, 1479 | Loose assertions named by T-14 in `test_cli.py` were not in any E-item. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-13 with exact strings; V-13 mutation on the `unknown command` wording. |
| PR-011 | low | IN-SCOPE | R4 (unspecified assertion) | `print_report` colors output unless `NO_COLOR` | Exact-line assertions would fail on color codes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-14 sets `NO_COLOR` and names the lines; V-14 mutates the commit length. |
| PR-012 | medium | IN-SCOPE | R2 (unspecified outcome; trap) | `--last` parsed only when samples exist | E-05 named no message, and a sample-free fixture would exit 0. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05 names every message and the two-sample fixture. |
| PR-013 | low | IN-SCOPE | R2 (trap) | `--max-length 3` alone prints the full value | Wrap is on by default, so a truncation test without `--no-wrap` fails. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-16 names both cases and the other flag outputs. |
| PR-014 | low | IN-SCOPE | R2 (unspecified outcome) | Ambiguous `'2'` message; close-out writes `crashed` and removes the lock | `status` selector tests had no expected results. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-17 with exact messages and on-disk checks; V-17 mutation on the close-out call. |
| PR-015 | low | IN-SCOPE | R4 (doc sync) | `docs/cli.md` and `docs/functional_spec.md` running-process sentences; spec `grep` empty | "N/A: test-only" became false once the plan fixes user-visible behavior. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | New E-08 adds `CHANGELOG.md` entries; the sync section cites the docs and the search. |
| PR-016 | medium | IN-SCOPE | S7 (execution contract) | Gate text "move this plan to `.aw/records/plans/executed/`" | Hand lifecycle move; three contract elements missing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Five-element contract with `aw commit ic6z4s` and `aw ipd finalize ic6z4s`. |
| PR-017 | low | IN-SCOPE | P (diagram) | No diagram in the plan | Requirement 12 not met for a six-group plan. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Mermaid work plan under the Goal. |
| PR-018 | low | IN-SCOPE | R1 (unmeasured resolution) | `show <run> bogus_section` stdout byte-identical to `show <run>`, exit 0 | OQ-01 was resolved from reading alone with no owner. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | OQ-01 cites the probe; E-05 pins the behavior. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Two one-line production fixes plus tests; no spec, security, or public API surface | yes |
| D-2 | Fix the two defects here or defer them? | Fix here (E-06, E-07) | Backlog item; separate plan | The hardened `test_status.py` tests cannot pass under `python3 -m pytest` without E-06; both fixes are one line, prototyped, and mutation-checked | yes |
| D-3 | How to make the live-run tests deterministic | Child process started with `Popen` | Keep in-process `Run()` and fail instead of skip | The in-process script name depends on the pytest launcher; `TestConcurrentLiveRuns` already uses the child pattern | yes |
| D-4 | Where to put the `python -m` regression test | `tests/test_status.py` | `tests/test_liveness.py` | Sibling `7y0gmc` owns `tests/test_liveness.py`; the user-visible effect is in `scan_runs` and `clean_runs` | yes |
| D-5 | Split the plan after `IPD-Z603` advisories (18 E-items, 10 Scope-Paths)? | Keep one plan with a cohesion rationale | Split by test file | The orchestrator assigns T-08 (part), T-14, and T-15 to this one row; splitting changes `vdxiw8`'s child table | yes |
| D-6 | Windows coverage for the live-child tests | Skip on `win32`, as `TestConcurrentLiveRuns` does | Write a Windows child-control mechanism | The fix is in `_script_is_generic`, shared by all three platform checks; `wmic` is covered by `7y0gmc` | yes |
| D-7 | Unknown `show` section | Characterize (exit 0, full report) | Change to an error | Changing CLI exit semantics is out of scope for a test plan; the pin makes a later change deliberate | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. E-06 to E-18 with V-06 to V-18 were added (`Highest E allocated: 18`, assigned by `aw ipd sync --apply`). `- Scope-Paths:` gained `src/pubrun/capture/liveness.py`, `src/pubrun/__main__.py`, and `CHANGELOG.md`. `- Item-Dependencies:` is unchanged (`none`). A re-review pass is required.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: re-read the revised plan in full against lane HEAD `66a7328`. Every test name in E-09, E-10, and E-13 exists at the cited line. Every mutation target string in the V-items was found verbatim with `grep -F`. Two targets were ambiguous (PR-020).
- PR-020: V-05 said to delete "the `except json.JSONDecodeError:` block" in `src/pubrun/report/diagnostics.py`, but `print_report` and `print_resources_report` each have one. V-18 said to append `"tui"` to `_PRIMARY_COMMANDS`, but that list is filled at run time from `subparsers.choices` minus `_known_aliases`. Both now name the function or the `_known_aliases = {"tui", "gui"}` line, and were re-measured: `print_report` block removed gave 1 failure, the `--last` exit removed gave 2, `_known_aliases = {"gui"}` gave 2.

### Step R2

- Checked: `aw ipd sync --apply` appended 13 `TODO` V-skeletons duplicating the V-06 to V-18 items already written; the duplicates were removed. `aw ipd lint --phase review-finalize` then reported PR-019.
- PR-019: `IPD-Z601` (error): 18 E-items with `Size assessment: standard`; and 12 `IPD-C801` advisories for citations given only as line numbers (`tests/conftest.py:15-34`, `src/pubrun/status.py:397-399`, `docs/cli.md:393`, and others). The gate now says `exception` with the cohesion rationale, and each citation names a symbol or quotes the text. After the fix, lint reports only the 2 `IPD-Z603` advisories answered by D-5.

### Step R4

- Checked: the added scope paths overlap siblings only as recorded in Round 1 R4. E-08's `CHANGELOG.md` prose falls under the `AGENTS.md` dash rule, and V-08 checks it.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-019 | low | IN-SCOPE | R2 (lint) | `IPD-Z601` error; 12 `IPD-C801` advisories | Size assessment did not match the item count, and citations relied on line numbers alone. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | `Size assessment: exception` with the cohesion rationale; citations anchored on symbols or quoted text. |
| PR-020 | low | IN-SCOPE | R1 (ambiguous mutation target) | Two `JSONDecodeError` blocks in `diagnostics.py`; `_PRIMARY_COMMANDS` built from `_known_aliases` | Two mutation instructions did not identify one edit. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-05 names `print_report` and `print_resources_report`; V-18 names the `_known_aliases` line; all re-measured. |

### Step S6

- Checked: Round 2 removed duplicate skeletons, changed the size assessment, anchored citations, and clarified two mutation targets. The E/V id set, `- Scope-Paths:`, and `- Item-Dependencies:` are unchanged since Round 1's S6. `aw ipd lint --phase review-finalize` reports only the 2 `IPD-Z603` advisories. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
