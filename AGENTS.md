# AGENTS

<!-- AGENT-WORKFLOWS:BEGIN -->
## Agent workflows

This repository includes reusable agent workflows under `.agents/workflows/`. They are invoked on demand and are NOT always-loaded context. See `.agents/workflows/index.md` for the list and how to run each (native `/commands` in OpenCode/Claude Code, or "read and execute <body path>" in any other agent).

### Guidelines for Antigravity & Other Agents
When requested to run one of these workflows (e.g. "run release-review", "assess <concern>", "run setup-repo", "run scaffold"):
1. Locate the workflow's entry file under `.agents/workflows/` (referenced in `.agents/workflows/index.md`).
2. Read and execute the instructions defined in that workflow file step-by-step.

### Writing prompts for another AI (research/handoff prompts)
When asked to write a prompt to give to another AI (e.g. a research prompt for an LLM with web search), the prompt you produce MUST be upload-ready:
1. It contains ONLY the prompt itself, addressed to that AI. Put NO instructions for the user inside it (no "copy this", no "paste below the line").
2. It is self-contained, so the user can select-all-and-copy it, or upload it and say "read and execute the attached prompt", with nothing to edit.
3. It instructs the target AI to return its answer as a DOWNLOADABLE markdown (`.md`) file, so the result can be handed back for consumption.

### Durable reference and walkthroughs documentation
1. Immortalize research/analysis you rely on for a decision to `.agents/docs/research/` using `YYYYMMDD-HHMM-NN-<slug>.md`.
2. Save narrative walkthroughs to `.agents/docs/walkthroughs/` with `...-walkthrough.md`.
3. If you keep plans/IPDs or walkthroughs in a private, hidden, or tool-internal "brain"/memory/scratch dir (e.g. Antigravity/Gemini), you MUST also keep an exact, conventions-compliant copy under `.agents/plans/` (moved through the lifecycle) and `.agents/docs/walkthroughs/`; the tracked copy is the source of truth, the private copy is disposable.

### Agent execution contract
When you execute a task or plan here you MUST: commit ONLY files you changed, path-scoped (`git commit -m msg -- <path>`), never `git add -A`/bare/`-a`, and never push; when you report tests passed, paste the ACTUAL runner output (never claim success you did not run); write no em or en dashes in authored Markdown. When asked to REVIEW or report, do NOT modify or commit anything: report and wait. Do NOT add commits to a plan already in `.agents/plans/executed/`; close a post-execution gap with a new corrective IPD, not an in-place edit. Never create or push a git tag, a GitHub Release, or a registry/PyPI upload except inside release-review Section 9 after an explicit human GO (see `RELEASING.md`); no ad-hoc `git tag` or `git push --follow-tags`. See `CONTRIBUTING.md` and the `.agents/plans` README for detail.
<!-- AGENT-WORKFLOWS:END -->

<!-- PLAN-LIFECYCLE:BEGIN -->
## Plan / IPD lifecycle

Proposals are dated Implementation Plan Documents (IPDs) in `.agents/plans/pending/`, named `YYYYMMDD-<slug>.md`. They are reviewed (optionally via the `plan-review` workflow), approved by a human, executed, then moved to `.agents/plans/executed/`. This workflow is NOT auto-executed; human approval gates execution.
<!-- PLAN-LIFECYCLE:END -->

## Doc-sync discipline

After any session that changes user-visible behavior (new config keys, changed defaults, new CLI commands, new API functions), run `/assess documentation` to verify docs match the implementation. The documentation lens requires cross-referencing every claim against the actual code — this catches stale defaults, missing keys, and renamed commands that manual review misses.

## Matrix-validation discipline

Local green ≠ done for anything **cross-platform or contract-shaped**. Changes to the manifest JSON schema (`schemas/manifest.schema.json`), capture-engine output shapes, import/CLI entry paths, or any behavior that varies by OS or Python version MUST be validated on the full CI matrix (3 OS × Python 3.8–3.14) before the work is considered complete — local dev only ever exercises one platform's output. This has repeatedly caught defects invisible locally (Windows-only import/liveness bugs, an incomplete `resources` alias, an empty-`console` manifest shape that failed the schema on Windows only). When you touch these areas: push, watch CI to green, and fix stragglers before moving on or moving an IPD to `executed/`.
