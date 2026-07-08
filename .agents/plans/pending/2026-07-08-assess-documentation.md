# IPD: Assess documentation — sync docs to the 2026-07-07 CLI/UX batch

- Date: 2026-07-08
- Concern: documentation (accuracy-first)
- Scope: primarily project docs (`README.md` CLI section, `docs/cli.md`,
  `docs/configuration.md`, `CHANGELOG.md`), PLUS one small code change (D2, decided): expose
  `--no-baseline` on `pubrun bench` so the CHANGELOG is truthful. Triggered by the doc-sync
  discipline in `AGENTS.md` after the 7-IPD CLI/UX batch (commits `f7ed43c`, `a262232`,
  `0da1ee5`, `e1eafe7`, `4cd956a`, `ac73c9a`, `fb86e84`).
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Make every user-facing doc match what pubrun does **today** after the batch. Two of the
findings are genuine *behavior/accuracy defects introduced by the batch itself* (a stale
`--passes` help string that now contradicts the tier docs, and a CHANGELOG line claiming a
`pubrun bench --no-baseline` flag that only exists on the harness) — those are the priority.
The rest is README lag: the README's CLI section was not fully updated for the batch's new
flags/behaviors, and a couple of pre-existing `cli.md` gaps (`res --average`) surfaced.

## Project conventions discovered (Step 0)

- Guiding principles: `AGENTS.md` (doc-sync discipline: run `/assess documentation` after
  user-visible changes; honest docs). KISS / zero-dep / concise-README ethos.
- Lifecycle: `.agents/plans/pending/` → `.agents/plans/executed/`, dated IPDs. Assess IPDs
  use `YYYY-MM-DD-assess-<concern>.md`. Run record under `workflow-artifacts/assess-<concern>/`.
- Docs set (all nav links verified to resolve): `docs/{architecture,functional_spec,api,cli,
  configuration,manifest,performance,research-use,hpc}.md`, `README.md`, `CHANGELOG.md`.
- Dev/validation interpreter: `~/venv/p3.11.8` (the prior `p3.14` venv is gone). Real command
  set verified via `python -m pubrun <cmd> -h`.
- Verified CLEAN (no action): `docs/manifest.md` (fully covers `peak_tree_cpu_percent`,
  `python.environment_kind/in_venv/sys_path_len`); nav-link integrity; CHANGELOG batch coverage
  (except finding D7); Roadmap "Future" items genuinely unshipped; README has no stale
  command-count number.

## Findings

Severity = impact if left alone; Remediation Risk = Fix-Bar gate. Persona: N=novice,
E=engineer/operator.

