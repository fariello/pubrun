# Review findings: ipd 2e6xfq

- Subject-Id: 2e6xfq
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-ql671s-01-2e6xfq-read-the-boot-import-conflict-policy-from-every-config-file.ipd.md` (front matter, Mermaid flowchart, E-01 to E-05, V-01 to V-05, conventions, findings, deferrals, scope check, required tests, spec sync, OQ-01, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches the normative text in `## Goal` and E-03 (environment first, then files in `_boot_config_paths()` order, first valid value wins, default `warn`, cache).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation and cross-check boilerplate | Two em dashes around the "as distinct from" clause (`IPD-C802` advisory twice) | Commas and parentheses | Clears both `IPD-C802` advisories; meaning unchanged. |
| E-04 test (5) | "after `.pubrun.toml` is deleted and `reset_state()` is called, it raises" left the repeated `select_mode` calls implicit | States the test repeats both `select_mode` calls before asserting the raise | Requirement 5 (explicit steps): after `reset_state()` there is no selected mode, so a single call cannot conflict. |
| E-04 tests (5) and (8) | "no warning" | "no `PubrunImportModeConflictWarning`" | Requirement 6: an unrelated warning would otherwise fail a correct implementation. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (5 files), 5 E-items in 5 task groups, `_bootstrap.select_mode` callers.

1. Yes: it changes observable behavior of the documented configuration key `[imports].on_conflict` (now honored from two more files) and adds a `docs/configuration.md` sentence; no spec is touched.
2. No: no code that guards private data, commits, worktree isolation, merges, or the sandbox.
3. No: 5 small E-items, two source files, one test file, two doc files.
4. Yes: all 5 files are listed.
5. Moderately: a user who had `on_conflict = "error"` in a deep or user config file will now see a conflicting import raise instead of warn. That is the intended fix, and it is reversible.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/_config_boot.py::_boot_config_paths`, `::_load_toml_file`, `::_extract_toml_key`, `::_load_local_toml`, `::_read_local_toml_key`, `::resolve_import_mode`, `::_global_config_dir`; `src/pubrun/_bootstrap.py::_resolve_conflict_policy` (lazy import of `_read_local_toml_key`, `.lower()` without `.strip()`), `::select_mode`, `::reset_state`, `::get_import_metadata` (`conflict_policy` field); `src/pubrun/resources/default.toml` `on_conflict = "warn"`; `src/pubrun/config.py::load_local_config` (deep file then `.pubrun.toml`, the latter wins); `tests/test_config_capture_modes.py::isolated_home`, `::_write`, `::_non_windows`, `::TestBootDiscovery` (including `test_invalid_mode_in_higher_file_falls_through`); `tests/conftest.py::isolated_cwd`, `::pubrun_state_isolation`; `tests/test_commit_identity.py::TestConfigBootSingleRead::test_read_local_toml_key_preserved_for_bootstrap_conflict_policy`; `tests/test_import_modes.py::TestConflictDetection`; `docs/configuration.md#Configuration Discovery` (paragraph "The import mode chosen at `import pubrun` time" exists); `CHANGELOG.md` `## [Unreleased]` with a `### Fixed` list; `pyproject.toml` `addopts` (coverage) and `pythonpath = ["src"]`; commits `296feab` and `4bd4552` (plan `l7ko8p`, executed) resolve; backlog `ql671s` is graduated.
- Ran the reproduction command on this lane at `9edd0b6` (CPython 3.14.6): it printed `deep exit=0 policy=warn` and `user exit=0 policy=warn`, which matches the plan's claim. Ran the same subprocess with `on_conflict = "error"` in `./.pubrun.toml`: exit 1 with `PubrunImportModeConflictError`, which matches the Findings table row 1.
- Ran `python3 -m pytest tests/test_config_capture_modes.py tests/test_import_modes.py tests/test_commit_identity.py -q --no-cov`: `172 passed in 37.43s` (baseline).
- All citations resolve.

### Step R2

- Checked: E/V bijection (E-01..E-05 to V-01..V-05), Scope-Paths completeness, `Item-Dependencies: none` (correct; `l7ko8p` is already executed), concreteness of each V-item, runtime-demonstration reachability, and the execution contract.
- Reachability: V-01 and V-05 observe the software acting through the reproduction command; the code path is `_bootstrap.select_mode` (triggered by `import pubrun.minimal`) and a direct `_bootstrap._resolve_conflict_policy()` call. V-04 test (10) observes a child process via the same `select_mode` path. Reachable.
- V-02, V-03, and V-04 used test names and a count of tests as the bar, which the test-organization convention forbids (PR-003).
- Gate: resolved questions, a non-STOP scope fence with `--scope-reason`/`--scope-ack`, the honesty rule, path-scoped `aw commit` with never-push, and conditional runner/executor `aw ipd finalize` ownership. Conforming.

### Step R3

- Checked: the change reads local TOML files the user already controls, through the existing best-effort parsers; no network, secrets, or new trust boundary. A value is accepted only from the closed set `ignore`/`warn`/`error`. The `conflict_policy` manifest field already exists and its value set does not change. No findings.

