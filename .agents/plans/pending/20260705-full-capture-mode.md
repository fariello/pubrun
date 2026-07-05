# IPD: Add a sixth import mode — "capture everything including console"

- Date: 2026-07-05
- Concern: functionality / API design (new public import mode)
- Scope: a new import-mode preset that, on a single import, captures everything
  pubrun can — including console streams (stdout/stderr), which no current mode
  turns on by default. New public API surface: a new `src/pubrun/<name>.py`
  submodule, a new `[imports].mode` value, a new `run --mode` choice, docs, tests.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Plan-review: hardened 2026-07-05 (verdict APPROVE WITH REVISIONS APPLIED). One
  BLOCKER-class design gap corrected on paper (the console-default mechanism was
  not implementable as first written). See "Plan-review revisions" at the end.

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
2. **How the mode enables console** (the crux).

   **⚠ PLAN-REVIEW BLOCKER (verified against code):** the naive "mode default,
   but user's explicit setting wins" cannot be implemented against the current
   config shape. `resolve_console_mode` reads
   `config.get("console", {}).get("capture_mode", "off")` (`console.py:35`), and
   `capture_mode = "off"` is set in `default.toml` (`default.toml:86`) — so the
   resolved config **always** contains `console.capture_mode`, and its value is
   `"off"` in BOTH cases: "user set nothing" and "user explicitly set off".
   Verified: `resolve_config()["console"]["capture_mode"] == "off"` on a clean
   checkout. There is therefore **no `"unset"` sentinel** to key "did the user
   choose?" off of. Any mechanism must resolve this ambiguity explicitly. The
   corrected approaches:

   - **(A) Precedence-layer injection (RECOMMENDED).** Inject the mode's console
     default as a config layer positioned **just above `default.toml` and below
     all user layers** (user config, local config, env, `start()` overrides) in
     `resolve_config`. Because every user-supplied layer sits above `default.toml`
     (see the precedence list in `config.py:135-140`), this makes `full` flip
     `"off"→"standard"` while ANY user-set `capture_mode` (including an explicit
     `"off"`) still wins. Requires: (i) removing/](or neutralizing) the
     `capture_mode = "off"` line from `default.toml` OR treating the mode overlay
     as replacing that specific default, and (ii) `resolve_config` learning the
     selected mode (e.g. read `get_selected_behavior()` or accept a
     `mode_defaults` arg). This is the correct seam but is the **Medium-High**
     part of this IPD — `resolve_config` is called from ~10 sites and must stay
     correct for the other five modes (which contribute no overlay).
   - **(B) Distinguish unset via a sentinel.** Change `default.toml` to omit
     `capture_mode` (or set it to a sentinel like `"auto"`/`null`) so "unset" is
     detectable, then have `full` supply `"standard"` and every other mode fall
     back to `"off"`. Larger blast radius (changes the meaning of the shipped
     default for ALL modes) and risks regressing the deliberate
     "capture_mode defaults to off" behavior. NOT recommended.
   - **(C) `full` submodule sets it at import** only when neither env nor a
     config file specifies `capture_mode`. Requires the submodule to do its own
     lightweight config probe (like `_config_boot._read_local_toml_key`) BEFORE
     boot to check user intent, then inject via override. Self-contained (no
     change to the shared `resolve_config`), but must replicate the precedence
     check and cannot see a `start(console=...)` override that happens later.

   **Recommendation: (A)**, implemented as a mode-default overlay that sits
   exactly one layer above `default.toml`. Whatever approach is chosen, the
   Remediation Risk of Step 2 is **Medium-High on functionality** (it touches the
   shared config-resolution precedence that all six modes depend on) — this is the
   one part of the IPD that itself warrants a mini plan-review of the diff before
   merge, and it should ship with the explicit precedence tests in Step 2's row.
3. **Should `full` also raise capture depth** (e.g. hardware `deep`, packages
   `full-environment`)? Recommendation: NO — keep `full` about *console being
   the missing piece*, not about maximizing every capture cost. "Everything on"
   should mean "all hooks + console," not "slowest possible." Revisit if the
   maintainer wants a separate max-cost preset.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Add the `full` behavior to `MODES`: `auto_start=True, global_hooks=True, patch_subprocesses=True, patch_console=True, signal_hooks=True` (same permits as `auto`). | `src/pubrun/_modes.py` | Low | `get_mode_behavior("full")` returns the expected dict; `VALID_MODES` includes it. |
