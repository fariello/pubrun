# IPD: Fix performance, benchmarks, and changelog documentation drift

- Date: 2026-11-25
- Kind: child
- Concern: `benchmarks/README.md` inverts `benchmarks/harness.py`'s redacted-only default output behavior and contains stale Slurm, scheduler, scenario, workload, `.gitignore`, and relative-path claims; `docs/performance.md` reports an already-fixed timing bug (`src/pubrun/tracker.py::Run._finalize_state`, commit `cb1b6d1`) as active, omits the redacted-only default, and embeds 6 opaque internal workflow IDs; `CHANGELOG.md` `## [Unreleased]` duplicates 18 Keep-a-Changelog subsection headings, carries superseded intermediate claims contradicting live `main` (retired `pubrun bench` flags, `patched open()`, `at close`-only hashing, `update_commit_file.py` post-commit instructions, `imported-transitive` "one level deep", `10.5281/zenodo.PENDING`, intermediate mypy ratchet, `xfail` schema note, inert-profile "separate design decision", internal IPD references, and duplicated copyright name phrasing), and omits historical `v1.0.1` through `v1.0.3` patch entries; and `CITATION.cff` has a release-date mismatch with tag `v1.3.1` plus a dangling internal IPD comment.
- Scope: `benchmarks/README.md`, `docs/performance.md`, `CHANGELOG.md`, and `CITATION.cff`.
- Scope-Paths: benchmarks/README.md, docs/performance.md, CHANGELOG.md, CITATION.cff
- Item-Dependencies: none
- Status: executed
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

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-26 executed (aw agy run model=Gemini-4-Neon-High): aw agy run self-finalize: 77pdvl verified (set doc-audit, attempt 1).
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

- [x] E-01 Fix all verified inaccuracies in `benchmarks/README.md` (with zero em or en dashes in added or edited lines):
  - **Default output behavior** (`benchmarks/README.md#Running` and `benchmarks/README.md#Contributing a result from a new machine`): replace the inverted default description (`results/<hostname>-<UTC-timestamp>.unredacted.json` + `--redacted-out`) with the live behavior of `benchmarks/harness.py::main`: by default, each run writes only `benchmarks/results/pubrun-bench-<hash>-<UTC-timestamp>.redacted.json` (override its path with `--redacted-out <path>`); the identifying unredacted copy (`benchmarks/results/<hostname>-<UTC-timestamp>.unredacted.json`) is written only when `--unredacted` (or `--out <path>`, which implies `--unredacted`) is explicitly passed. In the "Advanced / manual" bullet, clarify that `--redacted-out` overrides the default redacted output path rather than enabling redaction.
  - **Slurm and other schedulers** (`benchmarks/README.md#Running on an HPC cluster` and `benchmarks/README.md#Slurm details`): update the Slurm default output path to `benchmarks/results/pubrun-bench-${NODE}-${STAMP}.redacted.json` (matching `benchmarks/run_bench.sbatch`), noting that setting `PUBRUN_UNREDACTED=1` also writes `${NODE}-${STAMP}.unredacted.json` and `PUBRUN_REDACTED_OUT` overrides the redacted path; fix the `# random idle node, full 2-pass run:` comment to state the default tier (1 uncaptured baseline pass + 3 measured passes x 30 iterations, matching `benchmarks/harness.py::_TIERS`); and qualify the "Never a bare `*.json`" claim by stating that `harness.py` default output, `pubrun bench`, and `benchmarks/run_bench.sbatch` never write a bare `*.json`, whereas the template scripts `benchmarks/submit_bench_{pbs,lsf,sge}.sh` currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, which writes an unredacted bare `.json` file (gitignored, do not share) alongside the default `.redacted.json` file.
  - **Scenarios, workloads, `.gitignore`, and relative paths** (`benchmarks/README.md#Design` and `benchmarks/README.md#Interpreting the numbers`): replace `patched open() vs builtins.open` under `hotpath` with `pubrun.open()` and `pubrun.register_input()` vs `builtins.open()` (stating that `pubrun` never patches `open()`); add the `io_baseline` group to the `scenarios.py` bullet and `io_sink` to the `workloads/` bullet (matching `benchmarks/scenarios.py::all_scenarios` and `benchmarks/workloads/io_sink.py`); correct the `results/` bullet in `Design` to state that `benchmarks/results/.gitignore` tracks only `.gitignore` and `*.redacted.json` (local `aggregate.py` writes gitignored `benchmarks/results/summary.csv` and `benchmarks/results/summary.md` by default per `benchmarks/aggregate.py::main`, while committed community summaries live in `benchmarks/data/summary.csv` and `benchmarks/data/summary.md`); and normalize bare `results/...` example paths (`Running`, `Contributing a result from a new machine`, and `Advanced / manual`) to repo-root `benchmarks/results/...`.
  - Depends on: none
  - Expected outcome: Every output path, CLI flag, Slurm/scheduler note, scenario group, workload, and `.gitignore` statement in `benchmarks/README.md` matches `benchmarks/harness.py`, `benchmarks/run_bench.sbatch`, `benchmarks/submit_bench_{pbs,lsf,sge}.sh`, `benchmarks/scenarios.py`, `benchmarks/aggregate.py`, `benchmarks/results/.gitignore`, and `benchmarks/data/README.md`.
  - Execution state: performed

- [x] E-02 Fix output-file defaults, stale timing-bug status, and leaked internal workflow IDs in `docs/performance.md` (with zero em or en dashes in added or edited lines):
  - Under `docs/performance.md#Result files (schema pubrun-benchmark/5)`, state clearly that `benchmarks/harness.py` writes only the `.redacted.json` file by default and writes the `.unredacted.json` copy only when `--unredacted` or `--out` is passed; scope the "Neither is ever a bare `*.json`" note to `harness.py` default output, `pubrun bench`, and Slurm (noting that the PBS/LSF/SGE template scripts currently pass `--out ...json`, matching `benchmarks/README.md`).
  - Under `docs/performance.md#Whole-process harness context (af36c852, Pass 1 cold / Pass 3 warm)`, rewrite the `Known exception (backlog uatvzh):` passage to state that this exception applied to measured revision `af36c852` and has since been fixed (commit `cb1b6d1`, `src/pubrun/tracker.py::Run._finalize_state` records `end_mono` and `end_utc` before acquiring `_run_lock`, so wait time for an in-flight background hardware refresh is attributed to `finalization_overhead_seconds` rather than `workload_seconds`).
  - Remove all 6 opaque internal plan/backlog IDs (`fthyv5`, `ckc3vl`, `uatvzh`, `p6pon8`, `26euz0`, `4gpguy`) across `docs/performance.md`, replacing them with plain descriptions and git commit hashes where helpful (for example replacing `uncommitted changes of plan 4gpguy` with `uncommitted workload and documentation changes`). Preserve heading `## Package capture startup and finalization overhead (single-machine local measurements)` verbatim because `benchmarks/README.md` links to its anchor.
  - Depends on: none
  - Expected outcome: `docs/performance.md` accurately describes the redacted-only default, reports the `af36c852` lock-wait timing exception as resolved, preserves inbound anchors, and contains zero opaque internal workflow IDs.
  - Execution state: performed

