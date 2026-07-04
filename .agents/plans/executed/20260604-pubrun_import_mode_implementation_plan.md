# pubrun Import-Mode Configuration Implementation Plan

## Purpose

This implementation plan describes how to make pubrun import-time behavior stupid simple for casual users, while giving advanced users precise control over auto-start, global hooks, conflict handling, and diagnostics.

The default experience remains:

```python
import pubrun
```

That line should continue to be the 90% case. Existing scripts should keep working. The new feature set adds an elegant one-line import-mode API:

```python
import pubrun.noauto as pubrun
import pubrun.nopatch as pubrun
import pubrun.quiet as pubrun
```

It also adds project-level configuration, CLI wrapper support, conflict detection, and import provenance metadata so users can understand what happened when a dependency imports pubrun before their own script does.

## Decisions captured in this revision

1. `pubrun/__init__.py` must no longer contain the public API implementation or directly perform irreversible work.
2. The primary one-line override API should be namespaced import modes, not top-level shim modules.
3. Moving the current `__init__.py` implementation to `pubrun.core` is necessary, but not sufficient by itself. The parent package still loads before `pubrun.noauto`, so `__init__.py` needs a small target-aware bootstrap guard.
4. Top-level shim modules can remain optional compatibility or fallback helpers, but they should not be the primary documented user experience if namespaced modes pass the test matrix.
5. Legacy `import pubrun` scripts should continue to behave the same way by default.
6. Legacy `[core].auto_start` and `PUBRUN_AUTO_START` should continue to work. Do not break them in the first implementation.
7. `nopatch` should mean no process-global hooks, not merely no subprocess monkey patching.
8. pubrun should record import provenance in per-run metadata, including the file or package that selected the active import mode and any later conflicting import-mode requests.
9. The CLI wrapper should use an explicit `run` subcommand, such as `pubrun run --quiet -- python script.py`.
10. Documentation and default config should explain these features at the appropriate level without overwhelming new users.

## Current state reviewed

This plan was written against the current public repo and docs.

1. The README emphasizes the simple default: `import pubrun` is the quick-start path and the current docs say that importing pubrun starts an invisible tracer by default.
2. The README and configuration docs already describe `.pubrun.toml` and the environment-variable workaround `PUBRUN_AUTO_START=false`.
3. The configuration reference documents precedence as API overrides, then environment variables, then local project config, then user config, then built-in defaults.
4. The current `src/pubrun/__init__.py` contains both public API definitions and the boot sequence.
5. The current `src/pubrun/__init__.py` applies `PUBRUN_AUTO_START` in the boot sequence rather than through a centralized import-mode resolver.
6. The current docs list `[core].auto_start` as the setting that controls whether `import pubrun` starts a trace.

The implementation should centralize import behavior so it is not split across `__init__.py`, config resolution, tracker startup, and the CLI.

## The critical invariant

`pubrun/__init__.py` should be intentionally small and should not directly perform irreversible work.

In this context, irreversible work means:

1. Starting a run.
2. Creating a run directory.
3. Registering `atexit` handlers.
4. Replacing `sys.stdout` or `sys.stderr`.
5. Monkey patching `subprocess.Popen`, `subprocess.run`, `os.system`, or similar callables.
6. Installing signal handlers.
7. Starting background resource-monitoring threads.
8. Importing capture engines whose imports have process-level side effects.

`__init__.py` may select a mode and delegate to `pubrun.core` only after it decides that the active import is a plain root import. The irreversible work should live in `pubrun.core` and lower-level runtime modules, not directly in `__init__.py`.

This is the key design rule that makes the namespaced import mode possible.

## Why moving to `pubrun.core` does not solve everything by itself

The desired syntax is:

```python
import pubrun.noauto as pubrun
```

Python loads the parent package before loading the submodule. That means `pubrun/__init__.py` executes before `pubrun/noauto.py` gets control.

So this is good but incomplete:

```text
Move current __init__.py implementation to pubrun.core.
```

This is the full requirement:

