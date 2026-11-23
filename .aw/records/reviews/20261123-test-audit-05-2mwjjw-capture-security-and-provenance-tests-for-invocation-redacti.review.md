# Review findings: ipd 2mwjjw

- Subject-Id: 2mwjjw
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-05-2mwjjw-capture-security-and-provenance-tests-for-invocation-redacti.ipd.md` (front matter, Goal, E-01 to E-05, V-01 to V-05, conventions, findings, proposed changes, deferrals, scope check, required tests, documentation sync, open questions, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Proofreading kept the H2 heading list and order, E/V ids, checkbox states, Execution state values, and item field names. Substantive rewrites of the E-items, V-items, scope, and gate are recorded under Findings, not here.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One long sentence listing four modules and two cleanups | Opening sentence, then a numbered list of the four defects in plain terms (what is written, why), then one sentence on E-item ordering | One idea per sentence; state the consequence before the mechanism; define terms at first use. |
| Goal | No diagram | One sentence naming the single ordering edge (E-01 after E-02) | Requirement 12: one edge among five items is clearer as a sentence than as a diagram. |
| E-01 to E-04 | Lists of behaviors to test with no expected values ("verified", "pinned") | Each required test states its input and the exact asserted value | An executor cannot reproduce "test the branch" consistently; exact values make the item checkable. |
| Project conventions | Two bullets | Adds coverage before and after, the `addopts` workaround, `isolated_cwd`, the event-record keys, the `gitleaks` constraint, the diagnostic redactor, and the matrix rule | The executor needs each fact to make the E-items pass first time. |
| Citations | Bare module names and "70% coverage" | Symbol anchors (`get_invocation`, `phase.__enter__`, `ProvenanceFileProxy.readlines`, `_populate_hash_fields`) | `IPD-C801`: line numbers go stale before execution. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (6 paths as authored, 11 after review), E-01 to E-05, and the production code each item exercises: `src/pubrun/capture/invocation.py:get_invocation`, `src/pubrun/capture/redaction.py` (`_redact_dict_keys`, `_redact_any`, `_redact_value_string_heuristics`, `redact_env_vars`, `redact_argv`), `src/pubrun/capture/file_io.py:ProvenanceFileProxy` and `_populate_hash_fields`, `src/pubrun/core.py` (`phase.__enter__`, `report`, `artifact`, `_handle_inactive`), `src/pubrun/capture/process.py:get_process_info`, `src/pubrun/capture/host.py:get_host`, `src/pubrun/capture/python_runtime.py:environment_kind`, `scripts/sanitize_paths.py`.

1. Yes: after review the plan changes what `manifest.json` records under `invocation.inputs` (a documented output format) and what the redactor removes from env and argv values.
2. Yes: `redaction.py` and the argv path of `invocation.py` are the code that keeps secrets out of `manifest.json`.
3. Yes, moderately: 5 E-items across 4 task groups, touching three production modules and six test modules.
4. Yes: 11 paths after review, matching the E-items exactly.
5. Medium: a redaction regression would write secrets into manifests that users share. Each change is small and reversible, and every new assertion is mutation-checked.

AW-TIER: complex

### Step R1

- Checked: every cited path and symbol against lane HEAD `dbe4ac5`. `tests/test_invocation.py` does not exist (E-01 creates it). `get_invocation` step "3. Re-run Replication Engine" computes `rerun_command` from raw `argv`, and the later "Rebuild command_line and rerun_command from redacted argv" block overwrites it. `ProvenanceFileProxy.read1`, `readlines`, `readinto1`, and `truncate` bodies are uncovered in the baseline coverage data. `tomli>=1.1.0; python_version < '3.11'` is in `[project] dependencies`.
- PR-001 (defect 1, found by probe): argv `["train.py", "--key-file", "id_rsa", "--password", "train.py"]` with `compute_md5 = true` gave `argv` and `command_line` with `[REDACTED]`, but `invocation.inputs` recorded `path: "id_rsa"`, its `real_path`, and its MD5. Input discovery iterates `argv[1:]` before `redacted_argv` exists.
- PR-002 (defect 2, found by probe): `redact_env_vars({"NOTES": "key sk-proj-<20+ chars>"})` and `redact_argv(["--note=sk-proj-..."])` left the key in place. `openai_pattern` is `sk-[a-zA-Z0-9]{20,}`, which stops at `proj-`. `_DIAG_PREFIXED_KEY_RE` (`\bsk-[A-Za-z0-9_-]{8,}`) catches the same key in diagnostics, so only the value heuristic misses it.
- PR-003 (defect 3, found by probe): `sys.argv = ["s.py", Path("a/b"), "--lr=0.1"]` gave `capture_state == {"status": "failed", "detail": "TypeError: expected string object, got 'PosixPath'"}`. The cause is `shlex.join(argv)` in the dead step-3 block; `redact_argv` stringifies, so with the block removed capture completes. With `argv_enabled = false`, `redact_argv` returns `list(argv)` unchanged, so a second fix is needed there.
- PR-004 (defect 4, found by probe): `phase.__enter__` handles `"cprofile"` and `"yappi"` and has no `else`, so backend `"pyinstrument"` ran with no log line and no profile file. `docs/configuration.md` `[capture.profiling]` says "If the selected backend is unavailable, logs a warning and skips". The authored E-04 asked for a test of an "unknown profiling backend warning", which cannot pass on the current code.
- PR-009: E-04 said "`PYENV_VERSION` `\"pyenv\"`" as if `"pyenv"` were an `environment_kind` value. `environment_kind` returns `{"environment_kind": ..., "pyenv": bool}`; the item now asserts `pyenv is True` with kind `"system"`.

