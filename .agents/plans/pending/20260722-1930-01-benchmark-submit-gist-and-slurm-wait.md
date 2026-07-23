# IPD: Restore low-friction benchmark submission (gist/inline via gh) + Slurm submit-and-wait

- Date: 2026-07-22
- Concern: feature / usability / privacy (restore a browserless one-command contribution path;
  add an HPC submit-and-wait mode that reaches the interactive contribution step from a login node)
- Scope: `src/pubrun/__main__.py` (bench client: redacted-only default + `--unredacted` opt-in, gh
  preflight, gist/inline submit, `--contribute` flags, Slurm submit-and-wait), `benchmarks/harness.py`
  (make the redacted file the default output; write the unredacted file only when requested), the Slurm
  submit wrapper output contract (`benchmarks/submit_bench.sh` / `benchmarks/run_bench.sbatch` so the
  redacted file is produced and discoverable), the server intake
  (`.github/workflows/benchmark-intake.yml` trigger; `.github/scripts/extract_attachment_url.py` and
  `validate_benchmark_submission.py` to accept gist host + inline JSON), and docs/CHANGELOG/tests. NO
  Gist discovery/reconciliation, NO `--cleanup-submissions`, NO data-branch/archival, NO `contents:write`.
- Status: pending
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)
- Set: benchmark-intake
- Order: 4

## Parent / set / provenance

Amends the executed Phase 1 child IPD `20260721-2255-01` (attach-only client), which REMOVED the
auto-submit path. The maintainer determined in session 2026-07-22 that removal was a mistake: the
consent gate + local redaction were already in place, so "the client transmits the redacted file after
you say yes" is NOT a materially larger privacy risk than "you attach the same file by hand," and the
attach flow ADDS a wrong-file risk plus a hard funnel drop (estimated loss of >3/4 of would-be
submitters). It is also unusable on HPC compute nodes (no interactive TTY, often no browser/network),
which are a lead demographic. This IPD restores a browserless one-command path and adds the HPC mode
that makes it reachable. Corrective, per the plan-lifecycle rule (a new IPD, not an in-place edit of an
executed one).

Grounded in the imported reference `.agents/docs/research/20260722-1547-01-pubrun-benchmark-github-submission.reference.md`
(Slice A of that reference; Slice B = Gist lifecycle/reconciliation/`--cleanup-submissions` is DEFERRED
to a later IPD). The hard fact from the reference is confirmed: GitHub's create-issue API has no
file-attachment parameter, so a script cannot reproduce the browser drag-drop upload; Gist-plus-link is
the automated transport, with inline-in-body as the fallback for results under the issue-body cap.

## Goal

`pubrun bench` should let a contributor publish a share-checked redacted result to `fariello/pubrun`
in one command, without a browser, including from an HPC login node, while keeping every existing
privacy invariant. Two coordinated pieces:

1. Client contribution (any machine with `gh`): after the run + safe-file block + explicit consent,
   publish the redacted file as an unlisted Gist and open a marked issue linking its raw `.json` URL;
   fall back to inline-in-body when the complete body is `< 65_000` UTF-8 bytes; else print the browser
   fallback. `--submit-file` reuses the same path.
2. Slurm submit-and-wait: on a Slurm login node, offer to run by submitting to the queue; if yes, keep
   the login-node parent alive polling for completion, then run the interactive share-check +
   contribution from the login node (which has `gh`/network), with a graceful `--submit-file` fallback
   if the wait is interrupted or `gh` is not ready. Data is never lost (the result is on the shared FS).

## Project conventions / current-state findings (Step 0, verified)

- Client today (post Phase 1): `_BENCH_SUBMIT_URL` -> main-repo Issue Form; `_share_check` (prefers
  `benchmarks/share_safety.py`); `_print_safe_file_block`; `_prepare_submission`; NO transmit path
  (auto-post removed). `--submit`/`--yes` govern HPC scheduler JOB submission only (`__main__.py`
  ~:1403). `--submit-file` currently share-checks + prints how to attach (no transmit).