```text
Move current __init__.py implementation to pubrun.core, and make __init__.py target-aware so it does not import pubrun.core when the active import target is a mode submodule such as pubrun.noauto.
```

Without that guard, `import pubrun.noauto as pubrun` would still load `pubrun/__init__.py` first. If `__init__.py` imports `pubrun.core` unconditionally, auto-start may already have happened before `pubrun.noauto` can select no-auto behavior.

## Desired behavior

### Legacy default

```python
import pubrun
```

Expected behavior:

1. Resolve import mode from config and environment.
2. Default to `auto`.
3. Import `pubrun.core`.
4. Export the public API at `pubrun.*`.
5. Auto-start if the resolved config says to auto-start.
6. Install global hooks if the resolved import behavior permits global hooks.

For existing users with default config, this should feel unchanged.

### Namespaced no-auto

```python
import pubrun.noauto as pubrun
```

Expected behavior:

1. Python enters `pubrun/__init__.py` first.
2. `__init__.py` detects that a pubrun mode submodule import is in progress.
3. `__init__.py` does not select `auto` and does not import `pubrun.core`.
4. Python loads `pubrun/noauto.py`.
5. `pubrun.noauto` selects mode `noauto`.
6. `pubrun.noauto` imports `pubrun.core`.
7. `pubrun.core` exports the same public API but does not auto-start.
8. The alias gives the user the familiar name `pubrun`.

The user then writes:

```python
import pubrun.noauto as pubrun

pubrun.start()
```

### Namespaced no-patch

```python
import pubrun.nopatch as pubrun
```

Expected behavior:

1. Select mode `nopatch` before `pubrun.core` loads.
2. Auto-start normally.
3. Do not install process-global hooks.
4. Still capture static and low-risk metadata.

### Namespaced quiet

```python
import pubrun.quiet as pubrun
```

Expected behavior:

1. Select mode `quiet` before `pubrun.core` loads.
2. Do not auto-start.
3. Do not install process-global hooks.
4. Allow explicit `pubrun.start()` later, using quiet-mode defaults unless overridden.

### Unsupported form

Do not document this as import-time configuration:

```python
from pubrun import noauto
```

Reason: this form imports the parent package first and resolves the name afterward. It is much harder to make reliable as a configuration mechanism and is easier to misunderstand. It can remain a normal submodule import if Python resolves it, but it should not be promised as a way to prevent auto-start.

## File layout

Recommended layout:

```text
src/pubrun/
  __init__.py            # small bootstrap and public root package
  _bootstrap.py          # import-mode state, conflict detection, provenance
  _config_boot.py        # cheap bootstrap config resolver
  _modes.py              # mode definitions and config overlays
  core.py                # current public API and boot behavior moved here
  auto.py                # explicit namespaced default mode
  noauto.py              # namespaced no-auto mode
  nopatch.py             # namespaced no-global-hooks mode
  quiet.py               # namespaced API-only mode
```

Optional compatibility shims, not primary UX:

```text
src/pubrun_noauto.py
src/pubrun_nopatch.py
src/pubrun_quiet.py
```

These can be kept as a fallback for users or environments where namespaced mode detection is disabled, but the preferred public API should be the namespaced import form.

## Boot sequence design

### `pubrun/__init__.py`

`__init__.py` should perform only bootstrap routing.

Conceptual behavior:

```python
from pubrun._bootstrap import is_mode_submodule_import_in_progress

if is_mode_submodule_import_in_progress():
    # Do not select auto.
    # Do not import pubrun.core.
    # Let pubrun.noauto, pubrun.nopatch, pubrun.quiet, or pubrun.auto decide.
    pass
else:
    from pubrun._bootstrap import select_root_import_mode

    select_root_import_mode(selected_by="pubrun")

    from pubrun.core import *  # noqa: F403
```

Important details:

1. Root import still works.
2. Namespaced imports get control before core loads.
3. `__init__.py` itself does not create directories, patch functions, install signal handlers, or start background threads.
4. Public API stability comes from `pubrun.core` being re-exported for root imports.

