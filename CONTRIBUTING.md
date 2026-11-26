# Contributing to pubrun

Thank you for your interest in contributing to `pubrun`. Contributions are welcome, including bug reports, documentation improvements, examples, tests, and code changes. Before making design changes, review [Guiding Principles and Design Decisions](docs/architecture.md#22-guiding-principles-and-design-decisions).

## Development setup

Clone the repository and install the package in editable mode with development and TUI dependencies:

```bash
git clone https://github.com/fariello/pubrun.git
cd pubrun
python -m pip install -e ".[dev,tui]"
```

Installing `.[dev]` alone also works; the TUI tests skip when `textual` is not installed (`tests/test_tui.py` calls `pytest.importorskip("textual")`).

Run the test suite before opening a pull request:

```bash
python -m pytest
```

GitHub Actions CI runs every test suite in random order with `pytest-randomly`, while local and `tox` runs stay in fixed order. Each CI job log prints its seed in the `pytest` header as `Using --randomly-seed=<N>`. To reproduce a CI test order locally, pass that seed on the command line:

```bash
python -m pytest -p randomly --randomly-seed=<N>
```

To measure test coverage locally, pass the coverage flags explicitly (the GitHub Actions CI `ubuntu-latest` Python 3.12 job fails if total coverage drops below 78%):

```bash
python -m pytest --cov=src --cov-report=term-missing
```

To run the intake-script and benchmark contract suites that live outside `tests/`:

```bash
python -m pytest .github/scripts/ benchmarks/test_share_safety.py benchmarks/test_pull_submissions.py benchmarks/test_benchmarks.py
```

Installing `pyyaml` (as the `extra-suites` job in `.github/workflows/ci.yml` does) enables the optional YAML cross-check tests, which skip when `pyyaml` is absent.

Run static type checks locally before opening a pull request. The GitHub Actions CI `typecheck` job runs all three platform checks (`mypy`, `mypy --platform win32`, and `mypy --platform darwin`) and fails on a type error in any module of the package:

```bash
mypy
mypy --platform win32
mypy --platform darwin
```

### Local hooks and path hygiene

Install the pre-commit hooks once per clone:

```bash
pip install pre-commit
pre-commit install
```

`hatch_build.py` stamps commit metadata into wheels (`pubrun/_build_meta.json` and `pubrun/COMMIT`) and source distributions (`src/pubrun/_build_meta.json` and `src/pubrun/COMMIT`) at build time without writing to the working tree. In a source checkout, `pubrun --version` prefers live `git rev-parse HEAD`. `scripts/update_commit_file.py` remains only as a cleanup no-op that removes any stale untracked `src/pubrun/COMMIT` file for clones that installed the retired `post-commit` hook.

One of the hooks (`sanitize-paths`) blocks commits that contain absolute home
directory paths (`/home/<you>/...`), your machine hostname, and (if you enable it)
IP addresses, so machine-specific strings do not leak into the public repo. It
reports and blocks; it does not edit your files. To fix flagged content:

```bash
python3 scripts/sanitize_paths.py --fix          # rewrite staged files
python3 scripts/sanitize_paths.py --fix path...  # rewrite specific files
python3 scripts/sanitize_paths.py --check --all  # audit the whole tree
```

If a flagged value is legitimate (for example a documentation example path), add it
to the `whitelist` in `.sanitize-local.toml` (copy `.sanitize-local.toml.example` to
start). Generic placeholder paths used in tests are already allowed in the tracked
`.sanitize-allow.toml`. The same check runs in CI.

## Reporting issues

Please use GitHub issues to report bugs, request features, or ask questions about expected behavior. When reporting a bug, include:

- The `pubrun` version
- Your Python version
- Your operating system
- The command or script you ran
- The expected behavior
- The observed behavior
- Any relevant traceback or log output

Please do not include secrets, credentials, private file paths, unpublished data, or other sensitive information in issue reports.

## Contributing a benchmark result

Benchmark results help verify pubrun's overhead claims across real hardware, filesystems, and schedulers.

1. From a source checkout, run `pubrun bench` (or `pubrun bench --quick`). By default it writes only a redacted, share-safe file (`*.redacted.json`); add `--unredacted` if you also want the identifying copy for your own analysis. It runs a share-safety check on the redacted file.
2. On an interactive terminal, pubrun then offers to publish the redacted result to GitHub (press Enter to accept). This uses the GitHub CLI (`gh`): it creates an unlisted Gist of the redacted file and opens an issue linking it, or embeds the JSON inline when small. Install and authenticate `gh` first (`gh auth login`) for the one-command path; pubrun tells you if it is missing.
3. No `gh`, or prefer the browser? Use `pubrun bench --prepare-submission` to copy only the redacted file into a clean `pubrun-share/` folder, then attach that `*.redacted.json` file to the benchmark Issue Form (the command prints the link) and check the privacy box.
4. On an HPC login node, pubrun offers to submit the job to Slurm and, if you accept, waits for it to finish and then contributes from the login node. If the wait is interrupted, finish later with `pubrun bench --submit-file <path>`.

A validate-only automated check posts a pass/fail receipt on the issue. It parses the submission only as data and cannot un-share a file, so only ever submit the redacted result (never the unredacted one). Note the published Gist is unlisted, not private: anyone with its URL can read it (the file is redacted, so this is expected).

### Maintainer: collecting submissions

The collected corpus is gathered by a maintainer-run tool, not by any GitHub Action (nothing is stored automatically). From a source checkout, authenticated with `gh`:

```bash
python3 benchmarks/pull_submissions.py            # dry run: show what would happen, write nothing
python3 benchmarks/pull_submissions.py --apply     # store accepted results, re-tag issues, aggregate
```

It fetches benchmark-submission issues, runs the SAME fail-closed validation the server does (schema `pubrun-benchmark/5` + share-safety) plus a 256 KB size cap, stores each accepted redacted result content-addressed under `benchmarks/data/accepted/`, regenerates `summary.csv`/`summary.md`, and re-tags issues (quiet on acceptance, a short reason comment on rejection). It never pushes; you commit the corpus deliberately. See `benchmarks/data/README.md`.

## Pull requests

Pull requests should be focused and reviewable. Before opening a pull request:

- Run the test suite locally.
- Add or update tests for behavior changes.
- Update documentation when user-facing behavior changes.
- Keep changes scoped to one issue or improvement where possible.
- Explain the reason for the change in the pull request description.

Large design changes are easier to review if they begin as an issue or discussion before implementation.

## Testing expectations

`pubrun` records execution context, so tests should avoid depending on machine-specific values, timestamps, absolute paths, or environment details unless those values are part of the behavior being tested.

Where possible, tests should check structure, presence, type, and semantic behavior rather than exact host-specific output.

## Documentation expectations

Documentation should be accurate for the current tagged release. Examples should be runnable by a new user and should avoid relying on private data or unpublished research artifacts.

## Project scope

`pubrun` is intended to provide low-friction, run-level provenance capture for ordinary Python scripts. It is not intended to become a workflow engine, experiment tracking server, data versioning system, container platform, or hosted reproducibility service.

Contributions that preserve this scope are more likely to be accepted.

## Code of conduct

Contributors are expected to adhere to the [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to gfariello@uri.edu.

## Maintainer review

The maintainer will review issues and pull requests as availability permits. Acceptance of a contribution depends on correctness, maintainability, fit with project scope (including maintaining the zero-dependency, lightweight footprint), tests, documentation, and compatibility with existing behavior.
