# AGENTS

<!-- AGENT-WORKFLOWS:BEGIN -->
## Agent workflows

This repository includes reusable agent workflows under `.agents/workflows/`. They are invoked on demand and are NOT always-loaded context. See `.agents/workflows/index.md` for the list and how to run each (native `/commands` in OpenCode/Claude Code, or "read and execute <body path>" in any other agent).
<!-- AGENT-WORKFLOWS:END -->

<!-- PLAN-LIFECYCLE:BEGIN -->
## Plan / IPD lifecycle

Proposals are dated Implementation Plan Documents (IPDs) in `.agents/plans/pending/`, named `YYYYMMDD-<slug>.md`. They are reviewed (optionally via the `plan-review` workflow), approved by a human, executed, then moved to `.agents/plans/executed/`. This workflow is NOT auto-executed; human approval gates execution.
<!-- PLAN-LIFECYCLE:END -->