### Detecting mode submodule imports

Mode submodule detection should be private, small, and heavily tested.

For CPython, the active import stack can expose the currently requested dotted name, such as `pubrun.noauto`. The implementation can inspect the import stack for one of these exact names:

```text
pubrun.auto
pubrun.noauto
pubrun.nopatch
pubrun.quiet
```

Use this only to decide whether `__init__.py` should defer to a mode submodule. Do not use it for broad import spying.

Test this across supported versions and contexts:

1. CPython 3.8 through current supported versions.
2. Editable install.
3. Wheel install.
4. `python script.py`.
5. `python -m package.module`.
6. pytest.
7. IPython or Jupyter if supported.
8. Windows, macOS, and Linux.

If this detection becomes fragile, the implementation should fail safely: preserve legacy `import pubrun`, keep `.pubrun.toml` and CLI wrapper support, and do not document namespaced modes until they are reliable.

## Mode definitions

Use four import modes.

| Mode | auto_start | global_hooks | Meaning |
| --- | --- | --- | --- |
| `auto` | `true` | `true` | Default behavior. Importing pubrun starts tracking and installs normal capture hooks. |
| `noauto` | `false` | `true` | Load the API and default hook policy, but do not start until `pubrun.start()` is called. |
| `nopatch` | `true` | `false` | Start tracking automatically, but do not install global hooks or monkey patches. |
| `quiet` | `false` | `false` | Load the API only. No automatic run and no global hooks unless explicitly overridden later. |

## What `global_hooks = false` means

Use the internal term `global_hooks`, not only `monkey_patch`. It better captures what users mean when they say "do not monkey patch anything."

When `global_hooks = false`, suppress process-global runtime changes, including:

1. `subprocess.Popen` interception.
2. `subprocess.run` interception if added or used.
3. `os.system` interception.
4. Console stream replacement or teeing through `sys.stdout` and `sys.stderr`.
5. Signal handler installation.
6. Future import hooks, audit hooks, tracing hooks, profiling hooks, or similar process-level interception.

A `nopatch` run should still be useful. It can capture static or low-risk information such as process info, Python runtime, packages, environment, Git state, host, hardware, and possibly resource usage if resource monitoring is not considered a global hook.

Open decision: resource monitoring uses a background thread. It is not a monkey patch, but it is active background behavior. Keep it enabled by default for `nopatch` unless there is a separate `background_tasks = false` setting or a future `passive` mode.

## Configuration model

### New `[imports]` section

Add this to the shipped default config with clear comments:

```toml
[imports]
# Import behavior preset.
# auto:    import pubrun starts tracking and enables normal capture hooks.
# noauto:  import pubrun loads the API, but tracking starts only after pubrun.start().
# nopatch: import pubrun starts tracking, but avoids process-global hooks.
# quiet:   import pubrun loads the API only, with no auto-start and no process-global hooks.
mode = "auto"

# What to do if a later import asks for a different effective import behavior.
# ignore: record metadata only.
# warn:   record metadata and emit a warning.
# error:  raise PubrunImportModeConflictError.
on_conflict = "warn"

# Record the file or package that selected the import mode and any conflicting requests.
record_provenance = true

# Number of external caller frames to record for import diagnostics.
provenance_depth = 3

# How file paths should be written in run metadata.
# absolute: full path.
# relative: relative to project root when possible.
# basename: file name only.
# redacted: omit file path.
provenance_path_mode = "relative"

# Maximum number of import-mode requests to retain in metadata.
max_requests = 50
```

Documentation should include the same section, but the README should only show the most important examples.

### Backward-compatible `[core].auto_start`

Continue to support:

```toml
[core]
auto_start = false
```

Mapping rule:

1. If `[imports].mode` is set, it is the canonical import-mode setting.
2. If `[imports].mode` is absent and `[core].auto_start = false`, derive mode `noauto` unless hooks are independently disabled.
3. If `[imports].mode` is absent and `[core].auto_start = true`, derive mode `auto` unless hooks are independently disabled.

Do not break existing configs.

