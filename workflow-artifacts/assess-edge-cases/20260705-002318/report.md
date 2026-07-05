# Assessment - edge-cases (whole project, emphasis on manifest/lock readers + external-command capture)

Verdict: **needs work** for edge-cases / failure modes.

IPD written: `.agents/plans/pending/20260705-assess-edge-cases.md`

Run ID: `20260705-002318`
Repo: `~/VC/pubrun` @ HEAD `0f2e34b` (v1.3.1). Baseline: 599 passed, 2
skipped, 1 known-flaky (`test_real_sigpipe_via_pipe`, passes in isolation).

## Summary

pubrun's core promises are (1) never crash the host script and (2) never silently
record wrong provenance or make a wrong automated decision. The library-side
golden-rule guarding is generally strong (ghost mode, broad excepts in hooks, config
fallback in `Run.__init__`). The weak spots are on the **read/report side and the
external-tool capture side**:

- The `pubrun status`/`show`/`inspect` reader is not robust to malformed, truncated,
  hand-edited, or foreign-version manifests/locks: a single bad `started_at_utc`,
  timestamp, or `signals_received` shape throws an **uncaught** `TypeError`/`ValueError`
  from inside `RunInfo` construction/rendering and **crashes the whole listing** for
  all runs (the `except (json.JSONDecodeError, OSError)` catches are too narrow, and
  `scan_runs` builds each `RunInfo` with no per-entry guard).
- PID-liveness has three wrong-decision paths: non-positive PIDs into `os.kill(pid,0)`,
  substring script matching, and defaulting to "alive" when start-time is unreadable.
- External-tool capture (`hardware.py`, macOS/Windows `resources.py`) has **no
  subprocess timeouts**, so a hung `nvidia-smi`/`system_profiler`/`ps` orphans a thread
  + child and leaves a non-terminal `"pending"` hardware state in the manifest. Git
  capture's 1s timeout silently reports a slow/large repo as "not a git repository".
- `manual_subprocess_records` grows unbounded (OOM risk under tight loops).
- `packages.py` can crash out of the try (→ ghost mode) on a `None` distribution name
  in non-default modes.

All 27 findings' fixes are Low Remediation Risk except one (EC-27, signal-handler
finalization), which is deferred to a dedicated design pass on Functionality/Complexity
grounds.

### Top findings

| ID | Severity | Remediation Risk | Persona | Finding |
|----|----------|------------------|---------|---------|
| EC-01 | High | Low | QA | Non-numeric `started_at_utc` in a lock/manifest → uncaught `TypeError` crashes the entire `pubrun status` for all runs |
| EC-02 | High | Low | QA | Sort key `started_at_utc or 0` crashes on a string value (str vs int) |
| EC-03 | High | Low | QA | `_format_timestamp` `datetime.fromtimestamp(epoch)` crashes on string/NaN/out-of-range epoch |
| EC-09 | High | Low | SWE | `manual_subprocess_records` uncapped → unbounded growth / OOM |
| EC-10 | Medium | Low | SWE | No subprocess timeout in hardware capture → orphaned hung child + "pending" state in manifest |
| EC-05 | Medium | Low | Sec/SWE | `os.kill(pid,0)` unguarded for `pid<=0` → wrong RUNNING verdict |
| EC-13 | Medium | Low | Stakeholder | 1s git timeout → slow/large repo silently "not a git repository" |
| EC-08 | Medium | Low | SWE | `packages.py sorted().lower()` outside try → `None` dist name crashes → run ghosted (non-default modes) |
| EC-14 | Medium | Low | QA | Malformed `.pubrun.toml` crashes `pubrun status` (config load not guarded at all call sites) |
| EC-17 | Medium | Low | Domain | Status renders timestamps in local time; diff renders UTC — inconsistent for a provenance tool |

(Full 26-finding table + EC-27 deferred in the IPD and `findings.csv`.)

### Proposed plan (summary)

1. Harden the status reader: coerce/validate numeric fields, per-run try/except in
   `scan_runs`, safe sort key, guarded `_format_timestamp`, guarded `signals_received`.
2. Harden liveness: reject `pid<=0`/overflow, stricter script match, no blind "alive".
3. Move `packages.py sorted()` inside the try / null-guard names.
4. Cap `manual_subprocess_records`.
5. Add configurable subprocess timeouts to hardware/resources/git capture; terminal
   `"timeout"` hardware state; distinguish git timeout from no-repo.
6. Make the resource-watcher self-abort robust to transient zeros.
7. Tolerate malformed TOML in config loading (warn + skip file).
8. Identity-guard excepthook restore; broaden console-tee passthrough guard.
9. UTC-standardize status timestamps; label event-count estimate.
10. Diff robustness (prefix collisions, non-list normalize inputs, bool/int aliasing).
11. Small hygiene: `pubrun.print` sep/end, combined-log sort, Popen log race, failed
    manual-subproc record, mutable default arg.

### Deferred (with reason)

- **EC-27** (signal-handler finalization runs JSON I/O + locks + a 2s thread join
  inside the SIGTERM handler → deadlock/hang risk): Remediation Risk Medium-High on
  Functionality/Complexity. Fixing it correctly is a redesign of the crash-safety path
  with regression risk to the mechanism that guarantees artifacts on SIGTERM. Deferred
  to a dedicated design pass + its own IPD with cross-platform characterization tests.

Next step: review the IPD (optionally run `plan-review` on it) and approve before
execution. This workflow does not execute the plan.
