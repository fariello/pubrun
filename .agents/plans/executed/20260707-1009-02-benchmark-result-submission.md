# IPD: low-friction, consent-gated benchmark result submission

- Date: 2026-07-07
- Concern: usability / community data collection. Lower the bar to *submitting* a
  `pubrun bench` result as close to zero as possible — without ever transmitting anything
  the user did not explicitly consent to in that invocation. Builds directly on IPD-C
  (`20260706-easy-benchmark-and-hpc-submit.md`), which produces the redacted share artifact
  but leaves submission fully manual (attach JSON to a GitHub issue).
- Scope: `src/pubrun/__main__.py` (`pubrun bench` submission flow + new `--submit <file>`
  path + submission-method helpers), a small verifier in `benchmarks/harness.py` (or a
  helper reused by the CLI) to confirm a file is redacted, docs, tests. **No change to
  `import pubrun` runtime behavior. No new runtime dependency. No server.** The benchmark
  tooling remains dev/source-checkout only (not shipped in the wheel).
- Status: PENDING (proposal only; human approval required; NOT auto-executed).
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

IPD-C made *running* the benchmark trivial (`pubrun bench`) and produces a redacted,
share-safe `.redacted.json`. But *submitting* it is still: find the file, open a browser,
create a GitHub issue, attach the file. Every one of those steps loses contributors. The
JOSS paper needs a multi-system dataset; the friction between "I ran it" and "you have my
data point" is where that dataset dies.

We want submission to be as low-friction as running — an interactive offer at the end of the
run — while holding pubrun's hard line: **it must never transmit anything without an explicit
yes in that invocation, must never require infrastructure to function, and must degrade
gracefully to manual instructions when any automated path is unavailable.**

## Project conventions discovered (Step 0)

- Principles: zero runtime deps (only `tomli` on <3.11), KISS, no `rich`, honest docs, never
  intrude on/slow/break the host script, degrade gracefully, no surprise network calls.
- IPD-C artifacts (verified in tree):
  - `_run_bench` at `src/pubrun/__main__.py:903`; share guidance `_print_share_guidance`
    at `:889`; `_BENCH_SUBMIT_URL` now the real `…/pubrun-benchmarks/issues/new` (updated
    this session, uncommitted at time of writing).
  - `benchmarks/harness.py`: `redact_result` (`:395`), `--redacted-out` (`:432`), redaction
    key sets `_REDACT_KEYS`/`_REDACT_LIST_KEYS` (`:353`), schema `pubrun-benchmark/3`.
  - The full result is written to `benchmarks/results/<host>-<ts>.json` and the redacted
    copy to `…-<ts>.redacted.json` **before** any prompt — so the artifact persists
    regardless of the submit decision (this is what makes "submit later" free).
- Slurm invocation already uses an argv list, never `shell=True` (`_run_bench` `:922-946`).
- Plans: `.agents/plans/pending/` → `executed/`, `YYYYMMDD-<slug>.md`.

## Design decisions (agreed with maintainer, 2026-07-07)

These were settled in discussion before drafting:

- **Consent is the invariant, not the transport.** An API POST, a `gh` call, and a
  (hypothetical) server all equally "cause data to leave the machine." What protects the
  tenet is explicit consent + transparency + graceful degradation, NOT which transport is
  used. So the design is organized around an interactive consent gate with a probe-first
  fallback chain, and the transport is an implementation detail.
- **Interactive offer is primary; flags are the override/CI escape hatch.** At the end of a
  local run, `pubrun bench` OFFERS to submit. This is more naive-user-resistant than a
  `--print` flag the user has to know about.
- **Transmit prompt defaults to NO (`[y/N]`).** Pressing Enter must NEVER upload. The
  separate "print a ready-to-paste version?" prompt may default YES (`[Y/n]`) because
  printing is local and harmless. `--submit`/`--yes` provide explicit non-interactive
  consent (CI); `--no-submit` forces the manual path.
- **Redacted-by-default; `--no-redact` is a deliberate footgun** (unchanged from IPD-C).
- **Fallback chain = probe `gh` → HTTP-to-GitHub-Issues (stdlib `urllib`) → printed floor.**
  No server (maintainer chose "gh + HTTP-to-GitHub-issues (no server)"). Both automated paths
  file a real GitHub issue, so the submitter needs a GitHub account — this is the honest
  limitation and must be documented (GitHub has **no** anonymous-issue mechanism; the only
  account-free route would be a server, which was NOT chosen). The printed floor always works.
