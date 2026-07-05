# IPD: Add a sixth import mode — "capture everything including console"

- Date: 2026-07-05
- Concern: functionality / API design (new public import mode)
- Scope: a new import-mode preset that, on a single import, captures everything
  pubrun can — including console streams (stdout/stderr), which no current mode
  turns on by default. New public API surface: a new `src/pubrun/<name>.py`
  submodule, a new `[imports].mode` value, a new `run --mode` choice, docs, tests.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Give users a one-import "turn everything on" option. Today, capturing console
output requires two things: a console-permitting mode (auto/noauto/noconsole)
AND setting `[console].capture_mode` to `"standard"` (it defaults to `"off"`).
There is no single import that yields full capture including the console tee.
The maintainer explicitly wants this. This IPD adds a sixth preset that
auto-starts, permits all hooks, AND defaults the console tee ON.

This is additive: the existing five modes (auto/noauto/nopatch/noconsole/
minimal) are unchanged. The maintainer confirmed those five are correct and
stable; this only adds a convenience preset on top.

## Project conventions discovered (Step 0)

- Modes are defined in `src/pubrun/_modes.py` as boolean behavior dicts
  (`auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`,
  `signal_hooks`) and surfaced as importable submodules `src/pubrun/<mode>.py`
  that call `select_mode(...)` then rebind the public API into the `pubrun`
  namespace. `VALID_MODES` and `_MODE_SUBMODULES` (in `_bootstrap.py`) enumerate
  the set; `run --mode` choices are hardcoded in `__main__.py`.
- **Key design gap for this feature:** mode behavior flags only *permit* hooks;
  they do NOT carry a `capture_mode` value. The console tee is
  `patch_console AND resolve_console_mode(config) != "off"` (tracker.py:317),
  and `capture_mode` defaults to `"off"` (console.py:35). So a "full" mode must
  ALSO change the effective `capture_mode` default to `"standard"` — a new
  mechanism, because today no mode influences config defaults.
- Guiding principles: KISS, honest docs, never crash the host, zero runtime
  deps. A sixth mode adds surface area, justified only by the real "capture
  everything incl. console" need.
- Plans: `.agents/plans/pending/` → `executed/`; `YYYYMMDD-<slug>.md`.
- Doc-sync discipline (AGENTS.md): update README matrix, api.md, cli.md,
  configuration.md, functional_spec.md, CHANGELOG on this behavior change.
- Just-fixed related item: all mode aliases now expose the full public API
  (commit on 2026-07-05); the new mode must do the same.

## Open design decisions (need maintainer input — see Open questions)

1. **Mode name.** Candidates: `full`, `deep`, `verbose`, `all`. Recommendation:
   `full` (clear, short, not overloaded — `deep` already names a capture depth
   in config, which would confuse).
2. **How the mode enables console** (the crux). Two viable approaches:
   - **(A) Mode carries a config-default overlay.** Extend the mode system so a
     mode can declare default config (e.g. `full` implies
     `console.capture_mode = "standard"` unless the user set it). Cleanest
     semantically; touches `_modes.py` + the boot config merge. Must preserve
     precedence: an explicit user `capture_mode` (config/env/`start()`) still
     wins over the mode default.
   - **(B) The `full` submodule sets `capture_mode` at import** (e.g. via an
     env/override applied before boot) if the user has not set one. Smaller
     change to the mode core, but the "only if user didn't set it" check is
     fiddly and risks surprising precedence. (A) is recommended.
3. **Should `full` also raise capture depth** (e.g. hardware `deep`, packages
   `full-environment`)? Recommendation: NO — keep `full` about *console being
   the missing piece*, not about maximizing every capture cost. "Everything on"
   should mean "all hooks + console," not "slowest possible." Revisit if the
   maintainer wants a separate max-cost preset.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Add the `full` behavior to `MODES`: `auto_start=True, global_hooks=True, patch_subprocesses=True, patch_console=True, signal_hooks=True` (same permits as `auto`). | `src/pubrun/_modes.py` | Low | `get_mode_behavior("full")` returns the expected dict; `VALID_MODES` includes it. |
