# Review findings: ipd cuboum

- Subject-Id: cuboum
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `errors: 0`, `warnings: 0`, `info: 2` boilerplate `IPD-C802`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` with only the same two non-blocking advisories on line 176 boilerplate. Expanded `HPC` and `CLI` on first use and matched exact Markdown headings (with backticks) across `docs/cli.md`, `docs/performance.md`, `docs/functional_spec.md`, and `README.md`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `- Scope:`, `E-01`, `E-02`, `E-03` | `HPC` and `CLI` unexpanded; Markdown heading citations omitted backticks; `E-02` missed `benchmarks/README.md` line 206 `pubrun-bench-${NODE}`, line 9 em dash, `## Running on an HPC cluster`/`### Slurm details` updates, second stale PBS/LSF/SGE note (lines 268-270), and `benchmarks/share_safety.py` ref (line 273) | Expanded `HPC` and `CLI` on first use; matched exact Markdown headings; added explicit fixes for `benchmarks/README.md` lines 9, 206, 219-223, 239-245, 252, 268-270, and 273 and `docs/cli.md` line 311 | Prevent stale doc remnants and match exact repository headings (`PR-002`, `PR-003`) |
| `E-04`, `## Required tests / validation`, `V-04` | Validation Command 1 regex failed to match `docs/cli.md:318-319` (line-wrapped `not shipped in the\npip`) and `README.md:250` (`Requires a source checkout.` without `bench` on the same line); Command 2 used `git diff` instead of `git diff HEAD` | Rewrote Command 1 regex over all six target files to catch every stale checkout, PBS/LSF/SGE `--out`, and `${NODE}` filename pattern; updated Command 2 to `git diff HEAD --unified=0`; named all six files in `V-04` | Make validation non-vacuous and safe whether changes are staged or unstaged (`PR-001`, `PR-002`) |
| `## Approval and execution gate` | Single paragraph lacking open-question precondition, `--scope-reason`/`--scope-ack`, validation honesty rule, explicit no-`git add -A`/raw `git commit`, and conditional finalize ownership | Replaced with structured five-clause execution contract stating conditional `aw oc run`/`aw agy run` vs manual `aw ipd finalize cuboum` ownership | Satisfy execution-contract rules in `r2-executability.md` and `s7-finalize.md` (`PR-003`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: bej1qz`, `- Order: 4`, `- Item-Dependencies: executed:29nsim, executed:c1zz3x, executed:mfeptf`, `- Scope-Paths:` (`docs/cli.md, docs/performance.md, benchmarks/README.md, docs/hpc.md, docs/functional_spec.md, README.md`), 4 E-items in 3 task groups.

1. Yes: updates `docs/functional_spec.md` (Section 11.18 `bench` specification) alongside `docs/cli.md`, `docs/performance.md`, `benchmarks/README.md`, `docs/hpc.md`, and `README.md`.
2. No: documentation-only changes across six Markdown files; touches no code guarding private data, commits, worktree isolation, merges to main, or the sandbox.
3. No: 4 focused E-items across 3 task groups for one coherent documentation synchronization pass.
4. Yes: `- Scope-Paths:` explicitly lists all six documentation files.
5. No: prose-only documentation edits; cannot lose data or break runtime behavior and is trivially reversible.

AW-TIER: standard

### Step R1

- Checked: every target section in `docs/cli.md:309-380`, `docs/performance.md:1-75`, `benchmarks/README.md:1-310`, `docs/hpc.md:140-175`, `docs/functional_spec.md:645-660`, and `README.md:245-270`, plus a repository-wide grep across `docs/`, `README.md`, and `benchmarks/README.md` confirming no other documentation file claims `pubrun bench` requires a source checkout (`docs/manifest.md:39`, `docs/architecture.md:322`, and `docs/api.md:592` correctly describe `pubrun.__commit__` verified source-checkout resolution).
- Verified: reading the six files revealed that `docs/cli.md:318-319` wraps `"not shipped in the\npip package"`, `README.md:250` does not contain `"bench"` on the same line as `"Requires a source checkout."`, and `benchmarks/README.md` has a stale `pubrun-bench-${NODE}` filename pattern (line 206), an em dash (line 9), a second stale PBS/LSF/SGE `--out` note (lines 268-270), and a `benchmarks/share_safety.py` reference (line 273).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-04` <-> `V-01..V-04`), `- Scope-Paths:` completeness, `- Item-Dependencies: executed:29nsim, executed:c1zz3x, executed:mfeptf`, non-vacuous validation commands, and the execution gate contract.
- Verified: `PR-001` fixed the vacuous negative grep in Command 1 and staged-diff blind spot in Command 2; `PR-003` completed the five-clause execution contract in `## Approval and execution gate`.