- **`requests` is a no-op preference, not a dependency.** `urllib` (stdlib) is always
  available and is the real HTTP baseline; if `requests` happens to be importable we may
  prefer it for ergonomics, but we NEVER declare it and NEVER require it. Practically the
  meaningful branch is gh-vs-HTTP, not urllib-vs-requests.
- **"Oh no, I meant yes" recovery = `pubrun bench --submit <file>`.** Because the redacted
  file already persists on disk, recovery is not "re-run" (slow, and scientifically wrong —
  re-running produces *different* numbers than the ones the user just approved) and not a new
  top-level command (surface area). It is a second entry point into the same submission chain
  that submits an existing file. The exact command is printed when the user declines the
  interactive offer.
- **`--submit <file>` doubles as the HPC path.** A Slurm compute node often has no TTY and no
  outbound network / no `gh`; it writes the redacted file, and the user later runs
  `pubrun bench --submit <that file>` from the login node. Recovery and HPC are the same code.

## Proposed changes

1. **Interactive submit offer at end of a local `pubrun bench` run** (in `_run_bench`, after
   the redacted copy is written). Replaces the current print-only `_print_share_guidance`
   for the interactive case:
   - Print the full + redacted paths and the what-is-masked/preserved summary (keep IPD-C's
     honest disclosure).
   - Prompt `Contribute this redacted result to help verify pubrun's overhead claims? [y/N]`.
     - **No / Enter / non-interactive-without-`--submit`:** print the exact recovery command
       (`pubrun bench --submit "<redacted path>"`, shell-quoted) and the manual URL, then
       return. Never sends. **If `--no-redact` was set** (no redacted file exists), the
       recovery guidance instead tells the user to re-run without `--no-redact` (or points at
       the full file with the un-redacted caveat), rather than printing a `--submit` command
       for a file that would be refused.
     - **Yes:** run the fallback chain (change 3).
   - `--submit`/`--yes` skips the prompt and proceeds to the chain (explicit consent).
     `--no-submit` skips straight to printing the recovery command + URL.

2. **New `pubrun bench --submit [FILE]` path** (recovery / HPC / batch):
   - `--submit` with a FILE argument submits that existing file (recovery/HPC). `--submit`
     with NO argument keeps its current IPD-C meaning inside a local/Slurm run (submit the
     freshly produced result / trigger Slurm submit) — so the flag is now
     `nargs="?"`-style: bare `--submit` = "yes, submit what this run produces"; `--submit
     <file>` = "submit this specific file, no benchmark run." **This dual meaning must be
     called out** because `--submit` already exists (IPD-C, `__main__.py:1602`) as a
     store_true for Slurm; changing it to optionally take a value is a deliberate,
     backward-compatible widening (bare `--submit` behavior is preserved). Verify argparse
     handles `nargs="?"` here without ambiguity against the positional/other flags; if it is
     ambiguous, use a separate `--submit-file <path>` flag instead (decide at execution with
     evidence — see OQ5). **Single file for v1**; multiple files / globs is deferred (OQ3).
   - **Verifier (guardrail):** before sending, confirm the file *looks redacted* — parse
     JSON, assert the enumerated sensitive keys are `<redacted>` (or absent) and that no
     value contains the current user's home-dir prefix or username substring (reuse the same
     needle logic as `redact_result`). If the file is NOT redacted (e.g. the user pointed at
     the full `.json` twin), REFUSE with a clear message and require `--no-redact` to override.
   - Runs the same fallback chain (change 3). Works with NO benchmark run in this invocation
     (does not require locating the harness — pure submission), so it functions on a login
     node from a file produced on a compute node.
   - Note: this path does its own consent (the user typed `--submit <file>` = explicit intent)
     but still shows what will be sent and, when interactive, may confirm once before POSTing.

   - **The redaction verifier (change 2) gates EVERY transmit path, not just `--submit
     <file>`.** The interactive offer and `--submit`/`--yes` auto-paths must run the same
     verifier on the file about to be sent before any network call. **`--no-redact` +
     submit is a hard refusal:** a `--no-redact` run produces no `.redacted.json`, so there is
     nothing safe to send; the tool must REFUSE to transmit the full result and print the
     manual/recovery guidance instead (transmitting an un-redacted result to a PUBLIC repo is
     never done automatically). `--no-redact` on the explicit `--submit <full file>` path
     likewise only *overrides the verifier's refusal-to-read*, and even then must print a loud
     "you are about to publish un-redacted data to a public repo" confirmation that is NOT
     satisfied by `--yes` alone (require a distinct `--i-understand-unredacted`-style explicit
     ack, or simply do not support auto-transmitting un-redacted data at all — see OQ5).

