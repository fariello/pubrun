# IPD: Silent-skip hardening and vacuous or zero-assertion test repair

- Date: 2026-11-23
- Kind: child
- Concern: Testing rigor and completeness (eliminating silent bug-masking `pytest.skip` calls, zero-assertion tests, vacuous loops, tautological `.tmp` checks, and teardown leaks).
- Scope: `tests/test_capture_engines.py`, `tests/test_tracker.py`, `tests/test_quality.py`, `tests/test_new_features.py`, `tests/test_capture.py`, `tests/test_api.py`, `tests/test_manifest_schema.py`, and `tests/test_methods_multi.py`.
- Scope-Paths: tests/test_capture_engines.py, tests/test_tracker.py, tests/test_quality.py, tests/test_new_features.py, tests/test_capture.py, tests/test_api.py, tests/test_manifest_schema.py, tests/test_methods_multi.py
- Item-Dependencies: none
- Status: executed
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Remove bug-masking skips and repair zero-assertion, vacuous, and tautological tests across core and schema suites
- Work-Kind: bug
- Priority: high
- Set: test-audit
- Order: 4
- Highest E allocated: 05
- Author: Antigravity
- Id: g18xdt

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 executed (aw agy run model=Gemini-4-Neon-High): aw agy run self-finalize: g18xdt verified (set test-audit, attempt 1).
- 2026-11-24 approved (aw set): status set to approved
- 2026-11-23 /plan-review (uri/its_direct/pt3-claude-opus-5.5-1m-us): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-007, PR-008, PR-009, PR-010, PR-011
- 2026-11-23 to-review (Antigravity): authored from `/assess-testing` findings T-08 (schema/methods) and T-09.
- 2026-11-23 draft (Antigravity): created.

## Goal

Make each test named below fail when the behavior it describes breaks. Today these tests pass without checking anything in at least one of four ways: an `if` skips every assertion (zero-assertion tests), a loop runs over an empty list (vacuous tests), an assertion checks a file name the code never writes (tautological tests), or `pytest.skip` hides a failure (bug-masking skips). Two of them also leave state behind: an active run and a replaced `sys.stdout`.

The five E-items are independent: each edits one or two test files and none depends on another.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item addresses one concern executable in one focused pass. Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Repair zero-assertion and tautological core tests

- [x] E-01 In `tests/test_capture_engines.py`, make `TestGit.test_has_commit_when_in_repo`, `TestGit.test_has_branch`, and `TestGit.test_has_dirty` run against a real temporary git repository, and make `TestEnvironment.test_redacts_secrets` and `TestEnvironment.test_redaction_disabled_via_config` assert unconditionally.
  - Depends on: none
  - Expected outcome: (a) A `git_repo` fixture in `TestGit` (taking `tmp_path` and `monkeypatch`) creates `tmp_path / "repo"`, runs `git init`, `git add`, and `git commit` with `-c user.email=test@example.com -c user.name="Test User" -c commit.gpgsign=false` (so it works on a CI runner with no git identity and on a machine that signs commits), and calls `monkeypatch.chdir(repo)`. The three tests take `git_repo` and assert `result["capture_state"]["status"] == "complete"` with no `if`. `test_has_commit_when_in_repo` asserts a 40-character `commit`; `test_has_branch` asserts a non-empty string `branch`; `test_has_dirty` asserts `dirty is False`, writes an untracked file, and asserts that a second `get_git({})` reports `dirty is True`. Today the `isolated_cwd` fixture puts every test in `tmp_path`, which is not a repository, so `get_git({})` returns `unavailable` and all three `if` blocks are skipped. (b) Both `TestEnvironment` tests drop `if "TEST_API_TOKEN" in by_name:` and assert on `by_name["TEST_API_TOKEN"]` directly. `test_redacts_secrets` also asserts the redacted entry has no `"value"` key. At review, `get_environment` returned `TEST_API_TOKEN` in `filtered` mode in both cases, so the unconditional assertions pass.
  - Execution state: performed

