# Decisions - assess-documentation 20260704-231905

## Process deviation

This assessment fixed docs directly (DOC-01 through DOC-17) instead of writing
an IPD first and then executing. This violated the assess workflow protocol
("does not modify application code"). Rationale: docs-only fixes with Low
remediation risk; the user explicitly asked for direct fixes. Documented here
for honesty.

## Key decisions

1. DOC-18 (functional_spec.md Section 3.2): The spec said "MUST NOT wrap stdout
   unless configured." This was ASPIRATIONAL when written (code did wrap by
   default). Today's code change made the spec finally correct. No action needed.

2. DOC-19/20/21 left as remaining items: these are Low-severity completeness
   gaps (not inaccuracies) and can be addressed in a follow-up without urgency.

3. The root cause of all High findings: **code changes without doc updates**.
   This is a process gap, not a documentation-quality gap. The docs were
   accurate when written; they became stale because the code was changed
   without a mandatory doc-sync step.

## Recommendation for process improvement

The documentation lens rubric already says "Verify claims against the code."
The gap is in *execution discipline*, not in the rubric. Two process fixes:

1. Every code-changing commit that alters user-visible behavior should include
   a doc update in the same commit (or the PR is incomplete).
2. The assess-documentation workflow should explicitly run a diff between
   `default.toml` keys and `docs/configuration.md` keys as a mechanical check,
   not just a reading pass.