3. **Submission fallback chain helper** (`_submit_benchmark(path, method=None, gh_repo=..., …)`):
   Try methods in order; stop at first success; on total failure, offer the printed floor.
   - **(a) `gh`** — if `shutil.which("gh")` AND `gh auth status` probes clean, run
     `gh issue create --repo <owner/repo> --title <…> --body-file <redacted path>` via an
     **argv list, never `shell=True`**. Capture the returned issue URL and report it.
   - **(b) HTTP to GitHub Issues API** — `POST https://api.github.com/repos/<owner/repo>/issues`
     via stdlib `urllib.request` with a JSON body embedding the redacted result (as a fenced
     block) + title. Requires a token: from `--gh-token`, `GITHUB_TOKEN`/`GH_TOKEN` env, or
     (best-effort) `gh auth token`. If no token is resolvable, this method is *unavailable*
     (not an error) — fall through. On HTTP error, report status + message and fall through.
     **HTTP hardening (required):** send a `User-Agent: pubrun/<version>` header (GitHub's API
     **rejects** requests without one — a silent failure otherwise), `Accept:
     application/vnd.github+json`, `Authorization: Bearer <token>`; set an explicit socket
     **timeout** (e.g. 15s) so a stalled connection cannot hang the CLI; force **HTTPS**
     (reject a non-`https://api.github.com` endpoint — do not follow cross-host redirects);
     read and surface `X-RateLimit-*`/`Retry-After` on a 403/429 with a clear message; on
     201 parse the returned issue `html_url` and report it. The token is passed only in the
     `Authorization` header, never in the URL/argv/body, and is scrubbed from any error text
     printed (a 401/403 message from GitHub must not echo the token).
   - **(c) printed floor** — if (a) and (b) are unavailable or failed, EXPLAIN why each was
     skipped/failed, then prompt `Print a ready-to-paste submission (issue body + gh command)?
     [Y/n]`. On yes, print: a suggested title, the exact `gh issue create --repo … --body-file
     <path>` command, and the redacted JSON in a fenced ```json block for manual paste, plus
     the `…/issues/new` URL.
   - **Success reporting:** on (a)/(b) success, print `Submitted. Thank you! <issue url>`.
   - **Overrides:** `--submit-method {gh,http,print}` forces a single method (skip probing);
     `--gh-repo OWNER/NAME` (default `fariello/pubrun-benchmarks`); `--gh-token TOKEN`;
     `--print-submission` prints the floor without attempting network (power-user/offline);
     `--no-redact` (as above). `--yes` implies non-interactive (no confirm prompts;
     transmit still only happens because `--submit`/interactive-yes was given).

4. **Docs:** `docs/cli.md` (`bench` — document the interactive offer, `--submit <file>`
   recovery/HPC use, method chain, all overrides, and the **GitHub-account-required** honest
   limitation + no-anonymous-issue note); `docs/hpc.md` (the run-on-compute-node →
   submit-from-login-node pattern); `benchmarks/README.md` and the `pubrun-benchmarks`
   README (the automated submit path + that it still lands as an issue); `CHANGELOG.md`
   `[Unreleased] → Added`.

## Anti-regression / invariants

- **Never transmit without explicit in-invocation consent.** Enter on the `[y/N]` transmit
  prompt does NOT send. Non-interactive/no-TTY without `--submit`/`--yes` does NOT send.
  **Tests:** (i) declining prints the recovery command and sends nothing; (ii) a piped/EOF
  stdin (non-interactive) with no `--submit` sends nothing; (iii) `--submit` on a redacted
  file with a stubbed transport DOES attempt exactly one send.
- **No new runtime dependency.** Submission uses stdlib only (`shutil`, `subprocess`,
  `urllib`). `requests`, if used at all, is import-guarded and optional. **Test:** the
  submit code path imports cleanly with `requests` absent.
- **No surprise network at import or during a normal run.** All network is inside the
  consented submit step only. `pubrun bench` with no submit consent makes zero network calls.
  **Test:** run a local `--json` bench with submission declined; assert no outbound attempt
  (e.g. monkeypatch `urllib.request.urlopen` to fail-if-called).
- **`--submit <file>` refuses an un-redacted file** unless `--no-redact`. **Test:** point
  `--submit` at a full (un-redacted) result → refused with a clear message; at a redacted
  file → proceeds (transport stubbed).
- **No shell injection.** `gh` is invoked via argv list, never `shell=True`; repo, title,
  and file path are discrete argv elements. Token never appears in argv (passed via env/header
  for HTTP; `gh` uses its own auth). **Test:** a `--gh-repo` value with shell metacharacters
  is passed as a literal argv element, not executed.
- **Token is never written to the manifest, the result JSON, logs, or printed.** **Test:**
  the printed floor output and any captured stderr contain no token value.
- **Graceful degradation, never crash.** `gh` absent, `gh` unauthenticated, no token, network
  down, HTTP 4xx/5xx, offline compute node — each degrades to the next method and ultimately
  to printed instructions with a clear reason. **Test:** each unavailable/failed method falls
  through and the floor is reached.
- **Honest limitation documented.** Docs state plainly that the automated paths file a GitHub
  issue and therefore require a GitHub account, that GitHub has no anonymous-issue mechanism,
  and that fully anonymous submission means a throwaway account or manual paste. No promise of
  anonymity beyond what redaction provides (IPD-C's residual re-identification caveat stands).

## Required tests / validation

- Interactive decline → recovery command printed, nothing sent (consent invariant).
- Non-interactive (EOF stdin) without `--submit` → nothing sent.
- `--submit <redacted file>` with stubbed `gh`/`urllib` → exactly one send attempt; success
  URL reported.
- `--submit <full/un-redacted file>` → refused; `--no-redact` overrides.
- Method chain: `gh` unavailable → HTTP tried; no token → HTTP unavailable → floor reached
  with reasons; `--submit-method print` → floor only, no network.
- Redaction verifier: catches home-dir/username leak in a hand-crafted file; passes a real
  `redact_result` output.
- Security: `--gh-repo '$(touch pwned)'` treated as a literal argv element (no execution);
  token absent from all printed/logged output.
- No-`requests` import path works; no network on a declined run.
- `bench --help` documents the new flags. Full suite green (clear `__pycache__` first).

## Spec / documentation sync

`docs/cli.md`, `docs/hpc.md`, `benchmarks/README.md`, `pubrun-benchmarks/README.md`,
`CHANGELOG.md`. Run `/assess documentation` after execution.

## Open questions (for plan-review / maintainer)

1. **HTTP-to-Issues token source order — RESOLVED (maintainer 2026-07-07):** `--gh-token` >
   `GITHUB_TOKEN`/`GH_TOKEN` env > `gh auth token`. Deriving from `gh auth token` is allowed
   (the user already consented to submit in this invocation). **Print which source was used**
   so it is visible; never log the token value itself.
2. **Issue body format for HTTP path — RESOLVED (maintainer 2026-07-07):** embed the full
   redacted JSON in a fenced ```json block in the issue body (one API call; greppable;
   results are KB-sized). No file-attachment upload flow.
