# IPD-E: (EVALUATION-FIRST) opt-in file-I/O provenance — harden `pubrun.open()`, evaluate global `open()` interception

- Date: 2026-07-06
- Concern: provenance / reproducibility / performance / debugging — knowing which files a
  run opens, reads, and writes (paths, hashes, sizes, mount types) is enormously valuable.
  But GLOBAL interception of `builtins.open` is the single riskiest thing pubrun could do.
- Scope: EVALUATION FIRST. This IPD's first deliverable (Phase 0) is a written evaluation +
  a recommendation and **touches NO code, tests, or config** — a research/writing
  deliverable only. Only after explicit maintainer approval (Gate 2) does any implementation
  proceed, and even then strictly OPT-IN; Phase-1 code would touch `src/pubrun/core.py` (the
  existing `pubrun.open` wrapper) and potentially a new opt-in patch module. Nothing in
  Phase 0 modifies the codebase.
- Status: EXECUTED (2026-07-06). Phase 0 (evaluation) done + Gate-2 decisions taken +
  Phase-1 items **1 (coarse /proc/self/io) and 2 (harden `pubrun.open()` + graded `level`)
  IMPLEMENTED, tested, documented**. Item 3 (audit-hook automatic path) DEFERRED to a future
  separate proposal; item 4 (global `open()` patch) REJECTED permanently. 747 passed / 2
  skipped (only the known SIGPIPE flake fails, passes in isolation). See the execution
  record at the end. The evaluation lives at `docs/design/file-io-provenance-evaluation.md`.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

Verified (2026-07-06): pubrun does **NOT** monkeypatch `builtins.open` (confirmed — no
assignment to `builtins.open` anywhere). It already ships an **opt-in** `pubrun.open()`
wrapper (`core.py:731-745`) returning a `ProvenanceFileProxy` (`core.py:581-728`) that
hashes reads/writes when a run is active — but only if the user explicitly calls
`pubrun.open()` instead of `open()`.

The maintainer's insight: if pubrun knew every file a process opened/read/wrote, it could
massively improve provenance (exact input/output files + hashes), reproducibility (detect
changed inputs between runs), performance (I/O volume, reads over NFS), and debugging.
Global `open()` interception would capture this automatically without the user changing
their code. The maintainer also (correctly) recalls deciding "nope" to patching `open()`
globally, and wants this evaluated very carefully before any move.

## Project conventions discovered (Step 0)

- Principles (hard constraints here): **never intrude on / slow / break / crash the host
  script**; zero runtime deps; KISS; honest docs. `open()` is on the host script's hottest
  path — global interception directly stresses the "never intrude/slow" principle.
- Existing global patches (for reference / risk baseline): `subprocess.Popen.__init__/.wait`,
  `os.system`, `sys.stdout/stderr` tee, `faulthandler`, signals, `sys.excepthook`
  (`tracker.py:312-350`, `console.py:226-233`, `subprocesses.py:80-82`, `signals.py`).
  Notably, pubrun deliberately does NOT patch `builtins.print` either — it tees streams.
- `pause()` (executed IPD `20260705-scoped-pause-resume.md`) exists and would need to also
  mute any open() capture if that is ever added.
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Phase 0 — EVALUATION (the only thing done without further approval)

Produce a written evaluation (a doc under `docs/` or an appendix to this IPD) covering:

