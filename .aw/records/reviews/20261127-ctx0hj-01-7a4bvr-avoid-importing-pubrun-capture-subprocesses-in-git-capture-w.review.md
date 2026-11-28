# Review findings: ipd 7a4bvr

- Subject-Id: 7a4bvr
- Subject-Type: ipd
- Reviewed-At: 2026-11-28
- Reviewer: Antigravity
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: the complete text of `.aw/records/plans/pending/20261127-ctx0hj-01-7a4bvr-avoid-importing-pubrun-capture-subprocesses-in-git-capture-w.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 through 12 and spec Section 11.1 code citation rules. Working tree was clean (`git status --short` empty), so no pre-review snapshot commit was needed. `aw ipd lint --phase author --agent` exited `0` (`outcome: clean`, `findings: 0`), and `aw ipd lint --phase author --citation-anchors --detail` exited `0` (`conforming`). Identified a minor diagram/text mismatch under Requirement 12(d) (the `LOOKUP` flowchart node omitted the `modules is not None` guard specified in `E-01`) and an omitted `assert not hw_thread.is_alive()` check in `E-03` (`PR-003`).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `### Git subprocess spy-bypass flow` (`LOOKUP` node) | Showed `getattr(sys, 'modules', _SYS_MODULES).get('pubrun.capture.subprocesses')` without the `None` guard | Shows `Resolve modules = getattr(sys, 'modules', _SYS_MODULES); look up 'pubrun.capture.subprocesses' if modules is not None` | Match normative `E-01` null-guard wording per technical writing standard Req 12(d) (`PR-003`) |
| `E-02` item 1 | Required installing `SubprocessSpy` and asserting every git invocation had `_spy_bypassed() == True` and zero records | Requires asserting `SubprocessSpy.install(owner=...)` returns `True`, at least one wrapped invocation ran with `_spy_bypassed() == True`, `_spy_bypassed()` returns to `False` after `get_git`, and zero records before `finally: SubprocessSpy.uninstall(owner=...)` | Prevent vacuous `all([])` pass, silent pre-installed spy, leaked bypass depth, or post-uninstall empty-record check (`PR-002`) |
| `E-02` item 3, `## Proposed changes` item 2, `V-01` limb (1) | Ran bare `import pubrun.capture.git` in a fresh subprocess with only `PYTHONPATH=src` and asserted `"pubrun.capture.subprocesses" not in sys.modules` | Sets `PUBRUN_IMPORT_MODE="minimal"` and unsets `PUBRUN_AUTO_START` and `PUBRUN_RUN_MODE_OVERRIDE` alongside `PYTHONPATH=src`, and verifies `pubrun.capture.subprocesses` is unloaded both before and after calling `get_git` | Bare `import pubrun.capture.git` executes `src/pubrun/__init__.py` auto-start (`auto` mode) and loads `pubrun.capture.subprocesses` via Step 5 before `get_git` runs (`PR-001`) |
| `E-03` | Joined `run._hardware_thread` with a 15-second timeout without asserting thread completion | Joins `run._hardware_thread` with a 15-second timeout and asserts `not hw_thread.is_alive()` when present | Match sibling `test_nopatch_background_hw_does_not_load_subprocesses_module` and prevent a hung background thread from racing `loaded_before_stop` (`PR-003`) |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Kind: child`, `- Set: ctx0hj`, `- Order: 1`, `- Scope-Paths: src/pubrun/capture/git.py, tests/test_capture_engines.py, tests/test_import_modes.py`, 3 E-items in 2 task groups, no `.spec.md` file.

1. No: the plan introduces only a private internal helper (`_disable_spy_if_loaded`) in `src/pubrun/capture/git.py` and changes no spec, CLI flag, output format, manifest schema, configuration key, or public API signature.
2. No: `src/pubrun/capture/git.py` does not guard commits, worktree isolation, merges to main, or the sandbox, and leaves existing `remote_url` redaction untouched.
3. No: the plan has 3 focused E-items in 2 task groups across 1 production module and 2 test files.
4. Yes: `- Scope-Paths:` explicitly lists `src/pubrun/capture/git.py`, `tests/test_capture_engines.py`, and `tests/test_import_modes.py`.
5. Yes: `src/pubrun/capture/git.py::_run_git_raw` runs synchronously during Step 2 of `Run._bootstrap_engines()` on every tracked run with git capture enabled; a mistake in `_disable_spy_if_loaded()` could break active `SubprocessSpy` bypass (polluting subprocess provenance records with internal `git` calls) or degrade git capture to `failed`.

AW-TIER: standard

### Step R1

- Checked: backlog item `.aw/records/backlog/graduated/20261127-ctx0hj-01-ctx0hj-avoid-importing-pubrun-capture-subprocesses-in-src.backlog.md`, executed IPD `3ed2o4`, `pyproject.toml`, `.github/workflows/ci.yml`, `src/pubrun/capture/git.py`, `src/pubrun/capture/hardware.py`, `src/pubrun/capture/filesystem.py`, `src/pubrun/capture/resources.py`, `src/pubrun/capture/subprocesses.py`, `src/pubrun/capture/redaction.py`, `src/pubrun/tracker.py`, `src/pubrun/__init__.py`, `src/pubrun/_bootstrap.py`, `src/pubrun/nopatch.py`, `src/pubrun/minimal.py`, `src/pubrun/resources/default.toml`, `src/pubrun/core.py`, `src/pubrun/status.py`, `tests/conftest.py`, `tests/test_capture_engines.py`, `tests/test_import_modes.py`, `tests/test_capture_isolation.py`, `tests/test_signals.py`, `docs/architecture.md`, and `docs/functional_spec.md`.
- Verified: every cited path, symbol, fixture, CI command, and out-of-scope `disable_spy` caller list (`liveness.py`, `core.py`, `report/reproducibility.py`) resolves accurately against repository evidence. Also verified via `src/pubrun/__init__.py:530-559` and `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress:307-335` (plus a targeted subprocess probe) that bare `import pubrun.capture.git` triggers default auto-start and loads `pubrun.capture.subprocesses`, contradicting the original `E-02` item 3 and `V-01` limb (1) (`PR-001`, fixed).

### Step R2

- Checked: E/V bijection (`E-01`..`E-03` <-> `V-01`..`V-03`), `- Scope-Paths:` fence (all 3 files declared), `- Item-Dependencies: none`, execution contract in `## Approval and execution gate` (all 5 required elements present, including 2026-09-01 scope-fence wording and conditional runner/executor `aw ipd finalize` ownership), absence of hardcoded mutable-tree or collected-test counts, runtime-demonstration reachability for every `V-*` item, and right-sizing (3 E-items, 2 task groups, 3 files).
- Found and fixed: `V-01` limb (1) and `E-02` item 3 demanded `subprocesses_loaded=False` from a bare `import pubrun.capture.git` subprocess without `PUBRUN_IMPORT_MODE=minimal`, which is unreachable because `src/pubrun/__init__.py` auto-starts `pubrun` and imports `pubrun.capture.subprocesses` before `get_git` is called (`PR-001`).

