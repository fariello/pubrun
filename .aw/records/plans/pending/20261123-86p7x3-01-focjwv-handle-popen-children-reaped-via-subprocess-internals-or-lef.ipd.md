# IPD: Handle Popen children reaped via subprocess internals or left unwaited in SubprocessSpy

- Date: 2026-11-23
- Kind: child
- Concern: Subprocess exit-code and capture-state accuracy
- Scope: Record the exit code of a `subprocess.Popen` child that the host never waits on or polls, when pubrun can observe it through public attributes (`Popen.returncode`, `Popen.poll()`, a patched `Popen.__del__`) without patching the private `Popen._internal_poll`. Record `capture_state.status = "partial"` with a `detail` for a child whose exit pubrun did not observe by `SubprocessSpy.finalize_all`. Update tests, the user-facing docs that describe the spy, and `CHANGELOG.md`.
- Scope-Paths: src/pubrun/capture/subprocesses.py, tests/test_capture.py, docs/manifest.md, docs/functional_spec.md, docs/architecture.md, docs/api.md, CHANGELOG.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Work-Kind: followup
- Priority: low
- From-Backlog: 86p7x3
- Set: 86p7x3
- Order: 1
- Highest E allocated: 05
- Author: Antigravity
- Id: focjwv
- Approval: 2026-11-24, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 approved (aw set): status set to approved
- 2026-11-24 /plan-review (uri/its_direct/pt3-claude-opus-5.5-1m-us): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-007, PR-008, PR-009
- 2026-11-24 to-review (Antigravity): graduated from backlog item `86p7x3` into a review-ready plan.
- 2026-11-24 draft (Antigravity): created.

## Goal

`SubprocessSpy` (in `src/pubrun/capture/subprocesses.py`) records each `subprocess.Popen` child in the manifest's `subprocesses` list. Today it learns the exit code only when the host calls `Popen.wait()` or `Popen.poll()`. A child the host never waits on keeps `exit_code: null`, and `SubprocessSpy.finalize_all` then marks it `capture_state.status: "complete"`, which claims a complete observation that never happened.

After this plan:

1. A child that exited, and whose exit status CPython collected through `Popen.__del__` or `subprocess._cleanup()`, or that a non-blocking `poll()` at finalization can collect, records its real integer `exit_code` with `"complete"` (code 0) or `"failed"` (nonzero).
2. A child that is still running at finalization, or whose exit status was lost, records `exit_code: null`, `ended_at_utc: null`, and `capture_state: {"status": "partial", "detail": ...}`.
3. pubrun still never patches the private `Popen._internal_poll`, and the new `Popen.__del__` hook can never block or deadlock the host program.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Harvest unwaited exit codes and mark unobserved children partial

- [x] E-01 Change `src/pubrun/capture/subprocesses.py::SubprocessSpy` to collect exit codes of unwaited children and to mark unobserved children `"partial"`, as specified in "Proposed changes" item 1.
  - Depends on: none
  - Expected outcome:
    1. `SubprocessSpy.install` also patches `subprocess.Popen.__del__`, chaining to the previous `__del__`, and `SubprocessSpy.uninstall` restores it with the same identity guard as `__init__`, `wait`, and `poll`. `Popen._internal_poll` is not patched.
    2. The `__del__` hook acquires no lock and calls no blocking function. It only appends to `collections.deque` queues that later code drains under `SubprocessSpy._lock`.
    3. A child whose `returncode` is an integer other than `sys.maxsize` when the hook runs, or when a later drain reads it, completes its record with that `exit_code` and `"complete"` (0) or `"failed"` (nonzero).
    4. A child still running when its `Popen` is dropped stays observable: the hook keeps a strong reference, the patched `Popen.__init__` drains that queue after the chained `__init__` returns (that call runs `subprocess._cleanup()`), and `finalize_all` drains it again.
    5. `finalize_all` polls each still-open record's live `Popen` once with the chained non-blocking `poll()`, outside `SubprocessSpy._lock`. A record still without an exit code gets `exit_code: None`, `ended_at_utc: None`, `elapsed_seconds` to finalization, and `capture_state = {"status": "partial", "detail": "child process not waited on before finalization"}`.
    6. A `returncode` equal to `sys.maxsize` gives `capture_state = {"status": "partial", "detail": "child exit status was collected outside pubrun and is unavailable"}` with `exit_code: None`, never `exit_code: 9223372036854775807`.
    7. `finalize_all` and `uninstall` release every strong reference the spy holds to a `Popen`.
  - Execution state: performed

- [x] E-02 Update `tests/test_capture.py` so that the tests for unwaited children have deterministic outcomes, as listed in "Proposed changes" item 2.
  - Depends on: E-01
  - Expected outcome: The tests named in "Proposed changes" item 2 exist and pass, assert on records returned by `SubprocessSpy.get_records()` or on `manifest.json`, use no fixed sleeps to decide whether a child has exited, and leave no child process running after the test.
  - Execution state: performed

- [x] E-03 Update the `## subprocesses` table in `docs/manifest.md` for the new values.
  - Depends on: E-01
  - Expected outcome: The `capture_state` row says `"complete"` for exit code 0, `"failed"` for a nonzero exit code or a failed launch (with a redacted `detail`), and `"partial"` with a `detail` while the process runs, when pubrun did not observe its exit by finalization, or when its exit status is unavailable. The phrase "and for a process still unwaited at finalization" is gone. The `exit_code` row says `null` means pubrun did not observe the exit. The `ended_at_utc` row says `null` means pubrun did not observe the end by finalization. The `elapsed_seconds` row says that for a child whose exit pubrun first observed at the next `Popen` launch or at finalization, the duration ends at that observation. Edited lines contain no em dash (U+2014) and no en dash (U+2013).
  - Execution state: performed

- [x] E-04 Update the descriptions of the patched targets and of finalization in `docs/functional_spec.md`, `docs/architecture.md`, and `docs/api.md`.
  - Depends on: E-01
  - Expected outcome:
    1. Every list of the targets `SubprocessSpy` patches names `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, and `os.system`. The lists are at `docs/functional_spec.md#15.1 Mechanism`, `docs/functional_spec.md` (the bullet starting "Enforce transactional installation"), `docs/architecture.md` (the paragraph starting "`SubprocessSpy` transparently monkey-patches", the bullet "**Live target chaining and transactional install:**", and the bullet "**Independent cleanup and hook ownership:**"), and `docs/api.md` (the table row starting "| `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` (`SubprocessSpy`)").
    2. `docs/functional_spec.md#15.2 Recorded Fields` says that finalization records the exit of an unwaited child when pubrun can observe it, and otherwise marks the record `"partial"` with a `detail`.
    3. Edited lines contain no em dash (U+2014) and no en dash (U+2013).
  - Execution state: performed

- [x] E-05 Add a `### Fixed` entry under `## [Unreleased]` in `CHANGELOG.md`.
  - Depends on: E-01
  - Expected outcome: The entry says that a `subprocess.Popen` child the program never waited on now records its exit code when pubrun can observe it, and is otherwise reported as `capture_state.status: "partial"` with a `detail` instead of `"complete"`. It names the manifest change for readers who filter on `"complete"`. It contains no em dash and no en dash.
  - Execution state: performed

## Project conventions discovered (Step 0)

- Cite code by symbol (`path::Name`), Markdown by heading (`path#Heading text`), or by a quoted content string. A line number may follow one of those as a hint, but never stands alone (`IPD-C801`).
- `src/pubrun/capture/subprocesses.py::SubprocessSpy.install` patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, and `os.system`. It keeps the previous targets in a per-install `state` dict, tags each recorded `Popen` with `_pubrun_state`, `_pubrun_rec`, and `_pubrun_idx`, and keeps per-record monotonic start times in `SubprocessSpy._start_monos`. `SubprocessSpy.uninstall` restores each target only when it still holds pubrun's wrapper.
- `SubprocessSpy._lock` is a non-reentrant `threading.Lock`. `_complete_popen_record` (a closure inside `install`) acquires it. `SubprocessSpy.finalize_all` holds it for its whole loop and today sets `capture_state.status` to `"complete"` for every record with `exit_code` `None` and no `ended_at_utc`.
- `src/pubrun/tracker.py::Run._rollback_owned_hooks` calls `SubprocessSpy.finalize_all()`, then copies the list `SubprocessSpy.get_records()`, then calls `SubprocessSpy.uninstall(owner=...)`, each in its own `try/except`.
- CPython behavior, checked on CPython 3.12.3 and 3.14.6 at review:
  - `subprocess.Popen.__del__(self, _maxsize=sys.maxsize, _warn=warnings.warn)` warns `ResourceWarning` when `returncode` is `None`, calls `self._internal_poll(_deadstate=_maxsize)`, and appends a still-running instance to `subprocess._active`.
  - On POSIX, `subprocess._cleanup()` runs at the start of every `Popen.__init__`. It polls each `subprocess._active` instance and removes those that exited. On Windows `_cleanup()` does nothing and `_active` is `None`.
  - When the exit status was already collected by someone else (for example `os.waitpid`), `_internal_poll` sets `returncode` to the `_deadstate` value `sys.maxsize`.
  - `Popen.__del__` runs at most once per object (PEP 442), even when the object is resurrected.
