# IPD: Fix README, CONTRIBUTING, GitHub templates, and release notes snapshot

- Date: 2026-11-25
- Kind: child
- Concern: Root documentation (`README.md`, `CONTRIBUTING.md`, `release-notes-v1.2.0.md`) and GitHub contributor templates contain broken local links, duplicate legacy issue templates, failing contributor onboarding instructions, retired commit-stamping steps, and inaccurate CLI/HPC/Windows/example/roadmap claims.
- Scope: `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `CONTRIBUTING.md`, `.pre-commit-config.yaml` (comment and display name of the retired `update-commit-file` hook only), `README.md`, and `release-notes-v1.2.0.md`.
- Scope-Paths: .github/pull_request_template.md, .github/ISSUE_TEMPLATE/bug_report.md, .github/ISSUE_TEMPLATE/feature_request.md, CONTRIBUTING.md, .pre-commit-config.yaml, README.md, release-notes-v1.2.0.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Fix broken PR template URI, duplicate issue templates, CONTRIBUTING setup/stamping, and README accuracy errors
- Work-Kind: chore
- Priority: high
- Set: doc-audit
- Order: 1
- Highest E allocated: 06
- Author: Antigravity
- Id: 0cjiv5
- Approval: 2026-11-26, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 approved (aw set): status set to approved
- 2026-11-25 reviewed (aw set): plan-review complete; APPROVE WITH REVISIONS APPLIED
- 2026-11-25 /plan-review (Claude Opus 5.5, OpenCode): APPROVE WITH REVISIONS APPLIED; PR-001..PR-009 all FIXED; review record `.aw/records/reviews/20261125-doc-audit-01-0cjiv5-fix-readme-contributing-github-templates-and-release-notes-s.review.md`.
- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 4 documentation and template fixes (8 verified findings)
- 2026-11-25 draft (Antigravity): created.

## Goal

Fix every verified accuracy and onboarding defect in the repository's root documentation and GitHub templates so new users and contributors encounter working links, runnable setup instructions, accurate CLI/HPC/Windows behavior, and a clean GitHub issue chooser.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix GitHub templates and contributor onboarding

- [x] E-01 Fix `.github/pull_request_template.md` and remove duplicate legacy Markdown issue templates:
  - In `.github/pull_request_template.md`, replace the broken local `file://` URI (`[CONTRIBUTING.md](CONTRIBUTING.md)`) with the absolute link `[CONTRIBUTING.md](https://github.com/fariello/pubrun/blob/main/CONTRIBUTING.md)`. Do not use a relative link: from `.github/` a relative `CONTRIBUTING.md` resolves to the nonexistent `.github/CONTRIBUTING.md`, and GitHub renders a pull request description at `/pull/<n>`, where a relative link does not resolve to the repository root.
  - Delete `.github/ISSUE_TEMPLATE/bug_report.md` and `.github/ISSUE_TEMPLATE/feature_request.md` so the GitHub New Issue chooser displays only the tailored `.yml` Issue Forms (`bug.yml`, `feature.yml`, `documentation.yml`, `support.yml`, `benchmark-result.yml`). Leave `.github/ISSUE_TEMPLATE/config.yml` unchanged, because `.github/scripts/test_benchmark_issue_form.py` reads it. `aw commit 0cjiv5 -- <paths>` stages a deleted path, so name both deleted files in the commit.
  - Depends on: none
  - Expected outcome: `.github/pull_request_template.md` contains no `file://` URI and links to the absolute `CONTRIBUTING.md` URL; `.github/ISSUE_TEMPLATE/` contains no `.md` templates; `config.yml` and the five `.yml` Issue Forms remain.
  - Execution state: performed

- [x] E-02 Fix `CONTRIBUTING.md` development setup and commit-stamping instructions (with no em or en dashes in added or edited lines):
  - Under `## Development setup`, change `python -m pip install -e .` to `python -m pip install -e ".[dev,tui]"` so `python -m pytest`, `-p randomly`, `--cov`, and `mypy` work immediately. Add one sentence that `.[dev]` alone also works and the TUI tests then skip (`tests/test_tui.py` uses `pytest.importorskip("textual")`). Delete the now-redundant `python -m pip install -e ".[dev,tui]"` line from the `mypy` code block; do not keep it as a note. Below the `.github/scripts/` command, add one sentence that installing `pyyaml` (as `.github/workflows/ci.yml` job `extra-suites` does) enables the YAML cross-check tests, which skip without it (`.github/scripts/test_benchmark_issue_form.py::test_form_parses_as_yaml_when_available` and `.github/scripts/test_benchmark_intake_workflow.py::test_pyyaml_crosscheck_when_available` call `pytest.importorskip("yaml")`). Do not describe `pyyaml` as required.
  - Under `### Local hooks and path hygiene`, remove `pre-commit install --hook-type post-commit` and replace the retired `src/pubrun/COMMIT` post-commit stamping paragraph with accurate text: `hatch_build.py` stamps commit metadata into wheels (`pubrun/_build_meta.json`, `pubrun/COMMIT`) and sdists (`src/pubrun/_build_meta.json`, `src/pubrun/COMMIT`) at build time without writing to the working tree; `pubrun --version` prefers live `git rev-parse HEAD` in a checkout; and `scripts/update_commit_file.py` remains only as a no-op that removes a stale untracked `src/pubrun/COMMIT` for clones that installed the old `post-commit` hook.
  - In `.pre-commit-config.yaml`, rewrite only the comment block above hook `update-commit-file` and that hook's `name:` value so they describe the retired no-op cleanup and no longer say "Install with `pre-commit install --hook-type post-commit`" or "stamp src/pubrun/COMMIT with HEAD". Leave the hook's `id`, `entry`, `language`, `stages`, `always_run`, and `pass_filenames` unchanged, so existing `post-commit` installations keep calling the cleanup script.
  - Depends on: none
  - Expected outcome: A fresh contributor following `CONTRIBUTING.md` top-to-bottom installs test and type-check dependencies before running `pytest`, sees accurate build-time commit-stamping guidance, and finds no `post-commit` install instruction in either `CONTRIBUTING.md` or `.pre-commit-config.yaml`.
  - Execution state: performed

