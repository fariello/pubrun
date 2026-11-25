# IPD: Document PUBRUN_RUN_MODE_OVERRIDE in functional spec and configuration reference

- Date: 2026-11-25
- Kind: child
- Concern: Plan `lhwy0t` added the `PUBRUN_RUN_MODE_OVERRIDE` launch-time environment variable in `src/pubrun/__main__.py` and `src/pubrun/_bootstrap.py::select_mode`, and documented it in `docs/cli.md` and `docs/functional_spec.md` Section 11.13, but `docs/functional_spec.md` Sections 10.2 and 10.3 and `docs/configuration.md` (`## Environment Variables`) still omit it.
- Scope: Add `PUBRUN_RUN_MODE_OVERRIDE` to `docs/functional_spec.md` Sections 10.2 and 10.3 and to `docs/configuration.md` (`## Environment Variables`), and align the adjacent `PUBRUN_IMPORT_MODE` row in both tables so neither contradicts `PUBRUN_RUN_MODE_OVERRIDE` or explicit submodule import precedence. No other file, section, or code changes.
- Scope-Paths: docs/functional_spec.md, docs/configuration.md
- Item-Dependencies: none
- Status: to-review
- Short-Description: Document PUBRUN_RUN_MODE_OVERRIDE in docs/functional_spec.md sections 10.2 and 10.3 and docs/configuration.md
- Work-Kind: followup
- Priority: low
- From-Backlog: aqb2bu
- Set: aqb2bu
- Order: 1
- Highest E allocated: 02
- Author: Antigravity
- Id: 87qr8h

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (aw set): graduated from backlog item aqb2bu into a review-ready plan.
- 2026-11-25 draft (Antigravity): created.

## Goal

Ensure every environment-variable reference in the functional specification and configuration reference lists `PUBRUN_RUN_MODE_OVERRIDE` accurately. After this plan executes, `docs/functional_spec.md` Sections 10.2 and 10.3 and `docs/configuration.md` (`## Environment Variables`) document `PUBRUN_RUN_MODE_OVERRIDE` with the exact precedence, conflict-suppression, manifest-provenance, and boot-sequence semantics implemented in `src/pubrun/__main__.py` and `src/pubrun/_bootstrap.py::select_mode`, without contradicting the adjacent `PUBRUN_IMPORT_MODE` rows.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Environment-variable reference updates

- [ ] E-01 Update `docs/functional_spec.md` under headings `### 10.2 Configuration Discovery` and `### 10.3 Supported Environment Variables` using the exact text in "Proposed changes" items 1 and 2.
  - Depends on: none
  - Expected outcome: (1) Section 10.2 lists `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, and `PUBRUN_IMPORT_CONFLICT` as boot-sequence variables excluded from `resolve_config()` and cites Sections 3.2, 3.3, and 3.4. (2) Section 10.3 inserts the `PUBRUN_RUN_MODE_OVERRIDE` row immediately before `PUBRUN_IMPORT_MODE` and updates the `PUBRUN_IMPORT_MODE` row so both rows match "Proposed changes" item 2 verbatim. (3) No other line in `docs/functional_spec.md` changes, and zero em dashes or en dashes appear in any added or modified line.
  - Execution state: pending

- [ ] E-02 Update `docs/configuration.md` under heading `## Environment Variables` using the exact text in "Proposed changes" item 3.
  - Depends on: E-01
  - Expected outcome: (1) The `## Environment Variables` table inserts the `PUBRUN_RUN_MODE_OVERRIDE` row immediately before `PUBRUN_IMPORT_MODE` and updates the `PUBRUN_IMPORT_MODE` row to remove the stale `"Takes highest precedence."` claim, matching "Proposed changes" item 3 verbatim. (2) No other line in `docs/configuration.md` changes, and zero em dashes or en dashes appear in any added or modified line.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`path::Name`) or by a quoted content string, with a line number only appended to one of those and never alone: an offset expires before this plan executes (advisory `IPD-C801`).