### Environment variables

Add a canonical environment variable:

```bash
PUBRUN_IMPORT_MODE=quiet
```

Keep supporting existing behavior:

```bash
PUBRUN_AUTO_START=false
```

Recommended environment variables:

| Variable | Meaning |
| --- | --- |
| `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, or `quiet`. |
| `PUBRUN_AUTO_START` | Legacy alias for the auto-start portion of import behavior. |
| `PUBRUN_GLOBAL_HOOKS` | Optional explicit control over process-global hooks. |
| `PUBRUN_IMPORT_CONFLICT` | Maps to `[imports].on_conflict`. |
| `PUBRUN_IMPORT_PROVENANCE` | Maps to `[imports].record_provenance`. |

Recommendation on deprecation:

Do not emit a noisy import-time deprecation warning for `PUBRUN_AUTO_START` in the first implementation. It is documented today, and import-time warnings can be unpleasant in batch jobs and notebooks. Instead:

1. Keep it fully supported as a legacy alias.
2. Prefer `PUBRUN_IMPORT_MODE` in new docs.
3. Mention the legacy alias in the configuration docs.
4. If deprecation is ever desired, use a long major-version migration window and surface it through `pubrun --check-config` or `pubrun --info` before considering runtime warnings.

### Precedence

For root import mode resolution:

1. Environment variables.
2. Local project `.pubrun.toml`.
3. Local project deep config.
4. User config.
5. Built-in defaults.

For explicit namespaced import mode:

1. The explicit import preset wins for mode selection.
2. Environment and config still provide other settings such as conflict policy, provenance depth, output directory, capture depth, and redaction.
3. If the explicit preset conflicts with `[imports].mode`, do not treat that as an import conflict. The explicit import is closer to the code and should win. Record the selected source in metadata.

For explicit runtime calls:

1. `pubrun.start(...)` API overrides remain highest priority for runtime configuration.
2. API overrides cannot undo import-time side effects that already happened. This is why conflict detection and provenance matter.

## Import conflict detection

Conflict detection should compare effective behavior, not import text.

No warning:

```python
import pubrun
import pubrun
```

No warning if behavior matches:

```python
import pubrun
import pubrun.auto as pubrun
```

Warning or error:

```python
import pubrun
import pubrun.noauto as pubrun
```

Warning or error:

```python
import pubrun.noauto as pubrun
import pubrun.nopatch as pubrun
```

The first effective behavior should remain active. A later conflicting request should not silently mutate already-initialized runtime behavior.

### Config name

Use one setting rather than two booleans:

```toml
[imports]
on_conflict = "warn"
```

Allowed values:

| Value | Behavior |
| --- | --- |
| `ignore` | Record metadata, do not warn, do not raise. |
| `warn` | Record metadata and emit a warning. |
| `error` | Record metadata if possible, then raise `PubrunImportModeConflictError`. |

### Error and warning classes

Add:

```python
class PubrunImportModeConflictError(RuntimeError):
    """Raised when conflicting pubrun import modes are configured to error."""


class PubrunImportModeConflictWarning(RuntimeWarning):
    """Warns that a conflicting pubrun import mode was requested."""


class PubrunImportModeTooLateWarning(RuntimeWarning):
    """Warns that an import-mode request happened after pubrun.core loaded."""
