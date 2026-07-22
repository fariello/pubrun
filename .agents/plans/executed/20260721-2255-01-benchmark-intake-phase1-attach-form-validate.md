# IPD: Benchmark intake Phase 1 (attach-a-file client + Issue Form + validate-only Action)

- Date: 2026-07-21
- Concern: feature / usability / security (community benchmark submission, low-risk first slice)
- Scope: `src/pubrun/__main__.py` (bench client UX: paste -> attach), a new `.github/ISSUE_TEMPLATE/benchmark-result.yml`, a new VALIDATE-ONLY GitHub Actions workflow + a first-party validator script + adversarial fixtures, and a shared share-safety checker reused by client and Action. NO writes to any data branch, NO archival, NO repo-settings changes. Docs/CHANGELOG.
- Status: executed
- Approval: human-approved 2026-07-21 (maintainer "GO" after /plan-review); executed 2026-07-22 after a
  full CI matrix pass (21/21 green, run 29922109354); labels/settings remain human actions
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Set: benchmark-intake
- Order: 1

## Parent / set

Child of the approved orchestrator `.agents/plans/pending/20260721-2002-00-benchmark-intake-redesign.md`
(`Set: benchmark-intake`). This is Phase 1: the "if you do only one thing" slice from the research
(`.agents/docs/research/20260720-1422-01-benchmark-intake-options-and-recommendation.md`). It is the
lowest-risk, highest-value phase and grants the Action NO write permission. Phase 2 (data branch +
archival) and Phase 3 (docs/JOSS + retire satellite) are separate child IPDs, gated later; the HARD
`/assess security` gate in the orchestrator applies BEFORE Phase 2, not here (Phase 1 is validate-only).

## Goal

Stop pasting benchmark JSON into a GitHub issue body (which hits GitHub's ~65 KB cap and is brittle;
`src/pubrun/__main__.py:1224` `_bench_issue_body` fences the whole redacted file into the body). Instead:
a contributor runs `pubrun bench`, gets an unmistakable safe-file printout and a link to a main-repo
Issue Form, attaches the `.redacted.json` file, checks a privacy box, and submits. A validate-only Action
posts a pass/fail receipt (schema v5 + share-safety + semantic checks). No archival yet.

### Honest trade-off this phase introduces (review finding, recorded)

The SCRIPT is not ambiguous about which file to share: the harness already writes two distinctly-named
files, a `*.unredacted.json` (embeds the real hostname; local analysis only) and a de-hostnamed
`pubrun-bench-<hashtoken>-<stamp>.redacted.json` (`benchmarks/harness.py:490-513`). The OLD paste flow had
ZERO file-selection risk because the script generated the issue body from the redacted file itself; the
human never picked a file. The NEW attach flow ADDS a human file-picker step (drag a file into GitHub),
which is where "wrong file" risk is born, and because a public GitHub attachment uploads IMMEDIATELY
(before the Action validates), a wrong pick has already leaked. Therefore the LOCAL mitigations are the
real privacy defense, not the server validator (which is only a backstop that cannot un-leak an early
upload). Consequently `--prepare-submission` is PROMOTED to the primary, default-surfaced path (copy only
the redacted file into a clean `pubrun-share/` dir so the folder the human browses contains only the safe
file), and the end-of-run block leads the user there. This is the deliberate cost of the attach flow
(traded for size/UX and JOSS visibility); it is accepted, with these mitigations, per human decision
2026-07-21.

## Project conventions discovered (Step 0)

- Current client: `_BENCH_SUBMIT_URL` -> satellite repo (`__main__.py:1028`); `_bench_issue_body` embeds
  the redacted JSON in the issue body (`:1224`); `_submit_via_gh` posts via `gh` (`:1246`); submit flags
  `--submit`/`--submit-file`/`--submit-method` (`:2244-2255`); `_run_bench` orchestrates (`:1420`).
- Reuse: the `/5` schema (`schemas/benchmark.schema.json`) + its conformance test; redaction
  (`src/pubrun/capture/redaction.py`); the sanitizer's share-safety patterns (`scripts/sanitize_paths.py`).
