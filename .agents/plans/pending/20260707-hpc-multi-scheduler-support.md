# IPD: HPC multi-scheduler detection + submission + login-node benchmark suggestion

- Date: 2026-07-07
- Concern: usability / reach. `pubrun bench` today detects and offers submission only for
  **Slurm**. Broaden HPC support so researchers on PBS/Torque, LSF, and SGE clusters get the
  same low-friction "detected your scheduler — submit the benchmark to a compute node?" flow,
  and so `pubrun self-check` gently suggests running a compute-node benchmark when it notices
  it is on an HPC login node (where laptop-style numbers would be misleading).
- Scope: `src/pubrun/__main__.py` (generalize the `_slurm_available`/`_on_compute_node` seam
  into a scheduler-abstraction; submission dispatch), `benchmarks/` submit scripts (add
  PBS/LSF/SGE batch scripts mirroring `submit_bench.sh`/`run_bench.sbatch`),
  `src/pubrun/report/checks.py` (login-node suggestion), docs, tests. **No change to
  `import pubrun` runtime behavior. No new runtime dependency. Never auto-submit.**
- Status: PENDING (proposal only; human approval required; NOT auto-executed).
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Depends on / relates to: IPD-C (`20260706-easy-benchmark-and-hpc-submit.md`, the Slurm
  seam this generalizes) and `20260707-benchmark-data-quality-and-fs-health.md` (the fs-health
  warnings that pair naturally with an HPC login-node context). Sequence AFTER those two.

## Problem / motivation

IPD-C intentionally implemented **Slurm only** and left the detection as a single helper
(`_slurm_available` at `__main__.py:879`, `_on_compute_node` at `:884`) explicitly so a
future scheduler could extend it. Its execution record lists "PBS/LSF schedulers: Slurm-only
now; the detection seam is a single helper that a future scheduler can extend" as deferred.
This IPD is that follow-up.

Two gaps:
1. **Non-Slurm clusters get nothing.** A researcher on a PBS/Torque, LSF, or SGE cluster runs
   `pubrun bench` and it just runs locally (often on a login node — the worst place to
   benchmark: shared, throttled, wrong hardware). They get no offer to submit to a compute
   node and no warning that their numbers are unrepresentative.
2. **No proactive nudge.** Even on Slurm, the suggestion only appears at `bench` time. Someone
   running `pubrun self-check` on a login node is not told "you look like you're on an HPC
   login node; benchmark on a compute node for representative numbers."

## Project conventions discovered (Step 0)

- Principles: zero runtime deps, KISS, honest docs, never intrude, degrade gracefully,
  **never auto-submit** (IPD-C invariant — submission is always explicit + user-confirmed).
- Current Slurm seam (`__main__.py`):
  - `_slurm_available()` (`:879`): `SLURM_JOB_ID` env OR `sbatch` on PATH.
  - `_on_compute_node()` (`:884`): `SLURM_JOB_ID` present.
  - `_run_bench` (`:903`): `want_submit = submit or (not local and _slurm_available() and not
    _on_compute_node())`; prints exact submit command; prompts; submits via
    `benchmarks/submit_bench.sh` using an **argv list, never `shell=True`** (`:922-946`);
    sets `PUBRUN_REPO`/`PUBRUN_PY` env for the script.
- Existing batch scripts: `benchmarks/submit_bench.sh` (picks a RANDOM idle CPU node via
  `sinfo -h -t idle`, `sbatch --nodelist`), `benchmarks/run_bench.sbatch` (the job body:
  reads `PUBRUN_*`, runs the harness). Both use the `PUBRUN_*` env-var interface.
- `report/checks.py`: `_finding(severity, code, message, suggestion)`; `live_findings()`
  (`:128`) is the `self-check` entry point; CLI-only (not imported by `import pubrun`).
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Scheduler reference (detection + submit + compute-node signals)

Detection is best-effort, cheap, and never coercive — env vars + a binary on PATH. No
network calls, no scheduler queries at detection time (querying, e.g. `sinfo`, happens only
inside a submit script AFTER the user confirms).

