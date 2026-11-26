# IPD: Update example scripts and expected methods output to match live API

- Date: 2026-11-25
- Kind: child
- Concern: Eight numbered example scripts (`examples/01_*.py` through `examples/11_*.py`) teach the deprecated, inert `profile=` argument (with `11_cli_report.py` passing `"standard"` and invoking the hidden legacy alias `report` in both code and docstring), all nine targeted scripts use the legacy `PUBRUN_AUTO_START="false"` environment-variable pattern instead of `import pubrun.noauto as pubrun`, `10_hardware_probe.py`'s docstring still refers to a "deep profile", and `examples/minimal-research-workflow/expected_methods.md` shows freeform prose that diverges from `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE`.
- Scope: Nine numbered example scripts (`examples/01_minimal_start_stop.py`, `examples/02_context_manager.py`, `examples/03_audit_decorator.py`, `examples/04_annotate_events.py`, `examples/05_execution_phases.py`, `examples/08_diff_engine.py`, `examples/09_cli_methods.py`, `examples/10_hardware_probe.py`, `examples/11_cli_report.py`) and `examples/minimal-research-workflow/expected_methods.md`.
- Scope-Paths: examples/01_minimal_start_stop.py, examples/02_context_manager.py, examples/03_audit_decorator.py, examples/04_annotate_events.py, examples/05_execution_phases.py, examples/08_diff_engine.py, examples/09_cli_methods.py, examples/10_hardware_probe.py, examples/11_cli_report.py, examples/minimal-research-workflow/expected_methods.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Remove deprecated profile= kwargs from examples 01-11, switch them to pubrun.noauto, update 10/11 docstrings and CLI call, and align expected_methods.md with template output
- Work-Kind: chore
- Priority: medium
- Set: doc-audit
- Order: 6
- Highest E allocated: 03
- Author: Antigravity
- Id: 2uwuiu
- Approval: 2026-11-26, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Gemini 4 Neon, Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001..PR-006 all FIXED; review record `.aw/records/reviews/20261125-doc-audit-06-2uwuiu-update-example-scripts-and-expected-methods-output-to-match.review.md`.
- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 3 example-suite and output-alignment fixes (2 verified findings across 10 files under `examples/`)
- 2026-11-25 draft (Antigravity): created.

## Goal

Ensure the targeted example scripts in `examples/` teach current, non-deprecated `pubrun` APIs (`import pubrun.noauto as pubrun`, zero `profile=` arguments, zero `profile_deprecated` manifest notices via `src/pubrun/config.py::profile_deprecation_notice`, and `pubrun show` instead of the hidden `report` alias) and that `examples/minimal-research-workflow/expected_methods.md` accurately mirrors `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE` as rendered by `src/pubrun/report/methods.py::generate_report`.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Remove deprecated `profile=` usage and legacy `PUBRUN_AUTO_START` from targeted numbered examples

- [x] E-01 Update `examples/01_minimal_start_stop.py`, `examples/02_context_manager.py`, `examples/03_audit_decorator.py`, `examples/04_annotate_events.py`, and `examples/05_execution_phases.py`:
  - Remove every deprecated `profile="minimal"` keyword argument from `pubrun.start()`, `pubrun.tracked_run()`, and `@pubrun.audit_run()` (two decorators in `examples/03_audit_decorator.py`).
  - Replace `os.environ["PUBRUN_AUTO_START"] = "false"` and `import pubrun` with `import pubrun.noauto as pubrun` in all five scripts (keep `import os` in each file because all five call `os.path`).
  - Keep existing `[PASS]` stdout lines and manifest/event assertions unchanged so `examples/verify_all.py::main` and `tests/test_examples_smoke.py::test_example_runs_and_creates_manifest` continue to pass.
  - Depends on: none
  - Expected outcome: None of examples `01`-`05` pass `profile=` or set `PUBRUN_AUTO_START`, all five import `pubrun.noauto as pubrun`, and each runs cleanly with zero `profile_deprecated` notices in its generated `manifest.json`.
  - Execution state: performed

