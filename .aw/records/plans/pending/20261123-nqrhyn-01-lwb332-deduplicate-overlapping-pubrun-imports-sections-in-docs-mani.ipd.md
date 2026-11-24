# IPD: Deduplicate overlapping pubrun_imports sections in docs/manifest.md

- Date: 2026-11-23
- Kind: child
- Concern: Manifest documentation accuracy and deduplication
- Scope: Remove the stale duplicate `## pubrun_imports` section in `docs/manifest.md` and reconcile the single remaining `## pubrun_imports` and `### pubrun_imports.requests[]` section against `src/pubrun/_bootstrap.py::get_import_metadata`, `src/pubrun/_modes.py::MODES`, and `schemas/manifest.schema.json`.
- Scope-Paths: docs/manifest.md
- Item-Dependencies: none
- Status: reviewed
- Readiness: go-pending-approval
- Review-Depth: standard
- Work-Kind: chore
- Priority: low
- From-Backlog: nqrhyn
- Set: nqrhyn
- Order: 1
- Highest E allocated: 02
- Author: Antigravity
- Id: lwb332

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 /plan-review (uri/its_direct/pt3-claude-opus-5.5-1m-us): APPROVE WITH REVISIONS APPLIED; PR-001..PR-007 fixed (PR-001 both sections omit `global_hooks`; PR-002 the "second section is correct" premise was false; PR-003 E-02 named `force_console` without saying it is `full`-only); review record `.aw/records/reviews/20261123-nqrhyn-01-lwb332-deduplicate-overlapping-pubrun-imports-sections-in-docs-mani.review.md`.
- 2026-11-24 draft (Antigravity): created.
- 2026-11-24 to-review (Antigravity): graduated from backlog item `nqrhyn` into a review-ready plan.

## Goal

`docs/manifest.md` is the user reference for every field pubrun writes to `manifest.json`. The `pubrun_imports` field records how pubrun was imported: which import mode won (for example `import pubrun.noauto` selects the `noauto` mode), who asked for it, and any later conflicting requests. The reference documents `pubrun_imports` twice, and the two tables disagree with each other and with the code. This plan deletes the first, stale table and corrects the remaining one so that every field, every mode, and every behavior flag it lists matches what pubrun actually writes.

No diagram is added: the change edits one section of one file in two sequential steps (technical writing standard requirement 12(c)).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Deduplicate and reconcile pubrun_imports in docs/manifest.md

- [ ] E-01 Remove the first, stale `## pubrun_imports` section in `docs/manifest.md`: the one between `## profiling` and `## capture` whose intro is the single sentence "Import-mode provenance metadata." and whose table lists `capture_state`.
  - Depends on: none
  - Expected outcome: The deleted block runs from that `## pubrun_imports` heading through the `---` separator that follows its table, so the file reads `## profiling` table, `---`, `## capture`, with exactly one `---` between them. `docs/manifest.md` then contains exactly one `## pubrun_imports` heading, located between `## capture` and `## status`. The file has no table of contents and no other Markdown file links to `#pubrun_imports` (checked at review), so no link needs updating.
  - Execution state: pending

