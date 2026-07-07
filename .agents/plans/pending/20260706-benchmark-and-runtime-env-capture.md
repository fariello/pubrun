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
- Status: PENDING — plan-review, then execution on human approval. NOT auto-executed.
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
   `is_network` boolean. Linux: parse `/proc/mounts` (longest-prefix match) or
   `os.statvfs`. macOS: `df -T`/`mount` best-effort. Windows: drive type best-effort.
   `capture_state` on failure. Called once from the `pubrun-hw` startup thread.
2. **Extend memory/load capture:** add `MemAvailable`/`MemFree`/`Cached` (Linux
   `/proc/meminfo`) and `os.getloadavg()` — captured once at start (startup thread) AND
   sampled in the `ResourceWatcher` loop (`resources.py`) so the manifest gets a small
   time series (start + peak/last, matching the existing RSS/CPU peak/end shape). Keep it
   cheap: these are single small reads.
3. **Optional Linux iowait** from `/proc/stat` deltas in the watcher loop (Linux only;
   omitted elsewhere with a clear "not available"). Gate behind the resource config so it
   is off when resource capture is off.
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

- Unit: `get_filesystem` parses a synthetic `/proc/mounts` and classifies nfs/lustre/local
  correctly; longest-prefix mount match; `is_network` correct; failure → `capture_state`.
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

## Open questions (maintainer)

1. For run-time enrichment, should system free-RAM/load sampling be **on whenever the
   resource watcher is on** (default `depth="standard"`), or behind a separate opt-in key?
   (Recommend: on with the watcher — it is cheap and it is the whole point.)
2. Linux `iowait`: include by default (Linux-only, clearly "not available" elsewhere), or
   opt-in? (Recommend: include; it is the single most useful I/O-pressure signal.)
3. Should we also capture a coarse **disk throughput probe** (e.g. timed write of a small
   temp file) at run start? It is more intrusive (does real I/O) — recommend NO for normal
   runs, YES only inside the benchmark harness.

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.
