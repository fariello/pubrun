# IPD: Fix performance, benchmarks, and changelog documentation drift

- Date: 2026-11-25
- Kind: child
- Concern: `benchmarks/README.md` inverts `benchmarks/harness.py`'s redacted-only default output behavior and contains stale Slurm, scheduler, scenario, workload, `.gitignore`, and relative-path claims; `docs/performance.md` reports an already-fixed timing bug (`src/pubrun/tracker.py::Run._finalize_state`, commit `cb1b6d1`) as active, omits the redacted-only default, and embeds 6 opaque internal workflow IDs; `CHANGELOG.md` `## [Unreleased]` duplicates 18 Keep-a-Changelog subsection headings, carries superseded intermediate claims contradicting live `main` (retired `pubrun bench` flags, `patched open()`, `at close`-only hashing, `update_commit_file.py` post-commit instructions, `imported-transitive` "one level deep", `10.5281/zenodo.PENDING`, intermediate mypy ratchet, `xfail` schema note, inert-profile "separate design decision", internal IPD references, and duplicated copyright name phrasing), and omits historical `v1.0.1` through `v1.0.3` patch entries; and `CITATION.cff` has a release-date mismatch with tag `v1.3.1` plus a dangling internal IPD comment.
- Scope: `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff`.
- Scope-Paths: benchmarks/README.md, docs/performance.md, CHANGELOG.md, CITATION.cff
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Short-Description: Fix benchmarks/README.md redacted-default inversion, docs/performance.md stale bug/IDs, CHANGELOG consolidation and v1.0.1-v1.0.3 entries, and CITATION date
- Work-Kind: chore
- Priority: medium
- Set: doc-audit
- Order: 5
- Highest E allocated: 05
- Author: Antigravity
- Id: 77pdvl
- Approval: 2026-11-26, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 approved (aw set): status set to approved
- 2026-11-25 /plan-review (Gemini 4 Neon, Antigravity): APPROVE WITH REVISIONS APPLIED; PR-001..PR-007 all FIXED; review record `.aw/records/reviews/20261125-doc-audit-05-77pdvl-fix-performance-benchmarks-and-changelog-documentation-drift.review.md`.
- 2026-11-25 to-review (aw set): Authored from /assess-documentation
- 2026-11-25 /assess documentation (Antigravity): assessed; proposed 4 documentation and metadata fixes (4 grouped findings across benchmarks, performance, changelog, and citation metadata)
- 2026-11-25 draft (Antigravity): created.

## Goal

Align `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff` with the live benchmark harness (`benchmarks/harness.py`), scheduler scripts, resolved timing behavior (`src/pubrun/tracker.py::Run._finalize_state`), net `[Unreleased]` state on `main`, git tag history (`v1.0.1` through `v1.0.3` and `v1.3.1`), and citation tests (`tests/test_cli.py::TestCitationConsistency`).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix benchmark and performance documentation

