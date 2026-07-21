# IPD: Assess bug - manifest `console` section can be empty (startup-manifest wins a finalize race)

- Date: 2026-07-21
- Concern: bug / robustness (manifest completeness + a resulting CI test flake)
- Scope: `src/pubrun/writer.py` (startup vs final manifest), `src/pubrun/tracker.py` (finalize/write
  ordering), and the affected test `tests/test_full_mode.py`. No public-API change intended.
- Status: to-review
- Approval: (set when a human approves; omit until then)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Workflow history
- 2026-07-21 /assess (opencode / its_direct/pt3-claude-opus-4.8-1m-us): investigated a CI flake, traced
  it to a real manifest-finalization gap; proposed fixes. Written after a wrong initial guess (see Goal).

## Goal

A CI job (`ubuntu-latest, 3.11`) failed once on
`tests/test_full_mode.py::TestExistingModesConsoleOff::test_mode_default_console_off[nopatch]` with
`AssertionError: stdout: CONSOLE_MODE=None`. It passed on the next commit and passes 10/10 locally, so
it is intermittent. This IPD records the ACCURATE root cause (a manifest finalization race, NOT a
test-isolation global leak, which was an earlier incorrect hypothesis) and proposes a durable fix so the
manifest's `console` section is never empty in a completed run, and the test cannot flake.

Correcting the record: the flake was first guessed to be the cross-test console-mode global-leak class
addressed by `conftest.py::pubrun_state_isolation`. That is wrong: the failing test runs pubrun in a
SUBPROCESS (`tests/test_full_mode.py:87-91`), which a parent-process fixture cannot influence. The real
cause is below.

## Root cause (evidenced)

pubrun writes the manifest at TWO points:

1. **Startup manifest** at import/auto-start: `Writer.write_startup_manifest()` (called from
   `tracker.py:188` and `tracker.py:315`) writes `manifest.json` and explicitly "does not finalize
   state" (`writer.py:93-95`). At that point `self.console_data` is still its initial `{}`
   (`tracker.py:130,156`), so the startup manifest contains `"console": {}` with NO `capture_mode`.
2. **Final manifest** on `stop()`/atexit: `stop()` -> `_finalize_state()` (populates
   `self.console_data = self.console_interceptor.stop()` at `tracker.py:542`) -> `writer.write_artifacts()`
   (`tracker.py:581-583`), which re-runs the idempotent `_finalize_state()` (`writer.py:61`) and emits
   `"console": self.console_data` (`tracker.py:636`) with `capture_mode = "off"`.

Empirically confirmed (local repro): reading `manifest.json` BEFORE `stop()` shows `console: {}`; AFTER
`stop()` it shows `console.capture_mode: "off"`. So `CONSOLE_MODE=None` means the test read a manifest in
which the FINAL finalize had not (yet) landed: the startup manifest (empty `console`) was still the
on-disk content when the test read it, i.e. the child's `stop()`/atexit write raced with, or failed
before, the test's read.

This is a real robustness gap independent of the test: any consumer that reads a run's manifest can, in a
narrow window or on a finalize failure, see a run whose `console` (and by the same pattern other
finalize-only sections) is empty, with no signal distinguishing "not finalized yet" from "genuinely
off". The startup manifest already models incompleteness elsewhere via `capture_state.status`
(`pending`/`timeout`/`complete`), but the `console` section does not carry that marker.

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| B1 | Medium | Low | Operator/QA | manifest completeness | The startup manifest emits `console: {}` (no `capture_mode`); a consumer reading before final finalize sees an empty console section indistinguishable from a real value | `writer.py:93-106`; `tracker.py:130,156,636`; local repro (startup `console: {}`, final `off`) |
| B2 | Medium | Low | QA | flaky test | `test_mode_default_console_off` asserts `CONSOLE_MODE=off` by reading the child manifest, with no wait/guard for finalization, so it flakes if it reads the startup manifest | `tests/test_full_mode.py:70-94` |
| B3 | Low | Low | Operator | diagnosability | A finalize-only manifest section (`console`) carries no `capture_state`, so "not finalized" vs "off" is not machine-distinguishable | `tracker.py:636`; cf. run/timing sections carry `capture_state` at `tracker.py:625,631` |

## Proposed changes (ordered, validatable)

