# IPD-A: `pubrun diff` usability — meaningful `--basic`, redundant-field collapse, optional table

- Date: 2026-07-07
- Concern: usability / correctness of the semantic diff. `pubrun diff --basic` is far noisier
  than "basic" implies — on subprocess-heavy runs it produces 11,000+ lines, and it surfaces
  redundant/volatile fields (`invocation.command_line`, `invocation.rerun_command`,
  `filesystem.run_dir.path`) that restate a single real difference (`invocation.argv`).
- Scope: `src/pubrun/resources/default.toml` (`[diff]` ignore lists), `src/pubrun/analysis/diff.py`
  (normalization / redundant-field collapse), optionally `src/pubrun/analysis/render.py` (a
  compact/table rendering mode), docs, tests. No change to `import pubrun` runtime.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Make `--basic` genuinely basic (a short, human-scannable summary of the *meaningful*
differences), stop restating one logical change as several fields, and cap pathological
blow-ups from list-valued sections. Preserve `--deep` as the show-everything mode.

## Project conventions discovered (Step 0)

- Principles: KISS, honest output, don't overwhelm the user. Lifecycle: `.agents/plans/`
  pending→executed; dated IPDs.
- Diff engine: `_run_diff` (`__main__.py:370`) → `analysis/diff.py` (`compare_manifests`,
  `_normalize_manifest`, `_should_ignore` at `:33-40`) → `analysis/render.py` (`print_diff`
  → `_render_inline`, "git-style" `+/-/~` lines; **no table renderer has ever existed** — git
  history confirms).
- Depth→ignore-list mapping: `__main__.py:460-465`; lists in `default.toml:399-413`.
- **Root cause (verified):** `ignore_basic` = `["timing","run","process","hardware","resources",
  "capture","environment","*_utc","*_utc.*"]`. It does NOT ignore `invocation`, `filesystem`,
  `subprocesses`, or `packages`. `_normalize_manifest` flattens lists element-by-element
  (`diff.py:80-94`), so a run with N subprocesses becomes ~4N leaf keys; diffing two
  subprocess-heavy runs yields thousands of change lines (measured: one real run = 2,480
  subprocess keys). `default` CLI level is `--standard`.

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| A1 | High | Low | novice/eng | Usability | `--basic` shows `invocation.command_line` + `invocation.rerun_command`, which are derivable from `invocation.argv`; a lone `argv` change is reported 3×. | `default.toml:399-402`; manifest `invocation.*` |
| A2 | High | Low | eng | Usability | `--basic` shows `filesystem.run_dir.path` (always differs run-to-run; pure noise). | `default.toml:399-402` |
| A3 | High | Low | novice/eng | Usability | `--basic` deep-diffs `subprocesses` and `packages` list elements → 11,000+ lines on real runs; not "basic". | `diff.py:80-94`; measured |
| A4 | Medium | Low | eng | Consistency | `ignore_basic` and `ignore_standard` are independent hand-maintained lists; basic ignores *fewer* specific keys than standard in places (inverted expectation). | `default.toml:399-411` |
| A5 | Medium | Med | eng | Usability | No compact/table rendering; even a clean diff is a vertical `+/-/~` list. (A table was never implemented; user recalls one from a predecessor tool.) | `render.py:1-3,73-135` |

## Proposed changes (ordered, validatable)

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | A1 | **Collapse redundant invocation fields.** In `_normalize_manifest`, when `invocation.argv` is present, DROP `invocation.command_line` and `invocation.rerun_command` from `basic`/`standard` (they are derived views of argv); keep them only at `--deep`. Alternatively add them to `ignore_basic`+`ignore_standard`. Prefer the argv-aware collapse so they show at deep. | `diff.py`, `default.toml` | Low | A run pair differing only by an added argv flag shows ONE `invocation.argv` change at basic (not 3); `--deep` still shows all three. |
| 2 | A2 | Add `filesystem.run_dir`, `filesystem.*.path`, `filesystem.*.mount_point` (volatile absolute paths) to `ignore_basic` + `ignore_standard`; keep `fstype`/`is_network` visible (those are meaningful). | `default.toml` | Low | Basic diff of two runs on the same fs shows no `run_dir.path` line; an NFS-vs-local difference still shows via `fstype`. |
| 3 | A3, A4 | **Make `--basic` list-aware and genuinely summarizing.** Add `subprocesses` and `packages` to `ignore_basic` (basic = "did the script/env/user-facing config change?", not "every child process"). At `--standard`, summarize list-valued sections as a COUNT + added/removed identities rather than per-element leaf diffs (e.g. "subprocesses: 618 → 620 (+2 added: …)"). `--deep` keeps full element-by-element. Rebuild the ignore lists so basic ⊇ standard ⊇ deep in what-they-hide (basic hides the most). **Integrate with (do not duplicate) the EXISTING depth-aware array handling** (`_recruit_val`, `diff.py:80-94`, added in commit `eca6117`) — the summarization is a `--standard` presentation over the same normalized data, not a second array code path. | `diff.py`, `default.toml` | Med | A subprocess-heavy run pair at `--basic` is < ~40 lines; at `--standard` shows subprocess/package COUNT deltas + identities, not thousands of leaves; `--deep` unchanged (full detail). Add a test with two synthetic manifests each having 300 subprocesses: basic output line count is bounded. A regression test asserts existing depth-aware array formatting still works at `--deep`. |
| 4 | A5 | **Optional compact/table rendering** for the summary: a `--table` (or make it the default for basic/standard) two-column "Field | A → B" aligned view, ANSI-colored, NO_COLOR/`--no-color` aware, degrading to the current inline form with `--wrap`/narrow terminals. Keep `_render_inline` available. | `render.py`, `__main__.py` | Med | Table renders aligned columns, wraps safely at small widths, and is byte-identical in content to the inline form (same change set). Manual + a width-parametrized test. |