### Step R2

- Checked: author lint (`aw ipd lint --phase author --agent`: clean, 1 info `IPD-Z603`), the E/V bijection, and each E-item by prototype in a scratch clone at lane HEAD `dbe4ac5`. Every revised E-item and V-item mutation in the plan was run there.
- Prototype results: the plan's subset gave `303 passed` on Python 3.14.6 (fixed order), `303 passed` on Python 3.12.3 (random order, seed 12345), and `303 passed` on Python 3.14.6 in random order with seeds 777, 1, 2, and 3. The full suite in random order gave `1956 passed, 2 skipped in 440.52s` against a baseline of `1902 passed, 2 skipped`. `python3 scripts/sanitize_paths.py --check --all` exited 0. With the three production files reverted and the new tests kept, exactly the five defect tests failed across `tests/test_invocation.py`, `tests/test_redaction.py`, `tests/test_explicit_api.py`, and `tests/test_capture_fallbacks.py` (`5 failed, 85 passed`).
- PR-005: the first prototype of a false-positive test asserted that `desk-` followed by 20 letters is kept; it failed because the existing `openai_pattern` has no word boundary and redacts `de[REDACTED]`. That is over-redaction, not a leak; the plan keeps the existing pattern, adds an anchored one, and records the over-redaction as a Carrier-Declined deferral.
- PR-006: E-03 as written would open one path twice for the two `readlines` hint cases. A probe showed that two opens of one path merge into a single record (`registration_count`), so the second case overwrote the first. The item now uses two files and selects records by name.
- PR-007: the first E-04 prototype read `message` and `data` from annotation events and failed with `KeyError`; events carry `name` and `payload`. Its `pyenv` test also survived the "delete `PYENV_VERSION`" mutation, because `tmp_path` contains the test name `test_pyenv_version_env_var` and so matched the `pyenv` executable-path check. The fixture now pins `sys.executable` to a fixed path. The first `active_run` fixture reset `phase._yappi_active` by assignment, which left the attribute behind and failed `test_missing_yappi_backend_warns_and_skips` under random order (seed 12345); the fixture now uses `monkeypatch.setattr(..., raising=False)`.
- PR-010: the V-items asked only for passing output. Every authored test target already passed at HEAD, so a passing run proves nothing. Each V-item now names one-line mutations; each was applied in the prototype and failed exactly the named test.
- PR-012: a literal `sk-proj-...` string in `tests/test_redaction.py` made `gitleaks detect` report `generic-api-key`, which the `gitleaks` pre-commit hook would reject. The item now requires concatenated fake keys, as `tests/test_capture_isolation.py` already does, and V-02 runs `gitleaks`.

### Step R3

- Checked: the full security form. The plan now changes `redaction.py` and the argv path of `invocation.py`, which keep secrets out of `manifest.json`. Defects 1 and 2 are secret leaks into a file users share; both fixes only remove data from the manifest and add no new output. The new `_PREFIXED_KEY_VALUE_RE` is anchored with `\b` and needs 20 characters after `sk-`, matching the strength of the existing pattern; `test_short_sk_text_is_kept` fails if it is widened to 4. The inputs guard compares the redacted and raw string at the same index, so it drops a value only when redaction changed it, and the `argv_enabled = false` test shows discovery is unchanged when redaction is off. The redacted value also does not appear in the log at `DEBUG`. Tests use fake keys built by concatenation, no network, and no subprocess beyond the existing suite.

