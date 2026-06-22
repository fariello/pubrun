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

The script also writes ordinary analysis outputs under:

```text
outputs/
```

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

## Notes for reviewers

This example intentionally uses synthetic data so that it can be run without private files, credentials, network access, or domain-specific dependencies.

Generated manifests include machine-specific values such as paths, hostnames, process IDs, timestamps, hardware details, and Python environment details. For that reason, `manifest_excerpt.json` is redacted and shortened rather than copied directly from one developer machine.

The exact output of `pubrun methods` will vary by machine and Python environment. `expected_methods.md` is a representative example, not a byte-for-byte test fixture.
