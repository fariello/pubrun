# Review findings: ipd 6bgkyj

- Subject-Id: 6bgkyj
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-rmssqd-01-6bgkyj-guard-missing-host-os-fields-in-the-print-report-host-line.ipd.md` (front matter, Mermaid flowchart, E-01 to E-03, conventions, reproduction script and table, deferrals, OQ-01, V-01 to V-03, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches the E-01 logic and the prototype behavior.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning (PR-004). |
| V-02 | "listing all six parametrized cases"; pre-fix run described as "fails" | Names each case; pre-fix run must show every `host` case FAILED and the complete-host case PASSED; gives the exact worktree commands | Makes the evidence demand concrete and checkable (PR-002). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/report/diagnostics.py`, `tests/test_report_checks_bugs.py`, no `.spec.md`), E-item and task-group counts (3 items, 2 groups).

1. No: changes human-readable `pubrun show` text only; the manifest schema and every machine-readable format are unchanged, and no spec or doc describes the Host line.
2. No: touches no code guarding private data, commits, worktree isolation, merges, or the sandbox. Redaction rendering goes through the existing `_unwrap_value`.
3. No: 3 E-items in 2 task groups, one production line and one test file.
4. Yes: `- Scope-Paths:` lists both files.
5. No: a one-line display change, byte-identical for complete hosts, easy to revert.

AW-TIER: simple

### Step Q

- Checked: `src/pubrun/report/diagnostics.py::print_report` (Host line at the `if host_status == "failed":` branch, `hostname` via `_unwrap_value`); `src/pubrun/report/diagnostics.py::_unwrap_value` (returns `default` for `None` and `""`, unwraps `plain`, renders other representations as `<REP>`); `schemas/manifest.schema.json` `$defs/host/properties/os_name` and `os_version` (`["string", "null"]`); `src/pubrun/capture/host.py::get_host`; `src/pubrun/report/methods.py` (`"an unknown OS"`, `"unknown OS"`); `tests/test_report_checks_bugs.py::_report_manifest` (sets `meta_ref: None`, so hydration does not refill `host`) and `TestNullCpuModelPins`; `tests/test_edge_cases.py` (its null-OS manifest uses host status `failed`, the unchanged branch); backlog `rmssqd` (graduated to `6bgkyj`) and `zen6hs` (graduated, the TUI carrier); executed plan `ihh27o`; commit `e5189cf` exists.
- Reproduced with the plan's script and `PYTHONPATH=src`: the four Host lines contain `None` exactly as tabled. Applied E-01 to a scratch copy of `src/` under `/tmp/opencode/` (deleted afterwards): the four lines became `arm-01 - Linux (`, `arm-01 - Linux (`, `arm-01 - 6.8.0 (`, `arm-01 - unknown OS (`. A complete host printed `Host        : arm-01 - Linux 6.8.0 (unknown, 8.0 GB RAM)` before and after. A suppressed host printed `unknown - None None` before and `unknown - unknown OS` after, matching the plan's deferral text.
- Found an additional symptom on the same line: `os_name: {"representation": "redacted"}` printed `arm-01 - {'representation': 'redacted'} 6.8.0` on the base and `arm-01 - <REDACTED> 6.8.0` with the fix. The plan's conventions claim this rendering but no test pinned it (PR-001).
- Prototyped the E-02 class in a scratch test file: on the pre-fix `src/`, `6 failed, 1 passed` (the complete-host case passes); on the fixed `src/`, `7 passed`.
- Ran `python3 -m pytest -q` on the unmodified tree: `1819 passed, 2 skipped in 517.10s`, so V-03's zero-failure bar is reachable.
- What could break: only the Host line's text for hosts with missing, null, empty, or wrapped OS fields. No existing test asserts the buggy text.
- Deferrals: CHANGELOG `Carrier-Declined` claims that `ihh27o` did not edit `CHANGELOG.md` (true: its `- Scope-Paths:` omits it) and that `release-notes` drafts from commits (`.aw/system/workflows/release-notes/release-notes.md` step 2 "Read the commit history"). TUI deferral has `Carrier: zen6hs`.
- Gate: has precondition, scope fence with `--scope-reason`/`--scope-ack`, honesty, `aw commit 6bgkyj -- ...` with never-push, and runner-versus-executor `aw ipd finalize`. It lacked the pre-transition lint step (PR-003).

### Step R3 (short form not required)

- Checked: tier question 2 is "no"; no security review required. The change improves redaction display (a wrapped value no longer prints its dict text) and exposes no new data.

### Step S5

- Checked: OQ-01 (resolved, non-blocking; basis `print_report` `unknown` fallbacks and `methods.py` `"an unknown OS"`). All three deferrals carry `Carrier` or `Carrier-Declined`. All findings have Low remediation risk and are fixed. No question needs the human; no finding is OPEN or DEFERRED.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | low | UNDER-SCOPE | R4 D (invariant without a test) | `src/pubrun/report/diagnostics.py::_unwrap_value` ("return f\"<{rep.upper()}>\""); review probe with `os_name: {"representation": "redacted"}` printed `{'representation': 'redacted'} 6.8.0` on base and `<REDACTED> 6.8.0` with the fix | The plan's conventions claim that a redacted OS value renders like the hostname, and the fix delivers it, but no test pinned that behavior or recorded the pre-fix dict text. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added E-02 case (7) expecting `<REDACTED> 6.8.0` and recorded the pre-fix symptom in Findings (recommendation strength: strong). |
| PR-002 | low | IN-SCOPE | R2 (evidence concreteness) | V-02 "listing all six parametrized cases ... showing that the parametrized test fails on the pre-fix code" | V-02 did not say what the pre-fix run must show per case, did not cover the complete-host control, and left the worktree commands to the executor. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | V-02 now requires every `host` case PASSED on the fixed tree; on the pre-fix code, every `host` case FAILED and the complete-host case PASSED. It names `git worktree add /tmp/opencode/6bgkyj-prefix HEAD`, the removal command, and pasted `git worktree list` (recommendation strength: strong). |
| PR-003 | low | UNDER-SCOPE | R2 gate (execution contract) | Gate item 5 "finalize this plan with `aw ipd finalize 6bgkyj`" | The lifecycle step did not require `aw ipd lint --phase pre-transition` to conform after all E/V items, and the precondition did not state the OQ-01 status. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the pre-transition lint requirement and the OQ-01 status line (recommendation strength: medium). |
| PR-004 | low | IN-SCOPE | Check P (writing, `IPD-C802`); R1 evidence | `aw ipd lint --phase author` reported 2 `IPD-C802` info diagnostics | Two em dashes in the validation boilerplate. Findings lacked a review-time re-check and the green-suite baseline, and did not explain why the script needs `PYTHONPATH=src`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the dashes. Added a re-check paragraph: the reproduction, the prototype output, the `1819 passed, 2 skipped` baseline, and the `PYTHONPATH=src` rationale (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Should the regression tests also pin redacted OS rendering? | Yes, as parametrized case (7) | Leave it unpinned; add a separate test class | The plan already claims the behavior in its conventions; the review probe shows the base prints raw dict text; one extra case costs nothing | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined E-02, Findings, V-02, the boilerplate, and the gate. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
