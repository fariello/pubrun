# IPD: Benchmark intake Phase 2 (local pull/validate/aggregate/retag; NO server writes)

- Date: 2026-07-22
- Concern: feature / data-collection / security (collect accepted benchmark results WITHOUT granting any
  GitHub Action write access; all storage + aggregation happen in a maintainer-run local script)
- Scope: a NEW local script (proposed `benchmarks/pull_submissions.py`) + its tests; reuse of the
  existing validator (`.github/scripts/validate_benchmark_submission.py`), share-safety checker
  (`benchmarks/share_safety.py`), schema (`schemas/benchmark.schema.json`), and aggregator
  (`benchmarks/aggregate.py`); a committed local data dir under `benchmarks/` for accepted results;
  docs/CHANGELOG. NO changes to `.github/workflows/*` permissions, NO `contents: write` for any Action,
  NO server-side archival/aggregation/Pages/auto-close.
- Status: reviewed
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Set: benchmark-intake
- Order: 2

## Parent / set / provenance

Child of the approved orchestrator `.agents/plans/pending/20260721-2002-00-benchmark-intake-redesign.md`
(`Set: benchmark-intake`). This is the Phase 2 slot ("safe automation: data branch + archival +
aggregation"). It DELIBERATELY DEVIATES from the orchestrator's recorded Phase 2 shape (which assumed a
server-side archive job with `contents: write` on a `benchmark-data` branch): after weighing four models
with the maintainer (2026-07-22), the chosen design is the **local pull model (Model 0)**, in which
GitHub Actions gains NO new powers and there is NO server write path. The maintainer runs a local script
that fetches accepted/open benchmark issues, validates and aggregates their JSON locally, and re-tags
issues using the maintainer's own `gh` auth. Rationale: it removes (does not merely mitigate) the single
biggest risk of Phase 2, an internet-facing, attacker-input-processing Action holding repo write access,
and it matches the maintainer's stated workflow ("I'll pull and do the work locally"). Because there is
no server write path, the orchestrator's HARD `/assess security` gate (which existed specifically to gate
that write access) does NOT apply; a LIGHTER security pass on the local script's untrusted-JSON handling
is done instead and is recorded in the Security section below. The orchestrator will be updated with a
note that Model 0 supersedes its server-archival Phase 2 design and why the hard gate no longer applies.

## Goal

Let the maintainer collect the corpus of accepted community benchmark results with ONE local command and
no new GitHub automation. `benchmarks/pull_submissions.py`:

