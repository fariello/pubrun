# Review findings: ipd lwb332

- Subject-Id: lwb332
- Subject-Type: ipd
- Reviewed-At: 2026-11-24
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the full text of `.aw/records/plans/pending/20261123-nqrhyn-01-lwb332-deduplicate-overlapping-pubrun-imports-sections-in-docs-mani.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. No pre-review snapshot was needed: lane HEAD `93995d7` is clean and the plan is unchanged since `047a843`. `aw ipd lint --phase author --agent` reported `clean`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence naming three sources | Says what `pubrun_imports` records, what is wrong, and what the plan does; records why no diagram | Requirement 1 and requirement 12(c). |
| E-01 | "the version that lists `capture_state`"; "any internal TOC" | Locates the section by its neighbors and intro sentence, says exactly what to delete, and states that no TOC or link exists | Requirement 5: the executor must not guess the deletion bounds. |
| E-02 | One long sentence | Eight numbered row changes, each with its value | Requirement 6. |
| Findings | "The second occurrence ... matching `get_import_metadata`" | Lists each defect the second section has | The premise was false (PR-002). |
| Gate | One paragraph | Five-element execution contract | S7 execution contract. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`docs/manifest.md`), 2 E-items in 1 task group.

1. Partly: `docs/manifest.md` documents the manifest contract, but the plan changes no field, schema, or code; it corrects the description to match them.
2. No: no code guarding private data, commits, worktrees, merges, or the sandbox.
3. No: 2 E-items in one section of one file.
4. Yes: `docs/manifest.md`.
5. Low: text-only and undone by editing; the risk is publishing a still-wrong reference, which the parity check addresses.

AW-TIER: standard

### Step R1

- Checked: `docs/manifest.md` both `pubrun_imports` sections; `src/pubrun/_bootstrap.py::get_import_metadata`, `select_mode`, `_resolve_conflict_policy`; `src/pubrun/_modes.py::MODES`; `src/pubrun/_config_boot.py::resolve_import_mode`; `src/pubrun/tracker.py::Run._get_import_metadata`; `schemas/manifest.schema.json` `properties.pubrun_imports`; each mode submodule's `select_mode` call. Probes ran in scratch directories under `/tmp/opencode`: `import pubrun.minimal, pubrun.full` gave the nine top-level keys, the eight request keys, `conflict_policy` `"warn"`, and `selected_source` `"explicit"`; a manifest from `import pubrun` had `conflict_policy` `null` and no `pubrun_imports.capture_state`.
- Confirmed: the nine keys, the six modes, `force_console` only in `full`, and that `capture_state` is never emitted except by the exception fallback in `Run._get_import_metadata`.
- PR-001: both sections, and the plan's E-02 list of `selected_behavior` keys, omit `global_hooks`, which every entry of `src/pubrun/_modes.py::MODES` carries and `schemas/manifest.schema.json` declares under `selected_behavior.properties`. `requests[].effective_behavior` has the same gap. Executing the plan as written would have left the documented key set wrong. E-02 items 3 and 7 now name `global_hooks`.
- PR-002: Findings said the second section "documents all nine fields ... (matching `get_import_metadata` and `schemas/manifest.schema.json`)" and needed only a mode check and a dash fix. It also misses `global_hooks` and `force_console`, types `selected_behavior` as `object` though the schema allows `null`, omits `"explicit"` from `selected_source`, and does not say `conflict_policy` is `null` without a conflict. Findings and E-02 now list each.
- PR-003: E-02 listed `force_console` among "the emitted boolean keys" with "optional ... for `full`" but did not say it is absent in the other five modes. E-02 item 3 now says so.
- PR-004: the first section was described only as "the stale version". E-01 now locates it between `## profiling` and `## capture` and defines the deletion as the heading through the following `---`, so one separator remains. Proposed change 1 referred to "the top-level Table of Contents (if present)"; `docs/manifest.md` has none, and no Markdown file links to `#pubrun_imports`.

### Step R2

- Checked: the E/V bijection, each V-item's evidence, and the reachability of the runtime probe in Required tests 3 (`src/pubrun/_bootstrap.py::get_import_metadata`, reached by importing `pubrun.minimal` and `pubrun.full`).
- PR-005: V-02 asked the executor to "confirm exact parity" by reading a diff. That is a judgment, not evidence, and it is how the `global_hooks` gap survived authoring. Required tests 3 is now a parity script that compares the document's row names against a live probe and the schema, and checks each mode and behavior key. Run verbatim from the plan text, it printed eight mismatch lines and exited 1 on the current file, and printed `OK: pubrun_imports docs match runtime, schema, and MODES` (exit 0) on a scratch copy with the E-01 and E-02 edits applied. V-02 also requires a sentence for the E-02 changes the script does not test.
- PR-006: the old `grep -c '^## `pubrun_imports`'` check (Required tests) and the V-01 `grep -n '^## .*pubrun_imports'` used different patterns and neither checked placement. Required tests 1 now prints the four neighboring headings in order; on the scratch copy it gave `profiling` 492, `capture` 505, `pubrun_imports` 521, `status` 552. The dash check gained a command scoped to added lines.

