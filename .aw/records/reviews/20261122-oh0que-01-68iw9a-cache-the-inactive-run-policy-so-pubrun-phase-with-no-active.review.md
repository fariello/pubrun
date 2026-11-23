# Review findings: ipd 68iw9a

- Subject-Id: 68iw9a
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-oh0que-01-68iw9a-cache-the-inactive-run-policy-so-pubrun-phase-with-no-active.ipd.md` (front matter, Goal with the Mermaid flowchart and signature table, E-01 to E-05, conventions, findings, deferrals, open questions, V-01 to V-05, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches E-02 (signature, compare, resolve on mismatch, store one tuple, then error/warn/ignore).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning (PR-004). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (4 files, no `.spec.md`), E-item and task-group counts (5 items, 5 groups).

1. No: no spec, CLI option, file format, or configuration key changes; `on_inactive_annotate` keeps its values and default. One observable behavior changes (the malformed-file warning is logged once per file change instead of once per call), which OQ-02 resolves and `CHANGELOG.md` records.
2. No: configuration lookup for an event policy; touches no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 5 E-items, one production function plus its tests and two documentation entries.
4. Yes: `- Scope-Paths:` lists all four files.
5. Yes: a stale cache would silently apply the wrong policy (for example ignore an `"error"` policy a user just set) on every no-active-run call, and seven public entry points share the helper.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/core.py::_handle_inactive` (lines 56 to 70) and its seven callers (`annotate`, `phase.__enter__`, `report`, `artifact`, `register_file`, `register_input`, `register_output`); `src/pubrun/config.py::load_default_config` (cached, deep-copied), `get_global_config_dir` (`sys.platform`, `APPDATA`, `XDG_CONFIG_HOME`, `os.path.expanduser`), `_safe_load_toml` (warning `pubrun: ignoring malformed config file ...`), `load_user_config`, `load_local_config` (`Path.cwd()`, `.config/pubrun/config.toml`, `.pubrun.toml`), `_resolve_layers` (`PUBRUN_PROFILE`/`PUBRUN_META_REF` map only to `[core]`), `resolve_config`; `src/pubrun/resources/default.toml` (`on_inactive_annotate = "ignore"`); `tests/conftest.py::isolated_cwd` (patches `pathlib.Path.cwd`) and `pubrun_state_isolation` (restores `os.environ`); `tests/test_api.py::TestHandleInactivePolicy` and `tests/test_file_registration.py::TestValidationInactivePolicyAndSchema::test_inactive_run_honors_on_inactive_annotate_policy` (both replace `resolve_config`); `pyproject.toml` `addopts`; `docs/performance.md` line 202 and the `af36c85` revision line; `CHANGELOG.md` `## [Unreleased]` `### Fixed` at line 105; backlog `oh0que` (graduated, `Blocks-Release: next`). All citations resolve.
- Ran the E-01 benchmark command twice on the unchanged tree: `inactive_minus_null_us=99.77 active_minus_null_us=18.70` and `inactive_minus_null_us=102.39 active_minus_null_us=19.03`, matching the plan's Findings.
- No other test replaces `load_user_config` or `load_local_config` and then makes an inactive call, so leaving those loaders out of the signature does not break an existing test (confirmed by the full-suite run below).

### Step R2

- Checked: E/V bijection (E-01..E-05 to V-01..V-05), Scope-Paths completeness, `Item-Dependencies: none` (correct), ordering (E-01 before any `src/` edit), runtime-demonstration reachability, falsifiability of each E-03 test, and the gate.
- Prototyped E-02 in memory outside the repository (no repo edit) and ran six behavior tests modeled on E-03 plus a replaced-loader check: all passed. Timed it with the E-01 command: memoizing only the user configuration path gave 36.76, 35.81, and 36.90 us, then 35.54, 37.41, and 34.18 us; memoizing the user path and the two local paths (keyed on `Path.cwd()`) gave 17.87, 17.73, and 17.36 us. Against the 99.8 to 102.4 us baseline, the first design gives a ratio of about 0.36 and fails the E-04 one-third bar, while E-02 only said the user-path memo "may" be added and did not mention the local paths (PR-001).
- E-03 test (5) asserted only that no exception is raised, which the unchanged code also satisfies, so nothing pinned the once-per-file-change warning behavior that OQ-02 accepts and the `CHANGELOG.md` entry claims. Measured: unchanged code logs the warning 3 times for 3 calls and 6 after a rewrite; the prototype logs 1, then 2 (PR-002).
- V-02 and V-03 used test class names and "the five tests ... all passing" as their bar (PR-003).
- Full suite: serial `python3 -m pytest -q -p no:cacheprovider --no-cov` on the unchanged tree printed `1819 passed, 2 skipped in 487.21s`, exit 0. With the prototype loaded, `-n 6` printed `1 failed, 1820 passed`; the one failure is `tests/test_liveness.py::TestIsSameProcess::test_expected_script_matches`, which fails under xdist on the unchanged tree and is carried by plan `vv4vdd`. E-04's `python3 -m pytest -q` is serial, where that test passes.
- Gate: precondition, ordering, scope fence with `--scope-reason`/`--scope-ack`, validation honesty, path-scoped `aw commit 68iw9a` with never-push, and runner/executor `aw ipd finalize` ownership are present. Conforming.