- Slurm path today is FIRE-AND-FORGET: `_run_bench` builds `bash submit_bench.sh ...`, prompts
  `Submit this benchmark job to Slurm? [y/N]`, runs it, prints "Results will be written under
  benchmarks/results/ on the compute node," and returns (`__main__.py` ~:1405-1427). It does NOT wait
  and does NOT capture the job id.
- GAP (must fix for submit-and-wait to contribute): `benchmarks/run_bench.sbatch` writes a BARE
  `${NODE}-${STAMP}.json` via `--out` and passes NO `--redacted-out`, so the Slurm run produces NO
  `.redacted.json` and no share-safe artifact. `submit_bench.sh` discards `sbatch`'s job-id stdout.
- Server intake today: workflow triggers ONLY on the `type:benchmark-submission` LABEL (which an
  outside API caller cannot set); `extract_attachment_url.py` finds an allowlisted `.json` URL;
  `validate_benchmark_submission.py` validates a `--file`/`--url`. `ALLOWED_ATTACHMENT_HOSTS` does not
  include `gist.githubusercontent.com`; there is no inline-JSON extraction path.
- Stack: zero-runtime-dependency wheel. `gh` and any submission logic are invoked via stdlib
  `subprocess` (argv list, never `shell=True`); nothing new is imported at `import pubrun` time.
- House rules: no em/en dashes in authored Markdown; path-scoped commits; never push without
  authorization; matrix-validation for CLI-grammar/behavior changes; paste actual test/CI output.

## Design (Slice A)

### A0. Redacted-only by default; unredacted is opt-in (root-cause simplification)

The recurring privacy worry has a single root cause: an identifying file is written by default right
next to the safe one, so every mitigation (the "PRIVATE, DO NOT SHARE" line, `--prepare-submission`'s
clean folder, the wrong-file framing) exists to manage a danger we create by default. Removing the
danger at the source is simpler AND more correct: the redacted file already preserves everything
analytically useful (CPU/GPU model, timings, versions, filesystem type, Slurm partition); the
unredacted file adds only identity (hostname, username, home paths), which is not benchmark signal.

- `pubrun bench` (and `benchmarks/harness.py`) write ONLY the redacted, share-safe file by default:
  `pubrun-bench-<hostname-hash>-<stamp>.redacted.json` (keep the `.redacted.json` suffix so the name
  always advertises what it is, even as the sole output).
- `pubrun bench --unredacted` (harness: still `--out`) ALSO writes the identifying
  `*.unredacted.json` for local debugging, keeping the unmistakable naming + "do not share" guidance
  for THAT file only.
- Harness change: today `harness.py` always writes the full `--out` and optionally `--redacted-out`
  (`:620-646`). Flip it: default = write the redacted file; the unredacted `--out` is produced only when
  requested. Preserve `redact_result` and the compact serialization; keep a redaction self-check so an
  under-redaction bug is caught (the one real cost of not keeping raw data by default is mitigated by
  `--unredacted` for deliberate debugging + the share-safety validator).
- Downstream simplification (reflected in the steps below): `_print_safe_file_block` no longer needs a
  PRIVATE line in the common case (only when `--unredacted` was used); `--prepare-submission` mostly
  becomes redundant (the results dir already holds only the safe file) but is retained as a harmless
  convenience; submit-and-wait tracks one file, not two.

### A. gh preflight (pre-benchmark, non-blocking)

- `_probe_gh() -> GhReadiness{installed, authenticated, detail}`: `shutil.which("gh")`, then
  `gh auth status` (argv list, `GH_PROMPT_DISABLED=1`, timeout). NEVER runs `gh auth login`/`refresh`,
  never prints or requests a token, never blocks the benchmark.
- Before an expensive run, print a short readiness line and, if `gh` is missing/unauthenticated, the
  exact optional fix (install URL / `gh auth login`) plus "the benchmark will continue; you can still
  submit through the web form." Recheck readiness immediately before submitting (auth can change).

