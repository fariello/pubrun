# IPD: Scrub an un-redacted benchmark result from public git history

- Date: 2026-07-20
- Concern: security / privacy (information disclosure remediation)
- Scope: git history rewrite of one committed artifact under `benchmarks/results/`; a force-push;
  post-rewrite hygiene. NOT application code.
- Status: reviewed
- Approval: (set when a human approves; omit until then. This plan REQUIRES explicit human approval
  because it rewrites history and force-pushes, which the project's rules otherwise forbid. NOTE: the
  Step 4 force-push additionally needs a SEPARATE explicit out-of-band GO.)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## SELF-REDACTION NOTICE (read first)

This plan is a COMMITTED, public file. The material it scrubs is host-identifying / user-identifying
strings (a hostname, an OS username, and home-directory paths) that were leaked by an un-redacted
benchmark JSON. **This plan therefore refers to that material ONLY by category and by file path /
JSON field - never by literal value** - so committing the plan does not re-introduce the very strings
the rewrite removes (the recursion trap). Anyone executing this plan reads the literals FROM THE
TARGET FILE at execution time, not from this document. Do not paste the leaked literals into this
plan, its run record, or any commit message.

## Problem / driver

A benchmark result JSON committed under `benchmarks/results/` (the file whose name begins with a
machine label and ends `-<timestamp>.json`, added in the single commit that introduced the benchmark
suite) is **un-redacted**: its `machine.host.hostname` field holds a raw hostname, and the document
contains the OS username and `/home/`-style paths. It has zero `<redacted>` markers. The repository is
public, so this is a low-severity but real information disclosure sitting in history.

Removing the file from the current tree (done separately, see "Related work") does NOT remove it from
history or from the public remote. Only a history rewrite does.

## Verified facts (by path/field, no literals) - CORRECTED during /plan-review 2026-07-20

The original draft's blast-radius claim was WRONG. A history-wide pre-flight sweep (Step 1, run during
review with needles read from the target blob at runtime) established the true picture:

- **Hostname needle:** confined to EXACTLY ONE file, the un-redacted benchmark `.json` under
  `benchmarks/results/` (whose name begins with a host label and ends `-<timestamp>.json`). The host
  label ALSO appears in that file's NAME (so it is in tree/commit metadata, not only file content).
  This is the one genuinely host-private string. It has zero `<redacted>` markers.
- That benchmark `.json` was ADDED in one commit and already DELETED from the tree in a later commit
  (two commits touch it; a third touched the directory). It is gone from HEAD but its blob remains in
  history. So the rewrite target is that one path across all history.
- **Username needle:** NOT confined to the benchmark file. It is the maintainer's ALREADY-PUBLIC
  identity (the GitHub handle, and the published author email in `pyproject.toml` and `CITATION.cff`),
  and it appears as `/home/<user>/`-style paths in roughly 65 committed files across all history
  (many executed/pending plan files, docs, some source, and the former `src/runtrace/` tree). It is
  NOT a secret.
- `summary.csv` / `summary.md`: verified to NOT contain the hostname needle.

## Scope decision (human, 2026-07-20)

- **History rewrite scope: the HOSTNAME ONLY**, by removing the one un-redacted benchmark `.json`
  (path-based removal, which also drops the host label embedded in its filename). This is achievable
  and matches the IPD's mechanism.
- **Username + home-directory paths: OUT of the history-rewrite scope.** The username is the
  maintainer's published identity, and its ~65-file footprint makes a retroactive rewrite
  disproportionate and damage-prone. Instead, prevent it GOING FORWARD (see "Going-forward guard").
- Force-push cost here is LOW and independent of scrub size: the remote has zero open PRs and only
  `main`, and the maintainer is the sole clone-holder; a rewrite of the single file still requires a
  force-push, but breaks no collaborator.

## Non-goals

- No application-code change.
- Not scrubbing anything beyond the ONE un-redacted benchmark `.json` (hostname carrier). NOT
  retroactively rewriting the username/home-path footprint in the ~65 other files (out of scope per the
  scope decision; handled going-forward instead). No evidence of tokens/keys/other secrets in history
  for this issue; a broader `/assess secrets` sweep is a separate concern.

