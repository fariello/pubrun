# Review findings: ipd 98e99m

- Subject-Id: 98e99m
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-4ht7x4-01-98e99m-list-full-in-pubrun-import-mode-row-of-docs-configuration-md.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md` Section 11.1 code citation rules, plus `docs/configuration.md` (`## Environment Variables` and `### [imports]`), `docs/cli.md` (`### run`), `src/pubrun/_modes.py::MODES` and `::VALID_MODES`, `src/pubrun/_config_boot.py::resolve_import_mode`, `src/pubrun/__init__.py`, `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress`, `scripts/sanitize_paths.py`, `.aw/records/backlog/graduated/20261124-4ht7x4-01-4ht7x4-list-full-in-pubrun-import-mode-row-of-configurati.backlog.md`, `.aw/records/backlog/graduated/20261124-oubh58-01-oubh58-resolve-run-mode-vs-in-code-import-precedence-clai.backlog.md`, and `.aw/records/plans/pending/20261124-oubh58-01-lhwy0t-implement-launch-time-pubrun-run-mode-override-over-in-code.ipd.md`. No pre-review snapshot was needed: lane `HEAD` `0d88258` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(c) applies (single entity, one-step edit; no diagram should be added).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-01` Expected outcome and `Project conventions discovered` | Used single-backtick code spans with backslash-escaped inner backticks for the `PUBRUN_IMPORT_MODE` table row | Replaced both with double-backtick code spans so inner backticks render cleanly without backslashes | Backslashes do not escape backticks inside CommonMark/GFM code spans; prevents malformed rendering and accidental backslash copy into `docs/configuration.md` (PR-002). |
| `Deferred / out of scope` | Described `oubh58` as an unresolved question ("Resolving whether `pubrun run --mode` overrides...") and equated it with `"Takes highest precedence."` | Clarified that `oubh58` (graduated to plan `lhwy0t`) tracks `pubrun run --mode` vs. in-code `import pubrun.<mode>` precedence and that changing `"Takes highest precedence."` is out of scope for `4ht7x4` (keeping `- Carrier: oubh58`) | Matches the actual state of graduated backlog item `oubh58` and pending plan `lhwy0t` (PR-003). |
| `Project conventions discovered`, `Required tests / validation`, and `V-01` | Left the Python parity probe unspecified (risking `PUBRUN_IMPORT_MODE=full` auto-starting a run via `src/pubrun/__init__.py`) and used dotted module names instead of Section 11.1 `path::Symbol` citations | Added the `_execute_boot_sequence` import convention, replaced the prose check with an exact side-effect-free `PUBRUN_AUTO_START=false PYTHONPATH=src python3 -c '...'` command, and used Section 11.1 `path::Symbol` citations | Prevents untracked `runs/` artifacts during validation and satisfies Section 11.1 and requirement 6 (PR-001, PR-003). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`docs/configuration.md`), 1 E-item in 1 task group, `- Kind: child`.

1. No: documentation-only correction to one Markdown table row in `docs/configuration.md` to match existing runtime behavior (`src/pubrun/_modes.py::VALID_MODES` and `src/pubrun/_config_boot.py::resolve_import_mode`); changes no code, schema, CLI option, or configuration contract.
2. No: touches only `docs/configuration.md`, no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 1 E-item, 1 task group, 1 file, 1 line changed.
4. Yes: `docs/configuration.md`.
5. No: text-only one-line edit in a Markdown table; cannot lose data or break code, and is trivially reversible.

AW-TIER: simple

### Step Q

