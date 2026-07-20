# IPD: Shrink the benchmark result JSON (fit the GitHub submission path) without data loss

- Date: 2026-07-20
- Concern: functionality / interoperability (result-file size + schema) / documentation
- Scope: `benchmarks/harness.py` (result builder + redaction + filenames), `benchmarks/aggregate.py`
  and `benchmarks/plot.py` (readers), the benchmark schema/version, `benchmarks/README.md` +
  `docs/performance.md`, `src/pubrun/__main__.py` (the `pubrun bench` submit path), tests.
- Status: to-review
- Approval: (set when a human approves; omit until then)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / driver

The `pubrun bench` **redacted** result JSON is far too large for the community-submission path: it is
submitted via a GitHub issue (body cap ~65,536 bytes), but a real redacted result is ~204 KB pretty /
~120 KB compact - roughly 2-3x over. The oversize is almost entirely REDUNDANT / low-value bytes, so
it can be cut to well under the cap with ZERO analytical data loss.

Measured on a real redacted result (`benchmarks/results/*.redacted.json`, ~120,258 bytes compact):

| Variant | Compact bytes | vs. ~65 KB cap |
|---|---|---|
| Original (pretty, indent=2) | 204,204 | 3.1x over |
| Compact (no pretty-print) | 120,258 | 1.8x over |
| Compact + round timings 6 dp | 82,579 | still over |
| **Compact + 6 dp + de-duplicated schema (raw timings KEPT)** | **~35,802** | **fits, ~55% of budget** |

Conclusion: rounding alone is NOT enough (6 dp = 82.6 KB, still over). The decisive, no-data-loss lever
is REMOVING STRUCTURAL REDUNDANCY (define scenarios once; per-pass keep only what varies; drop stats
that are recomputable from the raw timings). Doing that at 6 dp lands ~36 KB with raw timings fully
retained. The maintainer's directive: implement every lever that does NOT lose data; use 6 decimals.

## Goal

Emit a compact, non-redundant, versioned benchmark JSON that (a) fits the GitHub issue-body cap with
headroom, (b) loses NO analytical data (every raw per-iteration timing retained), and (c) keeps the
LOCAL full result complete. Also correct two hygiene items uncovered alongside: timestamp capture and
explicit file naming.

## Design decisions (all no-data-loss unless noted)

1. **Compact serialization.** Write JSON with `separators=(",", ":")` (no indentation) for the
   result files. (-41% alone.)
2. **Round timings to 6 decimal places** (microsecond-ish; ample for wall-clock). Store as numbers,
   not strings. NO other numeric field is rounded lossily beyond its own natural precision.
3. **Define scenarios ONCE.** A run fixes its scenario set at start; today each pass repeats every
   scenario's `group`/`mode`/`workload`/`config` identically. Move the static scenario descriptors to
   a single top-level `scenarios` map (name -> {group, mode, workload, config}). Passes reference
   scenarios by name. (Pure redundancy removal.)
   - **If a scenario's definition can legitimately CHANGE mid-run, it does not today** (scenarios are
     fixed at run start - confirm in code during execution). If that ever changes, record per-pass
     overrides only for the changed fields. (Open question 1.)
4. **Merge/relocate timings; index by the fixed run shape.** Iterations and warmup are fixed at start,
   so capture them as small arrays and store timings positionally:
   - `iterations`: array describing the run shape, e.g. `[1, 30, 30, 30]` (warmup pass of 1, then
     three 30-iteration passes). `warmups`: array of warmup counts, e.g. `[]` = none, `[1]` = first
     iteration is warmup.
   - Per scenario, timings are an **array-of-arrays grouped by pass** (resolved: readable form),
     6 dp, in run order, aligned to `iterations`/`warmups` so readers know which members are which.
5. **Drop derived stats from the stored file** (`n`, `min_s`, `median_s`, `mean_s`, `p95_s`, `max_s`,
   `stdev_s`). They are all recomputable from the retained raw timings, so this is NO data loss.
   **BUT readers depend on them** (`aggregate.py:75-76` reads `median_s`/`min_s`): resolved -> readers
   RECOMPUTE from the retained timings (single source of truth). No derived-stats block in the
   transmitted `/5` file. If a richer "augmented" result with precomputed stats is ever wanted, it is
   generated on the RECEIVING side after ingest (this IPD is about transmission size). This is the one
   step with a reader-compatibility cost (handled in the "readers" step below).
6. **Per-pass, keep only what VARIES** (timings, and any per-run dynamic env/metrics such as
   mem/load/io that actually change between passes); do not repeat static scenario descriptors.
7. **Keep redaction placeholders.** Dropping the `<redacted>` markers saves only ~394 bytes (26
   values) and would erase the signal that a field existed-but-was-masked - not worth it. Keep them.

### Timestamp + filename hygiene (maintainer directive)

8. **Filename timestamp stays UTC** (already so: `harness.py:437` uses `now(timezone.utc)`). Do not
   change to local time.
9. **Capture BOTH UTC and local time (with offset) IN the JSON.** Today only `generated_utc` exists
   (`harness.py:377`). Add `generated_local` as a local ISO-8601 string WITH its UTC offset (e.g.
   `...-04:00`). Rationale (maintainer): storing local+offset explicitly is more reliable than trying
   to reconstruct local time from UTC after the fact; the offset lives in the data.