| 2 | Implement the console-default mechanism (decision #2, recommend A): let the selected mode contribute a config default so `full` yields effective `capture_mode="standard"` UNLESS the user explicitly set `[console].capture_mode` (config/env/`start()` override still wins). Thread the mode default into `resolve_console_mode`/config resolution without breaking the other five modes. | `_modes.py`, `config.py`/`tracker.py`/`console.py` (minimal touch) | **Medium** (functionality: precedence must be exactly right; risk of the mode default shadowing an explicit user setting) | Tests: `full` with no console config → tee active (`standard`); `full` + explicit `capture_mode="off"` → tee OFF (user wins); other modes unaffected (console still off by default). |
| 3 | Add `src/pubrun/full.py` submodule mirroring the others: `select_mode("full", ...)`, import + rebind the FULL public API (all 12 names — matching the parity fix), auto-start boot. | `src/pubrun/full.py` | Low | `import pubrun.full as pubrun` exposes all 12 names (extend `TestModeAliasApiParity` to include `full`); auto-starts. |
| 4 | Register `full` in the submodule set and CLI: add to `_MODE_SUBMODULES` (`_bootstrap.py`) and to the `run --mode` choices (`__main__.py`). | `_bootstrap.py`, `__main__.py` | Low | `pubrun run --mode full -- python script.py` runs and the child wraps console; `--help` lists `full`. |
| 5 | Legacy mapping: decide whether `full` needs a `(auto_start, global_hooks)` legacy tuple. It collides with `auto`'s `(True,True)`, so `full` is NOT representable by the legacy two-bool mapping — document that `full` is only selectable by explicit name (`[imports].mode="full"`, env, `--mode`, or the submodule), not via `auto_start`/`global_hooks` bools. | `_modes.py` (comment), docs | Low | `resolve_mode_name` unchanged; docs note the limitation. |
| 6 | Docs: add `full` to the README Preset Modes matrix (Console column = ✅ **on by default**, the distinguishing feature), the import-mode code blocks, `api.md`, `cli.md` `--mode`, `configuration.md` `[imports].mode`, `functional_spec.md` matrix. Explain it = `auto` + console tee on. | README, docs/* | Low | Docs read consistently; matrix footnotes updated. |
| 7 | CHANGELOG `[Unreleased]` Added entry. | `CHANGELOG.md` | Low | Present. |

## Deferred / out of scope (with reason)

| Item | Reason |
|------|--------|
| Raising capture *depth* (hardware deep, packages full-environment) in `full` | Complexity/usability: "everything on" should mean all hooks + console, not the slowest possible run. A separate max-cost preset can be its own decision later. |
| Renaming/removing any existing mode | Out of scope; the five are confirmed stable. Additive only. |

## Scope check

- Over-scope guard: exactly one new preset; no new deps; no change to the five
  existing modes' behavior. The Medium-risk piece (Step 2 precedence) is the
  only thing to implement carefully.
- Under-scope: the new mode must expose the full public API (Step 3) and be
  reachable via all four selection paths (submodule, `[imports].mode`, env,
  `--mode`) to match the others — included.

## Required tests / validation

- New: `get_mode_behavior("full")`; `import pubrun.full as pubrun` API parity
  (extend `TestModeAliasApiParity`); console-on-by-default; **user override
  precedence** (explicit `capture_mode="off"` beats the `full` default); the
  other five modes still default console OFF (regression).
- `pubrun run --mode full` end-to-end wraps console in the child.
- Full suite green: `~/venv/p3.14/bin/python -m pytest tests/ -q`
  (current baseline: 634 passed, 2 skipped, 1 known-flaky
  `test_real_sigpipe_via_pipe`).

## Spec / documentation sync

README matrix + import-mode blocks, `docs/api.md`, `docs/cli.md`,
`docs/configuration.md`, `docs/functional_spec.md`, `CHANGELOG [Unreleased]`.
Run `/assess documentation` after execution.

## Open questions

1. **Mode name:** `full` (recommended), `deep`, `verbose`, or `all`?
2. **Console-enable mechanism:** approach A (mode contributes a config default,
   recommended) vs B (submodule sets it at import)? A is cleaner but touches
   config resolution; confirm the appetite.
3. **Depth:** confirm `full` should NOT also max out capture depth (recommended
   NO — keep it "all hooks + console", not "slowest").
4. **Precedence intent:** confirm an explicit user `capture_mode` (even `"off"`)
   must override the `full` mode default (recommended YES — user always wins).

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution and is NOT auto-executed. Recommended: run `plan-review` on it, then
approve. On approval: implement, validate, sync docs, move to
`.agents/plans/executed/`.
