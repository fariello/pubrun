# IPD-A: benchmark dynamic-state + filesystem capture (per-pass) & async run-time I/O enrichment

- Date: 2026-07-06
- Concern: measurement fidelity + provenance completeness. Two related capture gaps:
  (1) the benchmark harness snapshots host metadata only once and captures no dynamic
  state or filesystem info, so results across machines/nodes are silently confounded;
  (2) a normal pubrun run captures nothing that would let anyone later tell a run was
  I/O-bound on a slow network filesystem.
- Scope: `benchmarks/harness.py` (metadata timing + new fields) and `src/pubrun/capture/`
  (new lightweight, no-dep filesystem/free-RAM/load capture, wired into the EXISTING
  background threads). No new runtime dependency. No change to host-script behavior.
- Status: EXECUTED (2026-07-06). Both parts implemented, tested (15 new tests),
  documented; hang-safe fstype probe and node-wide-iowait honesty labeling per the
  plan-review re-pass. 710 passed / 2 skipped (only the known SIGPIPE flake fails, passes
  in isolation). See the execution record at the end.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

Verified against the code (2026-07-06):

- **Benchmark harness** (`benchmarks/harness.py:82-104`, `_machine_metadata`) captures
  hostname, OS, CPU model/arch/logical-cores, GPU, **total** RAM, Python, git commit —
  and captures it **exactly once, before pass 1** (`harness.py:236`), NOT at the start of
  each pass. It captures **no** free/available/cached RAM, **no** load average, **no**
  filesystem type/mount, **no** disk metrics, and **no** Slurm allocation context. So a
  node that gets loaded between the two passes, or a `$TMPDIR`/output dir on NFS, is
  invisible in the result JSON — exactly the Unity-cluster NFS scenario the maintainer
  hit. (Confirmed: zero `nfs|mount|statvfs|loadavg|iowait` capture anywhere in
  `benchmarks/` or `src/pubrun/capture/`.)
