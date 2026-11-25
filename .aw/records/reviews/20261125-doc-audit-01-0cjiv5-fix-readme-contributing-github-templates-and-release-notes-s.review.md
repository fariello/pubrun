# Review findings: ipd 0cjiv5

- Subject-Id: 0cjiv5
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Claude Opus 5.5 (OpenCode)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete plan text against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 citation forms. No pre-review snapshot was needed: lane `HEAD` `1ff4eb9` had a clean working tree and the plan was already committed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`) before any edit. Requirement 12: no diagram is needed. The six steps are independent edits to unrelated files, with no entity relationships, branch, loop, or lifecycle, and the plan now says so in `## Scope check`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| E-01 | "`[CONTRIBUTING.md](CONTRIBUTING.md)` or `https://...`" | Absolute URL only, with the reason | Removes an executor choice whose first option is a broken link (PR-001). |
| E-02 | "noting `.[dev]` suffices"; "Remove ... or note it is already covered"; "also requires `pyyaml`" | One concrete instruction each; `pyyaml` described as optional with the skipping tests cited | Removes "or" alternatives and an inaccurate "requires" (PR-002). |
| E-03 | "point ... to `00_auto_start.py` (or clarify ...)"; "`--format markdown` or `--format latex`"; "clarify item 4" | One chosen action each | Removes executor-invented decisions (PR-004). |
| E-04 | "clear top-of-file historical-archive notice"; "(copied into `CHANGELOG.md`)" | Placement, content, and the `CHANGELOG.md` heading named; body stays unchanged | Makes the requirement verifiable (requirement 6). |
| Approval gate item 2 | "modify only the six paths" | Seven declared paths; out-of-scope edits justified at finalize | Matches the scope-fence wording rule and the new path (PR-007). |
| Approval gate item 5 | Unconditional `aw ipd finalize` | Conditional runner or executor ownership, no hand `git mv` | Matches the lifecycle contract (PR-007). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (six paths at review start, seven after), 4 E-items in 2 task groups at review start, `- Kind: child`, Set `doc-audit` sibling Scope-Paths.

1. No: documentation, GitHub templates, and one YAML comment. No spec, CLI option, output format, or configuration key changes. Two issue templates are deleted, which changes only the GitHub issue chooser.
2. No: no code guarding private data, commits, worktree isolation, merges, or the sandbox. The plan does touch `.pre-commit-config.yaml`, but only a comment and a hook display name.
3. Somewhat: six root documents across two task groups, but every edit is local prose; `README.md` alone carried seven sub-edits in one E-item.
4. Yes: all paths are declared.
5. No: text edits and two template deletions are reversible with `git revert`. The HPC example is copied by users, so a wrong example costs users time but no data.

AW-TIER: standard

### Step R1

- Checked every material citation against the repository:
  - `.github/pull_request_template.md` "CONTRIBUTING.md": present.
  - `.github/ISSUE_TEMPLATE/`: `bug_report.md`, `feature_request.md`, five `.yml` forms, and `config.yml` present.
  - `CONTRIBUTING.md#Development setup` and `#Local hooks and path hygiene`: text matches the plan's description.
  - `pyproject.toml` `[project.optional-dependencies]`: `dev` lacks `textual` and `pyyaml`; `tui` has `textual`.
  - `.github/workflows/ci.yml` job `extra-suites`: "pip install -e ".[dev]" pyyaml".
  - `scripts/update_commit_file.py::main`: no-op cleanup. `hatch_build.py`: stamps wheel and sdist paths.
  - `src/pubrun/__main__.py::main` `show_parser`: three `nargs="?"` positionals; the `show` dispatch iterates `filter_runs` results only when `run_dir` is empty.
  - `src/pubrun/report/utils.py::_is_meta_ref_allowed` and `::hydrate_manifest_with_report`: as claimed, except the plan named only `hydrate_manifest`, the wrapper (LOW drift; corrected in E-06).
  - `src/pubrun/capture/liveness.py`: `kernel32` and `wmic`, no `psapi`.
  - `src/pubrun/status.py::STATUS_BROKEN_PIPE`, and `--preflight` on `inspect_parser` and `rerun_parser`.
  - `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE` and `::LATEX_TEMPLATE`.
  - `examples/00_*` through `12_*`.
  - `LICENSE`, `NOTICE`, and `src/pubrun/__init__.py::__copyright__`: "Gabriele Fariello".
  - Tag `v1.2.0` holds `expected_methods_text.md`, `generated_output_notes.md`, and `tests/test_examples.py`; current `main` does not.
- Not found: `.pre-commit-config.yaml` hook `update-commit-file` still carries the retired instruction "Install with `pre-commit install --hook-type post-commit`". The plan did not cite it (PR-003).

### Step R2

