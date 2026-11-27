# Review findings: ipd p4ueaj

- Subject-Id: p4ueaj
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 1` info `IPD-Z603`, `0` errors/warnings). Expanded acronyms (`PEP`, `CSV`, `I/O`, `ENOENT`, `CI`) on first use, anchored symbols with `path::Symbol`, replaced ambiguous three-way fallback version wording with an explicit deterministic chain, updated the Mermaid `flowchart LR` diagram to include `src/pubrun/core.py`, `src/pubrun/tracker.py`, `src/pubrun/capture/_markers.py`, and the real test files (`tests/test_import_modes.py`, `tests/test_commit_identity.py`, `tests/test_package_resolution.py`), and added the five-clause execution contract.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `- Scope:`, `- Scope-Paths:`, `- Item-Dependencies:`, `E-04` | Omitted `src/pubrun/core.py` and `src/pubrun/tracker.py` from `- Scope-Paths:` (despite targeting `tracker`/capture-engine deferral) and declared `- Item-Dependencies: executed:1o1cua, executed:76z7ww` | Added `src/pubrun/core.py` and `src/pubrun/tracker.py` to `- Scope-Paths:`, added `executed:l596kn` to `- Item-Dependencies:` to serialize `tracker.py`, and specified concrete monkeypatch-preserving lazy loading in `core.py` and `tracker.py` | Make `E-04` cold-start reduction reachable and serialize shared `tracker.py` cleanly across Set `assess-8l` (`PR-001`, `PR-005`) |
| `- Scope:`, `- Scope-Paths:`, `E-05`, `## Required tests / validation`, `V-05` | Referenced non-existent `tests/test_package_capture.py` and ran only 4 test files | Replaced `tests/test_package_capture.py` with existing `tests/test_commit_identity.py` and `tests/test_package_resolution.py` and expanded validation to all 12 affected test suites | Eliminate non-existent test file path and verify all affected suites (`PR-002`) |
| `E-01`, `V-01` | Did not update `src/pubrun/__init__.py::_resolve_commit` (which referenced bare `__version__`), left 3-way ambiguous fallback version choice, missed second stale `"1.0.0"` in `src/pubrun/tracker.py:1530`, missed kill/reap before `Popen.__exit__` on non-`TimeoutExpired` exceptions, and missed stale `nopatch` comment in `src/pubrun/__init__.__doc__:33` | Specified `_get_version()` in `_resolve_commit`, deterministic fallback chain (`pyproject.toml` -> `_build_meta.json` -> `"0.0.0+unknown"`), `"0.0.0+unknown"` in `tracker.py:1530`, kill/reap on `TimeoutExpired` and any `BaseException` before `Popen.__exit__`, and updated `__init__.__doc__` `nopatch` line | Prevent `NameError` in `_resolve_commit`, eliminate fallback ambiguity/staleness, prevent `Popen.__exit__` hang, and keep docstrings consistent (`PR-003`, `PR-005`) |
| `E-02`, `V-02` | Assumed `meta.get("Version")` always holds a value (breaking dict mocks like `tests/test_reproducibility_preflight.py::_FakeDist`), left lazy `editable`/`requires` and `.egg-info` handling vague, missed `PurePosixPath` `./`/`/`/trailing-`/` edge cases in fast-path `RECORD` parsing, missed symlinked `.dist-info` guard in parent-dir `realpath` cache, omitted `_markers` deferral, and demanded an uncalibrated `>=55%` latency delta | Added dict-mock `Version` fallback, in-memory `Requires-Dist` + `.dist-info` zero-probe + lazy `.egg-info` fallback, lazy `_DistInfo.editable` + short-circuited shim check, `PurePosixPath` edge-case fallback, `os.path.islink` guard on parent `realpath` cache, deferred `_markers` import, and deterministic read-count assertions plus `package_capture_bench.py` output | Prevent regressions in `test_reproducibility_preflight.py`, symlinked `.dist-info`, and `RECORD` parsing, and make `V-02` deterministic (`PR-004`) |
| `E-03`, `## Required tests / validation`, `V-03` | Did not explicitly remove eager `from pubrun import __version__` from mode submodules, omitted `__dir__`, Python 3.8 typing constraints, and `__commit__` cache-reset preservation, and tested only `pubrun.noauto.start()`/`stop()` in downstream `mypy --strict` | Specified removing eager `__version__` import, adding `__dir__` and Python 3.8-compatible `TYPE_CHECKING` stubs, forwarding without submodule-local `__commit__` caching, and checking `__version__`/`__commit__` across all six mode submodules in downstream `mypy --strict --no-implicit-reexport` | Ensure mode submodules truly avoid eager `importlib.metadata` and satisfy PEP 561 on Python 3.8-3.14 (`PR-003`, `PR-005`) |
| `## Goal`, Mermaid diagram, `## Approval and execution gate` | Unexpanded acronyms, incomplete 4-node Mermaid diagram, and 2-line approval gate lacking the five-clause execution contract | Expanded acronyms on first use, aligned Mermaid diagram with all modified modules/tests, and added the complete five-clause execution contract | Comply with technical writing standard and execution-gate contract (`PR-006`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-8l`, `- Order: 4`, `- Scope-Paths:` (expanded from 10 to 13 files: `__init__.py`, `core.py`, `tracker.py`, `capture/packages.py`, six mode submodules, and three test files), 5 E-items in 4 task groups.

1. Yes: changes public package exports (`__all__`, `__dir__`, PEP 562 lazy `__version__` and `__commit__`, PEP 561 typing contract) across `pubrun` and all six import-mode submodules (`auto`, `full`, `noauto`, `nopatch`, `noconsole`, `minimal`), and changes fallback `__version__` resolution.
2. No: does not touch leak sanitizers, commit helpers, worktree isolation, merge locks, or host sandbox profiles (only fixes subprocess pipe cleanup in `src/pubrun/__init__.py::_resolve_checkout_commit`).
3. Yes: spans 5 execution items across 4 task groups touching package bootstrap (`__init__.py`, 6 mode submodules), `core.py`, `tracker.py`, `capture/packages.py`, and 3 test suites, with cross-plan serialization across Set `assess-8l`.
4. Yes: `- Scope-Paths:` explicitly lists all 13 modified files after Round 1 revision.
5. Yes: mistakes in lazy `__version__`/`Run`/capture-engine imports or `packages.py` indexing can break `pubrun.__commit__` (`NameError`), break downstream `mypy --strict`, break `test_report_subpackage_integrity.py`, break monkeypatch seams in `tests/`, or drop package versions/dependencies in manifests.

AW-TIER: complex

### Step R1

- Checked: every file, symbol, benchmark, doc, and test citation against the repository: `pyproject.toml`, `hatch_build.py`, `src/pubrun/__init__.py` (lines 1-397), `src/pubrun/_modes.py` (lines 1-90), `src/pubrun/_bootstrap.py` (lines 1-335), `src/pubrun/{auto,full,noauto,nopatch,noconsole,minimal}.py`, `src/pubrun/core.py` (lines 1-800), `src/pubrun/tracker.py` (lines 1-250, 1510-1570), `src/pubrun/capture/packages.py` (lines 1-1909), `src/pubrun/report/__init__.py`, `tests/test_import_modes.py`, `tests/test_full_mode.py`, `tests/test_report_subpackage_integrity.py`, `tests/test_commit_identity.py`, `tests/test_package_resolution.py`, `tests/test_package_transitive.py`, `tests/test_reproducibility_preflight.py:209-315`, `tests/test_api.py:310-450`, `tests/test_edge_cases.py:100-160`, `tests/test_new_features.py:45-95`, `tests/conftest.py`, `benchmarks/package_capture_bench.py:1-250`, and `docs/{api,functional_spec,cli}.md` + `README.md`.
- Ran targeted baseline checks: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -X importtime -c "import pubrun.minimal"` (confirmed 182.4 ms total: 46 ms `importlib.metadata`, 101.9 ms `pubrun.tracker` + 14 capture modules including 31.9 ms `packages.py` / 12.3 ms `_markers.py`) and `MYPYPATH=src python3 -m mypy --config-file /dev/null --strict --follow-imports=silent -c "..."` (confirmed current `[attr-defined]` errors on `pubrun.noauto`).
- Verified: caught non-existent `tests/test_package_capture.py` (`PR-002`), missing `src/pubrun/core.py` and `src/pubrun/tracker.py` in `- Scope-Paths:` (`PR-001`), `src/pubrun/__init__.py:257` bare `__version__` `NameError` risk + eager `from pubrun import __version__` in all 6 mode submodules + second stale `"1.0.0"` in `src/pubrun/tracker.py:1530` (`PR-003`), and `tests/test_reproducibility_preflight.py::_FakeDist:231-235` dict metadata lacking `"Version"` (`PR-004`).

### Step R2

- Checked: E/V 1:1 bijection (`E-01..E-05` <-> `V-01..V-05`), `- Scope-Paths:` completeness (all 13 files), `- Item-Dependencies: executed:1o1cua, executed:76z7ww, executed:l596kn`, runtime-demonstration reachability and concrete named units in every `V-*` item, non-tautological validation evidence, and the five-clause execution gate contract.
- Verified: adding `src/pubrun/core.py` and `src/pubrun/tracker.py` makes `V-04`'s >70% cold-start reduction actually reachable; replacing non-existent `tests/test_package_capture.py` with `tests/test_commit_identity.py` and `tests/test_package_resolution.py` makes `V-01`, `V-02`, and `V-05` executable; replacing the uncalibrated `>=55%` benchmark bar with deterministic read-count/import assertions plus `package_capture_bench.py` output prevents flaky validation failures; and the five-clause execution contract is now present with conditional runner/executor finalize ownership and zero forbidden "STOP and report" wording.

### Step R3

- Checked: trust-boundary input handling, subprocess safety, and privacy in `src/pubrun/__init__.py::_resolve_checkout_commit` (stripped `GIT_*` env, verified toplevel ownership, bounded timeout, deterministic kill/reap and pipe close on timeout and `BaseException`), `src/pubrun/__init__.py::_get_version` (only reads `pyproject.toml` inside `_is_verified_source_checkout`), and `src/pubrun/capture/packages.py::_is_editable_dist` (never exposes `direct_url.json` URLs, only boolean editable status).
- Verified: wrapping `_sp.Popen` with `with` plus kill/reap on both `TimeoutExpired` and arbitrary `BaseException` closes the pipe leak without weakening checkout ownership checks or `SubprocessSpy.disable_spy()` isolation.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing and conceptual density, and `## Spec / documentation sync`.
- Verified:
  - `PR-001` adds `src/pubrun/core.py` and `src/pubrun/tracker.py` to `- Scope-Paths:` and `executed:l596kn` to `- Item-Dependencies:` so `E-04` can actually defer the 102 ms `tracker.py`/capture-engine import chain.
  - `PR-002` fixes the non-existent `tests/test_package_capture.py` path and expands validation to all 12 affected suites.
  - `PR-003` prevents `NameError` in `src/pubrun/__init__.py::_resolve_commit:257`, removes eager `from pubrun import __version__` from all 6 mode submodules, specifies one deterministic fallback version chain plus `tracker.py:1530`, and prevents `Popen.__exit__` hangs on non-`TimeoutExpired` exceptions.
  - `PR-004` preserves `_FakeDist` (`test_reproducibility_preflight.py`), `.egg-info` `requires.txt`, symlinked `.dist-info` deduplication, and `PurePosixPath` edge cases in `RECORD` parsing, while also deferring `pubrun.capture._markers`.
  - `PR-005` specifies exact monkeypatch-preserving lazy seams in `core.py` and `tracker.py`, adds `__dir__` and Python 3.8 typing annotations on mode submodules, strengthens the downstream `mypy --strict` check to all 6 mode modules, and aligns `src/pubrun/__init__.__doc__:33` with `nopatch.py` and `_modes.py`.
  - `PR-006` completes the execution gate, expands acronyms, and aligns the Mermaid diagram.
  - `## Spec / documentation sync` verified truthful against `docs/api.md`, `docs/functional_spec.md`, and `README.md`.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `tests/test_package_capture.py` non-existence (`PR-002`), `_resolve_commit` bare `__version__` `NameError` (`PR-003`), and `_FakeDist` dict-metadata regression (`PR-004`).
  2. Testing and regression: preserved every `monkeypatch.setattr` seam on `pubrun.core` and `pubrun.tracker`, preserved `test_report_subpackage_integrity.py`, replaced uncalibrated wall-clock test bars with deterministic read-count and `sys.modules` assertions, and expanded validation to 12 suites (`PR-002`, `PR-004`, `PR-005`).
  3. UI / UX: aligned `src/pubrun/__init__.__doc__` and `src/pubrun/nopatch.py` docstrings on signal hooks and `[console].capture_mode = "off"` (`PR-005`).
  4. Architect: traced the full 182 ms `-X importtime` chain into `core.py` -> `tracker.py` -> 14 capture modules -> `_markers.py`, added the missing Scope-Paths, and serialized `tracker.py` cleanly (`76z7ww -> l596kn -> p4ueaj`) with zero cycles (`PR-001`).
  5. Software engineer: caught eager `from pubrun import __version__` in all 6 mode submodules, `Popen.__exit__` blocking risk on non-`TimeoutExpired` exceptions, symlinked `.dist-info` realpath edge case, `./`/`/`/trailing-`/` `RECORD` edge cases, and Python 3.8 typing compatibility (`PR-003`, `PR-004`, `PR-005`).
  6. Power user: verified downstream `mypy --strict --no-implicit-reexport` covers all six mode submodules including `__version__`, `__commit__`, and `paused`, and verified `pubrun._reset_commit_cache()` stays consistent across aliases (`PR-005`).
  7. Novice: ensured `help(pubrun)` lists all 20 public symbols and `help(pubrun.nopatch)` accurately distinguishes `nopatch` from `minimal` (`PR-005`).
  8. Stakeholder: confirmed full backward compatibility for Python 3.8-3.14, installed wheels, source checkouts, and all existing package-capture modes.

### Step R6

- Checked: decomposition and per-E-item conceptual density across `E-01..E-05` (5 E-items, 4 task groups, 13 Scope-Paths, Order 04 of 10-child Set `assess-8l`).
- Confirmed: each E-item owns one cohesive area (`E-01` `__init__.py` lazy `__version__`/fallback/pipes/doc, `E-02` `packages.py` I/O and `_markers` deferral, `E-03` six uniform mode submodules PEP 561 parity, `E-04` `core.py`/`tracker.py` lazy engine imports, `E-05` regression tests and validation). No further splitting is warranted.

### Step R7

- Checked: cross-plan consistency across Set `assess-8l`: orchestrator `k80suw` (Order 00), `1o1cua` (Order 01), `76z7ww` (Order 02), `l596kn` (Order 03), `ameehy` (Order 05), and `6y55x4` (Order 10).
- Verified:
  - `src/pubrun/core.py` is strictly serialized (`1o1cua -> p4ueaj`, via `executed:1o1cua`).
  - `src/pubrun/tracker.py` is strictly serialized (`76z7ww -> l596kn -> p4ueaj`, via `executed:76z7ww, executed:l596kn`), matching `k80suw:158` and `l596kn`'s Round 1 addition of `tracker.py`, with zero cycles (`1o1cua -> 76z7ww -> l596kn -> p4ueaj -> 6y55x4`).
  - Zero other siblings touch `src/pubrun/__init__.py`, `src/pubrun/capture/packages.py`, the six mode submodules, `tests/test_import_modes.py`, `tests/test_commit_identity.py`, or `tests/test_package_resolution.py`.
  - Downstream `mypy --strict` CI wiring remains cleanly deferred to `6y55x4` (Order 10), which already declares `executed:p4ueaj`.
  - Note for `k80suw` review: `k80suw`'s `E-04` and child table currently list `p4ueaj` depending on `01, 02` and should add `03` (`l596kn`) when `k80suw` is reviewed (the runner enforces `p4ueaj`'s own front-matter `- Item-Dependencies:` directly).

