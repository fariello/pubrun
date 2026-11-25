# IPD: Add full import mode to the Lock File import_mode row in docs/manifest.md

- Date: 2026-11-24
- Kind: child
- Concern: The `import_mode` row of the Lock File table in `docs/manifest.md` lists five import modes and omits `full`, although pubrun writes `"full"` to that field of `.pubrun.lock` when a script runs `import pubrun.full`.
- Scope: In `docs/manifest.md`, section "Lock File (`.pubrun.lock`)", change the description of the `import_mode` row so that it lists all six import modes, including `"full"`. No other file or row changes.
- Scope-Paths: docs/manifest.md
- Scope-Exceeded: .aw/records/backlog/open/20261124-ln0vci-01-ln0vci-document-sys-argv-in-the-lock-file-section-of-docs.backlog.md (Filed required defect-report backlog carrier ln0vci for undocumented sys_argv field in docs/manifest.md Lock File section)
- Item-Dependencies: none
- Status: executed
- Readiness: go-pending-approval
- Review-Depth: simple
- Short-Description: List "full" in the Lock File import_mode row of docs/manifest.md
- Work-Kind: followup
- Priority: low
- From-Backlog: kiir0y
- Set: kiir0y
- Order: 1
- Highest E allocated: 01
- Author: opencode
- Id: f12rk6

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 executed (aw agy run model=Gemini-4-Neon-High): aw agy run self-finalize: f12rk6 verified (set kiir0y, attempt 1). [Scope reconciliation - out-of-scope .aw/records/backlog/open/20261124-ln0vci-01-ln0vci-document-sys-argv-in-the-lock-file-section-of-docs.backlog.md: Filed required defect-report backlog carrier ln0vci for undocumented sys_argv field in docs/manifest.md Lock File section]
- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003 fixed; review record `.aw/records/reviews/20261124-kiir0y-01-f12rk6-add-full-import-mode-to-the-lock-file-import-mode-row-in-doc.review.md`.
- 2026-11-25 to-review (opencode): graduated from backlog item `kiir0y` into a review-ready plan.
- 2026-11-25 draft (opencode): created.

## Goal

A reader of `docs/manifest.md` learns every value that the lock file field `import_mode` can hold. After this plan, the Lock File `import_mode` row lists the same six import modes as the `selected_mode` row under heading `` ## `pubrun_imports` `` in the same file: `"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, and `"full"`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Documentation

- [x] E-01 In `docs/manifest.md`, section `## Lock File (.pubrun.lock)` (heading `` ## Lock File (`.pubrun.lock`) ``), replace the description cell of the `import_mode` table row with the text given in "Proposed changes" item 1.
  - Depends on: none
  - Expected outcome: (1) The `import_mode` row reads exactly as shown in "Proposed changes" item 1. (2) The row's field name cell (`` `import_mode` ``) and type cell (`string \| null`) are unchanged. (3) No other line of `docs/manifest.md` changes, including the Lock File JSON example, whose `"import_mode": "auto"` value stays valid.
  - Execution state: performed

## Project conventions discovered (Step 0)

- `docs/manifest.md` documents every manifest and lock file field in Markdown tables with the columns `Field`, `Type`, and `Description`. Enumerated string values are written as quoted JSON strings inside backticks, separated by commas, for example `"auto"`, `"noauto"`.
- The `selected_mode` row under `` ## `pubrun_imports` `` in the same file already reads: "The effective import mode: `"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, or `"full"`." Commit `15b3b37` (plan `lwb332`) reconciled that section and did not touch the Lock File section. Commit `142672074b` then filed this backlog item as an adjacent gap.
- `AGENTS.md` "Doc-sync discipline" asks that documentation match the implementation. The dash rule in `AGENTS.md` "Agent execution contract" applies to `docs/manifest.md`, because it is user-facing: the edited row must contain no em or en dashes.
- Commit `15b3b37`, the comparable documentation-only reconciliation, added no `CHANGELOG.md` entry. This plan follows that precedent.
- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone: an offset expires before this plan executes (advisory `IPD-C801`).

## Findings

Measured at authoring on Linux at `HEAD` `39fe0b5` (and verified at review against `HEAD` `4b005e7`).

The current row in `docs/manifest.md`, under heading `` ## Lock File (`.pubrun.lock`) ``:

```markdown
| `import_mode` | string \| null | The active import mode (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`). |
```

How pubrun fills the field:

| Step | Code | What it does |
|---|---|---|
| 1 | `src/pubrun/full.py` | Calls `select_mode("full", "pubrun.full", "explicit")` when a script runs `import pubrun.full`. |
| 2 | `src/pubrun/_bootstrap.py::get_selected_mode` | Returns the selected mode name, or `None` before any mode is selected. |
| 3 | `src/pubrun/tracker.py::Run._write_lock_file` | Writes `"import_mode": _import_mode`, the value from step 2, into `.pubrun.lock` in the run directory. |

`src/pubrun/_modes.py::MODES` defines six modes, and `pubrun run --mode` (`src/pubrun/__main__.py`, the `run_parser` `--mode` argument) accepts the choices `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, and `full`.

