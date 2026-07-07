# IPD-G: benchmark pass structure — baseline-warmup pass + `--rigorous` (50×50)

- Date: 2026-07-07
- Concern: benchmark methodology / usability. Two refinements to how `pubrun bench` structures
  its passes: (1) add an explicit "not captured" baseline pass (a warmup that also records the
  pubrun-absent floor), and (2) offer a heavier, statistically-stronger mode without doubling
  every casual run's runtime.
- Scope: `benchmarks/harness.py` (pass loop + iteration/pass defaults + a `--rigorous` mode),
  `src/pubrun/__main__.py` (`pubrun bench` flag passthrough), docs, tests. `benchmarks/` is
  dev/source-only (not shipped in the wheel).
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

A first baseline (uncaptured) warmup pass for a clean pubrun-absent floor + cache warming, a
tuned three-tier pass structure (quick / default / rigorous), and a recorded total wall-time
for the whole benchmark invocation.

**Decided pass structure (maintainer 2026-07-07):** every mode begins with a **1× uncaptured
baseline pass**, then N measured passes × M iterations:
- `--quick`   → baseline 1× + **2 passes × 15 iterations**
- (default)   → baseline 1× + **3 passes × 30 iterations**
- `--rigorous`→ baseline 1× + **5 passes × 50 iterations**

`--iterations`/`--passes` still override explicitly. The result JSON must record the **total
benchmark wall-time** (from harness start to finish, covering the whole invocation, not just
the summed per-iteration times).

## Project conventions discovered (Step 0)

- Harness: `FULL_ITERATIONS=30`, `QUICK_ITERATIONS=8` (`harness.py:47-48`); default
  `--passes 2` (full sweep twice, both recorded; `harness.py:10-18`); per-pass warmup=1
  (`_run_pass`, `:267,291`). Schema now `/4` with raw `timings` (IPD data-quality).
- `pubrun bench` exposes `--quick`/`--full`/`--iterations`/`--passes` (`__main__.py` bench
  subparser). Raw per-iteration timings are recorded (schema/4), so precision is
  re-poolable across submissions — a lighter default does not lose analyzable data.
- Maintainer decision (2026-07-07): **lighter default; 50×50 as `--rigorous`/`--full`.** The
  first pass should be a **1× not-captured baseline**.

## Findings

| ID | Severity | Rem. Risk | Persona | Area | Finding | Evidence |
|----|----------|-----------|---------|------|---------|----------|
| G1 | Low | Low | eng | Methodology | No explicit uncaptured "pubrun absent" baseline pass; the pubrun-off floor is inferred from baseline scenarios, not a dedicated warmup pass. | `harness.py` pass loop |
| G2 | Low | Low | eng | Methodology | Only one pass structure; no heavier high-confidence mode for those who want tight CIs. | `harness.py:47-48` |
| G3 | Low | Low | novice | Usability | Making a heavy sweep the default would ~double casual run time; the raw-timings/pooling design makes that unnecessary. | schema/4 timings |

## Proposed changes (ordered, validatable)

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | G1 | Add an initial **baseline (not-captured) pass**: 1× sweep run WITHOUT pubrun active (the honest "cost floor" + cache warm), recorded as `pass 0` / `baseline_pass` in the result. Its numbers establish the pubrun-absent reference and warm filesystem caches before the measured passes. | `harness.py` | Low | Result contains a labeled uncaptured baseline pass; its per-scenario timings are present; measured passes follow it. |
| 2 | G2,G3 | Implement the DECIDED three tiers: `--quick` = baseline 1× + **2×15**; default = baseline 1× + **3×30**; `--rigorous` = baseline 1× + **5×50**. `--iterations`/`--passes` override. `--full` stays a clarity alias of the DEFAULT (not the heavy mode) to avoid a silent redefinition. | `harness.py`, `__main__.py` | Low | `--quick`=2×15+baseline; default=3×30+baseline; `--rigorous`=5×50+baseline; explicit `--iterations/--passes` override; `--full`==default. |
| 3 | G2 | Record the pass structure (iterations, passes, baseline-pass flag, mode) AND the **total benchmark wall-time** (harness start→end, the whole invocation) in the result JSON. | `harness.py` | Low | Result JSON documents its own pass/iteration structure + mode, and a `total_wall_time_s` (or similar) covering the entire run. |

