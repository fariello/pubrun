# IPD: Declare all selected_behavior keys in the manifest schema

- Date: 2026-11-24
- Kind: child
- Concern: The published manifest JSON Schema declares only two of the six import-mode behavior flags that pubrun can write to `pubrun_imports.selected_behavior`, so it does not type-check the other four and does not detect a new undeclared flag.
- Scope: In `schemas/manifest.schema.json`, declare `patch_subprocesses`, `patch_console`, `signal_hooks`, and `force_console` as booleans under `properties.pubrun_imports.properties.selected_behavior`, add a description, and close the object with `additionalProperties: false`. Add schema conformance tests for real manifests written under every import mode, plus accept and reject tests for the subschema, to `tests/test_manifest_schema.py`. Add one `CHANGELOG.md` entry.
- Scope-Paths: schemas/manifest.schema.json, tests/test_manifest_schema.py, CHANGELOG.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Declare patch_subprocesses, patch_console, signal_hooks, and force_console under pubrun_imports.selected_behavior in schemas/manifest.schema.json
- Work-Kind: followup
- Priority: low
- From-Backlog: 31kpnv
- Set: 31kpnv
- Order: 1
- Highest E allocated: 03
- Author: opencode
- Id: 4r4ymv
- Approval: 2026-11-25, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006 fixed; review record `.aw/records/reviews/20261124-31kpnv-01-4r4ymv-declare-all-selected-behavior-keys-in-the-manifest-schema.review.md`.
- 2026-11-25 to-review (opencode): graduated from backlog item `31kpnv` into a review-ready plan.
- 2026-11-25 draft (opencode): created.

## Goal

Every manifest records the effective import-mode behavior flags in `pubrun_imports.selected_behavior`. Across the six import modes, pubrun writes five base flags (`auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, `signal_hooks`) for `auto`, `noauto`, `nopatch`, `noconsole`, and `minimal`, plus a sixth flag (`force_console`) for `full`. The shipped schema `schemas/manifest.schema.json` declares only `auto_start` and `global_hooks`. After this plan:

1. The schema declares all six flags that `src/pubrun/_modes.py::MODES` can produce, each as a boolean with a description.
2. The schema rejects a non-boolean value for any of the six flags and rejects an undeclared flag. A flag added to `src/pubrun/_modes.py::MODES` without a schema update therefore fails `tests/test_manifest_schema.py`.
3. A real manifest written under every import mode defined in `src/pubrun/_modes.py::MODES` (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`) validates against the schema, and a test proves it.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Schema

- [ ] E-01 In `schemas/manifest.schema.json`, replace the `selected_behavior` property inside `properties.pubrun_imports.properties` with the declaration given in "Proposed changes" item 1.
  - Depends on: none
  - Expected outcome: (1) `selected_behavior` keeps `"type": ["object", "null"]`. (2) It gains a non-empty `description` string. (3) Its `properties` declare exactly these six keys, each with `"type": "boolean"` and a non-empty `description` string: `auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, `signal_hooks`, `force_console`. (4) It carries `"additionalProperties": false`. (5) It has no `required` list. (6) No other part of the schema changes, and the file keeps its 4-space multi-line JSON indentation.
  - Execution state: pending

### Task group 2: Tests and changelog

- [ ] E-02 In `tests/test_manifest_schema.py`, add the helper and three tests specified in "Proposed changes" item 2.
  - Depends on: E-01
  - Expected outcome: `tests/test_manifest_schema.py` extracts the `selected_behavior` subschema (for example via `_selected_behavior_subschema`) and verifies: (1) real subprocess-generated manifests for every mode in `src/pubrun/_modes.py::MODES` record the expected `selected_mode` and exact `selected_behavior` dictionary and validate against `schemas/manifest.schema.json`; (2) `null`, the two-key legacy shape, and `{}` validate against the `selected_behavior` subschema; and (3) string values for every declared flag, a non-boolean integer value (`{"force_console": 1}`), and an undeclared flag (`{"auto_start": True, "bogus_flag": True}`) each raise `jsonschema.ValidationError`. Every test asserts on real manifests or `jsonschema` validation results, and none reads production source code. All tests in `tests/test_manifest_schema.py` pass.
  - Execution state: pending

- [ ] E-03 Add one bullet to `CHANGELOG.md` under `## [Unreleased]` `### Fixed`.
  - Depends on: E-01
  - Expected outcome: One bullet, written for users with no em or en dashes, states that the manifest schema now declares the `patch_subprocesses`, `patch_console`, `signal_hooks`, and `force_console` flags in `pubrun_imports.selected_behavior` as booleans and rejects undeclared flags there, and that manifests pubrun writes are unchanged.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `tests/test_manifest_schema.py` is the drift guard for the schema. Its module docstring says the schema "drifted silently as manifest sections were added over time", and `tests/test_manifest_schema.py::test_full_manifest_conforms_to_schema` is a hard gate. It loads the schema with `_schema()` and extracts subschemas with helpers such as `_timing_subschema` that return a copy of the target dictionary (and attach `$defs` when `$ref` resolution is needed).
