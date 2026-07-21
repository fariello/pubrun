# IPD: Sanitizer for home paths, hostnames, and IPs (pre-commit guard + fixer + CI + one-time tree sweep)

- Date: 2026-07-20
- Concern: security / privacy hygiene (recurrence prevention) + developer experience
- Scope: new `scripts/sanitize_paths.py`; a `.pre-commit-config.yaml` hook entry; a CI check; a
  gitignored local-config template; a ONE-TIME `--fix` sweep of the current tree. NO git-history
  rewrite (that is the separate IPD `20260720-1126-01`). NO application-behavior change.
- Status: executed
- Approval: human-approved 2026-07-20 (maintainer "GO" after /plan-review)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## SELF-REDACTION NOTICE (read first)

This plan is a COMMITTED, public file. It refers to the machine hostname, the OS username, and IP
addresses ONLY by category, never by literal value. The sanitizer reads those needles at RUNTIME
(auto-detected) or from a GITIGNORED local config, never from tracked files. Do not paste any literal
hostname, username, home path, or IP into this plan, the script, the run record, or commit messages.

## Goal

Prevent recurrence of the hygiene issues the history-scrub IPD (`20260720-1126-01`) addresses: absolute
`/home/<user>/` paths, the machine hostname, and (optionally) IP addresses landing in committed files.
Provide (a) a blocking pre-commit guard so new leaks cannot be committed, (b) a command-line fixer to
sanitize on demand, (c) a CI backstop for contributors who did not install the local hook, and (d) a
one-time cleanup of the current tree so the guard does not immediately block ordinary work. This is the
"going-forward guard" (Step 6) of the history-scrub IPD, promoted to its own plan. Rationale is purely
technical: hygiene, recurrence prevention, and reviewer-facing polish.

## Why (rationale, for a cold reader)

The reasoning behind the specific design choices, so an executor need not reconstruct it:

- **Why a guard at all, separate from the history rewrite.** The history-scrub IPD removes existing
  leaks but does nothing to stop the NEXT one. Absolute developer paths recur naturally: agent tools
  and IDEs paste `file:///home/<user>/...` links into plan/doc Markdown, tracebacks and test fixtures
  embed absolute paths, and benchmark/capture output records the host. Without a standing guard the
  tree re-accumulates exactly what the rewrite just removed. A guard is the durable half of the fix; the
  rewrite is the one-time half.
- **Why block, not auto-rewrite, in the commit hook.** A hook that silently mutates staged source is
  genuinely risky: an absolute path can be MEANINGFUL inside code or a test (a fixture, an expected
  output assertion, a config default). Rewriting it under the author can silently change behavior and
  turn tests red after the commit lands, and it surprises the author by editing files out from under
  them. The safe, conventional choice (this is how the existing gitleaks hook behaves) is detect and
  reject, with the author making the edit. Convenience is provided instead by an explicit, opt-in CLI
  fixer (`--fix`) the author runs deliberately, plus `--dry-run` to preview.
- **Why anchor rules on the `/home/<user>` PREFIX, never the bare username token.** The maintainer's
  username also legitimately appears as the author name and the published author email in
  `pyproject.toml` and `CITATION.cff`. Those are intentional, public identity and MUST be preserved;
  scrubbing them would corrupt package metadata and is self-defeating (the identity is public by
  design). Anchoring every rule on the `/home/<user>` path prefix means the rules match filesystem
  paths only and never touch the name or email. This is a hard invariant, not a nicety.
- **Why one anchored path rule instead of enumerating project names.** The leaked paths include not
  just this repo but a virtualenv tree and the directories of two OTHER, unrelated projects (one
  private, one public) that happen to live under the same home. A single `/home/<user>` -> `~` rule
  scrubs all of them, plus anything future, in one deterministic pass, WITHOUT naming any project in a
  committed file (which would itself be a small leak). `home-any` (`/home/<anyuser>/`) extends the same
  logic to contributor paths.
