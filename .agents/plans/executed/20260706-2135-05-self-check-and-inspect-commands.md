# IPD-B: `pubrun self-check` (live env) and `pubrun inspect` (post-hoc run diagnosis)

- Date: 2026-07-06
- Concern: usability / diagnosability. Two explicit, report-only commands that help users
  spot performance/config pitfalls (like installing pubrun on a slow NFS mount) both
  before/around a run (`self-check`) and after the fact from a completed run's manifest
  (`inspect`). `inspect` additionally performs a **capture-completeness assessment**: it
  tells the user which provenance features were NOT captured/enabled (e.g. resource
  `scope != "tree"`, no subprocess/file-`open()` provenance), why that limits insight, and
  how to enable them next time — with honest performance caveats, behind a terse default +
  `--show-suggestions` expansion to avoid a wall of text.
- Scope: `src/pubrun/__main__.py` (two new subcommands) + a new report/check module. Both
  are CLI-only and MUST NOT be on the `import pubrun` code path. No new runtime dependency.
- Status: EXECUTED (2026-07-06). Both commands implemented, tested (19 new tests incl. the
  import-isolation pin and the ambiguity-honesty test), documented (new `docs/hpc.md` + nav).
  729 passed / 2 skipped (only the known SIGPIPE flake fails, passes in isolation). Built on
  IPD-A's manifest fields/flags. See the execution record at the end.
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
  reads a completed run's manifest). **Two commands, one shared findings module** — NOT a
  single command with a `--live/--from-run` flag.
