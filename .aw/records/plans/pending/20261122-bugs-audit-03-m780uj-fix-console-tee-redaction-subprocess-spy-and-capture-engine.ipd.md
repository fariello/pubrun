# IPD: Fix console tee, redaction, subprocess spy, and capture engine bugs

- Date: 2026-11-22
- Kind: child
- Concern: Bugs and correctness (console log integrity, secret redaction safety, subprocess wait-status decoding, filesystem mount detection, and resource/liveness/hardware capture).
- Scope: `src/pubrun/capture/console.py`, `src/pubrun/capture/redaction.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/liveness.py`, `src/pubrun/capture/hardware.py`, and regression tests in `tests/test_capture_engine_bugs.py`.
- Scope-Paths: src/pubrun/capture/console.py, src/pubrun/capture/redaction.py, src/pubrun/capture/subprocesses.py, src/pubrun/capture/filesystem.py, src/pubrun/capture/resources.py, src/pubrun/capture/liveness.py, src/pubrun/capture/hardware.py, tests/test_capture_engine_bugs.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix CRLF log erasure, boolean-flag redaction leak, wait-status decoding, mount precedence, thread-child resources, liveness, and GPU capture bugs
- Work-Kind: bug
- Priority: high
- Blocks-Release: next
- Set: bugs-audit
- Order: 3
- Highest E allocated: 05
- Author: Antigravity
- Id: m780uj

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md`, including requirement 12 (diagrams).

## Workflow history

- 2026-11-22 draft (Antigravity): created from `/assess-bugs` audit.
- 2026-11-22 to-review (Antigravity): authored fix steps, citations, and falsifiable validation criteria.

## Goal

Fix 9 confirmed correctness and secret-leak bugs across console teeing, argv/URI redaction, subprocess spying, mount-table parsing, Linux thread-child resource accounting, liveness matching, and GPU capture.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item is one focused pass with its own V-item check (`IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Console tee and redaction safety

- [ ] E-01 Fix `capture.console.TqdmSafeTee.write` and `flush` to preserve CRLF lines, synchronize concurrent writes, and honor `pubrun.paused()`.
  - Depends on: none
  - Expected outcome: Writing `"hello world\r\nsecond line\r\n"` (including split across chunk boundaries `\r` then `\n` via `_pending_cr`) logs `"hello world\nsecond line\n"` instead of `"\n\n"`, concurrent threads do not corrupt `_buf` under a `threading.Lock`, and `flush()` skips writing to the log file while `pubrun.paused()` is active.
  - Execution state: pending

- [ ] E-02 Fix `capture.redaction.redact_argv`, `_compile_sensitive_patterns`, and `_redact_value_string_heuristics`.
  - Depends on: none
  - Expected outcome: In `redact_argv`, when `redact_next` is True and the next token starts with `"-"` (an option flag like `--password`), `redact_next` resets and the token is processed as a flag so `--use-auth --password SECRET` redacts `SECRET` instead of `--password`; invalid `sensitive_keys_regex` patterns are caught (`re.error`) with a warning instead of crashing host `Popen`; `_redact_value_string_heuristics` applies all URI credential patterns independently (not `if/else`) and forbids whitespace in userinfo matching (`[^\s/:@]+`) so `"see http://example.com email alice@corp.com"` is not corrupted.
  - Execution state: pending

### Task group 2: Subprocess spy and filesystem mount/probe fixes

- [ ] E-03 Fix `capture.subprocesses._patched_os_system`, `SubprocessSpy` `Popen.poll()` tracking, and `filesystem._longest_prefix_fstype`, `_unescape_mount_field`, and `LiveProbe`.
  - Depends on: none
  - Expected outcome: `_patched_os_system` decodes POSIX wait status via `os.waitstatus_to_exitcode` (with Python 3.8 fallback) so exit code 1 records `1` instead of `256`; `SubprocessSpy` records exit codes when a child is reaped through `Popen.poll()` returning non-`None`; `_longest_prefix_fstype` uses `>=` so later active mounts (`nfs4`/`ext4`) override shadowed `autofs`/`rootfs` entries on the same mountpoint; `_unescape_mount_field` checks `i + 3 < len(field)` (requiring 3 octal digits); `LiveProbe` releases `_live_probe_sem` if `Thread.start()` raises.
  - Execution state: pending

