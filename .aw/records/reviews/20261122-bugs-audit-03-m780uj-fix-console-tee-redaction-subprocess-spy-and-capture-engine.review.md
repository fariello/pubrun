# Review findings: ipd m780uj

- Subject-Id: m780uj
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, `Goal`, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261122-bugs-audit-03-m780uj-fix-console-tee-redaction-subprocess-spy-and-capture-engine.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal` and new `Console tee CRLF and carriage-return handling` diagram | No Mermaid diagram for branching `\r\n`/`_pending_cr`/`\r` state flow; unexpanded acronyms (`CRLF`, `URI`, `POSIX`, `GPU`, `RSS`, `CPU`) | Added `flowchart TD` matching text and expanded acronyms on first use | Technical writing requirements 1, 12(b), 12(d), and 12(e) |
| Symbol citations across `E-01`..`E-04`, `Findings`, `Proposed changes` | Nonexistent symbols `_buf`, `is_paused()`, and `_compile_sensitive_patterns`; bare dotted names | Standardized `path::Symbol` citations using verified names (`self._current_buffer`, `_tee_paused()`, `_get_secret_pattern`) | `steps/p-proofread.md` Section 11.1 and factual accuracy |
| `## Spec / documentation sync` | Bare unsubstantiated `N/A` | Cited existing `docs/architecture.md`, `docs/functional_spec.md`, and `docs/manifest.md` contracts satisfied by these internal fixes | `steps/r4-engineering.md` spec/documentation sync rule |
| `## Approval and execution gate` | Missing honesty, never-push, scope-declaration, and conditional finalize rules; vague manual-move wording | Replaced with compliant 5-item Execution contract using `--scope-reason`/`--scope-ack`, HARD MUST pasted output rule, never-push, and conditional `aw ipd finalize m780uj` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, `src/pubrun/capture/console.py`, `src/pubrun/capture/redaction.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/liveness.py`, `src/pubrun/capture/hardware.py`, and Set `bugs-audit` orchestrator `jqqvkh`.

1. Yes: modifies secret redaction behavior (`redact_argv`, `_get_secret_pattern`, `_redact_value_string_heuristics`), `SubprocessSpy` global monkey-patching (`subprocess.Popen.poll`, `os.system`), `TqdmSafeTee` console logging, and process liveness/filesystem/resource/GPU capture contracts.
2. Yes: directly modifies `src/pubrun/capture/redaction.py` (which guards private secrets in `argv`, env vars, and diagnostics) and `src/pubrun/capture/console.py` (pause-gated logging).
3. No: 5 focused E-items across 4 task groups in 7 capture modules plus 1 test module (child 03 of 9 in Set `bugs-audit`).
4. Yes: `- Scope-Paths:` explicitly lists all 8 modified files.
5. Yes: a bug in `redaction.py` leaks secrets or crashes host `Popen`; returning decoded wait status from `_patched_os_system` breaks host callers; naive `_match_script_in_tokens` stem matching breaks `tests/test_liveness.py:213` and PID-recycling guards; and `TqdmSafeTee` errors corrupt or lose console logs.

AW-TIER: complex

### Step R1

- Checked: Verified every cited symbol, test contract, and defect across `src/pubrun/capture/console.py`, `src/pubrun/capture/redaction.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/liveness.py`, `src/pubrun/capture/hardware.py`, `tests/test_liveness.py`, `tests/test_redaction.py`, `tests/test_env_capture.py`, `tests/test_capture.py`, `tests/test_pause_resume.py`, and `tests/test_hook_ownership_rollback.py`. Caught nonexistent symbols (`_buf`, `is_paused()`, `_compile_sensitive_patterns`), `test_substring_only_match_is_inconclusive` regression hazard in `_match_script_in_tokens`, `LC_ALL` / host-locale trap in `_get_start_time_macos` (`PR-001`), host return-value contract in `_patched_os_system`, transactional `Popen.poll` patch/restore contract, `LiveProbe` non-raising error contract, missing second Linux tree function `_get_tree_cpu_jiffies_linux`, and dead `.isdigit()` root cause in Windows `AdapterRAM` (`PR-002`).

### Step R2

- Checked: Verified author lint preflight (`aw ipd lint --phase author --agent` exit 0, `clean`, 0 findings), 1:1 `E-01`..`E-05` to `V-01`..`V-05` bijection (co-locating per-bug test authoring inside `E-01`..`E-04`), 8-file `- Scope-Paths:` parity, `- Item-Dependencies: none` matching `jqqvkh`, concrete behavioral evidence in all `V-*` items (all reachable via local `pytest`, no code-pinning), and `## Approval and execution gate` (fixed in `PR-003`).

### Step R3

- Checked: Verified secret redaction fixes in `src/pubrun/capture/redaction.py` (boolean-flag leak `--use-auth --password SECRET`, sequential multi-URI redaction without `if/else` bypass, invalid-regex fallback to `DEFAULT_SECRET_REGEX` rather than crashing or disabling redaction), pause-gate enforcement in `TqdmSafeTee.flush()` so secrets printed inside `pubrun.paused()` never flush to `stdout.log`, and semaphore-leak prevention in `LiveProbe.__init__`.

