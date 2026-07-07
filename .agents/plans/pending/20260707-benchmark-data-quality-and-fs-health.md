# IPD: benchmark data quality + filesystem-health capture

- Date: 2026-07-07
- Concern: data quality / observability. Make the shared benchmark result carry the signal
  needed to *interpret* it (raw timing distribution, environment kind, per-filesystem
  classification + live capacity), and surface genuinely system-wide filesystem hazards
  (hung/slow/network-backed mounts) to the user via `pubrun self-check`. Motivated by two
  questions raised while reviewing the submission flow: (a) summary stats vs. raw timings,
  and (b) what analysis signal is lost when we redact all paths.
- Scope:
  - `benchmarks/harness.py` (schema `/3` → `/4`: raw timings, more classified paths,
    environment kind).
  - `src/pubrun/capture/filesystem.py` (Linux `/proc/self/mountinfo`, Windows `ctypes`
    fstype branch, optional threaded live probe: `os.statvfs` on all POSIX incl. macOS,
    `GetDiskFreeSpaceExW` via `ctypes` on Windows — `getmntinfo` is intentionally NOT used
    (needless ctypes complexity; see OQ4), abandon-on-hang).
  - `src/pubrun/report/checks.py` (`self-check` surfaces hung/slow/network mounts).
  - `src/pubrun/capture/__init__.py` / environment capture helper for `environment_kind`.
  - Config default(s), docs, tests.
- **Hard constraints (unchanged tenets):** zero new runtime deps (stdlib + `ctypes` only);
  the always-on `import pubrun` path must NOT gain any blocking probe (the 5s threaded
  statvfs is bench/diagnostic-ONLY); never intrude on/slow/crash the host script; honest
  docs; degrade gracefully; redaction stays maximally aggressive on literal paths (PII).
- Status: PENDING (proposal only; human approval required; NOT auto-executed).
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

1. **Summary-only timings are lossy and un-poolable.** The harness records only
   min/median/mean/p95/max/stdev (`harness.py:228-243`). From summaries you cannot: compute
   a statistic you didn't include today, see distribution shape (bimodality from GC/JIT/CPU
   migration/node contention), detect order/warmup drift, or **correctly aggregate across
   submissions** (`median(median_A, median_B)` ≠ combined median). For a community dataset
   feeding a paper, the raw samples are the source of truth. 30 floats ≈ hundreds of bytes —
   size is a non-argument.
2. **Redacting all paths loses interpretive signal, not just PII.** The redactor masks
   `virtual_env`/`prefix`/`base_prefix`/`sys_path`/`tmpdir`/`mount_point` etc. (correct — those
   are PII/re-identifying). But with them gone we can no longer tell: venv vs conda vs system
   Python; whether `$TMPDIR`/`/dev/shm`/the Python install sit on NFS (which dominates
   startup/I-O time); or *why* an I/O-baseline scenario is an outlier. The fix is NOT to
   redact less — it is to **capture the derived, non-identifying classification** (fstype
   enum, env-kind enum, counts) so the signal survives redaction.
3. **We classify fstype but not live state.** `/proc/mounts` parsing tells us the *type*; it
   cannot tell us free space, inode exhaustion, read-only mounts, or — most importantly —
   that a mount is **wedged/slow**, which is itself a first-class performance finding and the
   classic HPC failure (NFS/Lustre/GPFS home dirs).

## Project conventions discovered (Step 0)

- `capture/filesystem.py` (IPD-A): non-blocking fstype classification via `/proc/mounts`
  (Linux) / `mount` with subprocess timeout (macOS); **Windows unsupported** (returns
  `failed`). Runs in the `pubrun-hw` startup thread whose result the finalizer waits on with
  a ~2s budget (`tracker.py:446-447`) — which is *why* it must never `statvfs`/`df`/`stat`
  the target. `_NETWORK_FSTYPES` set + `_is_network_fstype` already exist. Docstring already
  names `/proc/self/mountinfo` as the more accurate source (not yet parsed).
