# Restart Context for opencode

## 1. Recovery Purpose

This document reconstructs an interrupted opencode session for a future agent to read and execute. It contains no other reliable context.

- **Original session ID:** `ses_180d11757ffel5GqWedBcdqzm5`
- **Original session title:** `pubrun 0.3.0 release`
- **Transcript size:** 454 turns, 227 interactions, 14506 lines
- **Truncation status:** Complete (no truncation applied)
- **Active continuation goal:** The session ended cleanly at a deliberate stopping point; the next action is to start a fresh session, run `/assess edge-cases`, execute the resulting IPD, then run `/release-review`.

## 2. Project Summary

`pubrun` is a stupidly-simple, zero-runtime-dependency Python (3.8+) library and CLI for execution provenance capture aimed at researchers/ML practitioners. This session shipped v0.2.0 and v0.3.0 to PyPI, then ran an extended sequence of agent-workflow assessments (`/assess`), plan reviews, executions, and repo setup. At the point of interruption all work was committed and pushed, `.agents/plans/pending/` was empty, and 599 tests passed. The final agreed step was to pause and resume in a fresh session for `edge-cases` assessment and a full `release-review`.

## 3. Active User Intent at Interruption

- `Primary intent:` Continue the pre-release QA/QC pipeline for pubrun using the agent-workflows framework — specifically run `/assess edge-cases`, execute its IPD, then run `/release-review`.
- `Expected outcome:` A thorough edge-cases assessment IPD (verified against actual code paths, not inferred), its execution, then a broad release review.
- `Immediate next action implied by the transcript:` Start a brand-new opencode session (the prior agent declined to do `edge-cases` due to context-window exhaustion and risk of shallow work).
- `Constraints or cautions:` Do not push unless explicitly told. Prefer small, targeted, behavior-preserving changes. The `edge-cases` lens requires verifying claims against real code paths (do not infer from names) — the prior agent explicitly warned that doing it under context pressure would degrade quality.
- `Uncertainty:` Whether v0.3.0 was actually published to PyPI in this session (the transcript shows the local commits, tag, and green CI for 0.3.0, and a message-restart summary implies the twine upload was still pending awaiting a token). `Needs verification:` confirm 0.3.0 publish status on PyPI before any further release action.

## 4. Durable Development Frame

### 4.1 Strategic Objective

Ship pubrun as a robust, well-documented, well-tested, zero-dependency provenance library that "just works" on `import pubrun` and never crashes the importing script. Build toward eventual 1.0 after real-world validation.

### 4.2 Guiding Principles

- **Never crash the host script.** pubrun must degrade to "ghost mode" or silently no-op on any internal failure rather than propagate exceptions to the importing script. `High confidence` (repeatedly enforced).
- **Zero runtime dependencies** except `tomli` for Python < 3.11. `rich` was fully dropped. `High confidence`.
- **KISS / minimal scope.** Do only what pubrun uniquely can do; don't reimplement things users can already do (e.g. whole-run `python -m cProfile`). `High confidence`.
- **Observer, not policy enforcer.** pubrun records what happened; the importing script controls exit codes and behavior (e.g. `broken pipe` is display-only; manifest outcome/exit code stay script-controlled). `High confidence`.
- **Fix-by-default gated by Remediation Risk** (agent-workflows Fix Bar); effort is never a reason to defer. `High confidence`.
- **Cross-platform correctness** (Linux, macOS, Windows) using stdlib-only, platform-branching code. `High confidence`.

### 4.3 Design Principles

- Console tee operates at the **text layer** (`sys.stdout`), never the binary layer (`sys.stdout.buffer`); text handling is correct and intentional. `High confidence`.
- Import-mode architecture: `__init__.py` is a thin target-aware router; `core.py` holds the public API; `_bootstrap.py` tracks import-mode state/conflicts; `_config_boot.py` is a lightweight boot resolver; `_modes.py` defines modes. `High confidence`.
- Import modes: `auto` (default), `noauto` (no auto-start; hooks install on `start()`), `nopatch` (auto-start, no global hooks; resource monitoring still on), `quiet` (no auto-start, no hooks). `High confidence`.
- Additive-only changes preferred; preserve backward compatibility and manifest schema.
- Atomic writes (`os.replace`) for manifest/config; secure run dirs via `umask(0o077)`.

### 4.4 Development Principles

- Every code-changing IPD execution must sync docs/CHANGELOG in the same work. **Doc-sync discipline is now recorded in `AGENTS.md`.** `High confidence`.
- Documentation assessments must **cross-reference every factual claim (defaults, APIs, CLI) against the actual source**, not judge prose in isolation. `High confidence` (root cause of an earlier miss).
- Tests use mocks for platform-specific paths so they run on all CI OSes (avoid platform-skips where possible).
- IPD/plan naming convention: `YYYYMMDD-<slug>.md` (NOT `YYYY-MM-DD-`). `High confidence` (explicitly corrected).
- Plans live under `.agents/plans/pending/` and `.agents/plans/executed/` only. `High confidence` (consolidated from old `plans/` and `agents/plans/`).

### 4.5 Non-Goals and Scope Boundaries

