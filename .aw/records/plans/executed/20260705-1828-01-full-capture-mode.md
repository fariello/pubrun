# IPD: Add a sixth import mode — `full` (capture everything including console)

- Date: 2026-07-05
- Concern: functionality / API design (new public import mode)
- Scope: a new import-mode preset, `full`, that on a single import captures
  everything pubrun does by default **plus** wraps the console (stdout/stderr) —
  the one thing no current mode turns on by default. New public API surface: a
  `src/pubrun/full.py` submodule, a new `[imports].mode = "full"` value, a new
  `run --mode full` choice, docs, tests.
- Status: EXECUTED (2026-07-05). All steps implemented + tested; the
  characterization gate (Step 1) stayed green through the seam change. Full suite:
  654 passed, 2 skipped, 1 known-flaky (`test_real_sigpipe_via_pipe`). All four
  selection paths (submodule/env/config/`run --mode`) verified.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Plan-review: this IPD was rewritten 2026-07-05 to a simpler, low-risk design
  after a design discussion resolved the precedence model (see "Design decisions
  (resolved)"). It supersedes the earlier resolve_config-overlay approach, which
  is no longer needed.

## Goal

Give users a single-import "capture everything, including console output" option
that is consistent with the existing namespaced modes. Today, capturing console
output requires a console-permitting mode **and** setting
`[console].capture_mode` to a non-`"off"` value; there is no one-import form.
`full` fills that gap and is the natural opposite of `noconsole`.

Additive only: the five existing modes (auto/noauto/nopatch/noconsole/minimal)
are unchanged.

## Design decisions (resolved in discussion 2026-07-05)

These were settled with the maintainer and drive the design below:

1. **Name:** `full`. (Reads well as the opposite of `noconsole`; not overloaded.)
2. **Precedence model (the key one) — import mode is an ABSOLUTE imperative.**
   An `import pubrun.<mode> as pubrun` line is code the developer wrote on
   purpose; it **overrides environment variables and config files
   unconditionally** for the scope/hooks it dictates. The ONLY thing above it is
   the CLI operator override `pubrun run --mode Y -- script` (launch-time, by the
   person running it). Config/env only fill in what the import mode did not
   dictate. This is not new — it is exactly how the existing modes already work:
   `noconsole` sets `patch_console=False` and forces the console tee **off
   regardless of any `capture_mode` in config** (`tracker.py:317-321`). `full` is
   the mirror image: it forces the console tee **on** regardless of config.
   Therefore there is **no config-precedence machinery to build** — no change to
   `resolve_config`, no "unset vs off" ambiguity. (This removes the Medium-High
   risk of the superseded design.)
3. **`full` forces console base `"standard"` but still respects the SAFETY
   context-guards.** In a Jupyter kernel the tee still auto-disables (returns
   `jupyter_mode`, default `"off"` — verified `console.py:41-43`), because double-
   wrapping Jupyter's stdout is genuinely broken. The non-TTY guard also still
   runs, but note its exact semantics (verified `console.py:46-52`): it only
   downgrades when the user set a **non-default** `non_tty_mode` (default is
   `"inherit"`, which means "use the base" — so under `full` a piped/non-TTY run
   with default config WILL still capture at `"standard"`). That is consistent
   (inherit == use the forced base); the executor must not "fix" it into an
   unconditional non-TTY downgrade. These are correctness guards, not
   user-preference reads, so `full` keeps them as-is.
4. **`full` does NOT max out capture depth.** It means "all hooks + console," not
   "slowest possible run." Hardware depth, packages mode, etc. keep their normal
   defaults. (A separate max-cost preset can be its own decision later.)

## Project conventions discovered (Step 0)

- Modes live in `src/pubrun/_modes.py` as boolean behavior dicts and are surfaced
  as importable submodules `src/pubrun/<mode>.py` that call `select_mode(...)`,
  import + rebind the full public API into the `pubrun` namespace, and boot.
- The console decision seam is `tracker.py:317-321`: when `_patch_console` is
  True it calls `resolve_console_mode(self.config)`, else forces `"off"`.
  `resolve_console_mode` (`console.py:24-54`) reads the base `capture_mode`, then
  applies the Jupyter and non-TTY guards. Crucially, those guards run **after**
  the base decision — so injecting a forced base of `"standard"` naturally still
  passes through the guards. This is the whole implementation seam.
- `_MODE_SUBMODULES` (`_bootstrap.py`) and the `run --mode` argparse choices
  (`__main__.py`) enumerate the mode set and must include `full`.
- Legacy `(auto_start, global_hooks)` → mode mapping (`_modes.py`): `full` shares
  `(True, True)` with `auto`, so `full` is only selectable by explicit name, not
  via the two-bool legacy config. Document this.
- Guiding principles: stupid-simple, intuitive, consistent, honest docs, zero
  runtime deps. `full` is justified by consistency (it is the missing opposite of
  `noconsole`) and one-import ergonomics.
- Just-landed related fix: all mode aliases now rebind the full 12-name public
  API; `full` must do the same.
- Doc-sync (AGENTS.md): README matrix + import-mode blocks, api.md, cli.md,
  configuration.md, functional_spec.md, CHANGELOG.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 (anti-regression gate, do FIRST) | Characterization tests pinning current behavior so the console-seam change can't regress the other modes: default `import pubrun` + no console config → `resolve_console_mode == "off"`; each existing mode → console off with no config; explicit `capture_mode="standard"` → `"standard"`; **Jupyter/non-TTY guards still downgrade** when base is on. Green before AND after. | `tests/` | Low | Passes on current HEAD; still passes after Steps 2-3. |
| 2 | Add a `force_console` capability to the console seam. Add `"full"` to `MODES` with the same permits as `auto` (`auto_start/global_hooks/patch_subprocesses/patch_console/signal_hooks = True`) plus a new flag `force_console = True` (other modes: absent, treated as False). **Exact `resolve_console_mode` change:** add a keyword `force_base: Optional[str] = None`; set `base_mode = force_base if force_base else config.get("console", {}).get("capture_mode", "off")`, then keep the rest verbatim (the `if base_mode == "off": return "off"` early-return, then Jupyter guard, then non-TTY guard, then `return base_mode`). Because `force_base="standard"` is not `"off"`, the early-return is skipped and BOTH guards below still run unchanged — no other edit to that function. In `tracker.py:317`, when `_behavior.get("force_console")` is True (and `_patch_console` is True, which it is for `full`), call `resolve_console_mode(self.config, force_base="standard")`; otherwise call it as today. Do NOT touch `resolve_config`. | `src/pubrun/_modes.py`, `src/pubrun/capture/console.py`, `src/pubrun/tracker.py` | Low (local seam; no `resolve_config` change; guards preserved) | `full` with no console config OR explicit `capture_mode="off"` → tee active as `"standard"` (import overrides config); `full` in a (mocked) Jupyter kernel → still `"off"`; `full` non-TTY with default `non_tty_mode` → still `"standard"` (inherit uses base); `full` non-TTY with `non_tty_mode="off"` → `"off"`; all five other modes unchanged (Step 1 tests stay green). |
| 3 | Add `src/pubrun/full.py` mirroring the other submodules: `select_mode("full", ...)`, import + rebind the FULL 12-name public API, auto-start boot. | `src/pubrun/full.py` | Low | `import pubrun.full as pubrun` exposes all 12 names (extend `TestModeAliasApiParity` to include `full`); auto-starts; console is wrapped. |
| 4 | Register `full` in `_MODE_SUBMODULES` (`_bootstrap.py`, used for import-in-progress detection) and add `"full"` to the `run --mode` argparse `choices` (`__main__.py`). Note: `[imports].mode="full"` and `PUBRUN_IMPORT_MODE=full` need NO extra registration — `resolve_import_mode` validates against `VALID_MODES = frozenset(MODES.keys())` (`_config_boot.py:63,75`), which includes `full` once Step 1 adds it. Verify this rather than adding redundant lists. | `_bootstrap.py`, `__main__.py` | Low | `pubrun run --mode full -- python script.py` wraps console in the child; `--help` lists `full`; `PUBRUN_IMPORT_MODE=full python -c "import pubrun; ..."` selects `full`. |
| 5 | Docs: add `full` to the README Preset Modes matrix (Console column = ✅ **on**, the distinguishing feature; note it forces console regardless of config, like `noconsole` forces it off), the import-mode code blocks, `api.md`, `cli.md` `--mode`, `configuration.md` `[imports].mode`, `functional_spec.md` matrix (add a `force_console` column note). State that import modes are absolute over env/config and only `run --mode` overrides them. Note `full` is name-selectable only (legacy two-bool collision with `auto`). | README, docs/* | Low | Docs consistent; matrix footnotes updated. |
| 6 | CHANGELOG `[Unreleased]` Added entry. | `CHANGELOG.md` | Low | Present. |

## Deferred / out of scope (with reason)

| Item | Reason |
|------|--------|
| Raising capture *depth* in `full` (hardware deep, full-environment packages) | Complexity/usability: "everything on" = all hooks + console, not slowest-possible. Separate decision. |
| Scoped in-code pause/resume of capture (`with pubrun.paused(): ...`) | Orthogonal to `full`; carries real global-monkeypatch/thread-safety hazards. Recorded in `TODO.md` for its own future IPD. |
| Renaming/removing any existing mode | Out of scope; the five are stable. Additive only. |
| Documenting the "import mode is absolute over config" precedence *for the other five modes* beyond what Step 5 adds | Not a behavior change (it is already how they work); Step 5 documents it once. |

## Scope check

- Over-scope: exactly one new preset + one small, local console-seam parameter.
  No new deps, no `resolve_config` change, no change to the five existing modes'
  behavior. The earlier Medium-High config-overlay design was **dropped** because
  the resolved precedence model (import mode = absolute) makes it unnecessary.
- Under-scope: `full` must expose the full 12-name public API (Step 3) and be
  reachable via all selection paths (submodule, `[imports].mode`, `run --mode`);
  included. (Env-var selection uses the existing `PUBRUN_IMPORT_MODE`, which
  already accepts any valid mode name — verify `full` flows through it.)

## Execution order

Step 1 (characterization gate) → Step 2 → Step 3 → Step 4 → Steps 5-6.

## Required tests / validation

- `get_mode_behavior("full")` returns the expected dict incl. `force_console`.
- `import pubrun.full as pubrun` API parity (extend `TestModeAliasApiParity`).
- Console: `full` → tee on (`"standard"`) with no config AND with explicit
  `capture_mode="off"` (import overrides config); Jupyter kernel (mocked) →
  `"off"` (auto-disabled); non-TTY with default `non_tty_mode="inherit"` →
  `"standard"` (inherit uses the forced base); non-TTY with `non_tty_mode="off"`
  → `"off"`; all five other modes still default console off (Step 1 regression).
- `pubrun run --mode full` end-to-end wraps console in the child.
- `PUBRUN_IMPORT_MODE=full` selects the mode.
- Full suite green: `~/venv/p3.14/bin/python -m pytest tests/ -q`
  (baseline: 634 passed, 2 skipped, 1 known-flaky `test_real_sigpipe_via_pipe`).

## Spec / documentation sync

README matrix + import-mode blocks, `docs/api.md`, `docs/cli.md`,
`docs/configuration.md`, `docs/functional_spec.md`, `CHANGELOG [Unreleased]`.
Run `/assess documentation` after execution.

## Open questions

None blocking — the design decisions above are resolved. One confirmation to
carry into execution: the README/docs should also state, once, the general
precedence rule ("an in-code `import pubrun.<mode>` overrides env/config; only
`pubrun run --mode` overrides the import") since this IPD is the first to write
it down explicitly. (Assumed yes; it documents existing behavior.)

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution and is NOT auto-executed. On approval: implement in the given order,
validate, sync docs, and move to `.agents/plans/executed/`.

## Plan-review revisions (2026-07-05, simple design)

Verdict: **APPROVE WITH REVISIONS APPLIED**. Re-reviewed the rewritten low-risk
design against the actual source (`console.py:24-54`, `tracker.py:296-323`,
`_bootstrap.py` select_mode/`_MODE_SUBMODULES`, `_config_boot.py:52-75`
`resolve_import_mode`, `_modes.py` `VALID_MODES`). The mechanism is sound and
low-risk; no re-plan. Verified-correct claims: the `force_base="standard"` edit
preserves both context guards (they run after the skipped `"off"` early-return);
`full`'s extra `force_console` key does not break `select_mode`'s dict-equality
conflict check; Jupyter path returns `"off"`. Revisions (all LOW):

- **PR2-F1 (accuracy):** Step 4 implied `full` needed explicit registration for
  env/config selection. Corrected: `PUBRUN_IMPORT_MODE=full` and
  `[imports].mode="full"` work for free via `VALID_MODES = frozenset(MODES.keys())`
  once Step 1 adds `full`; only `_MODE_SUBMODULES` and the argparse `choices`
  need editing. Told the executor to verify, not add redundant lists.
- **PR2-F2 (accuracy):** the plan overstated "non-TTY downgrade still applies."
  Corrected in decision #3 and the tests: the non-TTY guard only downgrades when
  the user set a non-default `non_tty_mode`; with the default `"inherit"`, `full`
  captures at `"standard"` even when piped. Executor must NOT turn this into an
  unconditional downgrade.
- **PR2-F3 (precision):** pinned the exact `resolve_console_mode(force_base=...)`
  change (one-line base selection + keep the rest verbatim) so the executor
  cannot reintroduce the `"off"` early-return that would defeat the force. Added
  the explicit-`off`-config case to the validation matrix.
