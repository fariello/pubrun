- Id: mz0erz
- Status: graduated
- Graduated-To: mz0erz
- Set: mz0erz
- Work-Kind: chore
- Priority: low
- Summary: Remove deprecated profile= examples from src/pubrun docstrings and default.toml header comments
- Short-Description: Remove deprecated profile= examples from src/pubrun docstrings and default.toml header comments

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-26 graduated (aw backlog): graduated by run run-20261126T144416Z-1230057: ha769g
- 2026-11-26 created (aw backlog): Remove deprecated profile= examples from src/pubrun docstrings and default.toml header comments

During execution of plan 2uwuiu (Set doc-audit), inspecting src/pubrun/core.py showed that public docstrings and default configuration header comments still show deprecated, inert profile= and PUBRUN_PROFILE= usage even though core.profile is deprecated and records a profile_deprecated manifest notice:
- src/pubrun/__init__.py (module docstring: pubrun.start(profile="deep") and @pubrun.audit_run(profile="basic"))
- src/pubrun/core.py (docstrings for start(), audit_run(), and tracked_run() show profile="deep" or profile="minimal")
- src/pubrun/resources/default.toml (Resolution Order header comments show pubrun.start(profile="deep") and PUBRUN_PROFILE="deep" directly above the core.profile deprecation notice)

Update those docstrings and header comments to show non-deprecated capture.* overrides instead.
