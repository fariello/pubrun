# IPD: List the six valid import modes in the select_mode docstring

- Date: 2026-11-24
- Kind: child
- Concern: The docstring of `src/pubrun/_bootstrap.py::select_mode` says that the `mode` argument is one of `"auto"`, `"noauto"`, `"nopatch"`, `"minimal"`. The list omits `"noconsole"` and `"full"`, which are valid modes and which the `pubrun.noconsole` and `pubrun.full` submodules pass to `select_mode`.
- Scope: In `src/pubrun/_bootstrap.py`, replace the `mode: One of ...` line of the `select_mode` docstring with a two-line entry that lists the six valid import modes. No code, other docstring line, or other file changes.
- Scope-Paths: src/pubrun/_bootstrap.py
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: simple
- Short-Description: List the six valid import modes in the select_mode docstring
- Work-Kind: followup
- Priority: low
- From-Backlog: szf342
- Set: szf342
- Order: 1
- Highest E allocated: 01
- Author: opencode
- Id: wvrmqu
- Approval: 2026-11-25, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003
- 2026-11-25 to-review (opencode): graduated from backlog item `szf342` into a review-ready plan.
- 2026-11-25 draft (opencode): created.

## Goal

A developer who reads the `select_mode` docstring learns the exact set of mode names that the function accepts. After this plan, the `mode` entry lists the six keys of `src/pubrun/_modes.py::MODES`: `"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, and `"full"`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Docstring

- [ ] E-01 In `src/pubrun/_bootstrap.py`, in the `Args:` section of the `select_mode` docstring, replace the line `mode: One of "auto", "noauto", "nopatch", "minimal".` with the two lines given in "Proposed changes" item 1.
  - Depends on: none
  - Expected outcome: (1) The `mode` entry of the `Args:` section reads exactly as shown in "Proposed changes" item 1. (2) The `selected_by` and `source` entries, the summary line, and the `Returns:` section are unchanged. (3) No executable line of `src/pubrun/_bootstrap.py` changes, and no other line of the file changes.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `src/pubrun/_modes.py` is the single source of truth for import modes. `MODES` maps each mode name to its behavior flags, and `VALID_MODES = frozenset(MODES.keys())`. `select_mode` obtains its behavior from `src/pubrun/_modes.py::get_mode_behavior`, which returns a copy of `MODES[mode]`.
- Docstrings in `src/pubrun/_bootstrap.py` use Google style (`Args:`, `Returns:`) and indent a continuation line by four extra spaces, as the existing `selected_by:` and `source:` entries do.
- The sibling plan `wtpyx0` (`.aw/records/plans/pending/20261124-m8buxe-01-wtpyx0-correct-the-mode-name-list-in-the-resolve-import-mode-docstr.ipd.md`, from backlog item `m8buxe`) fixes the same stale list in `src/pubrun/_config_boot.py::resolve_import_mode`. It names this backlog item (`szf342`) as the carrier for the `select_mode` docstring. This plan uses the same wording pattern, so the two docstrings read alike. The two plans edit different files and do not depend on each other.
- The executed plan `.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md` added `full` by extending `MODES`. It did not update this docstring, which is one way the list became stale.
- `AGENTS.md#Agent execution contract` exempts code comments from the dash rule. The new docstring text still uses no em or en dashes, so it matches the surrounding lines.
- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone: an offset expires before this plan executes (advisory `IPD-C801`).

## Findings

Measured at authoring on Linux at `HEAD` `e656ec0`.

The current `select_mode` docstring, printed with `PYTHONPATH=src python3 -c "import pubrun._bootstrap as m; print(m.select_mode.__doc__)"`:

```text
Select an import mode. First call wins; later calls detect conflicts.

Args:
    mode: One of "auto", "noauto", "nopatch", "minimal".
    selected_by: Identifier for who selected this mode (e.g., "pubrun",
        "pubrun.noauto", "env:PUBRUN_IMPORT_MODE").
    source: Where the selection came from (e.g., "default", "config",
        "env:PUBRUN_IMPORT_MODE").

Returns:
    The effective behavior dict (e.g., {"auto_start": bool, ...}).
```

The valid modes, printed with `PYTHONPATH=src python3 -c "from pubrun._modes import VALID_MODES; print(sorted(VALID_MODES))"`:

```text
['auto', 'full', 'minimal', 'noauto', 'noconsole', 'nopatch']
```

`grep -rn "select_mode(" src` shows the callers. Each mode submodule passes its own mode name, and `src/pubrun/core.py` passes the resolved import mode:

