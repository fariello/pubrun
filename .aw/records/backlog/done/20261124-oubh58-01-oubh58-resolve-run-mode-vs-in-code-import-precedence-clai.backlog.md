- Id: oubh58
- Status: done
- Graduated-To: oubh58
- Set: oubh58
- Work-Kind: bug
- Priority: medium
- Summary: Resolve the false claim that pubrun run --mode overrides an in-code import pubrun.<mode>
- Short-Description: Resolve the false claim that pubrun run --mode overrides an in-code import pubrun.<mode>
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-25 done (aw backlog): closed by aw agy run: IPD lhwy0t executed (every IPD carrier is executed and this run executed .aw/records/plans/executed/20261124-oubh58-01-lhwy0t-implement-launch-time-pubrun-run-mode-override-over-in-code.ipd.md); evidence .aw/records/plans/executed/20261124-oubh58-01-lhwy0t-implement-launch-time-pubrun-run-mode-override-over-in-code.ipd.md
- 2026-11-25 graduated (aw set): Graduated to review-ready IPD lhwy0t (Set: oubh58) per /askme decision
- 2026-11-25 decision (the user via /askme): Implement the launch-time override so `pubrun run --mode <mode>` overrides an in-code `import pubrun.<mode>` import. No reason was given.
- 2026-11-25 created (aw backlog): Resolve the false claim that pubrun run --mode overrides an in-code import pubrun.<mode>

`docs/functional_spec.md#3.4 Import Modes`, `docs/api.md`, `docs/configuration.md`, `README.md`, and the `src/pubrun/full.py` module docstring state that only the launch-time `pubrun run --mode <mode>` overrides an in-code `import pubrun.<mode>`. The code does not do this. `pubrun run` (`src/pubrun/__main__.py`, the `run` command branch) only sets `PUBRUN_IMPORT_MODE` in the child environment. A mode submodule such as `src/pubrun/full.py` calls `select_mode("full", "pubrun.full", "explicit")` without reading that variable, and the first `select_mode` call wins. Observed on 2026-11-24: `python3 -m pubrun run --mode minimal -- python3 -c 'import pubrun.full as p; ...'` printed `env minimal selected full run active True`. The design intent is recorded in `.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md` (Precedence model, item 2). Decision needed from the maintainer: either implement the launch-time override, or correct the documentation and docstring. Acceptance: the documents and the observed behavior agree, and a test drives `pubrun run --mode` against a script that imports a mode submodule and asserts the selected mode. Found while authoring plan q4f9wi (backlog mv1g3x).
