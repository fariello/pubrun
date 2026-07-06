# IPD: `pubrun methods` over many runs (aggregate / multi-run methods text)

- Date: 2026-07-06
- Concern: functionality / UX (a real design decision, not a mechanical change)
- Scope: how `pubrun methods` should behave when pointed at, or filtered to,
  MANY runs (100+ is common, e.g. `~/VC/uri-ai-info` has 1600+). Today it emits
  one Computational Methods paragraph from exactly one run.
- Status: PENDING (design decision made 2026-07-06; plan-review done — verdict
  APPROVE WITH REVISIONS APPLIED; ready for execution on approval).
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Decisions (maintainer, 2026-07-06)

- **Representation: option (C)** — one representative paragraph + a compact
  variance note. When the selected runs are environment-homogeneous the output
  reads exactly like today's single-run methods; when they diverge, a short note
  discloses which fields varied and how. (Confirmed.)
- **Trigger: explicit flag** (`--aggregate`/`--all`), preserving the current
  single-run default of a bare/filtered `pubrun methods` (most-recent wins).
  (Recommended default; confirm exact flag name at implementation.)
- Remaining open questions (#3 git.commit handling, #4 large-set cap) still to be
  settled during `plan-review`/implementation, but they do not block the shape.

## Problem / motivation

`pubrun methods` produces a publication-ready "Computational Methods" paragraph
(OS, CPU, RAM, Python, key packages, git commit, pubrun version). It currently
resolves to a SINGLE run via `_get_manifest_path(...)` (default: most recent;
optionally narrowed by the run filters `-f/--status/--older-than/...`) and calls
`generate_report(manifest, format_type)` on that one manifest
(`__main__.py:_run_methods`; `report/methods.py:generate_report`).

For a paper, a researcher usually ran an analysis **many times** (sweeps, seeds,
folds, retries). They want ONE honest methods paragraph describing the
computational environment those runs shared — not to hand-pick a single run and
hope it is representative, and not 100 paragraphs. The hard part is that runs are
NOT guaranteed identical: different machines (cluster nodes), Python patch
versions, package versions, git commits, or hardware can vary across the set.

**Existing precedent (verified):** `pubrun show` ALREADY handles the multi-run
case — when no explicit run dir is given and the filters match many runs, it
loops `_run_report` over the whole matched set, emitting one report per run
(option B), with no flag required (`__main__.py:1387-1408`). The plumbing this
IPD needs (scan → filter → iterate) therefore already exists in the codebase;
`_get_manifest_path` (`__main__.py`) also already does `scan_runs` + `filter_runs`
with `limit=1` to pick the most-recent match. The multi-run methods path should
be modeled on that seam (drop the `limit=1`, collect the full matched set).

## Key design question (must be answered before building)

**How should methods text represent a *set* of runs?** Options:

- **(A) Aggregate into one paragraph, asserting homogeneity + noting variance.**
  Compute each field across the selected runs; if all runs agree, state the
  single value; if they differ, either summarize ("Python 3.11.4–3.11.7 across
  N runs on 3 hosts") or list the distinct values. This is the most useful for a
  paper but requires deciding, per field, how to express divergence honestly.
- **(B) Per-run paragraphs.** Emit one section per run (with a header). Honest
  and simple, but useless at 100+ runs (a wall of near-identical text).
- **(C) Representative + variance appendix.** One paragraph from a chosen
  representative run (e.g. most recent, or the modal environment), plus a short
  "N runs; environment varied as follows: ..." note listing only the fields that
  differ. Compromise: readable prose + honest disclosure.
- **(D) Refuse to aggregate divergent runs.** If the selected runs are not
  environment-identical, error/warn and require the user to narrow the filter.
  Safest but least helpful.

**Recommendation to evaluate: (C)** — a single representative paragraph plus a
compact variance note, defaulting to "if everything matches, it reads exactly
like today's single-run output." (A) and (C) converge when the runs are
homogeneous; (C) degrades more gracefully when they are not.

## Secondary design questions

1. **What triggers multi-run mode?** Options: an explicit flag
   (`pubrun methods --all` / `--aggregate`), OR: whenever the run filters match
   >1 run, aggregate automatically (vs. today's "most recent wins"). Changing the
   default behavior of a bare filtered `methods` is a **behavior change** and
   must be deliberate. Recommend an explicit flag (e.g. `--aggregate` / `--all`)
   so the current single-run default is preserved; a bare `pubrun methods` with a
   filter matching many runs keeps picking the most recent (backward compatible)
   unless the flag is given. CONFIRM.

   **Cross-command consistency note (rubric H):** `pubrun show` already
   auto-iterates the matched run set with NO flag (per-run output; see the
   precedent above). Choosing an explicit `--aggregate` flag for `methods` is
   therefore a *deliberate* divergence from `show`, justified because (a)
   `methods` produces a single publication paragraph where silently aggregating
   many runs by default could mislead, and (b) it preserves the current
   single-run default (no behavior change). This divergence must be documented in
   `docs/cli.md` so users are not surprised that `show` and `methods` treat a
   many-run filter differently. If instead auto-aggregation is preferred (to
   match `show`), that is a conscious behavior change and must be called out in
   the CHANGELOG. Settle this in `plan-review`/at implementation.
2. **Which fields are compared for homogeneity?** The methods-relevant ones:
   `host.os_name`, `hardware.cpu.model`, `hardware.memory_total_bytes`,
   `python.version` (+ implementation), highlighted packages + versions,
   `git.commit`, `run.library_version`. `git.commit` especially will often differ
   across a long-running project — decide whether a differing commit is "variance
   to note" or "these aren't the same analysis, refuse".
3. **How is divergence expressed in prose?** e.g. per field: single value if
   uniform; "ranged from X to Y (N runs)" for versions; "on hosts A, B, C" for
   os/cpu; a count like "across 137 runs". Needs a small, consistent formatting
   convention that stays readable and honest (no fabricated precision).
4. **Performance at scale.** 100–1600+ runs means reading that many
   `manifest.json` files. Must be bounded and reasonably fast (the runs-scan
   already exists in `status.py`; reuse it). Decide whether to cap (e.g. warn
   above N) or stream.
5. **Interaction with `hydrate_manifest`.** Single-run methods hydrates HPC
   parent context (`report/utils.hydrate_manifest`). Decide how/whether that
   applies per-run in aggregate mode.
6. **Output determinism.** Aggregation must produce stable, sorted output (e.g.
   sorted distinct values) so the same run set always yields the same text.

## Proposed shape (subject to the decisions above)

- Add an aggregation entry point (e.g. `generate_report_multi(manifests, fmt)`
  in `report/methods.py`) that takes a list of manifests, computes per-field
  uniformity, and renders a representative paragraph + variance note via the
  existing templates (extended with an optional variance section).
- Wire `pubrun methods` to collect the filtered run set (reuse
  `status.scan_runs` + `filter_runs`) when the aggregate flag is set, load each
  manifest defensively (the EC-01 hardening already makes the readers robust to
  malformed manifests), and call the multi-run generator.
- Keep single-run behavior byte-for-byte unchanged when not aggregating (or when
  exactly one run matches).

## Anti-regression / invariants (rubric D)

- **Write the single-run parity characterization test FIRST**, before touching
  `_run_methods`: capture the exact current output of both a default
  `pubrun methods <run>` and a filtered single-match `pubrun methods -f <x>`, and
  assert it is byte-identical after the change. Also assert `--aggregate` over a
  single matching run produces that same single-run output (the aggregate path
  must collapse to the single-run text when there is one run). Green before AND
  after.
- Aggregation output MUST be deterministic for a fixed run set (sorted).
- Must not crash on a malformed manifest in the set (skip it, note the count).
- Honesty: never present a single run's value as if it held for all when it did
  not; divergence must be disclosed.

## Required tests / validation (once designed)

- Single-run parity (unchanged output).
- Homogeneous set of N runs → one paragraph with the shared values + "N runs".
- Heterogeneous set (differing python/package/commit/host) → variance expressed
  per the chosen convention; deterministic ordering.
- Large set (e.g. 200 synthetic manifests) → completes in reasonable time; a
  malformed manifest in the set is skipped, not fatal.
- Full suite green.

## Spec / documentation sync

`docs/cli.md` (`methods` flags), `docs/api.md` (if a public generator is added),
README if it shows `methods` usage, `CHANGELOG`. Run `/assess documentation`.

## Open questions (for the maintainer)

1. Which representation — (A) aggregate, (B) per-run, (C) representative+variance
   [recommended], or (D) refuse-if-divergent?
2. Trigger: explicit `--aggregate`/`--all` flag [recommended] vs. auto-aggregate
   when a filter matches many runs (behavior change)?
3. Is a differing `git.commit` across the set "variance to note" or grounds to
   refuse/split? (Long projects will span many commits.)
4. Cap/warn threshold for very large sets, if any?

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution and is NOT auto-executed. The representation (option C) and trigger
(explicit flag) are decided; plan-review is done (below). Remaining open
questions #3 (git.commit variance vs. refuse) and #4 (large-set cap) can be
settled during implementation without blocking the shape. On approval:
implement (parity test first), validate, sync docs, move to
`.agents/plans/executed/`.

## Plan-review revisions (2026-07-06)

Verdict: **APPROVE WITH REVISIONS APPLIED**. Reviewed against the actual code
(`__main__.py` `_run_methods`, `_get_manifest_path`, the `show`/`report`
dispatch; `report/methods.py` `generate_report`; `status.py` `scan_runs`/
`filter_runs`). The approach (option C, explicit flag) is sound; no re-plan.
Revisions:

- **PR-M1 (MEDIUM, rubric H — consistency):** verified `pubrun show` already
  auto-iterates a many-run filter with NO flag (`__main__.py:1387-1408`).
  Choosing an explicit `--aggregate` flag for `methods` is a deliberate
  divergence from `show`; added a cross-command consistency note requiring it be
  documented in `docs/cli.md` (or, if auto-aggregation is chosen instead, called
  out as a behavior change in CHANGELOG).
- **PR-M2 (LOW, accuracy):** the "reuse scan_runs+filter_runs" description
  understated that the exact plumbing already exists — `_get_manifest_path` does
  `scan_runs`+`filter_runs(limit=1)` and `show` already loops the matched set.
  Added a precedent note pointing the executor at that seam (drop `limit=1`,
  collect the full set).
- **PR-M3 (LOW, rubric D/F):** sharpened the parity requirement — write the
  characterization test FIRST, assert byte-identical output for default AND
  filtered single-run methods, and that `--aggregate` over one run collapses to
  the single-run text.
- **PR-M4 (LOW):** removed the stale "settle #1/#2 then plan-review" from the gate
  (#1/#2 are decided and this is the plan-review pass).

Left open by design (do not block the shape): #3 (differing git.commit — note vs.
refuse) and #4 (large-set cap/warn threshold), to be settled at implementation.
