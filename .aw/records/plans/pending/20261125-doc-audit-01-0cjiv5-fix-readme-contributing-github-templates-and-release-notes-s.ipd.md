# IPD: Fix README, CONTRIBUTING, GitHub templates, and release notes snapshot

- Date: 2026-11-25
- Kind: child
- Concern: Root documentation (`README.md`, `CONTRIBUTING.md`, `release-notes-v1.2.0.md`) and GitHub contributor templates contain broken local links, duplicate legacy issue templates, failing contributor onboarding instructions, retired commit-stamping steps, and inaccurate CLI/HPC/Windows/example/roadmap claims.
- Scope: `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `CONTRIBUTING.md`, `README.md`, and `release-notes-v1.2.0.md`.
- Scope-Paths: .github/pull_request_template.md, .github/ISSUE_TEMPLATE/bug_report.md, .github/ISSUE_TEMPLATE/feature_request.md, CONTRIBUTING.md, README.md, release-notes-v1.2.0.md
- Item-Dependencies: none
- Status: to-review
- Short-Description: Fix broken PR template URI, duplicate issue templates, CONTRIBUTING setup/stamping, and README accuracy errors
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 1
- Highest E allocated: 04
- Author: Antigravity
- Id: 0cjiv5

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 4 documentation and template fixes (8 verified findings)
- 2026-11-25 draft (Antigravity): created.

## Goal

Fix every verified accuracy and onboarding defect in the repository's root documentation and GitHub templates so new users and contributors encounter working links, runnable setup instructions, accurate CLI/HPC/Windows behavior, and a clean GitHub issue chooser.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix GitHub templates and contributor onboarding

- [ ] E-01 Fix `.github/pull_request_template.md` and remove duplicate legacy Markdown issue templates:
  - In `.github/pull_request_template.md`, replace the broken local `file://` URI (`[CONTRIBUTING.md](CONTRIBUTING.md)`) with a valid repository link (`[CONTRIBUTING.md](CONTRIBUTING.md)` or `https://github.com/fariello/pubrun/blob/main/CONTRIBUTING.md`).
  - Delete `.github/ISSUE_TEMPLATE/bug_report.md` and `.github/ISSUE_TEMPLATE/feature_request.md` so the GitHub New Issue chooser displays only the tailored `.yml` Issue Forms (`bug.yml`, `feature.yml`, `documentation.yml`, `support.yml`, `benchmark-result.yml`).
  - Depends on: none
  - Expected outcome: `.github/pull_request_template.md` contains no `file://` URI and links cleanly to `CONTRIBUTING.md`; `.github/ISSUE_TEMPLATE/` contains no duplicate `.md` templates.
  - Execution state: pending

- [ ] E-02 Fix `CONTRIBUTING.md` development setup and commit-stamping instructions (with no em or en dashes in added or edited lines):
  - Under `## Development setup`, change `python -m pip install -e .` to `python -m pip install -e ".[dev,tui]"` (noting `.[dev]` suffices if skipping TUI tests) so `python -m pytest`, `-p randomly`, `--cov`, and `mypy` work immediately, and note that the `.github/scripts/` test command also requires `pyyaml` (matching `.github/workflows/ci.yml` `extra-suites`). Remove the redundant `pip install -e ".[dev,tui]"` block under the `mypy` snippet or note it is already covered by initial setup.
  - Under `### Local hooks and path hygiene`, remove `pre-commit install --hook-type post-commit` and replace the retired `src/pubrun/COMMIT` post-commit stamping description with accurate documentation that `hatch_build.py` stamps commit metadata into wheels and sdists at build time (`pubrun/_build_meta.json` and `pubrun/COMMIT`) without mutating the working tree, while `scripts/update_commit_file.py` is retained only as a legacy cleanup no-op.
  - Depends on: none
  - Expected outcome: A fresh contributor following `CONTRIBUTING.md` top-to-bottom installs test/typecheck dependencies before running `pytest` and sees accurate build-time commit-stamping guidance.
  - Execution state: pending

### Task group 2: Fix README accuracy errors and archive release-notes snapshot

