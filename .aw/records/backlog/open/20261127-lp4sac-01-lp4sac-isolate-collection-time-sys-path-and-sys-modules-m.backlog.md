- Id: lp4sac
- Status: open
- Set: lp4sac
- Work-Kind: chore
- Priority: low
- Summary: Isolate collection-time sys.path and sys.modules mutations in tests/test_benchmark_intake_bugs.py
- Short-Description: Isolate collection-time sys.path and sys.modules mutations in tests/test_benchmark_intake_bugs.py

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-28 created (aw backlog): Isolate collection-time sys.path and sys.modules mutations in tests/test_benchmark_intake_bugs.py

During execution of plan n39jh9 (Set assess-bt), tests/test_benchmark_intake_bugs.py was observed to insert benchmarks/ and .github/scripts/ into sys.path and register aggregate, extract_attachment_url, validate_benchmark_submission, and pull_submissions into sys.modules without teardown cleanup (same TEST-I5 class fixed in benchmarks/test_*.py, .github/scripts/test_*.py, tests/test_package_benchmark.py, and tests/test_startup_benchmark.py). Scope this cleanup into a small follow-up change using scoped fixtures that snapshot and restore sys.path and sys.modules.
