# IPD: Capture security and provenance tests for invocation, redaction, and file I/O

- Date: 2026-11-23
- Kind: child
- Concern: Testing rigor and completeness for the capture code that guards secrets and records provenance (`invocation.py`, `redaction.py`, `file_io.py`, the `core.py` and capture-engine fallbacks), plus the silent TOML skip in `test_sanitize_paths.py`. Review found four production defects on these paths; this plan fixes each one with a test that fails before the fix.
- Scope: `src/pubrun/capture/invocation.py`, `src/pubrun/capture/redaction.py`, `src/pubrun/core.py`, `tests/test_invocation.py`, `tests/test_redaction.py`, `tests/test_file_io_provenance.py`, `tests/test_explicit_api.py`, `tests/test_capture_fallbacks.py`, `tests/test_sanitize_paths.py`, `docs/manifest.md`, and `CHANGELOG.md`.
- Scope-Paths: src/pubrun/capture/invocation.py, src/pubrun/capture/redaction.py, src/pubrun/core.py, tests/test_invocation.py, tests/test_redaction.py, tests/test_file_io_provenance.py, tests/test_explicit_api.py, tests/test_capture_fallbacks.py, tests/test_sanitize_paths.py, docs/manifest.md, CHANGELOG.md
- Item-Dependencies: none
- Status: approved
- Readiness: go-pending-approval
- Review-Depth: complex
- Short-Description: Fix four secret and capture defects in invocation, redaction, and phase profiling, and add behavioral tests for invocation, redaction, file I/O, and fallbacks
- Work-Kind: bug
- Priority: high
- Set: test-audit
- Order: 5
- Highest E allocated: 05
- Author: Antigravity
- Id: 2mwjjw
- Approval: 2026-11-24, recorded via aw ipd set: status set to approved

> Write and proofread this plan per the technical writing standard, `.aw/system/workflows/technical-writing/technical-writing.md` (`.agents/workflows/technical-writing/technical-writing.md` in a legacy-layout install), including requirement 12 (diagrams).

## Workflow history

- 2026-11-24 approved (aw set): status set to approved
- 2026-11-23 /plan-review (uri/its_direct/pt3-claude-opus-5.5-1m-us): APPROVE WITH REVISIONS APPLIED; PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-007, PR-008, PR-009, PR-010, PR-011, PR-012
- 2026-11-23 to-review (Antigravity): authored from `/assess-testing` findings T-08 (`test_sanitize_paths.py`), T-10, T-11, and T-12.
- 2026-11-23 draft (Antigravity): created.

## Goal

Every capture path named below gets a test that fails when its behavior breaks. Review found that four of these paths are broken today:

1. A file path given as the value of a secret flag (for example `--key-file id_rsa`) is written to `manifest.json` under `invocation.inputs`, with its resolved path and, when `compute_md5` is on, its MD5 digest. `invocation.argv` and `invocation.command_line` show `[REDACTED]` for the same value, because input discovery in `get_invocation` scans the raw `sys.argv`.
2. An OpenAI key in the current hyphenated format (`sk-proj-...`) inside a non-secret environment variable value or argument value is not redacted. The value heuristic `sk-[a-zA-Z0-9]{20,}` stops at the first hyphen.
3. A `pathlib.Path` object in `sys.argv` makes the whole `invocation` section fail (`capture_state.status == "failed"`, `TypeError`). The cause is a dead block in `get_invocation` that calls `shlex.join` on the raw argv before redaction, which stringifies every entry.
4. An unknown `[capture.profiling].backend` value silently disables profiling. `docs/configuration.md` promises "If the selected backend is unavailable, logs a warning and skips"; `phase.__enter__` has no branch for an unknown name.

The E-items edit disjoint files. E-01 runs after E-02: `get_invocation` builds its output from `redact_argv`, and one E-01 test needs E-02's change that makes `redact_argv` return strings. E-03, E-04, and E-05 are independent.

## Detailed Implementation Checklist (TODO)

Execution-state rule: mark an `E-*` item complete only after performing the action. That mark is not validation. Right-sizing rule: each E-item addresses one concern executable in one focused pass. Accepted execution states: blocked, failed, pending, performed; terminal gate demands 'performed'.

### Task group 1: Invocation fixes and behavioral tests

