# IPD: Document sys_argv in the Lock File section of docs/manifest.md

- Date: 2026-11-25
- Kind: child
- Concern: `Run._write_lock_file` in `src/pubrun/tracker.py` writes a redacted `sys_argv` list (copied from `sys.argv`) into `.pubrun.lock`, but the Lock File table and JSON example in `docs/manifest.md` omit `sys_argv`.
- Scope: In `docs/manifest.md`, section "Lock File (`.pubrun.lock`)", insert a `sys_argv` row in the field table immediately after `argv` and insert a matching `"sys_argv"` entry in the Lock File JSON example immediately after `"argv"`. No other file, section, row, or example field changes.
- Scope-Paths: docs/manifest.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: simple
- Short-Description: Add sys_argv to the Lock File table and JSON example in docs/manifest.md
- Work-Kind: followup
- Priority: low
- From-Backlog: ln0vci
- Set: ln0vci
- Order: 1
- Highest E allocated: 01
- Author: antigravity
- Id: wg2l7b
- Approval: 2026-11-25, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Antigravity): APPROVE; no findings; review record `.aw/records/reviews/20261125-ln0vci-01-wg2l7b-document-sys-argv-in-the-lock-file-section-of-docs-manifest.review.md`.
- 2026-11-25 to-review (aw set): graduated from backlog item ln0vci into a review-ready plan.
- 2026-11-25 draft (antigravity): created.

## Goal

Ensure a reader of `docs/manifest.md` sees every field that `pubrun` writes to `.pubrun.lock`. After this plan executes, the Lock File field table and JSON example under heading `` ## Lock File (`.pubrun.lock`) `` document `sys_argv` in the same position and with the same redaction semantics that `src/pubrun/tracker.py::Run._write_lock_file` writes.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Documentation

- [ ] E-01 In `docs/manifest.md`, under heading `` ## Lock File (`.pubrun.lock`) ``, add the `sys_argv` table row immediately after the `argv` row and add the `"sys_argv"` line to the Lock File JSON example immediately after the `"argv"` line, using the exact text in "Proposed changes" items 1 and 2.
  - Depends on: none
  - Expected outcome: (1) The Lock File table contains the `sys_argv` row from "Proposed changes" item 1 immediately after `argv` and before `import_mode`. (2) The Lock File JSON example parses as valid JSON, places `"sys_argv"` immediately after `"argv"` and before `"import_mode"`, and matches "Proposed changes" item 2 verbatim. (3) No other line in `docs/manifest.md` changes.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `docs/manifest.md` documents lock file fields in a Markdown table with columns `Field`, `Type`, and `Description`, followed by a fenced `json` example block. List-of-string fields use the type notation `list[string]`.
