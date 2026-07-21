# IPD: Assess documentation - adoption breadth and demonstrated-competence signal (layered pyramid)

- Date: 2026-07-20
- Concern: documentation (adoption/getting-started clarity + accurate positioning; honest-docs)
- Scope: `README.md` (bridge links, breadth, examples pointer) and `docs/` (reframe research-use.md and hpc.md as deep pages; add complement-positioning; examples ladder). No source/behavior change. Assess-and-propose only.
- Status: executed
- Approval: human-approved 2026-07-21 (maintainer "GO" after light /plan-review; executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Workflow history
- 2026-07-20 /assess documentation (opencode / its_direct/pt3-claude-opus-4.8-1m-us): assessed through the "adoption-and-signal documentation strategist" lead-persona pairing (Casual Scientist/Engineer + Senior ML/MLOps Evaluator) layered on the standard documentation lens; proposed 6 changes, deferred 1.
- 2026-07-20 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS APPLIED. Re-verified all material claims against code/docs (F1 examples/ unlinked; F2 single HPC deep link; F3 doc leads; F4 zero MLflow/W&B/DVC hits; F5 dash counts re-counted README 41/functional_spec 48; research example test present). Findings PR-001..PR-004 FIXED: added F7 (unverified "over 500 downloads" metric on research-use.md:5 must be verified/qualified/removed), corrected stale dash counts, added Acceptance criteria (A1-A7) incl. the A5 98%-protection hard gate, hardened the gate with an execution contract + scope fence. All 6 open questions resolved interactively. Status -> reviewed. Readiness: GO (pending human approval).
- 2026-07-21 /plan-review (light re-verify, opencode / its_direct/pt3-claude-opus-4.8-1m-us): re-checked
  the plan's material claims against CURRENT main after the intervening history-scrub and sanitizer
  commits landed. NO drift: F1 (README still has no examples/ link), F2 (only the one HPC deep link at
  README.md:49; research-use reachable only via nav rows :1/:514), F4 (still zero MLflow/W&B/DVC across
  README+docs), F7 (the "over 500 downloads" + "four to six researchers at URI" line still at
  research-use.md:5), and F5 dash counts (README 41, functional_spec 48, hpc 7, research-use 1) all
  still hold exactly as written. README anchors :9 (component-not-platform) and :11 (breadth) intact, so
  the "Layer 0 already done" premise and the A5 98%-protection gate remain valid. No new findings; no
  edits needed. Verdict unchanged: APPROVE WITH REVISIONS APPLIED. Readiness: GO - PENDING HUMAN APPROVAL.
- 2026-07-21 EXECUTED (opencode / its_direct/pt3-claude-opus-4.8-1m-us) after human "GO". Step 1: added
  the README "Is pubrun for me?" bridge section (everyday-script link + HPC/ML deep link). Step 2: added
  the examples ladder into examples/ (trivial to data to file-capture/ETL to diff to HPC to ML; HPC/ML
  rungs honestly marked "no dedicated worked example yet"). Step 3: reframed docs/research-use.md to a
  high-stakes provenance thesis, generalized the adopter line, and REMOVED the unverifiable "over 500
  downloads" metric (F7). Step 4: reframed docs/hpc.md lead to a laptop-to-cluster thesis + added the
  canonical "Where pubrun fits (MLflow/Weights and Biases/DVC)" note, cross-linked from research-use.md
  (OQ5). Step 5: removed ALL em/en dashes from the three touched files (now 0 each). Step 6 guard held.
  Validation (actual): A5 grep (no MLflow/W&B/DVC in README) clean; A/B grep clean; hype grep clean; all
  example links resolve; hpc "Where pubrun fits" anchor matches the cross-link slug; nav intact; doc-sync
  spot-check maps to code. Persona four-tests all PASS. CHANGELOG entry added. Scope fence honored (only
  README + research-use.md + hpc.md + CHANGELOG). Docs-only, no CI-matrix trigger. Status -> executed.

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
| F7 | Medium | Low (accuracy/honesty) | Senior + Operator | honest-docs / verifiable metrics | Surfaced during /plan-review: `research-use.md:5` also asserts a quantitative metric, "over 500 direct downloads (excluding mirrors) on PyPI." This is an unverified adoption number in a page this IPD reframes. Per the honest-docs discipline (every claim checkable) and the "no fabricated adopters/metrics" rule, it must be verified against real PyPI data, qualified with an "as of <date>", or removed; it must not survive unverified. | `docs/research-use.md:5` |
| F4 | Medium | Low (accuracy/positioning) | Senior | honesty/accuracy of positioning | pubrun never states where it fits alongside the tools a Senior evaluator will compare it to (MLflow, Weights and Biases, DVC): zero mentions anywhere. The only complement framing is generic ("alongside whatever runs it", `README.md:9`). An accurate "complements, does not replace" note (in a deep page, NOT the front door) is missing, so the evaluator cannot place pubrun in the landscape. | README.md + docs/ (no MLflow/W&B/DVC hits); generic framing at `README.md:9` |
| F5 | Medium | Medium-High (complexity) | Operator + Novice | consistency / house-rule | Em/en dashes appear on ~290 authored-Markdown lines across README + docs, directly against `AGENTS.md:25` ("write no em or en dashes in authored Markdown"). Worst offenders (re-counted during /plan-review): `functional_spec.md` (48), `cli.md` (44), `README.md` (41), `architecture.md` (33). This is objective and high-signal, but a full 12-file sweep is a large mechanical edit that risks incidental prose damage; the low-risk subset (the docs this IPD already touches: README.md 41, hpc.md 7, research-use.md 1) is proposed here and the remainder deferred (see Deferred). | `AGENTS.md:25`; README.md 41 lines, docs/ ~250 lines (en-dash version ranges incl.) |
| F6 | Low | Low | (positive; no action) | no self-praise / no hype; positioning | Positive finding, recorded so execution does not "fix" what is already right: ZERO hype vocabulary across README + docs; product-category disclaimers are strong and consistent (`README.md:9`, `architecture.md:228-233`, `functional_spec.md:29-34`); all documented CLI commands and tracked-I/O APIs verified present in `src/pubrun/`; roadmap items correctly future-tagged (`README.md:454-457`); DOI honestly marked PENDING. Do NOT add competence adjectives or self-praise anywhere. | `README.md:9,454-457`; `architecture.md:228-233`; `functional_spec.md:29-34`; `src/pubrun/__main__.py:2152-2799` |

## Proposed changes (ordered, validatable)

Fix by default; doc changes are low Remediation Risk except where noted. Highest-harm-first is not applicable (no inaccuracy found); ordered by pyramid dependency (breadth + bridge first, then deep-page signal). All prose MUST use no em/en dashes (`AGENTS.md:25`) and only code-checkable claims.

| Step | Source finding IDs | Change | Files | Remediation Risk | Validation |
|------|--------------------|--------|-------|------------------|------------|
| 1 | F2 | Add two prominent, inviting bridge signposts in the README lead region (near `:11`): a "New here? Why pubrun helps a simple script, a data job, or a scraper ->" link, and a "Using pubrun in HPC, large-scale, or ML/scientific pipelines ->" link. Point them at the deep pages reframed in Steps 3-4 (and `docs/hpc.md`). Do not touch the tagline/lead paragraph. | `README.md` | Low (usability) | both links resolve; a Casual and a Senior reader each have one obvious next click; no tagline change |
| 2 | F1 | Add a short "Examples" pointer section in the README that links to `examples/` and orders a use-case ladder in prose: trivial script -> data/analysis run -> scraper/ETL -> HPC array job -> ML training/eval run, mapping each rung to an existing example file where one exists and marking rungs that do not yet have a worked example as such (honest, no fabrication). | `README.md` | Low (usability) | link to `examples/` resolves; each named example file exists; rungs without an example are labeled, not invented |
| 3 | F3, F7 | Reframe `docs/research-use.md` into a Layer-2 deep page "pubrun for provenance and reproducibility in scientific and ML work": open with a one-line thesis; keep the worked `minimal-research-workflow` example; demonstrate (by concrete example, not adjectives) WHY provenance is not optional in high-stakes work (silent environment drift, unversioned data/inputs, "the run finished" vs "the run is trustworthy", traceable-back-to-inputs). GENERALIZE the adopter line (OQ3 resolved): replace the specific "four to six researchers at URI" count with a non-numeric statement (e.g. "used in active research workflows"), and handle the "over 500 downloads" metric per F7 (verify, qualify with "as of <date>", or remove; do not keep unverified). | `docs/research-use.md` | Low (usability/accuracy) | thesis present; every claim code-checkable; NO unverified quantitative metric survives; adopter line generalized; example still matches `tests/test_example_minimal_research_workflow.py` |
| 4 | F3, F4 | Reframe `docs/hpc.md` lead into a "pubrun in HPC and large-scale pipelines" thesis (keep all gotchas/diagnostics below). Add ONE canonical "Where pubrun fits" note (OQ5 resolved: single source of truth, cross-linked from the other deep page) that NAMES MLflow, Weights and Biases, and DVC (OQ2 resolved: name them, in a deep page only, NEVER the front door): pubrun is a lightweight, zero-dependency, zero-infrastructure, no-account provenance COMPONENT that complements (does not replace) those tools, and where its design wins (air-gapped or egress-restricted HPC nodes, regulated environments, fast local rigor). | `docs/hpc.md` (canonical note) + `docs/research-use.md` (cross-link) | Low (accuracy/positioning) | complement framing accurate and non-triumphal; pubrun still a component; no claim it replaces those tools; note in ONE place, cross-linked; NOT in README lead |
| 5 | F5 (subset) | Remove em/en dashes from ONLY the docs this IPD already edits (README.md, docs/research-use.md, docs/hpc.md), rewriting with period/comma/colon/parentheses per `.agents/workflows/assess/references/prose-style.md`. En-dash version ranges (e.g. "3.8-3.10") become hyphen ranges. | `README.md`, `docs/research-use.md`, `docs/hpc.md` | Low | `grep -nE "[em/en dash]"` returns zero for these three files; prose unchanged in meaning |
| 6 | F6 | No-op guard (record, do not act): during execution, do NOT add competence adjectives, self-praise, hype vocabulary, career/motive language, or any "AI safety"/policy framing; do NOT reposition pubrun as a platform/service/orchestrator. Competence is shown by accurate detail only. | (none) | Low | reviewer confirms no self-praise/hype/motive language was introduced |

## Deferred / out of scope (with reason)

| Finding ID | Remediation Risk | Axis | Reason | Recommended later step |
|------------|------------------|------|--------|------------------------|
| F5 (full sweep) | Medium-High | complexity | Removing em/en dashes from all 12 README+docs files (~290 lines, ~252 outside the three files Step 5 touches) is a large mechanical edit spanning `functional_spec.md`, `cli.md`, `architecture.md`, `configuration.md`, `manifest.md`, `api.md`, `performance.md`, and the design notes. Bundling it here would balloon this adoption/signal IPD, obscure its diff, and risk incidental prose damage across files unrelated to adoption. This is a distinct, objective house-keeping concern. | A separate mechanical corrective IPD (or a `/assess documentation` prose-lens pass) that sweeps em/en dashes repo-wide, ideally with a scripted, reviewable transform and a follow-up grep gate; consider a pre-commit/CI check to prevent regressions. |
| (Layer-2 net-new pages) | Medium-High | complexity | The persona suggests creating three net-new deep pages (ML/AI model development; HPC/large-scale; regulated scientific work). pubrun already has `research-use.md` and `hpc.md`; reframing those (Steps 3-4) meets the pyramid's depth+signal at far lower risk than authoring dense net-new pages, which risks bloat (the persona's own Complexity guardrail) and unverifiable aspirational content. | If, after Steps 3-4, a specific deep page is still missing (e.g. a dedicated "regulated scientific work" page), propose it as its own small IPD with concrete, code/example-backed content, not as speculative scaffolding. |

