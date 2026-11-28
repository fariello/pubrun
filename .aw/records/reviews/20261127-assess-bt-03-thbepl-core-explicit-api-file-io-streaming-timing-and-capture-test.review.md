# Review findings: ipd thbepl

- Subject-Id: thbepl
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-bt-03-thbepl-core-explicit-api-file-io-streaming-timing-and-capture-test.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Added a Mermaid `flowchart LR` matching all 6 Scope-Paths (`PR-005`); fixed `E-03` bullet 2(b) to configure `console={"capture_mode": "standard", "non_tty_mode": "off"}` so `core.py`'s timestamped `pubrun.print` branch actually executes (`PR-001`); added a lock-free single-file time-cap abort in `E-02` and required a deterministic stepped `file_io.time.monotonic` fake clock for `BUG-E3` in `E-04` (`PR-002`); added `exit_status >= 0` and non-bool guards in `E-01` and POSIX-only skip for `kill -TERM`/`kill -9` in `E-03` (`PR-003`); specified the exact two thread-handshake sleep sites in `tests/test_runtime_safety.py`, `hardware.depth="off"` for symlink-escape tests, observable zero-fallback-read assertions for `TEST-C9`, and detailed `TEST-C5` pending re-registration assertions (`PR-004`); replaced `N/A.` with `Not applicable.` citing inspected docs, switched validation commands to `python3 -m pytest` and `python3 -m mypy`, added re-derivation wording to `V-01..V-05`, and completed the 5-clause execution contract (`PR-005`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### Core explicit API, file I/O timing, and test hardening scope` | Plan had no Mermaid diagram despite modifying 6 related files across 2 production modules and 4 test suites | Added `flowchart LR` mapping `E-01..E-04` files to `E-05` validation | Satisfy `technical-writing.md` Req 12(a) (`PR-005`) |
| `E-01`, `E-03` bullet 2(a) | Omitted `exit_status >= 0` and `not isinstance(exit_status, bool)` guards before `os.WIFEXITED`/`os.WIFSIGNALED`, and omitted POSIX-only skip marker for `kill -TERM $$` | Added `exit_status >= 0` and non-bool guards in `E-01` and `@pytest.mark.skipif(sys.platform == "win32", ...)` for POSIX signal tests in `E-03` | Prevent negative non-zero-low-byte misdecoding and Windows test failures (`PR-003`) |
| `E-02`, `E-04` bullet 2 | Timed small chunks without lock-free single-file time-cap early abort, and left `BUG-E3` test using real `time.monotonic()` (flaky at `round(..., 6)` on fast CPUs) | Added lock-free `self._stream_elapsed > budget.max_total_hash_seconds` abort in `E-02` and required stepped `file_io.time.monotonic` fake clock in `E-04` | Stop slow small-chunk hashing immediately and eliminate CPU-speed flakiness (`PR-002`) |
| `E-03` bullet 2(b), `## Project conventions discovered` | Tested `pubrun.print` timestamping with bare `console.capture_mode="standard"`, where `stdout_tee` causes `_should_log_pubrun_print` to return `False` | Specified `console={"capture_mode": "standard", "non_tty_mode": "off"}` so `_should_log_pubrun_print` returns `True` and `core.py:1282-1292` executes | Ensure `core.py`'s timestamped `pubrun.print` branch is genuinely tested and covered (`PR-001`) |
| `E-04` bullets 1-3 | Did not distinguish the 2 thread-handshake sleeps from the bounded child-exit poll in `test_runtime_safety.py`, omitted `hardware.depth="off"` in symlink-escape tests, omitted observable `extra_read_bytes`/`bytes_hashed` checks for `TEST-C9`, and left `TEST-C5` re-registration assertions terse | Named the 2 thread-handshake sleep sites, required `hardware.depth="off"` and `artifact(".")`/`artifact("./")`, added observable `extra_read_bytes == 0` / `bytes_hashed == 0` checks, and detailed `TEST-C5` pending re-registration assertions | Remove ambiguity, prevent `pubrun-hw` flakes, and preserve strong behavioral coverage (`PR-004`) |
| `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, `## Approval and execution gate` | Used bare `pytest`/`mypy`, used `N/A.`, omitted re-derivation wording in `V-01..V-05`, and omitted full scope-fence and runner-vs-manual finalize clauses | Switched to `python3 -m pytest`/`python3 -m mypy`, expanded `N/A.` to `Not applicable.` citing inspected docs, added re-derivation wording, and completed all 5 execution-contract clauses | Satisfy `technical-writing.md` Req 1, `r2-executability.md`, `r4-engineering.md`, and `s7-finalize.md:31-46` (`PR-005`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-bt`, `- Order: 3`, `- Scope-Paths:` (`src/pubrun/core.py, src/pubrun/capture/file_io.py, tests/test_explicit_api.py, tests/test_runtime_safety.py, tests/test_file_io_provenance.py, tests/test_file_registration.py`), 5 E-items in 3 task groups, no `.spec.md` file.

