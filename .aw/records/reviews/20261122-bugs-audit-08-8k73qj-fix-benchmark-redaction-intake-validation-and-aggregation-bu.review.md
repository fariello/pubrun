# Review findings: ipd 8k73qj

- Subject-Id: 8k73qj
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, `Goal`, Mermaid diagram, `E-01`..`E-05`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-05`, and `Approval and execution gate` of `.aw/records/plans/pending/20261122-bugs-audit-08-8k73qj-fix-benchmark-redaction-intake-validation-and-aggregation-bu.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal` and Mermaid flowchart | Unexpanded acronyms (`PII`, `JSON`, `URL`, `HTTPS`, `UTF-8`, `NaN`, `CSV`, `IPv6`); diagram lagged refined normative rules (`schema_path`, `status:needs-fix`, `errors` isolation) | Expanded acronyms on first use and synchronized flowchart labels with normative text | Technical writing requirements 1, 12(d), and 12(e) |
| Citations and label names across `E-01`..`E-04`, `Findings`, `Proposed changes` | Bare module-dotted names (`benchmarks.share_safety.check_share_safe`), wrong label `status:rejected` (real label is `status:needs-fix`), and imprecise `validate_benchmark_submission.validate_file` for `parse_json` | Standardized `path::Symbol` citations, corrected `status:needs-fix`, and cited `parse_json` and `_download` accurately | `steps/p-proofread.md` Section 11.1 and factual accuracy |
| `## Spec / documentation sync` | Bare unsubstantiated `N/A` | Cited verified `schemas/benchmark.schema.json`, `.github/workflows/benchmark-intake.yml`, `benchmarks/README.md`, `benchmarks/data/README.md`, and `docs/cli.md` | `steps/r4-engineering.md` spec/documentation sync rule |
| `## Approval and execution gate` | Missing honesty, never-push, scope-declaration, and conditional finalize clauses; vague manual-move wording | Replaced with compliant 5-item Execution contract using `--scope-reason`/`--scope-ack`, HARD MUST pasted-output rule, never-push, and conditional `aw ipd finalize 8k73qj` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| (none) | - | No unresolved ambiguities remain after in-place revisions. | None | None | very strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-05`, `benchmarks/harness.py`, `benchmarks/share_safety.py`, `benchmarks/aggregate.py`, `benchmarks/pull_submissions.py`, `.github/scripts/extract_attachment_url.py`, `.github/scripts/validate_benchmark_submission.py`, `schemas/benchmark.schema.json`, `.github/workflows/benchmark-intake.yml`, `tests/test_bench_command.py`, `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`, and Set `bugs-audit` orchestrator `jqqvkh`.

1. Yes: changes `benchmarks/share_safety.py::check_share_safe` validation rules, `benchmarks/harness.py` CLI exit/write behavior on self-check failure, `.github/scripts/extract_attachment_url.py` and `.github/scripts/validate_benchmark_submission.py` verdict/scheme contracts consumed by `.github/workflows/benchmark-intake.yml`, and `benchmarks/pull_submissions.py` report/retag behavior.
2. Yes: directly modifies PII redaction, share-safety enforcement, and internet-facing untrusted input parsers (`benchmarks/harness.py`, `benchmarks/share_safety.py`, `.github/scripts/extract_attachment_url.py`, `.github/scripts/validate_benchmark_submission.py`, `benchmarks/pull_submissions.py`).
3. No: 5 focused E-items across 4 task groups in 6 related benchmark/intake scripts plus 1 test file (child 08 of 9 in Set `bugs-audit`).
4. Yes: `- Scope-Paths:` explicitly lists all 7 modified files.
5. Yes: a defect in redaction, share-safety, or `check_schema` leaks private hostnames, Slurm node names, usernames, or raw submission payloads into public GitHub issues; using wrong label `status:rejected` breaks workflow label hygiene; and bare `pytest -q` skips the 4 dedicated benchmark/intake contract test suites outside `tests/`.

AW-TIER: complex

### Step R1

- Checked: Verified every cited file, symbol, workflow integration, schema constraint, and test contract across `benchmarks/harness.py`, `benchmarks/share_safety.py`, `benchmarks/aggregate.py`, `benchmarks/pull_submissions.py`, `.github/scripts/extract_attachment_url.py`, `.github/scripts/validate_benchmark_submission.py`, `schemas/benchmark.schema.json`, `.github/workflows/benchmark-intake.yml`, `pyproject.toml`, `tests/test_bench_command.py`, `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, `benchmarks/test_benchmarks.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`, and orchestrator `jqqvkh`. Caught wrong `status:rejected` label (actual label is `status:needs-fix`) and `test_pull_submissions.py` mock compatibility hazards (`PR-001`), missing `first.schema_path` vs user-keyed `first.path` leak guard + `int`/`str` sort crash in `check_schema` + Python 3.8+ transport/decode exception matrix (`PR-002`), un-specified integer `job_id` / `_scrub_pii_substrings` sentinel-splitting / bare `except Exception:` in `harness.py` (`PR-003`), missed `pyproject.toml` `testpaths = ["tests"]` exclusion of 4 existing benchmark/intake test suites (`PR-004`), and non-conforming execution gate / oldest-first history / inverted E/V test dependencies (`PR-005`).

