# Review findings: ipd c39m4v

- Subject-Id: c39m4v
- Subject-Type: ipd
- Reviewed-At: 2026-11-24
- Reviewer: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the full text of `.aw/records/plans/pending/20261123-ewgjmx-01-c39m4v-document-benchmarks-package-capture-bench-py-in-benchmarks-r.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. No pre-review snapshot was needed: lane HEAD `93995d7` is clean and the plan is unchanged since `047a843`. `aw ipd lint --phase author --agent` reported `clean`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal | One sentence naming the two files | Says what `package_capture_bench.py` does, what the guide lacks, and why the text must match the script; records why no diagram | Requirement 1 (explain before naming) and requirement 12(c). |
| E-01, E-02 | "explaining that it is ...", "matching the style of" | Exact placement (between which bullets and headings), numbered required content, and the dash rule scoped to the new text | Requirement 6: an executor cannot check an unplaced, unlisted outcome. |
| Project conventions | Facts stated without a source; "`main` / `_parse_args`" | Each fact cites its symbol (`parse_args`, `_measure_mode`, `_add_deltas`) and the observed run | Requirement 5 and `IPD-C801`; `_parse_args` does not exist. |
| Spec / documentation sync | One sentence | States the spec search, why `docs/performance.md` is linked and not edited, and why no `CHANGELOG.md` entry | R4 spec-sync truthfulness. |
| Gate | One paragraph | Five-element execution contract | S7 execution contract. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`benchmarks/README.md`), 2 E-items in 1 task group.

1. No: documentation only; no flag, output format, or configuration key changes.
2. No: no code guarding private data, commits, worktrees, merges, or the sandbox. The new text describes the script's redaction but does not change it.
3. No: 2 E-items, one file.
4. Yes: `benchmarks/README.md`.
5. Low: a wrong sentence is undone by editing the file. The one real risk is a copied example writing output somewhere harmful (PR-001).

AW-TIER: standard

### Step R1

- Checked: every symbol and claim in the plan against `benchmarks/package_capture_bench.py` (read in full), `python3 benchmarks/package_capture_bench.py --help`, a smoke run (`--small-count 2 --large-count 4 --repetitions 1 --cold-runs 1 --json-out /tmp/opencode/pcbench-smoke.json`, exit 0, `schema_version` `pubrun-package-capture-bench/1`), `--repetitions 0` (exit 2, `error: --repetitions must be an integer >= 1`), `benchmarks/README.md`, `benchmarks/results/.gitignore`, `benchmarks/test_benchmarks.py`, and `docs/performance.md`.
- Confirmed: the six flags and defaults, `SCHEMA_VERSION`, `MODES`, `PROFILES`, the cold and warm sampling, and the absence of any `gh`, Gist, `git push`, or scheduler call.
- PR-001: Proposed changes item 2 told the executor to document `--json-out benchmarks/results/package-capture.json`. `benchmarks/results/.gitignore` ignores every file there except `*.redacted.json` (`git check-ignore -v` reports rule `*`), and `benchmarks/test_benchmarks.py::TestSchema5Conformance.test_committed_redacted_sample_conforms` validates every `benchmarks/results/*.redacted.json` against `schemas/benchmark.schema.json`. The smoke-run output failed that schema (10 errors, first `Additional properties are not allowed`). So the suggested path suggests the result belongs with the shared, aggregated `pubrun-benchmark/5` results, and a contributor who renames it `*.redacted.json` there to keep it would break that test. E-02 now requires a `/tmp` example, forbids a `benchmarks/results/` path, and requires the README to say the format is not read by `aggregate.py`.
- PR-003: Project conventions cited "`main` / `_parse_args`"; the parser is `benchmarks/package_capture_bench.py::parse_args`. It also omitted the hidden `--_child` flag, which the README must not document. Both corrected.
- PR-004: E-02 left out user-visible behavior: the exit status `2` for a value below 1, exit status `1` when a sample fails, refusal to write output when the share-safety check fails, `off` as the baseline for `delta_vs_off_ms`, and that standard output always prints a Markdown summary. E-02 now lists each.

### Step R2

- Checked: the E/V bijection (E-01/V-01, E-02/V-02), each V-item's evidence against what its E-item produces, and the reachability of V-02's `--help` demand (`benchmarks/package_capture_bench.py::parse_args`).
- PR-002: V-01 and V-02 demanded only a pasted diff plus a reviewer's visual comparison, so a subsection missing a flag, a mode, a profile, or the schema string would still pass. Required tests now add a placement `grep` and a content check that prints each missing token. The content check exited 1 on the current README (no subsection) and printed `OK` on a scratch README carrying the required content, run from the plan text verbatim.
- PR-005: the dash check had no command. Required tests 3 is now `git diff -U0 benchmarks/README.md | grep '^+[^+]' | grep -c $'[\u2013\u2014]'`, with a note that `grep -c` exits 1 on a count of 0. Its scope is the added lines: 24 existing README lines carry em dashes and are outside this plan.

### Step R3

- Checked: the plan adds prose only. The example commands write only to a user-chosen `--workdir` subdirectory (removed on exit) and a `/tmp` path. `python3 scripts/sanitize_paths.py --check --all` exited 0 at review. The new text must not suggest committing unredacted output, which PR-001 also covers. No further finding.

### Step R4

- Checked: rubric A to F (only E and F apply to a documentation change), right-sizing (two single-concern items in one file), and spec-sync truthfulness.
- PR-006: Spec / documentation sync said only "This plan is the documentation update". It now records the spec search (no spec mentions `package_capture_bench`), why `docs/performance.md` is linked rather than edited, and why no `CHANGELOG.md` entry is needed (the benchmark's own addition in `7490aeb` added none).
- PR-007: the gate lacked the execution contract elements: approval precondition, scope declaration with `--scope-reason` and `--scope-ack`, the paste-actual-output rule, `aw commit c39m4v -- benchmarks/README.md`, and the runner and executor split for `aw ipd finalize c39m4v`. Added.

### Step R7

- Checked: Set `ewgjmx` has only this plan (no orchestrator, no siblings). The Set `nqrhyn` plan `lwb332`, reviewed in the same run, edits `docs/manifest.md` and does not overlap. No finding.

### Step S5

- Checked: the plan has no open questions. Every finding has Low remediation risk and is fixed, so none needs escalation and the lane outcome carries no question.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | medium | IN-SCOPE | R1 (wrong example) | `benchmarks/results/.gitignore` `*`; `benchmarks/test_benchmarks.py::TestSchema5Conformance.test_committed_redacted_sample_conforms`; smoke output failed `schemas/benchmark.schema.json` with 10 errors | The proposed `--json-out benchmarks/results/package-capture.json` example puts a non-`/5` result beside the aggregated results. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 uses `/tmp/package-capture.json`, forbids `benchmarks/results/`, and says `aggregate.py` does not read the format. |
| PR-002 | high | UNDER-SCOPE | R2 (evidence cannot prove the change) | V-01 and V-02 asked only for a diff | Validation could not catch a missing flag, mode, profile, or schema string. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Placement grep and token content check; exit 1 on current file, `OK` on a scratch fix. |
| PR-003 | low | IN-SCOPE | R1 (wrong symbol) | `benchmarks/package_capture_bench.py::parse_args`; `--_child` with `help=argparse.SUPPRESS` | Conventions named `_parse_args` and did not exclude the hidden flag. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Conventions cite `parse_args`; content check forbids `--_child`. |
| PR-004 | medium | UNDER-SCOPE | R1 (incomplete content) | `benchmarks/package_capture_bench.py::main` returns 2, 1; `_add_deltas` | E-02 omitted exit statuses, the share-safety refusal, the `off` baseline, and standard output. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | E-02 items 3 and 4 list each. |
| PR-005 | low | IN-SCOPE | R2 (validation command) | 24 existing em-dash lines in `benchmarks/README.md` | The dash check had no command or scope. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required tests 3, added lines only. |
| PR-006 | low | IN-SCOPE | R4 (doc sync) | `.aw/records/specs/` search; `7490aeb` file list has no `CHANGELOG.md` | Spec / documentation sync did not substantiate itself. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Section states the search and the reasons. |
| PR-007 | medium | IN-SCOPE | S7 (execution contract) | Gate had one paragraph | Contract elements were missing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Five-element execution contract. |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple` | Doc-only, but the plan states user-copied commands whose output location matters (PR-001) | yes |
| D-2 | Where should the documented `--json-out` example write? | `/tmp/package-capture.json` | `benchmarks/results/package-capture.json`; `results.json` (docstring) | `benchmarks/results/.gitignore` and `TestSchema5Conformance`; `startup_breakdown.py` README example already uses `/tmp/breakdown.redacted.json` | yes |
| D-3 | Repeat the measured numbers in the README? | No; link `docs/performance.md` | Copy the tables | The README subsection for `startup_breakdown.py` carries no numbers; one source avoids drift | yes |
| D-4 | Fix the 24 existing em-dash lines in `benchmarks/README.md`? | No | Fix them here | The dash rule binds text this plan authors; editing unrelated lines widens scope | yes |
| D-5 | Add a `CHANGELOG.md` entry? | No | Add one under `### Documentation` | Dev tooling not shipped in the wheel; the script's addition in `7490aeb` added none | yes |

### Step S6

- Checked: the review did not add or remove an E-item or V-item and did not change `- Scope-Paths:` or `- Item-Dependencies:`. It rewrote E-02's expected outcome and both V-items; the rewritten commands were run verbatim from the plan text against the current README (content check exit 1) and against a scratch README with the required content (`OK`, exit 0). `aw ipd lint --phase review-finalize --agent` reported `clean`. No new question or ambiguity remains, so no second pass is needed.

AW-REVIEW: DONE
