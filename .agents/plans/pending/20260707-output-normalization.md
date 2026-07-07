# IPD-B: normalize CLI output prefixes/colors + alphabetize the help command list

- Date: 2026-07-07
- Concern: usability / consistency. pubrun's console output uses **8 inconsistent prefix
  styles** (`[*]`, `[OK]`, `[ERRO]`, `[WARN]`, `[WARNING]`, `[FAIL]`, lowercase `[warn]`/
  `[info]`, `[dry run]`) via **duplicated** helpers and scattered `print()`s, and the `-h`
  command list is in arbitrary insertion order. Both hurt first-impression polish and
  scannability.
- Scope: a new central output helper module (e.g. `src/pubrun/report/output.py` or
  `src/pubrun/_output.py`), migration of all call sites (`__main__.py`, `report/diagnostics.py`,
  `report/meta_snapshot.py`, `status.py`, `report/checks.py` finding markers), and the help
  ordering in `__main__.py`. Docs, tests.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

One consistent, accessible prefix vocabulary everywhere pubrun prints a status line, and an
alphabetized command list in `-h`. Consistency and non-DIM color (accessibility) over ad-hoc
styling.

## Project conventions discovered (Step 0)

- Principles: intuitive/self-documenting, honest, accessibility (**never rely on ANSI DIM**;
  color is optional reinforcement, must respect `NO_COLOR`; the textual marker is
  authoritative). KISS.
- Current prefixes (verified, file:line): `[ERRO]` (`__main__.py:16,18`; **duplicated** in
  `report/diagnostics.py:30,32`), `[WARN]` (`__main__.py:23,25,1712`), `[WARNING]`
  (`__main__.py:187,456`; `diagnostics.py:159`), `[*]` (`__main__.py:128,429,441,1708,1714`;
  `status.py:534`; `meta_snapshot.py:19`), `[OK]` (`__main__.py:43,485,486,1652,1750,1769,1770`;
  `meta_snapshot.py:58`), `[FAIL]` (`__main__.py:1747`), lowercase `[warn]`/`[info]`
  (`__main__.py:742,748`), `[dry run]` (`status.py:1121`).
- Color: raw ANSI SGR; `NO_COLOR` checked in several places; `--no-color` sets
  `os.environ["NO_COLOR"]="1"` (`__main__.py:2274`). Findings additionally gate on
  `sys.stdout.isatty()`. Two separate `Colors` classes (`diagnostics.py`, `render.py`).
- Help: subparsers added in insertion order (`__main__.py:1929+`); argparse preserves it; the
  list is NOT alphabetical.

## Design decisions (maintainer-confirmed 2026-07-07)

- **Canonical prefixes (fixed 6-char bracket, left-aligned label):**
  `[INFO ]` (green), `[WARN ]` (yellow), `[ERROR]` (red), `[DEBUG]` (light blue / bright cyan),
  `[ OK  ]` (green). Textual label is authoritative; color is optional reinforcement, **never
  DIM**, suppressed under `NO_COLOR` / `--no-color` / non-TTY.
- **One central helper module** (no duplication): `info()/warn()/error()/debug()/ok()` (and a
  low-level `emit(level, msg)`), each writing to the right stream (errors/warnings→stderr;
  info/ok→stderr for status chatter so stdout stays clean for data, matching current
  behavior). Reused by every subsystem.
- **Alphabetize** the `-h` command list.

## Findings

| ID | Severity | Rem. Risk | Persona | Area | Finding | Evidence |
|----|----------|-----------|---------|------|---------|----------|
| B1 | Medium | Low | novice/eng | Consistency | 8 distinct prefix styles incl. `[WARN]` vs `[WARNING]` and lowercase `[warn]`/`[info]`. | see Step 0 |
| B2 | Medium | Low | eng | Maintainability | `_print_error` duplicated in two files; no central output module. | `__main__.py:14`, `diagnostics.py:28` |
| B3 | Low | Low | eng | Accessibility | color handling scattered; ensure single NO_COLOR/non-TTY gate + no DIM. | multiple |
| B4 | Low | Low | novice | Discoverability | `-h` command list not alphabetical. | `__main__.py:1929+` |