### Step R4

- Checked: the `AGENTS.md` "no code-pinning tests" rule (no new test reads production source; the one `grep` in V-01 is review evidence, not a test), right-sizing, sibling scopes (`bzi46m`, `gzc672`, `m66tfv`, `g18xdt`, `7y0gmc`, `ic6z4s`, `bwoyan`), documentation truth, and the gate.
- PR-008: E-01 asked for new internal helpers `_inspect_script` and `_discover_argv_inputs`. No finding or test needs them, and they would enlarge the diff in secret-guarding code. Review removed them as over-scope.
- PR-011: `## Spec / documentation sync` said "N/A" and the gate told the executor to move the plan by hand. With the four fixes, `docs/manifest.md` (`invocation.inputs`, and the missing `"unknown"` `entrypoint_type` value that E-01 now asserts) and `CHANGELOG.md` `### Fixed` need updates. The gate now has the five-element execution contract.
- Sibling scopes: no pending plan declares any 2mwjjw path except `CHANGELOG.md` (`bzi46m`), where each plan adds its own bullet. E-04's capture-engine tests go in a new `tests/test_capture_fallbacks.py` to stay out of `tests/test_capture_engines.py`, which `g18xdt` edits. `g18xdt` defers its `tests/test_sanitize_paths.py` skip to this plan; E-05 covers it.

### Step R5

- Checked: the eight viewpoints in `.aw/system/workflows/release-review/00-run-protocol.md`. QA and testing: covered by PR-006, PR-007, and PR-010. Architect and software engineer: PR-003 and PR-008 (the fix removes code rather than adding helpers). Power user: a researcher passing `--key-file` or `--credentials` to a training script had that file's path and MD5 recorded, which PR-001 fixes. Novice: an unknown backend name gave no hint why profiling did nothing, which PR-004 fixes. Stakeholder: the plan now ships four user-visible fixes, so `Work-Kind` changed from `chore` to `bug` and the `CHANGELOG.md` entry is required. UI/UX: no interface change.

### Step R6

- Checked: whether the plan should become a Set. It has 5 E-items (the followability guidance is at most 5) and 4 task groups (the size threshold is 5). Lint reports `IPD-Z603` because review raised `- Scope-Paths:` from 6 to 11 against a guidance of 8; that lint is advisory only. The added paths are the production file and documentation for each defect a test exposes, and splitting them from their tests would leave a test plan whose new tests fail. No split is recommended.

### Step R7

- Checked: the Set `test-audit` orchestrator `vdxiw8` child-table row for Order 05 and its E-05 confirm item, and the other children's `- Scope-Paths:` and `- Item-Dependencies:`. `vdxiw8` names this plan's area ("invocation, redaction & file I/O tests"), which still holds. No child depends on `2mwjjw` except the orchestrator. `g18xdt` carries its `tests/test_sanitize_paths.py` deferral to `2mwjjw`; E-05 discharges it.

### Step S5

