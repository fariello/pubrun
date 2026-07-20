# IPD: Assess documentation - adoption breadth and demonstrated-competence signal (layered pyramid)

- Date: 2026-07-20
- Concern: documentation (adoption/getting-started clarity + accurate positioning; honest-docs)
- Scope: `README.md` (bridge links, breadth, examples pointer) and `docs/` (reframe research-use.md and hpc.md as deep pages; add complement-positioning; examples ladder). No source/behavior change. Assess-and-propose only.
- Status: to-review
- Approval: (set when a human approves; omit until then)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Workflow history
- 2026-07-20 /assess documentation (opencode / its_direct/pt3-claude-opus-4.8-1m-us): assessed through the "adoption-and-signal documentation strategist" lead-persona pairing (Casual Scientist/Engineer + Senior ML/MLOps Evaluator) layered on the standard documentation lens; proposed 6 changes, deferred 1.

## Goal

Make pubrun's docs serve two readers at once without failing either: the large majority of users who are NOT doing ML/AI (a one-off script, a nightly job, an ETL/scraper, a simulation) must see instantly that the tool is for them, and a discerning ML/MLOps evaluator who follows a deep link must find accurate, specific, example-driven material that demonstrates real command of provenance and reproducibility in high-stakes work. The design mechanism is a layered pyramid: a universal front door (Layer 0), breadth shown as peers (Layer 1), and dedicated deep pages reached by a deliberate click (Layer 2), joined by prominent signpost "bridge" links. This assessment finds Layer 0 already largely in place (recent README reframe) and the pyramid's bridge, breadth-with-worked-examples, and deep-page signal to be the real gaps. The rationale here is purely technical: adoption, discoverability, correctness, and accurate positioning.

## Project conventions discovered (Step 0)

- Guiding principles: no dedicated GUIDING_PRINCIPLES.md; principles live in `AGENTS.md`, `docs/architecture.md` (principles + Non-Goals `architecture.md:228-233`), and `docs/functional_spec.md` (Non-Goals `functional_spec.md:29-34`). Universal fallbacks (intuitive/self-documenting, honest docs, KISS) also apply.
- Pending-plans location/format used: `.agents/plans/pending/`, filename `YYYYMMDD-HHMM-NN-<slug>.md`; five-state lifecycle (`pending/` + terminal `executed/`, `superseded/`, `not-executed/`, standing `reusable/`). Front-matter `Status:` is the single source of truth.
- Contributor/spec-sync contract: `AGENTS.md`. Two rules bind this IPD directly: (a) `AGENTS.md:25` "write no em or en dashes in authored Markdown"; (b) doc-sync discipline: every doc claim must be checkable against the code.
- IPD template: `.agents/workflows/assess/templates/ipd.md`.
- Stack / relevant context: zero-runtime-dependency Python library + CLI (`pip install pubrun`, `import pubrun`), 3.8-3.14, cross-platform; provenance/reproducibility COMPONENT (explicitly not a platform/orchestrator/experiment-tracking service, `README.md:9`, `architecture.md:228-233`).
- Review-scope exclusion applied: `.agents/workflows/` and `workflow-artifacts/` were NOT assessed as project docs.

## Prior work this assessment must NOT redo (accuracy note)

The README front door (Layer 0) was reframed and broadened very recently (commits `f611af8`, `076cbcd`; executed IPD `20260712-2307-01-readme-reframe-mlops-register.md`). The current state already satisfies much of the persona's Layer 0/1 intent, so this IPD assesses against the CURRENT text and does NOT propose re-writing the tagline or lead:
- Universal, non-ML tagline present (`README.md:5`).
- Ordinary examples listed first, ML/scientific as one of several (`README.md:7`).
- Explicit breadth/inclusivity line (`README.md:11`).
- Explicit component-not-platform positioning (`README.md:9`).
Proposing another rewrite of these would be churn and would misrepresent the repo state.

## Findings

Severity = impact if left alone; Remediation Risk = the Fix-Bar gate for acting now. Persona: Casual = the Casual Scientist/Engineer (the majority who are not doing ML); Senior = the Senior ML/AI + MLOps/AIOps Evaluator; Novice/Operator = the documentation lens's standing lead personas.

