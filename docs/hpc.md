[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# pubrun in HPC and large-scale pipelines

**pubrun scales from one laptop run to thousands of array jobs without turning provenance into overhead.** It runs unmodified on HPC clusters (Slurm, PBS, LSF, SGE), captures the same trustworthy run record on a compute node as on your laptop, and uses parent-child manifest hydration (`PUBRUN_META_REF`) so a large batch does not re-record the shared environment on every job. This page covers running pubrun at scale, where it fits alongside the tools you may already use, and the two most common performance surprises on clusters (**slow network filesystems** and **shared-node contention**) with the commands that spot them: `pubrun self-check` (before/around a run) and `pubrun inspect` (after a run).

## Where pubrun fits (alongside MLflow, Weights and Biases, and DVC)

pubrun is a lightweight, zero-dependency, zero-infrastructure provenance and reproducibility **component**, not a platform. It complements experiment-tracking and data-versioning tools rather than replacing them:

- **MLflow / Weights and Biases** are experiment-tracking services (metrics, params, model registries, dashboards, usually a server or account). pubrun does not track metrics or host a dashboard; it captures the *execution provenance* of a run (code, dependencies, hardware, environment, inputs, logs) into a local schema-validated manifest. Use them together: track your metrics in MLflow or W&B, and let pubrun record exactly what produced each run.
- **DVC** versions data and pipeline stages. pubrun does not version data; it records what a run actually used and did. They are complementary: DVC pins the inputs, pubrun captures the run.

pubrun's design wins where those tools are awkward: **air-gapped or egress-restricted HPC nodes** (no server, no account, no network needed), **regulated environments** where a self-contained on-disk record is preferable to a hosted service, and **fast local rigor** where you want a trustworthy run record without standing up infrastructure. (For the research/ML angle, see [Research Use](research-use.md).)

## The most common pitfall: pubrun (or your runs) on a network filesystem

On clusters, home directories and shared venvs are usually mounted over **NFS/Lustre/GPFS**,
which is far slower than node-local disk. If `pubrun` itself is imported from an NFS-mounted
venv, or if your run output directory lives on NFS, startup and per-run I/O can be markedly
slower, and it is easy to mistake this for pubrun overhead.

Check the current machine:

```bash
pubrun self-check --show-suggestions
```

This flags when the pubrun install, the run output directory, or `$TMPDIR` sit on a network
filesystem, and suggests remedies, e.g.:

- Install pubrun into a **node-local** venv (on local scratch or `$TMPDIR`) or use
  `pip install --target` to local disk.
- Point `[core].output_dir` at node-local storage and copy results back afterward.
- Point `$TMPDIR` at node-local storage.

## Diagnosing a finished run

After a run, `pubrun inspect` reads the run's manifest and reports both what was captured
and **what was not** (and how to capture more next time):

```bash
pubrun inspect                    # most recent run (terse summary)
pubrun inspect <run> -v           # full detail + suggestions
pubrun inspect <run> --json       # machine-readable findings
```

`inspect` records, when available (see [Configuration](configuration.md) →
`[capture.resources].system_metrics`, on by default):

- the **filesystem type** backing the run (flagging network filesystems),
- system **available memory** and **load average** over the run,
- a **node-wide iowait** hint (`system_iowait_pct`), *indicative only*; it reflects the
  whole node, not just your run (Linux `/proc/stat` iowait is a system-wide counter).

### The "different system" banner

On HPC you typically **run on a compute node** but **inspect from the head/login node**.
`pubrun inspect` prints a glaring banner when the host you are inspecting from differs from
the host the run executed on, because any live re-checks would reflect the wrong machine.

### Preflight on a cluster

`pubrun inspect --preflight` compares the recorded run with the machine you are on now,
read-only and offline (see [CLI: inspect](cli.md#inspect--post-hoc-run-diagnosis)). Run it on
the node type where you plan to rerun, for example inside an interactive allocation on a
compute node, rather than on the login node:

```bash
pubrun inspect <run> --preflight -v                 # per-check detail
pubrun inspect <run> --preflight --fail-on mismatch # job pre-check: exit 1 on material mismatch
pubrun rerun <run> --preflight --fail-on mismatch | bash
```

Preflight separates expected cluster differences from ones that can change results:

- **Portability differences** (`portability_diff`), such as a different hostname, a newer
  Python patch release, or a different OS release string, are reported but do not fail
  `--fail-on mismatch`.
- **Material mismatches** (`mismatch`), such as a different Python minor version or
  implementation, a missing package or different package version, a different Git commit or
  script digest, or a missing or content-changed input file, fail `--fail-on mismatch`.
- **Unknowns** (`unknown` or `not_checked`), such as an input recorded only by path and size,
  a Git query that timed out on a slow filesystem, or a section that was not captured, fail
  only `--fail-on unknown`. pubrun never reports an unknown as a match.

The plain `--strict` threshold (`warn`) also fails on portability warnings such as the
different-host banner, so prefer `--fail-on mismatch` for cross-node checks.

### Parent snapshots (`meta_ref`)

In the parent and child workflow, a login-node job writes `pubrun meta --out meta.json` and
array tasks set `PUBRUN_META_REF=meta.json` and switch off heavy capture. At report time,
`inspect`, `show`, and the TUI fill the child's missing sections (hardware, process, python,
packages, environment, git) from the parent snapshot, in memory only. They report those
sections as `inherited`, which is weaker evidence than what the child observed itself.

The Parent Metadata category checks the snapshot before trusting it:

- **Availability and policy:** a missing, moved, non-`.json`, malformed, or wrong-type
  snapshot, or one outside the directories allowed by `[report].allow_external_meta_ref` and
  `[report].meta_ref_allowed_dirs`, is reported as unavailable. pubrun does not invent the
  missing sections.
- **Age:** a snapshot taken more than one day before the child run is flagged as stale, and a
  snapshot dated after the child run started is flagged as post-dated.
- **Identity:** a snapshot whose hostname, OS name, Python version, or Git commit disagrees
  with what the child observed directly is flagged as an identity mismatch.
- **Script drift:** a script modified after the snapshot is flagged. An unchanged script
  modification time does not prove the dependencies matched, because packages can change
  without the script changing. Regenerate the snapshot, or capture packages on the child,
  when dependency evidence matters.

### Capture-completeness

`inspect` also tells you which provenance features were **not** enabled, so your next run
can capture more:

- process-tree resources (`[capture.resources].scope = "tree"`) for multiprocessing/Dask/Ray,
- subprocess tracking (`[capture.subprocesses].enabled = true`),
- file-I/O provenance: pubrun does **not** patch `open()` globally, so record inputs/outputs
  by calling `pubrun.open(...)` instead of `open(...)`.

Each suggestion comes with an honest performance note; see [Performance](performance.md).

## Running the benchmark suite on a cluster

The benchmark harness and scheduler submission scripts live under `benchmarks/` (see
`benchmarks/README.md`). Result JSONs capture filesystem type and scheduler allocation context
so results are comparable across nodes.

`pubrun bench` auto-detects the batch scheduler (**Slurm, PBS/Torque, LSF, or SGE/Grid
Engine**, precedence Slurm > PBS > LSF > SGE) from environment variables and submit tools on
`PATH`, and **offers** to submit to a compute node (never without confirmation). Because PBS
and SGE both use `qsub`, an ambiguous environment is reported; pick one with
`--scheduler pbs|sge`. The submit scripts (`submit_bench.sh`, `submit_bench_pbs.sh`,
`submit_bench_lsf.sh`, `submit_bench_sge.sh`) submit to the default queue and let the scheduler
place the job. Treat them as **starting points** and set your site's account/queue/walltime
(only the Slurm path is exercised in CI). Typical flow on a locked-down compute node (no
network / no `gh`): run the benchmark there, then submit the redacted result from the login
node with `pubrun bench --submit-file <result>.redacted.json`.

Tip: `pubrun self-check` on a login node prints an informational nudge suggesting you run the
benchmark on a compute node for representative numbers.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