- Stack: zero-runtime-dependency wheel. The validator + any JSON-schema check are DEV/CI/repo-automation
  only, never a runtime import of the installed package.
- House rules (`AGENTS.md`): no em/en dashes; path-scoped commits; never push without authorization;
  matrix-validation for CLI-grammar/behavior changes; every doc claim checkable.

## Design (Phase 1 only)

### Client (`pubrun bench`)

- Change `_BENCH_SUBMIT_URL` to the MAIN-repo Issue Form URL
  (`https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml`).
- Replace the paste path: STOP embedding the JSON in an issue body. `_bench_issue_body` is removed or
  reduced to a short human note WITHOUT the JSON fence; the `gh`/http auto-post of a body-embedded result
  is retired for the community path (keep `--submit-file` as the "which file to attach" helper).
- Print an unmistakable end block (per the research):
  ```
  PRIVATE, DO NOT SHARE:  <path>.unredacted.json
  SAFE TO SUBMIT:         <path>.redacted.json
  Share check:            PASSED|FAILED
  Submit (attach the SAFE file): <issue-form URL>
  ```
- Run the shared share-safety check on the redacted file before printing PASSED.
- `pubrun bench --prepare-submission` (INCLUDED in Phase 1, OQ1 resolved; primary file-pick mitigation):
  copy ONLY the checked redacted file into a clean `pubrun-share/` dir (stdlib only). The end-of-run
  block points the user at that dir so the folder they browse to attach contains only the safe file.

### Issue Form (`.github/ISSUE_TEMPLATE/benchmark-result.yml`)

- Integrates with the EXISTING issue-template chooser: `.github/ISSUE_TEMPLATE/` already holds
  `config.yml` (`blank_issues_enabled: true`, Discussions `contact_links`) plus sibling forms
  (`bug.yml`, `feature.yml`, `support.yml`, ...). The new form follows the sibling convention: front-matter
  `name:`, a `title:` prefix (e.g. `"[BENCH]: "`), and `labels: ["type:benchmark-submission", "status:pending"]`.
  No `config.yml` change is required (do not disable blank issues); just add the new form file.
- Short instructions, a required attachment guidance area, a REQUIRED privacy-acknowledgment checkbox
  ("I attached the redacted file shown by pubrun and did not attach the unredacted file"), optional notes.
- Labels themselves are created by the human (cannot-do-unilaterally); the form only references them.

### Validate-only Action (`.github/workflows/benchmark-intake.yml` + a first-party validator)

- Trigger: `issues` (opened/edited) filtered to the benchmark template marker/label ONLY.
- Permissions: `contents: read`, `issues: write` (comment + label). NO `contents: write` in Phase 1.
- A FIRST-PARTY Python validator (repo-owned; reuses `schemas/benchmark.schema.json` + the shared
  share-safety checker) runs the ordered checks from the orchestrator's security section: submission-shape
  -> safe-download (one attachment, GitHub host allowlist, redirect/timeout/byte cap ~1 MiB, `.json`) ->
  JSON parse (data only) -> schema v5 -> share-safety -> semantic. Never interpolate contributor content
  into a shell; pass via files/env; never print the payload; pin any third-party action to a full commit SHA.
- Schema-v5 check is CONCRETE (PR-003): the `/5` schema (`schemas/benchmark.schema.json`) has
  `properties.schema = {const: "pubrun-benchmark/5"}` and `required = [schema, generated_utc, mode,
  iterations, warmup, passes, machine, scenario_defs, pass_results]`. The validator asserts
  `schema == "pubrun-benchmark/5"` and validates against the committed schema; semantic checks use the
  schema's own `required` fields (not an invented list) plus finite/nonnegative timings and a supported
  `pubrun_version`.
