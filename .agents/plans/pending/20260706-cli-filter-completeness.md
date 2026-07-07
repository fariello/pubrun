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
2. **Resolve the `combined -f` collision.** Choose ONE (open question, recommend option a):
   - (a) Keep `combined`'s `-f` = `--force` (backward compatible) and simply document that
     `combined` uses `--filter` (long form) for filtering. Add a one-line note in help.
     Lowest risk, but `-f` remains inconsistent across commands.
   - (b) Rename `combined`'s force flag to `--force` (long only) / a different short (e.g.
     none), freeing `-f` to mean `--filter` like everywhere else. More consistent, but a
     breaking change to `combined -f` semantics — needs a deprecation note in CHANGELOG.
   Whichever is chosen, the outcome must be documented and tested so `-f` behavior on
   `combined` is unambiguous.
3. **Audit `clean`'s `-f`.** Confirm `clean` (no pre-existing `-f`) gets both `-f` and
   `--filter` (the audit found it does). Add a test pinning this so a future flag addition
   to `clean` cannot silently steal `-f` the way `combined` did.

## Anti-regression / invariants

- **`diff` default behavior unchanged** when called with no filters/positionals (still
  auto-pairs the last two valid runs). Characterization test BEFORE the change, green after.
- **No other command's flags change** (only `diff` gains flags; `combined` force/filter
  clarified per the chosen option).
- **`-f` semantics documented and tested** on every filter-capable command, especially
  `combined` and `clean`.
- Filtering still routes through the shared helper — no new ad hoc filter code (remove
  `diff`'s hand-rolled selection in favor of the shared `filter_runs`).

## Required tests / validation

- `diff -f <query>` restricts the auto-paired candidates; `diff` with no args reproduces
  today's output (characterization).
- `combined`: assert the chosen `-f` semantics (force or filter) explicitly, plus `--filter`
  works; add the trap regression test (`combined -f X` behaves as documented, not silently).
- `clean`: assert `-f` maps to `--filter`.
- CLI help for `diff`/`combined` reflects reality.
- Full suite green (baseline 690 passed; known SIGPIPE flake excepted).

## Spec / documentation sync

`docs/cli.md` (`diff`, `combined` flag tables), `CHANGELOG.md`. Run `/assess documentation`.

## Open questions (maintainer)

1. `combined -f` collision: option (a) keep `-f`=force + document, or (b) free `-f` for
   filter (breaking change, deprecation note)? (Recommend (a) — least surprise for existing
   `combined` users; the inconsistency is documented rather than a silent breakage.)
2. Should `ui/tui/gui` optionally accept `-f`/`-s` to PRE-SEED the dashboard filter? (Nice-
   to-have, not a correctness gap since the TUI filters interactively. Recommend: defer.)

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.