- [x] E-02 In `tests/test_tracker.py`, make `test_atomic_manifest_write` and `test_atomic_write_cleans_temp_on_failure` look for the temporary file name the writer actually uses, and in `tests/test_api.py`, make `TestHandleInactivePolicy.test_ignore_policy_is_silent` prove that nothing is logged or printed.
  - Depends on: none
  - Expected outcome: (a) `src/pubrun/writer.py:_atomic_json_write` writes `<name>.json.<pid>.<uuid8>.tmp`, never `<name>.json.tmp`, so today's `not tmp_file.exists()` checks pass whatever the writer does. `test_atomic_manifest_write` asserts `list(tracker.run_dir.glob("*.tmp")) == []`. `test_atomic_write_cleans_temp_on_failure` asserts `list(target.parent.glob("*.tmp")) == []` and `not target.exists()`. At review the revised cleanup test failed when the `tmp_path.unlink(...)` cleanup in `_atomic_json_write` was removed. (b) `test_ignore_policy_is_silent` takes `caplog` and `capsys`, calls `annotate("silently dropped")` inside `caplog.at_level(logging.DEBUG, logger="pubrun")`, and asserts `caplog.records == []` and `capsys.readouterr() == ("", "")`. At review this version failed when `_handle_inactive` in `src/pubrun/core.py` was changed to log a warning under the `ignore` policy; the current version passed.
  - Execution state: performed

### Task group 2: Repair vacuous assertions and unsafe teardown

- [x] E-03 In `tests/test_quality.py`, make `TestDoubleStop.test_double_stop_preserves_manifest` prove that a second `stop()` leaves the manifest alone, and make `TestConsoleRestoreSafety.test_stop_preserves_third_party_wrapper` restore `sys.stdout` even when it fails.
  - Depends on: none
  - Expected outcome: (a) After the first stop the test records `data1` and `mtime1 = os.stat(manifest_path).st_mtime_ns`. It then calls `tracker.stop(outcome="failed")`, re-reads the manifest as `data2`, and asserts `data2["status"]["outcome"] == "completed"`, `data2["timing"]["elapsed_seconds"] == elapsed1`, `data2 == data1`, and `os.stat(manifest_path).st_mtime_ns == mtime1`. Today the test stops a second time and asserts nothing. A content comparison alone is not enough: at review, removing the writer's "already written" guard (`_artifacts_written` check at the top of `ArtifactWriter.write_artifacts` and again inside `_write_lock` in `src/pubrun/writer.py`) left the content identical but changed the modification time, and only the mtime assertion failed. The `"failed"` outcome catches a second stop that overwrites the recorded outcome. The revised test passed 20 of 20 runs. (b) The test takes `monkeypatch` and, before starting the interceptor, calls `monkeypatch.setattr(sys, "stdout", sys.stdout)` and `monkeypatch.setattr(sys, "stderr", sys.stderr)`, so pytest restores both streams at teardown. The manual `sys.stdout = interceptor.original_stdout` at the end is deleted.
  - Execution state: performed

