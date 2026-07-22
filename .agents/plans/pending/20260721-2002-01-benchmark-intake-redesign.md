# IPD: Benchmark intake redesign (attach-a-file Issue Form + validating Action + data branch)

- Date: 2026-07-21
- Concern: feature / infrastructure / security (community benchmark submission mechanism) + JOSS readiness
- Scope: replace the paste-JSON-into-a-GitHub-issue submission flow with a GitHub Issue Form that takes
  a `.redacted.json` ATTACHMENT, validated by a GitHub Actions workflow, with accepted results archived
  to a dedicated `benchmark-data` branch and aggregates rebuilt; consolidate intake into the MAIN pubrun
  repo and retire `pubrun-benchmarks` as the primary destination. Phased (see below). Touches
  `pubrun bench` client UX (`src/pubrun/__main__.py`), `.github/`, docs, and repo/branch settings.
- Status: to-review
- Approval: (set when a human approves; omit until then)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

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
  Pin any third-party actions to full commit SHAs (prefer first-party + a repo Python script).
- Never print the payload in Actions logs.
- Privacy is decided by LOCAL redaction: a public attachment uploads immediately and cannot be un-shared;
  server-side rejection is a backstop, not the boundary. The client UX must make the safe file unmistakable.

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
- Action: test the validator logic from FIXTURES (a valid redacted `/5` result passes; a tampered/
  unredacted/oversized/multi-attachment/wrong-schema payload is rejected) without needing a live issue.
- Security: assert no contributor-controlled string reaches a shell; byte cap + host allowlist enforced.
- Matrix-validation: the `pubrun bench` client change is a CLI-grammar/behavior change, so it is NOT done
  on local green alone; push and validate on the full CI matrix before the phase moves to executed/.
- Honesty rule: paste ACTUAL test/CI output; never claim green unrun.

## Spec / documentation sync

- Update `docs/` (a "Benchmarking and community results" page), `CONTRIBUTING.md`, and the README
  "Contribute a benchmark" entry point; CHANGELOG entries per phase. Keep pubrun's role framed as a
  provenance component; no overclaim about what the corpus proves (per the research's honesty note).

## Open questions

1. Slice Phase 1 into its own child IPD for execution, or execute directly from this orchestrator?
2. Confirm the main-repo issue-form URL / label taxonomy (`type:benchmark-submission`, `status:*`).
3. Timing of retiring `pubrun-benchmarks` (Phase 3) relative to when the new path is proven; and whether
   to migrate the one existing submission (issue #1 on the satellite repo) into the new path.
4. Should the validator be a first-party repo Python script (reusing `schemas/benchmark.schema.json` +
   the shared share-safety checker) rather than third-party actions, to minimize supply-chain surface?
   (Recommend yes.)

## Approval and execution gate

This IPD is a proposal; it MUST be human-approved before ANY execution and is NOT auto-run. It is an
orchestrator: approving it is not approving all phases at once. Execution contract:
- Per-phase gate: each phase (1, 2, 3) requires its own explicit go before execution; do not start a
  later phase before the earlier one is validated (and, for Phase 1's CLI change, matrix-green).
- Security gate (Phase 1 Action / Phase 2 archival): the ingestion workflow is treated as an
  Internet-facing parser; a `/plan-review` (and ideally an `/assess security` pass) on the workflow is
  strongly recommended before it is enabled with any write permission.
- Cannot-do-unilaterally list above: the agent writes in-repo files only; the human performs
  settings/branch/repo actions and authorizes every push.
- Honesty rule: paste actual runner output for tests/CI; never claim unrun.
- Commits path-scoped; never push without explicit authorization.
- Lifecycle: as each phase completes + is approved + (where applicable) matrix-green, record it in
  Workflow history; move this orchestrator to `executed/` only when all approved phases are done (or
  split per-phase child IPDs and move each independently).

## Workflow history
- 2026-07-21 drafted (opencode / its_direct/pt3-claude-opus-4.8-1m-us): turned the maintainer-endorsed
  benchmark-intake research (`.agents/docs/research/20260720-1422-01-...` and `...-1406-01-...`) into a
  phased orchestrator IPD. Adopts Option 1 + the Part B main-repo/data-branch hybrid on the merits.
  Proposed 3 phases, deferred 3 alternative intake mechanisms. Not executed; awaiting review/approval.
