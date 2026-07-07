# IPD-F: TUI — view CPU & memory usage (with graphs)

- Date: 2026-07-07
- Concern: usability / feature. The interactive TUI (`pubrun ui`) can browse and inspect runs
  but offers no way to view a run's CPU/memory usage over its lifecycle. Users want to see
  resource usage in the TUI, preferably as graphs.
- Scope: `src/pubrun/tui/app.py` (+ any new TUI widget/screen), reusing the existing resource
  chart data path (`events.jsonl` `resource_sample` samples + the sparkline/chart logic in
  `report/diagnostics.py`). The TUI is an OPTIONAL extra (`pip install "pubrun[tui]"`,
  textual/rich); nothing here touches core/runtime or adds a core dependency. Docs, tests.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

In the TUI, selecting a run lets the user view its CPU% and RSS over time as graphs (with a
numeric summary), reusing pubrun's existing per-sample data — no new capture.

## Project conventions discovered (Step 0)

- TUI: `PubrunTUIApp` (`tui/app.py:23`, ~110 lines) — a Tree sidebar + a detail area; textual
  `App` with `action_toggle_sidebar`/`action_refresh_all`/`on_tree_node_selected`. Gated behind
  the `[tui]` extra; core stays zero-dep.
- Resource data: per-sample `rss_bytes`/`cpu_percent` live in `events.jsonl` (`resource_sample`
  payloads), already consumed by `print_resources_report`/the ASCII chart
  (`report/diagnostics.py:754-762,821-865`). Textual ships a `Sparkline` widget; rich has
  plotting-ish primitives. The existing ASCII chart logic can also be embedded in a `Static`.
- Principle: TUI is optional; degrade gracefully when `[tui]` deps are absent (already the
  pattern for launching `ui`).

## Findings

| ID | Severity | Rem. Risk | Persona | Area | Finding | Evidence |
|----|----------|-----------|---------|------|---------|----------|
| F1 | Medium | Low-Med | eng | Feature gap | TUI shows run metadata but no CPU/memory usage view/graph. | `tui/app.py` (no resource widget) |
| F2 | Low | Low | eng | Reuse | The per-sample data + chart rendering already exist for `pubrun res`; the TUI should reuse them, not reimplement. | `diagnostics.py:754-865` |

## Proposed changes (ordered, validatable)

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | F2 | Factor the per-sample extraction (read `events.jsonl` → time-ordered `rss`/`cpu` series + summary) into a reusable helper callable by BOTH `pubrun res` and the TUI (avoid divergence). If `print_resources_report` already isolates this, just expose it; else extract a small pure function. | `report/diagnostics.py` (+ maybe a `report/resource_series.py`) | Low | `pubrun res` output unchanged; the helper returns the same series it plots. |
| 2 | F1 | Add a **Resources view** to the TUI: on run selection, render CPU% and RSS as graphs — prefer textual's `Sparkline`/plot widgets when available, else embed the existing ASCII chart in a `Static`. Include a numeric summary (peak/avg/min/max — aligns with IPD-C). A key binding (e.g. `r`) toggles the resource view. | `tui/app.py` (+ a widget) | Low-Med | In the TUI (textual test harness), selecting a run with samples renders the resource view with non-empty CPU/RSS series; a run without samples shows a graceful "no resource samples" message. |
| 3 | F1 | Graceful degradation: if the run has no `events.jsonl`/samples, or the terminal is tiny, show a clear message instead of an empty/broken graph. | `tui/app.py` | Low | Sample-less run and a very small terminal both render a message, no exception. |

## Deferred / out of scope (with reason)

| Finding ID | Rem. Risk | Axis | Reason | Later step |
|------------|-----------|------|--------|------------|
| Live/streaming graphs for RUNNING runs | Med-High | Complexity/Functionality | Live-updating a graph for an in-progress run adds a refresh/poll loop and lifecycle complexity beyond "view a run's usage". Ship post-hoc graphs first; live streaming is a separate IPD. | Live-resource TUI IPD. |

## Scope check

- Over-scope: no live streaming (deferred); no new charting dependency beyond what `[tui]`
  already brings (textual/rich).
- Under-scope: resource viewing was absent from the TUI; added, reusing existing data.

## Required tests / validation

- Series helper: given a synthetic `events.jsonl`, returns correct time-ordered CPU/RSS +
  summary; `pubrun res` still renders identically (regression).
- TUI: textual test harness (Pilot) — select a run → resource view populated; sample-less run
  → message; toggle binding works. (Marked to skip if `[tui]` deps unavailable, matching
  existing TUI test gating.)
- Core import unaffected; no new core dependency (`import pubrun` works without textual).
- Full suite green.

## Spec / documentation sync

`docs/cli.md` (`ui` — resource view + key binding), README `ui` note if relevant,
`CHANGELOG.md`.

## Open questions

1. Graph widget: textual `Sparkline` (simple, built-in) vs embedding the existing ASCII chart
   (consistent with `pubrun res`) vs a richer plot? (Leaning: Sparkline for the live-feel +
   the numeric summary; reuse ASCII chart as fallback.)
2. Toggle vs dedicated tab/pane: a key toggle (`r`) vs a persistent resources pane beside
   metadata? (Leaning: a toggle to start; a pane later if wanted.)
3. Should the resources view honor the same peak/avg/min/max as IPD-C? (Leaning: yes — sequence
   F after C so the summary helper is shared.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`. Sequence AFTER IPD-C (shared resource series).