### Step R2

- Checked: Verified author lint preflight (`aw ipd lint --phase author --agent` exit 0, `clean`, 0 findings), 1:1 `E-01`..`E-05` to `V-01`..`V-05` bijection (co-locating per-bug test authoring inside `E-01`..`E-04`), 7-file `- Scope-Paths:` parity, `- Item-Dependencies: none` matching orchestrator `jqqvkh`, concrete behavioral evidence in every `V-*` (all reachable via local `pytest`, no code-pinning), and `## Approval and execution gate` (fixed in `PR-005`).

### Step R3

- Checked: Verified privacy and internet-facing security across all 6 scripts: `check_share_safe` rejects any non-`None` value != `"<redacted>"` (including integer `machine.slurm.job_id`), `harness.py` fails closed on `check_share_safe` failure or error without writing `*.redacted.json`, `_scrub_pii_substrings` scrubs standalone and path-embedded usernames without mangling `"<redacted>"`, `extract_attachment_url.py` and `validate_benchmark_submission.py` enforce `https`-only on initial URL and redirects (`max_redirections = 3`), `check_schema` never emits `first.message`, `first.instance`, or user-keyed `first.path` into public GitHub comments, and `pull_submissions.py` keeps argv-only `gh` calls and payload-free error reporting (`no eval/exec/shell=True`).

### Step R4