| ID | Severity | Rem. Risk | Persona | Area | Finding | Evidence |
|----|----------|-----------|---------|------|---------|----------|
| D1 | Medium | Low | E | **Accuracy (behavior)** | `bench --passes` help says "(default 2)" but the effective default tier is `--full` = **3 passes**; the "(default 2)" is a stale leftover from the old flat 2×30 and now contradicts the documented tiers. | `__main__.py` bench `--passes` help vs `benchmarks/harness.py:57` `"default": (30, 3)`; `bench -h` |
| D2 | Medium | Low | E | **Accuracy (docs claim a nonexistent flag)** | `CHANGELOG.md` bench bullet ends "`--no-baseline` skips the baseline pass" — but `--no-baseline` exists only on the harness (`harness.py:524`), NOT on `pubrun bench` (`bench -h` has no such flag). A reader can't run `pubrun bench --no-baseline`. | `CHANGELOG.md` (bench Added bullet) vs `bench -h`; `harness.py:524,542` |
| D3 | High | Low | N,E | Accuracy | README `self-check` entry shows only `[--show-suggestions] [--strict]`; real command also has `--quiet`/`-q`, `--json`, and `--show-suggestions` short form `-v`, and is now **itemized by default** (the whole point of IPD-D). README describes neither the new default nor the flags. | `README.md` self-check section vs `self-check -h`; commit `e1eafe7` |
| D4 | Medium | Low | N,E | Accuracy | README `diff` entry omits the new `--table` flag and that `--basic`/`--standard` now summarize (no longer a wall of text); still implies volatile-filtering "by default" without noting `--standard` is the default depth. | `README.md` diff section vs `diff -h`; commit `a262232` |
| D5 | Medium | Low | N,E | Accuracy | README `bench` entry omits the new `--rigorous` tier and the uncaptured baseline pass. | `README.md` bench section vs `bench -h`; commit `fb86e84` |
| D6 | Medium | Low | N,E | Completeness | The recency-index run selector (`pubrun show 2` = 2nd most recent) is documented in `cli.md` but not in the README (e.g. `status`/`show` examples). | `README.md` vs `docs/cli.md:25-43`; commit `4cd956a` |
| D7 | Medium | Low | E | Completeness | `docs/cli.md` `res`/`cpu`/`mem` omit the `--average` flag (and don't explain `-l/--last`), and omit the standard run-filter flags those commands accept. | `res -h`/`cpu -h`/`mem -h` (all show `--average`, `-l`, `-f/-F/-s/-S/--older-than/--exit-code`) vs `docs/cli.md` res/cpu/mem sections |
| D8 | Low | Low | E | Accuracy | `docs/configuration.md` `[diff]` ignore lists are shown only as `["timing", "run", ...]` placeholders; the real lists were rebuilt (`a262232`) and now differ (e.g. `run.run_id` not `run`, added `filesystem.*.path`, and basic-only section names). Reader can't see current defaults. | `docs/configuration.md` `[diff]` vs `default.toml` `ignore_basic`/`ignore_standard` |
| D9 | Low | Low | N | Accuracy | README `res` description predates peak/avg/min + tree CPU (IPD-C). | `README.md` res entry vs `cli.md` res section; commit `0da1ee5` |
| D10 | Low | Low | N | Completeness | README does not mention the normalized output-prefix scheme (`[INFO ]`/`[WARN ]`/`[ERROR]`/…); documented in `cli.md` but a README reader won't know. | `README.md` vs `docs/cli.md` "Output conventions" |
| D11 | Low | Low | E | Consistency | `docs/cli.md` `status` command section lists its columns but omits the new leading `#` recency column (which the selector section above it references). | `docs/cli.md` status section vs `status -h` output (`#` column) |

## Proposed changes (ordered, validatable)

Priority: the behavior/accuracy defects (D1, D2) first, then README accuracy (D3–D6, D9),
then completeness/consistency (D7, D8, D10, D11).

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | D1 | Fix the `bench --passes` help to not claim "(default 2)"; state it overrides the tier's passes (default tier = 3). | `src/pubrun/__main__.py` (bench `--passes` help), `docs/cli.md` if it echoes "default 2" | Low | `bench -h` no longer says "default 2"; help matches the tier table. |
| 2 | D2 | **DECIDED: expose `--no-baseline` on `pubrun bench`** (add the flag to the bench subparser; thread a `no_baseline` param through `_run_bench`; forward `--no-baseline` to the harness argv in both the local and Slurm-submit builders, exactly like `--rigorous`). Document it in `docs/cli.md` bench options. Keep the CHANGELOG line as-written. | `src/pubrun/__main__.py`, `docs/cli.md` | Low | `pubrun bench --no-baseline` is accepted and forwards `--no-baseline` to the harness argv (test); `bench -h` shows it. |
| 3 | D3 | Update the README `self-check` entry: itemized-by-default; add `--quiet`/`-q`, `--json`, `-v`. | `README.md` | Low | README matches `self-check -h`; mentions itemized default + `--quiet`. |
| 4 | D4 | Update the README `diff` entry: `--table`; note `--basic`/`--standard` summarize and `--standard` is the default depth. | `README.md` | Low | README matches `diff -h`; no "wall of text" implication. |
| 5 | D5 | Update the README `bench` entry: the three tiers (`--quick`/`--full`/`--rigorous`) + the uncaptured baseline pass. | `README.md` | Low | README matches `bench -h` + `cli.md` tier table. |
| 6 | D6 | Add a short "select a run by recency index (`1` = most recent)" note to the README (near the status/show examples), cross-referencing `cli.md`'s "Selecting a run". | `README.md` | Low | README mentions the recency selector. |
| 7 | D9, D10 | README `res` line updated to peak/avg/min + tree CPU; add a one-line pointer to the output-prefix conventions (link to `cli.md`). | `README.md` | Low | README `res` matches; output-conventions referenced. |
| 8 | D7 | `docs/cli.md`: document `--average` and `-l/--last` for `res`/`cpu`/`mem`, and list the standard run-filter flags they accept. | `docs/cli.md` | Low | Each chart command's documented flags match its `-h`. |
| 9 | D8 | `docs/configuration.md`: replace the `[diff]` ignore-list `...` placeholders with the current defaults (or an accurate summary of what each level hides), matching `default.toml`. | `docs/configuration.md` | Low | The documented `[diff]` defaults match `default.toml`. |
| 10 | D11 | `docs/cli.md` `status` section: add the leading `#` recency column to its column list. | `docs/cli.md` | Low | The `status` section lists the `#` column. |

## Deferred / out of scope (with reason)

| Finding ID | Rem. Risk | Axis | Reason | Later step |
|------------|-----------|------|--------|------------|
| (manifest.md duplicate `## pubrun_imports` heading) | — | — | Pre-dates this batch and is a structural nit, not a CLI/UX accuracy issue in scope of this assessment. Noting for a future docs pass. | Fix in a general docs cleanup. |

No finding is deferred on Remediation-Risk grounds — all fixes are documentation/help-string
edits at Low risk (D2's code option is a one-line forward, still Low).

## Scope check

- Over-scope: none. Not rewriting docs wholesale; surgical accuracy fixes. README stays a
  condensed index that links to `docs/cli.md` (Complexity axis — no per-command bloat).
- Under-scope: the README CLI section under-delivered relative to the shipped batch (D3–D6,
  D9); those gaps are filled concisely.

## Required tests / validation

Documentation + one small help-string/flag change (D1/D2); verification is against the code:
- `python -m pubrun bench -h` — `--passes` help no longer says "default 2"; if D2 exposes it,
  `--no-baseline` appears and a run forwards it to the harness.
- `python -m pubrun self-check -h` / `diff -h` / `bench -h` / `res -h` — every flag shown is
  reflected in README (by name) and in `docs/cli.md`.
- `grep` the README for each real command (20) — all present by canonical name (unchanged).
- `docs/configuration.md` `[diff]` defaults match `default.toml` (diff the lists).
- If D2 adds a flag: a test that `pubrun bench --no-baseline` forwards `--no-baseline` to the
  harness argv (extend `tests/test_bench_command.py`); full suite green (clear `__pycache__`).
- Re-run `/assess documentation` after execution to confirm the drift is closed.

## Spec / documentation sync

This plan **is** the doc sync. The only product change is D1/D2 (a help string, and possibly a
`--no-baseline` passthrough) — if D2 exposes the flag, note it in `docs/cli.md` bench options
and keep the CHANGELOG line; otherwise amend the CHANGELOG line. The external
`pubrun-benchmarks` repo README is already updated (schema/4) — no action here.

## Open questions

1. **D2 — RESOLVED (maintainer 2026-07-08):** EXPOSE `--no-baseline` on `pubrun bench` and
   forward it to the harness (consistent with how `--quick`/`--rigorous` are forwarded), making
   the CHANGELOG line true and giving users a real skip toggle. Keep the CHANGELOG text
   as-written. Add a test that `pubrun bench --no-baseline` forwards `--no-baseline` to the
   harness argv, and document the flag in `docs/cli.md`'s bench options.
2. **D8 — RESOLVED (maintainer 2026-07-08):** use a concise per-level PROSE description of what
   each depth hides (basic hides the most: volatile fields + high-volume sections
   subprocesses/packages/environment + per-run paths; standard hides less; deep hides nothing),
   and point at `default.toml` as the authoritative full list. Do NOT inline the verbatim
   arrays (bloat + re-drift risk).

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution, and it is
NOT auto-executed. Recommended next steps:

1. Review this IPD (optionally run `plan-review`).
2. On approval, execute the ordered changes, run the validation, and re-run
   `/assess documentation`.
3. Only then move this IPD from `.agents/plans/pending/` to `.agents/plans/executed/`.