### Step R3

- Checked: text-only change to a public document; no secrets, paths, or identifiers are introduced. The parity script runs pubrun in a fresh temporary directory, so it writes no `runs/` folder into the repository. `python3 scripts/sanitize_paths.py --check --all` exited 0 at review. No finding.

### Step R4

- Checked: rubric A to F (E and F apply), right-sizing (two single-concern items), and spec-sync truthfulness: no spec under `.aw/records/specs/` and no other file under `docs/` describes `pubrun_imports` fields (`grep` at review; `CHANGELOG.md` mentions the section only in a past release entry).
- PR-007: the gate lacked the execution contract elements: approval precondition, scope declaration with `--scope-reason` and `--scope-ack`, the paste-actual-output rule, `aw commit lwb332 -- docs/manifest.md`, and the runner and executor split for `aw ipd finalize lwb332`. Added. Spec / documentation sync now states the search and why no `CHANGELOG.md` entry is planned.

### Step R7

- Checked: Set `nqrhyn` has only this plan (no orchestrator, no siblings). The Set `ewgjmx` plan `c39m4v`, reviewed in the same run, edits `benchmarks/README.md` and does not overlap. No finding.

### Step S5

- Checked: the plan has no open questions. Every finding has Low remediation risk and is fixed, so none needs escalation and the lane outcome carries no question.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R1 (wrong key set) | `src/pubrun/_modes.py::MODES` every entry has `"global_hooks"`; schema `selected_behavior.properties.global_hooks` | Both sections and E-02 omit `global_hooks`; executing as written leaves the reference wrong. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 items 3 and 7 name `global_hooks`. |
| PR-002 | medium | IN-SCOPE | R1 (false premise) | `docs/manifest.md` "\| `selected_behavior` \| object \|"; probe `conflict_policy` `null`, `selected_source` `"explicit"` | Findings called the second section correct apart from modes and a dash. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Findings and E-02 items 3 to 6 list each defect. |
| PR-003 | low | IN-SCOPE | R1 (ambiguous outcome) | `src/pubrun/_modes.py::MODES` `"force_console": True` only under `"full"` | E-02 did not say `force_console` is `full`-only. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 item 3. |
| PR-004 | low | IN-SCOPE | R2 (deletion bounds) | `docs/manifest.md` has no TOC; no `#pubrun_imports` links | E-01 did not bound the deletion and referred to a nonexistent TOC. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 names the neighbors, the bounds, and the single remaining `---`. |
| PR-005 | high | UNDER-SCOPE | R2 (evidence cannot prove the change) | Parity script: 8 mismatches, exit 1 on current file; `OK`, exit 0 on scratch fix | V-02 relied on reading a diff for parity. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required tests 3 parity script; V-02 demands its `OK` output. |
| PR-006 | low | IN-SCOPE | R2 (validation command) | Two different `grep` patterns; no dash command | Heading and dash checks were inconsistent or missing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required tests 1 and 4. |
| PR-007 | medium | IN-SCOPE | S7 (execution contract) | Gate had one paragraph | Contract elements were missing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Five-element execution contract. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` | Doc-only, but it documents the manifest contract other tools read | yes |
| D-2 | Keep a `capture_state` row because the exception fallback in `Run._get_import_metadata` can emit it? | No row | Document it as a fallback-only field | The fallback is an error path not declared in `schemas/manifest.schema.json`; the backlog item `nqrhyn` and this plan's goal both require parity with the schema | yes |
| D-3 | Document `global_hooks` even though the original plan omitted it? | Yes | Leave the plan's key list as written | `src/pubrun/_modes.py::MODES` and the schema both carry it; the plan's own goal is exact parity | yes |
| D-4 | Validate parity by a live probe rather than against a hard-coded list? | Live probe plus schema | Hard-coded nine keys and six modes | A probe re-derives the facts at execution time, so a later mode addition is caught | yes |
| D-5 | Add a `CHANGELOG.md` entry? | No | Add one under `### Documentation` | Reference-text correction with no behavior change; the plan's Scope-Paths name only `docs/manifest.md` | yes |

### Step S6

- Checked: the review did not add or remove an E-item or V-item and did not change `- Scope-Paths:` or `- Item-Dependencies:`. It rewrote both E-items and both V-items; the rewritten commands were run verbatim from the plan text against the current file (exit 1) and against a scratch copy with the edits applied (exit 0). `aw ipd lint --phase review-finalize --agent` reported `clean`. No new question or ambiguity remains, so no second pass is needed.

AW-REVIEW: DONE