### B. Client contribution (gist -> inline -> web fallback)

- Pure body builders + a size gate (testable without network):
  `_build_gist_issue_body(path, raw_url)` and `_build_inline_issue_body(path)`, each starting with the
  exact marker `<!-- pubrun-benchmark-submission:v1 -->`; `inline_allowed = len(body.encode("utf-8")) < 65_000`
  measured over the COMPLETE body. Preserve the validated file bytes (do not reparse/reserialize except
  for the share check). Handle a JSON body containing triple backticks (longer fence or reject).
- `_run_gh(args, *, input_text=None, timeout)`: argv list, `shell=False`, `GH_PROMPT_DISABLED=1`;
  issue bodies via stdin (`--body-file -`), NEVER JSON in argv; sanitize stderr (no token/JSON/host
  path/hostname); timeout on every call; keep `OWNER/NAME` slug validation.
- `_create_result_gist(path) -> (gist_id, raw_url)`: `gh gist create` WITHOUT `--public` (unlisted; do
  NOT call it "private" in any message). Fetch metadata via `gh api /gists/{id}`, require exactly one
  file, and validate the `raw_url`: scheme https, host EXACTLY `gist.githubusercontent.com` (no suffix
  match), path ends `.json`.
- `_create_benchmark_issue(title, body, repo)`: `gh issue create --repo --title --body-file -`; NO
  label args (external callers cannot set labels; the workflow applies them). Title derived from
  NON-identifying fields only (OS family, arch, Python version, mode), whitespace-normalized, capped;
  never hostname/username/home path/job id.
- Orchestrator `_submit_benchmark_result(path, title, repo) -> SubmissionResult{submitted, method in
  (gist|inline|web-fallback|none), issue_url, detail}`: re-run `_share_check` immediately (refuse on
  fail); try gist+issue; on any gist-stage failure delete the just-created orphan best-effort
  (immediate rollback of an action the user authorized) then try inline if it fits; else web fallback.
  Never claim a gist/issue exists without a validated URL; report partial states honestly.

### C. `--contribute` / `--no-contribute` flags (do NOT overload `--submit`/`--yes`)

- Default (interactive TTY ONLY): after the safe-file block, prompt
  `Publish the share-checked redacted benchmark result to GitHub? [Y/n]` with Enter = YES (maintainer
  decision 2026-07-22). Rationale: the file is redacted + structurally share-checked + server-
  revalidated, so an accidental Enter cannot leak sensitive data; the only exposure is the low-stakes
  fact that this GitHub account submitted a benchmark, and making yes the default maximizes the
  submission funnel (the stated priority). No upload happens before the (defaulted) yes is given.
- HARD guard: the prompt is shown ONLY when stdin is a genuine interactive TTY. When stdin is not a TTY
  (pipe / CI / batch), there is NO prompt at all, so a stray newline or empty read can NEVER trigger a
  publish. Enter = YES therefore applies solely to a real human at a real terminal.
- `--contribute`: pre-consent; skip the prompt and attempt submission (still share-checks first). For
  scripts/CI/HPC batch.
- `--no-contribute`: never offer/attempt GitHub publication.
- `--submit` / `--yes` remain HPC-scheduler-only; document that `--yes` does NOT imply consent to public
  GitHub publication.

### D. Slurm submit-and-wait (Slurm-only; other schedulers unchanged, still fire-and-forget)

- On a Slurm login node (probe = existing detection: `SLURM_JOB_ID` / `sbatch` on PATH), when a submit
  is offered, ask `Run by submitting to the Slurm queue? [y/N]`. (Existing multi-scheduler detection
  for PBS/LSF/SGE is untouched; submit-and-wait is built for Slurm only this slice.)