- Checked: the E/V bijection; Scope-Paths against every file the steps edit; `- Item-Dependencies: none` against sibling plans `pqcx6o`, `dd7noz`, `wjsccu`, `77pdvl`, and `2uwuiu`, all of which have disjoint Scope-Paths; and each V-item for concrete, non-tautological evidence and reachability.
- Results:
  - V-03 demanded "link/anchor check output" and V-02 to V-04 demanded a "zero-dash check" without naming either command. Review ran both and pasted them into `## Required tests / validation`. The link check printed `broken=1` on the unrevised tree (the `file://` link). The dash check printed `exit=1` (no match) on an empty diff.
  - The plan's HPC expected outcome is a runtime claim ("actually works") with no runtime demonstration (PR-005).
  - The gate carried "modify only the six paths" and an unconditional `aw ipd finalize` (PR-007).

### Step R3

- Checked: the plan touches no authentication, secrets, or trust-boundary code. It removes a machine-local `file://` path from a public template, which reduces a local-information leak. `scripts/sanitize_paths.py --check --all` exits 0 on the current tree. The `.pre-commit-config.yaml` edit keeps the hook's `entry` and `stages`, so no hook is added, removed, or bypassed. The HPC example uses `meta_ref_allowed_dirs` (a scoped allowlist) as the primary option and mentions `allow_external_meta_ref = true` (allow everything) only as the alternative.

### Step R4

- Checked: rubric A through F, right-sizing, and spec and documentation sync.
- Results:
  - E-03 bundled seven independent `README.md` sections and one runtime-reachable claim. Review split it into E-03 (descriptive sections), E-05 (Windows and CLI reference), and E-06 (HPC example with demonstration) (PR-006). Six E-items now trigger the advisory `IPD-Z603` size note at info severity. Review accepted that rather than splitting the plan, because every item is a small local prose edit.
  - The two tests that read the touched files (`.github/scripts/test_benchmark_issue_form.py` reads `config.yml`; `tests/test_cli.py::TestCitationConsistency` reads `README.md`) were added to validation. They pass on the current tree (`9 passed in 1.77s`).
  - The spec and documentation sync line was accurate but now names the sibling owners of the matching `docs/` drift.
  - E-04's plan text said the v1.2.0 notes were "copied into `CHANGELOG.md`". `CHANGELOG.md` has `## [1.2.0] - 2026-06-22` with the same items, so the claim holds; review made the heading explicit.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | correctness | `.github/pull_request_template.md` "CONTRIBUTING.md"; `CONTRIBUTING.md` exists only at the repository root | E-01 offered `[CONTRIBUTING.md](CONTRIBUTING.md)` as an equal option. That relative link resolves to the nonexistent `.github/CONTRIBUTING.md` and does not resolve in a rendered pull request body. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-01 now requires the absolute `https://github.com/fariello/pubrun/blob/main/CONTRIBUTING.md` link and states why. |
