# IPD: Update benchmark documentation for packaged wheel runtime

- Date: 2026-11-27
- Kind: child
- Concern: Backlog item `bej1qz` requirement 8: `docs/cli.md`, `docs/performance.md`, and `benchmarks/README.md` (along with `docs/hpc.md`, `docs/functional_spec.md`, and `README.md`) still state that `pubrun bench` requires a source checkout because `benchmarks/harness.py` is not shipped in the wheel, and they do not document the packaged runtime under `src/pubrun/_bench/` or the writable default output directory (`./pubrun-bench-results/`) used outside a source checkout.
- Scope: Update `docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, `docs/functional_spec.md`, and `README.md` so all user-facing and benchmark documentation accurately describes wheel-installed `pubrun bench` execution, writable default output directory selection, packaged high-performance computing (HPC) scripts, direct checkout shims, and single-source `share_safety` validation.
- Scope-Paths: docs/cli.md, docs/performance.md, benchmarks/README.md, docs/hpc.md, docs/functional_spec.md, README.md
- Item-Dependencies: executed:29nsim, executed:c1zz3x, executed:mfeptf
- Status: executed
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Update docs/cli.md, docs/performance.md, benchmarks/README.md, docs/hpc.md, docs/functional_spec.md, and README.md to document packaged pubrun bench support
- Work-Kind: bug
- Priority: high
- From-Backlog: bej1qz
- Blocks-Release: g2qtg5
- Set: bej1qz
- Order: 4
- Highest E allocated: 04
- Author: Antigravity
- Id: cuboum

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-27 executed (aw agy run model=Gemini-4-Neon-High): aw agy run self-finalize: cuboum verified (set bej1qz, attempt 1).
- 2026-11-27 approved (aw set): status set to approved
- 2026-11-27 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003; review record `.aw/records/reviews/20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.review.md`.
- 2026-11-27 to-review (aw set): demoted approved -> to-review: APPROVAL WITHDRAWN: Demote to to-review so /plan-review writes Readiness attestations before execution
- 2026-11-27 approved (aw set): status set to approved
- 2026-11-27 to-review (aw set): Authored review-ready child plan from backlog item bej1qz
- 2026-11-27 draft (Antigravity): created.

## Goal

Bring every documentation file that describes `pubrun bench` and the benchmark harness (`docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, `docs/functional_spec.md`, and `README.md`) into accurate agreement with the packaged `src/pubrun/_bench/` runtime, removing all stale source-checkout requirements and writing clean user-facing prose with no em or en dashes.

### Documentation files updated