1. No: restores documented POSIX signal return-code parity (`-signum`) and `max_total_hash_seconds` budget enforcement without changing specs, CLI options, schema fields, or config keys.
2. Yes: adds security-containment regression coverage for `src/pubrun/core.py::_resolve_within_run_dir` (symlink escapes and `"."` targets guarding run-directory boundaries) and touches core subprocess/file-I/O provenance engines.
3. Yes: 5 E-items across 3 task groups spanning 6 files (2 core production modules and 4 test suites) in the 10-child Set `assess-bt`, with explicit coordination around pending plan `8o6o83` in `tests/test_explicit_api.py`.
4. Yes: `- Scope-Paths:` explicitly lists all 6 files.
5. Yes: an error in `_PopenPipeProxy.close` can misreport subprocess exit codes or fail `mypy --platform win32`, and an error in `ProvenanceFileProxy._update_stream_hash` can silently bypass hashing budgets or regress hot-path streaming provenance.

AW-TIER: complex

### Step R1

- Checked: every file and symbol cited in `thbepl` against the repository: `src/pubrun/core.py` (`phase.__exit__:736-848`, `_resolve_within_run_dir:1046-1069`, `report:1072-1129`, `artifact:1132-1169`, `_should_log_pubrun_print:1217-1236`, `print:1239-1328`, `popen:1896-2010`, `_PopenPipeProxy.close:1953-1987`), `src/pubrun/capture/file_io.py` (`FileIoBudgetTracker:304-460`, `register_file_provenance:1834-2134`, pending re-registration `1993-2036`, `finalize_pending_registrations:2137-2226`, `ProvenanceFileProxy._update_stream_hash:2330-2369`, `_populate_hash_fields:2710-2830`), `tests/conftest.py` (`isolated_cwd:42-53`), `tests/test_explicit_api.py` (all 1013 lines, including the 4 racy tests, 4 `Path.cwd` sites, and `8o6o83`'s untouched function at line 596), `tests/test_runtime_safety.py` (`time.sleep` sites at lines 473, 809, 918), `tests/test_file_io_provenance.py` (`Path.cwd` sites and private pins at lines 1306-1307, 1403-1409), `tests/test_file_registration.py` (`_run_manifest:27-47`), `.aw/records/plans/pending/20261127-7jd8g1-01-8o6o83-fix-background-pubrun-hw-manifest-refresh-race-in-test-repor.ipd.md`, and `docs/{configuration,manifest,api,functional_spec}.md`.
- Verified: all cited files and symbols exist; empirically confirmed on Linux that `os.popen("kill -TERM $$").close()` returns `-3840` (`-15 << 8`) and `os.popen("kill -9 $$").close()` returns `-2304` (`-9 << 8`); caught `_should_log_pubrun_print` bypassing `core.py`'s timestamped branch when `stdout_tee` is active (`PR-001`) and `round(self._stream_elapsed, 6)` rounding real small-chunk timings to `0.0` (`PR-002`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, deferred-item carrier (`- Carrier: 8o6o83`), runtime-demonstration reachability, re-derivation convention (`r2-executability.md:65`), and all 5 execution-contract clauses in `## Approval and execution gate`.
- Verified: `PR-001` through `PR-005` ensured every targeted coverage branch in `V-05` is genuinely reachable by the tests in `E-03` and `E-04`, eliminated potential test flakes, and completed the execution gate contract.

### Step R3

- Checked: full security and privacy rubric (`r3-security.md` B) across `src/pubrun/core.py`, `src/pubrun/capture/file_io.py`, and the `TEST-C2` symlink-escape tests.
- Verified:
  - Run-directory containment (`_resolve_within_run_dir`): `E-04` bullet 1 pins symlink-to-outside-directory escapes, symlink-to-`manifest.json` overwrites, and `"."` / `"./"` targets for `pubrun.artifact()` and `pubrun.report()`, verifying `manifest.json` remains intact.
  - Subprocess provenance (`pubrun.popen`): `_PopenPipeProxy.close` preserves `_manual_argv` redaction and `_manual_error_detail` safe logging while fixing POSIX wait-status decoding.
  - Hashing DoS / budget bounds (`file_io.py`): timing every small-chunk `update()` and adding a lock-free `self._stream_elapsed > budget.max_total_hash_seconds` abort closes the small-chunk timing bypass that allowed workloads doing <64 KiB reads/writes to ignore `max_total_hash_seconds`.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - A/C/D: `E-01` keeps Windows `sys.platform == "win32"` narrowing intact for `mypy --platform win32` and guards POSIX wait-status macros with `exit_status >= 0` and non-bool checks; `E-02` preserves the zero-timer fast path when `max_total_hash_seconds == 0.0` and keeps the 64 KiB locked `check_stream_progress` throttle while preventing small-chunk timing bypass; `E-03` and `E-04` eliminate `pubrun-hw` races, fixed-sleep thread handshakes, private-slot test pins, and redundant `Path.cwd` overwrites.
  - E: Command 1 runs all 4 affected suites under `python3 -m pytest -p randomly` with `--cov=pubrun.core --cov=pubrun.capture.file_io --cov-report=term-missing`, and Command 2 runs 3-OS `mypy`.
  - Right-sizing: 5 E-items in 3 task groups across 6 Scope-Paths; each E-item is focused and verifiable.
  - `## Spec / documentation sync`: substantiated against `docs/configuration.md`, `docs/manifest.md`, `docs/api.md`, and `docs/functional_spec.md`.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `_should_log_pubrun_print` skipping `core.py`'s timestamped `pubrun.print` lines (`PR-001`) and `round(..., 6)` flakiness on small-chunk real timing (`PR-002`).
  2. Testing and regression: caught `os.WIFSIGNALED` on negative integers with non-zero low byte and Windows portability of `kill -TERM` (`PR-003`), distinguished the 2 thread-handshake sleeps from the bounded child-exit poll (`PR-004`), and prevented a `pubrun-hw` race in the new symlink-escape test (`PR-004`).
  3. UI / UX: verified `pubrun.popen` records accurate `-15`/`-9` exit codes matching `pubrun.subprocess.run` and `SubprocessSpy`.
  4. Architect: verified clean separation between lock-free single-file caps and 64 KiB throttled locked `check_stream_progress` in `file_io.py`, and clean non-overlap with pending plan `8o6o83`.
  5. Software engineer: verified 3-OS `mypy` compatibility and removal of fragile manual `Path.cwd` mutations in favor of autouse `isolated_cwd`.
  6. Power user: verified `max_total_hash_seconds == 0.0` keeps the zero-timer streaming fast path with no overhead when time caps are unused.
  7. Novice: added a Mermaid scope diagram mapping each fix to its test file and validation pass.
  8. Stakeholder: confirmed full coverage of `BUG-C5`, `BUG-E3`, `TEST-C1`/`TEST-I3`, `TEST-C2`, `TEST-C5`, `TEST-C6`, `TEST-C7`, `TEST-C9`, and `TEST-I7` assigned by orchestrator `n6250e`.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 3 task groups, 6 Scope-Paths, already Order 03 of 10-child Set `assess-bt`).