- `jsonschema` is a dev and test dependency only (`pyproject.toml` lists `"jsonschema>=4.0"` under `[project.optional-dependencies].dev`), and `tests/test_manifest_schema.py` skips cleanly through `pytest.importorskip("jsonschema")` when it is absent. In `pyproject.toml`, pubrun's only conditional runtime dependency is `tomli>=1.1.0; python_version < '3.11'` (zero runtime dependencies on Python 3.11+).
- An import mode is chosen once per process: `src/pubrun/_bootstrap.py::select_mode` keeps the first selection and warns on a later conflicting one. `tests/test_full_mode.py::TestExistingModesConsoleOff` and `tests/test_full_mode.py::TestFullModeBehavior.test_full_wraps_console_end_to_end` therefore drive modes in child processes with `subprocess.run([PYTHON, "-c", script], ...)` and the environment `{**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""}`. `tests/conftest.py::_subprocess_pythonpath` prepends this checkout's `src` to `PYTHONPATH` for the whole session, so the child imports the code under test.
- Test outcomes, not code structure (`AGENTS.md` "Agent execution contract"): tests must not read production source with `inspect`, `ast`, regex, or substring search. Loading the schema JSON file is how the existing tests work; the schema is a published data contract, not source code.
- `AGENTS.md` "Matrix-validation discipline" names `schemas/manifest.schema.json` explicitly: a change there must pass the CI matrix (3 operating systems x Python 3.8 to 3.14) before the work counts as complete. Pushing requires an explicit human instruction.
- `CHANGELOG.md` `## [Unreleased]` already has `### Added`, `### Changed`, `### Documentation`, and `### Fixed` subsections. Earlier schema fixes (for example "Manifest schema now accepts the `imported-transitive` packages mode") are recorded as `### Fixed` bullets.
- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone: an offset expires before this plan executes (advisory `IPD-C801`).

## Findings

Measured at authoring on Linux with Python 3.14.6 and `jsonschema` 4.26.0, at `HEAD` `3c6ae50` (and verified at review against `HEAD` `712a13b`).

The producer chain for `pubrun_imports.selected_behavior`:

| Step | Code | What it does |
|---|---|---|
| 1 | `src/pubrun/_modes.py::MODES` | Maps each of the six mode names to a dictionary of boolean flags. Every mode has `auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, and `signal_hooks`. Only `full` also has `force_console: True`. |
| 2 | `src/pubrun/_bootstrap.py::select_mode` | Stores a copy of the chosen mode's dictionary (`get_mode_behavior(mode)`) in the module global `_selected_behavior`. |
| 3 | `src/pubrun/_bootstrap.py::get_import_metadata` | Returns `"selected_behavior": _selected_behavior`, which is `None` before any mode is selected. |
| 4 | `src/pubrun/tracker.py::Run._get_import_metadata` | Writes that dictionary as the manifest's `pubrun_imports` section. |

The current schema entry inside `"pubrun_imports"` in `schemas/manifest.schema.json`:

```json
                "selected_behavior": {
                    "type": [
                        "object",
                        "null"
                    ],
                    "properties": {
                        "auto_start": {
                            "type": "boolean"
                        },
                        "global_hooks": {
                            "type": "boolean"
                        }
                    }
                },
