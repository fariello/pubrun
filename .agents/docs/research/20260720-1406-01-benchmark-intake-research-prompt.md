# Research request: better ways to gather and receive community benchmark results for an open-source Python library

You are GPT-5.6 acting as a research analyst with web search. Investigate the question below, then return your findings as a downloadable Markdown (`.md`) file so it can be handed back to the engineering team. Prefer current, citable sources (link them); flag anything that is your own reasoning versus a sourced fact. No em dashes or en dashes in your prose.

## Who is asking and what the project is

`pubrun` (https://github.com/fariello/pubrun) is a small, zero-runtime-dependency Python library and CLI that captures execution provenance for a run (code state, dependency graph, hardware, environment, inputs, logs, exit status, resource usage) into a structured `manifest.json`, with essentially no ceremony (`import pubrun`). It ships a benchmark harness (`pubrun bench`) that measures pubrun's own overhead across a matrix of scenarios and produces a JSON result. The project is preparing a JOSS (Journal of Open Source Software) submission, so demonstrable community activity and reproducibility matter.

Hard constraints that any proposal MUST respect:
- **No standing server / no hosted service we operate.** We will not run a database, an API, a queue, or any always-on infrastructure. Solutions must ride on infrastructure we already have (GitHub) or on zero-maintenance/serverless primitives, and the cost/maintenance burden must be near zero for a solo-maintained OSS project.
- **Privacy first.** Benchmark results can embed the contributor's hostname, OS username, and home-directory paths. We already redact these before anything is shared, and this must remain true for any intake method.
- **Zero runtime dependencies in the library itself.** The benchmark/submission tooling is dev-only and not shipped in the installed wheel, but we still prefer minimal, standard tooling.
- **Low friction for contributors**, who are researchers, not necessarily Git power users.

## How we gather and receive benchmarks today (the current design, and why)

1. **Generate.** A contributor runs `pubrun bench` from a source checkout. The harness runs the scenario sweep and writes two local files: a full `*.unredacted.json` (kept local, never shared) and a `*.redacted.json` (safe to share). The redacted file has the hostname, username, and home paths masked in-content, and its FILENAME uses a stable non-identifying hash token instead of the hostname.
2. **Shrink.** We recently reworked the result schema (call it schema version 5) to be compact and non-redundant while losing no data: raw per-iteration timings are retained (rounded to 6 decimals), scenario descriptors are defined once rather than repeated per pass, derived summary statistics are dropped because they are recomputable from the raw timings, and the JSON is written in compact form. This took a real result from about 204 KB (pretty) / 120 KB (compact) down to about 38 KB.
3. **Submit.** The contributor opens a GitHub **issue** on a SEPARATE public repository, `pubrun-benchmarks` (https://github.com/fariello/pubrun-benchmarks), and pastes the redacted JSON into the issue body. GitHub caps an issue body at 65,536 bytes; the whole point of the schema-5 shrink was to fit the redacted result inside that cap (it now does, at about 38 KB, with headroom). If a result ever exceeds the cap, our tooling warns the contributor to attach the file to the issue instead of pasting it.
4. **Why this shape.** Issues give us: a zero-infrastructure intake (GitHub hosts it), a human-readable audit trail, the contributor's GitHub identity as a light authenticity signal, and a place to discuss/triage a submission. We deliberately avoided pull requests (they ask a non-Git-savvy researcher to fork, branch, commit, and open a PR) and avoided any server we would have to operate.

Known rough edges we want your research to improve on: (a) pasting a 38 KB JSON blob into an issue body is clunky and brittle (size cap, formatting, no schema validation at intake); (b) results are un-aggregated until a maintainer manually pulls them; (c) it is easy for a contributor to get the redaction or the paste wrong; (d) discoverability of "here is how you contribute a benchmark" is weak.

## What we want from you

### Part A: Alternative intake mechanisms (find 2 to 4, hopefully better)

Propose **2 to 4** concrete, different ways for us to gather and receive redacted benchmark result JSON from the community that do NOT require us to stand up or operate a separate server. For EACH option, give:
- A clear description of the mechanism and the contributor's step-by-step experience.
- What infrastructure it rides on (must be GitHub-native or a genuinely zero-maintenance/serverless primitive; if it needs any third-party service, name it and its free-tier limits and longevity risk).
- How it handles the ~38 KB (and occasionally larger) redacted payload without the issue-body size problem.
- Whether/how it can validate the submission against our schema at intake, and whether/how it can auto-aggregate accepted results.
- How it preserves the privacy guarantee and the light authenticity signal.
- Friction for a non-Git-savvy researcher (1 = trivial, 5 = painful) and maintenance burden for a solo maintainer (same scale).
- Concrete pros and cons, and any JOSS-activity implications.

Candidate directions to evaluate (not exhaustive; add better ones you find): GitHub Issue Forms / structured issue templates with validation; a GitHub Actions workflow triggered by an issue/comment that validates + redacts-checks + auto-commits the result into the repo and updates an aggregated table; GitHub Discussions instead of issues; file attachments or Gists referenced from an issue; a PR-based flow made painless via a web form or a bot; GitHub's `workflow_dispatch` / repository_dispatch with a small client; a static intake via a form service that files a GitHub issue; using GitHub Releases assets. Rank them at the end with a clear recommendation for a solo-maintained, JOSS-bound OSS project.

### Part B: Submit to the main `pubrun` repo instead of a separate `pubrun-benchmarks` repo?

JOSS reviewers and the wider signal-of-health value visible ACTIVITY on the main project. We currently route benchmark submissions to a SEPARATE repo (`pubrun-benchmarks`). Analyze the tradeoff of instead routing benchmark issues (or whatever intake mechanism you recommend in Part A) to the **main `pubrun` repository**:
- Pros and cons of consolidating benchmark intake into the main repo, specifically regarding: JOSS "activity/community" signals (issues, contributors, discussion on the main repo), maintainer triage noise, keeping the main issue tracker focused on bugs/features versus data submissions, the effect on the main repo's issue/label hygiene, and any privacy or moderation differences.
- Whether GitHub features (labels, issue types, Discussions categories, separate templates) let us get the "activity on the main repo" benefit while containing the noise.
- What most comparable JOSS-published or reproducibility-focused OSS projects actually do (cite examples if you can find them): do they collect community benchmark/environment data on the main repo, a satellite repo, or elsewhere, and what were the observed downsides?
- A clear recommendation: consolidate into `pubrun`, keep the separate repo, or a hybrid, with the reasoning tied to the JOSS-activity goal and the solo-maintainer constraint.

## Output format

Return a single downloadable Markdown (`.md`) file titled something like "pubrun benchmark intake: options and recommendation". Structure it as: a short executive summary with your top recommendation for Part A and for Part B; the per-option analysis for Part A with the friction/maintenance scores and a ranking table; the Part B tradeoff analysis with cited comparable-project examples; and a closing "if you do only one thing" recommendation. Cite sources inline with links. Keep it practical and specific to a solo-maintained, zero-server, privacy-conscious, JOSS-bound project. No em dashes or en dashes.
