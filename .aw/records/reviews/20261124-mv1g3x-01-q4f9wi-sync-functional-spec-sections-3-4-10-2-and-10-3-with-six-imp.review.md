# Review findings: ipd q4f9wi

- Subject-Id: q4f9wi
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-mv1g3x-01-q4f9wi-sync-functional-spec-sections-3-4-10-2-and-10-3-with-six-imp.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `663c2ea` had a clean working tree. `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). The Mermaid flowchart in Findings satisfies requirement 12(a)-(e) and matches the code consumers.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Findings flowchart intro and Proposed changes 2b | Said "The boot resolver reads them at `import pubrun` time", lumping `PUBRUN_IMPORT_CONFLICT` into import-time boot resolution | Distinguishes boot-time import-mode resolution from lazy conflict handling (`_resolve_conflict_policy`) in the boot sequence | Requirement 5 and factual parity with `src/pubrun/_bootstrap.py::_resolve_conflict_policy` and the flowchart (PR-002). |
| Required tests and V-01..V-03 | Used exit-1/vacuous `grep` checks, exit-0-on-failure cross-check scripts, and an in-repo `.mv1g3x_probe` scratch directory | Replaced with fail-closed exit-0 `python3 -c` checks (with explicit UTF-8 reading and assertions) and an isolated `tempfile.TemporaryDirectory()` runtime probe | Check R2 validation reliability and repo cleanliness (PR-001). |
| Gate item 2 | Mentioned `--scope-reason` only and referenced `.mv1g3x_probe` | Added `--scope-ack` and updated the temporary-directory probe note | S7 execution contract completeness (PR-003). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`docs/functional_spec.md`), 3 E-items in 1 task group, `- Kind: child`.

1. Partly: `docs/functional_spec.md` is the repository's functional specification document (Markdown reference, not a `.aw/records/specs/*.spec.md`); the plan synchronizes three sections with existing code without changing code, schemas, or CLI contracts.
2. No: touches only `docs/functional_spec.md`, no code guarding private data, commits, worktree isolation, merges, or the sandbox.
3. No: 3 E-items in 1 task group editing 3 bounded sections of 1 file.
4. Yes: `docs/functional_spec.md`.
5. Low: text-only documentation sync reversible via git, though an inaccurate functional spec misleads contributors.

AW-TIER: standard

### Step R1

- Checked: `docs/functional_spec.md` (sections 3.2, 3.3, 3.4, 10.1-10.7, 11.13); `src/pubrun/config.py` (full file, lines 1-264: `get_global_config_dir`, `_resolve_layers`, `resolve_config`); `src/pubrun/_config_boot.py` (`_global_config_dir`, `resolve_import_mode`); `src/pubrun/_bootstrap.py` (`_resolve_conflict_policy`, `select_mode`); `src/pubrun/_modes.py::MODES` and `VALID_MODES`; `src/pubrun/noauto.py`; all `os.environ` references across `src/pubrun/`; `docs/configuration.md` (`#Configuration Discovery`, `#Environment Variables`); `docs/architecture.md` (`#Initialization`); backlog carriers `mv1g3x`, `oubh58`, `4ht7x4`; executed plan `mspqm6`; and commits `a47fc45` and `aa2cbc9`.
- Confirmed: every section anchor, symbol, existing quote, env-var consumer (`PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, `PUBRUN_IMPORT_CONFLICT`, `PUBRUN_PROFILE`, `PUBRUN_META_REF`, `XDG_CONFIG_HOME`, `APPDATA`, plus deferred `PUBRUN_DEBUG`), and carrier id6 resolves cleanly in the repository.
- PR-002: Proposed changes 2b said "The boot resolver reads them at `import pubrun` time" for all three boot env vars, whereas `PUBRUN_IMPORT_CONFLICT` is read lazily by `src/pubrun/_bootstrap.py::_resolve_conflict_policy` only when two imports conflict. Fixed to "The boot sequence reads them during import-mode resolution and conflict handling (Sections 3.2 and 3.3)" and aligned the Findings flowchart intro.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-03` to `V-01`..`V-03`), `- Scope-Paths:` completeness, `- Item-Dependencies: none`, runtime-demonstration reachability of all P1..P11 observations (every producing symbol verified in `src/pubrun/`), validation scripts, and all five execution-contract elements in the gate.
- PR-001: (a) `grep -n 'five namespaced'` and `grep -c '[—–]'` exit 1 on expected zero matches, and the `grep -c` dash check passes vacuously with `0` on an empty diff; (b) both cross-check commands in Required tests printed `missing` and still exited `0` instead of failing closed, and omitted explicit `encoding='utf-8'`; (c) the execution runtime probe created `.mv1g3x_probe` inside the repo working tree. Replaced with fail-closed exit-0 `python3 -c` checks and a `tempfile.TemporaryDirectory()` runtime probe with `finally: os.chdir(orig)`.
- PR-003: Gate item 2 omitted `--scope-ack` for declared-but-unmodified paths and referenced `.mv1g3x_probe`. Added `--scope-ack` and aligned the probe note.

### Step R3

- Checked: all five bullets of Check R3 full form. Documentation-only edit to `docs/functional_spec.md`; no auth, secrets, or untrusted input surfaces; V-03 runs `python3 scripts/sanitize_paths.py --check --all`; moving the runtime probe to `tempfile.TemporaryDirectory()` prevents accidental untracked artifacts inside the repo. No finding.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing (3 single-section E-items in 1 file, cleanly scoped); spec and documentation sync (`docs/architecture.md#Initialization` and `docs/configuration.md#Configuration Discovery` verified; `4ht7x4` carries `docs/configuration.md#Environment Variables`; `oubh58` carries the `pubrun run --mode` precedence contradiction; `.aw/records/specs/` has no `.spec.md` file). No additional findings beyond PR-001..PR-003.

### Step S5

- Checked: `OQ-01` (deferring the `pubrun run --mode` contradiction to `oubh58`) and `OQ-02` (including `XDG_CONFIG_HOME` and `APPDATA` in section 10.3) are both `- Blocking: no`, `- Status: resolved`, `- Owner: plan author`, and backed by verified repository evidence. Every review finding PR-001..PR-003 had Overall Remediation Risk `Low` and was fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | R2 (non-fail-closed cross-checks, exit-1/vacuous greps, in-repo scratch dir) | Plan Required tests lines 232-242 and V-01..V-03 (`grep -c '[—–]'`, `print('OK' if not missing else missing)`, `.mv1g3x_probe`) | Both cross-checks exited 0 even when items were missing and omitted UTF-8 encoding; `grep` checks exited 1 on expected zero matches and the dash check passed vacuously on an empty diff; the runtime probe created `.mv1g3x_probe` inside the working tree. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced all four checks with fail-closed exit-0 `python3 -c` commands (UTF-8 explicit) and moved the execution runtime probe into `tempfile.TemporaryDirectory()` with `finally: os.chdir(orig)`. |
| PR-002 | LOW | IN-SCOPE | R1 / Proofreading (inaccurate consumer timing) | `src/pubrun/_bootstrap.py:122-145,235-236` (`_resolve_conflict_policy` called lazily on conflict); Plan Proposed changes 2b line 194 | Proposed changes 2b said "The boot resolver reads them at `import pubrun` time" for `PUBRUN_IMPORT_CONFLICT` as well, although `_resolve_conflict_policy` reads it lazily when two imports conflict. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reworded Proposed changes 2b and the Findings flowchart intro to distinguish boot-time mode resolution from conflict handling in the boot sequence. |
| PR-003 | LOW | IN-SCOPE | S7 (execution contract) | Plan Gate item 2 line 293 | Gate item 2 omitted `--scope-ack` for declared-but-unmodified paths and referenced `.mv1g3x_probe`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `--scope-ack` and updated Gate item 2 to match the temporary-directory probe. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` | Updates three sections of `docs/functional_spec.md` (the project's functional specification reference) across 3 E-items; matches `lwb332` (`standard`). | yes |
| D-2 | Keep the false `pubrun run --mode` override sentence in section 3.4 deferred to `oubh58` | Keep deferred to `oubh58` | Rewrite section 3.4 now | Resolving whether `pubrun run --mode` should override in-code imports or docs should be updated across 5 files is a maintainer decision properly carried by open backlog item `oubh58`. | yes |
| D-3 | Keep `PUBRUN_DEBUG` out of section 10.3 (`Carrier-Declined`) | Keep out of scope | Add `PUBRUN_DEBUG` to section 10.3 | `PUBRUN_DEBUG` (`src/pubrun/report/output.py:63`) is a CLI debug toggle already documented in `docs/cli.md`, outside the boot/config scope of backlog item `mv1g3x`. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All three findings were fixed in place with Low remediation risk and swept across the whole plan. No second pass is needed.

AW-REVIEW: DONE