| ID | Severity | Remediation Risk | Persona | Area | Finding | Evidence (file:line) |
|----|----------|------------------|---------|------|---------|----------------------|
| F1 | High | Low (usability) | Casual + Novice | breadth legibility / examples ladder | The breadth claim ("20-line script to a thousand-node cluster") is prose only, with no worked examples behind it. `examples/` is feature-indexed (`00_auto_start.py` .. `11_cli_report.py`), not use-case-escalating, and the README never links to `examples/` at all, so a Casual reader cannot climb from a trivial script to their own use. The tool's breadth is asserted, not shown. | `README.md:11`; `examples/` (00_*..11_*, verify_all.py); README has no `examples/` reference in body |
| F2 | High | Low (usability) | Casual + Senior | the bridge (pyramid mechanism) | Signpost "bridge" links from the front door into deeper material are thin: exactly one contextual deep link exists (HPC, `README.md:49`). There is no "why use pubrun for a simple script/data job/scraper ->" reassurance link, and no contextual "using pubrun in ML/scientific pipelines ->" link; `docs/research-use.md` is reachable only via the generic top nav (`README.md:1`). Casual users get no explicit "this is for you" path; Senior users get no inviting path to the depth that would impress them. | `README.md:1,11,49`; `docs/research-use.md` reachable only via nav |
| F3 | Medium | Low (usability/accuracy) | Senior | depth and signal (deep pages) | The two audience-specific docs read as narrow rather than as Layer-2 deep pages. `research-use.md:5` leads with a small specific adopter count ("approximately four to six researchers at the University of Rhode Island"), which under-signals rather than demonstrating command of provenance in high-stakes ML/scientific work. `hpc.md:5` is gotchas-first, not a "pubrun in HPC and large-scale pipelines" thesis. Neither demonstrates ML/MLOps judgment (drift, unversioned data, "finished vs trustworthy") by concrete example. | `docs/research-use.md:5,22-38`; `docs/hpc.md:5` |
| F4 | Medium | Low (accuracy/positioning) | Senior | honesty/accuracy of positioning | pubrun never states where it fits alongside the tools a Senior evaluator will compare it to (MLflow, Weights and Biases, DVC): zero mentions anywhere. The only complement framing is generic ("alongside whatever runs it", `README.md:9`). An accurate "complements, does not replace" note (in a deep page, NOT the front door) is missing, so the evaluator cannot place pubrun in the landscape. | README.md + docs/ (no MLflow/W&B/DVC hits); generic framing at `README.md:9` |
| F5 | Medium | Medium-High (complexity) | Operator + Novice | consistency / house-rule | Em/en dashes appear on ~290 authored-Markdown lines across README + docs, directly against `AGENTS.md:25` ("write no em or en dashes in authored Markdown"). Worst offenders: `functional_spec.md` (47), `cli.md` (44), `README.md` (38), `architecture.md` (33). This is objective and high-signal, but a full 12-file sweep is a large mechanical edit that risks incidental prose damage; the low-risk subset (the docs this IPD already touches) is proposed here and the remainder deferred (see Deferred). | `AGENTS.md:25`; README.md ~38 lines, docs/ ~252 lines (en-dash version ranges incl.) |
| F6 | Low | Low | (positive; no action) | no self-praise / no hype; positioning | Positive finding, recorded so execution does not "fix" what is already right: ZERO hype vocabulary across README + docs; product-category disclaimers are strong and consistent (`README.md:9`, `architecture.md:228-233`, `functional_spec.md:29-34`); all documented CLI commands and tracked-I/O APIs verified present in `src/pubrun/`; roadmap items correctly future-tagged (`README.md:454-457`); DOI honestly marked PENDING. Do NOT add competence adjectives or self-praise anywhere. | `README.md:9,454-457`; `architecture.md:228-233`; `functional_spec.md:29-34`; `src/pubrun/__main__.py:2152-2799` |

## Proposed changes (ordered, validatable)