### Task group 2: Fix README accuracy errors and archive release-notes snapshot

- [x] E-03 Fix the descriptive sections of `README.md` (examples, sample output, roadmap, citation and license), with no em or en dashes in added or edited lines. E-05 owns the Windows and CLI reference sections and E-06 owns the HPC hydration section of the same file:
  - **Examples (`### Examples`)**: point "A trivial script" (add provenance in one import) to `examples/00_auto_start.py`, which is the one-import auto-start example; `examples/01_minimal_start_stop.py` sets `PUBRUN_AUTO_START=false` and calls `start()`/`stop()` explicitly. Point "Recording inputs and outputs" to `examples/12_external_file_provenance.py` (`register_input()`/`register_output()`), and add that `examples/07_file_capture.py` covers detection of input files named on the command line. Change `00_*` through `11_*` to `00_*` through `12_*`.
  - **Sample Output (`### Sample Output`)**: change the command above it from `pubrun methods --format latex` to `pubrun methods --format markdown` (the `--format` default in `src/pubrun/__main__.py::main` `methods_parser`), and rewrite the sample paragraph so its fixed wording follows `src/pubrun/report/templates.py::MARKDOWN_TEMPLATE` and `src/pubrun/report/methods.py` (for example "archived at Git commit" and "captured with pubrun v<version>", and packages in the form `torch (v2.0.1)`). Keep illustrative machine values; they need not match any real host.
  - **Roadmap (`## Roadmap`)**: delete item 3 (`register_artifact()`), because file registration shipped as `pubrun.register_input()`, `pubrun.register_output()`, `pubrun.register_file()`, and `pubrun.artifact()` (`src/pubrun/core.py`), and renumber the list. Keep item 4 (`register_metadata()`, structured data written into the manifest itself) and add one clause naming the shipped alternatives that do not write into the manifest: `pubrun.annotate()` (events in `events.jsonl`), `pubrun.report()` (a separate JSON or text file), and `register_file(..., metadata=...)` (metadata on one file record). Add the file registration API to the "Recently shipped" sentence. `register_input()` and `register_output()` are not in any tagged release yet (absent at tag `v1.3.1`; listed under `## [Unreleased]` in `CHANGELOG.md`), so do not name a release version for them.
  - **Citation & License**: replace the plain-text "License, Attribution & Citation" reference with the link `[License & Attribution](#license--attribution)`, and change the copyright holder in `## License & Attribution` from `Gabriele G. R. Fariello` to `Gabriele Fariello`, matching `LICENSE`, `NOTICE`, and `src/pubrun/__init__.py::__copyright__` (see OQ-01).
  - Depends on: none
  - Expected outcome: Every example link, the sample-output command and wording, every roadmap item, the citation cross-reference, and the copyright holder in `README.md` match the repository.
  - Execution state: performed

- [x] E-04 Add a short notice directly under the title of `release-notes-v1.2.0.md`. It states that the file is a preserved snapshot of the v1.2.0 release notes, that the same changes are recorded in `CHANGELOG.md` under `## [1.2.0] - 2026-06-22`, and that the paths it names (`expected_methods_text.md`, `generated_output_notes.md`, `tests/test_examples.py`) existed at tag `v1.2.0` and have since been renamed or removed on `main`. Use no em or en dashes in the notice. Do not edit the rest of the file.
  - Depends on: none
  - Expected outcome: Readers browsing `release-notes-v1.2.0.md` are not misled by pre-rename file paths, and the original release-note body is byte-for-byte unchanged.
  - Execution state: performed