```

The object has no `additionalProperties` keyword, so JSON Schema accepts any extra key with any value. A check at authoring against the extracted subschema gave:

| Input | Current result |
|---|---|
| `{"patch_console": "yes"}` | accepted |
| `{"force_console": 1, "bogus": true}` | accepted |
| `{"auto_start": "x"}` | rejected: `'x' is not of type 'boolean'` |

A manifest written under each mode in a child process, then validated against the current schema, passed for all six modes. The recorded keys were the five base flags for `auto`, `noauto`, `nopatch`, `noconsole`, and `minimal`, and the five plus `force_console` for `full`. Real manifests therefore conform today; the gap is that the schema does not describe or check four of the keys. The same check run against the proposed declaration (six booleans and `additionalProperties: false`) accepted `None` and the two-key legacy shape `{"auto_start": true, "global_hooks": false}`, and rejected `{"bogus": true}` and `{"patch_console": "yes"}`.

History of the key set, from `git log -- src/pubrun/_modes.py`:

- Commit `6ff6837` (2026-06-04) defined modes with only `auto_start` and `global_hooks`.
- Commit `6bd3284` (2026-06-20) added `patch_subprocesses`, `patch_console`, and `signal_hooks`.
- Commit `d3f77c1` (2026-07-05) added the `full` mode and its `force_console` flag.

Manifests written before 2026-06-20 therefore carry only two flags. That is why the declaration must not list any key as `required`.

`docs/manifest.md` (heading `` ## `pubrun_imports` ``, row `selected_behavior`) already documents all six flags, including `Includes "force_console": true only for "full".`, so only the schema lags.

Consumers that read the flags: `src/pubrun/tracker.py::Run._bootstrap_engines` reads `patch_subprocesses`, `patch_console`, `signal_hooks`, and `force_console` with `.get(...)` defaults; `src/pubrun/tracker.py::Run._merge_and_migrate` reads `patch_subprocesses`; `src/pubrun/core.py::_execute_boot_sequence` reads `auto_start`; `src/pubrun/report/reproducibility.py::_assess_capture_completeness` checks `behavior.get("patch_subprocesses") is False`; and `src/pubrun/__main__.py` prints the five base flags in doctor output. None reads the schema, so the schema change does not affect them.

```mermaid
flowchart TD
    A["src/pubrun/_modes.py::MODES: 5 base boolean flags (+ force_console in full)"] --> B["src/pubrun/_bootstrap.py::select_mode: stores _selected_behavior"]
    B --> C["src/pubrun/_bootstrap.py::get_import_metadata"]
    C --> D["src/pubrun/tracker.py::Run._get_import_metadata writes pubrun_imports.selected_behavior"]
    D --> E{"Validated against schemas/manifest.schema.json"}
    E -->|"every key declared and boolean"| F["accepted"]
    E -->|"non-boolean value or undeclared key"| G["rejected: tests/test_manifest_schema.py fails"]