| Step | Src | Change | Files | Remediation Risk | Validation |
|------|-----|--------|-------|------------------|------------|
| 1 | B1 | Make the startup manifest's `console` section self-describing: instead of an empty `{}`, write `{"capture_mode": <resolved-or-off>, "capture_state": {"status": "pending"}}` at startup (mirroring how run/timing use `capture_state`). The final write overwrites it with the real result + `status: complete`. This removes the ambiguous empty section and gives consumers a truthful "not yet finalized" marker. | `src/pubrun/tracker.py` (initial `console_data`), `src/pubrun/writer.py` (startup path) | Low | a startup manifest has `console.capture_mode` present and `console.capture_state.status == "pending"`; the final manifest has the real mode and `status == "complete"`; schema conformance still passes |
| 2 | B2 | Harden the test so it is not order/timing dependent: assert on the FINAL manifest deterministically. The child already calls `pubrun.stop()` (which finalizes synchronously before returning), so read the manifest AFTER `stop()` returns in the child and print that; the parent asserts `CONSOLE_MODE=off` for auto/patched modes. Confirm the child does not read a pre-`stop()` manifest. | `tests/test_full_mode.py` | Low | the test passes deterministically across seeds/repeats (loop it locally, e.g. 50x, and under `-p randomly`) |
| 3 | B1/B3 | Confirm no OTHER finalize-only section shares the empty-vs-real ambiguity (subprocesses, resources, events). If any is emitted empty at startup with no `capture_state`, apply the same `pending` marker for consistency. | `src/pubrun/tracker.py` | Low | audit recorded; any additional sections fixed the same way or explicitly justified as N/A |
| 4 | B1 | Update `schemas/manifest.schema.json` and `docs/manifest.md` if the startup `console` shape changes (it should already allow `capture_state`; verify the `console` object permits `capture_state` and a `pending` status). | `schemas/manifest.schema.json`, `docs/manifest.md` | Low | schema validates both startup and final manifests; conformance test green |

## Deferred / out of scope

| Item | Risk | Axis | Reason | Later step |
|------|------|------|--------|-----------|
| Reworking the two-phase (startup + final) manifest model itself | Med-High | complexity/functionality | The startup manifest is a deliberate feature (a run is observable before it finishes; see the degraded/startup-manifest schema work). Redesigning it is out of scope; this IPD only makes its `console` section self-describing. | Separate design IPD if ever desired |

## Scope check

- Over-scope: not redesigning the startup/final two-phase model; not changing public API or console
  behavior; the fix only makes an already-written section self-describing and de-flakes one test.
- Under-scope (addressed): the ambiguous empty `console` section (B1), the timing-dependent test (B2),
  and consistency of the `capture_state` marker across finalize-only sections (B3).

## Required tests / validation

- Reproduce-and-fix: loop `test_full_mode.py::TestExistingModesConsoleOff::test_mode_default_console_off`
  (all params) many times and under `-p randomly`; must be deterministic green.
- Manifest-shape assertions: a startup manifest has `console.capture_mode` + `console.capture_state.status
  == "pending"`; a completed run has the real mode + `status == "complete"`.
- Schema conformance test green for both startup and final manifests.
- Full suite green locally; validate on the CI matrix (schema/manifest-shape change -> matrix-validation
  discipline applies).
- Honesty rule: paste ACTUAL loop output and the CI matrix result; do not claim de-flaked without the
  repeated-run evidence.

## Spec / documentation sync

- If Step 1/4 changes the startup `console` shape, update `schemas/manifest.schema.json` and
  `docs/manifest.md`, and add a CHANGELOG note ("manifest: startup `console` section now carries a
  `capture_state: pending` marker instead of being empty; fixes an intermittent empty-console read").

## Open questions

1. B1 marker value: at startup, should `console.capture_mode` be the RESOLVED mode (requires resolving
   console mode at startup, which `nopatch` etc. would report as "off") or a literal placeholder until
   finalize? (Recommend the resolved-or-"off" base plus `capture_state: pending`, so it is truthful and
   consistent with the interceptor always being created.)
2. B2: is asserting only the FINAL manifest sufficient, or should the test ALSO assert the startup
   manifest now carries `capture_state: pending` (turning the flake into positive coverage of the fix)?
   (Recommend the latter: convert the bug into a regression test.)
3. Matrix-validation: confirm this is treated as a manifest-contract change (it is) and must go green on
   the full 3-OS x 3.8-3.14 matrix before executed/.

## Approval and execution gate

This IPD is a proposal; it MUST be human-approved before execution and is NOT auto-run. Execution
contract:
- Scope fence: `tracker.py`, `writer.py`, `tests/test_full_mode.py`, and (if the shape changes)
  `schemas/manifest.schema.json` + `docs/manifest.md` + CHANGELOG. No public-API or console-behavior
  change. Anything beyond -> STOP and open a separate IPD.
- Honesty rule (hard MUST): paste the ACTUAL repeated-run/loop output proving de-flake, and the CI matrix
  result; never claim green unrun.
- Matrix-validation: this touches the manifest contract, so it is NOT done on local green alone; push,
  watch the full matrix, fix stragglers before moving to executed/.
- Commits path-scoped; never push without explicit authorization.
- On completion + approval + matrix green, `git mv` to `.agents/plans/executed/` (Status -> executed)
  with a Workflow-history line.