- [ ] E-01 Fix all verified inaccuracies in `benchmarks/README.md` (with zero em or en dashes in added or edited lines):
  - **Default output behavior** (`benchmarks/README.md#Running` and `benchmarks/README.md#Contributing a result from a new machine`): replace the inverted default description (`results/<hostname>-<UTC-timestamp>.unredacted.json` + `--redacted-out`) with the live behavior of `benchmarks/harness.py::main`: by default, each run writes only `benchmarks/results/pubrun-bench-<hash>-<UTC-timestamp>.redacted.json` (override its path with `--redacted-out <path>`); the identifying unredacted copy (`benchmarks/results/<hostname>-<UTC-timestamp>.unredacted.json`) is written only when `--unredacted` (or `--out <path>`, which implies `--unredacted`) is explicitly passed. In the "Advanced / manual" bullet, clarify that `--redacted-out` overrides the default redacted output path rather than enabling redaction.
  - **Slurm and other schedulers** (`benchmarks/README.md#Running on an HPC cluster` and `benchmarks/README.md#Slurm details`): update the Slurm default output path to `benchmarks/results/pubrun-bench-${NODE}-${STAMP}.redacted.json` (matching `benchmarks/run_bench.sbatch`), noting that setting `PUBRUN_UNREDACTED=1` also writes `${NODE}-${STAMP}.unredacted.json` and `PUBRUN_REDACTED_OUT` overrides the redacted path; fix the `# random idle node, full 2-pass run:` comment to state the default tier (1 uncaptured baseline pass + 3 measured passes x 30 iterations, matching `benchmarks/harness.py::_TIERS`); and qualify the "Never a bare `*.json`" claim by stating that `harness.py` default output, `pubrun bench`, and `benchmarks/run_bench.sbatch` never write a bare `*.json`, whereas the template scripts `benchmarks/submit_bench_{pbs,lsf,sge}.sh` currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, which writes an unredacted bare `.json` file (gitignored, do not share) alongside the default `.redacted.json` file.
  - **Scenarios, workloads, `.gitignore`, and relative paths** (`benchmarks/README.md#Design` and `benchmarks/README.md#Interpreting the numbers`): replace `patched open() vs builtins.open` under `hotpath` with `pubrun.open()` and `pubrun.register_input()` vs `builtins.open()` (stating that `pubrun` never patches `open()`); add the `io_baseline` group to the `scenarios.py` bullet and `io_sink` to the `workloads/` bullet (matching `benchmarks/scenarios.py::all_scenarios` and `benchmarks/workloads/io_sink.py`); correct the `results/` bullet in `Design` to state that `benchmarks/results/.gitignore` tracks only `.gitignore` and `*.redacted.json` (local `aggregate.py` writes gitignored `benchmarks/results/summary.csv` and `benchmarks/results/summary.md` by default per `benchmarks/aggregate.py::main`, while committed community summaries live in `benchmarks/data/summary.csv` and `benchmarks/data/summary.md`); and normalize bare `results/...` example paths (`Running`, `Contributing a result from a new machine`, and `Advanced / manual`) to repo-root `benchmarks/results/...`.
  - Depends on: none
  - Expected outcome: Every output path, CLI flag, Slurm/scheduler note, scenario group, workload, and `.gitignore` statement in `benchmarks/README.md` matches `benchmarks/harness.py`, `benchmarks/run_bench.sbatch`, `benchmarks/submit_bench_{pbs,lsf,sge}.sh`, `benchmarks/scenarios.py`, `benchmarks/aggregate.py`, `benchmarks/results/.gitignore`, and `benchmarks/data/README.md`.
  - Execution state: pending

- [ ] E-02 Fix output-file defaults, stale timing-bug status, and leaked internal workflow IDs in `docs/performance.md` (with zero em or en dashes in added or edited lines):
  - Under `docs/performance.md#Result files (schema pubrun-benchmark/5)`, state clearly that `benchmarks/harness.py` writes only the `.redacted.json` file by default and writes the `.unredacted.json` copy only when `--unredacted` or `--out` is passed; scope the "Neither is ever a bare `*.json`" note to `harness.py` default output, `pubrun bench`, and Slurm (noting that the PBS/LSF/SGE template scripts currently pass `--out ...json`, matching `benchmarks/README.md`).
  - Under `docs/performance.md#Whole-process harness context (af36c852, Pass 1 cold / Pass 3 warm)`, rewrite the `Known exception (backlog uatvzh):` passage to state that this exception applied to measured revision `af36c852` and has since been fixed (commit `cb1b6d1`, `src/pubrun/tracker.py::Run._finalize_state` records `end_mono` and `end_utc` before acquiring `_run_lock`, so wait time for an in-flight background hardware refresh is attributed to `finalization_overhead_seconds` rather than `workload_seconds`).
  - Remove all 6 opaque internal plan/backlog IDs (`fthyv5`, `ckc3vl`, `uatvzh`, `p6pon8`, `26euz0`, `4gpguy`) across `docs/performance.md`, replacing them with plain descriptions and git commit hashes where helpful (for example replacing `uncommitted changes of plan 4gpguy` with `uncommitted workload and documentation changes`). Preserve heading `## Package capture startup and finalization overhead (single-machine local measurements)` verbatim because `benchmarks/README.md` links to its anchor.
  - Depends on: none
  - Expected outcome: `docs/performance.md` accurately describes the redacted-only default, reports the `af36c852` lock-wait timing exception as resolved, preserves inbound anchors, and contains zero opaque internal workflow IDs.
  - Execution state: pending

### Task group 2: Consolidate `CHANGELOG.md` and align `CITATION.cff`