## Deferred / out of scope (with reason)

None deferred on risk. Note: whether `--full` is redefined to mean `--rigorous` is a naming
call (Open Q1), not a deferral — `--full` currently means "30 iters (the default)"; changing
its meaning is a small breaking-ish CLI nuance to settle at plan-review.

## Scope check

- Over-scope: not changing the measurement core or scenarios; only the pass STRUCTURE + a mode
  flag. Not making the heavy mode default (explicitly rejected — Complexity/usability).
- Under-scope: the uncaptured baseline pass (a cleaner methodology) was missing; added.

## Required tests / validation

- Baseline pass: present, labeled, uncaptured (runs the workload without pubrun active),
  recorded with its timings; measured passes still recorded.
- Tier numbers: `--quick`=baseline+2×15; default=baseline+3×30; `--rigorous`=baseline+5×50;
  `--iterations`/`--passes` still override; `--full`==default.
- Result JSON self-describes its pass structure/mode AND records the total benchmark wall-time
  (harness start→end), distinct from the summed per-iteration timings.
- A light smoke run (1 iter/1 pass) still completes and writes a valid schema/4 result.
- **Backward-compat:** the added baseline pass must not break schema/4 consumers — `aggregate.py`
  and `redact_result` must tolerate the new baseline/`pass 0` entry (verified `benchmarks/
  test_benchmarks.py` has NO pass-count assertion, so this is additive; confirm `aggregate.py`
  ignores or handles the uncaptured baseline pass rather than mixing it into measured stats).
- Full suite green (benchmarks self-test `benchmarks/test_benchmarks.py`).

## Spec / documentation sync

`benchmarks/README.md` (pass structure: baseline + measured; `--rigorous`), `docs/cli.md`
(`bench --rigorous`), `pubrun-benchmarks/README.md` (what the baseline pass is),
`CHANGELOG.md`.

## Open questions

1. **Tier numbers + naming — RESOLVED (maintainer 2026-07-07):** `--quick` = baseline+2×15;
   default = baseline+3×30; `--rigorous` = baseline+5×50. `--full` stays a clarity alias of the
   default (NOT the heavy mode). All modes begin with a 1× uncaptured baseline pass.
2. **Total wall-time — RESOLVED (added):** the result JSON records the total benchmark wall-time
   (harness start→end) covering the whole invocation, in addition to per-iteration timings.
3. Runtime expectation to document: default is now baseline+3×30 (~1.5× the old 2×30);
   `--rigorous` (baseline+5×50) is markedly longer — the docs should set expectations
   ("`--rigorous` may take many minutes; intended for a dedicated/HPC run"). (Confirm wording
   at execution.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.

## Plan-review record (2026-07-07)

Reviewed via `plan-review`. Verified `FULL_ITERATIONS=30`/`QUICK_ITERATIONS=8` + `--passes 2`
default (`harness.py:47-48,10-18`), schema/4 raw timings, and that `benchmarks/test_benchmarks.py`
has NO pass-count assertion. Verdict: **APPROVE WITH REVISIONS APPLIED.**
- **P9 (LOW, backward-compat):** required the added uncaptured baseline (`pass 0`) to not break
  schema/4 consumers — `aggregate.py`/`redact_result` must tolerate/ignore the baseline pass
  and not fold it into measured stats.
Correctly honors the maintainer decision (lighter default; 50-iter behind `--rigorous`). Open
questions (—`--full` vs `--rigorous` naming; exact heavy numbers = 2×50 not 50 passes; default
iteration bump) are the remaining maintainer calls, flagged clearly.
