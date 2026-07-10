# IPD: `pubrun show config` family — inspect resolved config (now / past run / defaults)

- Date: 2026-07-09
- Concern: functionality / self-documentation / UX
- Scope: `src/pubrun/__main__.py` (show grammar + dispatch), `src/pubrun/config.py`
  (resolution + optional provenance), `src/pubrun/report/diagnostics.py` (renderer),
  `docs/cli.md`, `docs/configuration.md`, tests
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Origin

Requested by the maintainer during the meta-ref/profile architect session (config was found to
already be captured per run as `config.resolved.json`, but there is no easy way to *see* the
config that is/was in effect, nor how ambiguities resolved). Captured in `TODO.md` under
"Deferred ideas". This IPD turns that into an executable plan.

## Goal

Let a user see exactly what configuration is (or was) in effect, for three distinct contexts, and
surface any resolution ambiguity and how it was resolved:

- **`pubrun show config`** — the config that *would* be in effect right now if the user ran
  `import pubrun` in the current directory (resolve the full hierarchy as of now). Answers "what
  will pubrun do if I import it here?"
- **`pubrun show run config [<run identifier>]`** — the config as it was *actually resolved for a
  past run*. Uses the standard run-selection criteria (recency index / id-prefix / path; default to
  the most recent run when the identifier is omitted). This is already durable per run as
  `config.resolved.json`.
- **`pubrun show default config`** — the shipped built-in defaults only.

## Project conventions discovered / verified facts (file:line)

- **`show` grammar** (`__main__.py:2282-2298`): two optional positionals `run_dir` (`:2289`) and
  `section` (`:2290`), both `nargs="?"`. `show` dispatches through `_run_report` (no `_run_show`).
- **The ONLY bare-section support is a hard-coded shift** (`__main__.py:2357-2361`):
  `if args.run_dir in {"logs","env","packages"}: section = run_dir; run_dir = None`. `config` is NOT
  in that set, so a bare `pubrun show config` binds `config` → `run_dir` and `find_run()` tries to
  resolve it as a run selector (fail path). **This shift block is the single chokepoint to extend.**
- **Valid section names `{logs, env, packages}` are duplicated in 3 places** with no shared
  constant: help text (`__main__.py:2290`), the shift test (`__main__.py:2359`), and `if section ==`
  branches (`diagnostics.py:156/176/199`).
- **`--show-config` flag** (`__main__.py:2335`, handler `:2655-2659`) prints the **raw packaged
  `default.toml`** verbatim — it does NOT run `resolve_config()`. Direct functional overlap with
  `show default config`.
- **Resolution** (`config.py:132-175`): 5 layers — built-in (`:145`) → user (`:147-149`) → local
  (`:151-153`) → env (`:156-162`, only `PUBRUN_PROFILE`/`PUBRUN_META_REF`) → API overrides
  (`:164-173`). Merge via `_deep_merge` (`:22-33`), which **discards origin**. **No config-key
  provenance mechanism exists anywhere (confirmed).**
- **Per-run resolved config** is persisted as `config.resolved.json` (`writer.py:73-75`, `:105-106`)
  and manifest-referenced (`tracker.py:646-652`); the deep report already reads it
  (`diagnostics.py:406-416`) but prints only 3 hand-picked keys.
- **Config discovery** (`config.py`): user = `~/.config/pubrun/config.toml`
  (`get_global_config_dir` `:62-73`, `load_user_config` `:94-99`); local = `.pubrun.toml` (wins) and
  `.config/pubrun/config.toml` (`load_local_config` `:102-129`).

## The CLI-grammar collision (the hard design problem)

`pubrun show <run> <section>` already exists (`pubrun show 1 env`). The new forms introduce
`config`/`run`/`default` as **keywords** in the same positional slots. Ambiguities to resolve
deliberately:

- `pubrun show config` — must mean "show current resolved config", NOT "show the run whose id starts
  with `config`" and NOT "show a section named config of the latest run".
- `pubrun show run config` — `run` here is a *mode keyword*, not a run id/section.
- `pubrun show default config` — `default` is a *mode keyword*.
- Must NOT break `pubrun show 1 env`, `pubrun show <prefix>`, `pubrun show env`.

**Proposed grammar (recommended):** treat `config` as a recognized leading keyword, parsed BEFORE
run/section resolution, with an optional qualifier:

| Command | Meaning |
|---|---|
| `pubrun show config` | current resolved config (live 4-layer resolve; API layer empty) |
| `pubrun show config --run [<id>]` | the resolved config of a past run (default: most recent) |
| `pubrun show config --default` | shipped built-in defaults only |

