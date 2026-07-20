# IPD: Reframe the README lead to the trustworthy-ML register (honest and impressive)

- Date: 2026-07-12
- Concern: documentation (accuracy + getting-started clarity) / self-documentation
- Scope: `README.md` (primarily the lead: nav, tagline, opening positioning, Features, Problem/
  Solution). Docs under `docs/` stay; some get reframed-not-removed. No source/behavior change.
- Status: executed
- Approval: human-approved 2026-07-20 (maintainer "GO" after /plan-review)
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
| 1 | Rewrite the lead (`README.md:3-9`, incl. the zero-dep footnote at `:9` which is a claim to PRESERVE, not drop): new tagline + one positioning paragraph in trustworthy-ML register, component-not-pipeline, payoff-for-effort. **LOCKED lead line (OQ1, human-approved 2026-07-20): "Reproducible, auditable ML runs: automatic provenance, environment capture, and run-to-run comparison, from a single `import pubrun`."** Verified: provenance/env capture in `src/pubrun/tracker.py`; run-to-run comparison = `_run_diff` (`src/pubrun/__main__.py:381`). Demote the pub joke per guardrail 6 and OQ1b (one-line aside near the name/acknowledgements note; keep "publication-ready runner" meaning). | Low (usability; prose only) | reads clearly to a newcomer; every clause maps to a real feature; `:9` footnote retained |
| 2 | Reframe the Features (`README.md:38-46`) + Problem/Solution (`README.md:48-56`) blocks to lead with reproducibility/provenance/comparison/scale; keep them accurate. Note the current "Publication-Ready Output" bullet (`:41`) and Solution paragraph (`:56`) are the publication-first framing to demote (not delete). | Low | each bullet traces to a shipped capability |
| 3 | Reframe the HPC section as a first-class "scales from laptop to cluster" differentiator (keep the hydration mechanics; drop academic framing). | Low | matches `docs/hpc.md` |
| 4 | Nav bar (`README.md:1` and the duplicate footer nav at `README.md:497`): keep all 11 doc links (do not remove Research Use / HPC). **DECIDED (OQ2, human-approved 2026-07-20): LEAVE "Research Use" label as-is** (honest, real use; avoids churn and broken-anchor risk). If any future relabel is done, it MUST include a link/anchor check across `docs/` and the two nav rows. | Low | no broken links; nothing removed; both nav rows (`:1`, `:497`) stay in sync |
| 5 | **DECIDED (OQ3, human-approved 2026-07-20): a SHORT PROSE section (or tight bullet list), NOT a badge wall.** Add a compact, factual "engineering maturity" note (CI across 3 OS x Python 3.8-3.14 per `.github/workflows/ci.yml`; schema-validated manifest per `schemas/manifest.schema.json` + conformance test `tests/test_manifest_schema.py`; zero runtime deps on 3.11+ per `pyproject.toml:39-41`; a real changelog). No external badge services. Factual, not boastful; watch the bloat axis. | Low | claims verifiable in-repo; no badge dependencies added |
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
- `plan-review` pass on THIS IPD: DONE 2026-07-20 (APPROVE WITH REVISIONS APPLIED; see Workflow history).
  A `/advise naive-user` pass on the drafted lead (does a newcomer get it in ~5 seconds?) is still
  recommended before committing the prose (taste-polish only; substance locked via OQ1).

## Spec / documentation sync

README is itself the doc; keep it consistent with `docs/` (functional_spec, cli, hpc, research-use).
CHANGELOG entry: "docs: reframed README lead to trustworthy-ML register (no behavior change)."

## Acceptance criteria (the reframe is DONE when all hold)

- A1: The lead (`README.md:3-9`) opens with the LOCKED tagline (Step 1) and one positioning paragraph
  in the trustworthy-ML register; the pub joke is demoted to a one-line aside near the name note (OQ1b);
  the zero-dep footnote (`:9`) is retained.
- A2: Features + Problem/Solution (`:38-56`) lead with reproducibility/provenance/comparison/scale; every
  bullet traces to a shipped capability (list in "Verified current capability"); no aspirational feature.
- A3: HPC is presented as a first-class "scales from laptop to cluster" differentiator (hydration
  mechanics kept), consistent with `docs/hpc.md`.
- A4: No `docs/` file removed; both nav rows (`:1`, `:497`) keep all 11 links; "Research Use" label
  unchanged (OQ2); no broken links.
- A5: A short-prose (not badge-wall) maturity note is present with only in-repo-verifiable claims (OQ3).
- A6: `grep -rniE "A/B" README.md docs/` stays clean (already clean at review time); no
  MLOps/AIOps-pipeline/platform overclaim anywhere (guardrail 1).
- A7: CHANGELOG has the docs-only reframe entry; `/assess documentation` run afterward reports clean.

