# IPD-C: easy benchmark runner + HPC auto-submit + opt-in manual result sharing

- Date: 2026-07-06
- Concern: usability / community data collection. Make it trivial for a user to run the
  benchmark suite, auto-detect an HPC (Slurm) environment and offer to submit to compute
  nodes, and then guide them to share results back — to build the multi-system dataset the
  JOSS paper needs.
- Scope: a new friendly entry point (a `pubrun bench` CLI command and/or a wrapper script)
  over the EXISTING `benchmarks/` harness + Slurm scripts; no change to `src/pubrun/`
  runtime behavior. The `[bench]` extra stays dev-only.
- Status: EXECUTED (2026-07-06). `pubrun bench` + redaction + contribute guidance
  implemented, tested (9 new tests), documented. 738 passed / 2 skipped (only the known
  SIGPIPE flake fails, passes in isolation). Built on IPD-A schema/3. Remaining OPERATOR
  step: create the public `pubrun-benchmarks` repo and replace the placeholder URL. See the
  execution record at the end.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

Today running the benchmarks requires knowing about `benchmarks/harness.py`,
`submit_bench.sh`, and a set of `PUBRUN_*` env vars (`run_bench.sbatch:26-30`,
`submit_bench.sh` node selection at `:30-64`). That is fine for the maintainer but too
much friction for a researcher who would otherwise contribute a data point. We want:
(1) one obvious command to run the suite locally; (2) automatic detection of Slurm (and
room for other schedulers) with an offer to submit to compute nodes; (3) a clear,
privacy-respecting path to send results back.

## Project conventions discovered (Step 0)

- Principles: zero runtime deps, KISS, honest docs, never intrude on host script.
- Existing benchmark tooling: `benchmarks/harness.py` (stdlib-only measurement core),
  `benchmarks/run_bench.sbatch`, `benchmarks/submit_bench.sh` (random idle node via
  `sinfo -h -t idle`), results in `benchmarks/results/<host>-<ts>.json`. The `[bench]`
  extra (matplotlib/pytest-benchmark) is dev-only and gated.
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Design decisions (agreed with maintainer)

- **Result sharing = MANUAL.** pubrun prints the results path and instructs the user to
  attach them to a GitHub issue/PR (URL provided). **No automatic transmission**, no
  server, no network dependency. Fully transparent; the user controls exactly what is
  shared. (Maintainer chose "Manual: print instructions to open a GitHub issue/PR".)
- **Measurement core stays stdlib-only**; the friendly runner adds no runtime dep. If it
  needs matplotlib for a summary chart, that stays behind the existing `[bench]` extra and
  degrades gracefully when absent.
- **HPC detection is best-effort and never coercive** — detect Slurm via `sinfo`/`sbatch`
  on PATH and `SLURM_*` env; if found, OFFER to submit (with a shown command) and, on
  confirmation, actually submit via the existing `submit_bench.sh`. Never auto-submit
  without explicit user confirmation. Architect the seam for other schedulers (PBS/LSF)
  but implement only Slurm now.

## Proposed changes

1. **New `pubrun bench` subcommand** (thin, friendly front-end over `benchmarks/harness.py`):
   - `pubrun bench` → run the suite locally with sensible defaults (the harness's existing
     two-pass design), print the results file path.
   - Auto-detects Slurm; if detected and not already on a compute node, prints the exact
     `submit_bench.sh` command and asks to submit (respects a `--yes`/non-interactive flag;
     never submits silently). Passes through partition/exclude/args.
   - On completion, prints the **manual share** guidance: results path + the GitHub issue/PR
     URL + a one-line summary of what the JSON contains (so users know what they'd share).
   - `--local` forces local even on HPC; `--submit` forces submit; `--json`/quiet options.
   - NOTE: the harness lives under `benchmarks/` which ships in the repo but may not be on
     an installed user's path — resolve its location robustly (packaged data vs repo
     checkout) or document that `pubrun bench` requires a source checkout. (Open question.)
2. **Small refactor of `submit_bench.sh`/`run_bench.sbatch`** only as needed to be callable
   from the new command with explicit args instead of only `PUBRUN_*` env vars (keep env
   vars working for backward compat).