- `AGENTS.md` ("Agent execution contract") prohibits em dashes (`\u2014`) and en dashes (`\u2013`) in user-facing documentation. Because `docs/functional_spec.md` and `docs/configuration.md` are user-facing documents, all added or modified lines in both files must contain zero em dashes and zero en dashes.
- Executed plan `lhwy0t` (`.aw/records/plans/executed/20261124-oubh58-01-lhwy0t-implement-launch-time-pubrun-run-mode-override-over-in-code.ipd.md`) introduced `PUBRUN_RUN_MODE_OVERRIDE` and updated `CHANGELOG.md`, `docs/manifest.md`, `docs/cli.md`, and `docs/functional_spec.md` (`### 11.13 Import Mode Wrapper (run)`). Prior documentation-only followups (such as executed plan `wg2l7b`) added no new `CHANGELOG.md` entry because runtime behavior does not change.
- `docs/functional_spec.md` (`### 10.3 Supported Environment Variables`) uses a two-column Markdown table (`Variable`, `Effect`) and explicitly states for each variable whether it is consumed in the boot sequence or in `resolve_config()`.
- `docs/configuration.md` (`## Environment Variables`) uses a two-column Markdown table (`Variable`, `Description`). Earlier sections of `docs/configuration.md` (`### [imports]`, `mode` row and note) already state that an in-code `import pubrun.<mode>` overrides config and ordinary environment variables, and only `pubrun run --mode` overrides the in-code import.

## Findings

Verified at authoring against `HEAD` `f7c0897`.

### Code behavior governing `PUBRUN_RUN_MODE_OVERRIDE`

| Role | Code location | Verified behavior |
|---|---|---|
| CLI wrapper | `src/pubrun/__main__.py::main` (`elif args.command == "run":`) | Spawns the child process with both `"PUBRUN_IMPORT_MODE": args.mode` and `"PUBRUN_RUN_MODE_OVERRIDE": args.mode` in `child_env`. |
| Boot mode selector | `src/pubrun/_bootstrap.py::select_mode` | When `_selected_mode is None`, reads `os.environ.get("PUBRUN_RUN_MODE_OVERRIDE", "").strip().lower()`. If that normalized value is a key of `pubrun._modes.MODES` (`auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`), it selects that mode ahead of the caller's requested mode (including explicit in-code `import pubrun.<mode>` imports) and sets `_selected_by` and `_selected_source` to `"cli:pubrun run --mode"`. It records any differing caller request with `conflict: False`, and subsequent `select_mode` calls under `_selected_source == "cli:pubrun run --mode"` also record `conflict: False` with no warning or error under `[imports].on_conflict` or `PUBRUN_IMPORT_CONFLICT`. Invalid or empty values are ignored. |
| Boot config resolver | `src/pubrun/_config_boot.py::resolve_import_mode` | Resolves fallback mode order when neither `PUBRUN_RUN_MODE_OVERRIDE` nor an explicit submodule import takes precedence: `PUBRUN_IMPORT_MODE`, then `PUBRUN_AUTO_START`, then `./.pubrun.toml`, `./.config/pubrun/config.toml`, user home `config.toml` (`[imports].mode` before `[core].auto_start` within a file), then built-in default `"auto"`. |
| Runtime config merge | `src/pubrun/config.py::_resolve_layers` and `resolve_config` | Reads only `PUBRUN_PROFILE` and `PUBRUN_META_REF` from the environment. Neither `PUBRUN_RUN_MODE_OVERRIDE` nor the other boot-time import variables enter `resolve_config()` or `config.resolved.json`. |

The boot-time import-mode selection flow across these components is:

```mermaid
flowchart TD
    S["Import pubrun or a mode submodule"] --> A{"PUBRUN_RUN_MODE_OVERRIDE valid?"}
    A -->|Yes| W1["Select PUBRUN_RUN_MODE_OVERRIDE (source: cli:pubrun run --mode)"]
    A -->|No| B{"Explicit mode submodule import?"}
    B -->|Yes| W2["Select submodule mode (source: explicit)"]
    B -->|No| C{"PUBRUN_IMPORT_MODE valid?"}
    C -->|Yes| W3["Select PUBRUN_IMPORT_MODE (source: env:PUBRUN_IMPORT_MODE)"]
    C -->|No| D{"PUBRUN_AUTO_START valid?"}
    D -->|Yes| W4["Select auto or noauto (source: env:PUBRUN_AUTO_START)"]
    D -->|No| E{"Config file sets [imports].mode or [core].auto_start?"}
    E -->|Yes| W5["Select first matching config file value"]
    E -->|No| W6["Select built-in default auto (source: default)"]
```

### Current documentation gaps

