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
5. **(Optional, coordinate with IPD-A) close the two manifest ambiguities.** To make inspect
   able to say *definitively* "subprocess tracking was OFF" and "file-open provenance was
   OFF", add two tiny boolean flags to the manifest at assembly time
   (`tracker.py:576-632`): e.g. `capture.subprocesses_enabled` (from
   `self._spying_subprocesses`, `tracker.py:316`) and `capture.file_provenance_available`
   (whether the `pubrun.open` API path was reachable / any proxy created). Additive, tiny,
   removes the ambiguity above. If not added, inspect degrades to the honest "either
   disabled or unused" phrasing. (Open question #5.)
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
4. **Resolved-config source.** To report exact settings (sample interval, packages mode,
   per-category depth), inspect must read the sibling `config.resolved.json`
   (`writer.py:69-70`) since they are NOT in the manifest. Should inspect read it when
   present (and degrade gracefully when absent/moved), or should we rely only on the
   manifest's coarse `capture_state` sentinels? (Recommend: read `config.resolved.json`
   opportunistically for richer detail, fall back to manifest sentinels.)
5. **Close the two ambiguities?** Add tiny additive manifest flags
   (`capture.subprocesses_enabled`, `capture.file_provenance_available`) so inspect can say
   definitively "off" rather than "off or unused"? (Recommend YES — trivial, and it makes
   the completeness report unambiguous. Coordinate with IPD-A which is already touching
   `tracker.py` manifest assembly.) The flag name for open()-provenance is subtle since it
   is not a config switch — see IPD-E; `file_provenance_available` should mean "a run was
   active and `pubrun.open` was importable", not "the user used it".
6. **Default terseness knob.** Is a single summary line + one nudge the right default, or do
   you want a 2–3 line "captured / not captured" mini-table by default with
   `--show-suggestions` for the how-to + caveats? (Recommend: 1 summary line + nudge;
   keep it minimal.)

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.