### Step R4

- Checked: rubric A (no writes; reads are idempotent; the module cache `_conflict_policy` and `reset_state()` are unchanged), C (reuses `_boot_config_paths`, `_load_toml_file`, `_extract_toml_key`; no new dependency; lazy import kept), D (invariants: environment beats files, `.pubrun.toml` beats deep beats user, invalid or malformed falls through, default `warn`; each is mapped to an E-04 test), E (in-process tests through public `select_mode`, plus one subprocess end-to-end test; Windows path covered by patching `sys.platform`), F (KISS), right-sizing (each E-item is one file and one concern), and spec/doc sync (`docs/manifest.md` `conflict_policy` rows and the `docs/configuration.md` `[imports]` table checked; neither needs an edit; no spec governs boot discovery).
- PR-001: the E-04 subprocess test did not set `PYTHONPATH`. Pytest's `pythonpath = ["src"]` affects only the test process. In this environment a child `python3` started outside the tree imports the editable install of the main checkout, not this lane's `src` (observed: `import pubrun` from `/tmp` resolved to the main checkout's `src/pubrun/__init__.py`, while an in-process pytest probe resolved to the lane's `src`). The test could therefore exercise unfixed code and fail, or pass against the wrong tree. Other subprocess tests in this repository prepend `src` (`tests/test_capture_isolation.py::_worktree_env`).
- PR-002: E-02 specified `valid=None` as an "accept any non-empty value" mode with no caller (YAGNI). E-02 also changes one behavior silently: `.strip()` makes `" error "` acceptable, which today's `_resolve_conflict_policy` rejects (it calls `.lower()` only). The change is harmless and matches `resolve_import_mode`, but the plan did not state it.

### Step S5

- Checked: `OQ-01` (resolved, non-blocking, basis cited), the three deferral carriers (`Carrier-Declined` each), and all findings. Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so none needs escalation. No question needs the human.
- PR-004: `OQ-01` recorded `- Owner: none` on a question the plan author resolved; changed to `plan author` and recorded as D-1.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | UNDER-SCOPE | R4.E (subprocess test targets the code under test) | Plan E-04 test (10); `pyproject.toml` `pythonpath = ["src"]`; `tests/test_capture_isolation.py::_worktree_env` | The end-to-end subprocess test did not put this repository's `src` on the child's `PYTHONPATH`, so the child can import a different installed `pubrun` (observed: the main checkout's editable install) and test unfixed code. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04 test (10) now requires `sys.executable`, a timeout, and `src` prepended to `PYTHONPATH`, with the reason; V-04 demands the pasted test source showing the prefix (recommendation strength: very strong). |
| PR-002 | low | OVER-SCOPE | R4.F (KISS) and R4.D (unstated behavior change) | Plan E-02; `src/pubrun/_bootstrap.py::_resolve_conflict_policy` (`.lower()` only); `src/pubrun/_config_boot.py::resolve_import_mode` (`.strip().lower()`) | `valid=None` was an unused mode, and the `.strip()` change that newly accepts `" error "` was not stated. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Made `valid` required, removed the "accept any value" mode from E-02, Proposed changes 2, and V-02, and stated the whitespace change (recommendation strength: strong). |
| PR-003 | medium | IN-SCOPE | R2 (test names and counts are not a V-item bar) | Plan V-02, V-03, V-04; `steps/r2-executability.md` "Live-artifact success criteria" | V-02 and V-03 used test function or class names as the bar, and V-04 required "the ten tests" by name. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Rewrote V-02, V-03, and V-04 to demand the pinned behaviors, re-derived at execution time, with test names only as pointers (recommendation strength: strong). |
| PR-004 | low | IN-SCOPE | S5 (owner provenance) and Check P (wording) | Plan `## Open questions` OQ-01; plan E-04 tests (5) and (8); validation boilerplate | `OQ-01` had `- Owner: none` although the author resolved it; E-04 (5) left the repeated `select_mode` calls implicit; "no warning" was broader than intended; two em dashes raised `IPD-C802`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Set Owner to `plan author` (D-1), made the re-trigger step explicit, narrowed to `PubrunImportModeConflictWarning`, and removed the dashes (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Does an invalid `on_conflict` in a higher file fall through or stop the search (OQ-01)? | Fall through; owner recorded as plan author | Stop at the first file that sets the key, even with an invalid value | `tests/test_config_capture_modes.py::TestBootDiscovery::test_invalid_mode_in_higher_file_falls_through`; `src/pubrun/_config_boot.py::resolve_import_mode` | yes |
| D-2 | Should `_read_boot_toml_key` keep an optional "accept any value" mode? | No; `valid` is required | Keep `valid=None` for future boot keys | Only caller is `_bootstrap._resolve_conflict_policy`; plan `## Deferred / out of scope` declines other boot keys | yes |
| D-3 | Should the subprocess test pin the child to this repository's `src`? | Yes, prepend `src` to `PYTHONPATH` | Rely on the installed `pubrun`; drop the subprocess test | Observed main-checkout editable install in a child process; `tests/test_capture_isolation.py::_worktree_env` | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined existing items. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
