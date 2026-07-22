# pubrun benchmark intake: options and recommendation

**Research date:** 2026-07-20
**Project:** [`fariello/pubrun`](https://github.com/fariello/pubrun)
**Current benchmark repository:** [`fariello/pubrun-benchmarks`](https://github.com/fariello/pubrun-benchmarks)

## Executive summary

### Top recommendation for Part A

Replace pasted JSON with a real `.redacted.json` attachment to a dedicated GitHub Issue Form in the main `pubrun` repository. Trigger a small GitHub Actions workflow when the issue is opened or edited. The workflow should:

1. Locate exactly one GitHub-hosted JSON attachment.
2. Download it with strict host, redirect, type, and size limits.
3. Parse it only as data.
4. Validate schema version 5 and perform a separate share-safety check.
5. Canonicalize the JSON, compute its SHA-256 digest, and reject duplicates.
6. Store an accepted copy on a dedicated `benchmark-data` branch in the same repository.
7. Rebuild machine-readable aggregates and a small Markdown or GitHub Pages index.
8. Label and comment on the issue with a clear accepted or rejected result.

This keeps the contributor experience to: run one command, click one link, attach one file, check one privacy box, and submit. GitHub supports `.json` attachments up to 25 MB, far beyond the current 38 KB result and the 65,536 byte issue-body ceiling. Attachments to a public repository are public and upload immediately, so local redaction must remain the primary privacy boundary. GitHub's attachment behavior and limits are documented in [Attaching files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files).

The Issue Form is useful for instructions, attestation, required metadata, default labels, and discoverability. It cannot validate JSON syntax or the pubrun schema by itself. GitHub says Issue Form answers are converted to Markdown in the issue body, and its native validations are field-level requirements rather than arbitrary schema validation. See [Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms). The Action supplies the substantive validation.

### Top recommendation for Part B

Consolidate **intake and conversation** into the main `pubrun` repository, but isolate accepted benchmark data on a dedicated `benchmark-data` branch in that same repository. Retire the separate repository as the primary submission destination. It may be archived with a prominent redirect after migration.

This is the best balance for a solo maintainer because it:

- puts authentic external issues and maintainer responses where JOSS reviewers will look;
- avoids mixing thousands of result files into the source branch;
- avoids a cross-repository personal access token or GitHub App;
- preserves one GitHub identity and audit trail per submission;
- allows the normal issue view to exclude closed `type:benchmark-submission` items;
- keeps raw accepted results, aggregate outputs, and an optional static dashboard reproducible from Git.

Current JOSS criteria explicitly look for public issues or pull requests, external engagement, responses to issues and feature requests, and community-driven improvements. The checklist also names issues or discussions from external users as evidence of community engagement. See [JOSS review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html) and the [JOSS review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html).

**Important qualification:** Moving benchmark issues to the main repository can make real participation easier to see. It does not turn automated data deposits into code contributors, and it should not be presented as a way to manufacture activity. The strongest JOSS evidence will be genuine outside use, useful discussion, resulting improvements, acknowledgments, and reproducible performance evidence.

## Evidence and reasoning convention

- Claims about GitHub, JOSS, or comparable projects are linked to sources.
- Statements labeled **Analysis** or **Recommendation** are my reasoning based on those facts and pubrun's stated constraints.
- All friction and maintenance scores are analyst judgments. They are relative estimates for pubrun, not measured values.

## Design requirements carried through the analysis

Every viable option below assumes the following non-negotiable controls:

- The unredacted file never leaves the contributor's machine.
- The sharing tool selects only the redacted filename and refuses `*.unredacted.json`.
- The contributor sees the exact path and size before sharing.
- The local checker and the GitHub-side checker use the same versioned share-safety rules.
- Server-side rejection is a backstop, not the privacy boundary. A rejected public upload may already have disclosed data.
- The installed pubrun wheel remains free of runtime dependencies. Any JSON Schema validator or submission helper is dev-only, an optional extra, or repository automation.
- Accepted data retains its raw timings. Aggregation creates derived views without replacing the submitted evidence.
- Every accepted record retains provenance such as source issue number, GitHub submitter, receipt time, schema version, content digest, and validator version.

## Part A: alternative intake mechanisms

## Option 1: Issue Form, JSON attachment, and GitHub Actions ingestion

### Mechanism

Create a `Benchmark result` Issue Form in `pubrun/.github/ISSUE_TEMPLATE/benchmark-result.yml`. The form contains short instructions, a required attachment area, a required privacy acknowledgment, and optional notes. It applies `type:benchmark-submission` and `status:pending` labels automatically. An `issues` workflow validates the attachment and archives accepted data.

GitHub supports workflows triggered by issue creation and editing, provided the workflow exists on the default branch. See [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#issues). Standard GitHub-hosted runners are free for public repositories. See [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

### Contributor experience

1. Clone or update pubrun and run `pubrun bench` as today.
2. The command writes both files locally, prints a prominent warning that the unredacted file must never be uploaded, and identifies the safe file by its full path.
3. The command runs a final local `share-check` over the redacted file.
4. On success, it prints and optionally opens a stable link to the benchmark Issue Form.
5. The researcher drags the `.redacted.json` file into the attachment field.
6. The researcher checks: `I confirm that I attached the redacted file shown by pubrun and did not attach the unredacted file.`
7. The researcher optionally adds context, then submits.
8. Within a minute or two, the Action comments with either specific repair instructions or an acceptance receipt and aggregate link.

No fork, branch, local commit, GitHub token, GitHub CLI, or manual JSON paste is required.

### Infrastructure and payload handling

- **Infrastructure:** GitHub Issues, Issue Forms, Actions, Git storage, and optionally GitHub Pages.
- **Payload:** GitHub documents a 25 MB maximum for non-media attachments and explicitly supports `.json`. A 38 KB result is tiny relative to that limit. See [Attaching files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files).
- **Cost:** Standard hosted runners are free for public repositories. The workflow should take seconds, not run benchmarks.
- **Third party:** None.

### Validation and aggregation

The Issue Form itself can require fields and acknowledgments, but it cannot perform JSON Schema validation. The Action should perform these stages in order:

1. **Submission-shape check:** correct template marker, exactly one attachment, `.json` suffix, allowed GitHub attachment host, no pasted JSON fallback unless explicitly supported.
2. **Safe download:** follow only expected GitHub redirects, cap the download at perhaps 1 MiB initially, require a JSON content type or `.json` filename, and fail closed.
3. **JSON parse:** parse without evaluating strings or interpolating contributor content into a shell command.
4. **Schema validation:** require schema version 5 and validate against a schema committed in the repository.
5. **Share-safety validation:** verify all privacy-sensitive fields contain the expected redaction representation; reject likely absolute home paths, Windows user-profile paths, unredacted hostname or username fields, and forbidden keys or representations.
6. **Semantic validation:** check scenario IDs, iteration counts, finite nonnegative timings, supported pubrun version, and internal cross-references.
7. **Canonicalization:** serialize deterministically and compute SHA-256.
8. **Deduplication:** reject or cross-link an existing digest.
9. **Archive and aggregate:** write one immutable canonical record, then regenerate summary JSON, CSV, and Markdown from all accepted records.
10. **Receipt:** comment with validator version, digest, accepted path, and aggregate link; apply `status:accepted` and close the issue. On failure, apply `status:needs-fix` and leave it open.

Use an Actions concurrency group for the archive-writing step so two accepted submissions cannot race. GitHub supports concurrency controls to serialize workflows or jobs. See [Control workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

### Privacy and authenticity

- **Privacy:** Local redaction remains decisive because GitHub states that public-repository attachments are publicly accessible and that an attachment uploads immediately, before the issue is submitted. The Action can prevent acceptance and propagation, but cannot promise to undo an accidental upload.
- **Authenticity:** The issue author supplies a light identity signal. Record `github_login`, source issue URL, submission timestamp, and digest in an ingestion envelope separate from the benchmark payload. This shows who submitted the file, not who physically ran the benchmark and not that the measurements are honest.
- **Pseudonym caution:** A stable machine token permits linking repeated submissions from the same token. It is pseudonymous, not fully anonymous. Document that property.

### Scores

| Dimension | Score | Reason |
| --- | ---: | --- |
| Contributor friction | **2 of 5** | Familiar web issue, one attachment, no Git operations. |
| Solo-maintainer burden | **2 of 5** | One form, one validator, one short workflow. Most work is initial implementation and schema evolution. |

### Pros

- Removes the issue-body size and paste-formatting problems.
- Preserves the current GitHub identity, audit trail, and triage conversation.
- Gives immediate, repeatable schema and privacy feedback.
- Can fully automate deduplication and aggregation.
- Works for payloads hundreds of times larger than the present result.
- Makes the contribution path visible through the issue-template chooser.
- Produces activity in the main repository if Part B's recommendation is adopted.

### Cons and mitigations

- **An attachment can expose an unredacted file before validation.** Mitigate with unmistakable filenames, a local fail-closed share check, an exact safe-path printout, and a confirmation step in `pubrun bench`.
- **An issue-triggered workflow processes attacker-controlled content.** GitHub specifically warns that issue titles and bodies are untrusted and can cause script injection if interpolated into executable code. See [Script injections](https://docs.github.com/en/actions/concepts/security/script-injections). Parse through files or environment variables, never inline expressions in shell source, pin third-party Actions to commit SHAs, and grant the minimum token permissions.
- **Automated writes need `contents: write`; comments and labels need `issues: write`.** GitHub recommends limiting `GITHUB_TOKEN` to the minimum required permissions. See [Using `GITHUB_TOKEN`](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token). Put validation in a read-only job and grant write permissions only to the fixed-path archival job.
- **Direct commits can race or clutter history.** Serialize writes and use a dedicated data branch. Use fixed paths derived only from validated digest and issue number.
- **Issue Forms are still described by GitHub as public preview.** Keep the underlying validator independent of the form's exact Markdown layout where practical.

### JOSS implications

**Analysis:** This option creates visible, attributable external use and a clear contribution pathway. It is stronger evidence when submissions generate useful discussion, uncover platform coverage gaps, or lead to code and documentation changes. A closed issue containing only a bot receipt is still evidence of use, but weaker evidence of collaboration than a substantive issue, PR, or external contribution.

## Option 2: Discussion category form, JSON attachment, and GitHub Actions ingestion

### Mechanism

Enable GitHub Discussions on the main `pubrun` repository and create a dedicated `Benchmark results` category with a Discussion Category Form. The contributor attaches the redacted JSON to a new discussion. An Action triggered by `discussion` creation or editing performs the same validation, archival, and aggregation pipeline as Option 1.

GitHub supports structured Discussion Category Forms in `/.github/DISCUSSION_TEMPLATE/`, using the same general form schema. See [Creating discussion category forms](https://docs.github.com/en/discussions/managing-discussions-for-your-community/creating-discussion-category-forms). GitHub Actions supports `discussion` and `discussion_comment` events. See [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#discussion).

### Contributor experience

1. Run `pubrun bench` and the local share check.
2. Follow the printed `Share this benchmark` link.
3. Attach the redacted file to the preselected `Benchmark results` discussion category.
4. Confirm the privacy acknowledgment and submit.
5. Receive a validator reply and accepted-result link in the discussion.

### Infrastructure and payload handling

- **Infrastructure:** GitHub Discussions, category forms, Actions, Git, and optionally Pages.
- **Payload:** Discussion comments support `.json` attachments under the same 25 MB non-media limit documented by GitHub.
- **Cost and third party:** Same as Option 1. No third party.

### Validation and aggregation

Use the identical validator and archive code as Option 1. Only the event adapter changes. The workflow can post a comment, add a label, and close or answer the discussion after acceptance. Keep submission state in labels such as `status:pending`, `status:accepted`, and `status:needs-fix` if discussion labels are enabled.

### Privacy and authenticity

The privacy model and light GitHub-identity signal are equivalent to Option 1. Discussion attachments are public in a public repository, so the same local redaction boundary is required.

### Scores

| Dimension | Score | Reason |
| --- | ---: | --- |
| Contributor friction | **2 of 5** | Nearly identical to an issue attachment, but some users overlook the Discussions tab. |
| Solo-maintainer burden | **2 of 5** | Same validator; slightly more event and moderation handling. |

### Pros

- Keeps data submissions out of the bug and feature issue list by construction.
- Provides a natural place for hardware-specific interpretation and follow-up.
- Still appears on the main repository and uses the contributor's GitHub identity.
- JOSS's current checklist explicitly includes external `issues/discussions` as community-engagement evidence.
- Category forms improve consistency and discoverability within Discussions.

### Cons

- The contribution path is less obvious to users conditioned to click `Issues`.
- Discussions are less naturally treated as discrete work items than issues.
- Some issue-centric maintainer tools and saved searches do not carry over cleanly.
- The event and API surface is somewhat less familiar than issue automation.
- A benchmark deposit can look like general conversation rather than an auditable submission unless the bot posts a formal receipt.

### JOSS implications

**Analysis:** Discussions can satisfy the visibility goal because JOSS now names external discussions as a community-engagement signal. Issues remain marginally stronger for a submission that has states, errors, and closure. Discussions are a good choice if keeping the issue tracker pristine is more important than the clearest possible intake audit trail.

## Option 3: Browser-only file-upload pull request with CI validation

### Mechanism

Provide a prominent `Submit through GitHub` link and a short browser walkthrough. The contributor forks through GitHub's web interface, uploads the redacted JSON into a fixed `incoming/` directory, and opens a PR. CI validates the file. A maintainer merges an accepted PR, and a post-merge workflow regenerates aggregates.

GitHub documents the fork-and-pull contribution model and browser-based PR creation. Contributors without write permission create or use a fork before proposing changes. See [Creating a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) and [Fork a repository](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo).

### Contributor experience

1. Run `pubrun bench` and the local share check.
2. Click a documentation link that opens the repository contribution flow.
3. Create a fork if GitHub asks.
4. Upload the redacted JSON in the browser to the prescribed directory.
5. Commit the change in the browser and open the proposed PR.
6. Wait for CI. If accepted, the maintainer merges it.

This avoids local Git commands but does not eliminate Git concepts or GitHub's multi-screen fork and PR flow.

### Infrastructure and payload handling

- **Infrastructure:** GitHub repository, forks, PRs, and Actions.
- **Payload:** A 38 KB JSON file is far below normal repository limits. GitHub recommends objects no larger than 1 MB and enforces 100 MB for a single Git object, so occasional larger pubrun results remain comfortable. See [Repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits).
- **Cost and third party:** No third party. Public-repository Actions are free on standard runners.

### Validation and aggregation

PR CI can validate filenames, schema, privacy rules, duplicates, and the rule that only one result file changed. After merge, an Action can rebuild aggregate outputs. Branch protection can require the validation check before merge.

### Privacy and authenticity

- Local privacy controls remain essential because the uploaded file is public in the contributor's fork and PR before CI finishes.
- A PR and commit provide a stronger GitHub-native authorship trail than an issue attachment. They still do not prove who ran the benchmark or that the measurements are genuine.

### Scores

| Dimension | Score | Reason |
| --- | ---: | --- |
| Contributor friction | **3 of 5** | No command-line Git, but fork, commit, and PR concepts remain. |
| Solo-maintainer burden | **2 of 5** | Native review and merge workflow, simple CI, but every valid result normally needs a merge decision. |

### Pros

- Strongest standard GitHub review, CI, and immutable-history model.
- Accepted data enters Git directly without a write-capable issue bot.
- External contributors appear in PR and commit history when GitHub attribution is correct.
- Aggregation naturally runs after merge.
- Branch protection and required checks are mature controls.

### Cons

- Materially higher friction for the intended researcher audience.
- Each result creates fork and PR ceremony.
- First-time contributor Actions may require maintainer approval depending on repository settings. GitHub documents approval controls for workflows from forks in [Managing GitHub Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).
- Merge conflicts become possible if aggregate files are included in contributor PRs. Avoid this by generating aggregates only after merge.
- Repetitive data PRs can crowd out code review.

### JOSS implications

**Analysis:** This creates the strongest conventional contribution record, including PR review and potentially an external commit contributor. That benefit is real under JOSS's collaborative-effort criteria. For pubrun's audience, however, lost submissions caused by PR friction may cost more community evidence than the stronger mechanics provide.

## Option 4: Optional `gh`-assisted Gist plus issue submission

### Mechanism

Offer an optional developer path, not the default path. A dev-only command such as `pubrun bench --submit-via-gh` verifies that GitHub CLI is installed and authenticated, performs the local share check, creates a Gist containing the redacted file, then opens a benchmark issue linking to that Gist. An issue Action fetches, validates, archives, and aggregates the file.

### Contributor experience

1. Install and authenticate GitHub CLI once.
2. Run the benchmark submission helper.
3. Review the exact redacted path and confirm.
4. The helper creates the Gist and issue, then opens the issue receipt in a browser.

The user does not need Git branching, but does need a separate CLI, authentication, and comfort granting it access.

### Infrastructure and payload handling

- **Infrastructure:** GitHub CLI, Gists, Issues, and Actions.
- **Payload:** The JSON is a Gist file rather than issue-body text, so the issue-body limit does not apply. Pubrun should impose its own conservative maximum, such as 1 MiB, because GitHub does not present Gists as a benchmark-object store with a service commitment tailored to this use.
- **Cost and third party:** GitHub only. No operated service.

### Validation and aggregation

The helper can validate locally before upload. The Action must independently fetch and validate the Gist, then archive a canonical copy so later Gist edits or deletion cannot change accepted evidence. The issue must record both the original Gist URL and accepted digest.

### Privacy and authenticity

- A Gist described as `secret` is unlisted, not a substitute for redaction. Use only redacted data and describe its visibility accurately.
- The authenticated GitHub user creates both Gist and issue, preserving the same light identity signal.
- Requiring a user-managed authentication tool increases the chance of token and account-support questions.

### Scores

| Dimension | Score | Reason |
| --- | ---: | --- |
| Contributor friction | **3 of 5** | One command after setup, but GitHub CLI installation and authentication are substantial prerequisites for researchers. |
| Solo-maintainer burden | **3 of 5** | Two GitHub object types, CLI compatibility, authentication support, fetch logic, and mutable-link handling. |

### Pros

- Very smooth repeat submissions for contributors who already use `gh`.
- Local validation can run immediately before upload.
- No paste or browser attachment step.
- Keeps the issue readable and small.

### Cons

- Poor default for nontechnical or non-GitHub-CLI users.
- Adds Gist lifecycle and mutability concerns.
- Creates two public artifacts for one result.
- Requires more documentation and support than Option 1.
- Offers little benefit over a GitHub attachment once attachments are supported for `.json` files.

### JOSS implications

**Analysis:** The issue remains visible on the project, but the Gist itself does not strengthen the main repository's contribution history. This is a convenience path for repeat technical contributors, not the core community intake design.

## Part A ranking

| Rank | Option | Contributor friction | Maintenance | Intake validation | Auto-aggregation | Main recommendation |
| ---: | --- | ---: | ---: | --- | --- | --- |
| **1** | Issue Form + JSON attachment + Action | **2** | **2** | Strong after submission | Yes | Adopt as the default |
| **2** | Discussion Form + JSON attachment + Action | **2** | **2** | Strong after submission | Yes | Use instead if issue-list cleanliness dominates |
| **3** | Browser-only file PR + CI | **3** | **2** | Strong before merge | Yes | Keep as an alternate documented path |
| **4** | `gh`-assisted Gist + issue | **3** | **3** | Strong locally and after submission | Yes | Optional later, only if requested by repeat contributors |

Scores use 1 for trivial and 5 for painful.

### Why Issue Forms alone do not solve the problem

Issue Forms provide input types, required fields, default labels, and consistent Markdown output. They do not natively validate a 38 KB JSON document against pubrun's schema. A large textarea also remains subject to the issue-body representation and retains the brittle paste experience. Use the form as the human interface and the attachment as the payload.

### Why `workflow_dispatch` and `repository_dispatch` are not recommended for public intake

- GitHub explicitly requires write access to manually run a `workflow_dispatch` workflow. That excludes ordinary community contributors. See [Manually running a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
- `repository_dispatch` is an API trigger. A casual contributor would need an appropriately permissioned token or a proxy service. That replaces issue friction with authentication and permission risk.
- Both are useful for maintainers or trusted automation, not open public intake.

### Why Releases assets are not recommended

Release creation and asset upload are maintainer or automation operations, not a natural permissionless contributor workflow. Community members cannot simply attach an asset to someone else's release. Releases are also the wrong semantic unit for independent benchmark submissions.

### Why a third-party form service is not recommended

A hosted form can provide polished uploads and validation, but it introduces another privacy policy, account, quota, integration credential, failure domain, and longevity risk. It weakens the GitHub identity signal unless GitHub authentication is added. The GitHub attachment flow already meets the payload-size need at no extra cost. A static GitHub Pages form would still need authentication and a write destination, pushing complexity into OAuth, Gists, a serverless function, or user tokens.

## Recommended implementation details for Option 1

### Submission contract

Add a small, versioned submission envelope either inside the redacted result or during ingestion:

```json
{
  "submission_format": 1,
  "benchmark_schema": 5,
  "redaction_version": 1,
  "pubrun_version": "...",
  "created_at": "...",
  "machine_token": "...",
  "result": {}
}
```

**Analysis:** Keeping `redaction_version` separate from `benchmark_schema` is important. Benchmark structure and privacy rules evolve for different reasons. A result can remain schema-valid while becoming unsafe under a stronger privacy policy.

### Local safety UX

The last lines of `pubrun bench` should be difficult to misread:

```text
PRIVATE, DO NOT SHARE:
  /path/to/result.unredacted.json

SAFE TO SUBMIT AFTER CHECK:
  /path/to/result.<machine-token>.redacted.json

Share check: PASSED
Submit: https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml
```

Consider an optional `pubrun bench --prepare-submission` command that copies only the checked redacted result into a dedicated `pubrun-share/` directory. This reduces wrong-file selection without adding any dependency.

### Workflow security boundaries

The workflow should be treated as an Internet-facing parser even though it runs on GitHub:

- Trigger only for the exact template marker or label.
- Do not check out or execute contributor code.
- Do not evaluate JSON strings.
- Do not place issue title, body, filename, or JSON values directly into shell program text.
- Accept only one attachment URL from an allowlist of GitHub attachment hosts.
- Enforce redirect count, final host, timeout, and byte limit.
- Canonicalize to a fresh object and filename rather than preserving an attacker-controlled name.
- Use only fixed archive paths derived from a validated lowercase hex digest and numeric issue ID.
- Avoid printing the payload in Actions logs.
- Pin third-party actions to full commit SHAs, or use first-party actions and a repository Python script.
- Set explicit job permissions. Validation needs `contents: read`; the receipt step needs `issues: write`; the archive step needs `contents: write`.
- Serialize archive writes and use idempotent digest checks.
- Keep aggregation deterministic and test it from fixtures.

### Data layout

Recommended `benchmark-data` branch layout:

```text
accepted/
  sha256-prefix/
    <full-sha256>.json
index/
  submissions.json
  submissions.csv
  summary.json
  summary.md
schema/
  benchmark-v5.schema.json
  submission-v1.schema.json
```

The canonical file should include an ingestion metadata block or have a sidecar that records issue number, submitter login, timestamps, original attachment URL, digest, and validator revision. Do not overwrite a canonical accepted object. Corrections should create a new digest and link the superseded record.

### Aggregation semantics

Do not collapse unlike systems into one headline overhead number. At minimum, stratify or expose filters for:

- pubrun version and source commit;
- Python implementation and version;
- operating system and architecture;
- CPU model or normalized CPU family where privacy rules allow it;
- scenario ID and parameters;
- warm versus cold behavior if represented;
- success, failure, timeout, and partial completion;
- run date and schema version.

Pandas warns that benchmark results can vary materially across hardware and even with different stress on nearly identical systems. See [pandas benchmarks](https://pandas.pydata.org/community/benchmarks.html). **Analysis:** For pubrun, community results are most defensible as a coverage corpus and distribution of observed overhead under described environments, not as a single cross-machine leaderboard.

### Discoverability

Use all of these low-maintenance entry points:

- A `Contribute a benchmark` badge or link near the top of the README.
- A short `Benchmarking and community results` documentation page.
- The Issue Form in the normal template chooser.
- The submission link printed at the end of every successful benchmark.
- A link from `CONTRIBUTING.md` and the JOSS paper's reproducibility material.
- A stable aggregate page that links back to the submission instructions.
- A success message that thanks and, with consent, acknowledges the contributor.

## Part B: main repository or separate benchmark repository

## JOSS and signal-of-health effects

### What JOSS actually asks reviewers to examine

Current JOSS guidance is more specific than a generic desire for a busy repository:

- open development with releases and public issues or PRs;
- ideally external engagement;
- multiple developers or other evidence of community engagement;
- responses to issues and feature requests;
- community-driven improvements;
- clear contribution, issue-reporting, and support pathways;
- confirmation of performance claims when such claims are made.

Sources: [JOSS review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html) and [JOSS review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html).

**Analysis:** Intake on the main repository helps because a reviewer can see external users, environments, maintainer responses, and resulting changes without discovering and interpreting a satellite repository. The benefit is evidentiary clarity, not raw issue count. A benchmark issue that finds a portability problem and leads to a fix is much stronger than ten silent deposits.

## Consolidating intake into `pubrun`: benefits

- **One obvious community home:** Users already on the package repository can find the form without learning that a second repository exists.
- **JOSS visibility:** External benchmark submitters and maintainer responses appear directly in the submitted software repository.
- **Traceable improvements:** Benchmark issue numbers can be linked from fixes, documentation PRs, releases, and the paper.
- **Lower credential burden:** An Action can archive to another branch in the same repository with the repository's short-lived `GITHUB_TOKEN`. A cross-repository write normally needs a GitHub App or another token because the workflow token is repository-scoped. GitHub documents use of the built-in token and recommends a GitHub App or stored personal token when additional permissions are required in [Using `GITHUB_TOKEN`](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).
- **Simpler governance:** One Code of Conduct, security policy, contributor guide, moderation surface, and label vocabulary.
- **Better discoverability:** README, docs, releases, issues, and benchmark intake share one URL namespace.

## Consolidating intake into `pubrun`: costs

- **Issue-list volume:** Each result becomes an issue, even when valid and unremarkable.
- **Notification noise:** Watchers may receive submission notifications.
- **Search dilution:** Bugs and feature requests can be harder to scan if filters are not used.
- **Metrics ambiguity:** A large number of machine-generated or repetitive issues may look inflated and should not be characterized as equivalent to development contributions.
- **Moderation exposure:** The main repository receives arbitrary public attachments and comments. The separate repository currently contains that blast radius.
- **Data growth:** Accepted JSON should not accumulate on the source branch indefinitely.

## Containing noise with GitHub features

Use a dedicated Issue Form and a small, consistent label taxonomy:

- `type:benchmark-submission`
- `status:pending`
- `status:accepted`
- `status:needs-fix`
- `status:rejected`
- optional platform labels such as `platform:linux`, applied by automation

Then:

- auto-close accepted submissions after posting the receipt;
- keep invalid submissions open only while contributor action is useful;
- link a saved search for bugs and features that excludes `type:benchmark-submission`;
- do not add benchmark submissions to release milestones;
- use issue types if available on the repository, but retain labels because labels are portable and automatable;
- pin one explanatory issue or Discussion rather than keeping routine submissions open;
- publish aggregate results separately from the issue list;
- consider moving to a Discussion category later if volume becomes distracting.

**Analysis:** At pubrun's likely near-term scale, labeled, rapidly closed benchmark issues should create little operational burden. If submissions become numerous enough to cause real noise, that is a good point to switch the same attachment workflow to a Discussion category. The validator should be written with a thin event adapter so this move is inexpensive.

## Privacy and moderation differences

There is no material privacy advantage to a separate public repository. Attachments and issue content are public in either location. The relevant protections are local redaction, clear file selection, ingestion validation, and fast moderation.

A separate repository provides some moderation isolation and lets users watch the main repository without seeing data deposits. The main repository provides better discoverability and a clearer project-level audit trail. Both preserve the submitter's GitHub identity.

## Comparable-project evidence

No reviewed project was found with pubrun's exact combination of arbitrary community machines, privacy-redacted provenance JSON, no hosted service, and researcher-focused low-friction intake. The examples below are architectural comparators, not exact precedents.

### Benchopt: separate results repository, automated PR publishing

Benchopt is a reproducible benchmarking framework with a separate [`benchopt/results`](https://github.com/benchopt/results) repository. Its documented `benchopt publish` command opens a PR against that results repository, and merged results appear on the benchmark website. The documented workflow requires the contributor to create and supply a GitHub access token. See [Manage benchmark results](https://benchopt.github.io/stable/benchmark_workflow/manage_benchmark_results.html).

**Observed design:** separate canonical results repository, PR gate, automatic publication.

**Documented downside relevant to pubrun:** the user must obtain and protect a GitHub token. Benchopt's own documentation warns that the token is sensitive. This is substantially more authentication ceremony than pubrun's target audience should face.

**Inference for pubrun:** Separating results scales organizationally, but a token-driven PR publisher is a poor default for non-Git-savvy researchers. Pubrun can retain separation at the branch level without imposing that contributor workflow.

### pandas: benchmark definitions in the main repo, automated runner and site elsewhere

Pandas keeps its ASV benchmark definitions in the main pandas repository's `asv_bench` directory. An automated runner repository executes the suite and publishes results to a site. The pandas documentation also warns that hardware and system stress materially affect results. See [pandas benchmarks](https://pandas.pydata.org/community/benchmarks.html).

**Observed design:** definitions with source, execution and published history separated into automation and a results site.

**Inference for pubrun:** Keeping benchmark functionality close to source improves discoverability, while isolating generated history avoids burdening the source tree. Pubrun's dedicated data branch follows the same separation principle without requiring another repository or service.

### MetPy: benchmark definitions in source, results in a separate repository

MetPy documents ASV benchmarks in its main codebase, execution through Jenkins and GitHub Actions, and publication through a separate results repository and GitHub Pages. See [MetPy performance benchmarking](https://unidata.github.io/MetPy/dev/devel/benchmarking.html).

**Observed design:** code and benchmark definitions in the main repository, machine-generated historical data in a results repository.

**Documented limitation relevant to pubrun:** MetPy intentionally uses the same Jenkins machine for consistency, so this is controlled automation rather than community submissions across heterogeneous systems.

**Inference for pubrun:** A satellite results repository is sensible when a project already operates cross-repository automation and controlled infrastructure. Pubrun does not need that complexity at its current scale.

### ASV: explicitly permits same-repo or separate-repo layouts

ASV's documentation says the benchmark suite may live in the project repository or a separate repository and notes that JSON result data can grow large, so storage should be planned. See [Using airspeed velocity](https://asv.readthedocs.io/en/stable/using.html). ASV also stores machine information and asks for a unique machine name, defaulting in common use to the hostname unless changed. See its [machine-information documentation](https://asv.readthedocs.io/en/stable/using.html#machine-information).

**Observed design:** both layouts are supported; growing per-machine JSON is a known consideration.

**Inference for pubrun:** There is no community norm requiring a satellite repository. Branch-level data isolation is a reasonable middle course, and pubrun's stronger redaction behavior is justified by its community-submission model.

### SciPy: benchmark suite and benchmark issues in the main repository

SciPy keeps its ASV suite in the main repository and documents local comparison commands for contributors. See [SciPy benchmarking](https://docs.scipy.org/doc/scipy/dev/contributor/benchmarking.html). Benchmark defects and work are tracked in the main issue tracker with benchmark labels, as illustrated by [SciPy issue 7658](https://github.com/scipy/scipy/issues/7658).

**Observed design:** benchmark code and benchmark-related engineering discussion remain on the main project.

**Inference for pubrun:** Main-repository labels can contain benchmark-related work without requiring a separate community identity. SciPy does not provide evidence that routine community result files should all be source-branch commits.

## Part B options compared

| Repository strategy | JOSS visibility | Tracker hygiene | Automation credentials | Data isolation | Solo-maintainer fit |
| --- | --- | --- | --- | --- | --- |
| Everything in separate `pubrun-benchmarks` repo | Low unless reviewers follow links | Excellent in main repo | Simple if automation stays there | Excellent | Good operationally, weak for stated visibility goal |
| Everything on main branch of `pubrun` | High | Manageable with labels | Simple same-repo token | Poor over time | Not recommended |
| Main-repo intake, separate results repo | High for issues | Manageable | Cross-repo token or App needed for full automation | Excellent | Acceptable, but needless credential burden |
| **Main-repo intake, same-repo data branch** | **High** | **Manageable** | **Built-in same-repo token** | **Strong** | **Recommended** |
| Main-repo Discussions, same-repo data branch | High under current JOSS criteria | Excellent | Built-in same-repo token | Strong | Strong fallback if issue volume becomes noisy |

## Clear Part B recommendation

Adopt the hybrid within `pubrun`:

1. Put the benchmark Issue Form, submission instructions, validation workflow, and human conversation in the main repository.
2. Store accepted canonical results and generated aggregates on a dedicated `benchmark-data` branch in the same repository.
3. Publish a simple aggregate index from that branch, optionally using GitHub Pages.
4. Close accepted issues automatically after the receipt is posted.
5. Archive `pubrun-benchmarks` after migration and replace its README with a clear redirect. Preserve its history.
6. If benchmark issues later create meaningful noise, move only the intake front end to a main-repo Discussion category. Keep the validator and data branch unchanged.

This recommendation is tied to the present scale and solo-maintainer constraint. If the benchmark corpus becomes large, gains independent maintainers, or needs its own release and citation lifecycle, promoting the data branch into a separate repository later is straightforward.

## Suggested phased rollout

### Phase 1: minimum useful change

1. Change the submission instruction from paste to attach.
2. Add the main-repo Benchmark Result Issue Form.
3. Add a local `share-check` and print the exact safe filename and Issue Form URL.
4. Add an Action that validates and comments, but does not yet write data.
5. Manually accept the first few submissions to tune false positives and contributor instructions.

### Phase 2: safe automation

1. Create the `benchmark-data` branch.
2. Add canonicalization, digest deduplication, and fixed-path archival.
3. Add serialized aggregation and deterministic tests.
4. Auto-label and close accepted submissions.
5. Publish a Markdown and JSON index.

### Phase 3: JOSS presentation

1. Link the intake path and aggregate from README, `CONTRIBUTING.md`, and research-use documentation.
2. Describe what the corpus proves and does not prove.
3. Acknowledge external submitters who consent to acknowledgment.
4. Link benchmark issues that led to compatibility fixes or documentation changes.
5. Cite the validator and schema version used for any performance statement.

## If you do only one thing

Stop pasting JSON into issue bodies. Put a `Benchmark result` Issue Form in the main `pubrun` repository, require the contributor to attach the locally checked `.redacted.json` file, and run a GitHub Action that validates both schema and share-safety before posting a receipt.

That one change removes the 65,536 byte dependency, reduces paste and formatting errors, accepts much larger results, strengthens discoverability, preserves the GitHub identity and discussion trail, and places genuine community use where JOSS reviewers are most likely to see it. Add automatic archival and aggregation only after the validation path has been exercised on real submissions.

## Source list

- [pubrun repository](https://github.com/fariello/pubrun)
- [pubrun-benchmarks repository](https://github.com/fariello/pubrun-benchmarks)
- [GitHub: Attaching files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files)
- [GitHub: Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [GitHub: Creating discussion category forms](https://docs.github.com/en/discussions/managing-discussions-for-your-community/creating-discussion-category-forms)
- [GitHub: Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [GitHub: Script injections](https://docs.github.com/en/actions/concepts/security/script-injections)
- [GitHub: Using `GITHUB_TOKEN`](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
- [GitHub: Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub: Control workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [GitHub: Manually running a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
- [GitHub: Repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
- [JOSS review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html)
- [JOSS review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html)
- [Benchopt: Manage benchmark results](https://benchopt.github.io/stable/benchmark_workflow/manage_benchmark_results.html)
- [pandas benchmarks](https://pandas.pydata.org/community/benchmarks.html)
- [MetPy performance benchmarking](https://unidata.github.io/MetPy/dev/devel/benchmarking.html)
- [ASV: Using airspeed velocity](https://asv.readthedocs.io/en/stable/using.html)
- [SciPy benchmarking](https://docs.scipy.org/doc/scipy/dev/contributor/benchmarking.html)