```

### Warning language

Recommended warning text:

```text
Conflicting pubrun import modes detected. pubrun was already initialized with mode 'auto' from library.py:12, but script.py:4 requested mode 'noauto'. The first effective behavior remains active. Set [imports].on_conflict = 'error' to fail fast or 'ignore' to suppress this warning. Use .pubrun.toml or 'pubrun run --quiet -- python script.py' if a dependency imports pubrun before your script does.
```

## Import provenance metadata

### Why this matters

If a dependency imports pubrun before the user's script does, the user may not know why a run directory appeared or why hooks are active. Warnings help during execution. Manifest metadata helps later, especially in batch jobs, notebooks, CI, and HPC workflows.

### What can and cannot be recorded

Python caches imported modules. A second identical `import pubrun` usually does not re-execute `pubrun/__init__.py`. Therefore, pubrun should not try to record every plain import without installing a global import hook.

Do not install a global import hook just to count imports. That would add overhead and contradict the purpose of `nopatch`.

Record instead:

1. The first observed import-mode selector.
2. The first external caller frames for that selector.
3. Any later import-mode selectors that actually execute.
4. Conflicting mode requests.
5. Whether a conflicting request happened after `pubrun.core` was already loaded.
6. The effective behavior that remained active.

### Manifest section

Add a top-level manifest section:

```json
{
  "pubrun_imports": {
    "selected_mode": "auto",
    "selected_behavior": {
      "auto_start": true,
      "global_hooks": true
    },
    "selected_by": "pubrun",
    "selected_source": "default",
    "selected_at_utc": 1780250544.068,
    "core_loaded": true,
    "conflict_policy": "warn",
    "conflicts_detected": 0,
    "requests": []
  }
}
```

Each request should include:

```json
{
  "timestamp_utc": 1780250544.068,
  "requested_mode": "noauto",
  "selected_by": "pubrun.noauto",
  "effective_behavior": {
    "auto_start": false,
    "global_hooks": true
  },
  "selected": false,
  "conflict": true,
  "core_loaded_at_request": true,
  "message": "Requested mode differs from already-selected mode.",
  "callers": [
    {
      "filename": "script.py",
      "line_number": 4,
      "function": "<module>",
      "module": "__main__",
      "package": null,
      "relationship": "entrypoint"
    }
  ]
}
```

### Caller classification

Classify callers where practical:

| Relationship | Meaning |
| --- | --- |
| `entrypoint` | The top-level script, notebook cell, or module being run. |
| `project` | A file under the current project root. |
| `site-packages` | A dependency installed in site-packages. |
| `stdlib` | Python standard library. |
| `pubrun-internal` | Internal pubrun frame, usually excluded. |
| `unknown` | Could not classify. |

For site-packages callers, attempt to include the top-level package and distribution name if this can be done cheaply.

### Privacy controls

Paths can reveal names and project structure. Default should be useful but not overly revealing.

```toml
[imports]
provenance_path_mode = "relative"
```

Allowed values:

| Value | Behavior |
| --- | --- |
| `absolute` | Full absolute path. Best diagnostics, least private. |
| `relative` | Relative to project root when possible. Recommended default. |
| `basename` | File name only. Useful for sharing manifests. |
| `redacted` | Suppress file path entirely. |

### Efficient stack capture

Use `sys._getframe()` for the common path if possible. Avoid `inspect.stack(context=...)` unless needed for readability or fallback diagnostics, because it is slower and can touch more frame metadata.

Capture only a small number of external frames. Filter out:

1. pubrun internals.
2. importlib internals.
3. standard import machinery.

## `pbr` alias convention

The alias is a user-side binding. pubrun cannot reliably know whether the caller wrote:

```python
import pubrun.nopatch as pubrun
```

or:

```python
import pubrun.nopatch as pbr
```

So `pbr` should be a documentation convention only, not something that changes runtime behavior.

It is a nice optional convention for concise examples and a pleasant nod to the existing `pbr me` easter egg:

```python
import pubrun.quiet as pbr

