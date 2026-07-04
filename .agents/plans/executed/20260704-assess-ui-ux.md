# IPD: Assess UI/UX - CLI and API Usability

- Date: 20260704
- Concern: UI/UX usability and intuitiveness
- Scope: CLI (`pubrun` commands), Python API ergonomics
- Status: PENDING (awaiting human approval; not executed)
- Author: OpenCode (its_direct/pt3-claude-opus-4.6-1m-us)

## Goal

Improve the usability of pubrun's CLI and Python API so that both novice users
and power users can accomplish tasks with minimal friction, clear feedback, and
discoverable features.

## Project conventions discovered (Step 0)

- Pending-plans location: `.agents/plans/pending/` (YYYYMMDD-slug.md)
- Stack: Python 3.8+, CLI via argparse, no TUI deps unless `[tui]` extra
- Guiding principles: Universal fallback (intuitive, KISS, honest docs)
- User surface: CLI (13 commands), Python API (start/stop/annotate/phase/etc.)

## Findings

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| UX-01 | Medium | Low | Novice | CLI help | Unknown command error shows the raw argparse error with ALL aliases expanded (`bug-report, feedback, issue, cite, clean, combined, cpu, diff, mem, meta, methods, report, rerun, res, run, show, status, ui, tui, gui`). This is noisy and confusing — aliases shouldn't appear in the valid choices list. | `pubrun boguscmd` output |
| UX-02 | Medium | Low | Novice/Power-user | CLI | No `pubrun report` in `--help` output (it's listed in the argparse error but not in the help text). The `show` command exists but isn't listed in the main help either. Inconsistency. | Compare `--help` output (lists `show`) vs argparse error (lists `report`). Actually `report` IS an alias for `show` — but the alias appears in error messages, creating confusion about whether it's a separate command. |
| UX-03 | Low | Low | Novice | CLI status | When run directory doesn't exist (`./runs/` absent), `pubrun status` shows "No runs found." with no guidance on what to do next. A first-time user doesn't know why or how to start tracking. | `pubrun status` with no runs dir |
| UX-04 | Low | Low | Power-user | CLI diff | `pubrun diff` with no runs silently fails. With only one run it shows an error, but the error isn't actionable (doesn't suggest running twice). | Expected: "Only 1 run found; need at least 2 to diff." |
| UX-05 | Low | Low | Novice | Python API | `pubrun.start()` returns a `Run` object but the type isn't documented in help/docstring as having any useful attributes. Users don't know they can do `run.run_dir`, `run.run_id`, etc. without reading source. | `core.py:78-105` — docstring mentions "Returns: The active Run instance" but not what's on it. |
| UX-06 | Low | Low | Power-user | CLI clean | `pubrun clean -y` deletes ALL matching runs without showing what will be deleted first. The `--dry-run` flag exists but `-y` doesn't show a summary before acting. For a destructive operation this is risky. | `status.py` clean_runs logic — `-y` skips to `to_delete = candidates` directly. |
| UX-07 | Low | Low | Novice | CLI | `pubrun --info` output is undocumented (not in `--help` description) and the flag is listed between `--show-config` and `--run-tests` without explanation of what "system capabilities" means. | `--help` output: `--info Display system capabilities and pubrun version info.` — vague. |
| UX-08 | Low | Low | Stakeholder | CLI | No `pubrun init` or equivalent obvious entry point. A new user's first experience is "what do I do?" The README says `import pubrun` but the CLI has no guided onboarding command. | Missing command; first-run experience is undiscoverable from CLI alone. |

## Proposed changes (ordered, validatable)

| Step | Source | Change | Files | Remediation Risk | Validation |
|------|--------|--------|-------|------------------|------------|
| 1 | UX-01 | Suppress aliases from the argparse `choices` error message. The existing `_SubcommandAwareArgumentParser.error()` at `__main__.py:1029` is the natural place: filter the "invalid choice" message to show only primary command names (exclude aliases). A primary-commands list is already implicit in the subparsers definition. | `__main__.py:1029` | Low | `pubrun boguscmd` shows clean error with only primary commands. |
| 2 | UX-03 | When `pubrun status` finds no runs, print a helpful hint: "No runs found in ./runs/. To start tracking: `import pubrun` in your script, or `pubrun run -- python script.py`." | `status.py` or `__main__.py` | Low | First-time user gets actionable guidance. |
| 3 | UX-04 | When `pubrun diff` has < 2 runs, print: "Need at least 2 runs to diff. Run your script twice, then try again." | `__main__.py` (diff handler) | Low | Clearer error for common novice case. |
| 4 | UX-05 | Add a "Useful attributes" section to the `start()` docstring listing `run.run_dir`, `run.run_id`, `run.config`, `run.is_active`. | `core.py` | Low | `help(pubrun.start)` shows useful return info. |
| 5 | UX-06 | When `clean -y` is used, still print a one-line summary BEFORE deleting: "Deleting N runs (X.Y MB)..." so the user sees what happened. Not a prompt — just feedback. | `status.py` clean_runs | Low | `-y` still shows what it did. |
| 6 | UX-08 | Add a `pubrun init` alias that runs `--create-config` and prints a getting-started message (what to do next). Thin wrapper, not a new feature. | `__main__.py` | Low | `pubrun init` is discoverable and friendly. |
| 7 | UX-07 | Improve `--info` help text to: "Display runtime diagnostics: Python version, pubrun version, import mode, detected config files, and capture capabilities." | `__main__.py` | Low | Self-documenting flag. |

## Deferred / out of scope

| Finding ID | Remediation Risk | Axis | Reason |
|------------|------------------|------|--------|
| UX-02 | Low | — | **Resolved by Step 1.** The alias-in-error problem IS UX-01. Once Step 1 filters the error message to show only primary commands, the confusing alias appearance is fixed. No separate work needed. |

## Domain invariants preserved

- `pubrun clean` safety contract: `-y` still does NOT add a `y` shortcut to
  delete all; it skips the selection prompt but deletes all *candidates*. Step 5
  adds feedback but does not change the deletion logic.
- `pubrun` must never crash the host script: none of these changes touch the
  tracking/capture path. All are CLI-layer only.

## Required tests / validation

1. `pubrun boguscmd` error output: no aliases visible.
2. `pubrun status` with empty runs dir: shows hint message.
3. `pubrun diff` with 0-1 runs: shows clear guidance.
4. `pubrun clean -y`: prints summary line before deleting.
5. `pubrun init`: runs and produces `.pubrun.toml` + getting-started output.
6. Full regression: 583+ tests green.

## Spec / documentation sync

- If `pubrun init` is added, document in `docs/cli.md` and README quickstart.
- Update `--info` description in docs.

## Open questions

1. Should `pubrun init` create a `.pubrun.toml` with `capture_mode = "standard"`
   pre-set (since the default is now "off"), or leave it as the bare default?
   Recommendation: include `capture_mode = "standard"` commented-out with a note.
2. Should we add shell completion (bash/zsh/fish) for discoverability?
   Recommendation: defer — nice-to-have but adds complexity and maintenance.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before
execution, and it is NOT auto-executed.
