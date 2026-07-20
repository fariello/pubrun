# IPD: Assess edge-cases - boundary/failure-mode hardening

- Date: 2026-07-05
- Concern: edge-cases (boundary conditions, malformed inputs, failure modes)
- Scope: whole project (`src/pubrun/`), with emphasis on the manifest/lock readers
  (`status.py`), external-command capture (`hardware.py`, `git.py`, `resources.py`),
  the monkeypatched surfaces (`core.py`, `console.py`, `signals.py`), config loading
  (`config.py`), and package capture (`packages.py`).
- Status: EXECUTED (2026-07-05). All steps implemented + tested; EC-27 deferred as
  planned. Full suite: 628 passed, 2 skipped, 1 known-flaky
  (`test_real_sigpipe_via_pipe`, passes in isolation). Docs/CHANGELOG synced.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Run record: `workflow-artifacts/assess-edge-cases/20260705-002318/`
- Plan-review: hardened 2026-07-05 (verdict APPROVE WITH REVISIONS APPLIED); see the
  "Plan-review revisions" section at the end for what changed and why.

## Goal

pubrun's promise is trustworthy, non-intrusive execution provenance: it must (a) never
crash the host script (the "golden rule"), and (b) never silently produce a wrong
provenance record or a wrong automated status. This assessment systematically probes
boundaries and failure modes and proposes hardening for the cases where a malformed,
truncated, hand-edited, or version-drifted input, a slow/hung external tool, or a
clock/tree/collection boundary can crash a `pubrun` command, corrupt the manifest,
grow memory unbounded, or make a wrong liveness decision.

The manifests and lock files are precisely the kind of data that gets truncated when a
process is killed mid-write, copied between hosts with different clocks (Slurm/rsync),
produced by a different pubrun version, or hand-edited during debugging — so the
readers must be robust to them. Several reader paths currently are not.

## Project conventions discovered (Step 0)

