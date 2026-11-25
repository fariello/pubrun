- Id: t55vh8
- Status: done
- Graduated-To: t55vh8
- Set: t55vh8
- Work-Kind: bug
- Priority: low
- Summary: Reuse canonical _classify_file_record in methods.py and require a non-empty digest before classifying hash_status=completed as verified
- Short-Description: Reuse canonical _classify_file_record in methods.py and require a non-empty digest before classifying hash_status=completed as verified
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-25 done (aw backlog): closed by aw agy run: IPD w24lw1 executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261124-t55vh8-01-w24lw1-reuse-the-canonical-file-record-classifier-in-methods-report.ipd.md); evidence .aw/records/plans/executed/20261124-t55vh8-01-w24lw1-reuse-the-canonical-file-record-classifier-in-methods-report.ipd.md
- 2026-11-25 graduated (aw backlog): graduated by run run-20261124T202433Z-1567679: w24lw1
- 2026-11-24 created (aw backlog): Reuse canonical _classify_file_record in methods.py and require a non-empty digest before classifying hash_status=completed as verified

src/pubrun/report/methods.py::_classify_file_record duplicates the file-provenance classifier now canonical in src/pubrun/report/reproducibility.py and classifies records with hash_status=='completed' or evidence_strength=='verified_content' as 'verified' even when no non-empty sha256/digest/md5 value is present. Share the canonical helper from reproducibility.py (or require a non-empty digest value) so methods reports cannot count digestless records as content-verified.
