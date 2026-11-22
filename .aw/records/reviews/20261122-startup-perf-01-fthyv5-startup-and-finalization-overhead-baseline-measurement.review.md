# Review findings: ipd fthyv5

- Subject-Id: fthyv5
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Antigravity / Gemini
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text, front matter, Mermaid diagram, E-01 through E-05, V-01 through V-05, Project conventions, Proposed changes, Open questions, and Approval and execution gate of `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Goal, E-05, Deferred, Scope check, Spec sync | Bare IDs (`4il383`, `tkmm5p`, `ckc3vl`, `t1xqpw`, `timing-acc`) | Attached concise descriptive labels to each referenced plan, backlog item, and sibling Set | Technical writing requirement 1 and reference check rule (name what referenced artifacts define or own). |
| Baseline measurement workflow diagram | Short workload listed phase/counters only; long workload listed ms/% only; omitted nested-repo installed case | Aligned nodes B, E, F, G, H with normative text (ephemeral subdir, nested-repo import, both phase/counters and ms/% for short and long workloads, share-safety gate) | Technical writing requirement 12(d) and 12(e) (diagram must agree with normative text). |
| E-01, E-05 Expected outcomes | Dense 74-word to 118-word run-on sentences; unexpanded `p95` | Split into short complete sentences; expanded `95th percentile (p95)` on first use | Technical writing requirements 1 and 2 (familiar words, expanded acronyms, short complete sentences). |
| Project conventions, Proposed changes | Informal `file.py` + `func()` references | Standardized code anchors to `path::Symbol` format (for example `benchmarks/harness.py::redact_result`, `src/pubrun/capture/filesystem.py::get_filesystem`) | `steps/p-proofread.md` Section 11.1 code citation format. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md` front matter, Scope-Paths, E-items, and cross-plan interfaces with `4il383`, `tkmm5p`, `ckc3vl`, `benchmarks/scenarios.py`, and `benchmarks/harness.py`.

1. Yes: creates `benchmarks/startup_breakdown.py` (CLI and output contract consumed by child plan `ckc3vl`) and adds scenario `startup-auto-default` to `benchmarks/scenarios.py` (part of the `pubrun-benchmark/5` harness/aggregation/submission contract).
2. Yes: guards private data at the redaction/share-safety boundary (`benchmarks/startup_breakdown.py` emits share-safe JSON and Markdown summaries pasted into tracked plan evidence `V-05` and optional `--out` files).
3. No: 5 E-items across 2 task groups and 4 related Scope-Paths (`benchmarks/startup_breakdown.py`, `benchmarks/scenarios.py`, `benchmarks/README.md`, `tests/test_startup_benchmark.py`).
4. Yes: `- Scope-Paths:` explicitly lists all 4 files modified or created.
5. Yes: a redaction defect would leak local paths or hostnames into git history (`V-05`), a `--workdir` cleanup bug could delete pre-existing user files, and distorted baseline instrumentation would invalidate targets for `4il383`, `tkmm5p`, and `ckc3vl`.

AW-TIER: standard

### Step R1

- Checked: Every cited file and symbol against the repository: `benchmarks/harness.py` (`redact_result`, `_REDACT_KEYS`, `_build_child_command`, `_stats`), `benchmarks/scenarios.py` (`all_scenarios`, `_ALL_OFF`), `benchmarks/share_safety.py` (`check_share_safe`), `benchmarks/test_benchmarks.py`, `benchmarks/test_share_safety.py`, `benchmarks/aggregate.py`, `benchmarks/README.md`, `benchmarks/workloads/noop.py`, `benchmarks/workloads/cpu_burn.py`, `schemas/benchmark.schema.json`, `tests/test_bench_command.py`, `src/pubrun/__init__.py`, `src/pubrun/config.py`, `src/pubrun/_config_boot.py`, `src/pubrun/tracker.py`, `src/pubrun/writer.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/git.py`, `pyproject.toml`, `docs/performance.md`, `.aw/records/backlog/graduated/20261121-pubrun-improve-01-t1xqpw-startup-overhead.backlog.md`, orchestrator `9ppa0r`, and sibling plans `4il383`, `tkmm5p`, and `ckc3vl`. All cited paths exist and were verified; discrepancies in `redact_result` coverage, `import pubrun` synchronous auto-start timing, `get_git` cwd behavior, and `tests/test_bench_command.py` scenario consumption were recorded as findings and fixed.

### Step R2