Fix by default; doc changes are low Remediation Risk except where noted. Highest-harm-first is not applicable (no inaccuracy found); ordered by pyramid dependency (breadth + bridge first, then deep-page signal). All prose MUST use no em/en dashes (`AGENTS.md:25`) and only code-checkable claims.

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|--------------------|--------|-------|------------------|------------|
| 1 | F2 | Add two prominent, inviting bridge signposts in the README lead region (near `:11`): a "New here? Why pubrun helps a simple script, a data job, or a scraper ->" link, and a "Using pubrun in HPC, large-scale, or ML/scientific pipelines ->" link. Point them at the deep pages reframed in Steps 3-4 (and `docs/hpc.md`). Do not touch the tagline/lead paragraph. | `README.md` | Low (usability) | both links resolve; a Casual and a Senior reader each have one obvious next click; no tagline change |
| 2 | F1 | Add a short "Examples" pointer section in the README that links to `examples/` and orders a use-case ladder in prose: trivial script -> data/analysis run -> scraper/ETL -> HPC array job -> ML training/eval run, mapping each rung to an existing example file where one exists and marking rungs that do not yet have a worked example as such (honest, no fabrication). | `README.md` | Low (usability) | link to `examples/` resolves; each named example file exists; rungs without an example are labeled, not invented |
| 3 | F3 | Reframe `docs/research-use.md` into a Layer-2 deep page "pubrun for provenance and reproducibility in scientific and ML work": open with a one-line thesis; keep the worked `minimal-research-workflow` example; demonstrate (by concrete example, not adjectives) WHY provenance is not optional in high-stakes work (silent environment drift, unversioned data/inputs, "the run finished" vs "the run is trustworthy", traceable-back-to-inputs). Keep the honest adopter/citation status but move it below the thesis so it stops being the lead signal. | `docs/research-use.md` | Low (usability/accuracy) | thesis present; every claim code-checkable; adopter count retained but not the lead; example still matches `tests/test_example_minimal_research_workflow.py` |
| 4 | F3, F4 | Reframe `docs/hpc.md` lead into a "pubrun in HPC and large-scale pipelines" thesis (keep all gotchas/diagnostics below). Add, in a deep page (hpc.md or research-use.md, NOT the front door), an accurate "Where pubrun fits alongside MLflow, Weights and Biases, and DVC" note: pubrun is a lightweight, zero-dependency, zero-infrastructure, no-account provenance COMPONENT that complements (does not replace) those tools, and where its design wins (air-gapped or egress-restricted HPC nodes, regulated environments, fast local rigor). | `docs/hpc.md` (and/or `docs/research-use.md`) | Low (accuracy/positioning) | complement framing is accurate and non-triumphal; pubrun still described as a component; no claim pubrun replaces those tools |
| 5 | F5 (subset) | Remove em/en dashes from ONLY the docs this IPD already edits (README.md, docs/research-use.md, docs/hpc.md), rewriting with period/comma/colon/parentheses per `.agents/workflows/assess/references/prose-style.md`. En-dash version ranges (e.g. "3.8-3.10") become hyphen ranges. | `README.md`, `docs/research-use.md`, `docs/hpc.md` | Low | `grep -nE "[em/en dash]"` returns zero for these three files; prose unchanged in meaning |
| 6 | F6 | No-op guard (record, do not act): during execution, do NOT add competence adjectives, self-praise, hype vocabulary, career/motive language, or any "AI safety"/policy framing; do NOT reposition pubrun as a platform/service/orchestrator. Competence is shown by accurate detail only. | (none) | Low | reviewer confirms no self-praise/hype/motive language was introduced |

## Deferred / out of scope (with reason)

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| F5 (full sweep) | Medium-High | complexity | Removing em/en dashes from all 12 README+docs files (~290 lines, ~252 outside the three files Step 5 touches) is a large mechanical edit spanning `functional_spec.md`, `cli.md`, `architecture.md`, `configuration.md`, `manifest.md`, `api.md`, `performance.md`, and the design notes. Bundling it here would balloon this adoption/signal IPD, obscure its diff, and risk incidental prose damage across files unrelated to adoption. This is a distinct, objective house-keeping concern. | A separate mechanical corrective IPD (or a `/assess documentation` prose-lens pass) that sweeps em/en dashes repo-wide, ideally with a scripted, reviewable transform and a follow-up grep gate; consider a pre-commit/CI check to prevent regressions. |
| (Layer-2 net-new pages) | Medium-High | complexity | The persona suggests creating three net-new deep pages (ML/AI model development; HPC/large-scale; regulated scientific work). pubrun already has `research-use.md` and `hpc.md`; reframing those (Steps 3-4) meets the pyramid's depth+signal at far lower risk than authoring dense net-new pages, which risks bloat (the persona's own Complexity guardrail) and unverifiable aspirational content. | If, after Steps 3-4, a specific deep page is still missing (e.g. a dedicated "regulated scientific work" page), propose it as its own small IPD with concrete, code/example-backed content, not as speculative scaffolding. |