- `schemas/manifest.schema.json` `$defs.subprocess_record` requires only `argv` and `capture_state`, and allows `null` for `exit_code` and `ended_at_utc`. `$defs.capture_state` allows `{"status": "partial", "detail": "..."}`. No schema change is needed.
- Consumers that read subprocess records are `src/pubrun/report/diagnostics.py` (prints `exit_code`), `src/pubrun/tui/widgets/details.py::_format_subprocess_rows`, and `src/pubrun/analysis/diff.py` (counts commands). None of them reads a subprocess record's `capture_state`. `src/pubrun/report/reproducibility.py` scans only dict-valued manifest sections for `"partial"`, so a list of subprocess records adds no new finding.
- `AGENTS.md` agent execution contract: user-facing docs (`docs/*.md`, `CHANGELOG.md`) must contain no em or en dashes in authored or edited prose. Tests must exercise behavior and must not read production source with `inspect`, `ast`, regex, or substring checks.
- `AGENTS.md` "Matrix-validation discipline": a change to capture-engine output shapes, or to behavior that varies by OS, must pass the CI matrix (3 OS x Python 3.8 to 3.14). Pushing requires an explicit human instruction.

## Findings

When a program runs `p = subprocess.Popen(...)` and never calls `p.wait()` or `p.poll()`, today's `SubprocessSpy` records `exit_code: null`, and `finalize_all` then records `capture_state.status: "complete"`. Backlog item `86p7x3` says the status stays `"running"`; that is not a valid status value, and the code writes `"complete"`. Four cases occur:

1. **Exited, then garbage-collected.** `Popen.__del__` calls `_internal_poll`, which sets `returncode`. A probe at review that wrapped `Popen.__del__` read `returncode == 7` after the wrapped call returned.
2. **Still running when garbage-collected, later reaped by `subprocess._cleanup()`.** `__del__` sees `returncode is None` and parks the object in `subprocess._active`. The next `Popen()` call reaps it and removes it from `_active`, and then the object is freed. At review a `weakref.ref` to such an object was dead after `_cleanup()` ran, so a weak reference alone loses the exit code. A wrapper that kept a strong reference read `returncode == 3` afterwards.
3. **Exited but never collected.** At review `os.waitid(..., WNOWAIT)` showed exit code 7 while `p.returncode` was still `None`. A non-blocking `poll()` at finalization collects it.
4. **Still running at finalization.** No exit code exists. Today this is recorded as `"complete"`, which is false.

Two hazards constrain the design:

- **Deadlock.** The cyclic garbage collector can run `Popen.__del__` on any thread, at any allocation, including inside a `with SubprocessSpy._lock:` block. At review, a `__del__` wrapper that tried to acquire a lock already held by the same thread failed to get it within its 1-second timeout. A plain `with lock:` would block forever. The hook therefore must not take `SubprocessSpy._lock`. For the same reason, `finalize_all` must not call `_complete_popen_record` while it holds the lock.
- **Sentinel exit code.** When the exit status was collected outside `subprocess` (for example by `os.waitpid` or a `SIGCHLD` handler), `__del__` sets `returncode` to `sys.maxsize`. At review this was `9223372036854775807` on both Python versions. Recording it as an exit code would be false.

The flowchart shows how each record reaches its final state.

```mermaid
flowchart TD
    L[Spy records a Popen launch] --> W{Host calls wait or poll and it returns a code?}
    W -->|Yes| DONE[exit_code set; complete or failed]
    W -->|No| G{Popen.__del__ runs before finalize_all?}
    G -->|No| FP[finalize_all polls the live Popen once, without the lock]
    G -->|Yes| H{returncode in the hook}
    H -->|integer, not sys.maxsize| Q1[Hook queues the exit; next drain records it]
    Q1 --> DONE
    H -->|sys.maxsize| UNAV[exit_code null; partial: exit status unavailable]
    H -->|None| Q2[Hook keeps a strong reference]
    Q2 --> DR[Drain at next Popen launch or at finalize_all reads returncode]
    DR -->|integer| DONE
    DR -->|still None| FP
    FP -->|integer| DONE
    FP -->|None| PART[exit_code null; ended_at_utc null; partial: not waited on]
```

## Proposed changes (ordered, validatable)

1. **`src/pubrun/capture/subprocesses.py` (E-01):**
   - Add `import collections`, `import sys`, and `import weakref`. Add two class attributes, `SubprocessSpy._pending_exits` and `SubprocessSpy._pending_running`, each a `collections.deque`. Add `SubprocessSpy._popen_refs: Dict[int, Tuple[Dict[str, Any], Any]]`, mapping `id(rec)` to `(rec, weakref.ref(popen))`. Add `SubprocessSpy._installed_popen_del`. `install` and `uninstall` reset all four, so no `Popen` reference outlives a run.
   - In `_patched_popen_init`, store the weak reference in `_popen_refs` when the record is appended. Skip it when `weakref.ref` raises `TypeError`. Call a new drain function (described below) in a `finally` around the chained `__init__`, so it runs after both a successful and a failed launch. On POSIX that chained call has just run `subprocess._cleanup()`. A drain failure is logged at debug level and never raised to the host.
   - Split `_complete_popen_record` into a record-level `_complete_record(rec, exit_code, end_ts, end_mono)` and the existing `Popen`-level guard that calls it. `_complete_record` acquires `SubprocessSpy._lock` and acts only when `state["active"]` is true and the record's `exit_code` is still `None`. Like today, a `wait()` that returns after `finalize_all()` but before `uninstall()` still fills in the exit code, and the monotonic `elapsed_seconds` already set by `finalize_all()` is kept. Then:
     - For a `returncode` equal to `sys.maxsize`, it sets `capture_state = {"status": "partial", "detail": "child exit status was collected outside pubrun and is unavailable"}` and `ended_at_utc = None`, and leaves `exit_code` `None`.
     - Otherwise it sets `exit_code`, `ended_at_utc`, the monotonic `elapsed_seconds`, and a fresh `capture_state` dict (`"complete"` or `"failed"`) with no stale `detail` key.
     - In both cases it removes the record's `_popen_refs` entry.
   - Add `_patched_popen_del(self, *args, **kwargs)`. It calls `prev_popen_del(self, *args, **kwargs)` inside `try/finally`. In the `finally` block it does only the following, inside `try/except Exception: pass`:
     - It returns unless `getattr(self, "_pubrun_state", None) is state` and `state["active"]`.
     - If `self.returncode is None`, it appends `self` to `_pending_running`.
     - Otherwise it appends `(self._pubrun_rec, self.returncode, time.time(), time.perf_counter())` to `_pending_exits`.
     It acquires no lock and binds `time.time` and `time.perf_counter` at install time, so it also works during interpreter shutdown. Patch and restore it like the other targets, with the same identity guard, and add it to the rollback list in `install`. Do not patch `Popen._internal_poll`.
   - Add a drain function, stored as `state["drain"]`, that runs outside `SubprocessSpy._lock`:
     1. It pops every `_pending_exits` entry and passes it to `_complete_record`.
     2. It pops every `_pending_running` object. When the object's `returncode` is now set, it passes `obj._pubrun_rec`, `obj.returncode`, and the current times to `_complete_record`. When it is still `None`, it puts the object back for the next drain.
   - Rewrite `SubprocessSpy.finalize_all` in four phases:
     1. Call `state["drain"]()`.
     2. Under `SubprocessSpy._lock`, collect the live `Popen` for each record whose `exit_code` is `None` and that has no `ended_at_utc`, from `_popen_refs` or `_pending_running`. Then release the lock.
     3. Call `state["prev_popen_poll"](proc)` once per live `Popen` inside `try/except Exception`, and complete each record that returns an integer.
     4. Under the lock again, mark every record that still has `exit_code` `None` and no `ended_at_utc` key as described in E-01 outcome 5, then clear `_popen_refs` and `_pending_running`. Phase 4 sets the `ended_at_utc` key (to `None`), so a second `finalize_all()` call changes nothing.
     When the spy is not installed (`SubprocessSpy._active_state is None`), skip phases 1 to 3 and apply phase 4.
   - Rename the `finalize_all` docstring "Mark any un-waited subprocess records as complete." to describe the new behavior.