- `report/checks.py`: `_finding(severity, code, message, suggestion)` model;
  `_network_fs_findings` (`:56`) already emits `WARN` for `is_network` paths;
  `_live_paths` (`:36`) classifies `tmpdir`/`cwd`/`pubrun_install`/`output_dir`. CLI-only
  (not imported by `import pubrun`).
- `harness.py`: `_stats` (`:228`), per-scenario entry build (`:280`), `_filesystem_context`
  (`:128`, classifies `tmpdir`/`results_dir`/`pubrun_install`), schema `pubrun-benchmark/3`
  (`:299`), `redact_result` + key sets (`:353`).
- Env-capture already records `python.executable/prefix/base_prefix/virtual_env/sys_path`
  (redacted by the share redactor).
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Design decisions (agreed with maintainer, 2026-07-07)

- **Store raw timings AND the summary** (maintainer choice). `timings: [...]` in **run order**
  = source of truth; the existing summary block stays for human readability (redundant but
  cheap; matches pytest-benchmark / hyperfine). Schema bumps `/3` → `/4`.
- **Capture redaction-surviving classifications** so the signal lost to path-redaction is
  recovered as non-identifying scalars: `environment_kind`, `in_venv`, `sys_path_len`, and
  per-relevant-path `fstype`/`is_network`.
- **Classify more paths**, including the Python install dir and each I/O-baseline target.
- **Do items 4 (mountinfo) and 5 (Windows fstype) as well** (maintainer chose to include the
  accuracy upgrades, not defer them).
