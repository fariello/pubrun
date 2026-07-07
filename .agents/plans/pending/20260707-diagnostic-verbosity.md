# IPD-D: verbose, transparent `self-check` and `meta` output

- Date: 2026-07-07
- Concern: usability. `pubrun self-check` prints only a one-line verdict ("no concerns found."
  or "N concern(s): …") — it never shows *what was checked*, how long it took, or the outcome
  of each check. A bare "everything OK" is a poor experience for a diagnostic command.
  `pubrun meta` is similarly terse (2 status lines + a 4-line brief). Both should, by default
  or via a verbose flag, show the checks/steps performed and their outcomes.
- Scope: `src/pubrun/__main__.py` (`_run_self_check` `:779`, `_emit_findings` `:754`,
  `_run_meta` `:683`), `src/pubrun/report/checks.py` (`live_findings`/`summarize`),
  `src/pubrun/report/meta_snapshot.py`. Docs, tests. Read-only diagnostics; no runtime change.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Turn `self-check` and `meta` into transparent diagnostics that show the checks/steps run,
their pass/warn/info outcome, and timing — so "OK" is *earned and visible*, not a black box.

## Project conventions discovered (Step 0)

- `_run_self_check`: no findings → `pubrun self-check: no concerns found.` (`__main__.py:761`);
  findings → one summary line (`summarize()`, `checks.py:367-374`, ≤4 codes) + a nudge;
  `--show-suggestions` → one line per FINDING only. **Passing checks are silent** — there is
  no enumeration of what was checked, no timing, no per-check OK.
- The checks themselves live as separate functions in `checks.py` (`_network_fs_findings`,
  `_install_health_findings`, `_live_fs_health_findings`, `_hpc_login_node_findings`, memory/
  load checks). They currently only APPEND findings for problems; a "check ran and passed"
  has no representation.
- `meta`: writes JSON; prints `[*] Analyzing…`, `[OK] saved to …`, and a 4-line brief
  (`meta_snapshot.py:19,58,61-72`). (Prefixes will be normalized by IPD-B.)
- Principle: honest, self-documenting output; accessibility (non-DIM color).

## Findings

| ID | Severity | Rem. Risk | Persona | Area | Finding | Evidence |
|----|----------|-----------|---------|------|---------|----------|
| D1 | Medium | Low | novice/eng | Usability | `self-check` shows no list of checks performed, no per-check outcome, no timing — only a verdict. | `__main__.py:761-776`; `checks.py:367` |
| D2 | Low | Low | eng | Transparency | Checks model only records PROBLEMS; a passed check is invisible (can't show "✓ output dir writable"). | `checks.py` (findings-only) |
| D3 | Low | Low | novice | Usability | `meta` console output is terse (2 lines + 4-line brief); doesn't show what was gathered or timing. | `meta_snapshot.py:19,58,61-72` |

## Proposed changes (ordered, validatable)

| Step | Findings | Change | Files | Rem. Risk | Validation |
|------|----------|--------|-------|-----------|------------|
| 1 | D2 | Extend the checks model so each check reports an OUTCOME (`ok`/`info`/`warn`) with a short label, not only problems. Introduce a lightweight "check ran" record (name + status + optional detail) that `live_findings` accumulates alongside the existing findings. Keep `--json` emitting the full structured result. | `checks.py` | Low | `live_findings`-equivalent returns both the passed-check records and the findings; existing finding behavior unchanged; `--strict` still keys on WARN only. |
| 2 | D1 | Make `self-check` output enumerate each check with a normalized prefix (IPD-B): `[ OK  ] output directory writable`, `[ OK  ] $TMPDIR is local (ext4)`, `[WARN ] pubrun installed on NFS → …`, plus a final summary line and **total time taken**. Default becomes this itemized view (not just the verdict); keep a `--quiet`/`-q` for the old one-line summary, and `--show-suggestions` still expands remediation detail. `--json` unchanged (now includes the passed checks). | `__main__.py`, `checks.py` | Low | `self-check` on a healthy machine lists each check as `[ OK  ]` + a timing line; on a problem machine mixes `[ OK  ]`/`[WARN ]`; `--quiet` prints the single verdict; `--json` parses and includes passed checks. |
| 3 | D3 | Make `meta` verbose in the same spirit: itemize what was gathered (`[ OK  ] packages: N recorded`, `[ OK  ] git: <commit>`, `[ OK  ] hardware: <cpu>`, `[ OK  ] python: <ver>`, `[WARN ]` on any capture_state != complete), the output path, and total time. Keep the JSON file as the source of truth. | `meta_snapshot.py`, `__main__.py` | Low | `meta` lists each gathered section with an outcome + timing; a section that failed to capture shows `[WARN ]`; the JSON file still written. |
| 4 | D1,D3 | Add an elapsed-time measurement around the check/gather phases and print it (`Checked N items in 0.3s`). | `__main__.py`, `meta_snapshot.py` | Low | Timing line present and plausible; no measurable overhead added to the checks themselves. |

## Deferred / out of scope (with reason)

None deferred on risk (all Low, output-only). Depends on IPD-B for the normalized prefixes;
if IPD-B has not landed, this IPD uses the same canonical prefixes and IPD-B's migration
subsumes them (sequence D after B, or share the helper).

## Scope check

- Over-scope: not turning self-check into a full linter; it enumerates the checks it already
  runs. Not adding new checks here (those belong to their own IPDs).
- Under-scope: the "show what passed + timing" transparency was missing; added.

## Required tests / validation

- Checks model: a passed check produces an `ok` record; a problem produces a `warn` finding;
  `--json` includes both; `--strict` exit code still keys on WARN only (unchanged).
- self-check default: itemized `[ OK  ]`/`[WARN ]` lines + timing; `--quiet` → single verdict.
- meta: itemized gather outcomes + timing; JSON still written; failed section → `[WARN ]`.
- No new network/subprocess/statvfs on the import path (unaffected; these are CLI commands).
- Full suite green; update existing self-check tests that assert the old one-line default
  (intentional output change; `--quiet` preserves the terse form for any script relying on it).

## Spec / documentation sync

`docs/cli.md` (`self-check` new default + `--quiet`; `meta` verbose output), `CHANGELOG.md`.

## Open questions

1. Default verbosity: make itemized the DEFAULT (my lean, per your request) with `--quiet` for
   the old one-liner, or keep terse default and add `--verbose`? (Leaning: itemized default +
   `--quiet`, since you said "just OK is not good UX".)
2. Show passed checks always, or only with `--show-suggestions`? (Leaning: always show the
   one-line-per-check outcomes; `--show-suggestions` adds the remediation detail underneath.)
3. Timing granularity: total only, or per-check? (Leaning: total + per-check only in `--json`.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. Recommended: `plan-review`.
On completion move to `.agents/plans/executed/`. Sequence AFTER IPD-B (shared prefixes).