## Acceptance criteria (the change is DONE when all hold)

- A1: Two visually-peer bridge signposts exist in the README lead region, the "simple script/data job/scraper" reassurance FIRST (novice-facing), the "HPC/large-scale/ML-scientific" deep link second; both resolve.
- A2: The README links to `examples/` and presents the use-case ladder (trivial -> data/analysis -> scraper/ETL -> HPC array -> ML training/eval), each rung mapped to a real example file or honestly labeled "no worked example yet".
- A3: `docs/research-use.md` opens with a thesis, generalizes the adopter line, contains NO unverified quantitative metric (F7), and its worked example still matches `tests/test_example_minimal_research_workflow.py`.
- A4: `docs/hpc.md` opens with a large-scale/pipeline thesis and hosts the single canonical "Where pubrun fits" note naming MLflow/W&B/DVC as complements (cross-linked from research-use.md).
- A5 (98% protection, hard criterion): NO MLflow/Weights and Biases/DVC name, and no ML/MLOps-depth or landscape-comparison language, appears in the README lead / above the fold. The competitor and depth material lives ONLY in the deep pages. (Enforce: `grep -niE "mlflow|weights.*biases|w&b|\bdvc\b" README.md` returns zero.)
- A6: README.md, docs/research-use.md, docs/hpc.md contain zero em/en dashes; prose meaning unchanged.
- A7: No self-praise, hype vocabulary, competence adjectives, or career/motive language introduced anywhere (F6 guard); pubrun still positioned as a component, never a platform/service/orchestrator.