- **Threaded live `statvfs` probe with decoupled wait budget vs. probe lifetime**
  (maintainer's refinement): run the blocking capacity/flags syscall in a **daemon thread**.
  The *caller* waits only a short responsiveness budget (~5s) then continues; the *daemon
  keeps running* and, if it returns later (even mid-run), fills a shared slot we re-read
  (non-blocking) before process exit — so a *slow-but-alive* mount is captured (with its
  measured `elapsed_s`) rather than falsely called hung. Only a probe that never returns
  before exit is recorded as `hung`/`pending`; the daemon is abandoned (threads can't be
  killed in Python; a daemon dies with the process and never delays shutdown). This probe is
  **opt-in and bench/diagnostic-ONLY** — it must NEVER run on the always-on `import pubrun`
  path or inside the ~2s startup-thread budget. The fast mount-parse classification remains
  the default everywhere.
- **A hung/slow/network mount is a system-wide warning, honestly worded.** `pubrun self-check`
  surfaces it as a WARNING framed as affecting *any* script on the system, not just pubrun —
  and does NOT over-claim a slowdown number we didn't measure. Never printed on the import
  path.
- HPC multi-scheduler detection + login-node benchmark suggestion = **separate IPD** (out of
  scope here; `pubrun bench` already auto-detects + offers Slurm submission).

## Proposed changes

### 1. Raw timings (schema `/3` → `/4`)
- In the per-scenario entry (`harness.py:280`), add `"timings": [<float>, …]` in **run order**
  (the raw per-iteration wall times) alongside the existing `_stats(...)` summary. Keep
  `failures`, `n`, and the summary keys unchanged (backward-compatible superset).
- Bump `"schema"` to `"pubrun-benchmark/4"`. Note in `benchmarks/README.md` /
  `pubrun-benchmarks/README.md` what `/4` adds; keep `/3` consumers working (they read the
  summary keys, which remain).
- The redactor treats a `timings` list of floats as non-identifying (no change needed; it is
  numbers, not paths/ids). Add a test asserting `redact_result` preserves `timings`.

### 2. Environment kind (pure stdlib, cross-OS, redaction-surviving)
- New helper (e.g. in `capture/` env module, reused by harness + `self-check`) returning:
  - `environment_kind`: `"conda" | "venv" | "virtualenv" | "system" | "frozen"` derived from:
    conda → `CONDA_PREFIX`/`conda-meta` marker or `CONDA_DEFAULT_ENV`; venv → `sys.prefix !=
    sys.base_prefix` (PEP 405) corroborated by `VIRTUAL_ENV`; virtualenv → legacy
    `sys.real_prefix`; frozen → `getattr(sys, "frozen", False)`; else system.
  - `in_venv`: bool (`sys.prefix != sys.base_prefix`).
  - `sys_path_len`: `len(sys.path)` (int).
  - `pyenv`: bool modifier (`PYENV_VERSION` or `pyenv` in the interpreter path), orthogonal.
- Record these under the harness `machine`/`python` block; identical on Linux/macOS/Windows.
  None expose a path/username/home → survive redaction. **Redact the conda ENV NAME**
  (`CONDA_DEFAULT_ENV`) — keep only the *kind*.

### 3. Classify more paths + interpret the I/O baselines
- Extend `_filesystem_context()` (harness) and `_live_paths()` (checks) to also classify:
  - `python_prefix` = `sys.base_prefix` (stdlib/interpreter location — startup I/O source).
  - `devshm` = `/dev/shm` **iff it exists** (POSIX; skip on Windows/absent).
  - each **I/O-baseline target** actually used by the io-baseline scenarios. Note the
    scenarios (verified `benchmarks/scenarios.py:117-126`) target `/dev/null`, `/dev/shm`, and
    `$TMPDIR` via `PUBRUN_BENCH_IO_TARGET`. **`/dev/null` is a character device** — record only
    its *presence* (a mount-prefix classification would misleadingly attribute it to `/dev` or
    `/`); `/dev/shm` and tmpdir get a real fstype. Classify the actual target used, resolved
    from `PUBRUN_BENCH_IO_TARGET`, so a slow/odd baseline is interpretable after redaction.
- Keep recording fstype/is_network (survives redaction); the literal `mount_point`/`path`
  stays redacted as today.

### 4. Linux `/proc/self/mountinfo` accuracy upgrade
- Add a `_parse_proc_mountinfo()` that returns `(mount_point, fstype, mount_root, is_bind)`
  and prefer it over `/proc/mounts` when present (fall back to `/proc/mounts`). `mountinfo`
  disambiguates bind/overlay mounts and gives the super-block fstype. Pure file read →
  non-blocking. Do **not** trigger autofs (never stat the target; classify from the table
  only). Add a fixture-based parse test (bind mount + overlay + nfs sample lines).

### 5. Windows fstype branch (`ctypes`, non-blocking)
- Add a Windows path in `get_filesystem`: map path → volume root via `GetVolumePathNameW`,
  then `GetVolumeInformationW` for the fstype string (`NTFS`/`ReFS`/`FAT32`/`exFAT`), and
  `GetDriveTypeW` == `DRIVE_REMOTE` (+ optional `WNetGetConnection`) for the network signal.
  These are fast local calls (do not traverse share contents) → respect the non-blocking
  constraint. Guard all `ctypes`/`windll` behind `sys.platform == "win32"`; failures record
  `capture_state: failed`, never raise.

### 6. Optional threaded live probe (`statvfs`/`getmntinfo`/`GetDiskFreeSpaceExW`)
- New function (e.g. `probe_filesystem_live(path, timeout=5.0)`) that runs the **blocking**
  capacity/flags syscall in a **daemon thread** that writes its result into a shared slot.
  - POSIX: `os.statvfs(path)` → `total_bytes`, `free_bytes`, `avail_bytes`, `total_inodes`,
    `free_inodes`, `read_only` (`ST_RDONLY` in `f_flag`).
  - Windows: `GetDiskFreeSpaceExW` for capacity.
- **Decouple the caller's wait budget from the probe's lifetime (maintainer's refinement).**
  These are two different things and must not be conflated:
  - The **caller** (`self-check`/`bench`) waits only a short *responsiveness budget*
    (`wait_budget_s`, default ~5s) so the tool stays responsive, then STOPS blocking and
    continues.
  - The **daemon thread keeps running** (a blocked daemon costs ~nothing and Python never
    waits on daemons at exit, so it can never delay shutdown). If it returns later — even
    mid-run — it fills the shared slot. Before the process exits (end of `self-check`, or when
    the harness assembles the result JSON) we do a **non-blocking re-read** of the slot (never
    re-block, never busy-wait). This means a *slow-but-alive* mount (returns in, say, 34s) is
    actually captured instead of being falsely recorded as hung — which for a minutes-long
    benchmark run is the common, valuable case.
  - Three-way outcome recorded per path:
    - returns within `wait_budget_s` → `{"status": "complete", <metrics>, "elapsed_s": …}`.
    - returns after the budget but before process exit → `{"status": "complete", "slow": true,
      <metrics>, "elapsed_s": …}` (the elapsed time itself is a red-flag data point).
    - never returns before exit → `{"status": "pending", "hung": true, "waited_s": <run/final
      wait>}` and the daemon is simply abandoned (never joined/killed — threads can't be killed
      in Python; the daemon dies with the process).
- **Gating (critical):** exposed via a config flag defaulting **off** for capture, and invoked
  only by (a) `pubrun bench`'s `_filesystem_context` enrichment and (b) `pubrun self-check`.
  NEVER by the auto-start capture path / startup thread. Document this explicitly.
- **Bound the number of probes.** These invocations classify a small, fixed set of paths
  (tmpdir, output/results dir, pubrun/python install, /dev/shm, io-baseline targets) — a
  handful, deduplicated by mount. Cap the concurrent probe count and **dedupe by resolved
  mount point** so we never spawn one abandoned daemon per path when several share a wedged
  mount. A hung-mount scenario thus leaks at most a couple of harmless daemon threads (which
  die at process exit), not one per classified path.
- The harness attaches the live metrics (or the pending/slow status) to each classified path
  entry when enabled, and does the final non-blocking slot re-read at result-assembly time.
- **The `slow`-vs-`pending` window depends on the caller's lifetime, and that is fine.** In
  `pubrun bench` (runs for minutes) the daemon has a long window to return late → we usually
  capture `slow` with a real `elapsed_s`. In `pubrun self-check` (near-instant) the final
  re-read happens milliseconds after the budget, so a mount that is merely slow will more
  often be reported `pending` there. This is honest (we truly did not get an answer in the
  time we ran) and must be documented so the two commands' differing outputs are expected, not
  a bug. `self-check` may optionally offer a `--fs-probe-wait <seconds>` to extend its own
  budget for users who want to wait longer.

### 7. `self-check` surfaces hung/slow/network mounts (honest, system-wide)
- Extend `report/checks.py`: after classification + the optional live probe, emit `WARN`
  findings for (a) `is_network` paths (existing `_network_fs_findings`), (b) `slow: true`
  probes (report the measured `elapsed_s` — this one IS measured, so it may be stated), and
  (c) `hung: true`/`pending` probes, worded as a **system-wide** hazard:
  > "`$TMPDIR` (…) is on nfs4 and a capacity probe did not return within the run (still
  >  pending). Any script doing temp I/O on this system — not just pubrun — is likely to
  >  stall or run slowly here."
  and, for the slow case:
  > "`$TMPDIR` (…, nfs4): a capacity probe took 34s to return. I/O on this system is likely
  >  slow for any script, not just pubrun."
- Guardrails: (i) only in `self-check`/`inspect`/`bench` (never the import path); (ii) state
  the measured `elapsed_s` for the *slow* case (it is measured), but for the *hung/pending*
  case say "likely" and do NOT invent a slowdown magnitude; (iii) never crash if the probe is
  disabled/unavailable (degrade to fstype-only wording).

## Anti-regression / invariants

- **Import path stays non-blocking and silent.** No blocking probe and no filesystem WARNING
  is ever triggered by `import pubrun` / auto-start / the ~2s startup thread. **Test:** the
  startup fstype capture still uses the mount-parse path only; the live probe is not called
  from the capture/auto-start code (grep + a test that auto-start capture makes no `statvfs`
  call — monkeypatch `os.statvfs` to fail-if-called during a tracked run).
- **Threaded probe cannot hang the caller.** **Test:** with `os.statvfs` monkeypatched to
  sleep beyond the timeout, `probe_filesystem_live` returns within ~timeout with
  `{"hung": true}` and does not join the daemon thread; a second call still works.
- **No new runtime dependency.** stdlib + `ctypes` only; Windows branch import-guarded.
  **Test:** modules import on non-Windows without touching `ctypes.windll`.
- **Redaction unchanged for PII; new fields survive.** `redact_result` still masks all literal
  paths/username/hostname (deep-scan test from IPD-C still passes), AND preserves `timings`,
  `environment_kind`, `in_venv`, `sys_path_len`, per-path `fstype`/`is_network`, and live
  capacity numbers. **Tests:** deep PII scan still clean; a positive test asserts each new
  non-identifying field survives redaction; the conda ENV NAME is masked.
- **Schema is a backward-compatible superset.** `/3` consumers reading summary keys still work
  (summary keys retained). **Test:** an old-shape consumer reads median/n from a `/4` result.
- **Graceful degradation everywhere.** No `/proc/self/mountinfo`, no `mount`, unsupported OS,
  probe disabled, probe timed out, Windows API failure — each records a per-path/top-level
  `capture_state`/`status` and never raises. **Tests** per branch (Linux fallback to
  `/proc/mounts` when mountinfo absent; unsupported-OS path; probe-disabled path).
- **`self-check` honesty.** Warnings for hung/slow/network mounts use "likely"/"can be" and
  attribute the hazard system-wide, not to pubrun. **Test:** finding message contains no
  fabricated magnitude and the finding fires only when the signal is present.
- **No shell injection / no autofs trigger.** macOS `mount` stays argv-list + timeout;
  classification never stats the target (no automount trigger). (Unchanged; assert in test.)

## Required tests / validation

- `_stats`/entry: `timings` present, length == n, in run order; summary keys unchanged.
- `environment_kind`: venv (prefix≠base_prefix), system (equal), conda (CONDA_PREFIX marker),
  frozen (`sys.frozen`); `in_venv`/`sys_path_len` correct; conda env NAME redacted.
- `/proc/self/mountinfo` parse fixture (bind + overlay + nfs); prefers mountinfo, falls back
  to `/proc/mounts`.
- Windows fstype branch: mock `ctypes.windll` calls → returns fstype + `DRIVE_REMOTE` network
  flag; failure → `capture_state: failed`.
- Threaded probe (decoupled model): (a) fast return within budget → `complete` + metrics;
  (b) returns *after* the caller's wait budget but before final re-read → `complete` +
  `slow: true` + measured `elapsed_s` (monkeypatch `os.statvfs` to sleep > budget but <
  final-read; assert the caller returned at ~budget yet the final slot re-read picks up the
  late result); (c) never returns → `pending`/`hung: true` + `waited_s`, daemon abandoned (not
  joined), caller unblocked at ~budget, a second probe still works; (d) disabled → not called.
- Import-path safety: tracked run makes no `statvfs` call (monkeypatch fail-if-called).
- Redaction: deep PII scan clean; new non-identifying fields survive; conda name masked.
- `self-check`: emits network + hung/slow WARNINGs with honest wording only when signal present;
  no crash when probe disabled.
- Full suite green (clear `__pycache__` first:
  `find src tests benchmarks -name __pycache__ -type d -exec rm -rf {} +`).

## Spec / documentation sync

`docs/manifest.md` (document `environment_kind`/`in_venv`/`sys_path_len` and per-path
`fstype`/`is_network` where they appear; be explicit that the **live-probe capacity/hung/slow
fields do NOT appear in the normal run manifest** — they surface only in the benchmark result
JSON and `self-check` output, because the probe is diagnostic-only and defaults off),
`docs/configuration.md` (the live-probe flag, default off, why), `docs/cli.md`
(`self-check` filesystem-health warnings; `bench` `/4` result contents), `docs/hpc.md`
(hung/slow-mount hazard + self-check), `benchmarks/README.md` + `pubrun-benchmarks/README.md`
(schema `/4`: raw timings + classifications), `CHANGELOG.md`. Run `/assess documentation`.

## Open questions (for plan-review / maintainer)

1. **Live-probe control — RESOLVED (maintainer 2026-07-07):** CLI-driven only for
   `bench`/`self-check` (each enables the probe for its own invocation); **no config key** —
   normal capture never records live metrics, so `[capture.filesystem].live_probe` is NOT
   added (less config surface, KISS).
2. **`environment_kind` location — RESOLVED (maintainer 2026-07-07):** a new small shared
   `capture/` helper imported by BOTH the harness and `report/checks.py`, so venv/conda/system
   detection cannot diverge between them.
3. **Raw-timings size cap — RESOLVED (maintainer 2026-07-07):** raw-only now, no cap/histogram
   (n is tiny by default; the size concern is theoretical). A histogram-above-threshold is a
   clean later optimization if it ever matters.
4. **`getmntinfo` on macOS — RESOLVED (plan-review):** use `os.statvfs` on all POSIX
   (including macOS) in the threaded probe. `getmntinfo` would add ctypes complexity for no
   extra benefit (KISS / Fix-Bar complexity axis). Dropped from scope.

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-07)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verified code claims: `_stats`
+ per-scenario entry (`harness.py:228`, `:280`), `_filesystem_context` targets (`:128`),
`capture/filesystem.py` non-blocking design + `_NETWORK_FSTYPES`, `report/checks.py`
`_finding`/`_network_fs_findings`/`_live_paths` (`:30`, `:56`, `:36`), io-baseline scenarios
+ `PUBRUN_BENCH_IO_TARGET` (`scenarios.py:117-126`). Verdict: **APPROVE WITH REVISIONS
APPLIED.**