- [ ] E-03 Consolidate `## [Unreleased]` in `CHANGELOG.md` and reconcile all superseded or contradictory intermediate entries against live `main` without dropping any user-facing change or breaking-change callout (with zero em or en dashes in added or edited lines):
  - Merge the 18 duplicated Keep-a-Changelog subsection headings inside `## [Unreleased]` (`### Added` 5x, `### Changed` 4x, `### Fixed` 5x, `### Documentation` 2x, `### Deprecated` 2x) into one single ordered set of `###` headings (`### Added`, `### Changed`, `### Deprecated`, `### Fixed`, `### Documentation`, keeping or folding the `#### Other fixes` and `#### Edge-case / failure-mode hardening` subsections cleanly under the single `### Fixed` heading).
  - Reconcile every superseded or contradictory intermediate `[Unreleased]` entry against live `main`:
    1. Fold the intermediate `pubrun bench` intake/submission bullets (`pubrun-benchmarks`, `--no-redact`, `--submit-method`, `--gh-token`, `--print-submission`, the superseded attach-only `--submit-file` "it no longer transmits" claim, the "PRIVATE (`*.unredacted.json`) vs SAFE" dual-write phrasing, and intermediate `pubrun-benchmark/3` and `pubrun-benchmark/4` schema-addition bullets) into concise entries reflecting the shipped net behavior: redacted-only default, `--unredacted`, `fariello/pubrun` target, `--contribute` / `--no-contribute` / `--prepare-submission` / `--submit-file` / `--wait-timeout` / `--no-submit` / `--gh-repo`, `pubrun-benchmark/5` compact schema (with `aggregate.py` reading older schemas), validate-only `.github/workflows/benchmark-intake.yml`, and `benchmarks/pull_submissions.py`; qualify the "never a bare `*.json`" wording so it does not contradict `benchmarks/submit_bench_{pbs,lsf,sge}.sh`.
    2. Replace the retired `scripts/update_commit_file.py` / `post-commit` hook instructions under `pubrun --version` with the shipped build-time stamping in `hatch_build.py` (stamping `_build_meta.json` and legacy `COMMIT` into wheel and sdist artifacts without mutating the working tree).
    3. Correct `imported-transitive` package mode from "one level deep" to recursive, cycle-safe transitive closure (`src/pubrun/capture/packages.py::_resolve_transitive_closure`).
    4. Correct `[capture.file_io].level = "hash"` from "reads from the on-disk bytes at close" to streamed SHA-256 hashing during sequential reads via `ProvenanceFileProxy`, falling back to re-reading at close only when streaming is not possible (matching `src/pubrun/capture/file_io.py` and the `ProvenanceFileProxy` bullet).
    5. Replace `patched open()/print() hot paths` under the benchmark suite bullet with `pubrun.open()` / `pubrun.register_input()` and `print()` console tee hot paths (`pubrun` never patches `open()`).
    6. Fold `10.5281/zenodo.PENDING`, the intermediate `[tool.mypy]` per-module `ignore_errors` ratchet entry, and the pending `xfail` manifest-schema reconciliation entry into their shipped net states: live Zenodo concept DOI `10.5281/zenodo.20801582`, full-package 3-platform `mypy` checking without `ignore_errors`, and completed `schemas/manifest.schema.json` reconciliation with `tests/test_manifest_schema.py` as a hard gate.
    7. Remove internal workflow jargon (`pending IPD`, `executed decision IPD`) and drop the superseded clause stating that `core.profile`'s relationship to capture "is tracked as a separate design decision" (since `core.profile` is now explicitly deprecated and inert).
    8. Fix the duplicated copyright-name contrast ("use the full legal name **Gabriele Fariello**; **citation** surfaces ... use the publication name **Gabriele Fariello**") into one plain statement that legal, copyright, and citation surfaces consistently use **Gabriele Fariello**.
  - Depends on: none
  - Expected outcome: `CHANGELOG.md` `## [Unreleased]` has each Keep-a-Changelog `###` heading at most once, preserves every net user-facing change and breaking-change callout since `v1.3.1`, and contains zero claims contradicted by live `main`.
  - Execution state: pending