| Scheduler | Submit bin (on PATH) | "am I on a compute node?" env | Distinctive login-side env | Node/host env in job |
| :--- | :--- | :--- | :--- | :--- |
| **Slurm** | `sbatch` (+ `sinfo`) | `SLURM_JOB_ID` | `SLURM_CLUSTER_NAME`, `sinfo`/`squeue` present | `SLURMD_NODENAME` |
| **PBS/Torque / OpenPBS** | `qsub` (+ `pbsnodes`) | `PBS_JOBID` / `PBS_ENVIRONMENT=PBS_BATCH` | `qstat`/`pbsnodes` present | `PBS_NODEFILE`, `PBS_O_HOST` |
| **LSF** | `bsub` | `LSB_JOBID` / `LSB_JOBINDEX` | `bqueues`/`bhosts` present, `LSF_ENVDIR` | `LSB_HOSTS`, `LSB_MCPU_HOSTS` |
| **SGE / Grid Engine (incl. UGE/OGE)** | `qsub` (+ `qhost`) | `JOB_ID` + `SGE_TASK_ID`/`PE_HOSTFILE` | `SGE_ROOT` set, `qhost`/`qconf` present | `PE_HOSTFILE`, `SGE_O_HOST` |

**Ambiguity to handle honestly:** PBS and SGE **both** use `qsub`. So `qsub`-on-PATH alone is
insufficient to name the scheduler. Disambiguate by env/root markers (`PBS_*`/`PBS_O_*` and
`pbsnodes` vs `SGE_ROOT`/`SGE_*` and `qhost`). If genuinely ambiguous, report
"PBS-or-SGE-style (`qsub`)" and pick the batch script by the strongest marker, never guess
silently.

## Design decisions (proposed; confirm in plan-review)

- **A small scheduler-abstraction seam**, not scattered `if`s. Introduce a lightweight list of
  scheduler descriptors, each with: `name`, `detect() -> (available: bool, on_compute_node:
  bool)`, `submit_script` path, and the env-var interface it expects. `_run_bench` iterates:
  first *available and not-on-compute-node* scheduler wins; if none, run local.
- **Preserve every IPD-C invariant per scheduler:** print the exact submit command; prompt;
  never submit without `--submit`/`--yes`/interactive "y"; argv-list, never `shell=True`;
  charset-validate any forwarded partition/queue/args.
- **`--scheduler {auto,slurm,pbs,lsf,sge,local}`** override (default `auto`) so a user on an
  odd/ambiguous setup can force the right one (or force `local`).
- **New batch scripts mirror the Slurm pair**, sharing the `PUBRUN_*` env interface and the
  same harness invocation, so `run_bench.*` bodies are near-identical and only the scheduler
  directives/submit mechanics differ. Keep them minimal; document that they are starting
  points users may need to adapt to site policy (queues, accounts, walltime).
- **`self-check` HPC login-node suggestion:** if a scheduler is detected AND we are NOT on a
  compute node, emit an `INFO`/`WARN` finding suggesting `pubrun bench` (which will offer to
  submit to a compute node) for representative numbers. Honest: phrase as "you appear to be on
  an HPC login node," never assert it definitively; never on the import path.

## Proposed changes

1. **Generalize the detection seam** (`__main__.py`): replace `_slurm_available`/
   `_on_compute_node` with a `_detect_schedulers()` returning an ordered list of detected
   scheduler descriptors (Slurm kept first for back-compat), each carrying `available`,
   `on_compute_node`, `submit_script`, and a human name. Keep thin `_slurm_available`-style
   shims if anything else references them (grep first).
2. **Submission dispatch in `_run_bench`:** choose the scheduler (respecting `--scheduler`),
   locate its submit script under `benchmarks/`, build the argv list, print it, prompt (unless
   `--submit`/`--yes`), submit. On an unsupported/ambiguous cluster, say so clearly and run
   local (or honor `--scheduler local`). Reuse the existing `PUBRUN_REPO`/`PUBRUN_PY` env
   wiring.
3. **New batch scripts** under `benchmarks/`:
   - `submit_bench_pbs.sh` + `run_bench.pbs` (`qsub`, `#PBS` directives, `PBS_NODEFILE`).
   - `submit_bench_lsf.sh` + `run_bench.lsf` (`bsub`, `#BSUB` directives, `LSB_HOSTS`).
   - `submit_bench_sge.sh` + `run_bench.sge` (`qsub`, `#$` directives, `PE_HOSTFILE`).
   Each mirrors `submit_bench.sh`/`run_bench.sbatch`: pick/allow a target node/queue, run the
   harness with the shared `PUBRUN_*` interface, write results under `benchmarks/results/`.
   Header comment in each: "starting point — adapt queue/account/walltime to your site."
