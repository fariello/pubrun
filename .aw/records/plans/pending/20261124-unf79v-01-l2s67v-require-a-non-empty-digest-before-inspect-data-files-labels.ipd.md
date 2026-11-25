# IPD: Require a non-empty digest before inspect Data Files labels a record verified

- Date: 2026-11-24
- Kind: child
- Concern: File-provenance display badge accuracy in `pubrun inspect` (`src/pubrun/report/diagnostics.py`)
- Scope: Derive `src/pubrun/report/diagnostics.py::_classify_file_record_display` from the shared canonical classifier `src/pubrun/report/file_evidence.py::_classify_file_record` (introduced by `w24lw1`) so a `data_files` record without a non-empty digest value (`digest.value`, `sha256`, or `md5`) is never labeled `verified` in `pubrun inspect`, add behavioral tests in `tests/test_reports.py`, and add a `CHANGELOG.md` entry.
- Scope-Paths: src/pubrun/report/diagnostics.py, tests/test_reports.py, CHANGELOG.md
- Item-Dependencies: executed:w24lw1
- Status: reviewed
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Derive inspect Data Files display badges from shared file_evidence classifier so digestless records are not labeled verified
- Work-Kind: bug
- Priority: low
- From-Backlog: unf79v
- Blocks-Release: next
- Set: unf79v
- Order: 1
- Highest E allocated: 03
- Author: Antigravity
- Id: l2s67v

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003
- 2026-11-25 to-review (Antigravity): graduated from backlog item `unf79v` into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Ensure `pubrun inspect` (`src/pubrun/report/diagnostics.py::_classify_file_record_display`, `_summarize_data_files`, and `_print_data_files_block`) labels a `data_files` record as `verified` only when the record carries a non-empty digest value (`digest.value`, `sha256`, or `md5`), by deriving the display badge from the shared canonical classifier `src/pubrun/report/file_evidence.py::_classify_file_record` created by `w24lw1`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Delegate diagnostics display classification to shared file_evidence classifier

- [ ] E-01 Refactor `src/pubrun/report/diagnostics.py::_classify_file_record_display` to call `src/pubrun/report/file_evidence.py::_classify_file_record` and map canonical categories to display badge strings, and add sanitized legacy `md5` fallback to `src/pubrun/report/diagnostics.py::_extract_display_digest`.
  - Depends on: none
  - Expected outcome: `src/pubrun/report/diagnostics.py` imports `_classify_file_record` from `pubrun.report.file_evidence` (stdlib-only module created by `w24lw1`, preserving `import pubrun` isolation). `_classify_file_record_display(rec)` maps `"over_budget"` to `"over-budget"`, maps `"identified_only"` to `"path-only"` when `rec.get("evidence_strength") == "path_only"` else `"metadata-only"`, and returns the canonical label directly for `"changed"`, `"failed"`, `"unavailable"`, `"verified"`, `"asserted"`, and `"pending"`. A digestless record such as `{"hash_status": "completed"}` or `{"evidence_strength": "verified_content", "digest": {"value": "   "}}` returns `"metadata-only"` instead of `"verified"`. In `_extract_display_digest(rec, badge)`, when `badge == "verified"` and neither `digest.value` nor `sha256` is non-empty, a non-empty string `rec.get("md5")` is sanitized via `_sanitize_inline(raw_md5, max_len=128)` and formatted as `f"md5:{val[:12]}"`. All edited lines use Python 3.8-compatible `typing` annotations.
  - Execution state: pending

- [ ] E-02 Add behavioral tests in `tests/test_reports.py` verifying `_classify_file_record_display`, `_extract_display_digest`, `_summarize_data_files`, and `_print_data_files_block` for digestless `completed` / `verified_content` records, valid `digest.value` / `sha256` / `md5` records (including `md5:<prefix12>` rendering), `path_only` vs `metadata_only`, `over-budget`, `asserted`, `changed`, `failed` (including caller-digest mismatch), `unavailable`, and `pending`.
  - Depends on: E-01
  - Expected outcome: New tests in `tests/test_reports.py` drive `_classify_file_record_display`, `_extract_display_digest`, `_summarize_data_files`, and `_print_data_files_block` directly on manifest fixtures, asserting that `{"hash_status": "completed"}` and `{"evidence_strength": "verified_content"}` without a non-empty digest are counted under `identified_only` and printed with `[metadata-only]` rather than `[verified]`, while valid `digest.value`, `sha256`, and legacy `md5` records show `[verified]` with their sanitized digest prefix.
  - Execution state: pending

