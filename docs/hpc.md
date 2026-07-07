[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# HPC & performance diagnosis

`pubrun` runs unmodified on HPC clusters (Slurm, etc.). This page covers the two most
common performance surprises — **slow network filesystems** and **shared-node contention** —
and the two commands that help you spot them: `pubrun self-check` (before/around a run) and
`pubrun inspect` (after a run).

## The most common pitfall: pubrun (or your runs) on a network filesystem

On clusters, home directories and shared venvs are usually mounted over **NFS/Lustre/GPFS**,
which is far slower than node-local disk. If `pubrun` itself is imported from an NFS-mounted
venv, or if your run output directory lives on NFS, startup and per-run I/O can be markedly
slower — and it is easy to mistake this for pubrun overhead.

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
- a **node-wide iowait** hint (`system_iowait_pct`) — *indicative only*; it reflects the
  whole node, not just your run (Linux `/proc/stat` iowait is a system-wide counter).

### The "different system" banner

On HPC you typically **run on a compute node** but **inspect from the head/login node**.
`pubrun inspect` prints a glaring banner when the host you are inspecting from differs from
the host the run executed on, because any live re-checks would reflect the wrong machine.

### Capture-completeness

`inspect` also tells you which provenance features were **not** enabled, so your next run
can capture more:

- process-tree resources (`[capture.resources].scope = "tree"`) for multiprocessing/Dask/Ray,
- subprocess tracking (`[capture.subprocesses].enabled = true`),
- file-I/O provenance — pubrun does **not** patch `open()` globally, so record inputs/outputs
  by calling `pubrun.open(...)` instead of `open(...)`.

Each suggestion comes with an honest performance note; see [Performance](performance.md).

## Running the benchmark suite on a cluster

The benchmark harness and Slurm submission scripts live under `benchmarks/` (see
`benchmarks/README.md`). Result JSONs capture filesystem type and Slurm allocation context
so results are comparable across nodes.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
