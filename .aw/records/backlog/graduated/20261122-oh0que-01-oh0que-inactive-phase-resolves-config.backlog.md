- Id: oh0que
- Status: graduated
- Graduated-To: oh0que
- Set: oh0que
- Work-Kind: bug
- Priority: low
- Summary: pubrun.phase() with no active run resolves the full configuration on every call (about 106 us per block)
- Short-Description: pubrun.phase() with no active run resolves the full configuration on every call (about 106 us per block)
- Blocks-Release: next

> Write and proofread this backlog item per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history
- 2026-11-23 graduated (aw backlog): graduated by run run-20261123T005542Z-1001883: 68iw9a
- 2026-11-22 created (aw backlog): pubrun.phase() with no active run resolves the full configuration on every call (about 106 us per block)

Observed while executing IPD 3tvesf (2026-11-22, git af36c85, CPython 3.14.6). _handle_inactive() in src/pubrun/core.py (lines 56-70) calls resolve_config() on every inactive annotate()/phase() call to read [events].on_inactive_annotate. resolve_config reloads and deep-copies the default and local TOML layers each time (cProfile: 500 inactive phases spent 0.207 s of 0.215 s in resolve_config). Measured cost per inactive phase minus contextlib.nullcontext: 108.4 us cold, 105.9 us warm median (n=30 x 1000 blocks), about 6x the 18.3 us of an ACTIVE phase that writes two events. Impact: library code that leaves pubrun.phase() in hot loops pays more when tracking is off than when it is on. Possible fix (unverified): cache the resolved on_inactive_annotate value, invalidated when configuration changes.