- [x] E-02 Update `examples/08_diff_engine.py`, `examples/09_cli_methods.py`, `examples/10_hardware_probe.py`, and `examples/11_cli_report.py`:
  - Remove deprecated `profile="minimal"` and `profile="standard"` keyword arguments from `examples/08_diff_engine.py` (two calls), `examples/09_cli_methods.py`, and `examples/11_cli_report.py`.
  - Replace `os.environ["PUBRUN_AUTO_START"] = "false"` and `import pubrun` with `import pubrun.noauto as pubrun` across all four scripts (`08`, `09`, `10`, `11`), and remove the now-unused `import os` from `examples/09_cli_methods.py` and `examples/11_cli_report.py` (keep `import os` in `08_diff_engine.py`, which uses `os.environ` for `PUBRUN_DUMMY_VAR`, and in `10_hardware_probe.py`, which uses `os.path`). Subprocess CLI calls (`python -m pubrun ...`) do not auto-start because `src/pubrun/core.py::_is_pubrun_cli_invocation` suppresses auto-start for CLI invocations.
  - Update `examples/10_hardware_probe.py`'s module docstring from "Hardware capture with deep profile" and "deep-profile run" to accurately reference `capture={"hardware": {"depth": "deep"}}`.
  - Update `examples/11_cli_report.py` to invoke `[sys.executable, "-m", "pubrun", "show"]` instead of `"report"`, update its module docstring to describe `pubrun show` (noting in docstring or comment that `pubrun report` remains a hidden legacy alias), and keep the filename `11_cli_report.py`, `[PASS]` stdout line, and `PUBRUN DIAGNOSTICS` / `Run ID` assertions unchanged.
  - Depends on: none
  - Expected outcome: None of examples `08`-`11` pass `profile=` or set `PUBRUN_AUTO_START`, `09_cli_methods.py` and `11_cli_report.py` have no unused `import os`, `10_hardware_probe.py`'s docstring matches its `capture={"hardware": {"depth": "deep"}}` call, and `11_cli_report.py` demonstrates `pubrun show` in both code and docstring with zero `profile_deprecated` notices in its generated `manifest.json`.
  - Execution state: performed

### Task group 2: Align `expected_methods.md` and run example verification

- [x] E-03 Update `examples/minimal-research-workflow/expected_methods.md` and run the full example verification suite:
  - Replace the freeform prose blockquote in `examples/minimal-research-workflow/expected_methods.md` (removing the unsupported sentence about a "deterministic synthetic dataset generated with a fixed random seed") with a representative sample that mirrors `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE` as rendered by `src/pubrun/report/methods.py::generate_report` for `examples/minimal-research-workflow/analysis.py`: `### Computational Methods`, the OS/CPU/RAM and `Python <version> (Cpython)` sentence, `Standard library dependencies were utilized.` (with a brief note outside the sample that highlighted libraries such as `numpy` or `pandas` appear when imported), the Git commit `` `<8-char-sha>` `` (optional `(origin: ...)`) and `pubrun v<version>` [1] sentence, and the exact `**References:**` `[1] Fariello, G. (2026). pubrun: Low-friction execution provenance for Python research [Computer software]. https://github.com/fariello/pubrun` line.
  - Use generic redacted placeholders rather than machine-local paths or hostnames (must pass `scripts/sanitize_paths.py --check --all`), keep the `pubrun methods --format markdown` and `pubrun methods ./runs/<RUN_DIRECTORY> --format markdown` commands, and introduce zero em or en dashes (`\u2013`, `\u2014`) in added or edited lines.
  - Run all validation checks in `## Required tests / validation`, including `python3 examples/verify_all.py`, the runtime zero-`profile_deprecated` manifest check, and `python3 -m pytest tests/test_examples_smoke.py tests/test_example_minimal_research_workflow.py -v --no-cov -p no:cacheprovider`.
  - Depends on: E-01, E-02
  - Expected outcome: `expected_methods.md` mirrors live `pubrun methods --format markdown` output with zero em/en dashes and zero broken links, all nine updated example scripts emit zero `profile_deprecated` manifest notices, `examples/verify_all.py` exits 0, both example pytest modules pass, and `scripts/sanitize_paths.py --check --all` exits 0.
  - Execution state: performed

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`examples/minimal-research-workflow/expected_methods.md`).
- `GUIDING_PRINCIPLES.md` is not present in this repository; review applies the fallback principles: Intuitive and self-documenting, General-case and configurable, KISS, and Honest documentation.
- `src/pubrun/config.py::profile_deprecation_notice` and `src/pubrun/resources/default.toml` deprecate `core.profile` as inert and record a `profile_deprecated` notice in `manifest["config"]["notices"]` for any non-empty value other than `"default"`.
- `src/pubrun/noauto.py` exports the full `pubrun` public API (`start`, `stop`, `tracked_run`, `audit_run`, `annotate`, `phase`, `diff`, `get_current_run`, etc.) without auto-starting a run and populates the parent `pubrun` package namespace; `src/pubrun/_config_boot.py::resolve_import_mode` retains `PUBRUN_AUTO_START` as a legacy alias.
- `src/pubrun/core.py::_is_pubrun_cli_invocation` prevents `python -m pubrun ...` CLI subprocesses from auto-starting a run even without `PUBRUN_AUTO_START="false"` in the environment.
- `src/pubrun/__main__.py::main` registers `show` as the primary diagnostic subcommand and hides `report` as a legacy alias (`help=argparse.SUPPRESS`); both route to `src/pubrun/report/diagnostics.py`, which outputs `PUBRUN DIAGNOSTICS` and `Run ID`.
- `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE` and `src/pubrun/report/methods.py::generate_report` format `### Computational Methods`, OS/CPU/RAM, `Python <version> (Cpython)` (`python_impl.capitalize()`), `Standard library dependencies were utilized.` (for stdlib-only scripts like `examples/minimal-research-workflow/analysis.py`), 8-char Git commit, `pubrun v<version>` [1], and `**References:**`.
- `examples/verify_all.py::main` discovers `[0-9]*.py` (`00_auto_start.py` through `12_external_file_provenance.py`) plus `examples/minimal-research-workflow/analysis.py` and runs each in a fresh temporary directory.
- `tests/test_examples_smoke.py::test_example_runs_and_creates_manifest` runs every `examples/[0-9]*.py` script in a temporary directory and asserts `returncode == 0`, `"[PASS]" in result.stdout`, and at least one `runs/*/manifest.json`; `tests/test_example_minimal_research_workflow.py` tests `examples/minimal-research-workflow/analysis.py` (it does not read `expected_methods.md`).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| E-01f | Medium | Low | New User / Evaluator | `examples/01_minimal_start_stop.py` through `examples/11_cli_report.py` vs `src/pubrun/config.py::profile_deprecation_notice`, `src/pubrun/noauto.py`, and `src/pubrun/__main__.py::main` | Eight examples pass deprecated/inert `profile=` (`11_cli_report.py` passes `"standard"` and invokes hidden alias `report` in code and docstring), all nine targeted scripts use legacy `PUBRUN_AUTO_START="false"`, and `10_hardware_probe.py` docstring still calls it "deep profile". |
| E-02f | Low | Low | New User / Academic | `examples/minimal-research-workflow/expected_methods.md` vs `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE` and `src/pubrun/report/methods.py::generate_report` | Sample paragraph diverges from `pubrun methods` template structure and implies script-specific prose about synthetic datasets and fixed random seeds. |

