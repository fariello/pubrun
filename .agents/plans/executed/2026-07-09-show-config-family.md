# IPD: `pubrun show config` family — inspect resolved config (now / past run / defaults)

- Date: 2026-07-09
- Concern: functionality / self-documentation / UX
- Scope: `src/pubrun/__main__.py` (show grammar + dispatch), `src/pubrun/config.py`
  (resolution + optional provenance), `src/pubrun/report/diagnostics.py` (renderer),
  `docs/cli.md`, `docs/configuration.md`, tests
- Status: EXECUTED 2026-07-20 (approved). Full CI matrix green (3 OS × Python 3.8–3.14). See
  "Execution notes" below.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Execution notes (2026-07-20)

All six steps landed as planned (commit `f565b80`); local suite 904 passed, matrix green after a
flake cleanup (below).

- **Grammar (Q1=B, positional):** `show config` / `show run config [<id>]` / `show default config`
  recognized before run selection, with explicit precedence over run ids named config/run/default.
  Regression tests confirm `show 1 env`, `show env`, `show <run>`, and a run id starting with a
  reserved keyword all still resolve (`tests/test_show_config.py`, 13 tests). PR-006 (the HIGH-risk
  disambiguation) validated on the full matrix, including arg-parsing across Python 3.8–3.14.
- **Provenance (Q3=A):** implemented as a SEPARATE `resolve_config_with_provenance()` (not a union
  return on `resolve_config`, per a review refinement) via a shared `_resolve_layers()` helper;
  value-identical to `resolve_config()`. Overridden keys annotated by default; `--all` for full.
- **Degraded runs (Q4=C):** crashed/unfinalized run shows a labeled startup snapshot; ghost run
  errors clearly.
- **`--show-config` (Q2=B):** soft-deprecated with a stderr notice pointing to `show default config`;
  `--info` help doc/impl mismatch corrected.
- **Section-set dedupe:** `diagnostics.SHOW_SECTIONS` replaces the 3 literals.
- Docs: `docs/cli.md` (new `show config` subsection + `--show-config` deprecation note),
  `docs/configuration.md` (cross-link), CHANGELOG. `/assess documentation` to follow.

### Flake cleanup (matrix rule did its job)

The push went red on four SEPARATE, PRE-EXISTING load/timing-sensitive tests (one per CI run, each a
different job), none from show-config (which passed on every job). All hardened in follow-up commits
`13f9beb`, `8e9978b`, `753ee76`:
1. `test_full_wraps_console_end_to_end` (ubuntu-3.8): bracket-access on an un-finalized console
   section → `.get()` + assert the load-bearing `CAPTURED=True`.
2. `test_startup_manifest_conforms_to_schema` (windows-3.14): read a live run's manifest → Windows
   file lock → tolerant retry + skip.
3. `test_resources` peak-RSS (ubuntu-3.11): asserted a non-None peak before the sampler landed →
   tolerate None, require positive int when present.
4. `test_run_tests_mock_run_manifest_is_wellformed` (ubuntu-3.14): subprocess atexit-finalize race →
   explicit `pubrun.stop()` in the child. Swept the suite for the same class; the rest finalize
   in-process and are not race-prone.

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

