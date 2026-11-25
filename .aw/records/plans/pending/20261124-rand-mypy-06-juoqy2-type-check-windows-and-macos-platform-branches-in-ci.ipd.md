# IPD: Type-check Windows and macOS platform branches in CI

- Date: 2026-11-24
- Kind: child
- Concern: Static type checking: `mypy` checks one target platform per run, and plan `gzc672`'s `typecheck` job runs only the Linux check, so a type error inside a Windows-only or macOS-only branch never fails CI. Running `mypy --platform win32` today reports 10 errors, all calls to POSIX-only `os` functions.
- Scope: Platform guards in `src/pubrun/capture/liveness.py`, `resources.py`, `system_metrics.py`, and `subprocesses.py`; a new `tests/test_platform_type_guards.py`; two more `mypy` steps in the `typecheck` job of `.github/workflows/ci.yml`; and the contributor documentation (`CONTRIBUTING.md`, `CHANGELOG.md`).
- Scope-Paths: src/pubrun/capture/liveness.py, src/pubrun/capture/resources.py, src/pubrun/capture/system_metrics.py, src/pubrun/capture/subprocesses.py, tests/test_platform_type_guards.py, .github/workflows/ci.yml, CONTRIBUTING.md, CHANGELOG.md
- Item-Dependencies: executed:gzc672, executed:m66tfv, executed:k6fs5k, executed:0uxy76
- Status: to-review
- Short-Description: Fix POSIX-only mypy errors reported under --platform win32 and add win32 and darwin mypy runs to the typecheck job
- Work-Kind: chore
- Priority: low
- From-Backlog: qqwebg
- Set: rand-mypy
- Order: 6
- Highest E allocated: 04
- Author: uri/its_direct/pt3-claude-opus-5.5-1m-us
- Id: juoqy2

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 to-review (aw set): authored from backlog qqwebg
- 2026-11-24 draft (uri/its_direct/pt3-claude-opus-5.5-1m-us): created.

## Goal

Make `mypy --platform win32` and `mypy --platform darwin` exit 0 on the package, and add both runs to the blocking `typecheck` CI job, so type errors in Windows and macOS code paths fail CI the same way Linux ones do. Runtime behavior on every platform stays the same.

`mypy --platform <p>` type-checks the code as if it ran on platform `<p>`: it uses that platform's standard-library stubs (Windows has no `os.sysconf`, `os.getloadavg`, or `os.WIFEXITED`) and treats `if sys.platform == "<other>":` branches as unreachable. It runs on any host, so the CI job can stay on `ubuntu-latest`.

### Platform guards and CI runs

```mermaid
flowchart TD
    A["0uxy76 executed: mypy on Linux exits 0 with no override"] --> B["E-01: _sysconf helper in liveness.py and resources.py"]
    A --> C["E-02: win32 early returns in system_metrics.py and subprocesses.py"]
    B --> D["E-03: tests for the helper and the guards"]
    C --> D
    D --> E{"mypy --platform win32 and darwin exit 0?"}
    E -->|yes| F["E-04: add both runs to the typecheck job, document them"]
    E -->|no| G["Guard the reported call; do not add an ignore"]
    G --> E
```

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: write for a modest executor that cannot hold much in its head. Each E-item is one step (one concern, about one file, executable in one focused pass) and its V-item names each unit it covers with its own check; a plan stays at about 5 E-items and 8 work Scope-Paths, else split it into more child plans (guidance, `IPD-Z603`). Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Fix the Windows-only errors

- [ ] E-01 Route the five `os.sysconf` calls through a module-level helper in `src/pubrun/capture/liveness.py` and `src/pubrun/capture/resources.py`. In each file, add this function after the module-level constants that follow the imports (`liveness.py`: after `_PLATFORM = sys.platform`; `resources.py`: after `logger = logging.getLogger("pubrun")`):
  ```python
  def _sysconf(name: str) -> int:
      """Return ``os.sysconf(name)``; raises ``AttributeError`` where ``os.sysconf`` is absent (Windows)."""
      return int(getattr(os, "sysconf")(name))
  ```
  Then replace `os.sysconf(` with `_sysconf(` in `liveness._get_start_time_linux`, `liveness._get_cpu_linux`, `resources._get_rss_linux`, `resources._get_tree_rss_linux`, and `resources.ResourceWatcher.__init__` (the `self._clk_tck = os.sysconf("SC_CLK_TCK")` line). Every call site already sits in a `try` that catches `AttributeError` or `Exception`, so on Windows the helper fails exactly as `os.sysconf` did. The attribute is looked up at call time, so `tests/test_liveness.py`'s `monkeypatch.setattr(liveness.os, "sysconf", ...)` keeps working.
  - Depends on: none
  - Expected outcome: `grep -n "os.sysconf" src/pubrun/capture/liveness.py src/pubrun/capture/resources.py` finds only the line inside each `_sysconf` docstring. `python3 -m pytest tests/test_liveness.py tests/test_resources.py -q` passes.
  - Execution state: pending

