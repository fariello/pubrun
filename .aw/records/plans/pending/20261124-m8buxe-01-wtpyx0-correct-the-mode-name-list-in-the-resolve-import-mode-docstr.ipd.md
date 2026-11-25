# IPD: Correct the mode_name list in the resolve_import_mode docstring

- Date: 2026-11-24
- Kind: child
- Concern: The docstring of `src/pubrun/_config_boot.py::resolve_import_mode` says that the returned `mode_name` is one of `"auto"`, `"noauto"`, `"nopatch"`, `"quiet"`. No `"quiet"` mode exists, and the list omits `"noconsole"`, `"minimal"`, and `"full"`, which the function can return.
- Scope: In `src/pubrun/_config_boot.py`, replace the `mode_name is one of:` line of the `resolve_import_mode` docstring with a two-line sentence that lists the six valid import modes. No code, other docstring line, or other file changes.
- Scope-Paths: src/pubrun/_config_boot.py
- Item-Dependencies: none
- Status: to-review
- Short-Description: List the six valid import modes in the resolve_import_mode docstring
- Work-Kind: followup
- Priority: low
- From-Backlog: m8buxe
- Set: m8buxe
- Order: 1
- Highest E allocated: 01
- Author: opencode
- Id: wtpyx0

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (opencode): graduated from backlog item `m8buxe` into a review-ready plan.
- 2026-11-25 draft (opencode): created.

## Goal

A developer who reads the `resolve_import_mode` docstring learns the exact set of mode names that the function can return. After this plan, the docstring lists the six keys of `src/pubrun/_modes.py::MODES`: `"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, and `"full"`, and it no longer names the nonexistent `"quiet"` mode.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Docstring

- [ ] E-01 In `src/pubrun/_config_boot.py`, in the `Returns:` section of the `resolve_import_mode` docstring, replace the line `mode_name is one of: "auto", "noauto", "nopatch", "quiet".` with the two lines given in "Proposed changes" item 1.
  - Depends on: none
  - Expected outcome: (1) The `Returns:` section of the docstring reads exactly as shown in "Proposed changes" item 1. (2) The `(mode_name, source) where ...` line and the two `source is one of:` lines are unchanged. (3) No executable line of `src/pubrun/_config_boot.py` changes, and no other line of the file changes. (4) The string `"quiet"` no longer appears in `src/pubrun/_config_boot.py`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `src/pubrun/_modes.py` is the single source of truth for import modes. `MODES` maps each mode name to its behavior flags, and `VALID_MODES = frozenset(MODES.keys())`. `resolve_import_mode` accepts a mode from `PUBRUN_IMPORT_MODE` or `[imports].mode` only when the value is in `VALID_MODES`.
- Docstrings in `src/pubrun/_config_boot.py` use Google style (`Returns:`) and indent a continuation line by four extra spaces, as the existing `source is one of:` entry does.
- The same stale-list defect was fixed once before: `CHANGELOG.md` records "Removed a stale `pubrun.quiet` reference in the `noauto` docstring (the mode is `noconsole`)." That fix did not reach `resolve_import_mode`.
- The executed plan `.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md` added `full` by extending `MODES` and states that `resolve_import_mode` needs no extra registration. It did not update this docstring, which is how `"full"` came to be missing.
- `AGENTS.md` "Agent execution contract" exempts code comments from the dash rule. The new docstring text still uses no em or en dashes, so it matches the surrounding lines.
- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone: an offset expires before this plan executes (advisory `IPD-C801`).

## Findings

Measured at authoring on Linux at `HEAD` `79ae65d`.

The current `Returns:` section of `src/pubrun/_config_boot.py::resolve_import_mode`, printed with `PYTHONPATH=src python3 -c "import pubrun._config_boot as m; print(m.resolve_import_mode.__doc__)"`:

```text
Returns:
    (mode_name, source) where source describes where the mode came from.
    mode_name is one of: "auto", "noauto", "nopatch", "quiet".
    source is one of: "env:PUBRUN_IMPORT_MODE", "env:PUBRUN_AUTO_START",
        "config:[imports].mode", "config:[core].auto_start", "default".
