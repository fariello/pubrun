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

A first baseline (uncaptured) warmup pass for a clean pubrun-absent floor + cache warming,
and a heavier `--rigorous` (50×50) mode — while keeping the DEFAULT light enough for casual
use (maintainer-confirmed: lighter default, 50×50 behind a flag).

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
| 2 | G2,G3 | Keep the DEFAULT light (proposed: baseline 1× + **2 measured passes × 30** — i.e. current 2×30 plus the new baseline pass). Add **`--rigorous`** (alias `--full` may map here or stay 30 — see Open Q1) = baseline 1× + **2 × 50** (or the maintainer's 50×50). Expose via `pubrun bench --rigorous`. | `harness.py`, `__main__.py` | Low | Default runtime ≈ current + one baseline sweep; `--rigorous` runs the heavier structure; `--quick` unchanged. |
| 3 | G2 | Record the pass structure (iterations, passes, baseline-pass flag, rigorous flag) in the result JSON so an analyzer knows how the numbers were produced. | `harness.py` | Low | Result JSON documents its own pass/iteration structure and mode. |

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
- Default vs `--rigorous`: default = baseline + 2×30; `--rigorous` = baseline + 2×50 (or agreed
  numbers); `--quick` unchanged; `--iterations`/`--passes` still override.
- Result JSON self-describes its pass structure/mode.
- A light smoke run (1 iter/1 pass) still completes and writes a valid schema/4 result.
- Full suite green (benchmarks self-test `benchmarks/test_benchmarks.py`).

## Spec / documentation sync

`benchmarks/README.md` (pass structure: baseline + measured; `--rigorous`), `docs/cli.md`
(`bench --rigorous`), `pubrun-benchmarks/README.md` (what the baseline pass is),
`CHANGELOG.md`.

## Open questions

1. **`--full` vs `--rigorous` naming:** redefine `--full` to be the heavy 50×50 (breaking its
   current "default 30" meaning), or add a distinct `--rigorous` and leave `--full` as the
   30-iter alias-of-default? (Leaning: distinct `--rigorous`; keep `--full` = current meaning
   to avoid a silent behavior change.)
2. **Exact heavy numbers:** maintainer floated 50×50 (50 iters × ... ); confirm "baseline 1× +
   2 measured × 50" vs literally "1×(uncaptured) + 50×all + 50×all" (i.e. 50 PASSES). 50 full
   passes is very long; 2 passes × 50 iterations is the likely intent — confirm.
3. **Default iteration bump:** keep measured default at 2×30, or bump to 2×50 now that raw
   timings pool across submissions? (Leaning: keep 2×30 default for casual speed; rigorous for
   tight CIs.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`.