```

## Proposed changes (ordered, validatable)

1. **Schema declaration (E-01).** Replace the `selected_behavior` entry in `schemas/manifest.schema.json` with this exact 4-space multi-line JSON declaration (matching the file's layout so the diff stays limited to this entry):

   ```json
                "selected_behavior": {
                    "type": [
                        "object",
                        "null"
                    ],
                    "description": "Effective import-mode behavior flags for the selected mode. Null until a mode is selected. Manifests written before 2026-06-20 carry only auto_start and global_hooks.",
                    "properties": {
                        "auto_start": {
                            "type": "boolean",
                            "description": "Importing pubrun starts tracking automatically."
                        },
                        "global_hooks": {
                            "type": "boolean",
                            "description": "Obsolete unified flag kept for backward compatibility; true when process-global hooks are permitted."
                        },
                        "patch_subprocesses": {
                            "type": "boolean",
                            "description": "The mode permits the subprocess spy."
                        },
                        "patch_console": {
                            "type": "boolean",
                            "description": "The mode permits redirecting sys.stdout and sys.stderr (console tee)."
                        },
                        "signal_hooks": {
                            "type": "boolean",
                            "description": "The mode permits signal and excepthook handlers."
                        },
                        "force_console": {
                            "type": "boolean",
                            "description": "The mode forces the console tee on regardless of capture_mode. Present only for the full mode."
                        }
                    },
                    "additionalProperties": false
                },
   ```

2. **Tests (E-02).** Add to `tests/test_manifest_schema.py`:
   - Helper `_selected_behavior_subschema(schema)`: asserts each key along `schema["properties"]["pubrun_imports"]["properties"]["selected_behavior"]` exists and returns a shallow copy `dict(...)` of that subschema (matching `_config_subschema` and `_timing_subschema`).
   - `test_import_mode_manifest_selected_behavior_conforms`, parametrized over `sorted(MODES)` imported from `pubrun._modes` (six modes today: `auto`, `full`, `minimal`, `noauto`, `noconsole`, `nopatch`). For each mode, run a child process with `subprocess.run([sys.executable, "-c", script, mode], capture_output=True, text=True, timeout=60, cwd=str(tmp_path), env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""})`. The script imports `pubrun.<mode>` with `importlib.import_module`, takes `get_current_run()` or calls `start()` when no run is active (`noauto` and `minimal` do not auto-start), records `str(run.run_dir)`, calls `stop()`, and prints `run_dir` as its last stdout line. The parent asserts `returncode == 0` (showing stderr on failure), loads `Path(run_dir) / "manifest.json"` using `encoding="utf-8"`, asserts `manifest["pubrun_imports"]["selected_mode"] == mode`, asserts `manifest["pubrun_imports"]["selected_behavior"] == get_mode_behavior(mode)`, and calls `jsonschema.validate(manifest, _schema())`. Add `import os` and `import subprocess` at module level if they are not already imported there.
   - `test_selected_behavior_schema_accepts_null_legacy_and_partial_shapes`, parametrized over `None`, `{"auto_start": True, "global_hooks": True}`, and `{}`. Each validates against `_selected_behavior_subschema(_schema())` without raising.
   - `test_selected_behavior_schema_rejects_bad_values`, parametrized over `{key: "yes"}` for each of the six keys declared in `selected_behavior.properties` (six cases), `{"force_console": 1}` (non-boolean integer), and `{"auto_start": True, "bogus_flag": True}` (undeclared flag). Each must raise `jsonschema.ValidationError`.

3. **Changelog (E-03).** Example wording under `### Fixed`: "**Manifest schema now declares every import-mode behavior flag.** `pubrun_imports.selected_behavior` in `schemas/manifest.schema.json` now declares `patch_subprocesses`, `patch_console`, `signal_hooks`, and `force_console` as booleans, alongside `auto_start` and `global_hooks`, and rejects flags it does not declare. Previously the schema checked only two of the six flags pubrun can write. Manifests are unchanged; older manifests with only `auto_start` and `global_hooks` still validate."

## Deferred / out of scope (with reason)

- Declaring the shape of `pubrun_imports.requests[]` items (including `effective_behavior`, which holds the same six flags). The schema types `requests` only as `"type": "array"`. The backlog item names only `selected_behavior`, and widening the work to every request field would need its own decisions about `caller` and legacy shapes.
  - Carrier-Declined: no defect report exists for `requests[]`, and `docs/manifest.md` `` ### `pubrun_imports.requests[]` `` already documents the fields for readers.
- Closing `pubrun_imports` itself with `additionalProperties: false`. It is open on purpose: `src/pubrun/tracker.py::Run._get_import_metadata` falls back to `{"selected_mode": None, "capture_state": {"status": "unavailable"}}`, and `capture_state` is not declared in that section.
  - Carrier-Declined: changing that fallback or the section's openness is a separate contract decision that the backlog item does not ask for.
