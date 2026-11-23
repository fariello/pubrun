- Id: g2434y
- Status: done
- Set: g2434y
- Work-Kind: chore
- Priority: low
- Summary: examples/verify_all.py leaves an untracked examples/outputs/ directory (gitignore covers only minimal-research-workflow/outputs/)
- Short-Description: examples/verify_all.py leaves an untracked examples/outputs/ directory (gitignore covers only minimal-research-workflow/outputs/)

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-23 done (aw set): Duplicate of cp1jvn (carried by root-cause plan t336id)
- 2026-11-22 created (aw backlog): examples/verify_all.py leaves an untracked examples/outputs/ directory (gitignore covers only minimal-research-workflow/outputs/)

Observed while executing IPD 3tvesf (2026-11-22, git af36c85). Running 'python3 examples/verify_all.py' runs minimal-research-workflow/analysis.py, which writes Path("outputs") relative to the current directory (analysis.py line 165). verify_all runs it with the examples/ directory as cwd, so it creates examples/outputs/summary.json and examples/outputs/synthetic_data.csv. .gitignore line 66 ignores only examples/minimal-research-workflow/outputs/, so git status shows '?? examples/outputs/' after every verification run. Fix direction: resolve the output directory relative to analysis.py's own location, or run it with cwd set to its directory, or add the path to .gitignore.