## Scope check

- Over-scope (proposed for removal/deferral): a full repo-wide dash sweep and net-new Layer-2 pages are deferred (see Deferred), not bundled. This IPD does NOT re-touch the recently-reframed tagline/lead (would be churn and misrepresent state).
- Under-scope (needed, proposed above): the pyramid's bridge links (F2/Step 1), the breadth-with-examples ladder and README->examples pointer (F1/Step 2), and Layer-2 depth+complement-positioning via reframed existing pages (F3/F4/Steps 3-4) were missing and are added.

## Required tests / validation

Prose/docs-only; no unit tests. On execution: (a) every capability/claim cross-checked against `src/pubrun/` and existing tests (honest-docs; e.g. the research example still matches `tests/test_example_minimal_research_workflow.py`); (b) all new links resolve (README bridge links, `examples/` pointer, deep-page cross-links, both nav rows still intact); (c) `grep` shows zero em/en dashes in the three files Step 5 touches; (d) apply the persona's four tests and PASTE the results into the execution record: the 98% test (a scipy-script/URL-fetcher reader sees "this is for me" at the front door and via the "simple script" bridge), the depth test (a Senior ML/MLOps reader following the deep link finds accurate, specific command), the honesty test (every claim true and checkable; pubrun still a component), the no-self-praise test (competence shown not asserted; no career/motive language). No CI-matrix concern (no code/contract change). A `/assess documentation` accuracy re-pass is recommended after execution per `AGENTS.md` doc-sync.

## Spec / documentation sync

README is itself a doc; keep it consistent with the reframed `docs/research-use.md` and `docs/hpc.md` and with `docs/architecture.md`/`functional_spec.md` Non-Goals (do not contradict the component-not-platform positioning). CHANGELOG entry on execution: "docs: added adoption bridge links, an examples ladder pointer, and reframed research-use/hpc as deep pages with accurate MLflow/W&B/DVC complement positioning (no behavior change)."

## Open questions

1. ASSUMPTION (confirm): Layer 0 (tagline + lead) is treated as DONE by the recent reframe and is out of scope here. If Gabriele wants further front-door changes, they belong in a separate IPD. Confirm the front door is settled.
2. F4 competitor positioning: is naming MLflow/Weights and Biases/DVC explicitly desired, or is generic "complements whatever runs it" framing preferred? (Recommend naming them, accurately and non-triumphally, in a deep page only, because a Senior evaluator expects the comparison; but this is a positioning/tone call and Gabriele is the final authority on claims.)
3. F3 adopter count: keep the specific "four to six researchers at URI" line (honest but a weak lead signal) below the new thesis, or generalize it? (Recommend keep it, demoted, for honesty.)
4. F5 scope split: is limiting the dash cleanup to the three touched files (with the full sweep as a separate corrective) acceptable, or should the full sweep be pulled into this IPD despite the complexity/bloat risk?
5. Step 4 placement: put the MLflow/W&B/DVC complement note in `hpc.md`, `research-use.md`, or a short shared "Where pubrun fits" section linked from both? (Recommend one canonical location cross-linked, to avoid drift.)

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human (Gabriele) before execution, and it is NOT auto-executed. It records only technical rationale (adoption, discoverability, correctness, accurate positioning); no other rationale is stated or implied. Recommended next steps:

1. Review this IPD (optionally run `plan-review` to harden it; that sets `Status: reviewed`). Resolve the open questions. Update `Status:` (`to-review` -> `reviewed` -> `approved`), appending a Workflow-history line at each step.
2. On human approval, set `Status: approved` (+ the `Approval:` line), execute the ordered changes, run the validation (including pasting the persona four-test results and the dash grep into the execution record), and sync CHANGELOG/docs. Commit path-scoped; never push without explicit authorization.
3. Only then set the terminal `Status: executed` and `git mv` this IPD to `.agents/plans/executed/` (per the lifecycle convention).
