# decisions and adaptations (persona guidance vs pubrun conventions)

The guidance file (~/VC/tmp/pubrun-docs-positioning-persona.md) was treated as input to reason about, not a directive. Adopt / adapt / decline decisions:

## Adopted

- The layered-pyramid design (Layer 0 universal front door, Layer 1 breadth as peers, Layer 2 deep pages, joined by bridge links) as the governing frame for the findings.
- The lead-persona pairing (Casual Scientist/Engineer + Senior ML/MLOps Evaluator) plus the standing documentation-lens personas.
- Signal discipline: competence shown by accurate detail, never asserted; no hype vocabulary; honest component positioning.
- The private-strategy caveat: the career/reputation motive behind AI/ML signaling is PRIVATE and appears nowhere in the IPD, this run record, or commit messages. Recorded rationale is purely technical (adoption, discoverability, correctness, positioning).
- House rule: no em/en dashes in authored Markdown (matches AGENTS.md:25). The IPD and this run record were written dash-free and verified.

## Adapted

- Layer 0 rewrite (persona proposed steps 1-3: rewrite the first screen, add bridges, add who-is-this-for): ADAPTED. The README front door was reframed and broadened just before this pass (commits f611af8, 076cbcd; executed IPD 20260712-2307-01). Re-proposing a tagline/lead rewrite would be churn and would misrepresent repo state, so the IPD assesses against the CURRENT text, treats Layer 0 as done, and proposes only the still-missing bridge/breadth/deep-page work.
- Net-new Layer-2 pages (persona step 4: create three new deep pages): ADAPTED to "reframe existing research-use.md and hpc.md" as the low-risk path; authoring dense net-new pages is deferred (complexity/bloat axis) unless a specific gap remains after reframing.
- Full em/en-dash sweep: ADAPTED. Only the three files this IPD edits get the dash cleanup (Step 5); the ~252-line remainder across the other docs is DEFERRED to a separate mechanical corrective (Medium-High complexity; bundling would balloon the adoption IPD and risk incidental damage).

## Declined / flagged conflicts

- No outright decline; the guidance was internally consistent with pubrun conventions. The one thing explicitly flagged to the human: the guidance is not authorization, and the F4 competitor-naming and F3 adopter-count calls are tone/claims decisions on which Gabriele is the final authority (raised as Open Questions 2 and 3 in the IPD).

## Fix-Bar application

Doc fixes are low Remediation Risk, so proposed by default (F1-F4, F5-subset). The only deferrals are risk-based (Medium-High complexity), not effort-based: the full dash sweep and net-new pages. No finding was silently dropped; the positive finding F6 is recorded as a guard so execution does not introduce self-praise.
