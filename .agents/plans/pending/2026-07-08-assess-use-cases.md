# IPD: Assess use-cases - close the narrow scenario gaps in pubrun

- Date: 2026-07-08
- Concern: use-cases (use-case / scenario coverage)
- Scope: whole project (pubrun library + CLI + docs + tests)
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Verify that pubrun handles the full range of reasonable ways it is actually used - the real
actors, scenarios, and contexts - and close the gaps that matter. pubrun's purpose is
low-friction, durable execution provenance for Python research runs, used today by the author
and a handful of URI researchers on laptops and HPC clusters (docs/research-use.md). For that
audience, a *documented capability that silently fails* or an *unverified user-facing scenario*
directly undermines the trust the tool exists to provide.

The headline result of this assessment is that use-case coverage is **strong**: nearly every
scenario in the lens rubric (auto-start, all import modes, crashed/interrupted/broken-pipe/ghost
classification, HPC hydration, diff/methods/redaction, clean/combined/self-check/inspect/bench/
cite, empty state, Jupyter guard) has both an implementation and a test. The findings below are
narrow, specific gaps - not a systemic problem.

## Project conventions discovered (Step 0)

- Guiding principles: no `GUIDING_PRINCIPLES.md`; principles are stated across README.md
  (l.7: "stupidly simple, zero-dependency", "no syntax hijacking"), docs/functional_spec.md
  1.1 Non-Goals (l.27-34) and 3.2 Lightweight Import Requirement (l.60-69: import must not slow
  startup, must not fail on missing optional deps, must not wrap streams or write output unless
  configured), and CONTRIBUTING.md l.69 (correctness, maintainability, zero-dependency/
  lightweight footprint). Applied as the universal fallback per the harness.
- Pending-plans location/format used: `.agents/plans/pending/` (currently empty); terminal dir
  `.agents/plans/executed/` (canonical default; matches existing dated IPDs there).
- Contributor/spec-sync contract: AGENTS.md (doc-sync discipline: run `/assess documentation`
  after user-visible behavior changes) + CONTRIBUTING.md.
- Stack / relevant context: pure-Python library + argparse CLI (`pubrun`/`pbr`), `src/` layout,
  runtime deps zero on 3.11+ / `tomli` on 3.8-3.10; supports 3.8-3.14 across Linux/macOS/Windows;
  extensive `tests/` suite (39 files) with platform `skipif` guards.

## Findings