- [ ] E-02 Add early returns that `mypy` recognizes as platform checks:
  - `system_metrics.get_load_average`: insert `if sys.platform == "win32":` / `return None` as the first statement after the docstring. On Windows `os.getloadavg` does not exist, so the existing `except (OSError, AttributeError)` already returned `None`; the guard returns the same value without the failed call and its debug log line.
  - `subprocesses._decode_wait_status`: insert `if sys.platform == "win32":` / `return status` immediately after the comment `# Python 3.8 fallback.` and before its `try:`. That point is reachable only when `os.name == "posix"`, which is never true on Windows, so the guard changes no result.
  - `sys` is already imported in both modules.
  - Depends on: none
  - Expected outcome: The diff of the two files is the two guards. `python3 -m pytest tests/test_env_capture.py tests/test_capture_engine_bugs.py tests/test_platform_capture_seams.py -q` passes.
  - Execution state: pending

- [ ] E-03 Create `tests/test_platform_type_guards.py` with these behavioral tests (7 test cases):
  - `test_get_load_average_is_none_on_windows_without_calling_getloadavg`: monkeypatches `sys.platform` to `"win32"` and `os.getloadavg` to a function that records each call and returns `(1.0, 2.0, 3.0)` (`raising=False`); asserts `system_metrics.get_load_average()` is `None` and the recorder saw no call.
  - `test_decode_wait_status_returns_raw_status_on_windows`: monkeypatches `sys.platform` to `"win32"` and deletes `os.waitstatus_to_exitcode` (`raising=False`) so the Python 3.8 fallback is reached; asserts `subprocesses._decode_wait_status(256) == 256` (the fallback would decode it to `1`).
  - `test_sysconf_helper_raises_attribute_error_without_os_sysconf`, parametrized over `liveness` and `resources`: deletes `os.sysconf` (`raising=False`) and asserts `module._sysconf("SC_CLK_TCK")` raises `AttributeError` matching `"module 'os' has no attribute 'sysconf'"`.
  - `test_sysconf_helper_returns_int_from_os_sysconf`, parametrized over `liveness` and `resources`: monkeypatches `os.sysconf` to return `4096` for `"SC_PAGE_SIZE"` (`raising=False`) and asserts `module._sysconf("SC_PAGE_SIZE") == 4096`.
  - `test_resource_watcher_clock_ticks_zero_without_os_sysconf`: deletes `os.sysconf` and asserts `resources.ResourceWatcher(run_tracker=None, interval_seconds=1.0, system_metrics=False)._clk_tck == 0`.
  - Depends on: E-01, E-02
  - Expected outcome: All 7 pass on Linux, macOS, and Windows (each test sets the platform state it needs). Removing either guard of E-02 fails its test (V-03).
  - Execution state: pending

### Task group 2: Gate the platforms in CI

- [ ] E-04 Extend the `typecheck` job that plan `gzc672` E-04 added to `.github/workflows/ci.yml`: after its `mypy` step, add two steps, `mypy --platform win32` and `mypy --platform darwin`, each with a `name:` that states the platform (for example `Type-check (Windows platform)`). Add no `continue-on-error`. Change no other job. Then document them: in `CONTRIBUTING.md` "Development setup", in the `mypy` paragraph, add the two commands to the code block and say that CI runs all three. In `CHANGELOG.md` `## [Unreleased]`, extend the `### Changed` entry that child `0uxy76` added (or add one) to say that CI also type-checks the Windows and macOS code paths. Follow the `AGENTS.md` dash rule: no em or en dashes in the added prose.
  - Depends on: E-03
  - Expected outcome: `python3 -c "import yaml; j=yaml.safe_load(open('.github/workflows/ci.yml'))['jobs']['typecheck']; print([s.get('run') for s in j['steps'] if 'run' in s])"` lists `mypy`, `mypy --platform win32`, and `mypy --platform darwin`; each of the three commands, run locally after deleting `.mypy_cache/`, prints `Success: no issues found in 58 source files`.
  - Execution state: pending

## Project conventions discovered (Step 0)

