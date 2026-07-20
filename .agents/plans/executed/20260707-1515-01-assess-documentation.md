# IPD: Assess documentation — README/CLI drift after the 1.4.0 command & feature changes

- Date: 2026-07-07
- Concern: documentation (accuracy-first)
- Scope: whole project docs, emphasis on `README.md`, `docs/cli.md`, `CHANGELOG.md` nav.
  Triggered by the doc-sync discipline in `AGENTS.md` after this session's user-visible
  changes (command rename, `res` comprehensive, file-I/O levels, benchmark submission,
  schema/4, env-kind, fs-health).
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Make every user-facing doc describe what `pubrun` actually does **today**. The library's
CLI grew from ~13–14 commands to **20** and renamed/added several (`bug-report` →
`report-bug` + `feedback`; `report` → `show`; `resources` → `res`/`cpu`/`mem`; new `init`,
`self-check`, `inspect`, `bench`, `cite`), and several roadmap "future" items have shipped.
The top-level `README.md` — the first thing a new user and PyPI visitor reads — still
advertises the old command names, an undercount, a nonexistent command, and lists shipped
features as "future". This is the highest-harm class of doc defect (accuracy), because it
makes a user type commands that error and misrepresents the project's maturity. This plan
fixes the inaccuracies first, then closes completeness gaps, without bloating the docs.

## Project conventions discovered (Step 0)

- Guiding principles: `AGENTS.md` (doc-sync discipline; honest docs), README "Principles"
  framing (KISS, zero-dep, honest). Universal fallback also applies.
- Pending-plans location/format: `.agents/plans/pending/` → `.agents/plans/executed/`,
  dated IPDs. This IPD uses the assess naming `YYYY-MM-DD-assess-<concern>.md`.
- Contributor/spec-sync contract: `AGENTS.md` — "After any session that changes
  user-visible behavior … run `/assess documentation`." (This is that run.)
- Stack/context: zero-dependency Python library + CLI; docs are Markdown under `docs/`,
  `README.md`, `CHANGELOG.md`. `docs/cli.md` is the exhaustive CLI reference; README has a
  condensed CLI section. Real command list verified via `python -m pubrun -h` (20 commands:
  `init, report-bug, feedback, cite, self-check, inspect, bench, clean, combined, cpu, diff,
  mem, meta, methods, rerun, res, run, show, status, ui`). `report` and `resources` exist
  only as HIDDEN dispatch aliases (`__main__.py:2068,2225`), not registered subparsers.

## Findings

Severity = impact if left alone; Remediation Risk = Fix-Bar gate. Persona: N=novice,
E=engineer/operator.

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| D1 | High | Low | N,E | Accuracy | README claims "fourteen commands"; there are 20. | `README.md:166` vs `python -m pubrun -h` (20 registered) |
| D2 | High | Low | N,E | Accuracy | `docs/cli.md` claims "thirteen commands" — wrong and self-contradictory (its own body documents 20). | `docs/cli.md:5` |
| D3 | High | Low | N,E | Accuracy | README documents `pubrun bug-report` (with a full `###` section) — that command was removed; it is now `report-bug` + a separate `feedback`. A user running `bug-report` gets an error. | `README.md:168-172` vs `__main__.py:1854,1860`; `docs/cli.md:47` already notes the rename |
| D4 | Medium | Low | N,E | Accuracy | README documents `pubrun report` as the primary viewer; the canonical registered command is `show` (`report` is a hidden back-compat alias). README never mentions `show`. | `README.md:213-217` vs `__main__.py:2121,2068`; `docs/cli.md:355` |
| D5 | Medium | Low | N,E | Accuracy | README documents `pubrun resources`; the canonical commands are `res`/`cpu`/`mem` (`resources` is a hidden alias). README mentions none of the three real names. | `README.md:225-229` vs `__main__.py:2096,2225`; `docs/cli.md:394,427,437` |
| D6 | High | Low | N,E | Accuracy | Roadmap "Future" lists `pubrun combined` as unbuilt — it ships (and is documented elsewhere in the same README at line 189). | `README.md:385` vs `README.md:189`, `__main__.py:1963`, `docs/cli.md:245` |
| D7 | High | Low | N,E | Accuracy | Roadmap "Future" lists "Timestamped console capture" as unbuilt — it ships (README line 34 relies on it). | `README.md:384` vs `capture/console.py:223`, `README.md:34` |
| D8 | Medium | Low | E | Accuracy | Roadmap "Future" lists "GitHub Actions CI" as unbuilt — it ships. | `README.md:380` vs `.github/workflows/ci.yml` |
| D9 | Medium | Low | N | Completeness | README CLI section omits shipped commands: `init`, `self-check`, `inspect`, `bench`, `report-bug`, `feedback`, and the canonical `show`/`res`/`cpu`/`mem`. | `README.md:164-265` vs `-h` |
| D10 | Medium | Low | N | Consistency | Two separate top-level License sections. | `README.md:416-418` & `427-446` |
| D11 | Medium | Low | N | Consistency | Two different suggested-citation strings for the same software (differing author format, title, DOI presence). | `README.md:395` & `443` |
| D12 | Medium | Low | E | Navigation | CHANGELOG nav (header + footer) omits `Performance` and `HPC` links that exist and are linked from README. | `CHANGELOG.md:1,542` vs `docs/performance.md`, `docs/hpc.md` |
| D13 | Low | Low | N | Consistency | README footer nav sits mid-document (before the License/Attribution section), not at the end. | `README.md:422` |
| D14 | Low | Low | E | Navigation | `docs/design/file-io-provenance-evaluation.md` is not in any nav (likely intentional internal design note). | `docs/design/…` |