pbr.start()
```

Recommended documentation approach:

1. Use `as pubrun` in primary docs because it is obvious.
2. Mention `as pbr` as a shorter optional alias in an advanced or playful note.
3. Do not make any API behavior depend on the alias.

## CLI wrapper

Add an explicit `run` subcommand:

```bash
pubrun run -- python script.py
pubrun run --quiet -- python script.py
pubrun run --noauto -- python script.py
pubrun run --nopatch -- python script.py
```

The double dash separates pubrun wrapper options from the target command.

The wrapper should:

1. Resolve the requested import mode.
2. Spawn the target command in a child process.
3. Set `PUBRUN_IMPORT_MODE` in the child environment.
4. Set conflict and provenance environment variables if requested.
5. Return the child process exit code.
6. Avoid creating a run in the wrapper process unless explicitly intended.
7. Avoid importing `pubrun.core` in the wrapper process if the CLI can handle this through lightweight modules.

This is especially useful for shell scripts, CI, Slurm, HPC submission scripts, and cases where source code should remain unchanged.

## Optional top-level shims

The primary API should be namespaced:

```python
import pubrun.noauto as pubrun
```

Optional top-level shims can still be provided:

```python
import pubrun_noauto as pubrun
import pubrun_nopatch as pubrun
import pubrun_quiet as pubrun
```

Use cases:

1. Compatibility fallback if namespaced mode detection is disabled or unsupported in a particular environment.
2. Users who strongly prefer top-level module aliases.
3. Test cases that need an import path that cannot accidentally trigger parent package work.

If provided, do not lead with them in the README. Put them in advanced docs or troubleshooting.

## Legacy behavior

### What happens to existing scripts

Existing scripts that say:

```python
import pubrun
```

should continue to work as they do today.

With default config:

1. `import pubrun` selects mode `auto`.
2. `pubrun.core` loads.
3. The public API is exported at the root package.
4. Tracking starts automatically.
5. Normal hooks are installed.
6. A run is written when the process exits.

Existing scripts that say:

```python
import pubrun

pubrun.start()
```

should also continue to work. The current active-run reference behavior should remain stable.

Existing scripts using:

```toml
[core]
auto_start = false
```

should still import the API without automatically starting a run.

Existing scripts using:

```python
import os
os.environ["PUBRUN_AUTO_START"] = "false"

import pubrun
```

should still work. The new docs should prefer this instead:

```python
import pubrun.noauto as pubrun
```

or this:

```toml
[imports]
mode = "noauto"
```

but the old environment variable path should not break.

### What changes internally

The root package becomes a router rather than the implementation module. `pubrun.core` holds the implementation. The root package re-exports the same public names so user code does not need to change.

Implementation must preserve:

1. `pubrun.start`.
2. `pubrun.stop`.
3. `pubrun.annotate`.
4. `pubrun.phase`.
5. `pubrun.audit_run`.
6. `pubrun.tracked_run`.
7. `pubrun.diff`.
8. `pubrun.get_current_run`.
9. `pubrun.__version__`.
10. `pubrun.__all__`.

### New warnings users may see

Users should only see new warnings when there is a meaningful conflict.

No warning:

```python
import pubrun
import pubrun
```

Warning by default:

```python
import pubrun
import pubrun.noauto as pubrun
```

Reason: `pubrun.core` was already loaded, so no-auto is too late to prevent side effects.

If a library imports pubrun first, users can control this globally by using:

```toml
[imports]
mode = "quiet"
```

or:

```bash
pubrun run --quiet -- python script.py
```

Those mechanisms apply before the user's script or dependency import order becomes a problem.

## Runtime APIs and unpatching

Preventing hooks is cleaner than undoing hooks.

Support:

```python
import pubrun.nopatch as pubrun
```

Do not make this the main story:

```python
import pubrun
pubrun.unpatch()
```

An `unpatch()` API can exist as a best-effort operational tool, but it should not be the primary configuration pattern because:

1. Other code may have already captured references to patched functions.
2. Other libraries may patch the same functions.
3. Restoring original functions can accidentally remove another wrapper.
4. Signal handlers and stream wrappers can be hard to unwind perfectly.
5. Undoing a side effect is more fragile than never doing it.

If `unpatch()` is added, it should be documented as best effort and should report what it restored, skipped, or could not safely restore.

## Additional configurable options to consider

Keep the first implementation small, but consider these as useful additions:

### `global_hooks`

Allow advanced users to override the hook part without selecting a preset:

```toml
[imports]
global_hooks = false
```

This can make config expressive without adding too many modes.

### `background_tasks`

Consider a future setting:

```toml
[imports]
background_tasks = false
```

This would suppress resource-monitoring threads and any future background work. Do not include this in the initial mode model unless needed. Too many switches will dilute the simplicity.

### `on_legacy_config`

Optional future diagnostic setting:

```toml
[imports]
on_legacy_config = "ignore"
```

Allowed values could be `ignore`, `warn`, or `error`. This would control whether use of legacy settings such as `PUBRUN_AUTO_START` is reported. Recommendation: do not add this now unless you plan a formal deprecation.

## Manifest, lock file, and reports

### Manifest

Add `pubrun_imports` as described above.

### Lock file

Add a small subset to `.pubrun.lock`:

```json
{
  "import_mode": "auto",
  "import_selected_by": "pubrun",
  "import_conflicts_detected": 0,
  "first_import_caller": "script.py:1"
}
```

### `config.resolved.json`

Include the expanded import preset so users can see that:

```toml
[imports]
mode = "nopatch"
```

became:

```toml
[core]
auto_start = true

