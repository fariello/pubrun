# IPD-B: `pubrun self-check` (live env) and `pubrun inspect` (post-hoc run diagnosis)

- Date: 2026-07-06
- Concern: usability / diagnosability. Two explicit, report-only commands that help users
  spot performance/config pitfalls (like installing pubrun on a slow NFS mount) both
  before/around a run (`self-check`) and after the fact from a completed run's manifest
  (`inspect`).
- Scope: `src/pubrun/__main__.py` (two new subcommands) + a new report/check module. Both
  are CLI-only and MUST NOT be on the `import pubrun` code path. No new runtime dependency.
- Status: PENDING — plan-review, then execution on human approval. NOT auto-executed.
  Depends on IPD-A for the manifest fields `inspect` surfaces (fstype/free-RAM/load); can
  land first and simply report "not captured" for runs predating IPD-A.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

The maintainer hit real NFS slowness on the Unity cluster (pubrun installed in an
NFS-mounted venv shared across nodes). There is currently no way to (a) proactively flag
such a configuration or (b) look at a finished run and ask "was this I/O-bound / on a slow
filesystem?". This IPD adds two explicit commands. Neither runs automatically; neither is
imported by `import pubrun`.

Key architectural clarification (agreed with maintainer): `self-check` and `inspect` are
ordinary CLI subcommands launched as their own process (`pubrun self-check`). They share
NOTHING with a user's `import pubrun` in a research script, so they **cannot** change,
slow, break, or crash that script. The ONLY thing that would have posed a host-script risk
was an import-time nudge — which is explicitly DROPPED (see "Explicitly out of scope").

## Project conventions discovered (Step 0)

- Principles: zero runtime deps, KISS, honest docs, never intrude on the host script,
  degrade gracefully / never crash, no reliance on ANSI DIM (WCAG), respect `NO_COLOR`.
- Subcommands live in `src/pubrun/__main__.py` (subparsers at `:1230`); the shared
  filter helper is `_add_run_filter_args` (`:1109`); manifest host identity is
  `host.hostname` (`tracker.py:613`, read at `status.py:236`).
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Design decisions (agreed with maintainer)

- **Names:** `pubrun self-check` (live, current machine) and `pubrun inspect` (post-hoc,
  reads a completed run's manifest).
- **Report-only.** Neither command mutates the environment or any run. No auto-fixing.
- **CLI-only, off the import path.** The check logic lives in a new module imported by
  `__main__.py`, NOT by `pubrun/__init__.py`. A test asserts `import pubrun` does not
  import the check module (keeps it impossible to affect the host script).
- **`self-check` scope = perf pitfalls + install health** (maintainer's choice), namely:
  filesystem type of install/output/`$TMPDIR` (flag network FS), free RAM, load average,
  pubrun import origin; PLUS install health: config file validity, output dir writable,
  git availability, Python version supported. The optional-dep/matplotlib check is
  DROPPED (matplotlib is only the dev-only `[bench]` extra; irrelevant to normal users).
- **`inspect`'s signature feature — the "different system" warning.** On an HPC the run
  executes on a compute node but `inspect` is typically typed on the head node. `inspect`
  compares the manifest's recorded `host.hostname` (and hardware descriptors) against the
  CURRENT host and, if they differ, prints a GLARING banner: any *live* re-checks reflect
  THIS machine, not where the run executed. This applies to `self-check` too when pointed
  at a run.
- **Exit codes:** both exit `0` normally; a `--strict` flag makes them exit non-zero if any
  warning fired (useful as an HPC job pre-check in a submit script or CI).

## Proposed changes

1. **New module `src/pubrun/report/checks.py`** (name TBD): pure functions that produce a
   list of findings `{severity, code, message, suggestion}` from (a) the live environment
   and (b) a loaded manifest. No printing here — returns data so it is unit-testable.
   Reuses IPD-A's `capture/filesystem.py`, memory, and load helpers (or, if IPD-A not yet
   landed, a minimal local `/proc` reader; consolidate later).
2. **`pubrun self-check`** subcommand (`__main__.py`): runs live checks + install-health
   checks, prints findings with an authoritative textual severity marker (e.g. `[warn]`)
   plus optional non-DIM color reinforcement respecting `NO_COLOR`. Suggestions are honest
   and non-magical (e.g. "pubrun is imported from an NFS mount (`/home/...`); startup
   overhead may be inflated. Consider a node-local venv or `pip install --target` to local
   disk."). `--strict` → non-zero on any warning. Optional `--json` for machine-readable
   output.
3. **`pubrun inspect [run]`** subcommand: loads a completed run's manifest (via the same
   run-selection path as other commands; supports `-f/-F/-s/-S` selectors via
   `_add_run_filter_args(..., include_limit=False)` to pick which single run), surfaces
   captured I/O/RAM/load/filesystem signals (from IPD-A fields; "not captured" for older
   runs), and prints the different-system banner when the inspecting host != the run host.
   `--json` and `--strict` as above.
4. **Docs:** `docs/cli.md` entries for both; a short "diagnosing performance / HPC" section
   in `docs/research-use.md` or a new `docs/hpc.md` pointing users at these commands.

## Anti-regression / invariants

- **`import pubrun` must not import the check module.** Explicit test:
  `import pubrun; assert 'pubrun.report.checks' not in sys.modules` (adjust to final name).
- **Report-only.** No test/anything writes to the environment; `inspect` opens manifests
  read-only.
- **Never crash.** Missing/partial/old manifests, unknown filesystems, non-Linux platforms
  → clear "not available / not captured" findings, never a traceback. Test with a manifest
  lacking the IPD-A fields.
- **Accessibility.** Severity conveyed by a textual marker (authoritative), color optional,
  non-DIM, `NO_COLOR`-respecting. Test the `NO_COLOR` path.
- **Filter parity.** `inspect` uses the shared `_add_run_filter_args` helper (consistency
  with IPD-D), not an ad hoc reimplementation.

## Required tests / validation

- Unit: findings functions given synthetic env / synthetic manifest produce expected
  finding codes (NFS install, low RAM, high load, different-host, old-manifest-no-data).
- CLI: `self-check` exits 0 normally, non-zero under `--strict` with a seeded warning;
  `--json` well-formed.
- CLI: `inspect` on a same-host manifest (no banner) vs a different-host manifest (banner
  present); on a pre-IPD-A manifest reports "I/O data not captured for this run".
- Import-isolation test (the key safety pin, above).
- `NO_COLOR` respected. Full suite green.

## Spec / documentation sync

`docs/cli.md`, `docs/research-use.md` (or new `docs/hpc.md`), `CHANGELOG.md`. Run
`/assess documentation` after implementation.

## Explicitly out of scope

- **Import-time nudge is DROPPED.** No environment check runs inside `import pubrun`. All
  warnings live in the explicit `self-check`/`inspect` commands only. (This was the only
  design element that touched the host-script process; removed by decision.)
- Auto-fixing the environment. Report + suggest only.

## Open questions (maintainer)

1. Final module name (`report/checks.py` vs `report/diagnostics.py` — note a
   `report/diagnostics.py` already exists; pick a non-colliding name).
2. Should `inspect` and `self-check` share one implementation with a `--live/--from-run`
   flag, or stay two commands? (Recommend two commands, one shared findings module.)
3. Add a `docs/hpc.md`, or fold HPC guidance into `docs/research-use.md`?

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.