### Step R3

- Checked (full form): the change reads only local configuration files and environment variables already read by `resolve_config()`, logs nothing new, and writes nothing. A stale cache could apply `"ignore"` after a user sets `"error"`, which drops events silently; the signature covers every file and directory input of `resolve_config()` that can set `[events]`, the stat limit is recorded in Deferred, and the resolver object is in the signature so a replaced resolver is honored. A failed resolution is not cached. Thread safety: one tuple assignment, so a reader never sees a mixed pair. No finding.

### Step R4

- Checked: rubric A (module-level cache with single-assignment updates, no lock needed), C (cache local to `_handle_inactive` rather than in `resolve_config`; Deferred explains the larger blast radius), D (invariants: messages, default, callers, exception propagation unchanged; a configuration change is honored on the next call), E (behavioral tests writing real TOML; no timing, call counts, or source reading), F (KISS: one function and small memos), right-sizing (5 E-items, 4 files), spec/doc sync (`docs/performance.md` line 202 and `CHANGELOG.md`; `docs/configuration.md` and `docs/api.md` unaffected; no spec governs the path).
- Windows inputs: `get_global_config_dir()` reads `APPDATA` on `win32` and falls back to `os.path.expanduser`, which on Windows reads `USERPROFILE`, `HOMEDRIVE`, and `HOMEPATH`; the E-02 memo key omitted `sys.platform`, `HOMEDRIVE`, and `HOMEPATH`. Folded into PR-001. The CI matrix gate is recorded in Deferred.

### Step S5

- Checked: OQ-01 and OQ-02 (resolved, non-blocking, with cited basis), the three deferral carriers (`Carrier-Declined` with reasons), and all findings. All findings have Low remediation risk and are fixed. No question needs the human. No finding is OPEN or DEFERRED.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | medium | IN-SCOPE | R2 (design meets its own bar) | Review prototype with the E-01 command: user-path memo only 34.18 to 37.41 us; user and local path memos 17.36 to 17.87 us; unchanged baseline 99.77 and 102.39 us; `src/pubrun/config.py::get_global_config_dir`, `ntpath.expanduser` reads `USERPROFILE`, `HOMEDRIVE`, `HOMEPATH` | E-02 made the user-path memo optional and did not memoize the local paths, so a faithful implementation could land at a ratio of about 0.36 and fail E-04's one-third bar; its memo key also omitted `sys.platform`, `HOMEDRIVE`, and `HOMEPATH`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-02 now requires both memos, keys the user path on `sys.platform` and all six variables, and cites the measurements; the Findings design note records them; V-02 checks both memos (recommendation strength: strong). |
| PR-002 | medium | IN-SCOPE | R2 (falsifiable test) | Review run: unchanged code logs `ignoring malformed config file` 3 times for 3 inactive calls, 6 after a rewrite; prototype logs 1, then 2 | E-03 test (5) asserted only "does not raise", which the unchanged code satisfies, so the once-per-file-change behavior that OQ-02 accepts and `CHANGELOG.md` will claim was untested. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Test (5) now asserts exactly one warning after three calls and exactly two after a different-size malformed rewrite (recommendation strength: strong). |
| PR-003 | low | IN-SCOPE | R2 (evidence bar uses test names) | `steps/r2-executability.md` "a test function name is permitted only as a non-binding pointer"; plan V-02, V-03 | V-02 and V-03 accepted named tests or classes passing as the bar. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Both now demand zero failures plus re-derived test lines that pin each behavior and the mechanism (real TOML files or a replaced resolver, asserted through a public call); names are pointers (recommendation strength: strong). |
| PR-004 | low | IN-SCOPE | Check P (writing, `IPD-C802`) | `aw ipd lint --phase author` reported 2 `IPD-C802` info diagnostics | Two em dashes in the validation boilerplate. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced with commas and parentheses (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Should the local file paths be memoized, or should the one-third bar be relaxed? | Memoize them, keyed on `Path.cwd()` | Relax E-04 to a weaker ratio; keep the memo optional | The memo is a few lines and the prototype meets the bar with margin (about 0.18) | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined E-02, E-03, the Findings note, V-02, V-03, and the boilerplate. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