Verified-accurate (no action): README nav links all resolve; `docs/cli.md` nav complete;
roadmap items 1/3/4/5 (Sphinx, plugin model, `register_artifact`, `register_metadata`) are
genuinely unimplemented (`grep` found no such symbols) and correctly listed as future;
`docs/configuration.md` correctly documents `[capture.file_io].level = "stat"` default,
`[capture.resources].system_metrics`, and (correctly) has NO `[capture.filesystem]` key
(the live probe is CLI/diagnostic-only by design).

## Proposed changes (ordered, validatable)

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|--------------------|--------|-------|------------------|------------|
| 1 | D1, D2 | Replace the brittle hard-coded count with a non-brittle phrasing ("a family of subcommands" / "twenty-plus commands") in both places, OR state the exact current count (20) — prefer non-brittle so it does not re-drift. | `README.md:166`, `docs/cli.md:5` | Low | Grep shows no "fourteen"/"thirteen commands"; phrasing does not name a number that can go stale (or names 20 and matches `-h`). |
| 2 | D3 | Remove the `### pubrun bug-report` section; replace with `### pubrun report-bug` and `### pubrun feedback` (mirroring `docs/cli.md`). | `README.md:168-172` | Low | `pubrun report-bug -h` and `pubrun feedback -h` succeed; README no longer mentions `bug-report`. |
| 3 | D4 | Retitle the README `### pubrun report` section to `### pubrun show` (note `report` as a backward-compatible alias), matching `docs/cli.md:355`. | `README.md:213-217` | Low | `-h` shows `show`; README documents `show` and notes the alias. |
| 4 | D5 | Replace the README `### pubrun resources` section with `res`/`cpu`/`mem` (note `resources` as a hidden alias). Keep it concise; link to `docs/cli.md` for depth. | `README.md:225-229` | Low | `-h` shows `res`/`cpu`/`mem`; README documents them. |
| 5 | D6, D7, D8 | In the Roadmap, remove the three shipped items (`combined`, timestamped capture, GitHub Actions CI) — or move them to a short "Recently shipped" note. Keep only genuinely-future items (Sphinx/MkDocs, plugin model, `register_artifact`, `register_metadata`). | `README.md:375-385` | Low | No shipped feature remains under "Future"; grep confirms `register_artifact`/`register_metadata` still absent (still legitimately future). |
| 6 | D9 | Add brief README CLI entries for `init`, `self-check`, `inspect`, `bench` (1–3 lines each, linking to `docs/cli.md`), and ensure `report-bug`/`feedback`/`show`/`res`/`cpu`/`mem` from steps 2–4 are present. Do NOT duplicate the full `docs/cli.md`; README stays a condensed index. | `README.md:164-265` | Low | Every command in `-h` appears (by canonical name) in the README CLI section or is explicitly deferred to `docs/cli.md`. |
| 7 | D10, D11 | Consolidate to a single License section and a single Citation block (keep the fuller "License, Attribution & Citation" wording; delete the earlier duplicates). Use ONE suggested-citation string consistent with `CITATION.cff` and `pubrun cite`. | `README.md:389-446` | Low | Exactly one `## License…` and one citation string; it matches `CITATION.cff`/`pubrun cite` output. |
| 8 | D12 | Add `Performance` and `HPC` links to the CHANGELOG nav header and footer to match the README/`docs/cli.md` nav. | `CHANGELOG.md:1,542` | Low | CHANGELOG nav lists the same docs as README nav; all resolve. |
| 9 | D13 | Move the README footer nav to the true end of the file (after the License/Attribution section). | `README.md:422` | Low | Footer nav is the last content block. |

## Deferred / out of scope (with reason)

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| D14 | — | — | Not deferred on risk; judged **intentional** (internal design note under `docs/design/`, not part of the user-facing index). No change proposed. | If a "Design notes" index is ever added, link it there. |

No finding is deferred on Remediation-Risk grounds — every fix is documentation-only and
Low risk. D14 is a no-op by judgment, not a deferral.

## Scope check

- Over-scope: none proposed. Explicitly avoiding (a) duplicating `docs/cli.md` into the
  README (README stays a condensed index — Complexity axis), and (b) auto-generating the
  command list (a build-step dependency the zero-dep project does not want).
- Under-scope: the README CLI section was materially incomplete (D9) and is filled in
  concisely.