- Adding `full` to the Lock File `import_mode` row in `docs/manifest.md`. Commit `142672074b` filed it as a sibling backlog item together with this one. It touches a different file and does not depend on this plan.
  - Carrier: kiir0y
- Updating the stale mode list in the `src/pubrun/_bootstrap.py::select_mode` docstring. Commit `142672074b` filed it as a sibling backlog item together with this one. It touches a different file and does not depend on this plan.
  - Carrier: szf342
- Running the changed tests on the GitHub Actions CI matrix (3 operating systems x Python 3.8 to 3.14). `AGENTS.md` "Matrix-validation discipline" requires it for a `schemas/manifest.schema.json` change. A push needs an explicit human instruction, so this plan validates on Linux only and V-02 records which operating system and Python version ran.
  - Carrier-Declined: a push needs explicit human authorization, so no plan can carry it; GitHub Actions runs the matrix automatically on the next push or pull request to `main`.

## Scope check

- Over-scope: none. The tests and changelog entry are the minimum needed to prove and announce the schema change.
- Under-scope: none. `docs/manifest.md` already lists all six flags, so no documentation edit is needed. No code produces or reads the schema at runtime, so no source file changes.

## Required tests / validation

- `python3 -m pytest tests/test_manifest_schema.py --no-cov -q -v` passes, covering every import mode re-derived from `src/pubrun/_modes.py::MODES`, the `null`/legacy/partial acceptance shapes, and all non-boolean and undeclared-key rejection cases.
- `python3 -m pytest tests/test_import_modes.py tests/test_full_mode.py --no-cov -q` passes. These suites cover the mode presets and the `full` mode end to end.
- The full suite (`aw suite --no-cache`) has no failure that also passes on unmodified `HEAD`.
- Mutation checks on `schemas/manifest.schema.json`, each restored afterwards and verified with `git diff -- schemas/manifest.schema.json` matching the E-01 diff and a passing `python3 -m pytest tests/test_manifest_schema.py --no-cov -q`:
  - Remove `"additionalProperties": false` from `selected_behavior` AND remove the trailing comma after the preceding `"properties": { ... }` block so the file remains valid JSON. `python3 -m pytest tests/test_manifest_schema.py -k rejects_bad_values --no-cov -q` must report exactly 1 failure (the `bogus_flag` case), with no `JSONDecodeError`.
  - Remove the `"force_console"` property from `selected_behavior.properties` AND remove the trailing comma after the preceding `"signal_hooks"` entry so the file remains valid JSON. `python3 -m pytest tests/test_manifest_schema.py -k "selected_behavior_conforms and full" --no-cov -q` must fail with `Additional properties are not allowed ('force_console' was unexpected)`.
- Before committing `CHANGELOG.md`, run the working-tree dash check (must assert at least one added line and exit `0` with `dashes=0`):
  `python3 -c "import subprocess, sys; lines = [l for l in subprocess.check_output(['git', 'diff', '-U0', '--', 'CHANGELOG.md'], text=True).splitlines() if l.startswith('+') and not l.startswith('+++')]; assert lines, 'no added CHANGELOG.md lines in working tree'; bad = [l for l in lines if '\u2014' in l or '\u2013' in l]; print(f'added_lines={len(lines)} dashes={len(bad)}'); sys.exit(1 if bad else 0)"`
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- `schemas/manifest.schema.json` (E-01) is the published contract that changes.
- `CHANGELOG.md` (E-03) records the change.
- `docs/manifest.md` already documents all six flags in the `selected_behavior` row under `` ## `pubrun_imports` ``, so it is not edited.
- `docs/functional_spec.md` (`## 4. Manifest Structure`) says the manifest "MUST strictly adhere to the JSON Schema defined in `schemas/manifest.schema.json`". It names no individual field, so it is not edited.
- `.aw/records/specs/` contains no `.spec.md` file, so no spec is touched.