| PR-002 | MEDIUM | IN-SCOPE | correctness | `.github/scripts/test_benchmark_issue_form.py::test_form_parses_as_yaml_when_available` and `.github/scripts/test_benchmark_intake_workflow.py::test_pyyaml_crosscheck_when_available` call `pytest.importorskip("yaml")` | E-02 told the executor to document `pyyaml` as required for `.github/scripts/`. Those tests skip without it, so "required" would be inaccurate documentation. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-02 now documents `pyyaml` as optional, enabling the YAML cross-check tests. D-03 wording is corrected to match. |
| PR-003 | MEDIUM | UNDER-SCOPE | completeness | `.pre-commit-config.yaml` "Install with `pre-commit install --hook-type post-commit`." and hook name "stamp src/pubrun/COMMIT with HEAD" | The retired stamping instruction that E-02 removes from `CONTRIBUTING.md` is repeated in the pre-commit config comment. Contributors read that comment, and no sibling plan owns the file. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `.pre-commit-config.yaml` to Scope and Scope-Paths. E-02 rewrites only the comment and `name:`, leaving `id`, `entry`, and `stages` unchanged so existing installs keep running the cleanup no-op. V-02 checks this and confirms the YAML still parses. |
| PR-004 | MEDIUM | IN-SCOPE | executability | E-02 and E-03 pre-review text: "(or clarify ...)", "`--format markdown` or `--format latex`", "or note it is already covered", "clarify item 4" | Several sub-steps left a choice or an undefined action to the executor, so two executors could produce different results and V-03 could not check a definite outcome. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Each alternative resolved to one action with its basis: `00_auto_start.py` is the one-import example; `--format markdown` is the parser default and matches the sample's Markdown shape; delete the duplicate install line; keep `register_metadata()` and name the shipped non-manifest alternatives. |
| PR-005 | HIGH | UNDER-SCOPE | testing | `src/pubrun/report/utils.py::hydrate_manifest_with_report`; `src/pubrun/config.py::load_local_config` reads `.pubrun.toml` from `Path.cwd()` | The HPC outcome ("actually works") was checked only by a diff. Review followed the proposed steps in `/tmp/opencode`. Without the `.pubrun.toml` allowlist the hydration status was `blocked_by_policy`. With the allowlist in the working directory it was `hydrated`. With the same allowlist but the report run from another directory it was `blocked_by_policy` again. The plan did not say that the policy is read where the report command runs. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | New E-06 owns the HPC example and states the working-directory rule. V-06 requires a pasted scratch-directory transcript showing `hydrated` versus `blocked_by_policy`, produced by existing code path `hydrate_manifest_with_report`. |
| PR-006 | MEDIUM | IN-SCOPE | right-sizing | E-03 pre-review text listed seven independent `README.md` sections | One E-item covered examples, sample output, Windows, CLI reference, HPC, roadmap, and license. V-03 needed seven unrelated checks, and the HPC part needed a runtime check. A small executor could lose a sub-edit. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Split into E-03 (descriptive sections), E-05 (Windows and CLI reference), and E-06 (HPC). Ids assigned by `aw ipd sync --apply`. V-03, V-05, and V-06 each require negative `grep` checks for the removed text. |
| PR-007 | MEDIUM | IN-SCOPE | execution contract | `## Approval and execution gate` items 2, 3, and 5 | Item 2 said "modify only the six paths", which is a stop-style fence and was stale after PR-003. Item 5 told the executor to run `aw ipd finalize` unconditionally. Item 3 lacked the explicit "never claim without pasted output" rule. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote item 2 as a declaration with `--scope-reason` and `--scope-ack`. Rewrote item 5 with conditional runner or executor ownership and no hand `git mv`. Strengthened item 3. |
| PR-008 | LOW | IN-SCOPE | evidence | V-02 to V-04 "zero-dash check"; V-03 "link/anchor check output" | The validation named checks but no commands, so the evidence was not reproducible. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added both exact commands to `## Required tests / validation`, with their passing output (`exit=1` for the dash grep, `broken=0` for links). Review ran both: the link check reported `broken=1` before execution (the `file://` link, the defect E-01 fixes). |
| PR-009 | LOW | IN-SCOPE | evidence | `src/pubrun/__init__.py::__all__` has `register_output`; tag `v1.3.1` does not; `CHANGELOG.md` `## [Unreleased]` | The roadmap fix could lead the executor to call `register_output()` part of a released version. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-03 says the file registration API is unreleased and must not be given a version. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` (rejected: seven files and a user-copied HPC example); `complex` (rejected: no contract or security code) | Step T answers | yes |
| D-2 | Which link form fixes the PR template? | Absolute GitHub URL | Relative `CONTRIBUTING.md` (broken from `.github/`); `../CONTRIBUTING.md` (does not resolve in a rendered PR body) | `CONTRIBUTING.md` exists only at the repository root | yes |
| D-3 | Which `--format` should the README sample use? | `markdown` | `latex` with a LaTeX sample (longer, includes `.bib` comments, less readable in a README) | `methods_parser` `--format` default `markdown`; the existing sample is Markdown prose | yes |
| D-4 | Keep or delete roadmap item 4 `register_metadata()`? | Keep it and name shipped alternatives | Delete it (no shipped API writes structured data into the manifest itself, so it is still future work) | `src/pubrun/core.py::annotate`, `::report`, `::register_file` write events, a separate file, or one file record | yes |
| D-5 | Copyright holder name (OQ-01, already resolved by the author) | Keep the author's resolution: `Gabriele Fariello` | `Gabriele G. R. Fariello` | `LICENSE` and `NOTICE` "Copyright 2007-2026 Gabriele Fariello"; `src/pubrun/__init__.py::__copyright__`; `pyproject.toml` authors; `CITATION.cff` given-names "Gabriele" | yes |
| D-6 | Edit `.pre-commit-config.yaml` here or in a new plan? | Here, comment and `name:` only | New child plan (rejected: one comment, same concern as E-02); also remove the hook (rejected: existing `post-commit` installs would call a missing hook id) | No sibling Scope-Paths names `.pre-commit-config.yaml`; `scripts/update_commit_file.py` docstring says it stays "for existing `post-commit` hook installations" | yes |
| D-7 | Split the plan for `IPD-Z603` (six E-items)? | Keep one plan | Split README work into another child (rejected: same file, and parallel children editing `README.md` would add merge risk without benefit) | `aw ipd lint --phase review-finalize` reports `IPD-Z603` at info severity only | yes |

### Step S5

- Checked: OQ-01 (`Blocking: no`, `Status: resolved`, `Owner: plan author`). The repository answers it (D-5), so it stays resolved. Every finding is FIXED, so no finding is escalated and no new open question is needed. No decision is irreversible. The lane outcome carries `questions: []`.

### Step S6

- Checked: this pass added E-05 and E-06 with V-05 and V-06, and added `.pre-commit-config.yaml` to Scope-Paths. Rule 1 therefore called for a second pass. Review re-read every item against the revised text:
  - The tokens "six paths", "seven corrections", and "requires `pyyaml`" no longer appear in the plan.
  - Proposed changes 1 to 6 map to E-01 to E-06.
  - `## Scope check` and `## Spec / documentation sync` name the new path.
  - V-02 covers the new `.pre-commit-config.yaml` edit.
  - `aw ipd lint --phase review-finalize --agent` exits `0` with only the info-level `IPD-Z603`.
- The second pass raised no new finding.

AW-REVIEW: DONE
