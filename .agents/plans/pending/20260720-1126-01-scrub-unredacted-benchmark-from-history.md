# IPD: Scrub an un-redacted benchmark result from public git history

- Date: 2026-07-20
- Concern: security / privacy (information disclosure remediation)
- Scope: git history rewrite of one committed artifact under `benchmarks/results/`; a force-push;
  post-rewrite hygiene. NOT application code.
- Status: to-review
- Approval: (set when a human approves; omit until then. This plan REQUIRES explicit human approval
  because it rewrites history and force-pushes, which the project's rules otherwise forbid.)
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

## Verified facts (by path/field, no literals)

- Exactly THREE paths were ever committed under `benchmarks/results/`: the un-redacted result `.json`
  (leaks), plus `summary.csv` and `summary.md` (verified to NOT contain the leaked needles, but are
  derived/unredacted-source artifacts that the "track only `*.redacted.json`" policy excludes anyway).
- All three entered in a SINGLE commit (the benchmark-suite introduction commit). Each is touched by
  that one commit only. So the rewrite target is one commit; all descendants inherit new SHAs.
- The leak is confined to the `.json` file's content (hostname field + username + home paths).

## Non-goals

- No application-code change.
- Not scrubbing anything beyond the identified `benchmarks/results/` artifacts (no evidence of tokens,
  keys, or other secrets in history for this issue; a broader secret sweep is separate - see below).

## Proposed changes (ordered, validatable)

| Step | Change | Remediation Risk | Validation |
|------|--------|------------------|------------|
| 1 | **Pre-flight sweep (widen the net once, by needles read at runtime).** Before rewriting, scan ALL of history for the leaked categories to confirm the blast radius is only the known paths and no OTHER committed file embeds the same hostname/username/home-path. Use `git log -p --all -S<needle>` / `git grep` over history with needles read from the target file at run time (never written into this plan). If the sweep finds more, expand the rewrite target set and re-review. | Low | a recorded list of every history path containing any needle; confirmed == the known set (or expanded) |
| 2 | **Choose the rewrite tool + scope.** Prefer `git filter-repo` (modern, recommended) over BFG. Rewrite to **remove the three `benchmarks/results/` paths from ALL of history** (path-based removal is safest and avoids per-string editing of binary-ish JSON). Removing the whole files (not editing them) sidesteps having to enumerate literals. | Medium (functionality: rewrites SHAs) | dry-run/report shows only those paths removed; commit count/topology otherwise unchanged |
| 3 | **Execute the rewrite on a fresh clone / backup first.** Make a full backup (mirror clone) of the repo before rewriting. Run `git filter-repo --path benchmarks/results/<...> --invert-paths` (or `--path-glob 'benchmarks/results/*.json'` etc.) for the target paths. | Medium-High (functionality: irreversible without the backup; can break in-flight branches/PRs) | post-rewrite: `git log --all -- <paths>` returns nothing; the leaked needles are absent from `git grep` over all history; the working tree at HEAD still builds/tests green |
| 4 | **Force-push the rewritten history** to the remote (all branches + tags). **This is the step the project rules forbid without explicit human approval - it is gated on the Approval line above.** Coordinate: any open clones/PRs must re-clone; announce if others collaborate. | High (functionality/operational: rewrites public history, invalidates existing clones, breaks open PRs) | remote history no longer contains the leaked paths; a fresh clone shows a clean history; GitHub's cached views eventually update |
| 5 | **Post-rewrite hygiene.** Because the data was public, treat the exposed identifiers as compromised-for-what-they-are (hostname/username are not secrets that can be "rotated", but note that if any credential were ever exposed the same way it MUST be rotated - out of scope here since none found). Confirm the going-forward guardrail (the `benchmarks/results/.gitignore` that tracks only `*.redacted.json`, plus the harness naming/redaction fix) is in place so this cannot recur. | Low | `.gitignore` + harness redaction confirmed; a fresh unredacted run does not get committed |

## Anti-regression / invariants

- The rewrite must NOT alter any file other than removing the three target artifacts. Verify the HEAD
  tree (minus those files) is byte-identical before/after for all other paths, and that the test suite
  is green on the rewritten HEAD.
- Preserve authorship/dates of surviving commits (`filter-repo` does by default).

## Required tests / validation

- `git log --all --name-only -- benchmarks/results/` returns nothing after the rewrite.
- A history-wide search for the leaked needles (read from a pre-rewrite copy of the target file) returns
  zero hits across all commits.
- Full test suite green on the rewritten HEAD (the removed files are not referenced by tests; confirm).
- The remote reflects the rewrite (fresh clone is clean).

## Spec / documentation sync

- None in application docs. Add a short note to `CHANGELOG` (without the literals): "Removed an
  un-redacted benchmark result from git history; benchmark results now track only redacted artifacts."
- If the project keeps a security/incident log, record the remediation there (again, no literals).

## Open questions

1. **Tool:** `git filter-repo` (recommended) vs. BFG? filter-repo is the current standard and handles
   path removal cleanly; BFG is simpler for blob-by-size/secret-by-string but less precise here.
   Recommend filter-repo with `--invert-paths`.
2. **Timing / coordination:** is anyone else cloning/PR-ing this repo right now? A force-push after a
   rewrite breaks their clones. Confirm a safe window.
3. **Scope of the pre-flight sweep (Step 1):** confirm we only care about the hostname/username/home
   -path categories, or also do a full `/assess secrets` pass over history while we are in there
   (recommend the latter, as a separate concern, so this IPD stays tightly scoped to the known leak).
4. **Is a rewrite even warranted for THIS content?** Hostname + username + home path are low-severity
   (not credentials). The maintainer chose the rewrite path; this records that decision. If priorities
   change, "accept + prevent recurrence" (untrack + gitignore + harness fix, already the going-forward
   guard) is the lower-effort alternative.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution and is NOT
auto-executed. **Because it rewrites history and force-pushes, it additionally requires an EXPLICIT,
out-of-band human GO for the force-push (Step 4)** - the standing "never push / never force-push
without approval" rule is not waived by this plan's existence. Execution contract:
- Take a full mirror-clone backup before any rewrite (Step 3).
- Honesty rule (hard MUST): paste ACTUAL command output (dry-run reports, post-rewrite verification)
  when reporting; never claim a scrub succeeded that was not verified.
- Do NOT write any leaked literal into commits, the run record, or this plan.
- On completion, `git mv` this IPD to `.agents/plans/executed/` (Status -> executed) and record the
  remediation (no literals).

## Related work

- Going-forward guard (already applied this session, separate commit): `benchmarks/results/.gitignore`
  tracks only `*.redacted.json`; local results are named `*.unredacted.json`; the redacted filename no
  longer embeds the hostname (hash token instead).
- Benchmark-JSON size reduction is a SEPARATE follow-up (see `TODO.md` "Deferred ideas"); do not
  conflate it with this security scrub.

## Workflow history
- 2026-07-20 (opencode / its_direct/pt3-claude-opus-4.8-1m-us): drafted; proposed 5 steps. Written
  with self-redaction discipline (no leaked literals in the plan).
