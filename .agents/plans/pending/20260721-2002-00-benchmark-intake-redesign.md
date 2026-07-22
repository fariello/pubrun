# IPD: Benchmark intake redesign (attach-a-file Issue Form + validating Action + data branch)

- Date: 2026-07-21
- Concern: feature / infrastructure / security (community benchmark submission mechanism) + JOSS readiness
- Scope: replace the paste-JSON-into-a-GitHub-issue submission flow with a GitHub Issue Form that takes
  a `.redacted.json` ATTACHMENT, validated by a GitHub Actions workflow, with accepted results archived
  to a dedicated `benchmark-data` branch and aggregates rebuilt; consolidate intake into the MAIN pubrun
  repo and retire `pubrun-benchmarks` as the primary destination. Phased (see below). Touches
  `pubrun bench` client UX (`src/pubrun/__main__.py`), `.github/`, docs, and repo/branch settings.
- Status: approved
- Approval: human-approved 2026-07-21 (maintainer "GO" on the APPROACH; each phase child IPD still
  separately reviewed + approved per this orchestrator's per-phase gate)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Set: benchmark-intake
- Order: 0

## Provenance and authority note

This IPD operationalizes external research the maintainer chose to pursue:
`.agents/docs/research/20260720-1422-01-benchmark-intake-options-and-recommendation.md` (options analysis
+ recommendation) and `.agents/docs/research/20260720-1406-01-benchmark-intake-research-prompt.md` (the
prompt that produced it). That research is INPUT, not authorization; this plan adopts its Option 1 +
Part B hybrid on the merits, and every consequential/irreversible action below is gated on explicit
human approval. Nothing here waives the standing never-push / never-force-push / human-approval rules.

## Goal

Let a contributor submit a benchmark result by running one command, clicking one link, attaching one
file, checking one privacy box, and submitting, with no JSON paste, no fork, no token, and no size-cap
problem. A GitHub Action validates schema and share-safety, dedupes, archives accepted results to a
`benchmark-data` branch, and rebuilds aggregates. Intake and conversation live in the MAIN repo (better
JOSS visibility, no cross-repo token), with accepted data isolated on a branch. This removes the current
~65 KB issue-body ceiling (`src/pubrun/__main__.py:1030,1044`) and the brittle paste UX, and supports
results far larger than today's.

## Project conventions discovered (Step 0)

- Current mechanism (to be replaced): `pubrun bench` points contributors at
  `_BENCH_SUBMIT_URL = "https://github.com/fariello/pubrun-benchmarks/issues/new"`
  (`src/pubrun/__main__.py:1028`) and embeds/points at the redacted JSON with a ~65 KB warning
  (`:1030-1046`, `_bench_issue_body` at `:1224`, `--submit-file` guidance at `:1354-1412`).
- Existing assets to reuse: the `/5` benchmark JSON schema (`schemas/benchmark.schema.json`) + its
  conformance test; the redaction/share-safety logic (harness redaction; the local `*.redacted.json`
  vs `*.unredacted.json` naming); the new `scripts/sanitize_paths.py` share-safety patterns.
- Stack: zero-runtime-dependency library. Any schema validator or submission automation MUST stay
  dev-only / CI-only / repository-automation, never a runtime dependency of the installed wheel.
- CI: `.github/workflows/` (ci.yml matrix, secret-scan.yml, dependency-audit.yml). New workflow lives
  here and must follow the same conventions.
- House rules (`AGENTS.md`): no em/en dashes in authored Markdown; path-scoped commits; never push
  without authorization; every doc claim checkable; matrix-validation for contract/CLI-grammar changes.

## Design (adopted from the research, on the merits)

Option 1 (Issue Form + JSON attachment + Actions ingestion) as the default, with the Part B hybrid
(main-repo intake, accepted data on a same-repo `benchmark-data` branch, retire `pubrun-benchmarks` as
primary). Discussions are the documented fallback if issue volume becomes noisy; the validator is built
with a thin event adapter so that move is cheap later.

### Security boundaries (HARD requirements; the Action is an Internet-facing parser)

Per the research's security section and GitHub's script-injection guidance, the ingestion workflow MUST:
- Trigger only on the exact benchmark template marker / label; never check out or execute contributor code.
- NEVER interpolate issue title/body/filename/JSON values into shell program text; pass via files/env only.
- Accept exactly one attachment from an allowlist of GitHub attachment hosts; enforce redirect count,
  final host, timeout, and a byte cap (start ~1 MiB); fail closed; require `.json` type/suffix.
- Parse JSON as data only (no eval/interpolation).
- Validate schema v5 AND run the SAME versioned share-safety checks as the local checker (reject absolute
  home paths, user-profile paths, unredacted hostname/username, forbidden keys/representations).
- Canonicalize + SHA-256; dedupe; write only to FIXED paths derived from the validated hex digest +
  numeric issue id, on the `benchmark-data` branch; serialize archive writes with a concurrency group.
- Split jobs by permission: validation `contents: read`; receipt `issues: write`; archive `contents: write`.
- **Validator is FIRST-PARTY (OQ4 resolved):** a repo-owned Python script reusing
  `schemas/benchmark.schema.json` (the `/5` schema) and the SAME versioned share-safety checker the local
  client uses (factored out per P1.4). Any unavoidable third-party action is pinned to a full commit SHA.
  This minimizes supply-chain surface and keeps local and server checks in lockstep.
- Never print the payload in Actions logs.
- Privacy is decided by LOCAL redaction: a public attachment uploads immediately and cannot be un-shared;
  server-side rejection is a backstop, not the boundary. The client UX must make the safe file unmistakable.

### Abuse and first-contributor handling (added during /plan-review; PR-002)

Because this is a public, issue-triggered, eventually write-capable surface:
- Account for GitHub's first-time-contributor workflow-approval behavior (a new account's issue-triggered
  workflow may require maintainer approval to run); document the expected contributor experience for that
  case rather than assuming instant automation.
