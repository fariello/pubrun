# Review findings: ipd bzi46m

- Subject-Id: bzi46m
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-01-bzi46m-ci-pipeline-tox-excluded-suites-examples-and-coverage-gate.ipd.md` (front matter, Goal, Mermaid flowchart, E-01 to E-05, V-01 to V-05, conventions, findings, proposed changes, deferrals, scope check, required tests, documentation sync, OQ-01, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Proofreading edits kept front-matter values, the H2 heading list and order, E/V ids, checkbox states, Execution state values, item field names, and OQ-01's Status and Blocking values unchanged. Substantive rewrites are recorded under Findings, not here.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One run-on sentence listing CI gaps, with "minimal non-TUI and sdist/wheel installs" undefined | Two sentences: what CI and `tox` will cover, then why `--cov` stops being forced; "an install without the `tui` extra" and the `hatch_build.py` commit stamp are named | Requirements on defining terms at first use and one idea per sentence. |
| Goal, diagram lead-in | "Solid nodes are new or changed" (the Mermaid diagram has no styling that distinguishes nodes) | States which job is unchanged and which three are new | The sentence described something the diagram does not show (requirement 12). |
| Project conventions | "CI run `45109957606` is green on `fd636d0`" stated as fact | Attributed to the plan author and marked not re-verified at review | Separates verified from unverified claims. |
| OQ-01 | `- Owner: none` on a question the author resolved | `- Owner: plan author` | Provenance of the resolution. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (6 files at start), E-01 to E-05, `.github/workflows/ci.yml`, `pyproject.toml`, `tox.ini`, `benchmarks/test_benchmarks.py`, `examples/verify_all.py`, `hatch_build.py`, orchestrator `vdxiw8` and sibling `gzc672`.

1. No: no public library or CLI contract changes. The default output of `pytest` (and therefore of `pubrun --run-tests`, `src/pubrun/__main__.py::_run_tests`) loses its coverage table, which is a contributor-facing change recorded in the documentation sync.
2. No: CI, test configuration, tests, an example runner, and contributor documentation; no private-data guard, commit helper, worktree isolation, or sandbox code.
3. No: one coherent concern (test and CI coverage), about one file per step.
4. No at start: the `no-tui` job needs `tests/test_tui.py`, and the documentation sync needs three documentation files, none of which were listed (PR-001, PR-002).
5. No: every change is reversible, and a wrong CI change shows up as a red job rather than a defect in shipped code.

AW-TIER: standard

### Step R1

- Checked: every cited path and symbol against HEAD `78ed358`. `.github/workflows/ci.yml` has one `test` job with 21 matrix entries (`pip install -e ".[dev,tui]"`, `pytest tests/ -v`). `pyproject.toml:87` `addopts = "--cov=src --cov-report=term-missing --cov-report=xml -p no:randomly"`; no `markers` key. `tox.ini` has `isolated_build = True` and `deps = pytest>=7.0`. `benchmarks/test_benchmarks.py:50-53` `TestSchema5Shape.test_schema_is_v5` takes no `tmp_path`, does `import re`, reads `benchmarks/harness.py` with `read_text()`, and calls `re.search`. `_make` (line 42) and `TestSchema5Conformance.test_fresh_result_and_redaction_conform` (line 194) and `test_broken_result_is_rejected` (line 206) call `h.run`. `examples/` has 13 numbered scripts (`00` to `12`), each printing `[PASS]` once.
- Reproduced the plan's measurements on this lane. `pytest -o addopts="" .github/scripts/ benchmarks/test_share_safety.py benchmarks/test_pull_submissions.py benchmarks/test_benchmarks.py -q`: `90 passed, 3 skipped in 372.46s`. `pytest -p no:cov tests/test_config.py -q` with the current `addopts`: exit 4. Both committed redacted samples (`benchmarks/results/*.redacted.json`, `benchmarks/data/accepted/*.redacted.json`) validate against `schemas/benchmark.schema.json` with 0 errors.
- Coverage baseline: `pytest tests/ -p no:randomly -o addopts="" --cov=src --cov-fail-under=78` on Python 3.12.3 (`pip install -e ".[dev,tui]"`): `Total coverage: 79.53%`, `1855 passed, 2 skipped in 463.41s`. On Python 3.14.6: `79.48%`.
- PR-004: the plan's Required tests command adds `-k "not benchmark"`. The keyword matches the module name `test_benchmarks`, so at review it collected 19 of 93 tests (74 deselected).
- PR-003: V-02 asked for `grep -n "harness.py" benchmarks/test_benchmarks.py` to prove no source scan remains, but that grep also matches the four legitimate `_load(..., "benchmarks/harness.py")` imports, so the evidence could never be satisfied.
- PR-002: the documentation sync said "N/A", but `benchmarks/README.md:67-71` and the `benchmarks/test_benchmarks.py:1-14` docstring both say `-o addopts=""` is needed to clear `--cov`, and `CONTRIBUTING.md:18` gives `python -m pytest` with no coverage command. All three go stale after E-01.
- Out of scope, observation only: `README.md:60` and `docs/research-use.md:45` say the examples run from `00` to `11`, but `12_external_file_provenance.py` exists.

### Step R2

- Checked: author-phase lint (`aw ipd lint --phase author --agent`: `clean`, exit 0), the E/V bijection, each V-item's evidence against what the matching E-item produces, and whether every command can run in a single Linux lane.
- PR-001: a `.[dev]` install without the `tui` extra gave `2 failed, 1822 passed, 10 skipped` for `pytest tests/`. `tests/test_tui.py::test_tui_cli_parser_and_run` fails because `mock.patch("pubrun.tui.app.PubrunTUIApp")` (line 13) imports the real `pubrun.tui.app`, which imports `textual`. `tests/test_tui.py::test_tui_toml_serialization` (line 69) imports `pubrun.tui.widgets.config`, which imports `textual` at module level. E-05(b) would therefore add a CI job that is red on its first run. No pending plan covers these tests: `bwoyan` (Order 08) scopes `tests/test_tui_widgets.py`, and `whacr3`, which also edited `tests/test_tui.py`, is executed. A scratch version of the first test that uses only `mock.patch.dict(sys.modules, ...)` with a `mock.Mock()` application passed with and without `textual`.
- PR-009: E-05(c) builds the sdist and wheel, but the `dev` extra has no `build` package, so `python -m build` fails unless the job installs it. With `pip install build`, `python -m build` succeeded; both the wheel and the wheel rebuilt from the unpacked sdist contain `pubrun/_build_meta.json`, `pubrun/COMMIT`, and `pubrun/py.typed`; in a clean virtual environment `pubrun.__commit__` equals `78ed35871f84b2dfa93175823930a042702c574e`, and `pubrun --version` printed `pubrun 1.3.1 (commit 78ed35871f84b2dfa93175823930a042702c574e)`. PyYAML is not in the `dev` extra either, so two `.github/scripts/` YAML cross-check tests skip unless the job installs `pyyaml`.
- PR-008: E-04 excluded `11_cli_report.py` "only if it requires a pre-existing run", which leaves the executor to decide. At review, all 13 examples exited 0 when run with a temporary working directory and `PYTHONPATH=src`; `11_cli_report.py` creates its own run. Each wrote 1 or 2 manifests under `<cwd>/runs`, the 13 took about 8 seconds together, and the checkout was left clean.
- PR-011: V-05 bundled the evidence for three different CI jobs, the coverage gate, and the sanitizer; V-03 accepted "`--help`/dry-run" output, which does not show that `runs/` survives. V-01 did not check `tox`.
- `tox` is listed in the `dev` extra but is not installed in this lane; V-01 now asks for `tox` output when it is available and an explicit statement otherwise.

### Step R3

- Checked: `examples/verify_all.py` deletes `<repo_root>/runs` before running and calls `rmdir /s /q` through `shell=True` on Windows; it sets no subprocess timeout. E-03 already removed all three; the revision makes the outcome concrete (one `tempfile.TemporaryDirectory()`, `cwd=` per example, `timeout=120`, `TimeoutExpired` reported per example). The new CI jobs use only `actions/checkout` and `actions/setup-python` with no secrets and no `pull_request_target`; the existing workflow declares no `permissions:` block, and the new jobs add none, so nothing widens. The smoke test isolates `XDG_CONFIG_HOME` and `APPDATA` (read by `src/pubrun/_config_boot.py:49-52`) so a developer's user configuration cannot leak into a test result. `python3 scripts/sanitize_paths.py --check --all` is in the required validation. No security finding.

### Step R4

- Checked: rubric sections on testability, anti-regression, right-sizing, and the AGENTS.md "no code-pinning tests" rule.
- PR-005: "add `--cov-fail-under=78`" did not say which job enforces the floor or how it interacts with the suites outside `tests/`. Revised: the `ubuntu-latest` Python 3.12 entry of the `test` matrix runs `pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=78`; the `extra-suites` job runs without coverage; OQ-01 records the re-measured baseline.
- PR-006: the diagram showed a "Linux CI job: examples smoke test" that no E-item created, while `tests/test_examples_smoke.py` would actually run in all 21 matrix entries. The diagram now shows the real jobs, and E-04 says the smoke test runs in every matrix entry (about 8 seconds).
- PR-007: E-01 registered a `slow` marker that nothing used. E-02(c) now applies it to every test that calls `harness.run` (40 to 58 seconds each at review), and a deferral records why no CI job deselects it.
- PR-010: the gate said to "move this plan to `.aw/records/plans/executed/`" by hand and lacked the scope declaration, the validation-honesty rule, and the runner/executor split for finalization. It now carries the five-element execution contract (modelled on `46fixy`), with `aw ipd finalize bzi46m`, `--scope-reason`/`--scope-ack`, and no stop directive for scope questions.
- PR-011: E-05 bundled three CI jobs and the coverage gate in one item. Split into E-05 (coverage floor and `extra-suites`), E-08 (`no-tui`), and E-09 (`packaging`), each with its own V-item. The plan now has 9 E-items and 10 Scope-Paths, above the `IPD-Z603` advisory guidance (5 and 8); the gate's cohesion rationale explains why it stays one plan, and splitting is offered to the maintainer as a non-blocking question.
- Matrix validation: `AGENTS.md` requires the full CI matrix for cross-platform work. That run needs a push, which needs explicit human authorization, so it is recorded as a `Carrier-Declined` deferral rather than a V-item no executor can satisfy.

### Step S5

- Checked: OQ-01 (resolved, non-blocking; the floor of 78% sits below both re-measured baselines), the three deferrals (`Carrier: gzc672` exists as Order 02 of Set `test-audit`; two `Carrier-Declined`), and every finding. Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so nothing is escalated as a blocking open question.
- One non-blocking choice is the maintainer's: keep this as one plan or split it to meet the `IPD-Z603` guidance. It is recorded in the lane outcome `questions[]` with `gates_verdict: false`; the recommended answer is to keep one plan.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | UNDER-SCOPE | R2 (executability) | `tests/test_tui.py:13` `mock.patch("pubrun.tui.app.PubrunTUIApp")`; `tests/test_tui.py:69` `test_tui_toml_serialization`; `.[dev]` run: `2 failed, 1822 passed, 10 skipped` | The planned non-TUI CI job would fail on its first run because two tests import `textual`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added E-07/V-07 (make both tests pass or skip without `textual`), added `tests/test_tui.py` to Scope-Paths, and made E-08 depend on E-07. |
| PR-002 | medium | UNDER-SCOPE | Documentation sync | `benchmarks/README.md:67-71`; `benchmarks/test_benchmarks.py:1-14`; `CONTRIBUTING.md:18` | Documentation sync said "N/A", but three documents describe the `--cov` behavior E-01 removes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added E-06/V-06 and E-02(d); added `benchmarks/README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` to Scope-Paths; rewrote the documentation sync section. |
| PR-003 | medium | IN-SCOPE | R2 (unsatisfiable evidence) | Plan V-02; `benchmarks/test_benchmarks.py` `_load(..., "benchmarks/harness.py")` (4 matches) | `grep -n "harness.py"` always matches the legitimate imports, so V-02 could never pass honestly. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-02 now greps for `read_text\(\)` and `re\.search` and asks for the behavioral `test_schema_is_v5` result; E-02(a) defines that assertion. |
| PR-004 | medium | IN-SCOPE | R1 (wrong command) | Plan Required tests `-k "not benchmark"`; review run: 19 of 93 collected | The filter deselects almost every benchmark contract test. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Removed the filter and stated why; the `bench` tests already skip without the extra. |
| PR-005 | medium | IN-SCOPE | R4 (ambiguous gate) | Plan E-05 and OQ-01; review coverage runs `79.53%` (3.12.3) and `79.48%` (3.14.6) | The plan did not say which job enforces `--cov-fail-under=78` or on which suites. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05 puts the floor on the `ubuntu-latest` Python 3.12 matrix entry over `tests/` only; OQ-01 records the re-measured baseline. |
| PR-006 | medium | IN-SCOPE | Requirement 12 (diagram) | Plan diagram node `EX["Linux CI job: examples smoke test"]`; E-04 and E-05 | The diagram showed a job no E-item creates. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Diagram redrawn with the real jobs; E-04 states the smoke test runs in every matrix entry. |
| PR-007 | low | IN-SCOPE | R4 (dead configuration) | Plan E-01 `slow` marker; `benchmarks/test_benchmarks.py:46,194,206` `h.run` | The `slow` marker was registered but applied to nothing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02(c) marks every `harness.run` test; a deferral records that no CI job needs to deselect them. |
| PR-008 | low | IN-SCOPE | R2 (executor decision left open) | Plan E-04 "excluding `11_cli_report.py` only if"; review run of all 13 examples, exit 0 | E-04 left the executor to decide whether to exclude one example. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04 includes all 13 examples, with the measured result. |
| PR-009 | medium | IN-SCOPE | R2 (missing prerequisite) | `pyproject.toml` `dev` extra (no `build`, no `pyyaml`); review `python -m build` run | The packaging job could not run `python -m build`, and two YAML tests would silently skip. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-09 installs `build`; E-05 installs `pyyaml` in `extra-suites`, and V-05 checks that no YAML skip appears. |
| PR-010 | medium | IN-SCOPE | S7 (execution contract) | Plan `## Approval and execution gate` "move this plan to `.aw/records/plans/executed/`" | The gate told the executor to move the plan by hand and lacked three contract elements. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Replaced with the five-element contract and `aw ipd finalize bzi46m` with runner/executor ownership. |
| PR-011 | low | IN-SCOPE | R4 (right-sizing) and R2 (weak evidence) | Plan E-05 (three jobs plus gate), V-03 ("or `--help`/dry-run"), V-05 | One item covered four deliverables; V-03 accepted output that cannot show `runs/` survives. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Split into E-05, E-08, E-09 with V-05, V-08, V-09; V-03 now uses a marker file in `runs/`; cohesion rationale added to the gate. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Scope-Paths was incomplete (tier answer 4), so `simple` does not apply; no public contract or safety-critical code changes | yes |
| D-2 | Where does the coverage floor run? | `ubuntu-latest` Python 3.12 entry of the `test` matrix | A separate coverage job; every matrix entry | One entry avoids a second full suite run (about 8 minutes) and avoids per-platform variance; it matches the existing Python 3.12 choice in `benchmark-intake.yml` | yes |
| D-3 | How are the two `tests/test_tui.py` failures fixed? | In this plan (E-07) | A separate backlog item; leave the `no-tui` job out | The `no-tui` job is red without the fix, and no other pending plan owns the file | yes |
| D-4 | Does the example smoke test run in every matrix entry? | Yes, unmarked | Mark it `slow` and run it in one Linux job | The 13 examples take about 8 seconds, and per-platform coverage of the examples is the point | yes |
| D-5 | How is the full-matrix check recorded? | `Carrier-Declined` deferral | A V-item requiring a CI run | A push needs explicit human authorization, so no executor can satisfy such a V-item; GitHub Actions runs it on the next push | yes |
| D-6 | Keep one plan at 9 E-items and 10 Scope-Paths? | Keep one plan; ask the maintainer (non-blocking) | Split into configuration, tests, and CI plans | Four items edit `.github/workflows/ci.yml`, and sibling `gzc672` depends on this plan as one unit | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. They added E-06 to E-09 and V-06 to V-09 (via `aw ipd sync --apply`, `Highest E allocated: 09`) and added four files to `- Scope-Paths:`. `- Item-Dependencies:` is unchanged. A re-review pass is required.

AW-REVIEW: AGAIN

## Round 2

### Step R1

- Checked: re-read the revised plan in full. Every new citation resolves at HEAD `78ed358`: `tests/test_tui.py::test_tui_cli_parser_and_run` (line 7), `::test_tui_cli_parser_and_run_leaves_real_tui_module` (line 29), `::test_tui_toml_serialization` (line 69); `benchmarks/README.md:67-71`; `CONTRIBUTING.md:18`; `CHANGELOG.md` `## [Unreleased]` (line 9); `src/pubrun/__main__.py::_run_tests` (line 2625, runs `pytest tests/ -q`); `docs/cli.md` `--run-tests` and `docs/functional_spec.md` 11.4, neither of which mentions coverage. `.coverage`, `coverage.xml`, `dist/`, and `runs/` are gitignored (`.gitignore:10,32,61,62`).

### Step R2

- Checked: `aw ipd lint --phase review-finalize --agent`: `clean`, exit 0, 0 errors, 0 warnings, 2 `IPD-Z603` advisories (9 E-items, 10 Scope-Paths), which the gate's cohesion rationale addresses. E-01 to E-09 map 1:1 to V-01 to V-09; no `TODO` or `E-NEW` remains. Dependencies are acyclic: E-06 needs E-01 and E-05; E-02 needs E-01; E-04 needs E-03; E-05 needs E-01 and E-02; E-08 needs E-07 and E-04. Each V-item names commands that run in a single Linux lane, and V-05 includes the sanitizer. Scope-Paths matches the Scope line, the Scope check, the gate's scope declaration, and the files the E-items edit.

### Step R4

- Checked: each new E-item is one step on one or a few files; E-07 changes test plumbing only and keeps every existing assertion (`assert_called_once` twice), so the CLI launch path stays covered. No new test reads production source. The `slow` marker selects exactly the `harness.run` tests, and V-02 checks that.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|

### Step S6

- Checked: Round 2 made no edits, so the E/V id set, `- Scope-Paths:`, and `- Item-Dependencies:` are unchanged since the start of this pass. No new finding. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