- **Determinism tracking** — removed from roadmap (fragile detection, locking harmful, low value vs `pubrun.annotate(seed=...)`).
- **summary.txt generation** — removed from roadmap (superseded by `pubrun status` / `pubrun report --basic`); config key marked "not yet implemented".
- **Whole-run profiling** — out of scope; only phase-scoped profiling was implemented.
- **Console `standard`/`deep` mode differentiation** — reserved for future.
- Out of scope entirely: workflow/DAG scheduling, server/dashboard, data versioning, plugin system (roadmap only), file-I/O monkey-patching of `open()`.

### 4.6 Definition of Done or Acceptance Criteria

- All tests pass across CI matrix (7 Python versions × 3 OSes = 21 jobs green).
- Working tree clean; version synced across `pyproject.toml`, `src/pubrun/__init__.py` fallback, `CITATION.cff`, docs; CHANGELOG entry; git tag on the green commit; fresh `dist/` built before publish.
- Docs factually match implementation.
- No breaking changes without explicit flagging.

## 5. Current State

### Verified by transcript evidence:

- Complete: All `.agents/plans/pending/` IPDs executed and moved to `executed/` (performance, bugs, bugs-2, console-capture-defaults, process-tree-and-profiling, transitive-package-capture, ui-ux, documentation, testing).
- Complete: `/setup-repo` applied (secret-scan CI, `.gitleaksignore`, `.gitignore` hardening, `.editorconfig`, pre-commit config, dependency-audit CI, plan lifecycle dirs + AGENTS.md doc).
- Complete: 599 tests passing locally (17 new testing-IPD tests + 582 prior), with a known flaky SIGPIPE pipe test.
- Complete: `edge-cases` assessment NOT started (prior agent declined due to context exhaustion).
- Pushed: All session work through the testing IPD execution was pushed. `.agents/plans/pending/` empty.

### Claimed or implied but needs repository verification:

- v0.3.0 published to PyPI (message-restart summary implies upload was pending a token; earlier transcript claims completion). `Needs verification.`
- `v0.3.0` git tag location relative to HEAD (tag was moved multiple times during CI flake fixing). `Needs verification.`
- Exact HEAD commit and clean working tree. `Needs verification.`
- Whether `dist/` is fresh vs stale (recurring issue). `Needs verification.`

### Unknown or uncertain:

- Current installed package version in the dev venv vs source (`pubrun --version` reads installed metadata; may be stale — run `pip install -e .` if mismatched).
- Whether any `.agents/workflows/` tool files have lingering mode-bit changes.

## 6. User Preferences, Style, and Working Agreements

- **Ask before executing** when a workflow/plan says to wait for go-ahead. The user corrected the agent twice early on for proceeding without explicit approval; "answering clarifying questions" is NOT approval. Require an unambiguous "go".
- **Do not push unless explicitly told.**
- README casual tone ("stupidly simple") is intentional and validated by a market/adoption assessment; keep it.
- Preserve Markdown nav bars at top/bottom of relevant `.md` files.
- IPDs named `YYYYMMDD-<slug>.md`; plans only under `.agents/plans/`.
- Use color in CLI output consistently (matched `pubrun status` summary line to existing ANSI markers).
- `pubrun clean` safety is non-negotiable: no default selection, no `y` shortcut to delete all, explicit selection/range/`all`, plus a selected-runs confirmation table before final `y/N`.
- Prefer terminal-width-adaptive column sizing in CLI tables.
- Wants questions asked when a workflow has open questions (grill-me style), then decisions recorded.

## 7. Key Decisions, Rationale, and Tradeoffs

- `Decision:` Release as 0.3.0, not 1.0.0. `Rationale:` Import-mode system is substantial but pre-1.0; needs real-world validation first. `Rejected alternatives:` 1.0.0 now. `Confidence:` High.
- `Decision:` Default `[console].capture_mode = "off"`. `Rationale:` Avoid surprising users by tee-ing stdout on import; performance and interactivity safety. `Rejected:` keeping `"standard"` default. `Confidence:` High. `Note:` This is a behavior change requiring `.pubrun.toml` opt-in for old behavior.
- `Decision:` Surface `broken pipe` as a display-only status in `pubrun status`. `Rationale:` `completed`/exit 0 hides early termination; manifest outcome unchanged. `Confidence:` High.
- `Decision:` `nopatch` keeps resource monitoring (not a global hook); `noauto` controls timing not scope. `Confidence:` High.
- `Decision:` Phase-scoped profiling only (`scope = "phases-only"`), stdlib `cProfile` default, external tools opt-in and never auto-installed. `Rationale:` KISS; whole-run profiling is trivially done without pubrun. `Confidence:` High.
- `Decision:` Removed determinism tracking and summary.txt from roadmap with documented rationale. `Confidence:` High.
- `Decision:` Documentation lens rubric is correct as-is; the earlier miss was because `/assess documentation` was never actually run, not a lens defect. Added doc-sync discipline to `AGENTS.md` instead of changing the lens. `Confidence:` High.
- `Decision:` PERF-09 (runs directory index) deferred. `Rationale:` Benchmarked 504 runs in 148ms (~0.29ms/run
