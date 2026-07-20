# advise / naive-user - session summary

- Date: 2026-07-20 18:44 local
- Persona: naive-user (`advise/personas/naive-user.md`)
- Artifact examined: `README.md` lead (nav, tagline, positioning paragraph, Features,
  The Problem / The Solution), immediately after executing the README-reframe IPD
  (`.agents/plans/executed/20260712-2307-01-readme-reframe-mlops-register.md`, commit `f611af8`).
- Agent/model: opencode / its_direct/pt3-claude-opus-4.8-1m-us

## Why this session ran

The reframe IPD recommended a `/advise naive-user` pass on the new lead before considering the
prose final. The maintainer additionally set a specific goal mid-session: the README must not turn
away the ~95% of potential users with small / non-ML projects, while still honestly crediting that
pubrun grew up in scientific and ML/AI workflows. "Developed for scientific pipelines including
ML/AI, but its utility goes beyond that - from small one-off scripts to large endeavors."

## Round 1 - general newcomer read

Verdict: tagline landed in ~3 seconds; ~80% clear at 30 seconds. The residual confusion was
UNEXPLAINED VOCABULARY in the lead, not inherent complexity (the charter's distinction).

Gaps surfaced and dispositions (all applied with consent):
- Q1 "provenance" used but never defined -> FIXED: defined inline on first use
  ("the full provenance of a run (a complete record of how it happened: ...)").
- Q5 output called both "footprint" (Quick Start) and "manifest.json" (lead/Features) -> FIXED:
  unified to "manifest" in Quick Start.
- Q2 tagline says "runs" but paragraph led with "ML pipeline" -> FIXED via Round 2 (see D).
- Q3 "schema-validated" in the first sentence is an expert trust-signal, noise for a newcomer ->
  FIXED: removed from the lead's first sentence (still present, accurately, in the Features bullet
  and the "Built to be Trustworthy" section).
- Q6 "hydration" + `PUBRUN_META_REF` jargon in a summary Features bullet -> FIXED: rewrote the
  "Scales from Laptop to Cluster" bullet in plain language; moved the term + env var to docs/hpc.md.
- Q7 "never slows" is a strong absolute with no proof path -> FIXED: linked the non-intrusive claim
  to docs/performance.md.

## Round 2 - the maintainer's real concern: "is this for MY (non-ML) project?"

Re-read as the author of a nightly cron job / a scraper CLI (no ML, no pipeline, no cluster).
Finding: the reader would STILL likely bounce, because although the prose said "any Python run,"
every CONCRETE anchor pointed at ML (`python train.py`, "ML pipeline", "ship a model") and the
tagline led with the science/compliance word "auditable." Newcomers pattern-match on the concrete
noun, not the abstract "any."

Improvements agreed and applied (with consent):
- D: broadened line 7's examples so the FIRST concrete example is ordinary and several are listed:
  "a one-off script, a nightly job, a data pipeline, or a step in a larger ML or scientific
  workflow." ML is now one of several, not THE example.
- E: broadened "The Problem" to lead with universally-relatable pain ("a nightly job starts
  failing, or you need to know which version of your script produced last quarter's output, or
  you're comparing two runs to explain why the numbers moved") before the ML case ("shipping a
  model").
- F: added an explicit one-line inclusivity statement after the component/not-a-platform line:
  "It grew up in scientific and ML workflows, but it is useful for any run you would ever want to
  reproduce, compare, or explain - from a 20-line script to a thousand-node cluster." This says the
  maintainer's intended message out loud and honestly credits the origin.
- Tagline softened (maintainer picked the option): from "Reproducible, auditable runs: ..." to
  "Reproducible runs - know exactly what any run did, and compare any two of them: automatic
  provenance and environment capture, from a single `import pubrun`." Plain-language "know what a
  run did / compare any two" replaces the compliance-register "auditable"; every clause still maps
  to real capability.

## Honesty / validation

All edits are wording/placement only; no capability claim was added or changed. Re-verified after
the edits (actual output): `grep -rniE "A/B" README.md docs/` empty (exit 1); no positive
orchestrator/platform/MLOps overclaim (only the ":9" negation "It is not an ..."); the new
docs/performance.md link target exists.

## Residual / open follow-ups the author still owns

- The nav still surfaces "Research Use" and "HPC", and a "Publication-Ready Methods" feature bullet
  remains - a deep skimmer still gets a mild science signal downstream of the lead. This is the
  honest, deliberately-kept origin framing; the lead now clearly frames science/ML as one of many
  uses, so the "not for my project" decision is addressed where 95% of it happens (the lead). No
  change recommended unless the maintainer wants to broaden the nav labels later (would require a
  link/anchor check).
- A full `/assess documentation` pass over the whole doc set remains the recommended follow-up (per
  the IPD Step 7 and AGENTS doc-sync discipline); this session only coached the README lead.

## Disposition

Round-2 verdict: the "this is for AI/ML people, not me" bounce risk is resolved at the lead. A
non-ML newcomer now sees themselves in the tagline, the first concrete examples, and an explicit
inclusivity line, without any dishonesty and without erasing the science/ML origin.
