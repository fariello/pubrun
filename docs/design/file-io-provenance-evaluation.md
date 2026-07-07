# File-I/O provenance — Phase 0 evaluation

- Date: 2026-07-06
- Status: **Phase 0 (evaluation only — NO code).** This document is the deliverable of
  Gate 1 of IPD `20260706-open-interception-evaluation.md`. It analyzes options and makes a
  recommendation. **No implementation is authorized by this document**; a specific Phase-1
  mechanism requires explicit maintainer sign-off (Gate 2).
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Question

The maintainer wants to know *which files a run read and wrote* (paths, and optionally
metadata/hashes) for provenance, reproducibility, performance, and debugging — and,
separately, *whether a run was I/O-heavy / on a slow network filesystem*. The tempting
mechanism is intercepting `open()` globally, but the maintainer's standing position is
"nope" to patching `builtins.open`. This evaluates the real options against pubrun's hard
principles: **never intrude on / slow / break / crash the host script; zero runtime deps;
KISS; honest docs.**

## Verified current state (2026-07-06)

- pubrun does **NOT** patch `builtins.open`. It ships an **opt-in** wrapper `pubrun.open()`
  (`src/pubrun/core.py:731`) returning a `ProvenanceFileProxy` (`core.py:581-728`) that
  hashes reads/writes and records `{path, size_bytes, sha256, accessed/modified_at_utc}`
  into `manifest["data_files"].{inputs,outputs}` when a run is active.
- `sys.addaudithook` exists and the `open` audit event fires on `open()`/`os.open()` from
  Python 3.8+ (`pyproject.toml` `requires-python = ">=3.8"`, confirmed on 3.14). **There is
  no `sys.removeaudithook`** — an audit hook is installed for the process lifetime.
- `/proc/self/io` exists on Linux and cheaply reports `rchar`/`wchar`/`read_bytes`/
  `write_bytes`/`syscr`/`syscw` (verified) — a coarse, zero-interception I/O-volume signal.
- pubrun already runs light background daemon threads (resource watcher, 15s;
  `pubrun-hw`), and `pause()` mutes capture via a **thread-local depth counter**
  (`_spy_local` in `capture/subprocesses.py:10-34`) — the established muting pattern.

## The two questions are separable

1. **"Was this run I/O-heavy / on a slow network FS?"** — a *coarse, aggregate* question.
   Already largely answered by IPD-A (fstype detection + node iowait). `/proc/self/io`
   read/write byte totals would complete it, at **zero interception cost**.
2. **"Exactly which files, with what content?"** — a *precise, per-file* question. This is
   where `open()` interception is tempting and risky.

Treating them separately means the high-value, low-risk coarse signal need not wait on (or
be entangled with) the risky precise-provenance work.

## The graded provenance-detail ladder (per-file question)

The maintainer framed per-file provenance as escalating levels, cheapest/safest first:

| Level | Captures | Reads file contents? | Relative cost |
|---|---|---|---|
| **L1** | path as given to `open()` | no | trivial |
| **L2** | realpath (symlinks resolved) | no (one `realpath`/`readlink`) | very low |
| **L3** | L2 + `stat` (ctime/mtime/size) | no (one `stat`) | low |
| **L4** | L3 + content **hash** | **yes — every byte** | high (I/O-bound) |

