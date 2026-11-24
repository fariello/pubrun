# IPD: Document benchmarks/package_capture_bench.py in benchmarks/README.md

- Date: 2026-11-23
- Kind: child
- Concern: Benchmark suite documentation completeness
- Scope: Add a design bullet and a running subsection in `benchmarks/README.md` documenting `benchmarks/package_capture_bench.py`, its CLI flags, measurement profiles/modes, cold-versus-warm methodology, and local redacted output.
- Scope-Paths: benchmarks/README.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: standard
- Work-Kind: chore
- Priority: low
- From-Backlog: ewgjmx
- Set: ewgjmx
- Order: 1
- Highest E allocated: 02
- Author: Antigravity
- Id: c39m4v
- Approval: 2026-11-24, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 approved (aw set): status set to approved
- 2026-11-24 /plan-review (uri/its_direct/pt3-claude-opus-5.5-1m-us): APPROVE WITH REVISIONS APPLIED; PR-001..PR-007 fixed (PR-001 `--json-out` example path is not a share-safe or aggregatable result; PR-002 validation could not catch a missing flag, mode, profile, or schema string); review record `.aw/records/reviews/20261123-ewgjmx-01-c39m4v-document-benchmarks-package-capture-bench-py-in-benchmarks-r.review.md`.
- 2026-11-24 draft (Antigravity): created.
- 2026-11-24 to-review (Antigravity): graduated from backlog item `ewgjmx` into a review-ready plan.

## Goal

`benchmarks/README.md` is the guide contributors read to find and run the benchmark scripts. It documents `harness.py` and `startup_breakdown.py` but not `benchmarks/package_capture_bench.py`, the script that times pubrun's package capture at run startup and at finalization. This plan adds the same two pieces the guide already has for `startup_breakdown.py`: one bullet under `## Design`, and one subsection under `## Running` that tells a contributor how to run the script, what each flag does, what it measures, and what it writes. The new text must match the script's actual behavior, because a reader will copy the commands.

No diagram is added: the change is two text additions to one file (technical writing standard requirement 12(c)).

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Document package_capture_bench.py in benchmarks/README.md

- [ ] E-01 Add a `package_capture_bench.py` bullet under `## Design` in `benchmarks/README.md`.
  - Depends on: none
  - Expected outcome: A bullet starting `- **`package_capture_bench.py`** - ` sits directly after the `startup_breakdown.py` bullet and before the `scenarios.py` bullet, in the same style (bold backticked name, then ` - `). It states that the script: uses only the Python standard library; is local and non-publishing; times the startup package snapshot and the finalization refresh separately; covers the five package-capture modes; and uses two synthetic profiles plus the ambient (real) interpreter profile. The bullet's own text contains no em dash (U+2014) or en dash (U+2013); the existing bullets keep their dashes, which are outside this plan's edit.
  - Execution state: pending

- [ ] E-02 Add a `### Package capture benchmark` subsection under `## Running` in `benchmarks/README.md`.
  - Depends on: E-01
  - Expected outcome: A `### Package capture benchmark` subsection sits directly after the `### Startup and finalization breakdown` subsection and before `## Running on an HPC cluster`, laid out like that subsection: an intro paragraph, a fenced `bash` block of example commands, a `CLI flags:` list, and a `What it measures and reports:` list. It contains all of the following, each taken from `benchmarks/package_capture_bench.py` (see Project conventions):
    1. Intro: standard library only; local and non-publishing (it uploads nothing and submits no scheduler job); the `--json-out` file is written locally and redacted.
    2. Example commands, which must include `python benchmarks/package_capture_bench.py`, the docstring's full-parameter form (`--small-count 10 --large-count 300 --repetitions 10 --cold-runs 3`), and a `--workdir /path/to/shared/scratch --json-out /tmp/package-capture.json` form. Do NOT use an output path under `benchmarks/results/` (see Findings PR-001).
    3. `CLI flags:` one bullet per flag with its meaning and default: `--small-count` (synthetic distributions in the `small` profile, integer >= 1, default `10`); `--large-count` (synthetic distributions in the `large` profile, integer >= 1, default `300`); `--repetitions` (warm measured passes per profile and mode, integer >= 1, default `10`); `--cold-runs` (fresh-process cold runs per profile and mode, integer >= 1, default `3`); `--workdir` (optional parent directory for the synthetic environments, for example an NFS or Lustre scratch path; only a dedicated temporary subdirectory is created inside it and it is removed on exit); `--json-out` (optional local path for the redacted JSON result; standard output always prints a Markdown summary). State that a value below 1 for the four integer flags exits with status `2`.
    4. `What it measures and reports:` the two timing points (`startup`: the startup snapshot; `finalization`: the refresh plus its merge with the startup snapshot, as `Run` does it); the five modes `off`, `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment`, with `off` as the baseline that each mode's `delta_vs_off_ms` is measured against; the three profiles `small` and `large` (synthetic `site-packages` trees run under `python -S`) and `ambient` (the running interpreter's real packages); cold samples (one fresh child process per run, empty distribution cache) versus warm samples (one child process per profile and mode, one discarded warmup pass, then repeated passes that reuse the cache); the JSON result format `pubrun-package-capture-bench/1`, which is not the `pubrun-benchmark/5` format and is not read by `aggregate.py`; redaction of hostname, username, and machine-local paths with a share-safety check before any output; and exit status `1` when any sample failed.
    5. One sentence linking to the published single-machine results: `[performance documentation](../docs/performance.md#package-capture-startup-and-finalization-overhead-single-machine-local-measurements)`.
    6. The subsection's own text contains no em dash (U+2014) or en dash (U+2013).
  - Execution state: pending