### Task group 3: Resource tree, liveness, and hardware capture fixes

- [ ] E-04 Fix `capture.resources` Linux child enumeration, `capture.liveness._match_script_in_tokens` and macOS `ps` parsing, and `capture.hardware` GPU capture.
  - Depends on: none
  - Expected outcome: Linux tree resource collection iterates `/proc/{p}/task/*/children` (capturing children spawned by worker threads); `_match_script_in_tokens` normalizes/sanitizes command stems consistently for scripts with spaces/special characters and matches exact `.py` script names; macOS `ps -o lstart=` runs with `LC_TIME=C` in its environment; `capture.hardware` fixes Windows negative `AdapterRAM` signed-32-bit overflow handling and accumulates all GPUs on macOS instead of overwriting earlier entries.
  - Execution state: pending

### Task group 4: Regression test suite

- [ ] E-05 Add targeted unit and integration regression tests in `tests/test_capture_engine_bugs.py` and verify the full `pytest` suite passes.
  - Depends on: E-01, E-02, E-03, E-04
  - Expected outcome: `tests/test_capture_engine_bugs.py` reproduces and verifies all 9 bug groups above, and `pytest -q` passes with zero regressions.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `pubrun` supports Python 3.8+ (`os.waitstatus_to_exitcode` was added in Python 3.9, so `subprocesses.py` needs a clean POSIX `WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`/`WTERMSIG` fallback on 3.8).
- Pending IPD Set `cap-isolation` also touches `capture/redaction.py` and `capture/subprocesses.py`; keep edits strictly focused on the bug sites below.
- Tests must assert observable behavior and outputs, never inspect source code strings.

## Findings

| Bug ID | Severity | Remediation Risk | Location (symbol) | Defect |
|---|---|---|---|---|
| `BUG-04` | High | Low | `capture.console.TqdmSafeTee.write`, `TqdmSafeTee.flush` | Splitting on `\r` before `\n` erases every `\r\n` line to `""`; lacks `threading.Lock`; `flush()` ignores `pubrun.paused()`. |
| `BUG-05` | High | Low | `capture.redaction.redact_argv` | Boolean sensitive flag (`--use-auth`) before `--password SECRET` consumes `--password` as `[REDACTED]` and leaks `SECRET`. |
| `BUG-28` | Medium | Low | `filesystem._longest_prefix_fstype`, `_unescape_mount_field`, `LiveProbe` | Strict `>` keeps shadowed `autofs`/`rootfs`; octal unescape off-by-one turns `\04` into `\x04`; `LiveProbe` leaks semaphore on thread start error. |
| `BUG-35` | Medium | Low | `capture.resources` (Linux `/proc` tree walk) | Reads only `/proc/{p}/task/{p}/children`, missing all child processes spawned from worker threads. |
| `BUG-36` | Medium | Low | `capture.liveness._match_script_in_tokens` | Fails on sanitized stems for scripts with spaces/special chars (falsely classifying live runs as `CRASHED`) and misses exact `.py` matches. |
| `BUG-37` | Medium | Low | `capture.redaction._compile_sensitive_patterns`, `_redact_value_string_heuristics` | Uncaught `re.error` crashes host `Popen`; `if/else` leaks second URI credential; `[^/:]+` spans whitespace and corrupts URL+email text. |
| `BUG-38` | Medium | Low | `capture.subprocesses._patched_os_system`, `SubprocessSpy` | `_patched_os_system` records raw POSIX wait status (`256` for exit 1); `Popen.poll()` reaping misses exit code recording. |
| `BUG-61` | Low | Low | `capture.hardware` (Windows/macOS GPU collection) | Dead negative `AdapterRAM` check on Windows and macOS multi-GPU loop overwrites previous entries. |
| `BUG-62` | Low | Low | `capture.liveness` (macOS `ps -o lstart=`) | Fails to parse localized dates under non-English `LC_TIME`. |