- **Normal runs** capture `host` (hostname/OS), `hardware` (CPU/GPU/**total** RAM), and,
  when the resource watcher is on, per-process **RSS + CPU%** every 15s
  (`resources.py:168,208`). There is **no** signal that would reveal a run was crippled
  by slow I/O: no fstype of the output dir, no free RAM over time, no load average, no
  iowait. The maintainer's instinct is correct — pubrun cannot currently infer an I/O
  problem after the fact. This IPD adds the (cheap, async) capture that makes post-hoc
  I/O diagnosis POSSIBLE (the diagnosis command itself is IPD-B).

## Project conventions discovered (Step 0)

- Principles (`AGENTS.md`/`README.md`): zero *runtime* deps (tomli only <3.11), KISS,
  honest docs, **never intrude on / crash / slow the host script**, degrade gracefully.
- pubrun ALREADY does light async work during a run (this is the key enabler):
  - `ResourceWatcher` daemon thread, 15s default interval, `/proc/self/statm` + `os.times()`
    (`resources.py:168-209`); self-aborts after 3 failures; bounded shutdown.
  - One-shot `pubrun-hw` daemon thread for slow hardware/GPU probing (`tracker.py:291-294`).
- Manifest host identity = `host.hostname` (`tracker.py:613`, read at `status.py:236`).
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Design decisions (already discussed with maintainer)

- **Enrichment is asynchronous and reuses the existing threads** — no new thread. Static,
  cheap-once fields (fstype/mount, free RAM at start, load at start) go into the one-shot
  `pubrun-hw` startup thread; time-varying fields (free RAM, load average, and optionally
  Linux iowait) are sampled by the EXISTING 15s `ResourceWatcher` loop so I/O pressure is
  visible over time, not just at start.
- **Zero new dependency, stdlib only:** Linux via `/proc` (`/proc/mounts`, `/proc/meminfo`
  `MemAvailable`, `/proc/loadavg`, `/proc/stat` iowait) and `os.statvfs`; macOS best-effort
  (`os.getloadavg`, `vm_stat`/`df -T` equivalents); Windows minimal (clearly report
  "not available"). Honest about what could not be determined — never guess.
- **Never intrude:** all new capture is read-only `/proc`/`statvfs`, runs in the existing
  daemon threads, must never raise into the host script, and is gated by the same
  `capture` config that already gates hardware/resource capture. If any probe fails it
  records `{"status": "failed", "detail": ...}` (matching the existing `capture_state`
  pattern) and continues.

## Proposed changes

### Part 1 — Run-time capture enrichment (`src/pubrun/capture/`)

1. **New `capture/filesystem.py`** (`get_filesystem(config, paths)`): for the run output
   dir and `$TMPDIR` (and optionally `pubrun.__file__`'s dir), report `mount_point`,
   `fstype` (nfs/nfs4/lustre/gpfs/cifs/smb/ext4/xfs/tmpfs/overlay/…), and an
   `is_network` boolean.
   - **CRITICAL (plan-review re-pass 2026-07-06, HIGH): the fstype probe must NEVER block
     on a sick network mount — the very thing it detects.** `os.statvfs()`, `df`, `stat`,
     and any path-touching call **block indefinitely on a hung/stale NFS/Lustre mount**.
     Since this probe runs in the `pubrun-hw` thread whose result the finalizer waits on
     with only a **2.0s timeout** (`tracker.py:446-447`), a blocking probe would either
     (a) silently miss the 2s window (fstype stuck `pending`) or (b) wedge a `df`
     subprocess. **Design mandate:** classify fstype by PARSING `/proc/mounts` +
     `/proc/self/mountinfo` ONLY (pure file reads that do NOT touch the target mount), doing
     a longest-prefix match of the resolved path against mount points. Do **NOT** call
     `os.statvfs`/`df`/`stat` on the target path for fstype. On macOS use the pre-read
     `mount` table output with a hard subprocess timeout; never a per-path `statvfs`.
     Windows: drive-type via `GetDriveType`-style lookup (no network round-trip). If the
     probe cannot classify within budget, record `{"status": "failed", "detail": ...}` and
     move on. A test simulates a mount whose `statvfs` would hang and asserts the probe
     still returns via `/proc/mounts` parsing without calling the blocking path.
   - Called once from the `pubrun-hw` startup thread; must complete well within the 2.0s
     finalizer budget (`tracker.py:446-447`). If it cannot, the manifest records `pending`/
     `failed` rather than delaying finalize.
2. **Extend memory/load capture:** add `MemAvailable`/`MemFree`/`Cached` (Linux
   `/proc/meminfo`) and `os.getloadavg()` — captured once at start (startup thread) AND
   sampled in the `ResourceWatcher` loop (`resources.py`) so the manifest gets a small
   time series (start + peak/last, matching the existing RSS/CPU peak/end shape). Keep it
   cheap: these are single small reads.
3. **Optional Linux iowait** from `/proc/stat` deltas in the watcher loop (Linux only;
   omitted elsewhere with a clear "not available"). Gate behind the resource config so it
   is off when resource capture is off.
   - **Honesty caveat (plan-review re-pass, MEDIUM):** `/proc/stat` `iowait` is a
     **system-wide, per-CPU** counter, NOT process- or cgroup-scoped, and the Linux kernel
     docs themselves warn it is unreliable/misleading on multi-core and shared nodes (it
     can be attributed to the wrong task and reset by scheduler migration). On a shared HPC
     compute node it reflects the WHOLE node, not this run. Therefore label it in the
     manifest and docs as **`system_iowait_pct` (node-wide, not run-scoped; indicative
     only)** so no one over-reads it as "this run's I/O wait". It is a hint, not a
     measurement. (This is exactly why per-file `open()` provenance in IPD-E is the
     complementary precise signal.)
4. **Manifest additions** (new keys, additive, never renaming existing ones):
   `filesystem` (object), and within the resources section `system_memory`
   (total/available/cached at start + last) and `load_average` (start + last) and, when
   available, `iowait_pct`. Document in `docs/manifest.md`.
5. **Wire into `tracker.py`** alongside the existing host/hardware collection
   (`tracker.py:274-294`) and the watcher metrics (`resources.py:259-295`); gated by the
   same `capture.resources`/`capture.hardware` switches.

### Part 2 — Benchmark harness (`benchmarks/harness.py`)

6. **Capture dynamic state at the START OF EACH PASS** (the maintainer's explicit ask):
   record free/available RAM, load average, and (Linux) iowait at the start of pass 1 and
   pass 2, stored per-pass under `pass_results[i]` (e.g. `pass_env`). Keep the one-time
   static `machine` block, but ADD a per-pass dynamic block so a loaded node between
   passes is visible.
7. **Capture filesystem context** of the harness workdir/`$TMPDIR` and the results dir
   (reuse `capture/filesystem.py`), plus the resolved `pubrun.__file__` origin, into the
   `machine` block. This is what surfaces the "installed over NFS" case.
8. **Capture Slurm allocation context when present** (env vars: `SLURM_JOB_ID`,
   `SLURM_CPUS_PER_TASK`, `SLURM_MEM_PER_NODE`, `SLURM_JOB_PARTITION`, `SLURMD_NODENAME`)
   into the `machine` block, so cross-node results are interpretable.
9. **Bump the result schema** `pubrun-benchmark/2` → `/3` and update `aggregate.py`/`plot.py`
   only as needed to tolerate the new fields (they read the warmest pass today; do not
   regress that).

## Anti-regression / invariants

- **Never intrude / never crash the host script.** New capture is read-only, runs in the
  existing daemon threads, and every probe is wrapped so failure yields a `capture_state`
  entry, never an exception into user code. A test asserts a probe raising internally does
  not propagate.
- **Zero new runtime dependency.** No import of any non-stdlib module in the capture path.
- **Additive manifest schema.** Existing manifest keys keep their names/shapes; only new
  keys are added. A test pins that the pre-existing keys are unchanged.
- **Watcher stays light.** The added per-interval reads are single small `/proc` reads;
  a test/benchmark confirms no material change to the 15s loop cost. The watcher's
  self-abort-after-3-failures and bounded-join behavior is preserved.
- **Benchmark backward-compat.** `aggregate.py`/`plot.py` must still work on `/2` JSONs
  and on `/3`; the warmest-pass top-level `scenarios` mirror is preserved.
- **Cross-platform honesty.** Non-Linux platforms report "not available" for fields they
  cannot cheaply obtain, rather than guessing or erroring.

## Required tests / validation

- Unit: `get_filesystem` parses a synthetic `/proc/mounts`/`mountinfo` and classifies
  nfs/lustre/local correctly; longest-prefix mount match; `is_network` correct; failure →
  `capture_state`.
- **Hang-safety (HIGH):** simulate a target path whose `os.statvfs`/`df` would block
  (monkeypatch them to raise/sleep) and assert `get_filesystem` still classifies via
  `/proc/mounts` parsing WITHOUT invoking the blocking call, and returns within budget.
- **Finalizer budget:** assert fstype capture does not push the `pubrun-hw` thread past the
  2.0s finalizer wait (`tracker.py:446-447`) on a normal mount; on a pathological mount the
  manifest records `pending`/`failed`, never hangs.
- Unit: memory/load parsing from synthetic `/proc/meminfo`/`/proc/loadavg`; iowait delta.
- Safety: a probe patched to raise does NOT propagate into a run (host-script safety).
- Manifest: new keys present when capture on; absent/`capture_state` when off or failing;
  pre-existing keys unchanged (anti-regression pin).
- Benchmark: harness produces `/3` with per-pass dynamic block + filesystem + Slurm
  context; `aggregate.py` still summarizes `/2` and `/3`.
- Full suite green (baseline 690 passed; known SIGPIPE flake excepted).

## Spec / documentation sync

`docs/manifest.md` (new fields), `docs/configuration.md` (if any new config key),
`benchmarks/README.md` + `docs/performance.md` (new fields, per-pass env, schema/3),
`CHANGELOG.md`. Run `/assess documentation` after implementation.

## Open questions — ANSWERED by maintainer 2026-07-06

1. **System free-RAM / load / fstype sampling → ON BY DEFAULT, but behind a dedicated
   config key.** Add a NEW `[capture.resources]` sub-key (e.g. `system_metrics = true`,
   default `true`) so it is independently controllable and documented, but it only
   actually samples when the resource watcher is running (`depth != "off"`). So: default
   on, cheap, gives the I/O/NFS signal for free on normal runs, yet a user can turn it off
   explicitly. (Sampled in the existing 15s loop; single small `/proc` reads.)
2. **Linux `iowait` → INCLUDE BY DEFAULT on Linux**, clearly "not available" on
   macOS/Windows. Sampled from `/proc/stat` deltas in the watcher loop. Gate under the same
   `system_metrics` key so turning that off also stops iowait.
3. **Disk throughput probe → BENCHMARK HARNESS ONLY, never on normal runs.** The harness
   may do a timed small-temp-file write (it is a benchmark; real I/O is expected). Normal
   pubrun runs must NOT (preserves "never intrude"); they rely on fstype + iowait instead.

## Cross-IPD coordination (added 2026-07-06)

- **IPD-B needs two additive manifest flags** the maintainer approved:
  `capture.subprocesses_enabled` (from `self._spying_subprocesses`, `tracker.py:316`) and
  `capture.file_provenance_available`. Since THIS IPD already edits the manifest-assembly
  dict (`tracker.py:576-632`), add those two booleans HERE too, so `pubrun inspect` can be
  definitive rather than ambiguous. Keep additive (no existing key renamed).
- **The new `system_metrics` key** must be documented in `docs/configuration.md` and its
  default reflected in `src/pubrun/resources/default.toml` (`sample_interval_seconds = 15`
  lives at `default.toml:278`; add the new key in the same `[capture.resources]` block).

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-06)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verdict: **APPROVE WITH
REVISIONS APPLIED**. Claims re-verified against source: async watcher/threads
(`resources.py:168-209`, `tracker.py:291-294`), zero `open()`/fs/load capture today,
`[capture.resources]` block + `sample_interval_seconds` in `default.toml`,
`config.resolved.json` written by `writer.py:69,100`. Maintainer answers folded in
(system-metrics config key default-on; iowait Linux-default; disk probe harness-only).
Added cross-IPD ownership of the two additive manifest flags (`subprocesses_enabled`,
`file_provenance_available`) here since this IPD already edits manifest assembly.
Sequence: A before B and C.

**Stricter re-pass (2026-07-06), additional findings fixed:**
- **A-R1 (HIGH):** the fstype probe could BLOCK on a sick NFS/Lustre mount (via
  `os.statvfs`/`df`/`stat`) — the exact failure it is meant to detect — and blow the 2.0s
  finalizer budget (`tracker.py:446-447`) or wedge a subprocess. Mandated pure
  `/proc/mounts`+`mountinfo` parsing (no path-touching calls) + a hang-safety test.
  Verified the finalizer-wait timeout via `tracker.py:446-447`.
- **A-R2 (MEDIUM):** `/proc/stat` iowait is node-wide + kernel-documented-unreliable, not
  run-scoped; relabeled `system_iowait_pct` (indicative only) to avoid over-reading.
- Verified `import pubrun` does NOT import the `report` package (empty), confirming IPD-B's
  CLI-only isolation holds; and the `pubrun-hw` thread + 2.0s wait semantics.

## Execution record (2026-07-06)

Executed by opencode after human approval. Both parts landed.

**Part 1 — run-time capture enrichment:**
- `src/pubrun/capture/filesystem.py` (NEW): `get_filesystem(config, paths)` classifies
  fstype/mount/is_network by PARSING `/proc/mounts` (Linux) / `mount` table (macOS) with
  a hard subprocess timeout — never `statvfs`/`df`/`stat` on the target, so it cannot hang
  on a sick NFS/Lustre mount (the A-R1 HIGH finding). Longest-prefix match; octal-escape
  decoding; per-path + top-level `capture_state`; never raises.
- `src/pubrun/capture/system_metrics.py` (NEW): `get_system_memory` (`/proc/meminfo`),
  `get_load_average` (`os.getloadavg`), `read_proc_stat_cpu_times` + `iowait_pct_between`
  (`/proc/stat` deltas). All None-on-failure, stdlib-only, non-blocking.
- `ResourceWatcher` (`resources.py`): new `system_metrics` flag; captures a baseline at
  construction and samples memory/load/node-iowait in the existing 15s loop (worst-case +
  last); emits `system_memory`/`load_average`/`system_iowait_pct` in `to_manifest_dict`.
  Fully exception-safe — a system-metrics failure never disturbs RSS/CPU or the run.
- `tracker.py`: filesystem capture runs in the existing `pubrun-hw` startup thread (well
  within the 2.0s finalizer budget); manifest gains `filesystem`, plus additive
  `capture.subprocesses_enabled` (from `_spying_subprocesses`) and
  `capture.file_provenance_available` (for IPD-B). Watcher wired to the new config key.
- `resources/default.toml`: new `[capture.resources].system_metrics = true`.
- **iowait honesty (A-R2):** surfaced as `system_iowait_pct` and documented as node-wide /
  indicative only in the manifest docs, config docs, and module docstring.

**Part 2 — benchmark harness (`benchmarks/harness.py`):**
- Schema `pubrun-benchmark/2` → `/3`. `machine.filesystem` (tmpdir/results/pubrun-install
  fstype) and `machine.slurm` (allocation context) added; `pass_results[i].pass_env`
  records RAM/load/iowait at the START OF EACH PASS. Top-level `scenarios` mirror preserved;
  `aggregate.py`/`plot.py` read `/3` and still read `/2` (no schema assertion in either).

**Tests (`tests/test_env_capture.py`, 15 new, all green):** network-fstype detection,
longest-prefix match, octal unescape, local classification, unsupported-platform,
**hang-safety (statvfs banned → still classifies via /proc/mounts)**, never-raises;
meminfo/loadavg parsing, iowait math, meminfo-failure-returns-None; manifest has
`filesystem` + both capture flags + preserved existing keys + system-metrics section.
Full suite: **710 passed**, 2 skipped; the lone failure is the known pre-existing SIGPIPE
flake (`tests/test_status.py::...test_real_sigpipe_via_pipe`, passes in isolation).

**Docs:** `docs/manifest.md` (`filesystem`, `resources.system_*`, `capture` flags),
`docs/configuration.md` (`system_metrics` key), `benchmarks/README.md` (schema/3),
`CHANGELOG.md` `[Unreleased] → Added`. Field names verified against real manifest output.

**Deferred (unchanged from plan):** disk-throughput probe is harness-only and NOT yet added
to the harness workloads (the harness already exercises real file I/O via `file_read.py`);
can be a follow-up if a dedicated throughput number is wanted.