## Project conventions discovered (Step 0)

- Cite code by SYMBOL (`module.function`) or by a quoted content string, with a line number only appended to one of those and never alone (`IPD-C801`).
- Facts about `benchmarks/package_capture_bench.py`, verified by reading it and running it at review (lane HEAD `93995d7`):
  - `benchmarks/package_capture_bench.py::SCHEMA_VERSION` is `"pubrun-package-capture-bench/1"`.
  - `benchmarks/package_capture_bench.py::MODES` is `off`, `imported-only`, `imported-transitive`, `top-level-installed`, `full-environment`; `benchmarks/package_capture_bench.py::PROFILES` is `small`, `large`, `ambient`.
  - `benchmarks/package_capture_bench.py::parse_args` defines `--small-count` (default `10`), `--large-count` (default `300`), `--repetitions` (default `10`), `--cold-runs` (default `3`), `--workdir` (default none), `--json-out` (default none), plus a hidden internal `--_child` flag that must not be documented.
  - `benchmarks/package_capture_bench.py::main` exits `2` with `error: --repetitions must be an integer >= 1` for a value below 1 (observed: `python3 benchmarks/package_capture_bench.py --repetitions 0` printed that line, exit 2); it redacts with `startup_breakdown.redact_breakdown`, validates with `startup_breakdown.validate_redacted_output` (which calls `benchmarks/share_safety.py::check_share_safe`), refuses to write output when that check fails, and returns `1` when any sample failed.
  - `benchmarks/package_capture_bench.py::_measure_mode` takes `cold_runs` fresh-process samples and one warm child process running `repetitions` passes; `benchmarks/package_capture_bench.py::_child_main` runs one discarded warmup pass first.
  - `benchmarks/package_capture_bench.py::_add_deltas` computes `delta_vs_off_ms` against the `off` mode.
  - The module docstring's usage block lists the three example invocations quoted in E-02 item 2 (`"python benchmarks/package_capture_bench.py --workdir /path/to/shared/scratch \\"`).
  - It uses only standard library modules plus the sibling `startup_breakdown` and `share_safety` helpers, and contains no `gh`, Gist, `git push`, `sbatch`, `qsub`, or `bsub` call.
- `benchmarks/results/.gitignore` ignores every file except `.gitignore` and `*.redacted.json` (`git check-ignore -v benchmarks/results/package-capture.json` reports rule `*`), and `benchmarks/test_benchmarks.py::TestSchema5Conformance.test_committed_redacted_sample_conforms` validates every `benchmarks/results/*.redacted.json` against `schemas/benchmark.schema.json`. A package-capture result fails that schema (measured at review: 10 errors, first `Additional properties are not allowed`).
- `benchmarks/README.md#Startup and finalization breakdown` is the style template: intro paragraph, `bash` block, `CLI flags:` list, `What it measures and reports:` list. It already uses ` - ` (hyphen) in its new bullets; older bullets contain em dashes (24 lines at review), which this plan does not touch.
- `docs/performance.md#Package capture startup and finalization overhead (single-machine local measurements)` already documents the method and one machine's results; the README subsection links to it rather than repeating the numbers.
- Agent execution contract (`AGENTS.md`): user-facing prose this plan authors in `benchmarks/README.md` contains no em or en dashes.

## Findings

`benchmarks/package_capture_bench.py` exists and is tested by `tests/test_package_benchmark.py`, and `docs/performance.md` reports its results, but `benchmarks/README.md` lists only `harness.py` and `startup_breakdown.py` under `## Design` and `## Running`. A contributor reading `benchmarks/README.md` has no guidance on how to run the script or what its flags and profiles are.

## Proposed changes (ordered, validatable)

