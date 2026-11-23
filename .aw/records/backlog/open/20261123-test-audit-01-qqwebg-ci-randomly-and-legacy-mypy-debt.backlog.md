- Id: qqwebg
- Status: open
- Set: test-audit
- Work-Kind: chore
- Priority: low
- Summary: Enable pytest-randomly across CI matrix and clear remaining legacy mypy errors (deferred from /assess-testing T-19)
- Short-Description: Enable pytest-randomly across CI matrix and clear remaining legacy mypy errors (deferred from /assess-testing T-19)

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-23 created (aw backlog): Enable pytest-randomly across CI matrix and clear remaining legacy mypy errors (deferred from /assess-testing T-19)

Deferred from /assess-testing (Set test-audit, T-19) due to Medium-High Remediation Risk on functionality and complexity: enabling pytest-randomly across all 21 OS x Python CI jobs and burning down the remaining ~175 legacy mypy errors across ~20 modules after gzc672 establishes the [tool.mypy] ratchet and m66tfv hardens conftest.py isolation.