| 2a | **Anti-regression gate (rubric D — do FIRST, before Step 2).** The console-default mechanism touches shared config resolution that all six modes depend on. Before changing it, add characterization tests pinning current behavior: (i) default `import pubrun` → `resolve_console_mode == "off"`; (ii) each of `auto/noauto/nopatch/noconsole/minimal` → console `"off"` with no user config; (iii) explicit `capture_mode="standard"` (config + `start()` override) → `"standard"`. Green before AND after Step 2. | `tests/` (new) | Low | The characterization tests pass on current HEAD, then still pass after Step 2 with only `full` changed. |
| 2 | Implement the console-default mechanism per decision #2 (recommend **A**: inject a mode-default overlay one layer above `default.toml`). ⚠ Cannot be done naively — see decision #2's BLOCKER note: `capture_mode` is always present/`"off"` in resolved config, so "user set nothing" is indistinguishable from "user set off" unless the mechanism operates at the config-resolution *layer* level (overlay above `default.toml`, below all user layers) rather than reading the merged value. `resolve_config` must learn the selected mode (read `get_selected_behavior()` or take a `mode_defaults` arg) and be verified correct for its ~10 call sites. **Blocked on decision #2 (Open question #2) being answered before implementation.** | `_modes.py`, `config.py` (the merge order + a mode-default overlay), possibly `default.toml` (neutralize the hardcoded `capture_mode="off"` so the overlay can win) | **Medium-High** (functionality: shared config precedence for all six modes) | Tests (Step 2a green + new): `full`, no user console config → effective `"standard"`; `full` + explicit user `capture_mode="off"` (config, env-if-supported, and `start(console={"capture_mode":"off"})`) → `"off"` (user wins); all five other modes still default `"off"`. |
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
  existing modes' behavior. The one carefully-implemented piece is the Step 2
  config-precedence mechanism, whose Remediation Risk is **Medium-High** on
  functionality (it edits `resolve_config`, shared by all six modes and ~10 call
  sites) — not Medium as originally written.
- **Complexity counterweight (KISS):** because Step 2 is the only Medium-High
  part, seriously weigh the cheaper alternative in Open question #5 — a
  documented config recipe (`import pubrun` + `capture_mode="standard"`) delivers
  ~80% of the value with near-zero risk. The sixth mode is justified only if the
  one-import ergonomics are worth the shared-config-resolution change.
- Under-scope: the new mode must expose the full public API (Step 3) and be
  reachable via all four selection paths (submodule, `[imports].mode`, env,
  `--mode`) to match the others — included.

## Execution order

Step 2a (characterization tests) → Step 1 → Step 2 (only after Open question #2
is answered) → Steps 3–7. Do NOT start Step 2 until the mechanism (decision #2)
is chosen, since the file touchpoints differ materially between approaches A/B/C.

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
2. **Console-enable mechanism:** approach **A** (mode-default overlay one layer
   above `default.toml` in `resolve_config`, recommended), **B** (change the
   shipped `capture_mode` default to a detectable "unset" sentinel), or **C**
   (`full` submodule probes config and injects at import)? See decision #2's
   BLOCKER note — the naive "read merged value" approach does NOT work. This
   choice sets the Step 2 file touchpoints, so it must be answered before Step 2.
3. **Depth:** confirm `full` should NOT also max out capture depth (recommended
   NO — keep it "all hooks + console", not "slowest").
4. **Precedence intent:** confirm an explicit user `capture_mode` (even `"off"`)
   must override the `full` mode default (recommended YES — user always wins).
   Note this is *only* achievable via approach A/B/C above, not naively.
5. **Is the mode worth the Medium-High config change at all?** The cheaper
   alternative is to add NO new mode and instead document a one-line recipe
   (`import pubrun` with `[console].capture_mode = "standard"`, or
   `pubrun.start(console={"capture_mode": "standard"})`) plus a `.pubrun.toml`
   snippet. That has near-zero risk and no new API surface. Confirm you still
   want the sixth mode given that Step 2 touches shared config resolution.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution and is NOT auto-executed. Recommended: run `plan-review` on it, then
approve. On approval: implement, validate, sync docs, move to
`.agents/plans/executed/`.

## Plan-review revisions (2026-07-05)

Verdict: **APPROVE WITH REVISIONS APPLIED**. Verified the plan's mechanism
against the actual source (`_modes.py`, `console.py:35`, `default.toml:86`,
`config.py:132-153`, `resolve_mode_name`). The approach (one additive preset) is
sound; no re-plan. Changes:

- **PR-F1 (BLOCKER → fixed on paper, functionality):** the original Step 2 said
  "mode default, but user's explicit `capture_mode` wins" without noting this is
  **not implementable** as stated. Verified: `capture_mode` is always present and
  `"off"` in resolved config (from `default.toml`), so "unset" and "explicit off"
  are indistinguishable. Rewrote decision #2 with three concrete, code-grounded
  approaches (A: precedence-layer overlay above `default.toml` — recommended; B:
  detectable-unset sentinel; C: submodule-probes-at-import) and made Step 2
  depend on choosing one first.
- **PR-F2 (HIGH, rubric D):** added Step 2a — characterization tests pinning that
  all six modes default console `"off"` and that explicit `"standard"` works,
  green before AND after the shared-config change, since Step 2 edits
  `resolve_config` (used by ~10 call sites).
- **PR-F3 (MEDIUM, KISS/scope):** corrected Step 2's Remediation Risk from Medium
  to **Medium-High** (it touches shared config precedence) and added Open
  question #5 — whether the sixth mode is worth that change vs. a documented
  config recipe with near-zero risk.
- **PR-F4 (LOW):** added an explicit Execution order (2a → 1 → 2-after-decision →
  3-7) so the mechanism isn't built before its approach is chosen.

Confirmed accurate (no change needed): Step 1 flag set matches `auto`; Step 5's
claim that `full` collides with `auto` in the legacy `(auto_start, global_hooks)`
tuple and must be name-selected only (verified against `_LEGACY_MODE_MAPPING`);
Step 3's requirement to rebind the full 12-name public API (matches the parity
fix landed earlier today).