- [ ] E-02 Correct the remaining `## pubrun_imports` table and its `### pubrun_imports.requests[]` table in `docs/manifest.md` so they match `src/pubrun/_bootstrap.py::get_import_metadata`, `src/pubrun/_bootstrap.py::select_mode`, `src/pubrun/_modes.py::MODES`, and `schemas/manifest.schema.json`.
  - Depends on: E-01
  - Expected outcome: The rows change as follows; rows not named here keep their current text.
    1. `## pubrun_imports` has exactly nine rows, one per key: `selected_mode`, `selected_behavior`, `selected_by`, `selected_source`, `selected_at_utc`, `core_loaded`, `conflict_policy`, `conflicts_detected`, `requests`. There is no `capture_state` row.
    2. `selected_mode` lists all six modes: `"auto"`, `"noauto"`, `"nopatch"`, `"noconsole"`, `"minimal"`, `"full"`.
    3. `selected_behavior` has type `object \| null` (the schema allows `null`) and names all five keys every mode has, `auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, `signal_hooks`, plus `force_console`, stated as present (`true`) only for `"full"`. Its em dash is replaced with plain punctuation.
    4. `selected_by` examples include `"pubrun"` and `"pubrun.<mode>"` (for example `"pubrun.noauto"`); `selected_source` examples include `"default"`, `"explicit"` (a `pubrun.<mode>` import), `"env:PUBRUN_IMPORT_MODE"`, `"env:PUBRUN_AUTO_START"`, `"config:[imports].mode"`, and `"config:[core].auto_start"`.
    5. `conflict_policy` states that it is `null` until a conflicting import-mode request occurs, and is then `"warn"`, `"error"`, or `"ignore"`.
    6. `requests` states that at most 50 requests are recorded.
    7. In `### pubrun_imports.requests[]`, `effective_behavior` names the same keys as `selected_behavior` (the five keys plus `force_console` for `"full"`); its other seven rows (`timestamp_utc`, `requested_mode`, `selected_by`, `selected`, `conflict`, `core_loaded_at_request`, `caller`) are unchanged.
    8. Neither section contains an em dash (U+2014) or en dash (U+2013).
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- Facts verified at review (lane HEAD `93995d7`) by reading the code and running it in a scratch directory:
  - `src/pubrun/_bootstrap.py::get_import_metadata` returns exactly nine keys: `selected_mode`, `selected_behavior`, `selected_by`, `selected_source`, `selected_at_utc`, `core_loaded`, `conflict_policy`, `conflicts_detected`, `requests`. `requests` is sliced to `_max_requests` (50). It never emits `capture_state`.
  - `src/pubrun/tracker.py::Run._get_import_metadata` puts that dict in the manifest; only its exception fallback returns `{"selected_mode": None, "capture_state": {"status": "unavailable"}}`. A manifest from `import pubrun` in a scratch directory had no `pubrun_imports.capture_state`.
  - `schemas/manifest.schema.json` `properties.pubrun_imports.properties` holds those nine keys, with `selected_behavior` typed `["object", "null"]` and `additionalProperties: true`.
  - `src/pubrun/_modes.py::MODES` holds six modes, `auto`, `noauto`, `nopatch`, `noconsole`, `minimal`, `full`. Each has five boolean keys, `auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, `signal_hooks`; only `full` adds `force_console: True`.
  - `src/pubrun/_bootstrap.py::select_mode` writes each request with the keys `timestamp_utc`, `requested_mode`, `selected_by`, `effective_behavior`, `selected`, `conflict`, `core_loaded_at_request`, and optional `caller`. Mode submodules call it with source `"explicit"` (for example `src/pubrun/noauto.py` `_behavior = select_mode("noauto", "pubrun.noauto", "explicit")`).
  - `src/pubrun/_config_boot.py::resolve_import_mode` returns the sources `"env:PUBRUN_IMPORT_MODE"`, `"env:PUBRUN_AUTO_START"`, `"config:[imports].mode"`, `"config:[core].auto_start"`, and `"default"`.
  - `src/pubrun/_bootstrap.py::_resolve_conflict_policy` is the only writer of `_conflict_policy` and runs only on a conflicting request, so a run without a conflict records `conflict_policy: null` (observed: `import pubrun` gave `null`; `import pubrun.minimal, pubrun.full` gave `"warn"`).
- `docs/manifest.md` has no table of contents; its only `pubrun_imports` links are the two headings themselves.
- Agent execution contract (`AGENTS.md`): user-facing documentation (`docs/manifest.md`) contains no em or en dashes in lines this plan authors or edits. Lines outside the `pubrun_imports` sections are not edited.

## Findings

`docs/manifest.md` has two `## pubrun_imports` sections, and neither matches the code:

1. The first (between `## profiling` and `## capture`) lists seven real fields plus `capture_state`, which pubrun does not write, and omits `core_loaded`, `requests`, and the `requests[]` table.
2. The second (between `## capture` and `## status`) lists all nine fields and the `requests[]` table, but:
   - `selected_mode` omits `"full"`;
   - `selected_behavior` and `requests[].effective_behavior` omit `global_hooks` (present in every mode) and `force_console` (in `full`);
   - `selected_behavior` is typed `object` though the schema allows `null`;
   - `conflict_policy` does not say it is `null` without a conflict, and `selected_source` omits `"explicit"`, the value a `pubrun.<mode>` import records;
   - `selected_behavior` contains an em dash.

## Proposed changes (ordered, validatable)

1. **`docs/manifest.md` (E-01):** Delete the first `## pubrun_imports` section and its trailing `---` separator.
2. **`docs/manifest.md` (E-02):** Edit the rows of the remaining `## pubrun_imports` and `### pubrun_imports.requests[]` tables as E-02 lists, using the Project conventions facts as the source of each value.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Only `docs/manifest.md` is modified; schema and runtime code are read-only sources of truth.
- Under-scope: none. Both the duplication and the field, mode, and behavior-key parity are covered, and the parity check in Required tests compares the document against the running code rather than against this plan's text.

## Required tests / validation

Run each command from the repository root and paste its actual output into the matching `V-*` item.

1. Heading count and order:

   ```bash
   grep -n -E '^## `(profiling|capture|pubrun_imports|status)`$' docs/manifest.md
   ```

   Expected: four lines in the order `profiling`, `capture`, `pubrun_imports`, `status`.