- **Why the IP ruleset is config-gated OFF by default.** IPv4/IPv6 regexes false-positive heavily on
  ordinary content: version numbers (`1.2.3.4`), benchmark timings (this repo's `pass_results` are full
  of decimal sequences), hashes, dependency pins, and `::` in code. An always-on IP `--check` would
  block nearly every commit and make the hook be disabled in frustration, defeating the whole guard.
  Shipping it available-but-off, with a whitelist that pre-covers private and documentation ranges, is
  what keeps the guard usable while still offering IP scrubbing to those who want it.
- **Why the one-time tree sweep must ship WITH the hook.** 20 tracked files currently contain
  `/home/<user>/` paths (35 distinct path STRINGS across them). If the hook were added without first
  cleaning them, the author's very next commit touching any of those files would be blocked, so the
  guard would arrive broken. Cleaning the tree and enabling the guard are one coherent change.
- **Why a consolidated end-of-run summary rather than per-hit messages.** Per-line output on a
  multi-file scan is noise; a single grouped summary with a one-time "how to allow/block" footer is what
  a developer can actually act on, and it keeps CI logs readable.
- **Why stdlib-only.** pubrun is a zero-runtime-dependency library; a hygiene tool that dragged in a
  dependency would contradict the project's own defining constraint. `re`, `ipaddress`, `socket`,
  `pathlib`, `tomllib`/`tomli`, and `argparse` cover everything needed.

## Portability note (upstream candidate for agent-workflows)

Nothing in this design is pubrun-specific except a couple of defaults. The same script + hook + CI check
+ example-config pattern is useful in ANY repository (absolute home paths and hostnames in committed
files are a near-universal hygiene issue, especially in agent-assisted repos where tools paste
`file:///home/...` links). This IPD was accompanied by a message to the `agent-workflows` project
proposing that an equivalent be offered as an OPTIONAL component of `setup-repo` / the installer. If
agent-workflows ships a canonical version, pubrun should prefer adopting/tracking that over maintaining
a private fork, keeping only local config in `.sanitize-local.toml`.

## Project conventions discovered (Step 0)

- Stack: zero-runtime-dependency Python library; the sanitizer MUST be stdlib-only to match that ethos.
- Existing local hooks: `.pre-commit-config.yaml` already runs gitleaks + end-of-file/trailing-whitespace
  fixers + check-yaml/toml + large-file guard. New hook follows that pattern (local, per-clone; each
  contributor runs `pre-commit install`).
- CI: `.github/workflows/secret-scan.yml` runs gitleaks over history; the new `--check` fits there or as
  a sibling step/job.
- House rules (`AGENTS.md`): no em/en dashes in authored Markdown; path-scoped commits; never push
  without authorization; every claim checkable.
- Plans: `.agents/plans/pending/`, `YYYYMMDD-HHMM-NN-<slug>.md`, front-matter `Status:`.

## Design

### One script, two modes: `scripts/sanitize_paths.py` (stdlib only)

- `--check` (hook/CI mode): scan the given files (default: staged files) for un-whitelisted needles;
  print a SINGLE consolidated summary at the end (grouped by rule, with `file:line`), then a one-time
  footer explaining how to allow/block; exit non-zero if any un-whitelisted needle is found. Never
  mutates.
- `--fix` (manual mode): rewrite matches in place and re-stage (when run against staged files).
- Args: `[files ...]` (optional; default staged, or `--all` for all tracked); `--scrub <ruleset>`
  (repeatable; choose which rules run, default = the configured default set); `--match <regex>` +
  `--replace <str>` (custom one-off rule, bypasses defaults); `--dry-run` (show diffs, write nothing).

### Rulesets (each anchored so it never matches the author name/email)

| Ruleset | Detects | Default replacement | Default in `--check`? |
|---------|---------|---------------------|-----------------------|
| `home-user` | the current user's `/home/<user>` prefix (from `$HOME`) | `~` | yes |
| `home-any`  | generic `/home/<anyuser>/` | `~/` | yes |
| `hostname`  | auto-detected FQDN AND short label (`socket.getfqdn()`, `socket.gethostname()`, and the label before the first dot) | `<host>` | yes |
| `ip`        | syntactically valid IPv4 and IPv6 addresses | `<ip>` | **config-gated (off unless enabled)** |

