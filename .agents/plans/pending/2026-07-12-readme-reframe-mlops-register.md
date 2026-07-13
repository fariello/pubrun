# IPD: Reframe the README lead to the trustworthy-ML register (honest and impressive)

- Date: 2026-07-12
- Concern: documentation (accuracy + getting-started clarity) / self-documentation
- Scope: `README.md` (primarily the lead: nav, tagline, opening positioning, Features, Problem/
  Solution). Docs under `docs/` stay; some get reframed-not-removed. No source/behavior change.
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Goal

Make the README lead with what pubrun actually does, in clear "trustworthy ML" language, so a reader
grasps the capability and the payoff-for-effort in the first few seconds. The current lead is a
usability defect: it opens with a joke ("write its own Methods section while you go to the pub",
`README.md:5`) and a research/publication frame (`README.md:7`), which (a) hides the real capability
behind whimsy and (b) narrows the perceived audience to academics. This is the documentation lens's
#1 persona (the confused newcomer) failing at second one.

Guiding intent (maintainer-set): pubrun's pitch is **impressive AND honest** — the impressive part is
how much you get for near-zero effort (`pip install pubrun`, `import pubrun`, no config, no infra),
and the honesty (never overclaim) is itself a maturity signal. The reframe surfaces the impressiveness
that the current README buries; it does not inflate.

## Guardrails (hard constraints on the rewrite)

1. **pubrun is a COMPONENT, not a pipeline/platform.** Lead in trustworthy-ML register (reproducibility,
   provenance, run-to-run comparison, auditable runs) but never claim to BE an MLOps/AIOps pipeline
   (no serving, orchestration, scheduling). Frame as "the reproducibility/provenance component you use
   in or as part of your ML pipeline." This is the one overclaim to avoid because it would be false.
2. **Every claim checkable against the code.** No aspirational features. The reframe describes only
   what pubrun does today (verified list below).
3. **HPC/scale is a LEAD differentiator, not a footnote.** "Runs from a laptop to thousand-node
   clusters" via parent-child manifest hydration is genuinely differentiated vs MLflow/W&B/DVC; feature
   it. Shed only the *academic/publication* frame, not the *scale* story.
4. **Do not strand existing users; reframe, do not amputate.** All `docs/` stay. `docs/research-use.md`
   and `docs/hpc.md` remain; HPC is reframed as "scale," research stays as a supported use, just not
   the front-door identity.
5. **README stays purely technical** (adoption/usability rationale only; no career/brand language).
6. **Keep the "pubrun" identity.** The name literally means publication-ready runner and the pub joke
   is the project's origin/character. Demote it from the headline to a lighter, later touch (e.g. an
   aside or the acknowledgements/name note) rather than erasing it. Honesty includes not pretending the
   project has no personality.

## Verified current capability (what the reframe may claim)

From this session's work and the codebase (all real, all tested):
- One-import provenance capture: code state (git), dependency graph, hardware, environment, inputs,
  logs, exit status, resource usage -> a structured, **schema-validated** `manifest.json`.
- Semantic **run-to-run diffing** (`pubrun diff`, basic/standard/deep) - "verify what changed between
  two runs" (NOT A/B experimentation; do not use "A/B evaluation").
- Reproduce-a-run command extraction (`pubrun rerun`); publication-ready methods text
  (`pubrun methods`).
- **Zero runtime dependencies** on 3.11+ (single `tomli` polyfill on 3.8-3.10); cross-platform;
  non-intrusive (never alters/slows/crashes the host).
- **HPC scale:** parent-child manifest hydration (`PUBRUN_META_REF`) keeps provenance cheap across
  thousands of array jobs.
- **Secret redaction:** credentials auto-redacted before manifests are written (one-line trust signal).
- **Engineering maturity signals (true, to surface):** CI across 3 OSes x Python 3.8-3.14; a published
  manifest JSON Schema enforced by a conformance gate; a real changelog; honest-docs discipline.