```mermaid
classDiagram
    class cli_md["docs/cli.md"] {
        bench subcommand reference
        default output dir and HPC scripts
    }
    class perf_md["docs/performance.md"] {
        how overhead is measured
        result file locations
    }
    class bench_readme["benchmarks/README.md"] {
        packaged runtime vs checkout tooling
        HPC submit scripts and PUBRUN_RESULTS_DIR
    }
    class hpc_md["docs/hpc.md"] {
        cluster benchmark section
    }
    class spec_md["docs/functional_spec.md"] {
        Section 11.18 bench specification
    }
    class root_readme["README.md"] {
        pubrun bench overview
    }
    cli_md --> bench_readme : links for harness details
    perf_md --> bench_readme : links for running instructions
    hpc_md --> bench_readme : links for HPC scripts
    root_readme --> cli_md : summarizes CLI usage
    spec_md --> cli_md : specifies bench behavior
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Update primary benchmark and command-line interface (CLI) documentation

- [x] E-01 Update `docs/cli.md` (`` ### `bench`: Overhead Benchmark Runner `` section):
  - Remove the paragraph stating `**Requires a source checkout** (the benchmark tooling is intentionally not shipped in the pip package to keep installs lightweight). Clone the repo and run from it.`
  - Update the opening line (`benchmarks/harness.py`) to note the packaged standard-library runtime (`pubrun._bench.harness`, with checkout shim `benchmarks/harness.py`) shipped in the wheel, working from any working directory after `pip install pubrun` with no extra dependencies.
  - Document default output directory selection: `./pubrun-bench-results/` under the current working directory outside a source checkout, `benchmarks/results/` inside a source checkout, or `PUBRUN_RESULTS_DIR` when set in the environment.
  - Update references to packaged HPC submit scripts (`src/pubrun/_bench/scripts/` with checkout shims under `benchmarks/`) and packaged share-safety validation (`pubrun._bench.share_safety`).
  - Use no em or en dashes in edited or added prose.
  - Depends on: none
  - Expected outcome: `docs/cli.md` accurately documents wheel-installed `pubrun bench` and contains no source-checkout requirement.
  - Execution state: performed

- [x] E-02 Update `docs/performance.md` and `benchmarks/README.md`:
  - In `docs/performance.md`:
    - Note under `## How overhead is measured` and `` ### Result files (schema `pubrun-benchmark/5`) `` that users can run `pubrun bench` directly from a `pip`-installed wheel without cloning the repository (writing to `./pubrun-bench-results/` by default outside a checkout, `benchmarks/results/` inside a checkout, or `PUBRUN_RESULTS_DIR` when set), while `python benchmarks/harness.py` and analysis scripts (`aggregate.py`, `plot.py`, `startup_breakdown.py`, `package_capture_bench.py`) remain available in a source checkout.
    - Correct the stale note claiming `benchmarks/submit_bench_{pbs,lsf,sge}.sh` pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"` so it matches the actual redacted-only default behavior of those scripts.
  - In `benchmarks/README.md`:
    - Clarify under `## Design` (and replace the existing em dash on the `harness.py` bullet with `-`) that the runtime measurement core (`harness.py`, `scenarios.py`, `share_safety.py`, `workloads/`, and HPC submit scripts) is packaged inside `src/pubrun/_bench/` and exposed in `benchmarks/` via checkout shims, while non-runtime analysis, plotting, archival, and micro-benchmark scripts (`aggregate.py`, `plot.py`, `pull_submissions.py`, `startup_breakdown.py`, `package_capture_bench.py`, `test_*.py`) and `results/`/`data/` stay outside the wheel.
    - Update `## Running on an HPC cluster` and `### Slurm details` to document packaged scripts under `src/pubrun/_bench/scripts/` (with checkout shims under `benchmarks/`), fix the stale filename pattern `pubrun-bench-${NODE}-${STAMP}.redacted.json` to use the non-identifying hostname hash (`${ANON_ID}` / `<hostname-hash>`), document `PUBRUN_RESULTS_DIR` and `pip install pubrun` (not only `pip install -e .`), and correct the stale note about PBS/LSF/SGE scripts writing bare `.json` files.
    - Update `## Contributing a result from a new machine` to remove `(from a source checkout)`, show `pip install pubrun` and `pubrun bench` working directly from a wheel install, document default output directory selection (`./pubrun-bench-results/` outside a checkout, `benchmarks/results/` inside one, or `PUBRUN_RESULTS_DIR`), update the share-safety validator reference to `pubrun._bench.share_safety` (with checkout shim `benchmarks/share_safety.py`), and correct the second stale note about PBS/LSF/SGE scripts passing `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`.
  - Use no em or en dashes in edited or added prose.
  - Depends on: E-01
  - Expected outcome: `docs/performance.md` and `benchmarks/README.md` agree with the packaged runtime, HPC script defaults, and checkout shims.
  - Execution state: performed

### Task group 2: Update secondary references for cross-doc consistency