```text
src/pubrun/_bootstrap.py:172:def select_mode(mode: str, selected_by: str, source: str) -> Dict[str, bool]:
src/pubrun/core.py:667:            mode_behavior = select_mode(import_mode, selected_by, import_source)
src/pubrun/nopatch.py:16:_behavior = select_mode("nopatch", "pubrun.nopatch", "explicit")
src/pubrun/noauto.py:21:_behavior = select_mode("noauto", "pubrun.noauto", "explicit")
src/pubrun/noconsole.py:13:_behavior = select_mode("noconsole", "pubrun.noconsole", "explicit")
src/pubrun/auto.py:19:_behavior = select_mode("auto", "pubrun.auto", "explicit")
src/pubrun/full.py:24:_behavior = select_mode("full", "pubrun.full", "explicit")
src/pubrun/minimal.py:19:_behavior = select_mode("minimal", "pubrun.minimal", "explicit")
```

A probe at authoring reset the bootstrap state, called `select_mode` once for each valid name, and checked that the selected mode and the returned behavior match `MODES`. Run from the repository root:

```sh
for m in auto noauto nopatch noconsole minimal full; do PYTHONPATH=src python3 -W ignore -c "import pubrun._bootstrap as b; b.reset_state(); r=b.select_mode('$m','probe','probe'); print('$m', b.get_selected_mode(), r == b.MODES['$m'])"; done
```

It printed:

```text
auto auto True
noauto noauto True
nopatch nopatch True
noconsole noconsole True
minimal minimal True
full full True
```

`select_mode` accepts each of the six valid modes and returns that mode's behavior. The docstring therefore omits two values the function accepts and that production code passes to it.

| Mode name | In `VALID_MODES` | Passed by a caller in `src/` | Listed in the docstring today |
|---|---|---|---|
| `auto` | yes | yes (`pubrun.auto`) | yes |
| `noauto` | yes | yes (`pubrun.noauto`) | yes |
| `nopatch` | yes | yes (`pubrun.nopatch`) | yes |
| `noconsole` | yes | yes (`pubrun.noconsole`) | no |
| `minimal` | yes | yes (`pubrun.minimal`) | yes |
| `full` | yes | yes (`pubrun.full`) | no |

`ruff check src/pubrun/_bootstrap.py` reports 19 pre-existing findings at authoring (`Found 19 errors.`). This plan does not fix them, and validation therefore checks only that the edit adds no finding.

No diagram is included. The change affects one docstring entry of one function, which is a single entity with no process (technical writing standard, requirement 12(c)).

## Proposed changes (ordered, validatable)

1. **Docstring line (E-01).** Replace this line of the `select_mode` docstring:

   ```python
           mode: One of "auto", "noauto", "nopatch", "minimal".
   ```

   with these two lines, keeping the eight-space indentation of the `Args:` entries and the twelve-space indentation of a continuation line:

   ```python
           mode: One of the keys of ``pubrun._modes.MODES``: "auto", "noauto",
               "nopatch", "noconsole", "minimal", or "full".
   ```

   After the change, the full `Args:` section reads:

   ```python
       Args:
           mode: One of the keys of ``pubrun._modes.MODES``: "auto", "noauto",
               "nopatch", "noconsole", "minimal", or "full".
           selected_by: Identifier for who selected this mode (e.g., "pubrun",
               "pubrun.noauto", "env:PUBRUN_IMPORT_MODE").
           source: Where the selection came from (e.g., "default", "config",
               "env:PUBRUN_IMPORT_MODE").
   ```

   Naming `pubrun._modes.MODES` tells a reader where the list is defined, so a future mode added there has an obvious place to check. Both new lines are shorter than 80 characters (75 and 57).

## Deferred / out of scope (with reason)

- Documenting in the docstring that `select_mode` records an unrecognized name as the selected mode and applies the `"auto"` behavior to it (an authoring probe with `"quiet"` printed `quiet True`). The backlog item asks only to correct the stale list, and the fallback is already documented on `src/pubrun/_modes.py::get_mode_behavior`.
  - Carrier-Declined: no backlog item requests documenting the fallback on `select_mode`, and adding it would change the docstring's contract beyond the requested list correction.
- Fixing the pre-existing `ruff check` findings in `src/pubrun/_bootstrap.py`. They are unrelated to the docstring.
  - Carrier-Declined: lint cleanup of this module is not requested by any backlog item, and mixing it into a docstring fix would widen the reviewed diff.
- Adding a test that asserts the docstring text. `AGENTS.md#Agent execution contract` forbids tests that pin docstring text.
  - Carrier-Declined: a docstring-pinning test is prohibited by the repository's testing rule.
- A `CHANGELOG.md` entry. The change corrects an internal docstring and changes no behavior.
  - Carrier-Declined: an internal docstring correction changes no user-visible behavior, so it does not meet the changelog's bar.

## Scope check