- Plan `gzc672` (status `approved`, not yet executed at authoring) E-04 adds the `typecheck` job (`ubuntu-latest`, Python 3.12, `pip install -e ".[dev,tui]"`, `mypy --version`, `mypy`) and records why it checks only Linux: at its review, `mypy --platform win32` reported 7 POSIX-only errors and `--platform darwin` none. `gzc672`'s "Deferred / out of scope" section assigns the platform guards to this burn-down. This plan edits that job, hence `Item-Dependencies: executed:gzc672`.
- The count is 10 at lane HEAD, not 7: `gzc672` measured with `capture/resources.py` on its `ignore_errors` list, which hid that module's 3 `os.sysconf` calls. Child `k6fs5k` removes `resources.py` from the list; this plan must therefore run after it.
- Child `0uxy76` edits the same `CONTRIBUTING.md` paragraph and `CHANGELOG.md` entry; this plan runs after it so the two edits apply in sequence.
- `mypy` treats `if sys.platform == "win32": return ...` as a platform check and skips the rest of the function only under `--platform win32`. It does not understand `getattr(os, "sysconf")`'s absence, which is why E-01 uses a helper rather than a guard: the Linux-only callers already catch the failure at runtime.
- `tests/test_liveness.py` monkeypatches `liveness.os.sysconf` with `raising=False` to simulate Linux on other hosts; the new tests follow the same pattern.

## Findings

| ID | Severity | Remediation Risk | Evidence | Finding |
|---|---|---|---|---|
| M-13 | Low | Low | `mypy --platform win32` with every earlier edit in this Set applied: `liveness._get_start_time_linux` and `liveness._get_cpu_linux`: `Module has no attribute "sysconf"  [attr-defined]`; `resources._get_rss_linux`, `resources._get_tree_rss_linux`, `ResourceWatcher.__init__`: the same (3); `system_metrics.get_load_average`: `Module has no attribute "getloadavg"`; `subprocesses._decode_wait_status`: `Module has no attribute "WIFEXITED"`, `"WEXITSTATUS"`, `"WIFSIGNALED"`, `"WTERMSIG"`; total `Found 10 errors in 4 files` | Windows paths are not type-checked, and the Windows view of the package has 10 errors. |
| M-14 | Low | Low | `mypy --platform darwin` on the same tree: `Success: no issues found in 58 source files` | macOS is clean today but is not gated, so a later regression would go unnoticed. |

Authoring measurements (lane HEAD `a4b7d12`, `mypy` 2.3.1, Python 3.14.6, Linux host), on a scratch tree with `gzc672`'s fixes and every edit in this Set:

- Before this plan's edits: Linux and darwin `Success: no issues found in 58 source files`; win32 `Found 10 errors in 4 files`. After them: all three print `Success: no issues found in 58 source files`.
- E-03 prototype: 7 passed, also in 3 runs under `-p randomly`. On the tree without this plan's edits, 6 of the 7 failed (the four `_sysconf` cases because the helper does not exist; the load-average and wait-status cases because the call is made). The clock-ticks case passed there too, because `ResourceWatcher.__init__` already caught `AttributeError`; it pins that the helper keeps that behavior.
- `python3 -m pytest tests/test_liveness.py tests/test_resources.py tests/test_env_capture.py tests/test_platform_capture_seams.py tests/test_capture_engine_bugs.py -q` on the edited tree: `137 passed`.

## Proposed changes (ordered, validatable)

1. Add `_sysconf` helpers and use them at the five Linux-only call sites (E-01; Remediation Risk: Low).
2. Add Windows early returns in `get_load_average` and `_decode_wait_status` (E-02; Remediation Risk: Low).
3. Add tests for the helper and the guards (E-03; Remediation Risk: Low).
4. Add `--platform win32` and `--platform darwin` steps to the `typecheck` job and document them (E-04; Remediation Risk: Low).

Rejected alternatives:

- A Windows or macOS runner for the `typecheck` job: `--platform` gives the same check from the existing Linux runner without extra runner minutes.
- `# type: ignore[attr-defined]` on the 10 calls: it would also hide a misspelled `os` attribute on Linux, where the ignore applies too.
- `if sys.platform != "win32":` guards around each `os.sysconf` call: the callers are Linux-only functions already wrapped in `try`, and five nested guards add indentation for no runtime effect; one helper per module is smaller.

## Deferred / out of scope (with reason)

- Pinning the `mypy` version in CI: deferred by `gzc672` (it would change the `dev` extra contract).
  - Carrier-Declined: Deliberate non-goal (changing the dev extra contract was deferred by gzc672).