- Output: comment a pass receipt (`status:accepted` label) or specific repair instructions
  (`status:needs-fix`). NO archival, NO close automation in Phase 1 (manual accept, to tune false
  positives per the research's Phase 1 plan).

### Shared share-safety checker (corrected design; PR-002 / PR-004)

This is NEW validation logic, not a reuse of `src/pubrun/capture/redaction.py`. That module REDACTS
(produces redacted output); it does not VERIFY that a file is already share-safe. The checker is a
STRUCTURAL VALIDATOR that rejects a result unless privacy-sensitive fields already carry the expected
redaction marker:
- `machine.host.hostname` (and other known host/user fields) MUST equal `<redacted>`; reject any value
  that is not the marker.
- Reject any absolute home/user path anywhere in the document (`/home/<x>/`, `/Users/<x>/`,
  `C:\\Users\\<x>\\`) and any forbidden key/representation.
- It MAY reuse the sanitizer's regex PATTERNS (`scripts/sanitize_paths.py`: home-path/IP shapes) for
  detection, but MUST NOT reuse its live-hostname AUTO-DETECTION: server-side the CI runner is a different
  machine, so comparing to a live hostname is meaningless. The check is structural (is-it-redacted),
  not identity-based (does-it-match-this-host).
- ONE versioned module, imported by both the local client (pre-share gate) and the Action validator, so
  they stay in lockstep; the version is recorded with any accepted result.

NOTE (maintainer, 2026-07-21): agent-workflows will soon ship a commit-hook + optional CI that performs
share-safety/path-hostname scrubbing of this kind repo-wide (cf. the executed sanitizer IPD
`20260720-2331-01`). Where that lands, this checker should PREFER adopting/reusing the canonical
agent-workflows implementation over maintaining a private fork, keeping only benchmark-result-specific
rules (e.g. the `machine.host.hostname == <redacted>` structural assertion) local. Track that overlap so
the two do not diverge.

## Findings (drivers)

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| P1-1 | High | Low | Contributor | intake usability | Paste-in-body hits the ~65 KB cap and is brittle; attach removes it | `__main__.py:1224,1028`; research Option 1 |
| P1-2 | High | Medium | Security | untrusted parsing (read-only) | Even validate-only, the Action parses attacker-controlled attachments; must obey the injection/host/byte-cap rules | orchestrator security section |
| P1-3 | Medium | Low | Privacy | share-safety parity | Local and server checks must share ONE versioned rule set; local redaction is the boundary | orchestrator B4 |
| P1-4 | High | Low | Security/QA | adversarial coverage | The validator needs a committed adversarial fixture corpus (accept 1 valid; reject unredacted/oversized/0-or-many-attachments/wrong-schema/tampered/injection) | orchestrator B5 |
| P1-5 | Medium | Low | Security/UX | new file-pick risk | The attach flow ADDS a human file-selection step the paste flow lacked, and a public attachment uploads before validation; local mitigation (`--prepare-submission` + unmistakable naming/printout), not the server backstop, is the real defense | `harness.py:490-513`; /plan-review 2026-07-21 |
| P1-6 | Medium | Low | Security/Arch | checker design | The share-safety checker must be a NEW structural is-it-redacted validator (not `redaction.py` reuse; not live-hostname detection, which is meaningless on the CI runner) | `redaction.py:46-185`; `sanitize_paths.py` |
| P1-7 | Low | Low | Architecture | issue-form integration | The new form must fit the EXISTING `.github/ISSUE_TEMPLATE/config.yml` chooser + sibling-form convention | `.github/ISSUE_TEMPLATE/config.yml`, `bug.yml` |

## Proposed changes (ordered, validatable)

| Step | Src | Change | Files | Remediation Risk | Validation |
|------|-----|--------|-------|------------------|------------|
| 1 | P1-3 | Factor the shared, versioned share-safety checker (client + Action reuse it). | `src/pubrun/` (or a shared module) + reuse from `scripts/sanitize_paths.py` patterns | Low | unit tests: rejects absolute home/user/hostname; accepts a properly redacted `/5` result |
| 2 | P1-1 | Client: point at the main-repo Issue Form; remove JSON-in-body; print the unmistakable safe-file block; run the share check before PASSED. Optionally `--prepare-submission`. | `src/pubrun/__main__.py` | Low (usability) | client unit tests for the printout + share-check gating; no JSON embedded in any issue body path |
| 3 | P1-1 | Add `.github/ISSUE_TEMPLATE/benchmark-result.yml` (instructions, required attachment + privacy checkbox, default labels). | `.github/ISSUE_TEMPLATE/benchmark-result.yml` | Low | form parses (valid issue-form YAML); required fields present |
| 4 | P1-2,P1-4 | Add the first-party validator script + adversarial fixtures. | `.github/` scripts + `tests/` or `benchmarks/` fixtures | Medium (security-sensitive parser) | validator unit-tested against the fixture corpus: 1 accept, all adversarial rejects; no contributor string reaches a shell; byte cap + host allowlist enforced |
| 5 | P1-2 | Add the VALIDATE-ONLY workflow (`issues` trigger, marker-gated, `contents:read`+`issues:write`, no writes) that runs the validator and comments a receipt. | `.github/workflows/benchmark-intake.yml` | Medium | dry-run/logic test from fixtures; workflow lints; permissions are read + issues:write only (assert no contents:write) |
| 6 | P1-1 | Docs + CHANGELOG: a short "contribute a benchmark" note (attach, do not paste) in README/CONTRIBUTING; CHANGELOG entry. | `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | Low | links resolve; dash-clean per house rule |

## Deferred / out of scope (Phase 1)

| Item | Reason |
|------|--------|
| Archival to a `benchmark-data` branch, dedupe, aggregation, auto-close | Phase 2 (separate child IPD); requires `contents:write` and the HARD security gate first |
| Retiring `pubrun-benchmarks`, migrating issue #1 | Phase 3 (separate child IPD) |
| Discussions/Gist/PR intake variants | Deferred in the orchestrator |

## Cannot-do-unilaterally (human / gated)

- Create the labels (`type:benchmark-submission`, `status:pending`, `status:accepted`, `status:needs-fix`),
  enable the Issue Form, and any push. The agent writes the in-repo files (client, form yaml, workflow
  yaml, validator, fixtures, docs); the human creates labels/settings and authorizes the push.
- The workflow will not actually run against real issues until it is on the default branch (pushed) and
  labels exist; until then it is validated by fixture-based unit tests.

## Required tests / validation

- Shared checker + client: unit tests (Step 1, 2).
- Validator: the committed adversarial fixture corpus (P1-4) is a REQUIRED deliverable; unit-tested with
  no live issue needed.
- Security asserts: no contributor-controlled string reaches a shell; one-attachment + host allowlist +
  byte cap enforced; workflow permissions are `contents:read`+`issues:write` only (no write).
- Matrix-validation: the `pubrun bench` client change is a CLI/behavior change, so it is NOT done on local
  green alone; push and validate on the full CI matrix before this child IPD moves to executed/.
- Honesty rule: paste ACTUAL test/CI output; never claim green unrun.

## Spec / documentation sync

- README "Contribute a benchmark" pointer + CONTRIBUTING note (attach, do not paste); CHANGELOG entry.
  Keep pubrun framed as a provenance component; no overclaim about what the corpus proves.

## Open questions (all RESOLVED during /plan-review 2026-07-21)

1. `--prepare-submission`: RESOLVED - INCLUDE in Phase 1 and PROMOTE it to the primary file-pick
   mitigation (see the trade-off note); it directly reduces the wrong-file risk the attach flow adds.
2. Checker location: RESOLVED - a dev/repo module reused by both the client submission path and the
   Action; NOT imported at `import pubrun` time (preserve the zero-runtime-dependency installed surface).
3. Form URL + labels: RESOLVED - form URL
   `github.com/fariello/pubrun/issues/new?template=benchmark-result.yml`; labels
   `type:benchmark-submission` + `status:{pending,accepted,needs-fix}` (matching the sibling-form
   convention). Label creation stays a human/settings action.

## Approval and execution gate

Proposal; MUST be human-approved before execution; NOT auto-run. Execution contract:
- Open questions resolved (or explicitly OPEN -> NO-GO).
- Scope fence: ONLY `src/pubrun/__main__.py` (+ the shared checker module), `.github/ISSUE_TEMPLATE/benchmark-result.yml`,
  `.github/workflows/benchmark-intake.yml` + validator script, the fixture corpus, and README/CONTRIBUTING/
  CHANGELOG. NO data-branch writes, NO `contents:write` in the workflow, NO repo-settings/label creation
  by the agent, NO retiring of the satellite repo. Anything beyond -> STOP and report.
- Security: the workflow is an Internet-facing parser even validate-only; obey the injection/host/byte-cap
  rules. (Full `/assess security` is the HARD gate before Phase 2's write access, not this phase.)
- Honesty rule (hard MUST): paste actual test + CI-matrix output; never claim green unrun.
- Commits path-scoped; never push without explicit authorization.
- Lifecycle: on completion + approval + matrix-green, `git mv` this child IPD to `.agents/plans/executed/`
  (Status -> executed) with a Workflow-history line; record the phase in the orchestrator's history.

## Workflow history
- 2026-07-21 drafted (opencode / its_direct/pt3-claude-opus-4.8-1m-us): Phase 1 child of the approved
  orchestrator `20260721-2002-00` (`Set: benchmark-intake`, `Order: 1`). Lowest-risk slice: client
  paste -> attach, main-repo Issue Form, a validate-only (no-write) Action with a first-party validator +
  adversarial fixtures, and a shared share-safety checker. Not executed; awaiting review/approval.
- 2026-07-21 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS
  APPLIED. Verified cited code (paste-embed `_bench_issue_body` :1224; `_submit_via_gh` :1246; submit flags
  :2244-2255; `/5` schema marker `const "pubrun-benchmark/5"`; distinct `.unredacted`/`.redacted` naming
  `harness.py:490-513`; existing ISSUE_TEMPLATE chooser). Findings PR-001..PR-004 FIXED (recorded as
  P1-5..P1-7 + edits): reframed the file-pick risk as one the attach flow ADDS (not a script bug) and
  promoted `--prepare-submission` to the primary local mitigation (human decision); CORRECTED the
  share-safety checker to a NEW structural is-it-redacted validator (not `redaction.py` reuse; not
  live-hostname detection); integrated the new Issue Form with the existing chooser/sibling convention;
  pinned the exact schema-v5 marker. Recorded the maintainer note that agent-workflows will soon ship an
  overlapping commit-hook/CI to prefer over a private fork. All 3 open questions resolved. Status ->
  reviewed. Readiness: GO - PENDING HUMAN APPROVAL.
- 2026-07-22 executed (opencode / its_direct/pt3-claude-opus-4.8-1m-us): completed the Phase 1 remainder
  on top of the security core (`ee54e0e`). Step 2 client (attach flow; retired the auto-post chain and the
  `--submit-method`/`--gh-token`/`--print-submission` flags; safe-file block; `--prepare-submission`;
  repointed to the main-repo Issue Form). Step 3 Issue Form `.github/ISSUE_TEMPLATE/benchmark-result.yml`.
  Step 5 validate-only workflow `.github/workflows/benchmark-intake.yml` (contents:read + issues:write, no
  writes) plus `extract_attachment_url.py`. Step 6 docs (README/CONTRIBUTING/CHANGELOG). Two commits:
  `ee54e0e` (core) + `7b81f71` (remainder). Full local suite 983 passed / 7 skipped; full CI matrix 21/21
  green (run 29922109354). Labels (type:benchmark-submission, status:{pending,accepted,needs-fix}) and the
  Issue Form enablement remain human/settings actions; the workflow does not fire on real issues until
  those exist. Status -> executed; moved to executed/. Phase 2 (data branch + archival) needs its own
  child IPD AND a HARD /assess security gate before the Action gets any write permission.
