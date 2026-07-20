# assess documentation (adoption-and-signal lens) - report

- Run ID: 20260720-193804
- Concern: documentation (adoption breadth + demonstrated-competence signal; layered pyramid)
- Persona adopted: "the Adoption-and-Signal Documentation Strategist" lead-persona pairing (the Casual Scientist/Engineer majority + the Senior ML/AI + MLOps/AIOps Evaluator), layered on the standard documentation lens.
- Agent/model: opencode / its_direct/pt3-claude-opus-4.8-1m-us
- Mode: assess-and-propose only. No docs edited, no plan executed. IPD produced for human approval.

## Verdict for documentation

CONDITIONAL PASS with a clear improvement path. The docs are HONEST and ACCURATE (zero hype vocabulary, strong and consistent component-not-platform disclaimers, all documented commands/APIs verified present in code). The front door (Layer 0) was recently reframed and already speaks to the non-ML majority. The real gaps are the pyramid's MECHANISM: thin signpost bridges into deep material, breadth asserted without a worked examples ladder, and two audience docs that read narrow rather than as deep pages that demonstrate command. One objective house-rule violation (em/en dashes vs AGENTS.md:25) is systemic; the low-risk subset is proposed and the full sweep deferred as its own corrective.

## Top findings (see findings.csv for the full table)

| ID | Severity | Remediation Risk | Persona | Summary |
|----|----------|------------------|---------|---------|
| F1 | High | Low | Casual + Novice | Breadth claim has no worked examples behind it; examples/ is feature-indexed and unlinked from README. |
| F2 | High | Low | Casual + Senior | Signpost bridge links into deep docs are thin (one HPC link only); no "simple script" reassurance link, no contextual ML/science deep link. |
| F3 | Medium | Low | Senior | research-use.md and hpc.md read narrow, not as Layer-2 deep pages; under-signal rather than demonstrate command. |
| F4 | Medium | Low | Senior | No MLflow/W&B/DVC complement positioning anywhere; evaluator cannot place pubrun in the landscape. |
| F5 | Medium | Med-High (full) / Low (subset) | Operator + Novice | ~290 em/en-dash lines vs AGENTS.md:25; subset proposed, full sweep deferred. |
| F6 | Low | Low | (positive) | Hype-clean, positioning-accurate, doc-to-code verified. Recorded so execution does not "fix" what is right. |

## Proposed plan summary

Six ordered changes operationalizing the layered pyramid: (1) two README bridge signposts; (2) a README examples-ladder pointer to examples/; (3) reframe research-use.md into a deep page that shows why provenance is not optional in high-stakes work; (4) reframe hpc.md lead + add accurate MLflow/W&B/DVC complement positioning in a deep page; (5) dash cleanup limited to the three touched files; (6) a no-op guard against self-praise/hype/motive language. Deferred (Medium-High complexity): the repo-wide dash sweep and any net-new Layer-2 pages.

## Persona four-test read (pre-execution, on the CURRENT docs)

- 98% test: PASS at the tagline/lead (recent reframe); FAILS at discoverability (no "this is for you" bridge or examples path). Steps 1-2 close it.
- Depth test: PARTIAL. A Senior reader who digs finds accurate command in cli/manifest/architecture, but the audience deep pages under-signal and there is no landscape positioning. Steps 3-4 close it.
- Honesty test: PASS. Every spot-checked claim is code-backed; positioning is accurate; DOI/roadmap honestly marked.
- No-self-praise test: PASS. No hype, no motive/career language present. Step 6 guards it in execution.

## Next step

Human review/approval of the IPD (optionally via plan-review) before any execution. This pass edited no docs and executed nothing.
