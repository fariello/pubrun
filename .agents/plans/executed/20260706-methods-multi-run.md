# IPD: `pubrun methods` over many runs (aggregate / multi-run methods text)

- Date: 2026-07-06
- Concern: functionality / UX (a real design decision, not a mechanical change)
- Scope: how `pubrun methods` should behave when pointed at, or filtered to,
  MANY runs (100+ is common, e.g. `~/VC/uri-ai-info` has 1600+). Today it emits
  one Computational Methods paragraph from exactly one run.
- Status: EXECUTED (2026-07-06). `pubrun methods --all` implemented (option C:
  representative paragraph + variance note via `generate_report_multi`;
  single-run parity preserved — the of-one path is byte-identical). Reuses the
  existing run-filter args (`-n` enabled via `include_limit=True`; `-f`/`-F`/`-s`/
  `-S` bound/curate); differing git commit noted as variance; non-methods "narrow
  it"/skip note on stderr with an authoritative textual marker + optional CYAN
  (never DIM), suppressed under NO_COLOR. 12 tests. Full suite: 686 passed, 2
  skipped, 1 known-flaky. Docs (cli.md) + CHANGELOG synced.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Decisions (maintainer, 2026-07-06)

- **Representation: option (C)** — one representative paragraph + a compact
  variance note. When the selected runs are environment-homogeneous the output
  reads exactly like today's single-run methods; when they diverge, a short note
  discloses which fields varied and how. (Confirmed.)
- **Trigger: explicit flag `--all`** (`pubrun methods --all`), preserving the
  current single-run default of a bare/filtered `pubrun methods` (most-recent
  wins). Confirmed 2026-07-06.
- **Differing `git.commit` across the set: NOTE as variance, do NOT refuse.**
  Consistent with option (C): the aggregate paragraph discloses that runs span
  multiple commits (e.g. "across N runs spanning commits `abc1234`..`def5678`",
  or lists the distinct commits) rather than blocking. Long projects legitimately
  span many commits. Confirmed 2026-07-06.
- **No hard cap on set size, but add run-selection + a non-methods suggestion.**
  Confirmed 2026-07-06 (expands the original "cap?" question — see
  "Run selection and large sets" below). Aggregate however many match, state
  "across N runs", and:
  1. enable the **existing** run-filter args for `methods` (call
     `_add_run_filter_args(..., include_limit=True)`) so `-n`/`-f`/`-F`/`-s`/`-S`
     bound and curate the set — no NEW include/exclude flags (they would
     duplicate `-f`/`-F`; see "Run selection and large sets"), and
  2. when the set is large or divergent, print a suggestion **after** the methods
     paragraph, **clearly marked as NOT part of the methods text** (e.g. a
     `# note (not part of the methods section):` line to stderr or a fenced
     aside), e.g. suggesting a tighter filter or `-n`.

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
   unless the flag is given. RESOLVED: flag = `--all` (2026-07-06).

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
- Use `--all` as the aggregate trigger flag; `git.commit` is treated as a
  variance field (noted, never a refusal).

## Run selection and large sets (resolved 2026-07-06)

`--all` aggregates the full filtered set with **no hard cap**, but the user must
be able to bound and curate it, and the output must never silently imply a cap:

- **Bounding / curation — REUSE the existing run-filter args; do NOT add new
  include/exclude flags.** Verified against `_add_run_filter_args`
  (`__main__.py`) and `filter_runs` (`status.py:348`): the `methods` subcommand
  already gets, via `_add_run_filter_args`, a full include/exclude/bound surface —
  it just currently passes `include_limit=False`. So:
  - `-n <N>` / `--limit <N>` — **already implemented** in `_add_run_filter_args`
    and honored by `filter_runs(limit=...)`; simply call
    `_add_run_filter_args(methods_parser, include_limit=True)` to enable it for
    aggregate mode (it is off today).
  - **Include** = the existing `-f/--filter` (matches script, args, **or run_id**,
    regex or plain — so `-f "id1|id2|id3"` selects specific runs). **Exclude** =
    the existing `-F/--not-filter`. Status include/exclude = `-s`/`-S`. These
    already back the single-run path and need no new flags.
  - **Over-scope avoided (plan-review):** a dedicated `--include`/`--exclude`
    flag pair was considered and **rejected** — it would duplicate `-f`/`-F`. The
    only thing `-f`/`-F` do not do *first-class* is take an explicit multi-run-ID
    list as separate tokens, but the regex form (`-f "id1|id2"`) covers it; a
    first-class multi-ID selector, if ever wanted, is a separate later decision,
    not v1 scope (KISS).
- **Non-methods suggestion in output.** When the set is large and/or divergent,
  print a suggestion AFTER the methods paragraph that is **clearly marked as NOT
  part of the methods section** — so it can never be copied into a paper as
  methods text. E.g. a trailing block prefixed like
  `# pubrun note (not part of the methods section): aggregated N runs; N is large
  / the environment varied — consider narrowing with -f / -F / -n.` Emit it to
  stderr, or as an obviously-fenced aside on stdout that the "captured methods"
  boundary excludes. The methods paragraph itself must remain clean and
  paste-ready.
  - **The textual/structural marker is the AUTHORITATIVE, accessible signal.**
    The labeled line (`# pubrun note (not part of the methods section): ...`),
    plus keeping the note outside the methods paragraph, is what conveys the
    boundary. It works with `NO_COLOR`/`--no-color`, when piped to a file, for
    screen readers, and on any terminal theme. A test asserts the note carries
    the textual marker with `NO_COLOR` set, and that the paste-ready methods text
    excludes it.
  - **Color is OPTIONAL reinforcement only — and must NOT use `DIM`/faint.**
    WCAG 2.1 AA (1.4.3) requires a measurable ≥ 4.5:1 text/background contrast;
    `DIM` (ANSI SGR 2) *reduces* the foreground toward the background by an
    amount the terminal emulator decides, so the resulting ratio is both
    unknowable at authoring time and frequently below 4.5:1 — it is the exact
    low-contrast pattern the criterion exists to catch. Do NOT dim the note. If
    color is used, use a **distinct full-strength color** (e.g. the codebase's
    existing `YELLOW`/`CYAN` note/warning colors via `_has_color()`), gated on
    `NO_COLOR`. Because pubrun does not control the user's terminal theme, the
    plan/docs must **not claim a specific contrast ratio** for colored terminal
    output; color is decoration, the text marker is the compliant signal. (ADA
    ≈ WCAG 2.1 AA in practice, so the same reasoning applies.)