### Task group 2: Consolidate `CHANGELOG.md` and align `CITATION.cff`

- [x] E-03 Consolidate `## [Unreleased]` in `CHANGELOG.md` and reconcile all superseded or contradictory intermediate entries against live `main` without dropping any user-facing change or breaking-change callout (with zero em or en dashes in added or edited lines):
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
  - Execution state: performed

- [x] E-05 Add brief historical entries for tagged patch releases `v1.0.1`, `v1.0.2`, and `v1.0.3` in `CHANGELOG.md` between `## [1.1.0]` and `## [1.0.0]` (with zero em or en dashes in added lines):
  - Insert `## [1.0.3] - 2026-06-21`, `## [1.0.2] - 2026-06-20`, and `## [1.0.1] - 2026-06-20` in newest-first order matching existing headings and backed by `git log v1.0.0..v1.0.3`:
    - `1.0.3` (`2026-06-21`, commit `98058ec`): explicit telemetry and provenance API (`e301c44`), subparser usage error handling (`2c0ee37`), `--no-color` accepted in any CLI position (`fe99380`), and Windows newline test fix (`98058ec`).
    - `1.0.2` (`2026-06-20`, commit `a015c14`): improved liveness checks for remote-host runs using lock age.
    - `1.0.1` (`2026-06-20`, commit `88fe38b`): set crashed-run timing fields to `None` and implemented `HH:MM:SS` elapsed formatting.
  - Depends on: E-03
  - Expected outcome: `CHANGELOG.md` has no silent version gap between `## [1.0.0]` and `## [1.1.0]`, with `## [1.0.3]`, `## [1.0.2]`, and `## [1.0.1]` matching the git tag dates and commits.
  - Execution state: performed

- [x] E-04 Align `CITATION.cff` release date for version `1.3.1` and clean up its trailing internal IPD comment:
  - Change `date-released: "2026-07-05"` to `date-released: "2026-06-24"` to match `git show -s --format=%cs v1.3.1` and `CHANGELOG.md` (`## [1.3.1] - 2026-06-24`).
  - Remove the dangling internal `(see the same IPD, Open Questions #1/#4)` parenthetical from the trailing comment in `CITATION.cff`, keeping the substance of the `preferred-citation` note intact.
  - Depends on: none
  - Expected outcome: `CITATION.cff` `version` (`1.3.1`) and `date-released` (`2026-06-24`) agree with tag `v1.3.1` and `CHANGELOG.md`, `tests/test_cli.py::TestCitationConsistency` passes, and no internal IPD reference remains in `CITATION.cff`.
  - Execution state: performed

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