```

The valid modes, printed with `PYTHONPATH=src python3 -c "from pubrun._modes import VALID_MODES; print(sorted(VALID_MODES))"`:

```text
['auto', 'full', 'minimal', 'noauto', 'noconsole', 'nopatch']
```

A probe at authoring called `resolve_import_mode()` once for each candidate name, with `PUBRUN_AUTO_START` set to an empty string and `PUBRUN_IMPORT_MODE` set to the name. Run from the repository root:

```sh
for m in auto noauto nopatch noconsole minimal full quiet; do PUBRUN_AUTO_START= PUBRUN_IMPORT_MODE=$m PYTHONPATH=src python3 -c "from pubrun._config_boot import resolve_import_mode as r; print('$m', r())"; done
```

It printed:

```text
auto ('auto', 'env:PUBRUN_IMPORT_MODE')
noauto ('noauto', 'env:PUBRUN_IMPORT_MODE')
nopatch ('nopatch', 'env:PUBRUN_IMPORT_MODE')
noconsole ('noconsole', 'env:PUBRUN_IMPORT_MODE')
minimal ('minimal', 'env:PUBRUN_IMPORT_MODE')
full ('full', 'env:PUBRUN_IMPORT_MODE')
quiet ('auto', 'default')
```

The function returns each of the six valid modes. It rejects `quiet` and falls back to the default `"auto"`. The docstring therefore names one value the function never returns and omits three values it does return.

| Mode name | In `VALID_MODES` | Returned by `resolve_import_mode` | Listed in the docstring today |
|---|---|---|---|
| `auto` | yes | yes | yes |
| `noauto` | yes | yes | yes |
| `nopatch` | yes | yes | yes |
| `noconsole` | yes | yes | no |
| `minimal` | yes | yes | no |
| `full` | yes | yes | no |
| `quiet` | no | no | yes |

`src/pubrun/_config_boot.py` has pre-existing `ruff check` findings (for example `F401` for the unused `get_mode_behavior` import and `FA100` on the `typing` annotations). This plan does not fix them, and validation therefore checks only that the edit adds no finding.

No diagram is included. The change affects one docstring sentence of one function, which is a single entity with no process (technical writing standard, requirement 12(c)).

## Proposed changes (ordered, validatable)

1. **Docstring line (E-01).** Replace this line of the `resolve_import_mode` docstring:

   ```python
           mode_name is one of: "auto", "noauto", "nopatch", "quiet".
   ```

   with these two lines, keeping the eight-space indentation of the `Returns:` entries and the twelve-space indentation of a continuation line:

   ```python
           mode_name is one of the keys of ``pubrun._modes.MODES``: "auto",
               "noauto", "nopatch", "noconsole", "minimal", or "full".
   ```

   After the change, the full `Returns:` section reads:

   ```python
       Returns:
           (mode_name, source) where source describes where the mode came from.
           mode_name is one of the keys of ``pubrun._modes.MODES``: "auto",
               "noauto", "nopatch", "noconsole", "minimal", or "full".
           source is one of: "env:PUBRUN_IMPORT_MODE", "env:PUBRUN_AUTO_START",
               "config:[imports].mode", "config:[core].auto_start", "default".
   ```

   Naming `pubrun._modes.MODES` tells a reader where the list is defined, so a future mode added there has an obvious place to check.

## Deferred / out of scope (with reason)

- Updating the stale mode list in the `src/pubrun/_bootstrap.py::select_mode` docstring, which reads `mode: One of "auto", "noauto", "nopatch", "minimal".` It is a separate backlog item in a different file and does not depend on this plan.
  - Carrier: szf342
- Fixing the pre-existing `ruff check` findings in `src/pubrun/_config_boot.py`, such as the unused `get_mode_behavior` import. They are unrelated to the docstring, and the backlog item asks only for the docstring correction.
  - Carrier-Declined: lint cleanup of this module is not requested by any backlog item, and mixing it into a docstring fix would widen the reviewed diff.
- Adding a test that asserts the docstring text. `AGENTS.md` "Agent execution contract" forbids tests that pin docstring text.
  - Carrier-Declined: a docstring-pinning test is prohibited by the repository's testing rule.
- A `CHANGELOG.md` entry. The change corrects an internal docstring and changes no behavior.
  - Carrier-Declined: an internal docstring correction changes no user-visible behavior, so it does not meet the changelog's bar.

## Scope check

- Over-scope: none. The plan edits one docstring sentence.
- Under-scope: none. No code, test, or documentation change is needed, because `resolve_import_mode` already returns the six modes (Findings probe), and no user-facing document quotes this docstring.

## Required tests / validation

- `git diff -- src/pubrun/_config_boot.py` shows exactly one removed line and two added lines, all inside the `resolve_import_mode` docstring, with the added lines identical to "Proposed changes" item 1.
- `PYTHONPATH=src python3 -c "import pubrun._config_boot as m; print(m.resolve_import_mode.__doc__)"` prints a `Returns:` section that matches "Proposed changes" item 1.
- `grep -c '"quiet"' src/pubrun/_config_boot.py` prints `0`.
- `git diff -U0 -- src/pubrun/_config_boot.py | grep '^+[^+]' | grep -cP '[\x{2013}\x{2014}]'` prints `0`.
- `ruff check src/pubrun/_config_boot.py` reports the same number of findings after the edit as before it (19 at authoring). Record both counts.
- A runtime check confirms the documented list: run the Findings probe again and observe the same seven output lines. The code path that produces the observation is `src/pubrun/_config_boot.py::resolve_import_mode`, step 1, validated against `src/pubrun/_modes.py::VALID_MODES`.
- `python3 -m pytest tests/test_import_modes.py tests/test_config_capture_modes.py --no-cov -q` passes. These suites call `resolve_import_mode` and show that the docstring edit leaves its behavior unchanged.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- `src/pubrun/_config_boot.py` (E-01) is the only file that changes.
- `docs/configuration.md`, `docs/functional_spec.md`, `docs/api.md`, and `README.md` document import modes from `MODES`, not from this docstring, so they are not edited.
- `.aw/records/specs/` contains no `.spec.md` file that governs this docstring, so no spec is touched.

## Open questions

### OQ-01: Should the docstring name `pubrun._modes.MODES` as the source of the list, or only list the six names?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: Name it. The list drifted from `MODES` in two ways: the `full` plan (`.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md`) added a mode to `MODES` without updating this docstring, and the docstring still names `quiet`, which `CHANGELOG.md` identifies as a stale name for `noconsole`. Naming `MODES` points a reader at the authoritative definition. The six names stay listed so that a reader does not need to open another file.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- src/pubrun/_config_boot.py`, showing one removed and two added lines inside the `resolve_import_mode` docstring, with the added lines identical to "Proposed changes" item 1. (2) Paste the output of `PYTHONPATH=src python3 -c "import pubrun._config_boot as m; print(m.resolve_import_mode.__doc__)"`, whose `Returns:` section matches "Proposed changes" item 1. (3) Paste the output of `grep -c '"quiet"' src/pubrun/_config_boot.py`, which must be `0`. (4) Paste the output of `git diff -U0 -- src/pubrun/_config_boot.py | grep '^+[^+]' | grep -cP '[\x{2013}\x{2014}]'`, which must be `0`. (5) Paste the `Found N errors.` line of `ruff check src/pubrun/_config_boot.py` from before and after the edit; the two counts must be equal. (6) Paste the seven output lines of the Findings probe, produced by `src/pubrun/_config_boot.py::resolve_import_mode` against `src/pubrun/_modes.py::VALID_MODES`, identical to the Findings output. (7) Paste the summary line of `python3 -m pytest tests/test_import_modes.py tests/test_config_capture_modes.py --no-cov -q`. (8) Paste the exit status of `python3 scripts/sanitize_paths.py --check --all`, which must be `0`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no blocking open questions.
2. Scope declaration: the expected modified file is the `- Scope-Paths:` entry (`src/pubrun/_config_boot.py`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the `V-01` `Observed evidence:` field. Do not mark `V-01` `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit wtpyx0 -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize wtpyx0`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize wtpyx0` after `E-01` is `performed`, `V-01` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
