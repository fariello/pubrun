# Restart Context for opencode

## 1. Recovery Purpose

This document reconstructs an interrupted opencode session so a future opencode agent can resume it. It is intended to be read and executed directly.

- **Original session ID:** `ses_0cf7e38f0ffeDlVZcXq3Z1ttH6`
- **Original session title:** `Review and execute OpenCode recovery file`
- **Transcript size:** 296 turns, 148 interactions, 16803 lines
- **Truncation status:** Complete (no truncation applied)
- **Active continuation goal:** The `pubrun` project is in a clean, green, fully-pushed state; the only queued work is drafting an instructional **video script (#1)** and (optionally) executing the just-drafted `show config` IPD after its 4 open questions are answered.

## 2. Project Summary

The project is **`pubrun`**, a zero-runtime-dependency Python execution-provenance library/CLI (`~/VC/pubrun`, `git@github.com:fariello/pubrun.git`), plus two companion repos: a public benchmark-contribution repo (`~/VC/pubrun-benchmarks`) and a private JOSS paper repo (`~/VC/pubrun-paper`). The session (spanning many sub-sessions) hardened and extended pubrun via a strict `assess → plan-review → execute` workflow pipeline, prepared it for a v1.4.0 release and JOSS submission, and repeatedly used CI to catch cross-platform bugs. Broad current status: everything landed is committed and pushed with the full CI matrix (3 OS × Python 3.8–3.14) green; the last action was drafting a pending `show config` IPD.

## 3. Active User Intent at Interruption

- `Primary intent:` The user approved drafting the `show config` / config-provenance IPD; the agent completed and committed it (`ed0bbaf`, pending, local). The user's last message was "Yes show config IPD." — now satisfied.
- `Expected outcome:` A committed, decision-ready `show config` IPD in `.agents/plans/pending/`, plus a clean stopping point.
- `Immediate next action implied by the transcript:` Either (a) push the `show config` IPD to remote, or (b) draft the deferred **video script (#1)** — the only remaining item — or (c) stop on the clean green state. The agent asked the user whether to push the IPD now; that question is unanswered.
- `Constraints or cautions:` **Never push or force-push without explicit user approval.** The IPD is a draft (proposal), not to be executed until its 4 open questions are answered and human approval is given.
- `Uncertainty:` Whether the user wants the `show config` IPD pushed immediately is unresolved. Whether the video script should be drafted by the agent or awaits the user's voice is noted as an open judgment (`Inference:` the user may prefer to lead the marketing copy).

## 4. Durable Development Frame

### 4.1 Strategic Objective

Harden, extend, and document `pubrun` for a v1.4.0 release and an accompanying JOSS (Journal of Open Source Software) paper, while ensuring the library is reliable, honest, and cross-platform correct. The tool's purpose is trustworthy execution provenance for researchers, including HPC/cluster users.

### 4.2 Guiding Principles

- **KISS / "stupidly simple"** — the user repeatedly invoked this to reject over-engineering.
- **Zero runtime dependencies** (only `tomli` on Python < 3.11 as a stdlib `tomllib` polyfill; documented decision to keep it — see `docs/design/tomli-dependency-decision.md`).
- **Never intrude on / slow / break / crash the host script** — `import pubrun` must be invisible to the user's research code. Failures degrade to recorded facts (ghost mode), never raise into the host.
- **Honest docs** — no fabricated DOIs/URLs (use clearly-labeled placeholders); no claims a feature works when it doesn't.
- **Accessibility** — do not rely on ANSI `DIM` (not reliably WCAG 2.1 AA); textual/structural markers are authoritative; color is optional non-DIM reinforcement respecting `NO_COLOR`.
- **Matrix-validation discipline** (now a standing rule in `AGENTS.md`): changes to cross-platform contracts/shapes (manifest JSON schema, capture output shapes, anything with per-OS/per-Python differences) are NOT "done" on local green — they must pass the full CI matrix. Evidence: CI caught Windows-only and race-condition bugs three-plus times.
- **Citation name convention:** publication name **"Gabriele Fariello" / "Fariello, G."** for all citation surfaces; full legal **"Gabriele G. R. Fariello"** only for LICENSE/NOTICE/`__copyright__`.

### 4.3 Design Principles

- **Import mode is absolute over env/config**; only `pubrun run --mode` overrides it. Six import modes are final: `auto`, `full`, `noauto`, `nopatch`, `noconsole`, `minimal`.
- **Config conflicts are data, not events** — record in the manifest, never raise into the host (mirrors ghost mode).
- **Pausable capture is thread-local, ref-counted, mute (not unpatch)**; only ambient synchronous recorders (subprocess spy + console tee) are pausable; resource watcher and explicit annotations are not.
- **`open()` is never globally monkeypatched** (permanently rejected); only an opt-in `pubrun.open()` proxy exists, with a graded `level` (`none|name|stat|realpath|hash`, default `stat`).
- **Filesystem detection must be hang-safe** — parse `/proc/mounts`/`mountinfo`, never `statvfs`/`df`/`stat` a potentially-wedged target on the always-on path.
- **Redact-by-default** for shared benchmark data; the submitter's GitHub account is the (optional) contact channel; no server required.

### 4.4 Development Principles

- Strict lifecycle: **IPD → `/plan-review` → human approval → execute → move to `.agents/plans/executed/`**. Never auto-execute an IPD. `/plan-review` reviews/revises plans only, never executes code.
- **Ask open questions interactively with ample context** — the user repeatedly and emphatically required this; do not just recommend and proceed.
- **Characterization tests first** for behavior-changing refactors (pin current behavior before changing).
- **Doc-sync discipline** (in `AGENTS.md`): sync docs after user-visible behavior changes; run `/assess documentation` after such sessions.
- Commit per-IPD; interrupt only for genuine design/scope decisions.
- Pre-commit hooks auto-fix whitespace/EOF and abort the commit → re-`git add -A` + re-commit. Use `git commit -F <file>` (or heredoc) to avoid shell backtick interpretation in multi-line messages.

### 4.5 Non-Goals and Scope Boundaries

- Do NOT globally patch `builtins.open` (permanently rejected in `docs/design/file-io-provenance-evaluation.md`).
- Do NOT drop Python 3.8–3.10 support (data shows ~25–29% of scientific-package installs are still <3.11); `tomli` stays.
- Do NOT add `rich` or any runtime dependency; `matplotlib`/`textual`/`pytest-benchmark`/`jsonschema` are dev/optional-extra only.
- Do NOT wire `core.profile` to capture (decided: it is deprecated/inert-by-design, not implemented as a capture dial).
- Do NOT insinuate a JOSS paper that does not yet exist (no live `preferred-citation` until accepted).

### 4.6 Definition of Done or Acceptance Criteria

- Full suite green locally (last: **889 passed, 2 skipped, 0 failed** except the known SIGPIPE flake which passes in isolation) AND full CI matrix green.
- Docs synced (README, `docs/*.md`, CHANGELOG, schema) for any user-visible change.
- Executed IPDs moved to `.agents/plans/executed/` with an execution-notes record.
- Nothing pushed without explicit user approval.

## 5. Current State

### Verified by transcript evidence:

- All 7-IPD CLI/UX batch executed + pushed (output normalization, diff usability, report/res richness, diagnostic verbosity, run-number selector, TUI resource graphs, benchmark passes).
- Citation-DOI IPD Phase 1 executed (`.zenodo.json`, ORCID `0000-0002-0326-4752`, URI affiliation, placeholder DOI `10.5281/zenodo.PENDING` in 5 sites — note concept DOI `10.5281/zenodo.20801582` now exists but points at old v1.2.0).
- Five pre-v1.4.0 IPDs (A–E) executed: benchmark/runtime env capture, self-check+inspect, easy-bench+HPC, CLI filter completeness, open()-provenance evaluation.
- `use-cases` assess IPD executed (`resources` alias fixed, `pubrun init` tested, SIGKILL crashed test, HPC hydration fixture repaired, concurrent-runs invariant test).
- Profile-deprecation IPD executed + a discovered pre-existing `pubrun.report` subpackage-shadowing bug fixed across all 6 mode modules + `__init__.py`.
- Manifest-schema-reconciliation IPD executed (schema now matches emitted manifests; `pending`/`timeout` added to `capture_state.status` enum; conformance test gate).
- Framework updated to v1.0.0, `AGENTS.md` matrix-discipline rule added — both committed.
- Last CI run (`29056620170`): **21/21 jobs green**. `origin/main` at `29b422e`.

### Claimed or implied but needs repository verification:

- The `show config` IPD (`ed0bbaf`) is committed **locally only** (unpushed) unless a later push occurred.
- Local test count "889 passed" — verify with a fresh run.
- The known SIGPIPE flake (`tests/test_status.py::TestStatusScan::test_real_sigpipe_via_pipe`) passes in isolation.

### Unknown or uncertain:

- Whether `pubrun-benchmarks` local commits (`d0f74df`, `ae5b460`, `008c76d`, `3a86e65`) are pushed.
- Exact current dev venv (see §9 — environment shifted repeatedly; last known: `~/venv/p3.14` with `pytest==8.2.2` and editable pubrun installed).

## 6. User Preferences, Style, and Working Agreements

- **Always ask open questions interactively, with ample context** — the user is juggling many concurrent sessions and needs re-contextualization each time. This was stated multiple times and is non-negotiable.
- Terse, honest, no flattery; call out real weaknesses and self-corrections.
- Commit per-IPD; push only with explicit approval; never force-push without approval.
- Prefer flags over positional subcommands (KISS); prefer reusing existing mechanisms over new surface.
- Output prefixes standardized: `[INFO ]` (green), `[WARN ]` (yellow), `[ERROR]` (red), `[DEBUG]` (bright blue, gated by `PUBRUN_DEBUG`/`--debug`), `[ OK  ]` (green), `[FAIL ]` (red for `--run-tests`), all `NO_COLOR`-aware, never DIM.
- User corrected the agent when it deviated silently from an agreed decision (e.g. `--force` vs `--submit`); document deviations, don't hide them.

## 7. Key Decisions, Rationale, and Tradeoffs

- `Decision:` Keep `tomli` as a conditional <3.11 poly