- Checked: what the one-line edit to `docs/configuration.md:361` could break; whether any test or other doc asserts on or duplicates the `PUBRUN_IMPORT_MODE` row (`grep -rn "configuration.md" tests/` returned nothing; `grep -rn "PUBRUN_IMPORT_MODE" docs/ src/ tests/` confirmed `docs/configuration.md:361` is the sole environment-variable mode list; `docs/configuration.md:81` and `docs/cli.md:743` already list all six modes); whether `lhwy0t` (`oubh58`) edits `docs/configuration.md` (no, its `- Scope-Paths:` excludes `docs/configuration.md`); whether `src/pubrun/_modes.py::MODES` key order matches the proposed row (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full` — exact match); and whether the validation commands have side effects.
- Confirmed via `PUBRUN_AUTO_START=false PYTHONPATH=src python3 -c ...`: `resolve_import_mode()` returns `('full', 'env:PUBRUN_IMPORT_MODE')` and `VALID_MODES` has all six modes; `git status --short` remained empty; `python3 scripts/sanitize_paths.py --check --all` exited 0.
- PR-001: inspecting `src/pubrun/__init__.py:319-346` and `src/pubrun/_bootstrap.py:256-284` (`is_mode_submodule_import_in_progress`) showed that `pubrun._config_boot` is not in `_MODE_SUBMODULES`. Running a naive `PUBRUN_IMPORT_MODE=full python3 -c "from pubrun._config_boot import ..."` executes `_execute_boot_sequence()`, auto-starting a live run in `full` mode and writing untracked `runs/` files into the checkout. Fixed by specifying `PUBRUN_AUTO_START=false PYTHONPATH=src` during import and setting `os.environ["PUBRUN_IMPORT_MODE"] = "full"` afterward in a single non-vacuous Python check in `Required tests / validation` and `V-01`.
- PR-002: `E-01` Expected outcome and `Project conventions discovered` used backslash-escaped backticks inside single-backtick Markdown code spans. Fixed with double-backtick code spans.
- PR-003: `Deferred / out of scope` described `oubh58` as still unresolved (it graduated to `lhwy0t` after a 2026-11-25 decision) and `Required tests / validation` used dotted module names instead of Section 11.1 `path::Symbol` citations. Fixed.

### Step S5

- Checked: `## Open questions` is `None.`. The single deferral carries `- Carrier: oubh58` (verified in `.aw/records/backlog/graduated/`). All three review findings (PR-001, PR-002, PR-003) have Overall Remediation Risk `Low` and were fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | Check Q / R2 (validation probe side effects and precision) | Plan `Required tests / validation` (line 70) and `V-01` (line 87); `src/pubrun/__init__.py` (`_execute_boot_sequence`, lines 321-346); `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress` (lines 256-284) | `Required tests / validation` and `V-01` asked for a `PUBRUN_IMPORT_MODE=full` check importing `pubrun._config_boot` without disabling boot auto-start first. Because `pubrun._config_boot` is not in `_MODE_SUBMODULES`, running with `PUBRUN_IMPORT_MODE=full` in the shell environment triggers `_execute_boot_sequence()`, auto-starting a run and creating untracked `runs/` files in the checkout. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the import-boot convention and replaced the prose check in `Required tests / validation` and `V-01` with an exact side-effect-free `PUBRUN_AUTO_START=false PYTHONPATH=src python3 -c '...'` command that sets `os.environ["PUBRUN_IMPORT_MODE"] = "full"` after import, asserts parity with `VALID_MODES`, and verifies zero em or en dashes (recommendation strength: strong). |
| PR-002 | LOW | IN-SCOPE | Check P (malformed Markdown code spans) | Plan `E-01` Expected outcome (line 39) and `Project conventions discovered` (line 47) | Both lines wrapped the `PUBRUN_IMPORT_MODE` table row in single-backtick code spans with backslashes before inner backticks. CommonMark/GFM treats backslashes inside code spans as literal characters, breaking rendering and risking literal backslashes being copied into `docs/configuration.md`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced both spans with double-backtick code spans matching `Proposed changes` item 1 (recommendation strength: strong). |
| PR-003 | LOW | IN-SCOPE | Check P / Section 11.1 (stale deferral wording and dotted citations) | Plan `Deferred / out of scope` (line 60) and `Required tests / validation` (line 70); `.aw/records/backlog/graduated/20261124-oubh58-01-oubh58-resolve-run-mode-vs-in-code-import-precedence-clai.backlog.md:13-15` | `Deferred / out of scope` described `oubh58` as an unresolved question even though it was decided on 2026-11-25 and graduated to plan `lhwy0t`, and `Required tests / validation` cited dotted module names (`pubrun._config_boot.resolve_import_mode`, `pubrun._modes.VALID_MODES`) instead of Section 11.1 `path::Symbol` citations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `Deferred / out of scope` to note `oubh58` graduated to `lhwy0t` while preserving `- Carrier: oubh58`, and updated `Required tests / validation` to Section 11.1 `path::Symbol` citations (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `simple` | `standard` | Documentation-only one-row update in `docs/configuration.md` matching existing runtime behavior in `src/pubrun/_modes.py::VALID_MODES` and `src/pubrun/_config_boot.py::resolve_import_mode`; all five tier risk questions answered No (Scope-Paths declared). | yes |
| D-2 | Keep `"Takes highest precedence."` text unchanged in `98e99m` | Leave unchanged, deferred to `oubh58` (`lhwy0t`) | Edit the precedence sentence in `98e99m` | `.aw/records/backlog/graduated/20261124-4ht7x4-01-4ht7x4-list-full-in-pubrun-import-mode-row-of-configurati.backlog.md` limits acceptance strictly to adding `full` to the mode list in the `PUBRUN_IMPORT_MODE` row; `oubh58` owns the CLI-override precedence work. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All three findings (PR-001, PR-002, PR-003) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified before committing. No second review pass is needed.

AW-REVIEW: DONE
