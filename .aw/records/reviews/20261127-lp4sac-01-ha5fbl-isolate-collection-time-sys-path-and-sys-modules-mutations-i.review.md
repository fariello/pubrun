# Review findings: ipd ha5fbl

- Subject-Id: ha5fbl
- Subject-Type: ipd
- Reviewed-At: 2026-11-28
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-lp4sac-01-ha5fbl-isolate-collection-time-sys-path-and-sys-modules-mutations-i.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 through 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Verified every cited path, symbol, test class, method count, and script import behavior against `tests/test_benchmark_intake_bugs.py`, `benchmarks/aggregate.py`, `benchmarks/pull_submissions.py`, `benchmarks/share_safety.py`, `.github/scripts/extract_attachment_url.py`, `.github/scripts/validate_benchmark_submission.py`, `tests/conftest.py`, `pyproject.toml`, `.github/workflows/ci.yml`, and sibling test files (`benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`). Verified the Mermaid flowchart under `### Scoped script-loader lifecycle` matches `E-01` step-for-step.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-03` heading, `## Required tests / validation` item 3, `V-03` Required evidence | `E-03` Expected outcome and `## Proposed changes` item 3 required a post-session teardown leak check, but `## Required tests / validation` and `V-03` omitted any post-session teardown command | Added a fresh-interpreter `pytest.main` post-session teardown leak check command (`post-teardown-clean`) as item 3 in `## Required tests / validation` (renumbering Python 3.8 syntax check to item 4), updated `E-03` title, and added it to `V-03` Required evidence | Align validation commands and `V-03` evidence with `E-03` Expected outcome and `## Proposed changes` item 3 (`PR-001`, technical writing standard Req 6) |
| `## Project conventions discovered (Step 0)` bullet 7 | Stated promoting `ps` to module scope "avoids repeating the four-script load nine times" | Stated it "avoids repeating the four-script load across all nine test methods (12 parametrized test invocations)" | Match exact test count (`TestPullIsolation` 2 methods + `TestPullRetag` 7 methods = 9 methods, 12 parametrized invocations; `PR-002`, technical writing standard Req 5) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: lp4sac`, `- Order: 1`, `- Scope-Paths: tests/test_benchmark_intake_bugs.py`, 3 E-items in 2 task groups, no `.spec.md` file.

1. No: the plan modifies only one internal test file (`tests/test_benchmark_intake_bugs.py`) and changes no spec, public interface, CLI flag, output format, file format, configuration key, or shared contract.
2. No: `tests/test_benchmark_intake_bugs.py` does not guard private data, commits, worktree isolation, merges to main, or the sandbox, and all existing redaction and share-safety regression assertions remain unchanged.
3. No: the plan has 3 focused E-items in 2 task groups confined to a single test file.
4. Yes: `- Scope-Paths:` explicitly lists `tests/test_benchmark_intake_bugs.py`.
5. No: a mistake affects only this test module, cannot lose data or break production behavior, and is trivially reversible.

AW-TIER: simple

### Step Q

- Checked: `tests/test_benchmark_intake_bugs.py` (all 12 test classes and 73 parametrized test cases), `benchmarks/aggregate.py`, `benchmarks/pull_submissions.py`, `benchmarks/share_safety.py`, `.github/scripts/extract_attachment_url.py`, `.github/scripts/validate_benchmark_submission.py`, `tests/conftest.py`, `pyproject.toml`, `.github/workflows/ci.yml`, and sibling `TEST-I5` isolation implementations (`benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`). Confirmed live leak behavior before the fix via `pytest.main(['-p', 'randomly', '-q', 'tests/test_benchmark_intake_bugs.py'])`, which currently leaves both `benchmarks/` and `.github/scripts/` in `sys.path` and all five modules (`aggregate`, `extract_attachment_url`, `validate_benchmark_submission`, `pull_submissions`, `share_safety`) in `sys.modules`.
- Verified:
  - Nothing outside `tests/test_benchmark_intake_bugs.py` imports symbols from it or relies on its leaked `sys.path`/`sys.modules` entries; sibling benchmark/intake test suites already isolate their own script loads.
  - None of the four loaded scripts perform lazy imports from `benchmarks/` or `.github/scripts/` after `exec_module`.
  - Making `agg`, `x`, `v`, and `ps` all module-scoped ensures `pytest` tears them down in strict LIFO order, restoring snapshots cleanly under any `pytest -p randomly` permutation.
  - Promoting `ps` from function scope to module scope is safe because `TestPullIsolation` and `TestPullRetag` mutate `ps` only via `monkeypatch` and reassign `PullErrorHolder.cls` at the start of every test method.
  - `TestShareSafetyCheckoutShimParity` snapshots `sys.modules.get("share_safety")` before loading its temporary shim and remains order-independent.
  - `E-03` Expected outcome and `## Proposed changes` item 3 required a post-session teardown leak check that was missing from `## Required tests / validation` and `V-03` (`PR-001`, fixed in place).

