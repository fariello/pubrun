# Review findings: ipd 67hcid

- Subject-Id: 67hcid
- Subject-Type: ipd
- Reviewed-At: 2026-11-24
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-0mnekm-01-67hcid-guard-missing-cpu-fields-in-the-tui-details-cpu-model-line.ipd.md` (front matter, Mermaid flowchart, E-01 to E-03, V-01 to V-03, conventions, findings, reproduction script, proposed changes, deferrals, scope check, required tests, spec sync, OQ-01, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches the four-way result in E-01 (all missing gives `-`, head is model or `unknown`, optional details, parentheses only when a detail is present). Terminology is consistent (`CPU model line`, `head`, `details list`). No dash advisories. Wording is clear; the review's edits are substantive and recorded as findings, not proofreading changes.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (2 files), 3 E-items in 2 task groups, every reader of `hardware.cpu.logical_cores` in `src/pubrun`.

1. No: it changes one display line of the TUI General Info tab; no spec, CLI option, file format, or configuration key changes, and no doc describes the line (`grep -rln "General Info\|HOST & HARDWARE" docs README.md .aw/records/specs` returns nothing).
2. No: it does not touch code that guards private data, commits, worktree isolation, merges, or the sandbox.
3. No: 3 E-items, one source file and one test file.
4. Yes: both files are listed.
5. No: a wrong result is a cosmetic display error, and the change is easy to undo.

AW-TIER: simple

### Step Q

- Checked: `src/pubrun/tui/widgets/details.py::RunDetailsView.update_general_pane` (CPU line at line 327; `cpu` already coerced to a dict at lines 322-323), `::_format_os_text` (line 139, the normalization rule to reuse), `::_escape_markup`; `src/pubrun/capture/hardware.py::get_hardware` (writes `architecture`, `logical_cores`, `model`; only `capture_state` when depth is `off`); `schemas/manifest.schema.json` `$defs.cpu_record` (all three fields nullable, none required; `logical_cores` integer with minimum 0) and `$defs.hardware_section` (requires only `capture_state`); `tests/test_tui_bugs.py::_write_manifest`, `::_DROP`, `::TestRunDetailsOsLine`; pending plan `bwoyan` (same source file, different line and different test file); executed sibling `46fixy` and its review record.
- What could break: only the text after `CPU model:`. No test asserts on the CPU line today (`grep -rn "CPU model" tests/*.py` finds only an unrelated docstring in `tests/test_report_checks_bugs.py`). Baseline: `python3 -m pytest tests/test_tui_bugs.py tests/test_tui.py tests/test_timing_consumers.py -q --no-cov -p no:cacheprovider` gave `71 passed in 45.26s`.
- Reproduced `## Findings` on this lane at `06000b6` with `PUBRUN_AUTO_START=false PYTHONPATH=src`: `None (None cores, None)`, `None (8 cores, x86_64)`, `Intel(R) Xeon(R) Gold 6248 (None cores, x86_64)`, `Intel(R) Xeon(R) Gold 6248 (8 cores, None)`, `None (None cores, None)`, `Intel(R) Xeon(R) Gold 6248 (8 cores, x86_64)`, then `textual.markup.MarkupError: auto closing tag ('[/]') has nothing to close`. All match the plan. `git status --short` was empty afterwards, so the command writes nothing into the checkout.
- Applied the E-01 design to a scratch copy of `src` under `/tmp/opencode/67hcid` (no repository code changed) and ran the same script against it: `-`, `unknown (8 cores, x86_64)`, `Intel(R) Xeon(R) Gold 6248 (x86_64)`, `Intel(R) Xeon(R) Gold 6248 (8 cores)`, `-`, `Intel(R) Xeon(R) Gold 6248 (8 cores, x86_64)`, `Vendor [Rev 2] [/] (8 cores, x86_64)`. These are exactly the seven lines V-01 demands. Direct calls on the scratch helper: `logical_cores=0` gave `Intel(R) Xeon(R) Gold 6248 (0 cores, x86_64)`, model `"  "` with null cores gave `unknown (x86_64)`, both details null gave `Intel(R) Xeon(R) Gold 6248`, a non-dict gave `-`.
- PR-001: E-01 states that `logical_cores` `0` must render `0 cores`, but no E-02 case pins it. The natural shortcut `cpu.get("logical_cores") or ...` (the pattern the other CPU readers use) drops `0`; a scratch check showed `0 or 'x'` evaluates to `'x'`. The schema allows `0` (minimum 0).
- V-02's pre-fix proof uses a temporary `git worktree` and runs under pytest's `pythonpath = ["src"]` (`pyproject.toml`) and `tests/conftest.py`, which prepends that checkout's `src`, so it tests the worktree's code. It is reachable. PR-002: V-02 says "the parametrized test ... fail[s]" without saying which cases; with case 12 added, that case and the unchanged-output test pass on pre-fix code, so the demand needed to name the expected split. It also did not say which commit is "pre-fix".

### Step S5

- Checked: OQ-01 (resolved, non-blocking, `Owner: plan author`, basis cited from the pane's `-` and `unknown` conventions and plan `46fixy`), the three deferrals (each `Carrier-Declined` with a reason), and all findings. Each finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED. No question needs the human.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | low | UNDER-SCOPE | Q (untested stated behavior) | Plan E-01 "An integer `0` for `logical_cores` is therefore present"; `schemas/manifest.schema.json` `$defs.cpu_record.logical_cores` minimum 0; `src/pubrun/report/diagnostics.py:875` uses `.get("model") or "unknown"` | E-01 promises `0 cores`, but no test pins it, so an executor using the repository's common `or` fallback would silently drop a zero core count. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added E-02 case (12), `logical_cores` `0` renders `Intel(R) Xeon(R) Gold 6248 (0 cores, x86_64)`; V-02 now counts twelve cases (recommendation strength: strong). |
| PR-002 | low | IN-SCOPE | R2 (evidence precision) | Plan V-02 "fail on the pre-fix code" | The pre-fix failure demand did not say which cases fail or which commit is pre-fix. With case 12, some cases pass on pre-fix code, so a literal reading was unsatisfiable. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-02 now demands cases (1) to (11) and the bracket test fail pre-fix while case (12) and the unchanged-output test pass, and names the pre-fix commit as the parent of the E-01 commit, checked out with `git worktree add --detach` (recommendation strength: strong). |
| PR-003 | low | IN-SCOPE | R4 F (self-documenting code) | `src/pubrun/tui/widgets/details.py::_format_os_text` docstring (lines 140-146) | E-01 did not ask for a docstring, while each sibling module-level helper carries one stating its rules. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01 now requires a docstring in the style of `_format_os_text` stating the `-`, `unknown`, and omitted-detail rules (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Should a test pin the `0 cores` rendering E-01 already promises? | Yes, add parametrized case (12) | Leave it to the executor's reading of E-01 | `schemas/manifest.schema.json` `logical_cores` minimum 0; the `or` fallback pattern in `src/pubrun/report/diagnostics.py:875` would drop it | yes |
| D-2 | Review tier | `simple` | `standard` | All tier answers are "no" except question 4 (Scope-Paths listed); one display line changes; same shape as `46fixy`, reviewed `simple` | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; E-01, E-02, and V-02 were refined in place. No new questions arose. No re-review pass needed.

AW-REVIEW: DONE
