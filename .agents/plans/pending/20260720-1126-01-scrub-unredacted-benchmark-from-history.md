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

- **Hostname needle (host A):** confined to EXACTLY ONE file, the un-redacted benchmark `.json` under
  `benchmarks/results/` (whose name begins with a host label and ends `-<timestamp>.json`). The host
  label ALSO appears in that file's NAME (so it is in tree/commit metadata, not only file content).
  It has zero `<redacted>` markers.
- That benchmark `.json` was ADDED in one commit and already DELETED from the tree in a later commit
  (two commits touch it; a third touched the directory). It is gone from HEAD but its blob remains in
  history. So the rewrite target is that one path across all history.
- **Second hostname needle (host B) - added 2026-07-20:** a DIFFERENT machine's host label (the
  CURRENT dev box) was found in `TODO.md` history, embedded in a stale benchmark filename reference (a
  `benchmarks/results/<hostB>-<timestamp>.redacted.json` string in prose). It was scrubbed from the
  WORKING TREE to `<host>` (commit `f51f205`, caught by the new sanitizer's `--check`), but it REMAINS
  in the history of `TODO.md`. So there are TWO host-label needles to remove from history (host A in the
  benchmark blob, host B in TODO.md history), not one. Both are read at runtime, never written here.
- **Username needle:** NOT confined to the benchmark file. It is the maintainer's ALREADY-PUBLIC
  identity (the GitHub handle, and the published author email in `pyproject.toml` and `CITATION.cff`),
  and it appears as `/home/<user>/`-style paths in roughly 65 committed files across all history
  (many executed/pending plan files, docs, some source, and the former `src/runtrace/` tree). It is
  NOT a secret.
- `summary.csv` / `summary.md`: verified to NOT contain the hostname needle.

## Secrets sweep (run during /plan-review 2026-07-20, all clean)

Before committing to the rewrite, three checkers were run so a second rewrite would not be needed later:
- `gitleaks detect --log-opts=--all`: 397 commits scanned, NO leaks found.
- `gitleaks detect --no-git` (current tree): NO leaks found.
- `detect-secrets scan --all-files`: 127 raw hits, ALL noise once filtered to git-tracked, non-vendored
  files (the `.opencode/node_modules/` and `.agent-workflows-installer-backups/` trees are gitignored;
  the remaining 7 are false positives: the redacted benchmark's SHA token, test fixtures, and pubrun's
  own redaction TESTS whose fake inputs like `user:password@host` are asserted to be redacted).
Conclusion: the ONLY genuine disclosures in tree or history are the two known categories (a hostname,
and `/home/<user>/` absolute paths). No credential/token/key exists to rotate. No second rewrite needed.

## Scope decision (human, 2026-07-20; UPDATED to full scrub)

The maintainer's rationale: this is a front-door repo an executive-search associate (possibly with
GitHub credentials) may browse; checked-in username/hostname/absolute home paths read as sloppy hygiene,
which is a poor signal for someone leading IP-sensitive development. The email/name are deliberately
public and stay; the `/home/<user>/...` filesystem paths should not be there.

