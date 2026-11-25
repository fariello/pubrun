# Review findings: ipd srs7bs

- Subject-Id: srs7bs
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-rand-mypy-00-srs7bs-randomized-ci-test-order-and-legacy-mypy-burn-down.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 citation rules. No pre-review snapshot was needed: lane `HEAD` `76fd0da` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`) and `aw ipd coverage srs7bs` exited 0 (`Orchestrator srs7bs is ready for review.`). Preserved all H2 headings, `E-01`..`E-06` and `V-01`..`V-06` ids, checkbox states, and field names. Requirement 12(b), (d), and (e) are satisfied by the Set dependency architecture Mermaid flowchart.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `Concern`, `Goal`, Mermaid node `G`, `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, `Scope check` | Described `gzc672` as `approved, not yet executed` with 20 listed modules (claiming `pubrun.capture.subprocesses` was unlisted, `k6fs5k` removed 5 modules, `0uxy76` followed 18 removed modules, and `f5yisk`/`qe6dad` validated exit-1 `mypy` output) | Synchronized with executed `gzc672` (21 listed modules including `pubrun.capture.subprocesses` for `z5xr49`) and reviewed children (`k6fs5k` removes all 6 capture entries, `0uxy76` follows 19 removed entries, and `f5yisk`/`qe6dad`/`k6fs5k` each validate `mypy` exiting 0) | Eliminates direct cross-plan contradictions with `pyproject.toml:115-141` and reviewed children `f5yisk`, `qe6dad`, `k6fs5k`, `0uxy76`, and `juoqy2` (PR-001). |
| `Completion criteria`, `Cross-IPD validation`, `Required tests / validation`, `V-01`..`V-06` | Hardcoded `58 source files` without re-derivation, claimed every new test file (including single-test `qe6dad` and `0uxy76`) runs repeatedly under `-p randomly`, said every CI job prints `Using --randomly-seed=`, omitted the human-authorized push/PR CI gate note, and omitted `E-*` `performed` / `V-*` `pass` wording in `V-01`..`V-06` | Re-derives `<N> source files` (`58` at review), distinguishes multi-test `-p randomly` loops (`k6fs5k`, `juoqy2`) from single-test files (`qe6dad`, `0uxy76`), distinguishes 23 `pytest` jobs from all 25 CI jobs (`1kcrdn`), notes the CI matrix gate on `1kcrdn`/`juoqy2`, and aligns `V-01`..`V-06` with `E-01`..`E-06` | Aligns orchestrator validation and completion criteria with all six reviewed children (PR-002). |
| `Concern`, Mermaid node `G`, `Child IPDs`, `Completion criteria`, `## Workflow history` | Left `CI` unexpanded on first use, left Mermaid node `G` without `executed`, cited `CONTRIBUTING.md` without `#Development setup`, and lacked `/plan-review` history line | Expands `Continuous Integration (CI)` on first use, updates Mermaid node `G` and `CONTRIBUTING.md#Development setup` citations, and prepends the newest-first `/plan-review` history entry | Technical writing requirements 1 and 12(d)/(e), Section 11.1 citations, and Check S7 history contract (PR-003). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R1

- Checked: every child plan filename, id6, Order number, `- Status:`, `- Readiness:`, `- Item-Dependencies:`, `- Scope-Paths:`, Goal, and `V-*` checks across all six reviewed children in `.aw/records/plans/pending/20261124-rand-mypy-0[1-6]-*.ipd.md` (`1kcrdn`, `f5yisk`, `qe6dad`, `k6fs5k`, `0uxy76`, `juoqy2`); executed prerequisites `gzc672` and `m66tfv` in `.aw/records/plans/executed/`; graduated backlog item `qqwebg` in `.aw/records/backlog/graduated/20261123-test-audit-01-qqwebg-ci-randomly-and-legacy-mypy-debt.backlog.md`; and `pyproject.toml:115-141` (21 `ignore_errors` entries including `pubrun.capture.subprocesses` at line 128).
- PR-001: `srs7bs` still carried pre-execution `gzc672` assumptions (20 modules, `gzc672` "approved, not yet executed", `pubrun.capture.subprocesses` unlisted, 18 modules removed before `0uxy76`, `k6fs5k` removing 5 modules, and `f5yisk`/`qe6dad` expecting exit-1 `mypy`). Fixed across all affected sections.