- [x] E-04 Make `tests/test_capture.py::TestSubprocessSpy.test_detached_subprocess_finalized`, `tests/test_new_features.py::TestResourceWatcherTreeScope.test_tree_scope_manifest_fields`, and `tests/test_new_features.py::TestConcurrentStart.test_only_one_run_created` assert exact results and leave no child process or active run behind.
  - Depends on: none
  - Expected outcome: (a) The detached-subprocess test starts `subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"], stdin=subprocess.PIPE)`, which waits on its standard input and so is still running when `tracker.stop()` runs. Inside `try:` it calls `tracker.stop()` and asserts `p.poll() is None`; in `finally:` it calls `p.stdin.close()` and `p.wait(timeout=10)`. It then asserts exactly one manifest record with `exit_code is None`, whose `capture_state.status` is `"complete"` and which has `ended_at_utc`. Today the child sleeps 0.1 s, so whether it is still running at `stop()` depends on timing, and `for s in unwatched` asserts nothing when the list is empty. At review the revised test failed when `SubprocessSpy.finalize_all` stopped marking records complete. (b) The tree-scope test patches `pubrun.capture.resources.ResourceWatcher._poll_tree_rss` with `lambda self: 100_000_000` instead of `_get_tree_rss_linux`. That method is the single entry point on every platform; on Windows it returns 0 today, so the old patch had no effect there. The `time.sleep(0.3)` is deleted with no replacement wait, because `ResourceWatcher.stop()` takes a final measurement (`end_tree_rss = self._poll_tree_rss()` in `ResourceWatcher.stop`, `src/pubrun/capture/resources.py`). The test asserts `resources["peak_tree_rss_bytes"] == 100_000_000` and `resources["end_tree_rss_bytes"] == 100_000_000`. At review the revised test passed 15 of 15 runs, and failed when `to_manifest_dict` wrote `None` for `peak_tree_rss_bytes`; the current test passed. (c) The concurrent-start test asserts that no worker thread is alive after `join`, that `len(runs) == 5`, that all five are one run, and that `runs[0].ref_count == 5`. In `finally:` it calls `pubrun.stop()` once per entry in `runs`, then asserts `runs[0].is_active is False` and `get_current_run() is None`. Today it calls `pubrun.stop()` once; at review that left the run active with `ref_count == 4`. The unused `_active_run` import is removed.
  - Execution state: performed

### Task group 3: Harden silent skips and expand schema contract coverage

- [x] E-05 Remove the bug-masking skips from `tests/test_manifest_schema.py` and `tests/test_methods_multi.py`, correct the stale module docstring, and add schema tests for the `meta_ref`, `determinism`, and `artifacts` manifest sections.
  - Depends on: none
  - Expected outcome: (a) In `test_startup_manifest_conforms_to_schema`, the read loop catches only `PermissionError`, and retries it only when `sys.platform == "win32"` and fewer than 10 attempts have failed; otherwise it re-raises. `json.JSONDecodeError` and `FileNotFoundError` are no longer caught, and the trailing `pytest.skip(...)` is deleted. The retry stays for Windows because commit `28ad814` added it after a `PermissionError` on the `windows-3.14` CI job; a decode or missing-file error cannot be a lock, because `start()` writes the manifest synchronously with an atomic `os.replace`. Add `import sys` to the module imports. (b) Replace the module docstring's point 2, which says whole-manifest drift is tracked "with an xfail", with text saying whole real manifests are validated as a hard gate, and that the xfail was removed at the 2026-07-09 schema reconciliation (`test_full_manifest_conforms_to_schema`). (c) Add `test_populated_meta_ref_manifest_conforms`: produce a real manifest with `_make_manifest(tmp_path, meta_ref="meta.json")`, assert `manifest["meta_ref"] == "meta.json"`, and validate it. (d) Add `test_populated_determinism_and_artifacts_sections_conform`. No code in `src/pubrun/` writes a `determinism` or `artifacts` section (only the `det = manifest.get("determinism")` read in `src/pubrun/report/reproducibility.py` touches `determinism`, and `pubrun.artifact()` writes a file and an event, not a manifest entry), so a live run cannot populate them. The test takes a real manifest from `_make_manifest`, sets `determinism` to a section with `python_hash_seed` (`{"representation": "plain", "value": "0"}`), two `registered_seeds` entries, and `capture_state`, sets `artifacts` to one fully populated entry (`modified_at_utc` as an epoch float, as the schema's `utc_datetime` requires) and one with only `role` and `path`, and validates it. It then asserts `jsonschema.ValidationError` for a seed entry with no `value` and for an artifact with `size_bytes: -1`. (e) In `tests/test_methods_multi.py::TestSingleRunParity.test_aggregate_of_one_equals_single`, delete `pytest.importorskip("pubrun.report.methods")`; the module already imports `pubrun.report.methods` at the top, so the skip could never fire. At review, with every E-item applied, the two new schema tests failed when `schemas/manifest.schema.json` was temporarily changed to make `meta_ref` null-only and seed values string-only.
  - Execution state: performed

## Project conventions discovered (Step 0)