2. **`tests/test_capture.py` (E-02):** Each test that launches a child makes the child's exit deterministic: the child runs `[sys.executable, "-c", "import sys; sys.stdin.read(); sys.exit(N)"]` with `stdin=subprocess.PIPE` and exits with code `N` only when the test closes the pipe. The test waits for exit with `os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)` (POSIX only) or with the original `subprocess.Popen.poll` captured before `SubprocessSpy.install`. Every test reaps every child it starts before it returns.
   - Change `TestSubprocessInterceptor::test_detached_subprocess_finalized` to use the stdin-blocked child. After `tracker.stop()`, it asserts on `manifest.json` that the child's record has `exit_code is None`, `ended_at_utc is None`, `capture_state["status"] == "partial"`, and `capture_state["detail"] == "child process not waited on before finalization"`. Then it closes stdin and waits on the child.
   - Change `TestFinalizeAll::test_upgrades_partial_to_complete` into a test that asserts `"partial"` with the not-waited `detail` and `ended_at_utc is None` for records that have no live `Popen`. Rename it to match.
   - Change `TestSubprocessSpyMonotonicTiming::test_finalize_all_monotonic_non_collision_and_post_finalize_wait`. Before `finalize_all()`, the real child's exit must be decided: wait for it with the original `poll`. Then assert `exit_code == 0` and `"complete"` for the real record, and `"partial"` for the synthetic record. Keep the existing monotonic-duration assertions.
   - Add `test_unwaited_exited_child_exit_code_harvested_at_finalize`, parametrized over exit codes `0` and `7`. The child exits and the test waits for it with the original `poll`, so `returncode` is set without the spy's `poll`. `finalize_all()` must then record exactly that `exit_code`, with `"complete"` for 0 and `"failed"` for 7.
   - Add `test_unwaited_uncollected_child_polled_at_finalize` (skip unless `hasattr(os, "waitid")`). It waits for exit with `WNOWAIT` while `returncode` is still `None`. `finalize_all()` must record `exit_code == 7` and `"failed"`.
   - Add `test_gc_after_exit_records_exit_code`. The child exits and `returncode` is set through the original `poll`. Then `del p` and `gc.collect()`, so no live `Popen` remains for `finalize_all()` to poll. After `finalize_all()`, the record shows `exit_code == 7` and `"failed"`; this outcome is only reachable through the `__del__` hook.
   - Add `test_cleanup_reaped_child_records_exit_code` (POSIX only). It keeps `p.stdin` and `p.pid`, then runs `del p` and `gc.collect()` while the child runs, so the object enters `subprocess._active`. It closes stdin, waits with `WNOWAIT`, and launches and waits a second `Popen`. The first record must then show `exit_code == 7` before `finalize_all()` runs.
   - Add `test_externally_reaped_child_is_partial_not_sentinel` (POSIX only). It reaps the child with `os.waitpid(pid, 0)`, then runs `del p` and `gc.collect()`. After `finalize_all()`, the record has `exit_code is None` and `"partial"` with the detail "child exit status was collected outside pubrun and is unavailable". It never has `exit_code == sys.maxsize`.
   - Add `test_popen_del_hook_does_not_take_spy_lock`. In a worker thread, drop the last reference to a recorded `Popen` and run `gc.collect()` while holding `SubprocessSpy._lock`. Then join the thread with a 10-second timeout and assert it finished.
   - Add `test_uninstall_restores_popen_del`. It asserts `subprocess.Popen.__del__` is the original after `uninstall()`, and that a third-party wrapper installed after the spy stays in place.
   - Mark tests that drop a running `Popen` with `@pytest.mark.filterwarnings("ignore::ResourceWarning")`. CPython's own `__del__` warns for them.
3. **`docs/manifest.md` (E-03):** Update the `capture_state`, `exit_code`, `ended_at_utc`, and `elapsed_seconds` rows of the `## subprocesses` table as stated in E-03.
4. **`docs/functional_spec.md`, `docs/architecture.md`, `docs/api.md` (E-04):** Add `subprocess.Popen.poll` (already patched since `m780uj`, but missing from these lists) and `subprocess.Popen.__del__` to every list of patched targets named in E-04. Update `docs/functional_spec.md#15.2 Recorded Fields`.
5. **`CHANGELOG.md` (E-05):** Add the `### Fixed` entry stated in E-05.

## Deferred / out of scope (with reason)

- Running the new tests on the GitHub Actions matrix (3 OS x Python 3.8 to 3.14). `AGENTS.md` "Matrix-validation discipline" requires this for a capture-engine output change, and the `__del__` and `_cleanup()` behavior differs on Windows. A push needs an explicit human instruction, so this plan validates on Linux only and records that gap in V-02.
  - Carrier-Declined: a push needs explicit human authorization, so no plan can carry it; GitHub Actions runs the matrix automatically on the next push or pull request to `main`.
- Patching the private `Popen._internal_poll`. Backlog `86p7x3` left this open. The public hooks above cover cases 1 to 4 in Findings without depending on a CPython implementation detail.
  - Carrier-Declined: the public-hook design meets the backlog acceptance criteria, so no later work needs this patch.
- The explicit wrapper `pubrun.subprocess.Popen` (`src/pubrun/core.py::_PubrunSubprocessNamespace.Popen`) logs a manual record only on `wait()`, `communicate()`, or a completed `poll()`, so an unwaited wrapper child is not recorded at all. That path is a separate mechanism from `SubprocessSpy` and was not named in `86p7x3`.
  - Carrier-Declined: no defect report exists for the wrapper, and the wrapper writes no record that claims a false status.

## Scope check

- Over-scope: none. The three doc files besides `docs/manifest.md`, and `CHANGELOG.md`, describe the changed behavior and are added to `- Scope-Paths:`.
- Under-scope: none after review. The review added the strong-reference queue for case 2 (a weak reference alone dies when `_cleanup()` frees the object), the lock-free hook, the `sys.maxsize` sentinel handling, `finalize_all` polling outside the lock, the two other `finalize_all` tests that assert `"complete"`, the stale patched-target lists in three docs, and the `CHANGELOG.md` entry.

## Required tests / validation