[capture.subprocesses]
enabled = false

[console]
capture_mode = "off"

[capture.signals]
enabled = false
```

### Reports

If conflicts occurred, `pubrun report` should show a short diagnostic block:

```text
Import mode: auto
Selected by: pubrun from library.py:12
Conflicts: 1
Later request: noauto from script.py:4, ignored because core was already loaded
```

`pubrun status -v` should show compact import diagnostics:

```text
import: auto by library.py:12, conflicts=1
```

## Documentation updates

### README

Keep the quick start simple:

```python
import pubrun  # That's it 90% of the time.
```

Then add a compact section:

```python
import pubrun.noauto as pubrun   # Load API now, start later.
import pubrun.nopatch as pubrun  # Start now, no process-global hooks.
import pubrun.quiet as pubrun    # API only, no auto-start, no process-global hooks.
```

Mention project-level config:

```toml
[imports]
mode = "quiet"
```

### Configuration reference

Add the full `[imports]` section with defaults and comments.

Also include a compatibility note:

```toml
[core]
auto_start = false
```

still works and is equivalent to `mode = "noauto"` when `[imports].mode` is absent.

### Troubleshooting

Add a section named "When a dependency imports pubrun first".

Suggested text:

```text
The first effective import mode wins. If a dependency imports pubrun before your script requests a different mode, pubrun will warn by default and record the import provenance in manifest.json. To control behavior process-wide, use .pubrun.toml or the pubrun run wrapper.
```

### Default config comments

The shipped default config should include concise comments directly above each new `[imports]` setting. These comments should be helpful enough that `pubrun --show-config` serves as lightweight documentation.

## Testing plan

Use subprocess tests for import behavior. Avoid relying on `importlib.reload()` for core behavior because import caching is part of what must be tested.

### Root import tests

1. `import pubrun` preserves current default behavior.
2. `import pubrun` with `[core].auto_start = false` still suppresses auto-start.
3. `import pubrun` with `[imports].mode = "quiet"` suppresses auto-start and global hooks.
4. `PUBRUN_AUTO_START=false` still suppresses auto-start.
5. `PUBRUN_IMPORT_MODE=quiet` works.

### Namespaced mode tests

1. `import pubrun.noauto as pubrun` does not auto-start.
2. `import pubrun.nopatch as pubrun` auto-starts but does not install global hooks.
3. `import pubrun.quiet as pubrun` does not auto-start and does not install global hooks.
4. `import pubrun.auto as pubrun` matches default auto behavior.
5. `from pubrun import noauto` is not documented as configuration and should not be required to prevent auto-start.

### Conflict tests

1. `import pubrun; import pubrun` is silent.
2. `import pubrun; import pubrun.auto as pubrun` is silent if behavior matches.
3. `import pubrun; import pubrun.noauto as pubrun` warns by default.
4. Same conflict raises when `[imports].on_conflict = "error"`.
5. Same conflict records metadata when `[imports].on_conflict = "ignore"`.
6. Conflicting requests record caller provenance.

### Hook tests

For `nopatch` and `quiet`, assert that these are not installed or modified:

1. Subprocess interception.
2. `os.system` interception.
3. Console stream replacement.
4. Signal handlers.

### Metadata tests

1. Manifest includes `pubrun_imports`.
2. Lock file includes compact import information.
3. `config.resolved.json` includes expanded mode overlay.
4. Provenance path modes work: `absolute`, `relative`, `basename`, `redacted`.
5. Max request retention works.

### Platform and environment matrix

Test namespaced mode detection across:

1. CPython 3.8 through current supported versions.
2. Windows, macOS, and Linux.
3. Editable install.
4. Wheel install.
5. pytest.
6. `python -m`.
7. IPython or Jupyter if supported.
8. PyPy if supported.

## Migration plan

### Phase 1: Centralize import config

1. Add `[imports]` defaults to the shipped default config.
2. Add `_modes.py` and `_config_boot.py`.
3. Move `PUBRUN_AUTO_START` handling into centralized import config resolution.
4. Keep `[core].auto_start` working.
5. Add tests proving legacy config and environment variables still work.

### Phase 2: Split implementation from package initializer

1. Move current public API and boot sequence from `pubrun/__init__.py` to `pubrun/core.py`.
2. Keep `__all__` stable.
3. Keep `import pubrun` behavior unchanged.
4. Add a root import test before adding namespaced modes.

### Phase 3: Add bootstrap state

1. Add `_bootstrap.py`.
2. Record selected mode, effective behavior, first importer, and core-loaded state.
3. Add conflict detection.
4. Add warning and error classes.

### Phase 4: Add target-aware `__init__.py`

1. Add `is_mode_submodule_import_in_progress()`.
2. Make `__init__.py` defer core import when importing mode submodules.
3. Add `pubrun.auto`, `pubrun.noauto`, `pubrun.nopatch`, and `pubrun.quiet`.
4. Add subprocess tests for every import form.

### Phase 5: Add metadata

1. Add `pubrun_imports` to manifest.
2. Add compact import data to `.pubrun.lock`.
3. Add import diagnostics to report and status.
4. Update manifest schema.

### Phase 6: Add CLI wrapper

1. Add `pubrun run`.
2. Set `PUBRUN_IMPORT_MODE` in the child environment.
3. Return child process exit code.
4. Document examples for CI, shell scripts, and HPC.

### Phase 7: Optional top-level shims

1. Add `pubrun_noauto.py`, `pubrun_nopatch.py`, and `pubrun_quiet.py` only if desired as compatibility helpers.
2. Do not lead with them if namespaced modes are reliable.

## Open design decisions

### Should `nopatch` disable signal handlers?

Recommendation: yes. Signal handler installation is global process behavior.

### Should `nopatch` disable console capture?

Recommendation: yes. Console capture wraps process-global streams.

### Should `nopatch` disable resource monitoring?

Recommendation: not initially. Resource monitoring is background behavior, but not monkey patching. Add `background_tasks = false` or a future `passive` mode if users ask for no background activity.

### Should `PUBRUN_AUTO_START` be deprecated?

Recommendation: not now. Keep it as a compatibility alias. Prefer `PUBRUN_IMPORT_MODE` in new docs.

### Should `pbr` be documented?

Recommendation: yes, lightly. Use `as pubrun` in primary docs and mention `as pbr` as an optional short alias.

## Final user experience

### Default

```python
import pubrun
```

### One-file no auto-start

```python
import pubrun.noauto as pubrun

pubrun.start()
```

### One-file no global hooks

```python
import pubrun.nopatch as pubrun
```

### One-file quiet API-only mode

```python
import pubrun.quiet as pubrun
```

### Optional short alias

```python
import pubrun.quiet as pbr

pbr.start()
```

### Project-wide quiet mode

```toml
[imports]
mode = "quiet"
```

Then code remains:

```python
import pubrun
```

### Strict conflict detection

```toml
[imports]
on_conflict = "error"
```

### Suppress conflict warnings while keeping metadata

```toml
[imports]
on_conflict = "ignore"
```

### CLI wrapper

```bash
pubrun run --quiet -- python script.py
```