- [x] E-01 Fix `src/pubrun/capture/invocation.py:get_invocation` and create `tests/test_invocation.py`.
  - Production changes, in this order inside the `try:` block of `get_invocation`:
    (a) Delete the whole "3. Re-run Replication Engine" block (the first `if sys.platform == "win32":` ... `rerun_command = f"cd {shlex.quote(str(cwd))} && python {escaped_args}"`). Nothing reads its `rerun_command`; the later "Rebuild command_line and rerun_command from redacted argv" block overwrites it.
    (b) Move the two lines `from pubrun.capture.redaction import redact_argv` and `redacted_argv = redact_argv(argv, config)` from just above "Rebuild command_line and rerun_command from redacted argv" to just above `inputs_data = []`.
    (c) Change the discovery loop header from `for idx, arg in enumerate(argv[1:], start=1):` to `for idx, arg in enumerate((str(a) for a in argv[1:]), start=1):`.
    (d) Directly after the `if arg.startswith("-") or arg.startswith("--"): continue` check, add `if redacted_argv[idx] != arg: continue` with the comment `# A value redaction removed from argv must not reappear here.`
  - Do not add internal helpers such as `_inspect_script` or `_discover_argv_inputs`; the refactor is dropped (PR-008).
  - New file `tests/test_invocation.py`. Use a fixture `argv(monkeypatch)` that sets `sys.argv` through `monkeypatch.setattr`. The autouse `tests/conftest.py:isolated_cwd` fixture already changes into `tmp_path`, so relative names resolve there. Required tests, each asserting the exact value shown:
    - `entrypoint_type`: an existing file gives `"script"`; parametrized `"-m"` gives `"module"`, `"-c"` and `""` give `"interactive"`, a missing `"does_not_exist.py"` gives `"unknown"` with `script == {}`; empty `sys.argv` gives `"interactive"`, `argv == []`, and `capture_state.status == "complete"`.
    - Script hashing: a small script's `sha256` equals `hashlib.sha256(body).hexdigest()` and `size == len(body)`; a script of exactly 1,048,576 bytes is hashed; a script of 1,048,577 bytes has no `sha256` and `sha256_skipped == "file exceeds 1MB"`.
    - Input discovery: `["s.py", "data.csv", "ds", "missing.csv"]` records exactly `(arg_index, path, is_dir)` `(1, "data.csv", False)` and `(2, "ds", True)`, with `size` and `real_path`, and no `md5`; `capture.inputs.enabled = False` gives `[]`; a file named `-v` and a directory named `--out` are not recorded; `ignore_extensions = ["Log"]` skips `a.LOG`; `compute_md5 = True` records the file's MD5, records no `md5` for a directory, and logs exactly one warning, `"Computing MD5 for sys.argv[1] (d.bin). This may cause startup latency."`.
    - Command formatting: with `sys.platform` patched to `"linux"` and argv `["s.py", "--password", "hunter2", "my file.csv"]`, `argv` is `["s.py", "--password", "[REDACTED]", "my file.csv"]`, `command_line == shlex.join(argv)`, `rerun_command == f"cd {shlex.quote(str(Path.cwd()))} && python {shlex.join(argv)}"`, and `"hunter2"` appears in neither. With `sys.platform` patched to `"win32"`, `command_line == subprocess.list2cmdline(redacted)` and `rerun_command == f"cd {subprocess.list2cmdline([str(Path.cwd())])}\npython {subprocess.list2cmdline(redacted)}"`.
    - Non-string argv (defect 3): `["s.py", Path("data.csv"), "--lr=0.1"]` gives `capture_state == {"status": "complete"}` and `command_line == "s.py data.csv --lr=0.1"`; the same with `{"redaction": {"argv_enabled": False}}` and an existing `data.csv` also completes and records `data.csv` as an input.
    - Redacted value not an input (defect 1): with `creds.json` and `data.csv` present, argv `["s.py", "--credentials", "creds.json", "data.csv"]` and `compute_md5 = True`, the input paths are exactly `["data.csv"]`, `"creds.json"` is absent from `repr(result)`, and absent from `caplog.text` captured at `DEBUG` on the `pubrun` logger. With `{"redaction": {"argv_enabled": False}}`, `creds.json` is recorded.
  - Ordering: execute after E-02, because the `argv_enabled = False` test needs `redact_argv` to return strings.
  - Depends on: E-02
  - Expected outcome: The dead block is gone, redacted values never reach `invocation.inputs` or the log, a `Path` in `sys.argv` no longer fails capture, and every `get_invocation` branch listed above has a test.
  - Execution state: performed

### Task group 2: Redaction fixes and tests

- [x] E-02 Fix `src/pubrun/capture/redaction.py` and add a `TestValueHeuristics` class to `tests/test_redaction.py`.
  - Production changes:
    (a) Above `def _redact_value_string_heuristics(`, add the module constant `_PREFIXED_KEY_VALUE_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")` with a one-line comment that it covers hyphenated prefixed keys such as `sk-proj-...`. In `_redact_value_string_heuristics`, directly after `val = openai_pattern.sub("[REDACTED]", val)`, add `val = _PREFIXED_KEY_VALUE_RE.sub("[REDACTED]", val)`. Keep the existing `openai_pattern` line: removing it would change what an unanchored match such as `desk-<20 letters>` redacts today (PR-005).
    (b) In `redact_argv`, change the `argv_enabled = False` early return from `return list(argv)` to `return [str(arg) for arg in argv]`, so the function returns strings on both paths.
  - Add `import json` to the test module. Build every fake key by concatenation (`"sk-" + "proj-..."`), as `tests/test_capture_isolation.py` does, because the `gitleaks` pre-commit hook rejects a literal key. Required tests, using a helper that maps `redact_env_vars(env)` to `{name: value}`:
    - A JSON object in a non-secret env value (`APP_CONFIG`) with `api_key`, nested `password`, and a list holding `{"token": 7}` and `"plain"` decodes to the same structure with each secret-key value `"[REDACTED]"`, the plain string kept, and `"n": 3` kept; `representation == "plain"`.
    - A JSON array argv value `["sk-" + "a" * 24, {"secret": "s"}, 1.5, None]` decodes to `["[REDACTED]", {"secret": "[REDACTED]"}, 1.5, None]`.
    - Invalid JSON `"{not json: postgres://u:pw@db/x Bearer abc.def}"` becomes `"{not json: postgres://u:[REDACTED]@db/x Bearer [REDACTED]}"`.
    - `"use sk-" + "A1" * 12 + " today"` becomes `"use [REDACTED] today"`; an `Authorization: Bearer <jwt>` value ends with `"Bearer [REDACTED]"` and no longer contains the token.
    - `redact_argv(["s.py", "https://ghp_abc123@github.com/o/r.git"])` gives `["s.py", "https://[REDACTED]@github.com/o/r.git"]`; `["s.py", "--db=postgres://u:pw@h/db", "--note=sk-" + "b" * 22]` gives `["s.py", "--db=postgres://u:[REDACTED]@h/db", "--note=[REDACTED]"]`.
    - `redact_argv(["s.py", Path("data") / "x.csv", 3, "--password", Path("pw.txt")])` gives `["s.py", str(Path("data") / "x.csv"), "3", "--password", "[REDACTED]"]`.
    - Defect 2: with `key = "sk-" + "proj-abc123_def456-7890xyzABC"`, the env value `f"key {key} end"` becomes `"key [REDACTED] end"`, a JSON argv value `{"openai": key}` decodes to `{"openai": "[REDACTED]"}`, and a bare positional `key` becomes `"[REDACTED]"`.
    - False-positive guard: `"task-runner sk-short sk-proj-tiny"` is unchanged.
  - Depends on: none
  - Expected outcome: Hyphenated `sk-` keys are redacted in env and argv values, `redact_argv` always returns strings, and the JSON-in-string, URI, bearer, and flag-value paths of `_redact_value_string_heuristics`, `_redact_dict_keys`, and `_redact_any` each have a test.
  - Execution state: performed