- Type-checking with a target Python version other than the runner's: `mypy` 2.x refuses `--python-version` below 3.10, and the project supports 3.8 (`gzc672` Project conventions).
  - Carrier-Declined: External tool limitation (mypy 2.x refuses --python-version below 3.10).

## Scope check

- Over-scope: none. The new test file covers only the helper and the guards this plan adds.
- Under-scope: none. The CI change cannot be observed until it is pushed; V-04 records that as a human-authorized step.

## Required tests / validation

- `rm -rf .mypy_cache && for p in linux win32 darwin; do mypy --platform $p; echo "$p exit=$?"; done`: three `Success` lines and `exit=0` each.
- Mutation checks, each restored before the next: delete the E-02 guard in `system_metrics.get_load_average`, then run `mypy --platform win32` (expect an `error:` line for `system_metrics.py`) and `python3 -m pytest tests/test_platform_type_guards.py -q` (expect `test_get_load_average_is_none_on_windows_without_calling_getloadavg` to fail). Repeat for the guard in `subprocesses._decode_wait_status` (expect `subprocesses.py` errors and `test_decode_wait_status_returns_raw_status_on_windows` to fail).
- `python3 -m pytest tests/test_platform_type_guards.py tests/test_liveness.py tests/test_resources.py tests/test_env_capture.py tests/test_platform_capture_seams.py tests/test_capture_engine_bugs.py -q`: exit 0.
- `python3 scripts/sanitize_paths.py --check --all`: exit 0.

## Spec / documentation sync

- No `.spec.md` under `.aw/records/specs/` and no file under `docs/` mentions `mypy` (checked at authoring with `grep -rln "randomly\|mypy" .aw/records/specs docs`: no match). No spec is amended.
- `CONTRIBUTING.md` and `CHANGELOG.md` are updated by E-04.

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'. Runtime-demonstration reachability rule: for each `V-*` item demanding the software be observed acting (such as a run, a dispatch, or a transition), as distinct from items demanding a diff, a file's content, or a test result, which are reachable by construction, name the code path that produces the observation or the sibling `E-*` that creates it, else the demand is UNDER-SCOPE.

- [ ] V-01 validates E-01
  - Required evidence: Pasted `git diff src/pubrun/capture/liveness.py src/pubrun/capture/resources.py` showing the two helpers and the five replaced calls and nothing else; pasted `grep -n "os.sysconf" src/pubrun/capture/liveness.py src/pubrun/capture/resources.py` showing only the docstring lines; and the last line of `python3 -m pytest tests/test_liveness.py tests/test_resources.py -q` showing all passed.
  - Observed evidence:
  - Result: pending

- [ ] V-02 validates E-02
  - Required evidence: Pasted `git diff src/pubrun/capture/system_metrics.py src/pubrun/capture/subprocesses.py` showing only the two guards; and the last line of `python3 -m pytest tests/test_env_capture.py tests/test_capture_engine_bugs.py tests/test_platform_capture_seams.py -q` showing all passed.
  - Observed evidence:
  - Result: pending

- [ ] V-03 validates E-03
  - Required evidence: (1) Pasted content of `tests/test_platform_type_guards.py`. (2) The last line of `python3 -m pytest tests/test_platform_type_guards.py -q` showing `7 passed`. (3) Pasted output of the two mutation checks in "Required tests / validation", each showing the `mypy --platform win32` `error:` line for the mutated file and the named `FAILED` test, then `git diff --stat src/pubrun` after the last restore showing only E-01 and E-02 files.
  - Observed evidence:
  - Result: pending

- [ ] V-04 validates E-04
  - Required evidence: (1) Pasted `git diff .github/workflows/ci.yml CONTRIBUTING.md CHANGELOG.md`. (2) Pasted output of the `yaml.safe_load` command from E-04 listing the three `mypy` commands. (3) Pasted output of the three-platform `mypy` loop from "Required tests / validation" with three `Success` lines and `exit=0` each. (4) Pasted output of `git diff -U0 CONTRIBUTING.md CHANGELOG.md | grep "^+" | grep -nP "[\x{2013}\x{2014}]"; echo "exit=$?"` showing `exit=1`. (5) After a human-authorized push, the CI run URL and the `typecheck` job log lines for the two new steps showing `Success: no issues found in 58 source files`; if no push is authorized, mark this item `blocked` with that reason. This observation is produced by the GitHub Actions run of the job E-04 edits.
  - Observed evidence:
  - Result: pending

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question, and for plans `gzc672`, `m66tfv`, `k6fs5k`, and `0uxy76` to be `executed`, before you change any file.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries. If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit juoqy2 -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize juoqy2`, never with a hand-written `git mv`. Outside a runner, run it after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