### Step R2

- Checked: `aw ipd lint --phase author --agent` (exit 0, `clean`, 0 findings) and `aw ipd coverage srs7bs` (exit 0, `Orchestrator srs7bs is ready for review.`) before edits. Verified typed child-tracking rows (`E-01`..`E-06` -> `CONFIRM <id6> REACHED executed`, `IPD-S407` clean), 1:1 `E-*`/`V-*` bijection, `- Scope-Paths:` self-scope, `- Item-Dependencies:` covering all six children (`executed:1kcrdn`..`executed:juoqy2`), valid `- Carrier-Declined:` dispositions on all three deferred items, aligned `V-01`..`V-06` evidence wording with `E-01`..`E-06`, and compliant 5-part Execution contract in `## Approval and execution gate`. Check T skipped per `plan-review.md` step 3 (Order-00 orchestrators are not rated by T, per spec `k3yx72` Section 5.1; `- Review-Depth: orchestrator`). Re-verified coverage and `aw ipd lint --phase review-finalize --agent` after edits.

### Step R7

- Checked: cross-plan consistency across the entire Set `rand-mypy` (`srs7bs` plus all six reviewed child plans `1kcrdn`, `f5yisk`, `qe6dad`, `k6fs5k`, `0uxy76`, `juoqy2`):
  - All six child plans (`01`..`06`) are `- Status: reviewed` with `- Readiness: go-pending-approval` and zero blocking open questions (`1kcrdn` `OQ-01` is `resolved`; `f5yisk`, `qe6dad`, `k6fs5k`, `0uxy76`, and `juoqy2` have `None.`).
  - Child table filenames, Order numbers (`01`..`06`), and dependency graph (`02, 03, 04 -> 05`, `04, 05 -> 06`, all `01..06 -> 00`; external `executed:m66tfv` on all six and `executed:gzc672` on `02..06`) match every child's `- Order:`, `- Item-Dependencies:`, `E-01`..`E-06`, and the Mermaid diagram.
  - Partition of `pyproject.toml:115-141`'s 21 `ignore_errors` entries is exact and disjoint: `f5yisk` (7) + `qe6dad` (6) + `k6fs5k` (6, including `pubrun.capture.subprocesses`) + `0uxy76` (2 + block deletion) = 21.
  - Shared-file edits are cleanly partitioned or serialized: `pyproject.toml` (`1kcrdn` comment above `addopts`, `f5yisk`/`qe6dad`/`k6fs5k` disjoint list entries, `0uxy76` block deletion after `02, 03, 04`); `.github/workflows/ci.yml` (`1kcrdn` `pytest` commands vs `juoqy2` `typecheck` job); `CONTRIBUTING.md` and `CHANGELOG.md` (`1kcrdn` random-order section vs `0uxy76` -> `juoqy2` serialized `mypy` section); `src/pubrun/capture/resources.py` and `subprocesses.py` (`k6fs5k` -> `juoqy2` serialized).
  - PR-001 and PR-002 fixed all remaining prose and validation-claim drifts between `srs7bs` and its six reviewed children.

### Step S5