- `tests/conftest.py:isolated_cwd` is `autouse=True` and changes every test into `tmp_path`, which is outside any git repository; a test that needs a repository must create one inside `tmp_path`. `tests/test_capture_engines.py::TestGit::test_combined_rev_parse_reduces_spawns_on_real_repo` already does this.
- `src/pubrun/writer.py:_atomic_json_write` writes a uniquely named temporary file, `<name>.json.<pid>.<uuid8>.tmp`, never `<name>.json.tmp`, and removes it if `os.replace` fails.
- `tests/test_manifest_schema.py` begins with `jsonschema = pytest.importorskip("jsonschema")`, so the whole module skips when `jsonschema` is missing. `jsonschema` is in the `dev` extra (`"jsonschema>=4.0"` in `pyproject.toml`), which every CI job installs, so this plan leaves that skip in place.
- `AGENTS.md` "Matrix-validation discipline": changes whose behavior varies by OS must pass the full CI matrix (3 OS x Python 3.8 to 3.14). E-01 (git on Windows), E-04 (subprocess standard input), and E-05(a) (the Windows-only retry) are such changes.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| T-08 (part) | High | Low | Testing expert / QA engineer | `tests/test_manifest_schema.py:test_startup_manifest_conforms_to_schema`; `tests/test_methods_multi.py:test_aggregate_of_one_equals_single` | Silent skips on `JSONDecodeError`/`FileNotFoundError` and internal `pubrun.report.methods` import mask real regressions. |
| T-09 | High | Low | Testing expert | `tests/test_capture_engines.py:TestGit`, `TestEnvironment`; `tests/test_tracker.py`; `tests/test_quality.py:TestDoubleStop`, `TestConsoleRestoreSafety`; `tests/test_new_features.py`; `tests/test_capture.py:TestSubprocessSpy`; `tests/test_api.py:test_ignore_policy_is_silent` | Zero-assertion git/env tests, vacuous double-stop and detached-subprocess tests, tautological `.json.tmp` checks, and unguarded `sys.stdout` mutation. |

## Proposed changes (ordered, validatable)