## Open questions

### OQ-01: Should `selected_behavior` reject undeclared keys with `additionalProperties: false`?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: Yes. Declaring the keys without closing the object would still accept `{"bogus": true}`, so a flag added to `src/pubrun/_modes.py::MODES` without a schema update would pass every test. That is the silent drift the module docstring of `tests/test_manifest_schema.py` describes. The top-level manifest object and most `$defs` entries in the schema already use `additionalProperties: false`. Every flag pubrun has ever written (Findings, "History of the key set") is declared, so no real manifest, old or new, is rejected; the six-mode check at authoring confirmed this for current manifests.

### OQ-02: Should the five flags that every current mode writes be `required`?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: No. Manifests written before commit `6bd3284` (2026-06-20) carry only `auto_start` and `global_hooks`, and `force_console` appears only for `full`. A `required` list would reject those older manifests, which `pubrun status`, `show`, and `diff` still read. The declaration constrains key names and value types only.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- schemas/manifest.schema.json` and confirm it changes only the `selected_behavior` entry using the file's 4-space multi-line JSON layout. (2) Paste the output of `python3 -c "import json; s=json.load(open('schemas/manifest.schema.json', encoding='utf-8')); b=s['properties']['pubrun_imports']['properties']['selected_behavior']; print(sorted(b['properties'])); print({k: v['type'] for k, v in b['properties'].items()}); print(b['additionalProperties'], 'required' in b, b['type'], bool(b.get('description')), all(bool(v.get('description')) for v in b['properties'].values()))"`, which must print the six sorted key names, `'boolean'` for each, and `False False ['object', 'null'] True True`. (3) Paste the schema meta-validation (`validator_for(schema).check_schema(schema)`, e.g. `test_schema_is_valid_draft`) result line from the V-02 run showing `PASSED`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: (1) Paste the pytest verbose result lines and summary line from `python3 -m pytest tests/test_manifest_schema.py --no-cov -q -v` proving all three new behavioral groups pass (non-binding pointers: `test_import_mode_manifest_selected_behavior_conforms`, `test_selected_behavior_schema_accepts_null_legacy_and_partial_shapes`, `test_selected_behavior_schema_rejects_bad_values`), re-deriving at execution time that every mode currently in `src/pubrun/_modes.py::MODES` ran in a subprocess and validated against `schemas/manifest.schema.json`, that `None`/legacy-two-key/`{}` validated, and that every declared flag's non-boolean case, the integer case, and the undeclared-key case raised `jsonschema.ValidationError`. The subprocess conformance cases observe real manifests written by the child process started in E-02 through `src/pubrun/tracker.py::Run._get_import_metadata`. (2) Paste the summary line of `python3 -m pytest tests/test_import_modes.py tests/test_full_mode.py --no-cov -q`. (3) Paste the `aw suite --no-cache` summary, and for any failure paste the same test's result on unmodified `HEAD`. (4) Paste the failing output of both valid-JSON mutation checks in "Required tests / validation", followed by `git diff --stat -- schemas/manifest.schema.json` and a passing `python3 -m pytest tests/test_manifest_schema.py --no-cov -q` after restoring `schemas/manifest.schema.json` to its exact E-01 state. (5) State which operating system and Python version ran the tests, and that the CI matrix was not run.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: (1) Paste `git diff -- CHANGELOG.md`, showing one added bullet under `## [Unreleased]` `### Fixed` that names the four added flags and says manifests are unchanged. (2) Paste the output and exit status `0` of the working-tree dash check command in "Required tests / validation", showing `added_lines>=1` and `dashes=0`. (3) Paste the exit status of `python3 scripts/sanitize_paths.py --check --all`, which must be `0`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no blocking open questions.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries (`schemas/manifest.schema.json`, `tests/test_manifest_schema.py`, `CHANGELOG.md`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`. The mutation checks edit `schemas/manifest.schema.json` only temporarily; restore it and do not commit the mutations.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit 4r4ymv -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize 4r4ymv`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize 4r4ymv` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