- Still **state "across N runs"** inside the methods text itself (that IS
  legitimate methods content); the *suggestion* about narrowing is the part that
  must be marked non-methods.

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
- `-n <N>` bounds the aggregated set; the existing `-f`/`-F` (and `-s`/`-S`)
  curate it — verify with those flags, not new ones.
- The "narrow the set" suggestion is emitted OUTSIDE the methods paragraph and is
  clearly marked non-methods via a textual marker (a test asserts the paste-ready
  methods text does not contain the suggestion, and that the marker is present
  under `NO_COLOR`/`--no-color`). Optional color reinforcement is a distinct
  full-strength color, **never `DIM`** (WCAG 2.1 AA: DIM's contrast ratio is
  unknowable/likely-failing against an arbitrary terminal theme).
- Full suite green.

## Spec / documentation sync

`docs/cli.md` (`methods` flags), `docs/api.md` (if a public generator is added),
README if it shows `methods` usage, `CHANGELOG`. Run `/assess documentation`.

## Open questions — ALL RESOLVED (maintainer, 2026-07-06)

1. Representation → **(C) representative + variance note.**
2. Trigger → **explicit `--all` flag** (single-run stays the default).
3. Differing `git.commit` → **note as variance, do not refuse.**
4. Large sets → **no hard cap;** enable the EXISTING run-filter args for
   `methods` (`-n` via `include_limit=True`, plus `-f`/`-F`/`-s`/`-S`) to bound
   and curate — no new include/exclude flags — and a clearly-marked non-methods
   "narrow it" suggestion after the paragraph (see "Run selection and large
   sets").

No open flag-design detail remains: run selection reuses the existing shared
run-filter args; only `include_limit` flips on. Not blocking.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution and is NOT auto-executed. All design questions are resolved; plan-review
is done (below). On approval: implement (parity test first), validate, sync docs,
move to `.agents/plans/executed/`.

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

Left open by design at the time of Plan-review 1 (do not block the shape): #3
(differing git.commit) and #4 (large-set cap/warn threshold). **Both later
resolved** by the maintainer (2026-07-06) — see "Open questions — ALL RESOLVED"
and "Plan-review 2".

## Decisions recorded (maintainer, 2026-07-06)

All open questions resolved (see the "Decisions" and "Open questions — ALL
RESOLVED" sections): representation (C), trigger flag `--all`, git.commit noted
as variance, no hard cap + reuse the existing run-filter args (`-n`/`-f`/`-F`/
`-s`/`-S`) for selection + a non-methods "narrow it" suggestion. The suggestion's boundary is conveyed by an **authoritative
textual/structural marker** (works under `--no-color`/`NO_COLOR`, in pipes, and
for screen readers); optional color reinforcement uses a distinct full-strength
color via the existing `_has_color()` mechanism and **must not use `DIM`** —
`DIM`/faint is not reliably WCAG 2.1 AA (its contrast against an arbitrary
terminal theme is unknowable and often below the 4.5:1 minimum), and pubrun does
not control the terminal theme, so no specific contrast ratio is claimed. Run
selection reuses the existing shared run-filter args (only `include_limit` flips
on for `methods`); no new selection flags are added. Ready for approval to
execute.

## Plan-review 2 (2026-07-06, post-decisions)

Verdict: **APPROVE WITH REVISIONS APPLIED**. Re-reviewed the material added after
Plan-review 1 (the `--all`/git-commit decisions and the new run-selection +
non-methods-note surface), verified against `_add_run_filter_args` and
`filter_runs` (`status.py:348`).

- **PR3-M1 (MEDIUM, over-scope / rubric G):** the proposed NEW `--include`/
  `--exclude` run-selection flags duplicate the existing `-f/--filter` (include;
  matches run_id, so `-f "id1|id2"` selects specific runs) and `-F/--not-filter`
  (exclude), plus `-s`/`-S` for status. Removed them; the plan now reuses the
  existing shared run-filter args and only flips `include_limit=True` so `methods`
  gains `-n`. A first-class multi-run-ID selector is a separate, later decision if
  ever needed (KISS).
- **PR3-M2 (LOW, accuracy):** confirmed `-n/--limit` already exists in
  `_add_run_filter_args` and is honored by `filter_runs(limit=...)`; the only
  change is enabling it for `methods` (currently `include_limit=False`).
- **PR3-M3 (LOW, testing/F):** the run-selection tests should exercise the
  existing `-f`/`-F`/`-n` flags, not new ones.

Verified-correct (no change): the accessibility handling (authoritative textual
marker + non-`DIM` optional color, no claimed contrast ratio) is sound; the
`--all` trigger and git-commit-as-variance decisions are consistent with option
C; the single-run parity gate (write the test first) is intact. The design is now
free of the over-scoped flag pair and ready for execution on approval.
