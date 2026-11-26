# Review findings: ipd 0vwc5z

- Subject-Id: 0vwc5z
- Subject-Type: ipd
- Reviewed-At: 2026-11-23
- Reviewer: Claude Opus 5.5
- Verdict: APPROVE WITH REVISIONS APPLIED

## Round 1

### Step P

- Checked: Full text of `.aw/records/plans/pending/20261122-ggaok0-01-0vwc5z-make-the-startup-breakdown-username-scrub-boundary-safe.ipd.md` (front matter, Mermaid flowchart, E-01 to E-04, V-01 to V-04, conventions, findings, deferrals, open question, gate) against `.aw/system/workflows/technical-writing/technical-writing.md` requirements 1 to 12 and `steps/p-proofread.md`. The flowchart matches E-01 (skip keys, protected literals, longest-first needles, path versus bare needle, rest-only rescan).

### Proofreading

#### Changes
| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| Validation boilerplate (runtime-demonstration reachability rule) | Two em dashes around the "as distinct from" clause (`IPD-C802` advisories at line 143) | Commas and parentheses | Removes both `IPD-C802` advisories without changing meaning. |
| E-01 skip-key list, V-01 | "exactly these keys ... `release` ..."; "the 21 keys" | 20 keys without `release`, with the reason stated | Requirement 5 and correctness; see PR-003. The count in V-01 now matches the list. |
| Deferral row on Markdown over-redaction | "the JSON report keeps those values because they are in `_SCRUB_SKIP_KEYS`" | "because they are dict keys (never scrubbed) or values under `_SCRUB_SKIP_KEYS`" | Scenario names are dict keys, not skip-key values; the old reason was inaccurate. |

#### Issues
| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|

### Step T

- Checked: front matter, `- Scope-Paths:` (2 files, no `.spec.md`), E-item and task-group counts (4 items, 2 groups).

1. No: changes no spec, CLI option, or file format; the `pubrun-startup-breakdown/1` JSON shape is unchanged, only which substrings become `<redacted>`.
2. Yes: the change is privacy redaction code that decides what identifying data leaves the machine in a shareable report.
3. No: 4 E-items in 2 task groups, one script and its test file.
4. Yes: `- Scope-Paths:` lists both files.
5. No: a local benchmark script; a mistake would over- or under-redact a report the user chooses to share, and is easy to revert.

AW-TIER: standard

### Step R1

- Checked: `benchmarks/startup_breakdown.py::_collect_redaction_needles` (lines 239 to 285, longest-first), `_redact_keys_recursive`, `_scrub_substrings` (plain `str.replace`), `redact_breakdown`, `scrub_text` (line 330), `validate_redacted_output` (line 339, `json.dumps` blob search, short-needle skip), `run_breakdown` (lines 1288 to 1297), `main` (lines 1527 to 1571), `format_markdown_report`, `_capture_filesystem_summary` (`status` values), `_capture_cpu_summary` (`architecture`, `model`), `_capture_pubrun_version`, scenario specs and `layouts` (lines 1049 to 1126); `benchmarks/harness.py::_SCRUB_SKIP_KEYS`, `_is_path_needle`, `_scrub_segment`, `_scrub_string`, `_scrub_pii_substrings` (lines 577 to 640); `benchmarks/share_safety.py::check_share_safe`, `_HOME_PATH_RE`; `tests/test_startup_benchmark.py` (`_load_module`, existing redaction tests at lines 90 and 130, CLI `timeout=180`); `tests/test_benchmark_intake_bugs.py::TestScrubBoundaries`; executed plan `8k73qj` and its review (D-1 boundary regex); backlog `ggaok0` (graduated to `0vwc5z`); `benchmarks/README.md` lines 119 to 121; `docs/performance.md` (method lines only).
- Reproduced the plan's Findings table on the current tree: `ed` gives hostname `<r<redacted>act<redacted>>` and validator `(True, [])`; `pub` gives `<redacted>run-startup-breakdown/1` and validator `(False, ['identifying substring remains in JSON payload'])`; `startup` gives `pubrun-<redacted>-breakdown/1`. The CLI with `USER=pub` exits 1 with the quoted error. All citations resolve.
- Collected every string-valued key in a real `--iterations 1` JSON report: all except `model` and `release` are in the plan's skip list; `kind` and `status` are absent from a normal run but harmless.

### Step R2

- Checked: E/V bijection (E-01..E-04 to V-01..V-04), Scope-Paths completeness, `Item-Dependencies: none` (correct; `8k73qj` already executed), runtime-demonstration reachability, and whether each test would fail on the unfixed code.
- Ran a prototype of the E-01/E-02 design against the real script (functions replaced in process, no repo edit): all five usernames give an intact schema, `note` as specified, no stray brackets, validator `(True, [])`; `scrub_text` cases pass; `"owner pub"` is refused; CLI runs with `USER=pub`, `ed`, and `run` exit 0 with intact schema.
- Ran the unfixed CLI with `USER=ed`: exit 0, schema intact, zero `<`/`>` outside `<redacted>`, but `layout` values `install<redacted>` and `install<redacted>-nest<redacted>`. The planned CLI `ed` case would therefore pass on the unfixed code (PR-001).
- V-01, V-02, and V-03 used test names and parametrize ids as their bar (PR-004).
- Gate: precondition, Scope-Paths fence with `--scope-reason`/`--scope-ack`, validation honesty, path-scoped `aw commit` with never-push, and runner/executor `aw ipd finalize` ownership are present. Conforming.

### Step R3