- Over-scope: none. The plan edits one docstring entry.
- Under-scope: none. No code, test, or documentation change is needed, because `select_mode` already accepts the six modes (Findings probe), and no file under `docs/`, `README.md`, or `.aw/records/specs/` mentions `select_mode` (`grep -rn select_mode docs README.md .aw/records/specs` printed nothing at authoring).

## Required tests / validation

- `git diff -- src/pubrun/_bootstrap.py` shows exactly one removed line and two added lines, all inside the `select_mode` docstring, with the added lines identical to "Proposed changes" item 1.
- `PYTHONPATH=src python3 -c "import pubrun._bootstrap as m; print(m.select_mode.__doc__)"` prints an `Args:` section that matches "Proposed changes" item 1.
- `grep -c '"noconsole", "minimal", or "full"' src/pubrun/_bootstrap.py` prints `1`.
- `PYTHONPATH=src python3 -c 'import pubrun._bootstrap as m; doc = m.select_mode.__doc__ or ""; assert "\"noconsole\", \"minimal\", or \"full\"" in doc; assert "\u2013" not in doc and "\u2014" not in doc; print("OK: six modes listed, 0 en/em dashes")'` prints `OK: six modes listed, 0 en/em dashes` and exits 0.
- `ruff check src/pubrun/_bootstrap.py` reports the same number of findings after the edit as the `HEAD` baseline (`git show HEAD:src/pubrun/_bootstrap.py | ruff check --stdin-filename src/pubrun/_bootstrap.py -`; 19 at authoring/review). Record both counts.
- A runtime check confirms the documented list: run the Findings probe again and observe the same six output lines. The code path that produces the observation is `src/pubrun/_bootstrap.py::select_mode`, which calls `src/pubrun/_modes.py::get_mode_behavior`.
- `python3 -m pytest tests/test_import_modes.py tests/test_full_mode.py --no-cov -q` passes. These suites call `select_mode` or import the mode submodules, and they show that the docstring edit leaves behavior unchanged.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- `src/pubrun/_bootstrap.py` (E-01) is the only file that changes.
- `docs/` and `README.md` document import modes from `MODES` and do not quote this docstring, so they are not edited.
- `.aw/records/specs/` contains no `.spec.md` file that mentions `select_mode`, so no spec is touched.

## Open questions

### OQ-01: Should the docstring name `pubrun._modes.MODES` as the source of the list, or only list the six names?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: Name it. The list drifted from `MODES` when the `full` plan (`.aw/records/plans/executed/20260705-1828-01-full-capture-mode.md`) added a mode without updating this docstring. Naming `MODES` points a reader at the authoritative definition. The six names stay listed so that a reader does not need to open another file. The sibling plan `wtpyx0` makes the same choice for `resolve_import_mode`, so both docstrings use one pattern.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- src/pubrun/_bootstrap.py`, showing one removed and two added lines inside the `select_mode` docstring, with the added lines identical to "Proposed changes" item 1. (2) Paste the output of `PYTHONPATH=src python3 -c "import pubrun._bootstrap as m; print(m.select_mode.__doc__)"`, whose `Args:` section matches "Proposed changes" item 1. (3) Paste the output of `grep -c '"noconsole", "minimal", or "full"' src/pubrun/_bootstrap.py`, which must be `1`. (4) Paste the output of the portable `python3 -c` docstring check from "Required tests / validation", which must print `OK: six modes listed, 0 en/em dashes` and exit 0. (5) Paste the `Found N errors.` line of `git show HEAD:src/pubrun/_bootstrap.py | ruff check --stdin-filename src/pubrun/_bootstrap.py -` (baseline) and `ruff check src/pubrun/_bootstrap.py` (after edit); the two counts must be equal. (6) Paste the six output lines of the Findings probe, produced by `src/pubrun/_bootstrap.py::select_mode` through `src/pubrun/_modes.py::get_mode_behavior`, identical to the Findings output. (7) Paste the summary line of `python3 -m pytest tests/test_import_modes.py tests/test_full_mode.py --no-cov -q`. (8) Paste the exit status of `python3 scripts/sanitize_paths.py --check --all`, which must be `0`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no blocking open questions.
2. Scope declaration: the expected modified file is the `- Scope-Paths:` entry (`src/pubrun/_bootstrap.py`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the `V-01` `Observed evidence:` field. Do not mark `V-01` `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit wvrmqu -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: inside a runner lane (`aw oc run` or `aw agy run`), the runner owns finalization once `E-01` is `performed` and `V-01` is `pass`. Outside a runner, after `E-01` is `performed`, `V-01` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`, finalize this plan with `aw ipd finalize wvrmqu` (never with a hand-written `git mv` to `.aw/records/plans/executed/`).