- Checked: open questions (none as authored, none added), deferrals (three, each `Carrier-Declined` with a reason: the push-gated CI matrix run, the unanchored `sk-` over-redaction, and the profiling documentation that already matches). Every finding is `fixed`, so no finding at or above `HIGH` remains open or deferred, and no escalation is required.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | UNDER-SCOPE | R1 (secret leak in tested path) | `src/pubrun/capture/invocation.py:get_invocation` discovery loop iterates raw `argv[1:]`; probe recorded `id_rsa` path and MD5 | A value redacted from `argv` was still recorded in `invocation.inputs` with its path and MD5. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 computes `redacted_argv` before discovery and skips any index redaction changed; tests check `inputs`, `repr(result)`, and the log. |
| PR-002 | high | UNDER-SCOPE | R1 (secret leak in tested path) | `src/pubrun/capture/redaction.py:_redact_value_string_heuristics` `openai_pattern`; probe left `sk-proj-...` unredacted | Hyphenated `sk-` keys in env and argv values were not redacted. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 adds anchored `_PREFIXED_KEY_VALUE_RE`; tests cover env, JSON, and positional forms plus a false-positive guard. |
| PR-003 | medium | UNDER-SCOPE | R1 (capture failure) | `get_invocation` step 3 `shlex.join(argv)`; probe `TypeError: expected string object, got 'PosixPath'` | A `Path` in `sys.argv` failed the whole `invocation` section; the `argv_enabled = false` path had the same flaw. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 deletes the dead block and stringifies discovery; E-02 stringifies the `redact_argv` early return; two tests fail before the fix. |
| PR-004 | high | IN-SCOPE | R1 (unexecutable item) | `src/pubrun/core.py:phase.__enter__` has no `else`; `docs/configuration.md` `[capture.profiling]` promises a warning | E-04 asked to test an unknown-backend warning that the code never emits. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04 adds `else: raise ValueError("unknown backend")` so the existing handler logs; the test fails before the fix. |
| PR-005 | low | IN-SCOPE | R2 (assertion premise) | `openai_pattern` redacts `de[REDACTED]` inside `desk-...` | An unanchored existing pattern over-redacts; a test asserting the opposite would fail. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | The false-positive test uses `sk-short` and `sk-proj-tiny`; the over-redaction is a Carrier-Declined deferral (safe direction). |
| PR-006 | medium | IN-SCOPE | R2 (unspecified technique) | Probe: two opens of one path give one record | E-03's two `readlines` hint cases on one file would merge into one record. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03 uses `partial.bin` and `full.bin` and selects records by name. |
| PR-007 | medium | IN-SCOPE | R2 (assertion cannot fail; order leak) | Event keys `name`/`payload`; `tmp_path` contains `pyenv`; `phase._yappi_active` exists only after first use | Three test mechanics were wrong: event keys, a `pyenv` test that could not fail, and a fixture leaking a class attribute under random order. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04 names the event keys, pins `sys.executable`, and restores the attribute through `monkeypatch`; five random-order seeds pass. |
| PR-008 | low | OVER-SCOPE | R4 (gold-plating) | E-01 "extract small internal helpers `_inspect_script` and `_discover_argv_inputs`" | A refactor no finding needs, in secret-guarding code. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Removed; E-01 says not to add them. |
| PR-009 | low | IN-SCOPE | R1 (wrong value) | `src/pubrun/capture/python_runtime.py:environment_kind` returns `pyenv` as a separate bool | E-04 treated `"pyenv"` as an `environment_kind` value. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04 asserts `pyenv is True` with kind `"system"`. |
| PR-010 | medium | IN-SCOPE | R2 (evidence cannot prove the change) | Every authored target passed at HEAD | V-items asked only for passing output. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Each V-item names defect checks and one-line mutations, each verified in the prototype to fail the named test. |
| PR-011 | medium | UNDER-SCOPE | R4 / S7 (doc sync; execution contract) | `docs/manifest.md` `invocation` table; plan gate "move this plan to `.aw/records/plans/executed/`" | Documentation sync said N/A despite output changes, and the gate lacked the execution contract. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | `docs/manifest.md` and `CHANGELOG.md` added to scope and sync; gate has the five-element contract. |
| PR-012 | medium | IN-SCOPE | R2 (commit would be rejected) | `gitleaks detect` `generic-api-key` on a literal `sk-proj-` test string | The new redaction test's fake key would fail the `gitleaks` pre-commit hook. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 requires concatenated fake keys; V-02 runs `gitleaks`. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `complex` | `standard` | After review the plan changes secret-guarding code and a documented manifest field | yes |
| D-2 | Fix the four probe-found defects in this plan, or defer them | Fix here, each with a test that fails first | Characterize current behavior; `xfail(strict=True)`; defer to a new backlog item | Each fix is a few lines on a path this plan already tests; a characterization test would pin a secret leak as correct; the review lane cannot file a backlog item; Remediation Risk is Low, so the Fix Bar requires fixing | yes |
| D-3 | How to redact hyphenated `sk-` keys | Add an anchored pattern beside the existing one | Replace the existing pattern | Replacing it would change existing over-redaction; adding keeps every current redaction | yes |
| D-4 | Where to put process, host, and `python_runtime` tests | New `tests/test_capture_fallbacks.py` | `tests/test_explicit_api.py` (as authored); `tests/test_capture_engines.py` | They are not explicit-API tests, and `g18xdt` edits `tests/test_capture_engines.py` | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. The E/V id set is unchanged (E-01 to E-05, V-01 to V-05, `Highest E allocated: 05`). `- Item-Dependencies:` is unchanged (`none`). `- Scope-Paths:` grew from 6 to 11 paths; each addition was prototyped and validated in this round (full suite in random order, the subset on two Python versions, every defect check and mutation check), and `aw ipd lint --phase review-finalize` reports only the advisory `IPD-Z603`. No question remains, so no second pass is needed.

AW-REVIEW: DONE
