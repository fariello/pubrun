# Decisions and assumptions - assess-performance 20260704-143134

## Concern and scope

- **Concern assessed:** Runtime and resource performance (speed, throughput,
  latency, efficiency).
- **Scope:** Entire `src/pubrun/` source tree — all capture engines, core API,
  event system, writer, status CLI, and import machinery.
- **Narrowing:** None specified by user; assessed the whole project.

## Project conventions discovered

- No `GUIDING_PRINCIPLES.md` exists; used universal fallback principles.
- Pending-plans directory: `plans/pending/` (created; `plans/` already existed).
- No explicit contributor contract beyond `AGENTS.md`.
- Stack: Pure Python 3.8+, single runtime dep (`tomli` for <3.11).
- Import-time auto-start is the default mode — therefore import-time cost IS
  user-facing latency for every script that does `import pubrun`.

## Key decisions

1. **Verdict: "adequate"** — pubrun is not broken for performance, but has
   clear optimization opportunities that matter for its target audience (ML/HPC
   scripts where import latency and per-line overhead are noticeable).

2. **Import-time is the critical hot path.** When `auto_start = true` (default),
   `import pubrun` triggers the full boot sequence including all capture engines.
   The combined cost of packages + hardware + git + invocation hashing can exceed
   500ms. This is the highest-priority area.

3. **Console tee and event stream are secondary hot paths.** They execute per
   print-line and per-event respectively. The overhead is small per-call but
   multiplied by potentially millions of calls in ML training loops.

4. **pubrun status scaling is a tertiary concern.** It only matters when users
   accumulate many runs (500+). Most users will clean regularly.

5. **Proposed changing packages default from `full-environment` to
   `imported-only`.** This is technically a behavior change but is the right
   default: most users care about their script's actual dependencies, not every
   unrelated package in the venv. The full list remains available via config.

6. **Event buffering trades durability for throughput.** Currently every event
   is flushed immediately (zero data loss on crash). Proposed buffering means
   up to 100 events or 1s of data could be lost on a hard crash. This is
   acceptable for resource_sample events but may not be for annotations/phases.
   Recommendation: buffer only non-critical events; keep immediate flush for
   phase_start/phase_end/annotation.

7. **Runs index (PERF-09) is conditional.** Only implement if benchmarks show
   >1s scan time for realistic run counts. Adds complexity for potentially
   marginal benefit.

## What was intentionally NOT proposed

- **Async I/O / asyncio rewrite:** Remediation Risk High on Complexity.
  pubrun's synchronous design is intentional for simplicity and Python 3.8
  compatibility. Converting to async would be a rewrite.

- **C extension for hashing/tee:** Remediation Risk High on Complexity.
  Would break the zero-dependency promise and complicate packaging.

- **Removing ProvenanceFileProxy entirely:** It's a user-facing feature
  (automatic dataset provenance). The fix is to make it cheaper, not remove it.

- **Full class hierarchy split for ProvenanceFileProxy:** Remediation Risk
  Medium-High on Complexity (doubles class surface for marginal gain).

## Open questions for the user

1. Is it acceptable for the crash-safety startup manifest to lack hardware data
   if we defer hardware detection to background?
2. Should event buffering be configurable, or is the proposed 100-event / 1s
   default sufficient?
3. What is the typical run count for real users? (Determines priority of PERF-09.)
4. Is changing `get_packages()` default acceptable in a minor version?
