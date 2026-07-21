# IPD: Sanitizer for home paths, hostnames, and IPs (pre-commit guard + fixer + CI + one-time tree sweep)

- Date: 2026-07-20
- Concern: security / privacy hygiene (recurrence prevention) + developer experience
- Scope: new `scripts/sanitize_paths.py`; a `.pre-commit-config.yaml` hook entry; a CI check; a
  gitignored local-config template; a ONE-TIME `--fix` sweep of the current tree. NO git-history
  rewrite (that is the separate IPD `20260720-1126-01`). NO application-behavior change.
- Status: to-review
- Approval: (set when a human approves; omit until then)
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

## Findings (drivers)

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| G1 | Medium | Low | Operator | recurrence prevention | No guard stops a new `/home/<user>/`, hostname, or IP from being committed; the history-scrub only cleans the past | history-scrub IPD Step 6; `.pre-commit-config.yaml` has no such hook |
| G2 | Low | Low | Operator | local-only enforcement | Pre-commit hooks are per-clone; without a CI check a contributor who skipped `pre-commit install` bypasses the guard | `secret-scan.yml` (CI backstop pattern exists) |
| G3 | Medium | Low | Novice+Operator | current-tree state | ~35 tracked files still contain `/home/<user>/` paths; enabling the guard without cleaning them first would block ordinary commits immediately | /plan-review inventory (run record 20260720-231511) |

## Proposed changes (ordered, validatable)

| Step | Src | Change | Files | Remediation Risk | Validation |
|------|-----|--------|-------|------------------|------------|
| 1 | G1 | Write `scripts/sanitize_paths.py` (stdlib-only): `--check`/`--fix`, rulesets `home-user`/`home-any`/`hostname`/`ip`, `--scrub`/`--match`/`--replace`/`--dry-run`, consolidated end-of-run summary + allow/block footer, reading needles at runtime and from `.sanitize-local.toml`. | `scripts/sanitize_paths.py` | Low | unit-level: given fixture strings it flags/rewrites the right ones and NEVER the author name/email; `--dry-run` writes nothing |
| 2 | G1 | Ship `.sanitize-local.toml.example` (schema + commented private/doc-range whitelist sections, no literals) and add `.sanitize-local.toml` to `.gitignore`. | `.sanitize-local.toml.example`, `.gitignore` | Low | example parses; real config is gitignored (git check-ignore confirms) |
| 3 | G3 | ONE-TIME `--fix` sweep of the current tree (`/home/<user>` -> `~`, hostname -> `<host>`; IP only if enabled). Review the diff; confirm the author name/email are untouched. | many (path strings only) | Medium (functionality: touches source/tests that embed paths) | `git grep "/home/<user>"` returns zero in tree; author name/email intact (grep); FULL TEST SUITE GREEN on the swept tree (paste actual output) |
| 4 | G1 | Add the pre-commit hook entry running `sanitize_paths.py --check` on staged files (home-user/home-any/hostname by default; ip per config). | `.pre-commit-config.yaml` | Low | `pre-commit run --all-files` passes on the cleaned tree; a deliberately-added `/home/<user>/x` is blocked with the consolidated message |
| 5 | G2 | Add the same `--check` to CI (a step in `secret-scan.yml` or a sibling job) as the backstop. | `.github/workflows/secret-scan.yml` (or new) | Low | CI job fails on a seeded home-path; passes on the clean tree; matrix not implicated (lint-style check) |

## Deferred / out of scope

| Item | Risk | Axis | Reason | Later step |
|------|------|------|--------|-----------|
| Git-history rewrite of existing paths | High | functionality | Separate concern with its own gate + force-push; owned by IPD `20260720-1126-01`. This IPD only prevents recurrence and cleans the CURRENT tree. | Execute `20260720-1126-01` separately |
| Aggressive IP `--check` by default | Med-High | usability | v4/v6 regexes false-positive on versions/timings/hashes and would block most commits | IP ruleset ships but is config-gated OFF by default; enable per `.sanitize-local.toml` |

## Scope check

- Over-scope: NOT rewriting history; NOT scrubbing the author identity; IP rule gated off by default to
  avoid false-positive friction.
- Under-scope (added): the one-time tree cleanup (Step 3) is required or the hook blocks immediately (G3).

## Required tests / validation

- Script unit checks: rulesets flag/rewrite the intended categories; author name + `CITATION.cff`/
  `pyproject.toml` email NEVER matched; whitelist/blacklist (regex + glob) honored; IP rule inert unless
  enabled; consolidated summary emitted once.
- `pre-commit run --all-files` green on the cleaned tree; a seeded `/home/<user>/` line is blocked.
- CI `--check` fails on a seeded needle, passes clean.
- After Step 3: `git grep` for `/home/<user>` returns zero (tree); identity strings intact; PASTE the
  ACTUAL full test-suite output showing green.
- Honesty rule (hard MUST): paste real command output for the tree grep, the identity-intact grep, and
  the suite run; no leaked literals in any tracked file, the run record, or commit messages.

## Spec / documentation sync

- CONTRIBUTING: add a short "path/hostname hygiene" note (run `pre-commit install`; how to whitelist in
  `.sanitize-local.toml`; how to run the fixer). CHANGELOG: "Added a path/hostname/IP sanitizer
  pre-commit hook, CLI fixer, and CI check; cleaned absolute home paths from the tree (no behavior
  change)." No literals.

## Open questions

1. CI placement: extend `secret-scan.yml` with a step, or a new sibling workflow? (Recommend a step in
   `secret-scan.yml` to keep security checks together.)
2. Hostname rule in CI: a CI runner's hostname differs from the dev machine, so the auto-detected
   hostname rule is effectively a no-op in CI (home-path rules still run). Acceptable? (Recommend yes;
   the hostname guard is primarily local + the harness already redacts it.)
3. Should `home-any` (generic `/home/<anyuser>/`) be in the default `--check` set, or opt-in? It could
   flag a legitimate doc example like `/home/alice/...`. (Recommend default-on but easily whitelisted.)

## Approval and execution gate

This IPD is a proposal; it MUST be human-approved before execution and is NOT auto-run. It records only
technical rationale. Execution contract:
- Scope fence: adds the script, the example config + `.gitignore` entry, the pre-commit hook, the CI
  check, and performs the ONE-TIME tree `--fix`. It does NOT rewrite git history and does NOT push.
- Self-redaction (hard MUST): no hostname/username/IP/home-path literal in any tracked file (script,
  example config, IPD, run record) or commit message; needles are read at runtime or from the gitignored
  config.
- Honesty rule (hard MUST): paste actual output for the tree grep, identity-intact grep, and the test
  suite; never claim a clean sweep unverified.
- Commits path-scoped; never push without explicit authorization.
- On completion, `git mv` this IPD to `.agents/plans/executed/` (Status -> executed) with a
  Workflow-history line.

## Workflow history
- 2026-07-20 (opencode / its_direct/pt3-claude-opus-4.8-1m-us): drafted from the history-scrub IPD's
  Step 6 after the maintainer requested a sanitizing pre-commit hook that also scrubs unrelated-project
  home paths, with a command-line fixer (file/filter/match/replace args), auto-detected FQDN+partial
  hostname and v4/v6 IPs, a gitignored whitelist/blacklist config (regex+glob; commented private-range
  sections), IP rule config-gated, and consolidated end-of-run reporting. Proposed 5 steps, deferred 2.
