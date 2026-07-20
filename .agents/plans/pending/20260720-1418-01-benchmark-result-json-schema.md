# IPD: Ship a formal JSON Schema for the benchmark result (`pubrun-benchmark/5`)

- Date: 2026-07-20
- Concern: documentation (machine-readable contract) / interoperability / testing
- Scope: add `schemas/benchmark.schema.json`; a conformance test; docs pointer; NO change to the
  harness output shape (it already emits `/5`). Optional intake-validation helper (see step 4).
- Status: to-review
- Approval: (set when a human approves; omit until then)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / driver

The benchmark result format has a version STRING (`"schema": "pubrun-benchmark/5"`, `harness.py:395`)
but **no machine-readable schema file**. The `manifest.json` format, by contrast, has
`schemas/manifest.schema.json` enforced by a conformance-test gate. Two consequences:

1. **Intake validation is impossible today.** The community-benchmark research (and any future
   validated-intake mechanism) assumes "validate the submission against our schema" - but there is
   nothing to validate against.
2. **The `/5` contract is only implicitly defined** (by the producer code + prose in
   `benchmarks/README.md`). A published, versioned schema is the honest, JOSS-friendly way to define
   the reproducibility artifact's shape.

This IPD adds the schema FILE only. It does not change what the harness emits (the `/5` shape shipped
and is matrix-green in commit `127375a`); it formalizes and gates that shape.

## Verified current `/5` shape (from a real redacted result)

Top-level keys: `schema` (const `"pubrun-benchmark/5"`), `generated_utc`, `generated_local`, `mode`,
`iterations` (int), `warmup` (int), `passes` (int), `baseline_pass` (bool), `git_commit`, `machine`,
`scenario_defs`, `pass_results`, `baseline` (present iff `baseline_pass`), `total_wall_time_s`.

- `scenario_defs`: map name -> `{group, mode, workload, config}` (static, defined once).
- `pass_results`: array of `{pass:int, pass_env, timings:{name:[float,...]}, failures:{name:int},
  skipped?:{name:reason}}`. `timings` are 6dp floats; `skipped` present only when a scenario skipped.
- `baseline`: `{pass:0, uncaptured:true, pass_env, timings, failures, skipped?}` (same compact shape).
- `pass_env`: `{system_memory:{total/free/available/cached_bytes}, load_average:{1min,5min,15min},
  system_iowait_pct}` (Linux-populated; may be partial/absent on other OSes - schema must tolerate).
- `machine`: `{host, hardware, python, pubrun_version, pubrun_commit, python_executable, platform,
  filesystem}` - largely mirrors run-manifest sub-blocks (host/hardware/python).

## Design decisions

1. **Validate the shape, not every nested field.** Lock the top-level structure, `scenario_defs`
   entries, and the pass/baseline shape (timings=arrays of numbers, failures=ints, skipped=strings).
   For `machine` and `pass_env`, be **permissive** (`additionalProperties: true`, most fields
   optional) - they mirror host/hardware detail that varies by OS/Python and is not the contract's
   point. This avoids the manifest-schema drift trap we hit this session (over-tight enums/objects
   failing on one platform). Honest-but-loose beats precise-but-brittle here.
2. **`schema` is a `const`** = `"pubrun-benchmark/5"` so the version is self-checking; when the format
   next changes, bump the const and the file together (mirror the manifest schema's discipline).
3. **The redacted file is the canonical validation target** (it is what gets submitted); the schema
   must accept redacted values (e.g. `"<redacted>"` strings) wherever redaction can land. Verify the
   redacted `/5` validates, not just the unredacted one.
4. **Keep it a SEPARATE file** (`schemas/benchmark.schema.json`), not folded into the manifest schema
   - different artifact, different lifecycle.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Author `schemas/benchmark.schema.json` (Draft 2020-12) matching the verified `/5` shape: strict top-level + scenario_defs + pass/baseline structure; permissive `machine`/`pass_env`; `schema` const; accepts redacted strings. | `schemas/benchmark.schema.json` | Low | it is valid JSON Schema (`check_schema`) |
| 2 | Add a conformance test: a produced `/5` result (both a fresh unredacted AND its redacted copy) validates against the schema; the committed real redacted result validates; a deliberately-broken result fails. Use the dev-only `jsonschema` (already in the `dev` extra). | `benchmarks/test_benchmarks.py` (or a new schema test) | Low | tests pass on the full matrix; the broken case fails |
| 3 | Point the harness + docs at the schema: a short comment in `harness.py` near the `schema` const referencing the file; document it in `benchmarks/README.md`; CHANGELOG entry. | `harness.py` (comment only), `benchmarks/README.md`, `CHANGELOG.md` | Low | doc references the file; `/assess documentation` clean |
| 4 | (Optional, if cheap) a tiny reusable validator hook: a function/CLI-agnostic helper the submit path (or a future intake Action) can call to validate a redacted file against the schema before submission, warning on mismatch. Do NOT add a runtime dep to the shipped library (dev-only tooling). | `benchmarks/harness.py` or a small `benchmarks/validate.py` | Low | validating a good file passes; a bad file is reported |

## Scope check

- Over-scope: do NOT redesign the `/5` shape (shipped + matrix-green); do NOT add `jsonschema` to the
  shipped library's runtime deps (dev/tooling only); do NOT build the community-intake mechanism here
  (that is the separate research/decision - this only provides the schema it would use).
- Under-scope: validating only the unredacted file would miss the actual submission artifact; step 2
  MUST validate the redacted `/5` too.

## Required tests / validation

- The schema is a well-formed Draft 2020-12 document (`validator_for(schema).check_schema`).
- A freshly produced `/5` unredacted result AND its redacted copy both validate; the committed real
  redacted result validates; a corrupted result fails validation (proves the schema has teeth).
- Full CI matrix green: `pass_env`/`machine` vary by OS/Python, so the permissive-there design must be
  confirmed across the matrix, not just locally (per AGENTS.md matrix discipline). This is the one
  reason the change, though small, is matrix-relevant.

## Spec / documentation sync

`benchmarks/README.md` gains a "schema" note pointing at `schemas/benchmark.schema.json`; CHANGELOG
entry ("added a machine-readable JSON Schema for benchmark results"). No manifest-schema change.

## Open questions

1. Strictness of `machine`/`pass_env`: fully permissive (recommended, avoids cross-platform brittleness)
   vs. documenting the common fields as optional-but-typed. Recommend permissive now; tighten later if
   a real consumer needs it.
2. Ship step 4 (the validator hook) now, or leave validation to tests + a future intake mechanism?
   Recommend: include it only if it stays a few lines of dev tooling; otherwise defer to whatever
   intake method is chosen from the community-benchmark research.

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Execution contract:
- Honesty rule (hard MUST): paste ACTUAL test/validation output; never claim an unrun pass.
- Matrix rule: `pass_env`/`machine` vary by platform; validate the schema against real results on the
  full CI matrix before done.
- Commit path-scoped; never push without explicit human approval.
- On completion, `git mv` this IPD to `.agents/plans/executed/` (Status -> executed).

## Workflow history
- 2026-07-20 (opencode / its_direct/pt3-claude-opus-4.8-1m-us): drafted; the `/5` result format has a
  version string but no schema file; proposed adding one + a conformance gate. Proposed 4 steps.