### Step R3

- Checked: privacy and sanitization rules across all six documentation files.
- Verified: `E-02` corrects the stale `pubrun-bench-${NODE}-${STAMP}.redacted.json` documentation bug in `benchmarks/README.md:206` so docs accurately reflect the non-identifying `${ANON_ID}` hostname hash; `E-04` enforces `python3 scripts/sanitize_paths.py --check --all` so no machine-local path leaks into docs.

### Step R4

- Checked: correctness (A), architecture/canonical references (C), anti-regression (D), testing and verification (E), KISS/UX/dash discipline (F), right-sizing (4 focused E-items across 6 docs), and `## Spec / documentation sync`.
- Verified: all six documentation files are consistent with `29nsim` (`src/pubrun/_bench/`), `c1zz3x` (`src/pubrun/_bench/scripts/` and `PUBRUN_RESULTS_DIR`), and `mfeptf` (`pubrun bench` writable default `./pubrun-bench-results/` and single-source `pubrun._bench.share_safety`).

### Step S5

- Checked: `## Open questions` contains `None.`. All three findings (`PR-001` through `PR-003`) had `Low` overall Remediation Risk and were fixed in place from repository evidence, leaving zero open or deferred findings and zero unresolved human decisions. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r4-engineering.md` E / `r2-executability.md` (Validation vacuity) | `.aw/records/plans/pending/20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.ipd.md:151,157` vs `docs/cli.md:318-319`, `README.md:250`, `benchmarks/README.md:206,252` | Validation Command 1's regex (`not shipped in the pip\|bench.*requires a source checkout\|requires a source checkout.*bench`) fails to match `docs/cli.md:318-319` (`not shipped in the` wraps across lines) and `README.md:250` (`Requires a source checkout.` has no `bench` on the same line), so it passes vacuously even if those files stay unedited; Command 2 uses `git diff` instead of `git diff HEAD`, missing staged changes. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Rewrote Validation Command 1 over all six target files to match `requires a source checkout\|not shipped in the\|from a source checkout\|pubrun-bench-\$\{NODE\}\|--out "\$RESULTS_DIR/\$\{NODE\}-\$\{STAMP\}\.json"`, updated Command 2 to `git diff HEAD --unified=0`, and named all six files in `V-04` (recommendation strength: `very strong`). |
| PR-002 | MEDIUM | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A (Completeness of doc fixes) | `.aw/records/plans/pending/20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.ipd.md:72-104` vs `benchmarks/README.md:9,206,219-223,239-245,252,268-273` and `docs/cli.md:309-311` | `E-02` missed updating `benchmarks/README.md` line 206's stale `pubrun-bench-${NODE}-${STAMP}.redacted.json` pattern (real script uses `${ANON_ID}`), line 9's em dash, `## Running on an HPC cluster`/`### Slurm details` (`PUBRUN_RESULTS_DIR`, `pip install pubrun`), the second stale PBS/LSF/SGE `--out` note (lines 268-270), and line 273's `benchmarks/share_safety.py` ref; `E-01`..`E-03` omitted backticks in four Markdown heading citations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added each missed `benchmarks/README.md` and `docs/cli.md` update to `E-01`/`E-02`/`V-01`/`V-02` and matched exact backticked Markdown headings (recommendation strength: `strong`). |
| PR-003 | MEDIUM | IN-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` (Execution contract and technical writing) | `.aw/records/plans/pending/20261127-bej1qz-04-cuboum-update-benchmark-documentation-for-packaged-wheel-runtime.ipd.md:6,70,198-203` | `## Approval and execution gate` omitted the open-question precondition, `--scope-reason`/`--scope-ack` scope declaration, hard-MUST validation honesty rule, explicit no-`git add -A`/raw `git commit` prohibition, and conditional runner vs manual `aw ipd finalize cuboum` ownership; `HPC` and `CLI` were not expanded on first use. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the gate paragraph with the complete five-clause execution contract (including conditional `aw oc run`/`aw agy run` vs manual `aw ipd finalize cuboum` ownership) and expanded `HPC` and `CLI` on first use (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `cuboum` | `standard` | `simple`, `complex` | Updates `docs/functional_spec.md` (Section 11.18) plus five user-facing docs (tier question 1 is Yes; questions 2, 3, and 5 are No), fitting `standard` tier in `steps/t-tier.md`. | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; all three revisions (`PR-001` through `PR-003`) were swept across `E-01..E-04`, `## Project conventions discovered`, `## Findings`, `## Proposed changes`, `## Required tests / validation`, `V-01..V-04`, and `## Approval and execution gate` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