- **History + current-tree rewrite scope: FULL path scrub.** (a) Remove the one un-redacted benchmark
  `.json` entirely (the HOSTNAME carrier; path-based removal also drops the host label in its filename).
  (b) Replace the absolute prefix `/home/<user>` with `~` EVERYWHERE (all history AND the current tree),
  which anonymizes the repo path, the venv layout, and the leaked directory names of two OTHER,
  unrelated projects (one private, one public) plus a venv `src/<project>`, in ONE deterministic rule.
  (They are unrelated to pubrun; whether a given one is itself public is beside the point, their paths
  should not appear in pubrun's history.)
- **PRESERVE identity (hard invariant):** the author name and the published author email in
  `pyproject.toml` / `CITATION.cff` MUST be untouched. The replacement rule anchors on the literal
  `/home/<user>` PREFIX, so it never matches the bare name or the email; verify this explicitly.
- Force-push cost here is LOW and independent of scrub size: the remote has zero open PRs and only
  `main`, and the maintainer is the sole clone-holder; the rewrite still requires a force-push, but
  breaks no collaborator.
- Footprint (recorded for blast-radius review): current tree = 35 distinct paths across 20 files;
  history = 53 distinct paths under four top-level prefixes: the repo dir, a `venv/p3.14` tree, and two
  UNRELATED project dirs (one private, one public). The full `uniq -c` inventory is in the /plan-review
  run record. All four are handled by the single `/home/<user>` -> `~` rule. Literal dir names are kept
  out of this plan.

## Non-goals

- No application-code BEHAVIOR change (path-string replacements inside code/tests are cosmetic and must
  not alter behavior; verified by the suite going green on the rewritten HEAD).
- Not scrubbing the author name or published email (deliberately public identity; hard-preserved).
- No broader content rewrite beyond removing the one hostname file and replacing the `/home/<user>`
  path prefix. The secrets sweep found no tokens/keys, so none are in scope.

## Proposed changes (ordered, validatable)

| Step | Change | Remediation Risk | Validation |
|------|--------|------------------|------------|
| 1 | **Pre-flight sweep + secrets sweep - DONE during /plan-review.** Established the true footprint (see corrected Verified facts + the recorded `uniq -c` inventory) and confirmed via gitleaks (history + tree) and detect-secrets that no credential/token exists. Re-confirm at execution time by reading the hostname needle from a pre-rewrite copy of the target blob (never written into this plan). | Low | recorded inventory; gitleaks clean over `--all`; no credential to rotate |
| 2 | **Tool + scope (resolved OQ1).** Use `git filter-repo`. In one rewrite: (a) `--invert-paths --path <the one benchmark json>` to REMOVE the host-A carrier entirely (drops content + host-labeled filename); (b) `--replace-text <expr>` mapping the literal prefix `/home/<user>` to `~` across ALL blobs; (c) `--replace-text` ALSO mapping the host-B label (the current dev box's hostname, still in `TODO.md` history) to `<host>`. Read `<user>`, both host labels, and the target path at runtime (e.g. `socket.gethostname()` for host B); do NOT write any host literal into this plan or the committed expr file (the expr file itself is written to a gitignored/temp path, not committed). | Medium (functionality: rewrites SHAs across history) | dry-run/report shows only the target path removed and only the `/home/<user>` prefix + the two host labels rewritten; topology/commit-count otherwise unchanged |
| 3 | **Execute on a mirror-clone BACKUP first.** `git clone --mirror` backup before rewriting. Run the Step 2 filter-repo invocation on the backup. Then ALSO fix the current working tree (35 paths / 20 files) with the same `/home/<user>` -> `~` replacement so HEAD is clean, not just history. Verify on the rewritten copy before touching the remote. | Medium-High (functionality: irreversible without the backup) | post-rewrite: `git log --all -- <benchmark path>` empty; hostname needle (field AND filename token) absent from all history; `git grep "/home/<user>"` over `--all` returns ZERO; the author name/email are UNCHANGED (grep confirms still present in pyproject.toml/CITATION.cff); test suite green on rewritten HEAD |
| 4 | **Force-push the rewritten history** to the remote (all refs). **REQUIRES the explicit out-of-band human GO named in the gate; not waived by approving this IPD.** Cost is low here (no open PRs; only `main`; sole maintainer) but it is irreversible on the remote. | High (operational: rewrites public history) | remote has no benchmark path, no hostname needle, and zero `/home/<user>` hits; a fresh clone is clean; author identity intact; GitHub cached views update eventually |
| 5 | **Post-rewrite hygiene.** No credential to rotate (sweep clean). Confirm recurrence prevention: the `benchmarks/results/.gitignore` (tracks only `*.redacted.json`) and the harness hostname redaction are in place. | Low | `.gitignore` + harness redaction confirmed; a fresh unredacted run is not committed |
| 6 | **Going-forward guard for home paths (recurrence prevention).** Add a small local guard (a pre-commit hook / lint) that flags newly-added `/home/<user>/` or `file:///home/` absolute paths in authored files, so the scrubbed state does not regress. May be split into its own tiny follow-up IPD. | Low (usability) | a fresh commit adding a `/home/<user>/` absolute path is flagged locally before commit |

## Anti-regression / invariants

- The ONLY changes are: (a) removal of the one benchmark `.json`, and (b) replacement of the literal
  `/home/<user>` prefix with `~` in blob contents. NO other byte should change. Verify by diffing the
  rewritten HEAD tree against the original with the same `/home/<user>` -> `~` transform applied, so the
  only residual differences are the removed file. Test suite MUST be green on the rewritten HEAD (watch
  test fixtures / tests that embed absolute paths, e.g. `test_cli.py`, `test_status.py`).
- HARD PRESERVE: author name and published email in `pyproject.toml` / `CITATION.cff` unchanged (the
  replacement anchors on the `/home/<user>` prefix, never the bare token); grep-confirm post-rewrite.
- Preserve authorship/dates of surviving commits (`filter-repo` does by default).

## Required tests / validation

- `git log --all --name-only -- <the one benchmark json path>` returns nothing after the rewrite.
- A history-wide search for the HOST-A needle - BOTH the `machine.host.hostname` field value AND the
  host-label token embedded in the filename - read from a pre-rewrite copy, returns zero hits across
  all commits.
- A history-wide search for the HOST-B needle (the current dev box's hostname, e.g. from
  `socket.gethostname()`; it lingers in `TODO.md` history) returns zero hits across all commits.
- A history-wide AND current-tree search for `/home/<user>` returns ZERO hits after the rewrite.
- The author name and published email STILL appear in `pyproject.toml` and `CITATION.cff` (identity
  preserved; grep-confirm the exact lines are intact).
- Full test suite green on the rewritten HEAD (watch tests/fixtures that embed absolute paths).
- The remote reflects the rewrite (fresh clone is clean of the hostname needle and of `/home/<user>`).

## Spec / documentation sync

- None in application behavior. Add a short note to `CHANGELOG` (without literals): "Rewrote git history
  to remove an un-redacted benchmark result and to replace absolute home-directory paths with `~`;
  benchmark results now track only redacted artifacts." (No hostname/path literals in the note.)
- If the project keeps a security/incident log, record the remediation there (again, no literals).

## Open questions (all RESOLVED during /plan-review 2026-07-20)

1. **Tool:** RESOLVED - `git filter-repo`: `--invert-paths` for the benchmark file removal PLUS
   `--replace-text` for the `/home/<user>` -> `~` prefix substitution, in one rewrite.
2. **Timing / coordination:** RESOLVED - safe now: `gh pr list` shows zero open PRs, the only branch is
   `main`, and the maintainer is the sole clone-holder. No collaborator is broken by the force-push.
3. **Sweep scope / secrets pass:** RESOLVED - a full secrets sweep (gitleaks over `--all` + detect-secrets)
   was run during review and is CLEAN; no tokens/keys in tree or history. No separate pass needed first.
4. **Scope of the scrub?** RESOLVED (human, 2026-07-20, UPDATED to FULL scrub): remove the hostname file
   AND replace `/home/<user>` with `~` across all history and the current tree, catching the repo path,
   venv layout, and two unrelated project dirs. PRESERVE the author name/email (anchored prefix rule
   never matches them). Rationale: a front-door repo for reviewers with GitHub access; checked-in
   absolute home paths read as sloppy hygiene. (This supersedes the earlier hostname-only scoping.)

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution and is NOT
auto-executed. **Because it rewrites history and force-pushes, it additionally requires an EXPLICIT,
out-of-band human GO for the force-push (Step 4)** - the standing "never push / never force-push
without approval" rule is not waived by this plan's existence, and generic plan approval does NOT
by itself authorize Step 4. Execution contract:
- Scope fence: the rewrite does exactly two things: (a) remove the one un-redacted benchmark `.json`,
  and (b) replace the literal `/home/<user>` prefix with `~` in all blobs (history) and the working
  tree. NOTHING else changes; the author name/email are hard-preserved. Steps 1-3 and 5-6 are
  non-destructive to the remote and may proceed on ordinary approval; ONLY Step 4 (force-push) needs
  the separate explicit GO.
- Take a full `git clone --mirror` backup before any rewrite (Step 3); verify on the copy first.
- Honesty rule (hard MUST): paste ACTUAL command output (dry-run reports, post-rewrite verification,
  the `/home/<user>` grep returning zero, the identity-preserved grep) when reporting; never claim a
  scrub succeeded that was not verified.
- Do NOT write any leaked literal (hostname, or the committed `--replace-text` expr file) into commits,
  the run record, or this plan; read `<user>` and the target path at runtime.
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
  Readiness: NO-GO until human approval AND the separate explicit force-push GO for Step 4.
- 2026-07-20 scope revised (human, during /plan-review): UPGRADED from hostname-only to a FULL scrub -
  remove the hostname file AND replace `/home/<user>` -> `~` across all history and the working tree
  (catching the repo path, venv layout, and two unrelated project dirs, one private and one public),
  while HARD-PRESERVING the author name/email. Rationale recorded: front-door repo for reviewers with
  GitHub access; absolute home paths read as sloppy hygiene. Ran a full secrets sweep first (gitleaks
  over --all + detect-secrets): CLEAN, no tokens/keys, so no second rewrite will be needed. Updated the
  Scope decision, Verified facts, Non-goals, Steps 2-3 and 6, anti-regression, validation, gate, and
  spec-sync accordingly. Still Status: reviewed; still NO-GO pending human approval + the Step 4 GO.
  Readiness: NO-GO until (a) human approval AND (b) the separate explicit force-push GO for Step 4.
- 2026-07-20 scope addition (human): the sanitizer IPD (20260720-2331-01) execution surfaced a SECOND
  host label (the current dev box) leaked in `TODO.md` history via a stale benchmark filename. It was
  scrubbed from the working tree (commit f51f205) but persists in history. Added it as "host B" to the
  Verified facts, Step 2 rewrite scope (a second `--replace-text` mapping to `<host>`), and validation
  (a history-wide zero-hit check for host B). No re-review required by the human beyond this note; the
  scope grew by one additional replace-text needle of the same kind already planned. Status unchanged.
