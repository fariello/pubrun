# IPD-E: numeric "Nth most recent" run selector everywhere a run id is accepted

- Date: 2026-07-07
- Concern: usability. Selecting a run currently requires an id-prefix, a dir-name substring,
  or a full path. There is no ergonomic "the 2nd most recent run" selector. Users want a
  1-based recency index: `1` = most recent, `2` = second most recent, … in the current (or
  `--dir`-specified) output directory, usable everywhere a run id is accepted.
- Scope: the run-resolution seam — `find_run` (`src/pubrun/status.py:582`) and/or
  `_get_manifest_path` (`src/pubrun/__main__.py:62`), plus every command that resolves a run
  (`report`/`show`, `res`/`cpu`/`mem`, `methods`, `inspect`, `rerun`, `diff`, `status`). Docs,
  tests. No runtime/capture change.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Let a user pass a small positive integer as a run selector meaning "Nth most recent", working
identically across all run-accepting commands and honoring `--dir`.

## Project conventions discovered (Step 0)

- `find_run(id_or_prefix, output_dir)` (`status.py:582-601`): (1) prefix match on `run_id`;
  (2) fallback dir-name substring; single-match-or-None.
- `_get_manifest_path(run_dir, …)` (`__main__.py:62-136`): calls `find_run` first, else treats
  the arg as a path; no arg → latest via `scan_runs` + `filter_runs(limit=1)`. `scan_runs`
  sorts most-recent-first (`status.py:551,577`).
- Consumers: `_run_report` (`:543`), `_run_resources` (`:516`), `_run_methods` (`:170`),
  `_run_inspect` (`:800`), `_run_rerun`, `_run_diff` (`find_run` `:413`, `_get_manifest_path`
  `:443`), `status <id>`.
- **No numeric Nth-most-recent selector exists.** `-n/--limit` only truncates a list; it does
  not select the Nth item.

## The ambiguity to resolve (design crux)

Run ids can themselves be numeric-ish (timestamps, hashes). A bare `3` must not accidentally
match a run id that *starts with* `3`. Decision needed on the selector SYNTAX so it is
unambiguous and predictable (see Open Q1). Options:
- **(a) Bare small integer** (`report 2`): treat a pure-integer arg ≤ some bound as a recency
  index, BUT only if it does not exactly/prefix match an existing run id (fall back to id
  match). Most ergonomic, slight ambiguity risk.
- **(b) Sigil prefix** (`report ^2` or `report @2` or `report -2`): explicit "Nth recent";
  never collides with an id. Unambiguous, slightly less discoverable.
- **(c) Bare integer, recency-FIRST** (`report 2` always = 2nd recent; ids must be non-pure-
  integer or use a longer prefix): simplest mental model, but could shadow a genuinely numeric
  id.

## Findings

| ID | Severity | Rem. Risk | Persona | Area | Finding | Evidence |
|----|----------|-----------|---------|------|---------|----------|
| E1 | Medium | Low-Med | novice/eng | Usability | No "Nth most recent" run selector; users must copy an id/prefix or path. | `status.py:582`; `__main__.py:62` |
| E2 | Medium | Med | eng | Correctness | Any selector syntax must not silently mis-resolve a numeric-looking run id (ambiguity). | id formats |

## Proposed changes (ordered, validatable)

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | E1,E2 | Add a single resolver `resolve_run_selector(sel, output_dir)` that centralizes: recency-index (per chosen syntax) → id-prefix → dir substring → path. It sorts via the existing `scan_runs` (most-recent-first) and returns the run dir or a CLEAR error (`"no 3rd most recent run; only 2 runs in ./runs"`). | `status.py` | Low-Med | Given 3 runs, selector "2" (per chosen syntax) resolves the 2nd-newest; out-of-range → clear error; ambiguous id still errors as today. |
| 2 | E1 | Route ALL run-accepting commands through the resolver (replace direct `find_run`/`_get_manifest_path` id handling with it), honoring `--dir`. | `__main__.py` (all consumers) | Low | Each of report/show/res/cpu/mem/methods/inspect/rerun/diff/status accepts the recency selector and `--dir`; a table test covers each command. |
| 3 | E2 | Implement the DISAMBIGUATION per Open Q1 decision (sigil vs bare-int-with-fallback), with a documented, tested precedence so a numeric id is never mis-resolved. | `status.py` | Med | A run whose id starts with the selector digits still resolves by id (or per the documented precedence); tests pin both directions. |

## Deferred / out of scope (with reason)

| Finding ID | Rem. Risk | Axis | Reason | Later step |
|------------|-----------|------|--------|------------|
| bare-int syntax (if chosen) shadowing numeric ids | Med | Functionality | If plan-review finds bare-int too ambiguous for this repo's id formats, adopt the sigil syntax (unambiguous) instead — same resolver, safer syntax. Decide at plan-review, don't ship an ambiguous default. | Sigil syntax. |

## Scope check

- Over-scope: one shared resolver, not per-command bespoke logic (reduces drift). Not adding
  ranges/globs of runs (KISS) — single selection only.
- Under-scope: the selector was entirely missing; added uniformly.

## Required tests / validation

- Recency resolution: N-run fixture; selector 1..N resolves newest..oldest; N+1 → clear error.
- `--dir` honored: selector resolves within the specified dir, not cwd.
- Disambiguation: numeric-looking id not mis-resolved (both precedence directions pinned).
- Every run-accepting command accepts the selector (parametrized test across commands).
- Empty dir / no runs → clear error, no crash.
- Full suite green.

## Spec / documentation sync

`docs/cli.md` (a shared "Selecting a run" note: id-prefix | recency index | path, with the
chosen syntax + examples; referenced from each command), `CHANGELOG.md`.

## Open questions

1. **Selector syntax (the crux):** bare small integer with id-fallback, a sigil (`^N`/`@N`),
   or recency-first bare integer? (Leaning: a sigil like `^N` for zero ambiguity + a bare
   small-int convenience that falls back to id match — decide at plan-review with the repo's
   actual id formats in view.)
2. Should `status` (which lists runs) also print the recency index next to each run so the
   selector is discoverable? (Leaning: yes — show a `#1/#2/…` column.)
3. Upper bound on the bare-int interpretation (e.g. treat only 1–999 as indices)? (Leaning:
   yes, small bound, if bare-int is chosen.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.