Severity = impact if left alone; Remediation Risk = the Fix-Bar gate for acting now.
Personas: **Power** = sophisticated power user; **Novice** = complete newcomer; **Stakeholder**
= research maintainer / reproducibility stakeholder; **QA** = scenario-based QA engineer.

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| U1 | High | Low | Power, Stakeholder | Backward-compat / CLI | The `resources` alias is documented as a backward-compatible alias of `res`, but `pubrun resources` **errors** with "unknown command". The dispatch block handles `res/resources/monitor/chart/stats/cpu/mem`, but only `res`,`cpu`,`mem` are registered as argparse subparsers, so argparse rejects `resources`/`monitor`/`chart`/`stats` before dispatch. A user following the docs hits a hard failure. | README.md:263 (claims alias); `__main__.py:2390` (dispatch handles the strings); no `add_parser("resources"...)` near `__main__.py:2256`; reproduced: `pubrun resources` -> exit "unknown command 'resources'" |
| U2 | Low | Low | Power | Dead code / clarity | `monitor`,`chart`,`stats` appear only in the dispatch `set` at `__main__.py:2390` and are unreachable (no parser, not documented). Dead scaffolding that misleads maintainers about what aliases exist. | `__main__.py:2390` |
| U3 | Medium | Low | Novice, QA | First-use lifecycle | `pubrun init` (writes `.pubrun.toml`, prints getting-started guidance) is a primary first-use scenario but has **no test**. The most common newcomer entry point is unverified; a regression (e.g. clobbering an existing config, malformed output) would ship silently. | command at `__main__.py:1996`,`:2615`; no test references `init` (test-suite inventory) |
| U4 | Medium | Low | QA, Stakeholder | Failure-scenario coverage | Two named lifecycle-classification scenarios are asserted only indirectly: (a) **SIGHUP** is named in docs/README as an "interrupted" trigger but has no test (only SIGINT + SIGTERM asserted); (b) **SIGKILL -> crashed** is tested only via the `pubrun run` exit-code path, not via the lock-file "crashed" classification of a genuinely SIGKILL'd tracked process (that path uses synthetic dead PIDs). These are exactly the "process died hard" cases the crashed/interrupted feature exists for. | README.md:323,331 (SIGHUP listed); `test_signals.py:422` (SIGHUP only in docstring); `test_signals.py:250,425` (SIGINT/SIGTERM); `test_import_modes.py:509` (SIGKILL via run exit code); `test_status.py:239` (crashed via synthetic dead PID) |
| U5 | Medium | Low-Medium | Stakeholder, QA | HPC multi-process scenario | The HPC parent-child hydration scenario (the flagship cluster use case) is tested at the unit level (env->config, hydrate-from-parent, meta security) but there is **no end-to-end test** that actually runs a child process with `PUBRUN_META_REF` set and asserts the child skips heavy capture then stitches the parent context back on `show`/`methods`. A mock fixture `tests/scripts/hpc_node.py` exists for exactly this but is **not invoked by any test** (dead fixture). | `test_config.py:170`, `test_reports.py:147`, `test_quality.py:376` (unit-level); `tests/scripts/hpc_node.py` (unreferenced) |
| U6 | Low | Low-Medium | Power, QA | Concurrency scenario | Two independent live tracked runs in separate processes at the same time (a normal HPC array reality: many `python script.py` under one output dir) is not exercised. Existing tests cover thread-level singleton `start()` and multiple runs *at rest* (diff/clean/combined), but not two simultaneously-live runs writing to the same `./runs/`. Risk is a race on shared listing/lock scanning. | `test_new_features.py:466` (thread singleton); `test_cli.py:427`, `test_combined.py:70` (runs at rest) |
| U7 | Low | Medium | Stakeholder | Documented deliverable | docs/research-use.md l.22-34 says "A public example workflow should be added under `examples/` before public release". This deliverable **already exists** (`examples/minimal-research-workflow/` covers all 7 required steps and has a test), so the doc's future-tense "should be added" is stale and understates the project. Reader-facing accuracy gap, not a missing capability. | docs/research-use.md:22-34 (says "should be added"); `examples/minimal-research-workflow/` (exists); `test_example_minimal_research_workflow.py:13` |

## Proposed changes (ordered, validatable)

Fix by default; each item is safe and well-scoped. Ordered by user impact.

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|--------------------|--------|-------|------------------|------------|
| 1 | U1, U2 | Make `resources` an actual working alias of `res` (register it via argparse `aliases=["resources"]` on the `res` subparser, matching how `ui` does `aliases=["tui","gui"]`), OR - if the alias is unwanted - remove the claim from README/docs and delete the dead strings. **Recommend making it work** (docs already promise it; least surprise). While here, drop `monitor`/`chart`/`stats` from the dispatch set (U2) since they are undocumented and unreachable. | `src/pubrun/__main__.py` (~:2256 add_parser, :2390 dispatch set), README.md:263, docs/cli.md | Low | `pubrun resources` renders the same chart as `pubrun res` (new test asserting parity); `pubrun monitor` still errors cleanly; existing res/cpu/mem tests pass |
| 2 | U3 | Add a test for `pubrun init`: fresh dir -> writes `.pubrun.toml`, prints guidance, exits 0; and the safety case of running `init` when `.pubrun.toml` already exists (assert it does not silently clobber, or documents/prompts per current behavior). | `tests/test_cli.py` (or a new `test_init.py`) | Low | New test passes; encodes current behavior; if it reveals a clobber bug, that becomes a follow-up finding |
| 3 | U4 | Add a SIGHUP interrupted-classification test (mirror the SIGINT test) and a lock-file "crashed" test driven by an actually SIGKILL'd child (POSIX; `skipif(win32)`), not a synthetic dead PID, so the real kill path is covered. | `tests/test_signals.py`, `tests/test_status.py` | Low | New tests pass on Linux/macOS; skipped on Windows with a reason |
| 4 | U5 | Add one end-to-end HPC-hydration test that spawns a child with `PUBRUN_META_REF=meta.json` (reusing/repairing `tests/scripts/hpc_node.py`), asserts the child skips heavy footprint capture, then asserts `show`/`methods` stitches the parent hardware/deps back in. Wire `hpc_node.py` into this test (or delete it if superseded). | `tests/` (new `test_hpc_hydration_e2e.py` or extend `test_reports.py`), `tests/scripts/hpc_node.py` | Low-Medium | New test passes; asserts child manifest lacks heavy sections AND rendered output contains parent context; the previously-dead fixture is now exercised |
| 5 | U6 | Add a test that launches two tracked runs as separate subprocesses concurrently against one `./runs/` dir and asserts both produce distinct valid manifests and `pubrun status` lists both without error/corruption. | `tests/` (extend `test_status.py` or new file) | Low-Medium | New test passes reliably (bounded, deterministic sync; no sleeps-as-timing); no lock/listing race |
| 6 | U7 | Update docs/research-use.md l.22-34 from future-tense "should be added" to present-tense pointing at the existing `examples/minimal-research-workflow/`, listing the 7 steps it already demonstrates. | docs/research-use.md | Low | Doc references the real path; `/assess documentation` (doc-sync) would pass |