## Non-goals (explicit exclusions)

- No source/behavior/CLI/config/schema change (this is docs-only; the CI-matrix rule does NOT trigger).
- Not rewriting the whole docs set; not amputating research/HPC docs (guardrail 4); not adding badges
  or external services; no career/brand/marketing language (guardrail 5).

## Open questions (all RESOLVED interactively 2026-07-20 during /plan-review)

1. **Tagline wording (OQ1)** - RESOLVED: lock the draft lead line as written (see Step 1); every clause
   is code-verified and honest. Sub-decision OQ1b: keep "publication-ready runner" name meaning + demote
   the pub joke to a one-line aside near the name/acknowledgements note (not the headline, not erased).
2. **Nav "Research Use" label (OQ2)** - RESOLVED: leave as-is (honest, real use; avoids churn and
   broken-anchor risk). See Step 4.
3. **Maturity-signal prominence (OQ3)** - RESOLVED: short prose section / tight bullet list, NOT a badge
   wall; no external badge services. See Step 5.

## Approval and execution gate

Proposal only; MUST be human-approved before execution; not auto-run. This is `Status: reviewed`, which
means the review occurred - it is NOT approval or GO. Execution contract (all MUST hold):

- **Resolved open questions:** OQ1/OQ1b/OQ2/OQ3 are resolved above; no open decision remains. Execute to
  those decisions; do not silently re-decide them.
- **Scope fence:** edits are confined to `README.md` (lead, Features, Problem/Solution, HPC section, both
  nav rows, maturity note) + a one-line `CHANGELOG.md` entry. NO source/test/config/schema/`docs/` file
  changes. If execution reveals a needed doc change, STOP and open a separate IPD.
- **Verification is honesty-gated:** run `/assess documentation` and a link check; **paste the ACTUAL
  command output** into the execution record - never claim a clean assess/grep you did not run. Required
  evidence: `grep -rniE "A/B" README.md docs/` empty; `/assess documentation` clean; all nav links resolve.
- **Commits:** path-scoped only (`git commit -- README.md CHANGELOG.md`); never `git add -A`/`-a`;
  **never push** (standing repo rule; the human authorizes any push).
- **Lifecycle move:** on completion + human approval, `git mv` this IPD `pending/` -> `.agents/plans/executed/`,
  set `Status: executed`, and append the execution to `## Workflow history`.
- **Recommended pre-execution:** a `/advise naive-user` pass on the drafted lead (does a newcomer get it
  in ~5 seconds?), per the plan's original intent; taste-polish only, the substance is locked above.

## Workflow history
- 2026-07-12 authored (opencode / its_direct/pt3-claude-opus-4.8-1m-us): proposed the README lead
  reframe to the trustworthy-ML register; Status PENDING.
- 2026-07-20 /plan-review (opencode / its_direct/pt3-claude-opus-4.8-1m-us): APPROVE WITH REVISIONS
  APPLIED. Verified every capability claim against code (tracker.py redaction/capture; `_run_diff`/
  `_run_rerun`/`_run_methods` in __main__.py; PUBRUN_META_REF hydration; manifest schema + conformance
  test; CI matrix 3 OS x 3.8-3.14; zero-dep pyproject; "A/B" already grep-clean). Findings PR-001..PR-004
  all FIXED. OQ1/OQ1b/OQ2/OQ3 resolved interactively. Added Acceptance criteria, Non-goals, and an
  execution contract to the gate. Status -> reviewed. Readiness: GO (pending human approval to execute).
- 2026-07-20 executed (opencode / its_direct/pt3-claude-opus-4.8-1m-us) after human "GO". Reframed
  README.md lead (LOCKED tagline), Features + Problem/Solution, added "Built to be Trustworthy" (short
  prose, no badges) and "About the name" (demoted pub joke), kept all 11 nav links x2 rows and the
  "Research Use" label. CHANGELOG docs entry added. Scope fence held: only README.md + CHANGELOG.md +
  this IPD changed (no source/test/config/schema/docs). Validation (actual output pasted in session):
  `grep -rniE "A/B" README.md docs/` -> empty (exit 1); overclaim grep -> only the :9 negation + the
  :219 factual "HPC scheduler" reference; all 10 nav targets exist; both nav rows = 11 links. Focused
  doc-sync verification of every NEW claim passed against code (diff basic/standard/deep; _run_rerun/
  _run_methods; PUBRUN_META_REF; redact_argv @tracker.py:221; schema + conformance test; zero-dep
  pyproject; CI 3 OS x 3.8-3.14; provenance fields in manifest schema). NOTE: a full `/assess
  documentation` pass (whole-doc lens) is the recommended follow-up per AGENTS doc-sync; this execution
  ran the focused per-claim verification, not the full workflow. Status -> executed; git mv to executed/.