4. **`self-check` login-node suggestion** (`report/checks.py`): an **`INFO`-severity** finding
   (not `WARN`) when a scheduler is detected and not on a compute node — "you appear to be on
   an HPC <name> login node; run `pubrun bench` to submit a representative benchmark to a
   compute node." **`INFO` is required, not optional:** `self-check --strict` exits non-zero
   on any `WARN` (`checks.py:788`, `:842`), and this nudge is advice, not a problem — making it
   `WARN` would break `--strict` CI/HPC pre-checks on every login node. Pairs with the
   fs-health warnings from the data-quality IPD.
5. **Docs:** `docs/hpc.md` (multi-scheduler support table; how to submit on each; the
   site-adaptation caveat; the login-node suggestion), `docs/cli.md` (`bench --scheduler`
   flag; updated detection description), `benchmarks/README.md` (the new scripts),
   `CHANGELOG.md` `[Unreleased] → Added`.

## Anti-regression / invariants

- **Never auto-submit.** For EVERY scheduler, non-interactive default without `--submit`/
  `--yes` prints the command and does NOT submit. **Test:** per-scheduler (fake PATH/env),
  detected → prints, does not execute, unless `--submit`/`--yes`/interactive "y".
- **Slurm behavior unchanged (back-compat) — refactor is characterization-gated.** This change
  refactors `_slurm_available`/`_on_compute_node`/`_run_bench` (`__main__.py:879`, `:884`,
  `:903`), which enforce the "never auto-submit" invariant. Per the anti-regression rule:
  **before** refactoring, confirm `tests/test_bench_command.py`'s Slurm tests pin the current
  behavior (detect / print-not-execute / submit-only-on-consent); if any gap exists, add the
  pinning test first, green, then refactor and keep it green. The current Slurm detection +
  `submit_bench.sh` path must behave **exactly** as before (bare `--submit`, `--yes`,
  interactive "y", `--local` all unchanged). **Test:** the current Slurm tests pass verbatim
  after the refactor; grep confirms no other caller of the removed helper names is left
  dangling (keep thin shims if so).
- **No shell injection (all schedulers).** Every submit script — the existing
  `submit_bench.sh` AND the new `.pbs`/`.lsf`/`.sge` ones — is invoked from `_run_bench` via an
  **argv list, never `shell=True`**, and never by interpolating user values into a shell
  string. Any value forwarded to a scheduler (partition/queue/account/args) is a discrete argv
  element and **charset-validated** (safe set) before forwarding; this includes the new
  scripts, which must NOT reintroduce the unquoted word-splitting of the
  `PUBRUN_BENCH_ARGS`-style env interface that IPD-C flagged (`submit_bench.sh:48`). **Tests:**
  a `--queue`/`--scheduler`/account value containing shell metacharacters is passed as a
  literal argument (not executed) for each scheduler path; the new scripts quote every
  expanded variable.
- **Ambiguity handled honestly.** With `qsub` present but neither PBS nor SGE markers,
  report the ambiguity and require `--scheduler` to disambiguate rather than guessing.
  **Test:** `qsub`-only PATH with no `PBS_*`/`SGE_*` → reported ambiguous, no silent guess.
- **Detection is cheap + side-effect-free.** Detection touches only env vars + `shutil.which`;
  it runs NO scheduler query and NO network call. **Test:** detection makes no subprocess
  call (monkeypatch `subprocess`/`which` accounting).
- **Never intrude on the import path.** All of this is CLI-only (`bench`, `self-check`); the
  library import is untouched. **Test:** import-path unaffected (no new import-time cost).
- **Graceful degradation.** No scheduler, unknown scheduler, missing submit script, submit
  binary absent → clear message, fall back to local run; never crash.
