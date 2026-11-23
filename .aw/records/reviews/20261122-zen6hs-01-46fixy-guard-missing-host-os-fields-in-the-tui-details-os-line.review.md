# Review findings: ipd 46fixy

- Subject-Id: 46fixy
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-zen6hs-01-46fixy-guard-missing-host-os-fields-in-the-tui-details-os-line.ipd.md` (front matter, Mermaid flowchart, E-01 to E-03, V-01 to V-03, conventions, findings, reproduction script, proposed changes, deferrals, scope check, required tests, spec sync, OQ-01, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches the four-way result in E-01; its normalization node is updated with PR-001.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation and cross-check boilerplate | Two em dashes around the "as distinct from" clause (`IPD-C802` advisory twice) | Commas and parentheses | Clears both `IPD-C802` advisories; meaning unchanged. |
| Goal, flowchart node B | "None or empty string becomes missing" | "None, empty, or whitespace-only becomes missing" | Keeps the diagram consistent with the revised E-01 rule (requirement 12). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (2 files), 3 E-items in 2 task groups, every reader of `host.os_release` in `src/pubrun`.

1. No: it changes one display line of the TUI General Info tab; no spec, CLI option, file format, or configuration key changes, and no doc describes the line.
2. No: it does not touch code that guards private data, commits, worktree isolation, merges, or the sandbox.
3. No: 3 E-items, one source file and one test file.
4. Yes: both files are listed.
5. No: a wrong result is a cosmetic display error, and the change is easy to undo.

AW-TIER: simple

### Step Q

- Checked: `src/pubrun/tui/widgets/details.py::RunDetailsView.update_general_pane` (OS line at line 300, `host` already coerced to a dict at line 294), `::_escape_markup`, `::_filter_package_rows`, `::_format_subprocess_rows` (module-level, textual-free); `src/pubrun/capture/host.py::get_host` (writes `os_name`, `os_version`, `os_release` as plain strings, or only `capture_state`); `schemas/manifest.schema.json` `host` properties (`["string", "null"]`, only `capture_state` required); `src/pubrun/status.py::RunInfo` (hostname unwrapped from a dict; OS fields are never wrapped); `tests/test_tui_bugs.py::_write_manifest`, `::_isolated_config`, `::TestRunDetailsGpu._render`; sibling plan `6bgkyj` (disjoint file `src/pubrun/report/diagnostics.py`); backlog `zen6hs` (graduated) and carrier `0mnekm` (open, the CPU line); commit `f6cfea2` resolves.
- What could break: only the text after `OS:`. No test asserts on the OS line today (`grep -rn "OS:" tests/*.py` returns nothing), and no other code reads it. Baseline: `python3 -m pytest tests/test_tui_bugs.py tests/test_tui.py tests/test_timing_consumers.py -q --no-cov` gave `61 passed in 37.88s`.
- Reproduced `## Findings` on this lane at `9478d9d` (textual 8.2.8): `Linux (None)` twice, `None (#101-Ubuntu SMP)`, `None (None)`; `#1 SMP [PREEMPT_DYNAMIC]` rendered `Linux (#1 SMP )`; `#1 SMP [/]` raised `MarkupError`. All match the plan.
- Applied the E-01 design to a scratch copy of `src` under `/tmp/opencode/46fixy` (no repository code changed) and rendered the same cases: `Linux`, `Linux`, `unknown (#101-Ubuntu SMP)`, `-`, `Linux (#1 SMP [PREEMPT_DYNAMIC])`, `Linux (#1 SMP [/])`. The design works, including the escaping.
- PR-001: the same scratch run rendered `os_release` `"  "` as `Linux (  )`, because the normalization rule tests only for an empty string.
- PR-002: the plan's reproduction command imports `pubrun` with the default `auto_start = true`, so it records the script as a run and writes `runs/pubrun-repro-*` into the repository root (observed; removed afterwards). `runs/` is gitignored, so nothing is committed, but the command leaves files in the checkout.
- V-02's pre-fix proof uses a temporary `git worktree` and runs in-process under pytest's `pythonpath = ["src"]`, so it tests that worktree's code. It is reachable in any environment.

### Step S5

- Checked: OQ-01 (resolved, non-blocking, basis cited from the pane's `-` and `unknown` conventions), the three deferrals (`Carrier: 0mnekm` exists as an open backlog item; two `Carrier-Declined`), and all findings. Each finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED. No question needs the human.
- OQ-01 recorded `- Owner: none` on a question the plan author resolved; changed to `plan author` (part of PR-003).

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | low | IN-SCOPE | Q (missing case) | Plan E-01 normalization rule; scratch render of `os_release: "  "` gave `Linux (  )` | A whitespace-only value counts as present, so the line still shows an empty pair of parentheses. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 now applies `.strip()` after normalization; Goal and flowchart updated; E-02 adds case (7) and V-02 counts seven cases (recommendation strength: strong). |
| PR-002 | low | IN-SCOPE | Q (side effect of a plan command) | Plan `## Findings` run command; `src/pubrun/resources/default.toml` `auto_start = true`; observed `runs/pubrun-repro-*` in the repository root | The reproduction command records itself as a pubrun run and writes into the checkout. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | The command now sets `PUBRUN_AUTO_START=false`, and the reason is stated; re-run with it wrote nothing (recommendation strength: strong). |
| PR-003 | low | IN-SCOPE | S5 (owner provenance) and Check P (wording) | Plan OQ-01; validation boilerplate | `Owner: none` on an author-resolved question; two em dashes raised `IPD-C802`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Set Owner to `plan author` and removed the dashes (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Should a whitespace-only OS value count as missing? | Yes, strip before the emptiness test | Keep it as present and print it | The plan's goal is to never print an empty or placeholder value; `-` is the pane's absent marker | yes |
| D-2 | Review tier | `simple` | `standard` | All five tier answers are "no" or "yes" to Scope-Paths only; one display line changes | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; E-01, E-02, and V-02 were refined in place. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
