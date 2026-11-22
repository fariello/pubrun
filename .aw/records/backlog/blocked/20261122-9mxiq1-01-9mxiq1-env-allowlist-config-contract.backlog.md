- Id: 9mxiq1
- Status: blocked
- Set: 9mxiq1
- Work-Kind: bug
- Priority: medium
- Summary: Decide [capture.environment] allowlist config key, matching rule, and empty default for l7ko8p OQ-01
- Short-Description: Decide [capture.environment] allowlist config key, matching rule, and empty default for l7ko8p OQ-01
- Blocks-Release: next
- Gate-Kind: artifact
- Gate-Ref: l7ko8p

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-22 created (aw backlog): Decide [capture.environment] allowlist config key, matching rule, and empty default for l7ko8p OQ-01

Plan l7ko8p (E-02) enforces [capture.environment].mode = "allowlist", which is documented in src/pubrun/resources/default.toml and docs/configuration.md without defining a config key name, matching rule, or empty-list default. Maintainer decision is required before approving l7ko8p: Option 1 (recommended, strength: strong) defines allowlist = [] with exact + fnmatch globs and fail-closed empty list; Option 2 defines allowlist = [] with exact names only; Option 3 defines allowed_vars with a built-in default safe list.