- Checked: `## Open questions` is `None.`. Every child plan's open questions are resolved, all three deferred items carry valid `- Carrier-Declined:` reasons, and all three review findings (`PR-001`..`PR-003`) had Overall Remediation Risk `Low` and were fixed in place. No unresolved human decision remains, so `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R7 / R1 (stale `gzc672` 20-module / `subprocesses.py`-unlisted claims contradicting executed `gzc672` and reviewed children) | `pyproject.toml:115-141` (21 entries including `pubrun.capture.subprocesses`); reviewed children `f5yisk`, `qe6dad`, `k6fs5k`, `0uxy76`, `juoqy2`; Plan lines 5, 36-38, 46, 114, 118, 122-123, 132, 138-139, 156 | Orchestrator described `gzc672` as unexecuted with 20 listed modules, claimed `pubrun.capture.subprocesses` was unlisted so `f5yisk`/`qe6dad` expected exit-1 `mypy` and `k6fs5k` removed 5 modules, and stated 18 modules were removed before `0uxy76`—directly contradicting executed `gzc672` and all five reviewed `mypy` children. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Synchronized `Concern`, `Goal`, Mermaid node `G`, `Child IPDs`, `Completion criteria`, `Cross-IPD validation`, and `Scope check` with executed `gzc672` (21 listed modules) and all five reviewed `mypy` children (recommendation strength: very strong). |
| PR-002 | MEDIUM | IN-SCOPE | R7 / R2 (drifted completion criteria, `-p randomly` scope, CI job counts, and `V-01`..`V-06` parity) | Reviewed children `1kcrdn`, `qe6dad`, `k6fs5k`, `0uxy76`, `juoqy2`; Plan lines 129, 133-134, 141, 160, 170-198 | Orchestrator hardcoded `58 source files` without re-derivation, claimed single-test files in `qe6dad` and `0uxy76` ran repeated `-p randomly` loops, claimed every CI job (rather than the 23 `pytest` jobs) prints `Using --randomly-seed=`, omitted the human-authorized push/PR CI gate note for `1kcrdn`/`juoqy2`, and omitted `E-*` `performed` / `V-*` `pass` wording from `V-01`..`V-06`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Re-derived `<N> source files`, distinguished multi-test `-p randomly` loops (`k6fs5k`, `juoqy2`) from single-test files (`qe6dad`, `0uxy76`), distinguished 23 `pytest` jobs from all 25 CI jobs, documented the push/PR CI gate on `1kcrdn`/`juoqy2`, and aligned `V-01`..`V-06` with `E-01`..`E-06` (recommendation strength: very strong). |
| PR-003 | LOW | IN-SCOPE | Check P / Section 11.1 (acronym expansion, citation anchors, Mermaid label, history entry) | Plan lines 5, 46, 115-116, 124, 129; `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 and 12 | `CI` was unexpanded on first use, Mermaid node `G` omitted `executed`, and `CONTRIBUTING.md` references omitted the `#Development setup` heading anchor. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Expanded `Continuous Integration (CI)` on first use, updated Mermaid node `G` and `CONTRIBUTING.md#Development setup` anchors, and prepended the newest-first `/plan-review` history entry (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Align `srs7bs` `Cross-IPD validation` `-p randomly` wording with reviewed `qe6dad` and `0uxy76` rather than editing those already-reviewed children | Update `srs7bs` to distinguish multi-test repeated `-p randomly` loops (`k6fs5k`, `juoqy2`) from single-test files (`qe6dad`, `0uxy76`) | Re-open and edit `qe6dad` and `0uxy76` to add `-p randomly` loops for single-test files | A single-test file has only one test order on its own (its random-order behavior is exercised in the full CI suite once `1kcrdn` lands), and `srs7bs` review scope is `srs7bs` only. | yes |

### Step S6

- Checked: no `E-*` or `V-*` item was added or removed (`E-01`..`E-06` and `V-01`..`V-06` unchanged), `- Scope-Paths:` and `- Item-Dependencies:` did not change, and no new open question or structural ambiguity was introduced. All three findings (`PR-001`..`PR-003`) were fixed in place with Low remediation risk and swept across the whole plan. Coverage and `aw ipd lint --phase review-finalize --agent` will be re-verified in Step S7. No second review pass is needed.

AW-REVIEW: DONE