L1–L3 are metadata-only and cheap. **L4 is the expensive, intrusive one** (it must read the
whole file; on a large input over NFS this can dominate runtime and *itself* generate the
I/O the user is trying to measure). L4 needs size caps, path filters, and possibly sampling.
"Hash verification" (compare an input's hash to a prior run to detect changed inputs) is a
useful L4 *consumer*, evaluated as a follow-on, not a capture level.

## Mechanism analysis

### A. Harden the opt-in `pubrun.open()` (no global patch) — LOWEST RISK

**What it is.** Keep interception opt-in: the user writes `pubrun.open(...)` (or
`from pubrun import open`). Extend the existing proxy to support the full ladder (L1–L4,
config-selectable) and fix its conformance gaps.

**Risk.** Minimal — it is not global, touches only files the user explicitly routes through
it, and cannot affect libraries or the host script's own `open()` calls. Cannot break numpy/
h5py/torch because they call the real builtin.

**Correctness gaps to fix (from reading `core.py:581-728`):**
- No `readinto`/`read1`/`peek`/`seek`/`tell` interception — they fall through `__getattr__`
  to the raw object, so bytes read via `readinto` (used by `io.BufferedReader`, numpy, etc.)
  are **not** counted/hashed. For read-mode hashing to be correct, either intercept all read
  paths or (better) compute the read-hash from the file on disk at close (as write-mode
  already does) rather than incrementally.
- Text-mode hashing re-encodes with `errors="ignore"` (`core.py:599`), so the recorded
  sha256 is **not** the on-disk file's hash for text files (line-ending/encoding drift). If
  the promise is "hash of the file", always hash the on-disk bytes at close; if it is "hash
  of the logical content read", document that explicitly. Current behavior is ambiguous —
  a hardening honesty fix.
- `fileno()`, `seekable()`, etc. work via `__getattr__` but the proxy is not registered as
  an `io.IOBase` subclass, so some C-level `isinstance(f, io.IOBase)` checks fail. Usually
  fine; document the limitation.

**Ladder feasibility.** All of L1–L4 are straightforward here; L4 already exists.

### B. `sys.addaudithook` on the `open` audit event — MEDIUM RISK, AUTOMATIC

**What it is.** Install ONE process-lifetime audit hook that fires on every `open`/`os.open`
(including inside libraries), records path (L1–L3 easily; L4 would require separately opening
+ hashing the file, which the hook cannot do inline safely). Automatic — the user need not
change their code.

**Key constraints (verified):**
- **Not removable** (`no sys.removeaudithook`). So "opt-in / muted by `pause()`" MUST be
  implemented by **gating inside the hook** (check a config flag + the thread-local pause
  depth per event), never by add/remove. If enabled, the hook is installed once at run start
  and self-suppresses when disabled/paused. This also means: if the feature is OFF, we must
  **not install the hook at all** (default OFF ⇒ zero cost, zero hook).
- **Per-`open()` overhead on the host's hot path.** The hook fires for *every* file open in
  the process, including the thousands libraries do. Even a fast hook (flag check + append)
  adds cost to every open; a slow one (realpath/stat/hash inline) would be unacceptable. L4
  in-hook is a non-starter (cannot read the file inside the audit callback without recursion
  and huge cost). L1 is cheap; L2/L3 add a syscall per open; L4 must be deferred/out-of-band.
- **Volume.** Auditing every open in a real run can produce thousands of records
  (site-packages imports, matplotlib font scans, etc.). Needs aggressive **path filters**
  (exclude the stdlib/site-packages/`/proc`/`/sys`/pubrun's own run dir) and a cap, or it
  becomes noise + a data-volume problem.
- **Never raise.** An exception in an audit hook can propagate oddly; the hook body must be
  wrapped to swallow everything.
- Interaction: must reuse the `_spy_local` pause pattern; must not double-count files also
  seen by `pubrun.open()`.

**Ladder feasibility.** L1 good; L2/L3 feasible with per-open syscalls (watch overhead); L4
**not** feasible in-hook.

### C. `/proc/<pid>/io` sampling in the existing watcher — LOWEST RISK, COARSE ONLY

**What it is.** In the existing 15s resource-watcher loop, read `/proc/self/io` and record
read/write byte totals over the run. **Zero interception**, no `open()` involvement, one
cheap file read per sample.

**Risk.** Negligible (same class as IPD-A's system-metrics). Linux-only (macOS/Windows: "not
available", honestly documented).

**What it answers.** Question 1 (I/O-heavy? how many bytes read/written?) — completing the
NFS/contention story with IPD-A. **It does NOT answer question 2** (which files) at all.

### D. `strace`/`ptrace` — REJECTED

Out-of-process syscall tracing would capture opens without patching, but it is heavy,
Linux-only, needs `ptrace` permissions (often disabled on HPC/hardened kernels), and would
massively slow the traced process. Violates "never slow the host script". Not pursued.

### E. Global `builtins.open` monkeypatch — REJECTED (the maintainer's "nope" stands)

Replacing `builtins.open` is the highest-blast-radius option: it sits on the hottest path,
risks breaking buffering/encoding/`PathLike`/fd-inheritance/subclass expectations across
every library, and C-extensions that captured the original `open` reference won't even see
it (so it is both dangerous AND incomplete). The audit hook (B) achieves the same
"automatic" goal with strictly lower blast radius (it observes, does not replace). **There is
no reason to monkeypatch `open` when the audit hook exists.** Recommend permanently ruling
this out.

## Per-OS capability table (honest, not all-or-nothing)

| Capability | Linux | macOS | Windows |
|---|---|---|---|
| `pubrun.open()` L1–L4 (opt-in, A) | full | full | full |
| Audit-hook open events (B) | full | full | full (3.8+) |
| `/proc/<pid>/io` byte totals (C) | full | **not available** (no `/proc/self/io`; `rusage` is coarser) | not available |
| realpath / stat (L2/L3) | full | full | full |

## Recommendation

Ordered, and explicitly **separating the two questions**:

1. **DO (low risk, high value) — coarse I/O totals via `/proc/self/io` (Mechanism C),** as a
   small extension of IPD-A's system-metrics in the existing watcher. This finishes the
   "was this run I/O-heavy / on NFS" story that motivated all of this, at ~zero risk and zero
   interception, and feeds `pubrun inspect`. Linux-only, honestly degraded elsewhere. *This
   is the single most cost-effective outcome and needs no `open()` work.* (It is arguably an
   IPD-A follow-up more than an `open()` feature.)

2. **DO (low risk) — harden the opt-in `pubrun.open()` (Mechanism A)** and expose the graded
   `level` there: fix the read-hash correctness (hash on-disk bytes at close), document the
   text-vs-bytes hashing semantics honestly, add path/size filters and the L1–L4 `level`
   selector. This gives users *precise* per-file provenance with **zero global risk** —
   they opt in per file. Recommend documenting `pubrun.open` / `from pubrun import open` as
   the supported precise-provenance API.

3. **EVALUATE-BUT-DEFER (medium risk) — the `sys.addaudithook` path (Mechanism B)** for
   *automatic* (no code-change) capture. It is the only "capture without the user calling
   `pubrun.open`" option that respects the principles, BUT it carries real per-open overhead
   and volume concerns and the not-removable constraint. Recommend it be its own Gate-2
   decision *after* (1) and (2) ship and only if the automatic-capture need is demonstrated;
   if built, strictly: default OFF (hook not installed unless enabled), L1/L2/L3 only (no
   in-hook L4), aggressive path filters, per-event gating via the `_spy_local` pause counter,
   hard never-raise wrapper, and a benchmark gate on per-open overhead.

4. **REJECT permanently — global `builtins.open` monkeypatch (E)** and **`strace`/`ptrace`
   (D).** The audit hook dominates E on every axis; D violates "never slow the host".

### Proposed config knob (design only — not implemented)

```toml
[capture.file_io]
# none | name | realpath | stat | hash    (default: none)
level = "none"
# "explicit"  -> only files opened via pubrun.open()  (Mechanism A)
# "auto"      -> also capture via the audit hook       (Mechanism B; if/when built)
mode = "explicit"
# path globs to exclude from auto capture (site-packages, /proc, the run dir, ...)
exclude = ["*/site-packages/*", "/proc/*", "/sys/*"]
max_hash_bytes = 268435456   # skip hashing files larger than this (L4 guard)
```

Default `level = "none"` ⇒ **no behavior change, no hook installed** — preserving "default
OFF" and zero footprint. `mode = "explicit"` keeps everything opt-in-per-file (Mechanism A);
`"auto"` is the audit-hook path, gated behind the deferred Gate-2 decision.

## Gate 2 (what needs maintainer sign-off before any code)

- **Approve (1)** `/proc/self/io` coarse totals — likely a quick, low-risk follow-up.
- **Approve (2)** hardening `pubrun.open()` + the `level` selector — low risk.
- **Decide (3)** whether to pursue the audit-hook automatic path at all, and if so accept the
  constraints above. Default recommendation: **defer** until (1)+(2) are in use.
- **(4)** is a recommendation to permanently close the door on global `open()` patching.

No code is written until the maintainer picks from the above.