1. **`docs/functional_spec.md` (`### 10.2 Configuration Discovery`):** The final paragraph reads:
   `` `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, and `PUBRUN_IMPORT_CONFLICT` are not part of this merge. The boot sequence reads them during import-mode resolution and conflict handling (Sections 3.2 and 3.3), so they do not change the values recorded in `config.resolved.json`. ``
   It omits `PUBRUN_RUN_MODE_OVERRIDE` and Section 3.4.
2. **`docs/functional_spec.md` (`### 10.3 Supported Environment Variables`):** The table lists `PUBRUN_IMPORT_MODE`, `PUBRUN_PROFILE`, `PUBRUN_AUTO_START`, `PUBRUN_META_REF`, `PUBRUN_IMPORT_CONFLICT`, `XDG_CONFIG_HOME`, and `APPDATA`, and omits `PUBRUN_RUN_MODE_OVERRIDE`. Its `PUBRUN_IMPORT_MODE` row notes only that a submodule import takes precedence over it and that `pubrun run --mode` sets it, without noting `PUBRUN_RUN_MODE_OVERRIDE`.
3. **`docs/configuration.md` (`## Environment Variables`):** The table lists `PUBRUN_IMPORT_MODE`, `PUBRUN_PROFILE`, `PUBRUN_AUTO_START`, `PUBRUN_META_REF`, and `PUBRUN_IMPORT_CONFLICT`, and omits `PUBRUN_RUN_MODE_OVERRIDE`. In addition, the existing `PUBRUN_IMPORT_MODE` row states `"Takes highest precedence."`, which contradicts both `PUBRUN_RUN_MODE_OVERRIDE` and explicit in-code `import pubrun.<mode>` imports (already documented in `docs/configuration.md` under `### [imports]`).

## Proposed changes (ordered, validatable)

1. **`docs/functional_spec.md`, Section 10.2 boot-variable paragraph (E-01).** Under heading `### 10.2 Configuration Discovery`, replace the paragraph beginning `` `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, and `PUBRUN_IMPORT_CONFLICT` are not part of this merge. `` with:

   ```markdown
   `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, and `PUBRUN_IMPORT_CONFLICT` are not part of this merge. The boot sequence reads them during import-mode resolution, selection, and conflict handling (Sections 3.2, 3.3, and 3.4), so they do not change the values recorded in `config.resolved.json`.
   ```

2. **`docs/functional_spec.md`, Section 10.3 table (E-01).** Under heading `### 10.3 Supported Environment Variables`, replace the existing `PUBRUN_IMPORT_MODE` row with the following two rows (placing `PUBRUN_RUN_MODE_OVERRIDE` immediately before `PUBRUN_IMPORT_MODE`):

   ```markdown
   | `PUBRUN_RUN_MODE_OVERRIDE` | Launch-time import-mode override: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Takes precedence over explicit in-code submodule imports (such as `import pubrun.full`), `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, and config files (`[imports].mode`, `[core].auto_start`). Records `"cli:pubrun run --mode"` as `selected_by` and `selected_source` in `manifest.json` and suppresses import-mode conflicts under `[imports].on_conflict` and `PUBRUN_IMPORT_CONFLICT` for overridden and subsequent imports. Matching ignores case and surrounding whitespace; any other value is ignored. `pubrun run --mode` sets it alongside `PUBRUN_IMPORT_MODE` in the child process (Section 11.13). Consumed in the boot sequence (`select_mode`, not in `resolve_config()`). |
   | `PUBRUN_IMPORT_MODE` | Selects the import mode: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Overrides `PUBRUN_AUTO_START` and `[imports].mode`. `PUBRUN_RUN_MODE_OVERRIDE` and explicit submodule imports such as `import pubrun.noauto` take precedence over it (Section 3.4). Matching ignores case and surrounding whitespace; any other value is ignored. `pubrun run --mode` sets it alongside `PUBRUN_RUN_MODE_OVERRIDE` in the child process (Section 11.13). Consumed in the boot sequence (not in `resolve_config()`). |
   ```

3. **`docs/configuration.md`, `## Environment Variables` table (E-02).** Under heading `## Environment Variables`, replace the existing `PUBRUN_IMPORT_MODE` row with the following two rows (placing `PUBRUN_RUN_MODE_OVERRIDE` immediately before `PUBRUN_IMPORT_MODE`):

   ```markdown
   | `PUBRUN_RUN_MODE_OVERRIDE` | Launch-time import-mode override: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Takes highest precedence, overriding explicit in-code `import pubrun.<mode>` imports, `PUBRUN_IMPORT_MODE`, `PUBRUN_AUTO_START`, and config files (`[imports].mode`, `[core].auto_start`). `pubrun run --mode` sets it alongside `PUBRUN_IMPORT_MODE` in the child process. It records `"cli:pubrun run --mode"` as manifest provenance and suppresses import-mode conflicts under `[imports].on_conflict` and `PUBRUN_IMPORT_CONFLICT`. Matching ignores case and surrounding whitespace; any other value is ignored. Consumed during the boot sequence (not in `resolve_config()`). |
   | `PUBRUN_IMPORT_MODE` | Canonical import mode: `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, or `full`. Overrides `PUBRUN_AUTO_START` and config files (`[imports].mode`, `[core].auto_start`). `PUBRUN_RUN_MODE_OVERRIDE` and explicit in-code `import pubrun.<mode>` imports take precedence over it. Matching ignores case and surrounding whitespace; any other value is ignored. Consumed during the boot sequence (not in `resolve_config()`). |
   ```

## Deferred / out of scope (with reason)

- Updating `src/pubrun/__main__.py` (`--info` display and `run` subcommand `description`), `src/pubrun/_config_boot.py` module docstring, or `docs/functional_spec.md` Section 3.3 / 3.4. None of those are requested by backlog item `aqb2bu`, and Sections 3.4 and 11.13 already document the launch-time `pubrun run --mode` override.
- Adding a `CHANGELOG.md` entry. Plan `lhwy0t` already added the `### Fixed` changelog entry for `PUBRUN_RUN_MODE_OVERRIDE`, and this followup changes only documentation reference tables with no runtime behavior change.
- Adding `XDG_CONFIG_HOME`, `APPDATA`, or `PUBRUN_DEBUG` rows to `docs/configuration.md` (`## Environment Variables`). Those variables are outside the scope of backlog item `aqb2bu`.