**Decided grammar (Q1 = positional form, maintainer's original wording):**

| Command | Meaning |
|---|---|
| `pubrun show config` | current resolved config (live resolve as of now, in CWD) |
| `pubrun show run config [<id>]` | the resolved config of a past run (default: most recent) |
| `pubrun show default config` | shipped built-in defaults only |

This reads most naturally, and it is what the maintainer wants. It costs a **keyword-vs-run-id
disambiguation layer** the flag form would have avoided, so the implementation MUST (see finding
PR-006):

- Recognize `config` as the leading token in the `run_dir` slot and route to `_run_show_config`,
  BEFORE `find_run()` treats it as a run selector (today `pubrun show config` errors with "Run
  directory 'config' does not exist" — verified `__main__.py` dispatch + `find_run`).
- Recognize the two-token forms `show run config` and `show default config`: here `run`/`default`
  occupy the `run_dir` slot and `config` the `section` slot. The parser must treat `run`/`default`
  as **mode keywords in this specific `... config` construction**, not as run selectors.
- **Guard the collision explicitly:** a real run whose id/prefix is literally `run`, `default`, or
  `config` must not be silently shadowed. Define precedence: the `... config` keyword forms win; if a
  user genuinely needs a run whose id starts with one of these words, they use an unambiguous form
  (full id or path). Document this. Add regression tests for `show 1 env`, `show <prefix>`,
  `show env`, and a run id that starts with `config`/`run`/`default`.
- Reuse the existing shared-section-constant (step 1) and the shift chokepoint (`__main__.py:2359`)
  rather than adding a parallel parsing path (rubric C: no duplicate mechanisms).

## Ambiguity surfacing (the "how it resolved" requirement)

The maintainer wants ambiguities highlighted and how they were resolved — ideally reaching a
"no ambiguity" place. Since **no provenance exists today**, this needs a real (small) mechanism:

Decided (Q3 = overridden-keys-only by default, `--all` for the full per-layer view):

- Add an OPTIONAL provenance capture in `resolve_config()`: when asked, record for each leaf key the
  highest-precedence layer that set it (built-in / user / local / env / api) and, where a key was
  set by more than one layer, that it was **overridden** (and by which). This is `profile`-independent
  and the same idea raised in the profile decision.
- **Default output annotates ONLY overridden keys** (e.g.
  `capture.hardware.depth = off  [local: .pubrun.toml, overrides built-in "basic"]`), so a config
  with no conflicts prints clean ("no ambiguity" reached by construction). `show config --all`
  annotates every key with its source layer.
- Keep it OFF the hot path: provenance is computed only for the `show config` command, not written
  into every run's manifest (that would be a separate, larger change — cross-reference the profile
  IPD's config-provenance note).
- **Separability (finding PR-004):** provenance (step 4) is the only Medium-risk step and is NOT
  required for the core value. Steps 1-3 (the three `show config` contexts showing effective config)
  can ship first and are independently useful; step 4 may follow as its own change. Do not block the
  core on the provenance mechanism.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Introduce a single shared constant for valid `show` section names (dedupe the 3 literals at `__main__.py:2290`, `:2359`, and `diagnostics.py:156/176/199`) so adding keywords is not error-prone. | `__main__.py`, `diagnostics.py` | Low | existing `show env/logs/packages` tests still pass |
| 2 | Add the positional `config` grammar (Q1=B): route `show config`, `show run config [<id>]`, `show default config` to a new `_run_show_config(...)` BEFORE `find_run()` treats the token as a run selector. Implement the keyword-vs-run-id disambiguation + precedence per the grammar section, reusing the shift chokepoint (no parallel parser). | `__main__.py` | **Medium-High (usability + functionality)** — a keyword grammar over the existing positional run/section slot risks shadowing real run ids and breaking `show <run> <section>`; the disambiguation is the riskiest part of the plan (PR-006). | new grammar tests AND regression: `show 1 env`, `show <prefix>`, `show env`, and a run id starting with `config`/`run`/`default` all still resolve correctly |
| 3 | Implement `_run_show_config` for the three contexts: **current** (live `resolve_config()` in CWD), **`show run config [<id>]`** (read the run's `config.resolved.json` via the standard selector), **`show default config`** (raw `default.toml`). Degraded-run handling (Q4=C): a crashed/unfinalized run reads its **startup** `config.resolved.json` labeled "from startup snapshot (run did not finalize)"; a **ghost** run (no run dir/config written) yields a clear non-zero error "run <id> has no recorded config (ghost run)". Never substitute current config for a past run's (PR-001). | `__main__.py`, `report/diagnostics.py` | Low | tests for each context + a crashed-run (startup snapshot) case + a ghost/absent-config error case |
| 4 | Add optional provenance to `resolve_config()` (opt-in per-key origin) and render override annotations in `show config` (Q3=A): default annotates only overridden keys; `--all` shows every key's source. **Separable/deferrable** — steps 1-3 ship independently (PR-004). | `config.py`, `diagnostics.py` | Medium (complexity — opt-in, off the hot path, value-preserving: annotate only, never change the resolved value) | provenance test: a local override of a built-in default is reported; a no-conflict config prints clean; `resolve_config()` hot-path output byte-identical with/without provenance requested |
| 5 | Reconcile `--show-config` (Q2=B, soft-deprecate): keep it working but print a one-line notice pointing to `show default config`; slate for later removal (mirrors this session's `profile` accept-but-notice pattern). Also fix the verified `--info` doc/impl mismatch (help claims it lists detected config files; `_show_info` does not) — correct the help text (do not expand scope by implementing config-file listing here). | `__main__.py`, docs | Low | `--show-config` still prints defaults + notice; `--info` help matches behavior |
| 6 | Docs: document the `show config` family in `docs/cli.md`; cross-link from `docs/configuration.md`; CHANGELOG. Note "current" reflects the ambient env + CWD at invocation time (PR-002). | `docs/cli.md`, `docs/configuration.md`, `CHANGELOG.md` | Low | `/assess documentation` clean |

## Scope check

- Over-scope guard: do NOT add per-run provenance to the manifest here (bigger change; the profile
  IPD tracks that). `show config` computes provenance on demand only. Step 4 is the one place to
  watch the Complexity axis — keep provenance opt-in and value-preserving.
- Under-scope: the shared-section-constant (step 1) is small but prevents the exact 3-way-drift class
  that this very investigation found; include it.

## Required tests / validation

- The three contexts (`show config`, `show run config [<id>]`, `show default config`) each produce
  the right output; degraded-run cases (crashed = startup snapshot labeled; ghost = clean error).
- **Regression (named invariants, PR-003):** `show 1 env` (recency index + section), `show <prefix>`,
  `show env` (bare section), and a run id that starts with `config`/`run`/`default` all resolve
  exactly as before. These are the invariants the new keyword grammar most endangers.
- Provenance: a local override of a built-in default is annotated; a no-conflict config prints clean;
  `resolve_config()` output is byte-identical whether or not provenance is requested (value-preserving).
- `pytest tests/ -v` green on the **full CI matrix** — this is a CLI-grammar (contract-shaped) change,
  so per the `AGENTS.md` matrix-validation discipline it is NOT done on local green; arg-parsing and
  keyword-vs-run-id behavior can differ subtly and must be confirmed on CI before the IPD moves to
  `executed/`.

## Spec / documentation sync

`docs/cli.md` (new command family), `docs/configuration.md` (cross-link + note `show config` shows
resolution), CHANGELOG. Run `/assess documentation` after.

## Open questions (all resolved interactively 2026-07-12)

1. **Grammar** → RESOLVED: positional form `show config` / `show run config [<id>]` / `show default
   config` (maintainer's original wording). Requires the keyword-vs-run-id disambiguation layer (see
   the grammar section + PR-006); accepted as the cost of the more natural UX.
2. **`--show-config` fate** → RESOLVED: soft-deprecate (keep working + one-line pointer to `show
   default config`; remove later), mirroring the `profile` accept-but-notice pattern.
3. **Provenance depth** → RESOLVED: overridden-keys-only by default; `show config --all` shows every
   key's source layer.
4. **Does `show config` (current) resolve in CWD like a real `import pubrun`?** → RESOLVED (evidence):
   yes. `resolve_config()` loads local config from `Path.cwd()` (`config.py` `load_local_config`), so
   `show config` in a project dir reflects that dir's `.pubrun.toml` plus ambient env vars. Documented
   caveat (PR-002): "current" depends on the env vars present when `show config` runs, which may differ
   from what a specific script sees.

## Findings (plan-review 2026-07-12)

| ID | Severity | Scope | Area | Finding | Remediation Risk | Decision |
|----|----------|-------|------|---------|------------------|----------|
| PR-001 | MEDIUM | UNDER-SCOPE | A/G | `show run config` degraded-run behavior (ghost/crashed) was unspecified. | Low | FIXED (step 3, Q4=C) |
| PR-002 | MEDIUM | IN-SCOPE | A | "current" config depends on ambient env/CWD at invocation; could mislead if unstated. | Low | FIXED (step 6 doc note) |
| PR-003 | LOW | UNDER-SCOPE | D | Regression invariants most at risk (`show 1 env`, run id starting with a keyword) were not named/routed to tests. | Low | FIXED (validation section) |
| PR-004 | LOW | IN-SCOPE | G | Provenance (step 4, Medium risk) not marked separable from the core. | Low | FIXED (separability note) |
| PR-005 | LOW | UNDER-SCOPE | Gate | Execution gate lacked the execution contract (honesty rule, path-scoped commit, lifecycle). | Low | FIXED (gate below) |
| PR-006 | HIGH | IN-SCOPE | C/F | Positional grammar (Q1=B) makes step 2 the riskiest part: a keyword grammar over the run_dir slot can shadow real run ids / break `show <run> <section>`. Step 2 risk raised to Medium-High; disambiguation + precedence + regression tests are mandatory, not optional. | Medium-High (usability+functionality) | FIXED-IN-PLAN (step 2 rewritten with explicit disambiguation + regression tests; execution must validate on CI) |

No finding is deferred; all are resolved in-plan. PR-006 is not a deferral — it is a raised-risk step
with mandated guardrails, to be proven by the regression tests + CI matrix at execution.

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Execution contract:

- Implement steps in order; steps 1-3 are the shippable core, step 4 (provenance) is separable.
- **Honesty rule (hard MUST):** when reporting that tests pass, paste the ACTUAL runner output; never
  claim a pass not run.
- **Matrix rule:** this is a CLI-grammar/contract change; validate on the full CI matrix (3 OS ×
  Python 3.8–3.14) before completion — local green is not done.
- Sync `docs/cli.md` + `docs/configuration.md` + CHANGELOG; run `/assess documentation` after.
- Commit **path-scoped** (only the files changed); **never push** without explicit human approval.
- Only after CI-green + approval, move this IPD from `.agents/plans/pending/` to
  `.agents/plans/executed/`.

## Workflow history
- 2026-07-12 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS
  APPLIED; PR-001..PR-006 all FIXED/FIXED-IN-PLAN; 4 open questions resolved interactively. Readiness:
  GO (pending human approval to execute).