- [ ] E-03 Fix verified accuracy defects in `README.md` (with no em or en dashes in added or edited lines):
  - **Examples (`### Examples`)**: point "A trivial script" (one-import auto-start) to `examples/00_auto_start.py` (or clarify `01_minimal_start_stop.py` demonstrates explicit `start()`/`stop()`), point "Recording inputs and outputs" to `examples/12_external_file_provenance.py` (noting `07_file_capture.py` covers CLI-argument input detection), and update `00_*` through `11_*` to `00_*` through `12_*`.
  - **Sample Output (`### Sample Output`)**: align the command above it (`pubrun methods --format markdown` or `pubrun methods --format latex`) with the sample block so the shown output actually matches `src/pubrun/report/templates.py` (`MARKDOWN_TEMPLATE` or `LATEX_TEMPLATE`).
  - **Windows support & live inspection**: qualify the Windows note to reflect actual platform differences (`uid`/`gid`, `os.system` parsing, single-process resource fallback, Linux-only `system_iowait_pct` and `io_counters`, unavailable POSIX signals, skipped directory `fsync` in `strict` durability) instead of "All other features work identically"; update Windows live inspection under `### Live Process Inspection` to `ctypes (kernel32) and wmic` (removing the inaccurate `psapi` reference, since `src/pubrun/capture/liveness.py` uses `kernel32` + `wmic`, not `psapi`, and noting RSS returns unavailable if `wmic` is absent).
  - **CLI Reference**: update `### pubrun show` to remove the false "Accepts multiple run directories" claim and invalid `pubrun show ./runs/pubrun-A ./runs/pubrun-B --deep` example; document single-run viewing with optional section (`pubrun show ./runs/pubrun-A [logs|env|packages] --deep`) and filter-based multi-run viewing (`pubrun show -n 2 --deep` or `pubrun show -f train.py`). Add `broken pipe` to the `### pubrun status` status list, and mention `--preflight` under `### pubrun inspect` and `### pubrun rerun`.
  - **HPC Global Hydration (`## Advanced HPC Ecosystems`)**: update the `PUBRUN_META_REF` example so it actually works under `src/pubrun/report/utils.py::_is_meta_ref_allowed` and `hydrate_manifest`: use an absolute shared path (for example `pubrun meta --out /shared/proj/meta.json --deep` and `export PUBRUN_META_REF=/shared/proj/meta.json`) and note that `[report].meta_ref_allowed_dirs = ["/shared/proj"]` (or `[report].allow_external_meta_ref = true`) must be configured in `.pubrun.toml` because relative paths resolve from each child's run directory and paths outside it are blocked by policy.
  - **Roadmap (`## Roadmap`)**: remove implemented `register_artifact()` (replaced by shipped `pubrun.register_output()`, `pubrun.register_file()`, and `pubrun.artifact()`) and clarify item 4 (`register_metadata()`) relative to existing `pubrun.annotate()` / `pubrun.report()` / `register_file(..., metadata=...)`.
  - **Citation & License**: fix "License, Attribution & Citation" reference to `[License & Attribution](#license--attribution)` and align the copyright holder name (`Gabriele Fariello`) with `LICENSE`, `NOTICE`, and `src/pubrun/__init__.py` (or keep `Gabriele G. R. Fariello` only if explicitly preferred; see OQ-01).
  - Depends on: none
  - Expected outcome: Every example, CLI command, HPC hydration snippet, Windows statement, roadmap item, and section link in `README.md` matches the live codebase.
  - Execution state: pending

- [ ] E-04 Add a clear top-of-file historical-archive notice to `release-notes-v1.2.0.md` stating that it is a preserved snapshot of the v1.2.0 release notes (copied into `CHANGELOG.md`) and that paths referenced in it (`expected_methods_text.md`, `generated_output_notes.md`, `tests/test_examples.py`) reflect the v1.2.0 tag rather than current `main`.
  - Depends on: none
  - Expected outcome: Readers browsing `release-notes-v1.2.0.md` are not misled by pre-rename file paths, while historical links remain intact.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`README.md`, `CONTRIBUTING.md`, `docs/*.md`, `CHANGELOG.md`).
- `scripts/sanitize_paths.py --check --all` runs in `.github/workflows/secret-scan.yml` and must exit 0.
- `src/pubrun/__main__.py::main` (`show_parser`) defines three `nargs="?"` positionals (`run_dir`, `section`, `config_extra`), not `nargs="*"`.
- `src/pubrun/report/utils.py::hydrate_manifest` resolves relative `meta_ref` against `Path(manifest_path).parent` and enforces `_is_meta_ref_allowed()`.
- `hatch_build.py` stamps `pubrun/_build_meta.json` and `pubrun/COMMIT` at wheel/sdist build time; `scripts/update_commit_file.py::main` is a retired cleanup no-op.
- `src/pubrun/capture/liveness.py::_get_rss_windows` uses `wmic`, while PID/CPU queries use `ctypes.windll.kernel32` (never `psapi`).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| D-01 | High | Low | Contributor / Maintainer | `.github/pull_request_template.md` checklist link (`CONTRIBUTING.md`) | Broken machine-local `file://` URI leaks local directory layout and fails on GitHub. |
| D-02 | High | Low | Operator / Novice | `README.md` `### pubrun show` vs `src/pubrun/__main__.py` `show_parser` | Claims `pubrun show` accepts multiple positional run directories; second directory is silently ignored as `section`. |
| D-03 | High | Low | New Contributor | `CONTRIBUTING.md` `## Development setup` vs `pyproject.toml` `[project.optional-dependencies]` and `.github/workflows/ci.yml` | `pip install -e .` omits `pytest`, `pytest-randomly`, `pytest-cov`, `mypy`, `textual`, and `pyyaml`. |
| D-04 | High | Low | Contributor / Maintainer | `CONTRIBUTING.md` `### Local hooks and path hygiene` vs `scripts/update_commit_file.py` and `hatch_build.py` | Documents retired `post-commit` `src/pubrun/COMMIT` stamping flow instead of `hatch_build.py`. |
| D-05 | High | Low | Bug Reporter / Novice | `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md` alongside `.yml` Issue Forms | Duplicate legacy Markdown templates appear in GitHub chooser and ask for Browser/Smartphone details. |
| D-06 | High | Low | HPC Operator / Novice | `README.md` `## Advanced HPC Ecosystems` vs `src/pubrun/report/utils.py::hydrate_manifest` and `_is_meta_ref_allowed` | `PUBRUN_META_REF=meta.json` fails with `missing` / `blocked_by_policy` without shared-path resolution and `[report].meta_ref_allowed_dirs`. |
| D-07 | Medium | Low | Novice / Evaluator | `README.md` `### Examples` and `## Roadmap` vs `examples/` and `src/pubrun/__init__.py::__all__` | `01_minimal_start_stop.py` misdescribed as one-import, `07_file_capture.py` misdescribed as outputs, `12_external_file_provenance.py` omitted, and shipped `register_output`/`artifact` listed as future work. |
| D-08 | Medium | Low | Windows Operator | `README.md` Windows note and `### Live Process Inspection` vs `src/pubrun/capture/liveness.py` and `src/pubrun/resources/default.toml` | Incorrectly cites `psapi` for Windows `status` and overclaims Windows feature parity. |
| D-09 | Low | Low | Academic / Reader | `README.md` `### Sample Output`, `## Citation`, `## License & Attribution`, `### pubrun status`/`inspect`/`rerun`; `release-notes-v1.2.0.md` | Markdown sample under `--format latex`, mismatched heading name, copyright name inconsistency, missing `broken pipe`/`--preflight`, and unlabelled historical v1.2.0 paths. |

