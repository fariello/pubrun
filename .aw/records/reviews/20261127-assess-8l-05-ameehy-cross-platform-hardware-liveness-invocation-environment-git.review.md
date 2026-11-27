# Review findings: ipd ameehy

- Subject-Id: ameehy
- Subject-Type: ipd
- Reviewed-At: 2026-11-27
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 1` `info` advisory `IPD-Z603` for 10 Scope-Paths). Expanded acronyms (`ROCm`, `GPU`, `VRAM`, `RAM`, `CPU`, `DLL`, `POSIX`, `CLI`, `MD5`, `JSON`, `LRU`, `RSS`) on first use, removed the contradicted `python_runtime.py normcase` mention from `- Concern:`, anchored symbols with `path::Symbol`, and updated the Mermaid `flowchart LR` diagram to include `system_metrics.py`, docs, and all five test modules.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `- Concern:`, `E-03`, `- Scope-Paths:`, `E-05`, `## Required tests / validation` | Referenced nonexistent `[capture.invocation].compute_md5` with no cap value/key; omitted `tests/test_invocation.py`, `tests/test_capture_engine_bugs.py`, and `tests/test_config_capture_modes.py` whose assertions break under `E-01`..`E-04`; omitted `__spec__.origin` guard for `python -m pytest` | Fixed to `[capture.inputs].compute_md5` with `100 MiB` default (`max_md5_bytes` override, `0` = uncapped, `md5_skipped`), added `__spec__.origin` guard, and added all three breaking test files to `- Scope-Paths:`, `E-05`, and `## Required tests / validation` | Prevent blocker test failures and wrong config key implementation (`PR-001`) |
| `E-01`, `V-01` (`hardware.py`) | Unspecified Windows fallback order (`platform.processor()` could shadow `wmic`), registry display-adapter class keys, `amd-smi`/`rocm-smi` JSON commands and `$defs.gpu_record` conformance, and binary macOS VRAM unit table | Specified testable Windows native helpers + fallback order (`winreg`/`GlobalMemoryStatusEx` -> `wmic` -> `platform.processor()`), display-class registry + `EnumDisplayDevicesW`, ARM64 CPU chain, `amd-smi`/`rocm-smi` JSON commands conforming to `$defs.gpu_record`, and binary `1024`-based `_parse_vram_bytes` | Make `hardware.py` deterministic, mypy-clean across 3 OSes, and schema-compliant (`PR-002`) |
| `E-02`, `V-02` (`liveness.py`, `system_metrics.py`) | Top-level `_PROCESS_MEMORY_COUNTERS` would eagerly import `ctypes` on Linux/macOS; cached `WinDLL` lacked lock and fake-`kernel32` re-check; `_get_cpu_linux` lacked `clock_ticks <= 0` guard | Specified lock-protected lazy caching of `_PROCESS_MEMORY_COUNTERS_CLS`, `_WIN_KERNEL32`, and `_WIN_PSAPI`, re-checking `isinstance(windll_k32, win_dll_cls)` on every call, never mutating `argtypes` on fakes, and guarding `right_paren == -1` and `clock_ticks <= 0` in both Linux helpers | Preserve cold-start speed, thread safety, and test monkeypatch semantics (`PR-003`) |
| `E-03`, `E-04`, `V-03`, `V-04` (`invocation.py`, `redaction.py`) | Missing zero-import `sys.modules.get("IPython")` check, `-c`/interactive `rerun_command = None`, redacted `--flag=value` pre-check, `stat.S_ISREG` guard, and Python 3.8–3.11 `json.loads`/`json.dumps` `RecursionError` fallback in `redaction.py` | Specified `sys.modules.get("IPython")` check, `rerun_command = None` for `-c`/interactive/notebook, pre-split `redacted_argv[idx] != arg` check, `S_ISREG` guard, iterative `_redact_any` with cycle guard, and `RecursionError` JSON key-value redaction fallback | Close Python 3.8–3.11 JSON redaction bypass and invocation edge cases (`PR-004`) |
| `- Concern:`, `- Scope-Paths:`, `- Item-Dependencies:`, `E-04`, `## Deferred / out of scope`, `## Spec / documentation sync` | Omitted `docs/configuration.md` and `docs/manifest.md` sync, declared `- Item-Dependencies: none`, contradicted `Deferred` on `python_runtime.py normcase`, and omitted `__main__.py::_format_rerun_cmd_for_platform` / `default.toml` handoff to `2ge0ea` | Added `docs/configuration.md` and `docs/manifest.md` (zero-dash check), set `- Item-Dependencies: executed:l596kn`, fixed `- Concern:`, and documented `2ge0ea` carrier follow-ups in `## Deferred / out of scope` | Keep user docs accurate and serialize shared doc files cleanly across Set `assess-8l` (`PR-005`) |
| `## Goal`, Mermaid diagram, `V-05`, `## Approval and execution gate` | Unexpanded acronyms, incomplete Mermaid diagram, suite-only `V-05`, and one-line execution gate | Expanded acronyms, updated Mermaid diagram, named concrete test units in `V-05`, and added the five-clause execution contract | Satisfy technical-writing, executability, and execution-contract rules (`PR-006`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: assess-8l`, `- Order: 5`, `- Scope-Paths:` (8 capture modules, 2 docs, 5 test files), 5 E-items in 3 task groups.

1. Yes: updates public manifest outputs (`invocation.rerun_command` using `sys.executable` or `null`, `entrypoint_type = "notebook"`, `hardware.gpus` AMD ROCm and macOS VRAM bytes, `invocation.inputs` `--flag=path` and `md5_skipped`) and documents `[capture.inputs].max_md5_bytes` and Windows environment allowlist behavior.
2. Yes: touches `src/pubrun/capture/redaction.py` (secret redaction and JSON `RecursionError` bypass defense) and `src/pubrun/capture/invocation.py` (`--flag=value` redaction gate).
3. Yes: spans eight capture modules across three OS platforms, two user-facing docs, five test files, and four rollup findings (`ROLL-13`, `ROLL-16`, `ROLL-31`, `ROLL-34`).
4. Yes: `- Scope-Paths:` explicitly lists all 15 modified files.
5. Yes: regressions in `redaction.py`, `invocation.py` `--flag=value` filtering, `liveness.py` Windows `ctypes`, or `hardware.py` probe fallbacks can leak secrets, fail on Windows 11 24H2+, or break existing CI suites.

AW-TIER: complex

### Step R1

- Checked: every cited source file, schema, config default, doc, and test file against the repository:
  - `src/pubrun/capture/hardware.py:1-356` (`_CaptureBudget`, `_get_cpu_model`, `_get_total_memory_bytes`, `_get_gpus`, `get_hardware`)
  - `src/pubrun/capture/liveness.py:1-698` (`_get_start_time_linux`, `_get_cpu_linux`, `_get_cpu_macos`, `_get_win_kernel32`, `_get_rss_windows`, `_get_cpu_windows`)
  - `src/pubrun/capture/system_metrics.py:1-121` (`iowait_pct_between`)
  - `src/pubrun/capture/invocation.py:1-187` (`get_invocation`)
  - `src/pubrun/capture/environment.py:1-45` (`_allowlist_patterns`, `get_environment`)
  - `src/pubrun/capture/git.py:1-199` (`get_git`, `_run_git_raw`)
  - `src/pubrun/capture/filesystem.py:1-421` (`_longest_prefix_fstype`, `_classify_path_linux`, `_classify_windows_path`, `get_filesystem`)
  - `src/pubrun/capture/redaction.py:1-398` (`_PATTERN_CACHE`, `_get_secret_pattern`, `_redact_dict_keys`, `_redact_any`, `_redact_value_string_heuristics`, `redact_argv`, `format_safe_error_detail`)
  - `src/pubrun/capture/console.py:38-48` (`_is_jupyter_kernel`), `src/pubrun/__main__.py:344-401` (`_format_rerun_cmd_for_platform`), `src/pubrun/resources/default.toml:191-311`, `schemas/manifest.schema.json:564-741,1275-1395`, `docs/manifest.md:93-122,356-386`, `docs/configuration.md:143-214`.
  - Tests: `tests/test_hardware.py:114-127`, `tests/test_liveness.py:349-460`, `tests/test_invocation.py:22-214`, `tests/test_capture_engines.py:1-475`, `tests/test_capture_engine_bugs.py:144-161,480-520`, `tests/test_config_capture_modes.py:362-428`, `tests/test_redaction.py:1-209`, `tests/test_env_capture.py:254-261`, `tests/test_platform_capture_seams.py:1-126`, `tests/test_capture.py:37-68`.
- Verified empirically: `LC_ALL=C` + `encoding="utf-8", errors="replace"` preserves UTF-8 repo paths while forcing English `"not a git repository"` stderr; on Python 3.14 `json.loads`/`json.dumps` handle depth 1,500 while Python 3.8–3.11 C `_json` can still raise `RecursionError`, proving the need for the `RecursionError` fallback in `_redact_value_string_heuristics()`.

### Step R2

- Checked: strict 1:1 `E-01..E-05` <-> `V-01..V-05` bijection, `- Highest E allocated: 05`, `- Scope-Paths:` completeness (all 15 modified files), `- Item-Dependencies: executed:l596kn`, concrete named units in every `V-*` item, non-tautological validation evidence, and the five-clause execution contract.
- Verified: every `E-*` maps cleanly to an observable `V-*` with named `path::Symbol` targets and explicit `pytest`, three-platform `mypy`, and user-facing dash-check evidence.

### Step R3

- Checked: trust boundaries and security invariants in `redaction.py` (1,500-level nested JSON secret redaction and `RecursionError` bypass prevention across Python 3.8–3.14, bounded 64-entry LRU regex cache preventing cache-growth DoS, unhashable/invalid regex resilience), `invocation.py` (`redacted_argv[idx] != arg` check prior to `--flag=value` extraction so `--api-key=creds.json` never leaks into `invocation.inputs`, bounded `[capture.inputs].max_md5_bytes` preventing startup disk-read DoS, `stat.S_ISREG` guard against FIFOs/devices), `environment.py` (fail-closed allowlist still redacting matched secrets), and `git.py` (remote URL credential redaction preserved).
- Verified: `PR-004` closes the Python 3.8–3.11 `json.loads`/`json.dumps` `RecursionError` redaction bypass and enforces the pre-split redaction check on `--flag=value` arguments.

### Step R4

- Checked: correctness and data integrity (A), architecture and operability (C), anti-regression and domain invariants (D), testing and verification (E), KISS/principles/UX (F), right-sizing, and `## Spec / documentation sync`.
- Verified: `PR-001` catches the wrong config section name and four breaking existing test files; `PR-002` pins Windows native probe seams/fallback ordering, Linux ARM64/ROCm schema conformance, and binary macOS VRAM units; `PR-003` preserves Linux/macOS cold-start import speed, thread safety, and fake-`kernel32` precedence in `liveness.py`; `PR-004` closes invocation and redaction edge cases; `PR-005` syncs `docs/configuration.md` and `docs/manifest.md` serialized after `l596kn`; `PR-006` adds the five-clause execution gate and technical-writing fixes.

### Step R5

- Checked: all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md`:
  1. QA / QC: caught `[capture.invocation]` vs `[capture.inputs]` mismatch and four existing test files broken by the planned changes (`PR-001`), plus `python -m pytest` hijacking `tests/test_invocation.py` (`PR-001`).
  2. Testing and regression: updated `test_hardware.py`, `test_capture_engine_bugs.py`, `test_invocation.py`, and `test_config_capture_modes.py` for cross-OS determinism on Windows CI and added all 13 relevant test suites to `## Required tests / validation` (`PR-001`, `PR-006`).
  3. UI / UX: ensured `-c`, interactive REPL, and Jupyter notebooks emit `rerun_command = None` rather than broken shell commands, and synced user-facing docs (`PR-004`, `PR-005`).
  4. Architect: serialized `docs/configuration.md` and `docs/manifest.md` via `- Item-Dependencies: executed:l596kn` with zero cycles and avoided touching `default.toml` or `__main__.py` owned by `2ge0ea` (`PR-005`).
  5. Software engineer: preserved lazy `ctypes` loading and lock-protected fake-aware `WinDLL` caching in `liveness.py` (`PR-003`), direct `sys.platform == "win32"` mypy guards in `hardware.py` (`PR-002`), and `stat.S_ISREG` + single `os.stat()` in `invocation.py` (`PR-004`).
  6. Power user: verified `python -m pkg.mod`, `--flag=path`, venv `sys.executable`, Linux ARM64/ROCm, and configurable `[capture.inputs].max_md5_bytes` (`0` = uncapped) work cleanly (`PR-001`, `PR-002`, `PR-004`).
  7. Novice: updated `docs/manifest.md` and `docs/configuration.md` (with zero em/en dashes) so documented fields and defaults match actual runtime output (`PR-005`).
  8. Stakeholder: confirmed 100% conformance to `schemas/manifest.schema.json` v1.0 (`$defs.gpu_record`, `$defs.invocation`) with zero breaking schema changes (`PR-002`, `PR-005`).

### Step R6

- Checked: decomposition and sizing across `E-01..E-05` (5 E-items, 3 task groups, 15 Scope-Paths, Order 05 of 10-child Set `assess-8l`) and the `IPD-Z603` info advisory on Scope-Paths count (`> 8`).
- Confirmed: no splitting is warranted. `ameehy` is already a bounded child plan within Set `assess-8l` covering ~240 lines of localized, non-overlapping cross-platform fixes across small capture modules (`environment.py` is 45 lines, `system_metrics.py` is 121 lines, `invocation.py` is 187 lines, `git.py` is 199 lines) plus the exact test/doc files needed to keep CI and docs consistent. Splitting tiny 3-to-15-line fixes out of Order 05 would add orchestrator churn in `k80suw`/`6y55x4` with no safety or parallelism benefit.

### Step R7

- Checked: cross-plan consistency across Set `assess-8l`: orchestrator `k80suw` (Order 00), `76z7ww` (Order 02, which defers Windows `liveness.py` caching to `ameehy`), `l596kn` (Order 03, which touches `docs/configuration.md` and `docs/manifest.md`), `p4ueaj` (Order 04, cold-start import optimization), `2ge0ea` (Order 08, which owns `default.toml`, `python_runtime.py`, `reproducibility.py`, and `__main__.py`), and `6y55x4` (Order 10, which depends on `executed:ameehy`).
- Verified: adding `- Item-Dependencies: executed:l596kn` serializes `docs/configuration.md` and `docs/manifest.md` cleanly with zero cycles (`1o1cua -> 76z7ww -> l596kn -> ameehy -> 6y55x4`); `ameehy` shares zero files with `p4ueaj`, `m5s3g8`, `caeqdz`, `2ge0ea`, `3q5rd5`, or `6y55x4`; and the two cross-file follow-ups (`__main__.py::_format_rerun_cmd_for_platform` and `default.toml` comments) are explicitly deferred with `- Carrier: 2ge0ea`. Note for `k80suw` review: `k80suw`'s `E-05` row and child table currently list `ameehy` as depending on `none` and should be updated to `03` (`E-03`) when `k80suw` is reviewed (the runner enforces `ameehy`'s own `- Item-Dependencies: executed:l596kn` directly).