A probe at authoring ran `import pubrun.full` in a child Python process with `PUBRUN_IMPORT_MODE` and `PUBRUN_AUTO_START` set to empty strings, then read `.pubrun.lock` from the active run's directory before `stop()`. Run from the repository root, the authoring probe was:

```sh
mkdir -p .kiir0y_probe
(cd .kiir0y_probe && PUBRUN_IMPORT_MODE= PUBRUN_AUTO_START= PYTHONPATH=../src python3 -c "
import json, pubrun.full as p
r=p.get_current_run(); d=json.load(open(r.run_dir/'.pubrun.lock')); print(d['import_mode'], d['import_selected_by']); p.stop()")
rm -rf .kiir0y_probe
```

It printed:

```text
full pubrun.full
```

These are the `import_mode` and `import_selected_by` values. The lock file therefore holds `"full"`, and the documentation row omits it.

No diagram is included. The change affects one table row, and the producer chain above is a linear three-step process with no branch (technical writing standard, requirement 12(c)).

## Proposed changes (ordered, validatable)

1. **Lock File row (E-01).** Replace the `import_mode` row with this line:

   ```markdown
   | `import_mode` | string \| null | The active import mode (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, or `"full"`). |
   ```

   The only change is the added text ``, or `"full"` `` before the closing parenthesis. It matches the wording of the `selected_mode` row under `` ## `pubrun_imports` ``.

## Deferred / out of scope (with reason)

- Updating the stale mode list in the `src/pubrun/_bootstrap.py::select_mode` docstring. Commit `142672074b` filed it as a sibling backlog item. It touches a different file and does not depend on this plan.
  - Carrier: szf342
- Declaring all `selected_behavior` keys in `schemas/manifest.schema.json`. Commit `142672074b` filed it as a sibling backlog item. It touches different files and does not depend on this plan.
  - Carrier: 31kpnv
- Adding `"full"` to the accepted-value tuple in `tests/test_import_modes.py::TestImportMetadataInManifest.test_lock_file_contains_import_mode` (and the similar tuple in the `selected_mode` assertion of the neighboring `test_manifest_imports_has_correct_mode` test). Those tests run in the default `auto` mode, so the omission causes no failure, and the backlog item asks for a documentation change only.
  - Carrier-Declined: the tuples are permissive membership checks in tests that never select `full`; the missing value has no observable effect, and no defect report asks for it.
- A `CHANGELOG.md` entry. The change corrects one table cell and changes no behavior, and the comparable reconciliation in commit `15b3b37` added no entry.
  - Carrier-Declined: a one-value documentation correction does not meet the bar the changelog has applied to documentation-only fixes.

## Scope check

- Over-scope: none. The plan edits one table cell.
- Under-scope: none. No code, schema, or test changes are needed, because pubrun already writes `"full"` (Findings probe) and the lock file is not described by `schemas/manifest.schema.json`.

## Required tests / validation

- `git diff -- docs/manifest.md` shows exactly one removed line and one added line, both the Lock File `import_mode` row.
- ``grep -n '^| `import_mode` |' docs/manifest.md`` prints exactly one line, and that line contains `` `"full"` ``.
- Before committing `docs/manifest.md`, run the working-tree dash check (must assert at least one added line and exit `0` with `dashes=0`):
  `python3 -c "import subprocess, sys; lines = [l for l in subprocess.check_output(['git', 'diff', '-U0', '--', 'docs/manifest.md'], text=True).splitlines() if l.startswith('+') and not l.startswith('+++')]; assert lines, 'no added docs/manifest.md lines in working tree'; bad = [l for l in lines if '\u2014' in l or '\u2013' in l]; print(f'added_lines={len(lines)} dashes={len(bad)}'); sys.exit(1 if bad else 0)"`
