# IPD-C: richer `report`/`res`/timeline output + `report`/`show` parity

- Date: 2026-07-07
- Concern: usability / completeness of the diagnostic viewers. Four related gaps: (#4) `pubrun
  res` shows process-tree RSS but no tree CPU, and it is unclear whether the main-process
  numbers still appear; (#8) `pubrun report`/`show` shows only peak RSS/CPU, not avg/min/max;
  (#9) the event timeline uses a verbose ISO timestamp and only truncates above 40 events;
  (#13) `report` and `show` are the same command except `show` has `--utc` and `report` does
  not (an accidental asymmetry).
- Scope: `src/pubrun/report/diagnostics.py` (resources + report + timeline rendering),
  `src/pubrun/__main__.py` (`report`/`show` flag parity). Read-only over the manifest +
  `events.jsonl`; no capture/runtime change. Docs, tests.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Make the viewers show the full, useful resource picture (main AND tree, CPU AND RSS,
avg/min/max not just peak), a readable timeline, and give `report`/`show` identical behavior.

## Project conventions discovered (Step 0)

- `print_resources_report` (`diagnostics.py:592`); `print_report` timeline
  (`diagnostics.py:213-247`). `report`/`show` share `_run_report` (`__main__.py:538`, dispatch
  `:2291`); `show` alone has `--utc` (`:2227`); `report` is a hidden alias (`help=SUPPRESS`).
- **Capture stores only peaks** (`resources.peak_rss_bytes`/`peak_cpu_percent`/
  `peak_tree_rss_bytes`/`end_rss_bytes`; `capture/resources.py:180-362`). BUT per-sample
  `rss_bytes`/`cpu_percent` are in `events.jsonl` `resource_sample` payloads
  (`diagnostics.py:754-758`), which report already reads for the chart. So **avg/min/max are
  computable at report time from the samples** — no capture change needed.
- Tree behavior (verified): `metric=="all"` adds one `Peak Tree RSS` line
  (`diagnostics.py:686-689`) and ALWAYS renders main Peak/End RSS + Peak CPU
  (`:651-670`). **No tree CPU exists anywhere** — CPU is main-process only by design
  (`:824-830`: "child CPU is excluded from the metric"). The RSS chart is scope-labeled;
  there is no separate tree chart.
- Timeline timestamp: `datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()` → e.g.
  `2026-07-07T04:47:49.235361+00:00` (`:232-234`); shows first 20 + last 20, truncates only
  when > 40 (`:218-245`); always UTC (ignores `--utc`).

## Findings

| ID | Severity | Rem. Risk | Persona | Area | Finding | Evidence |
|----|----------|-----------|---------|------|---------|----------|
| C1 | Medium | Low | eng | Completeness | `res` shows main RSS/CPU + Peak Tree RSS, but **no process-tree CPU**. Tree CPU is not captured at all. | `diagnostics.py:686-689,824-830`; `capture/resources.py` |
| C2 | Low | Low | eng | Clarity | User expected `res` to show BOTH tree and main; it does (main always rendered), but the labeling doesn't make the "main vs tree" distinction obvious. | `diagnostics.py:651-689` |
| C3 | Medium | Low | eng | Completeness | `report`/`res` show only **peak** RSS/CPU (+ end RSS), not **avg/min/max**, though per-sample data is available in `events.jsonl`. | `diagnostics.py:651-670` |
| C4 | Low | Low | novice | Readability | Timeline timestamp is full ISO w/ microseconds + `+00:00`; user wants `[2026-07-07 04:47:49]`. | `diagnostics.py:232-234` |
| C5 | Low | Low | novice | Readability | Timeline only truncates above 40; user wants oldest-10 + newest-10 with a `[... N truncated ...]` marker above 20. | `diagnostics.py:218-245` |
| C6 | Medium | Low | eng | Consistency | `report` lacks `--utc` that `show` has; otherwise identical (see IPD note / item #13). | `__main__.py:2227,2291` |

## Proposed changes (ordered, validatable)

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | C3 | Compute **avg / min / max** RSS and CPU from the `resource_sample` events at report time and render them alongside peak (e.g. `RSS: peak X / avg Y / min Z` ; `CPU: peak / avg / min / max`). **Data availability (verified):** each `resource_sample` payload carries `rss_bytes` + `cpu_percent`, and `tree_rss_bytes` when scope=tree (`capture/resources.py:367-369`). So avg/min/max are computable for **main RSS, main CPU, and tree RSS**. There is **no per-sample tree CPU** today — tree-CPU avg/min/max is only possible if step 2(a) additionally emits a per-sample tree-CPU value; otherwise report tree CPU as peak-only (or omit). Fall back gracefully to peak-only when no per-sample events exist (older/short runs). | `diagnostics.py` (+ `capture/resources.py` if step 2(a) adds per-sample tree CPU) | Low | A run with N samples shows main-RSS/main-CPU/tree-RSS avg/min/max matching a recomputation; a run with no samples shows just the peak line (no crash); tree-CPU stats appear only if per-sample tree CPU is emitted. |
| 2 | C1 | **Process-tree CPU: decide + implement.** Option (a) capture tree CPU in `capture/resources.py` and render `Peak Tree CPU` — this CHANGES capture and the "child CPU excluded" invariant, so it is gated behind the existing `scope="tree"` and documented; Option (b) render tree CPU only if already derivable, else state honestly that tree CPU is not measured. **Prefer (a)** per user request, but flag the invariant change for plan-review (Open Q1). **Correctness note (must not naively sum instantaneous %):** per-process CPU% is a rate over the sample interval; tree CPU must be computed as the delta of summed CPU *time* (jiffies/`utime+stime` across the tree from `/proc/<pid>/stat`, or the darwin equivalent already used for tree RSS) divided by the wall interval — NOT a sum of per-process instantaneous `cpu_percent` (which is window-sensitive and can mislead). It may legitimately exceed 100% (multi-core), so label it "% (of one core; tree)" and do not clamp. Reuse the tree-walk already present for `_poll_tree_rss` (`capture/resources.py:268`). | `capture/resources.py`, `diagnostics.py` | **Med** | If (a): a multiprocess tree run records + shows a plausible Peak Tree CPU computed from summed CPU-time deltas (not instantaneous-% sum); single-process run's tree CPU ≈ main CPU. Existing "CPU = main process" tests updated intentionally. |
| 3 | C2 | Relabel the resource block so main vs tree is explicit: `Peak RSS (main)` / `Peak RSS (tree)` / `Peak CPU (main)` / `Peak CPU (tree)`, each shown only when present. | `diagnostics.py` | Low | Labels present; a non-tree run shows only `(main)` lines. |
| 4 | C4 | Format timeline timestamps as `YYYY-MM-DD HH:MM:SS` (drop microseconds + offset in the human view; honor `--utc` vs local like the rest of the report). | `diagnostics.py` | Low | Timeline lines match `[2026-07-07 04:47:49]`; `--utc` toggles tz. |
| 5 | C5 | Truncate the timeline to **oldest 10 + newest 10** with `[... N events truncated ...]` when total > 20 (down from 40/20+20). | `diagnostics.py` | Low | 25-event run shows 10 + marker + 10; ≤20-event run shows all. |
| 6 | C6 | Give `report` and `show` identical flags — add `--utc` to `report` (or route both through one shared parser-builder). Keep `report` a documented back-compat alias of `show`. | `__main__.py` | Low | `pubrun report --utc` works; `report -h`/`show -h` show the same options. |

## Deferred / out of scope (with reason)

| Finding ID | Rem. Risk | Axis | Reason | Later step |
|------------|-----------|------|--------|------------|
| C1 opt (a) if it proves costly | Med-High | Functionality/perf | Summing child CPU% accurately across a tree can be sampling-noisy and adds watcher cost; if plan-review deems the capture change risky, fall back to option (b) (render only, honest "not measured") and defer true tree-CPU capture to its own IPD. | Dedicated tree-CPU capture IPD. |

## Scope check

- Over-scope: avg/min/max are computed from EXISTING samples (no new capture) — cheap.
  Not adding percentile histograms to the viewer (KISS).
- Under-scope: tree CPU genuinely missing (C1) — added, with the invariant-change caveat.

## Required tests / validation

- avg/min/max computed correctly from a synthetic `events.jsonl`; peak-only fallback with no
  samples; no crash on empty/short runs.
- Tree CPU (per chosen option): captured+rendered, or honestly labeled absent.
- Labels: main vs tree lines present/absent as appropriate.
- Timeline: timestamp format, `--utc` toggle, 10+10 truncation boundary at 20.
- `report`/`show` flag parity: `report --utc` accepted; help lists match.
- Full suite green (update the existing "CPU is main-process" test if option (a) is chosen —
  intentional behavior change, documented).

## Spec / documentation sync

`docs/cli.md` (`report`/`show`/`res` — avg/min/max, tree vs main, timeline format;
`report`/`show` parity), `docs/manifest.md` (if tree CPU is captured, document the new field),
`CHANGELOG.md`.

## Open questions

1. **Tree CPU (C1/step 2):** capture it (changes the "child CPU excluded from CPU metric"
   invariant, adds a `peak_tree_cpu_percent` field + watcher cost) vs. render-only/honest-absent?
   (Leaning: capture it since you explicitly want it, gated to `scope="tree"`; confirm the
   invariant change at plan-review.)
2. avg/min/max presentation: one dense line (`peak/avg/min/max`) vs separate lines? (Leaning:
   dense single line per metric.)
3. `--utc` parity: add the flag to `report`, or unify both commands on one parser builder?
   (Leaning: unify the builder — removes the whole class of future drift.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-07)

Reviewed via `plan-review`. Verified: `report`/`show` both dispatch to `_run_report`
(`__main__.py:2284,2291`); `show`/`status` have `--utc`, `report` does not (`:2227,2242`);
`resource_sample` payload = `rss_bytes`+`cpu_percent` (+`tree_rss_bytes` when tree)
(`capture/resources.py:367-369`); NO per-sample tree CPU exists; tree RSS via `_poll_tree_rss`
(`:268`). Verdict: **APPROVE WITH REVISIONS APPLIED.**
- **P4 (MEDIUM, functionality):** tree-CPU must be computed from summed CPU-TIME deltas over
  the tree (not a sum of instantaneous per-process `cpu_percent`, which is window-sensitive);
  may exceed 100% (multi-core) — label "% of one core", don't clamp; reuse the `_poll_tree_rss`
  tree walk.
- **P5 (MEDIUM, functionality):** clarified avg/min/max are computable for main-RSS/main-CPU/
  tree-RSS from existing samples, but tree-CPU avg/min/max needs step-2(a) to emit per-sample
  tree CPU, else report tree CPU peak-only.
No deferrals on risk (C1 option-(a) capture cost noted as a Med-High fallback to option (b)).
Sequence BEFORE IPD-F (shares the resource-series helper).