### Task group 3: File I/O proxy edge methods and budget recovery

- [x] E-03 Add a `TestProxyEdgeMethods` class to `tests/test_file_io_provenance.py`, using the module's helper `_run_with_file_io(tmp_path, file_io_cfg, fn)` with `{"level": "hash"}`. No production change.
  - Two `pubrun.open` calls on the same path merge into one record, so every case below that needs two records uses two files and selects records by `Path(r["path"]).name`.
  - Required tests:
    - `read1(16)` in a loop over 100 bytes: `eof_reached is True`, `bytes_read == 100`, `hash_status == "completed"`, `observation_time == "during_stream"`, and `sha256` matches.
    - `readinto1` into a 100-byte buffer over 768 bytes: `eof_reached is True`, `observation_time == "during_stream"`, `hash_stats.extra_read_bytes == 0`, and `sha256` matches.
    - Binary `readlines(1)` on `partial.bin` (`b"a\nb\nc\n"`) returns `[b"a\n"]` and gives `eof_reached is False`, `bytes_read == 2`, `observation_time == "at_close"`, `extra_read_bytes == 6`; `readlines()` on `full.bin` gives `eof_reached is True` and `observation_time == "during_stream"`; both `sha256` values match the full payload.
    - With `max_hash_bytes = 10`, writing 20 bytes and then `truncate(5)` gives `access_observations.truncate_used is True`, `hash_status == "completed"`, `observation_time == "at_close"`, and `sha256 == hashlib.sha256(b"x" * 5).hexdigest()`. The control case, 20 bytes with no truncate, gives `hash_status == "over_budget"` and `sha256 is None`.
    - `pubrun.open(p, "xb")` writes `b"exclusive\n"`; a second `pubrun.open(p, "xb")` raises `FileExistsError`; the manifest has exactly one output with `open_disposition == "exclusive_create"`, `hash_status == "completed"`, `observation_time == "during_stream"`, and a matching `sha256`.
  - Depends on: none
  - Expected outcome: `ProvenanceFileProxy.read1`, `readinto1`, `readlines`, and `truncate`, and the `xb` mode, each have a test that fails under the mutations listed in V-03.
  - Execution state: performed

### Task group 4: Core and capture fallbacks, and the sanitizer TOML assertion

- [x] E-04 Add the unknown-backend branch to `src/pubrun/core.py:phase.__enter__`, add report, artifact, and phase tests to `tests/test_explicit_api.py`, and create `tests/test_capture_fallbacks.py`.
  - Production change (defect 4): in `phase.__enter__`, after the `elif backend == "yappi":` branch and inside the same `try:`, add `else: raise ValueError("unknown backend")`. The existing `except Exception as prof_err:` then logs `pubrun: profiling backend '<name>' unavailable: unknown backend`, as `docs/configuration.md` `[capture.profiling]` already promises.
  - `tests/test_explicit_api.py`: add an `active_run(monkeypatch)` fixture that clears `pubrun.tracker._active_run`, sets `pubrun.phase._yappi_active` to `False` through `monkeypatch.setattr(..., raising=False)` (the attribute exists only after first use, so monkeypatch must restore its absence), starts runs with `console={"capture_mode": "off"}`, and stops any active run on teardown. Do not patch `Path.cwd`: `isolated_cwd` already changes into `tmp_path`. Required tests:
    - With `.pubrun.toml` setting `[events] on_inactive_annotate = "error"` and no active run, both `pubrun.report("r", {"a": 1})` and `pubrun.artifact("a.txt", "x")` raise `RuntimeError` matching `"no run is active"`.
    - `pubrun.report("rows", [1, 2, 3])` writes `rows.json` and the `annotation` event named `"report: rows"` has payload `{"filename": "rows.json", "summary": {"items": 3}}`. Events carry `name` and `payload`, not `message` and `data`.
    - With `Path.write_text` patched inside `monkeypatch.context()` to raise `OSError("disk full")`, `report` and `artifact` do not raise and log `"pubrun: failed to write report 'r': disk full"` and `"pubrun: failed to write artifact 'a.txt': disk full"`.
    - yappi is not installed, so insert a fake `yappi` module with `monkeypatch.setitem(sys.modules, "yappi", fake)` whose `start`, `stop`, `clear_stats`, and `get_func_stats().save` record calls. A phase nested inside another yappi phase logs `"pubrun: yappi already active (nested/concurrent phase); skipping profiling for phase 'inner'"`, the calls are exactly `["start", "stop", "save", "clear"]`, `profile-outer.prof` exists, `profile-inner.prof` does not, and `phase._yappi_active` is `True` inside and `False` after.
    - `monkeypatch.setitem(sys.modules, "yappi", None)` makes the import fail: a warning starting `"pubrun: profiling backend 'yappi' unavailable:"` is logged and no `profile-*.prof` file exists.
    - Backend `"pyinstrument"` logs exactly `"pubrun: profiling backend 'pyinstrument' unavailable: unknown backend"` and writes no profile file.
  - New file `tests/test_capture_fallbacks.py` (kept out of `tests/test_capture_engines.py`, which sibling `g18xdt` edits). Required tests:
    - `src/pubrun/capture/process.py:get_process_info`: `getpass.getuser` raising `OSError` gives `user.username == {"representation": "plain", "value": "unknown"}` and `capture_state.status == "complete"`; with `os.getuid` and `os.getgid` deleted (`raising=False`), `uid` and `gid` are `None`.
    - `src/pubrun/capture/host.py:get_host`: `platform.node` returning `""` falls back to `socket.gethostname()`; `platform.system` raising `RuntimeError("uname broke")` returns exactly `{"capture_state": {"status": "failed", "detail": "uname broke"}}`.
    - `src/pubrun/capture/python_runtime.py:environment_kind`, with a `plain_env` fixture that sets `sys.prefix` and `sys.base_prefix` to `tmp_path`, sets `sys.executable` to a fixed path containing no `pyenv` text (`os.path.join(os.sep, "opt", "py", "bin", "python")`; a `tmp_path`-based path contains the test name and so matches `pyenv` in `test_pyenv_version_env_var`), and removes `real_prefix`, `frozen`, `CONDA_PREFIX`, and `PYENV_VERSION`: plain gives `"system"` and `pyenv is False`; a `conda-meta` directory gives `"conda"`; `sys.real_prefix` gives `"virtualenv"`; `sys.frozen` plus `conda-meta` gives `"frozen"`; `PYENV_VERSION` gives `pyenv is True` with kind `"system"`; `os.path.isdir` raising `OSError` still gives `"system"`.
  - Depends on: none
  - Expected outcome: An unknown backend logs the documented warning, and each fallback listed above has a test that fails under the mutations listed in V-04.
  - Execution state: performed