Using **flags** (`--run [<id>]`, `--default`) rather than positional keywords (`show run config` /
`show default config`) avoids the positional collision entirely and is unambiguous with the existing
`show <run> <section>` form. (The maintainer's original phrasing was `show run config` /
`show default config`; the flag form is proposed as the collision-free equivalent — **open question
#1** records this as a choice to confirm.)

## Ambiguity surfacing (the "how it resolved" requirement)

The maintainer wants ambiguities highlighted and how they were resolved — ideally reaching a
"no ambiguity" place. Since **no provenance exists today**, this needs a real (small) mechanism:

- Add an OPTIONAL provenance capture in `resolve_config()`: when asked, record for each leaf key the
  highest-precedence layer that set it (built-in / user / local / env / api) and, where a key was
  set by more than one layer, that it was **overridden** (and by which). This is `profile`-independent
  and the same idea raised in the profile decision.
- `show config` then annotates keys whose value came from a non-default layer (e.g.
  `capture.hardware.depth = off  [local: .pubrun.toml, overrides built-in "basic"]`), so the user
  sees not just the effective value but *why*.
- Keep it OFF the hot path: provenance is computed only for the `show config` command, not written
  into every run's manifest (that would be a separate, larger change — cross-reference the profile
  IPD's config-provenance note).

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Introduce a single shared constant for valid `show` section names (dedupe the 3 literals) so adding keywords is not error-prone. | `__main__.py`, `diagnostics.py` | Low | existing `show env/logs/packages` tests still pass |
| 2 | Add `config` handling to `show`: recognize it as a leading keyword (before run/section resolution) with `--run [<id>]` and `--default` qualifiers per the grammar table. Route to a new `_run_show_config(...)`. | `__main__.py` | Low-Medium (usability — must not break `show <run> <section>`) | new + existing show tests; `show 1 env` still works |
| 3 | Implement `_run_show_config`: current (live `resolve_config()`), `--run` (read `config.resolved.json` via the standard selector, error clearly if absent/old run), `--default` (raw `default.toml`). | `__main__.py`, `report/diagnostics.py` | Low | golden-ish tests for each of the three contexts |
| 4 | Add optional provenance to `resolve_config()` (opt-in return of per-key origin) and render override annotations in `show config`. | `config.py`, `diagnostics.py` | Medium (complexity — keep it opt-in + off the hot path; do not change the resolved value, only annotate) | provenance test: local overriding built-in is reported; hot path unchanged |
| 5 | Reconcile `--show-config`: make it an alias/deprecation pointer to `show config --default` (or keep both, documented). Also fix the verified `--info` doc/impl mismatch (help claims it lists detected config files; `_show_info` `:1722-1761` does not) — either implement or correct the help. | `__main__.py`, docs | Low | `--show-config` still prints defaults; `--info` help matches behavior |
| 6 | Docs: document the `show config` family in `docs/cli.md`; cross-link from `docs/configuration.md`; CHANGELOG. | `docs/cli.md`, `docs/configuration.md`, `CHANGELOG.md` | Low | `/assess documentation` clean |

## Scope check

- Over-scope guard: do NOT add per-run provenance to the manifest here (bigger change; the profile
  IPD tracks that). `show config` computes provenance on demand only. Step 4 is the one place to
  watch the Complexity axis — keep provenance opt-in and value-preserving.
- Under-scope: the shared-section-constant (step 1) is small but prevents the exact 3-way-drift class
  that this very investigation found; include it.

## Required tests / validation

- `pubrun show config` / `--run` / `--default` each produce the right context; `show <run> <section>`
  and `show env` are unbroken (regression). Provenance annotation correctly reports a local override
  of a built-in default. `pytest tests/ -v` green on the full matrix (CLI-grammar change → per the
  AGENTS.md matrix-validation discipline, confirm on CI; arg-parsing differences can be subtle).

## Spec / documentation sync

`docs/cli.md` (new command family), `docs/configuration.md` (cross-link + note `show config` shows
resolution), CHANGELOG. Run `/assess documentation` after.

## Open questions

1. **Grammar:** flag form (`show config --run [<id>]` / `--default`) — recommended, collision-free —
   vs. the maintainer's original positional phrasing (`show run config` / `show default config`)? The
   positional form needs a keyword-vs-runid disambiguation layer; the flag form does not.
2. **`--show-config` fate:** alias it to `show config --default` and soft-deprecate, or keep both?
3. **Provenance depth:** is "which layer set each overridden key" enough, or do you also want to see
   the shadowed values from *every* layer (fuller but noisier)? Recommend: overridden-keys-only by
   default, with a `--verbose`/`--all` for the full per-layer view.
4. Should `show config` (current) reflect the current directory's local `.pubrun.toml` (yes, that is
   the point) — confirm it resolves relative to CWD like a real `import pubrun` would.

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. On approval: implement steps in order,
verify on the CI matrix, sync docs + CHANGELOG, then move this IPD to `.agents/plans/executed/`.