## Required tests / validation

Documentation-only; no code/tests change. Validation is verification against the code:
- `python -m pubrun -h` — every listed command appears in the README CLI section by its
  canonical name; no removed command (`bug-report`) is documented.
- `pubrun report-bug -h`, `pubrun feedback -h`, `pubrun show -h`, `pubrun res -h` succeed.
- `grep -n "fourteen\|thirteen commands\|bug-report" README.md docs/cli.md` returns nothing.
- Roadmap contains no shipped feature; `grep register_artifact register_metadata src/` still
  empty (confirms those remain legitimately future).
- Every nav link in `README.md` and `CHANGELOG.md` resolves to a real `docs/*.md`; the two
  navs list the same doc set.
- Exactly one License section and one citation string; the citation matches `CITATION.cff`.
- Re-run `/assess documentation` after execution to confirm the drift is closed.

## Spec / documentation sync

This plan **is** the documentation sync. No product behavior changes. The docs are being
brought in line with already-shipped behavior; no `docs/cli.md` command *body* is wrong
(it is the README and the counts/nav that drifted), so the edits are concentrated in
`README.md` and `CHANGELOG.md` with the two count fixes in `docs/cli.md`.

## Open questions

1. **Count phrasing (D1/D2):** prefer non-brittle ("a family of subcommands"/"twenty-plus")
   or state the exact number (20)? (Assumption: non-brittle, to avoid re-drift; confirm.)
2. **Roadmap shipped items (D6–D8):** delete outright, or keep as a short "Recently shipped
   (see CHANGELOG)" note? (Assumption: a one-line "shipped" note is friendlier than silent
   deletion; confirm.)
3. **README CLI depth (D9):** confirm README should stay a *condensed* index that links to
   `docs/cli.md` rather than growing a full per-command reference (Complexity axis).

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution, and it
is NOT auto-executed. Recommended next steps:

1. Review this IPD (optionally run the `plan-review` workflow to harden it).
2. On approval, execute the ordered changes, run the validation, and re-run
   `/assess documentation`.
3. Only then move this IPD from `.agents/plans/pending/` to `.agents/plans/executed/`.

## Execution record (2026-07-07)

Executed by opencode after human approval. All 9 proposed steps applied; open questions
resolved with the plan's stated assumptions (all Low risk, maintainer-approved as leanings):
non-brittle count phrasing; a one-line "Recently shipped" note (not silent deletion); README
kept a condensed index linking to `docs/cli.md`.

- **Step 1 (D1/D2):** replaced "fourteen commands" (README) / "thirteen commands"
  (`docs/cli.md`) with non-brittle "a family of subcommands" + a pointer to `pubrun -h`.
- **Step 2 (D3):** removed the `### pubrun bug-report` section; added `### pubrun report-bug /
  pubrun feedback`. (The `docs/cli.md:47` "Changed in 1.4.0…" note that still says
  "bug-report" is intentional — it documents the rename, not a live command.)
- **Step 3 (D4):** README section retitled `### pubrun show`, noting `report` as a
  backward-compatible alias.
- **Step 4 (D5):** README `resources` section replaced with `### pubrun res / cpu / mem`
  (comprehensive vs single-metric), noting `resources` as an alias of `res`.
- **Step 5 (D6/D7/D8):** removed the three shipped items from Roadmap "Future" (combined,
  timestamped capture, GitHub Actions CI); added a one-line "Recently shipped (see Changelog)"
  note. Remaining Future items (Sphinx/MkDocs, plugin model, `register_artifact`,
  `register_metadata`) verified still unimplemented (`grep` empty).
- **Step 6 (D9):** added concise README CLI entries for `init`, `self-check`, `inspect`,
  `bench` (plus the renamed `report-bug`/`feedback`/`show`/`res`/`cpu`/`mem`). Verified all 20
  `-h` commands now appear in the README CLI section by canonical name.
- **Step 7 (D10/D11):** consolidated to ONE `## License & Attribution` section (removed the
  duplicate standalone `## License`) and ONE citation string, aligned to `CITATION.cff`
  (`Fariello, Gabriele. (2026). pubrun [Computer software]. …`). The bottom section now
  cross-references the single `## Citation` block instead of repeating a second citation.
- **Step 8 (D12):** added `Performance` and `HPC` links to the CHANGELOG nav (header +
  footer), matching the README nav.
- **Step 9 (D13):** removed the mid-document footer-nav duplicate; the footer nav now sits at
  the true end of the README (after `## License & Attribution`).
- **D14:** no-op as planned (intentional internal design note).

**Validation:** `grep` confirms no "fourteen"/"thirteen commands" and no live `bug-report`
reference remains (only the rename note); all 20 `pubrun -h` commands appear in the README CLI
section; all README/CHANGELOG nav links resolve; exactly one License section and one citation
blockquote; `pubrun report-bug/show/res -h` succeed. Documentation-only; no code/tests
touched. Re-running `/assess documentation` should now find this drift closed.