- [x] E-05 In `tests/test_sanitize_paths.py:test_config_toggles_ip_and_lists`, replace `if sp._toml is None: pytest.skip("no TOML parser available")` with `assert sp._toml is not None, "tomllib/tomli is a declared dependency and must import"`.
  - Depends on: none
  - Expected outcome: A broken TOML import in `scripts/sanitize_paths.py` fails the test instead of skipping it.
  - Execution state: performed

## Project conventions discovered (Step 0)

- Coverage at lane HEAD `dbe4ac5` (full suite, `1902 passed, 2 skipped`): `invocation.py` 70%, `python_runtime.py` 78%, `host.py` 82%, `process.py` 86%, `redaction.py` 94% (missed lines in `_redact_dict_keys`, `_redact_any`, and the JSON branch of `_redact_value_string_heuristics`), `file_io.py` 82% (`ProvenanceFileProxy.read1`, `readlines`, `readinto1`, and `truncate` bodies uncovered), `core.py` 85%. With this plan prototyped at review: `invocation.py` 90%, `python_runtime.py` 94%, `host.py` 100%, `process.py` 100%, `redaction.py` 96%, `file_io.py` 85%, `core.py` 87%.
- `pyproject.toml` lists `tomli>=1.1.0; python_version < '3.11'` in `[project] dependencies`, and Python 3.11 and later ship `tomllib`, so `scripts/sanitize_paths.py` always has a TOML parser on Python 3.8 to 3.14.
- `pyproject.toml` `[tool.pytest.ini_options] addopts` adds `--cov` and `-p no:randomly`. Until sibling `bzi46m` E-01 lands, run tests with `-o addopts="-p no:randomly"` when `pytest-cov` is absent, and with `-o addopts="" -p randomly --randomly-seed=12345` to check order independence.
- `tests/conftest.py:isolated_cwd` is `autouse=True` and changes every test into `tmp_path`.
- Event records in `events.jsonl` have the keys `timestamp_utc`, `type`, `name`, and `payload`.
- The `gitleaks` pre-commit hook (`.pre-commit-config.yaml`) rejects a literal `sk-...` key in a test file; existing tests build fake keys by concatenation.
- The diagnostic redactor `_DIAG_PREFIXED_KEY_RE` (`\bsk-[A-Za-z0-9_-]{8,}`) already catches hyphenated keys in error messages; only the env and argv value heuristic misses them.
- `AGENTS.md` "Matrix-validation discipline": E-01 includes `sys.platform == "win32"` formatting and E-03 file-mode behavior, which differ by OS, so the change needs the full CI matrix (3 OS x Python 3.8 to 3.14).

## Findings

| ID | Severity | Remediation Risk | Persona | Evidence | Finding |
|---|---|---|---|---|---|
| T-10 | High | Low | Testing expert / Security reviewer | `src/pubrun/capture/invocation.py:get_invocation` (70% coverage) | Entrypoint classification, `sha256_skipped`, argv input discovery, `ignore_extensions`, `compute_md5`, and `win32` formatting have no tests; a dead pre-redaction `rerun_command` block remains. Review found that the dead block makes a `Path` in `sys.argv` fail capture, and that discovery records redacted values as inputs. |
| T-11 | High | Low | Security reviewer / Testing expert | `src/pubrun/capture/redaction.py:_redact_dict_keys`, `_redact_any`, `_redact_value_string_heuristics` | Recursive JSON-in-string redaction and the env and argv `sk-` and `Bearer` heuristics have no tests. Review found that hyphenated `sk-proj-` keys are not redacted. |
| T-12 | Medium | Low | Testing expert | `src/pubrun/capture/file_io.py:ProvenanceFileProxy`; `src/pubrun/core.py:phase`; `process.py`; `host.py`; `python_runtime.py` | Proxy `read1`, `readinto1`, `readlines`, `truncate`, and `xb`, and the core and capture fallbacks, have no tests. Review found that an unknown profiling backend logs nothing. |
| T-08 (part) | High | Low | Testing expert | `tests/test_sanitize_paths.py:test_config_toggles_ip_and_lists` | Skips silently if `sp._toml is None` although the TOML parser is a required dependency. |

## Proposed changes (ordered, validatable)

1. Fix input discovery, non-string argv, and the dead block in `src/pubrun/capture/invocation.py`, and add `tests/test_invocation.py` (E-01; Remediation Risk: Low).
2. Redact hyphenated `sk-` keys and make `redact_argv` return strings in `src/pubrun/capture/redaction.py`, and add value-heuristic tests to `tests/test_redaction.py` (E-02; Remediation Risk: Low).
3. Add proxy edge-method, `truncate` budget-recovery, and `xb` tests to `tests/test_file_io_provenance.py` (E-03; Remediation Risk: Low).
4. Warn on an unknown profiling backend in `src/pubrun/core.py`, and add report, artifact, phase, process, host, and `python_runtime` fallback tests (E-04; Remediation Risk: Low).
5. Replace the silent TOML skip in `tests/test_sanitize_paths.py` with an assertion (E-05; Remediation Risk: Low).

