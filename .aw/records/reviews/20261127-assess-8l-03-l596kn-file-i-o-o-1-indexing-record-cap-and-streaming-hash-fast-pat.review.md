# Review findings: ipd l596kn

- Subject-Id: l596kn
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-8l-03-l596kn-file-i-o-o-1-indexing-record-cap-and-streaming-hash-fast-pat.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`). Expanded acronyms (`I/O`, `SHA-256`, `JSON`, `TOML`, `KiB`) on first use, anchored symbols with `path::Symbol`, and updated the Mermaid `flowchart LR` diagram to include `src/pubrun/tracker.py::Run.to_manifest_dict`, `src/pubrun/resources/default.toml`, `schemas/manifest.schema.json`, `docs/configuration.md`, `docs/manifest.md`, and `tests/test_file_io_provenance.py`.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `- Scope-Paths:`, `- Item-Dependencies:`, `E-02` | Omitted `src/pubrun/tracker.py` (so `Run.to_manifest_dict()` silently dropped `data_files["records_truncated"]`) and set `- Item-Dependencies: none` | Added `src/pubrun/tracker.py` to `- Scope-Paths:`, set `- Item-Dependencies: executed:76z7ww` to serialize `tracker.py`, and specified emitting `records_truncated` when `> 0` in `Run.to_manifest_dict()` | Fix blocker preventing `records_truncated` from reaching `manifest.json` (`PR-001`) |
| `E-01` (index invariants and `_pending_file_registrations`) | Omitted index invalidation/re-insertion on in-place pending upgrades and finalization, omitted list-identity mutation checks, and omitted `O(1)` removal while keeping `run._pending_file_registrations` as a `list` | Specified re-indexing in `_upgrade_pending_or_append()` and `finalize_pending_registrations()`, list identity + length staleness check, `O(1)` swap-pop on `list` `_pending_file_registrations`, and emitting `validate_hash_algorithm` warning outside `_warn_lock` | Prevent stale index duplicates and preserve `tests/test_file_registration.py:371,383` (`PR-002`) |
| `E-02` (`max_tracked_files` semantics) | Left `resolve_file_io_config`, return value on truncation (`None`), event suppression, and `max_tracked_files == 0` hashing bypass unspecified | Specified `resolve_file_io_config` validation (`default=5000`, `0` disables recording), returning `None` and skipping `_emit_file_event` on truncation, and bypassing hashing when `max_tracked_files == 0` | Make truncation contract explicit and avoid wasted hashing or phantom returned dicts (`PR-003`) |
| `E-03`, `E-04`, `V-01`, `V-03` (`ProvenanceFileProxy` fast path and timing checks) | `write()` called `hasher.update(data)` directly (skipping `self._stream_bytes += n` and cap checks); 64 KiB cap interval delayed small `max_hash_bytes` aborts; hardcoded ms thresholds risked flaky `pytest` failures | Routed direct `bytes`/`bytearray` writes (and `readinto`/`readinto1`) through `_update_stream_hash(data)`, added lock-free `max_hash_bytes` check + 64 KiB interval for capped streams, and moved ms timing checks to standalone CLI validation while keeping behavioral assertions in `pytest` | Prevent zeroed `bytes_hashed`, broken small caps, and flaky CI tests (`PR-004`) |
| `- Scope-Paths:`, `## Spec / documentation sync`, `## Required tests / validation`, `## Approval and execution gate`, Mermaid diagram | Omitted `docs/configuration.md` and `docs/manifest.md`, omitted `test_explicit_api.py` and `test_tracker.py`, omitted five-clause execution gate, left acronyms unexpanded, and omitted new files in Mermaid diagram | Added `docs/configuration.md` and `docs/manifest.md` (with zero-dash check), expanded test command, added five-clause execution contract, expanded acronyms, and updated Mermaid diagram | Keep published config/manifest docs honest and satisfy execution-contract and technical-writing rules (`PR-005`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-8l`, `- Order: 3`, `- Scope-Paths:` (expanded from 4 to 7 files: `file_io.py`, `tracker.py`, `default.toml`, `manifest.schema.json`, `test_file_io_provenance.py`, `docs/configuration.md`, `docs/manifest.md`), 4 E-items in 2 task groups.