- If yes: capture the job id (prefer `sbatch --parsable`, else parse `Submitted batch job <id>` from
  stdout) and pass DETERMINISTIC output paths so the login-node parent can find the artifacts:
  set explicit `--out <.../pubrun-bench-<token>-<stamp>.unredacted.json>` and
  `--redacted-out <....redacted.json>` through the submit env. This CLOSES the current gap where the
  Slurm run produced no redacted file.
- The login-node parent then POLLS `sacct`/`squeue` for the job id with a visible waiting indicator,
  a bounded default max-wait plus a `--wait-timeout` override, and clean handling of Ctrl-C / dropped
  session. On completion (COMPLETED): verify the expected redacted file exists on the shared FS, then
  run the SAME interactive share-check + `_submit_benchmark_result` contribution from the login node.
- Graceful fallback (never lose data): if the wait is interrupted, times out, the job FAILED, or `gh`
  is not ready, print exactly where the result is and
  `pubrun bench --submit-file <path>` to finish from the login node. The shared-FS artifact is always
  the source of truth.

### E. Server intake changes (REQUIRED; the client is insufficient alone)

- Trigger by LABEL OR MARKER: add `|| contains(github.event.issue.body,
  '<!-- pubrun-benchmark-submission:v1 -->')` to the job `if:`. The marker is routing only; the JSON
  stays untrusted. The workflow (with its `issues: write`) applies `type:benchmark-submission` +
  `status:pending` itself, then sets the final status.
- Accept gist raw URLs: add `gist.githubusercontent.com` to `ALLOWED_ATTACHMENT_HOSTS` in BOTH
  `extract_attachment_url.py` and `validate_benchmark_submission.py` (exact host, https, bounded
  redirects, timeout, 1 MiB cap; NO suffix matching).
