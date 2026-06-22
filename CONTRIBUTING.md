# Contributing to pubrun

Thank you for your interest in contributing to `pubrun`. Contributions are welcome, including bug reports, documentation improvements, examples, tests, and code changes.

## Development setup

Clone the repository and install the package in editable mode:

```bash
git clone https://github.com/fariello/pubrun.git
cd pubrun
python -m pip install -e .
```

Run the test suite before opening a pull request:

```bash
python -m pytest
```

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

Contributors are expected to communicate respectfully and constructively. Maintainers may close issues or pull requests that are abusive, off-topic, or inconsistent with the project scope.

## Maintainer review

The maintainer will review issues and pull requests as availability permits. Acceptance of a contribution depends on correctness, maintainability, fit with project scope, tests, documentation, and compatibility with existing behavior.
