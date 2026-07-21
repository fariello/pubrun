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
- **Why the one-time tree sweep must ship WITH the hook.** ~35 tracked files currently contain
  `/home/<user>/` paths. If the hook were added without first cleaning them, the author's very next
  commit touching any of those files would be blocked, so the guard would arrive broken. Cleaning the
  tree and enabling the guard are one coherent change.
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
