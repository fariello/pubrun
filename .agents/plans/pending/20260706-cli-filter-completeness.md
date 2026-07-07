# IPD-D: CLI filter completeness — add filters to `diff`, resolve `combined -f` collision

- Date: 2026-07-06
- Concern: CLI consistency / usability. Ensure every subcommand that operates on a SET of
  runs offers the standard `-f/--filter` and `-F/--not-filter` (and the rest of the shared
  filter set), and that `-f` means the same thing everywhere.
- Scope: `src/pubrun/__main__.py` only (subparser wiring + `diff` run selection). No change
  to capture/runtime behavior. Small, low-risk.
- Status: PENDING — plan-review, then execution on human approval. NOT auto-executed.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

Verified audit (2026-07-06) of the shared helper `_add_run_filter_args`
(`__main__.py:1109-1122`, adds `-f/--filter`, `-F/--not-filter`, `-s/--status`,
`-S/--not-status`, `--older-than`, `--exit-code`, and optionally `-n/--limit`):

- **Filter-enabled today:** `clean`, `combined`, `cpu`, `mem`, `methods`, `report`,
  `rerun`, `res`, `show`, `status` — all via the helper (none ad hoc).
- **Correctly filter-free:** `init`, `cite`, `meta`, `run`, `ui/tui/gui`, `bug-report`.
- **Two real problems:**
  1. **`diff` has NO filter args at all** (`__main__.py:1305`, `_run_diff` at `:369`),
     yet it is set-oriented: it calls `scan_runs()` (`:378`), builds `valid_runs`, and
     auto-selects a pair. A user cannot say "diff the last two *matching* runs." It also
     hand-rolls selection instead of using the shared path — a consistency gap.
  2. **`combined`'s `-f` is `--force`, not `--filter`.** `combined` defines `-f/--force`
     (`__main__.py:1287`) BEFORE calling the helper (`:1288`); the helper's collision guard
     (`:1111-1112`) then registers only the long `--filter`. Net: on `combined`, `-f` =
     force. Every other filter-capable command has `-f` == `--filter`. This is a latent
     trap: `pubrun combined -f train.py` sets `--force` and treats `train.py` as a
     positional run id, silently NOT filtering.

(No command has `-f` without `-F`; the helper always adds both. `report` is a hidden
duplicate of `show`, both filter-enabled — noted, not changed here.)

## Project conventions discovered (Step 0)

- Principles: KISS, intuitive/self-documenting CLI, honest docs, no silent surprises.
- All filtering routes through `_add_run_filter_args` + `filter_runs` (`pubrun.status`).
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Proposed changes

1. **Add filters to `diff`.** Call `_add_run_filter_args(diff_parser, include_limit=False)`
   (single/pair selection, so no `-n`) and update `_run_diff` (`__main__.py:369`) to draw
   its auto-paired candidates from the FILTERED set (apply the same `filter_runs` inputs
   the other commands use) instead of raw `scan_runs()`. Positional `run_dirs` continue to
   override filters when given (explicit beats filter). Preserve current default behavior
   exactly when no filter/positional is supplied (anti-regression).
2. **Resolve the `combined -f` collision — DECIDED (maintainer 2026-07-06): option (b),
   hard switch in 1.4.0.** Make `combined`'s `-f` mean `--filter` like every other command;
   the force flag becomes **`--force` long-only** (drop its `-f` short). This is a
   **breaking change** to `combined -f` semantics (previously force). Rationale accepted:
   `combined` is a newer/less-used command; consistency across the CLI is worth it.
   Requirements:
   - Update `combined_parser` (`__main__.py:1287-1288`): remove `-f` from the force
     argument (keep `--force`), then call `_add_run_filter_args(combined_parser)` so the
     helper's collision guard no longer fires and `-f/--filter` is registered normally.
   - **CHANGELOG:** a clear `### Changed`/**BREAKING** entry under `[1.4.0]`:
     "`pubrun combined -f` now means `--filter` (was `--force`); use `--force` for force."
   - No deprecation-warning period (maintainer chose the clean hard switch, not warn-then-
     flip). Documented breakage only.
3. **Audit `clean`'s `-f`.** Confirm `clean` (no pre-existing `-f`) gets both `-f` and
   `--filter` (the audit found it does). Add a test pinning this so a future flag addition
   to `clean` cannot silently steal `-f` the way `combined` did.

## Anti-regression / invariants

- **`diff` default behavior unchanged** when called with no filters/positionals (still
  auto-pairs the last two valid runs). Characterization test BEFORE the change, green after.
- **Only `diff` and `combined` change** — `diff` gains filter flags; `combined -f` flips
  from force to filter (`--force` remains as long-only). No OTHER command's flags change.
  This is the one intentional breaking change; it must be in the CHANGELOG breaking note.
- **`-f` semantics documented and tested** on every filter-capable command, especially
  `combined` and `clean`.
- Filtering still routes through the shared helper — no new ad hoc filter code (remove
  `diff`'s hand-rolled selection in favor of the shared `filter_runs`).

## Required tests / validation

- `diff -f <query>` restricts the auto-paired candidates; `diff` with no args reproduces
  today's output (characterization).
- `combined`: assert `-f`/`--filter` now FILTERS (the new semantics), `--force` still
  forces, and there is no `-f` short for force. Regression test that `combined -f X`
  filters (does not force) — the intended behavior change.
- `clean`: assert `-f` maps to `--filter`.
- CLI help for `diff`/`combined` reflects reality.
- Full suite green (baseline 690 passed; known SIGPIPE flake excepted).

## Spec / documentation sync

`docs/cli.md` (`diff`, `combined` flag tables), `CHANGELOG.md`. Run `/assess documentation`.

## Open questions — ANSWERED by maintainer 2026-07-06

1. `combined -f` collision → **option (b), hard switch in 1.4.0** (`-f` = filter, `--force`
   long-only), documented as a breaking change in the CHANGELOG. No deprecation period.
2. `ui/tui/gui` pre-seed filter → **defer** (nice-to-have, TUI filters interactively).

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-06)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verdict: **APPROVE WITH
REVISIONS APPLIED**. Verified `_add_run_filter_args` (`__main__.py:1109-1122`), that
`combined` defines `-f/--force` then calls the helper (`__main__.py:1287-1288`, collision
guard fires), that `diff` has NO filter args and hand-rolls selection, and that `clean`
has no pre-existing `-f`. Maintainer chose the BREAKING change (option b): in 1.4.0
`combined -f` becomes `--filter`, force → `--force` long-only, hard switch (no deprecation
period), documented as a breaking change in the CHANGELOG (`[1.4.0]`). Note: pubrun is
already on PyPI, so the breaking note is required. `ui/tui/gui` pre-seed filter deferred.
Anti-regression: `diff` no-arg behavior must be characterization-pinned. Standalone;
smallest/lowest-risk of the five (aside from the intentional `combined` break).