- The existing `argv` row in the Lock File table reads: "Command-line arguments (excluding `sys.argv[0]`). Sensitive values are redacted." The new `sys_argv` row mirrors that phrasing so the distinction between `argv` and `sys_argv` is immediate.
- `AGENTS.md` ("Agent execution contract") prohibits em dashes and en dashes in user-facing documentation. Because `docs/manifest.md` is user-facing, the added lines must contain neither em dashes nor en dashes.
- Prior documentation-only reconciliations of `docs/manifest.md` (plan `f12rk6` in the Lock File section and commit `15b3b37` in `` ## `pubrun_imports` ``) added no `CHANGELOG.md` entry. This plan follows that precedent.
- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone: an offset expires before this plan executes (advisory `IPD-C801`).

## Findings

Measured at authoring on Linux at `HEAD` `afbc4f9`.

In `docs/manifest.md`, under heading `` ## Lock File (`.pubrun.lock`) ``, the field table lists ten keys (`pid`, `started_at_utc`, `script`, `run_id`, `hostname`, `git_commit`, `cwd`, `argv`, `import_mode`, `import_selected_by`) and omits `sys_argv` between `argv` and `import_mode`:

```markdown
| `argv` | list[string] | Command-line arguments (excluding `sys.argv[0]`). Sensitive values are redacted. |
| `import_mode` | string \| null | The active import mode (`"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, or `"full"`). |
```

The Lock File JSON example in the same section lists the same ten keys and also omits `"sys_argv"` between `"argv"` and `"import_mode"`:

```json
  "argv": ["--epochs", "100", "--lr", "0.001"],
  "import_mode": "auto",
```

How `pubrun` writes and reads `sys_argv` in `.pubrun.lock`:

| Role | Symbol | Behavior |
|---|---|---|
| Producer | `src/pubrun/tracker.py::Run._write_lock_file` | Copies `list(sys.argv)` (or `[]` when `sys.argv` is empty), redacts it on a best-effort basis via `src/pubrun/capture/redaction.py::redact_argv`, and writes `"sys_argv"` into `.pubrun.lock` immediately after `"argv"` and before `"import_mode"`. |
| Consumer | `src/pubrun/status.py::_crash_invocation_argv` | Reads `lock_data.get("sys_argv")` during crashed-run closeout (`close_out_crashed_run`) to populate `manifest.json` `invocation.argv`; falls back to prepending `script` to `argv` only for older lock files that lack `sys_argv`. |
| Consumer | `src/pubrun/__main__.py::_run_rerun` | Reads `lock_data.get("sys_argv")` when reconstructing a rerun command from `.pubrun.lock` for a running or crashed run without `manifest.json`; falls back to `[script_filename] + argv` when `sys_argv` is absent. |

An isolated temporary-directory probe at authoring ran `Run` with `sys.argv = ['train.py', '--epochs', '100', '--token=secret123']` and read `.pubrun.lock` before calling `Run.stop()`:

```text
keys: ['pid', 'started_at_utc', 'script', 'run_id', 'hostname', 'git_commit', 'cwd', 'argv', 'sys_argv', 'import_mode', 'import_selected_by']
argv: ['--epochs', '100', '--token=[REDACTED]']
sys_argv: ['train.py', '--epochs', '100', '--token=[REDACTED]']
```

`Run._write_lock_file` writes eleven keys including redacted `sys_argv`, while `docs/manifest.md` documents only ten keys.

No diagram is included. The plan edits one section of one document to record one existing field and involves no multi-step branched workflow or lifecycle transition (technical writing standard, requirement 12(c)).

## Proposed changes (ordered, validatable)

1. **Lock File table row (E-01).** In `docs/manifest.md`, under heading `` ## Lock File (`.pubrun.lock`) ``, insert this row immediately after the `argv` row and immediately before the `import_mode` row:

   ```markdown
   | `sys_argv` | list[string] | Full `sys.argv` list (including `sys.argv[0]`). Sensitive values are redacted. Used when reconstructing invocation commands from a lock file (for example during crashed-run closeout or `pubrun rerun`). |
   ```

2. **Lock File JSON example entry (E-01).** In the `**Example:**` JSON code block of the same section, insert this line immediately after `"argv": ["--epochs", "100", "--lr", "0.001"],` and immediately before `"import_mode": "auto",`:

   ```json
     "sys_argv": ["train.py", "--epochs", "100", "--lr", "0.001"],
   ```

   This value is consistent with `"script": "train"` (stem of `train.py`) and `"argv": ["--epochs", "100", "--lr", "0.001"]` (`sys.argv[1:]`) in the same example, and preserves the key order written by `src/pubrun/tracker.py::Run._write_lock_file`.

## Deferred / out of scope (with reason)

- Adding assertions for `sys_argv` to `tests/test_status.py::TestLockFile.test_lock_file_contains_expected_fields` or `tests/test_status.py::TestLockFile.test_lock_file_argv_is_redacted`. `tests/test_status_bugs.py` and `tests/test_cli.py` already exercise `sys_argv` lock consumption, and backlog item `ln0vci` requests only the documentation update in `docs/manifest.md`.
  - Carrier-Declined: runtime `sys_argv` behavior is already tested in `tests/test_status_bugs.py` and `tests/test_cli.py`, and backlog item `ln0vci` is scoped strictly to `docs/manifest.md`.
- Adding a `CHANGELOG.md` entry. The edit documents an existing field and changes no runtime behavior, matching the precedent of plan `f12rk6` in the same section.
  - Carrier-Declined: documentation-only reconciliation of an existing field does not meet the repository's changelog bar.
- Changing `"git_commit": "3df16cf"` in the Lock File JSON example to a 40-character hash. That example value is unrelated to `sys_argv` and outside backlog item `ln0vci`.
  - Carrier-Declined: unrelated example formatting outside the scope of `ln0vci`.

## Scope check

- Over-scope: none. The plan adds two lines in one section of `docs/manifest.md`.
- Under-scope: none. `src/pubrun/tracker.py::Run._write_lock_file` already writes redacted `sys_argv` (verified by the Findings probe), and `.pubrun.lock` is not governed by `schemas/manifest.schema.json`.

## Required tests / validation

1. `git diff -- docs/manifest.md` shows zero removed lines and exactly two added lines, both under `` ## Lock File (`.pubrun.lock`) ``: the `sys_argv` table row and the `"sys_argv"` JSON example entry, matching "Proposed changes" items 1 and 2 verbatim.
2. ``grep -n '^| `sys_argv` |' docs/manifest.md`` prints exactly one line matching "Proposed changes" item 1.
3. Run the Lock File JSON example validation check (must exit `0` and print all eleven keys in order):

   ```sh
   python3 -c 'import json, pathlib, re; text = pathlib.Path("docs/manifest.md").read_text(encoding="utf-8"); sec = text.split("## Lock File", 1)[1].split("\n---", 1)[0]; m = re.search(r"json\n(\{.*?\})\n", sec, re.S); assert m, "JSON example not found"; data = json.loads(m.group(1)); keys = list(data.keys()); assert keys.index("sys_argv") == keys.index("argv") + 1, keys; assert keys.index("import_mode") == keys.index("sys_argv") + 1, keys; assert data["sys_argv"] == ["train.py", "--epochs", "100", "--lr", "0.001"], data["sys_argv"]; print("lock_example_keys:", keys)'
   ```

4. Before committing `docs/manifest.md`, run the working-tree dash check (must assert at least one added line and exit `0` with `added_lines=2 dashes=0`):

   ```sh
   python3 -c "import subprocess, sys; lines = [l for l in subprocess.check_output(['git', 'diff', '-U0', '--', 'docs/manifest.md'], text=True).splitlines() if l.startswith('+') and not l.startswith('+++')]; assert lines, 'no added docs/manifest.md lines in working tree'; bad = [l for l in lines if '\u2014' in l or '\u2013' in l]; print(f'added_lines={len(lines)} dashes={len(bad)}'); sys.exit(1 if bad else 0)"
   ```

5. Run an isolated temporary-directory runtime probe to confirm `src/pubrun/tracker.py::Run._write_lock_file` (reached via `Run.__init__` and `Run._bootstrap_engines`) writes redacted `sys_argv` immediately after `argv` and before `import_mode` without writing untracked files into the repository:

   ```sh
   PUBRUN_IMPORT_MODE= PUBRUN_AUTO_START= python3 -c "
   import json, os, sys, tempfile
   sys.path.insert(0, os.path.abspath('src'))
   orig = os.getcwd()
   with tempfile.TemporaryDirectory() as td:
       os.chdir(td)
       try:
           sys.argv = ['train.py', '--epochs', '100', '--token=secret123']
           from pubrun.tracker import Run
           r = Run(overrides={'capture': {'hardware': {'depth': 'off'}, 'git': {'enabled': False}}})
           with open(r.run_dir / '.pubrun.lock', encoding='utf-8') as f:
               d = json.load(f)
           keys = list(d.keys())
           assert keys.index('sys_argv') == keys.index('argv') + 1, keys
           assert keys.index('import_mode') == keys.index('sys_argv') + 1, keys
           print('keys:', keys)
           print('argv:', d['argv'])
           print('sys_argv:', d['sys_argv'])
           r.stop()
       finally:
           os.chdir(orig)
   "
   ```

6. `python3 -m pytest tests/test_status.py tests/test_status_bugs.py --no-cov -q` passes with exit status `0`.
7. `python3 scripts/sanitize_paths.py --check --all` exits `0`.

## Spec / documentation sync

- `docs/manifest.md` (E-01) is the only document that changes.
- `README.md`, `docs/architecture.md`, `docs/cli.md`, and `docs/functional_spec.md` reference `.pubrun.lock` at a high level without enumerating its JSON fields, so they require no update.
- `.aw/records/specs/` contains no `.spec.md` file governing `.pubrun.lock`, so no spec is updated.

## Open questions

### OQ-01: Should this change also add a `CHANGELOG.md` entry?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: No. Documenting an existing lock file field changes no runtime behavior and follows the precedent of plan `f12rk6` in the same section of `docs/manifest.md`. See "Deferred / out of scope".

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- docs/manifest.md` showing zero removed lines and two added lines under `` ## Lock File (`.pubrun.lock`) `` matching "Proposed changes" items 1 and 2 verbatim. (2) Paste the output of ``grep -n '^| `sys_argv` |' docs/manifest.md`` showing one line matching "Proposed changes" item 1. (3) Paste the output and exit status `0` of the Lock File JSON example validation command in "Required tests / validation" item 3, printing all eleven keys in order. (4) Paste the output and exit status `0` of the working-tree dash check command in "Required tests / validation" item 4, showing `added_lines=2 dashes=0`. (5) Paste the output and exit status `0` of the isolated temporary-directory runtime probe in "Required tests / validation" item 5 (code path `src/pubrun/tracker.py::Run._write_lock_file` via `Run.__init__` and `Run._bootstrap_engines`), showing `sys_argv: ['train.py', '--epochs', '100', '--token=[REDACTED]']`, and paste `git status --short` confirming no untracked probe files exist in the repository. (6) Paste the summary line and exit status `0` of `python3 -m pytest tests/test_status.py tests/test_status_bugs.py --no-cov -q`. (7) Paste the exit status `0` of `python3 scripts/sanitize_paths.py --check --all`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before changing any file. This plan has no blocking open questions.
2. Scope declaration: the expected modified file is the `- Scope-Paths:` entry (`docs/manifest.md`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization; if a declared file needs no edit, acknowledge it with `--scope-ack`. The runtime probe runs inside a temporary directory outside the repository working tree so it leaves no untracked files behind.
3. Validation honesty: run every command in "Required tests / validation" and paste its actual output into `V-01` `Observed evidence:`. Do not mark `V-01` `pass` without captured output from that run.
4. Commit discipline: commit only the paths changed for this plan using `aw commit wg2l7b -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize wg2l7b`, never with a manual `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, run `aw ipd finalize wg2l7b` after `E-01` is `performed`, `V-01` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