2. `git diff docs/manifest.md` (the whole change).
3. Parity check. It reads both tables from `docs/manifest.md`, runs pubrun in a temporary directory to get the real keys, reads the schema, and prints one line per mismatch; it must print `OK: ...` and exit 0. At review it printed eight mismatch lines and exited 1 on the unedited file, and printed `OK` on a corrected scratch copy.

   ```bash
   python3 - <<'EOF'
   import json, os, re, subprocess, sys, tempfile
   text = open("docs/manifest.md", encoding="utf-8").read()
   def section(h):
       body = text.split("\n" + h + "\n", 1)[1]
       return re.split(r"\n(?:---|## |### )", body, maxsplit=1)[0]
   def rows(body):
       return {m.group(1): m.group(0) for m in re.finditer(r"^\| `([a-z_]+)` \|.*$", body, re.M)}
   top = rows(section("## `pubrun_imports`")); req = rows(section("### `pubrun_imports.requests[]`"))
   probe = ("import json, pubrun.minimal, pubrun.full\nfrom pubrun._bootstrap import get_import_metadata\n"
            "from pubrun._modes import MODES\nm = get_import_metadata()\n"
            "print(json.dumps([sorted(m), sorted(set().union(*m['requests'])), {k: sorted(v) for k, v in MODES.items()}]))\n")
   env = dict(os.environ, PYTHONPATH=os.path.abspath("src"))
   rt_top, rt_req, modes = json.loads(subprocess.run([sys.executable, "-W", "ignore", "-c", probe], cwd=tempfile.mkdtemp(), env=env, capture_output=True, text=True, check=True).stdout)
   schema = sorted(json.load(open("schemas/manifest.schema.json"))["properties"]["pubrun_imports"]["properties"])
   keys = sorted(set().union(*modes.values())); p = []
   if sorted(top) != rt_top or rt_top != schema: p.append(f"top-level fields: doc={sorted(top)} runtime={rt_top} schema={schema}")
   if sorted(req) != rt_req: p.append(f"requests[] fields: doc={sorted(req)} runtime={rt_req}")
   p += [f"selected_mode row lacks {m!r}" for m in modes if f'"{m}"' not in top.get("selected_mode", "")]
   for row, src in (("selected_behavior", top), ("effective_behavior", req)):
       p += [f"{row} row lacks {k!r}" for k in keys if k not in src.get(row, "")]
   for n in ("## `pubrun_imports`", "### `pubrun_imports.requests[]`"):
       if re.search("[\u2013\u2014]", section(n)): p.append(f"{n} contains an em or en dash")
   print("\n".join(p) if p else "OK: pubrun_imports docs match runtime, schema, and MODES"); sys.exit(1 if p else 0)
   EOF
   ```

4. Dash check on added lines (prints `0`; `grep -c` exits 1 when the count is 0, which is the expected result):

   ```bash
   git diff -U0 docs/manifest.md | grep '^+[^+]' | grep -c $'[\u2013\u2014]'
   ```

5. Leak scan: `python3 scripts/sanitize_paths.py --check --all`; expected exit code 0 (it exited 0 at review).

## Spec / documentation sync

This plan is itself the documentation fix. No code, schema, or behavior changes. No spec in `.aw/records/specs/` describes `pubrun_imports` (searched at review), and no other document under `docs/` describes its fields, so no other file changes. No `CHANGELOG.md` entry: the change corrects reference text without changing behavior; add one only if the maintainer asks.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste the heading-order output (Required tests 1) showing four lines in the order `profiling`, `capture`, `pubrun_imports`, `status`, and the hunk of `git diff docs/manifest.md` that deletes the stale section, showing its `capture_state` row among the removed lines and one `---` left between `## profiling` and `## capture`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste the hunk of `git diff docs/manifest.md` for the remaining `## pubrun_imports` and `### pubrun_imports.requests[]` tables; the parity check output (Required tests 3) printing `OK: pubrun_imports docs match runtime, schema, and MODES` (the runtime keys come from `src/pubrun/_bootstrap.py::get_import_metadata`, reached through `src/pubrun/minimal.py` and `src/pubrun/full.py` imports in the probe); a sentence confirming that the diff makes each E-02 change 3 to 6 that the parity check does not test (`object \| null`, the `"explicit"` source, the `conflict_policy` `null` note, the 50-request limit); the dash check (Required tests 4) printing `0`; and the output and exit code of `python3 scripts/sanitize_paths.py --check --all`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:

1. Precondition: wait for human approval (`- Status: approved`) before you change any file. This plan has no open question.
2. Scope declaration: the expected modified file is the `- Scope-Paths:` entry, `docs/manifest.md`. If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If the declared file needs no edit, acknowledge it with `--scope-ack`.
3. Validation honesty: you MUST run each Required tests command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only `docs/manifest.md` with `aw commit lwb332 -- docs/manifest.md`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize lwb332`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize lwb332` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