### Step S5

- Checked: `## Open questions` contains `None.`. All six findings (`PR-001` through `PR-006`) had `Low` overall Remediation Risk, were settled by repository code, schema, and test evidence, and were fixed in place with zero unfixed, deferred, or open findings and zero irreversible decisions requiring human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A, D | `.aw/records/plans/pending/20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md:70-73` vs `src/pubrun/capture/invocation.py:94-96`, `tests/test_invocation.py:23-60,164-184`, `tests/test_capture_engine_bugs.py:150,495-520`, `tests/test_hardware.py:114-127`, `tests/test_config_capture_modes.py:402-406` | `E-03` named nonexistent `[capture.invocation].compute_md5` instead of `[capture.inputs].compute_md5` with no cap value/key; unguarded `__main__.__spec__` detection breaks `tests/test_invocation.py` under `python -m pytest`; and four existing test files outside `- Scope-Paths:` (`test_invocation.py`, `test_capture_engine_bugs.py`, `test_hardware.py`, `test_config_capture_modes.py`) assert old bare-`python`, `_PATTERN_CACHE`, `None` macOS VRAM, Windows `wmic`, or unconditional POSIX allowlist casing. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected config section to `[capture.inputs]` with `100 MiB` default (`max_md5_bytes`, `0` = uncapped, `md5_skipped`), added `__spec__.origin` match guard, and added `tests/test_invocation.py`, `tests/test_capture_engine_bugs.py`, and `tests/test_config_capture_modes.py` to `- Scope-Paths:`, `E-05`, and `## Required tests / validation` with explicit updates for each breaking assertion (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r4-engineering.md` A, C | `src/pubrun/capture/hardware.py:68-291`, `schemas/manifest.schema.json:1321-1366` (`$defs.gpu_record`) | `E-01` left Windows fallback ordering ambiguous (`platform.processor()` would shadow legacy `wmic` fallback), omitted Windows display-adapter registry keys (`{4d36e968-...}`) and testable helper seams, omitted exact `amd-smi`/`rocm-smi` JSON commands and `$defs.gpu_record` (`additionalProperties: false`) conformance, and did not specify binary (`1024`-based) macOS `VRAM (Total):` unit conversion. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified testable Windows native helpers and exact fallback order (`winreg`/`GlobalMemoryStatusEx` -> `wmic` -> `platform.processor()`), display-class registry + `EnumDisplayDevicesW`, Linux ARM64 CPU chain, `amd-smi`/`rocm-smi` JSON commands conforming to `$defs.gpu_record`, direct `sys.platform == "win32"` mypy guards, and binary `_parse_vram_bytes` in `E-01` and `V-01` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` A, C, D | `src/pubrun/capture/liveness.py:310-379,444-498,572-637`, `tests/test_liveness.py:412-460` | Top-level `_PROCESS_MEMORY_COUNTERS` would eagerly import `ctypes`/`ctypes.wintypes` on Linux/macOS (hurting cold-start); caching `_WIN_KERNEL32` without re-checking `isinstance(windll_k32, win_dll_cls)` breaks fake-`kernel32` tests after a real call; lazy init lacked a lock; and `_get_cpu_linux()` lacked a `clock_ticks <= 0` guard while `_get_start_time_linux()` did not catch `ZeroDivisionError`/`AttributeError`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02` and `V-02` to specify lock-protected lazy caching of `_PROCESS_MEMORY_COUNTERS_CLS`, `_WIN_KERNEL32`, and `_WIN_PSAPI`, re-checking `isinstance(windll_k32, win_dll_cls)` on every call, never mutating `argtypes` on fakes, and guarding `right_paren == -1` and `clock_ticks <= 0` (catching `ZeroDivisionError`/`AttributeError`) in both Linux helpers (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D | `src/pubrun/capture/invocation.py:38-174`, `src/pubrun/capture/console.py:38-48`, `src/pubrun/capture/redaction.py:115-170,253,377-395` | `invocation.py` lacked zero-import `sys.modules.get("IPython")` Jupyter detection, `rerun_command = None` for `-c`/interactive, pre-split `redacted_argv[idx] != arg` check on `--flag=value` (preventing redacted secret paths from leaking into `inputs`), and `stat.S_ISREG` guard; in `redaction.py`, Python 3.8–3.11 `json.loads`/`json.dumps` can raise `RecursionError` at depth 1,500 and silently fall through `except Exception: pass` without redacting JSON secret keys. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-03`, `E-04`, `V-03`, and `V-04` to require `sys.modules.get("IPython")` detection, `rerun_command = None` for `-c`/interactive/notebook, pre-split redaction check and `S_ISREG` guard, iterative `_redact_any` with cycle protection, and an explicit `RecursionError` JSON key-value redaction fallback in `_redact_value_string_heuristics()` plus hoisting `_NEWLINE_RE` (recommendation strength: `very strong`). |
| PR-005 | MEDIUM | UNDER-SCOPE | `r4-engineering.md` E, F / `r7-cross-plan.md` | `docs/manifest.md:101-102,379-381`, `docs/configuration.md:149,201,212`, `src/pubrun/__main__.py:346`, `.aw/records/plans/pending/20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md:5,119,134` | `docs/configuration.md` and `docs/manifest.md` were missing from scope despite observable changes to `hardware.gpus`, `invocation`, `[capture.environment].allowlist`, and `[capture.inputs].compute_md5`; adding them requires `- Item-Dependencies: executed:l596kn` for Set serialization; `- Concern:` contradicted `Deferred` on `python_runtime.py normcase`; and `__main__.py::_format_rerun_cmd_for_platform` (`" && python "`) / `default.toml` comment sync needed explicit deferral to `2ge0ea`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Added `docs/configuration.md` and `docs/manifest.md` to `- Scope-Paths:`, `E-04`, `## Spec / documentation sync`, and `V-04` (zero-dash check); set `- Item-Dependencies: executed:l596kn`; fixed `- Concern:`; and documented the `2ge0ea` follow-ups in `## Deferred / out of scope` with `- Carrier: 2ge0ea` (recommendation strength: `strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `.aw/records/plans/pending/20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md:5,28-44,127-130,164-171` | `## Approval and execution gate` omitted the five-clause execution contract; `V-05` lacked concrete unit coverage across all modified test suites; acronyms were unexpanded on first use; and the Mermaid diagram omitted `system_metrics.py`, docs, and updated test suites. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Wrote the complete five-clause execution gate, expanded `## Required tests / validation` and `V-05` to cover all 13 test suites and concrete units, expanded acronyms on first use, and updated the Mermaid diagram (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `ameehy` | `complex` | `standard` | Modifies `redaction.py` (security boundary), changes public manifest outputs (`invocation`, `hardware`), spans 8 capture modules across 3 OSes, and updates user-facing docs; answers Yes to all five tier questions in `steps/t-tier.md`. | yes |
| D-2 | How to serialize `docs/configuration.md` and `docs/manifest.md` and avoid colliding with `2ge0ea` on `default.toml` / `__main__.py` | Add `docs/configuration.md` and `docs/manifest.md` to `ameehy` with `- Item-Dependencies: executed:l596kn`, and defer `default.toml` comment sync + `__main__.py::_format_rerun_cmd_for_platform` to `2ge0ea` (`- Carrier: 2ge0ea`) | Edit `default.toml` and `__main__.py` inside `ameehy` (creates unserialized overlap with `2ge0ea`, since `2ge0ea` does not depend on `ameehy`) or leave `docs/*.md` stale | Set `assess-8l` Scope-Paths partition (`l596kn` owns `docs/{configuration,manifest}.md`; `2ge0ea` owns `default.toml` and `__main__.py`). | yes |
| D-3 | Whether to split `ameehy` due to `IPD-Z603` (`> 8` Scope-Paths) | Keep `ameehy` as Order 05 of Set `assess-8l` (5 E-items, ~240 LOC total delta) | Split into two child plans (forces `no-go` and restructures orchestrator `k80suw` and `6y55x4` for small 3-to-15-line fixes) | `IPD-Z603` is an `info` advisory (`exit 0`); all 8 capture modules are tiny, localized, non-overlapping cross-platform fixes executable in one turn. | yes |

### Step S6

- Checked: Round 1 expanded `- Scope-Paths:` from 10 to 15 files (adding `docs/configuration.md`, `docs/manifest.md`, `tests/test_invocation.py`, `tests/test_capture_engine_bugs.py`, and `tests/test_config_capture_modes.py`) and changed `- Item-Dependencies:` from `none` to `executed:l596kn`. Per `steps/s6-rereview.md` rule 1, a second pass (Round 2) is required to verify the revised Scope-Paths, dependencies, cross-references, and lint conformance.

AW-REVIEW: AGAIN

## Round 2

### Step P

- Checked: re-read the complete revised `.aw/records/plans/pending/20261127-assess-8l-05-ameehy-cross-platform-hardware-liveness-invocation-environment-git.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12. Confirmed all acronyms are expanded on first use, no stale `[capture.invocation]` or contradicted `python_runtime.py normcase` wording remains, all `E-01..E-05` and `V-01..V-05` items name exact `path::Symbol` units with observable criteria, and the Mermaid `flowchart LR` matches all 15 `- Scope-Paths:` entries.

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step R2

- Checked: verified `- Highest E allocated: 05` matches `E-01..E-05` and `V-01..V-05` (strict 1:1 bijection); verified `- Scope-Paths:` lists all 15 modified files; verified `- Item-Dependencies: executed:l596kn` is acyclic; verified no superseded wording remains; verified the five-clause execution gate states conditional runner/executor finalize ownership with no forbidden "STOP and report" scope-fence wording.

### Step R7

- Checked: verified `1o1cua -> 76z7ww -> l596kn -> ameehy -> 6y55x4` serializes `docs/configuration.md` and `docs/manifest.md` cleanly across Set `assess-8l`, zero other siblings touch `ameehy`'s capture modules or five test files, and deferred `default.toml`/`__main__.py` follow-ups name `- Carrier: 2ge0ea`.

### Step S5

- Checked: `## Open questions` contains `None.`; all six findings (`PR-001` through `PR-006`) are `FIXED`; zero blocking questions or irreversible decisions remain; lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | BLOCKER | IN-SCOPE | `r1-references.md` / `r4-engineering.md` A, D | `src/pubrun/capture/invocation.py:94-96`, `tests/test_invocation.py:23-60,164-184`, `tests/test_capture_engine_bugs.py:150,495-520`, `tests/test_hardware.py:114-127`, `tests/test_config_capture_modes.py:402-406` | Wrong `[capture.invocation]` config section, missing cap spec, missing `__spec__.origin` guard, and four existing test files broken outside `- Scope-Paths:`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `[capture.inputs].max_md5_bytes` (`100 MiB` default), `__spec__.origin` guard, and all affected test files are reconciled across `- Scope-Paths:`, `E-03`, `E-05`, and `V-03`/`V-05` (recommendation strength: `very strong`). |
| PR-002 | HIGH | IN-SCOPE | `r4-engineering.md` A, C | `src/pubrun/capture/hardware.py:68-291`, `schemas/manifest.schema.json:1321-1366` | Ambiguous Windows fallback order, omitted Windows display registry/seams, unspecified `amd-smi`/`rocm-smi` `$defs.gpu_record` contract, and unspecified binary macOS VRAM units. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-01` and `V-01` specify all Windows native seams/order, Linux ARM64/ROCm commands and `$defs.gpu_record` compliance, mypy guards, and binary `_parse_vram_bytes` (recommendation strength: `very strong`). |
| PR-003 | HIGH | IN-SCOPE | `r4-engineering.md` A, C, D | `src/pubrun/capture/liveness.py:310-379,444-498,572-637`, `tests/test_liveness.py:412-460` | Eager `ctypes` import on non-Windows, unguarded `WinDLL` caching vs fake-`kernel32` tests, missing lock, and missing `clock_ticks <= 0` / `ZeroDivisionError` guards. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-02` and `V-02` specify lock-protected lazy caching, fake-`kernel32` precedence, and full `/proc` + `iowait` guards (recommendation strength: `very strong`). |
| PR-004 | HIGH | IN-SCOPE | `r3-security.md` / `r4-engineering.md` A, D | `src/pubrun/capture/invocation.py:38-174`, `src/pubrun/capture/redaction.py:115-170,253,377-395` | Missing zero-import Jupyter check, `-c`/interactive `rerun_command = None`, pre-split `--flag=value` redaction gate, `S_ISREG` guard, and Python 3.8–3.11 `json.loads`/`json.dumps` `RecursionError` redaction fallback. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: `E-03`, `E-04`, `V-03`, and `V-04` close every invocation and Python 3.8–3.14 JSON redaction edge case (recommendation strength: `very strong`). |
| PR-005 | MEDIUM | UNDER-SCOPE | `r4-engineering.md` E, F / `r7-cross-plan.md` | `docs/manifest.md:101-102,379-381`, `docs/configuration.md:149,201,212`, `src/pubrun/__main__.py:346` | Missing `docs/configuration.md` and `docs/manifest.md` sync, missing `executed:l596kn` dependency, `- Concern:` contradiction, and unrecorded `2ge0ea` carrier follow-ups. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: docs, `executed:l596kn`, `- Concern:`, and `2ge0ea` deferrals are fully reconciled (recommendation strength: `strong`). |
| PR-006 | MEDIUM | UNDER-SCOPE | `r2-executability.md` / `s7-finalize.md` / `p-proofread.md` | `ameehy` | Missing five-clause execution gate, suite-only `V-05`, unexpanded acronyms, and incomplete Mermaid diagram. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Verified in Round 2: five-clause gate, named `V-05` units, acronym expansions, and Mermaid diagram are all reconciled (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `ameehy` | `complex` | `standard` | Modifies `redaction.py`, updates public manifest outputs across 8 capture modules and 3 OSes, and syncs user-facing docs; answers Yes to all five tier questions in `steps/t-tier.md`. | yes |
| D-2 | How to serialize `docs/configuration.md` and `docs/manifest.md` and avoid colliding with `2ge0ea` on `default.toml` / `__main__.py` | Add `docs/configuration.md` and `docs/manifest.md` to `ameehy` with `- Item-Dependencies: executed:l596kn`, and defer `default.toml` comment sync + `__main__.py::_format_rerun_cmd_for_platform` to `2ge0ea` (`- Carrier: 2ge0ea`) | Edit `default.toml` and `__main__.py` inside `ameehy` or leave docs stale | Set `assess-8l` Scope-Paths partition (`l596kn` owns `docs/{configuration,manifest}.md`; `2ge0ea` owns `default.toml` and `__main__.py`). | yes |
| D-3 | Whether to split `ameehy` due to `IPD-Z603` (`> 8` Scope-Paths) | Keep `ameehy` as Order 05 of Set `assess-8l` (5 E-items, ~240 LOC total delta) | Split into two child plans | `IPD-Z603` is an `info` advisory (`exit 0`); all 8 capture modules are small, localized, non-overlapping cross-platform fixes executable in one turn. | yes |

### Step S6

- Checked: Round 2 introduced no further edits, no new findings, and no structural changes. All revisions from Round 1 are internally consistent and reconciled across all sections. Ready for Step S7 finalization (`APPROVE WITH REVISIONS APPLIED`, `go-pending-approval`).

AW-REVIEW: DONE
