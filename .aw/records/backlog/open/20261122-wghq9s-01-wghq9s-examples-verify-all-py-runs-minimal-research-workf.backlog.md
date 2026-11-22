- Id: wghq9s
- Status: open
- Set: wghq9s
- Work-Kind: bug
- Priority: low
- Summary: examples/verify_all.py runs minimal-research-workflow/analysis.py from repo root and leaves untracked outputs/ directory
- Short-Description: examples/verify_all.py runs minimal-research-workflow/analysis.py from repo root and leaves untracked outputs/ directory
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-22 created (aw backlog): examples/verify_all.py runs minimal-research-workflow/analysis.py from repo root and leaves untracked outputs/ directory

## Context
`examples/verify_all.py` executes `examples/minimal-research-workflow/analysis.py` via `subprocess.run([sys.executable, script], ...)` using the repository root as the working directory. Because `analysis.py` writes `outputs/summary.json` and `outputs/synthetic_data.csv` relative to its current working directory, running `python3 examples/verify_all.py` creates an untracked `outputs/` directory at the repository root even though `.gitignore` ignores only `examples/minimal-research-workflow/outputs/`.

## Acceptance criteria
- Running `python3 examples/verify_all.py` executes `examples/minimal-research-workflow/analysis.py` inside its own directory (or cleans up generated example outputs) so `git status -s` shows zero untracked `outputs/` files at the repository root afterward.
- Existing example verification assertions in `examples/verify_all.py` continue to pass with exit code 0.