### Step R4

- Checked: Evaluated engineering rubric sections A (CRLF/split-chunk state machine, thread-safe `TqdmSafeTee._lock` with unlocked passthrough, raw host return value on `_patched_os_system`, transactional `Popen.poll` patching, `LiveProbe` non-raising semaphore cleanup, both Linux tree functions covering `/proc/{p}/task/*/children`), C (reusing `_DIAG_URI_USERPASS_RE`/`_DIAG_URI_TOKEN_RE` and extracting `_get_linux_child_pids` + `_decode_wait_status`), D (preserving `tests/test_liveness.py:213`, `cap-isolation` `SubprocessSpy` transactional rollback and identity-guarded uninstall, and `probe_filesystem_live` non-raising guarantee), E (concrete unit/concurrency/mocked-platform tests in `tests/test_capture_engine_bugs.py` plus full `pytest -q`), F (KISS, preventing silent log erasure and silent secret leaks), right-sizing (5 focused E-items without inverted `E-05`/`V-01`..`V-04` test dependencies), and `## Spec / documentation sync`.

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught `test_liveness.py:213` stem-collision trap (`"train.py"` vs `"train.py.bak"`), `LC_ALL` + host `locale.LC_TIME` failure mode on macOS `ps`, missing `_get_tree_cpu_jiffies_linux` fix, and dead `.isdigit()` guard on negative `AdapterRAM` (`PR-001`, `PR-002`).
  2. **Testing and regression expert:** Fixed inverted `V-01`..`V-04` dependency on `E-05`, pinned `test_substring_only_match_is_inconclusive` in `V-04`, and verified raw `os.system` return-value preservation in `V-03` (`PR-001`, `PR-002`, `PR-004`).
  3. **UI / UX expert:** Verified CRLF console logs render cleanly on Windows/SSH while bare `\r` progress bars still squash cleanly (`PR-001`, `PR-004`).
  4. **Systems and software architect:** Aligned `Popen.poll` patching with `cap-isolation`'s transactional install/identity-guarded uninstall contract and reused existing `_DIAG_URI_*` patterns (`PR-001`, `PR-002`).
  5. **Software engineer:** Corrected nonexistent symbols (`_buf`, `is_paused()`, `_compile_sensitive_patterns`), specified `LiveProbe` non-raising error slot, and hardened the execution-contract gate (`PR-001`, `PR-002`, `PR-003`).
  6. **Sophisticated power user:** Confirmed multi-threaded Linux child processes count toward both tree RSS and tree CPU, `nfs4` overrides shadowed `autofs`, and multi-GPU Macs record every GPU (`PR-002`).
  7. **Complete novice:** Added `TqdmSafeTee` CRLF/CR flowchart, expanded acronyms, and clarified exact error handling (`PR-004`).
  8. **Stakeholder:** Confirmed all 9 capture-engine bug groups assigned to `m780uj` in Set `bugs-audit` (`jqqvkh`) are covered cleanly with zero silent deferrals.

### Step R6

- Checked: Evaluated decomposition across `E-01`..`E-05`. `m780uj` is already child 03 of 9 in Set `bugs-audit`, covering 7 cohesive capture modules grouped cleanly into 4 focused implementation passes plus 1 full-suite verification pass. No split recommended.

### Step R7

- Checked: Verified alignment with Set `bugs-audit` orchestrator `jqqvkh` and sibling child plans (`njn1up`..`kqzd15`). Confirmed `- Item-Dependencies: none` matches `jqqvkh`, `- Scope-Paths:` is completely disjoint from all 8 sibling child plans in `bugs-audit`, and `redaction.py`/`subprocesses.py`/`console.py` edits preserve all invariants landed by `cap-isolation`.

### Step S5