### Step S5

- Checked: `## Open questions` contains `None.`. All six findings (`PR-001` through `PR-006`) have `Low` overall Remediation Risk, are settled by repository code, tests, `-X importtime` measurements, and Set `assess-8l` contracts, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | UNDER-SCOPE | `r2-executability.md` / `r7-cross-plan.md` | `.aw/records/plans/pending/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md:7-8,76-80` vs `src/pubrun/core.py:23`, `src/pubrun/tracker.py:15-32`, `20261127-assess-8l-03-l596kn-...ipd.md:7` | `- Scope-Paths:` omitted `src/pubrun/core.py` and `src/pubrun/tracker.py`, which account for 122 ms of the 182 ms `import pubrun.minimal` cold start (making `E-04` and `V-04` unreachable); `- Item-Dependencies:` also lacked `executed:l596kn` needed to serialize shared `src/pubrun/tracker.py`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `src/pubrun/core.py` and `src/pubrun/tracker.py` to `- Scope-Paths:` and added `executed:l596kn` to `- Item-Dependencies:` (`1o1cua -> 76z7ww -> l596kn -> p4ueaj -> 6y55x4`, acyclic) (recommendation strength: `very strong`). |
| PR-002 | BLOCKER | IN-SCOPE | `r1-references.md` / `r2-executability.md` | `.aw/records/plans/pending/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md:6-7,84,113,127,165` | `tests/test_package_capture.py` does not exist in the repository; existing package-capture and commit-identity tests live in `tests/test_package_resolution.py`, `tests/test_package_lifecycle.py`, `tests/test_package_transitive.py`, and `tests/test_commit_identity.py`, and `## Required tests / validation` omitted 9 affected test suites. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `tests/test_package_capture.py` with `tests/test_commit_identity.py` and `tests/test_package_resolution.py` across `- Scope-Paths:`, `E-05`, `Proposed changes`, and `V-01..V-05`, and expanded validation to all 12 affected suites (recommendation strength: `very strong`). |
| PR-003 | BLOCKER | IN-SCOPE | `r4-engineering.md` A, D (Correctness and resource safety) | `src/pubrun/__init__.py::_resolve_commit:257`, `_resolve_checkout_commit:183-222`, `src/pubrun/tracker.py::Run.to_manifest_dict:1530`, `src/pubrun/{auto,full,noauto,nopatch,noconsole,minimal}.py` (`from pubrun import __version__`) | Moving `__version__` to PEP 562 `__getattr__` causes `NameError` at `src/pubrun/__init__.py:257` (`_read_packaged_commit(__version__)`); leaving `from pubrun import __version__` in all 6 mode submodules defeats lazy `importlib.metadata`; `E-01` left a 3-way ambiguous fallback version choice and missed stale `"1.0.0"` at `src/pubrun/tracker.py:1530`; and `with _sp.Popen` without killing/reaping on arbitrary `BaseException` risks blocking in `Popen.__exit__`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-01` and `E-03` to call `_get_version()` in `_resolve_commit`, remove eager `from pubrun import __version__` from all 6 mode submodules, specify a single deterministic fallback chain (`pyproject.toml` -> `_build_meta.json` -> `"0.0.0+unknown"`) plus `tracker.py:1530`, and kill/reap before `Popen.__exit__` on both `TimeoutExpired` and any `BaseException` (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r4-engineering.md` A, D, E (`packages.py` compatibility and test stability) | `src/pubrun/capture/packages.py:23-27,425-631,666-680,1087-1095`, `tests/test_reproducibility_preflight.py::_FakeDist:231-235`, `benchmarks/package_capture_bench.py:102-125` | Reading `Version` solely via `meta.get("Version")` breaks dict-based mocks lacking `"Version"` (`_FakeDist`); `E-02` left lazy `editable`/`requires` and `.egg-info` fallback underspecified, missed `PurePosixPath` `./`/`/`/trailing-`/` edge cases in fast-path `RECORD` parsing, missed symlinked `.dist-info` guard on parent-dir `realpath` cache, omitted deferring `pubrun.capture._markers` (12.3 ms), and used an uncalibrated `>=55%` latency bar in `V-02`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02`, `E-05`, and `V-02` with dict-mock `Version` fallback, in-memory `Requires-Dist` + zero `requires.txt` probes on `.dist-info` + lazy `.egg-info` fallback, lazy `_DistInfo.editable` + short-circuited shim check, `PurePosixPath` edge-case fallback, `os.path.islink` guard, deferred `_markers` import, and deterministic read-count/import assertions plus `package_capture_bench.py` output (recommendation strength: `very strong`). |
| PR-005 | HIGH | IN-SCOPE | `r4-engineering.md` C, D, F (Lazy seams, PEP 561, Python 3.8 typing, docstrings) | `src/pubrun/core.py:23`, `src/pubrun/tracker.py:15-34`, `src/pubrun/__init__.py:33,277-284`, `tests/test_api.py:410-415`, `tests/test_capture_isolation.py:103-129`, `tests/test_import_modes.py:1072-1077` | `E-04` lacked a concrete lazy-loading design preserving `monkeypatch.setattr` seams on `pubrun.core` and `pubrun.tracker`; `E-03` omitted `__dir__`, Python 3.8-compatible typing (`Optional`/`List`), and avoiding submodule-local `__commit__` caching; downstream `mypy --strict` validation checked only `pubrun.noauto.start()`/`stop()`; and `src/pubrun/__init__.py:33` still had the contradictory `nopatch` comment. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified exact lazy `Run`/`get_current_run` in `core.py` and `_LAZY_IMPORTS`/`_get_dep`/`__getattr__` in `tracker.py`, added `__dir__` and Python 3.8 typing on all 6 mode submodules, expanded Command 2 to check `__version__`/`__commit__` on all 6 mode submodules with `--no-implicit-reexport`, and included `src/pubrun/__init__.__doc__:33` `nopatch` fix in `E-01` (recommendation strength: `very strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `p-proofread.md` / `s7-finalize.md` | `.aw/records/plans/pending/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md:5-6,32-37,169-171` | `## Approval and execution gate` omitted the required five-clause execution contract, acronyms (`PEP`, `CSV`, `I/O`, `ENOENT`, `CI`) were unexpanded, code citations lacked `path::Symbol` anchors, and the Mermaid diagram omitted `core.py`, `tracker.py`, `_markers.py`, and test files. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added the five-clause execution contract, expanded acronyms on first use, anchored citations with `path::Symbol`, and updated the Mermaid `flowchart LR` diagram (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `p4ueaj` | `complex` | `standard` | Changes public package exports and PEP 561 typing across `__init__.py` and all six mode submodules, plus lazy import architecture across `core.py`, `tracker.py`, and `packages.py`; answers Yes to tier questions 1, 3, and 5 in `steps/t-tier.md`. | yes |
| D-2 | How to make `E-04`'s cold-start reduction reachable while serializing `src/pubrun/tracker.py` across Set `assess-8l` | Add `src/pubrun/core.py` and `src/pubrun/tracker.py` to `- Scope-Paths:` and add `executed:l596kn` to `- Item-Dependencies:` | Keep `core.py`/`tracker.py` out of `- Scope-Paths:` (leaves 122 ms of the 182 ms `import pubrun.minimal` untouched, making >70% reduction impossible) | `-X importtime` measurement (`pubrun.tracker` = 102 ms, `pubrun.core` = 122 ms), `k80suw:158` (`core.py -> tracker.py: 1o1cua -> 76z7ww -> p4ueaj`), and `l596kn:7-8` (`tracker.py`, `executed:76z7ww`). | yes |
| D-3 | Which deterministic fallback version chain to use in `src/pubrun/__init__.py::_get_version` | `importlib.metadata.version("pubrun")` -> verified checkout `pyproject.toml` `[project].version` -> packaged `_build_meta.json` `"version"` -> `"0.0.0+unknown"` (and `"0.0.0+unknown"` in `tracker.py:1530`) | Hardcode `"1.4.0"` (goes stale on next release) or return `"0.0.0+unknown"` in checkouts without editable install (breaks `E-01` expectation of `"1.4.0"` in `PYTHONPATH=src` checkouts) | `src/pubrun/__init__.py:110-167`, `hatch_build.py:139`, `tests/test_commit_identity.py:426-435`, and `src/pubrun/tracker.py:1530`. | yes |
| D-4 | Where to place new package-capture and pipe-cleanup regression tests after removing non-existent `tests/test_package_capture.py` | Add package read-count/`RECORD`/`_markers` tests to `tests/test_package_resolution.py` and lazy `__version__`/pipe-cleanup tests to `tests/test_commit_identity.py` | Create a new orphan `tests/test_package_capture.py` duplicating fixtures from `tests/test_package_resolution.py` | Existing test layout (`tests/test_package_resolution.py` already owns `_build_distribution_index`/`_extract_top_levels` fixtures; `tests/test_commit_identity.py` already owns `_resolve_checkout_commit` tests); zero other Set `assess-8l` plans touch either file. | yes |

### Step S6

- Checked: Round 1 changed `- Scope-Paths:` (added `src/pubrun/core.py`, `src/pubrun/tracker.py`, `tests/test_commit_identity.py`, `tests/test_package_resolution.py`; removed non-existent `tests/test_package_capture.py`) and changed `- Item-Dependencies:` (added `executed:l596kn`). Per `steps/s6-rereview.md` rule 1, a second pass (Round 2) is required to verify the revised Scope-Paths, dependencies, cross-references, and lint conformance.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised `.aw/records/plans/pending/20261127-assess-8l-04-p4ueaj-cold-start-import-package-capture-optimization-and-pep-561-m.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. Confirmed all acronyms are expanded on first use, all `E-01..E-05` and `V-01..V-05` items use exact `path::Symbol` citations with verifiable criteria, no superseded `tests/test_package_capture.py` or ambiguous fallback wording remains, and the Mermaid `flowchart LR` matches all 13 `- Scope-Paths:` entries.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R2

- Checked: verified `- Highest E allocated: 05` matches `E-01..E-05` and `V-01..V-05` (strict 1:1 bijection); verified `- Scope-Paths:` lists all 13 modified files with zero non-existent paths; verified `- Item-Dependencies: executed:1o1cua, executed:76z7ww, executed:l596kn` is acyclic; verified every runtime demonstration in `V-01..V-05` is reachable through `E-01..E-05`; verified the five-clause execution gate states conditional runner/executor finalize ownership with zero forbidden "STOP and report" scope-fence wording.

### Step R7

- Checked: verified `1o1cua -> 76z7ww -> l596kn -> p4ueaj -> 6y55x4` strictly serializes both `src/pubrun/core.py` and `src/pubrun/tracker.py` across Set `assess-8l` with zero cycles, and zero other pending plans touch `src/pubrun/__init__.py`, `src/pubrun/capture/packages.py`, the six mode submodules, `tests/test_import_modes.py`, `tests/test_commit_identity.py`, or `tests/test_package_resolution.py`.

### Step S5

- Checked: `## Open questions` contains `None.`; all six findings (`PR-001` through `PR-006`) are `FIXED`; zero blocking questions or irreversible decisions remain; lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | UNDER-SCOPE | `r2-executability.md` / `r7-cross-plan.md` | `src/pubrun/core.py:23`, `src/pubrun/tracker.py:15-32`, `l596kn:7` | Missing `src/pubrun/core.py` and `src/pubrun/tracker.py` in `- Scope-Paths:` and missing `executed:l596kn` in `- Item-Dependencies:`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `src/pubrun/core.py` and `src/pubrun/tracker.py` are in `- Scope-Paths:` and `- Item-Dependencies: executed:1o1cua, executed:76z7ww, executed:l596kn` serializes both shared files without cycles (recommendation strength: `very strong`). |
| PR-002 | BLOCKER | IN-SCOPE | `r1-references.md` / `r2-executability.md` | `p4ueaj` (`tests/test_package_capture.py`) | Non-existent `tests/test_package_capture.py` path and missing affected test suites in validation. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: zero references to `tests/test_package_capture.py` remain; tests target existing `tests/test_commit_identity.py` and `tests/test_package_resolution.py` and Command 1 runs all 12 affected suites (recommendation strength: `very strong`). |
| PR-003 | BLOCKER | IN-SCOPE | `r4-engineering.md` A, D | `src/pubrun/__init__.py:183-222,257`, `src/pubrun/tracker.py:1530`, six mode submodules | Bare `__version__` `NameError` in `_resolve_commit`, eager `from pubrun import __version__` in mode submodules, ambiguous fallback version + second stale `"1.0.0"` in `tracker.py`, and `Popen.__exit__` hang risk on non-`TimeoutExpired` exceptions. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-01` and `E-03` cover `_get_version()` in `_resolve_commit`, removing eager `__version__` imports, the deterministic fallback chain + `tracker.py:1530`, and kill/reap before `Popen.__exit__` on `TimeoutExpired` and `BaseException` (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r4-engineering.md` A, D, E | `src/pubrun/capture/packages.py:23-27,425-631,1087-1095`, `tests/test_reproducibility_preflight.py::_FakeDist:231-235` | Dict-mock `Version` breakage, underspecified lazy `editable`/`requires`/`.egg-info` handling, `PurePosixPath` and symlink `.dist-info` edge cases, eager `_markers` import, and uncalibrated `>=55%` bar. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-02`, `E-05`, and `V-02` address every edge case, defer `_markers`, and require deterministic read-count/import assertions plus `package_capture_bench.py` output (recommendation strength: `very strong`). |
| PR-005 | HIGH | IN-SCOPE | `r4-engineering.md` C, D, F | `src/pubrun/core.py:23`, `src/pubrun/tracker.py:15-34`, `src/pubrun/__init__.py:33`, `tests/test_api.py:410-415`, `tests/test_capture_isolation.py:103-129` | Unspecified lazy seams preserving monkeypatches, missing `__dir__` and Python 3.8 typing on mode submodules, narrow downstream `mypy --strict` check, and stale `__init__.__doc__` `nopatch` comment. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-01`, `E-03`, `E-04`, and Command 2 specify exact lazy seams, Python 3.8 typing, `__dir__`, all-6-modes `mypy --strict`, and aligned docstrings (recommendation strength: `very strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `p-proofread.md` / `s7-finalize.md` | `p4ueaj` | Missing five-clause execution contract, unexpanded acronyms, unanchored citations, and incomplete Mermaid diagram. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: five-clause execution gate, expanded acronyms, `path::Symbol` citations, and full Mermaid diagram are all reconciled (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `p4ueaj` | `complex` | `standard` | Changes public exports/PEP 561 typing across `__init__.py` and all six mode submodules plus lazy import architecture across `core.py`, `tracker.py`, and `packages.py`. | yes |
| D-2 | How to make `E-04` reachable while serializing `src/pubrun/tracker.py` | Add `src/pubrun/core.py` and `src/pubrun/tracker.py` to `- Scope-Paths:` and add `executed:l596kn` to `- Item-Dependencies:` | Leave them out of `- Scope-Paths:` | `-X importtime` measurement, `k80suw:158`, and `l596kn:7-8`. | yes |
| D-3 | Deterministic fallback version chain in `_get_version()` | `importlib.metadata` -> verified checkout `pyproject.toml` -> `_build_meta.json` -> `"0.0.0+unknown"` (and `"0.0.0+unknown"` in `tracker.py:1530`) | Static `"1.4.0"` or bare `"0.0.0+unknown"` everywhere | `src/pubrun/__init__.py:110-167`, `hatch_build.py:139`, `tests/test_commit_identity.py:426-435`, and `src/pubrun/tracker.py:1530`. | yes |
| D-4 | Test file targets replacing non-existent `tests/test_package_capture.py` | `tests/test_package_resolution.py` and `tests/test_commit_identity.py` | Create a new duplicate `tests/test_package_capture.py` | Existing test suite ownership and zero overlap with sibling Set `assess-8l` plans. | yes |

### Step S6

- Checked: Round 2 introduced no further edits, no new findings, and no structural changes. All revisions from Round 1 are internally consistent and reconciled across all sections. Ready for Step S7 finalization (`APPROVE WITH REVISIONS APPLIED`, `go-pending-approval`).

AW-REVIEW: DONE