## Deferred / out of scope (with reason)

- Running the changed tests on the GitHub Actions matrix (Windows and macOS in particular) requires a push, and pushing requires explicit human instruction (`AGENTS.md` agent execution contract). Local validation covers Linux on Python 3.12 and 3.14.
  - Carrier-Declined: a push needs explicit human authorization, so no plan can carry it; GitHub Actions runs the matrix automatically on the next push or pull request to `main`.
- The value heuristic `sk-[a-zA-Z0-9]{20,}` in `_redact_value_string_heuristics` has no word boundary, so it also redacts the tail of a word such as `desk-` followed by 20 letters. This over-redacts, which loses information but leaks nothing.
  - Carrier-Declined: over-redaction is the safe direction; changing it alters what existing manifests redact and is not needed to close any leak found here.
- `docs/configuration.md` `[capture.profiling]` lists `backend` values but does not name the warning text. E-04 makes the code match the existing sentence, so no edit there is needed.
  - Carrier-Declined: the documented behavior already matches E-04; no documentation change remains.

## Scope check

- Over-scope: the authored E-01 asked for internal helpers `_inspect_script` and `_discover_argv_inputs`. No finding needs them, and they would enlarge the diff in a module that guards secrets, so review removed them (PR-008).
- Under-scope: none remaining. Review added `src/pubrun/capture/redaction.py`, `src/pubrun/core.py`, `tests/test_capture_fallbacks.py`, `docs/manifest.md`, and `CHANGELOG.md` to `- Scope-Paths:`, because the four defect fixes, the new fallback test module, and their documentation live there. No other pending plan declares any of these paths except `CHANGELOG.md` (sibling `bzi46m`), where each plan adds its own bullet.

## Required tests / validation

- Run `python3 -m pytest tests/test_invocation.py tests/test_redaction.py tests/test_file_io_provenance.py tests/test_explicit_api.py tests/test_capture_fallbacks.py tests/test_sanitize_paths.py tests/test_capture.py tests/test_hook_ownership_rollback.py tests/test_capture_engine_bugs.py tests/test_capture_isolation.py -o addopts="-p no:randomly" -q -rs`. At review, with every E-item applied, this gave `303 passed` on Python 3.14.6 and on Python 3.12.3.
- Run the same set with `-o addopts="" -p randomly --randomly-seed=12345`; at review it gave `303 passed`.
- Run the full suite in random order, `python3 -m pytest tests/ benchmarks/test_pull_submissions.py -o addopts="" -p randomly --randomly-seed=12345 -q`. At review it gave `1956 passed, 2 skipped`, against `1902 passed, 2 skipped` without the change.
- Run `python3 scripts/sanitize_paths.py --check --all` and `gitleaks detect --no-git --source tests/ --redact`; both reported no findings at review.
- With the production changes reverted and the new tests kept, exactly five tests fail: `test_path_entry_in_argv_completes`, `test_path_entry_with_argv_redaction_disabled_completes`, `test_redacted_argument_is_not_recorded_as_input`, `test_hyphenated_prefixed_key_in_values`, and `test_unknown_backend_warns_and_skips`.

## Spec / documentation sync

- No `.spec.md` file describes these capture paths (`grep` over `.aw/records/specs/` for `invocation.inputs`, `redact_argv`, `sensitive_keys_regex`, and `profiling` found none).
- `docs/manifest.md` `invocation` table: E-01 changes what `inputs` may contain, so the `inputs` row gains the sentence "An argument whose value is redacted in `argv` is not recorded." The `entrypoint_type` row lists only `"script"`, `"module"`, and `"interactive"`, but `get_invocation` also writes `"unknown"` when `argv[0]` is neither an existing file nor `-m` or `-c`; add `"unknown"` to that row, because E-01 now asserts it.
- `CHANGELOG.md` `## [Unreleased]` `### Fixed`: add bullets for defects 1 to 4 (redacted argv values no longer recorded as inputs; hyphenated `sk-` keys redacted in env and argv values; a `Path` in `sys.argv` no longer fails invocation capture; an unknown profiling backend now logs a warning).

## Open questions

None.

## Validation and cross-check (verify before reporting done)

Validation-state rule: inspect evidence in a separate pass. Do not mark a `V-*` item complete from memory or from the matching execution checkmark. Accepted validation results: blocked, failed, pass, pending; terminal gate demands 'pass'.

Mutation-check rule for V-01 to V-05: apply the named one-line change to the named file, run the named test file with `-o addopts="-p no:randomly" -q`, paste the failing test names, restore the file with `git checkout -- <file>` (or re-apply the E-item change for a file the E-item itself edits), and paste `git status --short src/ scripts/` showing only this plan's intended changes. A defect check means: revert only that E-item's production change, run its test file, and paste the failing test names.