### Step R3

- Checked: trust boundaries, subprocess invocation safety, `remote_url` redaction preservation, and `SubprocessSpy` bypass semantics.
- Verified: `_disable_spy_if_loaded()` performs a read-only `sys.modules` lookup and calls `disable_spy()` only when callable; `subprocess.run(["git"] + args, ...)` remains argument-list only (no shell), timeout-bounded, and `LC_ALL=C` / UTF-8 decoded; `remote_url` heuristic redaction in `src/pubrun/capture/git.py:179-180` is untouched; internal `git` capture calls remain bypassed whenever `SubprocessSpy` is loaded. Zero security or privacy findings.

### Step R4

- Checked: correctness, thread safety, anti-regression invariants, test rigor, KISS reuse of the existing `_SYS_MODULES` / `_disable_spy_if_loaded()` pattern from `hardware.py`, `filesystem.py`, and `resources.py`, per-item right-sizing, and `## Spec / documentation sync` truthfulness against `docs/architecture.md:246` and `docs/functional_spec.md:815`.
- Found and fixed:
  - `E-02` item 3 and `V-01` limb (1) omitted `PUBRUN_IMPORT_MODE=minimal` (and unsetting `PUBRUN_AUTO_START` / `PUBRUN_RUN_MODE_OVERRIDE`), causing root `pubrun/__init__.py` auto-start to load `pubrun.capture.subprocesses` before `get_git` ran (`PR-001`).
  - `E-02` item 1 omitted asserting `SubprocessSpy.install(owner=...) is True`, non-empty wrapped invocation count, post-call `_spy_bypassed() is False`, and checking `get_records()` before `uninstall()` clears `_records` (`PR-002`).
  - `E-03` omitted `assert not hw_thread.is_alive()` after `join(timeout=15)` (`PR-003`).
  - Verified `docs/architecture.md:246` and `docs/functional_spec.md:815` remain accurate without modification because active `SubprocessSpy` sessions still bypass internal `git` queries via `disable_spy()`.