- **They are OVERLAPPING, not nested (maintainer's Venn observation, 2026-07-06).** Neither
  is a subset of the other:
  - **`self-check` only:** "is THIS machine well-configured RIGHT NOW?" — pubrun install on
    NFS, current free RAM, current load, config file validity, output dir writable, git
    availability, Python version. None of this needs (or reads) a run manifest.
  - **`inspect` only:** what a COMPLETED run captured — the capture-completeness assessment,
    the recorded-at-runtime I/O/RAM/load, the different-host banner. Needs a manifest;
    self-check has none.
  - **Overlap (the shared module):** filesystem-type / is-network-FS classification, RAM/
    load interpretation thresholds, severity/marker formatting, `NO_COLOR` handling — pure
    functions both commands call. The executor must NOT implement one command as a subset
    of the other; build the shared findings module + two thin command-specific layers.
- **Shared module name → `src/pubrun/report/checks.py`** (non-colliding with the existing
  `report/diagnostics.py`; note the package is `report/`, singular).
- **Report-only.** Neither command mutates the environment or any run. No auto-fixing.
- **CLI-only, off the import path.** The check logic lives in `report/checks.py`, imported
  by `__main__.py`, NOT by `pubrun/__init__.py`. A test asserts `import pubrun` does not
  import `pubrun.report.checks` (keeps it impossible to affect the host script).
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

1. **New module `src/pubrun/report/checks.py`**: pure functions that produce a list of
   findings `{severity, code, message, suggestion}` from (a) the live environment and (b) a
   loaded manifest. No printing here — returns data so it is unit-testable. Reuses IPD-A's
   `capture/filesystem.py`, memory, and load helpers (or, if IPD-A not yet landed, a minimal
   local `/proc` reader; consolidate later).
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
4. **Capture-completeness assessment (maintainer's ask).** `inspect` must report not only
   what the run captured but **what it could NOT tell you and why**, then offer how to
   enable it next time — WITH an honest performance caveat. This turns `inspect` into a
   teaching tool for provenance completeness. Concretely, for a completed run it detects
   and reports which capture features were on/off:
   - **Detectable from the manifest alone** (verified 2026-07-06):
     - resource **scope** — `manifest["resources"]["scope"]` (`resources.py:327`); flag
       when `scope != "tree"`: "process-tree resources were NOT captured (only the main
       process). Set `[capture.resources] scope = \"tree\"` to sum RSS/CPU across children."
     - resource **depth on/off**, hardware, packages, git, signals, event stream —
       each via `capture_state.status == "suppressed"` (`tracker.py:600-623`).
     - console tee + mode — `manifest["console"]["capture_mode"]` (`console.py:274`).
     - import mode + behavior flags — `manifest["pubrun_imports"]["selected_mode"]`
       (`_bootstrap.py:91-92`), which reveals whether `patch_subprocesses`/`patch_console`
       were even permitted.
   - **NOT reliably detectable from the manifest today** (honesty requirement — inspect
     must NOT claim a feature was off when it merely produced no records):
     - **subprocess tracking** — no enabled flag; empty `manifest["subprocesses"]`
       (`tracker.py:596`) is ambiguous (enabled-but-idle vs disabled). A non-empty list
       proves it was on.
     - **file `open()` provenance** — no flag; empty `manifest["data_files"]`
       (`tracker.py:626`) is ambiguous (user never called `pubrun.open()` vs called on
       nothing). Non-empty proves it was used. inspect must phrase these as "no
       subprocess/file-I/O provenance was recorded — either it was disabled or nothing was
       captured; note pubrun does NOT patch `open()`/subprocess globally, so file reads/
       writes are only recorded if you call `pubrun.open()` / `pubrun.subprocess`."
     - **exact resolved config** (sample interval, packages mode string, per-category
       depth) — lives in the sibling `config.resolved.json` (`writer.py:69-70`), NOT the
       manifest. See open question #4 for how inspect resolves this.
   - **Anti-wall-of-text (maintainer's ask):** the DEFAULT output is terse — a one-line
     summary plus a single nudge, e.g.:
     `Not all provenance was captured (process-scope only; no subprocess/file-I/O record).`
     `Run \`pubrun inspect <run> --show-suggestions\` for how to capture more (and the perf trade-offs).`
     `--show-suggestions` (or `--verbose`/`-v`) expands into the per-feature findings with
     the exact config keys to set AND the honest performance caveat ("…may add overhead;
     see `docs/performance.md`"). `--json` always includes the full structured findings
     regardless (machines don't have a wall-of-text problem).
5. **Close the two manifest ambiguities — DECIDED YES (maintainer 2026-07-06).** Add two
   tiny additive boolean flags to the manifest at assembly time (`tracker.py:576-632`):
   `capture.subprocesses_enabled` (from `self._spying_subprocesses`, `tracker.py:316`) and
   `capture.file_provenance_available` (a run was active and `pubrun.open` was importable —
   NOT "the user used it"; see IPD-E note). **These flags are added in IPD-A** (which
   already edits manifest assembly) to avoid two IPDs touching the same dict; this IPD
   CONSUMES them. `inspect` then reports definitively "subprocess tracking was OFF" rather
   than the ambiguous phrasing. For runs predating the flags (older manifests), inspect
   falls back to the honest "disabled OR not used" wording. A test covers both the
   flag-present (definitive) and flag-absent (ambiguous) manifests.
6. **Docs:** `docs/cli.md` entries for both; a short "diagnosing performance / HPC" section
   in `docs/research-use.md` or a new `docs/hpc.md`; and a "capture completeness / how to
   capture more" subsection cross-linked from `docs/configuration.md` and
   `docs/performance.md`.

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
- **Honesty about the unknown.** inspect must NEVER assert a feature was "off" when the
  manifest only shows an absence of records (subprocess/file-I/O). It must use the
  ambiguous phrasing ("disabled OR not used") unless the optional manifest flags (change 5)
  make it definitive. A test seeds an empty-`subprocesses` / empty-`data_files` manifest and
  asserts inspect does NOT claim the feature was disabled.
- **Terse by default.** Default `inspect` output stays short (summary + one nudge); the
  wall-of-text lives only behind `--show-suggestions`. A test asserts default output is
  under a small line budget and that `--show-suggestions` expands it.
- **Performance honesty.** Every "turn this on" suggestion is paired with a truthful
  overhead caveat; no suggestion implies "free."

## Required tests / validation

- Unit: findings functions given synthetic env / synthetic manifest produce expected
  finding codes (NFS install, low RAM, high load, different-host, old-manifest-no-data).
- CLI: `self-check` exits 0 normally, non-zero under `--strict` with a seeded warning;
  `--json` well-formed.
- CLI: `inspect` on a same-host manifest (no banner) vs a different-host manifest (banner
  present); on a pre-IPD-A manifest reports "I/O data not captured for this run".
- Capture-completeness: synthetic manifests exercise each detectable feature —
  `scope="process"` → "process-tree not captured" finding; `scope="tree"` → no such
  finding; console `capture_mode="off"` → console-off finding; import mode `nopatch` →
  "patching disabled" finding; each `capture_state="suppressed"` section → its off finding.
- Ambiguity honesty: empty `subprocesses`/`data_files` → "disabled OR not used" phrasing,
  NOT a definitive "off" (unless change 5's flags present, then definitive).
- Terse-default vs `--show-suggestions`: default under the line budget; expansion includes
  the exact config key AND a perf caveat for each suggestion.
- Import-isolation test (the key safety pin, above).
- `NO_COLOR` respected. Full suite green.

## Spec / documentation sync

`docs/cli.md`, **new `docs/hpc.md`** (decided — dedicated HPC/perf/diagnosis guidance,
not crammed into `research-use.md`; add it to the doc nav footer used across the docs),
`CHANGELOG.md`. Run `/assess documentation` after implementation.

## Explicitly out of scope

- **Import-time nudge is DROPPED.** No environment check runs inside `import pubrun`. All
  warnings live in the explicit `self-check`/`inspect` commands only. (This was the only
  design element that touched the host-script process; removed by decision.)
- Auto-fixing the environment. Report + suggest only.

## Open questions — ANSWERED by maintainer 2026-07-06

1. Module name → **`src/pubrun/report/checks.py`** (non-colliding with `report/diagnostics.py`).
2. One command with a flag, or two? → **Two commands, one shared findings module** (they
   overlap but neither is a subset — see the Venn note in Design decisions).
3. `docs/hpc.md` vs fold into `research-use.md` → **new `docs/hpc.md`**.
4. Resolved-config source → **read `config.resolved.json` opportunistically** for exact
   settings (sample interval, packages mode, per-category depth) when it sits next to the
   manifest; **fall back gracefully** to the manifest's coarse `capture_state` sentinels
   when absent/moved.
5. Close the two ambiguities → **YES, add the two additive manifest flags** (in IPD-A;
   consumed here). `file_provenance_available` means "a run was active and `pubrun.open`
   was importable", NOT "the user used it".
6. Default terseness → **1 summary line + one nudge** by default; full findings behind
   `--show-suggestions`; `--json` always full.

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-06)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verdict: **APPROVE WITH
REVISIONS APPLIED**. Manifest-detectability claims re-verified (resource scope
`resources.py:327`; console mode `console.py:274`; import mode `_bootstrap.py:91-92`;
ambiguous empty `subprocesses`/`data_files`; `config.resolved.json` at `writer.py:69,100`).
Maintainer answers folded in: `report/checks.py` module name; TWO commands (not a flag)
with the explicit OVERLAPPING-not-nested Venn note; add + consume the two manifest flags
(added in IPD-A); read `config.resolved.json` opportunistically; new `docs/hpc.md`; terse
1-line default + `--show-suggestions`. Honesty guardrail kept: never claim "off" when the
manifest only shows "no records" unless the flags make it definitive. Depends on IPD-A.

**Stricter re-pass (2026-07-06):** VERIFIED the CLI-only isolation empirically — `import
pubrun` pulls in ZERO `report` modules (`report/__init__.py` does not eagerly import
submodules), so the `report/checks.py` placement and the import-isolation test are sound.
No new findings; the never-claim-"off"-when-only-absent honesty guardrail is the key
correctness property and is well-specified.

## Execution record (2026-07-06)

Executed by opencode after human approval.

- **`src/pubrun/report/checks.py` (NEW):** pure, printing-free findings functions.
  `live_findings()` (self-check: network-FS on install/output/tmpdir, low RAM, high load,
  + install health: config validity, output-dir writability, git availability, Python
  version); `manifest_findings(manifest, current_hostname)` (inspect: different-host banner,
  recorded network-FS, capture-completeness). `summarize()` for the terse line. Never raises.
- **`__main__.py`:** `_run_self_check` + `_run_inspect` + shared `_emit_findings`
  (NO_COLOR-respecting textual `[warn]`/`[info]` markers, optional non-DIM yellow/cyan; terse
  by default; `--show-suggestions` expands with honest perf caveats; `--json` always full).
  Two subparsers registered (`self-check`, `inspect`); `inspect` reuses
  `_add_run_filter_args(include_limit=False)` + `_get_manifest_path` for run selection.
  The different-host banner is always shown (boxed), never hidden behind `--show-suggestions`.
- **Honesty guardrail (verified by test):** with the IPD-A flag `capture.subprocesses_enabled`
  present, inspect says definitively "subprocess tracking was OFF"; on older manifests lacking
  the flag it says the honest "either disabled or nothing was spawned — cannot be determined",
  never a false "off". File-I/O finding explains pubrun does not patch `open()` globally.
- **Import isolation (verified by test):** `import pubrun` does NOT import
  `pubrun.report.checks` (empty `sys.modules` check) — the diagnostics can never touch a host
  script.
- **Docs:** `docs/cli.md` (`self-check` + `inspect` with the honesty note); **new
  `docs/hpc.md`** (network-FS pitfall, the two commands, different-system banner,
  capture-completeness); `[HPC](hpc.md)` added to the nav footer across all docs + README;
  `CHANGELOG.md` `[Unreleased] → Added`.
- **Tests (`tests/test_checks_commands.py`, 19 new, all green):** import-isolation pin;
  manifest findings (banner fires on mismatch / silent on same host; process-scope flagged,
  tree not; definitive-off with flag vs honest-unknown without; no-file-provenance mentions
  `pubrun.open`; resources-off; never-raises on garbage); live findings shape; self-check CLI
  (exit 0, `--json` well-formed, NO_COLOR no ANSI); inspect CLI (terse default,
  `--show-suggestions` expands, `--json` full, no-runs errors). Also added `self-check`/
  `inspect` to the subcommand-help-examples test. Full suite: **729 passed**, 2 skipped; lone
  failure is the known pre-existing SIGPIPE flake (passes in isolation).

**Dropped as planned:** the import-time nudge (no environment check inside `import pubrun`).