1. Repair `TestGit` and `TestEnvironment` in `tests/test_capture_engines.py` (E-01; Remediation Risk: Low).
2. Fix the `.tmp` glob assertions in `tests/test_tracker.py` and the silence check in `tests/test_api.py` (E-02; Remediation Risk: Low).
3. Complete the double-stop assertions and the `sys.stdout` restore in `tests/test_quality.py` (E-03; Remediation Risk: Low).
4. Make `test_detached_subprocess_finalized`, `test_tree_scope_manifest_fields`, and `test_only_one_run_created` exact and leak-free in `tests/test_capture.py` and `tests/test_new_features.py` (E-04; Remediation Risk: Low).
5. Remove bug-masking skips and add `meta_ref`, `determinism`, and `artifacts` schema tests in `tests/test_manifest_schema.py` and `tests/test_methods_multi.py` (E-05; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Silent skips in `tests/test_liveness.py` are owned by `7y0gmc`.
  - Carrier: 7y0gmc
- Silent skips in `tests/test_status.py` are owned by `ic6z4s`.
  - Carrier: ic6z4s
- Silent skips in `tests/test_sanitize_paths.py` are owned by `2mwjjw`.
  - Carrier: 2mwjjw
- Running the changed tests on the GitHub Actions matrix (Windows and macOS in particular) requires a push, and pushing requires explicit human instruction (`AGENTS.md` agent execution contract). Local validation covers Linux.
  - Carrier-Declined: a push needs explicit human authorization, so no plan can carry it; GitHub Actions runs the matrix automatically on the next push or pull request to `main`.
- Whether `pubrun` itself should write `determinism` and `artifacts` manifest sections. The schema declares both as optional and `src/pubrun/report/reproducibility.py` reads `determinism` when present; E-05(d) tests the schema contract for both without production changes.
  - Carrier-Declined: no defect was observed; the sections are optional in the schema, and adding them is a feature decision outside this test-only plan.

## Scope check

- Over-scope: none.
- Under-scope: none. Every file an E-item edits is listed in `- Scope-Paths:`. No production file changes; the mutation checks in the V-items edit `src/pubrun/` and `schemas/manifest.schema.json` only temporarily and restore them before evidence is recorded.

## Required tests / validation

- Run `python3 -m pytest tests/test_capture_engines.py tests/test_tracker.py tests/test_quality.py tests/test_new_features.py tests/test_capture.py tests/test_api.py tests/test_manifest_schema.py tests/test_methods_multi.py -v -rs`. Until sibling `bzi46m` E-01 lands, `addopts` adds `--cov`, which needs `pytest-cov` (in the `dev` extra).
- Confirm the `-rs` summary lists no skipped test.
- Run the same subset with `-p randomly --randomly-seed=12345` to check order independence. At review, with every E-item applied, both runs gave `248 passed`, and the full suite in random order (`python3 -m pytest tests/ benchmarks/test_pull_submissions.py -p randomly --randomly-seed=12345 -q`) gave `1904 passed, 2 skipped in 442.72s`, against `1902 passed, 2 skipped` without the change (the two new schema tests).
- Run `python3 scripts/sanitize_paths.py --check --all`.

## Spec / documentation sync

N/A with reason: test-only hardening; no production code, `.spec.md`, schema, or user-facing behavior changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

Mutation-check rule for V-02 to V-05: apply the named one-line change to the production file, run the named test, paste the failing output, restore the file with `git checkout -- <file>`, and paste `git status --short src/ schemas/` showing no change.

- [x] V-01 validates E-01
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_capture_engines.py -v -rs -k "TestGit or TestEnvironment"` with 0 failures and 0 skips. (2) Pasted output of `grep -n 'if result\["capture_state"\]\["status"\] == "complete"\|if "TEST_API_TOKEN" in by_name' tests/test_capture_engines.py` showing no match.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_capture_engines.py -v -rs -k "TestGit or TestEnvironment"`:
      `collected 38 items / 20 deselected / 18 selected`
      `tests/test_capture_engines.py::TestEnvironment::test_redacts_secrets PASSED`
      `tests/test_capture_engines.py::TestEnvironment::test_redaction_disabled_via_config PASSED`
      `tests/test_capture_engines.py::TestGit::test_has_commit_when_in_repo PASSED`
      `tests/test_capture_engines.py::TestGit::test_has_branch PASSED`
      `tests/test_capture_engines.py::TestGit::test_has_dirty PASSED`
      `====================== 18 passed, 20 deselected in 0.28s =======================` (0 failures, 0 skips).
    - (2) `grep -n 'if result\["capture_state"\]\["status"\] == "complete"\|if "TEST_API_TOKEN" in by_name' tests/test_capture_engines.py`: `(no matches, exit=1)`.
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_tracker.py tests/test_api.py -v` with 0 failures, and the diff showing `glob("*.tmp")` and the `caplog.records == []` and `capsys` assertions. (2) Mutation check: delete the `tmp_path.unlink(missing_ok=True)` cleanup in `src/pubrun/writer.py:_atomic_json_write`; `test_atomic_write_cleans_temp_on_failure` fails. (3) Mutation check: in `src/pubrun/core.py:_handle_inactive`, change `elif action == "warn":` to `else:`; `test_ignore_policy_is_silent` fails.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_tracker.py tests/test_api.py -v`: `collected 68 items` -> `============================== 68 passed in 5.79s ==============================` (0 failures). Diff in `tests/test_tracker.py` asserts `list(tracker.run_dir.glob("*.tmp")) == []`, `list(target.parent.glob("*.tmp")) == []`, and `not target.exists()`. Diff in `tests/test_api.py` runs `annotate("silently dropped")` under `caplog.at_level(logging.DEBUG, logger="pubrun")` and asserts `caplog.records == []` and `capsys.readouterr() == ("", "")`.
    - (2) Mutation check (removed `tmp_path.unlink(missing_ok=True)` in `src/pubrun/writer.py`): `tests/test_tracker.py::test_atomic_write_cleans_temp_on_failure FAILED` (`AssertionError: assert [PosixPath('...output.json.<pid>.<uuid8>.tmp')] == []`, `1 failed in 0.17s`), restored via `git checkout -- src/pubrun/writer.py`.
    - (3) Mutation check (changed `elif action == "warn":` to `else:` in `src/pubrun/core.py`): `tests/test_api.py::TestHandleInactivePolicy::test_ignore_policy_is_silent FAILED` (`assert [<LogRecord: pubrun, 30, ..., "pubrun.annotate() dropped: No active run.">] == []`, `1 failed in 0.16s`), restored via `git checkout -- src/pubrun/core.py`.
    - `git status --short src/ schemas/`: empty output (exit 0).
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_quality.py -v` with 0 failures, and the diff showing the post-second-stop comparison (outcome, elapsed time, content, mtime) and the `monkeypatch.setattr(sys, "stdout", ...)` guard. (2) Mutation check: remove both `if self._artifacts_written and getattr(self.run, "_finalized", False): return True` guards in `src/pubrun/writer.py`; `test_double_stop_preserves_manifest` fails.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_quality.py -v`: `collected 41 items` -> `============================== 41 passed in 0.40s ==============================` (0 failures). Diff in `tests/test_quality.py` records `mtime1 = os.stat(manifest_path).st_mtime_ns`, calls `tracker.stop(outcome="failed")`, asserts `data2["status"]["outcome"] == "completed"`, `data2["timing"]["elapsed_seconds"] == elapsed1`, `data2 == data1`, and `os.stat(manifest_path).st_mtime_ns == mtime1`; `test_stop_preserves_third_party_wrapper` calls `monkeypatch.setattr(sys, "stdout", sys.stdout)` and `monkeypatch.setattr(sys, "stderr", sys.stderr)` before `interceptor.start()` and removes the manual `sys.stdout = interceptor.original_stdout` restore.
    - (2) Mutation check (removed both `if self._artifacts_written and getattr(self.run, "_finalized", False): return True` guards in `src/pubrun/writer.py`): `tests/test_quality.py::TestDoubleStop::test_double_stop_preserves_manifest FAILED` (`AssertionError: assert 1795546185813427244 == 1795546185804427263` on `os.stat(manifest_path).st_mtime_ns == mtime1`, `1 failed in 0.20s`), restored via `git checkout -- src/pubrun/writer.py`.
    - `git status --short src/ schemas/`: empty output (exit 0).
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_capture.py tests/test_new_features.py -v` with 0 failures, and the diff showing `len(unwatched) == 1`, `peak_tree_rss_bytes == 100_000_000`, no `time.sleep` in the tree-scope test, and one `pubrun.stop()` per started reference. (2) Mutation check: delete the two lines in `SubprocessSpy.finalize_all` (`src/pubrun/capture/subprocesses.py`) that set a `partial` record's status to `complete`; `test_detached_subprocess_finalized` fails. (3) Mutation check: in `ResourceWatcher.to_manifest_dict` (`src/pubrun/capture/resources.py`), write `None` for `peak_tree_rss_bytes`; `test_tree_scope_manifest_fields` fails.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_capture.py tests/test_new_features.py -v`: `collected 58 items` -> `============================== 58 passed in 1.94s ==============================` (0 failures). Diff in `tests/test_capture.py` adds `assert p.poll() is None` and `unwatched = [s for s in subs if s["exit_code"] is None]; assert len(unwatched) == 1` while preserving the executed `focjwv` (`edc6343e`) contract (`ended_at_utc is None`, `capture_state == {"status": "partial", "detail": "child process not waited on before finalization"}`; see decision `D-01`). Diff in `tests/test_new_features.py` patches `ResourceWatcher._poll_tree_rss`, deletes `time.sleep(0.3)`, asserts `peak_tree_rss_bytes == 100_000_000` and `end_tree_rss_bytes == 100_000_000`, removes unused `_active_run`, checks worker threads / `len(runs) == 5` / `runs[0].ref_count == 5`, calls `pubrun.stop()` once per entry in `runs` inside `finally:`, and asserts `runs[0].is_active is False` and `get_current_run() is None`.
    - (2) Mutation check (adapted to executed `focjwv` `edc6343e`, which replaced the old `complete` assignment with Phase 4's `ended_at_utc = None` and `capture_state = {"status": "partial", "detail": _UNWAITED_DETAIL}` in `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all`; removed Phase 4's finalization body): `tests/test_capture.py::TestSubprocessInterceptor::test_detached_subprocess_finalized FAILED` (`KeyError: 'ended_at_utc'`, `1 failed in 0.22s`), restored via `git checkout -- src/pubrun/capture/subprocesses.py`.
    - (3) Mutation check (set `result["peak_tree_rss_bytes"] = None` in `src/pubrun/capture/resources.py::ResourceWatcher.to_manifest_dict`): `tests/test_new_features.py::TestResourceWatcherTreeScope::test_tree_scope_manifest_fields FAILED` (`assert None == 100000000`, `1 failed in 0.25s`), restored via `git checkout -- src/pubrun/capture/resources.py`.
    - `git status --short src/ schemas/`: empty output (exit 0).
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_manifest_schema.py tests/test_methods_multi.py -v -rs` with 0 failures and 0 skips, including `test_populated_meta_ref_manifest_conforms` and `test_populated_determinism_and_artifacts_sections_conform`. (2) Pasted output of `grep -n "pytest.skip\|importorskip(\"pubrun\|JSONDecodeError\|FileNotFoundError\|xfail" tests/test_manifest_schema.py tests/test_methods_multi.py`, where any remaining match is explained (the docstring's past-tense mention of the removed xfail is expected). (3) Mutation check: in `schemas/manifest.schema.json`, set `properties.meta_ref` to `{"type": "null"}`; `test_populated_meta_ref_manifest_conforms` fails. (4) Pasted output of `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_manifest_schema.py tests/test_methods_multi.py -v -rs`: `collected 51 items`, including `tests/test_manifest_schema.py::test_populated_meta_ref_manifest_conforms PASSED` and `tests/test_manifest_schema.py::test_populated_determinism_and_artifacts_sections_conform PASSED` -> `============================= 51 passed in 12.12s ==============================` (0 failures, 0 skips). Combined 8-file run: `256 passed in 17.40s` (0 skips); random-order 8-file run (`-p randomly --randomly-seed=12345`): `256 passed in 17.99s` (0 skips); full suite (`aw suite`): `1926 passed in 149.73s (0:02:29)` (0 failures, 0 skips).
    - (2) `grep -n 'pytest.skip\|importorskip("pubrun\|JSONDecodeError\|FileNotFoundError\|xfail' tests/test_manifest_schema.py tests/test_methods_multi.py`:
      `tests/test_manifest_schema.py:12:     the temporary xfail was removed at the 2026-07-09 schema reconciliation.`
      `tests/test_manifest_schema.py:102:    Hard gate (was an xfail tripwire until the 2026-07-09 schema reconciliation): any`
      (Only the two expected past-tense docstring references to the removed xfail remain; zero skip/decode/file-not-found/importorskip matches.)
    - (3) Mutation check (set `properties.meta_ref` to `{"type": "null"}` in `schemas/manifest.schema.json`): `tests/test_manifest_schema.py::test_populated_meta_ref_manifest_conforms FAILED` (`jsonschema.exceptions.ValidationError: 'meta.json' is not of type 'null'`, `1 failed in 0.70s`), restored via `git checkout -- schemas/manifest.schema.json`.
    - (4) `python3 scripts/sanitize_paths.py --check --all`: exited 0 with no findings. `git status --short src/ schemas/`: empty output (exit 0).
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no open questions.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries (`tests/test_capture_engines.py`, `tests/test_tracker.py`, `tests/test_quality.py`, `tests/test_new_features.py`, `tests/test_capture.py`, `tests/test_api.py`, `tests/test_manifest_schema.py`, `tests/test_methods_multi.py`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`. Do not commit any change to `src/pubrun/` or `schemas/`: the mutation checks edit them only temporarily and must restore them.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit g18xdt -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize g18xdt`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize g18xdt` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