- [ ] E-05 Add brief historical entries for tagged patch releases `v1.0.1`, `v1.0.2`, and `v1.0.3` in `CHANGELOG.md` between `## [1.1.0]` and `## [1.0.0]` (with zero em or en dashes in added lines):
  - Insert `## [1.0.3] - 2026-06-21`, `## [1.0.2] - 2026-06-20`, and `## [1.0.1] - 2026-06-20` in newest-first order matching existing headings and backed by `git log v1.0.0..v1.0.3`:
    - `1.0.3` (`2026-06-21`, commit `98058ec`): explicit telemetry and provenance API (`e301c44`), subparser usage error handling (`2c0ee37`), `--no-color` accepted in any CLI position (`fe99380`), and Windows newline test fix (`98058ec`).
    - `1.0.2` (`2026-06-20`, commit `a015c14`): improved liveness checks for remote-host runs using lock age.
    - `1.0.1` (`2026-06-20`, commit `88fe38b`): set crashed-run timing fields to `None` and implemented `HH:MM:SS` elapsed formatting.
  - Depends on: E-03
  - Expected outcome: `CHANGELOG.md` has no silent version gap between `## [1.0.0]` and `## [1.1.0]`, with `## [1.0.3]`, `## [1.0.2]`, and `## [1.0.1]` matching the git tag dates and commits.
  - Execution state: pending

- [ ] E-04 Align `CITATION.cff` release date for version `1.3.1` and clean up its trailing internal IPD comment:
  - Change `date-released: "2026-07-05"` to `date-released: "2026-06-24"` to match `git show -s --format=%cs v1.3.1` and `CHANGELOG.md` (`## [1.3.1] - 2026-06-24`).
  - Remove the dangling internal `(see the same IPD, Open Questions #1/#4)` parenthetical from the trailing comment in `CITATION.cff`, keeping the substance of the `preferred-citation` note intact.
  - Depends on: none
  - Expected outcome: `CITATION.cff` `version` (`1.3.1`) and `date-released` (`2026-06-24`) agree with tag `v1.3.1` and `CHANGELOG.md`, `tests/test_cli.py::TestCitationConsistency` passes, and no internal IPD reference remains in `CITATION.cff`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- `AGENTS.md` forbids em and en dashes (`\u2013`, `\u2014`) in added or edited lines of user-facing Markdown prose (`benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`).