- Checked: Audited pre-existing `## Open questions` (`None`), `## Deferred / out of scope` (`None`), and all 4 review findings (`PR-001`..`PR-004`). All 4 findings had Low remediation risk and were fixed in place. Recorded reversible evidence-based decisions `D-1`..`D-3` below. Zero unresolved or blocking human questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-03-m780uj-fix-console-tee-redaction-subprocess-spy-and-capture-engine.ipd.md:39,42,58,83,90`, `src/pubrun/capture/console.py:21-23,99,155,190-214`, `src/pubrun/capture/redaction.py:19-36,234-239`, `src/pubrun/capture/liveness.py:86-113,340-354`, `tests/test_liveness.py:207-215` | Cited nonexistent symbols `_buf` (`_current_buffer`), `is_paused()` (`_tee_paused()`), and `_compile_sensitive_patterns` (`_get_secret_pattern`); naive stem matching in `_match_script_in_tokens` would break `tests/test_liveness.py:213` (`"train.py"` vs `"train.py.bak"` must return `None`); and passing only `LC_TIME=C` to macOS `ps` fails when `LC_ALL` is set or host Python uses a non-English `locale.LC_TIME` in `datetime.strptime`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected all symbol citations, specified unlocked passthrough + `_lock` + `_pending_cr` + `_tee_paused()` in `console.py`, specified `(re.error, TypeError)` fallback + sequential `_DIAG_URI_*` reuse in `redaction.py`, and specified suffix-safe stem matching plus `LC_ALL=C`/`LC_TIME=C` + locale-independent month parsing in `liveness.py` (`D-1`, `D-2`, recommendation strength: very strong). |
| PR-002 | HIGH | UNDER-SCOPE | R1/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-03-m780uj-fix-console-tee-redaction-subprocess-spy-and-capture-engine.ipd.md:49-59,80-86,92-93`, `src/pubrun/capture/subprocesses.py:69-71,248-377`, `src/pubrun/capture/filesystem.py:96,308-360`, `src/pubrun/capture/resources.py:79-107,168-207`, `src/pubrun/capture/hardware.py:248-276` | Omitted critical constraints: `_patched_os_system` must return the raw wait status to the host caller unchanged (decoding only for the manifest record); `Popen.poll` patching must follow `SubprocessSpy`'s transactional install/identity-guarded uninstall contract; `LiveProbe.__init__` must capture `Thread.start()` errors into `self._slot` without raising (`probe_filesystem_live` contract); `BUG-35` occurs in BOTH `_get_tree_rss_linux` and `_get_tree_cpu_jiffies_linux`; and `BUG-61` Windows `AdapterRAM` fails because `.isdigit()` rejects negative strings. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified all five mechanisms explicitly in `E-03`, `E-04`, `Proposed changes`, and `V-03`/`V-04` (`D-3`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261122-bugs-audit-03-m780uj-fix-console-tee-redaction-subprocess-spy-and-capture-engine.ipd.md:147-152`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | `## Approval and execution gate` omitted the HARD MUST pasted-output honesty rule, never-push rule, `--scope-reason`/`--scope-ack` scope declaration, and conditional runner vs standalone `aw ipd finalize m780uj` ownership, and used vague manual-move wording. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract (recommendation strength: very strong). |
| PR-004 | MEDIUM | IN-SCOPE | Check P/R2/R4 | `.aw/records/plans/pending/20261122-bugs-audit-03-m780uj-fix-console-tee-redaction-subprocess-spy-and-capture-engine.ipd.md:22-66,110-145` | `Workflow history` was oldest-first; `V-01`..`V-04` depended on `tests/test_capture_engine_bugs.py` not created until `E-05`; lacked a Mermaid diagram for the branching CRLF/`_pending_cr`/`\r` state machine (Requirement 12(b)); `Spec / documentation sync` was bare `N/A`; code citations lacked `path::Symbol` format; and acronyms were unexpanded. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reordered `Workflow history` newest-first, co-located per-bug test authoring inside `E-01`..`E-04`, added `TqdmSafeTee` flowchart, substantiated `Spec / documentation sync`, standardized `path::Symbol` citations, and expanded acronyms on first use (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should `_match_script_in_tokens` support sanitized stems without breaking `test_substring_only_match_is_inconclusive`? | Match exact basenames and suffix-safe sanitized stems (`Path(tok).stem` sanitized only for `.py`/extensionless scripts when `expected_script` is a stem), keeping `"train.py"` vs `"/x/train.py.bak"` returning `None`. | Compare `Path(tok).stem == expected_script` unconditionally (breaks `tests/test_liveness.py:213` because `Path("/x/train.py.bak").stem == "train.py"`). | `src/pubrun/capture/liveness.py:86-113`, `src/pubrun/tracker.py:141-143`, `tests/test_liveness.py:207-215` | yes |
| D-2 | How should macOS `_get_start_time_macos` avoid localized date parse failures? | Pass both `LC_ALL=C` and `LC_TIME=C` in `subprocess.run(..., env=...)` and parse English month abbreviations without relying on host Python `locale.LC_TIME` in `datetime.strptime`. | Set only `LC_TIME=C` and keep `datetime.strptime("%a %b ...")` (still fails if `LC_ALL` is set in env or host Python set a non-English locale). | `src/pubrun/capture/liveness.py:340-354` | yes |
| D-3 | What should `LiveProbe.__init__` and `_patched_os_system` return/raise on edge cases? | `LiveProbe.__init__` catches `Thread.start()` errors, releases `_live_probe_sem`, populates `self._slot` with `status: "error"`, sets `self._done`, and never raises; `_patched_os_system` decodes POSIX wait status only for `rec["exit_code"]` while returning raw status unchanged to the host caller. | Let `LiveProbe.__init__` raise (contradicts `probe_filesystem_live` docstring `"Never raises"`) or return decoded exit code from `_patched_os_system` (breaks host callers calling `os.WEXITSTATUS`). | `src/pubrun/capture/filesystem.py:308-360`, `src/pubrun/capture/subprocesses.py:248-286` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed (still `E-01`..`E-05` and `V-01`..`V-05`), `- Scope-Paths:` and `- Item-Dependencies:` did not change, and a full cross-section sweep confirmed zero stale tokens (`_buf`, `is_paused`, `_compile_sensitive_patterns`) and full alignment across front matter, workflow history, flowchart, checklist, findings, proposed changes, doc sync, validation items, and execution gate.

AW-REVIEW: DONE