## Scope check

- Over-scope: none. Only the three target locations in `docs/functional_spec.md` (Sections 10.2 and 10.3) and `docs/configuration.md` (`## Environment Variables`) are modified, plus the adjacent `PUBRUN_IMPORT_MODE` row in each of the two tables so neither contradicts `PUBRUN_RUN_MODE_OVERRIDE`.
- Under-scope: none. Every location named in backlog item `aqb2bu` is covered, and every stated behavior matches `src/pubrun/__main__.py`, `src/pubrun/_bootstrap.py`, `src/pubrun/_config_boot.py`, and `src/pubrun/config.py`.

## Required tests / validation

1. Run `git diff -- docs/functional_spec.md` and confirm that only the Section 10.2 paragraph and the `PUBRUN_RUN_MODE_OVERRIDE` / `PUBRUN_IMPORT_MODE` rows in Section 10.3 change, matching "Proposed changes" items 1 and 2 verbatim.
2. Run `git diff -- docs/configuration.md` and confirm that only the `PUBRUN_RUN_MODE_OVERRIDE` / `PUBRUN_IMPORT_MODE` rows in `## Environment Variables` change, matching "Proposed changes" item 3 verbatim.
3. Before committing, run the content and dash validation check across both modified files (must exit `0` and confirm zero em or en dashes in added lines):

   ```sh
   python3 -c '
   import pathlib, subprocess, sys

   spec = pathlib.Path("docs/functional_spec.md").read_text(encoding="utf-8")
   s102 = spec.split("### 10.2 Configuration Discovery", 1)[1].split("### 10.3 Supported Environment Variables", 1)[0]
   for var in ("PUBRUN_RUN_MODE_OVERRIDE", "PUBRUN_IMPORT_MODE", "PUBRUN_AUTO_START", "PUBRUN_IMPORT_CONFLICT"):
       assert var in s102, f"missing {var} in Section 10.2"
   s103 = spec.split("### 10.3 Supported Environment Variables", 1)[1].split("### 10.4 Configuration Contents", 1)[0]
   idx_ov = s103.index("| `PUBRUN_RUN_MODE_OVERRIDE` |")
   idx_im = s103.index("| `PUBRUN_IMPORT_MODE` |")
   assert idx_ov < idx_im, "Section 10.3 row order wrong"

   cfg = pathlib.Path("docs/configuration.md").read_text(encoding="utf-8")
   env_sec = cfg.split("## Environment Variables", 1)[1].split("\n---", 1)[0]
   idx_cfg_ov = env_sec.index("| `PUBRUN_RUN_MODE_OVERRIDE` |")
   idx_cfg_im = env_sec.index("| `PUBRUN_IMPORT_MODE` |")
   assert idx_cfg_ov < idx_cfg_im, "configuration.md row order wrong"
   im_row = next(l for l in env_sec.splitlines() if l.startswith("| `PUBRUN_IMPORT_MODE` |"))
   assert "Takes highest precedence." not in im_row, "stale precedence claim in PUBRUN_IMPORT_MODE"

   for path in ("docs/functional_spec.md", "docs/configuration.md"):
       diff = subprocess.check_output(["git", "diff", "-U0", "--", path], text=True)
       added = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
       assert added, f"no added lines in {path}"
       bad = [l for l in added if "\u2014" in l or "\u2013" in l]
       print(f"{path}: added_lines={len(added)} dashes={len(bad)}")
       if bad:
           sys.exit(1)
   '
   ```