## Proposed changes (ordered, validatable)

| Step | Change | Remediation Risk | Validation |
|------|--------|------------------|------------|
| 1 | **Pre-flight sweep - DONE during /plan-review.** History-wide scan established the true blast radius (see corrected Verified facts): the HOSTNAME needle is confined to the one benchmark `.json` (content + filename); the USERNAME needle is the maintainer's public identity, spread across ~65 files, and is OUT of history scope. Re-confirm at execution time by reading needles from a pre-rewrite copy of the target blob (never written into this plan). | Low | recorded: hostname in exactly the one path; scope unchanged from this decision |
| 2 | **Tool + scope (resolved OQ1).** Use `git filter-repo` with `--invert-paths`. Rewrite to **remove the ONE un-redacted benchmark `.json` path from ALL of history** (path-based removal drops both its content and its host-labeled filename; sidesteps enumerating literals). `summary.csv`/`summary.md` do NOT carry the hostname; remove them too ONLY as tidy-up if desired, but they are not required for the hostname scrub. | Medium (functionality: rewrites SHAs from the add-commit onward) | dry-run/report shows only the target path removed; topology otherwise unchanged |
| 3 | **Execute on a mirror-clone BACKUP first.** Make a full `git clone --mirror` backup before rewriting. Run `git filter-repo --path <the one benchmark json> --invert-paths` (path read at runtime). Verify on the rewritten copy before touching the remote. | Medium-High (functionality: irreversible without the backup) | post-rewrite on the copy: `git log --all -- <path>` returns nothing; the hostname needle (field AND the filename token) is absent from `git grep`/`git log` over ALL history; HEAD tree byte-identical for every OTHER path; test suite green on rewritten HEAD |
| 4 | **Force-push the rewritten history** to the remote. **REQUIRES the explicit out-of-band human GO named in the gate; not waived by approving this IPD.** Force-push cost here is low (no open PRs; only `main`; sole maintainer) but it is still irreversible on the remote. | High (operational: rewrites public history) | remote no longer contains the target path or the hostname needle; a fresh clone is clean; GitHub cached views update eventually |
| 5 | **Post-rewrite hygiene.** The hostname is not a rotatable secret; nothing to rotate (no credential found). Confirm recurrence prevention for the HOSTNAME is in place (the `benchmarks/results/.gitignore` tracking only `*.redacted.json`; harness redacts the hostname field and uses a SHA token in the redacted filename). | Low | `.gitignore` + harness hostname redaction confirmed; a fresh unredacted run is not committed |
| 6 | **Going-forward guard for the USERNAME / home paths (NEW; the scope decision's forward half).** Because the username/home-path footprint is NOT being rewritten, add a going-forward guard so new commits do not embed `/home/<user>/` absolute paths (e.g. a small pre-commit hook or lint that flags `file:///home/` and `/home/<user>/` in authored Markdown, matching the existing gitleaks-style local-hook pattern). This is a follow-up guardrail; it may be split into its own tiny IPD if preferred. | Low (usability) | a fresh commit containing a `/home/<user>/` absolute path is flagged locally before commit |

## Anti-regression / invariants

- The rewrite must NOT alter any file other than removing the ONE target benchmark `.json` (plus the
  optional summary tidy-up). Verify the HEAD tree (minus that file) is byte-identical before/after for
  all other paths, and that the test suite is green on the rewritten HEAD.
- The username / home-path footprint in the ~65 other files is intentionally UNCHANGED by the rewrite
  (out of scope); it must not be accidentally touched.
- Preserve authorship/dates of surviving commits (`filter-repo` does by default).

## Required tests / validation

- `git log --all --name-only -- <the one benchmark json path>` returns nothing after the rewrite.
- A history-wide search for the HOSTNAME needle - BOTH the `machine.host.hostname` field value AND the
  host-label token embedded in the filename - read from a pre-rewrite copy, returns zero hits across
  all commits.
- Full test suite green on the rewritten HEAD (the removed file is not referenced by tests; confirm).
- The remote reflects the rewrite (fresh clone is clean of the hostname needle).
- (Out of scope, do NOT assert) the username/home-path needle is expected to STILL appear in history;
  that is by decision, not a failure.

## Spec / documentation sync

- None in application docs. Add a short note to `CHANGELOG` (without the literals): "Removed an
  un-redacted benchmark result from git history; benchmark results now track only redacted artifacts."
- If the project keeps a security/incident log, record the remediation there (again, no literals).

## Open questions (all RESOLVED during /plan-review 2026-07-20)

1. **Tool:** RESOLVED - `git filter-repo` with `--invert-paths` (path-based removal of the one file).
2. **Timing / coordination:** RESOLVED - safe now: `gh pr list` shows zero open PRs, the only branch is
   `main`, and the maintainer is the sole clone-holder. No collaborator is broken by the force-push.
3. **Sweep scope / secrets pass:** RESOLVED - this IPD is tightly scoped to the HOSTNAME leak. A broader
   `/assess secrets` history pass remains a separate, recommended concern (not blocking).
4. **Is a rewrite warranted, and for what?** RESOLVED (human, 2026-07-20): rewrite for the HOSTNAME only
   (genuinely host-private, one file). The USERNAME is the maintainer's already-public identity and is
   NOT rewritten; it is prevented going forward (Step 6). This was the pivotal correction from review:
   the original plan would have force-pushed without removing the username footprint it implied it fixed.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution and is NOT
auto-executed. **Because it rewrites history and force-pushes, it additionally requires an EXPLICIT,
out-of-band human GO for the force-push (Step 4)** - the standing "never push / never force-push
without approval" rule is not waived by this plan's existence, and generic plan approval does NOT
by itself authorize Step 4. Execution contract:
- Scope fence: the history rewrite removes ONLY the one un-redacted benchmark `.json` (hostname
  carrier). The username/home-path footprint is explicitly NOT rewritten (Step 6 handles it forward).
  Steps 1-3 and 5-6 are non-destructive to the remote and may proceed on ordinary approval; ONLY Step 4
  (force-push) needs the separate explicit GO.
- Take a full `git clone --mirror` backup before any rewrite (Step 3); verify on the copy first.
- Honesty rule (hard MUST): paste ACTUAL command output (dry-run reports, post-rewrite verification)
  when reporting; never claim a scrub succeeded that was not verified.
- Do NOT write any leaked literal into commits, the run record, or this plan.
- On completion, `git mv` this IPD to `.agents/plans/executed/` (Status -> executed) and record the
  remediation (no literals). If Step 6's going-forward guard is split out, note the follow-up IPD.

## Related work

- Going-forward guard (already applied this session, separate commit): `benchmarks/results/.gitignore`
  tracks only `*.redacted.json`; local results are named `*.unredacted.json`; the redacted filename no
  longer embeds the hostname (hash token instead).
- Benchmark-JSON size reduction is a SEPARATE follow-up (see `TODO.md` "Deferred ideas"); do not
  conflate it with this security scrub.

## Workflow history
- 2026-07-20 (opencode / its_direct/pt3-claude-opus-4.8-1m-us): drafted; proposed 5 steps. Written
  with self-redaction discipline (no leaked literals in the plan).
- 2026-07-20 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): REVIEWED - REVISIONS
  APPLIED. Ran the pre-flight sweep and found the draft's blast-radius facts WRONG (PR-001, BLOCKER):
  the hostname is confined to one file, but the username needle is the maintainer's already-public
  identity spread across ~65 files, so the original 3-path plan would have force-pushed without
  removing the username footprint it implied. PR-002/003/004 also recorded (public identity; filename
  token; two-commit history). Human scope decision: rewrite the HOSTNAME only (one file); handle
  username/home-paths going forward (new Step 6), not by history rewrite. Corrected Verified facts,
  narrowed Steps 2-3, added Step 6, hardened the gate (Step 4 needs a separate explicit force-push GO;
  Steps 1-3/5-6 are non-destructive to the remote). All 4 open questions resolved. Status -> reviewed.
  Readiness: NO-GO until (a) human approval AND (b) the separate explicit force-push GO for Step 4.