- Anti-spam / abuse: gate substantive work behind the exact template marker/label; the validate-only
  Phase 1 posts a receipt but grants no write; junk or non-conforming issues are labeled `status:needs-fix`
  or closed, never archived. Consider a simple per-issue idempotency (one accepted digest per issue) and
  rely on GitHub's native rate limiting; do not build a bespoke rate limiter.
- The archive job (Phase 2) runs only after validation passes and only writes fixed digest-derived paths,
  so a malicious submission cannot cause writes outside the accepted-results namespace.

## Phased rollout (each phase is separately reviewed/approved before execution)

This IPD is the ORCHESTRATOR. Each phase MAY be split into its own child IPD at execution time; this plan
records the shape and the gates. Do NOT execute a later phase before the earlier one is validated.

### Phase 1: minimum useful change (lowest risk, highest value; the "if you do only one thing")

- P1.1 `pubrun bench` client: switch guidance from paste to ATTACH; print an unmistakable safe-file block
  (PRIVATE do-not-share unredacted path; SAFE-to-submit redacted path; share-check result; Issue Form URL
  pointing at the MAIN repo). Change `_BENCH_SUBMIT_URL` to the main-repo issue-form URL; keep
  `--submit-file` guidance consistent. Optional `pubrun bench --prepare-submission` that copies only the
  checked redacted file into a `pubrun-share/` dir (stdlib only, no dep).
- P1.2 Add the `Benchmark result` Issue Form `.github/ISSUE_TEMPLATE/benchmark-result.yml` (instructions,
  required attachment guidance, required privacy acknowledgment, `type:benchmark-submission` +
  `status:pending` labels).
- P1.3 Add a VALIDATE-ONLY Action (no writes yet): on issue open/edit with the marker, run the
  submission-shape + safe-download + parse + schema-v5 + share-safety + semantic checks, then COMMENT a
  pass/fail receipt and set `status:accepted`/`status:needs-fix`. No archival yet (that is Phase 2).
- P1.4 Factor the share-safety rules into ONE versioned checker reused by the local client and the Action.
- Validation: manually accept the first few submissions to tune false positives before automating writes.
  Requires: a maintainer to create the labels + enable the issue form (repo-settings; human).

### Phase 2: safe automation (data branch + archival + aggregation)

- Create the `benchmark-data` branch; add canonicalization, SHA-256 dedupe, fixed-path archival
  (`accepted/<sha-prefix>/<sha>.json` + an ingestion metadata sidecar with issue id, submitter login,
  timestamps, digest, validator version); serialized aggregation (summary json/csv/md); auto-label +
  auto-close accepted issues; publish a Markdown/JSON index (optionally GitHub Pages).
- Requires (human/gated): creating the branch, granting the archive job `contents: write`, optional Pages.

### Phase 3: JOSS presentation + retire the satellite repo

- Link the intake path + aggregate from README, `CONTRIBUTING.md`, research-use docs; describe honestly
  what the corpus proves and does not prove; acknowledge consenting submitters; link benchmark issues
  that led to fixes.
- Retire `pubrun-benchmarks` as the primary destination: archive it with a prominent redirect README,
  preserving history. (Human action; irreversible-ish; explicit approval.)