- [x] V-01 validates E-01
  - Required evidence: Pasted `git diff -- benchmarks/README.md` confirming redacted-only default output, `--redacted-out` override clarification, accurate Slurm (`pubrun-bench-${NODE}-${STAMP}.redacted.json`, `PUBRUN_UNREDACTED`, `PUBRUN_REDACTED_OUT`, 3 measured passes + 1 baseline pass) and PBS/LSF/SGE (`--out "$RESULTS_DIR/${NODE}-${STAMP}.json"` unredacted bare `.json` alongside `.redacted.json`) notes, `pubrun.open()`/`register_input()`, `io_baseline`/`io_sink`, `results/.gitignore` vs `benchmarks/data/summary.{csv,md}`, and normalized `benchmarks/results/...` paths; pasted `grep -nE 'Each run writes `results/<hostname>|patched `open\(\)`|full 2-pass run|results/<node>-<timestamp>\.json' benchmarks/README.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); plus pasted zero-dash check (Required tests item 1) exiting 0.
  - Observed evidence:

    `git diff -- benchmarks/README.md`:
    ```diff
    diff --git a/benchmarks/README.md b/benchmarks/README.md
    index aa01184..0e6ec85 100644
    --- a/benchmarks/README.md
    +++ b/benchmarks/README.md
    @@ -20,17 +20,20 @@ machines.
       package snapshot and the finalization refresh separately across all five
       package-capture modes, using two synthetic profiles and the ambient (real)
       interpreter profile.
    -- **`scenarios.py`** — declarative scenario list (import mode, config overrides,
    -  workload) grouped into `startup`, `feature`, and `hotpath`.
    -- **`workloads/`** — tiny scripts the scenarios execute (`noop`, `cpu_burn`,
    -  `file_read`, `print_loop`).
    -- **`aggregate.py`** — stdlib-only; merges result JSONs into a CSV + a Markdown
    +- **`scenarios.py`** - declarative scenario list (import mode, config overrides,
    +  workload) grouped into `startup`, `feature`, `hotpath`, and `io_baseline`.
    +- **`workloads/`** - tiny scripts the scenarios execute (`noop`, `cpu_burn`,
    +  `file_read`, `print_loop`, `io_sink`).
    +- **`aggregate.py`** - stdlib-only; merges result JSONs into a CSV + a Markdown
       overhead table (overhead computed vs each group's baseline).
    -- **`plot.py`** — optional matplotlib figures (requires `pip install -e .[bench]`).
    -- **`test_benchmarks.py`** — optional `pytest-benchmark` micro-suite for hot
    +- **`plot.py`** - optional matplotlib figures (requires `pip install -e .[bench]`).
    +- **`test_benchmarks.py`** - optional `pytest-benchmark` micro-suite for hot
       paths. Not collected by the default `pytest` run.
    -- **`results/`** — collected result JSONs (committed for reproducibility) plus
    -  the generated `summary.csv`/`summary.md`.
    +- **`results/`** - local result JSONs. `benchmarks/results/.gitignore` tracks only
    +  `.gitignore` and `*.redacted.json`. Running `benchmarks/aggregate.py` locally writes
    +  gitignored `benchmarks/results/summary.csv` and `benchmarks/results/summary.md` by
    +  default; committed community summaries live in `benchmarks/data/summary.csv` and
    +  `benchmarks/data/summary.md`.

     ## Running

    @@ -45,11 +48,15 @@ python benchmarks/harness.py --iterations 1 --passes 1   # tiny custom run
     python benchmarks/harness.py --no-baseline               # skip the baseline pass
     ```

    -Each run writes `results/<hostname>-<UTC-timestamp>.unredacted.json` (the full result;
    -add `--redacted-out <path>` to also write a shareable, redacted copy). Files are written
    -**compact** (no indentation): the redacted copy must fit GitHub's ~65 KB issue-body cap, and
    -the local copy uses the same form (it parses identically). The timestamp in the filename is
    -UTC; the JSON also records `generated_utc` and `generated_local` (local time with its offset).
    +By default, each run writes only the share-safe redacted result at
    +`benchmarks/results/pubrun-bench-<hash>-<UTC-timestamp>.redacted.json` (pass
    +`--redacted-out <path>` to override its output path). The identifying unredacted copy
    +(`benchmarks/results/<hostname>-<UTC-timestamp>.unredacted.json`) is written only when you
    +explicitly pass `--unredacted` (or `--out <path>`, which implies `--unredacted`). Files are
    +written **compact** (no indentation): the redacted copy must fit GitHub's ~65 KB issue-body
    +cap, and any unredacted local copy uses the same form (it parses identically). The timestamp
    +in the filename is UTC; the JSON also records `generated_utc` and `generated_local` (local
    +time with its offset).

     The result format is `pubrun-benchmark/5`, defined by a machine-readable JSON Schema at
     [`schemas/benchmark.schema.json`](../schemas/benchmark.schema.json). Both the full and the
    @@ -193,24 +200,32 @@ PBS/Torque, LSF, or SGE/Grid Engine**) and offers to submit to a compute node.

     For direct use, per-scheduler submit scripts live here:

    -- `submit_bench.sh` + `run_bench.sbatch` — **Slurm**. Picks a **random idle CPU node**
    +- `submit_bench.sh` + `run_bench.sbatch` - **Slurm**. Picks a **random idle CPU node**
       (via `sinfo`) and submits to it; falls back to an unpinned submit if none are idle.
    -  Each job writes a node-tagged result to `benchmarks/results/<node>-<timestamp>.json`.
    -- `submit_bench_pbs.sh` — **PBS/Torque/OpenPBS** (`qsub`).
    -- `submit_bench_lsf.sh` — **LSF** (`bsub`).
    -- `submit_bench_sge.sh` — **SGE / Grid Engine** (`qsub`).
    +  By default, each job writes only a redacted result to
    +  `benchmarks/results/pubrun-bench-${NODE}-${STAMP}.redacted.json` (override its path with
    +  `PUBRUN_REDACTED_OUT`; set `PUBRUN_UNREDACTED=1` to also write
    +  `benchmarks/results/${NODE}-${STAMP}.unredacted.json`).
    +- `submit_bench_pbs.sh` - **PBS/Torque/OpenPBS** (`qsub`).
    +- `submit_bench_lsf.sh` - **LSF** (`bsub`).
    +- `submit_bench_sge.sh` - **SGE / Grid Engine** (`qsub`).

     The PBS/LSF/SGE scripts submit to the default queue and let the scheduler place the job (no
    -site-specific idle-node query). They are **starting points** — real clusters usually need an
    +site-specific idle-node query). They are **starting points**: real clusters usually need an
     account/allocation and often a queue/walltime, set via env knobs (`PUBRUN_QUEUE`,
     `PUBRUN_ACCOUNT`/`PUBRUN_PROJECT`, `PUBRUN_PE`) or by editing the directives. Only the Slurm
     path is exercised in CI; the others are provided as adaptable templates. Note: PBS and SGE
    -both use `qsub` — if `pubrun bench` cannot tell them apart, pass `--scheduler pbs|sge`.
    +both use `qsub`; if `pubrun bench` cannot tell them apart, pass `--scheduler pbs|sge`.
    +While `benchmarks/harness.py` default output, `pubrun bench`, and `benchmarks/run_bench.sbatch`
    +never write a bare `*.json`, the template scripts `benchmarks/submit_bench_pbs.sh`,
    +`benchmarks/submit_bench_lsf.sh`, and `benchmarks/submit_bench_sge.sh` currently pass
    +`--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, which writes an unredacted bare `.json` file
    +(gitignored; do not share) alongside the default `.redacted.json` file.

     ### Slurm details

     ```bash
    -# random idle node, full 2-pass run:
    +# random idle node, default tier (1 uncaptured baseline pass + 3 measured passes x 30 iterations):
     benchmarks/submit_bench.sh

     # forward harness args (e.g. a quick smoke run):
    @@ -222,9 +237,12 @@ PUBRUN_PARTITION=compute PUBRUN_EXCLUDE='^gpu' \
     ```

     Environment knobs (all optional): `PUBRUN_PARTITION`, `PUBRUN_PY` (default
    -`python3`), `PUBRUN_REPO`, `PUBRUN_EXCLUDE` (regex of node names to skip). The
    -job fails fast with a clear message if `pubrun` is not importable on the node —
    -`pip install -e .` into the venv the compute nodes share, if needed. To sample
    +`python3`), `PUBRUN_REPO`, `PUBRUN_EXCLUDE` (regex of node names to skip),
    +`PUBRUN_REDACTED_OUT` (overrides the default redacted output path), and
    +`PUBRUN_UNREDACTED` (set to `1` to also write
    +`benchmarks/results/${NODE}-${STAMP}.unredacted.json`). The
    +job fails fast with a clear message if `pubrun` is not importable on the node:
    +run `pip install -e .` into the venv the compute nodes share, if needed. To sample
     several node types, submit repeatedly (each lands on a different random idle
     node) or set `PUBRUN_PARTITION` per node class, then `aggregate.py` over all the
     committed result JSONs.
    @@ -238,15 +256,18 @@ pip install -e .
     python -m pubrun bench            # runs locally; on an HPC login node, offers to submit to Slurm
     ```

    -By default `pubrun bench` writes only a redacted, share-safe file under `results/`:
    +By default `pubrun bench` writes only a redacted, share-safe file under `benchmarks/results/`:

    -- `pubrun-bench-<hash>-<UTC-timestamp>.redacted.json`: a **redacted** copy safe to share
    +- `benchmarks/results/pubrun-bench-<hash>-<UTC-timestamp>.redacted.json`: a **redacted** copy safe to share
       publicly. The filename embeds a stable, non-identifying hostname hash (never the hostname
       itself, matching the in-file hostname redaction). Inside, hostname, OS username, and every
       home-directory path are masked, while the analysis-relevant data (CPU/GPU model, core count,
       raw timings, versions, filesystem type, Slurm partition) is preserved.
    -- Pass `--unredacted` if you also want `<host>-<UTC-timestamp>.unredacted.json` (the full,
    -  identifying result for your own local analysis; do not share). Never a bare `*.json`.
    +- Pass `--unredacted` if you also want `benchmarks/results/<host>-<UTC-timestamp>.unredacted.json`
    +  (the full, identifying result for your own local analysis; do not share). `harness.py` default
    +  output, `pubrun bench`, and `benchmarks/run_bench.sbatch` never write a bare `*.json` (the
    +  PBS/LSF/SGE template scripts currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`,
    +  writing a gitignored unredacted bare `.json` alongside the default `.redacted.json`).

     After a run, `pubrun bench` runs the structural share-safety validator
     (`benchmarks/share_safety.py`) and, on an interactive terminal, **offers to contribute** the
    @@ -259,7 +280,7 @@ unavailable.
     If you decline, or if a Slurm wait is interrupted, submit later without re-running:

     ```bash
    -pubrun bench --submit-file results/pubrun-bench-<hash>-<timestamp>.redacted.json
    +pubrun bench --submit-file benchmarks/results/pubrun-bench-<hash>-<timestamp>.redacted.json
     ```

     Prefer to attach manually in a browser? Run `pubrun bench --prepare-submission` to copy only
    @@ -275,8 +296,9 @@ are comfortable making public.

     Advanced / manual:

    -- `python benchmarks/harness.py --redacted-out results/shareable.redacted.json` runs the
    -  harness directly and writes a compact redacted copy.
    +- `python benchmarks/harness.py --redacted-out benchmarks/results/shareable.redacted.json` runs
    +  the harness directly and overrides the default redacted output path (redaction is already
    +  enabled by default).
     - `python benchmarks/pull_submissions.py` (dry-run; `--apply` to store/aggregate/re-tag)
       collects validated community submissions locally into `benchmarks/data/`.
     - Re-run `aggregate.py` over results and, if helpful, `plot.py`.
    @@ -339,8 +361,8 @@ Advanced / manual:
       - `feature` scenarios compare against `feature-baseline`; note `feature-none`
         (pubrun active with everything off) captures pubrun's fixed startup cost —
         the *marginal* cost of a single feature is its delta above `feature-none`.
    -  - `hotpath` scenarios pair with their `*-baseline` (e.g. patched `open()` vs
    -    `builtins.open`).
    +  - `hotpath` scenarios pair with their `*-baseline` (for example, `pubrun.open()`
    +    and `pubrun.register_input()` vs `builtins.open()`; `pubrun` never patches `open()`).
       - `io_baseline` scenarios are **ground-truth reference floors** (not overhead pairs):
         `io-baseline-devnull` (write-only sink — isolates the open()/write path from any
         storage), `io-baseline-devshm` (RAM-backed tmpfs, Linux; skipped where `/dev/shm` is
    ```

    Stale-pattern grep:
    ```text
    exit=1
    ```

    Zero em/en-dash check:
    ```text
    dashes_in_added=0
    exit=0
    ```

  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: Pasted `git diff -- docs/performance.md` confirming redacted-only default output and scoped bare-`.json` note, resolved `af36c852` lock-wait timing exception citing `src/pubrun/tracker.py::Run._finalize_state` and commit `cb1b6d1`, removal of all 6 internal IDs, and preservation of heading `## Package capture startup and finalization overhead (single-machine local measurements)`; pasted `grep -nE 'fthyv5|ckc3vl|uatvzh|p6pon8|26euz0|4gpguy' docs/performance.md; echo "exit=$?"` showing `exit=1` (baseline `exit=0`); plus pasted zero-dash check (Required tests item 1) exiting 0.
  - Observed evidence:

    `git diff -- docs/performance.md`:
    ```diff
    diff --git a/docs/performance.md b/docs/performance.md
    index c39080f..4b6fb14 100644
    --- a/docs/performance.md
    +++ b/docs/performance.md
    @@ -34,10 +34,18 @@ python benchmarks/aggregate.py benchmarks/results/*.json

     ### Result files (schema `pubrun-benchmark/5`)

    -Each run writes a **compact** (no-indent) JSON. The full local copy is
    -`<host>-<UTC-timestamp>.unredacted.json`; a shareable, redacted copy is
    -`pubrun-bench-<hostname-hash>-<UTC-timestamp>.redacted.json` (the filename embeds a
    -non-identifying hostname hash, never the hostname). Neither is ever a bare `*.json`.
    +Each run writes a **compact** (no-indent) JSON file. By default, `benchmarks/harness.py`
    +writes only the shareable, redacted copy:
    +`benchmarks/results/pubrun-bench-<hostname-hash>-<UTC-timestamp>.redacted.json` (the filename
    +embeds a non-identifying hostname hash, never the hostname; pass `--redacted-out <path>` to
    +override its path). The identifying local copy
    +(`benchmarks/results/<host>-<UTC-timestamp>.unredacted.json`) is written only when you pass
    +`--unredacted` or `--out <path>`. Neither `benchmarks/harness.py` default output,
    +`pubrun bench`, nor Slurm (`benchmarks/run_bench.sbatch`) ever writes a bare `*.json` (the
    +PBS/LSF/SGE template scripts `benchmarks/submit_bench_{pbs,lsf,sge}.sh` currently pass
    +`--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, which writes a gitignored unredacted bare
    +`.json` file alongside the default `.redacted.json` file; see
    +[`benchmarks/README.md`](../benchmarks/README.md#running-on-an-hpc-cluster)).

     Schema `/5` is a compact, non-redundant reshape of `/4` with **zero analytical data loss**:
     static per-scenario descriptors live once in a top-level `scenario_defs` map; each pass keeps
    @@ -93,7 +101,7 @@ The measurements below come from a single local machine and are scoped strictly

     - **Machine and runtime:** `Linux 6.8.0-149-generic` (`x86_64`), Python `3.14.6`, `Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz` (12 logical cores), `pubrun 1.3.1`.
     - **Storage:** Local `ext4` (`is_network = false` for `workdir`, `tmpdir`, and `pubrun_install`).
    -- **Revisions:** Pre-change baseline `d1ba84b55997d9d6cad99830570aadd9b8c41b00` (`fthyv5`) versus post-change `e9e694ca62c67a0a49e4df8f6e14c53382f2d6ba` (`ckc3vl`).
    +- **Revisions:** Pre-change baseline `d1ba84b55997d9d6cad99830570aadd9b8c41b00` versus post-change `e9e694ca62c67a0a49e4df8f6e14c53382f2d6ba`.
     - **Method:** `python3 benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1` (with `--durability-policies fsync,finalize,atomic,strict` post-change) and local non-publishing `python3 benchmarks/harness.py --passes 3 --iterations 15`. Workloads are short (`benchmarks/workloads/noop.py`, baseline `bare-python-noop`) and long (`benchmarks/workloads/cpu_burn.py`, baseline `bare-python-cpu-burn`). Pass 1 is cold and Pass 3 is warm.

     #### Before and after comparison under default durability (`fsync`)
    @@ -196,7 +204,7 @@ Values are median / stdev / IQR in milliseconds over 30 fresh processes.
     What these measurements show on this machine:

     - **The timing instrumentation itself is negligible.** A run takes a handful of `perf_counter()` readings, each about 67 ns warm, so the clock reads add well under a microsecond per run.
    -- **pubrun's overhead stays out of `workload_seconds`.** A `time.sleep(0.020)` workload measured `20.099` ms warm median (`20.091` ms cold), about 0.1 ms above the requested sleep, while pubrun's own startup (about 21 to 22 ms in process) and finalization (about 2.8 ms) were reported separately. The three disjoint intervals add up to `session_seconds`. **Known exception (backlog `uatvzh`):** these runs wrote to a temporary directory where the background hardware refresh write took about 7 ms. With the run directory on the repository disk, that refresh write (an `fsync`ed `manifest.json` rewrite, made while holding the run lock) took a median of 180 ms, and a `stop()` issued during it waited for the lock before recording `ended_at_utc`. For a 20 ms workload this added a median of 47.3 ms (stdev 36.1, IQR 40.0, maximum 185.9, n=30) to `workload_seconds`; for a 500 ms workload, which ends after the refresh, it added 0.03 ms. Very short runs on slow-to-sync storage can therefore report an inflated `workload_seconds` until that defect is fixed.
    +- **pubrun's overhead stays out of `workload_seconds`.** A `time.sleep(0.020)` workload measured `20.099` ms warm median (`20.091` ms cold), about 0.1 ms above the requested sleep, while pubrun's own startup (about 21 to 22 ms in process) and finalization (about 2.8 ms) were reported separately. The three disjoint intervals add up to `session_seconds`. **Historical exception at `af36c852` (fixed in commit `cb1b6d1`):** these `af36c852` runs wrote to a temporary directory where the background hardware refresh write took about 7 ms. At that revision, with the run directory on the repository disk, that refresh write (an `fsync`ed `manifest.json` rewrite, made while holding the run lock) took a median of 180 ms, and a `stop()` issued during it waited for the lock before recording `ended_at_utc`. For a 20 ms workload this added a median of 47.3 ms (stdev 36.1, IQR 40.0, maximum 185.9, n=30) to `workload_seconds`; for a 500 ms workload, which ended after the refresh, it added 0.03 ms. That exception has since been fixed in commit `cb1b6d1`: `src/pubrun/tracker.py::Run._finalize_state` now records `end_mono` and `end_utc` before acquiring `_run_lock`, so wait time for an in-flight background hardware refresh is attributed to `finalization_overhead_seconds` rather than `workload_seconds`.
     - **Background hardware capture overlaps the workload.** `background_hardware_seconds` (about 21 to 22 ms) is close to the 20 ms workload because the two ran concurrently; adding it to `workload_seconds` would double-count. The finalization wait for it was about 4 us because it had already finished.
     - **The `manifest.json` write is not in any persisted duration.** `Run.writer_overhead_seconds` (about 8 ms, held in memory only) is larger than `finalization_overhead_seconds` (about 2.8 ms) because it also covers building and atomically writing `manifest.json` and `methods.md`.
     - **An active `pubrun.phase()` costs about 18 us warm** (38 us cold) per block, mostly writing the `phase_start` and `phase_end` events. A later measurement of the inactive-policy cache change (built on commit `7f8af7c`, CPython 3.14.6, Intel Core i7-6800K, same machine) put a `pubrun.phase()` with **no** active run at about 22 us per block and an active one at about 19 us per block, down from about 114 us inactive on the unchanged tree in the same session. The inactive path caches `[events].on_inactive_annotate` and resolves the configuration again only when the user or local configuration file, the working directory, or the user configuration directory changes.
    @@ -210,14 +218,14 @@ The measurements below come from one local machine and are scoped strictly to th

     - **Machine and runtime:** Operating System (OS) `Linux 6.8.0-149-generic` (`x86_64`), Central Processing Unit (CPU) `Intel(R) Core(TM) i7-6800K CPU @ 3.40GHz` (12 logical cores), Python `3.14.6`.
     - **Storage:** Local `ext4` detected via `pubrun.capture.filesystem.get_filesystem()` (`is_network = false` for both `workdir` and `tmpdir`).
    -- **Git revisions:** Pre-`p6pon8` baseline `9703da77e41fb27fd19e8f0b081ac0fccdc0547f` versus post-`26euz0` HEAD `114d243d1e82739172d45a4d842303f7281882c5`.
    +- **Git revisions:** Pre-isolation baseline `9703da77e41fb27fd19e8f0b081ac0fccdc0547f` versus post-isolation HEAD `114d243d1e82739172d45a4d842303f7281882c5`.
     - **Workloads and repetitions:**
    -  1. Ephemeral Python micro-benchmark run against both revisions (baseline checked out in a temporary detached Git worktree that was removed after measurement), with 1 explicit cold pass plus 25 warm iterations per workload. `SubprocessSpy` micro-benchmarks monkeypatch `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to no-op stubs before importing `pubrun.capture.subprocesses` so both import-time (pre-`p6pon8`) and install-time (post-`p6pon8`) hooks measure pure Python wrapper overhead without OS fork jitter.
    +  1. Ephemeral Python micro-benchmark run against both revisions (baseline checked out in a temporary detached Git worktree that was removed after measurement), with 1 explicit cold pass plus 25 warm iterations per workload. `SubprocessSpy` micro-benchmarks monkeypatch `subprocess.Popen.__init__`, `subprocess.Popen.wait`, and `os.system` to no-op stubs before importing `pubrun.capture.subprocesses` so both import-time (`9703da77`) and install-time (`114d243d`) hooks measure pure Python wrapper overhead without OS fork jitter.
       2. Local non-publishing harness sweep (`python3 benchmarks/harness.py --passes 2 --iterations 20 --redacted-out <temp_path>`) on `114d243d` (1 uncaptured baseline pass, Pass 1 cold, Pass 2 warm, 20 measured iterations plus 1 discarded warmup per scenario; total wall time `303.579` s; temporary output deleted after reading).

    -### Micro-benchmark comparison (pre-`p6pon8` `9703da77` vs. post-`26euz0` `114d243d`)
    +### Micro-benchmark comparison (pre-isolation `9703da77` vs. post-isolation `114d243d`)

    -| Workload | Pre-`p6pon8` (`9703da77`) Cold / Warm Median (ms) | Pre-`p6pon8` IQR / Stdev (ms) | Post-`26euz0` (`114d243d`) Cold / Warm Median (ms) | Post-`26euz0` IQR / Stdev (ms) | Warm Median Delta |
    +| Workload | Pre-isolation (`9703da77`) Cold / Warm Median (ms) | Pre-isolation IQR / Stdev (ms) | Post-isolation (`114d243d`) Cold / Warm Median (ms) | Post-isolation IQR / Stdev (ms) | Warm Median Delta |
     |---|---:|---:|---:|---:|---:|
     | `Run` start/stop (all-off, 1 run) | 46.427 / 47.739 | 8.278 / 6.055 | 31.479 / 34.871 | 3.962 / 4.199 | -12.868 ms (-26.95%) |
     | `Run` start/stop (default, 1 run) | 200.246 / 93.500 | 16.926 / 15.714 | 427.441 / 62.941 | 10.906 / 6.390 | -30.559 ms (-32.68%) |
    @@ -335,8 +343,7 @@ uploaded or written under `benchmarks/results/`.

     Environment: Linux 6.8 (x86_64), Intel Core i7-6800K (12 logical CPUs), CPython 3.14.6,
     temporary directory on local `ext4` (file contents in the page cache), Git revision
    -`7164b15` plus the uncommitted changes of plan `4gpguy` (workload and documentation
    -only; no `src/pubrun/` changes).
    +`7164b15` plus uncommitted workload and documentation changes (no `src/pubrun/` changes).

     Columns: **Read total** is the time from the first read to the end of close (or of the
     registration call), which also includes the one-time lazy import of
    ```

    Internal-ID grep and preserved heading check:
    ```text
    exit=1
    264:## Package capture startup and finalization overhead (single-machine local measurements)
    exit=0
    ```

    Zero em/en-dash check:
    ```text
    dashes_in_added=0
    exit=0
    ```

  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: Pasted output of the `CHANGELOG.md` `## [Unreleased]` Python check (Required tests item 3) showing `dups={} banned_hits={}` and exiting 0, pasted `git diff --stat -- CHANGELOG.md` plus key reconciled hunks (`pubrun bench`, `hatch_build.py`, `imported-transitive`, `file_io` streamed hashing, `core.profile`, copyright-name phrasing, and preserved `BREAKING` entries), pasted zero-dash check (Required tests item 1) exiting 0, and pasted link/anchor check (Required tests item 2) showing `broken=0` and exiting 0.
  - Observed evidence:

    `CHANGELOG.md` `## [Unreleased]` heading & retired-claim check:
    ```text
    h3=['### Added', '### Changed', '### Deprecated', '### Fixed', '### Documentation']
    dups={} banned_hits={}
    exit=0
    ```

    `git diff --stat -- CHANGELOG.md` and key reconciled entries:
    ```text
     CHANGELOG.md | 770 +++++++++--------------------------------------------------
     1 file changed, 119 insertions(+), 651 deletions(-)

    12:- **`pubrun bench` command and one-command GitHub contribution (`fariello/pubrun`).** Friendly front-end over the benchmark harness that runs locally by default and, on an HPC login node, detects the batch scheduler (`--scheduler {auto,slurm,pbs,lsf,sge,local}`) and offers to submit the job to a compute node (never submits without confirmation; `--submit`/`--yes` govern HPC scheduler job submission only and never imply consent to publish). Writes only a share-safe redacted result by default (`benchmarks/results/pubrun-bench-<hash>-<UTC-timestamp>.redacted.json`; pass `--unredacted` to also write the identifying local copy). After a run, `pubrun bench` runs the shared structural share-safety validator (`benchmarks/share_safety.py`) and offers to contribute the redacted result to `fariello/pubrun` (`--contribute` / `--no-contribute`, `--no-submit`, `--gh-repo`): via `gh` it creates an unlisted Gist and opens a GitHub issue linking the raw `.json` URL, falling back to embedding JSON inline under GitHub's ~65 KB body cap and then to a manual browser Issue Form (`--prepare-submission` copies only the redacted file into a clean `pubrun-share/` folder). `--submit-file <file>` validates and contributes an existing redacted file without re-running. All transport uses argv lists or stdin (never a shell), re-checks share-safety immediately before sending, never prints tokens or payloads, and rolls back an orphaned Gist if issue creation fails. A validate-only GitHub Actions workflow (`.github/workflows/benchmark-intake.yml`, `contents: read` + `issues: write`) checks attachments, Gist raw URLs, and inline JSON as data only and comments an idempotent pass/fail receipt. Requires a source checkout (benchmark tooling is not shipped in the wheel).
    13:- **Slurm submit-and-wait.** On a Slurm login node, `pubrun bench` offers to submit the benchmark job (`benchmarks/submit_bench.sh` / `benchmarks/run_bench.sbatch`, emitting a parseable job ID via `sbatch --parsable`) and poll for completion (`--wait-timeout` to extend or disable), then runs the interactive share-check and contribution from the login node. Any interruption, timeout, or job failure falls back to `pubrun bench --submit-file <path>`; the result stays on the shared filesystem.
    14:- **HPC multi-scheduler benchmark submission (Slurm/PBS/LSF/SGE).** `pubrun bench` detects and offers to submit to PBS/Torque, LSF, and SGE/Grid Engine in addition to Slurm (auto-detect order Slurm > PBS > LSF > SGE) using env+PATH checks only (resolving PBS-vs-SGE `qsub` ambiguity with `--scheduler pbs|sge`). Starting-point template scripts `benchmarks/submit_bench_pbs.sh`, `benchmarks/submit_bench_lsf.sh`, and `benchmarks/submit_bench_sge.sh` submit to the default queue (not CI-validated against live clusters; they currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, writing a gitignored unredacted bare `.json` alongside the default `.redacted.json`). `pubrun self-check` emits an `INFO` nudge on HPC login nodes suggesting a compute-node `pubrun bench` run (does not trip `--strict`).
    16:- **Benchmark suite (`benchmarks/`) and `pubrun-benchmark/5` schema (`schemas/benchmark.schema.json`).** A reproducible, stdlib-only harness (`benchmarks/harness.py`) measuring startup and run-time overhead per feature (import modes, resource watcher, subprocess spy, git/hardware/packages capture, `pubrun.open()` / `pubrun.register_input()` and `print()` console tee hot paths; `pubrun` never patches `open()`). Includes `aggregate.py` (CSV + Markdown summary), optional `plot.py` and `test_benchmarks.py` under the dev-only `[bench]` extra, `docs/performance.md`, and a Draft 2020-12 JSON Schema (`schemas/benchmark.schema.json`) validated against both full and redacted `pubrun-benchmark/5` results.
    19:- **`pubrun --version` shows the commit hash.** Prints `pubrun <version> (commit <hash>)` when resolvable: live `git rev-parse HEAD` in source checkouts, falling back to build-time commit metadata stamped by `hatch_build.py` (`_build_meta.json` and legacy `COMMIT` written into wheel and sdist artifacts during build without mutating the working tree). Both paths are best-effort and stdlib-only.
    26:- **Graded file-I/O provenance for `pubrun.open()` and per-process I/O counters.** `pubrun.open()` records provenance at configurable `[capture.file_io].level` (`none | name | stat | realpath | hash`): `stat` uses `fstat` on the open fd, `realpath` adds symlink resolution, and `hash` computes a streamed SHA-256 hash during sequential reads via `ProvenanceFileProxy`, falling back to re-reading at close only when streaming is not possible (capped by `max_hash_bytes`). Still opt-in and per-file (`pubrun` never patches global `open()`). The resource watcher also records per-process Linux `/proc/self/io` byte counters (`resources.io_counters`, `system_metrics`-gated).
    29:- **Citation and Zenodo concept DOI metadata.** Added `.zenodo.json`, `NOTICE` (Apache-2.0 attribution), and updated `CITATION.cff` (author ORCID `0000-0002-0326-4752`, affiliation `University of Rhode Island`, `version`, and live Zenodo concept DOI `10.5281/zenodo.20801582`), plus matching DOI/citation metadata across `pubrun cite` (all styles), `README.md` (with a Zenodo DOI badge), `docs/research-use.md`, and `docs/cli.md`. No `preferred-citation`/paper reference is added (no peer-reviewed paper exists yet). A citation consistency test guards author, DOI, and version alignment across all citation surfaces and rejects placeholder DOIs.
    33:- **`imported-transitive` package mode**: Records imported packages plus their recursive, cycle-safe transitive dependency closure (`src/pubrun/capture/packages.py::_resolve_transitive_closure`) with `source` and `required_by` fields.
    49:- **BREAKING: `capture_mode` default is now `"off"`.** `import pubrun` no longer wraps stdout/stderr without explicit opt-in. To restore the old behavior, add `capture_mode = "standard"` to `.pubrun.toml`. Jupyter/IPython is auto-detected and capture is suppressed.
    50:- **BREAKING (command rename): `pubrun bug-report` -> `pubrun report-bug`, and `feedback` is now its own command.** The old `bug-report` command and its `issue` alias were removed (hard rename). Use `pubrun report-bug` (bug reports / feature requests) or `pubrun feedback` (general feedback); both open the GitHub issue tracker and print diagnostics.
    51:- **BREAKING (`pubrun combined`): `-f` now means `--filter`, not `--force`.** For CLI consistency, `-f`/`--filter` on `combined` now filters runs (as on every other command). The force-large-file flag is now **`--force`** (long form only). Scripts relying on `combined -f` to force must switch to `combined --force`.
    53:- **Behavior change: `pubrun bench` and `benchmarks/harness.py` write only a redacted result by default.** Only `benchmarks/results/pubrun-bench-<hostname-hash>-<UTC-timestamp>.redacted.json` is written by default; pass `--unredacted` (or `--out <path>` on `harness.py`) to also write the identifying `*.unredacted.json` copy for local debugging. `harness.py` default output, `pubrun bench`, and `benchmarks/run_bench.sbatch` never write a bare `*.json` (the adaptable PBS/LSF/SGE template scripts `benchmarks/submit_bench_{pbs,lsf,sge}.sh` currently pass `--out "$RESULTS_DIR/${NODE}-${STAMP}.json"`, writing a gitignored unredacted bare `.json` alongside the default `.redacted.json`).
    56:- **Full-package 3-platform static type checking (`mypy`) repaired and gated in CI.** Fixed the duplicate-module import in `src/pubrun/__main__.py` (preventing `pubrun report-bug` from loading `pubrun` twice) and type errors in `src/pubrun/__main__.py`, `src/pubrun/tui/widgets/actions.py`, `src/pubrun/tui/widgets/diff.py`, and `src/pubrun/report/reproducibility.py`. `mypy` now checks every module of the `pubrun` package with no `ignore_errors` exemptions in `pyproject.toml`, and the blocking Linux Python 3.12 CI `typecheck` job runs `mypy` for Linux plus `--platform win32` and `--platform darwin`.
    62:- **License changed from BSD-3-Clause to Apache-2.0 and package metadata aligned.** Relicensed under Apache-2.0 (`LICENSE`, `NOTICE`, `pubrun.__license__ = "Apache-2.0"`, copyright span 2007-2026 preserved, author email `gfariello@fariel.com`). Legal, copyright, and citation surfaces (`LICENSE`, `NOTICE`, `__copyright__`, README copyright, `pubrun cite`, generated methods report, `CITATION.cff`, PyPI author) consistently use **Gabriele Fariello**.
    63:- **`pubrun cite` and generated methods citation corrected.** Cite the software itself (`[Computer software]`, repository URL, version-aware, live Zenodo concept DOI `10.5281/zenodo.20801582`) with one consistent title across all surfaces instead of a premature, unpublished reference.
    74:- **`core.profile` (and `PUBRUN_PROFILE`, `start(profile=)`, and the TUI "Profile Mode" selector) is deprecated and inert.** `profile` was never wired to any capture engine, so setting it had no effect on capture. It remains accepted for backward compatibility, records a deprecation notice in `config.notices` (surfaced by `pubrun status`, `pubrun inspect`, and `pubrun show`) when set to a non-default value, and may be removed in a future release. To control capture depth, set the specific `capture.*` keys (such as `[capture.hardware].depth` and `[capture.packages].mode`). Wiring `profile` to real capture tiers was considered and declined; `core.profile` remains deprecated and inert.
    80:- **Manifest schema declares every import-mode behavior flag.** `pubrun_imports.selected_behavior` in `schemas/manifest.schema.json` now declares `patch_subprocesses`, `patch_console`, `signal_hooks`, and `force_console` alongside `auto_start` and `global_hooks`, and rejects undeclared flags (older manifests with only `auto_start` and `global_hooks` still validate).
    99:- **Manifest schema reconciled with emitted manifests and enforced as a hard test gate.** `schemas/manifest.schema.json` now covers `config.notices`, `imported-transitive` and `package_record.required_by`, transient `pending` and `timeout` capture states, root `filesystem`, `capture` enable flags, the full `host` section (with string `hostname`), `packages.records[].source`, `python` env-classification fields, and `resources` system/tree metrics. `docs/manifest.md` matches field-for-field, and `tests/test_manifest_schema.py` validates freshly generated manifests across variants (default, profile-notice, console-on, tree-scope, startup, and `imported-transitive`) as a hard gate via the dev-only `jsonschema` dependency.
    102:- **Honest HPC hydration documentation.** Corrected README and docs to state that `PUBRUN_META_REF` provides report-time hydration rather than automatically suppressing child capture; suppress heavy engines explicitly via `capture.hardware.depth = "off"` and `capture.packages.mode = "off"`. (`core.profile` is deprecated and inert.)
    105:- **`ProvenanceFileProxy`**: Uses incremental streamed hashing for read-mode files (avoiding redundant re-reads); added `write()`/`writelines()` support for write-mode hash accuracy.
    132:- **Synced benchmark-intake documentation and Issue Form with live `pubrun bench` behavior.** Updated `docs/cli.md`, `benchmarks/README.md`, `.github/ISSUE_TEMPLATE/benchmark-result.yml`, `.github/workflows/benchmark-intake.yml`, and `pubrun bench --help` to reflect the redacted-only default, `--unredacted` / `--contribute` / `--prepare-submission` / `--wait-timeout` flags, main-repo (`fariello/pubrun`) targeting, and the local-pull collection workflow (`benchmarks/pull_submissions.py`). Fixed a stale `Code of Conduct` link in `CONTRIBUTING.md`.
    324:- **Schema validation**: Added `signals` property and `signals_section` definition to `manifest.schema.json`. Added `ghost` to the `outcome` enum. Manifests now validate correctly.
    448:- **Schema**: Formal JSON Schema (`schemas/manifest.schema.json`) for manifest validation.
    ```

    Zero em/en-dash check:
    ```text
    dashes_in_added=0
    exit=0
    ```

    Relative link and anchor check:
    ```text
    broken=0
    exit=0
    ```

  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: Pasted `git diff -- CITATION.cff` showing `date-released: "2026-06-24"` matching `git show -s --format=%cs v1.3.1` and removal of the `(see the same IPD, Open Questions #1/#4)` comment, pasted `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov` passing, and pasted `python3 scripts/sanitize_paths.py --check --all` exiting 0.
  - Observed evidence:

    `git diff -- CITATION.cff` and `git show -s --format=%cs v1.3.1`:
    ```diff
    diff --git a/CITATION.cff b/CITATION.cff
    index 744c433..b9bf44b 100644
    --- a/CITATION.cff
    +++ b/CITATION.cff
    @@ -14,7 +14,7 @@ repository-code: "https://github.com/fariello/pubrun"
     url: "https://github.com/fariello/pubrun"
     license: Apache-2.0
     version: "1.3.1"
    -date-released: "2026-07-05"
    +date-released: "2026-06-24"
     # Zenodo concept DOI (all versions; always resolves to the latest archived release).
     identifiers:
       - type: doi
    @@ -23,4 +23,4 @@ identifiers:
     # NOTE: no `preferred-citation` block by design — pubrun has no peer-reviewed
     # paper yet, and we do not cite/insinuate one that does not exist. If a
     # peer-reviewed paper is accepted, add a `preferred-citation` block here with the real
    -# paper DOI (see the same IPD, Open Questions #1/#4).
    +# paper DOI.

    # git show -s --format=%cs v1.3.1
    tag v1.3.1
    Tagger: Gabriele Fariello <gabriele.fariello@gmail.com>

    Release v1.3.1
    2026-06-24
    ```

    `python3 -m pytest tests/test_cli.py::TestCitationConsistency -q --no-cov`:
    ```text
    ....                                                                     [100%]
    4 passed in 9.05s
    exit=0
    ```

    `python3 scripts/sanitize_paths.py --check --all`:
    ```text
    exit=0
    ```

  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: Pasted `git diff -- CHANGELOG.md` hunk between `## [1.1.0]` and `## [1.0.0]` confirming `## [1.0.3] - 2026-06-21`, `## [1.0.2] - 2026-06-20`, and `## [1.0.1] - 2026-06-20` match `git log --format="%h %cs %d %s" v1.0.0..v1.0.3`; pasted `grep -nE '^## \[1\.0\.[123]\]' CHANGELOG.md` showing all three headings (baseline `exit=1`); plus pasted zero-dash check (Required tests item 1) exiting 0.
  - Observed evidence:

    `git diff -U3 -- CHANGELOG.md` (`1.0.1`..`1.0.3` hunk) and `git log v1.0.0..v1.0.3`:
    ```diff

    @@ -760,6 +208,26 @@ The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
     ### Fixed
     - **Windows CI compatibility**: Made rerun tests platform-independent to ensure Windows CI compatibility.

    +## [1.0.3] - 2026-06-21
    +
    +### Added
    +- **Explicit Telemetry and Provenance API**: Added explicit file, output, and provenance tracking APIs (`e301c44`).
    +
    +### Fixed
    +- **Subparser error handling**: Improved CLI subparser error handling to display subcommand usage on invalid arguments (`2c0ee37`).
    +- **Position-independent `--no-color`**: Accepted `--no-color` in any position on the CLI (`fe99380`).
    +- **Windows newline test assertion**: Fixed Windows newline handling in `test_explicit_api.py` (`98058ec`).
    +
    +## [1.0.2] - 2026-06-20
    +
    +### Fixed
    +- **Remote-host liveness checks**: Improved liveness checks for remote-host runs using lock age (`a015c14`).
    +
    +## [1.0.1] - 2026-06-20
    +
    +### Fixed
    +- **Crashed-run timing and elapsed formatting**: Set crashed-run timing fields to `None` and implemented `HH:MM:SS` elapsed duration formatting (`88fe38b`).
    +
     ## [1.0.0] - 2026-06-19

     ### Added

    # git log --format="%h %cs %d %s" v1.0.0..v1.0.3
    98058ec 2026-06-21  (tag: v1.0.3) Fix Windows newline assertion failure in test_explicit_api.py
    e301c44 2026-06-21  Implement Explicit Telemetry and Provenance API (Phases 1-4)
    908c87f 2026-06-21  docs: expand explicit tracking API plan with stream hashing and proxy details
    bc2f419 2026-06-21  docs: add explicit tracking API evolution implementation plan
    d53c8a2 2026-06-21  docs: update implementation plan for subcommand-aware parsing errors
    2c0ee37 2026-06-21  fix: improve subparser error handling to show subcommand usage
    93c3d50 2026-06-21  docs: convert README.md relative links to absolute GitHub URLs
    fe99380 2026-06-21  fix: support --no-color flag in any position on the CLI
    8a19f57 2026-06-20  docs: add automated release preparation steps to release-review pipeline
    a015c14 2026-06-20  (tag: v1.0.2) fix: improve liveness checks for remote host runs by checking lock age
    88fe38b 2026-06-20  (tag: v1.0.1) fix: set crashed run timing fields to None and implement HH:MM:SS elapsed formatting
    ```

    `grep -nE '^## \[1\.0\.[123]\]' CHANGELOG.md`:
    ```text
    211:## [1.0.3] - 2026-06-21
    221:## [1.0.2] - 2026-06-20
    226:## [1.0.1] - 2026-06-20
    exit=0
    ```

    Zero em/en-dash check:
    ```text
    dashes_in_added=0
    exit=0
    ```

  - Result: pass


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