## Proposed changes (ordered, validatable)

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | B1,B2,B3 | Add a central `output` module: `emit(level,msg,stream=…)` + `info/warn/error/debug/ok` wrappers, with the canonical fixed-width prefixes and one color/NO_COLOR/isatty gate (no DIM). | new `src/pubrun/report/output.py` | Low | Unit test: each level emits the exact prefix; with `NO_COLOR=1` no ANSI; label present regardless. |
| 2 | B1,B2 | Migrate all call sites to the helper, replacing `[*]`→`info`, `[OK]`→`ok`, `[ERRO]`/`_print_error`→`error`, `[WARN]`/`[WARNING]`→`warn`, `[FAIL]`→`error` (or a distinct test-only marker), lowercase finding markers→`warn`/`info`. Remove the duplicated `_print_error`. `[dry run]` → `info` with a "(dry run)" suffix. | `__main__.py`, `diagnostics.py`, `meta_snapshot.py`, `status.py`, `checks.py` | Low | grep shows no `[*]`/`[ERRO]`/`[WARNING]`/`[warn]`/`[info]`/`[FAIL]` prefixes remain (only the 5 canonical); suite green. |
| 3 | B4 | Sort the subcommand list shown in `-h` alphabetically (sort the choices actions for display; keep dispatch unaffected). Hidden aliases (`report`, `resources`, …) stay hidden. | `__main__.py` | Low | `pubrun -h` command list is alphabetical; every command still dispatches; hidden aliases absent from help. |

## Deferred / out of scope (with reason)

None deferred on risk. Note: migrating output is mechanical but broad — done fully (Fix Bar),
not partially, since a half-migration would leave the very inconsistency we are fixing.

## Scope check

- Over-scope: NOT introducing a logging framework or dependency (KISS) — a ~40-line stdlib
  helper. NOT changing WHICH messages print, only their prefix/format/stream-consistency.
- Under-scope: previously no central helper; this adds the missing seam.

## Required tests / validation

- Output helper: prefix exactness per level; `NO_COLOR`/non-TTY suppresses ANSI but keeps the
  textual label; DEBUG only emitted when a debug/verbose flag is set (define the gate).
- Migration: grep-based test (or a scan test) asserting no legacy prefix strings remain in
  `src/pubrun`.
- Streams: errors/warnings go to stderr (existing tests that capture stderr still pass).
- Help ordering: a test parses `pubrun -h` and asserts the visible command list is sorted.
- Full suite green (several existing tests assert on `[ERRO]`/`[OK]`/`[*]` text — update them
  to the canonical prefixes as part of this change; that is expected, not a regression).

## Spec / documentation sync

`docs/cli.md` (a short "Output conventions" note: the 5 prefixes + NO_COLOR), `CHANGELOG.md`
(cosmetic but user-visible: prefix normalization; note the renamed prefixes for anyone
grepping pubrun output in scripts — recommend matching on the level word, not the brackets).

## Open questions

1. DEBUG gating: only under an existing verbose/`PUBRUN_DEBUG` flag? (Leaning: yes — DEBUG is
   silent unless explicitly enabled, so normal output is unchanged apart from prefix glyphs.)
2. Do any downstream scripts grep pubrun output for `[OK]`/`[*]`? (Assumption: no stable
   contract on these; documenting the change in CHANGELOG is sufficient.)
3. `[FAIL]` in the built-in self-test (`--run-tests`) — map to `[ERROR]` or keep a distinct
   `[FAIL ]` for test results? (Leaning: keep test pass/fail semantics distinct from log
   ERROR to avoid confusing a failed *check* with a logged error.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.