- `benchmarks/harness.py::main` sets `want_unredacted = bool(args.unredacted or args.out)` and always writes `benchmarks/results/pubrun-bench-<hash>-<stamp>.redacted.json` by default (`--redacted-out` overrides that path; `--unredacted` or `--out` adds the unredacted copy).
- `benchmarks/run_bench.sbatch` writes `benchmarks/results/pubrun-bench-${NODE}-${STAMP}.redacted.json` by default (with `PUBRUN_UNREDACTED` opt-in and `PUBRUN_REDACTED_OUT` override); `benchmarks/submit_bench_{pbs,lsf,sge}.sh` pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"` (writing an unredacted bare `.json` alongside the default `.redacted.json`).
- `benchmarks/results/.gitignore` ignores `*` except `!.gitignore` and `!*.redacted.json`; `benchmarks/aggregate.py::main` defaults to local gitignored `benchmarks/results/summary.{csv,md}`, while committed community summaries live in `benchmarks/data/summary.{csv,md}`.
- `src/pubrun/tracker.py::Run._finalize_state` (fixed in commit `cb1b6d1`) reads `end_mono = time.perf_counter()` and `end_utc = time.time()` before acquiring `_run_lock`.
- `hatch_build.py::CustomBuildHook` stamps `_build_meta.json` and `COMMIT` into wheels and sdists at build time; `scripts/update_commit_file.py` is now a cleanup no-op.
- `src/pubrun/capture/packages.py::_resolve_transitive_closure` computes recursive, cycle-safe transitive dependency closures for `imported-transitive`.
- `src/pubrun/capture/file_io.py::ProvenanceFileProxy` computes streamed SHA-256 hashes during sequential reads, falling back to re-reading at close only when streaming is not possible.
- `git tag -l 'v1.0.*' 'v1.3.*'` confirms `v1.0.1` (`2026-06-20`), `v1.0.2` (`2026-06-20`), `v1.0.3` (`2026-06-21`), and `v1.3.1` (`2026-06-24`).
- `tests/test_cli.py::TestCitationConsistency` validates `CITATION.cff` against `.zenodo.json`, `README.md`, `docs/research-use.md`, `pubrun cite`, and `pubrun.__version__`.

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| P-01 | High | Low | Benchmark Contributor / Security | `benchmarks/README.md#Running` & `docs/performance.md#Result files (schema pubrun-benchmark/5)` vs `benchmarks/harness.py::main` | Inverts `harness.py`'s redacted-only default output behavior, contradicting the privacy section in the same file. |
| P-02 | Medium | Low | Benchmark Runner / HPC Operator | `benchmarks/README.md` vs `benchmarks/run_bench.sbatch`, `benchmarks/submit_bench_*.sh`, `benchmarks/scenarios.py::all_scenarios`, `benchmarks/aggregate.py::main`, `benchmarks/results/.gitignore` | Stale Slurm filename and 2-pass comment, overstated "Never a bare `*.json`" claim across PBS/LSF/SGE scripts, false `patched open()` claim, missing `io_baseline`/`io_sink`, wrong `results/` tracking note, inconsistent `results/` relative paths. |
| P-03 | Medium | Low | Performance Reader | `docs/performance.md` vs `src/pubrun/tracker.py::Run._finalize_state` (commit `cb1b6d1`) | Reports already-fixed `af36c852` lock-wait timing defect as active and leaks 6 opaque internal workflow IDs (`fthyv5`, `ckc3vl`, `uatvzh`, `p6pon8`, `26euz0`, `4gpguy`). |
| P-04 | Medium | Low | Upgrader / Release Reviewer | `CHANGELOG.md` `## [Unreleased]` & `CITATION.cff` vs `src/pubrun/`, `hatch_build.py`, `pyproject.toml`, and git tags | 18 duplicated `[Unreleased]` `###` headings, superseded/contradictory claims vs live code (bench flags/intake, `update_commit_file.py`, `imported-transitive`, `file_io` hash, `patched open()`, `zenodo.PENDING`, mypy ratchet, `xfail` schema note, inert `core.profile` note, internal IPD mentions, duplicated copyright name phrasing), missing `v1.0.1` through `v1.0.3` entries, and `CITATION.cff` `1.3.1` date mismatch (`2026-07-05` vs `2026-06-24`) plus dangling IPD comment. |

## Proposed changes (ordered, validatable)

