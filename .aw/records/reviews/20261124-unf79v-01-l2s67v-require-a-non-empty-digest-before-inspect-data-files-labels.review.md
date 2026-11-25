# Review findings: ipd l2s67v

- Subject-Id: l2s67v
- Subject-Type: ipd
- Reviewed-At: 2026-11-25
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261124-unf79v-01-l2s67v-require-a-non-empty-digest-before-inspect-data-files-labels.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md` Section 11.1 code citation rules, plus `src/pubrun/report/diagnostics.py` (`_classify_file_record_display`, `_extract_display_digest`, `_summarize_data_files`, `_format_data_files_summary_line`, `_print_data_files_block`), `src/pubrun/report/reproducibility.py` (`_is_caller_digest_mismatch`, `_has_nonempty_digest_value`, `_classify_file_record`), `tests/test_show_sections.py` (`TestShowDataFilesProvenance`), `tests/test_report_subpackage_integrity.py`, `pyproject.toml` (`[[tool.mypy.overrides]]`), `docs/cli.md` (`--standard` / `--deep`), `CHANGELOG.md`, prerequisite plan `.aw/records/plans/pending/20261124-t55vh8-01-w24lw1-reuse-the-canonical-file-record-classifier-in-methods-report.ipd.md`, and backlog item `.aw/records/backlog/graduated/20261124-unf79v-01-unf79v-inspect-data-files-badge-requires-nonempty-digest.backlog.md`. No pre-review snapshot was needed: lane `HEAD` `9ae07f8` had a clean working tree (`git status --short` empty). `aw ipd lint --phase author --agent` exited 0 (`outcome: clean`, `findings: 0`). Requirement 12(b), (d), and (e) are satisfied by the Mermaid flowchart in `## Findings`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `E-01`, `Proposed changes` item 1, `E-02`, `V-01`, `V-02` | Hedged `_extract_display_digest`'s `md5` fallback (`"(or remains consistent with canonical 'verified')"`), omitted `_sanitize_inline`, and omitted `_extract_display_digest` / `md5:<prefix12>` checks from `E-02` and `V-01`/`V-02` | Unambiguously requires `_sanitize_inline`-sanitized `md5:<prefix12>` in `E-01`/`Proposed changes` item 1, tests `_extract_display_digest` in `E-02`/`V-02`, and uses Section 11.1 `src/pubrun/report/file_evidence.py::_classify_file_record` citations | Removes ambiguity, ensures ANSI/newline sanitization of `md5` display prefixes, and satisfies Section 11.1 (PR-003). |
| `Project conventions discovered`, `Required tests / validation`, `V-01`, `V-02` | Omitted `tests/test_show_sections.py` and omitted `pyproject.toml`'s `ignore_errors = true` on `pubrun.report.diagnostics` | Added `tests/test_show_sections.py` to `Project conventions discovered`, `Required tests / validation`, and `V-02`, and documented `pyproject.toml` `ignore_errors` on `pubrun.report.diagnostics` in `Project conventions discovered`, `Required tests / validation`, and `V-01` | Covers the existing Data Files badge regression suite and keeps `mypy` evidence honest (PR-001, PR-002). |
| `E-03`, `Proposed changes` item 3, `Spec / documentation sync`, `V-03` | Did not specify the top-most `### Fixed` heading under `## [Unreleased]`, did not substantiate `docs/cli.md` non-edit, and lacked a concrete zero-dash diff check | Specified the top-most `### Fixed` heading of `## [Unreleased]`, noted `docs/cli.md` verification, and added a portable exit-0 Python zero-dash diff check in `V-03` | Eliminates ambiguous changelog placement and strengthens `V-03` verification (PR-003). |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (`src/pubrun/report/diagnostics.py`, `tests/test_reports.py`, `CHANGELOG.md`), `- Item-Dependencies: executed:w24lw1`, 3 E-items in 1 task group, `- Kind: child`.

1. Yes (bounded): changes user-facing `pubrun inspect` / `pubrun show` `Data Files` summary counts and `[ Data Files ]` per-file badges and digest prefix rendering for digestless `completed`/`verified_content` records and legacy `md5`-only records (matching prerequisite `w24lw1`, which is `standard`).
2. No: touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 3 focused E-items in 1 task group across 3 files.
4. Yes: all modified paths are declared in `- Scope-Paths:`.
5. No: display-only classification and tests; cannot lose data and is trivially reversible.