- **No new runtime dependency.** stdlib only.
- **Honest testability boundary.** We have no PBS/LSF/SGE cluster in CI, so the batch scripts
  cannot be end-to-end validated here. What IS tested: scheduler *detection* (faked env/PATH),
  the *argv/command construction* for each submit path, the consent gate, and shell-metachar
  literal handling — i.e. everything up to the actual `qsub`/`bsub`. The scripts themselves are
  shipped as **clearly-labeled, site-adaptable starting points** ("not validated against a live
  <scheduler>; adapt queue/account/walltime"), never presented as turnkey. Docs must say so
  plainly rather than implying tested support.

## Required tests / validation

- Per-scheduler detection from faked env/PATH: Slurm, PBS (`PBS_JOBID`/`qsub`+`pbsnodes`),
  LSF (`LSB_JOBID`/`bsub`), SGE (`SGE_ROOT`/`qsub`+`qhost`); on-compute-node vs login-node.
- PBS-vs-SGE `qsub` disambiguation (markers present → correct name; absent → ambiguous +
  requires `--scheduler`).
- `--scheduler` override forces the chosen scheduler or `local`.
- Non-submit safety per scheduler (prints, does not execute without consent).
- Shell-metacharacter arg treated as literal.
- Slurm regression: existing bench/Slurm tests unchanged and green.
- `self-check`: login-node suggestion fires when scheduler detected + not on compute node;
  does NOT fire on a laptop or on a compute node.
- Detection makes no subprocess/network call.
- Full suite green (clear `__pycache__` first).

## Spec / documentation sync

`docs/hpc.md`, `docs/cli.md`, `benchmarks/README.md`, `CHANGELOG.md`. Run
`/assess documentation` after execution.

## Open questions (for plan-review / maintainer)

1. **Site adaptation — RESOLVED (maintainer 2026-07-07):** (a) ship minimal, clearly-labeled
   "adapt to your site" scripts now (KISS; honest about the testability boundary). No
   `--account`/`--queue`/`--walltime` passthrough and no `[bench.hpc]` config block in this
   IPD — add passthrough flags later only if users hit friction (fast-follow).
2. **Node-selection strategy — RESOLVED (maintainer 2026-07-07):** submit to the default queue
   and let the scheduler place the job (simpler, portable, matches site expectations). Do NOT
   reimplement per-scheduler idle-node selection; document that `submit_bench.sh`'s random-
   idle-node (`sinfo`) trick is **Slurm-only**.
3. **Multi-scheduler precedence under `auto` — RESOLVED (maintainer 2026-07-07):** deterministic
   order **Slurm > PBS > LSF > SGE** (Slurm first for back-compat); **report ALL detected**
   schedulers so the ambiguity is visible; `--scheduler` overrides. PBS-vs-SGE `qsub` ambiguity
   still disambiguated by env markers as specced above.
4. **`self-check` login-node nudge severity — RESOLVED (plan-review):** `INFO`. Verified
   `self-check --strict` exits non-zero on any `WARN` (`checks.py:788`, `:842`); a login-node
   nudge is advice, so `WARN` would break `--strict` on every login node. Folded into change 4.

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-07)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verified: the Slurm seam
`_slurm_available`/`_on_compute_node`/`_run_bench` (`__main__.py:879`, `:884`, `:903`), the
existing `submit_bench.sh`/`run_bench.sbatch` env interface, `report/checks.py` `_finding`
model, and — decisively for the severity question — that `self-check --strict` exits non-zero
on any `WARN` (`checks.py:788`, `:842`). Verdict: **APPROVE WITH REVISIONS APPLIED.**

- **H1 (MEDIUM, functionality — resolved with evidence):** the login-node nudge MUST be `INFO`,
  not `WARN`; `WARN` would trip `self-check --strict` on every login node. Fixed in change 4 +
  OQ4 resolved.
- **H2 (HIGH, testing/anti-regression):** the refactor of the Slurm helpers/`_run_bench` is now
  characterization-gated — pin current Slurm consent behavior before refactor, green after,
  grep for dangling callers. Fixed in anti-regression.
- **H3 (MEDIUM, honesty/scope):** made explicit that PBS/LSF/SGE scripts cannot be
  end-to-end CI-tested (no live clusters); test detection + argv construction + consent + shell
  safety, and ship the scripts as clearly-labeled site-adaptable starting points. Fixed in
  anti-regression.
- **H4 (MEDIUM, security):** the no-shell-injection invariant now explicitly covers the new
  `.pbs`/`.lsf`/`.sge` scripts and any new queue/account passthrough, and forbids
  reintroducing the unquoted `PUBRUN_BENCH_ARGS`-style word-splitting IPD-C flagged. Fixed in
  anti-regression.

Deferred/open: OQ1 (site-adaptation depth — flags vs config), OQ2 (per-scheduler idle-node
selection vs default-queue), OQ3 (multi-scheduler precedence) — decidable at execution with
the stated leanings; none carry Medium-High+ Remediation Risk. Sequence: after the submission
and data-quality IPDs.