## Scope check

- Over-scope (proposed for removal/deferral): a full repo-wide dash sweep and net-new Layer-2 pages are deferred (see Deferred), not bundled. This IPD does NOT re-touch the recently-reframed tagline/lead (would be churn and misrepresent state).
- Under-scope (needed, proposed above): the pyramid's bridge links (F2/Step 1), the breadth-with-examples ladder and README->examples pointer (F1/Step 2), Layer-2 depth+complement-positioning via reframed existing pages (F3/F4/Steps 3-4), and verifiable-metric hygiene on the reframed page (F7/Step 3) were missing and are added.

## Required tests / validation

Prose/docs-only; no unit tests. On execution: (a) every capability/claim cross-checked against `src/pubrun/` and existing tests (honest-docs; e.g. the research example still matches `tests/test_example_minimal_research_workflow.py`); (b) all new links resolve (README bridge links, `examples/` pointer, deep-page cross-links, both nav rows still intact); (c) `grep` shows zero em/en dashes in the three files Step 5 touches; (d) apply the persona's four tests and PASTE the results into the execution record: the 98% test (a scipy-script/URL-fetcher reader sees "this is for me" at the front door and via the "simple script" bridge), the depth test (a Senior ML/MLOps reader following the deep link finds accurate, specific command), the honesty test (every claim true and checkable; pubrun still a component), the no-self-praise test (competence shown not asserted; no career/motive language). No CI-matrix concern (no code/contract change). A `/assess documentation` accuracy re-pass is recommended after execution per `AGENTS.md` doc-sync.