1. **`benchmarks/README.md` (`## Design`, E-01):** Add one bullet for `package_capture_bench.py` directly below the `startup_breakdown.py` bullet, with the content E-01 lists.
2. **`benchmarks/README.md` (`## Running`, E-02):** Add a `### Package capture benchmark` subsection directly after `### Startup and finalization breakdown`, with the six parts E-02 lists. Take each flag's meaning and default from `python3 benchmarks/package_capture_bench.py --help`.

## Deferred / out of scope (with reason)

None.

## Scope check

- Over-scope: none. Only `benchmarks/README.md` is edited.
- Under-scope: none. Every user-visible flag, mode, profile, exit status, and output property of `benchmarks/package_capture_bench.py` is listed in E-01 and E-02.

## Required tests / validation

Run each command from the repository root and paste its actual output into the matching `V-*` item.

1. `git diff benchmarks/README.md` (the whole change).
2. Placement check:

   ```bash
   grep -n -E '^## |^### |^- \*\*`(startup_breakdown|package_capture_bench|scenarios)\.py`\*\*' benchmarks/README.md
   ```

   Expected: the `package_capture_bench.py` bullet line falls between the `startup_breakdown.py` and `scenarios.py` bullet lines, and `### Package capture benchmark` falls between `### Startup and finalization breakdown` and `## Running on an HPC cluster`.
3. Dash check on added lines (prints `0`; `grep -c` exits 1 when the count is 0, which is the expected result):

   ```bash
   git diff -U0 benchmarks/README.md | grep '^+[^+]' | grep -c $'[\u2013\u2014]'
   ```

4. Content check. It extracts the new subsection and prints one line per required token that is missing; it must print `OK` and exit 0:

   ```bash
   python3 - <<'EOF'
   import re, sys
   text = open("benchmarks/README.md", encoding="utf-8").read()
   sub = text.split("\n### Package capture benchmark\n", 1)[1].split("\n## ", 1)[0]
   design = re.search(r"^- \*\*`package_capture_bench\.py`\*\*.*?(?=^- \*\*)", text, re.S | re.M).group(0)
   need = ["--small-count", "--large-count", "--repetitions", "--cold-runs", "--workdir", "--json-out",
           "`10`", "`300`", "`3`", "off", "imported-only", "imported-transitive", "top-level-installed",
           "full-environment", "small", "large", "ambient", "cold", "warm", "startup", "finalization",
           "pubrun-package-capture-bench/1", "aggregate.py", "performance.md#package-capture-startup-and-finalization-overhead-single-machine-local-measurements"]
   miss = [t for t in need if t not in sub]
   miss += ["design bullet lacks " + t for t in ("startup", "finalization", "ambient") if t not in design]
   miss += ["forbidden: benchmarks/results/ path or --_child"] if ("benchmarks/results/" in sub or "--_child" in sub) else []
   print("\n".join(miss) if miss else "OK"); sys.exit(1 if miss else 0)
   EOF
   ```

5. Flag and default parity: `python3 benchmarks/package_capture_bench.py --help`, compared by the executor line by line with the `CLI flags:` list.
6. Leak scan: `python3 scripts/sanitize_paths.py --check --all`; expected exit code 0 (it exited 0 at review).

## Spec / documentation sync

This plan is itself the documentation update. No spec in `.aw/records/specs/` mentions `package_capture_bench` (searched at review), and no code, flag, or output format changes, so no spec or other document changes. `docs/performance.md` already documents the benchmark's method and results and is linked, not edited. No `CHANGELOG.md` entry: the benchmark is dev tooling not shipped in the wheel, and its addition was not itself recorded in `CHANGELOG.md`.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Paste the `## Design` hunk of `git diff benchmarks/README.md` showing the new bullet; the output of the placement check (Required tests 2) showing the bullet line number between the `startup_breakdown.py` and `scenarios.py` bullets; and the dash check (Required tests 3) printing `0`.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Paste the `## Running` hunk of `git diff benchmarks/README.md` showing the new subsection; the placement check output showing `### Package capture benchmark` between `### Startup and finalization breakdown` and `## Running on an HPC cluster`; the content check (Required tests 4) printing `OK`; the full `python3 benchmarks/package_capture_bench.py --help` output (reachable through `benchmarks/package_capture_bench.py::parse_args`) with a sentence confirming each documented default equals the help text; and the output and exit code of `python3 scripts/sanitize_paths.py --check --all`.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:

1. Precondition: wait for human approval (`- Status: approved`) before you change any file. This plan has no open question.
2. Scope declaration: the expected modified file is the `- Scope-Paths:` entry, `benchmarks/README.md`. If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If the declared file needs no edit, acknowledge it with `--scope-ack`.
3. Validation honesty: you MUST run each Required tests command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only `benchmarks/README.md` with `aw commit c39m4v -- benchmarks/README.md`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize c39m4v`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize c39m4v` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