- Guiding principles: no `GUIDING_PRINCIPLES.md`; principles are stated in `README.md`
  and `AGENTS.md` (zero runtime deps, "stupidly simple", golden rule "never crash the
  host script", ghost-mode degradation, no `rich`). Universal fallback principles from
  `00-run-protocol.md` also applied.
- Pending-plans location/format used: `.agents/plans/pending/`, naming
  `YYYYMMDD-<slug>.md`; terminal dir `.agents/plans/executed/`.
- Contributor/spec-sync contract: `AGENTS.md` (doc-sync discipline; run
  `/assess documentation` after user-visible behavior changes).
- Stack: Python 3.8+ library + CLI, zero runtime deps (`tomli` only on <3.11). Version
  1.3.1. 599 tests passing (1 known-flaky SIGPIPE test).

## Findings

Severity = impact if left alone. Remediation Risk = the Fix-Bar gate for acting now
(the risk the *fix* harms complexity/usability/security/functionality). All findings
were verified by reading the cited code, not inferred from names. Default-mode
reachability is noted where a finding only bites a non-default configuration.

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| EC-01 | High | Low | QA | status reader | A malformed/hand-edited/foreign-version lock or manifest with a **non-numeric `started_at_utc`** (e.g. a string) makes `time.time() - self.started_at_utc` raise `TypeError`, which is **not** caught by the narrow `except (json.JSONDecodeError, OSError)`. `RunInfo()` is built per-entry in `scan_runs` with no per-entry guard, so **one bad run crashes the entire `pubrun status`/`inspect`** for all runs. | `status.py:205,212,216,250`; `scan_runs` `status.py:485-490` |
| EC-02 | High | Low | QA | status sort | `runs.sort(key=lambda r: r.started_at_utc or 0)` raises `TypeError: '<' not supported between 'str' and 'int'` if any run's `started_at_utc` survived JSON parsing as a string. `or 0` only rescues `None`/`0`. Crashes the whole scan. | `status.py:490` |
| EC-03 | High | Low | QA | status render | `_format_timestamp` does `datetime.fromtimestamp(epoch)` guarding only `None`; a string, NaN, negative, or out-of-range epoch raises `ValueError`/`TypeError`/`OverflowError`. Reached from every list/inspect/summary render — one bad timestamp crashes the whole render. | `status.py:542-547` |
| EC-04 | Medium | Low | QA | status reader | `_received_sigpipe` / inspect rendering iterate `signals_received` assuming list-of-dicts and call `.get(...)`; a non-dict entry (version drift) raises `AttributeError`, uncaught by the JSON/OSError catch → crashes scan/inspect. `len(signals_received)` also assumes a sized type. | `status.py:112-119,172,740,813-817` |
| EC-05 | Medium | Low | Sec/SWE | liveness | `is_pid_alive` calls `os.kill(pid, 0)` with no guard against `pid <= 0`. On POSIX `os.kill(0,0)`/negatives target process groups; a lock with `pid: 0`/negative (hand-edited, or a dir-name parse yielding a negative) makes liveness return `True` unconditionally → wrong RUNNING verdict driving `close_out_crashed_run` side effects. `status.py:213` rejects `pid==0` (falsy) but not negatives. `OverflowError` from a huge pid is also not in the catch tuple. | `liveness.py:32-41`; `status.py:213,264` |
| EC-06 | Medium | Low | Sec/SWE | liveness | Same-process substring match: `expected_script in part`/`in cmdline` yields a false-positive "same process" for a recycled PID running a command line that merely *contains* the script name, or when `expected_script` is a short/generic token (`python`, `-c`). Wrong RUNNING verdict. Empty string is guarded (`if expected_script:`) but short/generic names are not. | `liveness.py:59-70,84,102,131` |
| EC-07 | Medium | Low | Sec/SWE | liveness | Timing fallback: when `get_process_start_time` returns `None` (e.g. `/proc/<pid>/stat` permission denied), `is_same_process` **returns True (alive)** for any live PID → a reused PID owned by another user is treated as the original run. Also the 86400s tolerance is very wide. | `liveness.py:~145-150` |
| EC-08 | Medium | Low | SWE | packages | `sorted(records, key=lambda x: x["name"].lower())` is **outside** the try/except; in `full-environment`/`top-level-installed` modes a distribution whose `metadata["Name"]` is `None` makes `None.lower()` raise, propagating out of `get_packages` → the run is demoted to ghost mode (all tracking lost). Default `imported-only` mode is safe (names are `sys.modules` keys). | `packages.py:112,136` |
| EC-09 | High | Low | SWE | memory | `manual_subprocess_records` (populated by `pubrun.subprocess.run/Popen/popen`) has **no cap**, unlike `SubprocessSpy._records` (`_max_records`). A host calling these in a tight loop grows the list unbounded → OOM risk on long/loop-heavy scripts. | `core.py:684-686,716-718,774-776`; cf. `subprocesses.py:33,103-105` |
| EC-10 | Medium | Low | SWE | external cmd | `hardware.py` runs `nvidia-smi`/`system_profiler`/`sysctl`/`wmic` via `subprocess.check_output` with **no `timeout=`** (contrast `git.py` uses `timeout=1`). A hung `nvidia-smi` (wedged driver) or slow `system_profiler` blocks the hardware thread; `_finalize_state` only waits 2s then proceeds, leaving an **orphaned hung child process** and `hardware_data` stuck as non-terminal `"pending"` written to the manifest as if final. | `hardware.py:17,24,43,50,78,107,127`; `tracker.py:437-438,603` |
| EC-11 | Medium | Low | SWE | external cmd | macOS/Windows RSS pollers and the macOS tree-RSS `ps -eo pid,ppid,rss` shell out with **no `timeout=`**; a hung `ps`/`wmic` orphans the watcher thread + child. The skip-final-update-if-alive guard prevents a data race but not the orphan. | `resources.py:13-27,42-60,97-148` |
| EC-12 | Medium | Low | QA | resource monitor | Three consecutive poll failures (any poll returning RSS 0, which also happens on *any* transient error) permanently set `_stop_event`, killing all telemetry for the rest of the run with no recovery → silently under-reported peak RSS/CPU on long runs after a transient blip. | `resources.py:229-237` |
| EC-13 | Medium | Low | Stakeholder | git capture | `git.py` uses a hardcoded `timeout=1`; on a slow FS or large repo, `rev-parse --show-toplevel` times out and the run is recorded as **"Not a git repository or git binary not installed"** — a wrong, misleading provenance conclusion. Timeout should be configurable and larger by default, and a timeout should be distinguished from "no repo". | `git.py:24-30,40-46` |
| EC-14 | Medium | Low | QA | config loading | `load_local_config`/`load_user_config` call `tomllib.loads(...)` with no error handling. A malformed `.pubrun.toml` raises `TOMLDecodeError`. `Run.__init__` catches this and falls back to defaults (good), but `scan_runs`/`status.py:477` and other CLI call sites invoke `resolve_config()` unguarded → a malformed local config crashes `pubrun status`. Fix at the source (tolerate + warn per file). | `config.py:73-104`; `status.py:477`; `tracker.py:54-61` (guarded) |
| EC-15 | Medium | Low | SWE | signals | `_restore_excepthook` sets `sys.excepthook = self._previous_excepthook` with **no identity check** — if a third party installed a hook after pubrun, `stop()` silently clobbers it. `console.py:200-203` already does the correct identity-guarded restore; excepthook should match. | `signals.py:242-246`; cf. `console.py:200-203` |
| EC-16 | Medium | Low | SWE | console tee | The tee's passthrough `original_stream.write(data)` only catches `BrokenPipeError`; other write errors (e.g. `ValueError: I/O on closed file` when host code closed stdout) propagate out of the tee's `write()` and can surface an exception the host would otherwise handle differently. Broaden to protect the passthrough. Note: only active when `capture_mode != "off"` (non-default). | `console.py:70-82` |
| EC-17 | Medium | Low | Domain | timestamps | Same `*_utc` epoch renders as **local time** in `status.py` (`datetime.fromtimestamp(epoch)`) but as **UTC** in `diff.py` (`fromtimestamp(ts, tz=timezone.utc)`). For a provenance tool this inconsistency can mislead a researcher about ordering/timing. Standardize on UTC in `status.py` (and label it). | `status.py:546` vs `diff.py:12-21` |
| EC-18 | Medium | Low | SWE | diff export | `unflatten_manifest` walks `d = d[part]`; if the flattened dict has both a scalar leaf and a nested key under the same prefix (e.g. a package literally named `numpy.core`, or an env var containing `.`), it does `scalar[key] = v` → `TypeError`. Reached via `pubrun diff --export json` (not `show`; `--export` is a `diff` flag). The outer CLI catch degrades to "Failed to generate diff report", so no host crash, but the export path is broken for such manifests. | `diff.py:102-113,199`; `__main__.py:338,1163` |
| EC-19 | Low | Low | SWE | diff correctness | List-diff uses `x not in val_a` / `.index(x)` with `==` semantics, so `True`/`1` and `False`/`0` alias (bool/int), producing wrong add/remove/reorder markers. Env-var flattening also silently collapses duplicate names (last wins) and assumes `environment.variables`/`packages.records` are lists of dicts (a dict/None/str raises `AttributeError` inside `_normalize_manifest`). | `diff.py:43-56,138,149-153`; `render.py:39,46` |
| EC-20 | Low | Low | SWE | events | `event_count` is estimated as `max(1, file_size // 120)` and displayed verbatim as "Events: N" with no indication it is an estimate; a single large line reports a wildly wrong count and a non-empty-but-zero-complete-event file still reports ≥1. Cosmetic-but-misleading; label it "~N (est.)" or count cheaply. | `status.py:236` |
| EC-21 | Low | Low | SWE | print wrapper | `pubrun.print` computes `sep.join(map(str, args))` before its try; `pubrun.print(x, sep=None)` (which builtin `print` accepts as "default") raises `AttributeError`. Only reachable when the user explicitly calls `pubrun.print` (not installed into builtins by default), so it is a library-API edge, not a golden-rule violation. Normalize `sep`/`end` defaults and move arg handling into the guard. | `core.py:458-462` |
| EC-22 | Low | Low | QA | combined logs | `combined` log interleave sorts on the timestamp *string*; lines emitted before the first timestamped line (or partial final lines from a killed process) get an empty timestamp that sorts to the very top, silently mis-ordering the chronology. | `__main__.py:754,769,799` |
| EC-23 | Low | Low | SWE | manifest timing | `elapsed_seconds` / manifest duration are computed from wall-clock `time.time()`; a backward clock step (NTP) yields a **negative** persisted duration. `_format_elapsed` handles negatives for *display*, but the persisted value is still negative. (CPU% correctly uses `perf_counter`.) Low because rare and display-tolerant; note as a known limitation or clamp at 0 with a flag. | `tracker.py:441,551`; `status.py:444-446,525` |
| EC-24 | Low | Low | SWE | Popen race | `_log_pubrun_record` checks-then-sets `_pubrun_logged` non-atomically; concurrent `wait()`/`poll()` on the same Popen from two threads can double-append the record. Rare. | `core.py:698-734` |
| EC-25 | Low | Low | SWE | manual subproc | `pubrun.subprocess.run` records nothing when the wrapped call raises (e.g. `FileNotFoundError`), unlike `SubprocessSpy` which records a failed invocation — inconsistent provenance for failed manual subprocesses. | `core.py:660-688` |
| EC-26 | Low | Low | SWE | code hygiene | `compare_manifests(..., ignores: List[str] = [])` uses a mutable default argument (latent bug; currently not mutated). | `diff.py:116` |

## Proposed changes (ordered, validatable)

Grouped by theme; ordered so the crash-prevention hardening lands first. All items are
low Remediation Risk (defensive guards + config, behavior-preserving on the happy path).

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|--------------------|--------|-------|------------------|------------|
| 1 | EC-01, EC-02, EC-03, EC-04 | Make the status reader tolerant of malformed/foreign manifests+locks. (a) Add ONE private coercion helper in `status.py` (e.g. `_as_float(x)` / `_as_int(x)` returning `None` for non-numeric/NaN/inf) and route `started_at_utc`/`ended_at_utc`/`pid` through it at the assignment points in both `_load_from_lock` and `_load_from_manifest` — a single choke point, not scattered guards, so all downstream arithmetic (`time.time() - started_at_utc`, elapsed, sort) is safe by construction. (b) Wrap each `RunInfo(entry)` construction in `scan_runs` in a try/except that degrades that single run to `crashed`/`unknown` and continues (never crash the whole listing) — this is the backstop even if a new field is missed. (c) Make the sort key numeric-safe (falls out of (a), but keep `or 0` defensively). (d) Guard `_format_timestamp` (try/except → `"-"`). (e) Guard `signals_received` iteration/`len` against non-list/non-dict (coerce a non-list to `[]`, skip non-dict entries). | `status.py` | Low | New tests feeding a run dir with a string `started_at_utc`, an out-of-range/NaN epoch, a non-dict `signals_received`, and a non-list `argv`; assert `pubrun status`/`inspect` still list all other runs and mark the bad one degraded, no exception. Include a test asserting the per-run try/except backstop catches an unforeseen bad field. |
| 2a | EC-05 | **Unambiguous PID guard (no behavior-flip risk).** In the shared `is_pid_alive` entry point, return `False` immediately for `pid is None` or `pid <= 0` (before the platform branch, so both the POSIX `os.kill` path and the Windows `OpenProcess` path are covered), and add `OverflowError` to the POSIX `except` tuple (`os.kill(2**70, 0)` raises it). Rationale: `os.kill(0,0)`/`os.kill(-1,0)` do NOT raise — they signal process groups and return `True`, a wrong liveness verdict. This guard only rejects impossible-PID inputs and cannot flip a legitimate run's status. | `liveness.py:22-41` | Low | Unit tests: `is_pid_alive(0)`/`(-1)`/`(None)` → False; `is_pid_alive(2**70)` → False, no raise. |
| 2b | EC-06 | **Tighten script match, prefer the existing exact-basename branch.** On Linux, `_check_command_linux` already tests `Path(part).name == expected_script` alongside the loose `expected_script in part` substring (liveness.py:68); make exact-basename the trusted signal and treat a substring-only hit as NOT a confirmed match (fall through to timing). On macOS/Windows the check is substring-only (liveness.py:84,102); tokenize the command line and require an exact basename/token match. Additionally, do not trust ANY script match when `expected_script` is a short/generic token (e.g. length < 3, or in `{"python","python3","-c","-m"}`); fall through to timing instead. | `liveness.py:59-70,84,102,131-143` | Low–Medium (functionality) — **gated by 2d characterization tests** | Unit tests: recycled PID running `python /x/train_backup.py` with `expected_script="train.py"` → not confirmed; `expected_script="python"` → never confirmed via script, falls to timing. |
| 2c | EC-07 | **Conservative start-time handling (bounded to avoid the macOS flake regression).** Do NOT change the current "start-time unobtainable → assume alive" default into an unconditional "crashed" — on macOS/Windows `get_process_start_time` returns `None` legitimately when `ps`/`wmic` is slow or the `lstart` format does not parse, so flipping it would wrongly mark live runs crashed (this is the documented macOS PID-liveness flake source). Instead: only treat the process as NOT the same when we have **positive evidence of a mismatch** (a readable `actual_start` that differs beyond `tolerance`, OR a confirmed script mismatch from 2b). When start-time is genuinely unreadable AND the script check was inconclusive, keep the conservative "assume alive". This narrows EC-07's dangerous branch (permission-denied on `/proc/<pid>/stat` → blindly alive) via the 2b script check without introducing false "crashed" verdicts. | `liveness.py:145-150` | Low–Medium (functionality) — **gated by 2d** | Unit tests: readable `actual_start` far from expected → not same; `actual_start=None` + script confirmed → same; `actual_start=None` + script inconclusive → same (conservative). |
| 2d | EC-05/06/07 | **Anti-regression gate (rubric D — do this FIRST).** Liveness determines run *status* (running/crashed), a domain invariant. Before changing 2b/2c, write characterization tests that pin the CURRENT correct verdicts for the common cases (Linux `/proc`, macOS `ps`, Windows via mocks): live matching PID → running; dead PID → crashed; matching PID+start → running. These must be green before AND after 2b/2c. Any intentional verdict change (e.g. the recycled-PID false-positive being corrected) is called out explicitly in the commit message as a deliberate correctness fix, not a silent behavior diff. | `tests/` (new), `liveness.py` | Low | New characterization tests pass pre-change; full suite green post-change; no unexplained verdict diffs. |
| 3 | EC-08 | Move `sorted(...)` inside the try in `packages.py` (or null-guard: `key=lambda x: (x["name"] or "").lower()`), so a `None` dist name yields `status="partial"` instead of crashing → run keeps tracking. | `packages.py` | Low | Test: `full-environment` mode with a mocked distribution whose `metadata["Name"]` is `None` → returns records + `status="partial"`, run not ghosted. |
| 4 | EC-09 | Cap `manual_subprocess_records` at `capture.subprocesses.max_tracked_commands` (reuse the existing key), matching `SubprocessSpy`. Stop appending past the cap (optionally record a truncation marker). | `core.py` | Low | Test: call `pubrun.subprocess.run` past the cap; assert list length is bounded. |
| 5 | EC-10, EC-11, EC-13 | Add subprocess `timeout=` to all `hardware.py` and macOS/Windows `resources.py` external calls; make them configurable. **Exact keys + DECISION (user) defaults (add to `default.toml` with comments, matching existing sections):** `[capture.hardware].timeout` (default **10**), `[capture.resources].poll_timeout` (default **3**; the `[capture.resources]` section already holds `sample_interval_seconds`/`max_consecutive_failures`), `[capture.git].timeout` (default **5**; `[capture.git]` already holds `check_dirty`). **The git timeout must apply to the repo-detection call `rev-parse --show-toplevel` (git.py:39), not only the dirty check** — `check_dirty=false` does not cover it. On timeout in hardware capture set `hardware_data.capture_state.status = "timeout"` (a terminal state distinct from "pending"). In `git.py`, distinguish a `TimeoutExpired` (record `capture_state.status = "timeout"` / detail "git timed out") from a genuine non-repo/`git`-missing so the manifest never falsely claims "Not a git repository". | `hardware.py`, `resources.py`, `git.py`, `resources/default.toml`, `docs/configuration.md`, `docs/manifest.md` | Low | Tests mocking a slow/raising subprocess → capture returns a terminal `timeout`/`unavailable` status, no hang beyond the timeout, child not left running; a mocked git `TimeoutExpired` → status `timeout`, not `unavailable`. |
| 6 | EC-12 | Make the resource-watcher self-abort less brittle: only count a *raised exception / unreadable poll* (not a legitimate RSS of 0) toward the consecutive-failure counter. The existing `[capture.resources].max_consecutive_failures` (default 3, `resources.py:229-237`) key stays as-is — do NOT add a new key; just change what counts as a "failure" so a transient 0 never permanently disables telemetry. | `resources.py` | Low | Existing `test_resource_watcher_failure_threshold` updated to reflect the new semantics + a test that a legitimate 0-RSS poll does not count toward the threshold and sampling continues. |
| 7 | EC-14 | Make config loading tolerant: wrap each `tomllib.loads(...)` in `load_local_config`/`load_user_config` in try/except that logs a warning and skips the malformed file (returns the rest), so no CLI command crashes on a bad `.pubrun.toml`. | `config.py` | Low | Test: malformed `.pubrun.toml` → `resolve_config()` returns defaults+valid layers with a warning, `pubrun status` runs. |
| 8 | EC-15, EC-16 | (a) Make `_restore_excepthook` identity-guarded like `console.py` (only restore if current hook is still ours). (b) Broaden the console tee passthrough guard beyond `BrokenPipeError` (catch `(OSError, ValueError)` around the passthrough write). | `signals.py`, `console.py` | Low | Tests: install a later excepthook, stop pubrun, assert the later hook survives; tee write to a closed original stream does not raise out of `write()`. |
| 9 | EC-17, EC-20 | **DECISION (user):** store timestamps as UTC epochs (already the case) and **display local time by default**, with an opt-in `--utc` flag that renders UTC. Add `--utc` to the relevant `status`/`show`/`inspect` argparse subcommands; thread it into `_format_timestamp(epoch, utc: bool = False)` (local by default; `datetime.fromtimestamp(epoch, tz=timezone.utc)` when `--utc`). Label the zone in output either way (local shows the local offset or a "local" note; `--utc` shows `Z`/"UTC"). This makes the zone explicit and user-controlled, resolving the status-vs-diff ambiguity without forcing UTC on everyone. Also mark `event_count` as an estimate ("~N est."). **Grep tests for local-time status assertions and update as needed** (local remains the default so most should be stable). | `status.py`, `__main__.py` (argparse), `docs/cli.md`, `tests/` | Low | Test: `_format_timestamp(epoch)` (local) and `_format_timestamp(epoch, utc=True)` (UTC `Z`); `pubrun status --utc` renders UTC; default renders local; malformed epoch → "-". |
| 10 | EC-18, EC-19 | Diff robustness: guard `unflatten_manifest` against scalar/dict prefix collisions; guard `_normalize_manifest` against non-list `variables`/`records`; use identity-aware list-diff (compare by `repr`/type-tagged value) so `True`/`1` do not alias; note duplicate-env-name collapse. | `diff.py`, `render.py` | Low–Medium (complexity: keep the diff logic simple; do the minimal type-tag) | Tests: manifest with `a.b` scalar + `a.b.c`, env var with `.`, list containing both `1` and `True`; export + diff succeed with correct output. |
| 11 | EC-21, EC-22, EC-24, EC-25, EC-26 | Small correctness/hygiene fixes: normalize `sep`/`end` in `pubrun.print` inside the guard; make combined-log sort stable/robust for empty timestamps (secondary key = original order); make `_pubrun_logged` set atomic under a lock; record failed `pubrun.subprocess.run` invocations; replace the mutable default arg with `None`. | `core.py`, `__main__.py`, `diff.py` | Low | Targeted unit tests for each. |

## Deferred / out of scope (with reason)

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| EC-27 (signal-handler finalization) | Medium-High | Functionality / Complexity | `_make_handler` runs full finalization (`write_artifacts` → JSON I/O, `hashlib`, a 2s thread join, lock acquisition) **inside** the SIGTERM/SIG_DFL signal handler (`signals.py:176-190`). This is not async-signal-safe and can deadlock/hang shutdown if the signal interrupts a thread holding `_run_lock` or mid-write. The correct fix (defer finalization to a self-pipe/flag drained on the main thread, or restrict signal-context work to a minimal atomic write) is a real redesign of the crash-safety path with meaningful regression risk to the very mechanism that guarantees artifacts on SIGTERM. Do NOT bundle it with the low-risk hardening above. | Dedicated design pass (consider a `spec`/`advise architect` session) then its own IPD with characterization tests for the SIGTERM/SIGINT/SIGHUP finalization paths across platforms. |

Nothing else is deferred. Every other finding's fix is low Remediation Risk and is
proposed above. No finding was dropped for effort.

## Scope check

- **Over-scope:** none proposed. The changes are guards, a configurable timeout, and a
  bounded list — no new abstractions, no new dependencies, no `rich`. The one item with
  redesign temptation (EC-27) is explicitly deferred to guard the Complexity axis.
- **Under-scope (added by default):** subprocess timeouts for hardware/resources
  capture (EC-10/EC-11) and a terminal `"timeout"` hardware state are missing
  capabilities the tool needs to be honest under hung tools; config tolerance for
  malformed TOML (EC-14) is a missing robustness the ghost-mode philosophy implies.

## Execution order and commit grouping

- **Do Step 2d (liveness characterization tests) BEFORE Steps 2a–2c.** Everything else
  is order-independent.
- Suggested commit grouping (keep product changes separate from the test-only commit
  per the project's convention): (1) status-reader hardening (Steps 1, 9-status parts),
  (2) liveness (2d then 2a-2c), (3) capture timeouts + config + docs (Step 5),
  (4) resource-watcher + config-TOML tolerance (Steps 6, 7), (5) hooks (Step 8),
  (6) memory cap + diff + hygiene (Steps 4, 10, 11), (7) the new tests in one commit,
  (8) CHANGELOG/docs sync. Adjust as convenient, but never bundle a behavior change
  with an unrelated one.

## KISS / dependency guardrail (rubric G)

- **No new runtime dependencies, no `rich`, no new abstraction layers.** Every change
  is a defensive guard, a configurable timeout, a bounded list, or a helper local to
  its module. If any step seems to require a new dependency or a broad refactor, STOP
  and raise it as an open question rather than expanding scope. This is the Complexity
  counterweight to fix-by-default.

## Required tests / validation

- New regression tests for every proposed step (enumerated in the Validation column).
  Group the *new-test* additions into one commit per the project's testing-IPD
  convention; the liveness characterization tests (Step 2d) are the exception — they
  land before the liveness code change so they can be shown green pre- and post-change.
- Full suite green: `~/venv/p3.14/bin/python -m pytest tests/ -q`
  (baseline: 599 passed, 2 skipped, 1 known-flaky `test_real_sigpipe_via_pipe` — confirm
  any failure reproduces in isolation before treating it as a regression).
- Manual smoke: create a run dir with a hand-edited malformed `manifest.json`/lock
  (string `started_at_utc`, non-dict `signals_received`) and confirm `pubrun status`,
  `pubrun show`, `pubrun inspect` all still work and degrade only that run.
- Confirm no behavior change on the happy path. Existing tests should stay green
  unchanged EXCEPT: the resource-watcher threshold test (Step 6) and any status
  timestamp assertion that hardcodes local-time formatting (Step 9) — both must be
  updated in the same commit as the code change, with the change explained.

## Spec / documentation sync

User-visible behavior changes requiring doc/CHANGELOG updates (per AGENTS.md doc-sync):

- New config keys `[capture.hardware].timeout`, `[capture.resources].poll_timeout`,
  `[capture.git].timeout` → `docs/configuration.md`, `default.toml` (with comments),
  `docs/manifest.md` (new hardware/git `"timeout"` capture_state), `README` if it lists
  config.
- Status timestamps switching to UTC and the `event_count` estimate label →
  `docs/cli.md` / status output docs.
- `CHANGELOG.md` `[Unreleased]`: add the hardening entries.
- After execution, run `/assess documentation` to verify.

## Open questions — RESOLVED (user decisions 2026-07-05)

1. **Timezone for `status.py`:** RESOLVED — store UTC, **display local by default, add
   `--utc` flag** for UTC display. (See Step 9, updated.)
2. **Default timeouts:** RESOLVED — hardware **10s**, git **5s**, resource poll **3s**.
   (See Step 5, updated.)
3. **EC-27 (signal finalization):** RESOLVED — **defer** to its own design pass.
   (Remains in the Deferred table.)
4. **Liveness strictness (EC-06/EC-07):** RESOLVED — **accept the correctness fix**; a
   run wrongly shown "running" due to a recycled-PID false-positive may now correctly
   show "crashed". Gated by Step 2d characterization tests; intentional verdict changes
   are called out in the commit.

Execution approved by the user on 2026-07-05.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution,
and it is NOT auto-executed. Recommended next steps:

1. Review this IPD (optionally run the `plan-review` workflow to harden it).
2. On approval, execute the ordered changes, run the validation, and sync specs/docs.
3. Only then move this IPD from `.agents/plans/pending/` to `.agents/plans/executed/`.

## Plan-review revisions (2026-07-05)

Verdict: **APPROVE WITH REVISIONS APPLIED**. The plan-review re-read the actual source
(`liveness.py`, `default.toml`, `config.py`, `status.py`) to verify the plan's claims
and hardened it. No finding required a re-plan; the approach is sound. Changes:

- **PR-01 / PR-02 (High, rubric D + functionality):** the original single Step 2 for
  liveness refactored run-status logic (a domain invariant) without pinning current
  behavior, and its "do not default to alive" instruction, if executed literally, would
  have flipped legitimate macOS/Windows runs to "crashed" whenever `ps`/`wmic`
  start-time reads fail — exactly the known macOS PID-liveness flake source. Split into
  2a (unambiguous `pid<=0`/overflow guard — no flip risk), 2b (tighten script match,
  preferring the exact-basename branch that already exists at `liveness.py:68`), 2c
  (conservative start-time handling: only mark "not same" on positive mismatch
  evidence, keep "assume alive" when start-time is genuinely unreadable), and 2d
  (mandatory characterization tests FIRST, per rubric D).
- **PR-06 (Medium):** Step 1 (EC-01) now names a single coercion choke point
  (`_as_float`/`_as_int` helper routed through both loaders) plus a per-run try/except
  backstop, instead of scattered guards.
- **PR-03 (Medium):** Step 5 now names the exact TOML sections/keys (all under existing
  `[capture.hardware]`/`[capture.resources]`/`[capture.git]` sections) and calls out
  that the git timeout must cover the repo-detection `rev-parse --show-toplevel` call
  (not just the dirty check) and must record a distinct `"timeout"` status.
- **PR-04 (Medium):** Step 6 (EC-12) clarified to reuse the existing
  `max_consecutive_failures` key (no new key) and only change what counts as a failure.
- **PR-05 (Medium, rubric F):** added an "Execution order and commit grouping" section
  (Step 2d first; suggested commit split) and the exact venv pytest command.
- **PR-07 (Low):** Step 9 now requires grepping/updating any existing local-time status
  assertions in the same commit as the UTC switch, so the diff is not silently masked.
- **PR-08 (Low, rubric G/H):** added an explicit KISS / no-new-dependency / no-`rich`
  guardrail with a STOP-and-ask instruction if any step appears to need one.

No new findings were deferred; every plan-review finding was fixed in place. The IPD's
own deferral (EC-27) remains correctly deferred (Medium-High Remediation Risk on
Functionality/Complexity).
