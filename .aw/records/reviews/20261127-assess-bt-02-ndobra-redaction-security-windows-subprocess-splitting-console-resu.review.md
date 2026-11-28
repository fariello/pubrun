# Review findings: ipd ndobra

- Subject-Id: ndobra
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-02-ndobra-redaction-security-windows-subprocess-splitting-console-resu.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Fixed the Mermaid diagram ordering so `_BEARER_TOKEN_RE` inside `_redact_value_string_heuristics()` precedes `_DIAG_KV_EQ_RE` / `_redact_flag_space_values()` and included `console.py` and `liveness.py` (`PR-005`); extended atomic `\[REDACTED\]|` preservation to `_DIAG_KV_EQ_RE` and `_DIAG_KV_COLON_RE` alongside `_DIAG_TOKEN_VAL_RE` (`PR-001`); specified explicit Windows splitter edge cases (`PR-003`), independent `resume_after_migration` error handling (`PR-004`), and cross-platform-safe `getattr(ctypes, "get_last_error", None)` + non-tautological `disable_spy()` tests (`PR-002`); replaced `N/A.` with `Not applicable.` citing inspected docs, switched validation commands to `python3 -m pytest` (adding `tests/test_redaction.py`, `tests/test_capture.py`, and `tests/test_hook_ownership_rollback.py`) and `python3 -m mypy`, sharpened `V-01..V-05`, and completed the 5-clause execution contract (`PR-005`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### Redaction, Windows tokenization, console resume, and liveness scope` | Mermaid flowchart placed `_BEARER_TOKEN_RE` after `_redact_flag_space_values()` and omitted `console.py` / `liveness.py` | Corrected execution order (`_redact_value_string_heuristics()` -> `_BEARER_TOKEN_RE` -> `_DIAG_KV_EQ_RE`/`_DIAG_KV_COLON_RE`/`_redact_flag_space_values()`) and added `console.py` and `liveness.py` flows | Align diagram with actual redaction pipeline and complete 4-module scope per `technical-writing.md` Req 12(d)-(e) (`PR-005`) |
| `E-01` bullet 3, `E-04` bullet 1, `## Findings` (`BUG-E1`) | Updated only `_DIAG_TOKEN_VAL_RE` to treat `\[REDACTED\]` as atomic and tested only `--password [REDACTED]` | Required sharing an atomic `\[REDACTED\]` branch across `_DIAG_TOKEN_VAL_RE`, `_DIAG_KV_EQ_RE`, and `_DIAG_KV_COLON_RE`, and testing `--password [REDACTED]`, `--password=[REDACTED]`, `password: [REDACTED]`, and `auth --password supersecret` | Close remaining `[REDACTED]]` corruption in `_DIAG_KV_EQ_RE` and `_DIAG_KV_COLON_RE` (`PR-001`) |
| `E-02`, `E-04` bullet 1 | Left Windows quote-aware splitter edge cases unspecified (trailing backslash before quote, empty string/quoted tokens, nested opposite quotes, unquoted apostrophes) | Specified exact quote-scanning semantics (verbatim backslashes, `"` anywhere, `'` at token start or after `=`, literal opposite quote inside quotes, empty quoted tokens, `[]` on blank input, `[args]` on unterminated quotes) and paired test cases | Prevent executor ambiguity and regressions on Windows paths (`PR-003`) |
| `E-03` bullet 1, `E-04` bullet 2 | Omitted clearing failed log handle attribute, detaching `tee.log_file = None`, logging outside tee lock, and testing single-stream reopen isolation / failed-`start()` `failed` status | Required closing any opened handle on failure, resetting `stdout_log`/`stderr_log` to `None`, detaching `tee.log_file = None` with `_log_write_failed = True` under `finalization_lock`, logging outside the tee lock, and testing single-stream isolation plus failed-`start()` status preservation | Prevent handle leaks, lock-order hazards, and under-tested migration branches (`PR-004`) |
| `E-03` bullets 2-3, `E-04` bullet 3, `## Project conventions discovered` | Called `ctypes.get_last_error()` directly (absent on Linux/macOS and fails Linux/darwin `mypy`) and left `disable_spy()` test unspecified against tautological `subprocess.run` stubbing | Specified lazy `disable_spy` import, `getattr(ctypes, "get_last_error", None)`, non-generic script name + forced `wmic` fallback + `_spy_bypassed() is True` assertion across all six helpers, and `raising=False` when monkeypatching `ctypes.get_last_error` | Ensure 3-OS `mypy` passes and tests cannot pass without the real fixes (`PR-002`) |
| `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, `## Approval and execution gate` | Used bare `pytest`/`mypy`, omitted `test_redaction.py`/`test_capture.py`/`test_hook_ownership_rollback.py`, used `N/A.`, and omitted full execution-contract scope-fence and lifecycle-ownership clauses | Switched to `python3 -m pytest` (adding the three suites) and `python3 -m mypy`, replaced `N/A.` with `Not applicable.` citing inspected docs, sharpened `V-01..V-05` with re-derivation wording, and completed all 5 execution-contract clauses | Satisfy `technical-writing.md` Req 1, `r2-executability.md`, `r4-engineering.md`, and `s7-finalize.md:31-46` (`PR-005`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 2`, `- Scope-Paths:` (`src/pubrun/capture/redaction.py, src/pubrun/capture/subprocesses.py, src/pubrun/capture/console.py, src/pubrun/capture/liveness.py, tests/test_security_hardening.py, tests/test_capture_engine_bugs.py, tests/test_liveness.py`), 5 E-items in 3 task groups, no `.spec.md` file.

1. No: enforces existing documented secret-redaction, console `capture_state`, and liveness parity contracts without changing specs, CLI options, schema fields, or config keys.
2. Yes: directly modifies secret-redaction and subprocess command-tokenization code (`src/pubrun/capture/redaction.py`, `src/pubrun/capture/subprocesses.py`) that guards private credentials from leaking into manifests, lock files, and diagnostic logs.
3. Yes: 5 E-items across 3 task groups spanning 7 files (4 capture modules and 3 test suites) in the 10-child Set `assess-bt`.
4. Yes: `- Scope-Paths:` explicitly lists all 7 files.
5. Yes: a mistake in secret redaction or Windows command splitting can leak plaintext credentials or corrupt recorded command lines, and a mistake in `ConsoleInterceptor.resume_after_migration` can lose post-migration console logs or leak open file descriptors.

AW-TIER: complex

### Step R1

- Checked: every file and symbol cited in `ndobra` against the repository: `src/pubrun/capture/redaction.py` (`_BEARER_TOKEN_RE:185`, `_redact_value_string_heuristics:255-283`, `redact_argv:317-389`, `_DIAG_KV_EQ_RE:400-405`, `_DIAG_KV_COLON_RE:406-411`, `_DIAG_FLAG_PREFIX_RE:412-414`, `_DIAG_TOKEN_VAL_RE:415`, `_redact_flag_space_values:429-448`, `_redact_diagnostic_message:451-470`, `format_safe_error_detail:473-512`), `src/pubrun/capture/subprocesses.py` (`_spy_bypassed:23`, `disable_spy:43`, `SubprocessSpy.get_records:677`, `SubprocessSpy._safe_shlex_split:776-801`), `src/pubrun/capture/console.py` (`TqdmSafeTee._log_write_failed:111`, `ConsoleInterceptor.suspend_for_migration:473-512`, `ConsoleInterceptor.resume_after_migration:514-543`, `ConsoleInterceptor.start:549-602`, `ConsoleInterceptor.stop:604-675`), `src/pubrun/capture/liveness.py` (`_check_command_macos:181-195`, `_check_command_windows:198-213`, `_get_start_time_macos:399-414`, `_get_rss_macos:444-455`, `_get_cpu_macos:458-472`, `_get_win_kernel32:513-565`, `_is_pid_alive_windows:593-621`, `_get_rss_windows:665-710`), `src/pubrun/capture/signals.py` (`finalization_lock:63-100`, lock inventory line 117), `src/pubrun/tracker.py:1219-1265`, `src/pubrun/core.py:1665-1690`, `src/pubrun/capture/hardware.py`, `src/pubrun/capture/git.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/resources.py`, `tests/test_security_hardening.py`, `tests/test_redaction.py`, `tests/test_capture_engine_bugs.py`, `tests/test_liveness.py`, `tests/test_runtime_safety.py`, `tests/test_signals.py`, and `docs/{configuration,manifest,architecture,functional_spec}.md`.
- Verified: all cited files and symbols exist; confirmed empirically on Linux that `hasattr(ctypes, "get_last_error")` is `False` (`PR-002`); caught `_DIAG_KV_EQ_RE` and `_DIAG_KV_COLON_RE` sharing the same `[REDACTED]]` truncation pattern as `_DIAG_TOKEN_VAL_RE` (`PR-001`); caught the inverted redaction pipeline order in the Mermaid diagram (`PR-005`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability, re-derivation convention (`r2-executability.md:65`), and all 5 execution-contract clauses in `## Approval and execution gate`.
- Verified: `PR-001` through `PR-005` aligned every `E-*`/`V-*` pair, added missing existing test suites (`test_redaction.py`, `test_capture.py`, `test_hook_ownership_rollback.py`) to Command 1, ensured every `E-04` test is non-tautological and cross-platform, and completed the execution gate contract.

### Step R3

- Checked: full security and privacy rubric (`r3-security.md` B) across `src/pubrun/capture/redaction.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/console.py`, and `src/pubrun/capture/liveness.py`.
- Verified:
  - Secret redaction (`redaction.py`): requiring `(?<![A-Za-z0-9_-])` and `(?!-)` in `_BEARER_TOKEN_RE` plus skipping `val_match.group(0).startswith("-")` in `_redact_flag_space_values` closes plaintext credential leaks after boolean sensitive flags (`--use-auth`, `--use-key`, `--token`) and bare subcommands (`auth --password ...`) while preserving `Bearer tok123` and quoted secrets starting with `-`. Sharing `\[REDACTED\]|` across `_DIAG_TOKEN_VAL_RE`, `_DIAG_KV_EQ_RE`, and `_DIAG_KV_COLON_RE` eliminates `[REDACTED]]` corruption without weakening detection of real values.
  - Windows subprocess splitting (`subprocesses.py`): keeping mid-token quoted values (`--password="my secret"`, `API_KEY="foo bar"`) together ensures `redact_argv()` redacts the entire multi-word secret instead of leaking trailing words into `manifest.json`; preserving backslashes verbatim avoids breaking `"C:\dir\"`; preserving `[args]` fallback on unterminated quotes routes broken syntax through `redact_argv()`'s unsplit-string redaction path.
  - Diagnostic log safety (`console.py`): routing `resume_after_migration` reopen exceptions through `format_safe_error_detail(err, self._config)` prevents raw exception text (potentially containing sensitive paths or values) from leaking to debug logs.
  - Spy isolation (`liveness.py`): wrapping all six internal `subprocess.run` calls with `disable_spy()` prevents pubrun's own `ps`/`wmic` probes from polluting user `subprocesses` records.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - A/C/D: independent `try/except` blocks in `ConsoleInterceptor.resume_after_migration` ensure one stream failing to reopen does not discard the sibling stream or skip `faulthandler` when `stderr.log` succeeds, and `not self._started` prevents reopening handles after a failed `start()` or after `stop()`; logging outside `finalization_lock(tee._lock, 0.25)` avoids lock-reentry hazards; `getattr(ctypes, "get_last_error", None)` preserves Windows `ERROR_ACCESS_DENIED` parity while compiling cleanly under Linux and macOS `mypy`.
  - E: Command 1 runs all 8 relevant security, redaction, capture, and liveness pytest files under `-p randomly`, and Command 2 runs 3-OS `mypy` (Linux, `win32`, `darwin`).
  - Right-sizing: 5 E-items in 3 task groups across 7 Scope-Paths; each E-item is concise, bounded, and directly verifiable.
  - `## Spec / documentation sync`: substantiated against `docs/configuration.md`, `docs/manifest.md`, `docs/architecture.md`, and `docs/functional_spec.md`.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `_DIAG_KV_EQ_RE`/`_DIAG_KV_COLON_RE` `[REDACTED]]` corruption (`PR-001`), `ctypes.get_last_error` absence on Linux/macOS (`PR-002`), and Windows splitter edge cases (`PR-003`).
  2. Testing and regression: caught potential tautological `disable_spy()` mock test and missing Windows `wmic` fallback forcing in `E-04` (`PR-002`), added single-stream reopen isolation test (`PR-004`), and added `test_redaction.py`, `test_capture.py`, and `test_hook_ownership_rollback.py` to Command 1 (`PR-005`).
  3. UI / UX: verified `capture_state.status` accurately reports `"partial"` on migration reopen failure and `"failed"` when `start()` failed, with no `[REDACTED]]` artifacts in manifests or error logs.
  4. Architect: verified reuse of canonical `format_safe_error_detail`, `finalization_lock`, and lazy `disable_spy` patterns across sibling capture modules.
  5. Software engineer: verified 3-OS `mypy` compatibility of `getattr(ctypes, "get_last_error", None)` and lock-order hygiene in `resume_after_migration`.
  6. Power user: verified Windows paths with spaces, trailing backslashes (`"C:\dir\"`), and apostrophes (`C:\work\O'Brien\train.py`) split cleanly without corrupting backslashes or false-triggering unterminated-quote fallback.
  7. Novice: corrected the Mermaid diagram to reflect actual execution order and cover all four modules cleanly.
  8. Stakeholder: confirmed full coverage of `BUG-E1`, `BUG-E2`, `BUG-E4`, and `BUG-E9` assigned by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, 7 Scope-Paths, already Order 02 of 10-child Set `assess-bt`).
- Confirmed: `E-01` and `E-02` each own a single security module; `E-03` bundles two small (~15-20 line) capture-engine parity/error-tracking fixes cleanly within the 5-item child budget without requiring orchestrator churn. No further split is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt` (orchestrator `n6250e` and sibling children `wcjdbu`, `thbepl`, `qum7gf`, `kk83rk`, `n39jh9`, `dqaj9a`, `kgoymu`, `4eo4z2`, `37sth0`).
- Verified: strictly disjoint `Scope-Paths` across all 10 children (`ndobra` owns `src/pubrun/capture/{redaction,subprocesses,console,liveness}.py` and `tests/{test_security_hardening,test_capture_engine_bugs,test_liveness}.py`, with zero overlap against `wcjdbu`, `thbepl`, `n39jh9`, `kgoymu`, or any other child); `ndobra` deliverables, `Order: 2`, and `Item-Dependencies: none` match `n6250e` E-02 and child table row 02.

### Step S5

- Checked: `## Open questions` contains `None.`. All five findings (`PR-001` through `PR-005`) had `Low` overall Remediation Risk, were settled by repository code and documented workflow policy, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r3-security.md` / `r4-engineering.md` A | `.aw/records/plans/pending/20261127-assess-bt-02-ndobra-redaction-security-windows-subprocess-splitting-console-resu.ipd.md:52,75` vs `src/pubrun/capture/redaction.py:383,400-415,467-469` | `E-01` bullet 3 updated only `_DIAG_TOKEN_VAL_RE` for atomic `\[REDACTED\]`, leaving `_DIAG_KV_EQ_RE` and `_DIAG_KV_COLON_RE` with the same `[^\s,)\];]+` value pattern that corrupts `--password=[REDACTED]` and `password: [REDACTED]` into `[REDACTED]]`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-01` bullet 3 and `E-04` bullet 1 to share an atomic `\[REDACTED\]` branch across `_DIAG_TOKEN_VAL_RE`, `_DIAG_KV_EQ_RE`, and `_DIAG_KV_COLON_RE` and test `--password [REDACTED]`, `--password=[REDACTED]`, `password: [REDACTED]`, and `auth --password supersecret` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` A, E | `.aw/records/plans/pending/20261127-assess-bt-02-ndobra-redaction-security-windows-subprocess-splitting-console-resu.ipd.md:67,77,92` vs `src/pubrun/capture/liveness.py:181-213,399-472,513-565,593-621,665-710` | `E-03` bullet 2 called `ctypes.get_last_error()` directly even though `ctypes.get_last_error` does not exist on Linux or macOS (breaking Linux/darwin `mypy` and non-Windows tests); `E-04` bullet 3 also lacked safeguards against a tautological `subprocess.run` mock and did not force `_get_rss_windows` into its `wmic` fallback on Windows. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `getattr(ctypes, "get_last_error", None)` and lazy `disable_spy` import in `E-03`, updated `## Project conventions discovered`, and required `E-04` bullet 3 to exercise all six helpers with `_spy_bypassed() is True` + empty `SubprocessSpy.get_records()`, a non-generic script name, forced `wmic` fallback, and `raising=False` on `ctypes.get_last_error` (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r2-executability.md` / `r3-security.md` / `r4-engineering.md` A, D | `.aw/records/plans/pending/20261127-assess-bt-02-ndobra-redaction-security-windows-subprocess-splitting-console-resu.ipd.md:58,75` vs `src/pubrun/capture/subprocesses.py:776-801`, `tests/test_runtime_safety.py:778-791` | `E-02` left Windows quote-aware splitter edge cases unspecified for trailing backslashes before closing quotes (`"C:\dir\"`), empty/whitespace-only inputs, empty quoted tokens (`--password=""`), nested opposite quotes (`--password="it's secret"`), and unquoted apostrophe paths (`C:\work\O'Brien\train.py`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified explicit Windows splitter scanning rules in `E-02` (verbatim backslashes, `"` anywhere, `'` at token start or after `=`, literal opposite quotes inside active quotes, preserved empty quoted tokens, `[]` on blank input, `[args]` on unterminated quotes) and added edge-case test coverage in `E-04` bullet 1 (recommendation strength: `strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A, E | `.aw/records/plans/pending/20261127-assess-bt-02-ndobra-redaction-security-windows-subprocess-splitting-console-resu.ipd.md:66,76` vs `src/pubrun/capture/console.py:514-543,604-675` | `E-03` bullet 1 did not specify closing/clearing the failed log handle, detaching `tee.log_file = None`, or logging outside `finalization_lock(tee._lock, 0.25)`; `E-04` bullet 2 did not test single-stream reopen isolation or verify `capture_state.status == "failed"` after a failed `start()` + `resume_after_migration()`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Tightened `E-03` bullet 1 to clear the failed handle attribute, detach `tee.log_file = None` with `_log_write_failed = True` under `finalization_lock`, log safe error detail outside the tee lock, and preserve sibling stream + `faulthandler` recovery; expanded `E-04` bullet 2 to test both single-stream isolation and failed-`start()` status preservation (recommendation strength: `strong`). |
| PR-005 | MEDIUM | IN-SCOPE | `p-proofread.md` / `r2-executability.md` / `r4-engineering.md` E / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-bt-02-ndobra-redaction-security-windows-subprocess-splitting-console-resu.ipd.md:30-41,120-134,143-177` vs `src/pubrun/capture/redaction.py:382-384,458-469`, `.aw/system/workflows/technical-writing/technical-writing.md:29,40-46`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | Mermaid flowchart inverted `_BEARER_TOKEN_RE` vs `_redact_flag_space_values()` order and omitted `console.py`/`liveness.py`; `## Required tests / validation` omitted `test_redaction.py`/`test_capture.py`/`test_hook_ownership_rollback.py` and used bare `pytest`/`mypy`; `## Spec / documentation sync` used `N/A.` without naming inspected docs; `## Approval and execution gate` omitted the full scope-fence justification and runner-vs-manual finalize clauses. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected the Mermaid flowchart order and coverage, switched to `python3 -m pytest` (adding the three suites) and `python3 -m mypy`, expanded `N/A.` to `Not applicable.` citing inspected docs, sharpened `V-01..V-05`, and completed the 5-clause execution contract (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `ndobra` | `complex` | `standard` | Directly modifies secret-redaction and subprocess tokenization (`src/pubrun/capture/redaction.py`, `src/pubrun/capture/subprocesses.py`) across 7 files and 3 task groups in 10-child Set `assess-bt`; answers Yes to tier questions 2, 3, and 5 (`steps/t-tier.md`). | yes |
| D-2 | Single-quote opening rule in Windows `_safe_shlex_split(..., posix=False)` | Open `'` quote spans at token start or immediately after `=`, while `"` opens anywhere in a token | Open `'` anywhere in a token (breaking unquoted Windows apostrophe paths like `C:\work\O'Brien\train.py`), or ignore `'` completely (breaking `'D:\a\b'` in `tests/test_runtime_safety.py:782` and `--password='my secret'`) | `tests/test_runtime_safety.py:782-787` requires `'D:\a\b'` to strip outer single quotes, and `ndobra` requires `--password='my secret'` to stay grouped; restricting `'` to token start or immediately after `=` satisfies both while avoiding false unterminated-quote fallbacks on Windows apostrophe paths. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; every revision (`PR-001` through `PR-005`) was swept across `## Goal`, the Mermaid diagram, `E-01..E-05`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