- Accept inline JSON: extractor returns exactly one of `kind=url|inline|none`. Read the body from
  `$GITHUB_EVENT_PATH` (not a possibly-65KB env var), treat as data. Inline contract: require the exact
  v1 marker; exactly one ```json fenced block; reject zero/multiple; enforce the 1 MiB cap before
  writing to a FIXED path `submission.json` (never a content-derived name); never log the JSON. The
  validate step picks one fixed invocation (`--url` or `--file`) off the enumerated `kind` ONLY; never
  build the command from issue text.
- Idempotence: the workflow runs on opened AND edited; include a hidden receipt marker and update the
  existing receipt instead of piling comments; keep exactly one of `status:accepted`/`status:needs-fix`;
  never create/delete a submitter's Gist.

## Findings (drivers)

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence |
|----|----------|------------------|---------|------|---------|----------|
| S4-0 | High | Medium | Privacy/Simplicity | root cause | Writing an unredacted file by default is the source of the wrong-file risk and the mitigations built around it; redacted-only default (unredacted opt-in) removes the danger at the source | session 2026-07-22; `harness.py:620-646` |
| S4-1 | High | Medium | Contributor/HPC | adoption | Attach-only dropped the browserless one-command path; large funnel loss; unusable on compute nodes | session 2026-07-22; reference S1 |
| S4-2 | High | Medium | Security | untrusted transport | gh/gist path must never shell-interpolate title/body/JSON/URL; bodies via stdin; errors sanitized | reference S6.1/S13 |
| S4-3 | High | Low | Security | server routing | Outside callers cannot set the label; workflow must trigger on the body MARKER too, and self-apply labels | reference S7.1; workflow `if:` |
| S4-4 | High | Low | Privacy | share-safety parity | Client re-share-checks immediately before transmit; server revalidates; local pass is not trusted | reference S13; Phase 1 checker |
| S4-5 | High | Medium | HPC/Data-loss | Slurm artifact gap | run_bench.sbatch produces no `.redacted.json`; submit-and-wait must pass explicit out/redacted-out | `run_bench.sbatch:38-60` |
| S4-6 | Medium | Medium | HPC/UX | blocking wait | Queue time is unbounded; parent wait must be best-effort with a clean `--submit-file` fallback | session 2026-07-22 |
| S4-7 | Medium | Low | UX/Safety | flag overload | `--submit`/`--yes` are scheduler-only; GitHub publish needs its own `--contribute` + confirmation | reference S10 |
| S4-8 | Medium | Low | Security | gist host allowlist | Add exact `gist.githubusercontent.com`; never suffix-match `githubusercontent.com` | reference S7.2 |
| S4-9 | Medium | Low | Correctness | inline size/fence | Measure UTF-8 bytes over the FULL body (`< 65_000`); handle triple-backtick JSON | reference S5.5 / test 13 |
| S4-10 | Low | Low | Honesty | partial publish | A created-then-failed gist/issue must be reported honestly, never a false "nothing published" | reference S9/S11 |

## Proposed changes (ordered, validatable)

| Step | Src | Change | Files | Remediation Risk | Validation |
|------|-----|--------|-------|------------------|------------|
| 0 | S4-0 | Redacted-only by default; write the unredacted file only on `--unredacted`. Harness default output = redacted; keep `.redacted.json` naming; keep a redaction self-check. Simplify `_print_safe_file_block` (PRIVATE line only when `--unredacted`). | `benchmarks/harness.py`, `src/pubrun/__main__.py` | Medium | unit: default run writes ONLY `*.redacted.json` (no unredacted sibling); `--unredacted` writes both with the do-not-share naming; redacted file still validates against schema `/5`; safe-file block omits PRIVATE line by default |
| 1 | S4-2,S4-9 | Pure body builders + size gate + `SubmissionResult`/`GhReadiness` types | `src/pubrun/__main__.py` | Low | unit: marker present; `<65_000` boundary at 64999/65000; UTF-8 byte count; triple-backtick handling |
| 2 | S4-1,S4-2 | `_probe_gh` (non-blocking) + pre-run readiness messaging | `src/pubrun/__main__.py` | Low | unit (mock subprocess): missing/unauth/ready; benchmark never blocked; no token printed |
| 3 | S4-2,S4-8 | `_run_gh` safe wrapper; `_create_result_gist` (unlisted) + raw-url host/shape validation | `src/pubrun/__main__.py` | Medium | unit: argv/no-shell; stdin body; exact-host raw url; sanitized errors |
| 4 | S4-2,S4-9,S4-10 | `_create_benchmark_issue` + orchestrator (gist -> inline -> web) + immediate orphan rollback | `src/pubrun/__main__.py` | Medium | unit: gist success; gist-fail->inline; issue-fail->rollback+report; oversized->web |
| 5 | S4-7 | `--contribute`/`--no-contribute` flags + default post-run confirmation; TTY-aware; `--submit-file` reuse | `src/pubrun/__main__.py` | Low | CLI tests: prompt default N; `--contribute` pre-consents; non-TTY no-hang; `--yes` != publish |
| 6 | S4-5,S4-6 | Slurm submit-and-wait: capture job id, pass an explicit redacted-out path (unredacted only if `--unredacted`), poll sacct/squeue, graceful fallback. Tracks the single redacted file by default. | `src/pubrun/__main__.py`, `benchmarks/submit_bench.sh`, `benchmarks/run_bench.sbatch` | Medium | unit (mock sbatch/sacct): job-id capture; completion->contribute; interrupt/timeout->`--submit-file`; sbatch produces the redacted file (and unredacted only with `--unredacted`) |
| 7 | S4-3,S4-8 | Server: trigger on label OR v1 marker; workflow self-applies labels | `.github/workflows/benchmark-intake.yml` | Medium | workflow tests: marker triggers; perms still contents:read + issues:write |
| 8 | S4-3,S4-8 | Extractor: `kind=url|inline|none`, read `$GITHUB_EVENT_PATH`, add gist host (both files) | `.github/scripts/extract_attachment_url.py`, `validate_benchmark_submission.py` | Medium | tests: gist raw url accepted; gist HTML page + lookalike rejected; single inline block; 0/many rejected; cap before parse |
| 9 | S4-1 | Docs + CHANGELOG: contribute-via-gh, HPC submit-and-wait, unlisted (not private), web path still supported | `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | Low | links resolve; dash-clean; describes gist as unlisted |