### Config (`.sanitize-local.toml`, GITIGNORED) - the allow/block model

- The repo ships a COMMITTED template `.sanitize-local.toml.example` (no literals) documenting the schema;
  the real `.sanitize-local.toml` is gitignored so machine-specific literals never get committed.
- Keys:
  - `ip.enabled = false` (default): master on/off for the IP ruleset.
  - `whitelist` and `blacklist`: each a list accepting BOTH regex and glob entries (a prefix or
    per-entry `type = "regex"|"glob"|"literal"` marks which; default glob). Whitelisted matches are
    never flagged; blacklisted extra needles are always flagged/scrubbed.
  - The template includes COMMENTED-OUT whitelist sections for private / non-Internet-routable ranges
    (loopback `127.0.0.0/8`, `::1`; RFC1918 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`;
    link-local `169.254.0.0/16`, `fe80::/10`; documentation `192.0.2.0/24`, `198.51.100.0/24`,
    `203.0.113.0/24`, `2001:db8::/32`) that the user can uncomment to whitelist.
- No env-var needle injection (the config covers it); a single toggle env var MAY exist only to switch
  `--check` into fix-and-restage for a given run, if desired (optional, low priority).

### UX (consolidated reporting)

Collect all findings across all scanned files, then emit ONE summary at the end: grouped by rule, each
with `file:line` and the matched CATEGORY (never the raw secret in CI logs where possible). End with a
SINGLE footer: how to whitelist (add to `.sanitize-local.toml`), how to blacklist, and how to run the
fixer. No per-hit spam.

### Implementation details (implicit decisions, made explicit)

- **Hostname detection specifics:** derive up to three needles at runtime and match any: the FQDN
  (`socket.getfqdn()`), the node name (`socket.gethostname()`), and the SHORT label (everything before
  the first `.` of either). Matching both FQDN and short label is deliberate: capture output may embed
  either form. All are auto-detected, never written into a tracked file. In CI the runner's hostname
  differs from a dev machine, so the hostname rule is effectively inert there (by design; home-path
  rules still run, and the benchmark harness already SHA-tokenizes the hostname in redacted output).
- **How `--check` reads content:** default target is the STAGED blob content (what will actually be
  committed), obtained via `git diff --cached` / `git show :<path>`, not the working-tree file, so the
  guard judges exactly what is being committed. `--all` scans all tracked files (for the CI backstop and
  ad-hoc audits). Explicit `[files ...]` overrides both.
- **Exit-code semantics:** `--check` exits `0` when clean, non-zero when any un-whitelisted needle is
  found (so it works as a pre-commit and CI gate). `--fix` exits `0` after rewriting (and, in hook
  context, re-stages the fixed files); `--dry-run` always exits `0` and only prints proposed diffs.
- **Config schema (`.sanitize-local.toml`):** stdlib TOML (`tomllib` on 3.11+, `tomli` fallback,
  matching pubrun's existing dependency shape). Shape (illustrative, no literals):
  `[rules] enabled = ["home-user","home-any","hostname"]`; `[ip] enabled = false`;
  `[[whitelist]] type = "glob"|"regex"|"literal"; pattern = "..."`; `[[blacklist]] type = ...; pattern
  = ...; replace = "..."`. Whitelist entries suppress a match; blacklist entries add always-scrub
  needles with an optional per-entry replacement. Missing config = defaults (home rules + hostname on,
  IP off, empty allow/block lists).
- **Replacement safety:** replacements are literal-string substitutions on a matched span, not
  free-form regex backrefs in the default rules, to avoid accidental broadening. Custom `--match`/
  `--replace` allows backrefs for power users, explicitly opt-in per run.
- **Ordering vs. other hooks:** place the `--check` hook AFTER the whitespace/EOF fixers and gitleaks in
  `.pre-commit-config.yaml` so it evaluates the final staged bytes; it is independent of gitleaks (which
  targets secrets, not hygiene paths) and complements it.

## Findings (drivers)

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| G1 | Medium | Low | Operator | recurrence prevention | No guard stops a new `/home/<user>/`, hostname, or IP from being committed; the history-scrub only cleans the past | history-scrub IPD Step 6; `.pre-commit-config.yaml` has no such hook |
| G2 | Low | Low | Operator | local-only enforcement | Pre-commit hooks are per-clone; without a CI check a contributor who skipped `pre-commit install` bypasses the guard | `secret-scan.yml` (CI backstop pattern exists) |
| G3 | Medium | Low | Novice+Operator | current-tree state | 20 tracked files (35 distinct path strings) still contain `/home/<user>/` paths; enabling the guard without cleaning them first would block ordinary commits immediately | /plan-review inventory (run record 20260720-231511); `git grep -l "/home/<user>"` = 20 |
| G4 | Medium | Low | QA/Operator | test coverage | The script's whole job is correctness of match/replace and the hard "never match the author name/email" invariant, but no COMMITTED test guards it; a future edit could silently break the identity-preservation anchor | added during /plan-review (PR-002) |

## Proposed changes (ordered, validatable)

| Step | Src | Change | Files | Remediation Risk | Validation |
|------|-----|--------|-------|------------------|------------|
| 1 | G1 | Write `scripts/sanitize_paths.py` (stdlib-only): `--check`/`--fix`, rulesets `home-user`/`home-any`/`hostname`/`ip`, `--scrub`/`--match`/`--replace`/`--dry-run`, consolidated end-of-run summary + allow/block footer, reading needles at runtime and from `.sanitize-local.toml`. | `scripts/sanitize_paths.py` | Low | see Step 2 (committed tests); `--dry-run` writes nothing |
| 2 | G4 | Write `tests/test_sanitize_paths.py` (REQUIRED deliverable, PR-002): assert each ruleset flags/rewrites its category; the HARD invariant that a `/home/<user>`-anchored rule NEVER matches the author name `Gabriele Fariello` or `gfariello@fariel.com` (feed those exact strings and assert unchanged); whitelist/blacklist honored for regex AND glob AND literal entries; `ip` ruleset inert unless `[ip] enabled=true`; the consolidated summary is emitted exactly once; `--check` exit codes (0 clean, non-zero on match); `--dry-run` mutates nothing. | `tests/test_sanitize_paths.py` | Low | the new tests pass in the existing suite / CI |
| 3 | G1 | Ship `.sanitize-local.toml.example` (schema + commented private/doc-range whitelist sections, no literals) and add `.sanitize-local.toml` to `.gitignore`. | `.sanitize-local.toml.example`, `.gitignore` | Low | example parses (tomllib/tomli); real config is gitignored (`git check-ignore` confirms) |
| 4 | G3 | ONE-TIME `--fix` sweep of the current tree (`/home/<user>` -> `~`, hostname -> `<host>`; IP only if enabled). This touches SOURCE and TEST files (per the inventory: `src/pubrun/__main__.py`, `status.py`, `tracker.py`, `resources/default.toml`, several `tests/test_*.py`), so INSPECT the source/test diff specifically for any absolute path that is behaviorally meaningful (a config default, an expected-output assertion, a fixture) before accepting; do not rely on the suite alone. Commit this sweep SEPARATELY from the tooling (PR-004) so the many-file diff is reviewable on its own. | many (path strings only) | Medium (functionality: touches source/tests that embed paths) | `git grep "/home/<user>"` returns zero in tree; author name/email intact (grep `pyproject.toml:12`, `CITATION.cff:10`); source/test diff manually inspected; FULL TEST SUITE GREEN on the swept tree (paste actual output) |
| 5 | G1 | Add the pre-commit hook entry running `sanitize_paths.py --check` on staged files (home-user/home-any/hostname on by default per OQ3; ip per config). Order it AFTER the whitespace/EOF fixers and gitleaks so it sees final staged bytes. | `.pre-commit-config.yaml` | Low | `pre-commit run --all-files` passes on the cleaned tree; a deliberately-added `/home/<user>/x` is blocked with the consolidated message |
| 6 | G2 | Add the same `--check --all` as a STEP in the existing `secret-scan.yml` (OQ1: keep security checks together, not a new workflow). | `.github/workflows/secret-scan.yml` | Low | CI step fails on a seeded home-path; passes on the clean tree; not a matrix concern (lint-style check) |

## Deferred / out of scope

| Item | Risk | Axis | Reason | Later step |
|------|------|------|--------|-----------|
| Git-history rewrite of existing paths | High | functionality | Separate concern with its own gate + force-push; owned by IPD `20260720-1126-01`. This IPD only prevents recurrence and cleans the CURRENT tree. | Execute `20260720-1126-01` separately |
| Aggressive IP `--check` by default | Med-High | usability | v4/v6 regexes false-positive on versions/timings/hashes and would block most commits | IP ruleset ships but is config-gated OFF by default; enable per `.sanitize-local.toml` |

## Scope check

- Over-scope: NOT rewriting history; NOT scrubbing the author identity; IP rule gated off by default to
  avoid false-positive friction.
- Under-scope (added): the one-time tree cleanup (Step 4) is required or the hook blocks immediately
  (G3); a committed test (Step 2) is required to guard the identity-preservation invariant (G4/PR-002).

## Required tests / validation

- `tests/test_sanitize_paths.py` (Step 2, committed): rulesets flag/rewrite the intended categories; the
  author name and `pyproject.toml`/`CITATION.cff` email are fed in and asserted NEVER matched;
  whitelist/blacklist honored for regex + glob + literal; IP rule inert unless enabled; consolidated
  summary emitted exactly once; `--check` exit codes; `--dry-run` mutates nothing.
- `pre-commit run --all-files` green on the cleaned tree; a seeded `/home/<user>/` line is blocked with
  the consolidated message.
- CI `--check --all` step (in `secret-scan.yml`) fails on a seeded needle, passes clean.
- After the Step 4 sweep: `git grep "/home/<user>"` returns zero (tree); identity strings intact
  (grep `pyproject.toml:12`, `CITATION.cff:10`); the SOURCE/TEST diff manually inspected for meaningful
  absolute paths; PASTE the ACTUAL full test-suite output showing green.
- Honesty rule (hard MUST): paste real command output for the tree grep, the identity-intact grep, and
  the suite run; no leaked literals in any tracked file, the run record, or commit messages.

## Spec / documentation sync

- CONTRIBUTING: add a short "path/hostname hygiene" note (run `pre-commit install`; how to whitelist in
  `.sanitize-local.toml`; how to run the fixer). CHANGELOG: "Added a path/hostname/IP sanitizer
  pre-commit hook, CLI fixer, and CI check; cleaned absolute home paths from the tree (no behavior
  change)." No literals.

## Open questions (all RESOLVED during /plan-review 2026-07-20)

1. CI placement: RESOLVED - add the check as a STEP in the existing `secret-scan.yml` (keep security
   checks together), not a new workflow. (Step 6.)
2. Hostname rule in CI: RESOLVED - accepted as a no-op in CI (runner hostname differs; home-path rules
   still run; the harness already SHA-tokenizes the hostname). No change needed.
3. `home-any` default: RESOLVED - default-ON in `--check`; a legitimate doc example like `/home/alice/`
   is handled by adding it to the whitelist. (Step 5.)

## Approval and execution gate

This IPD is a proposal; it MUST be human-approved before execution and is NOT auto-run. It records only
technical rationale. Execution contract:
- Resolved open questions: OQ1-OQ3 resolved above; execute to those decisions.
- Scope fence: adds `scripts/sanitize_paths.py`, `tests/test_sanitize_paths.py`, the example config +
  `.gitignore` entry, the pre-commit hook, the `secret-scan.yml` CI step, and performs the ONE-TIME tree
  `--fix`. It does NOT rewrite git history and does NOT push. Anything outside this fence -> STOP and
  open a separate IPD.
- Commit separation (PR-004): commit the tooling (script + test + config + hook + CI) separately from
  the many-file one-time tree sweep, so each diff is reviewable.
- Identity invariant (hard MUST): the author name and email at `pyproject.toml:12` / `CITATION.cff:10`
  MUST be byte-unchanged after the sweep; grep-confirm and the committed test guards it.
- Self-redaction (hard MUST): no hostname/username/IP/home-path literal in any tracked file (script,
  example config, IPD, run record) or commit message; needles are read at runtime or from the gitignored
  config. NOTE: the committed test (Step 2) may reference the PUBLIC author name/email (they are already
  public in `pyproject.toml`/`CITATION.cff`) solely to assert they are NOT scrubbed; it must NOT contain
  any private hostname/home-path literal.
- Honesty rule (hard MUST): paste actual output for the tree grep, the identity-intact grep, the
  source/test-diff inspection, and the test suite; never claim a clean sweep unverified.
- Commits path-scoped; never push without explicit authorization.
- On completion, `git mv` this IPD to `.agents/plans/executed/` (Status -> executed) with a
  Workflow-history line.

## Workflow history
- 2026-07-20 (opencode / its_direct/pt3-claude-opus-4.8-1m-us): drafted from the history-scrub IPD's
  Step 6 after the maintainer requested a sanitizing pre-commit hook that also scrubs unrelated-project
  home paths, with a command-line fixer (file/filter/match/replace args), auto-detected FQDN+partial
  hostname and v4/v6 IPs, a gitignored whitelist/blacklist config (regex+glob; commented private-range
  sections), IP rule config-gated, and consolidated end-of-run reporting. Proposed 5 steps, deferred 2.
- 2026-07-20 enriched (opencode): added Why/Portability/Implementation-details sections for cold-start
  self-containment.
- 2026-07-20 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS
  APPLIED. Verified claims (gitleaks+fixers present with no path hook; `secret-scan.yml` exists; author
  identity at `pyproject.toml:12`/`CITATION.cff:10`; `tomli` fallback at `pyproject.toml:40`). Findings:
  PR-001 file count corrected (20 files, not ~35 - that was distinct path strings); PR-002 added a
  REQUIRED committed test (`tests/test_sanitize_paths.py`, new Step 2 + finding G4) to guard the
  identity-preservation invariant; PR-003 sharpened the sweep step to require inspecting the SOURCE/TEST
  diff, not just a green suite; PR-004 required committing the tooling separately from the tree sweep.
  All 3 open questions resolved (CI step in secret-scan.yml; hostname no-op in CI accepted; home-any
  default-on). Now 6 steps, 2 deferred. Status -> reviewed. Readiness: GO - PENDING HUMAN APPROVAL.
- 2026-07-20 executed (opencode / its_direct/pt3-claude-opus-4.8-1m-us) after human "GO". Commit A
  (d3107ab): script + tests (19 pass) + example config + gitignore. Commit B (eed0ca1): one-time sweep
  of 20 files (/home/<user> -> ~), verified 80/80 balanced path-only diff, no source/test touched, full
  suite 926 passed / 2 skipped. Commit C (f51f205): pre-commit hook + CI step; plus two refinements
  found by running the tool: (1) a TRACKED baseline `.sanitize-allow.toml` (so CI shares the
  known-legitimate generic placeholders) with `exclude` support for the tool's own self-test; (2) the
  tool caught a REAL hostname leak in TODO.md (a stale benchmark filename) which was scrubbed to <host>.
  `--check --all` exits 0 clean; the sanitize-paths pre-commit hook passed on its own commit. CONTRIBUTING
  + CHANGELOG updated. Deferred items unchanged (history rewrite = IPD 20260720-1126-01; aggressive IP
  default stays off). Status -> executed; git mv pending/ -> executed/. NOT pushed.