## Deferred / out of scope (with reason)

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| (none) | - | - | All findings clear the Fix-Bar (Remediation Risk Low to Low-Medium); none reach Medium-High. Nothing is deferred. | - |

Explicitly out of scope (legitimately, per lens "distinguish scenarios the project should
support from those out of scope"), so NOT findings:

- **Real Jupyter-kernel / real Textual-TUI integration tests.** Current coverage monkeypatches
  `_is_jupyter_kernel` and mocks the TUI app. Standing up a live IPython ZMQ kernel or a live
  Textual render harness in CI is high Remediation-Risk on the Complexity axis (heavy, flaky,
  adds test-only weight against the "stupidly simple / zero-dependency" principle) for marginal
  scenario assurance. The guard *logic* is already unit-tested. Leave as-is.
- **The four Roadmap items** (Sphinx/MkDocs, plugin model, `register_artifact`, `register_metadata`;
  README l.415-422) are declared future scope, traceable to a stated roadmap - not under-scope.
- **Windows-only positive assertions.** Windows currently only has `skipif` guards. The
  compatibility lens (not use-cases) owns whether Windows deserves positive-path tests; noted
  here as a cross-reference, not proposed.

## Scope check

- Over-scope (untraceable to a need; propose removal/deferral): the dispatch strings
  `monitor`/`chart`/`stats` (`__main__.py:2390`) - unreachable, undocumented; Step 1 removes them.
- Under-scope (needed capability missing; propose adding): the `resources` alias is *promised*
  but non-functional (U1) - Step 1 adds the real alias. No other missing capabilities found; the
  feature surface matches the documented scenarios.

## Required tests / validation

- New/changed tests from Steps 1-5 all pass under the project's CI command `pytest tests/ -v`
  across the 3-OS x Python-3.8-3.14 matrix (POSIX-only cases guarded with `skipif(win32)` and a
  reason). Clear `__pycache__` before local runs.
- Step 1 additionally verified by hand: `pubrun resources <run>` == `pubrun res <run>` output.
- Concurrency (Step 5) and HPC-e2e (Step 4) tests must be deterministic (explicit readiness
  sync, no wall-clock sleeps used as ordering) to avoid the load-sensitive flakes already seen
  on busy runners.
- No behavior regression: full suite green before and after.

## Spec / documentation sync

Behavior/doc changes touch user-visible surface, so per AGENTS.md doc-sync discipline:

- Step 1 changes the CLI alias set -> update README.md:263 and docs/cli.md (and re-verify no
  other doc claims an alias that does not resolve). Run `/assess documentation` afterward.
- Step 6 is itself a documentation-sync fix (research-use.md).
- Add a CHANGELOG.md entry for the `resources` alias fix (user-visible behavior change).

## Open questions

1. **U1 direction:** make `resources` a working alias (recommended - docs already promise it), or
   remove the promise from the docs? Assumption in this plan: make it work.
2. **U5 fixture:** repair and wire in `tests/scripts/hpc_node.py`, or write a fresh inline child
   script and delete the unreferenced fixture? Assumption: reuse/repair it (it exists for this).
3. Is two-live-runs-in-one-output-dir (U6) an officially supported scenario the project wants to
   guarantee, or best-effort? The fix assumes "supported, should not corrupt listing/locks".

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution, and it is
NOT auto-executed. Recommended next steps:

1. Review this IPD (optionally run the `plan-review` workflow to harden it).
2. On approval, execute the ordered changes, run the validation (`pytest tests/ -v`), and sync
   docs/CHANGELOG.
3. Only then move this IPD from `.agents/plans/pending/` to `.agents/plans/executed/` per the
   project's lifecycle convention.