## Deferred / out of scope (this slice)

| Item | Reason |
|------|--------|
| Gist discovery/classification, prior-run reconciliation, Gist-to-inline conversion, `--cleanup-submissions`, per-user state file | Slice B: stateful, edits/deletes users' Gists+issues; own IPD + review. Only IMMEDIATE orphan rollback is in scope here. |
| Submit-and-wait for PBS/LSF/SGE | Slurm-only this slice (maintainer scope); existing fire-and-forget detection for the others is untouched. |
| Archival/aggregation to a data branch, any `contents:write` | Phase 2; hard `/assess security` gate first. |

## Cannot-do-unilaterally (human / gated)

- Labels (`type:benchmark-submission`, `status:{pending,accepted,needs-fix}`) and any push remain human
  actions. The workflow references/self-applies labels but the human creates them.
- Integration testing against real GitHub uses a DISPOSABLE test repo / explicitly authorized test
  issue, never production by default (human sets this up).

## Required tests / validation

- Redacted-only default (Step 0): a default `pubrun bench` / harness run writes ONLY the
  `*.redacted.json` and NO `*.unredacted.json`; `--unredacted` writes both (with do-not-share naming);
  the redacted default still conforms to schema `/5`; the safe-file block omits the PRIVATE line unless
  `--unredacted` was used. Update/retire existing tests that assumed an unredacted file always exists
  (e.g. `tests/test_bench_command.py::TestBenchCLI::test_bench_quick_local_json` asserts a `redacted`
  key AND an unredacted `results` path).
- Client unit tests (mock `subprocess.run`; no live GitHub): the reference S12.1 cases 1-17 that fall in
  this slice (preflight, consent, share-check refusal, gist success, gist->inline fallback, orphan
  rollback, 64999/65000 boundary, multibyte UTF-8, triple-backtick, title sanitization, no token/JSON
  leak, `--submit-file` parity, HPC path never publishes an unredacted/login-node result).
- Slurm submit-and-wait unit tests (mock sbatch/sacct/squeue): job-id capture; COMPLETED -> contribute;
  interrupt/timeout/FAILED -> `--submit-file` fallback with data intact; sbatch invocation now passes
  `--redacted-out`.
- Server extractor/validator tests: existing web attachment still accepted; gist raw `.json` accepted;
  gist HTML page + lookalike host rejected; redirect-off-allowlist rejected; single inline block
  accepted; missing marker / 0 / multiple blocks rejected; oversize rejected before parse; identical
  URL-vs-inline behavior; receipt idempotence; marker-triggered issue gets labels from the workflow.
- Security asserts (hard MUST): only a re-share-checked file transmits; unredacted sibling never enters
  any publish path; no shell interpolation anywhere; gist/issue URLs parsed + host-validated; server
  never executes/evaluates JSON; errors never contain JSON/creds/hostname/paths; workflow perms remain
  `contents:read`+`issues:write`.
- Matrix-validation: this is a CLI/behavior change AND a server-contract change, so it is NOT done on
  local green alone; push + full CI matrix, fix stragglers, THEN move to executed/.
- Honesty rule: paste ACTUAL test + CI-matrix output; never claim green unrun.

## Spec / documentation sync

- README/CLI docs: document that `pubrun bench` now writes ONLY the redacted, share-safe file by
  default, and that `--unredacted` opts into the identifying copy for local debugging. Add the
  one-command `--contribute` path and the HPC submit-and-wait flow; keep the browser attach path
  documented as still supported. CONTRIBUTING note. CHANGELOG Added/Changed (call out the default
  change to redacted-only as a behavior change). Describe Gists as UNLISTED (accessible to anyone with
  the URL), never "private". No overclaim about what the corpus proves.