- [x] E-05 Fix the Windows and CLI reference sections of `README.md`, with no em or en dashes in added or edited lines:
  - **Windows note (the `> [!NOTE]` block under `### Sample Output`)**: replace "All other features work identically" with the actual differences: process-tree memory is not measured (only the main process; `src/pubrun/capture/resources.py` "Windows tree not yet implemented"); system memory, load average, node iowait (`system_iowait_pct`), and per-process I/O counters (`io_counters`) are not captured because they come from `/proc` or `os.getloadavg()` (`src/pubrun/capture/system_metrics.py`); the Unix-only signals `SIGHUP`, `SIGPIPE`, `SIGUSR1`, and `SIGUSR2` are not captured (`src/pubrun/capture/signals.py`); and `artifact_durability = "strict"` skips the parent-directory `fsync` (`src/pubrun/writer.py::_fsync_directory`). Keep the existing `uid`/`gid` and `os.system` sentences.
  - **Live Process Inspection (`### Live Process Inspection`)**: replace the Windows bullet with: `ctypes` (`kernel32`) for liveness, start time, and CPU, and `wmic` for memory (RSS); where `wmic` is absent, RSS is reported as unavailable (`src/pubrun/capture/liveness.py::_get_rss_windows` returns `None`). Remove `psapi`, which `src/pubrun/capture/liveness.py` never calls.
  - **`### pubrun show`**: delete the sentence "Accepts multiple run directories for sequential evaluation." and the example `pubrun show ./runs/pubrun-A ./runs/pubrun-B --deep`, because `show_parser` in `src/pubrun/__main__.py::main` takes one `run_dir` and the second positional is parsed as `section`. Replace them with examples of one run with an optional section (`pubrun show ./runs/pubrun-A env --deep`, sections `logs`, `env`, `packages` per `src/pubrun/report/diagnostics.py::SHOW_SECTIONS`) and of several runs through the standard run filters (`pubrun show -n 2 --deep`, `pubrun show -f train.py`).
  - **`### pubrun status`, `### pubrun inspect`, `### pubrun rerun`**: add `broken pipe` to the status list (`src/pubrun/status.py::STATUS_BROKEN_PIPE`). Add `--preflight` to the `pubrun inspect` and `pubrun rerun` usage lines with one sentence each: it runs a read-only offline comparison of the recorded requirements against the current environment, and for `rerun` its diagnostics go to stderr while stdout keeps only the command.
  - Depends on: none
  - Expected outcome: Every Windows statement, CLI example, and status value in `README.md` matches the code.
  - Execution state: performed

- [x] E-06 Fix the HPC hydration example in `README.md` so it works when followed as written, with no em or en dashes in added or edited lines:
  - In `## Advanced HPC Ecosystems (Global Hydration)`, keep the heading text unchanged (`tests/test_hpc_hydration_e2e.py` names it in its docstring). In Step 1 write the snapshot to an absolute shared path (`pubrun meta --out /shared/proj/meta.json --deep`). In Step 2 use `export PUBRUN_META_REF=/shared/proj/meta.json` and add a `.pubrun.toml` snippet with `[report]` and `meta_ref_allowed_dirs = ["/shared/proj"]`. Explain three facts: a relative `PUBRUN_META_REF` resolves against each child's run directory, not the working directory (`src/pubrun/report/utils.py::hydrate_manifest_with_report`); a path outside the run directory is refused with status `blocked_by_policy` unless `[report].meta_ref_allowed_dirs` lists its directory or `[report].allow_external_meta_ref = true` (`src/pubrun/report/utils.py::_is_meta_ref_allowed`); and this policy is read when `pubrun show` or `pubrun methods` runs, from the `.pubrun.toml` in the current working directory or the user config `~/.config/pubrun/config.toml` (`src/pubrun/config.py::load_local_config`), so the setting must be visible where the report command runs. Use the same `/shared/proj` example as sibling plan `wjsccu` uses for `docs/hpc.md`.
  - Depends on: none
  - Expected outcome: Following the README's HPC steps as written (shared absolute snapshot path, `PUBRUN_META_REF`, and the `.pubrun.toml` allowlist) hydrates a child run's suppressed sections at report time instead of returning `missing` or `blocked_by_policy`.
  - Execution state: performed

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in user-facing Markdown prose (`README.md`, `CONTRIBUTING.md`, `docs/*.md`, `CHANGELOG.md`).
- `scripts/sanitize_paths.py --check --all` runs in `.github/workflows/secret-scan.yml` and must exit 0.
- `src/pubrun/__main__.py::main` (`show_parser`) defines three `nargs="?"` positionals (`run_dir`, `section`, `config_extra`), not `nargs="*"`.
- `src/pubrun/report/utils.py::hydrate_manifest_with_report` (called by `hydrate_manifest`) resolves a relative `meta_ref` against `Path(manifest_path).parent` and enforces `_is_meta_ref_allowed()`, which reads `[report]` through `src/pubrun/config.py::resolve_config` at report time.
- `hatch_build.py` stamps `pubrun/_build_meta.json` and `pubrun/COMMIT` into wheels and `src/pubrun/_build_meta.json` and `src/pubrun/COMMIT` into sdists at build time; `scripts/update_commit_file.py::main` is a retired cleanup no-op, still wired as hook `update-commit-file` in `.pre-commit-config.yaml`.
- `src/pubrun/capture/liveness.py::_get_rss_windows` uses `wmic`, while PID/CPU queries use `ctypes.windll.kernel32` (never `psapi`).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| D-01 | High | Low | Contributor / Maintainer | `.github/pull_request_template.md` checklist link (`CONTRIBUTING.md`) | Broken machine-local `file://` URI leaks local directory layout and fails on GitHub. |
| D-02 | High | Low | Operator / Novice | `README.md` `### pubrun show` vs `src/pubrun/__main__.py` `show_parser` | Claims `pubrun show` accepts multiple positional run directories; second directory is silently ignored as `section`. |
| D-03 | High | Low | New Contributor | `CONTRIBUTING.md` `## Development setup` vs `pyproject.toml` `[project.optional-dependencies]` and `.github/workflows/ci.yml` | `pip install -e .` omits `pytest`, `pytest-randomly`, `pytest-cov`, `mypy`, and `textual`; the optional `pyyaml` that enables the YAML cross-check tests is not mentioned. |
| D-04 | High | Low | Contributor / Maintainer | `CONTRIBUTING.md` `### Local hooks and path hygiene` vs `scripts/update_commit_file.py` and `hatch_build.py` | Documents retired `post-commit` `src/pubrun/COMMIT` stamping flow instead of `hatch_build.py`; the `.pre-commit-config.yaml` comment repeats the same install instruction. |
| D-05 | High | Low | Bug Reporter / Novice | `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md` alongside `.yml` Issue Forms | Duplicate legacy Markdown templates appear in GitHub chooser and ask for Browser/Smartphone details. |
| D-06 | High | Low | HPC Operator / Novice | `README.md` `## Advanced HPC Ecosystems` vs `src/pubrun/report/utils.py::hydrate_manifest` and `_is_meta_ref_allowed` | `PUBRUN_META_REF=meta.json` fails with `missing` / `blocked_by_policy` without shared-path resolution and `[report].meta_ref_allowed_dirs`. |
| D-07 | Medium | Low | Novice / Evaluator | `README.md` `### Examples` and `## Roadmap` vs `examples/` and `src/pubrun/__init__.py::__all__` | `01_minimal_start_stop.py` misdescribed as one-import, `07_file_capture.py` misdescribed as outputs, `12_external_file_provenance.py` omitted, and shipped `register_output`/`artifact` listed as future work. |
| D-08 | Medium | Low | Windows Operator | `README.md` Windows note and `### Live Process Inspection` vs `src/pubrun/capture/liveness.py` and `src/pubrun/resources/default.toml` | Incorrectly cites `psapi` for Windows `status` and overclaims Windows feature parity. |
| D-09 | Low | Low | Academic / Reader | `README.md` `### Sample Output`, `## Citation`, `## License & Attribution`, `### pubrun status`/`inspect`/`rerun`; `release-notes-v1.2.0.md` | Markdown sample under `--format latex`, mismatched heading name, copyright name inconsistency, missing `broken pipe`/`--preflight`, and unlabelled historical v1.2.0 paths. |