- [x] V-01 validates E-01
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_invocation.py tests/test_capture.py tests/test_hook_ownership_rollback.py -o addopts="-p no:randomly" -q -rs` with 0 failures and 0 skips. (2) Pasted output of `grep -n "Re-run Replication Engine\|escaped_args" src/pubrun/capture/invocation.py` showing no match. (3) Defect check: with `src/pubrun/capture/invocation.py` at its pre-change content, `test_path_entry_in_argv_completes` and `test_redacted_argument_is_not_recorded_as_input` fail. (4) Mutation checks, each failing the named test: `<= _max_hash_size` to `< _max_hash_size` fails `test_script_at_limit_is_hashed`; removing `.lower()` from `po.suffix.lstrip(".").lower()` fails `test_ignore_extensions_is_case_insensitive`; `shlex.join(redacted_argv)` to `shlex.join(argv)` fails `test_posix_commands_use_redacted_argv`; `if compute_md5 and po.is_file():` to `if compute_md5:` fails `test_compute_md5_hashes_files_and_warns`; `arg.startswith("-") or arg.startswith("--")` to `arg.startswith("--")` fails `test_option_flags_are_not_inputs`; deleting the new `if redacted_argv[idx] != arg: continue` fails `test_redacted_argument_is_not_recorded_as_input`.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_invocation.py tests/test_capture.py tests/test_hook_ownership_rollback.py -o addopts="-p no:randomly" -q -rs`:
      `99 passed in 2.59s` (0 failures, 0 skips).
    - (2) `grep -n "Re-run Replication Engine\|escaped_args" src/pubrun/capture/invocation.py`:
      `(no match, exit 1)`.
    - (3) Defect check (`src/pubrun/capture/invocation.py` at HEAD):
      `FAILED tests/test_invocation.py::TestCommandFormattingAndSecurity::test_path_entry_in_argv_completes`,
      `FAILED tests/test_invocation.py::TestCommandFormattingAndSecurity::test_path_entry_with_argv_redaction_disabled_completes`,
      `FAILED tests/test_invocation.py::TestCommandFormattingAndSecurity::test_redacted_argument_is_not_recorded_as_input` (`3 failed, 16 passed in 0.27s`).
    - (4) Mutation checks in `src/pubrun/capture/invocation.py` (each restored afterwards):
      - `<= _max_hash_size` -> `< _max_hash_size`: `FAILED tests/test_invocation.py::TestScriptHashing::test_script_at_limit_is_hashed` (`1 failed, 18 passed in 0.37s`).
      - Remove `.lower()` from `po.suffix.lstrip(".").lower()`: `FAILED tests/test_invocation.py::TestInputDiscovery::test_ignore_extensions_is_case_insensitive` (`1 failed, 18 passed in 0.81s`).
      - `shlex.join(redacted_argv)` -> `shlex.join(argv)`: `FAILED tests/test_invocation.py::TestCommandFormattingAndSecurity::test_posix_commands_use_redacted_argv` (plus 3 other command tests; `4 failed, 15 passed in 0.25s`).
      - `if compute_md5 and po.is_file():` -> `if compute_md5:`: `FAILED tests/test_invocation.py::TestInputDiscovery::test_compute_md5_hashes_files_and_warns` (`1 failed, 18 passed in 2.01s`).
      - `arg.startswith("-") or arg.startswith("--")` -> `arg.startswith("--")`: `FAILED tests/test_invocation.py::TestInputDiscovery::test_option_flags_are_not_inputs` (`1 failed, 18 passed in 0.31s`).
      - Delete `if redacted_argv[idx] != arg: continue`: `FAILED tests/test_invocation.py::TestCommandFormattingAndSecurity::test_redacted_argument_is_not_recorded_as_input` (`1 failed, 18 passed in 0.33s`).
    - `git status --short src/ scripts/`: `M src/pubrun/capture/invocation.py`, `M src/pubrun/capture/redaction.py`, `M src/pubrun/core.py`.
  - Result: pass

- [x] V-02 validates E-02
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_redaction.py tests/test_hook_ownership_rollback.py tests/test_capture_engine_bugs.py -o addopts="-p no:randomly" -q -rs` with 0 failures and 0 skips. (2) Defect check: with `src/pubrun/capture/redaction.py` at its pre-change content, `test_hyphenated_prefixed_key_in_values` fails in `tests/test_redaction.py`, and `test_path_entry_with_argv_redaction_disabled_completes` fails in `tests/test_invocation.py`. (3) Mutation checks: widening `_PREFIXED_KEY_VALUE_RE` to `{4,}` fails `test_short_sk_text_is_kept`; `res[k] = "[REDACTED]"` to `res[k] = v` in `_redact_dict_keys` fails the two JSON tests; `return json.dumps(redacted_data)` to `return val` fails the two JSON tests; deleting `arg_str = _redact_value_string_heuristics(arg_str, config)` in `redact_argv` fails `test_uri_token_in_argv_positional`. (4) Pasted output of `gitleaks detect --no-git --source tests/ --redact` reporting no leaks.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_redaction.py tests/test_hook_ownership_rollback.py tests/test_capture_engine_bugs.py -o addopts="-p no:randomly" -q -rs`:
      `130 passed in 3.28s` (0 failures, 0 skips).
    - (2) Defect check (`src/pubrun/capture/redaction.py` at HEAD):
      `FAILED tests/test_redaction.py::TestValueHeuristics::test_hyphenated_prefixed_key_in_values`,
      `FAILED tests/test_invocation.py::TestCommandFormattingAndSecurity::test_path_entry_with_argv_redaction_disabled_completes` (`2 failed, 60 passed in 0.47s`).
    - (3) Mutation checks in `src/pubrun/capture/redaction.py` (each restored afterwards):
      - `_PREFIXED_KEY_VALUE_RE` `{20,}` -> `{4,}`: `FAILED tests/test_redaction.py::TestValueHeuristics::test_short_sk_text_is_kept` (`1 failed, 42 passed in 0.47s`).
      - `_redact_dict_keys` `res[k] = "[REDACTED]"` -> `res[k] = v`: `FAILED tests/test_redaction.py::TestValueHeuristics::test_json_object_in_env_value`, `FAILED tests/test_redaction.py::TestValueHeuristics::test_json_array_in_argv_value` (`2 failed, 41 passed in 0.31s`).
      - `return json.dumps(redacted_data)` -> `return val`: `FAILED tests/test_redaction.py::TestValueHeuristics::test_json_object_in_env_value`, `FAILED tests/test_redaction.py::TestValueHeuristics::test_json_array_in_argv_value`, `FAILED tests/test_redaction.py::TestValueHeuristics::test_hyphenated_prefixed_key_in_values` (`3 failed, 40 passed in 0.24s`).
      - Delete `arg_str = _redact_value_string_heuristics(arg_str, config)`: `FAILED tests/test_redaction.py::TestValueHeuristics::test_uri_token_in_argv_positional` (plus `test_json_array_in_argv_value` and `test_hyphenated_prefixed_key_in_values`; `3 failed, 40 passed in 0.20s`).
    - (4) `gitleaks detect --no-git --source tests/ --redact`:
      `2:04PM INF scan completed in 752ms` / `2:04PM INF no leaks found` (exit 0).
    - `git status --short src/ scripts/`: `M src/pubrun/capture/invocation.py`, `M src/pubrun/capture/redaction.py`, `M src/pubrun/core.py`.
  - Result: pass

