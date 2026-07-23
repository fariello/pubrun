# Reference: Implementing GitHub Benchmark Submission in `pubrun bench`

**Target repository:** [`fariello/pubrun`](https://github.com/fariello/pubrun/)
**Prepared:** 2026-07-22
**Audience:** Coding agent implementing the feature, primarily Claude Opus 4.8
**Status:** Implementation guidance, not authorization to modify or push the repository

## 1. Objective

Extend `pubrun bench` so a contributor can publish a locally generated, share-checked benchmark result to `fariello/pubrun` with minimal effort.

The submission order must be:

1. Before benchmarking, check whether GitHub CLI (`gh`) is installed and authenticated. If either check fails, recommend the exact installation or authentication action before the benchmark begins. Do not prevent the benchmark from running.
2. After benchmarking, validate that the candidate is the redacted JSON and passes the existing local share-safety check.
3. If `gh` is installed and authenticated, first try to publish the JSON as an unlisted Gist and create a GitHub issue containing the Gist's raw JSON URL.
4. If Gist publication fails, but `gh` can still create an issue and the complete inline issue body is smaller than 65,000 UTF-8 bytes, create the issue with the JSON in a fenced code block.
5. If neither automatic route works, give concise instructions to:
   - submit through the GitHub Issue Form in a browser;
   - install `gh` if it is absent; or
   - authenticate/extend its authorization if it is installed but unusable.
6. Track Gists created by `pubrun`, offer to remove an orphan immediately after a failed issue creation, and offer to reconcile and clean Gists left by earlier runs. Never delete the only surviving copy of a submitted result.

GitHub does not expose a supported attachment-upload parameter on the issue-creation REST API. The REST endpoint accepts title, body, labels, assignees, and related metadata, but not a file. GitHub's supported file attachment flow is interactive drag-and-drop in the web editor. Therefore, Gist-plus-link is an attachment-like automated transport, not a literal issue attachment. See [GitHub's create-issue API](https://docs.github.com/en/rest/issues/issues#create-an-issue), [GitHub file attachments](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files), [`gh gist create`](https://cli.github.com/manual/gh_gist_create), and [`gh issue create`](https://cli.github.com/manual/gh_issue_create).

## 2. Existing repository behavior to preserve

The current default branch already contains:

- `_BENCH_SUBMIT_URL`, pointing to the main-repository `benchmark-result.yml` Issue Form;
- `_share_check`, which performs the local structural share-safety validation;
- `_print_safe_file_block`, which distinguishes the private unredacted file from the safe redacted file;
- `_prepare_submission`, which copies only the safe file into `pubrun-share/`;
- `.github/ISSUE_TEMPLATE/benchmark-result.yml`, which asks the user to attach the redacted JSON;
- `.github/scripts/extract_attachment_url.py`, which currently finds an allowlisted `.json` URL;
- `.github/scripts/validate_benchmark_submission.py`, which downloads or reads the JSON and validates size, schema, share safety, and semantic constraints;
- `.github/workflows/benchmark-intake.yml`, which currently runs only when the issue has the `type:benchmark-submission` label.

Do not weaken or bypass the existing privacy boundary. The local share-safety check must run immediately before either Gist publication or inline issue creation, even if it already ran earlier in the benchmark flow.

## 3. Recommended user experience

### 3.1 Preflight before the benchmark starts

Run a fast, noninteractive GitHub readiness probe before expensive benchmark work:

```text
GitHub submission readiness:
  gh installed:       yes
  gh authenticated:   yes
  automatic submit:   available after the benchmark
```

If `gh` is absent:

```text
Optional: install GitHub CLI before the benchmark if you want one-command
submission afterward:
  https://cli.github.com/

The benchmark will continue. You can still submit through the web form.
```

If `gh` exists but authentication fails:

```text
Optional: authenticate GitHub CLI before the benchmark if you want one-command
submission afterward:
  gh auth login

The benchmark will continue. You can still submit through the web form.
```

Requirements:

- Never run `gh auth login` or `gh auth refresh` automatically.
- Never request or print a token.
- Never block benchmark execution because GitHub submission is unavailable.
- Cache the preflight result for user messaging, but recheck immediately before submission because authentication may change during the run.
- Suppress interactive prompts during probes with `GH_PROMPT_DISABLED=1`.

When `gh` is ready, also perform a bounded lookup for earlier Gists created by `pubrun`. If candidates exist, report the count and offer cleanup before starting the benchmark:

```text
Found 2 earlier pubrun benchmark Gists owned by this GitHub account.
Review and clean them up before benchmarking? [y/N]
```

Cleanup must be optional, itemized, and conservative. Discovery alone must not delete or edit anything.

### 3.2 Confirmation after the benchmark

The benchmark result is public once submitted. Obtain explicit confirmation after showing the existing safe-file block:

```text
Publish the share-checked redacted benchmark result to GitHub? [y/N]
```

An Enter/default response must mean no. Do not upload the Gist before this confirmation.

### 3.3 Success messages

Gist route:

```text
Submitted benchmark using GitHub CLI and an unlisted Gist:
  https://github.com/fariello/pubrun/issues/123
```

Inline route:

```text
Gist upload was unavailable; submitted the 22.4 KB result inline:
  https://github.com/fariello/pubrun/issues/123
```

Do not call an unlisted Gist private. A secret/unlisted Gist is accessible to anyone who has its URL, and linking it from a public issue makes it public in practice.

After a Gist-backed issue is successfully created, explain its lifecycle and offer cleanup when it becomes safe. Ordinarily this means a later run or an explicit cleanup command, after the issue has an inline or archived copy.

## 4. Submission decision tree

```text
Run preflight
  |
  +-- gh missing ------------> benchmark continues; suggest install; web fallback
  |
  +-- gh unauthenticated ----> benchmark continues; suggest gh auth login; web fallback
  |
  +-- gh ready
         |
         v
Run benchmark -> produce redacted JSON -> run share check -> ask confirmation
         |
         +-- declined / failed share check -> stop; transmit nothing
         |
         v
Try unlisted Gist -> obtain raw gist.githubusercontent.com URL
         |
         +-- success -> create marked issue containing URL -> record association
         |                -> offer safe cleanup/reconciliation -> return issue URL
         |
         +-- failure
                |
                v
Build complete inline issue body and measure UTF-8 bytes
                |
                +-- < 65,000 bytes -> create marked issue with fenced JSON
                |
                +-- too large or issue create fails -> print web/install/auth guidance
```

## 5. Issue contract

Both automatic routes should produce the same title and machine-readable header.

### 5.1 Title

```text
[BENCH]: SOME_TITLE
```

Normalize whitespace and cap the generated portion conservatively. Do not put raw hostname, username, home path, scheduler job ID, or another possibly identifying value in the title. A safe default can be derived from non-identifying fields such as OS family, architecture, Python version, and benchmark mode.

Example:

```text
[BENCH]: Linux x86_64, Python 3.14, default run
```

### 5.2 Common marker

Place this exact marker at the start of the body:

```html
<!-- pubrun-benchmark-submission:v1 -->
```

The marker is routing metadata, not authentication and not a security boundary. All public issue input remains attacker-controlled.

### 5.3 Gist body

```markdown
<!-- pubrun-benchmark-submission:v1 -->

## Benchmark result

Automated submission from `pubrun bench`.

- Result: [pubrun-bench-XXXXXXXX-TIMESTAMP.redacted.json](RAW_GIST_URL)
- Submission method: `gh-gist-v1`
- Share-safety check: passed

The submitter confirmed that this is the redacted result.
```

Use the Gist's `raw_url`, whose host is `gist.githubusercontent.com`, rather than the HTML Gist page. The raw URL must end in `.json` so the current conservative extractor can recognize the intended media type.

### 5.4 Inline body

```markdown
<!-- pubrun-benchmark-submission:v1 -->

## Benchmark result

Automated submission from `pubrun bench`.

- Submission method: `gh-inline-v1`
- Share-safety check: passed

The submitter confirmed that this is the redacted result.

<details>
<summary>Redacted benchmark JSON</summary>

```json
COMPACT_JSON_HERE
```

</details>
```

The JSON serializer already produces compact output. Preserve the file bytes rather than parsing and reserializing during submission, except when parsing is required by the share-safety validator. This avoids changing the artifact after it was validated.

### 5.5 Size rule

Measure the complete final body, not just the JSON:

```python
body_size = len(body.encode("utf-8"))
inline_allowed = body_size < 65_000
```

Use `< 65_000`, not `<=`, and include all Markdown wrappers, descriptions, and markers in the measurement. GitHub's issue body limit is commonly treated as roughly 65 KB; the small safety margin below 65,536 protects against counting and formatting differences. Normal 20-23 KB benchmark results should fit easily.

Do not truncate JSON to make it fit. If the complete body is too large, use the web attachment fallback.

## 6. Python implementation structure

Add a small internal submission abstraction rather than folding more branches into `_run_bench`.

Suggested types:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


@dataclass(frozen=True)
class GhReadiness:
    installed: bool
    authenticated: bool
    detail: str = ""


@dataclass(frozen=True)
class SubmissionResult:
    submitted: bool
    method: Literal["gist", "inline", "web-fallback", "none"]
    issue_url: Optional[str] = None
    detail: str = ""
```

Suggested functions:

```python
def _probe_gh() -> GhReadiness: ...
def _run_gh(args, *, input_text=None, timeout=30) -> str: ...
def _create_result_gist(path: Path) -> tuple[str, str]: ...
def _delete_gist_best_effort(gist_id: str) -> None: ...
def _build_gist_issue_body(path: Path, raw_url: str) -> str: ...
def _build_inline_issue_body(path: Path) -> str: ...
def _create_benchmark_issue(title: str, body: str, repo: str) -> str: ...
def _submit_benchmark_result(path: Path, title: str, repo: str) -> SubmissionResult: ...
def _print_submission_fallback(readiness: GhReadiness, path: Path) -> None: ...
def _list_pubrun_gists() -> list[ManagedGist]: ...
def _reconcile_managed_gist(gist: ManagedGist) -> CleanupAssessment: ...
def _cleanup_managed_gist(gist: ManagedGist, *, confirmed: bool) -> bool: ...
```

### 6.1 Safe subprocess wrapper

Always use an argument list and `shell=False`:

```python
def _run_gh(args, *, input_text=None, timeout=30):
    env = dict(os.environ)
    env["GH_PROMPT_DISABLED"] = "1"
    result = subprocess.run(
        ["gh", *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        raise GitHubSubmissionError(
            _safe_gh_error(result.stderr)
        )
    return result.stdout.strip()
```

Security requirements:

- No `shell=True`.
- Do not include JSON in argv; pass issue bodies through stdin with `--body-file -`.
- Do not print `gh auth token`, environment variables, raw JSON, or complete contributor-controlled stderr.
- Sanitize error output because an upstream tool could echo URLs or values. Report stage and general cause.
- Apply timeouts to every external command.
- Keep the existing `OWNER/NAME` repository-slug validation.

### 6.2 Preflight

```python
def _probe_gh() -> GhReadiness:
    if shutil.which("gh") is None:
        return GhReadiness(False, False, "GitHub CLI is not installed")
    try:
        _run_gh(["auth", "status"], timeout=10)
    except GitHubSubmissionError:
        return GhReadiness(True, False, "GitHub CLI is not authenticated")
    return GhReadiness(True, True)
```

`gh auth status` can return failure for an expired or invalid credential. Treat that as unauthenticated without exposing credential details.

### 6.3 Gist creation

Use an unlisted Gist by omitting `--public`:

```python
gist_page_url = _run_gh([
    "gist", "create", str(result_path),
    "--desc", "pubrun redacted benchmark result",
])
```

Then extract and validate the Gist ID from the returned `https://gist.github.com/USER/HEXID` URL. Retrieve the Gist metadata through the authenticated API and parse it in Python:

```python
metadata = json.loads(_run_gh(["api", f"/gists/{gist_id}"]))
files = metadata.get("files", {})
if len(files) != 1:
    raise GitHubSubmissionError("unexpected Gist file count")
raw_url = next(iter(files.values())).get("raw_url")
```

Validate the raw URL:

- scheme is `https`;
- hostname is exactly `gist.githubusercontent.com`;
- path ends in `.json`;
- the metadata contains exactly one file;
- the file name matches the submitted redacted file where practical.

If Gist creation succeeds but issue creation fails, run a best-effort cleanup:

```text
gh gist delete GIST_ID --yes
```

Never delete a Gist after successful issue creation while it is the issue's only copy. Cleanup must first preserve the matching result inline or at a durable archive URL, as specified in Section 8.

### 6.4 Gist failure classification

Any Gist-stage failure should fall through to inline submission when:

- `gh` remains authenticated enough to create an issue;
- the inline body fits;
- the local share-safety check still passes.

Examples include missing Gist scope, organization policy, network error, response parsing failure, timeout, or an unexpected raw URL. Do not automatically run `gh auth refresh -s gist`; permission expansion requires explicit user action.

### 6.5 Inline issue creation

Create the issue without label arguments:

```python
issue_url = _run_gh(
    [
        "issue", "create",
        "--repo", repository,
        "--title", issue_title,
        "--body-file", "-",
    ],
    input_text=body,
)
```

External contributors can create public-repository issues but cannot reliably apply repository labels through the API. GitHub documents that setting labels during issue creation requires push access and silently drops them otherwise. The server workflow should add labels with its `issues: write` token.

### 6.6 Overall algorithm

```python
def _submit_benchmark_result(path, title, repo):
    readiness = _probe_gh()
    if not readiness.installed or not readiness.authenticated:
        return SubmissionResult(False, "web-fallback", detail=readiness.detail)

    passed, reasons = _share_check(path)
    if not passed:
        return SubmissionResult(False, "none", detail="share-safety check failed")

    gist_id = None
    try:
        gist_id, raw_url = _create_result_gist(path)
        body = _build_gist_issue_body(path, raw_url)
        issue_url = _create_benchmark_issue(title, body, repo)
        return SubmissionResult(True, "gist", issue_url)
    except GitHubSubmissionError:
        if gist_id:
            _delete_gist_best_effort(gist_id)

    body = _build_inline_issue_body(path)
    if len(body.encode("utf-8")) >= 65_000:
        return SubmissionResult(False, "web-fallback", detail="inline body too large")

    try:
        issue_url = _create_benchmark_issue(title, body, repo)
    except GitHubSubmissionError as exc:
        return SubmissionResult(False, "web-fallback", detail=str(exc))
    return SubmissionResult(True, "inline", issue_url)
```

The real code should retain stage-specific diagnostics internally for tests while showing concise, non-sensitive messages to users.

## 7. Required server-side changes

The client change alone is insufficient. The existing intake workflow expects an attachment URL and gates execution on a label the external API caller may not be allowed to set.

### 7.1 Trigger by label or marker

Change the job condition to accept the existing Issue Form label or the automatic-submission marker:

```yaml
if: >-
  contains(
    join(github.event.issue.labels.*.name, ','),
    'type:benchmark-submission'
  ) ||
  contains(
    github.event.issue.body,
    '<!-- pubrun-benchmark-submission:v1 -->'
  )
```

The marker only routes the issue to the validator. The JSON remains untrusted.

After routing, the workflow can add `type:benchmark-submission` and `status:pending` itself using `issues: write`, then replace the status after validation.

### 7.2 Accept Gist raw URLs

Add `gist.githubusercontent.com` to `ALLOWED_ATTACHMENT_HOSTS` in both:

- `.github/scripts/extract_attachment_url.py`;
- `.github/scripts/validate_benchmark_submission.py`.

Retain exact-host matching, HTTPS, bounded redirects, timeout, and byte cap. Do not allow suffix matching such as `host.endswith("githubusercontent.com")` because an incorrectly implemented suffix check can accept attacker-controlled lookalikes.

### 7.3 Accept inline JSON

Replace the URL-only extractor with a source extractor that returns exactly one of:

```text
kind=url     url=https://...
kind=inline  file=submission.json
kind=none    error=...
```

Prefer reading the issue body from the checked event JSON at `$GITHUB_EVENT_PATH` rather than placing a potentially 65 KB multiline body into an environment variable. Treat it solely as data.

Inline extraction contract:

- require the exact v1 marker;
- find exactly one fenced block labeled `json` beneath the benchmark section;
- reject zero or multiple JSON blocks for an inline submission;
- enforce the same 1 MiB cap before writing;
- write bytes to a fixed workspace path such as `submission.json`;
- never use a filename or path derived from issue content;
- never print the JSON in logs.

The validation step then selects one fixed invocation:

```bash
python3 .github/scripts/validate_benchmark_submission.py \
  --url "$ATTACHMENT_URL" --out verdict.json
```

or:

```bash
python3 .github/scripts/validate_benchmark_submission.py \
  --file submission.json --out verdict.json
```

Do not construct either command by evaluating issue text. Only the extractor's enumerated `kind` controls the branch.

### 7.4 Duplicate comments and issue edits

The workflow runs on `opened` and `edited`. Preserve idempotence:

- include a hidden receipt marker in the bot comment;
- update the existing receipt when possible instead of posting another comment on every edit;
- remove `status:pending` after a final validation result;
- ensure only one of `status:accepted` and `status:needs-fix` remains;
- do not create or delete a submitter's Gist.

## 8. Gist ownership, cleanup, and previous-run reconciliation

### 8.1 Safety rule

A Gist-backed issue contains a URL, not a copy of the JSON. The current validate-only workflow does not archive the result. A managed Gist may therefore be deleted only when:

1. issue creation failed and the Gist is an orphan;
2. the issue body has been successfully replaced with the matching inline JSON;
3. a later archival workflow has stored the matching result at a durable URL and the issue points to it; or
4. the user explicitly orders destructive deletion after being warned that it may remove the issue's only copy.

Normal cleanup must use conditions 1, 2, or 3. Condition 4 is an advanced override and must never be selected by a generic `--yes` flag.

### 8.2 Mark and record ownership

Use a unique, versioned Gist description:

```text
pubrun-benchmark-submission:v1 sha256=HEX_DIGEST issue=ISSUE_NUMBER_OR_PENDING
```

Calculate SHA-256 over the exact redacted file bytes. Create the Gist with `issue=pending`; after issue creation, update its description with the numeric issue number using `gh gist edit --desc`. This allows later runs to identify and associate prior Gists without touching unrelated user Gists.

Also write an atomic local record in a per-user state directory, not the repository or results directory:

```text
Linux:   $XDG_STATE_HOME/pubrun/benchmark-submissions.json
         or ~/.local/state/pubrun/benchmark-submissions.json
macOS:   ~/Library/Application Support/pubrun/benchmark-submissions.json
Windows: %LOCALAPPDATA%\pubrun\benchmark-submissions.json
```

Record only Gist ID/page URL, repository, issue number/URL, result digest, filename, optional local result path, creation time, and lifecycle state. Never store JSON or credentials. A local path can reveal a username, so protect the state file with user-only permissions where supported, never commit it, and tolerate moved/deleted files.

### 8.3 Discover and classify previous runs

Use the authenticated user's Gist API with bounded pagination. Filter locally for descriptions beginning exactly with `pubrun-benchmark-submission:v1 `, then require one `.redacted.json` file and expected GitHub URL hosts. Never infer ownership from filename alone.

| Classification | Default action |
|---|---|
| `issue=pending`, older than a short grace period, no issue association | Offer orphan deletion |
| Associated issue still depends on Gist | Do not delete; offer conversion to inline if matching local bytes exist and fit |
| Issue contains matching inline JSON | Offer Gist deletion |
| Issue points to verified durable archive | Offer Gist deletion |
| Local file missing and no archive verified | Retain Gist |
| Gist already absent but state remains | Offer local-state cleanup |
| Association/digest ambiguous | Leave untouched; show manual-review Gist page URL |

Limit discovery, for example to the newest 100 Gists. If the scan is incomplete, say so.

### 8.4 Safe Gist-to-inline conversion

Normal 20-23 KB results can be preserved inline before Gist deletion:

1. Load the locally recorded redacted file.
2. Re-run `_share_check` immediately.
3. Verify SHA-256 against the ownership record.
4. Build the complete inline body and require fewer than 65,000 UTF-8 bytes.
5. Fetch the current issue and verify it still contains the v1 marker and this Gist ID. Do not blindly overwrite a substantially edited issue.
6. Show the planned issue edit and deletion; get explicit confirmation.
7. Run `gh issue edit ISSUE --repo OWNER/REPO --body-file -` with the body through stdin.
8. Fetch the issue again and verify it contains the inline representation and no longer depends on the Gist URL.
9. Only then run `gh gist delete GIST_ID --yes`.
10. Verify remote deletion and update local state.

If any step before deletion fails, retain the Gist. If remote deletion succeeds but local-state update fails, report that remote cleanup succeeded and repair stale state during the next reconciliation.

Editing the issue triggers the existing `edited` workflow event so the server independently validates the inline copy. The CLI need not wait indefinitely for that workflow; matching local digest/share validation plus a successful issue refetch is the transactional prerequisite for deletion.

### 8.5 Immediate orphan rollback

If Gist creation succeeds but issue creation fails, automatically attempt to delete the just-created orphan. This is rollback of the operation the user already authorized and need not prompt again. Verify deletion. If cleanup fails, retain an `orphan` state record, report the Gist page URL, and offer cleanup during the next preflight.

### 8.6 Explicit cleanup command

Provide cleanup independently of running another benchmark:

```text
pubrun bench --cleanup-submissions
```

It should require installed/authenticated `gh`, list each managed candidate with issue and classification, default to no changes, and confirm each conversion/deletion. A read-only `--json` report is useful. `--yes` used for HPC submission must not imply cleanup consent, and ambiguous candidates must never be deleted automatically.

Example:

```text
Managed pubrun benchmark Gists:
  1. issue #123, Gist is only copy, matching local result can be converted inline
  2. orphan from 2026-07-20, safe to delete
  3. issue #118, durable archive verified, safe to delete

Choose an item to clean, `all-safe`, or Enter to leave unchanged:
```

## 9. Fallback instructions

When automation cannot complete, print only the instructions relevant to the detected state.

### `gh` absent

```text
Automatic GitHub submission is unavailable because GitHub CLI is not installed.

Submit the safe redacted file in your browser:
  https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml

Or install GitHub CLI and submit later:
  https://cli.github.com/
  gh auth login
  pubrun bench --submit-file PATH_TO_REDACTED_JSON
```

### `gh` installed but unauthenticated

```text
Automatic GitHub submission is unavailable because GitHub CLI is not authenticated.

Authenticate and submit later:
  gh auth login
  pubrun bench --submit-file PATH_TO_REDACTED_JSON

Or attach the safe redacted file in your browser:
  https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml
```

### Gist and inline routes failed

```text
The benchmark completed, but automatic GitHub submission did not.
No issue was created.

Attach this SAFE file in your browser:
  PATH_TO_REDACTED_JSON

At:
  https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml
```

If a Gist was created and cleanup failed, say so and show only its Gist page URL, allowing the user to delete it. Do not falsely report that nothing was published.

## 10. CLI compatibility recommendations

The current `--submit` and `--yes` flags govern HPC scheduler submission. Do not overload them silently for GitHub publication.

Prefer explicit options such as:

```text
--contribute             Offer/attempt GitHub contribution after the benchmark
--no-contribute          Never offer GitHub contribution
--submit-file PATH       Validate and contribute an existing redacted result
--prepare-submission     Existing browser-safe staging behavior
--gh-repo OWNER/NAME     Existing test/development override
--cleanup-submissions    Review and safely reconcile Gists from current/earlier runs
```

If interactive contribution remains the default after a local benchmark, document that `--yes` does not imply consent to public GitHub publication. Public transmission requires its own explicit flag or post-run confirmation.

## 11. Failure and transaction semantics

| Failure point | Published state | Required behavior |
|---|---|---|
| Preflight says no `gh` | Nothing | Continue benchmark; show install and web options |
| Authentication invalid | Nothing | Continue benchmark; show `gh auth login` and web options |
| Share check fails | Nothing | Refuse both automatic routes and web-ready claim |
| Gist creation fails | Nothing or uncertain | Try inline; never claim a Gist exists without a validated URL |
| Gist created, metadata lookup fails | Gist may exist | Parse ID from creation response and attempt deletion; report cleanup failure |
| Gist created, issue creation fails | Gist exists | Delete Gist best-effort, then try inline only after cleanup attempt |
| Inline body too large | Nothing new | Web attachment instructions |
| Inline issue creation fails | Nothing new | Web/install/auth instructions based on refreshed readiness |
| Issue created, URL parsing odd | Issue may exist | Preserve raw stdout internally; report uncertain success and avoid retry that could duplicate |
| Prior Gist is issue's only copy | Deletion would break issue | Offer verified inline/archive conversion; do not delete directly |
| Issue conversion cannot be verified | Gist still exists | Retain Gist and state record |
| Prior orphan cleanup fails | Orphan remains | Retain/add state record and show manual-review URL |

Prevent accidental duplicate issues by treating an ambiguous issue-creation response as an uncertain outcome, not an ordinary retry. A future enhancement can include a client-generated submission UUID in the body and search for it before retrying.

## 12. Test plan

### 11.1 Client unit tests

Mock `subprocess.run`; do not require live GitHub access.

Required cases:

1. `gh` absent: suggestion printed before benchmark; benchmark continues.
2. `gh` installed and authenticated: readiness shown; no upload occurs before confirmation.
3. User declines: no Gist or issue command.
4. Share check fails: no Gist or issue command.
5. Gist success, metadata success, issue success: returns Gist method and issue URL.
6. Gist command fails, inline body under limit, issue succeeds: returns inline method.
7. Gist permission failure specifically: inline fallback still attempted.
8. Gist created, issue fails: Gist deletion attempted before inline submission.
9. Gist cleanup fails: user is told a Gist may remain.
10. Complete inline body is 64,999 bytes: allowed.
11. Complete inline body is 65,000 bytes: rejected to web fallback.
12. Multibyte Unicode: size is measured as UTF-8 bytes, not Python characters.
13. JSON containing triple backticks: either reject as an impossible/current-schema value, or use a fence length longer than every backtick run; test it explicitly.
14. Title sanitization strips newlines and excludes identifying values.
15. `gh` timeout and malformed output do not leak JSON or tokens.
16. `--submit-file` uses the same share check and decision tree.
17. HPC path does not accidentally publish a login-node or unredacted result.
18. Successful Gist submission writes atomic ownership state and updates the Gist description with the issue number.
19. Preflight discovers a previous namespaced orphan and offers, but does not perform, cleanup by default.
20. Unrelated Gists are never classified as managed based only on filename.
21. A Gist-only issue is retained when its local result is missing.
22. A matching local file converts the issue to inline, refetch-verifies it, then deletes the Gist.
23. Digest mismatch, oversize replacement, or issue-edit conflict blocks deletion.
24. Remote deletion success plus local-state failure is reported honestly and repaired on reconciliation.

### 11.2 Extractor and validator tests

1. Existing GitHub web attachment still accepted.
2. Valid `gist.githubusercontent.com/.../*.json` URL accepted.
3. `gist.github.com` HTML page rejected as data URL.
4. Gist lookalike host rejected.
5. Redirect away from allowlist rejected.
6. Valid single inline JSON block accepted.
7. Missing marker, zero block, or multiple blocks rejected.
8. Oversize inline data rejected before JSON parsing.
9. Malformed JSON rejected without logging payload.
10. Schema, share-safety, and semantic failures behave identically for URL and inline inputs.
11. Issue edit updates/reuses receipt rather than posting unlimited comments.
12. Marker-triggered external issue receives labels from the workflow token.

### 11.3 Integration test

Use a disposable test repository or an explicitly authorized test issue. Do not test against production by default. Verify:

- actual `gh` authentication behavior with and without Gist scope;
- unlisted Gist creation and raw URL shape;
- issue body rendering;
- workflow receipt and labels;
- deletion of test issues and Gists;
- no raw benchmark payload in CLI or Actions logs.

## 13. Security and privacy invariants

These are hard requirements:

- Only a file that passes the latest local share-safety check can be transmitted.
- The unredacted sibling is never passed to `gh`, placed in an issue body, or copied into the share directory.
- Publication requires explicit user confirmation.
- No shell interpolation of title, path, JSON, URL, issue body, or GitHub output.
- Gist and issue URLs are parsed and host-validated.
- The server revalidates everything; local validation is not trusted merely because the client claims it passed.
- The server never executes, imports, or evaluates submitted JSON.
- Error output never contains the JSON, credentials, hostname, username, or private paths.
- The script does not request new OAuth scopes automatically.
- Inline size is calculated over the final encoded body.
- A partial publication is reported honestly.
- A successful Gist is not deleted until a matching inline or archived copy is verified.
- Cleanup selects only Gists carrying the exact versioned `pubrun` ownership description.
- Prior-run cleanup is opt-in and itemized; unrelated or ambiguous Gists are untouched.

## 14. Suggested implementation sequence

1. Add pure body builders, size measurement, result types, and unit tests.
2. Add noninteractive `gh` preflight and pre-benchmark messaging.
3. Add Gist creation/metadata validation/cleanup with mocked tests.
4. Add inline issue fallback and exact boundary tests.
5. Integrate the decision tree after the existing share check and explicit confirmation.
6. Update the server extractor to accept URL or inline sources.
7. Add `gist.githubusercontent.com` to both exact host allowlists.
8. Change workflow routing from label-only to label-or-marker and let the workflow apply labels.
9. Add adversarial extractor/validator fixtures.
10. Add versioned Gist descriptions, atomic local state, and immediate orphan rollback.
11. Add read-only previous-run discovery and classification.
12. Add verified Gist-to-inline conversion and `--cleanup-submissions` behind explicit confirmation.
13. Run the full local suite and the repository's complete CI matrix before declaring the CLI behavior complete.

## 15. Acceptance criteria

The change is complete only when:

- the user is advised about missing/unauthenticated `gh` before benchmarking begins;
- benchmarking remains usable without GitHub CLI or authentication;
- a share-checked result uses Gist-plus-link when available;
- a Gist failure falls back to inline JSON when the complete body is under 65,000 UTF-8 bytes;
- automatic failure ends with actionable browser/install/authentication instructions;
- both Gist and inline issues trigger the same server-side validation;
- outside contributors do not need push access to apply the routing label;
- no unredacted file can enter any publication path;
- partial Gists are cleaned up when possible and reported when not;
- namespaced Gists from earlier runs are discovered and offered for safe reconciliation;
- a Gist that is the issue's only copy is never deleted automatically;
- normal-size prior submissions can be converted to inline JSON before Gist removal;
- unrelated and ambiguous Gists remain untouched;
- all boundary, injection, duplicate, and privacy tests pass;
- documentation describes Gists as unlisted, not private, and the web attachment path remains supported.

## 16. References

- [`pubrun` repository](https://github.com/fariello/pubrun/)
- [GitHub REST API: Create an issue](https://docs.github.com/en/rest/issues/issues#create-an-issue)
- [GitHub: Attaching files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files)
- [GitHub CLI: `gh gist create`](https://cli.github.com/manual/gh_gist_create)
- [GitHub CLI: `gh gist delete`](https://cli.github.com/manual/gh_gist_delete)
- [GitHub CLI: `gh issue create`](https://cli.github.com/manual/gh_issue_create)
- [GitHub CLI: `gh auth status`](https://cli.github.com/manual/gh_auth_status)
- [GitHub CLI installation](https://cli.github.com/)