- [ ] E-03 Add one bullet to `CHANGELOG.md` under `## [Unreleased]` -> the top-most `### Fixed` subsection documenting that `pubrun inspect` / `pubrun show` Data Files badges require a non-empty digest before labeling a file `verified`, with zero em or en dashes.
  - Depends on: E-01
  - Expected outcome: `CHANGELOG.md` contains a clear user-facing bullet under the top-most `### Fixed` heading of `## [Unreleased]` with zero em or en dashes.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- Pending plan `w24lw1` (`From-Backlog: t55vh8`, `- Blocks-Release: next`) extracts `_classify_file_record`, `_is_caller_digest_mismatch`, and `_has_nonempty_digest_value` into stdlib-only `src/pubrun/report/file_evidence.py` and reuses it from `reproducibility.py` and `methods.py`. Declaring `- Item-Dependencies: executed:w24lw1` ensures `file_evidence.py` exists before this plan executes.
- `src/pubrun/report/diagnostics.py::_classify_file_record_display` currently returns `"verified"` whenever `hash_status == "completed"` or `evidence_strength == "verified_content"` without checking for a non-empty digest.
- `src/pubrun/report/diagnostics.py::_summarize_data_files` and `src/pubrun/report/diagnostics.py::_print_data_files_block` both call `_classify_file_record_display`, expecting display badge strings: `"verified"`, `"asserted"`, `"metadata-only"`, `"path-only"`, `"over-budget"`, `"pending"`, `"changed"`, `"failed"`, `"unavailable"`.
- `tests/test_show_sections.py::TestShowDataFilesProvenance` exercises `pubrun show` / `print_report` across all nine Data Files badges, digest prefixes, anomaly suppression, legacy records, and malformed `data_files`.
- `pyproject.toml` (`[[tool.mypy.overrides]]`) currently lists `"pubrun.report.diagnostics"` under `ignore_errors = true` (pending cleanup in `qe6dad`), so `python3 -m mypy` skips `diagnostics.py` unless `qe6dad` has already executed.
- Agent execution contract: user-facing prose (`CHANGELOG.md`) must contain zero em or en dashes, and tests must test runtime behavior without inspecting production source code.

## Findings

`src/pubrun/report/diagnostics.py::_classify_file_record_display` duplicates the file-provenance classification logic independently of `src/pubrun/report/file_evidence.py::_classify_file_record` (`w24lw1`) and omits the non-empty digest check on the `hash_status == "completed"` / `evidence_strength == "verified_content"` branch. Consequently, `pubrun inspect` displays `[verified]` and increments `counts["verified"]` for a record like `{"hash_status": "completed"}` even when no digest exists, disagreeing with `reproducibility.py` and `methods.py`.

```mermaid
flowchart TD
    R[data_files record] --> C[file_evidence._classify_file_record]
    C -->|verified - non-empty digest required| V[verified]
    C -->|over_budget| OB[over-budget]
    C -->|identified_only| ID{evidence_strength == path_only?}
    ID -->|Yes| PO[path-only]
    ID -->|No| MO[metadata-only]
    C -->|changed / failed / unavailable / asserted / pending| SAME[Same display badge]
```

## Proposed changes (ordered, validatable)

1. **`src/pubrun/report/diagnostics.py` (E-01):**
   - Import `_classify_file_record` from `pubrun.report.file_evidence`.
   - Replace the duplicated classification branches in `_classify_file_record_display(rec)` with delegation to `_classify_file_record(rec)` plus the two display-badge mappings (`"over_budget"` -> `"over-budget"`, and `"identified_only"` -> `"path-only"` if `rec.get("evidence_strength") == "path_only"` else `"metadata-only"`).
   - In `_extract_display_digest(rec, badge)`, also fall back to non-empty `rec.get("md5")` sanitized via `_sanitize_inline(raw_md5, max_len=128)` (formatted `f"md5:{val[:12]}"`) when `badge == "verified"` and neither `digest.value` nor `sha256` is set, so legacy `md5`-only records classified as `"verified"` display their digest prefix safely.