- [x] V-03 validates E-03
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_file_io_provenance.py -o addopts="-p no:randomly" -q -rs` with 0 failures and 0 skips. (2) Mutation checks in `src/pubrun/capture/file_io.py`: in `ProvenanceFileProxy.readlines`, replacing `if hint is None or (isinstance(hint, int) and hint <= 0):` with `if True:` fails `test_binary_readlines_hint_controls_eof`, and with `if False:` fails it too; in `_populate_hash_fields`, removing `and not self._truncate_used` from the over-budget shortcut fails `test_truncate_back_under_budget_is_hashed_at_close`; in `truncate`, deleting `self._truncate_used = True` fails the same test; in `read1`, deleting `self._update_stream_hash(data)` fails `test_read1_stream_hashes_and_sets_eof`.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_file_io_provenance.py -o addopts="-p no:randomly" -q -rs`:
      `38 passed in 5.21s` (0 failures, 0 skips).
    - (2) Mutation checks in `src/pubrun/capture/file_io.py` (each restored afterwards):
      - `readlines` hint check -> `if True:`: `FAILED tests/test_file_io_provenance.py::TestProxyEdgeMethods::test_binary_readlines_hint_controls_eof` (`1 failed, 37 passed in 2.15s`).
      - `readlines` hint check -> `if False:`: `FAILED tests/test_file_io_provenance.py::TestProxyEdgeMethods::test_binary_readlines_hint_controls_eof` (`1 failed, 37 passed in 1.93s`).
      - Remove `and not self._truncate_used`: `FAILED tests/test_file_io_provenance.py::TestProxyEdgeMethods::test_truncate_back_under_budget_is_hashed_at_close` (`1 failed, 37 passed in 2.42s`).
      - Delete `self._truncate_used = True`: `FAILED tests/test_file_io_provenance.py::TestProxyEdgeMethods::test_truncate_back_under_budget_is_hashed_at_close` (`1 failed, 37 passed in 2.32s`).
      - Delete `self._update_stream_hash(data)` in `read1`: `FAILED tests/test_file_io_provenance.py::TestProxyEdgeMethods::test_read1_stream_hashes_and_sets_eof` (`1 failed, 37 passed in 3.21s`).
    - `git status --short src/ scripts/`: `M src/pubrun/capture/invocation.py`, `M src/pubrun/capture/redaction.py`, `M src/pubrun/core.py`.
  - Result: pass

- [x] V-04 validates E-04
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_explicit_api.py tests/test_capture_fallbacks.py -o addopts="-p no:randomly" -q -rs` with 0 failures and 0 skips, and of the same command with `-o addopts="" -p randomly --randomly-seed=12345`. (2) Defect check: with `src/pubrun/core.py` at its pre-change content, `test_unknown_backend_warns_and_skips` fails. (3) Mutation checks: in `core.py:report`, `{"items": len(data)}` to `{}` fails `test_list_report_summarizes_item_count`; in `core.py:phase.__enter__`, `if not getattr(phase, "_yappi_active", False):` to `if True:` fails `test_nested_yappi_phase_is_skipped_with_warning`; in `process.py`, `username = "unknown"` to `username = None` fails `test_getuser_failure_reports_unknown`; in `host.py`, `platform.node() or socket.gethostname()` to `platform.node()` fails `test_empty_node_falls_back_to_socket_hostname`; in `python_runtime.py:environment_kind`, deleting `os.environ.get("PYENV_VERSION") or ` fails `test_pyenv_version_env_var`, and swapping the `frozen` and `conda` checks fails `test_frozen_wins_over_conda`.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_explicit_api.py tests/test_capture_fallbacks.py -o addopts="-p no:randomly" -q -rs`:
      `23 passed in 2.29s` (0 failures, 0 skips).
      With `-o addopts="" -p randomly --randomly-seed=12345`:
      `23 passed in 1.89s` (0 failures, 0 skips).
    - (2) Defect check (`src/pubrun/core.py` at HEAD):
      `FAILED tests/test_explicit_api.py::test_unknown_backend_warns_and_skips` (`1 failed, 12 passed in 5.04s`).
    - (3) Mutation checks (each restored afterwards):
      - `core.py:report` `{"items": len(data)}` -> `{}`: `FAILED tests/test_explicit_api.py::test_list_report_summarizes_item_count` (`1 failed, 12 passed in 2.08s`).
      - `core.py:phase.__enter__` `if not getattr(phase, "_yappi_active", False):` -> `if True:`: `FAILED tests/test_explicit_api.py::test_nested_yappi_phase_is_skipped_with_warning` (`1 failed, 12 passed in 2.02s`).
      - `process.py` `username = "unknown"` -> `username = None`: `FAILED tests/test_capture_fallbacks.py::TestProcessFallbacks::test_getuser_failure_reports_unknown` (`1 failed, 9 passed in 0.22s`).
      - `host.py` `platform.node() or socket.gethostname()` -> `platform.node()`: `FAILED tests/test_capture_fallbacks.py::TestHostFallbacks::test_empty_node_falls_back_to_socket_hostname` (`1 failed, 9 passed in 0.12s`).
      - `python_runtime.py:environment_kind` delete `os.environ.get("PYENV_VERSION") or `: `FAILED tests/test_capture_fallbacks.py::TestPythonRuntimeEnvironmentKind::test_pyenv_version_env_var` (`1 failed, 9 passed in 0.87s`).
      - `python_runtime.py:environment_kind` swap `frozen` and `conda` checks: `FAILED tests/test_capture_fallbacks.py::TestPythonRuntimeEnvironmentKind::test_frozen_wins_over_conda` (`1 failed, 9 passed in 0.22s`).
    - `git status --short src/ scripts/`: `M src/pubrun/capture/invocation.py`, `M src/pubrun/capture/redaction.py`, `M src/pubrun/core.py`.
  - Result: pass