- **(defect, BLOCKER-for-doc-integrity):** removed a stray trailing ```` ``` ```` code fence
  that left the document in a malformed state.
- **DQ1 (MEDIUM, functionality):** bounded the probe count + dedupe-by-mount so a wedged mount
  leaks at most a couple of harmless daemon threads, not one per classified path. Fixed
  in change 6.
- **DQ2 (MEDIUM, functionality):** `/dev/null` is a char device — record presence only (a
  mount-prefix classify would misattribute it to `/dev`/`/`); classify the resolved
  `PUBRUN_BENCH_IO_TARGET`. Fixed in change 3.
- **DQ3 (MEDIUM, complexity/KISS):** dropped `getmntinfo` from scope; use `os.statvfs` on all
  POSIX incl. macOS (needless ctypes complexity). Fixed in scope bullet + OQ4 resolved.
- **DQ4 (MEDIUM, functionality):** documented that the `slow`-vs-`pending` window differs by
  caller (bench = minutes → captures `slow`; self-check = instant → often `pending`), which is
  honest, not a bug; optional `--fs-probe-wait`. Fixed in change 6.
- **DQ5 (LOW, docs/honesty):** clarified that live-probe capacity/hung/slow fields do NOT
  appear in the normal run manifest (diagnostic-only, off by default) — only in benchmark JSON
  + self-check output. Fixed in Spec/doc-sync.

Deferred/open: OQ1 (live-probe config key vs CLI-only), OQ2 (helper location), OQ3 (raw-timings
size cap / histogram) — all decidable at execution with the stated leanings; none carry
Medium-High+ Remediation Risk.