## Proposed changes (ordered, validatable)

1. Remove deprecated `profile="minimal"` and switch `PUBRUN_AUTO_START="false"` to `import pubrun.noauto as pubrun` in examples `01`-`05` (E-01; Remediation Risk: Low).
2. Remove deprecated `profile=` from examples `08`, `09`, `11`, switch examples `08`-`11` to `import pubrun.noauto as pubrun` (dropping unused `import os` in `09` and `11`), fix `10_hardware_probe.py`'s docstring, and update `11_cli_report.py`'s CLI invocation and docstring to `pubrun show` (E-02; Remediation Risk: Low).
3. Align `examples/minimal-research-workflow/expected_methods.md` with `MARKDOWN_TEMPLATE` / `generate_report` and run the full example verification suite, runtime notice check, dash check, link check, and path sanitizer (E-03; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- `examples/06_subprocess_spy.py`, `examples/07_file_capture.py`, and `examples/12_external_file_provenance.py` still set legacy `PUBRUN_AUTO_START="false"` (still supported by `src/pubrun/_config_boot.py::resolve_import_mode`) and do not pass `profile=`; left untouched to stay within the `/assess-documentation` findings scope.
  - Carrier-Declined: `PUBRUN_AUTO_START` remains a supported legacy alias and these three scripts have zero `profile=` usage; no follow-up is required by Set `doc-audit`.
- Renaming `examples/11_cli_report.py` is out of scope because `docs/research-use.md` and sibling plan `wjsccu` reference the existing filename.
  - Carrier-Declined: Filename retained intentionally for documentation stability; no rename follow-up is wanted.
- Repo-wide historical em/en-dash sweep across untouched Markdown is deferred at the Set level (orchestrator `86cd17`); this plan enforces zero em/en dashes in added or edited lines of `examples/minimal-research-workflow/expected_methods.md`.
  - Carrier-Declined: Pre-existing repo-wide cleanup deferred separately at Set level (`86cd17`) to avoid noisy diffs across untouched sections.

## Scope check

- Over-scope: none. Only the 10 declared files under `examples/` are modified; no product code, tests, or other docs are touched.
- Under-scope: none. `- Scope-Paths:` is strictly disjoint from all five sibling plans in Set `doc-audit` (`0cjiv5`, `pqcx6o`, `dd7noz`, `wjsccu`, `77pdvl`) and from orchestrator `86cd17`.
- Diagram check (Technical Writing Standard Requirement 12): no Mermaid diagram is needed because this plan edits existing example scripts and one short sample Markdown file with no new multi-entity data model, branch, loop, or status lifecycle (Requirement 12(c)).

## Required tests / validation

1. **Negative `grep` checks** (all must exit `1`; pre-execution baselines verified as `exit=0`):
   - `grep -rn "profile=" examples/0*.py examples/1*.py; echo "exit=$?"` (baseline: 10 matches across 8 files, `exit=0`)
   - `grep -rn "PUBRUN_AUTO_START" examples/01_minimal_start_stop.py examples/02_context_manager.py examples/03_audit_decorator.py examples/04_annotate_events.py examples/05_execution_phases.py examples/08_diff_engine.py examples/09_cli_methods.py examples/10_hardware_probe.py examples/11_cli_report.py; echo "exit=$?"` (baseline: 9 matches across 9 files, `exit=0`)
   - `grep -nE "deep profile|deep-profile" examples/10_hardware_probe.py; echo "exit=$?"` (baseline: 2 matches, `exit=0`)
   - `grep -n '"report"' examples/11_cli_report.py; echo "exit=$?"` (baseline: 1 match, `exit=0`)
   - `grep -n "fixed random seed" examples/minimal-research-workflow/expected_methods.md; echo "exit=$?"` (baseline: 1 match, `exit=0`)
2. **Zero em/en dashes on added lines** of `examples/minimal-research-workflow/expected_methods.md` (must exit 0):

   ```sh
   python3 - <<'PY'
   import subprocess, sys
   diff = subprocess.check_output(
       ["git", "diff", "-U0", "--", "examples/minimal-research-workflow/expected_methods.md"],
       text=True,
   )
   hits = [
       line for line in diff.splitlines()
       if line.startswith("+") and not line.startswith("+++")
       and ("\u2013" in line or "\u2014" in line)
   ]
   print(f"dash_hits={len(hits)}")
   for h in hits:
       print(h)
   sys.exit(1 if hits else 0)
   PY
   ```

3. **Relative and anchor Markdown link check** on `examples/minimal-research-workflow/expected_methods.md` (orchestrator `86cd17` Cross-IPD validation; must exit 0 with `broken=0`, baseline `broken=0`):

   ```sh
   python3 - <<'PY'
   import pathlib, re, sys
   def slugs_for(path: pathlib.Path) -> set[str]:
       slugs = set()
       text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
       for m in re.finditer(r"^#{1,6}\s+(.+)$", text, flags=re.M):
           raw = re.sub(r"`([^`]*)`", r"\1", m.group(1).strip())
           slug = re.sub(r"[^\w\s-]", "", raw.lower()).strip()
           slugs.add(re.sub(r"\s+", "-", slug))
       return slugs
   f = pathlib.Path("examples/minimal-research-workflow/expected_methods.md")
   text = re.sub(r"```.*?```", "", f.read_text(encoding="utf-8"), flags=re.S)
   bad = 0
   for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
       t = m.group(1).strip().split()[0]
       if t.startswith(("http://", "https://", "mailto:")):
           continue
       if t.startswith("#"):
           ok = t[1:] in slugs_for(f)
       else:
           p, _, frag = t.partition("#")
           target = (f.parent / p).resolve()
           ok = target.exists() and (not frag or not target.is_file() or frag in slugs_for(target))
       if not ok:
           bad += 1
           print("BROKEN", f, t)
   print(f"broken={bad}")
   sys.exit(1 if bad else 0)
   PY
   ```

4. **Runtime zero-`profile_deprecated` manifest notice check** across the 9 updated example scripts (must exit 0 with `notices=0`):

   ```sh
   python3 - <<'PY'
   import json, os, pathlib, subprocess, sys, tempfile
   repo = pathlib.Path.cwd()
   env = os.environ.copy()
   env["PYTHONPATH"] = f"{repo / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
   scripts = [
       "examples/01_minimal_start_stop.py",
       "examples/02_context_manager.py",
       "examples/03_audit_decorator.py",
       "examples/04_annotate_events.py",
       "examples/05_execution_phases.py",
       "examples/08_diff_engine.py",
       "examples/09_cli_methods.py",
       "examples/10_hardware_probe.py",
       "examples/11_cli_report.py",
   ]
   bad = []
   manifests_checked = 0
   with tempfile.TemporaryDirectory(prefix="pubrun-ex-notices-") as tmp:
       for rel in scripts:
           sub = pathlib.Path(tmp) / pathlib.Path(rel).stem
           sub.mkdir()
           res = subprocess.run([sys.executable, str(repo / rel)], cwd=sub, env=env, capture_output=True, text=True, timeout=120)
           if res.returncode != 0:
               bad.append((rel, f"rc={res.returncode}: {res.stderr.strip()}"))
               continue
           manifests = sorted(sub.glob("runs/*/manifest.json"))
           if not manifests:
               bad.append((rel, "no manifest.json created"))
               continue
           for mf in manifests:
               manifests_checked += 1
               data = json.loads(mf.read_text(encoding="utf-8"))
               notices = [n for n in data.get("config", {}).get("notices", []) if n.get("code") == "profile_deprecated"]
               if notices:
                   bad.append((rel, f"profile_deprecated notices: {notices}"))
   print(f"manifests_checked={manifests_checked} notices={len(bad)}")
   for item in bad:
       print("FAIL", item)
   sys.exit(1 if bad else 0)
   PY
   ```

5. **Master example runner**: `python3 examples/verify_all.py` (must exit 0).
6. **Example pytest suites**: `python3 -m pytest tests/test_examples_smoke.py tests/test_example_minimal_research_workflow.py -v --no-cov -p no:cacheprovider` (must exit 0).
7. **Path leak sanitizer**: `python3 scripts/sanitize_paths.py --check --all` (must exit 0).

## Spec / documentation sync

- Updates example scripts and sample expected methods output only; no runtime library behavior or schema contract changes.
- Sibling `doc-audit` plans own all other repository documentation fixes (`0cjiv5`: root docs and templates; `pqcx6o`: `docs/cli.md` and `docs/configuration.md`; `dd7noz`: `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, `docs/design/`; `wjsccu`: `docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`; `77pdvl`: `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, `CITATION.cff`).

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Pasted `git diff -- examples/01_minimal_start_stop.py examples/02_context_manager.py examples/03_audit_decorator.py examples/04_annotate_events.py examples/05_execution_phases.py` confirming zero `profile=` calls and `import pubrun.noauto as pubrun` across all five files, plus pasted `grep -rn "profile=\|PUBRUN_AUTO_START" examples/01_minimal_start_stop.py examples/02_context_manager.py examples/03_audit_decorator.py examples/04_annotate_events.py examples/05_execution_phases.py; echo "exit=$?"` showing `exit=1`.
  - Observed evidence:
    ~~~~diff
    diff --git a/examples/01_minimal_start_stop.py b/examples/01_minimal_start_stop.py
    index f0c77b8..f38301e 100755
    --- a/examples/01_minimal_start_stop.py
    +++ b/examples/01_minimal_start_stop.py
    @@ -4,14 +4,13 @@
     Verifies manual initialization, tracking, and manifest generation.
     """
     import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import json
    -import pubrun
    +import pubrun.noauto as pubrun


     def main() -> None:
         print("Testing 01_minimal_start_stop...")
    -    tracker = pubrun.start(profile="minimal")
    +    tracker = pubrun.start()

         run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
         assert run_dir is not None, "Run directory not created."
    diff --git a/examples/02_context_manager.py b/examples/02_context_manager.py
    index 6c31025..811b8dd 100755
    --- a/examples/02_context_manager.py
    +++ b/examples/02_context_manager.py
    @@ -4,15 +4,14 @@
     Verifies that tracked_run() scopes tracking to the with-block.
     """
     import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import json
    -import pubrun
    +import pubrun.noauto as pubrun


     def main() -> None:
         print("Testing 02_context_manager...")
         run_dir = None
    -    with pubrun.tracked_run(profile="minimal") as active_run:
    +    with pubrun.tracked_run() as active_run:
             tracker = getattr(active_run, "run_tracker", None)
             run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
             assert run_dir is not None, "Run directory not accessible inside context."
    diff --git a/examples/03_audit_decorator.py b/examples/03_audit_decorator.py
    index a7e0a5d..8f04cea 100755
    --- a/examples/03_audit_decorator.py
    +++ b/examples/03_audit_decorator.py
    @@ -4,20 +4,19 @@
     Verifies that the decorator tracks both successful and failing functions.
     """
     import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import json
    -import pubrun
    +import pubrun.noauto as pubrun
     from pubrun.tracker import get_current_run


    -@pubrun.audit_run(profile="minimal")
    +@pubrun.audit_run()
     def success_task() -> str:
         """Return the run directory path."""
         tracker = get_current_run()
         return getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))


    -@pubrun.audit_run(profile="minimal")
    +@pubrun.audit_run()
     def failing_task() -> None:
         """Raise an exception to test failure recording."""
         tracker = get_current_run()
    diff --git a/examples/04_annotate_events.py b/examples/04_annotate_events.py
    index e9e7896..c0beaa5 100755
    --- a/examples/04_annotate_events.py
    +++ b/examples/04_annotate_events.py
    @@ -4,14 +4,13 @@
     Verifies that annotate() writes structured events to events.jsonl.
     """
     import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import json
    -import pubrun
    +import pubrun.noauto as pubrun


     def main() -> None:
         print("Testing 04_annotate_events...")
    -    tracker = pubrun.start(profile="minimal")
    +    tracker = pubrun.start()
         run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))

         pubrun.annotate("Matrix Instantiated", dimensions="1024x1024", simulated_device="cpu")
    diff --git a/examples/05_execution_phases.py b/examples/05_execution_phases.py
    index 7cb85f9..89cb13b 100755
    --- a/examples/05_execution_phases.py
    +++ b/examples/05_execution_phases.py
    @@ -6,10 +6,9 @@ that each phase_end event carries a monotonic duration, and that the finalized
     manifest separates the tracked workload from pubrun's own capture overhead.
     """
     import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import json
     import time
    -import pubrun
    +import pubrun.noauto as pubrun


     def _is_duration(value: object) -> bool:
    @@ -18,7 +17,7 @@ def _is_duration(value: object) -> bool:

     def main() -> None:
         print("Testing 05_execution_phases...")
    -    tracker = pubrun.start(profile="minimal")
    +    tracker = pubrun.start()
         run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))

         with pubrun.phase("Dataset Initialization"):
    ~~~~
    ~~~~text
    $ grep -rn "profile=\|PUBRUN_AUTO_START" examples/01_minimal_start_stop.py examples/02_context_manager.py examples/03_audit_decorator.py examples/04_annotate_events.py examples/05_execution_phases.py; echo "exit=$?"
    exit=1
    ~~~~
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `git diff -- examples/08_diff_engine.py examples/09_cli_methods.py examples/10_hardware_probe.py examples/11_cli_report.py` confirming zero `profile=` calls, `import pubrun.noauto as pubrun` across all four files, removal of unused `import os` in `09_cli_methods.py` and `11_cli_report.py`, updated `10_hardware_probe.py` docstring, and `pubrun show` in both code and docstring of `11_cli_report.py`; plus pasted negative `grep` checks (Required tests item 1) for `profile=` across `examples/0*.py examples/1*.py`, `PUBRUN_AUTO_START` across the 9 updated scripts, `deep profile|deep-profile` in `10_hardware_probe.py`, and `"report"` in `11_cli_report.py`, all showing `exit=1`.
  - Observed evidence:
    ~~~~diff
    diff --git a/examples/08_diff_engine.py b/examples/08_diff_engine.py
    index 49bb94c..36ac7df 100755
    --- a/examples/08_diff_engine.py
    +++ b/examples/08_diff_engine.py
    @@ -5,8 +5,7 @@ Creates two runs with different environment variables and verifies that
     pubrun.diff() detects the change.
     """
     import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
    -import pubrun
    +import pubrun.noauto as pubrun


     def main() -> None:
    @@ -15,13 +14,13 @@ def main() -> None:

         # Run A: baseline environment
         os.environ["PUBRUN_DUMMY_VAR"] = "BASELINE"
    -    tracker1 = pubrun.start(profile="minimal")
    +    tracker1 = pubrun.start()
         run_dir_a = getattr(tracker1, "run_dir", getattr(tracker1, "_run_dir", None))
         pubrun.stop()

         # Run B: mutated environment
         os.environ["PUBRUN_DUMMY_VAR"] = "MUTATED"
    -    tracker2 = pubrun.start(profile="minimal")
    +    tracker2 = pubrun.start()
         run_dir_b = getattr(tracker2, "run_dir", getattr(tracker2, "_run_dir", None))
         pubrun.stop()

    diff --git a/examples/09_cli_methods.py b/examples/09_cli_methods.py
    index deccf6d..45c9c48 100755
    --- a/examples/09_cli_methods.py
    +++ b/examples/09_cli_methods.py
    @@ -4,17 +4,15 @@
     Creates a run, then invokes `pubrun methods --format markdown` via subprocess
     and verifies the output contains expected methodology text.
     """
    -import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import subprocess
     import sys
    -import pubrun
    +import pubrun.noauto as pubrun


     def main() -> None:
         print("Testing 09_cli_methods...")

    -    tracker = pubrun.start(profile="minimal")
    +    tracker = pubrun.start()
         tracker.stop()

         cmd = [sys.executable, "-m", "pubrun", "methods", "--format", "markdown"]
    diff --git a/examples/10_hardware_probe.py b/examples/10_hardware_probe.py
    index 23d2a39..bce7e9f 100755
    --- a/examples/10_hardware_probe.py
    +++ b/examples/10_hardware_probe.py
    @@ -1,13 +1,12 @@
     #!/usr/bin/env python3
    -"""Test 10: Hardware capture with deep profile.
    +"""Test 10: Hardware capture with deep hardware depth.

    -Creates a deep-profile run that allocates memory, then verifies the manifest
    -contains hardware data (cpu, memory).
    +Creates a run with capture={"hardware": {"depth": "deep"}} that allocates
    +memory, then verifies the manifest contains hardware data (cpu, memory).
     """
     import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import json
    -import pubrun
    +import pubrun.noauto as pubrun


     def main() -> None:
    diff --git a/examples/11_cli_report.py b/examples/11_cli_report.py
    index 4df700f..bd67d9c 100755
    --- a/examples/11_cli_report.py
    +++ b/examples/11_cli_report.py
    @@ -1,23 +1,22 @@
     #!/usr/bin/env python3
    -"""Test 11: CLI report generation.
    +"""Test 11: CLI diagnostic output via `pubrun show`.

    -Creates a run and invokes `pubrun report` via subprocess, then verifies
    -the output contains expected diagnostic headers and fields.
    +Creates a run and invokes `pubrun show` via subprocess (`pubrun report`
    +remains a hidden legacy alias), then verifies the output contains expected
    +diagnostic headers and fields.
     """
    -import os
    -os.environ["PUBRUN_AUTO_START"] = "false"
     import subprocess
     import sys
    -import pubrun
    +import pubrun.noauto as pubrun


     def main() -> None:
         print("Testing 11_cli_report...")

    -    tracker = pubrun.start(profile="standard")
    +    tracker = pubrun.start()
         tracker.stop()

    -    cmd = [sys.executable, "-m", "pubrun", "report"]
    +    cmd = [sys.executable, "-m", "pubrun", "show"]
         result = subprocess.run(cmd, capture_output=True, text=True)

         output = result.stdout.strip()
    ~~~~
    ~~~~text
    $ grep -rn "profile=" examples/0*.py examples/1*.py; echo "exit=$?"
    exit=1
    $ grep -rn "PUBRUN_AUTO_START" examples/01_minimal_start_stop.py examples/02_context_manager.py examples/03_audit_decorator.py examples/04_annotate_events.py examples/05_execution_phases.py examples/08_diff_engine.py examples/09_cli_methods.py examples/10_hardware_probe.py examples/11_cli_report.py; echo "exit=$?"
    exit=1
    $ grep -nE "deep profile|deep-profile" examples/10_hardware_probe.py; echo "exit=$?"
    exit=1
    $ grep -n '"report"' examples/11_cli_report.py; echo "exit=$?"
    exit=1
    ~~~~
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Pasted `git diff -- examples/minimal-research-workflow/expected_methods.md` confirming alignment with `MARKDOWN_TEMPLATE` (`### Computational Methods`, OS/CPU/RAM/Python `(Cpython)`, `Standard library dependencies were utilized.`, Git commit, `pubrun v... [1]`, `**References:**`) and `grep -n "fixed random seed" examples/minimal-research-workflow/expected_methods.md; echo "exit=$?"` showing `exit=1`; pasted zero-dash check (Required tests item 2) showing `dash_hits=0` and exiting 0; pasted relative/anchor link check (Required tests item 3) showing `broken=0` and exiting 0; pasted runtime zero-`profile_deprecated` notice check (Required tests item 4) showing `notices=0` and exiting 0; pasted output of `python3 examples/verify_all.py` exiting 0; pasted output of `python3 -m pytest tests/test_examples_smoke.py tests/test_example_minimal_research_workflow.py -v --no-cov -p no:cacheprovider` exiting 0; and pasted output of `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
    ~~~~diff
    diff --git a/examples/minimal-research-workflow/expected_methods.md b/examples/minimal-research-workflow/expected_methods.md
    index f0332dd..1c8f732 100644
    --- a/examples/minimal-research-workflow/expected_methods.md
    +++ b/examples/minimal-research-workflow/expected_methods.md
    @@ -1,8 +1,24 @@
     # Representative methods output

    -The exact methods text generated by `pubrun methods` depends on the local machine, Python environment, package state, operating system, and Git state. A completed run of this example should produce methods text similar in purpose to the following:
    +The exact text generated by `pubrun methods --format markdown` depends on the local machine, operating system, Python runtime, package state, and Git state. A completed run of `analysis.py` produces output with the following structure (machine-specific values replace the placeholders in angle brackets):

    -> Computational experiments were executed using Python in a local command-line environment. Execution provenance was recorded with `pubrun`, including the command-line invocation, Python runtime, dependency state, operating environment, Git state, logs, exit status, and user-recorded analysis events. The analysis used a deterministic synthetic dataset generated with a fixed random seed. The run record was written to a local `pubrun` run directory, and the resulting manifest can be used to inspect the execution context, generate methods-supporting text, compare runs, and extract a rerun command.
    +```markdown
    +### Computational Methods
    +
    +Computational experiments were executed on a machine running <OS> equipped with an <CPU model> and <RAM> GB of RAM. The execution environment relied on Python <version> (Cpython).
    +
    +Standard library dependencies were utilized.
    +
    +To facilitate computational reproducibility, the exact state of the source code was archived at Git commit `<8-char-sha>` (origin: <remote-url>). Environment and execution provenance were captured with pubrun v<version> [1].
    +
    +**References:**
    +[1] Fariello, G. (2026). pubrun: Low-friction execution provenance for Python research [Computer software]. https://github.com/fariello/pubrun
    +```
    +
    +Notes on template variations:
    +
    +- `analysis.py` uses only the Python standard library, so the sample prints `Standard library dependencies were utilized.` When a tracked script imports highlighted libraries such as `numpy` or `pandas`, `pubrun methods` lists their names and versions in that paragraph instead.
    +- `(origin: <remote-url>)` appears only when a Git remote URL is available and not redacted, and `pubrun v<version>` may include `(commit <8-char-sha>)` when `pubrun` records its own library commit.

     To generate current methods text from the latest local run:
    ~~~~
    ~~~~text
    $ grep -n "fixed random seed" examples/minimal-research-workflow/expected_methods.md; echo "exit=$?"
    exit=1

    # Required tests item 2 (zero em/en dashes on added lines)
    dash_hits=0
    dash_exit=0

    # Required tests item 3 (relative and anchor Markdown link check)
    broken=0
    link_exit=0

    # Required tests item 4 (runtime zero-profile_deprecated manifest notice check)
    manifests_checked=11 notices=0
    notice_exit=0

    # Required tests item 5 (python3 examples/verify_all.py)
    Starting pubrun examples verification...
    ============================================================
    Executing 00_auto_start.py...
    Testing 00_auto_start...
    [PASS] PASS: 00_auto_start.py
    ------------------------------------------------------------
    Executing 01_minimal_start_stop.py...
    Testing 01_minimal_start_stop...
    [PASS] PASS: 01_minimal_start_stop.py
    ------------------------------------------------------------
    Executing 02_context_manager.py...
    Testing 02_context_manager...
    [PASS] PASS: 02_context_manager.py
    ------------------------------------------------------------
    Executing 03_audit_decorator.py...
    Testing 03_audit_decorator...
    [PASS] PASS: 03_audit_decorator.py
    ------------------------------------------------------------
    Executing 04_annotate_events.py...
    Testing 04_annotate_events...
    [PASS] PASS: 04_annotate_events.py
    ------------------------------------------------------------
    Executing 05_execution_phases.py...
    Testing 05_execution_phases...
    [PASS] PASS: 05_execution_phases.py
    ------------------------------------------------------------
    Executing 06_subprocess_spy.py...
    Testing 06_subprocess_spy...
    [PASS] PASS: 06_subprocess_spy.py
    ------------------------------------------------------------
    Executing 07_file_capture.py...
    Testing 07_file_capture...
    [PASS] PASS: 07_file_capture.py
    ------------------------------------------------------------
    Executing 08_diff_engine.py...
    Testing 08_diff_engine...
    [PASS] PASS: 08_diff_engine.py
    ------------------------------------------------------------
    Executing 09_cli_methods.py...
    Testing 09_cli_methods...
    [PASS] PASS: 09_cli_methods.py
    ------------------------------------------------------------
    Executing 10_hardware_probe.py...
    Testing 10_hardware_probe...
    [PASS] PASS: 10_hardware_probe.py
    ------------------------------------------------------------
    Executing 11_cli_report.py...
    Testing 11_cli_report...
    [PASS] PASS: 11_cli_report.py
    ------------------------------------------------------------
    Executing 12_external_file_provenance.py...
    Testing 12_external_file_provenance...
    [PASS] PASS: 12_external_file_provenance.py
    ------------------------------------------------------------
    Executing minimal-research-workflow/analysis.py...
    ------------------------------------------------------------
    [SUCCESS] All examples passed.
    verify_all_exit=0

    # Required tests item 6 (python3 -m pytest tests/test_examples_smoke.py tests/test_example_minimal_research_workflow.py -v --no-cov -p no:cacheprovider)
    # Note: local interpreter home path and worktree rootdir redacted to ~/... and . for path-leak hygiene.
    ============================= test session starts ==============================
    platform linux -- Python 3.14.6, pytest-8.2.2, pluggy-1.6.0 -- ~/venv/p3.14/bin/python3
    rootdir: .
    configfile: pyproject.toml
    plugins: anyio-4.14.1, cov-7.1.0, xdist-3.8.0
    collected 16 items

    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[00_auto_start.py] PASSED [  6%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[01_minimal_start_stop.py] PASSED [ 12%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[02_context_manager.py] PASSED [ 18%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[03_audit_decorator.py] PASSED [ 25%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[04_annotate_events.py] PASSED [ 31%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[05_execution_phases.py] PASSED [ 37%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[06_subprocess_spy.py] PASSED [ 43%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[07_file_capture.py] PASSED [ 50%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[08_diff_engine.py] PASSED [ 56%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[09_cli_methods.py] PASSED [ 62%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[10_hardware_probe.py] PASSED [ 68%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[11_cli_report.py] PASSED [ 75%]
    tests/test_examples_smoke.py::test_example_runs_and_creates_manifest[12_external_file_provenance.py] PASSED [ 81%]
    tests/test_example_minimal_research_workflow.py::test_minimal_research_workflow_runs PASSED [ 87%]
    tests/test_example_minimal_research_workflow.py::test_default_output_dir_is_next_to_script PASSED [ 93%]
    tests/test_example_minimal_research_workflow.py::test_output_dir_is_created_when_missing PASSED [100%]

    ============================= 16 passed in 11.04s ==============================
    pytest_exit=0

    # Required tests item 7 (python3 scripts/sanitize_paths.py --check --all)
    sanitize_exit=0
    ~~~~
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: The 10 declared files belong to one cohesive documentation-audit deliverable (aligning the example suite and its representative methods output with live non-deprecated `pubrun` APIs) grouped into 3 small E-items (under ~50 lines total diff) verified together by `examples/verify_all.py` and `tests/test_examples_smoke.py`.

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`). No blocking open questions exist.
2. Scope declaration: `- Scope-Paths:` declares the 10 paths this plan changes (`examples/01_minimal_start_stop.py`, `examples/02_context_manager.py`, `examples/03_audit_decorator.py`, `examples/04_annotate_events.py`, `examples/05_execution_phases.py`, `examples/08_diff_engine.py`, `examples/09_cli_methods.py`, `examples/10_hardware_probe.py`, `examples/11_cli_report.py`, `examples/minimal-research-workflow/expected_methods.md`). If an out-of-scope edit proves necessary, make it and justify it at finalize (`--scope-reason <path>=<why>`); acknowledge any declared path left unmodified (`--scope-ack`).
3. Validation honesty: run every required validation command and paste the actual output into each `V-*` item. Never claim a check passed without pasting its output.
4. Commit discipline: commit through `aw commit 2uwuiu -- examples/01_minimal_start_stop.py examples/02_context_manager.py examples/03_audit_decorator.py examples/04_annotate_events.py examples/05_execution_phases.py examples/08_diff_engine.py examples/09_cli_methods.py examples/10_hardware_probe.py examples/11_cli_report.py examples/minimal-research-workflow/expected_methods.md`. Never use `git add -A`, `-a`, or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: the plan must reach `executed/` through `aw ipd finalize 2uwuiu`, never a hand-run `git mv`. When a runner (`aw oc run` or `aw agy run`) drives execution, the runner finalizes; otherwise the executor runs it. Finalize only once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
