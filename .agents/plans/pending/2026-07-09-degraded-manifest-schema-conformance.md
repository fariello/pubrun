# IPD: Schema conformance for degraded / startup manifests (the `pending` capture_state)

- Date: 2026-07-09
- Concern: documentation (accuracy) / testing / bugs
- Scope: `schemas/manifest.schema.json`, `docs/manifest.md`, `tests/test_manifest_schema.py`
- Status: PENDING (awaiting human approval; not executed)
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Origin

Filed while investigating the follow-up noted in
`.agents/plans/executed/2026-07-09-manifest-schema-reconciliation.md` ("ghost-mode manifests"). The
investigation **corrected the premise** and found the real, narrower defect.

**Ghost mode does NOT write a manifest** (verified): on a run-dir-creation failure the tracker sets
`writer = None`, `is_active = False` and returns (`tracker.py:120-140`); the empty `{}` section data
lives only in memory and is never serialized. `tests/test_quality.py::test_ghost_mode_no_artifacts`
confirms no `manifest.json` is produced. So there is no "ghost manifest" on disk to validate — the
earlier "~16 violations" was a hypothetical in-memory dict, not a real file.

**The real defect is the `pending` capture_state on the STARTUP manifest.** `start()` writes a
manifest synchronously (`writer.write_startup_manifest()`, `tracker.py:188`) BEFORE the async
hardware/host/filesystem capture completes. Those three sections are stamped
`capture_state.status = "pending"` (`tracker.py:283-285`, and `filesystem.py:351`) until the
background `pubrun-hw` thread fills them in. **This startup manifest is a real on-disk file that
persists and is read by `pubrun status`/`inspect`/`show` when a run crashes before finalizing.**

But the schema's `status_value` enum is `["complete","partial","unavailable","suppressed","failed"]`
— it **does not include `"pending"`**. So **every startup/crashed manifest fails schema validation**
on the hardware/host/filesystem sections (verified: 3 errors, all `'pending' is not one of [...]`).

This is the same CLASS as the empty-`console` bug the Windows CI caught: a legitimate on-disk
manifest shape the schema rejects.

## Verified facts

- `"pending"` is emitted at `tracker.py:283-285` (hardware/host/filesystem) and `filesystem.py:351`
  (hung-mount live probe), and is consumed at `report/checks.py:98` — it is an intentional, real
  transient status, not an accident.
- The schema `status_value` enum (`$defs/status_value`) omits `pending`.
- `docs/manifest.md` (Capture State section) also does not list `pending`.
- A startup/pre-finalize manifest validates with exactly 3 errors, all `pending`-related.

## Proposed changes (ordered, validatable)

| Step | Change | Files | Remediation Risk | Validation |
|------|--------|-------|------------------|------------|
| 1 | Add `"pending"` to the schema `status_value` enum (it is a real, emitted, terminal-for-now-transient status). | `schemas/manifest.schema.json` | Low | a startup/pre-stop manifest validates with 0 errors |
| 2 | Document `pending` in the `docs/manifest.md` "Capture State" list (transient: async section not yet populated by the background hardware thread; may persist in a crashed run's startup manifest). | `docs/manifest.md` | Low | doc lists all emitted statuses |
| 3 | Add a regression test: a manifest captured **immediately after `start()` (pre-`stop()`)** conforms to the schema — pinning the startup/crashed-manifest shape as a valid, gated case. | `tests/test_manifest_schema.py` | Low | new test passes; would fail without step 1 |

## Scope check

- Over-scope: none. NOT touching ghost mode (it writes nothing — no schema surface). NOT changing
  the `pending` runtime behavior (it is correct); only teaching the schema/docs/tests about it.
- Under-scope guard: also validate a manifest that crashed *while* a section is `pending` if it can
  be produced deterministically in a test; otherwise the pre-`stop()` startup manifest is the
  representative shape (same section states).

## Required tests / validation

- New pre-`stop()` conformance test passes; the existing full-manifest + variant gates stay green.
- `pytest tests/ -v` green on the full matrix. (Per the matrix-validation discipline in `AGENTS.md`:
  schema changes must be confirmed on CI, not just locally — the `console` fix taught us this.)

## Spec / documentation sync

`docs/manifest.md` Capture State list updated to include `pending`; CHANGELOG entry (schema now
accepts the transient `pending` status so startup/crashed manifests validate).

## Open questions

1. Should `pending` be a first-class *documented* status or treated as an internal transient that
   ideally never persists? Recommendation: document it — it demonstrably persists in crashed runs'
   startup manifests, so pretending it is internal-only would be dishonest (and the schema must
   accept what is actually written).
2. Are there OTHER transient statuses emitted anywhere that the enum also omits? Step 1 should grep
   for all emitted `status` string literals and reconcile the enum against the full set in one pass
   (avoid a second round-trip).

## Approval and execution gate

Proposal only; human-approved before execution; not auto-run. On approval: reconcile the enum + docs
+ test, verify on the CI matrix, sync CHANGELOG, then move this IPD to `.agents/plans/executed/`.