## Proposed changes (ordered, validatable)

1. In `src/pubrun/capture/console.py`: track `_pending_cr` across `write()` calls, normalize `\r\n` to `\n` before handling bare `\r` progress overwrites, guard `_buf` and file writes with `self._lock`, and gate `flush()` writes on `not is_paused()`.
2. In `src/pubrun/capture/redaction.py`: handle flag-after-boolean-flag in `redact_argv`, catch `re.error` during regex compilation, and rewrite `_redact_value_string_heuristics` to run every pattern cleanly with whitespace-bounded URI userinfo regexes.
3. In `src/pubrun/capture/subprocesses.py` and `src/pubrun/capture/filesystem.py`: decode `os.system` wait status cleanly (Python 3.8 compatible), capture exit codes on `Popen.poll()`, switch `_longest_prefix_fstype` to `>=`, fix `_unescape_mount_field` bounds to `i + 3 < len(field)`, and wrap `LiveProbe` thread start in `try/except` releasing `_live_probe_sem`.
4. In `src/pubrun/capture/resources.py`, `src/pubrun/capture/liveness.py`, and `src/pubrun/capture/hardware.py`: scan all `/proc/{p}/task/*/children` entries, align `_match_script_in_tokens` stem sanitization and `.py` matching, pass `LC_TIME=C` to macOS `ps`, and fix Windows/macOS GPU parsing.
5. Add `tests/test_capture_engine_bugs.py` covering all 9 bug groups.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none.
- Under-scope: none. Every finding has a concrete fix and unit test.

## Required tests / validation

- Run `pytest tests/test_capture_engine_bugs.py -v` and paste actual output.
- Run full `pytest -q` and paste actual output confirming zero regressions.

## Spec / documentation sync

N/A: internal capture correctness and privacy-redaction bug fixes with no public API changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `pytest tests/test_capture_engine_bugs.py -v` output confirming `TqdmSafeTee` preserves CRLF lines (including split `\r` / `\n` writes), remains thread-safe under concurrent writers, and omits flushed bytes while paused.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `pytest tests/test_capture_engine_bugs.py -v` output confirming `redact_argv(["train.py", "--use-auth", "--password", "SUPERSECRET"], {})` redacts `SUPERSECRET`, invalid `sensitive_keys_regex` does not raise, multi-URI strings redact all credentials, and `"see http://example.com email alice@corp.com"` is preserved intact.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `pytest tests/test_capture_engine_bugs.py -v` output confirming `os.system` exit 1 records `1`, `Popen.poll()` records child exit code, `_longest_prefix_fstype` picks `nfs4` over shadowed `autofs`, `_unescape_mount_field("foo\\04")` stays `"foo\\04"`, and `LiveProbe` releases its semaphore on start failure.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `pytest tests/test_capture_engine_bugs.py -v` output confirming Linux `/proc/{p}/task/*/children` traversal, `_match_script_in_tokens("my_train", ["python3", "my train.py"]) == True`, `LC_TIME=C` passed to macOS `ps`, and Windows/macOS multi-GPU parsing.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted full `pytest -q` summary confirming `tests/test_capture_engine_bugs.py` and the entire test suite pass with zero failures.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Wait for human approval (`- Status: approved`) before executing. Commit only files listed in `Scope-Paths` via `aw commit m780uj -- src/pubrun/capture/console.py src/pubrun/capture/redaction.py src/pubrun/capture/subprocesses.py src/pubrun/capture/filesystem.py src/pubrun/capture/resources.py src/pubrun/capture/liveness.py src/pubrun/capture/hardware.py tests/test_capture_engine_bugs.py`, then move this plan to `.aw/records/plans/executed/` through the post-gate lifecycle transition.