- Checked: E/V 1:1 bijection (`E-01`..`E-05` to `V-01`..`V-05`), Scope-Paths completeness, `Item-Dependencies: none`, runtime-demonstration reachability of `V-01`..`V-05`, cross-plan CLI compatibility with `ckc3vl` (`--durability-policies fsync,finalize,atomic,strict`), and `## Approval and execution gate` compliance against `steps/r2-executability.md` and `steps/s7-finalize.md`. Caught and fixed non-conforming scope-fence STOP wording and hand-rolled `git mv` lifecycle wording (PR-004), plus phase-separation and scenario-mechanics gaps (PR-001, PR-005).

### Step R3

- Checked: Privacy, redaction, share-safety, non-publishing invariant, and `--workdir` filesystem safety against `benchmarks/harness.py::redact_result` and `benchmarks/share_safety.py::check_share_safe`. Caught and fixed incomplete redaction of `platform.node()` hostnames, custom `--workdir` paths, and repository root paths (PR-002), and missing enforcement of `check_share_safe` before emitting or writing `--out`.

### Step R4

- Checked: Engineering rubric A (correctness/data integrity), C (architecture/operability), D (anti-regression/invariants), E (testing/verification), F (KISS/principles), right-sizing/conceptual density (all 5 E-items are single-concern, single-file or single-pass steps), and `## Spec / documentation sync`. Caught and fixed `--workdir` ephemeral-subdirectory safety to prevent deleting pre-existing directories (PR-003), clean timing vs counter probe separation (PR-001), child env isolation, deterministic Git-repo cwd, `pubrun.__file__` verification, small-`n` statistics handling, CLI validation, and `tests/test_bench_command.py` regression coverage (PR-005, PR-007).

### Step S5