- A runtime check confirms the documented value without writing into the repository working tree: run the isolated temporary-directory probe below and observe `full pubrun.full`. The code path that produces the observation is `src/pubrun/tracker.py::Run._write_lock_file`, reached through `src/pubrun/full.py`:

  ```sh
  PUBRUN_IMPORT_MODE= PUBRUN_AUTO_START= python3 -c "
  import json, os, sys, tempfile
  sys.path.insert(0, os.path.abspath('src'))
  orig = os.getcwd()
  with tempfile.TemporaryDirectory() as td:
      os.chdir(td)
      try:
          import pubrun.full as p
          r = p.get_current_run()
          with open(r.run_dir / '.pubrun.lock', encoding='utf-8') as f:
              d = json.load(f)
          print(d['import_mode'], d['import_selected_by'])
          p.stop()
      finally:
          os.chdir(orig)
  "
  ```

- `python3 -m pytest tests/test_import_modes.py tests/test_full_mode.py --no-cov -q` passes. These suites cover the lock file provenance fields and the `full` mode; they are run to show that the documentation change sits beside unchanged, passing behavior.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- `docs/manifest.md` (E-01) is the document that changes.
- `docs/functional_spec.md`, `docs/configuration.md`, `docs/api.md`, and `README.md` do not document the lock file `import_mode` values, so they are not edited.
- `.aw/records/specs/` contains no `.spec.md` file that governs the lock file, so no spec is touched.

## Open questions

### OQ-01: Should the change also add a `CHANGELOG.md` entry?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: No. The edit corrects one documentation table cell and changes no behavior. Commit `15b3b37`, which reconciled the neighboring `` ## `pubrun_imports` `` section of the same file, added no changelog entry. See "Deferred / out of scope".

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- docs/manifest.md`, showing one removed and one added line, both the Lock File `import_mode` row, with the added line identical to "Proposed changes" item 1. (2) Paste the output of ``grep -n '^| `import_mode` |' docs/manifest.md``: one line containing `` `"full"` ``. (3) Paste the output and exit status `0` of the working-tree dash check command in "Required tests / validation", showing `added_lines=1 dashes=0`. (4) Paste the output of the isolated temporary-directory probe in "Required tests / validation", `full pubrun.full`, produced by `src/pubrun/tracker.py::Run._write_lock_file` through `src/pubrun/full.py`, and confirm `git status --short` shows no untracked probe files. (5) Paste the summary line of `python3 -m pytest tests/test_import_modes.py tests/test_full_mode.py --no-cov -q`. (6) Paste the exit status of `python3 scripts/sanitize_paths.py --check --all`, which must be `0`.
  - Observed evidence:
    (1) `git diff -- docs/manifest.md`:
    ```diff
    diff --git a/docs/manifest.md b/docs/manifest.md
    index 94c873e..74e723d 100644
    --- a/docs/manifest.md
    +++ b/docs/manifest.md
    @@ -618,7 +618,7 @@ While a run is active, a `.pubrun.lock` JSON file exists in the run directory. I
     | `git_commit` | string \| null | Git commit hash at start, or `null` if not in a repo. |
     | `cwd` | string | Working directory of the process. |
     | `argv` | list[string] | Command-line arguments (excluding `sys.argv[0]`). Sensitive values are redacted. |
    -| `import_mode` | string \| null | The active import mode (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`). |
    +| `import_mode` | string \| null | The active import mode (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, or `"full"`). |
     | `import_selected_by` | string \| null | Who selected the mode (e.g., `"pubrun"`, `"pubrun.noauto"`). |

     **Example:**
    ```
    (2) ``grep -n '^| `import_mode` |' docs/manifest.md``:
    `621:| `import_mode` | string \| null | The active import mode (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, or `"full"`). |`
    (3) Working-tree dash check: `added_lines=1 dashes=0`, exit status `0`.
    (4) Isolated temporary-directory probe (`src/pubrun/tracker.py::Run._write_lock_file` via `src/pubrun/full.py`): `full pubrun.full`, exit status `0`; `git status --short` output: ` M docs/manifest.md` (no untracked probe files).
    (5) `python3 -m pytest tests/test_import_modes.py tests/test_full_mode.py --no-cov -q`: `98 passed in 24.54s`, exit status `0`.
    (6) `python3 scripts/sanitize_paths.py --check --all`: exit status `0`.
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no blocking open questions.
2. Scope declaration: the expected modified file is the `- Scope-Paths:` entry (`docs/manifest.md`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization; if a declared file needs no edit, acknowledge it with `--scope-ack`. The runtime probe runs inside a temporary directory outside the repository working tree so it leaves no untracked files behind.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the `V-01` `Observed evidence:` field. Do not mark `V-01` `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit f12rk6 -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize f12rk6`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize f12rk6` after `E-01` is `performed`, `V-01` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