3. **`--submit` accepting multiple files / globs** — DEFERRED to keep v1 single-file (plan-
   review decision: reduces the `nargs`/argparse ambiguity surface and the verifier's blast
   radius; multi-file batch backfill is a clean fast-follow). Revisit once single-file ships.
4. **`gh issue create` body — RESOLVED (maintainer 2026-07-07):** generate a tiny markdown
   wrapper (title + one intro line + fenced JSON) to a temp file, pass via `--body-file`, so
   the issue is human-readable (consistent with the HTTP body in OQ2).
5. **`--submit` value syntax + un-redacted policy.** (a) *Syntax* — decide at execution, with
   evidence from argparse behavior, whether bare `--submit` vs `--submit <file>` via
   `nargs="?"` is unambiguous alongside the existing flags, or whether a distinct
   `--submit-file <path>` is cleaner. (This half stays an execution-time detail.) (b)
   *Un-redacted policy* — **RESOLVED (maintainer 2026-07-07): NEVER auto-transmit an
   un-redacted result to the public repo.** `--no-redact` + submit refuses and prints manual
   guidance; the only way un-redacted (potentially PII-bearing) data reaches the public repo is
   a deliberate, fully manual human paste. There is NO `--i-understand-unredacted` auto-path.

## Approval and execution gate

Proposal only; human approval required; NOT auto-executed. Recommended: run `plan-review`.
On completion move to `.agents/plans/executed/`.

## Execution record (2026-07-07)

Executed by opencode after human approval (first of the three 2026-07-07 IPDs).

- **Submission machinery (`src/pubrun/__main__.py`):** all self-contained + stdlib-only (the
  CLI cannot import from `benchmarks/`, which is not packaged). New helpers: `_verify_redacted`
  / `_scan_for_pii` / `_pii_needles` (redaction verifier reusing the harness's key sets +
  home/username needle logic, duplicated with a sync comment), `_submit_via_gh` (probes
  `gh auth status`, argv-list `gh issue create --body-file`, temp md wrapper), `_resolve_gh_token`
  (order `--gh-token` > `$GITHUB_TOKEN`/`$GH_TOKEN` > `gh auth token`, prints source, never logs
  value), `_submit_via_http` (stdlib `urllib`, `User-Agent`/`Accept`/`Bearer`, 15s timeout,
  HTTPS-only, rate-limit surfacing, token scrubbed from errors via `_scrub`), `_print_floor`
  (copy-paste), `_submit_benchmark` (chain gh→http→floor, `--submit-method` forces one).
