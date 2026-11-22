# Review findings: ipd e1fwy2

- Subject-Id: e1fwy2
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step T

1. Yes — extends published `schemas/manifest.schema.json` (`$defs.timing` and `$defs.subprocess_record`), changes `Run` timing lifecycle and `elapsed_seconds` semantics, and changes `ArtifactWriter.write_artifacts()` write ordering relied on by sibling plans `8co0wy`, `vrr1fv`, and `3tvesf`.
2. No — does not touch redaction, `meta_ref` allowlist, commit helpers, worktree isolation, or sandbox enforcement.
3. No — 5 E-items across 5 closely coupled files (`schemas/manifest.schema.json`, `src/pubrun/tracker.py`, `src/pubrun/writer.py`, `tests/test_timing_accuracy.py`, `tests/test_manifest_schema.py`).
4. Yes — `- Scope-Paths:` lists all five files.
5. Yes — `schemas/manifest.schema.json` enforces `"additionalProperties": false`, `tests/test_writer.py::DummyRun` duck-types `Run`, and `tracker.py` locking guards against the async hardware-thread manifest-overwrite race.

AW-TIER: complex

### Step R1

- Checked: Verified every code, schema, test, backlog, and sibling-plan citation against `src/pubrun/tracker.py`, `src/pubrun/writer.py`, `src/pubrun/core.py`, `schemas/manifest.schema.json`, `tests/test_manifest_schema.py`, `tests/test_tracker.py`, `tests/test_writer.py`, `tests/test_quality.py`, `tests/test_api.py`, `tests/fixtures/sample_manifest.json`, `.aw/records/backlog/graduated/20261121-pubrun-improve-01-6hp1zu-timing-accuracy.backlog.md`, and sibling plans `nr63qr`, `8co0wy`, `vrr1fv`, and `3tvesf`. Surfaced and fixed `DummyRun` incompatibility (PR-001), ghost-manifest schema scope error (PR-002), and startup/freeze timing lifecycle hazards (PR-003).

### Step R2

- Checked: Verified 1:1 `E-*`/`V-*` bijection (`E-01..E-05` to `V-01..V-05`), `- Scope-Paths:` fence, `- Item-Dependencies: none`, concrete diff and pasted-output demands in every `V-*`, runtime-demonstration reachability (all V-items demand diffs or `pytest` runs, reachable by construction), absence of hardcoded mutable record-tree counts, and execution contract in `## Approval and execution gate`. Surfaced and fixed non-compliant "STOP and report" scope-fence text and hand-rolled lifecycle move instructions (PR-004).

### Step R3

- Checked: Verified raw process-local `time.perf_counter()` counter values are never serialized into `manifest.json` or `.pubrun.lock`, restrictive `0o077` umask and unique temp-file atomic writes in `src/pubrun/writer.py::_atomic_json_write` stay intact, and host-safety exception swallowing in `ArtifactWriter.write_artifacts` is preserved.

### Step R4

- Checked: Applied engineering rubric sections A (correctness/data integrity), C (architecture/operability), D (anti-regression/domain invariants), E (testing/verification), F (KISS, fallback principles), right-sizing/conceptual density, and spec/documentation sync (deferred honestly to `3tvesf`). Surfaced and fixed missing `import time` in `writer.py`, `DummyRun` duck-typing (`PR-001`), ghost-mode attribute init order before `mkdir()` and finalized-only freeze semantics (`PR-003`), `anyOf` JSON Schema 2020-12 syntax (`PR-006`), and missing `TestDoubleStop` / `test_timing_values_are_floats` regression test coverage (`PR-005`).

### Step R5

- Checked: Evaluated through all eight reviewer personas (`QA/QC`, `Testing & regression`, `UI/UX`, `Architect`, `Software engineer`, `Power user`, `Novice`, `Stakeholder`). QA/QC and Software engineer caught `DummyRun` `AttributeError`, ghost-manifest whole-schema mismatch, startup-vs-finalized freeze bug, ghost attribute initialization order, missing `import time`, and `KeyboardInterrupt` path nuances; Testing & regression added `TestDoubleStop`, `test_timing_values_are_floats`, and scoped clock monkeypatching guidance; Architect confirmed single `manifest.json` write alignment with `startup-perf` (`t1xqpw`); UI/UX, Power user, Novice, and Stakeholder confirmed self-describing timing metadata, clear interval separation without summing overlaps, and backlog `6hp1zu` alignment.

### Step R6

