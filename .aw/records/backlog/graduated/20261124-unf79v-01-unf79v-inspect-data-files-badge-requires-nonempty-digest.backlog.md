- Id: unf79v
- Status: graduated
- Graduated-To: unf79v
- Set: unf79v
- Work-Kind: bug
- Priority: low
- Summary: Require a non-empty digest before the inspect Data Files block labels a record verified
- Short-Description: Require a non-empty digest before the inspect Data Files block labels a record verified
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-25 graduated (aw set): Graduated to review-ready IPD l2s67v (Set: unf79v)
- 2026-11-25 created (aw backlog): Require a non-empty digest before the inspect Data Files block labels a record verified

src/pubrun/report/diagnostics.py::_classify_file_record_display labels a data_files record 'verified' when hash_status is 'completed' or evidence_strength is 'verified_content', even when the record carries no non-empty digest.value, sha256, or md5 value. For example, _classify_file_record_display({'hash_status': 'completed'}) returns 'verified', while src/pubrun/report/reproducibility.py::_classify_file_record returns 'identified_only' for the same record. The inspect Data Files block (diagnostics._print_data_files_block and diagnostics._summarize_data_files) therefore shows a digestless record as content-verified. Make the display badge require a non-empty digest value before it shows 'verified', for example by deriving the badge from the shared classifier that plan w24lw1 (backlog t55vh8) moves into src/pubrun/report/file_evidence.py. Found while authoring plan w24lw1, which fixes the same defect in src/pubrun/report/methods.py only.
