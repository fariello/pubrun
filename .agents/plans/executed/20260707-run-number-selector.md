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

## The ambiguity to resolve (design crux) — RESOLVED (maintainer 2026-07-07)

**Decision: bare small integer = recency index, with a collision guard.** `pubrun show 2`
means "the 2nd most recent run". Run ids can be numeric-ish (timestamps, hashes), so a bare
integer *could* in principle also be a run-id prefix — but in practice a run id that is a
*pure small integer* is extremely unlikely. Therefore:

- A bare **pure-integer** argument (1..bound) is interpreted as a **recency index**.
- **Collision guard:** if that same integer ALSO exactly/prefix-matches an existing run id (the
  rare case), do NOT silently guess. Print a `[WARN ]` explaining the ambiguity ("`2` matches
  both the 2nd-most-recent run AND run id `2f9c…`") and REQUIRE disambiguation — either
  `--force`/an explicit flag to take the recency meaning, or an explicit longer id prefix / a
  prompt for interactive sessions. Non-interactive without the flag → clear error, no guess.
- Non-integer arguments resolve exactly as today (id-prefix → dir-substring → path); recency
  is only ever considered for a bare integer.

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
| 3 | E2 | Implement the **collision guard** (decided): bare pure-integer → recency index; if it ALSO matches a run id, emit `[WARN ]` + require `--force` (recency) or an explicit id/prompt; non-interactive without `--force` → clear error, never a silent guess. | `status.py`, `__main__.py` | Med | Recency index resolves for a bare int; a fabricated collision (a run whose id IS/starts-with that integer) triggers the WARN + refusal-without-`--force`; `--force` takes recency; non-integer args resolve exactly as today. |

## Deferred / out of scope (with reason)

| Finding ID | Rem. Risk | Axis | Reason | Later step |
|------------|-----------|------|--------|------------|
| bare-int syntax (if chosen) shadowing numeric ids | Med | Functionality | If plan-review finds bare-int too ambiguous for this repo's id formats, adopt the sigil syntax (unambiguous) instead — same resolver, safer syntax. Decide at plan-review, don't ship an ambiguous default. | Sigil syntax. |

## Scope check

- Over-scope: one shared resolver, not per-command bespoke logic (reduces drift). Not adding
  ranges/globs of runs (KISS) — single selection only.
- Under-scope: the selector was entirely missing; added uniformly.

## Required tests / validation

- **Characterization gate (anti-regression):** pin CURRENT `find_run`/`_get_manifest_path`
  resolution first — id-prefix match, dir-substring fallback, no-arg→latest — with tests, and
  keep them green after the resolver refactor. The selector must be ADDITIVE: existing
  id-prefix/path resolution behavior is unchanged (this is the invariant the ambiguity design
  protects). If the chosen syntax is bare-int, a test proves a run whose id starts with the
  selector digits still resolves the way it does today (per the documented precedence).
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

1. **Selector syntax — RESOLVED (maintainer 2026-07-07):** bare small integer = recency index,
   with a collision guard (`[WARN ]` + require `--force`/explicit disambiguation on the very
   unlikely event it also matches a numeric run id). See the design crux above.
2. **`status` recency column — RESOLVED (accepted lean):** yes — `status` prints a `#1/#2/…`
   recency index next to each run so the selector is discoverable.
3. **Override flag — RESOLVED (maintainer 2026-07-07):** reuse **`--force`** (consistent with
   `combined --force`) to force the recency interpretation on the rare collision. Upper bound:
   interpret only a small range (e.g. 1..999) as a recency index (larger integers fall through
   to id resolution). (Confirm exact bound at execution — minor.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.

## Execution record (2026-07-07)

Executed by opencode after human approval (IPD-E, fifth of the batch; after B/A/C/D).

- **Recency resolution in `find_run` (`status.py`) — additive:** a bare positive integer
  1..999 is a RECENCY INDEX (`1` = most recent, from `scan_runs`' most-recent-first order).
  The id-prefix and dir-substring paths are unchanged (existing `test_find_run_by_prefix`/
  `_returns_none_for_no_match` still pass — P6 characterization). Out-of-range index falls
  through to id/path resolution.
- **Collision guard refined during execution (better than the IPD's first sketch):** the
  initial design flagged a collision when a run id merely *started with* the digit — but
  pubrun ids are hex and commonly start with a digit, so that fired constantly (caught in
  smoke-testing: `status 3` wrongly collided with id `343468e7`). Corrected to fire ONLY when
  a run id is **exactly** the integer (`run_id == sel`) AND it is a different run than the
  recency Nth — i.e. genuinely "the run literally named 3 vs the 3rd most recent". This is
  practically impossible for real ids, so recency is unambiguous in practice. On a true
  collision, `AmbiguousRunSelectorError` is raised and the CLI prints a clear WARN pointing at
  the full-id/path escape (no `--force` flag added — maintainer decision; the escape hatch is
  giving a longer id or the path, which already works everywhere).
- **CLI wiring:** `_get_manifest_path` (covers show/report/res/cpu/mem/methods/inspect/rerun/
  diff) and `_run_status` catch `AmbiguousRunSelectorError` → `_emit_ambiguous_selector` (a
  clear `[WARN ]`). `--dir` is honored where the command has it (recency counts within the
  scanned dir). No signatures threaded — the logic lives in the shared `find_run`.
- **`status` `#` column:** `render_short_list` now shows a leading `#` recency index (from the
  full unfiltered set, so `#1` is always newest even when filtered) — the number shown is the
  number you pass.
- **Tests (`tests/test_status.py::TestRunRecencySelector`, +6):** recency 1..N; out-of-range →
  None; digit-prefix id does NOT block recency (`3` = 3rd, `3abc` = id); collision only on
  EXACT integer id (raises) + no-collision when the exact-id run IS the Nth; `--dir` honored.
- **Docs:** `docs/cli.md` "Selecting a run" table (recency / id-prefix / path) near the top;
  `CHANGELOG.md`.
- **Validation:** full suite **836 passed / 2 skipped / 1 failed** on py3.11.8 — the lone
  failure is the known SIGPIPE flake (passes in isolation). Existing 52 status tests green
  (the new `#` column did not break them).

## Plan-review record (2026-07-07)

Reviewed via `plan-review`. Verified `find_run` prefix→substring resolution (`status.py:582-601`),
`_get_manifest_path` (`__main__.py:62-136`), most-recent-first `scan_runs`, and that no numeric
selector exists. Verdict: **APPROVE WITH REVISIONS APPLIED.**
- **P6 (MEDIUM, anti-regression):** added a characterization gate pinning CURRENT id-prefix /
  dir-substring / no-arg→latest resolution before the resolver refactor; the selector must be
  purely ADDITIVE and existing id/path resolution unchanged. This is the invariant the
  ambiguity design (E2/OQ1) exists to protect.
The syntax crux (E-OQ1: sigil vs bare-int-with-fallback) is the key maintainer decision — the
Deferred table already routes an "ambiguous bare-int" outcome to the safe sigil syntax rather
than shipping an ambiguous default.