- Checked: Evaluated engineering rubric sections A (uniform `None`-safe `_MUST_BE_REDACTED` check, sentinel-safe PII scrubbing, strict JSON `parse_constant` + `UnicodeDecodeError`, schema-path-only error messages, `isinstance(..., dict)` guards in `aggregate.py`, idempotent marker-based rejection comments, two-stage `gh issue edit` fallback), C (reusing `_v.Reject`, `share_safety.check_share_safe`, `gh issue view`), D (preserving `tests/test_bench_command.py`, `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, `.github/scripts/test_extract_attachment_url.py`, and `.github/scripts/test_validate_benchmark_submission.py`), E (explicitly running the 4 dedicated benchmark/`.github/scripts` test suites with `-o addopts=""` in addition to `tests/test_benchmark_intake_bugs.py`, `tests/test_bench_command.py`, and full `pytest -q`), F (KISS, preventing silent unsafe `.redacted.json` writes and silent batch aborts), right-sizing (5 focused E-items without inverted `E-05`/`V-01`..`V-04` dependency), and `## Spec / documentation sync`.

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught nonexistent `status:rejected` label (`PR-001`), `int` vs `str` `e.path` sort crash in `check_schema` (`PR-002`), `aggregate.py` non-dict `cpu`/`host`/JSON-root poisoning (`PR-002`), integer `slurm.job_id` bypass (`PR-003`), and bare `except Exception:` swallowing self-check errors in `harness.py:683` (`PR-003`).
  2. **Testing and regression expert:** Caught that `pyproject.toml` `testpaths = ["tests"]` hides 4 existing contract test suites from bare `pytest -q` (`PR-004`), preserved `benchmarks/test_pull_submissions.py:176-198` mock behavior (`PR-001`), and fixed inverted `V-01`..`V-04` test dependencies (`PR-005`).
  3. **UI / UX expert:** Preserved clear error substrings in `extract_attachment_url.py`, avoided spamming duplicate bot comments while still reporting genuinely new failure reasons (`PR-001`), and ensured `aggregate.py` creates missing output parent dirs cleanly.
  4. **Systems and software architect:** Aligned `pull_submissions.py` label constants and marker-based comment dedup with `.github/workflows/benchmark-intake.yml`, kept `_scrub_pii_substrings` backwards-compatible, and preserved single-source validation reuse (`PR-001`, `PR-003`).
  5. **Software engineer:** Specified exact `check_schema` `schema_path` + `validator` format, Python 3.8+ transport/decode exception handling, and compliant 5-item Execution contract (`PR-002`, `PR-005`).
  6. **Sophisticated power user:** Confirmed non-venv Linux/HPC users, Slurm cluster users, and short-username accounts (`ed`, `mark`, `run`) all get valid, share-safe, schema-conforming redacted results (`PR-003`).
  7. **Complete novice:** Expanded acronyms, updated flowchart parity, and clarified exact failure behavior on self-check failure (`PR-005`).
  8. **Stakeholder:** Confirmed all 10 benchmark redaction, intake security, aggregation, and pull bugs assigned to `8k73qj` in Set `bugs-audit` (`jqqvkh`) are fixed with zero silent deferrals.

### Step R6

- Checked: Evaluated decomposition across `E-01`..`E-05`. `8k73qj` is already child 08 of 9 in Set `bugs-audit`, covering 6 cohesive benchmark/intake scripts across 4 focused implementation passes plus 1 verification pass. No split recommended.

### Step R7

- Checked: Verified alignment with Set `bugs-audit` orchestrator `jqqvkh` and sibling child plans (`njn1up`..`kqzd15`). Confirmed `- Item-Dependencies: none` matches `jqqvkh`, `- Scope-Paths:` is completely disjoint from sibling `kqzd15` (`benchmarks/scenarios.py`, `benchmarks/workloads/file_read.py`, `scripts/`) and all other children in `bugs-audit`, and `tests/test_benchmark_intake_bugs.py` is owned exclusively by `8k73qj`.

### Step S5

- Checked: Audited pre-existing `## Open questions` (`None`), `## Deferred / out of scope` (`None`), and all 5 review findings (`PR-001`..`PR-005`). All 5 findings had Low remediation risk and were fixed in place. Recorded reversible evidence-based decisions `D-1`..`D-4` below. Zero unresolved or blocking human questions remain.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | R1/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-08-8k73qj-fix-benchmark-redaction-intake-validation-and-aggregation-bu.ipd.md:70`, `benchmarks/pull_submissions.py:60-62,220-285`, `.github/workflows/benchmark-intake.yml:112-158`, `benchmarks/test_pull_submissions.py:176-198` | `E-04` named a nonexistent label `status:rejected` (the canonical label in `pull_submissions.py` and `benchmark-intake.yml` is `status:needs-fix`), did not specify how comment deduplication stays compatible with `benchmarks/test_pull_submissions.py::test_retag_apply_rejection_comments` (where mocked `_run_gh` returns `""`) or how a new failure reason still posts, and did not specify storing unexpected per-issue errors in `report["errors"]` without mislabeling the issue `status:needs-fix`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected label to `status:needs-fix`, specified two-stage fallback (`--add-label <add> --remove-label status:pending` then `--add-label <add>`), specified `<!-- pubrun-benchmark-pull-reject:v1 -->` + reason-matched comment dedup degrading cleanly on empty/mocked `gh issue view`, and specified per-issue `report["errors"]` isolation (`D-3`, recommendation strength: very strong). |
| PR-002 | HIGH | IN-SCOPE | R3/R4.A | `.aw/records/plans/pending/20261122-bugs-audit-08-8k73qj-fix-benchmark-redaction-intake-validation-and-aggregation-bu.ipd.md:58,65,104`, `.github/scripts/validate_benchmark_submission.py:91-122,174-202`, `benchmarks/aggregate.py:104-196` | `validate_benchmark_submission.py::check_schema` sorting by `list(e.path)` crashes with `TypeError` on mixed `int`/`str` paths and interpolating `first.path` can still leak user-chosen dict keys (such as under `scenario_defs` or `machine`); `_download` needs `OSError` alongside `TimeoutError`/`HTTPException`/`ValueError` for Python 3.8+ `socket.timeout`; and `aggregate.py` also crashes on non-dict `machine`/`cpu`/`host` and non-dict JSON roots. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required `check_schema` to sort by `[str(p) for p in e.schema_path]` and format reasons strictly from `first.schema_path` and `first.validator`, added `(URLError, HTTPException, TimeoutError, OSError, ValueError)` + `(OSError, UnicodeDecodeError)` guards in `validate_benchmark_submission.py`, and added full `isinstance(..., dict)` guards in `aggregate.py` (`D-2`, recommendation strength: very strong). |
| PR-003 | HIGH | IN-SCOPE | R3/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-08-8k73qj-fix-benchmark-redaction-intake-validation-and-aggregation-bu.ipd.md:51,102-103`, `benchmarks/share_safety.py:45-93`, `benchmarks/harness.py:551-687`, `tests/test_bench_command.py:58-125` | `Proposed changes #1` restricted `machine.slurm.node`/`job_id` enforcement to "non-empty strings" (missing integer `job_id`); `_scrub_pii_substrings` lacked exact sentinel-splitting and non-PII schema key exclusions needed to preserve `tests/test_bench_command.py` while handling `"ed"`/`"mark"`; and `harness.py:683` had bare `except Exception: pass` that would swallow unexpected validator errors instead of failing closed. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified uniform `val is None` allowance and `val != "<redacted>"` rejection for all `_MUST_BE_REDACTED` entries (including `machine.slurm.node`/`job_id`), specified exact sentinel-splitting + path-vs-boundary scrubbing + fixed-key exclusions in `_scrub_pii_substrings`, and restricted `harness.py::main` ignore to `ImportError` only (`D-1`, recommendation strength: very strong). |
| PR-004 | HIGH | UNDER-SCOPE | R4.E | `.aw/records/plans/pending/20261122-bugs-audit-08-8k73qj-fix-benchmark-redaction-intake-validation-and-aggregation-bu.ipd.md:75-77,117-120,154-157`, `pyproject.toml:80-87`, `benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py` | `pyproject.toml` sets `testpaths = ["tests"]`, so bare `pytest -q` does NOT execute the 4 existing dedicated contract test suites for the exact 6 scripts modified by this plan (`benchmarks/test_share_safety.py`, `benchmarks/test_pull_submissions.py`, `.github/scripts/test_extract_attachment_url.py`, `.github/scripts/test_validate_benchmark_submission.py`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added explicit `pytest -o addopts="" benchmarks/test_share_safety.py benchmarks/test_pull_submissions.py .github/scripts/test_extract_attachment_url.py .github/scripts/test_validate_benchmark_submission.py -v` and `tests/test_bench_command.py` to `E-05`, `Required tests / validation`, and `V-05` (`D-4`, recommendation strength: very strong). |
| PR-005 | HIGH | IN-SCOPE | R2/S7/Check P | `.aw/records/plans/pending/20261122-bugs-audit-08-8k73qj-fix-benchmark-redaction-intake-validation-and-aggregation-bu.ipd.md:22-78,122-164`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | `## Approval and execution gate` omitted the HARD MUST pasted-output honesty rule, never-push rule, `--scope-reason`/`--scope-ack` scope declaration, and conditional `aw ipd finalize 8k73qj` ownership; `Workflow history` was oldest-first; `V-01`..`V-04` depended on tests created only in `E-05`; `Spec / documentation sync` was bare `N/A`; citations lacked `path::Symbol` form; and acronyms were unexpanded. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract, reordered `Workflow history` newest-first, co-located per-bug test authoring inside `E-01`..`E-04`, synchronized the Mermaid flowchart, substantiated `Spec / documentation sync`, standardized `path::Symbol` citations, and expanded acronyms (recommendation strength: very strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | How should `share_safety.py` enforce `virtual_env=None` and Slurm fields, and how should `_scrub_pii_substrings` handle short usernames? | Allow `val is _MISSING or val is None` for `_MUST_BE_REDACTED` entries (adding `machine.slurm.node` and `machine.slurm.job_id`) while rejecting any non-`None` value != `"<redacted>"`; in `_scrub_pii_substrings`, skip `"<redacted>"` and fixed schema/metadata keys, split around `"<redacted>"` tokens, replace path needles literally, and match username needles on `(?<![A-Za-z0-9_])...(?![A-Za-z0-9_])` boundaries. | Check only non-empty strings in `share_safety` (allows integer `job_id` leaks) or skip username scrubbing entirely (breaks `tests/test_bench_command.py:69,74,118,312`). | `benchmarks/share_safety.py:45-93`, `benchmarks/harness.py:183-195,551-618`, `src/pubrun/capture/python_runtime.py:67-68`, `tests/test_bench_command.py:58-125` | yes |
| D-2 | What should `validate_benchmark_submission.py::check_schema` include in its rejection `reason`? | Sort errors by `[str(p) for p in e.schema_path]` and format `reason` strictly from `first.schema_path` and `first.validator`, excluding `first.message`, `first.instance`, and untrusted user-keyed `first.path`. | Include `first.path` or sanitized `first.message` (can still leak untrusted user-supplied keys under permissive objects like `machine` or `scenario_defs` into public GitHub comments). | `.github/workflows/benchmark-intake.yml:130`, `.github/scripts/validate_benchmark_submission.py:116-121`, `.github/scripts/test_validate_benchmark_submission.py:53-56` | yes |
| D-3 | How should `pull_submissions.py` handle rejection labels, comment deduplication, and unexpected per-issue errors? | Keep canonical `_LABEL_NEEDS_FIX` (`"status:needs-fix"`), try `--add-label <add> --remove-label status:pending` before `--add-label <add>` in the `PullError` fallback, deduplicate comments with `<!-- pubrun-benchmark-pull-reject:v1 -->` + exact `- reason: {reason}` lookup via `gh issue view --json comments` (defaulting to empty on mocked/failed output), and capture unexpected per-issue exceptions into `report["errors"]` without mislabeling the issue. | Use `status:rejected` (contradicts workflow and tests), skip comment check on error (breaks idempotence), or label transient errors `status:needs-fix` (misleads contributors). | `benchmarks/pull_submissions.py:60-62,220-285`, `.github/workflows/benchmark-intake.yml:112-158`, `benchmarks/test_pull_submissions.py:176-198` | yes |
| D-4 | Should `E-05`/`V-05` run the benchmark and `.github/scripts` test suites explicitly in addition to `pytest -q`? | Yes: run `pytest -o addopts="" benchmarks/test_share_safety.py benchmarks/test_pull_submissions.py .github/scripts/test_extract_attachment_url.py .github/scripts/test_validate_benchmark_submission.py -v` plus `tests/test_benchmark_intake_bugs.py`, `tests/test_bench_command.py`, and full `pytest -q`. | Rely on bare `pytest -q` alone (skips all 4 dedicated suites because `pyproject.toml` sets `testpaths = ["tests"]`). | `pyproject.toml:80-87`, `benchmarks/test_benchmarks.py:3-13` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed (still `E-01`..`E-05` and `V-01`..`V-05`), `- Scope-Paths:` and `- Item-Dependencies:` did not change, and a full cross-section sweep confirmed zero stale tokens (`status:rejected`, bare `N/A`, manual-move wording) and full consistency across front matter, workflow history, flowchart, checklist, findings, proposed changes, doc sync, validation items, and execution gate.

AW-REVIEW: DONE