1. Yes: adds a new configuration key (`[capture.file_io].max_tracked_files`), extends the published v1.0 manifest JSON Schema (`data_files.records_truncated`), and updates `Run.to_manifest_dict()`, `docs/configuration.md`, and `docs/manifest.md`.
2. No: does not touch private-data leak sanitizers, commit helpers, worktree isolation, merge locks, or host sandbox profiles.
3. Yes: spans core file-provenance engine, tracker manifest serialization, schema, config defaults, docs, and tests across 2 task groups and 3 rollup findings.
4. Yes: `- Scope-Paths:` lists all 7 modified files explicitly.
5. Yes: bugs in `O(1)` index maintenance, truncation accounting, or streaming-hash fast paths can silently corrupt SHA-256 provenance digests, zero out `bytes_hashed`, drop records, or fail schema validation.

AW-TIER: complex

### Step R1

- Checked: every file, symbol, schema, doc, and test citation against the repository: `src/pubrun/capture/file_io.py` (`_warned_invalid_algorithms`, `validate_hash_algorithm`, `validate_non_negative_int`, `resolve_file_io_config`, `FileIoBudgetTracker`, `_record_dedup_key`, `append_or_deduplicate_record`, `_find_unchanged_completed_record`, `_upgrade_pending_or_append`, `register_file_provenance`, `finalize_pending_registrations`, `ProvenanceFileProxy`), `src/pubrun/tracker.py` (`Run.__init__:268-271`, `Run.to_manifest_dict:1533-1555`), `src/pubrun/resources/default.toml:351-391`, `schemas/manifest.schema.json:191-270`, `docs/configuration.md:258-279`, `docs/manifest.md:454-512`, `tests/test_file_io_provenance.py`, `tests/test_file_registration.py:371,383,894`, and `tests/test_manifest_schema.py`.
- Verified: reading `src/pubrun/tracker.py:1533-1555` caught a blocker omission (`Run.to_manifest_dict()` drops any key on `self.data_files` other than `inputs`/`outputs`/`mixed`/`hashing_summary`), and reading `src/pubrun/capture/file_io.py` caught in-place mutation staleness in `_upgrade_pending_or_append`/`finalize_pending_registrations` and `self._stream_bytes` omission in the `write()` fast path.

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-04` <-> `V-01..V-04`), `- Scope-Paths:` completeness (all 7 files), `- Item-Dependencies: executed:76z7ww`, runtime-demonstration reachability and concrete named units in every `V-*` item, non-tautological validation evidence, and the five-clause execution contract.
- Verified: every `V-*` item names its concrete code units and demands reproducible `pytest`, `mypy`, timing, and dash-check outputs reachable via `E-01..E-04`; `PR-001` makes `V-02`'s `manifest["data_files"]["records_truncated"]` assertion actually reachable through `src/pubrun/tracker.py::Run.to_manifest_dict`.

### Step R3

- Checked: trust-boundary input handling and resource bounds across `resolve_file_io_config` (`validate_non_negative_int` rejecting negative/`bool`/non-finite values for `max_tracked_files`), `data_files` / `_pending_file_registrations` memory cap, `_warned_invalid_algorithms` 256-entry cap, and `schemas/manifest.schema.json` `"additionalProperties": false` integrity.
- Verified: bounding `data_files`, `_pending_file_registrations`, and `_warned_invalid_algorithms` closes unbounded-memory DoS surfaces on high-I/O scripts without altering host I/O behavior or suppressing host exceptions.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified: `PR-001` wires `records_truncated` into `Run.to_manifest_dict()`; `PR-002` keeps all three `O(1)` indexes consistent across in-place pending upgrades, finalization, and test mutations while preserving `list` `_pending_file_registrations`; `PR-003` nails down `max_tracked_files = 0` and truncation return/event semantics; `PR-004` preserves `bytes_hashed` accounting and small-cap aborts in `ProvenanceFileProxy` while moving ms timing out of flaky `pytest` assertions; `PR-005` adds `docs/configuration.md` and `docs/manifest.md` sync and the five-clause execution contract.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `Run.to_manifest_dict()` dropping `records_truncated` (`PR-001`) and `write()` fast path zeroing `self._stream_bytes` (`PR-004`).
  2. Testing and regression: preserved `list` type on `_pending_file_registrations` (`tests/test_file_registration.py:371,383`), avoided flaky ms assertions inside `pytest` (`PR-004`), and added `test_explicit_api.py` and `test_tracker.py` to validation (`PR-005`).
  3. UI / UX: contrasted `max_tracked_files = 0` (disable recording) clearly against `max_hash_bytes = 0` (unlimited) in `default.toml` and `docs/configuration.md` (`PR-003`, `PR-005`).
  4. Architect: verified clean serialization edge `executed:76z7ww` for shared `src/pubrun/tracker.py` with zero cycles in Set `assess-8l` (`PR-001`).
  5. Software engineer: caught stale index keys after in-place `existing_rec.clear(); existing_rec.update(record)` in `_upgrade_pending_or_append` and `finalize_pending_registrations`, and moved `logger.warning` outside `_warn_lock` (`PR-002`).
  6. Power user: verified `max_tracked_files = 0` skips hashing overhead and `max_tracked_files > 0` still deduplicates repeated reads of already-tracked files (`PR-003`).
  7. Novice: updated `docs/configuration.md` and `docs/manifest.md` so both the new config key and manifest field are documented accurately (`PR-005`).
  8. Stakeholder: confirmed full v1.0 manifest schema backward compatibility (`records_truncated` optional and omitted when `0`).

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-04` (4 E-items, 2 task groups, 7 Scope-Paths, Order 03 of 10-child Set `assess-8l`).
- Confirmed: each E-item addresses one coherent unit (`E-01` O(1) indexing + warning cap, `E-02` `max_tracked_files` cap + schema/tracker/docs, `E-03` streaming-hash fast path, `E-04` regression tests and validation). No splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-8l`: orchestrator `k80suw` (Order 00), `76z7ww` (Order 02), `2ge0ea` (Order 08), and `6y55x4` (Order 10).
- Verified: adding `- Item-Dependencies: executed:76z7ww` strictly serializes `src/pubrun/tracker.py` (`76z7ww` -> `l596kn`) with zero cycles (`1o1cua -> 76z7ww -> l596kn -> 2ge0ea -> 6y55x4`); `src/pubrun/resources/default.toml` remains strictly serialized (`l596kn -> 2ge0ea`, since `2ge0ea` already declares `executed:l596kn`); zero other siblings touch `schemas/manifest.schema.json`, `docs/configuration.md`, or `docs/manifest.md`. Note for `k80suw` review: `k80suw`'s `E-03` row and child table currently show `l596kn` depending on `none` and should be updated to `02` (`E-02`) when `k80suw` is reviewed (the runner enforces `l596kn`'s own front-matter `- Item-Dependencies: executed:76z7ww` directly).

### Step S5

- Checked: `## Open questions` contains `None.`. All five findings (`PR-001` through `PR-005`) had `Low` overall Remediation Risk, were settled by repository code, schema, and test evidence, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | UNDER-SCOPE | `r2-executability.md` / `r4-engineering.md` A / `r7-cross-plan.md` | `.aw/records/plans/pending/20261127-assess-8l-03-l596kn-file-i-o-o-1-indexing-record-cap-and-streaming-hash-fast-pat.ipd.md:61-64,138` vs `src/pubrun/tracker.py::Run.to_manifest_dict:1533-1555` | `Run.to_manifest_dict()` builds `data_files_snapshot` copying only `"inputs"`, `"outputs"`, `"mixed"`, and `"hashing_summary"`, silently dropping `data_files["records_truncated"]`. Without updating `src/pubrun/tracker.py` (which was missing from `- Scope-Paths:`), `V-02`'s manifest truncation assertion is unreachable. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `src/pubrun/tracker.py` to `- Scope-Paths:`, set `- Item-Dependencies: executed:76z7ww` to serialize `tracker.py` after Child 02 with zero cycles, and updated `E-02`/`V-02` to emit `data_files["records_truncated"]` in `Run.to_manifest_dict()` under `_data_files_lock` whenever `> 0` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r4-engineering.md` A, D (Correctness and anti-regression) | `src/pubrun/capture/file_io.py::_upgrade_pending_or_append:1202-1220`, `register_file_provenance:1806-1821`, `finalize_pending_registrations:1875-1933`, `validate_hash_algorithm:90-99`, `tests/test_file_registration.py:371,383` | `E-01` did not evict stale pending keys or insert upgraded keys into `_data_files_dedup_index`/`_completed_hash_index` when `_upgrade_pending_or_append()` or `finalize_pending_registrations()` mutates `existing_rec` in place, did not specify clearing `_pending_file_index` on finalization or preserving `list` `_pending_file_registrations` with `O(1)` swap-pop, and checked only length (not list identity) on direct test mutations. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-01` and `V-01` to specify full index synchronization on every append, in-place upgrade, and finalization, `list` identity + length staleness rebuilds, `O(1)` swap-pop preserving `list` `_pending_file_registrations`, and moving `logger.warning` outside `_warn_lock` in `validate_hash_algorithm` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` A, F (Cap semantics and UX clarity) | `src/pubrun/capture/file_io.py::resolve_file_io_config:137-165`, `register_file_provenance:1714-1856`, `src/pubrun/resources/default.toml:376-391` | `E-02` omitted `resolve_file_io_config` parsing/validation for `max_tracked_files`, left the return value and `_emit_file_event` behavior on truncated registrations unspecified, did not short-circuit disk/stream hashing when `max_tracked_files == 0`, and did not contrast `max_tracked_files = 0` (store 0) against adjacent `max_hash_bytes = 0` (unlimited). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02` and `V-02` to parse `max_tracked_files` via `validate_non_negative_int(..., 5000)`, return `None` and skip `_emit_file_event` on truncation, short-circuit hashing when `max_tracked_files == 0`, and explicitly contrast `0` semantics in `default.toml` and `docs/configuration.md` (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r4-engineering.md` A, E (Streaming hash accounting and test stability) | `src/pubrun/capture/file_io.py::ProvenanceFileProxy._update_stream_hash:2042-2061`, `write:2177-2195`, `_populate_hash_fields:2432-2455`, `tests/test_file_io_provenance.py:906-929` | Calling `hasher.update(data)` directly from `ProvenanceFileProxy.write()` bypasses `self._stream_bytes += n` (zeroing `bytes_hashed`/`total_bytes_hashed`) and bypasses cap checks when caps are active; checking caps only every 64 KiB delays small `max_hash_bytes` aborts; hardcoded ms thresholds inside `pytest` are CI-flaky. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Routed direct `bytes`/`bytearray` `write()` (and `readinto`/`readinto1`) through `_update_stream_hash(data)`, added lock-free `max_hash_bytes` check + 64 KiB interval for capped streams, and moved wall-clock ms targets to a standalone CLI timing check while keeping behavioral assertions in `pytest` (recommendation strength: `very strong`). |
| PR-005 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `r4-engineering.md` E, F / `p-proofread.md` / `s7-finalize.md` | `docs/configuration.md:258-279`, `docs/manifest.md:454-467`, `.aw/records/plans/pending/20261127-assess-8l-03-l596kn-file-i-o-o-1-indexing-record-cap-and-streaming-hash-fast-pat.ipd.md:30-40,115-123,152-154` | `## Spec / documentation sync` omitted `docs/configuration.md` (`[capture.file_io]` table) and `docs/manifest.md` (`data_files` table); `## Required tests / validation` omitted `tests/test_explicit_api.py` and `tests/test_tracker.py`; `## Approval and execution gate` omitted the five-clause execution contract; acronyms were unexpanded and the Mermaid diagram omitted `tracker.py`, `default.toml`, `manifest.schema.json`, docs, and tests. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `docs/configuration.md` and `docs/manifest.md` to `- Scope-Paths:` and `E-02` (with zero-dash check), expanded `## Required tests / validation`, wrote the five-clause execution contract, expanded acronyms, and updated the Mermaid diagram (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `l596kn` | `complex` | `standard` | Adds a new config key (`[capture.file_io].max_tracked_files`), extends the published v1.0 manifest JSON Schema (`data_files.records_truncated`), and modifies `tracker.py` alongside `file_io.py`; answers Yes to tier questions 1, 3, and 5 in `steps/t-tier.md`. | yes |
| D-2 | How to serialize `data_files.records_truncated` without colliding with Child 02 (`76z7ww`) on `src/pubrun/tracker.py` | Add `src/pubrun/tracker.py` to `l596kn`'s `- Scope-Paths:` and add `- Item-Dependencies: executed:76z7ww`; emit `records_truncated` in `Run.to_manifest_dict()` only when `> 0` | Store `records_truncated` inside `hashing_summary` (wrong for default `level="stat"` runs where `_file_io_budget` is `None` and contradicts `schemas/manifest.schema.json` `data_files.records_truncated`), or defer to `76z7ww` (leaves `l596kn` `V-02` unsatisfiable) | `src/pubrun/tracker.py:1533-1555`, `schemas/manifest.schema.json:191-269`, and Set `assess-8l` DAG (`76z7ww` does not depend on `l596kn`). | yes |
| D-3 | How to achieve `O(1)` removal on `_pending_file_registrations` while keeping existing test assertions green | Keep `run._pending_file_registrations` as a `list` and index it with `_pending_file_index: Dict[Tuple, int]` using `O(1)` swap-pop | Replace `_pending_file_registrations` with a `dict` (breaks `assert run._pending_file_registrations == []` in `tests/test_file_registration.py:383`) or use `list.pop(idx)` (`O(N)`) | `tests/test_file_registration.py:371,383,894` and `src/pubrun/capture/file_io.py:1194-1203`. | yes |

### Step S6

- Checked: Round 1 added `src/pubrun/tracker.py`, `docs/configuration.md`, and `docs/manifest.md` to `- Scope-Paths:` and changed `- Item-Dependencies:` from `none` to `executed:76z7ww`. Per `steps/s6-rereview.md` rule 1, a second pass (Round 2) is required to verify the revised Scope-Paths, dependencies, cross-references, and lint conformance.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised `.aw/records/plans/pending/20261127-assess-8l-03-l596kn-file-i-o-o-1-indexing-record-cap-and-streaming-hash-fast-pat.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. Confirmed all acronyms are expanded on first use, all `E-01..E-04` and `V-01..V-04` items name exact `path::Symbol` units with observable criteria, and the Mermaid `flowchart LR` matches all seven `- Scope-Paths:` entries.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R2

- Checked: verified `- Highest E allocated: 04` matches `E-01..E-04` and `V-01..V-04` (strict 1:1 bijection); verified `- Scope-Paths:` lists all 7 modified files (`src/pubrun/capture/file_io.py`, `src/pubrun/tracker.py`, `src/pubrun/resources/default.toml`, `schemas/manifest.schema.json`, `tests/test_file_io_provenance.py`, `docs/configuration.md`, `docs/manifest.md`); verified `- Item-Dependencies: executed:76z7ww` is acyclic; verified no superseded wording remains; verified the five-clause execution gate states conditional runner/executor finalize ownership with no forbidden "STOP and report" scope-fence wording.

### Step R7

- Checked: verified `76z7ww -> l596kn -> 2ge0ea -> 6y55x4` serializes both `src/pubrun/tracker.py` and `src/pubrun/resources/default.toml` cleanly across Set `assess-8l`, and zero other pending plans touch `schemas/manifest.schema.json`, `docs/configuration.md`, or `docs/manifest.md`.

### Step S5

- Checked: `## Open questions` contains `None.`; all five findings (`PR-001` through `PR-005`) are `FIXED`; zero blocking questions or irreversible decisions remain; lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | UNDER-SCOPE | `r2-executability.md` / `r4-engineering.md` A / `r7-cross-plan.md` | `src/pubrun/tracker.py::Run.to_manifest_dict:1533-1555` | `Run.to_manifest_dict()` dropped `data_files["records_truncated"]` and `src/pubrun/tracker.py` was missing from `- Scope-Paths:`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `src/pubrun/tracker.py` is in `- Scope-Paths:`, `- Item-Dependencies: executed:76z7ww` is set, and `E-02`/`V-02` propagate `records_truncated` when `> 0` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r4-engineering.md` A, D | `src/pubrun/capture/file_io.py` (`_upgrade_pending_or_append`, `finalize_pending_registrations`, `validate_hash_algorithm`), `tests/test_file_registration.py:371,383` | Stale index keys on in-place pending upgrades/finalization, missing list-identity rebuild trigger, and `list` preservation on `_pending_file_registrations`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-01` and `V-01` specify full re-indexing, list-identity staleness checks, `O(1)` swap-pop on `list` `_pending_file_registrations`, and lock-free warning emission (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` A, F | `src/pubrun/capture/file_io.py::resolve_file_io_config`, `register_file_provenance`, `src/pubrun/resources/default.toml` | Unspecified `resolve_file_io_config` parsing, truncation return/event semantics, `max_tracked_files == 0` hashing bypass, and `0`-semantics contrast in docs. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-02` and `V-02` specify all `max_tracked_files` validation, return, event, and doc-contrast semantics (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r4-engineering.md` A, E | `src/pubrun/capture/file_io.py::ProvenanceFileProxy` (`_update_stream_hash`, `write`, `_populate_hash_fields`) | Direct `hasher.update(data)` in `write()` skipped `self._stream_bytes` and cap checks; 64 KiB cap interval delayed small caps; hardcoded ms assertions in `pytest` were flaky. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-03`, `E-04`, and `V-03` route direct writes/reads through `_update_stream_hash`, add lock-free `max_hash_bytes` check, and separate standalone timing checks from behavioral `pytest` assertions (recommendation strength: `very strong`). |
| PR-005 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `r4-engineering.md` E, F / `p-proofread.md` / `s7-finalize.md` | `docs/configuration.md:258-279`, `docs/manifest.md:454-467`, `l596kn` | Missing `docs/configuration.md` and `docs/manifest.md` sync, missing test suites, incomplete execution gate, unexpanded acronyms, and incomplete Mermaid diagram. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: docs, tests, five-clause gate, acronyms, and Mermaid diagram are all reconciled (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `l596kn` | `complex` | `standard` | Adds a new config key (`[capture.file_io].max_tracked_files`), extends the published v1.0 manifest JSON Schema (`data_files.records_truncated`), and modifies `tracker.py` alongside `file_io.py`; answers Yes to tier questions 1, 3, and 5 in `steps/t-tier.md`. | yes |
| D-2 | How to serialize `data_files.records_truncated` without colliding with Child 02 (`76z7ww`) on `src/pubrun/tracker.py` | Add `src/pubrun/tracker.py` to `l596kn`'s `- Scope-Paths:` and add `- Item-Dependencies: executed:76z7ww`; emit `records_truncated` in `Run.to_manifest_dict()` only when `> 0` | Store `records_truncated` inside `hashing_summary` or defer to `76z7ww` | `src/pubrun/tracker.py:1533-1555`, `schemas/manifest.schema.json:191-269`, and Set `assess-8l` DAG (`76z7ww` does not depend on `l596kn`). | yes |
| D-3 | How to achieve `O(1)` removal on `_pending_file_registrations` while keeping existing test assertions green | Keep `run._pending_file_registrations` as a `list` and index it with `_pending_file_index: Dict[Tuple, int]` using `O(1)` swap-pop | Replace `_pending_file_registrations` with a `dict` or use `list.pop(idx)` (`O(N)`) | `tests/test_file_registration.py:371,383,894` and `src/pubrun/capture/file_io.py:1194-1203`. | yes |

### Step S6

- Checked: Round 2 introduced no further edits, no new findings, and no structural changes. All revisions from Round 1 are internally consistent and reconciled across all sections. Ready for Step S7 finalization (`APPROVE WITH REVISIONS APPLIED`, `go-pending-approval`).

AW-REVIEW: DONE