## Spec / documentation sync

README is itself a doc; keep it consistent with the reframed `docs/research-use.md` and `docs/hpc.md` and with `docs/architecture.md`/`functional_spec.md` Non-Goals (do not contradict the component-not-platform positioning). CHANGELOG entry on execution: "docs: added adoption bridge links, an examples ladder pointer, and reframed research-use/hpc as deep pages with accurate MLflow/W&B/DVC complement positioning (no behavior change)."

## Open questions (all RESOLVED during /plan-review 2026-07-20)

1. Layer 0 front door settled? RESOLVED: yes, confirmed by Gabriele ("we're fine as is"). The tagline/lead are DONE by the recent reframe and are OUT OF SCOPE here; further front-door changes would be a separate IPD.
2. Name MLflow/Weights and Biases/DVC? RESOLVED: yes, name them accurately and non-triumphally, in a deep page ONLY, never the front door (see Step 4 and A5).
3. Adopter count line? RESOLVED: GENERALIZE it (drop the specific "four to six at URI" count for a non-numeric statement); see Step 3.
4. Dash cleanup scope? RESOLVED: touched files only (README, research-use, hpc); the full repo-wide sweep is a separate corrective IPD (see Deferred).
5. Complement-note placement? RESOLVED: ONE canonical location (in `hpc.md`), cross-linked from `research-use.md`; single source of truth to avoid drift (see Step 4).

New during /plan-review:
6. F7 "over 500 downloads" metric? RESOLVED: verify against real PyPI data and keep only if accurate (qualified "as of <date>"), else generalize or remove; no unverified metric survives (see Step 3 and A3).

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human (Gabriele) before execution, and it is NOT auto-executed. It records only technical rationale (adoption, discoverability, correctness, accurate positioning); no other rationale is stated or implied. Execution contract (all MUST hold):

- **Resolved open questions:** OQ1-OQ6 are all resolved above; execute to those decisions, do not silently re-decide them.
- **Scope fence:** edits are confined to `README.md`, `docs/research-use.md`, `docs/hpc.md`, and a one-line `CHANGELOG.md` entry. NO source/test/config/schema changes, and NO edits to other `docs/` files (the full dash sweep and any net-new pages are deferred). If execution reveals a needed change outside this fence, STOP and open a separate IPD.
- **98% protection (hard):** acceptance criterion A5 is a gate, not a preference: no competitor names or ML-depth/landscape language above the fold; `grep -niE "mlflow|weights.*biases|w&b|\bdvc\b" README.md` must return zero.
- **Honesty-gated validation:** run the link checks, the dash grep, the A5 grep, and PASTE THE ACTUAL command output plus the persona four-test results into the execution record. Never claim a clean check you did not run. No unverified quantitative metric may ship (F7).
- **Commits:** path-scoped only (`git commit -- <listed files>`); never `git add -A`/`-a`; never push without explicit authorization.
- **Lifecycle move:** on completion + human approval, set terminal `Status: executed` and `git mv` this IPD to `.agents/plans/executed/`, appending a Workflow-history line.

Recommended next steps: (1) human approval sets `Status: approved` + the `Approval:` line; (2) execute, validate (pasting actual output), sync CHANGELOG/docs; (3) then the lifecycle move above.