1. Fix `benchmarks/README.md` default output, Slurm/scheduler behavior, scenarios, workloads, `.gitignore`/summary paths, and relative paths (E-01; Remediation Risk: Low).
2. Fix `docs/performance.md` output-file defaults, resolved lock-wait timing bug status, and 6 leaked internal IDs while preserving inbound anchors (E-02; Remediation Risk: Low).
3. Consolidate `CHANGELOG.md` `## [Unreleased]` subsections and reconcile all superseded or contradictory claims against live `main` (E-03; Remediation Risk: Low).
4. Add historical `v1.0.1`, `v1.0.2`, and `v1.0.3` patch entries to `CHANGELOG.md` from git tag history (E-05; Remediation Risk: Low).
5. Align `CITATION.cff` `date-released` with tag `v1.3.1` (`2026-06-24`) and remove its dangling internal IPD comment (E-04; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Updating `benchmarks/submit_bench_{pbs,lsf,sge}.sh` to drop `--out ...json` and match the redacted-only default is deferred in orchestrator `86cd17` (Medium-High Remediation Risk on Functionality for a documentation-only plan).
  - Carrier-Declined: Runtime HPC script change outside documentation-only scope; recorded in orchestrator `86cd17`.
- Repo-wide historical em/en-dash sweep across untouched paragraphs is deferred in orchestrator `86cd17` (tracked in `TODO.md` under `### Full repo-wide em/en-dash sweep`). This plan enforces zero em/en dashes in added or edited lines without churning untouched historical prose.
  - Carrier-Declined: Pre-existing repo-wide cleanup deferred separately in orchestrator `86cd17` to avoid noisy diffs across untouched sections.

## Scope check

- Over-scope: none. Only `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff` are modified.
- Under-scope: none. `- Scope-Paths:` is strictly disjoint from all five sibling plans in Set `doc-audit` (`0cjiv5`, `pqcx6o`, `dd7noz`, `wjsccu`, `2uwuiu`) and from orchestrator `86cd17`.
- Technical writing standard requirement 12 (diagrams): no diagram is needed because this plan edits four existing documentation and metadata files with no new multi-entity data model, branch, loop, or status lifecycle.

## Required tests / validation

1. **Zero em/en-dash check** on added lines of `benchmarks/README.md`, `docs/performance.md`, and `CHANGELOG.md` (must exit 0 with `dashes_in_added=0`):

   ```sh
   python3 - <<'PY'
   import subprocess, sys
   files = ["benchmarks/README.md", "docs/performance.md", "CHANGELOG.md"]
   diff = subprocess.check_output(["git", "diff", "-U0", "--"] + files, text=True)
   hits = [ln for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++") and ("\u2013" in ln or "\u2014" in ln)]
   print(f"dashes_in_added={len(hits)}")
   for h in hits:
       print(h)
   sys.exit(1 if hits else 0)
   PY
   ```

2. **Internal relative link and anchor check** across `benchmarks/README.md`, `docs/performance.md`, and `CHANGELOG.md` (must exit 0 with `broken=0`; baseline `broken=0`):

   ```sh
   python3 - <<'PY'
   import pathlib, re, sys

   def slugs_for(path: pathlib.Path) -> set[str]:
       slugs, counts = set(), {}
       for line in path.read_text(encoding="utf-8").splitlines():
           m = re.match(r"^#{1,6}\s+(.*)$", line)
           if not m:
               continue
           raw = re.sub(r"`([^`]*)`", r"\1", m.group(1).strip())
           slug = re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", raw.lower()).strip())
           n = counts.get(slug, 0)
           counts[slug] = n + 1
           slugs.add(slug if n == 0 else f"{slug}-{n}")
       return slugs

   files = [pathlib.Path("benchmarks/README.md"), pathlib.Path("docs/performance.md"), pathlib.Path("CHANGELOG.md")]
   bad = 0
   for f in files:
       text = re.sub(r"```.*?```", "", f.read_text(encoding="utf-8"), flags=re.S)
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

3. **`CHANGELOG.md` `## [Unreleased]` heading uniqueness and retired-claim check** (must exit 0 with `dups={}` and `banned_hits={}`; baseline: 18 `###` headings across 5 unique names and 12 banned strings matching):

   ```sh
   python3 - <<'PY'
   import collections, pathlib, re, sys
   cl = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
   unrel = cl.split("## [Unreleased]", 1)[1].split("## [1.3.1]", 1)[0]
   h3 = re.findall(r"^### .+$", unrel, flags=re.M)
   dups = {k: v for k, v in collections.Counter(h3).items() if v > 1}
   banned = [
       "--no-redact", "--submit-method", "--gh-token", "--print-submission",
       "zenodo.PENDING", "pubrun-benchmarks", "update_commit_file",
       "one level deep", "patched `open()`", "pending IPD",
       "executed decision IPD", "xfail",
   ]
   hits = {b: unrel.count(b) for b in banned if b in unrel}
   print(f"h3={h3}")
   print(f"dups={dups} banned_hits={hits}")
   sys.exit(1 if (dups or hits) else 0)
   PY
   ```

4. **Path leak sanitizer**: `python3 scripts/sanitize_paths.py --check --all` (must exit 0).
5. **Citation consistency test** (reads `CITATION.cff`): `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov` (must pass).

## Spec / documentation sync

- Pure documentation and citation-metadata synchronization with live code (`benchmarks/`, `src/pubrun/`, `hatch_build.py`), git tags, and `tests/test_cli.py::TestCitationConsistency`; no runtime behavior or schema contract changes.
- Cross-file alignment inside this plan: redacted-only default output and PBS/LSF/SGE `--out ...json` notes match across `benchmarks/README.md`, `docs/performance.md`, and `CHANGELOG.md`; `benchmarks/README.md`'s link to `docs/performance.md#package-capture-startup-and-finalization-overhead-single-machine-local-measurements` remains valid.
- Sibling `doc-audit` plans own the matching documentation fixes in the rest of the repository (`0cjiv5`: root docs and templates; `pqcx6o`: `docs/cli.md` and `docs/configuration.md`; `dd7noz`: `docs/api.md`, `docs/manifest.md`, `docs/architecture.md`, `docs/design/`; `wjsccu`: `docs/functional_spec.md`, `docs/hpc.md`, `docs/research-use.md`; `2uwuiu`: `examples/`).

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff -- benchmarks/README.md` confirming redacted-only default output, `--redacted-out` override clarification, accurate Slurm (`pubrun-bench-${NODE}-${STAMP}.redacted.json`, `PUBRUN_UNREDACTED`, `PUBRUN_REDACTED_OUT`, 3 measured passes + 1 baseline pass) and PBS/LSF/SGE (`--out "$RESULTS_DIR/${NODE}-${STAMP}.json"` unredacted bare `.json` alongside `.redacted.json`) notes, `pubrun.open()`/`register_input()`, `io_baseline`/`io_sink`, `results/.gitignore` vs `benchmarks/data/summary.{csv,md}`, and normalized `benchmarks/results/...` paths; pasted `grep -nE 'Each run writes `results/<hostname>|patched `open\(\)`|full 2-pass run|results/<node>-<timestamp>\.json' benchmarks/README.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); plus pasted zero-dash check (Required tests item 1) exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/performance.md` confirming redacted-only default output and scoped bare-`.json` note, resolved `af36c852` lock-wait timing exception citing `src/pubrun/tracker.py::Run._finalize_state` and commit `cb1b6d1`, removal of all 6 internal IDs, and preservation of heading `## Package capture startup and finalization overhead (single-machine local measurements)`; pasted `grep -nE 'fthyv5|ckc3vl|uatvzh|p6pon8|26euz0|4gpguy' docs/performance.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); plus pasted zero-dash check (Required tests item 1) exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: Pasted output of the `CHANGELOG.md` `## [Unreleased]` Python check (Required tests item 3) showing `dups={} banned_hits={}` and exiting 0, pasted `git diff --stat -- CHANGELOG.md` plus key reconciled hunks (`pubrun bench`, `hatch_build.py`, `imported-transitive`, `file_io` streamed hashing, `core.profile`, copyright-name phrasing, and preserved `BREAKING` entries), pasted zero-dash check (Required tests item 1) exiting 0, and pasted link/anchor check (Required tests item 2) showing `broken=0` and exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: Pasted `git diff -- CITATION.cff` showing `date-released: "2026-06-24"` matching `git show -s --format=%cs v1.3.1` and removal of the `(see the same IPD, Open Questions #1/#4)` comment, pasted `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov` passing, and pasted `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:
  - Result: pending

- [ ] V-05 validates E-05
  - Required evidence: Pasted `git diff -- CHANGELOG.md` hunk between `## [1.1.0]` and `## [1.0.0]` confirming `## [1.0.3] - 2026-06-21`, `## [1.0.2] - 2026-06-20`, and `## [1.0.1] - 2026-06-20` match `git log --format="%h %cs %d %s" v1.0.0..v1.0.3`; pasted `grep -nE '^## \[1\.0\.[123]\]' CHANGELOG.md` showing all three headings (baseline `exit=1`); plus pasted zero-dash check (Required tests item 1) exiting 0.
  - Observed evidence:
  - Result: pending


## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution begins only after a human approves this plan (`- Status: approved`). This assessment workflow does not execute the plan.

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`). No blocking open questions exist.
2. Scope declaration: `- Scope-Paths:` declares the four paths this plan changes (`benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, `CITATION.cff`). If an out-of-scope edit proves necessary, make it and justify it at finalize (`--scope-reason <path>=<why>`); acknowledge any declared path left unmodified (`--scope-ack`).
3. Validation honesty: run every required validation command and paste the actual output into each `V-*` item. Never claim a check passed without pasting its output.
4. Commit discipline: commit through `aw commit 77pdvl -- benchmarks/README.md docs/performance.md CHANGELOG.md CITATION.cff`. Never use `git add -A` or raw `git commit`, and never push without explicit human instruction.
5. Lifecycle transition: the plan must reach `executed/` through `aw ipd finalize 77pdvl`, never a hand-run `git mv`. When a runner (`aw oc run` or `aw agy run`) drives execution, the runner finalizes; otherwise the executor runs it. Finalize only once every `E-*` is `performed`, every `V-*` is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
