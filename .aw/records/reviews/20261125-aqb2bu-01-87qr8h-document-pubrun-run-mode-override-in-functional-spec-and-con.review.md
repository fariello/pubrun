# Review findings: ipd 87qr8h

- Subject-Id: 87qr8h
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. No pre-review snapshot was needed: lane `HEAD` `8054ab8` had a clean working tree and the plan was already committed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) and `aw ipd lint --phase author --citation-anchors --detail` reported `conforming` (exit `0`). Requirement 12: the Mermaid flowchart in `## Findings` depicts the five-branch boot-time import-mode selection sequence and agrees with `src/pubrun/_bootstrap.py::select_mode`, `src/pubrun/_config_boot.py::resolve_import_mode`, and the surrounding prose.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Proposed changes` item 2 (`PUBRUN_IMPORT_MODE` row) | "Overrides `PUBRUN_AUTO_START` and `[imports].mode`." | "Overrides `PUBRUN_AUTO_START` and config files (`[imports].mode`, `[core].auto_start`)." | Aligns with `_config_boot.py::resolve_import_mode`, Section 10.3 `PUBRUN_RUN_MODE_OVERRIDE`, and `docs/configuration.md` item 3 (requirement 4). |
| `## Proposed changes` item 3 (`PUBRUN_RUN_MODE_OVERRIDE` row) | "Takes highest precedence, overriding explicit in-code `import pubrun.<mode>` imports..." | "Takes precedence over explicit in-code `import pubrun.<mode>` imports..." | Matches Section 10.3 phrasing and avoids colliding with reviewed sibling `pqcx6o` `V-05`'s negative grep for `"Takes highest precedence"` (PR-001). |
| `## Project conventions discovered (Step 0)` | Bare reference to executed plan `wg2l7b`; omitted cross-Set overlap with `pqcx6o` and `wjsccu` | Describes what `wg2l7b` did and documents cross-Set convergence with `pqcx6o` and `wjsccu` | Explains referenced artifact relationship (technical-writing references rule) and records execution-order context (PR-002). |
| `E-01`, `E-02`, `## Proposed changes` items 2-3, `## Required tests / validation` items 1-3, `V-01`, `V-02`, `## Approval and execution gate` item 4 | Assumed neither file was modified by another plan; asserted non-empty `git diff` and hardcoded `added_lines=3` / `added_lines=2` | Idempotent replacement preserving unrelated rows, verbatim-presence Python check tolerating already-applied files with `--scope-ack`, and modified-only `aw commit` paths | Prevents execution and validation failure if `pqcx6o` or `wjsccu` runs first (PR-002). |
| `## Deferred / out of scope (with reason)` | Single bullet citing `- Carrier: pqcx6o` for `XDG_CONFIG_HOME`, `APPDATA`, and `PUBRUN_DEBUG` | Split into `Carrier: pqcx6o` (`PUBRUN_DEBUG`, `NO_COLOR` in `docs/configuration.md`), `Carrier: wjsccu` (`PUBRUN_DEBUG`, `NO_COLOR` in `docs/functional_spec.md`), and `Carrier-Declined:` for `XDG_CONFIG_HOME`/`APPDATA` | Fixes false carrier claim on `pqcx6o` (PR-003). |
| `## Spec / documentation sync` | Claimed `docs/manifest.md` and `docs/functional_spec.md` Section 3.4 already document `PUBRUN_RUN_MODE_OVERRIDE` | Distinguishes files naming `PUBRUN_RUN_MODE_OVERRIDE` from `docs/manifest.md` (`"cli:pubrun run --mode"` provenance) and Section 3.4 (`pubrun run --mode <mode>` behavior), and notes `pqcx6o`/`wjsccu` overlap | Corrects overstated sync claim (PR-004). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`docs/functional_spec.md, docs/configuration.md`), 2 E-items in 1 task group, `- Kind: child`, and pending plans outside Set `aqb2bu` declaring either path (`pqcx6o` and `wjsccu` in Set `doc-audit`).