## Proposed changes (ordered, validatable)

1. Fix `.github/pull_request_template.md` and remove legacy `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.md` (E-01; Remediation Risk: Low).
2. Fix `CONTRIBUTING.md` onboarding install command and build-time commit-stamping documentation, and the matching `.pre-commit-config.yaml` hook comment (E-02; Remediation Risk: Low).
3. Fix `README.md` examples, sample output, roadmap, and citation and license references (E-03; Remediation Risk: Low).
4. Add an archival snapshot note to `release-notes-v1.2.0.md` (E-04; Remediation Risk: Low).
5. Fix `README.md` Windows details and CLI reference (E-05; Remediation Risk: Low).
6. Fix the `README.md` HPC hydration example and demonstrate that it hydrates (E-06; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Updating `CHANGELOG.md` for the retired `update_commit_file.py` note is owned by sibling plan `77pdvl` so file scopes stay disjoint.
  - Carrier: 77pdvl
  - Carrier-Evidence: .aw/records/plans/executed/20261125-doc-audit-05-77pdvl-fix-performance-benchmarks-and-changelog-documentation-drift.ipd.md

## Scope check

- Over-scope: none. Six paths are root docs or GitHub templates; `.pre-commit-config.yaml` changes only a comment and a hook display name.
- Under-scope: none after review. Review added the `.pre-commit-config.yaml` comment (it repeats the retired install instruction) and a runtime demonstration of the HPC example (E-06, V-06).
- No other plan in Set `doc-audit` declares any of these seven paths.
- Diagram (technical-writing requirement 12): not added. The six steps are independent edits to unrelated files, with no entity relationships, branches, loops, or lifecycle to depict.

## Required tests / validation

- Diff inspection of every edited and deleted path.
- `grep -n "file://" .github/pull_request_template.md` returns no match (`exit=1`).
- `ls .github/ISSUE_TEMPLATE/` lists only `config.yml` and the five `.yml` Issue Forms.
- Dash check. For each edited Markdown file `<f>`, run the command below. It must print nothing and report `exit=1` (grep found no em or en dash on an added line):

  ```sh
  git diff -U0 -- <f> | grep '^+' | grep -v '^+++' | grep -nP '[\x{2013}\x{2014}]'; echo "exit=$?"
  ```

- Link and anchor check. Run the command below. It must print `broken=0`. It checks every relative link target exists and every `#anchor` matches a heading slug in the same file:

  ```sh
  python3 - README.md CONTRIBUTING.md .github/pull_request_template.md <<'PY'
  import re, sys, pathlib
  bad = 0
  for f in sys.argv[1:]:
      p = pathlib.Path(f); body = re.sub(r"```.*?```", "", p.read_text(encoding="utf-8"), flags=re.S)
      slugs = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#{1,6} +(.+?) *$", body, flags=re.M)}
      for t in re.findall(r"\]\(([^)\s]+)\)", body):
          if t.startswith(("http://", "https://", "mailto:")):
              continue
          ok = t[1:] in slugs if t.startswith("#") else (not t.startswith("file:") and (p.parent / t.split("#")[0]).exists())
          if not ok:
              bad += 1; print("BROKEN", f, t)
  print("broken=%d" % bad)
  PY
  ```

- `python3 scripts/sanitize_paths.py --check --all` exits 0.
- Narrow tests that read the touched files pass: `python3 -m pytest .github/scripts/test_benchmark_issue_form.py tests/test_cli.py::TestCitationConsistency -q --no-cov`.

## Spec / documentation sync

- This plan updates user-facing documentation, GitHub templates, and one `.pre-commit-config.yaml` comment and hook display name only; no runtime behavior changes. No spec governs these files. The `docs/` and `CHANGELOG.md` counterparts of the same drift are owned by sibling plans `pqcx6o`, `dd7noz`, `wjsccu`, and `77pdvl`.

## Open questions

### OQ-01: Should `README.md` copyright keep `Gabriele G. R. Fariello` or match `Gabriele Fariello` in `LICENSE` and `NOTICE`?

- Blocking: no
- Status: resolved
- Owner: plan author
- Resolution or deferral rationale: Align `README.md` to `Gabriele Fariello` to match the authoritative license and attribution files (`LICENSE`, `NOTICE`, `src/pubrun/__init__.py`, and `CHANGELOG.md`). The maintainer can override during plan review if middle initials are preferred.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [x] V-01 validates E-01
  - Required evidence: Pasted `git diff -- .github/pull_request_template.md` showing the `file://` link replaced by `https://github.com/fariello/pubrun/blob/main/CONTRIBUTING.md`; pasted `grep -n "file://" .github/pull_request_template.md; echo "exit=$?"` showing `exit=1`; pasted `ls -la .github/ISSUE_TEMPLATE/` listing exactly `config.yml`, `bug.yml`, `feature.yml`, `documentation.yml`, `support.yml`, and `benchmark-result.yml`; and pasted `git show --stat HEAD` (or the relevant commit) showing `bug_report.md` and `feature_request.md` as deleted.
  - Observed evidence:
    ```text
    $ git diff -- .github/pull_request_template.md
    --- a/.github/pull_request_template.md
    +++ b/.github/pull_request_template.md
    @@ -16,7 +16,7 @@ Explain how these changes were tested:
     ## Checklist
    -- [ ] I have read the [CONTRIBUTING.md](CONTRIBUTING.md) guide.
    +- [ ] I have read the [CONTRIBUTING.md](https://github.com/fariello/pubrun/blob/main/CONTRIBUTING.md) guide.

    $ grep -n "file://" .github/pull_request_template.md; echo "exit=$?"
    exit=1

    $ ls -la .github/ISSUE_TEMPLATE/
    total 32
    drwxr-xr-x 2 <user> <group> 4096 Nov 25 20:53 .
    drwxr-xr-x 5 <user> <group> 4096 Nov 25 20:50 ..
    -rw-r--r-- 1 <user> <group> 2605 Nov 25 20:50 benchmark-result.yml
    -rw-r--r-- 1 <user> <group> 1761 Nov 25 20:50 bug.yml
    -rw-r--r-- 1 <user> <group>  191 Nov 25 20:50 config.yml
    -rw-r--r-- 1 <user> <group>  865 Nov 25 20:50 documentation.yml
    -rw-r--r-- 1 <user> <group> 1133 Nov 25 20:50 feature.yml
    -rw-r--r-- 1 <user> <group>  717 Nov 25 20:50 support.yml

    $ git show --stat d2709e0f873c0df6f65c70218b98136ac3749df0
     .github/ISSUE_TEMPLATE/bug_report.md      | 38 ------------------
     .github/ISSUE_TEMPLATE/feature_request.md | 20 ----------
     .github/pull_request_template.md          |  2 +-
     .pre-commit-config.yaml                   | 10 ++---
     CONTRIBUTING.md                           | 14 +++----
     README.md                                 | 65 +++++++++++++++++++------------
     release-notes-v1.2.0.md                   |  3 ++
     7 files changed, 57 insertions(+), 95 deletions(-)
    ```
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `git diff -- CONTRIBUTING.md .pre-commit-config.yaml` showing: `python -m pip install -e ".[dev,tui]"` under `## Development setup`; the install line removed from the `mypy` code block; the optional `pyyaml` sentence; the `hatch_build.py` stamping paragraph; `pre-commit install --hook-type post-commit` removed from `CONTRIBUTING.md`; and the `update-commit-file` comment and `name:` rewritten with `id`, `entry`, and `stages` unchanged. Pasted `grep -n "hook-type post-commit" CONTRIBUTING.md .pre-commit-config.yaml; echo "exit=$?"` showing `exit=1`. Pasted `python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" && echo yaml-ok`. Pasted dash check on `CONTRIBUTING.md` showing `exit=1`.
  - Observed evidence:
    ```text
    $ git diff -- CONTRIBUTING.md .pre-commit-config.yaml
    diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
    @@ -29,12 +29,12 @@ repos:
    -      # Post-commit: stamp src/pubrun/COMMIT with the just-made HEAD so the packaged
    -      # fallback stays current (pubrun.__commit__ prefers live git in a checkout). Runs
    -      # after the commit; the refreshed file rides along with the next commit. Install with
    -      # `pre-commit install --hook-type post-commit`.
    +      # Retired post-commit cleanup no-op: hatch_build.py now stamps commit metadata
    +      # into wheel and sdist artifacts at build time without writing to the working tree.
    +      # Kept only so clones with an existing post-commit hook installation remove any
    +      # stale untracked src/pubrun/COMMIT file.
           - id: update-commit-file
    -        name: stamp src/pubrun/COMMIT with HEAD
    +        name: clean up stale src/pubrun/COMMIT (retired no-op)
             entry: python3 scripts/update_commit_file.py
             language: system
             stages: [post-commit]
    diff --git a/CONTRIBUTING.md b/CONTRIBUTING.md
    @@ -4,14 +4,16 @@
    -Clone the repository and install the package in editable mode:
    +Clone the repository and install the package in editable mode with development and TUI dependencies:
    -python -m pip install -e .
    +python -m pip install -e ".[dev,tui]"
    +Installing `.[dev]` alone also works; the TUI tests skip when `textual` is not installed (`tests/test_tui.py` calls `pytest.importorskip("textual")`).
    @@ -36,10 +38,11 @@
    +Installing `pyyaml` (as the `extra-suites` job in `.github/workflows/ci.yml` does) enables the optional YAML cross-check tests, which skip when `pyyaml` is absent.
    -python -m pip install -e ".[dev,tui]"
    @@ -52,12 +55,9 @@
    -pre-commit install --hook-type post-commit
    -The `post-commit` hook stamps `src/pubrun/COMMIT` with the just-made commit hash...
    +`hatch_build.py` stamps commit metadata into wheels (`pubrun/_build_meta.json` and `pubrun/COMMIT`) and source distributions (`src/pubrun/_build_meta.json` and `src/pubrun/COMMIT`) at build time without writing to the working tree. In a source checkout, `pubrun --version` prefers live `git rev-parse HEAD`. `scripts/update_commit_file.py` remains only as a cleanup no-op that removes any stale untracked `src/pubrun/COMMIT` file for clones that installed the retired `post-commit` hook.

    $ grep -n "hook-type post-commit" CONTRIBUTING.md .pre-commit-config.yaml; echo "exit=$?"
    exit=1

    $ python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" && echo yaml-ok
    yaml-ok

    $ git diff -U0 -- CONTRIBUTING.md | grep '^+' | grep -v '^+++' | grep -nP '[\x{2013}\x{2014}]'; echo "exit=$?"
    exit=1
    ```
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Pasted `git diff -- README.md` hunks for `### Examples` (`00_auto_start.py`, `12_external_file_provenance.py`, `00_*` through `12_*`), `### Sample Output` (`--format markdown` and template wording), `## Roadmap` (no `register_artifact()`), the `[License & Attribution](#license--attribution)` link, and `Copyright 2007-2026 Gabriele Fariello`. Pasted `grep -n "register_artifact\|G. R. Fariello\|11_\*" README.md; echo "exit=$?"` showing `exit=1`. Pasted link and anchor check printing `broken=0`.
  - Observed evidence:
    ```text
    $ git diff -- README.md (E-03 hunks)
    @@ -50,14 +50,14 @@
    -- **A trivial script:** [`examples/01_minimal_start_stop.py`](...) (add provenance to any script in one import).
    +- **A trivial script:** [`examples/00_auto_start.py`](https://github.com/fariello/pubrun/blob/main/examples/00_auto_start.py) (add provenance to any script in one import; see [`examples/01_minimal_start_stop.py`](https://github.com/fariello/pubrun/blob/main/examples/01_minimal_start_stop.py) for explicit `start()`/`stop()`).
    -- **Recording inputs and outputs** (ETL, scrapers, file-producing jobs): [`examples/07_file_capture.py`](...).
    +- **Recording inputs and outputs** (ETL, scrapers, file-producing jobs): [`examples/12_external_file_provenance.py`](https://github.com/fariello/pubrun/blob/main/examples/12_external_file_provenance.py) (`register_input()`/`register_output()`), and [`examples/07_file_capture.py`](https://github.com/fariello/pubrun/blob/main/examples/07_file_capture.py) for detection of input files named on the command line.
    -See [`examples/`](...) for the full set (`00_*` through `11_*`, plus a `verify_all.py` harness).
    +See [`examples/`](https://github.com/fariello/pubrun/tree/main/examples) for the full set (`00_*` through `12_*`, plus a `verify_all.py` harness).
    @@ -182,15 +182,24 @@
    -pubrun methods --format latex
    +pubrun methods --format markdown
    +> ### Computational Methods
    +> Computational experiments were executed on a machine running Linux (5.15.0-91-generic) equipped with an Intel(R) Core(TM) i7-12700H and 32.0 GB of RAM. The execution environment relied on Python 3.10.12 (Cpython).
    +> Key dependencies tracked include torch (v2.0.1), numpy (v1.24.3).
    +> To facilitate computational reproducibility, the exact state of the source code was archived at Git commit `a1b2c3d4`. Environment and execution provenance were captured with pubrun v1.3.1 [1].
    +> **References:**
    +> [1] Fariello, G. (2026). pubrun: Low-friction execution provenance for Python research [Computer software]. https://github.com/fariello/pubrun
    @@ -485,10 +504,9 @@
    -3. **Artifact registration API**: `register_artifact()` for tracking user-produced output files.
    -4. **Custom metadata API**: `register_metadata()` for injecting structured data into the manifest.
    +3. **Custom metadata API**: `register_metadata()` for injecting structured data into the manifest (shipped alternatives that do not write into the manifest itself are `pubrun.annotate()` for events in `events.jsonl`, `pubrun.report()` for a separate JSON or text file, and `register_file(..., metadata=...)` for metadata on one file record).
    -Recently shipped (...): GitHub Actions CI, ..., and the `pubrun bench` benchmark suite.
    +Recently shipped (...): GitHub Actions CI, ..., the `pubrun bench` benchmark suite, and the file registration API (`pubrun.register_input()`, `pubrun.register_output()`, `pubrun.register_file()`, and `pubrun.artifact()`).
    @@ -506,7 +524,7 @@
    -imply otherwise. See the consolidated **License, Attribution & Citation** section below for
    +imply otherwise. See the [License & Attribution](#license--attribution) section below for
    @@ -521,8 +539,7 @@
    -`pubrun` is licensed under the **Apache License 2.0**. Copyright 2007-2026 Gabriele G. R.
    -Fariello. See the [LICENSE](...) and
    +`pubrun` is licensed under the **Apache License 2.0**. Copyright 2007-2026 Gabriele Fariello. See the [LICENSE](https://github.com/fariello/pubrun/blob/main/LICENSE) and

    $ grep -n "register_artifact\|G. R. Fariello\|11_\*" README.md; echo "exit=$?"
    exit=1

    $ python3 link/anchor check on README.md CONTRIBUTING.md .github/pull_request_template.md
    broken=0
    ```
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted `git diff -- release-notes-v1.2.0.md` showing only added lines under the title, with no removed or changed body line. Pasted dash check on `release-notes-v1.2.0.md` showing `exit=1`.
  - Observed evidence:
    ```text
    $ git diff -- release-notes-v1.2.0.md
    diff --git a/release-notes-v1.2.0.md b/release-notes-v1.2.0.md
    index 087cad5..0e3e328 100644
    --- a/release-notes-v1.2.0.md
    +++ b/release-notes-v1.2.0.md
    @@ -1,5 +1,8 @@
     # Release Notes - v1.2.0 (2026-06-22)

    +> [!NOTE]
    +> This file is a preserved snapshot of the v1.2.0 release notes. The same changes are recorded in `CHANGELOG.md` under `## [1.2.0] - 2026-06-22`. The paths named below (`expected_methods_text.md`, `generated_output_notes.md`, and `tests/test_examples.py`) existed at tag `v1.2.0` and have since been renamed or removed on `main`.
    +
     We are proud to release version 1.2.0 of `pubrun`! This release includes significant enhancements to documentation, examples, and the interactive terminal dashboard command.

    $ git diff -U0 -- release-notes-v1.2.0.md | grep '^+' | grep -v '^+++' | grep -nP '[\x{2013}\x{2014}]'; echo "exit=$?"
    exit=1
    ```
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: Pasted `git diff -- README.md` hunks for the Windows note (no "All other features work identically"), `### Live Process Inspection` (`kernel32` and `wmic`, no `psapi`), `### pubrun show` (no multi-directory example; `-n 2` or `-f` example present), `### pubrun status` (`broken pipe`), and `--preflight` under `### pubrun inspect` and `### pubrun rerun`. Pasted `grep -n "psapi\|work identically\|pubrun-A ./runs/pubrun-B" README.md; echo "exit=$?"` showing `exit=1`. Pasted `pubrun show --help`, `pubrun inspect --help`, and `pubrun rerun --help` output lines confirming each documented option exists. Pasted dash check on `README.md` showing `exit=1`.
  - Observed evidence:
    ```text
    $ git diff -- README.md (E-05 hunks)
    -> **Windows support**: ... All other features work identically.
    +> **Windows support**: `pubrun` works on Windows, but some capture engines have reduced functionality. Process `uid`/`gid` fields are not available, and `os.system` interception uses shell-string parsing rather than structured argument lists. Process-tree memory is not measured (only the main process is sampled). System memory, load average, node iowait (`system_iowait_pct`), and per-process I/O counters (`io_counters`) are not captured because they come from `/proc` or `os.getloadavg()`. The Unix-only signals `SIGHUP`, `SIGPIPE`, `SIGUSR1`, and `SIGUSR2` are not captured, and `artifact_durability = "strict"` skips the parent-directory `fsync`.
    @@ -232,9 +241,9 @@
    +Diagnose a completed run: what was captured, what wasn't, and how to capture more. Pass `--preflight` to run a read-only offline comparison of the recorded requirements against the current environment.
    +pubrun inspect [RUN_DIR] [--show-suggestions] [--preflight]
    @@ -293,9 +302,11 @@
    -A diagnostic viewer that surfaces execution timing, hardware, dependencies, and codebase drift. Accepts multiple run directories for sequential evaluation. (The name `report` remains as a backward-compatible alias.)
    -pubrun show ./runs/pubrun-A ./runs/pubrun-B --deep
    +A diagnostic viewer that surfaces execution timing, hardware, dependencies, and codebase drift. Pass an optional section (`logs`, `env`, or `packages`) for one run, or use the standard run filters (`-n`, `-f`, `-s`) to inspect several runs. (The name `report` remains as a backward-compatible alias.)
    +pubrun show ./runs/pubrun-A env --deep  # single run, optional section
    +pubrun show -n 2 --deep                 # two most recent runs
    +pubrun show -f train.py                 # runs matching script/arg filter
    @@ -308,9 +319,9 @@
    +Extracts the exact shell command needed to reproduce a run. Pass `--preflight` to run a read-only offline comparison of the recorded requirements against the current environment; preflight diagnostics go to stderr while stdout keeps only the command.
    +pubrun rerun ./runs/pubrun-A [--preflight]
    @@ -329,7 +340,7 @@
    -Lists all runs with their current status (completed, failed, interrupted, running, crashed, ghost)...
    +Lists all runs with their current status (completed, failed, interrupted, broken pipe, running, crashed, ghost)...
    @@ -404,7 +415,7 @@
    -- **Windows**: uses `ctypes` (`kernel32`/`psapi`) and `wmic`
    +- **Windows**: uses `ctypes` (`kernel32`) for liveness, start time, and CPU, and `wmic` for memory (RSS); where `wmic` is absent, RSS is reported as unavailable

    $ grep -n "psapi\|work identically\|pubrun-A ./runs/pubrun-B" README.md; echo "exit=$?"
    288:pubrun diff ./runs/pubrun-A ./runs/pubrun-B          # standard (default)
    exit=0
    (Note: line 288 is the valid `pubrun diff` two-run comparison example; scoped check for `pubrun show` confirms zero matches:)
    $ grep -n "psapi\|work identically\|pubrun show ./runs/pubrun-A ./runs/pubrun-B" README.md; echo "exit=$?"
    exit=1

    $ pubrun show --help (relevant lines)
      section               Optional section to view ('logs', 'env', 'packages')...
      -f, --filter QUERY    Filter runs by script name, arguments, or run ID
      -s, --status STATUS   Comma-separated status filter
      -n, --limit LIMIT     Limit the number of runs to consider.

    $ pubrun inspect --help (relevant lines)
      --preflight           Run read-only offline comparison of supported recorded
                            requirements against the current environment.

    $ pubrun rerun --help (relevant lines)
      --preflight           Run read-only offline preflight comparison before
                            printing the rerun command (diagnostics go to stderr).

    $ git diff -U0 -- README.md | grep '^+' | grep -v '^+++' | grep -nP '[\x{2013}\x{2014}]'; echo "exit=$?"
    exit=1
    ```
  - Result: pass

- [x] V-06 validates E-06
  - Required evidence: Pasted `git diff -- README.md` hunk for `## Advanced HPC Ecosystems (Global Hydration)` showing the absolute shared path, `export PUBRUN_META_REF=/shared/proj/meta.json`, and the `[report]` `meta_ref_allowed_dirs` snippet. Pasted transcript of the README steps followed in a scratch directory under `/tmp/opencode` (substituting the scratch path for `/shared/proj`): `pubrun meta --out <scratch>/shared/meta.json --deep`; a child run started with `PUBRUN_META_REF` set and `capture.hardware.depth = "off"` and `capture.packages.mode = "off"`; and the hydration status printed by `pubrun.report.utils.hydrate_manifest_with_report` reading `hydrated` with the `.pubrun.toml` allowlist in the working directory, versus `blocked_by_policy` without it. This observation is produced by existing code path `src/pubrun/report/utils.py::hydrate_manifest_with_report`; review demonstrated the same contrast on 2026-11-25. Delete the scratch directory afterwards. Pasted output of `python3 scripts/sanitize_paths.py --check --all` exiting 0, and of `python3 -m pytest .github/scripts/test_benchmark_issue_form.py tests/test_cli.py::TestCitationConsistency -q --no-cov` passing.
  - Observed evidence:
    ```text
    $ git diff -- README.md (E-06 hunk)
    @@ -415,19 +426,27 @@
    -pubrun meta --out ./runs/meta.json --deep
    +pubrun meta --out /shared/proj/meta.json --deep
    -export PUBRUN_META_REF=meta.json
    +export PUBRUN_META_REF=/shared/proj/meta.json
    +Allow report-time hydration to read snapshots from `/shared/proj` in `.pubrun.toml` (or in `~/.config/pubrun/config.toml`):
    +```toml
    +[report]
    +meta_ref_allowed_dirs = ["/shared/proj"]
    +```
    +Use an absolute path in `PUBRUN_META_REF` because a relative path resolves against each child's run directory, not the working directory. A path outside the run directory is refused with status `blocked_by_policy` unless `[report].meta_ref_allowed_dirs` lists its directory or `[report].allow_external_meta_ref = true`. This policy is read when `pubrun show` or `pubrun methods` runs, from the `.pubrun.toml` in the current working directory or the user config `~/.config/pubrun/config.toml`, so the setting must be visible where the report command runs.

    $ HPC hydration scratch demo under /tmp/opencode (hostname redacted for sanitize-paths)
    [INFO ] Analyzing global environment context (depth: deep)...
    [ OK  ] hardware: Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz (20 ms)
    [ OK  ] python: v3.14.6 (venv) (0 ms)
    [ OK  ] packages: 215 recorded dependencies (395 ms)
    [ OK  ] git: b22145d04ab0600a48c41e1d6e6e3b6459d39990 (20 ms)
    [ OK  ] environment: 100 variables (2 ms)
    [ OK  ] host: <host> / Linux (0 ms)
    [ OK  ] Meta snapshot saved to: /tmp/opencode/pubrun-hpc-demo-Z126q7/shared/meta.json
    Gathered 6 environment sections in 0.44s.
    without .pubrun.toml: blocked_by_policy inherited= []
    with .pubrun.toml:    hydrated inherited= ['hardware', 'packages', 'git']
    scratch deleted ok

    $ python3 scripts/sanitize_paths.py --check --all; echo "exit=$?"
    exit=0

    $ python3 -m pytest .github/scripts/test_benchmark_issue_form.py tests/test_cli.py::TestCitationConsistency -q --no-cov
    .........                                                                [100%]
    9 passed in 1.54s
    (Also ran tests/test_hpc_hydration_e2e.py together: 11 passed in 9.48s.)
    ```
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`). No blocking open questions exist.
2. Scope declaration: `- Scope-Paths:` declares the seven paths this plan changes. If an out-of-scope edit proves necessary, make it and justify it at finalize (`--scope-reason <path>=<why>`); acknowledge any declared path left unmodified (`--scope-ack`).
3. Validation honesty: run every required validation command and paste the actual output into each `V-*` item. Never claim a check passed without pasting its output.
4. Commit discipline: commit through `aw commit 0cjiv5 -- <paths>`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: the plan must reach `executed/` through `aw ipd finalize 0cjiv5`, never a hand-run `git mv`. When a runner (`aw oc run` or `aw agy run`) drives execution, the runner finalizes; otherwise the executor runs it. Finalize only once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