1. Lists benchmark-submission issues on `fariello/pubrun` (via the maintainer's `gh`), optionally filtered
   by label/state.
2. For each, resolves the submission source (the SAME way the server does: an attachment/gist `.json`
   URL, or an inline `pubrun-benchmark-submission:v1` JSON block), downloads/reads it under the same
   host-allowlist + byte-cap + redirect protections, and runs the SAME fail-closed validation
   (schema `/5` + share-safety + semantic), now with a tightened 256 KB cap.
3. Stores each accepted, validated, redacted result locally at a fixed, content-addressed path
   (`benchmarks/data/accepted/<sha256>.json`) plus a small sidecar of ingestion metadata (issue number,
   submitter login, timestamps, digest, validator + share-safety versions). Dedupes by SHA-256.
4. Aggregates the accepted corpus with the existing `benchmarks/aggregate.py` (summary csv/md), locally.
5. Re-tags each issue as `status:accepted` or `status:needs-fix` (and posts a short comment on a
   rejection) using the maintainer's `gh`. A `--dry-run` default shows what WOULD change; writes/retags
   happen only with an explicit `--apply`.

Nothing is automatic on GitHub. Anything that does not validate, or exceeds 256 KB, is refused.

## Project conventions / current-state findings (Step 0, verified)

- Reuse (verified present): `.github/scripts/validate_benchmark_submission.py` exposes `validate_file()`,
  `check_shape/parse_json/check_schema/check_share_safe/check_semantic`, `_download()` (host allowlist +
  redirect guard + `MAX_BYTES` cap, `:174-201`), and `MAX_BYTES = 1 MiB` (`:45`). `benchmarks/share_safety.py`
  is the structural is-it-redacted checker. `benchmarks/aggregate.py` exposes `_load()`, `build_rows()`,
  `write_csv()`, `write_markdown()` (`:97,120,158,168`). `schemas/benchmark.schema.json` is the `/5`
  contract. The extractor `.github/scripts/extract_attachment_url.py` already resolves
  `kind=url|inline|none` from an issue body and enforces the same host allowlist + inline size cap.
- Current server intake is validate-only: workflow perms `contents: read` + `issues: write`, no writes
  (`.github/workflows/benchmark-intake.yml`). THIS IPD DOES NOT CHANGE THAT.
- Stack: zero-runtime-dependency wheel; `benchmarks/` is dev/repro tooling NOT shipped in the wheel, so
  the pull script may import the benchmark modules and use `jsonschema` (dev/CI dep), never a runtime dep.
- `gh` is the supported GitHub transport; call it via argv lists (never a shell), read issue bodies as
  DATA. House rules: no em/en dashes in authored Markdown; path-scoped commits; never push without
  authorization; matrix-validation for behavior/contract changes; paste actual test output.

## Design (Model 0: local pull script)

### Reuse, do not re-implement
- Import validation from `validate_benchmark_submission` (shape/parse/schema/share-safety/semantic) and
  the shared `share_safety` rules; import aggregation from `aggregate`. The pull script is orchestration
  glue, not new validation logic, so local and server stay in lockstep (same rejections).
- Reuse the validator's `_download()` (host allowlist, bounded redirects, byte cap, timeout) for fetching
  attachment/gist URLs; reuse the extractor's `resolve_source()` shape for inline vs URL.
- Import mechanism (PR-001): `validate_benchmark_submission` and `extract_attachment_url` live in
  `.github/scripts/` (loose scripts, not a package) and `share_safety`/`aggregate` live in `benchmarks/`.
  The pull script imports them the SAME way the validator already imports `share_safety`, prepend the two
  dirs to `sys.path` and `import` by module name (mirroring `validate_benchmark_submission.py:60-61`).
  Load with `importlib` by explicit path if a name clash is a concern. This cross-dir coupling
  (`benchmarks/ -> .github/scripts/`) is deliberate reuse (one validation implementation, no fork) and
  MUST be covered by an import smoke test so a moved/renamed module is caught.

### Tightened acceptance gate
- Add a `MAX_STORE_BYTES = 256 * 1024` cap applied by the pull script (stricter than the validator's
  1 MiB network cap). Apply it UNIFORMLY before parse to BOTH sources (PR-004): a URL download AND an
  inline block (whose extractor cap is 1 MiB), so no source can smuggle a 256KB..1MiB payload past the
  store gate. Everything else (schema `/5`, share-safety, semantic) is the existing fail-closed
  validation. A file that fails ANY check is never stored and the issue is marked `status:needs-fix`
  (with a short, payload-free reason comment).

### Local storage (content-addressed, deduped)
- Store accepted results at `benchmarks/data/accepted/<sha256>.json` (the sha256 of the exact validated
  bytes; content-addressed so re-pulling is idempotent and duplicates collapse). Write a sidecar
  `benchmarks/data/accepted/<sha256>.meta.json` with: submission `kind` (url|inline), source host (for a
  URL), fetch timestamp (UTC), sha256, validator version, `share_safety_version`, and a `sources` LIST of
  {issue_number, issue_url, submitter_login} (PR-002): the SAME redacted bytes can legitimately arrive
  from more than one issue, so the meta records ALL contributing issues (append on a dedupe hit; do not
  overwrite/lose the earlier attribution). The result JSON itself is written once (content-addressed);
  only the `sources` list grows. NEVER store the unredacted anything; the stored file is the
  already-redacted, share-checked result. A `.gitignore`-tracked `benchmarks/data/` with a README
  explaining the corpus; the maintainer commits accepted results deliberately (the script writes them to
  the working tree; committing/pushing is a separate maintainer action, path-scoped).

### Aggregation (local only)
- After storing, call `aggregate.build_rows()` over `benchmarks/data/accepted/*.json` and
  `write_csv`/`write_markdown` to `benchmarks/data/summary.csv` + `summary.md`. No server involvement.

### Issue re-tagging (maintainer's gh; explicit --apply)
- Default `--dry-run`: print the plan (which issues would become accepted/needs-fix, which results would
  be stored, dedupe hits) and change NOTHING. With `--apply`: set `status:accepted` / `status:needs-fix`
  via `gh issue edit ... --add-label/--remove-label` (argv list, never a shell), ALWAYS removing
  `status:pending` on a decision (PR-003; mirrors the Phase 1 workflow's label hygiene), and on a
  rejection post a short, payload-free comment with the failing stage/reason. All GitHub writes are the
  maintainer's own authenticated actions, not an Action.

### CLI shape
- `benchmarks/pull_submissions.py [--repo OWNER/NAME] [--label type:benchmark-submission] [--state open]
  [--apply] [--limit N] [--data-dir benchmarks/data]`. `--dry-run` is the default (explicit `--apply` to
  write). `--json` for a machine-readable report. Refuses to run without `gh` available/authenticated
  (clear message), never runs `gh auth login`.

## Security (LIGHTER pass; the hard gate does not apply, Model 0 has NO server write path)

The hard `/assess security` gate in the orchestrator was for granting an internet-facing Action
`contents: write`. Model 0 grants NO Action any new permission and adds NO server write path, so that gate
is not triggered. The residual risk is that the LOCAL script parses attacker-controlled JSON and calls
`gh`; the following are REQUIRED and are the focus of the lighter pass:

| ID | Risk | Required control |
|----|------|------------------|
| S2-1 | Untrusted JSON parsed locally | Reuse the existing fail-closed validator (schema/share-safety/semantic); parse as DATA only; never `eval`/`exec`/`pickle`; treat every field as inert. |
| S2-2 | Oversized / zip-bomb-ish input | 256 KB store cap enforced BEFORE parse; reuse `_download` 1 MiB network cap + host allowlist + bounded redirects + timeout. |
| S2-3 | Path traversal on store | The stored filename is the SHA-256 hex of the validated bytes (content-addressed), never derived from issue/attachment-supplied names; write only under `benchmarks/data/accepted/`; reject a computed path that escapes it. |
| S2-4 | Shell / argument injection via issue content | All `gh` calls use argv lists, `shell=False`; issue numbers are ints; labels are fixed constants; comment bodies are our own text (never echo the payload). |
| S2-5 | Leaking a bad submission into the corpus | Only a file passing ALL checks is stored; a rejection stores nothing and marks needs-fix. The stored file is already redacted + re-share-checked at pull time. |
| S2-6 | Accidental write / wrong repo | `--dry-run` is the default; `--apply` required for any label/comment/store-commit; repo slug validated `OWNER/NAME`; the script never pushes (the maintainer commits/pushes deliberately). |
| S2-7 | Credential exposure | Never print `gh` tokens or `gh auth token`; rely on the maintainer's ambient `gh` auth; sanitize any error text. |

A focused security review of the finished script MUST confirm S2-1..S2-7. This is lighter than the hard
gate ONLY because there is no server write path to assess; the untrusted-input handling is treated with
the same fail-closed rigor as the server validator.

## Findings (drivers)

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| P2-1 | High | Low | Maintainer | data collection | Phase 1 collects nothing; accepted results are not stored. A local pull/store closes that with zero server risk | orchestrator Phase 2; session 2026-07-22 |
| P2-2 | High | Low | Security | no server write | Model 0 adds NO Action write access, removing the hard-gated risk entirely (vs mitigating it) | orchestrator Phase 2 gate; model comparison 2026-07-22 |
| P2-3 | Medium | Low | Security | untrusted parse (local) | The local script still parses attacker JSON; must reuse the fail-closed validator + caps, no eval | reference S13; `validate_benchmark_submission.py` |
| P2-4 | Medium | Low | Correctness | dedupe / idempotence | Re-pulling must be idempotent: content-addressed store + SHA dedupe so re-runs do not duplicate | design |
| P2-5 | Medium | Low | Safety | accidental writes | Default dry-run; explicit --apply for any label/comment/store; never auto-push | design |
| P2-6 | Low | Low | Reuse | lockstep | Validation/aggregation reuse the existing modules so local == server behavior | `aggregate.py`, validator |

## Proposed changes (ordered, validatable)

| Step | Src | Change | Files | Remediation Risk | Validation |
|------|-----|--------|-------|------------------|------------|
| 1 | P2-3,P2-6 | Add `benchmarks/pull_submissions.py`: import the validator + share_safety + aggregate; resolve source (url/inline) reusing the extractor shape; fetch via the validator's `_download`. | `benchmarks/pull_submissions.py` | Low | unit (mock gh + fixtures): a valid `/5` result validates; an unredacted/oversized/off-schema one is refused |
| 2 | P2-2 | Enforce a 256 KB store cap before parse; reuse the 1 MiB network cap + host allowlist. | `benchmarks/pull_submissions.py` | Low | unit: 256KB+1 rejected pre-parse; off-allowlist host rejected |
| 3 | P2-3,P2-4 | Content-addressed store (`data/accepted/<sha256>.json` + `.meta.json`), SHA-256 dedupe, path confined under data dir. | `benchmarks/pull_submissions.py`, `benchmarks/data/` (+ README, .gitignore) | Low | unit: same bytes -> one file; path traversal attempt rejected; sidecar has the recorded fields |
| 4 | P2-1 | Aggregate accepted corpus via `aggregate.build_rows` + `write_csv/write_markdown` to `data/summary.*`. | `benchmarks/pull_submissions.py` | Low | unit: aggregation over 2 stored fixtures writes non-empty csv/md |
| 5 | P2-5 | Issue re-tag/comment via `gh` (argv/no-shell); `--dry-run` default, `--apply` to write; never push. | `benchmarks/pull_submissions.py` | Low | unit (mock subprocess): dry-run makes no gh write; --apply emits the expected argv; injection stays literal |
| 6 | P2-1 | Docs + CHANGELOG: how to run the pull script; the local corpus layout; that GitHub does nothing automatically. | `README.md`/`CONTRIBUTING.md`, `CHANGELOG.md`, `benchmarks/data/README.md` | Low | links resolve; dash-clean |

## Deferred / out of scope (this phase)

| Item | Reason |
|------|--------|
| Any server-side archival / `contents: write` / `benchmark-data` branch Action | Superseded by Model 0; would reintroduce the hard-gated risk. Revisit only if an always-current public aggregate becomes a requirement. |
| GitHub Pages / published index / auto-close automation | Not needed; maintainer aggregates locally. |
| Gist discovery/reconciliation, `--cleanup-submissions` (client Slice B) | Separate future IPD (Order 5), unrelated to intake collection. |
| Retiring `pubrun-benchmarks` | Phase 3 (Order 3). |

## Cannot-do-unilaterally (human / gated)

- The maintainer runs the script (it acts as the maintainer via `gh`); the agent authors the script + tests
  and MUST NOT run it against the live repo. Committing/pushing the collected corpus is a deliberate
  maintainer action.
- Labels already exist (created by the maintainer). No repo-settings change is needed for this phase.

## Required tests / validation

- Validation reuse: a genuine redacted `/5` fixture is accepted; adversarial fixtures (unredacted host,
  home path, wrong schema, missing required, negative timing, oversized >256 KB, non-JSON) are refused
  with the correct stage, reusing the committed corpus in `.github/scripts/test_fixtures/`.
- Import smoke (PR-001): `pull_submissions` can import `validate_benchmark_submission`,
  `extract_attachment_url`, `share_safety`, and `aggregate` via the documented path-injection; a
  moved/renamed module fails this test loudly.
- Store: content-addressed filename == sha256 of bytes; re-store of identical bytes is a no-op (dedupe);
  a filename/path-traversal attempt never escapes `benchmarks/data/accepted/`; sidecar fields present.
- Multi-issue dedupe (PR-002): the SAME bytes submitted from two different issues yields ONE result file
  and a meta `sources` list of length 2 (both issues recorded); no attribution lost.
- Label hygiene (PR-003): a decision removes `status:pending` and leaves exactly one of
  `status:accepted`/`status:needs-fix` (assert the emitted `gh` argv).
- Uniform cap (PR-004): an inline payload of 256KB+1 is rejected before parse (not just the URL path).
- Aggregation: `build_rows` over >=2 stored fixtures yields rows and non-empty csv/md.
- gh interaction (mock `subprocess`): `--dry-run` performs NO gh write; `--apply` issues the expected
  argv (`gh issue edit ... --add-label status:accepted` etc.); a `$(...)`/backtick-shaped issue field is
  treated literally and never executed; tokens never printed.
- Security asserts (S2-1..S2-7): no `eval/exec/pickle`; 256 KB cap before parse; host allowlist honored;
  content-addressed writes confined to the data dir; gh via argv; no token in output.
- Matrix note: this is a dev/CI-tooling script (not shipped in the wheel, not a CLI-grammar change to the
  installed package). Local green on the supported Pythons is sufficient; a full OS/py matrix run is NOT
  required unless a later change touches the installed surface. (Paste actual local test output.)
- Honesty rule: paste ACTUAL test output; never claim green unrun.

## Spec / documentation sync

- README/CONTRIBUTING: a short "maintainer: collecting benchmark submissions" note (run
  `benchmarks/pull_submissions.py`, dry-run by default, `--apply` to store + retag; corpus lives under
  `benchmarks/data/`; GitHub does nothing automatically). CHANGELOG Added entry. A `benchmarks/data/README.md`
  documenting the layout and that stored files are redacted + validated. No overclaim about what the
  corpus proves.

## Open questions (all RESOLVED 2026-07-22)

1. Corpus location: RESOLVED. Commit accepted results under `benchmarks/data/accepted/*.json` on `main`
   (small, redacted, human-reviewable in a normal diff; travels with a clone), with `summary.csv`/
   `summary.md` regenerated alongside and a `benchmarks/data/README.md`. NOT a separate branch.
2. Store cap: RESOLVED. Keep an explicit `MAX_STORE_BYTES = 256 * 1024` constant (commented: a real
   redacted `/5` result is ~38 KB, so ~6x headroom), applied uniformly to URL and inline sources before
   parse. NOT schema-derived.
3. Comment on acceptance: RESOLVED. Re-label quietly on acceptance (label only, no comment); post a
   short, payload-free, actionable comment ONLY on rejection (failing stage/reason).

## Approval and execution gate

Proposal; MUST be human-approved before execution; NOT auto-run. Execution contract:
- Open questions resolved (or explicitly OPEN -> NO-GO).
- Scope fence: ONLY `benchmarks/pull_submissions.py` (+ its tests), `benchmarks/data/` (dir + README +
  .gitignore), and docs/CHANGELOG. NO `.github/workflows/*` permission change, NO `contents: write` for
  any Action, NO server-side archival/aggregation. Anything beyond -> STOP and report.
- Security: reuse the fail-closed validator + caps; 256 KB store cap; content-addressed confined writes;
  gh via argv (never a shell); never print tokens/payload; `--dry-run` default. The lighter security pass
  (S2-1..S2-7) MUST be confirmed on the finished script.
- Honesty rule (hard MUST): paste actual test output; never claim green unrun.
- Commits path-scoped; never push without explicit authorization. The agent never runs the script against
  the live repo.
- Lifecycle: on completion + approval + local-green, move this IPD to `.agents/plans/executed/`
  (Status -> executed) with a Workflow-history line; record the phase in the orchestrator's history.

## Workflow history
- 2026-07-22 drafted (opencode / its_direct/pt3-claude-opus-4.8-1m-us): Phase 2 as the LOCAL PULL model
  (Model 0), chosen over three server-write models after a maintainer comparison. GitHub Actions gains no
  new powers; a maintainer-run `benchmarks/pull_submissions.py` validates (reusing the existing
  fail-closed validator + a tightened 256 KB cap), content-addressed-stores accepted redacted results
  locally, aggregates with the existing aggregator, and re-tags issues via the maintainer's own `gh`
  (dry-run by default). No server write path, so the orchestrator's HARD /assess security gate does not
  apply; a lighter security pass (S2-1..S2-7) on the untrusted-JSON handling is required instead. `Set:
  benchmark-intake`, `Order: 2`. Not executed; awaiting review/approval (maintainer's default is to run
  /plan-review).
- 2026-07-22 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS
  APPLIED. Verified every reuse claim against the tree: validator exports
  (`validate_benchmark_submission.py:79,91,105,124,130,159`), `_download` host-allowlist/redirect/cap
  (`:174-201`), `MAX_BYTES` (`:45`), `ALLOWED_ATTACHMENT_HOSTS` (`:49`); aggregate `_load/build_rows/
  write_csv/write_markdown` (`aggregate.py:97,120,158,168`) and `_scenarios_view` `/5` recompute
  (`:55-83`); extractor `resolve_source/find_inline_json/find_attachment_url` + marker + inline cap
  (`extract_attachment_url.py:40,43,67,95,127`); fixture corpus present; wheel excludes benchmarks/ +
  .github/ (`pyproject.toml:71`). Findings PR-001..PR-005 FIXED in place: PR-001 named the cross-dir
  import mechanism (sys.path-injection mirroring the validator) + an import smoke test; PR-002 made the
  meta sidecar record a `sources` LIST so the same bytes from multiple issues keep all attribution;
  PR-003 made a decision always drop `status:pending`; PR-004 applied the 256 KB store cap uniformly to
  URL AND inline before parse; PR-005 set `Status: reviewed`. All 3 open questions resolved with the
  maintainer (corpus on main under benchmarks/data/; explicit 256 KB constant; quiet accept, comment on
  reject). No BLOCKER/HIGH unresolved. Verdict: APPROVE WITH REVISIONS APPLIED; Readiness: GO - PENDING
  HUMAN APPROVAL.
