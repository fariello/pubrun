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
  `[INFO ]` (green), `[WARN ]` (yellow), `[ERROR]` (red), `[DEBUG]` (light blue), `[ OK  ]`
  (green). Textual label is authoritative; color is optional reinforcement, **never DIM**,
  suppressed under `NO_COLOR` / `--no-color` / non-TTY. **"Light blue" = bright cyan/blue
  (ANSI 96 or 94), NOT dim blue (34)** — plain blue on a dark terminal is low-contrast, which
  violates the accessibility principle; pick the bright variant and verify legibility on both
  dark and light backgrounds. INFO/OK share green — that is fine since the textual label
  disambiguates them (color is never the sole signal).
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

- **Pre-migration inventory (do first):** grep the WHOLE repo (`src/` AND `tests/`) for every
  legacy prefix (`[*]`, `[OK]`, `[ERRO]`, `[WARN]`, `[WARNING]`, `[FAIL]`, `[warn]`, `[info]`,
  `[dry run]`) to enumerate (a) all emit sites and (b) all TEST assertions that will need
  updating. This inventory is the change's scope-of-blast; it prevents a missed call site
  leaving the inconsistency, and a missed test assertion failing mysteriously.
- **Streams must be PRESERVED exactly.** The new helper must send each migrated message to the
  SAME stream (stdout/stderr) it used before — several tests capture a specific stream
  (`capsys.readouterr().err` vs `.out`). Changing a message's stream is a behavior change and
  is out of scope; assert the pre/post stream for each level in the helper's tests.
- Output helper: prefix exactness per level; `NO_COLOR`/non-TTY suppresses ANSI but keeps the
  textual label; DEBUG only emitted when a debug/verbose flag is set (define the gate).
- Migration: grep-based test (or a scan test) asserting no legacy prefix strings remain in
  `src/pubrun` (excluding the changelog note and any string that is intentionally not a prefix).
- Help ordering: a test parses `pubrun -h` and asserts the visible command list is sorted.
- Full suite green. Existing tests asserting `[ERRO]`/`[OK]`/`[*]`/`[warn]`/`[info]` text are
  updated to the canonical prefixes IN THE SAME COMMIT (expected, not a regression); the
  pre-migration inventory guarantees none are missed.

## Spec / documentation sync

`docs/cli.md` (a short "Output conventions" note: the 5 prefixes + NO_COLOR), `CHANGELOG.md`
(cosmetic but user-visible: prefix normalization; note the renamed prefixes for anyone
grepping pubrun output in scripts — recommend matching on the level word, not the brackets).

## Open questions

1. **DEBUG gating — RESOLVED (maintainer 2026-07-07):** DEBUG is silent unless explicitly
   enabled (`PUBRUN_DEBUG` env or a `--debug` flag). Normal output is unchanged apart from the
   prefix-glyph normalization; the `[DEBUG]` style is defined + consistent but never spams a
   normal run.
2. **Prefix as a script contract — RESOLVED (assumption accepted):** no stable contract on
   `[OK]`/`[*]` etc.; the CHANGELOG documents the normalization and recommends matching on the
   level word if anyone scrapes output.
3. **Self-test `[FAIL]` — RESOLVED (maintainer 2026-07-07):** keep a DISTINCT `[FAIL ]` (red)
   for `--run-tests` failures and `[ OK  ]` for passes — a failed test is not a logged runtime
   ERROR; `[ERROR]` stays reserved for actual error conditions.

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-07)

Reviewed via `plan-review`. Verified the 8 legacy prefix styles + duplicated `_print_error`
(`__main__.py:14`, `diagnostics.py:28`) and the insertion-ordered `-h` list. Verdict:
**APPROVE WITH REVISIONS APPLIED.**
- **P3 (HIGH, functionality):** added a mandatory pre-migration grep INVENTORY (src/ AND
  tests/) of every legacy prefix + all test assertions, and required that message STREAMS
  (stdout/stderr) be preserved exactly (several tests capture a specific stream); a
  stream change is out of scope.
- **P7 (LOW, accessibility):** pinned "light blue" to bright cyan/blue (ANSI 96/94), NOT dim
  blue (34), to satisfy the WCAG/non-DIM principle; noted INFO/OK sharing green is fine since
  the textual label is authoritative.
No deferrals on risk. Sequence this FIRST (its helper + prefixes are reused by IPD-D and the
diagnostic verbosity work).