## Proposed changes (ordered, validatable)

1. Fix `.github/pull_request_template.md` and remove legacy `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md` (E-01; Remediation Risk: Low).
2. Fix `CONTRIBUTING.md` onboarding install command and build-time commit-stamping documentation (E-02; Remediation Risk: Low).
3. Fix `README.md` examples, sample output, Windows details, CLI reference, HPC hydration example, roadmap, and citation/license references (E-03; Remediation Risk: Low).
4. Add an archival snapshot note to `release-notes-v1.2.0.md` (E-04; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Updating `CHANGELOG.md` for the retired `update_commit_file.py` note is owned by sibling plan `77pdvl` so file scopes stay disjoint.
  - Carrier: 77pdvl

## Scope check

- Over-scope: none. All six paths are root docs or GitHub templates.
- Under-scope: none.

## Required tests / validation

- Diff inspection of every edited and deleted path.
- `grep -n "file://" .github/pull_request_template.md` returns no match (`exit=1`).
- `ls .github/ISSUE_TEMPLATE/` confirms only `.yml` Issue Forms remain.
- Zero em/en dashes (`\u2013`, `\u2014`) in added lines of `README.md`, `CONTRIBUTING.md`, `.github/pull_request_template.md`, and `release-notes-v1.2.0.md`.
- Link and anchor verification across `README.md`, `CONTRIBUTING.md`, and `.github/pull_request_template.md`.
- `python3 scripts/sanitize_paths.py --check --all` exits 0.

## Spec / documentation sync

- This plan updates user-facing documentation and templates only; no runtime behavior changes.

## Open questions

### OQ-01: Should `README.md` copyright keep `Gabriele G. R. Fariello` or match `Gabriele Fariello` in `LICENSE` and `NOTICE`?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: Align `README.md` to `Gabriele Fariello` to match the authoritative license and attribution files (`LICENSE`, `NOTICE`, `src/pubrun/__init__.py`, and `CHANGELOG.md`). The maintainer can override during plan review if middle initials are preferred.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- .github/pull_request_template.md`, pasted `grep -n "file://" .github/pull_request_template.md; echo "exit=$?"` showing `exit=1`, and pasted `ls -la .github/ISSUE_TEMPLATE/` confirming `bug_report.md` and `feature_request.md` are removed while the `.yml` forms remain.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- CONTRIBUTING.md` showing `pip install -e ".[dev,tui]"`, the `pyyaml` note, and the `hatch_build.py` commit-stamping explanation with `post-commit` removed; plus pasted zero-dash check on added lines of `CONTRIBUTING.md` exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted `git diff -- README.md` covering all seven corrections (examples `00`-`12`, sample output aligned to template, Windows note + `kernel32`/`wmic`, `pubrun show` + `broken pipe` + `--preflight`, working `PUBRUN_META_REF` + `[report].meta_ref_allowed_dirs`, roadmap, and `[License & Attribution](#license--attribution)`), plus pasted link/anchor check output and zero-dash check on added lines exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- release-notes-v1.2.0.md` showing the archival snapshot banner, pasted zero-dash check on added lines exiting 0, and pasted output of `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`). No blocking open questions exist.
2. Scope declaration: modify only the six paths in `- Scope-Paths:`.
3. Validation honesty: run every required validation command and paste actual output into each `V-*` item.
4. Commit discipline: commit through `aw commit 0cjiv5 -- <paths>`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: finalize through `aw ipd finalize 0cjiv5` (or the runner) once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