- **`_run_bench` reworked:** validates `--gh-repo` (charset `_GH_REPO_RE`, exits 1 on bad
  input — blocks shell metachars); new `--submit-file` path (recovery/HPC/batch) that verifies
  redaction and REFUSES an un-redacted file unless `--no-redact` (loud warning); after a local
  run, a consent-gated `[y/N]` contribute offer (Enter = No); decline prints the exact
  `--submit-file` recovery command; `--no-redact` never auto-transmits (nothing redacted to
  send). Decision (S-OQ5a, with evidence): kept the existing Slurm `--submit` store_true and
  added a **separate `--submit-file`** flag rather than widening `--submit` to `nargs="?"`
  (avoids mutex-group + store_true ambiguity).
- **CLI flags + dispatch:** `--submit-file`, `--no-submit`, `--submit-method {gh,http,print}`,
  `--gh-repo`, `--gh-token`, `--print-submission`; dispatch updated.
- **Tests (`tests/test_bench_command.py`, +13, all green):** verifier passes redacted / catches
  sensitive key / catches home+username substring / rejects unparseable; consent — missing file
  errors, un-redacted refused, `--print-submission` makes no network, `--gh-repo` injection is
  literal (no exec); chain — gh success (http not attempted), gh→http fallthrough, all-fail →
  floor with reasons, HTTP error scrubs the token, no-token → http unavailable (no POST).
- **Docs:** `docs/cli.md` (`bench` rewritten: contribute flow, `--submit-file`, method chain,
  all flags, GitHub-account honest limitation, never-auto-transmit-un-redacted), `CHANGELOG.md`
  `[Unreleased] → Added`, `benchmarks/README.md`, and `pubrun-benchmarks/README.md`
  (contributor repo).
- **Validation:** full suite **770 passed / 1 failed / 2 skipped** — the lone failure is the
  known pre-existing SIGPIPE flake (`test_real_sigpipe_via_pipe`, passes in isolation; verified).
  Submission tests: 26/26 in isolation. Only the 4 pre-existing benign LSP warnings remain.

### Deferred (unchanged)

Multi-file / glob `--submit` (OQ3) — v1 is single-file. `--submit` value-syntax half of OQ5(a)
resolved by choosing a separate `--submit-file` flag. Remaining OQ leanings folded in as
maintainer-confirmed.

## Plan-review record (2026-07-07)

Reviewed via `.agents/workflows/plan-review/plan-review.md` (Fix Bar: fix-by-default gated by
Remediation Risk). Verified code claims against tree: `_run_bench` signature/dispatch
(`__main__.py:903`, `:1982`), the existing `--submit` store_true (`:1602`), `redact_result`
needle logic (`harness.py:395`), `_BENCH_SUBMIT_URL` (`:850`). Verdict: **APPROVE WITH
REVISIONS APPLIED.**

- **S1 (HIGH, security):** verifier now gates EVERY transmit path (interactive + `--submit`),
  and `--no-redact` + submit is a hard refusal (never auto-transmit un-redacted data to a
  PUBLIC repo). Fixed in change 2/3.
- **S2 (HIGH, security):** added mandatory HTTP hardening — `User-Agent` (GitHub rejects
  without it), `Accept`/`Authorization: Bearer`, explicit socket timeout, HTTPS-only / no
  cross-host redirect, rate-limit surfacing, token scrubbed from error text and never in
  URL/argv/body. Fixed in change 3(b).
- **S3 (MEDIUM, functionality):** decline recovery command shell-quoted; `--no-redact` case
  no longer prints a `--submit` command for a file that would be refused. Fixed in change 1.
- **S4 (MEDIUM, functionality):** reconciled the `--submit` single-vs-multi inconsistency —
  v1 single file; `nargs="?"` dual meaning (bare vs valued) called out with an argparse-
  ambiguity fallback (`--submit-file`); multi-file deferred (OQ3). Fixed in change 2 + OQ3/5.

Deferred/open: OQ1 (token source order), OQ2 (issue body format), OQ4 (gh body wrapper) — all
LOW, wording/ergonomics, no Remediation-Risk justification needed to leave for execution-time.
OQ3 (multi-file) deferred to reduce argparse/verifier blast radius. OQ5 (submit syntax +
un-redacted policy) records plain-review's security position: never auto-transmit un-redacted.