10. **Explicit result filenames** (already applied going-forward this session; make the harness
    produce them): full result -> `*.unredacted.json`; shareable -> `*.redacted.json`; never a bare
    `*.json`. The redacted filename must NOT embed the hostname (use a stable non-identifying hash
    token), matching the in-file hostname redaction.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Bump the schema to `pubrun-benchmark/5` and design the compact shape: top-level `scenarios` map (defined once), `iterations`/`warmups` arrays, per-pass `timings` (6 dp) keyed by scenario, per-pass only-varying data, retained raw timings, kept redaction markers. Write JSON compact. | `harness.py`, schema | Medium (functionality: output-shape change) | a produced /5 file is <=~40 KB and round-trips |
| 2 | Add `generated_local` (local ISO-8601 + offset) alongside `generated_utc`; keep the UTC filename stamp. | `harness.py` | Low | both fields present; offset correct |
| 3 | Make the harness write `*.unredacted.json` (full) and `*.redacted.json` (shareable, hostname-hashed filename) - no bare `*.json`. | `harness.py`, `__main__.py` bench path | Low | produced filenames match; redacted name has no hostname |
| 4 | **Update readers to the /5 shape**: `aggregate.py` (and `plot.py` if it reads stats) recompute `n/min/median/mean/p95/max/stdev` FROM the retained timings instead of reading stored stat fields; read scenarios from the top-level map. Handle BOTH /4 and /5 during transition (version-gated) so old committed/contributed results still aggregate. | `aggregate.py`, `plot.py` | Medium (functionality: readers must not break on old files) | aggregate produces identical stats from a /5 file and from the equivalent /4 file |
| 5 | Add a **size guard** to the bench submit path: warn/refuse if the redacted file exceeds the GH issue-body budget, pointing at the attach-file alternative. | `__main__.py`, `harness.py` | Low | an over-budget file triggers the guard |
| 6 | Tests: a /5 result validates + round-trips; stats recomputed from timings match the old stored stats within tolerance; redacted /5 file is <= budget; both-timestamps present; filename conventions. **Contract/output-shape change -> full CI matrix.** | `benchmarks/test_benchmarks.py` (+ schema test if one exists) | Low | new tests green on the full matrix |
| 7 | Docs: update `benchmarks/README.md` + `docs/performance.md` for the /5 shape, the timestamp fields, and the filename conventions; CHANGELOG entry. | docs, CHANGELOG | Low | `/assess documentation` clean |

## Scope check

- Over-scope: NOT redesigning the metrics collected, only how they are stored. NOT touching the
  history-scrub of the already-leaked file (separate IPD `20260720-1126-01`). NOT changing what
  `pubrun` the library captures - this is benchmark-tooling only.
- Under-scope: the reader update (step 4) is REQUIRED, not optional - a compact schema that breaks
  `aggregate.py` is half a fix. Both-version support during transition is required so existing
  contributed results still work.

## Required tests / validation

- A produced `/5` redacted file is comfortably under the GH issue-body cap (target < ~40 KB; measured
  prototype ~36 KB) and contains every raw timing.
- Stats recomputed from `/5` timings equal (within float tolerance) the `/4` stored stats for the same
  data - proves NO data loss.
- Readers (`aggregate.py`, `plot.py`) work on both `/4` and `/5` inputs.
- `generated_utc` + `generated_local` (with offset) both present; filename stamp UTC.
- Full CI matrix green (output-shape/reader change is contract-shaped, per AGENTS.md matrix discipline).

## Spec / documentation sync

`benchmarks/README.md`, `docs/performance.md`, schema doc, CHANGELOG (schema /5; timestamp fields;
filename conventions; size fits GH submission). Run `/assess documentation` after.

## Open questions (resolved 2026-07-20)

1. **Scenario definitions change mid-run?** -> RESOLVED: NO. Scenarios are fixed at run start and we
   will NOT enable per-run definition differences at this time. So "define scenarios once" needs no
   per-pass override mechanism; a single top-level `scenarios` map is authoritative. (Execution still
   confirms in code that nothing currently mutates a scenario def mid-run; if something does, that is
   a bug to fix, not a schema feature to add.)
2. **Timings layout** -> RESOLVED: ARRAY-OF-ARRAYS, grouped by pass (e.g. `[[warmup...],[pass1...],
   [pass2...]]`), aligned to the `iterations`/`warmups` arrays. Chosen for readability; the size cost
   over a flat array is negligible because the whole file is ~36 KB, i.e. well under the ~65 KB
   GitHub cap (that headroom is the "budget" - we can afford the slightly larger, clearer form).
3. **Stored stats** -> RESOLVED: DROP them from the transmitted file; readers RECOMPUTE from the raw
   timings (single source of truth). This IPD is about TRANSMISSION size. If a richer "augmented"
   JSON with precomputed stats is ever wanted, it is produced on the RECEIVING side after ingest, not
   stored in the submitted artifact. No precomputed-stats block in the `/5` file.

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Execution contract:
- Honesty rule (hard MUST): paste ACTUAL runner/size output when reporting; never claim a pass/size not
  measured.
- Matrix rule: output-shape + reader change is contract-shaped; validate on the full CI matrix before
  done.
- Commit path-scoped; never push without explicit human approval.
- Keep the LOCAL `*.unredacted.json` complete; only the redacted/submitted artifact is size-optimized.
- On completion, `git mv` this IPD to `.agents/plans/executed/` (Status -> executed).

## Workflow history
- 2026-07-20 (opencode / its_direct/pt3-claude-opus-4.8-1m-us): drafted from measured size analysis;
  6 dp chosen; all no-data-loss levers included; proposed 7 steps.
- 2026-07-20 (opencode / its_direct/pt3-claude-opus-4.8-1m-us): open questions resolved by maintainer
  - (1) scenarios fixed per run, no per-pass definition differences; (2) timings array-of-arrays
  grouped by pass; (3) drop stored stats, readers recompute, augmented-stats only receiver-side.
