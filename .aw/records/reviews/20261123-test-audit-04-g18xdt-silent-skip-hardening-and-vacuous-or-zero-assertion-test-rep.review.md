# Review findings: ipd g18xdt

- Subject-Id: g18xdt
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261123-test-audit-04-g18xdt-silent-skip-hardening-and-vacuous-or-zero-assertion-test-rep.ipd.md` (front matter, Goal, E-01 to E-05, V-01 to V-05, conventions, findings, proposed changes, deferrals, scope check, required tests, documentation sync, open questions, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. Proofreading kept front-matter values, the H2 heading list and order, E/V ids, checkbox states, Execution state values, and item field names. Substantive rewrites of E-items, V-items, and the gate are recorded under Findings, not here.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence listing "zero-assertion, vacuous, tautological, and bug-masking-skip tests" with no definitions | Defines each of the four kinds in plain terms and names the two leaked states | Define terms at first use; one idea per sentence. |
| Goal | No diagram | One sentence stating the five E-items are independent | Requirement 12: five independent edits have no flow worth a diagram, so the text states the structure instead. |
| Project conventions | Two bullets | Adds the existing real-repository test to copy, the module-level `jsonschema` skip and why it stays, and the `AGENTS.md` matrix-validation rule | The executor needs these facts to make the E-items pass on every CI platform. |
| Citations | Bare line offsets (`writer.py:263`, `reproducibility.py:1276`, `pyproject.toml:58`, `resources.py:573`) | Symbol or quoted-content anchors | `IPD-C801` advisories; a bare line number goes stale before execution. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (8 test files), E-01 to E-05, and the production code each test exercises (`src/pubrun/capture/git.py`, `src/pubrun/capture/environment.py`, `src/pubrun/writer.py`, `src/pubrun/core.py`, `src/pubrun/tracker.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/resources.py`, `schemas/manifest.schema.json`).

1. No: tests only; the schema file and every public interface are read, not changed.
2. No: no private-data guard, commit, worktree, merge, or sandbox code.
3. No: 5 independent E-items in 3 task groups, each editing one or two test files.
4. Yes: 8 test files, matching the E-items exactly.
5. Low: test-only and reversible. A wrong edit could turn a passing test red or weaken one, which the mutation checks in the V-items detect.

AW-TIER: standard

### Step R1

- Checked: every cited path and symbol against lane HEAD `a2658e3`. `tests/test_capture_engines.py:225-242` (`TestGit`, three `if result["capture_state"]["status"] == "complete":` blocks) and `:50-69` (`TestEnvironment`, two `if "TEST_API_TOKEN" in by_name:` blocks). `tests/test_tracker.py:100` (`manifest.json.tmp`) and `:124` (`target.with_suffix(".json.tmp")`); `src/pubrun/writer.py:_atomic_json_write` names its temporary file `path.with_suffix(f".json.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")`. `tests/test_api.py:500` `TestHandleInactivePolicy.test_ignore_policy_is_silent` has no assertion. `tests/test_quality.py:75-90` stops twice and asserts nothing after the second stop; `:503-514` assigns `sys.stdout` with no guard. `tests/test_capture.py:59-71` loops over `unwatched` with no length check. `tests/test_new_features.py:392-416` patches `_get_tree_rss_linux` and sleeps 0.3 s; `:466-499` calls `pubrun.stop()` once after five `start()` calls. `tests/test_manifest_schema.py:191-199` catches `PermissionError, json.JSONDecodeError, FileNotFoundError` and then skips; the docstring at `:11-13` still describes an xfail that `test_full_manifest_conforms_to_schema` says was removed. `tests/test_methods_multi.py:57` `importorskip` on a module the file imports at line 14.
- Before any edit, the 8 files gave `246 passed in 14.95s`, so every defect is a test that passes without checking anything.
- PR-007: E-05(c) asked for "live end-to-end schema validation for populated `meta_ref`, `determinism`, and `artifacts`". `grep` over `src/` found no code that writes a `determinism` or `artifacts` manifest section. `src/pubrun/report/reproducibility.py` only reads `determinism`, and `pubrun.artifact()` (`src/pubrun/core.py:artifact`) writes a file and an annotation event, not a manifest entry. A live run with `meta_ref="/x/meta.json"` and an `artifact()` call produced `meta_ref` set, no `determinism` key, and no `artifacts` key. As written, that part of E-05 could not be executed.
- PR-009: `test_ignore_policy_is_silent` belongs to `TestHandleInactivePolicy`. The `importorskip` in `tests/test_methods_multi.py` could never fire, because the module-level import would already have failed collection; it is dead code, not a skip that hides failures.
- PR-004: E-04 asked for "deadline polling" in the tree-scope test. `ResourceWatcher.stop()` already takes a final measurement (`end_tree_rss = self._poll_tree_rss()`), so no wait is needed. `ResourceWatcher._poll_tree_rss` is the one entry point on every platform and returns 0 on Windows, so the existing `_get_tree_rss_linux` patch did nothing off Linux.

### Step R2

- Checked: author-phase lint (`aw ipd lint --phase author --agent`: `clean`, 0 findings), the E/V bijection, each V-item against what its E-item produces, and each E-item by prototype. Every E-item was applied in a scratch clone of the lane at `a2658e3` (not in the lane), and each strengthened test was checked against a temporary one-line break of the production code it guards.
- Prototype results: the 8 files gave `248 passed` with lane `python3` (pytest 8.2.2), in random order (`-p randomly --randomly-seed=12345`), with seed 999, and under a Python 3.12 virtual environment (pytest 9.2.0). The full suite in random order, `python3 -m pytest tests/ benchmarks/test_pull_submissions.py -q -p randomly --randomly-seed=12345`, gave `1904 passed, 2 skipped in 442.72s`, against `1902 passed, 2 skipped` before the change. The difference is the two new schema tests. `python3 scripts/sanitize_paths.py --check --all` exited 0.
- PR-002: E-03(a) as written (`data2 == data1`, `elapsed_seconds == elapsed1`) cannot detect a second write. With both `_artifacts_written` guards in `ArtifactWriter.write_artifacts` removed, the second stop rewrote the manifest with identical content, so the test passed. With `if self._finalized: return` removed from `_finalize_state` as well, it still passed. A probe showed only the mtime changing (`SAME True MTIME False`). Adding the mtime assertion made the guard-removal mutation fail. Calling the second stop with `outcome="failed"` and asserting the outcome stays `completed` also catches an overwrite of the sticky outcome. The revised test passed 20 of 20 runs.
- PR-001: E-01 said "creates a real temporary git repository" without saying how. A CI runner may have no git identity, and a developer machine may sign commits. The prototype fixture passes `-c user.email=... -c user.name=... -c commit.gpgsign=false` to each command. It also checks `dirty` in both states, so the test fails if dirty detection always returns `False`.
- PR-003: E-02(b) said `caplog.records == []` without a capture level. The prototype captures at `DEBUG` on the `pubrun` logger and also checks `capsys`. It failed when `_handle_inactive` logged under every policy (`elif action == "warn":` changed to `else:`). The original test passed under that change. Changing the policy fallback string had no effect, because the resolved configuration always supplies `ignore`.
- PR-005: E-04(a) said "a child that stays alive until `stop()`" without a mechanism. A child that blocks on `sys.stdin.read()` stays alive for as long as the test holds the pipe open, and `finally: p.stdin.close(); p.wait(timeout=10)` reaps it. The revised test failed when `SubprocessSpy.finalize_all` stopped marking records `complete`. The original test also failed under that mutation, but only by timing (the 0.1 s child was usually still alive); the revised test does not depend on timing.
- PR-006: E-04(c) said "stop all 5 ref-counts cleanly". A probe of the current test showed the run still active with `ref_count == 4` after its single `pubrun.stop()`. The revised test asserts `ref_count == 5`, calls `stop()` once per reference in `finally:`, and asserts the run is inactive and unpublished. It passed 10 of 10 runs.
- PR-004 (continued): the revised tree-scope test passed 15 of 15 runs with no sleep, and failed when `to_manifest_dict` wrote `None` for `peak_tree_rss_bytes`. The original test passed under that mutation.
- PR-008: E-05(a) said "tolerate retry only on `PermissionError` on `win32`" but gave no mechanics, and the module did not import `sys`. Commit `28ad814` added the retry after a `PermissionError` on the `windows-3.14` CI job. `start()` writes the manifest through `_atomic_json_write` (`os.replace`), so a reader never sees a partial file, and the decode and missing-file cases are real failures. The plan now says which exception is retried, on which platform, how many times, and that the last failure is re-raised. It also records the `AGENTS.md` matrix-validation rule and a deferral for the push-gated CI run.
- PR-007 (continued): the revised E-05(d) validates a real manifest with injected `determinism` and `artifacts` sections, plus two rejected malformed entries. The first prototype used an ISO string for `modified_at_utc` and failed, because the schema's `utc_datetime` is an epoch number; the plan states the type. Both new schema tests failed when the schema was temporarily changed to make `meta_ref` null-only and seed values string-only.
- PR-010: the V-items asked only for "passing" output and a diff. A passing run cannot show that a test would catch a regression, and every original test here already passed. Each V-item now names a one-line production mutation that the strengthened test must fail on, with a restore step. V-01 and V-05 add `grep` checks for the removed conditional and skip patterns.

### Step R3

- Checked: the new fixture runs `git` with fixed arguments in `tmp_path`; the new subprocess runs `sys.executable` with a fixed `-c` string. No network, shell, or untrusted input. The mutation checks edit production files only temporarily, and the gate forbids committing any `src/pubrun/` or `schemas/` change. No security finding.

### Step R4

- Checked: the `AGENTS.md` "no code-pinning tests" rule (no revised test reads production source), right-sizing (each E-item edits one or two files), sibling scopes (`7y0gmc`, `ic6z4s`, `2mwjjw`, `bzi46m`, `gzc672`, `m66tfv`, `bwoyan`: no `- Scope-Paths:` overlap; `2mwjjw` only runs `tests/test_capture.py`), and the three `Carrier:` deferrals, each naming a pending sibling that owns the file.
- PR-011: the gate told the executor to "move this plan to `.aw/records/plans/executed/`" by hand and lacked the scope declaration, the validation-honesty rule, and the runner and executor split for finalization. It now has the five-element execution contract with `aw commit g18xdt` and `aw ipd finalize g18xdt`.

### Step S5

- Checked: open questions (none), deferrals (three `Carrier:` siblings that exist in `pending/`; two `Carrier-Declined` entries added at review, for the push-gated CI matrix run and for whether `pubrun` should write `determinism` and `artifacts`). Every finding has Low remediation risk and is fixed. No finding is OPEN or DEFERRED, so the lane outcome carries no question.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | medium | IN-SCOPE | R2 (unspecified technique) | `tests/test_capture_engines.py:225-242`; CI runners may lack a git identity | E-01 did not say how to build the repository, and one-sided `dirty` checks would miss a constant result. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-01(a) specifies the fixture, the `-c` identity and signing flags, and a clean-then-dirty check. |
| PR-002 | high | IN-SCOPE | R2 (assertion cannot fail) | Mutation: writer guards removed, content-only test passed; mtime assertion failed | E-03(a) as written could not detect a second manifest write. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-03(a) adds the mtime assertion and a `"failed"` second stop; V-03 runs the mutation. |
| PR-003 | low | IN-SCOPE | R2 (weak assertion) | Mutation in `_handle_inactive` fails the revised test, passes the original | E-02(b) gave no capture level and ignored printed output. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02(b) captures at `DEBUG` and checks `capsys`; V-02 runs the mutation. |
| PR-004 | medium | IN-SCOPE | R1 (wrong mechanism) | `ResourceWatcher.stop` final measurement; `_poll_tree_rss` returns 0 on Windows | E-04(b) asked for an unnecessary polling wait and left the patch target open. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04(b) patches `ResourceWatcher._poll_tree_rss`, deletes the sleep, and asserts both tree fields. |
| PR-005 | medium | IN-SCOPE | R2 (unspecified technique) | `tests/test_capture.py:62` 0.1 s child; timing-dependent | E-04(a) did not say how to keep the child alive or reap it. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04(a) uses a stdin-blocking child with `finally:` reaping and asserts exactly one finalized record. |
| PR-006 | medium | IN-SCOPE | R2 (leak left unspecified) | Probe: `ref_count == 4`, run still active after the test | E-04(c) did not say how the references are released or checked. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-04(c) asserts `ref_count == 5`, releases each in `finally:`, and asserts the run ended. |
| PR-007 | high | IN-SCOPE | R1 (unexecutable item) | No `src/` code writes `determinism` or `artifacts`; live probe | E-05(c) required live validation of sections that no run produces. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05(c) is a live `meta_ref` test; E-05(d) injects both sections into a real manifest with negative cases; a `Carrier-Declined` deferral records the feature question. |
| PR-008 | medium | IN-SCOPE | R2 (unspecified, platform-specific) | Commit `28ad814`; `_atomic_json_write` uses `os.replace` | E-05(a) lacked retry mechanics, the `sys` import, and a basis; no matrix-validation note. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-05(a) states the exception, platform, attempts, and re-raise; conventions and a deferral cover the CI matrix. |
| PR-009 | low | IN-SCOPE | R1 (citation) | `tests/test_api.py:459`; `tests/test_methods_multi.py:14` | Class name missing; the `importorskip` was described as masking regressions but could never fire. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 names `TestHandleInactivePolicy`; E-05(e) explains the dead skip. |
| PR-010 | medium | IN-SCOPE | R2 (evidence cannot prove the change) | All 8 files passed before any edit (`246 passed`) | V-items asked only for passing output, which the unrepaired tests already produce. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | V-02 to V-05 each require a named mutation that fails the test, with a restore step; V-01 and V-05 add `grep` checks. |
| PR-011 | medium | IN-SCOPE | S7 (execution contract) | Plan `## Approval and execution gate` "move this plan to `.aw/records/plans/executed/`" | The gate told the executor to move the plan by hand and lacked three contract elements. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Replaced with the five-element contract and `aw ipd finalize g18xdt`. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Five E-items across eight files, with platform-specific behavior; no public contract or safety-critical code | yes |
| D-2 | How to test `determinism` and `artifacts` without production changes | Inject both sections into a real manifest and validate, plus negative cases | Make `pubrun` write them; drop the item | The plan is test-only; the schema contract is what readers rely on | yes |
| D-3 | Keep the Windows `PermissionError` retry? | Yes, Windows only, re-raise on the last attempt | Remove all retries | Commit `28ad814` records a real Windows CI failure; decode and missing-file errors cannot be a lock | yes |
| D-4 | Strengthen the double-stop test with content only, or with mtime as well? | Content, outcome, and mtime | Content only | Measured: content-only survived the guard-removal mutation | yes |

### Step S6

- Checked: whether Round 1 edits changed the E/V id set, `- Scope-Paths:`, or `- Item-Dependencies:`. The E/V id set is unchanged (E-01 to E-05, V-01 to V-05, `Highest E allocated: 05`), `- Scope-Paths:` is unchanged (8 files), and `- Item-Dependencies:` is unchanged (`none`). No re-review pass is required. `aw ipd lint --phase review-finalize --agent`: `clean`, 0 findings, after the four bare line citations were anchored. Finalized with `- Status: reviewed`, `- Readiness: go-pending-approval`, `- Review-Depth: standard`.

AW-REVIEW: DONE