## Open questions (all RESOLVED 2026-07-22)

1. Default post-run behavior: RESOLVED. Interactive OFFER by default, with Enter = YES, shown ONLY on a
   genuine interactive TTY (non-TTY = no prompt, so no accidental publish). `--no-contribute` opts out;
   `--contribute` pre-consents. Chosen over silent-unless-`--contribute` for adoption; the accidental-
   Enter risk is acceptable because the artifact is redacted/share-checked/server-revalidated and the
   only exposure is the low-stakes fact of submission. The deciding factor is the ASYMMETRY of the
   accidental cases: a reflexive Enter under `[y/N]` would silently DISCARD a long run's contribution
   (forcing a full re-run), whereas under `[Y/n]` it at worst produces a redacted benchmark issue we
   wanted anyway. FUTURE FALLBACK (maintainer, 2026-07-22): if this ever draws a complaint, switch to a
   REQUIRED explicit answer (no default; Enter re-prompts). Cheap, reversible, one prompt; deferred
   until real feedback rather than pre-engineered.
2. Flag name: RESOLVED. `--contribute` / `--no-contribute` (over `--publish`/`--share`).
3. Submit-and-wait max-wait: RESOLVED. Bounded default (~30 min) with a `--wait-timeout` override
   (extend or disable); Ctrl-C / timeout / dropped session fall back to `pubrun bench --submit-file
   <path>`; data always on the shared FS.

Also resolved earlier this session: redacted-only default output with `--unredacted` opt-in (Step 0 /
finding S4-0); Slice A scope (gist/inline + Slurm submit-and-wait), with Gist lifecycle/reconciliation/
`--cleanup-submissions` deferred to Slice B.

## Approval and execution gate

Proposal; MUST be human-approved before execution; NOT auto-run. Execution contract:
- Open questions resolved (or explicitly OPEN -> NO-GO).
- Scope fence: ONLY the files listed in Scope. NO Gist discovery/reconciliation/`--cleanup-submissions`,
  NO submit-and-wait for non-Slurm schedulers, NO data-branch/archival, NO `contents:write`. Anything
  beyond -> STOP and report.
- Security: the gh/gist transport and the server intake are Internet-facing; obey the injection/host/
  byte-cap/no-eval rules; the server revalidates independently of any client claim.
- Honesty rule (hard MUST): paste actual test + CI-matrix output; never claim green unrun.
- Commits path-scoped; never push without explicit authorization.
- Lifecycle: on completion + approval + matrix-green, move this IPD to `.agents/plans/executed/`
  (Status -> executed) with a Workflow-history line; record the phase in the orchestrator's history.

## Workflow history
- 2026-07-22 drafted (opencode / its_direct/pt3-claude-opus-4.8-1m-us): corrective IPD restoring the
  browserless one-command benchmark submission (gist-and-link + inline fallback via `gh`) that Phase 1
  removed, plus a Slurm submit-and-wait mode that reaches the interactive contribution step from a login
  node, plus the required server-intake changes (marker trigger, gist host, inline JSON). Slice A of the
  imported reference `20260722-1547-01`; Slice B (Gist lifecycle/reconciliation/`--cleanup-submissions`)
  deferred. `Set: benchmark-intake`, `Order: 4`. Not executed; awaiting review/approval.
- 2026-07-22 revised (opencode / its_direct/pt3-claude-opus-4.8-1m-us): folded in the maintainer's
  root-cause simplification (Step 0 / finding S4-0): `pubrun bench` and the harness now write ONLY the
  redacted, share-safe file by default; the identifying `*.unredacted.json` is written only on
  `--unredacted` (local debugging). Keeps the `.redacted.json` filename. This removes the wrong-file
  risk at the source and simplifies the safe-file block, `--prepare-submission`, and submit-and-wait.
  Added `benchmarks/harness.py` to scope. Still pending; awaiting review/approval.