- Checked: Pre-existing `OQ-01` and all review findings. All 7 findings had Low remediation risk and were fixed in place with zero remaining unresolved or deferred findings and zero blocking human questions. Fixed `OQ-01` owner provenance per `steps/s5-questions.md` rule 5 (PR-006) and recorded the reversible decision below.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | high | IN-SCOPE | R2 / R4 (Measurement correctness and phase separation) | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:105-112`; `src/pubrun/__init__.py` lines 54-80 and 114-136; `src/pubrun/tracker.py::Run.__init__` | Installing `subprocess.Popen` or `json` wrappers in the same child process that times wall-clock import pre-imports `subprocess`/`json` and distorts before/after deltas for `4il383`; wrapping `import pubrun` with `perf_counter()` alone cannot separate package import from synchronous `Run.__init__` auto-start. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified separate clean uninstrumented timing probes and dedicated instrumented counter/serialization probes, plus matched phased probes (`import pubrun.noauto` -> `pubrun.start()` -> workload -> `pubrun.stop()`) alongside clean `import pubrun` auto-start timing (recommendation strength: strong). |
| PR-002 | high | UNDER-SCOPE | R3 (Security and privacy redaction) | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:101,114`; `benchmarks/harness.py::redact_result` lines 551-618; `benchmarks/share_safety.py::check_share_safe` | Reusing `benchmarks/harness.py::redact_result` alone does not substring-scrub `platform.node()` hostnames, non-home `--workdir` paths, or repository root paths, risking PII/path leaks into tracked `V-05` evidence or `--out` JSON. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required omitting raw paths from filesystem output, scrubbing `platform.node()`, `getpass.getuser()`, `~`, resolved `--workdir`, and repo root substrings, gating output with `benchmarks/share_safety.py::check_share_safe` (fail closed), and testing hostname and `--workdir` redaction in `tests/test_startup_benchmark.py` (recommendation strength: strong). |
| PR-003 | high | UNDER-SCOPE | R4 (Data integrity and cleanup safety) | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:99,125` | Describing `--workdir` as "cleaned up on exit" without requiring an ephemeral child subdirectory risks deleting a user's pre-existing directory or sibling files when `--workdir` points to an existing shared mount or directory. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Required `tempfile.TemporaryDirectory(prefix="pubrun-startup-bench-", dir=workdir)` so only the script's own subdirectory is removed on exit, plus a behavioral test verifying pre-existing sibling files inside `--workdir` survive cleanup (recommendation strength: very strong). |
| PR-004 | high | IN-SCOPE | R2 / S7 (Execution contract policy) | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:200,203`; `.aw/system/workflows/plan-review/steps/s7-finalize.md` lines 31-46 | Gate item 2 carried the prohibited "if additional files seem required, STOP and report" wording for out-of-scope edits, and gate item 5 instructed a hand-rolled lifecycle move to `executed/` instead of conditional runner/executor `aw ipd finalize` ownership. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Rewrote gate item 2 as a scope declaration with `--scope-reason`/`--scope-ack` justification (reserving STOP for genuinely unsafe conditions) and gate item 5 with conditional runner/executor `aw ipd finalize` ownership (recommendation strength: very strong). |
| PR-005 | medium | UNDER-SCOPE | R2 / R4 (Executability and scenario mechanics) | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:99-113`; `src/pubrun/config.py::get_global_config_dir`; `src/pubrun/capture/git.py::get_git`; `ckc3vl:94` | Six execution mechanics were underspecified: child `PUBRUN_*`/`XDG_CONFIG_HOME`/`APPDATA` isolation, omission of the mentioned nested-repo scenario from the numbered list, running `auto` scenarios in a non-Git temp dir (missing `get_git`'s 5-call path), `pubrun.__file__` layout verification against editable installs, `--durability-policies` `.pubrun.toml` wiring and CLI validation, and small-`n` (`n < 2`) quantile/failure handling. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Specified all six mechanics explicitly in Proposed changes item 1 and mirrored their verification in E-01, E-04, V-01, and V-04 (recommendation strength: strong). |
| PR-006 | low | IN-SCOPE | S5 (Open-question owner provenance) | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:157-162`; `.aw/system/workflows/plan-review/steps/s5-questions.md` line 21 | `OQ-01` recorded `- Owner: maintainer (confirmed upon plan approval)` on a resolved question that the plan author proposed rather than the maintainer answering. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Changed `- Owner:` to `plan author (overridable via CLI flags or upon plan approval)` and logged the reversible decision in `### Decisions` below (recommendation strength: strong). |
| PR-007 | low | IN-SCOPE | P / Technical Writing and regression coverage | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:29,35-46,56,78,83-88,146`; `tests/test_bench_command.py:351` | Bare sibling IDs lacked descriptive labels, E-01/E-05 Expected outcomes were long run-on sentences with unexpanded `p95`, Mermaid diagram nodes F/G differed from normative text, code citations lacked `path::Symbol` form, and `tests/test_bench_command.py` (which consumes `benchmarks/scenarios.py::all_scenarios`) was omitted from required test commands. | C:Low; U:Low; S:Low; F:Low; Overall:Low | fixed | Added descriptive labels for cited IDs, split run-on sentences and expanded `95th percentile (p95)`, aligned the Mermaid diagram, adopted `path::Symbol` citations, and added `tests/test_bench_command.py` to E-02/E-05/V-02/Required tests (recommendation strength: medium). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Default repetition count (`OQ-01`) and owner provenance for local pre-change and post-change breakdown runs | Keep default 3 passes x 15 iterations (+1 warmup per pass) with `--iterations`/`--passes`/`--warmup` CLI overrides, and record `- Owner: plan author (overridable via CLI flags or upon plan approval)` | Prompt maintainer before review completion; or default to 3 passes x 30 iterations matching `benchmarks/harness.py` | `.aw/records/plans/pending/20261121-startup-perf-01-fthyv5-startup-and-finalization-overhead-baseline-measurement.ipd.md:157-162`; `.aw/records/plans/pending/20261121-startup-perf-04-ckc3vl-post-change-overhead-comparison-documentation-sync-and-whole.ipd.md:94`; `.aw/system/workflows/plan-review/steps/s5-questions.md:21` | yes |
| D-2 | How to separate clean wall-clock timings from `subprocess`/`os.replace`/`os.fsync`/`json` instrumentation and separate `import` from `Run.__init__` startup | Run uninstrumented wall-clock timing probes (clean `import pubrun` + matched phased `noauto`/`start`/`workload`/`stop`) and separate instrumented counter/serialization probes | Patch `subprocess.Popen`/`json` inside the timed child process (distorts pre-change `subprocess` import timing and adds wrapper overhead) | `src/pubrun/__init__.py` lines 54-80 and 114-136; `src/pubrun/tracker.py::Run.__init__`; `src/pubrun/writer.py::_atomic_json_write`; `.aw/records/plans/pending/20261121-startup-perf-02-4il383-build-stamped-and-deferred-commit-identity-resolution.ipd.md:64` | yes |
| D-3 | Working directory for `auto-noop-default` and `auto-cpu-burn-default` scenarios | Initialize a deterministic temporary Git repository inside the ephemeral workdir so `get_git()` exercises its real 5-call pre-change path rather than short-circuiting on a non-Git temp dir | Run in an empty non-Git temp directory (misses `get_git`'s 5-to-3 spawn optimization in `tkmm5p`) | `src/pubrun/capture/git.py::get_git` lines 52-85; `.aw/records/plans/pending/20261121-startup-perf-03-tkmm5p-snapshot-write-coalescing-durability-policy-and-bounded-capt.ipd.md:102,176-178` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed, `- Scope-Paths:` and `- Item-Dependencies:` did not change, all revised sections (`Goal`, diagram, `E-*`, `Project conventions`, `Proposed changes`, `Required tests`, `Open questions`, `V-*`, and `Approval and execution gate`) were swept for internal consistency with zero residual contradictions or new open questions.

AW-REVIEW: DONE