AW-TIER: standard

### Step R1

- Checked: `src/pubrun/report/diagnostics.py:122-311` (`_classify_file_record_display`, `_extract_display_digest`, `_summarize_data_files`, `_format_data_files_summary_line`, `_print_data_files_block`), `src/pubrun/report/diagnostics.py:934-936,1020`, `src/pubrun/report/reproducibility.py:866-925` (`_is_caller_digest_mismatch`, `_has_nonempty_digest_value`, `_classify_file_record`), `tests/test_show_sections.py:175-413` (`TestShowDataFilesProvenance`), `tests/test_report_subpackage_integrity.py:1-127`, `pyproject.toml:115-141` (line 137 `"pubrun.report.diagnostics"` under `ignore_errors = true`), `docs/cli.md:560-561`, `CHANGELOG.md:9,120`, prerequisite plan `w24lw1` (`.aw/records/plans/pending/20261124-t55vh8-01-w24lw1-*.ipd.md`, `- Status: reviewed`, `- Readiness: go-pending-approval`), and backlog item `unf79v`.
- Confirmed: every branch of `file_evidence._classify_file_record` maps cleanly onto `diagnostics._classify_file_record_display`'s 9 badge strings; `tests/test_show_sections.py::_rich_manifest` verified entry carries `sha512` (`"1234567890abcdef" * 8`), so existing tests remain compatible; `docs/cli.md:560-561` requires no edit.
- PR-001: `tests/test_show_sections.py::TestShowDataFilesProvenance` is the primary regression suite for `Data Files` badges and was omitted from `Required tests / validation` and `V-02`. Fixed.
- PR-002: `pyproject.toml:137` lists `"pubrun.report.diagnostics"` under `ignore_errors = true`, so `python3 -m mypy` silently skips it until `qe6dad` lands. Fixed by documenting this honestly in `Project conventions discovered`, `Required tests / validation`, and `V-01`.
- PR-003: normalized Section 11.1 `path::Symbol` citations, removed the hedge in `E-01` for `_extract_display_digest` `md5` fallback, and specified the top-most `### Fixed` heading in `CHANGELOG.md`.

### Step R2

- Checked: 1:1 E/V bijection (`E-01`..`E-03` to `V-01`..`V-03`), `- Scope-Paths:` completeness (3 paths), `- Item-Dependencies: executed:w24lw1` (valid reviewed plan creating `src/pubrun/report/file_evidence.py`), runtime-demonstration reachability of `V-01`..`V-03`, re-derivation convention (no hardcoded test counts), and all five execution-contract elements in the gate.
- PR-001, PR-002, PR-003: strengthened `V-01` (`md5:<prefix12>` diff + honest `ignore_errors` note), `V-02` (`tests/test_show_sections.py` + `md5:<prefix12>` assertion), and `V-03` (portable exit-0 Python zero-dash diff check).

### Step R3

- Checked: all five bullets of Check R3 full form.
  - Identity/authorization: read-only local manifest display in `diagnostics.py`; no auth boundary changes.
  - Secrets/trust-boundary inputs: manifest fields (`digest.value`, `sha256`, `md5`, `path`, `label`, `hash_status_detail`) are untrusted input when inspecting an external or tampered manifest. Required `_extract_display_digest` to pass `rec.get("md5")` through `_sanitize_inline(raw_md5, max_len=128)` (matching `digest.value` and `sha256`), preventing terminal ANSI/newline injection (PR-003).
  - Queries, commands, files, uploads, outbound calls: none added; `file_evidence.py` is stdlib-only (`typing` only), preserving `import pubrun` isolation.
  - Sensitive data collection, logging, exposure, retention, and errors: displays only 12-char digest prefixes for verified/asserted records; anomaly hashes stay suppressed.
  - Privileged bypasses: none.

### Step R4

- Checked: engineering rubric A, C, D, E, F; right-sizing and conceptual density (3 focused E-items in 1 task group across 3 files, each executable in one focused pass; no splitting warranted); anti-regression (single canonical classifier shared across `reproducibility.py`, `methods.py`, and `diagnostics.py` eliminates duplicate drift; `tests/test_show_sections.py` pins all 9 badges, `NO_COLOR`, no-`Colors.DIM`, legacy records, and malformed `data_files`); spec and documentation sync (verified `docs/cli.md:560-561` needs no edit; `CHANGELOG.md` updated in `E-03`).