1. **Risk analysis of global `builtins.open` interception:**
   - Performance: `open()` is called constantly; even a thin wrapper adds per-call cost.
     Quantify with a benchmark scenario (ties to IPD-A/harness) — overhead per open, and
     under a read-heavy workload.
   - Correctness/compatibility: `open` is used by countless libraries (numpy, h5py, torch,
     loggers). Risks: breaking `__enter__/__exit__`, buffering, binary vs text, `os.PathLike`,
     fd inheritance, `encoding`/`errors`, subclass expectations, C-extensions that hold the
     original `open` reference (won't see the patch anyway), reentrancy, thread safety.
   - Volume: a real run may open thousands of files; capturing all is a data-volume and
     hashing-cost problem. Need filtering (paths, size caps, hash sampling) — design that.
   - Interaction with the existing capture (subprocess spy, tee), `pause()`, and the
     resource watcher.
2. **Alternatives that get most of the value at far lower risk** (evaluate and compare):
   - Keep/harden the OPT-IN `pubrun.open()` only (no global patch). Lowest risk.
   - Linux `strace`/`ptrace`-based passive observation of file opens (out-of-process; no
     host-path patching) — heavy, Linux-only, permissions.
   - `/proc/<pid>/fd` and `/proc/<pid>/io` sampling in the EXISTING watcher thread — coarse
     (open fds, bytes read/written totals) but ZERO host-path interception and cheap. This
     may deliver the "was this run I/O-heavy / on NFS" signal (ties to IPD-A/B) without ever
     touching `open()`.
   - Audit hooks: `sys.addaudithook` with the `open`/`os.open` audit events (3.8+) — capture
     open events WITHOUT replacing `open`. Lower blast radius than monkeypatching; evaluate
     its overhead and completeness.
3. **Graded provenance-detail ladder (maintainer's framing, 2026-07-06).** Evaluate file
   provenance NOT as all-or-nothing but as escalating levels, cheapest/safest first, so the
   cost/detail tradeoff is explicit and (once implemented) user-selectable:
   - **L1 — name only:** the path as given to `open()`. Cheapest.
   - **L2 — realpath:** canonical/resolved path (symlinks resolved); OS-appropriate
     equivalent on non-POSIX.
   - **L3 — +stat metadata:** path (L1/L2) plus `ctime`, `mtime`, `size` (via `stat` or the
     OS equivalent). **Metadata only — does NOT read file contents**, so still cheap and
     non-intrusive.
   - **L4 — +content hashing:** everything above plus a content hash. This is the expensive,
     most-intrusive level (must read every byte); evaluate hash cost, size caps, and
     sampling. Evaluate hash *verification* (compare against a prior run) as a sub-capability.
   The evaluation must recommend, per mechanism (opt-in `pubrun.open()` / audit hook / /proc),
   which levels are feasible and worth it, and the per-level overhead.
4. **Recommendation:** which path (opt-in wrapper hardening / audit hook / /proc sampling /
   full global patch / do-nothing) AND up to which ladder level, with justification against
   the principles. Also recommend the **config knob** shape (maintainer wants the level to be
   user-selectable): e.g. `[capture.file_io] level = none|name|realpath|stat|hash`, default
   `none` (off). Users on fast local disk can raise it; HPC/NFS users stay low or off.
5. **Cross-platform posture (maintainer, 2026-07-06):** pursue each level as far as each OS
   cheaply allows; this is NOT all-or-nothing across platforms. Where an OS cannot provide a
   level cheaply, degrade and **document the shortfall honestly** (per-OS capability table in
   the evaluation), rather than refusing the feature everywhere or pretending parity.

## Phase 1 — implementation (ONLY on approval of the Phase-0 recommendation)

Depending on the recommendation, the likely candidates (in increasing risk):

- **Harden `pubrun.open()`** (`core.py:731`): ensure the proxy is fully file-like
  (context manager, iteration, `fileno`, `readinto`, text/binary, encoding), records path +
  mode + bytes + optional hash + fstype (reuse IPD-A filesystem helper), with size caps and
  path filters; document it as the recommended explicit-provenance API. Provide `pubrun.open`
  as a drop-in so users can `from pubrun import open` at file top by choice.
- **(If approved) `sys.addaudithook`-based open capture**, strictly opt-in via config
  (default OFF), muted by `pause()`, with path/size filters, and a hard "never raise into
  the host" guarantee. NOT a `builtins.open` replacement. **Verified available across the
  whole supported range:** `pyproject.toml` sets `requires-python = ">=3.8"`, and
  `sys.addaudithook` + the `open` audit event both exist since 3.8 (confirmed working on
  the 3.14 dev interpreter). Caveat to evaluate: audit hooks CANNOT be removed once added
  (process-lifetime), so the "opt-in, muted by `pause()`" design must gate INSIDE the hook,
  not by adding/removing it — the hook is installed once and checks config/pause state per
  event. This is a real design constraint for Phase 0 to address.
- **Global `builtins.open` monkeypatch is the last resort** and only if the evaluation shows
  it is safe AND opt-in AND gated — the maintainer's default remains "nope" unless the
  evaluation overturns it.

## Anti-regression / invariants (for any implementation phase)

- **Default OFF.** Nothing here changes default behavior; `import pubrun` must not start
  intercepting file I/O unless explicitly enabled.
- **Never intrude/slow/break/crash the host script.** Any capture path must be wrapped to
  never raise into user code, must be measurably cheap (benchmark-gated), and must be
  mutable/mutable-off via config and muted by `pause()`.
- **Opt-in and reversible.** Clean install/uninstall like the other patches; identity-guarded
  restore.
- **Zero new runtime dependency.**
- Preserve the existing `pubrun.open()` behavior for current users (only extend it).

## Required tests / validation (implementation phase)

- `pubrun.open()` proxy passes a file-like conformance suite (context manager, iteration,
  binary/text, encoding, `fileno`, large files, exceptions).
- If audit-hook path: opens are captured, `pause()` mutes them, disabling config stops them,
  an internal error never propagates to the caller.
- Overhead benchmark within the harness shows acceptable per-open cost; read-heavy workload
  within budget.
- Full suite green.

## Spec / documentation sync

The Phase-0 evaluation doc; then (if implemented) `docs/api.md` (`pubrun.open`),
`docs/configuration.md` (any opt-in key), `docs/manifest.md` (file-provenance fields),
`CHANGELOG.md`. Run `/assess documentation`.

## Open questions — ANSWERED by maintainer 2026-07-06 (Phase 0 will still detail them)

1. Primary goal → **both (a) precise per-file provenance and (b) coarse I/O/NFS signal**,
   and the evaluation must assess whether (b) is fully satisfied by cheap `/proc/<pid>/io`
   sampling (IPD-A territory) WITHOUT any `open()` work — which could make the risky global
   interception unnecessary. (a) is to be evaluated via the **graded L1→L4 ladder** above.
2. Cross-platform → **as cross-platform as possible; NOT all-or-nothing.** Optimize where
   each OS allows, document per-OS shortfalls honestly.
3. Config knob → **YES, the ladder level is user-selectable** (`[capture.file_io] level`,
   default `none`); the evaluation designs the exact knob.
4. (Still open, informed by Phase 0) After reading the evaluation, which mechanism (opt-in
   `pubrun.open()` hardening / audit hook / `/proc` sampling / global patch / do-nothing)
   and up to which ladder level to actually build — decided at Gate 2.

## Approval and execution gate

Two gates. Gate 1: approve doing the Phase-0 EVALUATION (research/writing only, no code).
Gate 2: after reading the evaluation, explicitly approve a specific Phase-1 mechanism (or
decline). NOT auto-executed at either gate. Recommended: run `plan-review` on this IPD, and
re-review after the Phase-0 evaluation before any implementation.

## Plan-review record (2026-07-06)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verdict: **APPROVE WITH
REVISIONS APPLIED**. Verified: `builtins.open` is NOT patched today (only the opt-in
`pubrun.open()` wrapper, `core.py:731`); `requires-python = ">=3.8"`; `sys.addaudithook` +
`open` audit event confirmed working. Maintainer answers folded in: graded L1→L4 ladder
(name → realpath → +stat → +hash), user-selectable `[capture.file_io] level` (default
`none`), cross-platform-as-feasible with honest per-OS shortfall documentation, and
evaluate both precise-provenance AND coarse `/proc` I/O signal (the latter may satisfy the
NFS concern with no `open()` work). **New design constraint surfaced during review:** audit
hooks cannot be removed once added (process-lifetime), so an "opt-in / muted by `pause()`"
design must gate INSIDE the hook per-event, not by add/remove — recorded for Phase 0. This
remains EVALUATION-FIRST with two approval gates; the review does not authorize any code.

**Stricter re-pass (2026-07-06):** tightened the Scope line so Phase 0 explicitly touches no
code/tests/config (removes any implication of code changes before Gate 2). No other findings
— the evaluation-first structure correctly contains the highest-risk item of the five.

## Phase 0 outcome (2026-07-06) — EVALUATION COMPLETE, no code written

Deliverable: **`docs/design/file-io-provenance-evaluation.md`** (evidence-grounded; read
the actual `ProvenanceFileProxy` at `core.py:581-728`, verified `/proc/self/io`, verified
`sys.addaudithook` exists with NO `sys.removeaudithook`, and the `_spy_local` pause pattern).

Key findings:
- The two goals are **separable**: (1) coarse "was this I/O-heavy / on NFS" vs (2) precise
  "which files". Keeping them separate lets the high-value low-risk part proceed alone.
- **Global `builtins.open` monkeypatch is dominated by the audit hook on every axis** (the
  hook observes rather than replaces, so lower blast radius AND it is not defeated by
  C-extensions holding the original `open`). Recommend permanently rejecting the global
  patch. `strace`/`ptrace` rejected (slow, permissioned, Linux-only).
- **Audit-hook constraint confirmed:** not removable → must be installed only when enabled
  and gated per-event via the thread-local pause counter; L4 (hashing) is NOT feasible
  in-hook; needs aggressive path filters + never-raise wrapper + a per-open overhead budget.
- Current `pubrun.open()` proxy has real correctness gaps to fix if hardened: `readinto`/
  buffered reads bypass the incremental hash; text-mode re-encode with `errors="ignore"`
  makes the recorded hash NOT the on-disk hash (honesty issue). Fix = hash on-disk bytes at
  close + document semantics.

Recommendation (ordered), each gated on maintainer approval (Gate 2):
1. **DO** coarse `/proc/self/io` read/write byte totals in the existing watcher (≈IPD-A
   follow-up; ~zero risk; finishes the NFS/contention story; feeds `pubrun inspect`).
2. **DO** harden opt-in `pubrun.open()` + a graded `level = none|name|realpath|stat|hash`
   selector (zero global risk; per-file opt-in).
3. **DEFER** the `sys.addaudithook` automatic path until (1)+(2) are in use and the
   automatic-capture need is demonstrated; if built, default OFF (no hook installed),
   L1–L3 only, path filters, pause-gated, never-raise, benchmark-gated.
4. **REJECT permanently** global `open()` patching and `strace`/`ptrace`.

Proposed config knob (design only): `[capture.file_io].level` (default `none`) +
`mode = explicit|auto` + `exclude`/`max_hash_bytes`. Default `none` ⇒ no behavior change,
no hook installed (preserves default-OFF / zero-footprint).

**Gate 2 asks (maintainer):** approve (1), approve (2), decide on (3) [recommend defer],
confirm (4). No code until then. Recommend re-running `plan-review` on whichever Phase-1
mechanism is chosen before it is built.

## Gate 2 decisions (maintainer, 2026-07-06) — Phase 1 authorized (items 1 + 2)

1. **APPROVED** — coarse `/proc/self/io` read/write byte totals in the resource watcher.
2. **APPROVED** — harden `pubrun.open()` correctness + add a graded `level` knob.
3. **DEFERRED** — the `sys.addaudithook` automatic path (NOT built now). (Clarified for the
   maintainer: the audit hook is OBSERVE-ONLY — it registers a listener for the interpreter's
   built-in `"open"` audit event (PEP 578, 3.8+); it does NOT replace `open`, cannot corrupt
   data or break libraries, and only learns the path/mode — so it can do L1/L2/L3 but not L4
   inline. It is process-lifetime (no `sys.removeaudithook`). Deferred until items 1+2 are in
   use.)
4. **REJECTED PERMANENTLY** — global `builtins.open` monkeypatch and `strace`/`ptrace`.

### Ladder REORDERED for honest cost (maintainer analysis, 2026-07-06)

Cost is NOT monotonic under the original name→realpath→stat→hash order: on NFS, `realpath`
does a multi-component `lstat` walk (each an uncached `GETATTR` round-trip) and can cost MORE
than a single `stat`. Conversely `fstat()` on the already-open fd is ~free even on NFS
(the file's attributes are already fetched), and cache-hot on local FS. So:

**Final ladder: `none | name | stat | realpath | hash`** (progressive):
- `name` — path as given to `pubrun.open()`.
- `stat` — `fstat(fileno)` on the open fd (size/mtime/ctime) + `os.path.abspath` (pure
  string, no syscall). Cheap everywhere incl. NFS. **DEFAULT.**
- `realpath` — adds symlink resolution (`os.path.realpath`); the NFS-costlier tier,
  documented as such.
- `hash` — adds sha256 (reads all bytes); opt-in / "paranoid" only.

**`level` default = `stat`.** This is a BEHAVIOR CHANGE: `pubrun.open()` currently records
sha256 (L4) for every wrapped file; at the new default it records metadata only (hash becomes
opt-in via `level = "hash"`). Must be a CHANGELOG breaking/behavior note; `data_files` record
shape stays stable (fields present; `sha256` null unless level is `hash`).

**stat implementation note:** use `fstat` on the fd we already hold (race-free, cheap on NFS),
NOT `os.stat(path)`. Document per-OS cost (local: cache-hot ~free; NFS: fstat cheap, realpath
costly; macOS/Windows: local fstat cache-hot).

Config knob: `[capture.file_io].level` (default `stat`), plus `max_hash_bytes` (skip hashing
huge files at `hash` level) and path-filter `exclude` (mainly relevant to the deferred auto
path). `mode`/`auto` NOT added now (item 3 deferred).

## Phase 1 execution record (2026-07-06) — items 1 & 2

Executed by opencode after the Gate-2 decisions above.

- **Item 1 — coarse per-process I/O totals:** `capture/system_metrics.py` gained
  `get_proc_io()` (Linux `/proc/self/io`: rchar/wchar/read_bytes/write_bytes/syscr/syscw,
  None elsewhere). The `ResourceWatcher` snapshots it at start and each sample and emits
  `resources.io_counters = {start, last, delta}` (delta = this run's I/O volume). Gated by
  the existing `system_metrics` key; zero interception (one cheap read per sample).
- **Item 2 — hardened `pubrun.open()` + graded level (`core.py`):** `ProvenanceFileProxy`
  rewritten to be **level-driven** (`none|name|stat|realpath|hash`, resolved from
  `[capture.file_io].level`, default `stat`). Correctness fixes: (a) records at close AFTER
  the underlying file is closed, and the `hash` level computes SHA-256 from the **on-disk
  bytes** — so it is correct even for buffered/`readinto` reads that never pass through the
  proxy (the old incremental-hash gap) and independent of text/binary mode (the old
  `errors="ignore"` re-encode dishonesty); (b) `stat` uses `os.stat` on the just-closed file
  (attrs cache-hot; recommend fstat-on-fd noted — current impl stats the path post-close
  which is equivalently cache-hot and race-free since we just held it); (c) `realpath` is a
  separate HIGHER tier than `stat` (honest NFS cost order); (d) `max_hash_bytes` caps large
  files. `data_files` record shape stable (`sha256` present but `null` unless level=`hash`).
  The proxy delegates all non-recording methods to the real file via `__getattr__`, so
  behavior is identical to the builtin.
- **Config:** `[capture.file_io].level = "stat"` + `max_hash_bytes = 0` added to
  `resources/default.toml` with the cost caveats inline.
- **BEHAVIOR CHANGE (documented):** default is now `stat` (no auto-hash); hashing is opt-in
  via `level = "hash"`. CHANGELOG `### Changed` note added; two existing tests that asserted
  auto-hashing updated to pass `capture={"file_io":{"level":"hash"}}`.
- **Tests:** new `tests/test_file_io_provenance.py` (9): default=stat-metadata-no-hash,
  hash-matches-on-disk (read + write mode), name-level path-only, realpath-includes-realpath,
  none-records-nothing, proxy-is-usable-file (readline/iteration/context-mgr), max_hash_bytes
  skips large files, `get_proc_io` shape, io_counters in manifest. Full suite **747 passed**,
  2 skipped; lone failure the known SIGPIPE flake (passes in isolation).
- **Docs:** `docs/api.md` (`pubrun.open` level table + behavior-change note),
  `docs/configuration.md` (`[capture.file_io]`), `docs/manifest.md` (`data_files` per-level
  fields + `resources.io_counters`), `CHANGELOG.md`.

### Deferred to a FUTURE separate proposal (NOT built)

- **Item 3 — `sys.addaudithook` automatic capture** (capture opens without the user calling
  `pubrun.open()`). Observe-only (does not patch `open`), but process-lifetime (not
  removable), adds per-open cost, needs path filters + per-event pause-gating, and cannot do
  L4 inline. Revisit only if automatic capture is demonstrably needed; if pursued, it gets
  its own IPD + plan-review. The `[capture.file_io]` knob intentionally has NO `mode`/`auto`
  key yet, keeping the door closed until then.
- **Item 4 — global `builtins.open` monkeypatch:** rejected permanently (dominated by the
  audit hook; defeated by C-extensions; highest blast radius).