## Findings (drivers)

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| B1 | High | Low (Phase 1) | Contributor | intake usability | The paste flow hits GitHub's ~65 KB issue-body cap and is brittle; attachments allow 25 MB and remove paste errors | `src/pubrun/__main__.py:1030,1044`; research Option 1 |
| B2 | High | Medium-High | Security | untrusted-input parsing | An issue-triggered Action parses attacker-controlled attachments; script-injection and over-broad token perms are real risks if built naively | research security section; GitHub script-injection guidance |
| B3 | Medium | Low | Maintainer/JOSS | discoverability + signal | Intake on a satellite repo is low-visibility for JOSS; consolidating into the main repo (data on a branch) is the recommended balance | research Part B |
| B4 | Medium | Low | Privacy | share-safety parity | The local checker and the server checker must use the SAME versioned rules; local redaction is the real boundary | research design requirements |
| B5 | High | Low | Security/QA | adversarial test coverage | The security case rests on the validator rejecting tampered/oversized/multi-attachment/injection-shaped payloads, so a COMMITTED adversarial fixture corpus is required, not just "test the logic" | added during /plan-review (PR-001) |

## Proposed changes

See the phased rollout above. Phase 1 is the concrete first execution slice; Phases 2-3 are scoped here
and each gated on separate approval. Remediation Risk: Phase 1 client + issue-form is Low; the Action is
Medium-High (security-sensitive parser) and is the item most warranting careful review and a validate-only
first cut. Phase 2 (write access + data branch) and Phase 3 (retire satellite repo) are higher-risk and
partly irreversible, hence separately gated.

## Deferred / out of scope

| Item | Risk | Axis | Reason | Later step |
|------|------|------|--------|-----------|
| Discussions-based intake (research Option 2) | Low | complexity | Documented fallback if issue volume becomes noisy; the validator's thin event adapter makes the switch cheap later | Revisit if issue noise becomes real |
| `gh`-assisted Gist path (Option 4) | Low | usability | Convenience path for repeat technical contributors only; little benefit once attachments work | Only if requested |
| Browser-only PR intake (Option 3) | Low | usability | Higher friction for the researcher audience; keep only as an alternate documented path | Optional docs mention |

## Cannot-do-unilaterally (explicit; require human / are gated)

- Creating/pushing the `benchmark-data` branch; enabling repo Issue Forms/labels/Discussions/Pages;
  granting workflow token permissions; archiving/retiring `pubrun-benchmarks`; ANY push or force-push.
  The agent implements the in-repo files (issue form yaml, workflow yaml, client code, checker, docs)
  and the human performs the settings/branch/repo-lifecycle actions and authorizes pushes.

## Required tests / validation

- Client: unit tests for the safe-file printout, the reused share-safety checker (reject absolute home
  paths / unredacted host/user; accept a properly redacted `/5` result), and `--prepare-submission`.
- Action validator: a COMMITTED adversarial fixture corpus is a required deliverable (PR-001), not just
  "test the logic". At minimum: a valid redacted `/5` result (accept); and rejects for each of an
  unredacted result, an oversized payload (over the byte cap), zero and multiple attachments, a
  wrong/absent schema version, a tampered digest, and an injection-shaped filename/title/body. The
  first-party validator is unit-tested against these fixtures with NO live issue required.
- Security: assert no contributor-controlled string reaches a shell; byte cap + host allowlist enforced;
  the archive job writes only fixed digest-derived paths.
- Matrix-validation: the `pubrun bench` client change is a CLI-grammar/behavior change, so it is NOT done
  on local green alone; push and validate on the full CI matrix before the (Phase 1) child IPD moves to
  executed/.
- Honesty rule: paste ACTUAL test/CI output; never claim green unrun.

## Spec / documentation sync