- [x] V-05 validates E-05
  - Required evidence: (1) Pasted output of `python3 -m pytest tests/test_sanitize_paths.py -o addopts="-p no:randomly" -q -rs` with 0 failures and 0 skips. (2) Mutation check: in `scripts/sanitize_paths.py`, rename the import `tomllib` to `tomllib_missing` (and `tomli` to `tomli_missing`); `test_config_toggles_ip_and_lists` fails, where before E-05 it was reported `SKIPPED`. (3) Pasted output of `python3 scripts/sanitize_paths.py --check --all` exiting 0. (4) Pasted diff of `docs/manifest.md` and `CHANGELOG.md` showing the edits listed under `## Spec / documentation sync`, and pasted output of the full-suite command under `## Required tests / validation`.
  - Observed evidence:
    - (1) `python3 -m pytest tests/test_sanitize_paths.py -o addopts="-p no:randomly" -q -rs`:
      `19 passed in 0.21s` (0 failures, 0 skips).
    - (2) Mutation check (`scripts/sanitize_paths.py` renaming `tomllib` -> `tomllib_missing` and `tomli` -> `tomli_missing`, then restored):
      `FAILED tests/test_sanitize_paths.py::test_config_toggles_ip_and_lists` (`1 failed, 18 passed in 0.26s`).
    - (3) `python3 scripts/sanitize_paths.py --check --all`: exited 0 with no findings.
    - (4) `git diff docs/manifest.md CHANGELOG.md`:
      `docs/manifest.md` adds `"unknown"` to `invocation.entrypoint_type` and `"An argument whose value is redacted in `argv` is not recorded."` to `invocation.inputs`; `CHANGELOG.md` adds four bullets under `## [Unreleased]` `### Fixed` covering defects 1 through 4.
      ```diff
      --- a/docs/manifest.md
      +++ b/docs/manifest.md
      @@ -95,10 +95,10 @@
      -| `entrypoint_type` | string | `"script"`, `"module"`, or `"interactive"`. |
      +| `entrypoint_type` | string | `"script"`, `"module"`, `"interactive"`, or `"unknown"`. |
       | `script` | object | Script file metadata (see below). |
       | `working_directory` | object | `{"path": "/abs/path", "real_path": "/resolved/path"}`. |
      -| `inputs` | list[object] | Detected input files from `sys.argv` (path, size, mtime, optional md5). |
      +| `inputs` | list[object] | Detected input files from `sys.argv` (path, size, mtime, optional md5). An argument whose value is redacted in `argv` is not recorded. |
      ```
      Combined 10-file test suite: `305 passed in 18.61s` (default order) and `305 passed in 17.61s` (`--randomly-seed=12345`).
      Combined all-production-reverted defect check: exactly 5 tests failed (`test_path_entry_in_argv_completes`, `test_path_entry_with_argv_redaction_disabled_completes`, `test_redacted_argument_is_not_recorded_as_input`, `test_hyphenated_prefixed_key_in_values`, `test_unknown_backend_warns_and_skips`; `5 failed, 70 passed in 2.10s`).
      Full suite in random order (`python3 -m pytest tests/ benchmarks/test_pull_submissions.py -o addopts="" -p randomly --randomly-seed=12345 -q`):
      `1991 passed, 2 skipped in 506.44s (0:08:26)`.
      Full suite via `aw suite`:
      `1974 passed in 159.50s (0:02:39)`.
    - `git status --short src/ scripts/`: `M src/pubrun/capture/invocation.py`, `M src/pubrun/capture/redaction.py`, `M src/pubrun/core.py`.
  - Result: pass

## Approval and execution gate

- Size assessment: standard
- Cohesion rationale: not required

Execution contract:
1. Precondition: wait for human approval (`- Status: approved`) with no unresolved `Blocking: yes` open question before you change any file. This plan has no open questions.
2. Scope declaration: the expected modified files are the `- Scope-Paths:` entries (`src/pubrun/capture/invocation.py`, `src/pubrun/capture/redaction.py`, `src/pubrun/core.py`, `tests/test_invocation.py`, `tests/test_redaction.py`, `tests/test_file_io_provenance.py`, `tests/test_explicit_api.py`, `tests/test_capture_fallbacks.py`, `tests/test_sanitize_paths.py`, `docs/manifest.md`, `CHANGELOG.md`). If execution requires an out-of-scope file, justify it with `--scope-reason` at finalization. If a declared file needs no edit, acknowledge it with `--scope-ack`. The mutation checks edit `src/pubrun/capture/file_io.py`, `src/pubrun/capture/process.py`, `src/pubrun/capture/host.py`, `src/pubrun/capture/python_runtime.py`, and `scripts/sanitize_paths.py` only temporarily; restore them and do not commit them.
3. Validation honesty: you MUST run each required validation command and paste its actual output into the matching `V-*` `Observed evidence:` field. Do not mark a `V-*` item `pass` without output captured from that run.
4. Commit discipline: commit only the paths you changed with `aw commit 2mwjjw -- <paths>`. Do not use `git add -A` or raw `git commit`. Do not push without an explicit human instruction.
5. Lifecycle transition: finalize this plan with `aw ipd finalize 2mwjjw`, never with a hand-written `git mv` to `.aw/records/plans/executed/`. Inside a runner lane (`aw oc run` or `aw agy run`), the runner finalizes after the turn. Outside a runner, the executor runs `aw ipd finalize 2mwjjw` after every `E-*` item is `performed`, every `V-*` item is `pass`, and `aw ipd lint --phase pre-transition` reports `conforming`.