3. **A `CONTRIBUTING`-style note / `benchmarks/README.md` section**: "How to contribute a
   benchmark data point" — run `pubrun bench`, then attach the **redacted** results JSON to
   an issue at the given URL. State plainly what the JSON contains so contributors give
   informed consent.
4. **Redaction for sharing — DECIDED (maintainer 2026-07-06): redact by default for the
   SHARE artifact; `--no-redact` to opt into full detail.** `pubrun bench` produces the full
   JSON locally (for the user's own analysis) AND, for sharing, a redacted copy for a
   **public** repo. Redaction is deterministic and documented.
   - **COMPLETE field list (plan-review re-pass, MEDIUM — "and any other identifier fields"
     was too vague for a control feeding a PUBLIC repo).** Home paths leak into MANY string
     values, not just `sys_path`. Redact/mask ALL of:
     - `machine.host.hostname` and any `hostname` field;
     - the OS username wherever it appears (`process.user.username` if present, and as a
       substring of any path);
     - **every path that can contain the home dir**: `python.executable`,
       `python.prefix`, `python.base_prefix`, `python.virtual_env`, every entry of
       `python.sys_path`, `python_executable`, `machine.filesystem.*` mount points/paths
       (from IPD-A), and the harness workdir/results paths.
   - **Belt-and-suspenders:** after field-level redaction, run a final pass that replaces any
     remaining occurrence of the current user's home-dir prefix and username **anywhere** in
     the JSON (deep string scan) with a placeholder, so an un-enumerated field cannot leak.
   - Document exactly what is masked and what is preserved (CPU model, timings, versions,
     fstype classification, Slurm partition — the analysis-relevant, non-identifying data).
   - **Residual re-identification caveat (honest disclosure):** even redacted, CPU/GPU model
     + core count + a distinctive Slurm partition name can be re-identifying in a small
     group. The contribute guidance must say so plainly rather than promising anonymity.
5. **Identity via GitHub, not via the data (maintainer's design).** The redacted JSON
   carries NO PII, yet the maintainer can still follow up with a submitter because the
   submission is an issue/PR opened from the submitter's **own GitHub account** — GitHub is
   the authenticated contact channel. Fully anonymous submission remains possible (redacted
   JSON + throwaway account). This needs **no server and no contact database** (honors the
   "manual, no infrastructure" decision). The contribute guidance must explain this so users
   understand the privacy model.
6. **Collection home = a separate public `pubrun-benchmarks` repo (DECIDED).** The harness
   CODE stays in the main repo (`benchmarks/`, for reproducibility/version-matching), but
   submitted result JSONs + the issue template + aggregation live in a NEW public
   `pubrun-benchmarks` repo so the main repo stays code-only. `pubrun bench`'s share
   guidance points at that repo's issue template. **Operator step (maintainer):** create the
   `pubrun-benchmarks` repo; the executor wires the URL/template reference but cannot create
   the repo. Until it exists, use a clearly-marked placeholder URL + follow-up (never a fake
   live URL).
7. **Analysis-critical fields confirmed present + gaps closed by IPD-A.** Verified
   (`benchmarks/harness.py:98-99,107-117`): the result JSON already records `pubrun_version`,
   `pubrun_commit` (package), and repo `git_commit`, plus host/hardware/python,
   `python_executable`, `platform`, iterations/warmup/passes, and timestamp. The fields
   needed for cross-machine comparison that are NOT yet captured — per-pass dynamic state,
   filesystem type (the NFS signal), and Slurm allocation context — are ADDED by IPD-A
   (schema/3). This IPD's share/analysis flow DEPENDS on IPD-A's schema/3; sequence C after
   A. The redaction list (change 4) must be kept in sync with schema/3's fields.

## Anti-regression / invariants

- **Never auto-submit or auto-transmit.** Submission and sharing are both explicit,
  user-confirmed actions. Test that non-interactive default does NOT submit without `--yes`.
- **No new runtime dependency**; `pubrun bench` works with stdlib. Chart summary optional
  via `[bench]`, graceful when absent.
- **Existing scripts keep working** with their `PUBRUN_*` env-var interface (backward compat
  test / documented).
- **Honest data disclosure.** The share guidance accurately lists every field the result
  JSON contains (cross-check against IPD-A's schema/3), and states plainly which fields the
  default redaction masks vs. leaves.
- **Redaction actually removes PII (DEEP scan).** A test recursively walks the entire
  redacted JSON and asserts NO value contains the hostname, the OS username, or the home-dir
  prefix substring — not merely that the named fields are masked (the belt-and-suspenders
  pass must catch un-enumerated leaks). `--no-redact` preserves them. Analysis-relevant
  fields (timings, CPU model, fstype, versions, Slurm partition) survive redaction.
- **Never crash on a locked-down node** (no scheduler, no network) — degrade to local run +
  print-path, with a clear message.
- **No shell injection when invoking Slurm (plan-review re-pass, MEDIUM/security).** `pubrun
  bench` must invoke `submit_bench.sh`/`sbatch` via `subprocess` with an **argv list, never
  `shell=True`** and never by interpolating user values (partition, exclude regex, extra
  args) into a shell string. Note the existing `submit_bench.sh:48` sets
  `PUBRUN_BENCH_ARGS="${*:-}"` which `run_bench.sbatch` later word-splits unquoted into the
  harness argv — so the friendly command must pass each arg as a separate argv element and
  document that partition/exclude values are validated (e.g. restrict to a safe charset)
  before being forwarded. A test passes an arg containing shell metacharacters and asserts
  it is treated as a literal argument, not executed.

## Required tests / validation

- CLI: `pubrun bench --local` runs the harness and prints a results path (smoke; may be
  marked slow / few iterations in CI).
- Slurm detection unit test: given a fake PATH/env with/without `sbatch`/`SLURM_*`, the
  command reports detected/not-detected and, when detected, prints (does not execute) the
  submit command unless `--yes/--submit`.
- Non-interactive safety: default without `--yes` never submits.
- Share-guidance text lists the actual JSON fields (kept in sync with schema).
- Redaction test (above): redacted artifact has no hostname/username/home-path; `--no-redact`
  keeps them; analysis fields survive redaction.
- Full suite green.

## Spec / documentation sync

`docs/cli.md` (`pubrun bench`), `benchmarks/README.md`, `docs/performance.md`,
`CHANGELOG.md`, and the contribute-a-data-point guidance. Run `/assess documentation`.

## Open questions — ANSWERED by maintainer 2026-07-06

1. `pubrun bench` CLI command vs wrapper → **prefer the CLI command IF harness-location
   resolves cleanly for a pip-installed user** (package the harness as data OR require a
   source checkout); fall back to a wrapper script only if resolution is messy. Decide with
   evidence at execution time (check packaging first).
2. Submission channel → **a dedicated issue template in the new `pubrun-benchmarks` repo**
   (structured `benchmark-result` template). (Repo creation is an operator step; see change 6.)
3. PBS/LSF → **Slurm-only now, seam documented** for later schedulers.
4. Redaction → **redact by default for the share artifact** (mask hostname, username,
   home-paths in `sys_path`); `--no-redact` for full detail; identity carried by the
   submitter's GitHub account, not the data (changes 4–5). No server/contact DB.

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-06)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verdict: **APPROVE WITH
REVISIONS APPLIED**. Verified the harness already records `pubrun_version`/`pubrun_commit`
(`harness.py:98-99`) + repo `git_commit` (`harness.py:107-117`); the cross-machine fields
it LACKS (per-pass dynamic state, fstype, Slurm context) are added by IPD-A/schema-3, so C
depends on A. Maintainer answers folded in: redact-by-default share artifact (mask
hostname/username/home-paths) with `--no-redact`; identity via the submitter's GitHub
account (no server/contact DB); NEW public `pubrun-benchmarks` repo as the collection home
(harness code stays in main repo); dedicated issue template; Slurm-only now (seam
documented); `pubrun bench` CLI iff harness-location resolves cleanly, else wrapper.
Operator step: create `pubrun-benchmarks`; use a placeholder URL + follow-up until then
(never a fake live URL). Sequence: after IPD-A.

**Stricter re-pass (2026-07-06), findings fixed:**
- **C-R1 (MEDIUM, privacy):** the redaction list was too vague ("and any other identifier
  fields") for a control feeding a PUBLIC repo. Enumerated ALL home-path-leaking fields
  (`python.executable/prefix/base_prefix/virtual_env/sys_path`, `machine.filesystem.*`,
  workdir/results paths, username, hostname) + a belt-and-suspenders deep-scan pass + a
  recursive test + an honest residual re-identification caveat.
- **C-R2 (MEDIUM, security):** invoking `submit_bench.sh`/`sbatch` must use an argv list
  (never `shell=True`/string interpolation); `submit_bench.sh:48` word-splits
  `PUBRUN_BENCH_ARGS` unquoted, so forwarded partition/exclude/args must be passed as
  discrete argv + charset-validated. Added a metacharacter-as-literal test.

## Execution record (2026-07-06)

Executed by opencode after human approval.

- **`pubrun bench` (`__main__.py` `_run_bench` + subparser/dispatch):** friendly front-end
  over `benchmarks/harness.py`. Locates the harness in a source checkout (`_find_bench_harness`
  tries the installed package's repo root, then cwd) and errors CLEARLY with the clone command
  if absent — the benchmark tooling is intentionally NOT packaged (verified: `pyproject.toml`
  wheel = `src/pubrun` + COMMIT only), keeping installs zero-footprint. Runs locally by
  default; if Slurm is detected (`SLURM_JOB_ID` or `sbatch` on PATH) and not on a compute
  node, it prints the exact submit command and PROMPTS (never submits without `--submit`/
  `--yes`/an interactive "y"). Slurm invocation uses an **argv list, never `shell=True`**
  (the C-R2 security finding); args passed as discrete argv.
- **Redaction (`harness.py` `redact_result` + `--redacted-out`):** default local run writes
  BOTH the full JSON and a `.redacted.json` share copy. Field-level redaction masks
  hostname/username/all home-path fields (`executable`/`prefix`/`base_prefix`/`virtual_env`/
  `sys_path`/`path`/`mount_point`/run+output dirs), THEN a belt-and-suspenders deep scrub
  removes the home-dir prefix and username anywhere they leaked into un-enumerated strings
  (the C-R1 finding). Analysis fields (CPU/GPU model, timings, versions, fstype, Slurm
  partition) are preserved. `--no-redact` opts out.
- **Share guidance:** prints the redacted path, what is masked vs preserved, the honest
  residual re-identification caveat, and the (placeholder) `pubrun-benchmarks` issue URL,
  explaining the GitHub-account-as-contact-channel privacy model. No server, no contact DB.
- **`benchmarks/README.md`:** rewrote the "Contributing a result" section for `pubrun bench`
  + redaction + the pubrun-benchmarks repo. `submit_bench.sh`/`run_bench.sbatch` env-var
  interface unchanged (backward compatible; `_run_bench` sets `PUBRUN_REPO`/`PUBRUN_PY`).
- **Docs:** `docs/cli.md` (`bench` entry), `CHANGELOG.md` `[Unreleased] → Added`.
- **Tests (`tests/test_bench_command.py`, 9, all green):** redaction removes ALL PII incl.
  un-enumerated fields (deep scan) + preserves analysis fields + does not mutate input;
  harness resolution in a checkout + clean error without one; **Slurm detected but NOT
  submitted on an interactive "no"** (security-critical); Slurm env detection; bench --help;
  a minimal local `--json` run writing a verified-clean redacted copy. Full suite: **738
  passed**, 2 skipped; lone failure is the known pre-existing SIGPIPE flake (passes in
  isolation).

### REMAINING — operator step (maintainer)

Create the public **`pubrun-benchmarks`** repository (with a `benchmark-result` issue
template), then replace the placeholder `_BENCH_SUBMIT_URL` in `src/pubrun/__main__.py`
(grep `pubrun-benchmarks`) and the `benchmarks/README.md` reference with the real URL. Until
then the command prints a clearly-labeled "pending: create this repo" placeholder — never a
fake live URL.

### Deferred (unchanged)

PBS/LSF schedulers: Slurm-only now; the detection seam is a single helper (`_slurm_available`)
that a future scheduler can extend. Disk-throughput probe (from IPD-A) remains a possible
follow-up.
