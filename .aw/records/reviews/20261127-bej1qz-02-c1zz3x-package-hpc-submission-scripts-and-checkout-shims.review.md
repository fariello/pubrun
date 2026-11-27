# Review findings: ipd c1zz3x

- Subject-Id: c1zz3x
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `errors: 0`, `warnings: 0`, `info: 2` boilerplate `IPD-C802`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` with only the same two non-blocking advisories on line 178 boilerplate. Expanded `PBS`, `LSF`, `SGE`, and `CLI` on first use and updated the Mermaid flowchart to match the revised `import pubrun.minimal, pubrun._bench.harness` preflight check and relative-path normalization.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Goal`, `## Spec / documentation sync`, and Mermaid flowchart | `PBS`, `LSF`, `SGE`, and `CLI` used without first-use expansion; diagram showed `import pubrun._bench.harness` | Expanded scheduler acronyms and `command-line interface (CLI)` on first use; updated flowchart node to `import pubrun.minimal, pubrun._bench.harness` and `Resolve absolute PUBRUN_RESULTS_DIR` | Satisfy technical writing requirements 1 and 12(d)-(e) (`PR-002`, `PR-005`) |
| `E-01`, `E-02` | Preflight ran `"$PUBRUN_PY" -c "import pubrun._bench.harness"`; omitted `set -u` initialization for optional `PUBRUN_*` vars, relative `PUBRUN_RESULTS_DIR` normalization, and explicit no-`PUBRUN_REPO=$HERE/..` rule in E-02 | Changed preflight to `import pubrun.minimal, pubrun._bench.harness`, added `set -u`-safe defaults for all optional `PUBRUN_*` vars, normalized relative `PUBRUN_RESULTS_DIR` to absolute paths, and forbade defaulting `PUBRUN_REPO` to `$HERE/..` in E-02 | Prevent compute-node auto-start (`PR-002`) and `set -u`/relative-path bugs (`PR-003`) |
| `E-03` | `benchmarks/run_bench.sbatch` relied only on `PUBRUN_REPO` / `$HERE` (fails under Slurm spooling); `benchmarks/submit_bench_{pbs,lsf,sge}.sh` dropped `STARTING POINT` and `QSUB_OPTS`/`BSUB_OPTS` comments | Added Slurm `SLURM_SUBMIT_DIR` and packaged-path fallback to `benchmarks/run_bench.sbatch` and retained honest `STARTING POINT` + `QSUB_OPTS=()`/`BSUB_OPTS=()` delegation header comments in PBS/LSF/SGE shims | Handle Slurm spool execution (`PR-003`) and keep `tests/test_bench_command.py::TestSchedulerSubmitSafety` green before Order 05 (`PR-001`) |
| `E-04`, `## Required tests / validation`, `V-01..V-04` | Validation command 2 ran `cat` inside `sbatch` stub (hangs/reads nothing), checked only a combined log without asserting empty `PUBRUN_REPO` or testing `run_bench.sbatch`; command 3 tested only `submit_bench.sh`; temp dirs leaked; command 4 missed win32/darwin `mypy` and `TestSchedulerSubmitSafety` | Rewrote commands 1 to 4 with executable-bit checks, per-script isolated `stdin=DEVNULL` stub checks, direct `run_bench.sbatch` execution, all five checkout shims (including spooled `run_bench.sbatch`), `TemporaryDirectory` cleanup, three-platform `mypy`, and `TestSchedulerSubmitSafety` | Close verification, hang, and vacuity gaps (`PR-004`) |
| `## Approval and execution gate` | Single paragraph lacking open-question precondition, `--scope-reason`/`--scope-ack`, validation honesty rule, no-`git add -A`/raw `git commit`, and conditional runner/executor finalize ownership | Replaced with structured five-clause execution contract stating conditional `aw oc run`/`aw agy run` vs manual `aw ipd finalize c1zz3x` ownership | Satisfy execution-contract rules in `r2-executability.md` and `s7-finalize.md` (`PR-005`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: bej1qz`, `- Order: 2`, `- Item-Dependencies: executed:29nsim`, `- Scope-Paths:` (`src/pubrun/_bench/scripts, benchmarks/run_bench.sbatch, benchmarks/submit_bench.sh, benchmarks/submit_bench_pbs.sh, benchmarks/submit_bench_lsf.sh, benchmarks/submit_bench_sge.sh`), 4 E-items in 4 task groups.

1. Yes: creates `src/pubrun/_bench/scripts/` and defines the `PUBRUN_RESULTS_DIR` / `PUBRUN_REPO` / `PUBRUN_REDACTED_OUT` / `PUBRUN_UNREDACTED` HPC script contract consumed by `mfeptf` (Order 03) and tested by `1r585o` (Order 05), and converts five checkout scripts under `benchmarks/`.
2. Yes: every script enforces the redacted-only default (`PUBRUN_REDACTED_OUT`, opaque `ANON_ID` hostname hashing, opt-in `PUBRUN_UNREDACTED`) and shell-quoting / argv-array injection safety (`SBATCH_OPTS`, `QSUB_OPTS`, `BSUB_OPTS`).
3. Yes: 4 E-items across 4 task groups spanning 11 files across four HPC schedulers (Slurm, PBS, LSF, SGE).
4. Yes: `- Scope-Paths:` explicitly lists all 6 directories/files touched.
5. Yes: mistakes can break HPC job submission, fail under `set -u` when `PUBRUN_REPO` is unset, auto-start `pubrun` during compute-node preflight, fail under Slurm script spooling, or break `tests/test_bench_command.py::TestSchedulerSubmitSafety` before Order 05 lands.

AW-TIER: complex

### Step R1

- Checked: all five existing HPC scripts (`benchmarks/run_bench.sbatch`, `benchmarks/submit_bench.sh`, `benchmarks/submit_bench_pbs.sh`, `benchmarks/submit_bench_lsf.sh`, `benchmarks/submit_bench_sge.sh`), `src/pubrun/__main__.py::_run_bench:2148-2210`, `src/pubrun/core.py::_is_pubrun_cli_invocation:618-650`, `tests/test_bench_command.py::TestSchedulerSubmitSafety:238-287`, `pyproject.toml`, and graduated backlog item `bej1qz`.
- Verified: every existing script behavior cited in `## Project conventions discovered` matches the repository; reading the scripts and `tests/test_bench_command.py` surfaced the `TestSchedulerSubmitSafety` text check (`PR-001`), the `python -c` auto-start side effect (`PR-002`), and the Slurm spooling / `set -u` / relative-path hazards (`PR-003`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-04` <-> `V-01..V-04`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:29nsim`, runtime-demonstration reachability for every `V-*` item, non-vacuous validation commands, and the execution gate contract.
- Verified: `PR-004` fixed the broken/vacuous validation command 2 (`sbatch` stub `cat` hang + combined-log assertion) and expanded command 3 to cover all five checkout shims including spooled `run_bench.sbatch`; `PR-005` completed the five-clause execution contract in `## Approval and execution gate`.

### Step R3

- Checked: privacy/PII redaction defaults (`PUBRUN_REDACTED_OUT` default using SHA-256 `ANON_ID` so raw cluster hostnames do not leak into filenames, `PUBRUN_UNREDACTED` opt-in), argv-array option construction (`SBATCH_OPTS`, `QSUB_OPTS`, `BSUB_OPTS`) preventing shell injection, and compute-node side-effect isolation (`import pubrun.minimal, pubrun._bench.harness` preventing stray `runs/` creation).
- Verified: no raw hostname leaks into default filenames, no user env vars are interpolated into shell strings, and preflight checks do not auto-start `pubrun`.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified: `PR-001` keeps `TestSchedulerSubmitSafety` passing across Orders 02 to 04; `PR-002` eliminates compute-node auto-start during preflight; `PR-003` handles Slurm spooling, `set -u`, and relative `PUBRUN_RESULTS_DIR`; `PR-004` closes all validation coverage, determinism, and cleanup gaps; `## Spec / documentation sync` truthfully defers documentation updates to `cuboum` (Order 04).

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught the `sbatch` stub `cat` hang and vacuous combined-log assertion in Validation Command 2 (`PR-004`).
  2. Testing and regression: caught `TestSchedulerSubmitSafety` breakage before Order 05 (`PR-001`) and missing shim/three-platform `mypy` checks (`PR-004`).
  3. UI / UX: preserved clear install error messages naming `$PUBRUN_PY` and honest `STARTING POINT` site-adaptation headers.
  4. Architect: verified single canonical script implementation under `src/pubrun/_bench/scripts/` with thin checkout shims and clean `get_submit_script_path` alignment with `29nsim` and `mfeptf`.
  5. Software engineer: caught `python -c` auto-start side effect (`PR-002`) and Slurm spooling / `set -u` / relative `PUBRUN_RESULTS_DIR` bugs (`PR-003`).
  6. Power user: verified `PUBRUN_RESULTS_DIR` override (including relative paths), `PUBRUN_PARTITION`/`PUBRUN_EXCLUDE`/`PUBRUN_QUEUE`/`PUBRUN_ACCOUNT`/`PUBRUN_PROJECT`/`PUBRUN_PE`, and direct `sbatch benchmarks/run_bench.sbatch`.
  7. Novice: verified wheel users on HPC clusters get working packaged scripts writing to `./pubrun-bench-results/` without cloning the repo.
  8. Stakeholder: confirmed full alignment with backlog item `bej1qz` requirements 1, 4, and 6.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-04` (4 E-items, 4 task groups, 6 Scope-Paths, Order 02 of 5-child Set `bej1qz`).
- Confirmed: each E-item covers one cohesive concern (Slurm packaged scripts, PBS/LSF/SGE packaged scripts, checkout shims, verification). No further splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `bej1qz` (`s3y296`, `29nsim`, `mfeptf`, `cuboum`, `1r585o`).
- Verified: `c1zz3x` depends on `executed:29nsim` (which creates `src/pubrun/_bench/` and `get_submit_script_path`), provides the five scripts under `src/pubrun/_bench/scripts/` consumed by `mfeptf` (Order 03) and checked in the wheel by `1r585o` (Order 05), preserves `sbatch --parsable` bare job-id output required by `mfeptf` Slurm polling, and keeps `tests/test_bench_command.py::TestSchedulerSubmitSafety` green until `1r585o` replaces it.

### Step S5

- Checked: `## Open questions` contains `None.`. All five findings (`PR-001` through `PR-005`) had `Low` overall Remediation Risk, were settled by repository code and policy evidence, and were fixed in place with zero open or deferred findings and zero unresolved human decisions. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r4-engineering.md` D (Anti-regression) / `r7-cross-plan.md` | `.aw/records/plans/pending/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md:91-93` vs `tests/test_bench_command.py::TestSchedulerSubmitSafety.test_new_submit_scripts_exist_and_quote_vars:278-286` | Converting `benchmarks/submit_bench_{pbs,lsf,sge}.sh` into bare `exec bash` shims drops `"STARTING POINT"` and `"QSUB_OPTS=("`/`"BSUB_OPTS=("` from those files, immediately breaking `tests/test_bench_command.py::TestSchedulerSubmitSafety` when Order 02 lands before Order 05 (`1r585o`) updates that test. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Required `E-03` shims for PBS/LSF/SGE to retain honest `# STARTING POINT` site-adaptation header comments noting delegation to the canonical script's `QSUB_OPTS=()`/`BSUB_OPTS=()` argv-array handling, and added `TestSchedulerSubmitSafety` to `E-04` validation (recommendation strength: `strong`). |
| PR-002 | HIGH | IN-SCOPE | `r4-engineering.md` A / `r3-security.md` (Side-effect isolation) | `.aw/records/plans/pending/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md:62,83` vs `src/pubrun/__init__.py:319-346` and `src/pubrun/core.py::_is_pubrun_cli_invocation:618-650` | Preflight checks in `run_bench.sbatch` and the embedded PBS/LSF/SGE job bodies ran `"$PUBRUN_PY" -c "import pubrun._bench.harness"`; under `-c`, `_is_pubrun_cli_invocation()` returns `False`, so the preflight check auto-starts a tracked `pubrun` run and creates a stray `runs/` directory on the compute node. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Changed compute-node preflight checks in `E-01`, `E-02`, the flowchart, and Validation Command 2 to `"$PUBRUN_PY" -c "import pubrun.minimal, pubrun._bench.harness" 2>/dev/null` and asserted `not (td / "runs").exists()` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` A (Correctness under Slurm spooling, `set -u`, and relative paths) | `.aw/records/plans/pending/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md:60-70,79-85,93` vs `benchmarks/run_bench.sbatch:22-36` and `benchmarks/submit_bench_{pbs,lsf,sge}.sh:18-30` | Three Bash hazards remained: (a) Slurm spools `sbatch benchmarks/run_bench.sbatch` into `/var/spool/slurmd/...`, where `dirname "${BASH_SOURCE[0]}"` is not `benchmarks/`; (b) under `set -euo pipefail`, unset `PUBRUN_REPO`/`PUBRUN_RESULTS_DIR`/`PUBRUN_BENCH_ARGS`/`PUBRUN_REDACTED_OUT`/`PUBRUN_UNREDACTED` trigger unbound-variable crashes unless explicitly defaulted; and (c) `E-02` did not forbid defaulting `PUBRUN_REPO` to `$HERE/..` or normalize relative `PUBRUN_RESULTS_DIR` paths to absolute paths before compute-node submission. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `set -u`-safe variable initialization and relative-to-absolute `PUBRUN_RESULTS_DIR` normalization to `E-01` and `E-02`, forbade `PUBRUN_REPO=$HERE/..` in `E-02`, and added `SLURM_SUBMIT_DIR` + packaged-path fallback resolution to `benchmarks/run_bench.sbatch` in `E-03` (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r4-engineering.md` E / `r2-executability.md` (Validation reliability and coverage) | `.aw/records/plans/pending/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md:100-107,142-167,180-198` | Validation Command 2 put `cat >> log` in the `sbatch` stub (which receives no stdin, risking hangs and recording nothing from `run_bench.sbatch`), asserted only over one merged log (vacuous per script), never checked empty `PUBRUN_REPO` or executed `run_bench.sbatch`, and leaked temp dirs; Command 3 tested only `benchmarks/submit_bench.sh` (skipping PBS/LSF/SGE and spooled `run_bench.sbatch`); Command 4 omitted `win32`/`darwin` `mypy` and `TestSchedulerSubmitSafety`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote Validation Commands 1 to 4 and `V-01..V-04` to check executable bits, run per-script `stdin=DEVNULL` assertions including empty `PUBRUN_REPO` and direct `run_bench.sbatch` execution, test all five checkout shims (including spooled `run_bench.sbatch`), clean up via `TemporaryDirectory`, and run three-platform `mypy` plus `TestSchedulerSubmitSafety` (recommendation strength: `very strong`). |
| PR-005 | MEDIUM | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` (Execution contract and technical writing) | `.aw/records/plans/pending/20261127-bej1qz-02-c1zz3x-package-hpc-submission-scripts-and-checkout-shims.ipd.md:32,170,200-205` | `## Approval and execution gate` omitted the open-question precondition, `--scope-reason`/`--scope-ack` scope declaration, hard-MUST validation honesty rule, explicit no-`git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize c1zz3x` ownership; `PBS`, `LSF`, `SGE`, and `CLI` were not expanded on first use. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the gate paragraph with the complete five-clause execution contract (including conditional `aw oc run`/`aw agy run` vs manual `aw ipd finalize c1zz3x` ownership) and expanded acronyms on first use (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `c1zz3x` | `complex` | `standard` | Order 02 of 5-child Set `bej1qz`, defines HPC submission script contracts consumed by `mfeptf` and `1r585o`, and enforces privacy redaction defaults and shell-injection safety; answers Yes to tier questions 1, 2, 3, and 5 in `steps/t-tier.md`. | yes |
| D-2 | How to keep `tests/test_bench_command.py::TestSchedulerSubmitSafety` green across Orders 02 to 04 | Retain honest `# STARTING POINT` header comments noting delegation to `QSUB_OPTS=()`/`BSUB_OPTS=()` in `benchmarks/submit_bench_{pbs,lsf,sge}.sh` shims | Add `tests/test_bench_command.py` to `c1zz3x` Scope-Paths or let Order 02 break the test suite until Order 05 | `tests/test_bench_command.py::TestSchedulerSubmitSafety.test_new_submit_scripts_exist_and_quote_vars:278-286` and Set `bej1qz` Scope-Paths partition (`1r585o` owns `tests/test_bench_command.py`). | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; all five revisions (`PR-001` through `PR-005`) were swept across the flowchart, `E-01..E-04`, `## Project conventions discovered`, `## Proposed changes`, `## Required tests / validation`, `V-01..V-04`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