2. **`tests/test_reports.py` (E-02):**
   - Add unit tests covering `_classify_file_record_display`, `_extract_display_digest`, `_summarize_data_files`, and `_print_data_files_block` across digestless `completed` / `verified_content` records, valid `digest.value` / `sha256` / `md5` records (including `md5:<prefix12>` rendering), `path_only`, `over_budget`, `asserted`, `changed`, `failed`, `unavailable`, and `pending`.
3. **`CHANGELOG.md` (E-03):**
   - Add one bullet under `## [Unreleased]` -> the top-most `### Fixed` subsection with zero em or en dashes.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Only `src/pubrun/report/diagnostics.py`, `tests/test_reports.py`, and `CHANGELOG.md` are modified; `file_evidence.py`, `reproducibility.py`, and `methods.py` are owned by prerequisite `w24lw1`.
- Under-scope: none. All `diagnostics.py` consumers (`_classify_file_record_display`, `_summarize_data_files`, `_print_data_files_block`, and `_extract_display_digest`) are covered.

## Required tests / validation

- Run `python3 -m pytest tests/test_reports.py tests/test_show_sections.py tests/test_checks_commands.py tests/test_report_subpackage_integrity.py -v`.
- Run `python3 -m mypy` (from repository root) to confirm zero type regressions (noting whether `pubrun.report.diagnostics` remains in `pyproject.toml`'s `ignore_errors` list).
- Verify zero em or en dashes in added `CHANGELOG.md` diff lines using a portable exit-0 Python check on `git diff`.
- Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit code 0.

## Spec / documentation sync

`CHANGELOG.md` is updated in E-03. `docs/cli.md` (lines describing `--standard` and `--deep` `Data Files` output) does not claim digestless records are labeled `verified`, and no manifest schema field or CLI option changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste `git diff src/pubrun/report/diagnostics.py` showing `_classify_file_record_display` delegating to `src/pubrun/report/file_evidence.py::_classify_file_record` and `_extract_display_digest` formatting sanitized `md5:<prefix12>`, and paste output of `python3 -m pytest tests/test_report_subpackage_integrity.py -v` plus `python3 -m mypy` exiting 0 (noting whether `pubrun.report.diagnostics` remains in `pyproject.toml`'s `ignore_errors` list).
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste actual output of `python3 -m pytest tests/test_reports.py tests/test_show_sections.py tests/test_checks_commands.py -v` showing all new digestless/digested badge and `md5:<prefix12>` tests plus existing show/report/check tests passing with zero failures.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Paste `git diff CHANGELOG.md` showing the new bullet under the top-most `### Fixed` heading of `## [Unreleased]`; paste output of a portable exit-0 Python check confirming zero em or en dashes (`\u2014`, `\u2013`) in added (`+`) diff lines (e.g., `python3 -c 'import subprocess; diff = subprocess.check_output(["git", "diff", "--", "CHANGELOG.md"], text=True); added = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]; assert added, "empty diff"; bad = [l for l in added if "\u2014" in l or "\u2013" in l]; assert not bad, bad; print("OK added lines:", len(added))'`); and paste `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`) and prerequisite `w24lw1` reaches `executed`.

Execution contract:
1. **Open-questions precondition:** Zero blocking open questions remain before execution (`## Open questions` is empty).
2. **Scope declaration:** `- Scope-Paths:` declares `src/pubrun/report/diagnostics.py`, `tests/test_reports.py`, and `CHANGELOG.md`. If execution must edit another file or leave a declared file unchanged, make the change and justify it with `--scope-reason` or `--scope-ack` at finalize.
3. **Validation honesty (HARD MUST):** Paste the actual `pytest`, `mypy`, and `sanitize_paths.py` output observed after the final edit into `V-01`..`V-03`; never claim checks pass without running them.
4. **Path-scoped commit and never-push:** Commit only the modified paths through `aw commit l2s67v -- <paths>`; never use `git add -A` or `-a`, and never push without explicit human instruction.
5. **Lifecycle transition (conditional runner vs. standalone ownership):** When executed inside `aw oc run` / `aw agy run`, the runner owns the lifecycle move after the merge-and-revalidate gate; when executed standalone outside the runner, run `aw ipd finalize l2s67v` (never a hand-rolled `git mv` to `executed/`).