- Checked: Evaluated decomposition and conceptual density across `E-01..E-05`. `e1fwy2` is child 01 of 4 in Set `timing-acc` with 5 E-items across 5 Scope-Paths (1 focused concern/file per E-item). Right-sized; no further split warranted.

### Step R7

- Checked: Verified cross-plan consistency across Set `timing-acc` (`nr63qr`, `e1fwy2`, `8co0wy`, `vrr1fv`, `3tvesf`) and coordination with `startup-perf` (`t1xqpw`). Confirmed all `$defs.timing` fields/enums match `vrr1fv` and `3tvesf`, all `$defs.subprocess_record` fields/enums match `8co0wy`, and single final `manifest.json` write preserves `t1xqpw` compatibility.

### Step S5

- Checked: Audited `OQ-01` and `OQ-02`. Updated `- Owner:` from `maintainer (confirmed upon plan approval)` to `plan author` per `steps/s5-questions.md` so author-proposed defaults are not misattributed as already answered by the maintainer, and recorded `D-1`, `D-2`, and `D-3` as reversible decisions confirmed upon human approval of this plan. No blocking open question remains.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-03` & Proposed changes #4 | Unconditional `self.run._mark_finalization_end()` and omitted `import time` | Added `import time`, `_artifacts_written` init, and `hasattr` guard for `DummyRun` | Prevented `tests/test_writer.py` regression (Req 5, 6) |
| Proposed changes #1, #3 | Ambiguous freeze timing on `to_manifest_dict()`, ghost-mode attribute init order unspecified, startup `duration_clock`/`elapsed_basis` implicit | Initialized timing attrs before `mkdir()`, froze timing only on finalized `to_manifest_dict()`, specified exact startup/ghost/finalized metadata | Closed concurrency and ghost-mode lifecycle defects (Req 5, 6) |
| `E-05`, Proposed changes #5, `V-05` | Demanded whole-schema validation of ghost manifests; omitted `TestDoubleStop` and `test_timing_values_are_floats` | Scoped ghost validation to `$defs.timing` subschema; added regression test commands, `KeyboardInterrupt` path note, and scoped clock patching | Made validation satisfiable and complete (Req 6, 11) |
| Proposed changes #2 & `V-01` | Wrote `utc_datetime \| null` shorthand for nullable `$ref` timestamps | Specified JSON Schema 2020-12 `anyOf` pattern matching `ended_at_utc` | Prevented invalid JSON Schema draft syntax (Req 5, 7) |
| `OQ-01`, `OQ-02`, `Project conventions`, `Findings` | Listed `- Owner: maintainer (confirmed upon plan approval)` and unanchored code refs | Set `- Owner: plan author` with explicit approval confirmation note and `path::Symbol` citations | Enforced honest owner attribution and citation format (Req 7, 10) |
| `Approval and execution gate` | Included "STOP and report" scope fence and hand-rolled lifecycle move | Updated to `--scope-reason`/`--scope-ack` fence and conditional runner/executor `aw ipd finalize` ownership | Conformed to execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R4 | `tests/test_writer.py::DummyRun:35-50`, `src/pubrun/writer.py::ArtifactWriter.write_artifacts:52-91` | Unconditional `self.run._mark_finalization_end()` in `ArtifactWriter.write_artifacts()` would raise `AttributeError` on `tests/test_writer.py::DummyRun` (silently swallowed before writing `manifest.json`/`methods`), and `writer.py` lacks `import time`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required `import time`, `_artifacts_written` initialization, and `hasattr(self.run, "_mark_finalization_end")` guard in `E-03`, Proposed changes #4, and `V-03`. Recommendation strength: very strong. |
| PR-002 | HIGH | IN-SCOPE | R1/R4 | `src/pubrun/tracker.py::Run.__init__:128-136`, `schemas/manifest.schema.json:417-423`, `tests/test_manifest_schema.py::_config_subschema:46-52` | Proposed changes #5 directed validating ghost `Run` dicts against the full `schemas/manifest.schema.json`, which fails on unrelated empty `{}` section dicts (`invocation`, `git`, `host`) left by ghost mode. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Scoped ghost-run schema validation to `$defs.timing` subschema (mirroring `_config_subschema`) while keeping full-schema validation for finalized, startup, and legacy v1.0 manifests (`D-3`). Recommendation strength: very strong. |
| PR-003 | HIGH | IN-SCOPE | R1/R4 | `src/pubrun/tracker.py::Run.__init__:106-180`, `src/pubrun/tracker.py::Run._bootstrap_engines:337-345`, `src/pubrun/tracker.py::Run.to_manifest_dict:631-666` | Freezing timing on `to_manifest_dict()` without checking `self._finalized` would freeze startup/hardware-thread snapshots, and initializing timing attributes after `mkdir()` would raise `AttributeError` in ghost mode; also startup/ghost metadata values were under-specified. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified initializing all timing attributes before `mkdir()`, freezing timing only inside finalized `to_manifest_dict()` (allowing `write_artifacts()` to refresh `t3` after `config.resolved.json`), and explicit startup/ghost/finalized metadata values. Recommendation strength: very strong. |
| PR-004 | HIGH | IN-SCOPE | R2/R4/S7 | `.aw/records/plans/pending/20261121-timing-acc-01-e1fwy2-manifest-timing-schema-and-tracker-monotonic-lifecycle.ipd.md:280-285` (`Approval and execution gate`) | Execution gate contained prohibited "STOP and report" scope-fence wording and instructed a hand-rolled move to `executed/` instead of conditional runner/executor `aw ipd finalize`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced gate items 2 and 5 with compliant `--scope-reason`/`--scope-ack` fence wording and conditional runner/executor `aw ipd finalize` ownership. Recommendation strength: very strong. |
| PR-005 | MEDIUM | IN-SCOPE | R1/R4/S5 | `tests/test_quality.py::TestDoubleStop:75-92`, `tests/test_api.py::test_timing_values_are_floats:285-295`, `src/pubrun/core.py::audit_run:226-228` | `OQ-01`/`OQ-02` carried `- Owner: maintainer (confirmed upon plan approval)` for author-resolved defaults; `TestDoubleStop` and `test_timing_values_are_floats` were omitted from validation commands; `KeyboardInterrupt` test path and scoped clock patching needed clarification. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `OQ-01`/`OQ-02` `- Owner:` to `plan author` and recorded `D-1`/`D-2`; added `TestDoubleStop` and `test_timing_values_are_floats` to `Required tests / validation` and `V-05`; clarified interruption test paths and scoped fake-clock patching. Recommendation strength: strong. |
| PR-006 | LOW | IN-SCOPE | P/R7 | `schemas/manifest.schema.json:389-396`, `.aw/records/plans/pending/20261121-timing-acc-01-e1fwy2-manifest-timing-schema-and-tracker-monotonic-lifecycle.ipd.md:48-49,95-108,142-143` | Proposed changes #2 used informal `utc_datetime \| null` notation rather than JSON Schema 2020-12 `anyOf`, flowchart nodes used bare method names, and conventions/findings used unanchored code references. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `anyOf` nullable `$ref` schema form, aligned flowchart labels with exact method names, and updated code citations to `path::Symbol`. Recommendation strength: strong. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Should `timing.elapsed_seconds` equal monotonic `workload_seconds` (`[t1, t2]`) with self-describing `elapsed_basis: "workload"`, `duration_clock: "monotonic"`, and `interval_scope: "tracked_interval"`? | Keep the author's resolution (`OQ-01`): `elapsed_seconds = workload_seconds` with additive self-describing metadata, attributed to `plan author` and confirmed upon human plan approval. | Keep `elapsed_seconds` as full session duration including startup/teardown (leaves short scripts inflated unless every caller migrates). | Backlog `6hp1zu` (`Problem and why it matters` and `Implementation guidance` item 5), sibling consumer plan `vrr1fv`, and pre-approval human sign-off gate. | yes |
| D-2 | Should `ArtifactWriter.write_artifacts()` write `config.resolved.json` before `manifest.json` and track post-manifest writer duration in memory on `Run.writer_overhead_seconds`? | Keep the author's resolution (`OQ-02`), attributed to `plan author` and confirmed upon human plan approval. | Write `manifest.json` twice to persist its own write latency (adds redundant fsync/replace I/O and conflicts with `t1xqpw`). | `src/pubrun/writer.py::ArtifactWriter.write_artifacts`, backlog `6hp1zu`, and coordination with `startup-perf` (`t1xqpw`). | yes |
| D-3 | How should `tests/test_manifest_schema.py` schema-validate ghost-mode `Run` timing without failing on unrelated empty `{}` section dicts? | Validate ghost-mode `Run.to_manifest_dict()["timing"]` against the `$defs.timing` subschema (mirroring existing `_config_subschema`), while validating finalized, startup, and legacy v1.0 manifests against the full schema. | Populate synthetic `capture_state` in every unrelated ghost section in `tracker.py` (out-of-scope behavioral change for ghost runs that never write manifests). | `src/pubrun/tracker.py::Run.__init__:128-136` and `tests/test_manifest_schema.py::_config_subschema:46-52`. | yes |