- `pytest tests/test_capture.py --no-cov -q` passes, including every test named in "Proposed changes" item 2.
- `pytest tests/test_capture.py tests/test_capture_engine_bugs.py tests/test_hook_ownership_rollback.py tests/test_capture_isolation.py tests/test_pause_resume.py tests/test_tracker.py --no-cov -q` passes. These are the other suites that install `SubprocessSpy` or assert on its patched targets.
- `pytest tests/test_capture.py -k "unwaited or gc_after_exit or cleanup_reaped or externally_reaped or del_hook or popen_del" -W error::pytest.PytestUnraisableExceptionWarning --no-cov -q` passes. This shows the hook raises nothing inside `__del__`.
- The full suite (`aw suite --no-cache`) has no failure that also passes on unmodified `HEAD`. It also checks that manifests with `"partial"` subprocess records validate against `schemas/manifest.schema.json` (`tests/test_capture.py`, `tests/test_capture_isolation.py`).
- Mutation check: temporarily replace the body of `_patched_popen_del`'s `finally` block with `pass` and run `test_gc_after_exit_records_exit_code` and `test_cleanup_reaped_child_records_exit_code`; both must fail. Restore the file and confirm `git diff --stat` matches the intended edit.
- `git diff -U0 -- docs/ CHANGELOG.md | grep '^+[^+]' | grep -c '[—–]'` prints `0`.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- `docs/manifest.md` (E-03), `docs/functional_spec.md`, `docs/architecture.md`, and `docs/api.md` (E-04) describe the new behavior and the full list of patched targets.
- `CHANGELOG.md` (E-05) records a user-visible change: some subprocess records that read `"complete"` now read `"partial"`, and the exit code of an unwaited child now appears.
- No `.spec.md` file under `.aw/records/specs/` describes `SubprocessSpy`, so none is touched.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- src/pubrun/capture/subprocesses.py`, and for each of E-01 outcomes 1 to 7 name the added lines that satisfy it. (2) Paste the output of `grep -n "_internal_poll" src/pubrun/capture/subprocesses.py`; it must show no assignment to `Popen._internal_poll`. (3) Paste the output of the `-W error::pytest.PytestUnraisableExceptionWarning` run from "Required tests / validation". The behavior of each outcome is observed through the E-02 tests named in V-02.
  - Observed evidence:
    (1) Outcome-to-diff mapping for `src/pubrun/capture/subprocesses.py`:
    - Outcome 1 (`Popen.__del__` patch, chaining, identity-guarded restore, no `_internal_poll` patch): `prev_popen_del = subprocess.Popen.__del__`, `_patched_popen_del` chaining to `prev_popen_del(self, *args, **kwargs)`, `(subprocess.Popen, "__del__", _patched_popen_del, prev_popen_del)` in `targets` and rollback in `install()`, and `(subprocess.Popen, "__del__", cls._installed_popen_del, state["prev_popen_del"])` in `restores` in `uninstall()`.
    - Outcome 2 (lock-free, non-blocking `__del__` hook): `_patched_popen_del` binds `_now_wall`/`_now_mono` at install time, takes no lock, calls no blocking function, and only appends to `pending_running` or `pending_exits` (`collections.deque`) inside `try/except Exception: pass`; `_drain()` pops those deques and delegates to `_complete_record`, which acquires `SubprocessSpy._lock`.
    - Outcome 3 (integer `returncode != sys.maxsize` records `exit_code` and `"complete"`/`"failed"`): `_complete_record` sets `rec["exit_code"] = exit_code`, `rec["ended_at_utc"] = end_ts`, `rec["capture_state"] = {"status": "complete" if exit_code == 0 else "failed"}`, and monotonic `elapsed_seconds`.
    - Outcome 4 (running dropped `Popen` stays observable via strong ref and drained at next `__init__` and `finalize_all`): `_patched_popen_del` appends `self` to `pending_running` when `rc is None`; `_patched_popen_init` calls `_safe_drain()` in `finally` around `prev_popen_init` (after `subprocess._cleanup()` runs); `finalize_all` Phase 1 calls `state["drain"]()`.
    - Outcome 5 (`finalize_all` polls live `Popen` once outside `_lock`; unobserved records get `exit_code: None`, `ended_at_utc: None`, `elapsed_seconds`, `"partial"` with `"child process not waited on before finalization"`): `finalize_all` Phase 2 collects live `(rec, proc)` under `cls._lock`, Phase 3 calls `state["prev_popen_poll"](proc)` outside `cls._lock` and completes integer returns, and Phase 4 sets `rec["ended_at_utc"] = None`, monotonic `elapsed_seconds`, and `rec["capture_state"] = {"status": "partial", "detail": _UNWAITED_DETAIL}`.
    - Outcome 6 (`sys.maxsize` sentinel): `_complete_record` checks `exit_code == sys.maxsize and not isinstance(exit_code, bool)`, leaves `exit_code` `None`, sets `rec["ended_at_utc"] = None`, and sets `rec["capture_state"] = {"status": "partial", "detail": _EXTERNAL_REAP_DETAIL}`.
    - Outcome 7 (release all strong `Popen` references on `finalize_all` and `uninstall`): `finalize_all` Phase 4 clears `cls._popen_refs`, `cls._pending_running`, and `state["pending_running"]` (and local `live_procs` drops on return); `uninstall` clears `state["pending_exits"]`, `state["pending_running"]`, and resets `cls._popen_refs = {}`, `cls._pending_exits = collections.deque()`, `cls._pending_running = collections.deque()`.

    `git diff -- src/pubrun/capture/subprocesses.py`:
    ```diff
    diff --git a/src/pubrun/capture/subprocesses.py b/src/pubrun/capture/subprocesses.py
    index 0b4be66..f1a5ddb 100644
    --- a/src/pubrun/capture/subprocesses.py
    +++ b/src/pubrun/capture/subprocesses.py
    @@ -1,11 +1,14 @@
    -import os
    -import subprocess
    +import collections
     import logging
    +import os
     import shlex
    +import subprocess
    +import sys
     import threading
     import time
    +import weakref
     from contextlib import contextmanager
    -from typing import Any, Dict, List, Optional, Tuple
    +from typing import Any, Deque, Dict, List, Optional, Tuple

     _spy_local = threading.local()

    @@ -54,8 +57,14 @@ logger = logging.getLogger("pubrun")
     _original_popen_init = subprocess.Popen.__init__
     _original_popen_wait = subprocess.Popen.wait
     _original_popen_poll = subprocess.Popen.poll
    +_original_popen_del = subprocess.Popen.__del__
     _original_os_system = os.system

    +_UNWAITED_DETAIL = "child process not waited on before finalization"
    +_EXTERNAL_REAP_DETAIL = (
    +    "child exit status was collected outside pubrun and is unavailable"
    +)
    +

     def _decode_wait_status(status: Any) -> Any:
         """Convert an ``os.system`` return value to a process exit code for recording.
    @@ -87,6 +96,9 @@ class SubprocessSpy:
         _installed = False
         _records: List[Dict[str, Any]] = []
         _start_monos: Dict[int, Tuple[Dict[str, Any], float]] = {}
    +    _popen_refs: Dict[int, Tuple[Dict[str, Any], Any]] = {}
    +    _pending_exits: Deque[Tuple[Dict[str, Any], Any, float, float]] = collections.deque()
    +    _pending_running: Deque[Any] = collections.deque()
         _max_records = 5000
         _truncated = False
         _lock = threading.Lock()
    @@ -96,6 +108,7 @@ class SubprocessSpy:
         _installed_popen_init: Optional[Any] = None
         _installed_popen_wait: Optional[Any] = None
         _installed_popen_poll: Optional[Any] = None
    +    _installed_popen_del: Optional[Any] = None
         _installed_os_system: Optional[Any] = None

         @classmethod
    @@ -125,22 +138,115 @@ class SubprocessSpy:
                 prev_popen_init = subprocess.Popen.__init__
                 prev_popen_wait = subprocess.Popen.wait
                 prev_popen_poll = subprocess.Popen.poll
    +            prev_popen_del = subprocess.Popen.__del__
                 prev_os_system = os.system

    +            # Bind wall and monotonic clocks at install time so __del__ works
    +            # even if module globals are cleared during interpreter shutdown.
    +            _now_wall = time.time
    +            _now_mono = time.perf_counter
    +
    +            pending_exits: Deque[
    +                Tuple[Dict[str, Any], Any, float, float]
    +            ] = collections.deque()
    +            pending_running: Deque[Any] = collections.deque()
    +
                 state: Dict[str, Any] = {
                     "active": True,
                     "config": config,
                     "prev_popen_init": prev_popen_init,
                     "prev_popen_wait": prev_popen_wait,
                     "prev_popen_poll": prev_popen_poll,
    +                "prev_popen_del": prev_popen_del,
                     "prev_os_system": prev_os_system,
    +                "pending_exits": pending_exits,
    +                "pending_running": pending_running,
                 }

    +            def _complete_record(
    +                rec: Dict[str, Any],
    +                exit_code: Any,
    +                end_ts: float,
    +                end_mono: float,
    +            ) -> None:
    +                """Record a child's observed exit or unavailable status once under _lock."""
    +                if exit_code is None or not state["active"]:
    +                    return
    +                if rec.get("exit_code") is not None:
    +                    return
    +                try:
    +                    with cls._lock:
    +                        if not state["active"] or rec.get("exit_code") is not None:
    +                            return
    +                        cls._popen_refs.pop(id(rec), None)
    +                        entry = cls._start_monos.pop(id(rec), None)
    +                        if entry is not None and entry[0] is rec:
    +                            rec["elapsed_seconds"] = max(0.0, end_mono - entry[1])
    +                            rec["duration_clock"] = "monotonic"
    +                        if exit_code == sys.maxsize and not isinstance(exit_code, bool):
    +                            rec["ended_at_utc"] = None
    +                            rec["capture_state"] = {
    +                                "status": "partial",
    +                                "detail": _EXTERNAL_REAP_DETAIL,
    +                            }
    +                        else:
    +                            rec["exit_code"] = exit_code
    +                            rec["ended_at_utc"] = end_ts
    +                            rec["capture_state"] = {
    +                                "status": "complete" if exit_code == 0 else "failed"
    +                            }
    +                except Exception as e:
    +                    logger.debug(
    +                        f"pubrun failed to finalize subprocess record: {e}"
    +                    )
    +
    +            def _drain() -> None:
    +                """Drain lock-free Popen.__del__ queues outside SubprocessSpy._lock."""
    +                if not state["active"]:
    +                    return
    +                while True:
    +                    try:
    +                        rec, exit_code, end_ts, end_mono = pending_exits.popleft()
    +                    except IndexError:
    +                        break
    +                    _complete_record(rec, exit_code, end_ts, end_mono)
    +
    +                still_running: List[Any] = []
    +                while True:
    +                    try:
    +                        proc = pending_running.popleft()
    +                    except IndexError:
    +                        break
    +                    rc = getattr(proc, "returncode", None)
    +                    if rc is not None:
    +                        rec = getattr(proc, "_pubrun_rec", None)
    +                        if rec is not None:
    +                            _complete_record(rec, rc, time.time(), time.perf_counter())
    +                    else:
    +                        still_running.append(proc)
    +                if still_running and state["active"]:
    +                    pending_running.extend(still_running)
    +
    +            def _safe_drain() -> None:
    +                try:
    +                    _drain()
    +                except Exception as e:
    +                    logger.debug(
    +                        f"pubrun failed to drain subprocess exit queues: {e}"
    +                    )
    +
    +            state["drain"] = _drain
    +            state["complete_record"] = _complete_record
    +
                 def _patched_popen_init(
                     self: Any, args: Any, *sys_args: Any, **kwargs: Any
                 ) -> None:
                     if not state["active"] or _spy_bypassed():
    -                    return prev_popen_init(self, args, *sys_args, **kwargs)
    +                    try:
    +                        return prev_popen_init(self, args, *sys_args, **kwargs)
    +                    finally:
    +                        if state["active"]:
    +                            _safe_drain()

                     with cls._lock:
                         if not state["active"]:
    @@ -152,7 +258,11 @@ class SubprocessSpy:
                             should_record = True

                     if not should_record:
    -                    return prev_popen_init(self, args, *sys_args, **kwargs)
    +                    try:
    +                        return prev_popen_init(self, args, *sys_args, **kwargs)
    +                    finally:
    +                        if state["active"]:
    +                            _safe_drain()

                     start_time = time.time()
                     start_mono = time.perf_counter()
    @@ -188,6 +298,8 @@ class SubprocessSpy:
                                     "capture_state": {"status": "failed", "detail": detail},
                                 })
                         raise
    +                finally:
    +                    _safe_drain()

                     rec: Dict[str, Any] = {
                         "argv": argv_list,
    @@ -196,6 +308,10 @@ class SubprocessSpy:
                         "exit_code": None,
                         "capture_state": {"status": "partial"},
                     }
    +                try:
    +                    popen_ref: Optional[Any] = weakref.ref(self)
    +                except TypeError:
    +                    popen_ref = None
                     with cls._lock:
                         if state["active"]:
                             self._pubrun_state = state
    @@ -203,6 +319,8 @@ class SubprocessSpy:
                             self._pubrun_idx = len(cls._records)
                             cls._records.append(rec)
                             cls._start_monos[id(rec)] = (rec, start_mono)
    +                        if popen_ref is not None:
    +                            cls._popen_refs[id(rec)] = (rec, popen_ref)

                 def _complete_popen_record(self: Any, exit_code: Any) -> None:
                     """Record a reaped child's exit once (idempotent across wait/poll)."""
    @@ -210,33 +328,11 @@ class SubprocessSpy:
                         return
                     if getattr(self, "_pubrun_state", None) is not state:
                         return
    -                rec0 = getattr(self, "_pubrun_rec", None)
    -                if rec0 is None or rec0.get("exit_code") is not None:
    +                rec = getattr(self, "_pubrun_rec", None)
    +                if rec is None or rec.get("exit_code") is not None:
                         # Already recorded: repeated poll() calls stay cheap.
                         return
    -                end_ts = time.time()
    -                end_mono = time.perf_counter()
    -                try:
    -                    with cls._lock:
    -                        if (
    -                            state["active"]
    -                            and getattr(self, "_pubrun_state", None) is state
    -                        ):
    -                            rec = getattr(self, "_pubrun_rec", None)
    -                            if rec is not None and rec.get("exit_code") is None:
    -                                rec["exit_code"] = exit_code
    -                                rec["ended_at_utc"] = end_ts
    -                                rec["capture_state"]["status"] = (
    -                                    "complete" if exit_code == 0 else "failed"
    -                                )
    -                                entry = cls._start_monos.pop(id(rec), None)
    -                                if entry is not None and entry[0] is rec:
    -                                    rec["elapsed_seconds"] = max(0.0, end_mono - entry[1])
    -                                    rec["duration_clock"] = "monotonic"
    -                except Exception as e:
    -                    logger.debug(
    -                        f"pubrun failed to finalize subprocess record wait hook: {e}"
    -                    )
    +                _complete_record(rec, exit_code, time.time(), time.perf_counter())

                 def _patched_popen_wait(self: Any, *args: Any, **kwargs: Any) -> int:
                     exit_code = prev_popen_wait(self, *args, **kwargs)
    @@ -248,6 +344,27 @@ class SubprocessSpy:
                     _complete_popen_record(self, exit_code)
                     return exit_code

    +            def _patched_popen_del(self: Any, *args: Any, **kwargs: Any) -> None:
    +                try:
    +                    prev_popen_del(self, *args, **kwargs)
    +                finally:
    +                    try:
    +                        if (
    +                            getattr(self, "_pubrun_state", None) is state
    +                            and state["active"]
    +                        ):
    +                            rc = getattr(self, "returncode", None)
    +                            if rc is None:
    +                                pending_running.append(self)
    +                            else:
    +                                rec = getattr(self, "_pubrun_rec", None)
    +                                if rec is not None and rec.get("exit_code") is None:
    +                                    pending_exits.append(
    +                                        (rec, rc, _now_wall(), _now_mono())
    +                                    )
    +                    except Exception:
    +                        pass
    +
                 def _patched_os_system(command: str) -> int:
                     if not state["active"] or _spy_bypassed():
                         return prev_os_system(command)
    @@ -336,6 +453,9 @@ class SubprocessSpy:
                 cls._max_records = max_records
                 cls._records = []
                 cls._start_monos = {}
    +            cls._popen_refs = {}
    +            cls._pending_exits = pending_exits
    +            cls._pending_running = pending_running
                 cls._truncated = False
                 cls._config = config

    @@ -344,6 +464,7 @@ class SubprocessSpy:
                     (subprocess.Popen, "__init__", _patched_popen_init, prev_popen_init),
                     (subprocess.Popen, "wait", _patched_popen_wait, prev_popen_wait),
                     (subprocess.Popen, "poll", _patched_popen_poll, prev_popen_poll),
    +                (subprocess.Popen, "__del__", _patched_popen_del, prev_popen_del),
                     (os, "system", _patched_os_system, prev_os_system),
                 ]
                 try:
    @@ -364,13 +485,18 @@ class SubprocessSpy:
                     cls._installed_popen_init = None
                     cls._installed_popen_wait = None
                     cls._installed_popen_poll = None
    +                cls._installed_popen_del = None
                     cls._installed_os_system = None
    +                cls._popen_refs = {}
    +                cls._pending_exits = collections.deque()
    +                cls._pending_running = collections.deque()
                     raise

                 cls._active_state = state
                 cls._installed_popen_init = _patched_popen_init
                 cls._installed_popen_wait = _patched_popen_wait
                 cls._installed_popen_poll = _patched_popen_poll
    +            cls._installed_popen_del = _patched_popen_del
                 cls._installed_os_system = _patched_os_system
                 cls._owner = owner
                 cls._installed = True
    @@ -388,6 +514,8 @@ class SubprocessSpy:
                 state = cls._active_state
                 if state is not None:
                     state["active"] = False
    +                state["pending_exits"].clear()
    +                state["pending_running"].clear()
                     restores = [
                         (
                             subprocess.Popen,
    @@ -407,6 +535,12 @@ class SubprocessSpy:
                             cls._installed_popen_poll,
                             state["prev_popen_poll"],
                         ),
    +                    (
    +                        subprocess.Popen,
    +                        "__del__",
    +                        cls._installed_popen_del,
    +                        state["prev_popen_del"],
    +                    ),
                         (
                             os,
                             "system",
    @@ -431,10 +565,14 @@ class SubprocessSpy:
                 cls._installed_popen_init = None
                 cls._installed_popen_wait = None
                 cls._installed_popen_poll = None
    +            cls._installed_popen_del = None
                 cls._installed_os_system = None
                 # BUG-09: Clear records on uninstall to prevent cross-run leakage.
                 cls._records = []
                 cls._start_monos = {}
    +            cls._popen_refs = {}
    +            cls._pending_exits = collections.deque()
    +            cls._pending_running = collections.deque()
                 cls._truncated = False

         @classmethod
    @@ -453,19 +591,88 @@ class SubprocessSpy:

         @classmethod
         def finalize_all(cls) -> None:
    -        """Mark any un-waited subprocess records as complete."""
    -        now_ts = time.time()
    +        """Harvest observable exit codes and mark unobserved unwaited records partial."""
    +        with cls._lock:
    +            state = cls._active_state
    +
    +        if state is not None and state.get("active"):
    +            # Phase 1: Drain exits and reaped objects queued by Popen.__del__.
    +            try:
    +                state["drain"]()
    +            except Exception as e:
    +                logger.debug(
    +                    f"pubrun failed to drain subprocess queues at finalization: {e}"
    +                )
    +
    +            # Phase 2: Collect live Popen objects for open records under _lock.
    +            live_procs: List[Tuple[Dict[str, Any], Any]] = []
    +            seen_rec_ids = set()
    +            with cls._lock:
    +                for rec in cls._records:
    +                    if rec.get("exit_code") is None and "ended_at_utc" not in rec:
    +                        rec_id = id(rec)
    +                        ref_entry = cls._popen_refs.get(rec_id)
    +                        if ref_entry is not None and ref_entry[0] is rec:
    +                            proc = ref_entry[1]()
    +                            if proc is not None:
    +                                live_procs.append((rec, proc))
    +                                seen_rec_ids.add(rec_id)
    +                pending_running = state["pending_running"]
    +                while True:
    +                    try:
    +                        proc = pending_running.popleft()
    +                    except IndexError:
    +                        break
    +                    rec = getattr(proc, "_pubrun_rec", None)
    +                    if (
    +                        rec is not None
    +                        and rec.get("exit_code") is None
    +                        and "ended_at_utc" not in rec
    +                        and id(rec) not in seen_rec_ids
    +                    ):
    +                        live_procs.append((rec, proc))
    +                        seen_rec_ids.add(id(rec))
    +
    +            # Phase 3: Poll each live Popen once outside _lock.
    +            prev_poll = state["prev_popen_poll"]
    +            complete_record = state["complete_record"]
    +            for rec, proc in live_procs:
    +                try:
    +                    rc = prev_poll(proc)
    +                except Exception as e:
    +                    logger.debug(
    +                        f"pubrun failed to poll subprocess at finalization: {e}"
    +                    )
    +                    continue
    +                if isinstance(rc, int) and not isinstance(rc, bool):
    +                    complete_record(rec, rc, time.time(), time.perf_counter())
    +
    +            # Drain any exits queued while Phase 2/3 ran.
    +            try:
    +                state["drain"]()
    +            except Exception as e:
    +                logger.debug(
    +                    f"pubrun failed to drain subprocess queues after polling: {e}"
    +                )
    +
    +        # Phase 4: Mark remaining unobserved records partial and drop all Popen refs.
             now_mono = time.perf_counter()
             with cls._lock:
                 for rec in cls._records:
                     if rec.get("exit_code") is None and "ended_at_utc" not in rec:
    -                    rec["ended_at_utc"] = now_ts
    +                    rec["ended_at_utc"] = None
                         entry = cls._start_monos.pop(id(rec), None)
                         if entry is not None and entry[0] is rec:
                             rec["elapsed_seconds"] = max(0.0, now_mono - entry[1])
                             rec["duration_clock"] = "monotonic"
    -                    if rec.get("capture_state", {}).get("status") == "partial":
    -                        rec["capture_state"]["status"] = "complete"
    +                    rec["capture_state"] = {
    +                        "status": "partial",
    +                        "detail": _UNWAITED_DETAIL,
    +                    }
    +            cls._popen_refs.clear()
    +            cls._pending_running.clear()
    +            if state is not None:
    +                state["pending_running"].clear()

         @staticmethod
         def _safe_shlex_split(args: Any) -> list:
    ```
    (2) `grep -n "_internal_poll" src/pubrun/capture/subprocesses.py` -> `<no match>` (exit 1; no reference or assignment to `Popen._internal_poll`).
    (3) `python3 -m pytest tests/test_capture.py -k "unwaited or gc_after_exit or cleanup_reaped or externally_reaped or del_hook or popen_del" -W error::pytest.PytestUnraisableExceptionWarning --no-cov -q`:
    ```text
    .........                                                                [100%]
    9 passed, 32 deselected in 0.43s
    ```
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: (1) Paste the `pytest tests/test_capture.py --no-cov -q -v` output lines for every test named in "Proposed changes" item 2, each `PASSED` (a POSIX-only test is `SKIPPED` only on a non-POSIX host). (2) Paste the summary line of the six-file related-suites run. (3) Paste the full-suite summary line, and for any failure paste the same test's result on unmodified `HEAD`. (4) Paste the two failing test results from the mutation check, then `git diff --stat` after restoring. (5) State which OS and Python version ran the tests, and that the CI matrix was not run.
  - Observed evidence:
    (1) `python3 -m pytest tests/test_capture.py --no-cov -v` (41 passed in 2.01s; every test from "Proposed changes" item 2):
    ```text
    tests/test_capture.py::TestSubprocessInterceptor::test_detached_subprocess_finalized PASSED [ 12%]
    tests/test_capture.py::TestFinalizeAll::test_marks_unwaited_records_partial PASSED [ 36%]
    tests/test_capture.py::TestSubprocessSpyMonotonicTiming::test_finalize_all_monotonic_non_collision_and_post_finalize_wait PASSED [ 73%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_unwaited_exited_child_exit_code_harvested_at_finalize[0-complete] PASSED [ 82%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_unwaited_exited_child_exit_code_harvested_at_finalize[7-failed] PASSED [ 85%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_unwaited_uncollected_child_polled_at_finalize PASSED [ 87%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_gc_after_exit_records_exit_code PASSED [ 90%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_cleanup_reaped_child_records_exit_code PASSED [ 92%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_externally_reaped_child_is_partial_not_sentinel PASSED [ 95%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_popen_del_hook_does_not_take_spy_lock PASSED [ 97%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_uninstall_restores_popen_del PASSED [100%]
    ```
    (2) Six-file related-suites run (`python3 -m pytest tests/test_capture.py tests/test_capture_engine_bugs.py tests/test_hook_ownership_rollback.py tests/test_capture_isolation.py tests/test_pause_resume.py tests/test_tracker.py --no-cov -q`):
    ```text
    202 passed in 17.50s
    ```
    (3) Full suite (`aw suite --no-cache`):
    ```text
    ======================= 1906 passed in 150.67s (0:02:30) =======================
    ```
    Zero failures.
    (4) Mutation check (replaced body of `_patched_popen_del`'s `finally` block with `pass` and ran the two tests):
    ```text
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_gc_after_exit_records_exit_code FAILED [ 50%]
    tests/test_capture.py::TestUnwaitedPopenHarvesting::test_cleanup_reaped_child_records_exit_code FAILED [100%]
    FAILED tests/test_capture.py::TestUnwaitedPopenHarvesting::test_gc_after_exit_records_exit_code (assert None == 7)
    FAILED tests/test_capture.py::TestUnwaitedPopenHarvesting::test_cleanup_reaped_child_records_exit_code (assert None == 7)
    ======================= 2 failed, 39 deselected in 0.33s =======================
    ```
    `git diff --stat` after restoring `src/pubrun/capture/subprocesses.py`:
    ```text
     CHANGELOG.md                       |   2 +
     docs/api.md                        |   2 +-
     docs/architecture.md               |   6 +-
     docs/functional_spec.md            |   6 +-
     docs/manifest.md                   |   8 +-
     src/pubrun/capture/subprocesses.py | 277 ++++++++++++++++++++++++----
     tests/test_capture.py              | 368 ++++++++++++++++++++++++++++++++++---
     7 files changed, 601 insertions(+), 68 deletions(-)
    ```
    (5) Environment: Linux x86_64 (kernel `6.8.0-151-generic`), Python `3.14.6`. The GitHub Actions CI matrix (3 OS x Python 3.8 to 3.14) was not run because pushing requires explicit human instruction.
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: (1) Paste `git diff -- docs/manifest.md` and name the edited `capture_state`, `exit_code`, `ended_at_utc`, and `elapsed_seconds` rows. (2) Paste the output of `grep -n "still unwaited at finalization" docs/manifest.md`, which must show no match. (3) Paste the output of `git diff -U0 -- docs/manifest.md | grep '^+[^+]' | grep -c '[—–]'`, which must print `0`.
  - Observed evidence:
    (1) Edited rows in `docs/manifest.md#subprocesses`: `ended_at_utc`, `elapsed_seconds`, `exit_code`, and `capture_state`.
    ```diff
    diff --git a/docs/manifest.md b/docs/manifest.md
    index 2f380a4..42ac818 100644
    --- a/docs/manifest.md
    +++ b/docs/manifest.md
    @@ -140,14 +140,14 @@ Array of subprocess records. Each element:
     |---|---|---|
     | `argv` | list[string] | Command and arguments. Sensitive values may be redacted. |
     | `started_at_utc` | float | Start time (POSIX epoch float). |
    -| `ended_at_utc` | float \| null | End time, or `null` if the process was still running at finalization. |
    -| `elapsed_seconds` | float \| null | Optional. Nonnegative monotonic duration (`time.perf_counter()`) from launch until `pubrun` observed the process finish (`wait()`, `communicate()`, a completed `poll()`, `os.system` returning, or pipe close for `pubrun.popen()`), or until the launch attempt failed. For a process never waited on, it is the time until run finalization. Not derived from the UTC fields. |
    +| `ended_at_utc` | float \| null | End time, or `null` when `pubrun` did not observe the process end by finalization. |
    +| `elapsed_seconds` | float \| null | Optional. Nonnegative monotonic duration (`time.perf_counter()`) from launch until `pubrun` observed the process finish (`wait()`, `communicate()`, a completed `poll()`, `Popen.__del__`, `os.system` returning, or pipe close for `pubrun.popen()`), or until the launch attempt failed. For a child whose exit `pubrun` first observed at the next `Popen` launch or at finalization, the duration ends at that observation. For a child still unobserved at finalization, the duration ends at finalization. Not derived from the UTC fields. |
     | `duration_clock` | string \| null | Optional. `"monotonic"` when `elapsed_seconds` is present. Absent on records written before monotonic subprocess timing. |
     | `pid` | int \| null | Optional. Written by the explicit wrappers only: the process ID for `pubrun.subprocess.Popen`, `null` for `pubrun.subprocess.run()`, `pubrun.popen()`, and failed launches. |
     | `error` | string \| null | Optional. Bounded, redacted error detail when an explicit wrapper's launch failed. |
     | `cwd` | string | Working directory of the subprocess. |
    -| `exit_code` | int \| null | Exit code, or `null` if the process was not waited on. |
    -| `capture_state` | object | `"complete"` for exit code 0 (and for a process still unwaited at finalization), `"failed"` for a nonzero exit code or a failed launch (with a redacted `detail`), `"partial"` while the process is still running. See [Capture State](#capture-state). |
    +| `exit_code` | int \| null | Exit code, or `null` when `pubrun` did not observe the exit. |
    +| `capture_state` | object | `"complete"` for exit code 0, `"failed"` for a nonzero exit code or a failed launch (with a redacted `detail`), and `"partial"` with a `detail` while the process runs, when `pubrun` did not observe its exit by finalization, or when its exit status is unavailable. See [Capture State](#capture-state). |
    ```
    (2) `grep -n "still unwaited at finalization" docs/manifest.md` -> `<no match>` (exit 1).
    (3) `git diff -U0 -- docs/manifest.md | grep '^+[^+]' | grep -c '[—–]'` -> `0`.
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: (1) Paste `git diff -- docs/functional_spec.md docs/architecture.md docs/api.md` and name each edited target list and the `#15.2 Recorded Fields` change. (2) Paste the output of `grep -n 'Popen.__init__' docs/functional_spec.md docs/architecture.md docs/api.md | grep -v 'Popen.__del__'`, which must show no match (at review it matched the six lists named in E-04 outcome 1). (3) Paste the output of `git diff -U0 -- docs/functional_spec.md docs/architecture.md docs/api.md | grep '^+[^+]' | grep -c '[—–]'`, which must print `0`.
  - Observed evidence:
    (1) Edited target lists (all six now name `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, and `os.system`):
    - `docs/functional_spec.md#15.1 Mechanism`
    - `docs/functional_spec.md#20. Failure Behavior` ("Enforce transactional installation" bullet)
    - `docs/architecture.md#15. Subprocess Model` (opening paragraph and "**Live target chaining and transactional install:**" bullet)
    - `docs/architecture.md#18. Failure Model` ("**Independent cleanup and hook ownership:**" bullet)
    - `docs/api.md#Third-Party Hook Ownership Rules` (`SubprocessSpy` table row)
    Also updated `docs/functional_spec.md#15.2 Recorded Fields` to describe finalization harvesting observable unwaited child exits and marking unobserved children `"partial"` with a `detail` and `null` `exit_code`/`ended_at_utc`.
    ```diff
    diff --git a/docs/api.md b/docs/api.md
    index f419b45..1f44acf 100644
    --- a/docs/api.md
    +++ b/docs/api.md
    @@ -482,7 +482,7 @@ When global hooks are permitted by the active import mode and enabled in configu
     | `faulthandler` (`ConsoleInterceptor`) | Checks `faulthandler.is_enabled()` before touching it; enables `faulthandler` on `stderr.log` only when previously disabled. | Calls `faulthandler.disable()` (before closing `stderr.log`) only when `pubrun` enabled it. A pre-existing user or test-runner `faulthandler` remains enabled. |
     | OS signal handlers (`SignalExitCapture`) | Records each installed shim and chains to the prior handler. Rolls back registered shims on unexpected install errors. | Restores each signal only when `signal.getsignal(signum)` is still `pubrun`'s shim. Deactivated shims left under a later third-party handler pass signals through passively without recording or calling `_finalize_active_run()`. |
     | `sys.excepthook` (`SignalExitCapture`) | Captures the prior `sys.excepthook` in a local closure and redacts sensitive values in captured exception messages. | Restores `sys.excepthook` only when it is still `pubrun`'s wrapper. If a third-party hook wraps `pubrun`, `pubrun`'s deactivated wrapper forwards passively to the closure-captured prior hook. |
    -| `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` (`SubprocessSpy`) | Snapshots live targets at `install()`, chains to pre-existing wrappers, tags spawned processes with install-generation state, and rolls back already-patched targets if a later patch fails. | Verifies caller ownership token when set, marks the generation inactive first, and restores each target independently only when it still matches `pubrun`'s installed wrapper. Any wrapper left beneath a later third-party wrapper passes calls through passively without recording. |
    +| `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, and `os.system` (`SubprocessSpy`) | Snapshots live targets at `install()`, chains to pre-existing wrappers, tags spawned processes with install-generation state, and rolls back already-patched targets if a later patch fails. | Verifies caller ownership token when set, marks the generation inactive first, and restores each target independently only when it still matches `pubrun`'s installed wrapper. Any wrapper left beneath a later third-party wrapper passes calls through passively without recording. |

     ---

    diff --git a/docs/architecture.md b/docs/architecture.md
    index afcd640..e904aff 100644
    --- a/docs/architecture.md
    +++ b/docs/architecture.md
    @@ -219,9 +219,9 @@ Contents:

     ## 15. Subprocess Model

    -`SubprocessSpy` transparently monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to capture spawned process metadata (argv, UTC start and end timestamps, monotonic `elapsed_seconds` with `duration_clock: "monotonic"`, exit codes). Per-record monotonic start readings stay in an in-memory map keyed by record identity and are never serialized. Record mutations and lifecycle transitions are thread-safe under `SubprocessSpy._lock`.
    +`SubprocessSpy` transparently monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, and `os.system` to capture spawned process metadata (argv, UTC start and end timestamps, monotonic `elapsed_seconds` with `duration_clock: "monotonic"`, exit codes). Per-record monotonic start readings stay in an in-memory map keyed by record identity and are never serialized. Record mutations and lifecycle transitions are thread-safe under `SubprocessSpy._lock`.

    -- **Live target chaining and transactional install:** `SubprocessSpy.install(max_records, config, owner)` snapshots the live `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` attributes at install time, builds generation-scoped wrapper closures that chain to those pre-existing targets, and rolls back any already-patched target if a later patch fails.
    +- **Live target chaining and transactional install:** `SubprocessSpy.install(max_records, config, owner)` snapshots the live `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, and `os.system` attributes at install time, builds generation-scoped wrapper closures that chain to those pre-existing targets, and rolls back any already-patched target if a later patch fails.
     - **Generation-scoped records:** Each spawned `Popen` instance carries its install generation's `state` dict and direct record reference (`_pubrun_state`, `_pubrun_rec`), and `os.system` holds a direct local reference to its record. Post-uninstall `wait()` calls or concurrent `uninstall()` calls cannot corrupt a newer run's records or raise `IndexError`. Failed spawn details pass through `format_safe_error_detail()`.
     - **Ownership-guarded uninstall and passive passthrough:** `SubprocessSpy.uninstall(owner=...)` verifies the caller's ownership token when set, flips `state["active"] = False` first, and restores each target independently only when the current attribute is still `pubrun`'s installed wrapper. If a third-party wrapper sits outside `pubrun`, that wrapper remains intact while `pubrun`'s deactivated closure passes calls through passively without recording.

    @@ -263,7 +263,7 @@ The system must:
     ### Bounded Redacted Diagnostics, Independent Cleanup, and Consumer Honesty

     - **Bounded redacted error records:** Capture and cleanup exceptions pass through `format_safe_error_detail()` (single-line, sensitive values redacted, 240-character cap, `traceback = null`, falling back to default patterns and then `type(exc).__name__`). `Run` retains up to `MAX_CAPTURE_ERRORS = 50` entries in `errors.records` under `_errors_lock`; additional errors increment the omitted counter and set `errors.capture_state.status = "partial"`. Runtime warnings in `Run`, `EventStream`, and `ArtifactWriter` are emitted at most once per `(section, stage)` or failure episode, outside internal locks.
    -- **Independent cleanup and hook ownership:** `_finalize_state()` and `_rollback_owned_hooks()` isolate every pre-teardown and teardown step independently, separating `SubprocessSpy.finalize_all()` and record snapshotting from `SubprocessSpy.uninstall(owner=...)`. Process-global hooks (`sys.stdout`, `sys.stderr`, `faulthandler`, signal handlers, `sys.excepthook`, `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `os.system`) use identity-guarded restoration and passive passthrough so later third-party wrappers are never clobbered.
    +- **Independent cleanup and hook ownership:** `_finalize_state()` and `_rollback_owned_hooks()` isolate every pre-teardown and teardown step independently, separating `SubprocessSpy.finalize_all()` and record snapshotting from `SubprocessSpy.uninstall(owner=...)`. Process-global hooks (`sys.stdout`, `sys.stderr`, `faulthandler`, signal handlers, `sys.excepthook`, `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, `os.system`) use identity-guarded restoration and passive passthrough so later third-party wrappers are never clobbered.
     - **Honest consumers:** `pubrun report`, `pubrun inspect`, `pubrun methods`, and `pubrun status` tolerate failed, `null`, or malformed section fields without crashing. They surface failed sections and deduplicated `capture-error` findings explicitly (distinct from `"suppressed"`) and disclose partial provenance instead of claiming complete capture or standard-library-only dependencies.

     ## 19. Redaction Model
    diff --git a/docs/functional_spec.md b/docs/functional_spec.md
    index 7600ed3..a171ddf 100644
    --- a/docs/functional_spec.md
    +++ b/docs/functional_spec.md
    @@ -661,11 +661,11 @@ produced elsewhere (see 14.1).

     ### 15.1 Mechanism

    -`SubprocessSpy` monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to transparently record spawned process metadata.
    +`SubprocessSpy` monkey-patches `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, and `os.system` to transparently record spawned process metadata.

     ### 15.2 Recorded Fields

    -Each subprocess record includes: `argv`, `started_at_utc`, `ended_at_utc`, `cwd`, `exit_code`, and `capture_state`. Once the process is observed to finish (or the launch fails, or finalization closes an unwaited record), the record also carries `elapsed_seconds` (nonnegative monotonic duration) and `duration_clock: "monotonic"`. Monotonic start readings are held in an internal map keyed by record identity and are never serialized. The explicit wrappers (`pubrun.subprocess.run`, `pubrun.subprocess.Popen`, `pubrun.popen`) record the same timing fields plus `pid`, and on a failed launch record `error` and `capture_state: {"status": "failed", "detail": ...}` before re-raising.
    +Each subprocess record includes: `argv`, `started_at_utc`, `ended_at_utc`, `cwd`, `exit_code`, and `capture_state`. Once the process is observed to finish (or the launch fails, or finalization closes an unwaited record), the record also carries `elapsed_seconds` (nonnegative monotonic duration) and `duration_clock: "monotonic"`. Monotonic start readings are held in an internal map keyed by record identity and are never serialized. At finalization, `SubprocessSpy` records the exit of an unwaited child when `pubrun` can observe it (through `Popen.__del__`, `subprocess._cleanup()` on a later `Popen` launch, or a non-blocking `poll()`), and otherwise leaves `exit_code` and `ended_at_utc` as `null` and marks `capture_state` as `"partial"` with a `detail`. The explicit wrappers (`pubrun.subprocess.run`, `pubrun.subprocess.Popen`, `pubrun.popen`) record the same timing fields plus `pid`, and on a failed launch record `error` and `capture_state: {"status": "failed", "detail": ...}` before re-raising.

     ### 15.3 Memory Safety

    @@ -834,7 +834,7 @@ The system MUST:
     - Set `capture.capture_state.status = "partial"` (naming the degraded sections in `detail`) whenever any section failed, covering both escaping exceptions and self-caught failed returns, while keeping `status.outcome` accurate to the host script's execution outcome.
     - Record structured `capture-error` entries (`kind = "capture-error"`, `type`, bounded redacted `message`, `traceback = null`, optional `section`, optional `stage`) in `errors.records` under `_errors_lock`, capped at `MAX_CAPTURE_ERRORS = 50`. When additional errors exceed the cap, set `errors.capture_state.status = "partial"` with the omitted count.
     - Emit bounded runtime warnings without traceback spam: at most one warning per `(section, stage)` in `Run`, at most one per write-failure episode in `EventStream` (outside its lock), and at most one on finalization write failure in `ArtifactWriter`.
    -- Enforce transactional installation, prior `faulthandler.is_enabled()` preservation, identity-guarded restoration, and passive passthrough across all process-global hooks (`sys.stdout`/`sys.stderr`, `faulthandler`, signal handlers, `sys.excepthook`, `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `os.system`) so later third-party wrappers are never overwritten.
    +- Enforce transactional installation, prior `faulthandler.is_enabled()` preservation, identity-guarded restoration, and passive passthrough across all process-global hooks (`sys.stdout`/`sys.stderr`, `faulthandler`, signal handlers, `sys.excepthook`, `subprocess.Popen.__init__`, `subprocess.Popen.wait`, `subprocess.Popen.poll`, `subprocess.Popen.__del__`, `os.system`) so later third-party wrappers are never overwritten.
     - Surface partial manifests honestly in downstream consumers without crashing on `null` or malformed fields:
       - `pubrun report` (across `basic`, `standard`, `deep`, and `section="env"`/`"packages"` extracts, respecting `NO_COLOR`) renders a bounded `[WARN ]` summary of failed sections and up to 10 `capture-error` records (with overflow and truncation detail) and displays `capture failed` instead of misleading empty counts.
       - `pubrun inspect` emits `WARN` findings (`{section}_capture_failed`, deduplicated `capture_error_{section}`, and `errors_capture_partial` truncation notices) distinct from `"suppressed"` (`*_off`).
    ```
    (2) `grep -n 'Popen.__init__' docs/functional_spec.md docs/architecture.md docs/api.md | grep -v 'Popen.__del__'` -> `<no match>` (exit 1).
    (3) `git diff -U0 -- docs/functional_spec.md docs/architecture.md docs/api.md | grep '^+[^+]' | grep -c '[—–]'` -> `0`.
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: (1) Paste `git diff -- CHANGELOG.md`, showing the entry under `## [Unreleased]` and `### Fixed`. (2) Paste the output of `git diff -U0 -- CHANGELOG.md | grep '^+[^+]' | grep -c '[—–]'`, which must print `0`. (3) Paste the output and exit code of `python3 scripts/sanitize_paths.py --check --all`, which must be 0.
  - Observed evidence:
    (1) `git diff -- CHANGELOG.md`:
    ```diff
    diff --git a/CHANGELOG.md b/CHANGELOG.md
    index 3be0fca..8e4b97c 100644
    --- a/CHANGELOG.md
    +++ b/CHANGELOG.md
    @@ -103,6 +103,8 @@ The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
       the deep pages, never the README front door.

     ### Fixed
    +- **Unwaited `subprocess.Popen` children now record observable exit codes and report unobserved exits as `"partial"` instead of `"complete"`.**
    +  `SubprocessSpy` now hooks `subprocess.Popen.__del__` without taking locks and performs a single non-blocking poll of live unwaited `Popen` objects at finalization, recording the real `exit_code` with `capture_state.status: "complete"` (exit code 0) or `"failed"` (nonzero) when observable through public `Popen` attributes. A child still running at finalization, or whose exit status was collected outside `pubrun`, now records `exit_code: null`, `ended_at_utc: null`, and `capture_state: {"status": "partial", "detail": ...}` instead of `"complete"`. Downstream consumers that filter subprocess records on `capture_state.status == "complete"` should note that unobserved unwaited children now report `"partial"`.
     - **`workload_seconds` no longer includes a background manifest refresh write.** A `stop()` call made
       while the background hardware capture was rewriting `manifest.json` waited for that write and counted
       it as workload; with the default fsynced durability on a slow disk this added tens to hundreds of
    ```
    (2) `git diff -U0 -- CHANGELOG.md | grep '^+[^+]' | grep -c '[—–]'` -> `0`.
    (3) `python3 scripts/sanitize_paths.py --check --all` -> no stdout/stderr findings, `sanitize_exit=0`.
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no open questions.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries (`src/pubrun/capture/subprocesses.py`, `tests/test_capture.py`, `docs/manifest.md`, `docs/functional_spec.md`, `docs/architecture.md`, `docs/api.md`, `CHANGELOG.md`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`. The mutation check edits `src/pubrun/capture/subprocesses.py` only temporarily and must restore it.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit focjwv -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize focjwv`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize focjwv` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
