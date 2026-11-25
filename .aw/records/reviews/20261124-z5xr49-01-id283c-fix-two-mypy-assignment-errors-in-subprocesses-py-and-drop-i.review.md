# Review findings: ipd id283c

- Subject-Id: id283c
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-z5xr49-01-id283c-fix-two-mypy-assignment-errors-in-subprocesses-py-and-drop-i.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md` Section 11.1 code citation rules, plus `src/pubrun/capture/subprocesses.py` (full file, lines 1-691), `pyproject.toml` (full file, lines 1-141), `tests/test_capture.py::TestUnwaitedPopenHarvesting` (lines 730-890), `CONTRIBUTING.md:33`, `.aw/records/backlog/graduated/20261124-z5xr49-01-z5xr49-fix-2-mypy-assignment-errors-in-src-pubrun-capture.backlog.md`, sibling plans `k6fs5k` and `juoqy2`, `MYPYPATH=src python3 -m mypy --config-file /dev/null --explicit-package-bases --follow-imports=silent src/pubrun/capture/subprocesses.py` (`mypy` 2.3.1, confirmed exact 2 `[assignment]` errors at lines 224 and 628), and `grep -rn "z5xr49\|capture\.subprocesses\|ignore_errors" CONTRIBUTING.md CHANGELOG.md docs/ .aw/records/specs/`. No pre-review snapshot was needed: lane `HEAD` `e6ca5d5` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(c) exemption applies (linear 2-step plan across 2 files; no diagram added).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-01`, `Proposed changes` item 1, `V-01`, `Deferred / out of scope` | Described the two `rec` -> `proc_rec` renames at a high level without spelling out all occurrences or the in-scope shadowing hazard in the uncovered `finalize_all` Phase 2 `pending_running` branch | Listed exact before/after scope for both `pending_running` blocks (3 lines in `_drain`, 9 lines / 8 `rec` occurrences in `finalize_all` Phase 2), warned about in-scope `rec` shadowing, required zero stale `rec` verification in `V-01`, and recorded `k6fs5k` as carrier for `finalize_all` Phase 2 behavioral test coverage | Prevents a partial rename in lines 628-636 from silently passing `mypy` and `pytest` while referencing the wrong record (PR-001). |
| `E-02`, `Project conventions`, `Proposed changes` item 2, `Required tests / validation`, `V-02` | Used `[tool.mypy.overrides]` (single brackets), instructed `remove and z5xr49` (leaving plural `backlog items qqwebg`), and omitted `--no-incremental` from `mypy` commands | Corrected to `[[tool.mypy.overrides]]` (`ignore_errors = true`), specified `# Remove each module as its existing errors are fixed (backlog item qqwebg).`, and added `--no-incremental` to both `mypy` commands | Fixes comment grammar, TOML table syntax, and stale `.mypy_cache` masking risk (PR-002). |
| `Goal`, `Project conventions`, `Findings`, `Deferred / out of scope`, `Spec / documentation sync`, `Approval and execution gate` items 4-5 | Used bare `SubprocessSpy.*` names and undescribed record IDs (`focjwv`, `gzc672`), wrote `N/A` for doc sync without noting `CONTRIBUTING.md:33` check, and omitted raw `git commit` ban and standalone `pre-transition` lint precondition in Gate items 4-5 | Applied Section 11.1 `path::Symbol` citations and descriptive record names, recorded the `CONTRIBUTING.md:33` / `docs/` verification, clarified `k6fs5k` execution-order interplay, and completed Gate items 4 and 5 | Section 11.1 citation rules, honest doc-sync evidence, and Check S7 execution-contract completeness (PR-003). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/capture/subprocesses.py, pyproject.toml`), `- Item-Dependencies: none`, 2 E-items in 1 task group, `- Kind: child`.

1. No: internal local-variable rename with type annotation in two methods of `src/pubrun/capture/subprocesses.py` and removing `"pubrun.capture.subprocesses"` from `[[tool.mypy.overrides]]` in `pyproject.toml`; no spec, public API, CLI, schema, or runtime contract changes.
2. No: edits only the two `pending_running` record-lookup blocks in `subprocesses.py` (not argv redaction) and the `mypy` overrides list in `pyproject.toml`; touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 2 focused E-items in 1 task group across 2 files.
4. Yes: `src/pubrun/capture/subprocesses.py, pyproject.toml`.
5. No: local variable rename with identical runtime behavior plus removing one `ignore_errors` module entry; cannot lose data and is trivially reversible (the only functional risk is a partial rename leaving a stale `rec` in scope, which PR-001 addresses explicitly).

AW-TIER: simple

### Step Q

- Checked: `src/pubrun/capture/subprocesses.py:11` (`Any`, `Dict`, `Optional` already imported), `src/pubrun/capture/subprocesses.py:205-231` (`SubprocessSpy.install._drain`), `src/pubrun/capture/subprocesses.py:595-678` (`SubprocessSpy.finalize_all`), `pyproject.toml:14,106-141` (`requires-python = ">=3.8"`, `[tool.mypy]`, `[[tool.mypy.overrides]]`), `tests/test_capture.py:730-886` (`TestUnwaitedPopenHarvesting`), `CONTRIBUTING.md:33`, sibling plans `k6fs5k` and `juoqy2`, and direct `mypy` 2.3.1 run on `src/pubrun/capture/subprocesses.py` without `pyproject.toml` ignores (confirmed exactly 2 `[assignment]` errors at lines 224 and 628).
- PR-001: in both `_drain` and `finalize_all`, `rec` (`Dict[str, Any]`) remains bound from the preceding loop (`pending_exits.popleft()` at line 211; `for rec in list(cls._records):` at line 613), and no existing test enters `finalize_all` Phase 2's `pending_running` loop (lines 628-636). A missed rename of any `rec` inside lines 628-636 would pass both `mypy` and `pytest` while referencing the wrong record. Spelled out exact replacements, warned about the shadowing hazard, required zero stale `rec` verification in `V-01`, and recorded `k6fs5k` as carrier for dedicated Phase 2 `pending_running` behavioral coverage.
- PR-002: literal `remove and z5xr49` produces `(backlog items qqwebg)` (ungrammatical plural), plan cited `[tool.mypy.overrides]` instead of `[[tool.mypy.overrides]]` (`ignore_errors = true`), and `mypy` commands omitted `--no-incremental`. Fixed all three in place.
- PR-003: normalized citations to Section 11.1 `path::Symbol`, gave descriptive names to `focjwv` and `gzc672`, verified and documented `CONTRIBUTING.md:33` / `docs/` doc-sync status, clarified execution-order interplay with `k6fs5k`, and tightened Gate items 4 and 5.

### Step S5

- Checked: `## Open questions` is `None.`. Every entry in `## Deferred / out of scope (with reason)` carries an explicit `- Carrier:` (`juoqy2` and `k6fs5k`). All three review findings (`PR-001`, `PR-002`, `PR-003`) have Overall Remediation Risk `Low` and were fixed in place. No unresolved human decision remains, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | IN-SCOPE | Check Q / Check P (uncovered `finalize_all` Phase 2 shadowing hazard) | `src/pubrun/capture/subprocesses.py::SubprocessSpy.finalize_all:613-636`; `src/pubrun/capture/subprocesses.py::SubprocessSpy.install._drain:211-226`; `tests/test_capture.py::TestUnwaitedPopenHarvesting:730-886`; Plan `E-01` (line 38), `Proposed changes` item 1 (lines 64-66), `V-01` (line 99) | Neither `tests/test_capture.py` nor `tests/test_signals.py` enters the `pending_running` loop in `finalize_all` Phase 2 (lines 628-636), and `rec` (`Dict[str, Any]`) remains bound from the preceding loop in both methods; a partial rename inside lines 628-636 would pass both `mypy` and `pytest` while referencing the wrong record. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Spelled out exact replacements for all 3 lines in `_drain` and all 9 lines (8 `rec` occurrences) in `finalize_all` Phase 2, added an explicit shadowing warning, required `V-01` to verify zero stale `rec` references in either `pending_running` block, and recorded sibling plan `k6fs5k` as carrier for dedicated Phase 2 behavioral coverage (recommendation strength: strong). |
| PR-002 | MEDIUM | IN-SCOPE | Check Q / Check P (`pyproject.toml` comment grammar, TOML table syntax, uncached `mypy`) | `pyproject.toml:115-141` (`[[tool.mypy.overrides]]`, line 117 `# Remove each module as its existing errors are fixed (backlog items qqwebg and z5xr49).`); Plan `E-02` (line 43), `Project conventions` (line 54), `Proposed changes` item 2 (line 68), `Required tests / validation` (line 82), `V-02` (line 104) | `E-02`'s literal `remove and z5xr49` leaves ungrammatical `(backlog items qqwebg)`, body references wrote `[tool.mypy.overrides]` instead of `[[tool.mypy.overrides]]` (`ignore_errors = true`), and `mypy` validation omitted `--no-incremental`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified `# Remove each module as its existing errors are fixed (backlog item qqwebg).`, corrected all body references to `[[tool.mypy.overrides]]` (`ignore_errors = true`), and added `--no-incremental` to both `mypy` commands in `E-02`, `Required tests / validation`, and `V-02` (recommendation strength: strong). |
| PR-003 | LOW | IN-SCOPE | Check P / Check S7 (Section 11.1 citations, doc-sync evidence, execution contract) | Plan `Goal` (line 30), `E-01` (line 38), `Project conventions` (lines 50-56), `Findings` (line 60), `Deferred / out of scope` (line 72), `Spec / documentation sync` (line 88), `Approval and execution gate` items 4-5 (lines 119-120); `CONTRIBUTING.md:33` | Code citations omitted Section 11.1 `path::Symbol`, record IDs (`focjwv`, `gzc672`) lacked descriptive names, `Spec / documentation sync` gave `N/A` without noting `CONTRIBUTING.md:33` / `docs/` verification, and Gate items 4-5 omitted raw `git commit` ban and standalone `pre-transition` lint precondition. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Normalized citations to Section 11.1 `path::Symbol`, added descriptive names for `focjwv` and `gzc672`, documented the `CONTRIBUTING.md:33` / `docs/` check in `Spec / documentation sync`, noted `k6fs5k` execution-order interplay, and tightened Gate items 4 and 5 (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `simple` | `standard` | Internal 2-file bugfix (local variable rename/annotation in two methods of `src/pubrun/capture/subprocesses.py` plus removing one entry from `pyproject.toml` `ignore_errors`); all risk questions answered No (`Scope-Paths` declared). | yes |
| D-2 | Whether to expand `- Scope-Paths:` to add a new `finalize_all` Phase 2 `pending_running` test in `id283c` | Keep `- Scope-Paths:` limited to `src/pubrun/capture/subprocesses.py` and `pyproject.toml`, enforce strict diff verification in `V-01`, and cite `k6fs5k` as carrier for dedicated Phase 2 behavioral coverage | Add a test file to `id283c` `- Scope-Paths:` | Backlog item `z5xr49` requests only the two mypy fixes and ratchet removal; sibling reviewed plan `k6fs5k` (`E-04`) already owns `test_finalize_harvests_exit_code_of_collected_unwaited_child` in `tests/test_capture_mypy_guarded_paths.py`, avoiding duplicate test work across sibling plans. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All three findings (`PR-001`, `PR-002`, `PR-003`) were fixed in place with Low remediation risk and swept across the entire plan. `aw ipd lint --phase review-finalize --agent` will be verified before committing. No second review pass is needed.

AW-REVIEW: DONE