- Confirmed: each E-item is concise, bounded, and naturally paired (`E-01 -> E-03`, `E-02 -> E-04`, `E-05` validation). No further split is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-bt` (orchestrator `n6250e` and sibling children `wcjdbu`, `ndobra`, `qum7gf`, `kk83rk`, `n39jh9`, `dqaj9a`, `kgoymu`, `4eo4z2`, `37sth0`) plus standalone pending plan `8o6o83`.
- Verified: strictly disjoint `Scope-Paths` across all 10 children in Set `assess-bt`; `thbepl` explicitly defers `tests/test_explicit_api.py::test_report_and_artifact_reject_blank_and_reserved_names_case_insensitively` to `8o6o83` (`- Carrier: 8o6o83`) so both plans merge cleanly in either order; `thbepl` deliverables, `Order: 3`, and `Item-Dependencies: none` align with `n6250e` E-03 and child table row 03.

### Step S5

- Checked: `## Open questions` contains `None.`. The one deferred item carries `- Carrier: 8o6o83`. All five findings (`PR-001` through `PR-005`) had `Low` overall Remediation Risk, were settled by repository code and documented workflow policy, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` A, E | `.aw/records/plans/pending/20261127-assess-bt-03-thbepl-core-explicit-api-file-io-streaming-timing-and-capture-test.ipd.md:52,156` vs `src/pubrun/core.py:1217-1295` | `E-03` bullet 2(b) tested `pubrun.print` timestamped multi-line output with bare `console.capture_mode="standard"`, where active `stdout_tee` causes `_should_log_pubrun_print` to return `False` and leaves `core.py`'s timestamp formatting branch (`core.py:1282-1292`) unexecuted and uncovered. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-03` bullet 2(b) and `## Project conventions discovered` to configure `console={"capture_mode": "standard", "non_tty_mode": "off"}` so `_should_log_pubrun_print` returns `True` and `core.py`'s multi-line timestamp formatting branch is exercised and verified (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A, E | `.aw/records/plans/pending/20261127-assess-bt-03-thbepl-core-explicit-api-file-io-streaming-timing-and-capture-test.ipd.md:43,60,141` vs `src/pubrun/capture/file_io.py:2330-2369,2758-2802` | `E-02` lacked a lock-free single-file `self._stream_elapsed > budget.max_total_hash_seconds` early-abort guard for slow small-chunk streams, and `E-04` bullet 2 did not specify a deterministic stepped `file_io.time.monotonic` fake clock, risking flakes where fast CPUs round `hash_duration_seconds` to `0.0` at `round(..., 6)`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the lock-free single-file time-cap early-abort guard in `E-02` (retaining 64 KiB locked `check_stream_progress` throttling and `close()` cumulative checks) and required a stepped `file_io.time.monotonic` fake clock for `BUG-E3` in `E-04` bullet 2 (recommendation strength: `very strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r2-executability.md` / `r4-engineering.md` A, D, E | `.aw/records/plans/pending/20261127-assess-bt-03-thbepl-core-explicit-api-file-io-streaming-timing-and-capture-test.ipd.md:37,52` vs `src/pubrun/core.py:1961-1967` | `E-01` omitted `exit_status >= 0` and `not isinstance(exit_status, bool)` guards before `os.WIFEXITED`/`os.WIFSIGNALED` (so a negative integer with a non-zero low byte would misdecode via `os.WIFSIGNALED`), and `E-03` bullet 2(a) did not mark `kill -TERM $$` POSIX-only. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `exit_status >= 0` and non-bool guards in `E-01` and marked the `kill -TERM $$` / `kill -9 $$` test POSIX-only (`sys.platform == "win32"` skip) while keeping `exit 5` and double-`close()` cross-platform in `E-03` (recommendation strength: `strong`). |
| PR-004 | MEDIUM | IN-SCOPE | `r1-references.md` / `r2-executability.md` / `r4-engineering.md` E | `.aw/records/plans/pending/20261127-assess-bt-03-thbepl-core-explicit-api-file-io-streaming-timing-and-capture-test.ipd.md:59-61` vs `tests/test_runtime_safety.py:473,809,918`, `src/pubrun/core.py:1046-1069`, `tests/test_file_io_provenance.py:1306-1307,1403-1409`, `src/pubrun/capture/file_io.py:1993-2036` | `E-04` did not distinguish the two thread-handshake sleeps (`_fake_hw_worker`, concurrent `ConsoleInterceptor`) from the bounded child-exit poll in `test_runtime_safety.py`, omitted `hardware.depth="off"` in symlink-escape tests (and conflated `report(".")` with `artifact(".")`), omitted observable zero-fallback-read assertions when dropping `TEST-C9` private pins, and left `TEST-C5` pending re-registration assertions terse. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Named the exact two thread-handshake sleep sites in `test_runtime_safety.py`, required `capture={"hardware": {"depth": "off"}}` and `artifact(".")`/`artifact("./")` in symlink-escape tests, added observable `extra_read_bytes == 0` / `bytes_hashed == 0` assertions in `test_file_io_provenance.py`, and detailed `TEST-C5` pending re-registration assertions in `test_file_registration.py` (recommendation strength: `strong`). |
| PR-005 | MEDIUM | IN-SCOPE | `p-proofread.md` / `r2-executability.md` / `r4-engineering.md` E / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-bt-03-thbepl-core-explicit-api-file-io-streaming-timing-and-capture-test.ipd.md:26-29,112-126,135-169` vs `.aw/system/workflows/technical-writing/technical-writing.md:29,40-46`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46`, `.aw/system/workflows/plan-review/steps/r2-executability.md:65` | Plan lacked a Mermaid diagram for its 6-file scope (Req 12(a)), used bare `pytest`/`mypy`, used `N/A.` without citing inspected docs, lacked re-derivation wording in `V-01..V-05`, and omitted full scope-fence and runner-vs-manual finalize clauses in `## Approval and execution gate`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added a Mermaid `flowchart LR` for all 6 Scope-Paths, switched to `python3 -m pytest` and `python3 -m mypy`, expanded `N/A.` to `Not applicable.` citing inspected docs, added re-derivation wording to `V-01..V-05`, and completed all 5 execution-contract clauses (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `thbepl` | `complex` | `standard` | Touches core explicit subprocess/file-I/O engines (`src/pubrun/core.py`, `src/pubrun/capture/file_io.py`) and run-directory symlink containment tests across 6 files in 10-child Set `assess-bt`, coordinating with pending plan `8o6o83`; answers Yes to tier questions 2, 3, and 5 (`steps/t-tier.md`). | yes |
| D-2 | Whether to add a lock-free `self._stream_elapsed > budget.max_total_hash_seconds` abort inside `ProvenanceFileProxy._update_stream_hash` | Add the lock-free single-file time-cap abort immediately after updating `self._stream_elapsed`, while keeping locked `budget.check_stream_progress` at 64 KiB intervals and on `close()` | Wait until 64 KiB or `close()` to check `max_total_hash_seconds` | Matches the existing lock-free per-file `max_hash_bytes` guard (`src/pubrun/capture/file_io.py:2344-2351`), adds zero lock acquisitions on small chunks, and prevents slow small-chunk streams from wasting up to 64 KiB of hashing after already exceeding `max_total_hash_seconds`. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; every revision (`PR-001` through `PR-005`) was swept across `## Goal`, the Mermaid diagram, `E-01..E-05`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `## Required tests / validation`, `## Spec / documentation sync`, `V-01..V-05`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