### Step S5

- Checked: `## Open questions` contains `None.`. All three findings (`PR-001`, `PR-002`, `PR-003`) had `Low` overall Remediation Risk, were settled directly by repository evidence and a targeted subprocess probe, and were fixed in place. Zero open, deferred, or unfixed findings remain and zero irreversible decisions require human escalation. The lane outcome JSON carries `"questions": []`.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | IN-SCOPE | `r2-executability.md` G / `r4-engineering.md` E (unsatisfiable fresh-subprocess test & probe) | `.aw/records/plans/pending/20261127-ctx0hj-01-7a4bvr-avoid-importing-pubrun-capture-subprocesses-in-git-capture-w.ipd.md:70,135` vs `src/pubrun/__init__.py:530-559` and `src/pubrun/_bootstrap.py::is_mode_submodule_import_in_progress:307-335` | `E-02` item 3 and `V-01` limb (1) ran a fresh Python subprocess with only `PYTHONPATH=src` and bare `import pubrun.capture.git`, then asserted `"pubrun.capture.subprocesses" not in sys.modules`. Because `is_mode_submodule_import_in_progress()` only exempts the six mode submodules, importing `pubrun.capture.git` executes `pubrun/__init__.py::_execute_boot_sequence()` in default `auto` mode, which loads `pubrun.capture.subprocesses` in Step 5 before `get_git` runs (empirically confirmed: bare yields `True`, `PUBRUN_IMPORT_MODE=minimal` yields `False`). | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated `E-02` item 3, `## Proposed changes` item 2, and `V-01` limb (1) to set `PUBRUN_IMPORT_MODE=minimal` and unset `PUBRUN_AUTO_START` and `PUBRUN_RUN_MODE_OVERRIDE` alongside `PYTHONPATH=src`, and to assert `"pubrun.capture.subprocesses" not in sys.modules` both before and after calling `get_git` (recommendation strength: `very strong`). |
| PR-002 | LOW | IN-SCOPE | `r4-engineering.md` E (test rigor in `E-02` item 1) | `.aw/records/plans/pending/20261127-ctx0hj-01-7a4bvr-avoid-importing-pubrun-capture-subprocesses-in-git-capture-w.ipd.md:68` vs `src/pubrun/capture/subprocesses.py::SubprocessSpy.install:176-198` and `SubprocessSpy.uninstall:578-649` | `E-02` item 1 did not assert that `SubprocessSpy.install(owner=...)` returned `True`, that at least one wrapped `subprocess.run` invocation occurred, that `_spy_bypassed()` returned to `False` after `get_git` returned, or that `SubprocessSpy.get_records() == []` was checked before `uninstall()` cleared `_records`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Tightened `E-02` item 1 to require asserting `SubprocessSpy.install(owner=...)` returns `True`, at least one wrapped invocation ran with `_spy_bypassed() == True`, `_spy_bypassed()` is `False` after `get_git` returns, and zero records before `finally: SubprocessSpy.uninstall(owner=...)` (recommendation strength: `strong`). |
| PR-003 | LOW | IN-SCOPE | `p-proofread.md` / `technical-writing.md` Req 12(d) & `r4-engineering.md` E (diagram null-guard & `hw_thread` join check) | `.aw/records/plans/pending/20261127-ctx0hj-01-7a4bvr-avoid-importing-pubrun-capture-subprocesses-in-git-capture-w.ipd.md:37,79` vs `E-01` (`:54-55`) and `tests/test_import_modes.py::TestSpecProbeAndBackgroundImportLockSafety.test_nopatch_background_hw_does_not_load_subprocesses_module:1989-1992` | The `LOOKUP` flowchart node omitted the `modules is not None` null-guard required by `E-01`, and `E-03` joined `run._hardware_thread` with a 15-second timeout without asserting `not hw_thread.is_alive()` as the sibling `nopatch` test does. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Updated the `LOOKUP` flowchart node to include the `modules is not None` guard matching `E-01`, and added `assert not hw_thread.is_alive()` after `join(timeout=15)` in `E-03` (recommendation strength: `strong`). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Review tier for `7a4bvr` | `standard` | `simple`, `complex` | Modifies production startup capture code (`src/pubrun/capture/git.py::_run_git_raw`) interacting with `SubprocessSpy` bypass semantics on every tracked run, across 3 cohesive files (3 E-items, 2 task groups); no spec, public contract, or privacy/commit/sandbox guard changes (`steps/t-tier.md`). | yes |
| D-2 | How to isolate direct `get_git` fresh-subprocess checks (`E-02` item 3 and `V-01` limb 1) from root `pubrun/__init__.py` auto-start | Set `PUBRUN_IMPORT_MODE=minimal` and unset `PUBRUN_AUTO_START` and `PUBRUN_RUN_MODE_OVERRIDE` alongside `PYTHONPATH=src`, asserting `"pubrun.capture.subprocesses" not in sys.modules` before and after `get_git` | Leave bare `import pubrun.capture.git` (fails because `auto` mode installs `SubprocessSpy`) or import `pubrun.noauto` in-script | `src/pubrun/__init__.py:530-559`, `src/pubrun/_bootstrap.py:202-203,307-335`, and empirical probe confirming bare import yields `True` while `PUBRUN_IMPORT_MODE=minimal` yields `False`. | yes |
| D-3 | Whether to keep `_disable_spy_if_loaded()` local in `src/pubrun/capture/git.py` vs extract a shared utility module | Keep the 7-line `_SYS_MODULES` / `_disable_spy_if_loaded()` helper local in `src/pubrun/capture/git.py` | Extract a shared helper imported by `hardware.py`, `filesystem.py`, `resources.py`, and `git.py` | Backlog item `ctx0hj` explicitly specifies matching `hardware.py`, `filesystem.py`, and `resources.py` from IPD `3ed2o4`; keeping it local avoids cross-module import edges and blast radius into three untouched capture modules (`r4-engineering.md` F. KISS). | yes |

### Step S6

- Checked: no `E-*` or `V-*` items were added or removed; `- Scope-Paths:` and `- Item-Dependencies:` are unchanged; all three revisions (`PR-001`, `PR-002`, `PR-003`) were swept consistently across the Mermaid flowchart, `E-02`, `E-03`, `## Proposed changes`, and `V-01` with no remaining contradictions, open questions, or structural ambiguities. No second pass is needed.

AW-REVIEW: DONE
