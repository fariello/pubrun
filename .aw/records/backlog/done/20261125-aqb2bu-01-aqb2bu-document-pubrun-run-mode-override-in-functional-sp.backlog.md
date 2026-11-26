- Id: aqb2bu
- Status: done
- Graduated-To: aqb2bu
- Set: aqb2bu
- Work-Kind: followup
- Priority: low
- Summary: Document PUBRUN_RUN_MODE_OVERRIDE in functional_spec.md sections 10.2 and 10.3 and configuration.md
- Short-Description: Document PUBRUN_RUN_MODE_OVERRIDE in functional_spec.md sections 10.2 and 10.3 and configuration.md

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-26 done (aw backlog): closed by aw agy run: IPD 87qr8h executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md); evidence .aw/records/plans/executed/20261125-aqb2bu-01-87qr8h-document-pubrun-run-mode-override-in-functional-spec-and-con.ipd.md
- 2026-11-25 graduated (aw backlog): graduated by run run-20261125T192525Z-1777170: 87qr8h
- 2026-11-25 created (aw backlog): Document PUBRUN_RUN_MODE_OVERRIDE in functional_spec.md sections 10.2 and 10.3 and configuration.md

Plan lhwy0t added the PUBRUN_RUN_MODE_OVERRIDE launch-time environment variable in src/pubrun/__main__.py (pubrun run --mode) and src/pubrun/_bootstrap.py::select_mode, and documented it in docs/cli.md and docs/functional_spec.md section 11.13. Three environment-variable reference locations still omit it: docs/functional_spec.md section 10.2 (the paragraph listing boot environment variables excluded from resolve_config), docs/functional_spec.md section 10.3 (the Supported Environment Variables table), and docs/configuration.md (the Environment Variables table). Add PUBRUN_RUN_MODE_OVERRIDE to those three locations so every supported boot-time environment variable appears in the configuration reference and functional specification.