- Checked (full form): what identifying data can leave the machine. Needles are the hostname, username (`getpass` plus `USER`/`USERNAME`/`LOGNAME`), home, repo root, and `--workdir`; path needles stay literal, so no path leak is introduced. The boundary rule narrows bare-needle matching: a username adjacent to `_` or a letter (for example `/scratch/alice_runs`) is no longer redacted, which matches `benchmarks/harness.py` (`8k73qj` D-1) and the self-check uses the same rule, so it does not catch that case either; home-directory paths are still caught literally and by `_HOME_PATH_RE`. Recorded as an accepted parity trade-off, not a finding.
- Skip keys exempt values from scrubbing, so each must be script-generated. `environment.os.release` is `platform.release()`, a host-controlled string that can carry a custom kernel suffix (PR-003).
- The JSON validator as written would flag the scrub's own `<redacted>` markers when a bare needle is `redacted` (PR-002).

### Step R4

- Checked: rubric A (pure functions, no shared state), C (port rather than import; matches the backlog item and avoids touching `harness.py`), D (invariants: schema string and fixed metadata unchanged; standalone usernames still redacted; the self-check still refuses a leaked standalone username and a home path; issue strings unchanged), E (behavioral tests via function calls and subprocess, no source reading), F (KISS: three helpers and one frozenset), right-sizing (4 E-items, 2 files), spec/doc sync (`benchmarks/README.md` statement stays true; no spec governs the scrub).
- Repository matrix discipline: `getpass.getuser` and `os.path.expanduser` read different variables on Windows, and the plan's tests set only POSIX variables; the plan did not record the CI matrix gate (PR-005).

### Step S5

- Checked: `OQ-01` (resolved, non-blocking, cited basis: every dict key is script-generated; path needles still checked in keys), deferral carriers (three `Carrier-Declined` entries with reasons), and all findings. All findings have Low remediation risk and are fixed. No question needs the human. No finding is OPEN or DEFERRED.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | medium | IN-SCOPE | R2 (falsifiable validation) | Review run of unfixed `benchmarks/startup_breakdown.py` with `USER=ed`: exit 0, `schema` intact, layouts `install<redacted>`, `install<redacted>-nest<redacted>`, zero `<`/`>` outside `<redacted>` | The E-03 CLI case for `ed` asserted only exit code, schema, and stray angle brackets, all of which the unfixed script already satisfies, so it could not detect the bug it targets. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | The CLI test now also asserts the four `layout` values and `import-minimal-installed-nested` in stdout, with `timeout=180`; the unit test adds `layout` `installed-nested`. The stale "2026-11-22 run" note was replaced with the review's measurements (recommendation strength: strong). |
| PR-002 | medium | IN-SCOPE | R3 / R4.D (validator false refusal) | Plan E-02 JSON check; review prototype: with username `redacted`, a matcher over whole values flags `<redacted>` and the scrubbed `note` | E-02 stripped protected literals before matching Markdown but not JSON string values, so a bare needle that matches inside `<redacted>` makes the self-check refuse correctly scrubbed output. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-02 now splits each JSON string value on the protected literals and checks only the segments between them, exactly as the scrub does (recommendation strength: strong). |
| PR-003 | medium | IN-SCOPE | R3 (skip-key exemption) | `benchmarks/startup_breakdown.py` `env_meta["os"]["release"] = platform.release()`; `harness.py::_SCRUB_SKIP_KEYS` has no `release` | E-01 exempted `release` from scrubbing, but it is a host-controlled free-form string (a custom kernel build string can embed a user or host name), so a username inside it would be emitted. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Removed `release` from the list (now 20 keys), stated why, and added a `release` of `6.8.0-{user}` that must come back as `6.8.0-<redacted>` (recommendation strength: strong). |
| PR-004 | low | IN-SCOPE | R2 (evidence bar uses test names) | `steps/r2-executability.md` "a test function name is permitted only as a non-binding pointer"; plan V-01 to V-03 | V-01 to V-03 set named tests and parametrize ids passing as the bar. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Each V-item now demands zero failures plus the re-derived test lines pinning each behavior and the mechanism (function call or subprocess); names are pointers. V-03 also requires at least one selected test and names its reachability path (recommendation strength: strong). |
| PR-005 | low | UNDER-SCOPE | R4.E (matrix portability) | `AGENTS.md` "Matrix-validation discipline"; `.github/workflows/ci.yml` (3 OS by Python 3.8 to 3.14); Windows `getpass.getuser` order and `USERPROFILE` | The plan's tests set POSIX environment variables only and E-04/V-04 did not record the CI matrix gate, so local Linux green could be taken as done. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | E-04 and V-04 now record the CI matrix as the gate before release and explain the Windows difference (recommendation strength: medium). |
| PR-006 | low | IN-SCOPE | Check P (writing, `IPD-C802`) | Plan line 143; plan deferral row on Markdown over-redaction | Two em dashes raised `IPD-C802` advisories; one deferral reason misattributed why scenario names survive in JSON. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced the dashes and corrected the reason (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | Should `release` be a skip key? | No: keep it scrubbed with the boundary rule | Keep it skipped to protect the value from over-redaction | `platform.release()` is host-controlled; harness `_SCRUB_SKIP_KEYS` omits it; prototype shows `6.8.0-<redacted>` and validator `(True, [])` | yes |
| D-2 | Should the boundary rule's narrowing (`alice_runs` not redacted) be changed? | No: keep parity with `benchmarks/harness.py` | Treat `_` as a boundary in both scripts | `8k73qj` review D-1 chose `[A-Za-z0-9_]`; changing it is outside the backlog item and would also change `harness.py` | yes |

### Step S6

- Checked: whether review edits added or removed E/V items or changed `- Scope-Paths:` or `- Item-Dependencies:`. None did; edits refined existing items. `aw ipd lint --phase review-finalize --agent` reported `clean`, exit 0, 0 findings. No re-review pass needed.

AW-REVIEW: DONE