- [x] E-03 Update `docs/hpc.md`, `docs/functional_spec.md`, and `README.md`:
  - In `docs/hpc.md` (`## Running the benchmark suite on a cluster`): remove "`pubrun bench` requires a source checkout (`git clone`), because `benchmarks/harness.py` is not shipped in the pip wheel" and explain that `pubrun bench` runs directly from a wheel install using packaged submit scripts (`src/pubrun/_bench/scripts/`, with checkout shims under `benchmarks/`) and writes to `./pubrun-bench-results/` (or `PUBRUN_RESULTS_DIR`, or `benchmarks/results/` inside a checkout).
  - In `docs/functional_spec.md` (`` ### 11.18 Overhead Benchmarks (`bench`) ``): replace `(requires a source checkout; benchmarks/harness.py is not shipped in the pip wheel)` with the packaged `src/pubrun/_bench/` runtime and writable default output directory behavior (`./pubrun-bench-results/` outside a checkout, `benchmarks/results/` inside one, or `PUBRUN_RESULTS_DIR`).
  - In `README.md` (`` ### `pubrun bench` ``): remove `"Requires a source checkout."` and note that it works directly from a `pip`-installed wheel.
  - Use no em or en dashes in edited or added prose.
  - Depends on: E-01, E-02
  - Expected outcome: Zero documentation files in the repository claim `pubrun bench` requires a source checkout.
  - Execution state: performed

### Task group 3: Verify documentation consistency and hygiene

- [x] E-04 Run all verification checks listed in `## Required tests / validation`:
  - Run negative `grep` across all six updated documentation files (`docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, `docs/functional_spec.md`, `README.md`) and across `docs/` for stale source-checkout requirements, "not shipped in the", stale PBS/LSF/SGE `--out ...json` notes, and stale `pubrun-bench-${NODE}` filename claims.
  - Check `git diff HEAD --unified=0` of the six documentation files for any newly introduced em or en dashes (`\u2014`, `\u2013`).
  - Run `python3 scripts/sanitize_paths.py --check --all`.
  - Depends on: E-01, E-02, E-03
  - Expected outcome: Negative grep finds zero stale bench-checkout or filename claims, added lines have zero em/en dashes, and path sanitization exits `0`.
  - Execution state: performed

## Project conventions discovered (Step 0)

- Six documentation files currently carry stale `pubrun bench` source-checkout or output claims: `docs/cli.md` (`` ### `bench`: Overhead Benchmark Runner ``), `docs/hpc.md` (`## Running the benchmark suite on a cluster`), `docs/functional_spec.md` (`` ### 11.18 Overhead Benchmarks (`bench`) ``), `README.md` (`` ### `pubrun bench` ``), `benchmarks/README.md` (`## Design`, `## Running on an HPC cluster`, `## Contributing a result from a new machine`, including `pubrun-bench-${NODE}` and two stale PBS/LSF/SGE bare-`.json` notes), and `docs/performance.md` (`## How overhead is measured`, `` ### Result files (schema `pubrun-benchmark/5`) ``).
- `AGENTS.md` prohibits em dashes (`—`) and en dashes (`–`) in user-facing prose (`README.md`, `docs/`, `benchmarks/README.md`).
- `scripts/sanitize_paths.py --check --all` checks tracked files for machine-local paths and identifying leaks.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| F-01 | Medium | Low | End User | `docs/cli.md`, `docs/hpc.md`, `docs/functional_spec.md`, `README.md`, `benchmarks/README.md` | Documentation tells users `pubrun bench` requires cloning the Git repository. |
| F-02 | Low | Low | End User | `docs/performance.md`, `benchmarks/README.md` | Documentation omits `./pubrun-bench-results/` and `PUBRUN_RESULTS_DIR`, shows stale `pubrun-bench-${NODE}` in `benchmarks/README.md`, and still describes an older PBS/LSF/SGE bare-`.json` `--out` behavior. |

## Proposed changes (ordered, validatable)

1. Update `docs/cli.md` `bench` section for packaged runtime, writable default output directory, packaged HPC scripts, and `pubrun._bench.share_safety` (E-01; Remediation Risk: Low).
2. Update `docs/performance.md` and `benchmarks/README.md` for packaged runtime vs checkout analysis tooling, accurate HPC script defaults, `${ANON_ID}` filename token, and `PUBRUN_RESULTS_DIR` (E-02; Remediation Risk: Low).
3. Update `docs/hpc.md`, `docs/functional_spec.md`, and `README.md` to eliminate all remaining source-checkout requirements for `pubrun bench` (E-03; Remediation Risk: Low).
4. Verify zero stale claims across all six files, zero added em/en dashes against `HEAD`, and clean `scripts/sanitize_paths.py --check --all` (E-04; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Updating `CHANGELOG.md` is deferred to the release-notes step when preparing release `g2qtg5`, as backlog item `bej1qz` does not request a changelog entry.
  - Carrier-Declined: Release changelog entries are authored during `/release-notes`, not per backlog item.

## Scope check

- Over-scope: none. The three files named in backlog item `bej1qz` requirement 8 (`docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`) plus the three sibling docs that make the identical contradicted claim (`docs/hpc.md`, `docs/functional_spec.md`, `README.md`) are updated.
- Under-scope: none. Every user-facing claim that `pubrun bench` requires a source checkout is removed.

## Required tests / validation

1. **Negative `grep` for stale `pubrun bench` source-checkout, PBS/LSF/SGE `--out`, and `${NODE}` filename claims** (must exit `1` with zero matches across all six documentation files):

   ```sh
   grep -rn -iE 'requires a source checkout|not shipped in the|from a source checkout|pubrun-bench-\$\{NODE\}|--out "\$RESULTS_DIR/\$\{NODE\}-\$\{STAMP\}\.json"' docs/cli.md docs/performance.md benchmarks/README.md docs/hpc.md docs/functional_spec.md README.md; echo "exit=$?"
   ```

2. **Check added documentation lines (staged or unstaged against `HEAD`) for em or en dashes** (must exit `0` and print `ok`):

   ```sh
   python3 -c 'import subprocess; diff = subprocess.check_output(["git", "diff", "HEAD", "--unified=0", "--", "docs/cli.md", "docs/performance.md", "benchmarks/README.md", "docs/hpc.md", "docs/functional_spec.md", "README.md"], text=True); bad = [ln for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++") and ("\u2014" in ln or "\u2013" in ln)]; print("bad=", bad); assert not bad; print("ok")'
   ```

3. **Path-leak sanitizer check** (must exit `0`):

   ```sh
   python3 scripts/sanitize_paths.py --check --all
   ```

## Spec / documentation sync

This plan performs the documentation sync across `docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, `docs/functional_spec.md`, and `README.md`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition)—as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction—name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Pasted `git diff -- docs/cli.md` showing removal of the source-checkout requirement and documentation of `pubrun._bench.harness`, `./pubrun-bench-results/`, `PUBRUN_RESULTS_DIR`, packaged HPC scripts, and `pubrun._bench.share_safety`.
  - Observed evidence:
    - `git diff -- docs/cli.md` (exit `0`):
      ````diff
      diff --git a/docs/cli.md b/docs/cli.md
      index b810a1d..fdf7bd8 100644
      --- a/docs/cli.md
      +++ b/docs/cli.md
      @@ -308,15 +308,21 @@ pubrun inspect runs/pubrun-XYZ --preflight --json | jq '.preflight.status'

       ### `bench`: Overhead Benchmark Runner

      -Friendly front-end over the benchmark harness (`benchmarks/harness.py`). Runs the suite
      -locally by default; on an HPC login node it detects the batch scheduler (**Slurm, PBS/Torque,
      -LSF, or SGE/Grid Engine**) and **offers** to submit to a compute node (and never submits
      -without confirmation; on Slurm it can wait for completion and then contribute from the login
      -node). By default it writes **only a redacted, share-safe** result file (`*.redacted.json`)
      -and, on an interactive terminal, offers to contribute it to `fariello/pubrun`.
      -
      -**Requires a source checkout** (the benchmark tooling is intentionally not shipped in the
      -pip package to keep installs lightweight). Clone the repo and run from it.
      +Command-line front-end over the packaged standard-library benchmark harness
      +(`pubrun._bench.harness`, with source-checkout shim `benchmarks/harness.py`). The benchmark
      +runtime ships in the `pubrun` wheel and works from any working directory after
      +`pip install pubrun` with no extra runtime dependencies. It runs locally by default; on a
      +high-performance computing (HPC) login node it detects the batch scheduler (**Slurm,
      +PBS/Torque, LSF, or SGE/Grid Engine**) and **offers** to submit to a compute node (and never
      +submits without confirmation; on Slurm it can wait for completion and then contribute from the
      +login node). By default it writes **only a redacted, share-safe** result file
      +(`*.redacted.json`) and, on an interactive terminal, offers to contribute it to
      +`fariello/pubrun`.
      +
      +**Default output directory.** `pubrun bench` resolves the results directory in this order:
      +`PUBRUN_RESULTS_DIR` when set in the environment, `benchmarks/results/` when run inside a
      +`pubrun` source checkout, or `./pubrun-bench-results/` under the current working directory
      +outside a checkout.
      @@ -369,25 +375,29 @@ or an interactive "y"). On Slurm, after submission, the login-node process polls
      -The per-scheduler submit scripts under `benchmarks/` (`submit_bench.sh`, `submit_bench_pbs.sh`,
      -`submit_bench_lsf.sh`, `submit_bench_sge.sh`) are starting points to adapt to your site.
      -
      -**Contributing a result (consent-gated).** After a run, `pubrun bench` runs a structural
      -share-safety check (`benchmarks/share_safety.py`), prints a safe-file block, ...
      +The packaged per-scheduler submit scripts live under `src/pubrun/_bench/scripts/`
      +(`submit_bench.sh`, `run_bench.sbatch`, `submit_bench_pbs.sh`, `submit_bench_lsf.sh`,
      +`submit_bench_sge.sh`), with source-checkout shims under `benchmarks/`; treat them as starting
      +points to adapt to your site.
      +
      +**Contributing a result (consent-gated).** After a run, `pubrun bench` runs the packaged
      +structural share-safety check (`pubrun._bench.share_safety`, with source-checkout shim
      +`benchmarks/share_safety.py`), prints a safe-file block, ...
      +**"Submit later" / HPC recovery.** Because the redacted file persists on disk (under
      +`./pubrun-bench-results/` outside a checkout, `benchmarks/results/` inside a checkout, or
      +`PUBRUN_RESULTS_DIR`), you can submit it later without re-running:
      +
      +```bash
      +pubrun bench --submit-file pubrun-bench-results/pubrun-bench-<hash>-<ts>.redacted.json
      +```
      ````
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/performance.md benchmarks/README.md` showing packaged wheel execution, writable default output directory (`./pubrun-bench-results/`, `PUBRUN_RESULTS_DIR`), `${ANON_ID}`/`<hostname-hash>` redacted filename pattern, `pubrun._bench.share_safety`, and accurate PBS/LSF/SGE redacted-only defaults.
  - Observed evidence:
    - `git diff --stat -- docs/performance.md benchmarks/README.md` (exit `0`):
      ```text
       benchmarks/README.md | 189 +++++++++++++++++++++++++++++++--------------------
       docs/performance.md  |  41 +++++++----
       2 files changed, 143 insertions(+), 87 deletions(-)
      ```
    - `git diff -- docs/performance.md` (exit `0`):
      ````diff
      diff --git a/docs/performance.md b/docs/performance.md
      index 2d55a26..318d852 100644
      --- a/docs/performance.md
      +++ b/docs/performance.md
      @@ -25,7 +25,18 @@ median of a scenario minus its group baseline:
      -See [`benchmarks/README.md`](../benchmarks/README.md) to run it:
      +You can run the benchmark suite directly from a `pip`-installed wheel without cloning the
      +repository (`src/pubrun/_bench/` ships the standard-library runtime harness):
      +
      +```bash
      +pip install pubrun                    # includes packaged benchmark runtime (stdlib only)
      +pubrun bench                          # run from any working directory
      +```
      +
      +In a source checkout, `python benchmarks/harness.py` (checkout shim over
      +`pubrun._bench.harness`) and the non-runtime analysis scripts (`aggregate.py`, `plot.py`,
      +`startup_breakdown.py`, `package_capture_bench.py`) remain available. See
      +[`benchmarks/README.md`](../benchmarks/README.md) for full instructions:
      @@ -34,17 +45,23 @@ python benchmarks/aggregate.py benchmarks/results/*.json
      -Each run writes a **compact** (no-indent) JSON file. By default, `benchmarks/harness.py`
      -...
      -PBS/LSF/SGE template scripts `benchmarks/submit_bench_{pbs,lsf,sge}.sh` currently pass
      -`--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, which writes a gitignored unredacted bare
      -`.json` file alongside the default `.redacted.json` file; see
      +Each run writes a **compact** (no-indent) JSON file. When you run `pubrun bench` or the
      +packaged harness (`python -m pubrun._bench.harness`, also invoked via the
      +`benchmarks/harness.py` checkout shim) without an explicit output path, results go to
      +`PUBRUN_RESULTS_DIR` when set in the environment, `benchmarks/results/` inside a `pubrun`
      +source checkout, or `./pubrun-bench-results/` under the current working directory outside a
      +checkout.
      +
      +By default, every invocation writes only the shareable, redacted copy:
      +`pubrun-bench-<hostname-hash>-<UTC-timestamp>.redacted.json` (the filename embeds a
      +non-identifying hostname hash, never the hostname; pass `--redacted-out <path>` to the harness
      +to override its path). The identifying local copy
      +(`<host>-<UTC-timestamp>.unredacted.json`) is written only when you pass `--unredacted`, pass
      +`--out <path>` to the harness, or set `PUBRUN_UNREDACTED=1` for a high-performance computing
      +(HPC) submit script. Neither `pubrun bench`, the harness default output, nor any packaged HPC
      +submit script (`run_bench.sbatch`, `submit_bench_pbs.sh`, `submit_bench_lsf.sh`,
      +`submit_bench_sge.sh`) writes a bare `*.json` file; all of them write only the redacted
      +`.redacted.json` file by default (see
      ````
    - `git diff -- benchmarks/README.md` (key hunks, exit `0`):
      - `## Design`: replaces em dash on `harness.py` bullet with `-`, documents `src/pubrun/_bench/` packaging (`harness.py`, `scenarios.py`, `share_safety.py`, `workloads/`, `scripts/`) with `benchmarks/` checkout shims and confirms `aggregate.py`, `plot.py`, `pull_submissions.py`, `startup_breakdown.py`, `package_capture_bench.py`, `test_*.py`, `results/`, and `data/` remain outside the wheel.
      - `## Running`, `## Running on an HPC cluster`, `### Slurm details`, `## Contributing a result from a new machine`: removes `(from a source checkout)`, documents `pip install pubrun` + `pubrun bench`, documents `PUBRUN_RESULTS_DIR` / `benchmarks/results/` / `./pubrun-bench-results/`, updates filename pattern to `$RESULTS_DIR/pubrun-bench-${ANON_ID}-${STAMP}.redacted.json` (`<hostname-hash>`), updates share-safety reference to `pubrun._bench.share_safety` (checkout shim `benchmarks/share_safety.py`), and removes both stale PBS/LSF/SGE `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"` notes.
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Pasted `git diff -- docs/hpc.md docs/functional_spec.md README.md` showing removal of all remaining source-checkout claims for `pubrun bench`.
  - Observed evidence:
    - `git diff -- docs/hpc.md docs/functional_spec.md README.md` (exit `0`):
      ````diff
      diff --git a/README.md b/README.md
      index 4e8f97e..d6a18c5 100644
      --- a/README.md
      +++ b/README.md
      @@ -247,7 +247,7 @@ pubrun inspect [RUN_DIR] [--show-suggestions] [--preflight]
       ### `pubrun bench`
      -Run the pubrun overhead benchmark suite (auto-detects an HPC scheduler, Slurm/PBS/LSF/SGE, and offers to submit the job to a compute node). Every run starts with an uncaptured **baseline pass** (pubrun absent), then N measured passes: `--quick` (2x15), `--full`/default (3x30), or `--rigorous` (5x50). Requires a source checkout.
      +Run the pubrun overhead benchmark suite directly from a `pip`-installed wheel in any working directory with no extra runtime dependencies (auto-detects a high-performance computing (HPC) scheduler, Slurm/PBS/LSF/SGE, and offers to submit the job to a compute node). Every run starts with an uncaptured **baseline pass** (pubrun absent), then N measured passes: `--quick` (2x15), `--full`/default (3x30), or `--rigorous` (5x50). Results default to `./pubrun-bench-results/` outside a source checkout, `benchmarks/results/` inside one, or `PUBRUN_RESULTS_DIR` when set.

      diff --git a/docs/functional_spec.md b/docs/functional_spec.md
      index 1bf4598..035e862 100644
      --- a/docs/functional_spec.md
      +++ b/docs/functional_spec.md
      @@ -647,12 +647,13 @@ pubrun self-check [-v|--show-suggestions] [--json] [--strict] [-q|--quiet]
       ### 11.18 Overhead Benchmarks (`bench`)
      -Front-end over the overhead benchmark harness under `benchmarks/` (requires a source checkout; `benchmarks/harness.py` is not shipped in the pip wheel).
      +Front-end over the packaged standard-library overhead benchmark runtime under `src/pubrun/_bench/` (with source-checkout shims under `benchmarks/`). Works directly from a `pip`-installed wheel in any working directory with no extra runtime dependencies.
      +- Resolves the default writable results directory to `PUBRUN_RESULTS_DIR` when set in the environment, `benchmarks/results/` inside a `pubrun` source checkout, or `./pubrun-bench-results/` under the current working directory outside a checkout.
      +- Runs locally by default or auto-detects high-performance computing (HPC) schedulers (Slurm, PBS, LSF, SGE) and offers to submit to a compute node using packaged scripts under `src/pubrun/_bench/scripts/` (never submitting without confirmation unless `--submit` or `-y`/`--yes` is passed).
      +- Writes only a redacted, share-safe result JSON by default (`--unredacted` also writes the identifying copy) and validates it with the packaged `pubrun._bench.share_safety` validator.

      diff --git a/docs/hpc.md b/docs/hpc.md
      index ca66633..3c12a1d 100644
      --- a/docs/hpc.md
      +++ b/docs/hpc.md
      @@ -142,24 +142,28 @@ Each suggestion comes with an honest performance note; see [Performance](perform
       ## Running the benchmark suite on a cluster
      -`pubrun bench` requires a source checkout (`git clone`), because `benchmarks/harness.py` is
      -not shipped in the pip wheel. ...
      +`pubrun bench` runs directly from a `pip`-installed wheel using the packaged standard-library
      +benchmark runtime (`src/pubrun/_bench/`) and packaged scheduler submission scripts
      +(`src/pubrun/_bench/scripts/`, with source-checkout shims under `benchmarks/`; see
      +`benchmarks/README.md`). Result JSONs capture filesystem type and scheduler allocation context
      +so results are comparable across nodes. By default, results are written to
      +`./pubrun-bench-results/` outside a source checkout, `benchmarks/results/` inside a checkout,
      +or `PUBRUN_RESULTS_DIR` when set in the environment.
      ````
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted output of all three commands in `## Required tests / validation` across `docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, `docs/functional_spec.md`, and `README.md` showing `exit=1` (zero matches) for the negative grep, `ok` for the `git diff HEAD` dash check, and exit `0` for `scripts/sanitize_paths.py --check --all`.
  - Observed evidence:
    - Command 1 (negative grep across all six updated documentation files, and across `docs/`):
      ```text
      === CMD1: six files ===
      exit=1
      === CMD1b: docs/ ===
      exit=1
      ```
    - Command 2 (`git diff HEAD --unified=0` em/en dash check across all six files, exit `0`):
      ```text
      === CMD2: em/en dash check ===
      bad= []
      ok
      ```
    - Command 3 (`python3 scripts/sanitize_paths.py --check --all`, exit `0`, plus `aw sanitize --agent`, exit `0`):
      ```text
      === CMD3: sanitize_paths ===
      === CMD4: aw sanitize ===
      {"schema":"aw.agent/v1","kind":"result","cmd":"check-local-leaks","outcome":"clean","exit":0,"verified":true,"complete":true,"checked":1017,"findings":0,"evidence":["leak-scan"],"next":null}
      ```
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

1. **Preconditions:** Execute E-01 through E-04 only after this plan carries `- Status: approved`, `29nsim`, `c1zz3x`, and `mfeptf` have reached `executed`, and all blocking open questions are resolved.
2. **Scope declaration:** `- Scope-Paths:` declares the authorized file set (`docs/cli.md, docs/performance.md, benchmarks/README.md, docs/hpc.md, docs/functional_spec.md, README.md`). If execution requires modifying a path outside `- Scope-Paths:` or leaving a declared path unmodified, justify each exception explicitly with `--scope-reason` or `--scope-ack` at finalize rather than silently deviating.
3. **Validation honesty:** Every `V-*` item MUST paste the actual command runner output captured during execution; never mark any `V-*` item `pass` without running the corresponding command and observing its exit code and output.
4. **Commit and push discipline:** Commit only paths modified for this plan through `aw commit cuboum -- <paths>`. Never use `git add -A`, bare `git add .`, or raw `git commit`, and never push, tag, or publish without explicit human authorization.
5. **Lifecycle transition:** After all `E-*` items are `performed` and all `V-*` items are `pass`, the plan MUST complete the post-gate transition to `.aw/records/plans/executed/`. When executing under an automated runner (`aw oc run` or `aw agy run`), leave finalization to the runner's post-turn finalize step; in a manual or interactive execution outside a runner, run `aw ipd finalize cuboum` (never hand-roll `git mv` to `executed/`).