- Update `docs/` (a "Benchmarking and community results" page), `CONTRIBUTING.md`, and the README
  "Contribute a benchmark" entry point; CHANGELOG entries per phase. Keep pubrun's role framed as a
  provenance component; no overclaim about what the corpus proves (per the research's honesty note).

## Open questions (all RESOLVED during /plan-review 2026-07-21)

1. Execution slicing: RESOLVED - split EACH phase into its own dated child IPD; this file stays the
   orchestrator and moves to `executed/` only when all phases are done or explicitly closed. Each risky
   slice is reviewed/approved on its own. (See the gate.)
2. Label taxonomy / form URL: RESOLVED - adopt the research taxonomy as proposed:
   `type:benchmark-submission` + `status:{pending,accepted,needs-fix,rejected}` + optional
   `platform:{linux,macos,windows}` applied by automation; issue-form URL is the MAIN repo
   (`github.com/fariello/pubrun/issues/new?template=benchmark-result.yml`). Label creation is a
   human/settings action (cannot-do-unilaterally list).
3. Retire timing + existing submission: RESOLVED - keep `pubrun-benchmarks` live until Phase 1+2 are
   validated with real submissions; retire it only in Phase 3 (archive + redirect README, history
   preserved) AND migrate the one existing submission (issue #1 on the satellite) through the new
   validated path so no community data is lost.
4. Validator implementation: RESOLVED - FIRST-PARTY repo Python script reusing the `/5` schema + the
   shared share-safety checker; third-party actions pinned to full commit SHAs. (See Security boundaries.)

## Approval and execution gate

This IPD is a proposal; it MUST be human-approved before ANY execution and is NOT auto-run. It is an
orchestrator: approving it is not approving all phases at once. Execution contract:
- **Child-IPD lifecycle (OQ1 resolved):** each phase is executed via its OWN dated child IPD
  (`YYYYMMDD-HHMM-NN-benchmark-intake-phase-{1,2,3}-...`), reviewed and approved on its own. This
  orchestrator stays in `pending/` as the umbrella and is moved to `executed/` only when all phases are
  done or explicitly closed (retire to `not-executed/`/`superseded/` if a phase is dropped). Default:
  do NOT execute directly from this file; spin the Phase 1 child IPD first.
- Per-phase gate: each phase requires its own explicit human go before execution; do not start a later
  phase before the earlier one is validated (and, for Phase 1's CLI change, matrix-green).
- **Security gate (HARD, PR-002):** the ingestion workflow is an Internet-facing parser. A dedicated
  `/assess security` (or a security-focused `/plan-review`) pass on the workflow is a REQUIRED gate
  BEFORE the Action is granted ANY write permission (i.e. before Phase 2 archival). Phase 1's
  validate-only Action (no write) may proceed under ordinary review; write access waits for the security
  pass. The committed adversarial fixture corpus (B5) must be green before write access too.
- Cannot-do-unilaterally list above: the agent writes in-repo files only; the human performs
  settings/branch/repo actions (branch creation, labels, Issue Forms, Pages, token permissions,
  retiring/archiving `pubrun-benchmarks`, migrating issue #1) and authorizes every push.
- Honesty rule: paste actual runner output for tests/CI; never claim unrun.
- Commits path-scoped; never push without explicit authorization.

## Workflow history
- 2026-07-21 drafted (opencode / its_direct/pt3-claude-opus-4.8-1m-us): turned the maintainer-endorsed
  benchmark-intake research (`.agents/docs/research/20260720-1422-01-...` and `...-1406-01-...`) into a
  phased orchestrator IPD. Adopts Option 1 + the Part B main-repo/data-branch hybrid on the merits.
  Proposed 3 phases, deferred 3 alternative intake mechanisms. Not executed; awaiting review/approval.
- 2026-07-21 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS
  APPLIED. Verified cited evidence against code (paste-in-body flow at `__main__.py:1224` `_bench_issue_body`;
  `_BENCH_SUBMIT_URL` :1028; 65 KB warning :1030/:1044; `/5` schema + redaction/sanitizer present). Findings
  PR-001..PR-004 FIXED: PR-001 required a committed adversarial fixture corpus (new finding B5) and named it
  in validation; PR-002 upgraded the security review to a HARD gate before any write access and added
  abuse/first-contributor handling; PR-003 recorded migrating the existing satellite issue #1; PR-004 set
  the per-phase child-IPD lifecycle as the default. All 4 open questions resolved interactively (split into
  child IPDs; adopt the research label taxonomy + main-repo form URL; retire the satellite only in Phase 3
  and migrate issue #1; first-party validator). Status -> reviewed. Readiness: GO - PENDING HUMAN APPROVAL
  (orchestrator; each phase still separately approved and gated).
- 2026-07-21 set-tagged (opencode / its_direct/pt3-claude-opus-4.8-1m-us): grouped this work as
  `Set: benchmark-intake` per plans-README D82. This orchestrator is `Order: 0` and was renamed
  `-2002-01-` to `-2002-00-` so the filename `NN=00`-reserved-for-orchestrator convention holds. The
  three phase child IPDs, when created, will carry `Set: benchmark-intake` with `Order: 1/2/3`.
- 2026-07-21 approved (human): maintainer approved the APPROACH. Status -> approved; stays in pending/
  as the umbrella (moves to executed/ only when all phases are done). Per the per-phase gate, the Phase 1
  child IPD (Order 1) is being drafted next and will be separately reviewed + approved before execution.
- 2026-07-22 Phase 1 (Order 1) executed (opencode / its_direct/pt3-claude-opus-4.8-1m-us): the child IPD
  `20260721-2255-01` (attach-a-file client + Issue Form + validate-only Action) is complete and moved to
  executed/. Commits `ee54e0e` (security core) + `7b81f71` (client/form/workflow/docs); full CI matrix
  21/21 green (run 29922109354). Orchestrator stays in pending/ (umbrella). NEXT: Phase 2 (Order 2, data
  branch + archival/aggregation) requires its own child IPD AND a HARD /assess security gate BEFORE the
  Action is granted any `contents: write`; labels + Issue Form enablement remain human/settings actions.