### Step S5

- Checked: `## Open questions` contains `None.`. Both findings (`PR-001`, `PR-002`) had `Low` overall Remediation Risk, were settled directly by repository evidence, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | UNDER-SCOPE | `q-quick-risk.md` / `s7-finalize.md` (Validation & evidence completeness) | `.aw/records/plans/pending/20261127-lp4sac-01-ha5fbl-isolate-collection-time-sys-path-and-sys-modules-mutations-i.ipd.md:91,117,131-145,170` | `E-03` Expected outcome and `## Proposed changes` item 3 required a post-session teardown leak check proving no script paths or modules remain after pytest teardown, but `## Required tests / validation` and `V-03` omitted any post-session teardown command (`E-02` only tests `_load_scoped` directly in a `with` block, not `pytest` fixture teardown). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added a fresh-interpreter `pytest.main` post-session teardown leak check command printing `post-teardown-clean` as item 3 in `## Required tests / validation`, updated `E-03` title, and added the command and required output to `V-03` (recommendation strength: `very strong`). |
| PR-002 | LOW | IN-SCOPE | `p-proofread.md` / `technical-writing.md` Req 5 | `.aw/records/plans/pending/20261127-lp4sac-01-ha5fbl-isolate-collection-time-sys-path-and-sys-modules-mutations-i.ipd.md:102` vs `tests/test_benchmark_intake_bugs.py::TestPullIsolation,TestPullRetag:556-699` | `## Project conventions discovered (Step 0)` bullet 7 stated promoting `ps` to module scope "avoids repeating the four-script load nine times", whereas `TestPullIsolation` (2 methods) and `TestPullRetag` (7 methods, two parametrized) invoke `ps` across 9 test methods and 12 parametrized test invocations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated bullet 7 to state "across all nine test methods (12 parametrized test invocations)" (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `ha5fbl` | `simple` | `standard`, `complex` | Single test file (`tests/test_benchmark_intake_bugs.py`), 3 E-items in 2 task groups, no spec/public interface/security-guard changes, easily reversible (`steps/t-tier.md`). | yes |
| D-2 | How to verify post-session teardown cleanliness in `## Required tests / validation` and `V-03` without false failures on `pyproject.toml` `pythonpath = ["src"]` | Run `pytest.main(['-p', 'randomly', '-q', 'tests/test_benchmark_intake_bugs.py'])` in a fresh interpreter and assert `rc == 0`, absence of `benchmarks/` and `.github/scripts/` in `sys.path`, and absence of all five script names in `sys.modules` | Assert strict `sys.path == before_path` across `pytest.main` | `pyproject.toml` configures `pythonpath = ["src"]`, which pytest adds to `sys.path` itself; checking the two script directories and five script modules directly tests the exact `TEST-I5` teardown invariant (`pyproject.toml:100`, verified live via `pytest.main`). | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; both revisions (`PR-001`, `PR-002`) were swept across `E-03`, `## Project conventions discovered`, `## Proposed changes`, `## Required tests / validation`, and `V-03` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
