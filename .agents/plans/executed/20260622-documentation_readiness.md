# Implementation Plan: Documentation Readiness and API/CLI Audit

This plan details the updates to finalize and complete the `pubrun` documentation directory (`docs/`) for public adoption. It audits missing public APIs and CLI commands, adds the research usage page, and ensures consistent version/dependency statements across all project metadata files.

All changes will be implemented **locally** first. No commits will be pushed to the remote repository.

---

## 1. Task Breakdown and Status

| Task | Owner | Action Plan / Implementation Details |
| :--- | :---: | :--- |
| **Add `docs/research-use.md`** | GF (User) | **AI Action (Pending Approval)**: Copy the draft from `tmp/JOSS-paper/pubrun_research_use_draft.md` to `docs/research-use.md`. Remove any JOSS references (replacing them with generic terms like "public release" or "submission"). |
| **Audit API docs (`docs/api.md`)** | GF (User) | **AI Action (Pending Approval)**: Document the missing public API functions `pubrun.report(name, data)` and `pubrun.artifact(filename, content)` to ensure all public methods are detailed with purpose, arguments, return values, and minimal examples. |
| **Audit CLI docs (`docs/cli.md`)** | GF (User) | **AI Action (Pending Approval)**: Add documentation for the missing `tui` subcommand in `docs/cli.md`. |
| **Align Python/dependency wording** | GF (User) | **AI Action (Pending Approval)**: Audit and align all statements regarding Python compatibility (Python 3.8+ supported, standard-library-only on 3.11+, and `tomli` fallback on 3.8–3.10) in `README.md`, `pyproject.toml`, `CITATION.cff`, `docs/functional_spec.md`, and any other documentation files. |

---

## 2. Proposed Changes

### A. Add `docs/research-use.md`

We will write `docs/research-use.md` based on the local draft but stripped of any JOSS references:
*   *Draft text to modify (Line 22)*: `"before JOSS submission"` -> `"before public release"`.
*   Add a link to the new `docs/research-use.md` page in the documentation index bar at the top/bottom of all `.md` files.

### B. Audit API Docs (`docs/api.md`)

Add a new section for Custom Artifacts and Reports to document the missing public methods:

```markdown
## 7. Custom Artifacts and Reports

### `pubrun.report(name: str, data: Any)`
Saves a structured custom report directly to the run directory.
*   **Arguments**:
    *   `name`: The base filename (without extension).
    *   `data`: The payload to write. If `data` is a `dict` or `list`, it is serialized as JSON (`{name}.json`). Otherwise, it is written as plain text (`{name}.txt`).
*   **Return value**: None.
*   **Example**:
    ```python
    import pubrun
    pubrun.report("eval_metrics", {"accuracy": 0.942, "loss": 0.108})
    ```

### `pubrun.artifact(filename: str, content: Any)`
Writes a raw artifact file (such as CSV data, text, or binary bytes) directly to the active run directory.
*   **Arguments**:
    *   `filename`: The output filename (including extension, e.g., `"data.csv"`).
    *   `content`: The file content. If `content` is `bytes`, it is written using binary mode; otherwise, it is cast to `str` and written as UTF-8 text.
*   **Return value**: None.
*   **Example**:
    ```python
    import pubrun
    pubrun.artifact("predictions.csv", "id,pred\n1,0.94\n2,0.12")
    ```
```

### C. Audit CLI Docs (`docs/cli.md`)

Add the missing `ui` subcommand (along with `tui` and `gui` aliases) under the "Commands" section:

```markdown
### `ui` — Interactive Dashboard

Launches the terminal user interface (TUI) dashboard to browse, inspect, and manage run records interactively.

```bash
pubrun ui [--dir PATH]
```

**Aliases:** `tui`, `gui`

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the directory containing the runs (default: configured `output_dir` or `./runs`) |

**Example:**
```bash
pubrun ui
pubrun gui
```
```

### D. Align Python/Dependency Wording

Verify and align all files to use the exact uniform statement:
*   **README.md**:
    *   Line 9: `[^1]: On Python 3.11+, pubrun uses only the standard library. On Python 3.8–3.10, the sole runtime dependency is tomli...` (Aligned)
    *   Line 19: `On Python 3.8–3.10, this also installs tomli... On Python 3.11+, there are zero runtime dependencies.` (Aligned)
*   **pyproject.toml**:
    *   Line 14: `requires-python = ">=3.8"` (Aligned)
    *   Line 41: `dependencies = ["tomli>=1.1.0; python_version < '3.11'"]` (Aligned)
*   **CITATION.cff**:
    *   Line 13: `pubrun is a zero-dependency, manifest-first Python framework...` (Needs update to add the clarification for Python 3.8–3.10, or keep it generic as "zero-dependency on Python 3.11+"). We will update CFF abstract:
        *   *Proposed Abstract*: `pubrun is a zero-dependency (on Python 3.11+), manifest-first Python framework for tracking computational provenance, environment state, and execution metadata without requiring complex virtualization overhead.`
*   **docs/functional_spec.md**:
    *   Line 356: `TOML is the required format, leveraging Python 3.11+ tomllib (with tomli fallback for Python 3.8–3.10).` (Aligned)

---

## 3. Verification Plan

### Automated Tests
Run `pytest` locally to verify that all 554 tests pass.

### Documentation Navigation Check
Verify that all docs render correctly, links work, and the top/bottom navigation indices are updated to link to the new `research-use.md` file.

### Twine Check
Verify that rebuilding the package compiles correctly and twine check passes:
```bash
rm -rf dist/*
python -m build
twine check dist/*
```