### Step S5

- Checked: `## Open questions` is `None.`. `## Deferred / out of scope (with reason)` is `None.`. All three review findings (PR-001, PR-002, PR-003) have Overall Remediation Risk `Low` and were fixed in place. No unresolved human decision exists, so no blocking open question is added and the lane outcome carries `questions: []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | MEDIUM | UNDER-SCOPE | R2 / R4 E (missing Data Files regression suite) | `tests/test_show_sections.py:175-413` (`TestShowDataFilesProvenance`); Plan `Required tests / validation` (line 98) and `V-02` (line 120) | `tests/test_show_sections.py::TestShowDataFilesProvenance` is the primary existing test suite exercising `diagnostics.py`'s `Data Files` summary counts, all nine `[ Data Files ]` badges, digest prefixes, and legacy/malformed handling, yet `Required tests / validation` and `V-02` omitted it. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `tests/test_show_sections.py` to `Project conventions discovered`, `Required tests / validation`, and `V-02` (recommendation strength: strong). |
| PR-002 | MEDIUM | IN-SCOPE | R1 / R2 (`mypy` `ignore_errors` on `diagnostics.py`) | `pyproject.toml:115-141` (line 137 `"pubrun.report.diagnostics"` under `ignore_errors = true`); Plan `Required tests / validation` (line 99) and `V-01` (line 115) | `V-01` relied on `python3 -m mypy` exiting 0 to verify zero type regressions in `src/pubrun/report/diagnostics.py`, without noting that `pyproject.toml` lists `"pubrun.report.diagnostics"` under `ignore_errors = true` until `qe6dad` clears it. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Documented `pyproject.toml`'s `ignore_errors` status in `Project conventions discovered`, `Required tests / validation`, and `V-01`, and required Python 3.8-compatible `typing` annotations on edited lines (recommendation strength: strong). |
| PR-003 | LOW | IN-SCOPE | Check P / R2 / R3 (hedged `md5` display spec, sanitization, citations, and `CHANGELOG.md` check) | Plan `E-01` (lines 38, 40), `E-02` (line 43), `E-03` (line 48), `Project conventions` (line 58), `V-01`..`V-03` (lines 115-125); `src/pubrun/report/diagnostics.py:168-200`; `CHANGELOG.md:120,263,290,335,609` | `E-01` hedged `_extract_display_digest`'s `md5` fallback (`"(or remains consistent with canonical 'verified')"`), omitted `_sanitize_inline` on `md5`, omitted `_extract_display_digest` / `md5:<prefix12>` checks from `E-02`/`V-01`/`V-02`, used dotted citations instead of Section 11.1 `path::Symbol`, did not specify the top-most `### Fixed` heading in `CHANGELOG.md`, and lacked an exit-0 zero-dash check in `V-03`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Made `_sanitize_inline`-sanitized `md5:<prefix12>` unconditional in `E-01`/`Proposed changes` item 1, added `md5:<prefix12>` verification in `E-02`/`V-01`/`V-02`, applied Section 11.1 `path::Symbol` citations, specified the top-most `### Fixed` heading under `## [Unreleased]`, and added a portable exit-0 Python zero-dash diff check to `V-03` (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier | `standard` | `simple`, `complex` | Changes user-facing `pubrun inspect` / `pubrun show` Data Files badge classification and digest display across 3 E-items and 3 files, matching prerequisite `w24lw1` (`standard`). | yes |
| D-2 | Require sanitized `md5:<prefix12>` in `_extract_display_digest` unconditionally instead of leaving it optional | Require `_sanitize_inline`-sanitized `md5:<prefix12>` for `md5`-only verified records | Leave `md5` digest display optional or omit it | `file_evidence._classify_file_record` classifies legacy `md5`-only records as `verified`; displaying `md5:<prefix12>` via `_sanitize_inline` keeps `[verified]` lines consistent with `digest.value` and `sha256` while preserving ANSI/newline sanitization. | yes |

### Step S6

- Checked: the review did not add or remove any `E-*` or `V-*` item, did not change `- Scope-Paths:` or `- Item-Dependencies:`, and introduced no new open question or structural ambiguity. All three findings (PR-001, PR-002, PR-003) were fixed in place with Low remediation risk and swept across the whole plan. `aw ipd lint --phase review-finalize --agent` will be verified before committing. No second review pass is needed.

AW-REVIEW: DONE
