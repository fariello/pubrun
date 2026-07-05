# IPD link

- IPD: `.agents/plans/pending/20260705-assess-edge-cases.md`
- Summary: Edge-case / failure-mode hardening — 27 findings (3 High, most Medium/Low),
  26 proposed for fix (all Low Remediation Risk), 1 deferred (EC-27, signal-handler
  finalization, Medium-High on Functionality/Complexity). Highest-value fixes: make the
  `pubrun status` manifest/lock reader robust to malformed inputs (EC-01/02/03/04),
  cap `manual_subprocess_records` (EC-09), add configurable subprocess timeouts to
  hardware/resources/git capture (EC-10/11/13), and guard PID-liveness wrong-decision
  paths (EC-05/06/07).
- Status: PENDING — awaiting human approval; not executed.