1. No: documentation-only synchronization with existing behavior in `src/pubrun/__main__.py`, `src/pubrun/_bootstrap.py`, `src/pubrun/_config_boot.py`, and `src/pubrun/config.py`; changes no runtime interface, schema, or `.spec.md` file, although reviewed pending plan `pqcx6o` dynamically parses item 3 of this plan.
2. No: touches only `docs/functional_spec.md` and `docs/configuration.md`; touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 2 E-items in 1 task group across 2 documentation files.
4. Yes: `docs/functional_spec.md, docs/configuration.md`. Both paths overlap with pending plans in Set `doc-audit` (`pqcx6o` and `wjsccu`).
5. No: text-only reference edits; cannot lose data or break code, and is trivially reversible with `git revert`.

AW-TIER: standard

### Step R1

- Checked every material citation against the repository:
  - `src/pubrun/__main__.py::main` (`elif args.command == "run":`, lines 3468-3483): sets both `"PUBRUN_IMPORT_MODE": args.mode` and `"PUBRUN_RUN_MODE_OVERRIDE": args.mode` in `child_env`.
  - `src/pubrun/_bootstrap.py::select_mode` (lines 173-304): checks `os.environ.get("PUBRUN_RUN_MODE_OVERRIDE", "").strip().lower()` against `pubrun._modes.MODES` (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`), sets `_selected_by` and `_selected_source` to `"cli:pubrun run --mode"`, records differing caller request and subsequent `select_mode` calls with `conflict: False` without triggering `[imports].on_conflict` / `PUBRUN_IMPORT_CONFLICT`, and ignores invalid or empty values.
  - `src/pubrun/_config_boot.py::resolve_import_mode` (lines 158-192): resolves `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, config files (`./.pubrun.toml`, `./.config/pubrun/config.toml`, user home `config.toml`; `[imports].mode` before `[core].auto_start` within a file), then built-in default `"auto"`.
  - `src/pubrun/config.py::_resolve_layers` and `resolve_config` (lines 148-199): read only `PUBRUN_PROFILE` and `PUBRUN_META_REF` from the environment; boot-time import variables never enter `resolve_config()` or `config.resolved.json`.
  - `docs/functional_spec.md` Sections 3.3, 3.4, 10.2, 10.3, 11.13 (lines 77-138, 365-395, 553-567) and `docs/configuration.md` (`## Configuration Discovery`, `### [imports]`, `## Environment Variables`, lines 9-24, 75-99, 357-367): exact pre-edit quotes match character for character.
  - `docs/cli.md` (line 733), `CHANGELOG.md` (lines 154-157), `docs/manifest.md` (lines 521-536), executed plans `lhwy0t` and `wg2l7b`, graduated backlog item `aqb2bu`, commit `f7c0897` (verified valid commit; `git log --oneline f7c0897..HEAD` shows only plan/backlog/review commits since authoring), and `tests/test_import_modes.py` / `tests/test_config.py` (124 tests collected via `--collect-only`).
- Drift found:
  - `## Proposed changes` item 3 row 1 (`PUBRUN_RUN_MODE_OVERRIDE`) contained `"Takes highest precedence, overriding..."`, which collides with reviewed pending plan `pqcx6o` `V-05`'s `grep -n "Takes highest precedence" docs/configuration.md` (`exit=1`) check (PR-001).
  - `## Deferred / out of scope` cited `- Carrier: pqcx6o` for `XDG_CONFIG_HOME` and `APPDATA`, which `pqcx6o` does not touch (they are already documented in `docs/configuration.md` `## Configuration Discovery` and `docs/functional_spec.md` Section 10.3) (PR-003).
  - `## Spec / documentation sync` stated `docs/manifest.md` and `docs/functional_spec.md` Section 3.4 already document `PUBRUN_RUN_MODE_OVERRIDE`; neither names that environment variable (they document `"cli:pubrun run --mode"` provenance and `pubrun run --mode <mode>` behavior, respectively) (PR-004).

### Step R2

- Checked: E/V bijection (`E-01`/`V-01`, `E-02`/`V-02`), `- Scope-Paths:`, `- Item-Dependencies: none`, concrete non-tautological evidence, runtime-demonstration reachability (all checks inspect files, diffs, and existing tests — reachable by construction), execution contract (all five required clauses present), and cross-Set execution-order safety against `pqcx6o` and `wjsccu`.
- Results:
  - Pre-review `E-01`, `E-02`, `## Required tests / validation` item 3 (`assert added`), and `V-01`/`V-02` (`added_lines=3` / `added_lines=2`) assumed neither file had been updated by `pqcx6o` or `wjsccu`. Fixed to be idempotent in either execution order, with verbatim-presence verification and `--scope-ack` guidance when a file is already converged (PR-002).
  - Verified that `pqcx6o` `V-05`'s exact Python extraction snippet still parses `87qr8h` item 3 and returns both target rows cleanly, and that neither row contains `"Takes highest precedence"`.

### Step R3

- Checked: the plan touches no authentication, authorization, secrets, redaction, or trust-boundary code. Confirmed the proposed documentation accurately describes the security-relevant override semantics of `PUBRUN_RUN_MODE_OVERRIDE` (overrides in-code `import pubrun.<mode>` imports, suppresses conflict errors under `PUBRUN_IMPORT_CONFLICT=error`, and ignores invalid or empty values). Confirmed zero hardcoded secrets or machine-local paths; `python3 scripts/sanitize_paths.py --check --all` exits `0`.

### Step R4

- Checked: rubric items A through F (pure documentation reference synchronization; runtime invariants verified against `_bootstrap.py`, `_config_boot.py`, `config.py`, and `__main__.py`), right-sizing (2 E-items, 1 file per E-item, low conceptual density), and `## Spec / documentation sync`.
- Results:
  - Right-sizing is clean: `E-01` covers `docs/functional_spec.md` (Sections 10.2 and 10.3) and `E-02` covers `docs/configuration.md` (`## Environment Variables`), each executable in one focused pass.
  - Corrected `## Spec / documentation sync` (PR-004) and aligned `PUBRUN_IMPORT_MODE` config-file wording across both tables.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R2 coordination | `.aw/records/plans/pending/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md:111` (`## Proposed changes` item 3); `.aw/records/plans/pending/20261125-doc-audit-02-pqcx6o-fix-cli-and-configuration-reference-inaccuracies-and-drift.ipd.md:113,266-277` (`E-05`, `V-05`) | Reviewed pending plan `pqcx6o` copies `87qr8h` item 3 verbatim into `docs/configuration.md` and then asserts `grep -n "Takes highest precedence" docs/configuration.md` exits `1`. Item 3 row 1 (`PUBRUN_RUN_MODE_OVERRIDE`) contained `"Takes highest precedence, overriding..."`, which would cause `pqcx6o` `V-05` to fail in either execution order. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reworded `"Takes highest precedence, overriding"` to `"Takes precedence over"` in `## Proposed changes` item 3 row 1 (matching Section 10.3 and keeping `pqcx6o` `V-05`'s dynamic `same=2` anchor intact) (recommendation strength: strong). |
| PR-002 | HIGH | IN-SCOPE | R2 executability | `.aw/records/plans/pending/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md:37-45,101-113,131-165,184-192,203` (`E-01`, `E-02`, `## Required tests / validation` item 3, `V-01`, `V-02`, `## Approval and execution gate` item 4); `pqcx6o` `E-05`; `wjsccu` `E-03` | Pending plans `pqcx6o` (`docs/configuration.md`) and `wjsccu` (`docs/functional_spec.md`) overlap on the same sections. If either executes before `87qr8h`, blindly inserting a new row could duplicate `PUBRUN_RUN_MODE_OVERRIDE`, `assert added` in item 3's Python check would crash on an already-converged file, `V-01`/`V-02` hardcoded `added_lines=3`/`added_lines=2`, and `aw commit` named both files unconditionally. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Made `E-01` and `E-02` idempotent (replacing any pre-existing `PUBRUN_RUN_MODE_OVERRIDE` row alongside `PUBRUN_IMPORT_MODE` while preserving unrelated rows, or leaving an already-converged file untouched with `--scope-ack`), replaced item 3's script with a verbatim-presence and dash check that allows `added_lines=0` when already converged, and updated `V-01`, `V-02`, `## Scope check`, and gate item 4 accordingly (recommendation strength: strong). |
| PR-003 | MEDIUM | IN-SCOPE | R1 references | `.aw/records/plans/pending/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md:121-122` (`## Deferred / out of scope`); `pqcx6o` `E-05`; `docs/configuration.md:18` (`## Configuration Discovery`) | Bullet 3 cited `- Carrier: pqcx6o` for adding `XDG_CONFIG_HOME`, `APPDATA`, and `PUBRUN_DEBUG` rows to `docs/configuration.md`. `pqcx6o` adds `PUBRUN_DEBUG` and `NO_COLOR` only and never touches `XDG_CONFIG_HOME` or `APPDATA` (already documented in `## Configuration Discovery` and `docs/functional_spec.md` Section 10.3). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split the deferral into `- Carrier: pqcx6o` (`PUBRUN_DEBUG` and `NO_COLOR` in `docs/configuration.md`), `- Carrier: wjsccu` (`PUBRUN_DEBUG` and `NO_COLOR` in `docs/functional_spec.md`), and `- Carrier-Declined:` for `XDG_CONFIG_HOME`/`APPDATA` with evidence of existing documentation (recommendation strength: strong). |
| PR-004 | LOW | IN-SCOPE | R1/R4 doc sync | `.aw/records/plans/pending/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md:173` (`## Spec / documentation sync`); `docs/manifest.md:521-536` (``## `pubrun_imports` ``); `docs/functional_spec.md:88-138` (`### 3.4 Import Modes`) | `## Spec / documentation sync` claimed `docs/manifest.md` and `docs/functional_spec.md` Section 3.4 already document `PUBRUN_RUN_MODE_OVERRIDE`. Neither names that variable (`docs/manifest.md` documents `"cli:pubrun run --mode"` provenance; Section 3.4 documents `pubrun run --mode <mode>` override behavior). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote `## Spec / documentation sync` to describe accurately what each file documents and noted the cross-Set overlap with `pqcx6o` and `wjsccu` (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` (rejected: cross-Set overlaps on both target files and reviewed plan `pqcx6o` parses this plan's item 3); `complex` (rejected: docs-only, 2 E-items, no security or runtime code) | Step T answers and `pqcx6o` review record D-1 | yes |
| D-2 | How to coordinate cross-Set overlap with `pqcx6o` and `wjsccu`? | Make `E-01`, `E-02`, validation, and commit instructions idempotent in either execution order without adding cross-Set `- Item-Dependencies:` | Add `- Item-Dependencies: executed:pqcx6o, executed:wjsccu` (rejected: `wjsccu` is unreviewed and cross-Set ordering is unnecessary when edits converge verbatim, matching `pqcx6o` Decision D-2) | `pqcx6o` `E-05`/`V-05`, `pqcx6o` review record D-2, and `wjsccu` `E-03` | yes |
| D-3 | How to resolve the `"Takes highest precedence"` collision with `pqcx6o` `V-05`? | Reword item 3 row 1 from `"Takes highest precedence, overriding"` to `"Takes precedence over"` | Leave wording unchanged (rejected: breaks `pqcx6o` `V-05`'s negative grep); edit `pqcx6o` (rejected: out of scope for this review) | `pqcx6o` `V-05` dynamically extracts `87qr8h` item 3 and asserts `grep -n "Takes highest precedence" docs/configuration.md` exits `1` | yes |
| D-4 | How to correct the false `pqcx6o` carrier for `XDG_CONFIG_HOME` and `APPDATA`? | Split into `Carrier: pqcx6o` (`PUBRUN_DEBUG`, `NO_COLOR` in `docs/configuration.md`), `Carrier: wjsccu` (`PUBRUN_DEBUG`, `NO_COLOR` in `docs/functional_spec.md`), and `Carrier-Declined:` for `XDG_CONFIG_HOME`/`APPDATA` | File a new backlog item for `XDG_CONFIG_HOME`/`APPDATA` (rejected: both are already documented in `docs/configuration.md` `## Configuration Discovery` and `docs/functional_spec.md` Section 10.3) | `docs/configuration.md:18`, `docs/functional_spec.md:393-394`, `pqcx6o` `E-05`, and `wjsccu` `E-03` | yes |

### Step S5

- Checked: `## Open questions` is `None.`. Every finding (`PR-001`..`PR-004`) had Overall Remediation Risk `Low` and was fixed in place. Every decision (`D-1`..`D-4`) is backed by repository evidence and reversible (`Reversible: yes`). Every deferred item carries an accurate `- Carrier:` or `- Carrier-Declined:`. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, and no edits introduced new questions or ambiguities. Re-read the complete revised plan after editing, verified the embedded Python validation check parses the revised plan cleanly, verified `pqcx6o` `V-05`'s extraction snippet extracts both rows cleanly with zero `"Takes highest precedence"` matches, and verified `aw ipd lint --phase review-finalize --agent` exits `0` (`outcome: clean`, `findings: 0`). No second pass is needed.

AW-REVIEW: DONE
