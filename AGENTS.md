# AGENTS

<!-- AGENT-WORKFLOWS:BEGIN -->
## Agent workflows

This repository includes reusable agent workflows under `.agents/workflows/`. They are invoked on demand and are NOT always-loaded context. See `.agents/workflows/index.md` for the list and how to run each (native `/commands` in OpenCode/Claude Code, or "read and execute <body path>" in any other agent).
<!-- AGENT-WORKFLOWS:END -->

<!-- PLAN-LIFECYCLE:BEGIN -->
## Plan / IPD lifecycle

Proposals are dated Implementation Plan Documents (IPDs) in `.agents/plans/pending/`, named `YYYYMMDD-<slug>.md`. They are reviewed (optionally via the `plan-review` workflow), approved by a human, executed, then moved to `.agents/plans/executed/`. This workflow is NOT auto-executed; human approval gates execution.
<!-- PLAN-LIFECYCLE:END -->

## Doc-sync discipline

After any session that changes user-visible behavior (new config keys, changed defaults, new CLI commands, new API functions), run `/assess documentation` to verify docs match the implementation. The documentation lens requires cross-referencing every claim against the actual code — this catches stale defaults, missing keys, and renamed commands that manual review misses.

## Matrix-validation discipline

Local green ≠ done for anything **cross-platform or contract-shaped**. Changes to the manifest JSON schema (`schemas/manifest.schema.json`), capture-engine output shapes, import/CLI entry paths, or any behavior that varies by OS or Python version MUST be validated on the full CI matrix (3 OS × Python 3.8–3.14) before the work is considered complete — local dev only ever exercises one platform's output. This has repeatedly caught defects invisible locally (Windows-only import/liveness bugs, an incomplete `resources` alias, an empty-`console` manifest shape that failed the schema on Windows only). When you touch these areas: push, watch CI to green, and fix stragglers before moving on or moving an IPD to `executed/`.