## Deferred / out of scope (with reason)

| Finding ID | Rem. Risk | Axis | Reason | Later step |
|------------|-----------|------|--------|------------|
| A5 (table as *default*) | Med-High | Usability | Making the table the default for ALL depths could regress scripts/pipelines that parse the current `+/-/~` inline format. Propose table as opt-in (`--table`) or default only for basic/standard summary, inline preserved; revisit defaulting after user feedback. | Gather feedback, then consider defaulting. |

## Scope check

- Over-scope: not rewriting the diff engine; reusing `_normalize_manifest`/`_should_ignore`.
  The table is opt-in to avoid gold-plating + pipeline breakage.
- Under-scope: `--basic` was under-delivering (the core bug); this fills it.

## Required tests / validation

- **Characterization gate (anti-regression):** before changing the ignore lists / renderer,
  add a test that pins the CURRENT diff output for a fixed pair of sample manifests at each
  depth (`--basic`/`--standard`/`--deep`) — capture the exact change set. The change is a
  DELIBERATE behavior change, so the pinned expectations are then updated in the SAME commit
  to the new (quieter) output, with the diff of expectations visible in review. `--deep` output
  must be UNCHANGED by this IPD (deep hides nothing new); assert deep is byte-identical
  before/after.
- Redundant-collapse: manifests differing only in `argv` → basic shows 1 change, not 3;
  deep shows command_line/rerun_command too.
- Volatile paths: `run_dir.path` never in basic/standard; `fstype` diff still shown.
- Blow-up cap: two 300-subprocess manifests → basic output bounded (< ~40 lines); standard
  shows counts+identities; deep shows full.
- Ignore-list monotonicity: assert `set(ignore_deep) ⊆ set(ignore_standard-ish) ⊆ basic`
  in spirit (basic hides ≥ standard hides ≥ deep). A test encodes the invariant.
- Table renderer (if built): aligned, width-safe, content-equal to inline; NO_COLOR honored.
- Full suite green (clear `__pycache__` first).

## Spec / documentation sync

`docs/cli.md` (`diff` — what each depth hides now; `--table` if added), `CHANGELOG.md`.
Note the changed `--basic`/`--standard` output as a behavior change (scripts parsing diff
output at those depths may see fewer lines; `--deep` is unchanged).

## Open questions

1. **Table rendering — RESOLVED (maintainer 2026-07-07):** opt-in `--table`; the current
   `+/-/~` inline output stays the DEFAULT so nothing parsing it breaks. Revisit defaulting
   only after real-world feedback.
2. **List-summary identity — RESOLVED (accepted lean):** subprocess = `argv[0]` basename;
   package = `name@version`. (Confirm exact truncation at execution — minor.)
3. **command_line/rerun_command — RESOLVED (maintainer 2026-07-07):** COLLAPSE when
   `invocation.argv` is present (suppress the two derived views in basic/standard so one argv
   change = one line); `--deep` still shows all three.

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-07)

Reviewed via `plan-review`. Verified: `render.py` has only `_render_inline`/`print_diff` (no
table ever existed — `render.py:73,138`); `ignore_basic`/`ignore_standard` (`default.toml:399-411`);
`invocation` has `argv`/`command_line`/`rerun_command` (`capture/invocation.py`);
`_recruit_val` array flattening (`diff.py:80-94`). Verdict: **APPROVE WITH REVISIONS APPLIED.**
- **P1 (HIGH, anti-regression):** added a characterization gate — pin current per-depth diff
  output before the change, update expectations in the same commit, assert `--deep` byte-identical.
- **P2 (MEDIUM, functionality):** required the standard-level summarization to integrate with
  the EXISTING depth-aware array handling (`eca6117`), not add a second array code path; added a
  deep-array regression test.
No deferrals on risk. Open questions (table opt-in vs default, identity format, collapse-vs-ignore
of command_line/rerun_command) remain for execution-time/maintainer.
