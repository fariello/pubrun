# Implementation Plan: Comprehensive pubrun TUI Manager

This document outlines the detailed implementation plan for building a terminal user interface (TUI) for `pubrun`, drawing structural and aesthetic inspiration from the `ocman_tui` controller.

---

## 1. Goal & Overview

`pubrun` traces Python executions and packages dependencies, hardware profiles, and environment setups into structured JSON manifests and log files. Currently, interactions with runs are CLI-only.
The goal is to design and implement a premium, interactive TUI that allows users to:
1. **Explore runs** chronological/grouped views, with filter-by-status and fuzzy search capabilities.
2. **Inspect runs in detail** (timing, git, environment, packages, subprocesses, stdout/stderr logs, event streams).
3. **Compare runs (Diff)** using `pubrun`'s built-in diff engine, highlighting differences in dependency versions, CLI arguments, or hardware.
4. **Generate methods sections** for papers (Markdown/LaTeX) directly in the UI with copy-to-clipboard functionality.
5. **Manage runs**: rerun commands, individual/bulk deletions, and compressing/archiving runs into a subdirectory of the scanned runs directory (e.g. `<runs_dir>/archive/`).
6. **Manage configuration**: view and modify local/global `.pubrun.toml` settings.

---

## 2. Architecture & Dependency Management

To preserve `pubrun`'s core promise of **zero dependencies** for runtime tracing and logging:
*   **Optional TUI Submodule**: All TUI-related code resides under `src/pubrun/tui/`.
*   **Dynamic Importing**: The TUI codebase (which relies on `textual` and `rich`) will **only** be imported dynamically when the command `pubrun tui` is executed.
*   **Graceful Degrade on Missing Dependencies**: If a user runs `pubrun tui` without the required TUI libraries installed, the CLI intercepts the `ImportError` and prints a friendly, informative message:
    > "pubrun is by default zero-dependency based to keep it lean and compatible to use; however, using the GUI based tool does require additional libraries. Run `pip install textual rich` (or `pip install "pubrun[tui]"`) to run the gui."
*   **Optional Extra**: An optional dependency group `tui = ["textual>=0.80.0", "rich>=13.0.0"]` will be defined under `[project.optional-dependencies]` in `pyproject.toml` so developers/users can optionally pull TUI libraries during installation if desired, leaving the default installation dependency-free.

---

## 3. UI Layout & Visual Aesthetics

Inspired by the slate theme in `ocman_tui`, the application will use:
*   **Theme**: Slate/Catppuccin dark color scheme (e.g., `#1e1e2e` background, `#cba6f7` accents, `#89b4fa` headers, and styled success/error statuses).
*   **Layout**:
    *   **Header**: Showing title and system clock.
    *   **Sidebar (Docked Left)**: A `Tree` or custom list widget showing runs sorted by started time (newest first). Each run displays its short ID, script name, and colored status badge. Can be toggled with `Ctrl+S`.
    *   **Workspace (Center/Right)**: A `TabbedContent` container displaying:
        1.  **Details & Transcript**: Manifest details and interactive log explorer.
        2.  **Run Diffing**: Semantic side-by-side or highlighted comparison of two selected runs.
        3.  **Actions & Methods**: Citations viewer, rerun copy helper, compression/archival, and deletion safety controls.
        4.  **TUI Config**: Interactive editor for `.pubrun.toml` settings.
    *   **Footer**: Quick key bindings (e.g., `Ctrl+Q` Quit, `Ctrl+S` Sidebar, `Ctrl+R` Refresh).

---

## 4. Proposed Components & Modules

### `src/pubrun/tui/`
*   **`__init__.py`**: Re-exports public entry points.
*   **`app.py`**: The main `PubrunTUIApp(App)` controller. Coordinates global state (selected runs, configuration, background threads).
*   **`css/style.css`**: Catppuccin-inspired Slate stylesheet with CSS classes for cards, status colors, and buttons.

### `src/pubrun/tui/widgets/`
*   **`sidebar.py` (`RunsSidebar`)**:
    *   Scans runs dynamically using `pubrun.status.scan_runs()`.
    *   Lists run directories with status markers.
    *   Supports a search input to filter runs by ID or script name.
*   **`details.py` (`RunDetailsView`)**:
    *   Displays general metadata, Git repo status, host environment, and CPU/memory specs.
    *   Uses a searchable table/list for the captured Python packages (packages and versions).
    *   Lists captured subprocesses (command line, timing, exit code).
    *   Displays live RSS RAM and CPU usage if the run status is `running` (using live polling via a background thread).
*   **`viewer.py` (`LogViewer`)**:
    *   Displays stdout/stderr or `console.log` contents from the run.
    *   Supports toggling line wrap and quick searches inside the log.
*   **`diff.py` (`DiffView`)**:
    *   Allows selecting a baseline run and a target run.
    *   Applies `pubrun.diff()` with configurable depth (basic, standard, deep).
    *   Renders a clear highlight comparison of differences.
*   **`actions.py` (`ActionsPanel`)**:
    *   **Methods Paragraph**: Displays Markdown and LaTeX methods sections, with a "Copy to Clipboard" button.
    *   **Rerun**: Renders the exact command to replicate, and provides a simple copy-to-clipboard button.
    *   **Archive/Compress**: Packs the selected run into `<runs_dir>/archive/<run_id>.zip` or `.tar.gz` and offers to delete the raw directory.
    *   **Delete**: Invokes a safety modal (typing `yes` to confirm deletion).
    *   **Bulk Clean**: Prunes runs older than X days or with specified statuses (similar to `pubrun clean` CLI).
*   **`config.py` (`ConfigPanel`)**:
    *   Exposes `.pubrun.toml` variables in form fields (Output directory, Console mode, Redaction filters, default Diff ignores).
    *   Saves changes back to the active configuration file.

---

## 5. Verification & Testing Plan

### Automated Verification
*   Implement unit tests in `tests/test_tui.py` mocking the run directory structures.
*   Verify that `pubrun tui` CLI invocation triggers App start.
*   Verify that when Textual/Rich are missing, the command exits gracefully with code 1 and writes the correct message to stderr.

### Manual Verification
*   Execute `pubrun tui` to launch the GUI.
*   Inspect a completed run.
*   Validate the search/filter features on the sidebar list of runs.
*   Validate diff reports with `--basic`/`--deep` modes.
*   Archive a run, verify the archive file is created correctly under the designated `<runs_dir>/archive/` directory, and run deletion with confirmation.