4. Run `python3 -m pytest tests/test_import_modes.py tests/test_config.py --no-cov -q` and confirm exit status `0` (verifying the documented `PUBRUN_RUN_MODE_OVERRIDE`, `PUBRUN_IMPORT_MODE`, and `resolve_config` behaviors pass without regression).
5. Run `python3 scripts/sanitize_paths.py --check --all` and confirm exit status `0`.

## Spec / documentation sync

- `docs/functional_spec.md` (Sections 10.2 and 10.3) and `docs/configuration.md` (`## Environment Variables`) are updated in E-01 and E-02.
- `docs/cli.md` (`run` wrapper), `docs/manifest.md` (``## `pubrun_imports` ``), `docs/functional_spec.md` (Sections 3.4 and 11.13), and `CHANGELOG.md` already document `PUBRUN_RUN_MODE_OVERRIDE` from executed plan `lhwy0t` and require no further edits.
- `.aw/records/specs/` contains no `.spec.md` file governing `PUBRUN_RUN_MODE_OVERRIDE`, so no spec record changes.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: (1) Paste `git diff -- docs/functional_spec.md` showing only the updated Section 10.2 paragraph and the `PUBRUN_RUN_MODE_OVERRIDE` and `PUBRUN_IMPORT_MODE` rows in Section 10.3, matching "Proposed changes" items 1 and 2 verbatim. (2) Paste the `docs/functional_spec.md` output line and exit status `0` from the Python content and dash check in "Required tests / validation" item 3, confirming all four boot variables appear in Section 10.2, `PUBRUN_RUN_MODE_OVERRIDE` precedes `PUBRUN_IMPORT_MODE` in Section 10.3, and `dashes=0` across all added lines (`added_lines=3 dashes=0`).
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: (1) Paste `git diff -- docs/configuration.md` showing only the `PUBRUN_RUN_MODE_OVERRIDE` and `PUBRUN_IMPORT_MODE` rows in `## Environment Variables`, matching "Proposed changes" item 3 verbatim. (2) Paste the `docs/configuration.md` output line and exit status `0` from the Python content and dash check in "Required tests / validation" item 3, confirming `PUBRUN_RUN_MODE_OVERRIDE` precedes `PUBRUN_IMPORT_MODE`, the stale `"Takes highest precedence."` claim is gone from `PUBRUN_IMPORT_MODE`, and `dashes=0` across all added lines (`added_lines=2 dashes=0`). (3) Paste the summary line and exit status `0` of `python3 -m pytest tests/test_import_modes.py tests/test_config.py --no-cov -q`. (4) Paste the exit status `0` of `python3 scripts/sanitize_paths.py --check --all`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before changing any file. This plan has no open questions.
2. Scope declaration: `- Scope-Paths:` declares `docs/functional_spec.md` and `docs/configuration.md`. Do not expand scope; if execution requires an out-of-scope file, justify it with `--scope-reason` at finalization, and if a declared file needs no edit, acknowledge it with `--scope-ack`.
3. Validation honesty (HARD MUST): run every command in "Required tests / validation" after the final edit and paste its actual output into `V-01` and `V-02` `Observed evidence:`. Never mark a `V-*` item `pass` without captured output from that run.
4. Commit discipline: commit only the paths changed for this plan using `aw commit 87qr8h -- docs/functional_spec.md docs/configuration.md`. Never use `git add -A`, `git commit -a`, or raw `git commit`, and never push without an explicit human instruction.
5. Lifecycle transition: when executed inside a runner lane (`aw oc run` or `aw agy run`), the runner owns the lifecycle move after the merge-and-revalidate gate. When executed standalone outside a runner, run `aw ipd finalize 87qr8h` after `E-01` and `E-02` are `performed`, `V-01` and `V-02` are `pass`, and `aw ipd lint --phase pre-transition` reports `conforming` (never perform a manual `git mv` to `.aw/records/plans/executed/`).