## Proposed changes (ordered, validatable)

| Step | Change | Remediation Risk | Validation |
|------|--------|------------------|------------|
| 1 | Rewrite the lead (`README.md:3-7`): new tagline + one positioning paragraph in trustworthy-ML register, component-not-pipeline, payoff-for-effort. Draft lead line: *"Reproducible, auditable ML runs: automatic provenance, environment capture, and run-to-run comparison, from a single `import pubrun`."* Demote the pub joke per guardrail 6. | Low (usability; prose only) | reads clearly to a newcomer; every clause maps to a real feature |
| 2 | Reframe the Features / Problem-Solution blocks (`README.md:38-56`) to lead with reproducibility/provenance/comparison/scale; keep them accurate. | Low | each bullet traces to a shipped capability |
| 3 | Reframe the HPC section as a first-class "scales from laptop to cluster" differentiator (keep the hydration mechanics; drop academic framing). | Low | matches `docs/hpc.md` |
| 4 | Nav bar (`README.md:1`): keep all doc links (do not remove Research Use / HPC). Optionally relabel "Research Use" -> a use-cases framing only if it stays honest; otherwise leave. | Low | no broken links; nothing removed |
| 5 | Add a compact "engineering maturity" signal near the top or in a short section (CI matrix, schema-validated manifest, zero-dep, changelog) - factual, not boastful. | Low | claims verifiable in-repo |
| 6 | Sweep the rest of `README.md` for the shed-the-frame items: publication-first language, the pub headline; ensure `docs/research-use.md` present-tense pointer still accurate. Correct any "A/B" phrasing anywhere. | Low | grep clean for "A/B evaluation"; research framing demoted not deleted |
| 7 | Doc-sync: verify README claims against `docs/` (run `/assess documentation` after); CHANGELOG note that the README lead was reframed (docs-only; no behavior change). | Low | assess-documentation clean |

## Scope check

- Over-scope: NOT rewriting the whole docs set; NOT touching source/behavior; NOT relabeling anything
  that would strand a real user. The rewrite is the README lead + framing, plus the HPC section's
  register.
- Under-scope: if the lead changes but Features/Problem/Solution keep the old research framing, the
  reframe is half-done and incoherent; steps 2-3 are required, not optional.

## Required tests / validation

- Prose-only change, so no unit tests, BUT: (a) every capability claim cross-checked against the code/
  `docs/` (honest-docs); (b) `/assess documentation` run afterward per `AGENTS.md` doc-sync discipline;
  (c) links checked. No CI-matrix concern (no code/contract change) - this is the rare doc-only IPD
  where the matrix rule does not trigger.
- Recommend a `plan-review` pass on THIS IPD before execution (front-door rewrite; worth the rigor),
  and a `/advise` pass (e.g. `naive-user` on the drafted lead: does a newcomer get it in 5 seconds?).

## Spec / documentation sync

README is itself the doc; keep it consistent with `docs/` (functional_spec, cli, hpc, research-use).
CHANGELOG entry: "docs: reframed README lead to trustworthy-ML register (no behavior change)."

## Open questions

1. **Tagline wording** - confirm the draft lead line, or iterate. Keep or cut "publication-ready
   runner" as the name's meaning (guardrail 6 keeps the pub joke as a lighter touch; your call on how
   light).
2. **Nav "Research Use" label** - leave as-is (honest, it is a real use) or relabel to "Use Cases"?
   Recommend leave, to avoid churn and keep honest.
3. How prominent should the maturity signals be - a one-line badge row, or a short prose section? (Watch
   the Complexity/bloat axis; concise beats a wall of badges.)

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. On approval: draft the prose, ideally
run `plan-review` + `/advise naive-user` first, execute the ordered steps, run `/assess documentation`,
sync CHANGELOG, then move this IPD to `.agents/plans/executed/`.
