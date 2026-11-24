# Review findings: ipd mspqm6

- Subject-Id: mspqm6
- Subject-Type: ipd
- Reviewed-At: 2026-11-24
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-2rhs16-01-mspqm6-sync-functional-spec-and-architecture-docs-with-multi-file-b.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Front-matter keys, the H2 heading list and order, E/V ids, checkbox states, Execution state values, and item field names are unchanged. Substantive rewrites of E-items, V-items, the diagram, and the gate are recorded under Findings.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence naming "multi-file boot configuration precedence order" | Says what the boot resolver is and does, names the stale behavior, and points to `docs/configuration.md` as already-correct reference | Define terms at first use (requirement 1). |
| Findings | "Two user-facing docs" followed by three numbered places | Five numbered places, each with a heading citation and the quoted stale text | Requirement 5: state every location; requirement 11: the count did not match the list. |
| Project conventions | `module.function` citation form | `path::Name` and `path#Heading` forms | Matches `steps/p-proofread.md` Section 11.1. |
| E-01, E-02 Expected outcome | One long sentence each | Numbered sub-outcomes, one per document location | Requirement 2 and 9: one idea per item, so each V-item can name its unit. |
| Workflow history | Oldest first | Newest first | `steps/s7-finalize.md` states the section is newest-first. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`docs/functional_spec.md`, `docs/architecture.md`), E-01 and E-02, and the cited code.

1. No: documentation only; no `.spec.md`, CLI option, output format, or configuration key changes.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. No: 2 E-items in 1 task group, both in `docs/`.
4. Yes: 2 files, matching the E-items.
5. No: a wrong sentence in a document is easy to correct and breaks no code.

AW-TIER: simple

### Step Q

- Checked: what could break, which docs other text depends on, and whether the plan's claims match the code. Read `src/pubrun/_config_boot.py` in full, `src/pubrun/_bootstrap.py::_resolve_conflict_policy`, `src/pubrun/core.py::_execute_boot_sequence`, `src/pubrun/_modes.py::VALID_MODES`, `src/pubrun/config.py::get_global_config_dir`, every `docs/` and `README.md` mention of `PUBRUN_AUTO_START` and "at most once", and the backlog item `2rhs16`.
- Probe at review (lane HEAD `047a843`, temporary directory, `XDG_CONFIG_HOME` pointed at an empty directory): malformed `./.pubrun.toml` alone gave `('auto', 'default')`; malformed `./.pubrun.toml` plus `[core] auto_start = "off"` in `./.config/pubrun/config.toml` gave `('noauto', 'config:[core].auto_start')`; `PUBRUN_AUTO_START=" YES "` gave `('auto', 'env:PUBRUN_AUTO_START')`; `PUBRUN_AUTO_START="maybe"` was ignored; `PUBRUN_IMPORT_MODE=minimal` with `PUBRUN_AUTO_START=1` gave `('minimal', 'env:PUBRUN_IMPORT_MODE')`.
- Risk: the change is prose only. The main risk is a new inaccuracy, which the strengthened V-items now check against named code facts.
- `python3 scripts/sanitize_paths.py --check --all` exited 0 on the unchanged tree.
- `aw ipd lint --phase author --agent` and `--phase review-finalize --agent` both reported `clean`, exit 0, 0 findings.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | medium | UNDER-SCOPE | Q (stale doc claim) | `docs/functional_spec.md#3.2 Lightweight Import Requirement` "If configuration resolution fails (e.g., corrupt TOML), the import succeeds silently with auto-start disabled."; `src/pubrun/_config_boot.py::_load_toml_file`; probe gave `('auto', 'default')` for a malformed `./.pubrun.toml` | The paragraph next to the bullet being fixed says corrupt TOML disables auto-start. The resolver skips a malformed file and continues, so auto-start stays on unless another source disables it. The plan left this stale claim in place. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 outcome 1 rewrites the paragraph; V-01 greps for `corrupt TOML`. |
| PR-002 | medium | UNDER-SCOPE | Q (stale doc claim) | `docs/architecture.md#21. System Components` "parses `./.pubrun.toml` at most once without importing the full config system" | A second one-file claim in `docs/architecture.md` was not in the plan. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 outcome 2 updates the `**Boot Config Resolver**` bullet; V-02 greps for the stale phrase. |
| PR-003 | low | UNDER-SCOPE | Q (completeness) | `src/pubrun/_config_boot.py::_auto_start_mode`; `src/pubrun/_config_boot.py::resolve_import_mode` checks `PUBRUN_IMPORT_MODE` first | E-01 did not require saying that unrecognized values are ignored, that `[core].auto_start` accepts the same values, or that `PUBRUN_IMPORT_MODE` takes precedence. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 outcome 3 and V-01 list each fact. |
| PR-004 | low | IN-SCOPE | P (diagram) | `src/pubrun/_config_boot.py::resolve_import_mode` steps 1 and 2 | The diagram merged the two environment variables into one decision and said "set?", but an unrecognized value falls through to the config files. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Diagram shows two separate decisions on a valid or recognized value; the text states that malformed files are skipped. |
| PR-005 | medium | IN-SCOPE | R2 (weak evidence) | V-01 and V-02 asked only for `git diff` with a general "confirming" | A diff alone does not prove each required fact or the dash rule. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-items name each fact to locate in the diff, add a dash count over added lines, and add stale-phrase greps whose patterns were checked to match the current text (1 and 2 matches). |
| PR-006 | medium | IN-SCOPE | S7 (execution contract) | Gate text "commit only the scoped files through `aw commit`, and complete the post-gate lifecycle transition under `ipd-lifecycle`" | The gate lacked the precondition, scope declaration, validation-honesty rule, never-push rule, and the runner or executor split for `aw ipd finalize`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Replaced with the five-element execution contract naming `aw commit mspqm6` and `aw ipd finalize mspqm6`. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `simple` | `standard` | Two documentation files, no code, no contract change (Step T answers) | yes |
| D-2 | Fix the two stale places not named in backlog `2rhs16` in this plan, or file a new backlog item? | This plan | New backlog item | Same files, same stale behavior, same `Scope-Paths`; a separate item would leave the plan's goal "describe what the boot resolver actually does" unmet | yes |
| D-3 | Use `docs/configuration.md` as the reference wording? | Yes | Write new wording from the code only | `docs/configuration.md` "The import mode chosen at `import pubrun` time" matches the code and was updated in `2e6xfq` | yes |

### Step S5

- Checked: open questions (none in the plan; none created by findings). Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so the lane outcome carries no question.

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. The E/V id set is unchanged (E-01, E-02, V-01, V-02, `Highest E allocated: 02`). `- Scope-Paths:` and `- Item-Dependencies:` are unchanged. The new findings stay within the same two files. No re-review pass is needed. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: simple`.

AW-REVIEW: DONE
