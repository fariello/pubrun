# Decisions & assumptions - assess use-cases (20260708-231828)

## Concern / scope assessed

- Concern: **use-cases** (lens: `.agents/workflows/assess/lenses/use-cases.md`) - whole-scenario
  coverage, complementing functionality (capabilities) and edge-cases (boundary inputs).
- Scope: whole project. No `$ARGUMENTS` scope narrowing was given beyond the concern.

## Project conventions discovered

- No `GUIDING_PRINCIPLES.md`; principles inferred from README.md (l.7 simple/zero-dependency/no
  syntax hijacking), functional_spec.md 1.1 (Non-Goals) + 3.2 (Lightweight Import Requirement),
  CONTRIBUTING.md l.69 (zero-dependency, lightweight footprint). Applied the harness's universal
  fallback for the Fix Bar + multi-persona review.
- Plans lifecycle: `.agents/plans/pending/` -> `.agents/plans/executed/` (canonical default;
  matches existing dated IPDs in `executed/`). `pending/` was empty at assessment time.
- Doc-sync contract: AGENTS.md requires `/assess documentation` after user-visible behavior
  changes - reflected in the IPD's spec/doc-sync section.

## Actors enumerated (grounding the personas)

1. **Novice researcher** - `import pubrun`, `pubrun init`, reads `status`/`methods`; wants zero
   ceremony and honest first-use output.
2. **Power user** - explicit API (`start`/`stop`/`tracked_run`/`audit_run`/`paused`), import
   modes, `diff`, `res/cpu/mem`, CLI aliases; uses `pubrun run --mode` for scripts they can't edit.
3. **HPC operator / integrator** - Slurm/PBS array jobs, `pubrun meta` + `PUBRUN_META_REF`
   parent-child hydration; many concurrent runs under one output dir.
4. **Reproducibility stakeholder / maintainer** - trusts the manifest, methods text, citation,
   redaction; cares that documented behavior actually works.
5. **QA engineer** - scenario-based test coverage of the lifecycle classifications.

## Key decisions

- **Verdict: strong.** The evidence (two exploration passes over CLI, examples, and all 39 test
  files) showed nearly every rubric scenario has both implementation and a test. This was
  deliberately NOT inflated into a long findings list; only genuine, evidence-backed gaps were
  recorded. The lens warns against duplicating functionality/testing/edge-cases work, so findings
  are framed as *scenario* gaps and cross-referenced.
- **U1 (resources alias) rated High severity, Low remediation risk.** It is a documented
  backward-compatibility promise that produces a hard error - directly reproduced at the shell
  (`pubrun resources` -> "unknown command 'resources'"). High severity because it breaks a
  documented user path; Low remediation risk because the fix mirrors the existing `ui` alias
  pattern. Fix-by-default applies.
- **Fix-by-default with nothing deferred.** Every finding's remediation risk is Low or
  Low-Medium; none reaches the Medium-High deferral bar. Recorded explicitly.

## What was intentionally NOT proposed (and why)

- **Real Jupyter-kernel and real Textual-TUI integration tests.** Deferred as legitimately
  out of scope, not as a deferred finding: standing up a live IPython ZMQ kernel or live Textual
  render harness in CI is **Medium-High Remediation Risk on the Complexity axis** (heavy, flaky,
  test-only weight against the "stupidly simple / zero-dependency" principle) for marginal added
  assurance. The guard *logic* (`resolve_console_mode` Jupyter/non-TTY branches; TUI parser/
  digest/resource-view) is already unit-tested via monkeypatch/mock. Left as-is.
- **The four Roadmap items** (Sphinx/MkDocs, plugin model, `register_artifact`,
  `register_metadata`) - declared future scope, traceable to a stated roadmap; not under-scope.
- **Windows positive-path tests** - Windows currently only has `skipif` guards. Whether Windows
  deserves positive assertions is the **compatibility** lens's call; cross-referenced, not
  proposed here, to avoid duplicating that lens.

## Assumptions (to confirm with the maintainer - see IPD Open Questions)

1. `resources` should be *made to work* as an alias (docs already promise it), rather than the
   promise being removed from the docs.
2. The dead `tests/scripts/hpc_node.py` fixture should be repaired and wired into the new HPC
   end-to-end test, rather than deleted in favor of a fresh inline child script.
3. Two-live-runs-in-one-output-dir is an intended, supported scenario (must not corrupt the run
   listing / lock scanning), not merely best-effort.

## Open questions for the user

Carried into the IPD's "Open questions" section (the three assumptions above).
