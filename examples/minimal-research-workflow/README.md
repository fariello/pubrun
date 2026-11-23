# Minimal research workflow example

This example demonstrates how `pubrun` records execution provenance for a small Python analysis. It uses synthetic data and is intended for documentation and review, not as a scientific result.

## What this example shows

This workflow demonstrates:

1. Running an ordinary Python script with `import pubrun`
2. Recording custom analysis events with `pubrun.annotate()`
3. Recording named phases with `pubrun.phase()`
4. Writing ordinary analysis outputs
5. Writing run-attached reports and artifacts
6. Inspecting runs with `pubrun status`
7. Generating methods text with `pubrun methods`
8. Extracting a rerun command with `pubrun rerun`
9. Comparing two runs with `pubrun diff`

## Files

- `analysis.py`: deterministic synthetic analysis using only the Python standard library and `pubrun`
- `README.md`: this guide
- `expected_methods.md`: representative methods output from a completed run
- `manifest_excerpt.json`: redacted excerpt showing the kind of manifest fields produced by `pubrun`

## Run the example

From the repository root:

```bash
cd examples/minimal-research-workflow
python -m pip install pubrun
python analysis.py --seed 42 --n 1000
```

For a local development checkout, use this instead from the repository root:

```bash
python -m pip install -e .
cd examples/minimal-research-workflow
python analysis.py --seed 42 --n 1000
```

After the script completes, `pubrun` writes a local run directory under:

```text
runs/
```

The script also writes ordinary analysis outputs (`synthetic_data.csv` and `summary.json`) under:

```text
examples/minimal-research-workflow/outputs/
```

The outputs go to that directory next to `analysis.py` wherever you run the script from, so running it from another directory leaves no `outputs/` folder there. To write them somewhere else, pass `--output-dir <path>`:

```bash
python analysis.py --seed 42 --n 1000 --output-dir ~/pubrun-example-outputs
```

A relative `--output-dir` is resolved against the current working directory. The directory is created if it does not exist.

## Inspect recent runs

```bash
pubrun status
```

For more detail:

```bash
pubrun status -v
```

## Generate methods text

By default, this uses the most recent run in `./runs`:

```bash
pubrun methods --format markdown
```

You can also pass a specific run directory:

```bash
pubrun methods ./runs/<RUN_DIRECTORY> --format markdown
```

## Extract a rerun command

```bash
pubrun rerun ./runs/<RUN_DIRECTORY>
```

## Compare two runs

Create two runs with different seeds:

```bash
python analysis.py --seed 42 --n 1000
python analysis.py --seed 43 --n 1000
```

Then compare the two run directories:

```bash
pubrun diff ./runs/<FIRST_RUN_DIRECTORY> ./runs/<SECOND_RUN_DIRECTORY> --basic --same --wrap
```

Use `pubrun status -v` to identify the run directories.

## What timing metrics measure

The `timing` section of `manifest.json` (see `manifest_excerpt.json`) separates how long your analysis ran from how long `pubrun` spent recording it:

- `workload_seconds` is your code: from the moment `pubrun` finished its startup capture to the moment the run began finalizing. `elapsed_seconds` reports the same value, and `elapsed_basis: "workload"` says so.
- `startup_overhead_seconds` and `finalization_overhead_seconds` are `pubrun`'s own capture work before and after your code. These three intervals follow each other without overlap, so together they add up to `session_seconds`.
- `background_hardware_seconds` is hardware capture that ran in a background thread *while* your code ran. It overlaps `workload_seconds`, so do not add the two together. `hardware_wait_seconds` is already part of `finalization_overhead_seconds`.
- All durations come from a monotonic clock (`duration_clock: "monotonic"`), so a system clock change during the run cannot make them wrong or negative. The `*_at_utc` fields are calendar timestamps for ordering runs; do not subtract them to get durations.
- The run measures only the tracked interval (`interval_scope: "tracked_interval"`). Here `analysis.py` imports `pubrun` right after a few standard-library imports, so nearly the whole script is covered, but interpreter startup and those earlier imports are not. If you import `pubrun` later in a script, earlier work is not measured.

The numbers in `manifest_excerpt.json` are synthetic but internally consistent.

## Notes for reviewers

This example intentionally uses synthetic data so that it can be run without private files, credentials, network access, or domain-specific dependencies.

Generated manifests include machine-specific values such as paths, hostnames, process IDs, timestamps, hardware details, and Python environment details. For that reason, `manifest_excerpt.json` is redacted and shortened rather than copied directly from one developer machine.

The exact output of `pubrun methods` will vary by machine and Python environment. `expected_methods.md` is a representative example, not a byte-for-byte test fixture.
