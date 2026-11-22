# Review findings: ipd l7ko8p

- Subject-Id: l7ko8p
- Subject-Type: ipd
- Reviewed-At: 2026-11-22
- Reviewer: Gemini 4 Neon (High)
- Verdict: REVIEWED - OPEN QUESTIONS

## Round 1

### Step P

- Checked: Complete text, front matter, `Workflow history`, `Goal`, `E-01`..`E-04`, `Project conventions`, `Findings`, `Proposed changes`, `Deferred / out of scope`, `Scope check`, `Required tests / validation`, `Spec / documentation sync`, `Open questions`, `V-01`..`V-04`, and `Approval and execution gate` of `.aw/records/plans/pending/20261122-bugs-audit-04-l7ko8p-fix-config-boot-discovery-and-capture-mode-or-depth-enforcem.ipd.md` against `.aw/system/workflows/technical-writing/technical-writing.md` (requirements 1 through 12) and `.aw/system/workflows/plan-review/steps/p-proofread.md`.

### Proofreading

#### Changes

| Location | Old text summary | New text summary | Reason |
|---|---|---|---|
| `## Workflow history` | Listed `draft` above `to-review` (oldest-first) | Reordered newest-first and prepended `/plan-review` entry | `steps/s7-finalize.md` newest-first history contract |
| `Goal` and new `Boot import-mode resolution flow` diagram | No Mermaid diagram for multi-step branching boot resolution; unexpanded acronyms (`XDG`, `TOML`) | Added `flowchart TD` matching text and expanded acronyms on first use | Technical writing requirements 1, 12(b), 12(d), and 12(e) |
| Symbol citations across `E-01`..`E-03`, `Project conventions`, `Findings`, `Proposed changes`, `V-03` | Nonexistent symbols `capture.process.get_process`, `config._user_config_path`, `_config_boot.load_boot_config`, and false claim that `config.resolve_config` reads `pyproject.toml` | Standardized `path::Symbol` citations (`get_process_info`, `get_global_config_dir`, `resolve_import_mode`) and removed false `pyproject.toml` claim | `steps/p-proofread.md` Section 11.1 and repository factual accuracy |
| `## Spec / documentation sync` and `## Open questions` | Claimed `N/A` and `None` despite no defined allowlist config key anywhere in the repo | Documented missing allowlist key gap and added `OQ-01` (`Blocking: yes`, `Finding: PR-001`) plus adjacent Unresolved annotation in `E-02` | Technical writing requirement 10 and `steps/s5-questions.md` finding escalation |
| `## Approval and execution gate` | Missing honesty, never-push, scope-declaration, and conditional finalize rules; vague manual-move wording | Replaced with compliant 5-item Execution contract noting `OQ-01` precondition, `--scope-reason`/`--scope-ack`, HARD MUST pasted output rule, never-push, and conditional `aw ipd finalize l7ko8p` ownership | `steps/r2-executability.md` and `steps/s7-finalize.md` execution-contract rules |

#### Issues

| ID | Location | Ambiguity | Information needed | Recommended answer | Recommendation strength |
|---|---|---|---|---|---|
| TW-01 | `E-02`, `Proposed changes #3`, `Spec / documentation sync`, `OQ-01` | `[capture.environment].mode = "allowlist"` is documented in `default.toml` and `docs/configuration.md` with no configuration key name, matching semantics, or empty-list default. | Maintainer choice of public key name (e.g. `allowlist` vs `allowed_vars`), exact vs `fnmatch` glob matching, empty-list default (`[]` fail-closed vs built-in safe list), and adding `default.toml`/`docs/configuration.md` to scope. | Define `[capture.environment].allowlist = []` in `default.toml` and `docs/configuration.md` with exact + `fnmatch` glob matching, fail-closed empty list, and `redact_env_vars` still applied. | strong |

### Step T

- Checked: Front matter, `- Scope-Paths:`, `E-01`..`E-04`, `src/pubrun/_config_boot.py`, `src/pubrun/config.py`, `src/pubrun/capture/environment.py`, `src/pubrun/capture/git.py`, `src/pubrun/capture/host.py`, `src/pubrun/capture/process.py`, `src/pubrun/capture/python_runtime.py`, `src/pubrun/resources/default.toml`, `docs/configuration.md`, `schemas/manifest.schema.json`, and Set `bugs-audit` orchestrator `jqqvkh`.

1. Yes: introduces or enforces a public configuration contract (`[capture.environment]` allowlist key and semantics, `[capture.*].depth = "off"`, `PUBRUN_AUTO_START` values, and user/local boot config discovery).
2. Yes: `[capture.environment].mode = "allowlist"` directly controls which environment variables (potential secrets/private data) are captured into `manifest.json`.
3. No: 4 focused E-items across 3 task groups touching config resolution and 5 small capture collectors (child 04 of 9 in Set `bugs-audit`).
4. Yes: `- Scope-Paths:` lists the 8 code/test files (with `src/pubrun/resources/default.toml` and `docs/configuration.md` gated on `OQ-01`).
5. Yes: inventing the wrong public TOML key name or leaking unintended environment variables in allowlist mode is hard to undo once users adopt it in `.pubrun.toml`, and returning `{}` instead of `{"capture_state": {"status": "suppressed"}}` violates `schemas/manifest.schema.json`.

AW-TIER: complex

### Step R1

- Checked: Verified every cited symbol, config key, schema definition, and test across `src/pubrun/_config_boot.py`, `src/pubrun/config.py`, `src/pubrun/capture/environment.py`, `src/pubrun/capture/git.py`, `src/pubrun/capture/host.py`, `src/pubrun/capture/process.py`, `src/pubrun/capture/python_runtime.py`, `src/pubrun/resources/default.toml`, `docs/configuration.md`, `docs/manifest.md`, `schemas/manifest.schema.json`, `tests/test_import_modes.py`, and `tests/test_capture_engines.py`. Caught missing allowlist config key contract (`PR-001`), nonexistent symbols (`get_process`, `_user_config_path`, `load_boot_config`) and false `pyproject.toml` claim (`PR-002`), and missing precedence/Windows `APPDATA`/`_resolve_layers` deepcopy/schema-suppressed payload details (`PR-003`).

### Step R2

- Checked: Verified author lint preflight (`aw ipd lint --phase author --agent` exit 0, `clean`, 0 findings), 1:1 `E-01`..`E-04` to `V-01`..`V-04` bijection (co-locating per-bug test authoring inside `E-01`..`E-03`), `- Item-Dependencies: none` matching `jqqvkh`, `OQ-01` escalation (`- Blocking: yes`, `- Finding: PR-001`), concrete behavioral evidence in `V-01`..`V-04` (reachable via local `pytest`, no code-pinning), and `## Approval and execution gate` (fixed in `PR-004`).

### Step R3

- Checked: Verified privacy/security posture of `[capture.environment].mode = "allowlist"` (fail-closed empty default and retaining `redact_env_vars` on matched entries recommended in `OQ-01` so no unrequested or secret env vars leak), verified `depth = "off"` skips `os.environ` / `git` subprocess / host / process / Python capture completely, and verified empty `XDG_CONFIG_HOME=""` no longer loads untrusted `./pubrun/config.toml` from the current working directory!

### Step R4

- Checked: Evaluated engineering rubric sections A (schema-compliant `{"capture_state": {"status": "suppressed"}}` payloads matching `schemas/manifest.schema.json`, deep copy in `_resolve_layers` covering both `resolve_config` and `resolve_config_with_provenance`, highest-to-lowest boot file walk preserving fast-path startup), C (keeping `_config_boot.py` stdlib-only and lightweight without importing `config.py`), D (preserving `tests/test_import_modes.py` and `tests/test_capture_engines.py` contracts), E (isolated `HOME`/`XDG_CONFIG_HOME`/`APPDATA` tests in `tests/test_config_capture_modes.py` plus full `pytest -q`), F (KISS, fail-closed allowlist recommendation), right-sizing (4 focused E-items), and `## Spec / documentation sync` (honestly linked `default.toml`/`docs/configuration.md` sync to `OQ-01`).

### Step R5

- Checked: Evaluated through all eight reviewer personas per `.aw/system/workflows/release-review/00-run-protocol.md#Review mindset: the eight reviewer personas`:
  1. **QA / QC engineer:** Caught missing allowlist config key in `default.toml`/`docs/configuration.md` (`PR-001`), nonexistent symbols and false `pyproject.toml` claim (`PR-002`), and Windows `APPDATA` + `resolve_config_with_provenance` mutation (`PR-003`).
  2. **Testing and regression expert:** Required `monkeypatch` isolation of `HOME`/`XDG_CONFIG_HOME`/`APPDATA` in `tests/test_config_capture_modes.py`, co-located tests with `E-01`..`E-03`, and verified zero `subprocess.run` calls in `get_git` under `depth = "off"` (`PR-003`, `PR-005`).
  3. **UI / UX expert:** Surfaced the missing user-facing TOML allowlist key to the maintainer rather than inventing an undocumented config key (`PR-001`).
  4. **Systems and software architect:** Aligned all five `depth = "off"` collectors with `schemas/manifest.schema.json` `{"capture_state": {"status": "suppressed"}}` and preserved `_config_boot.py` fast-path startup via highest-to-lowest file search (`PR-002`, `PR-003`).
  5. **Software engineer:** Fixed nonexistent symbols (`get_process_info`, `get_global_config_dir`, `resolve_import_mode`) and execution-contract gate (`PR-002`, `PR-004`).
  6. **Sophisticated power user:** Recommended `fnmatch` glob support (such as `SLURM_*`, `NCCL_*`) in `OQ-01` for HPC environments and consistent `PUBRUN_AUTO_START=0/1/no/yes/off/on` handling (`PR-001`, `PR-003`).
  7. **Complete novice:** Added boot-resolution Mermaid flowchart and expanded acronyms (`PR-005`).
  8. **Stakeholder:** Protected public config contract stability by refusing to invent an unapproved TOML key name while fixing every other defect cleanly in place (`PR-001`..`PR-005`).

### Step R6

- Checked: Evaluated decomposition across `E-01`..`E-04`. `l7ko8p` is already child 04 of 9 in Set `bugs-audit`, covering 3 cohesive config/capture bug groups in 4 focused E-items. No split recommended.

### Step R7

- Checked: Verified alignment with Set `bugs-audit` orchestrator `jqqvkh` and sibling child plans (`njn1up`..`kqzd15`). Confirmed `- Item-Dependencies: none` matches `jqqvkh`, `- Scope-Paths:` is completely disjoint from all 8 sibling child plans in `bugs-audit`, and flagged that `src/pubrun/resources/default.toml` and `docs/configuration.md` (if added upon resolving `OQ-01`) remain disjoint from all sibling `bugs-audit` child plans.

### Step S5

- Checked: Evaluated the missing `[capture.environment]` allowlist configuration key under `.aw/system/workflows/askme/askme.md` ("Establish facts before asking") and `steps/s5-questions.md` ("Reversible or not"). Because defining a new public TOML key name, matching semantics, and empty-list default is a public contract (`Reversible: no`) with no approved decision rule in the repository, left `PR-001` `OPEN`, escalated it into `l7ko8p` as `OQ-01` (`- Blocking: yes`, `- Status: open`, `- Finding: PR-001`), recorded it in `05-l7ko8p.json` `questions[]` (`gates_verdict: true`), and set Verdict `REVIEWED - OPEN QUESTIONS` and `- Readiness: no-go`. Fixed `PR-002`..`PR-005` in place and recorded reversible decisions `D-1`..`D-2` below.

### Findings

| ID | Severity | Scope | Area | Evidence | Finding | Remediation Risk | Decision | Resolution |
|---|---|---|---|---|---|---|---|---|
| PR-001 | HIGH | UNDER-SCOPE | R1/R4.A/R4.Spec-doc-sync/S5 | `.aw/records/plans/pending/20261122-bugs-audit-04-l7ko8p-fix-config-boot-discovery-and-capture-mode-or-depth-enforcem.ipd.md:44-46,78,98,114`, `src/pubrun/resources/default.toml:191-198`, `docs/configuration.md:140-146`, `src/pubrun/capture/environment.py:11-27` | `[capture.environment].mode = "allowlist"` is documented without any config key name, matching rule (exact vs glob), or empty-list default anywhere in `default.toml`, `docs/configuration.md`, or `src/pubrun/`. Implementing `E-02` requires defining a new public TOML configuration key (irreversible once adopted by users) and updating `default.toml` and `docs/configuration.md`. | C:Low; U:Medium-High; S:Medium; F:Medium-High; Overall:Medium-High | OPEN | Escalated as blocking `OQ-01` (`- Blocking: yes`, `- Finding: PR-001`, `- Carrier: 9mxiq1`) in `l7ko8p`, tracked in blocked backlog item `9mxiq1`, and recorded in `05-l7ko8p.json` `questions[]` (`gates_verdict: true`). Recommended answer: `[capture.environment].allowlist = []` with exact + `fnmatch` glob matching, fail-closed empty list, and `redact_env_vars` still applied, documented in `default.toml` and `docs/configuration.md` (recommendation strength: strong). |
| PR-002 | HIGH | IN-SCOPE | R1/R4.A | `.aw/records/plans/pending/20261122-bugs-audit-04-l7ko8p-fix-config-boot-discovery-and-capture-mode-or-depth-enforcem.ipd.md:49-51,64,70-72,119`, `src/pubrun/capture/process.py:5`, `src/pubrun/config.py:62-73,102-155`, `src/pubrun/_config_boot.py:23,79`, `schemas/manifest.schema.json:790-795,874-879,1170-1195` | Cited nonexistent symbols `capture.process.get_process` (actual: `get_process_info`), `config._user_config_path` (actual: `get_global_config_dir`), and `_config_boot.load_boot_config` (actual: `resolve_import_mode`); falsely claimed `config.resolve_config` reads `pyproject.toml`; and left `E-03` disabled return value vague ("empty/disabled result") instead of schema-required `{"capture_state": {"status": "suppressed"}}`. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Corrected all symbol citations, removed the false `pyproject.toml` claim, and required `{"capture_state": {"status": "suppressed"}}` across all five collectors (`D-1`, recommendation strength: very strong). |
| PR-003 | HIGH | UNDER-SCOPE | R1/R4.A/R4.D | `.aw/records/plans/pending/20261122-bugs-audit-04-l7ko8p-fix-config-boot-discovery-and-capture-mode-or-depth-enforcem.ipd.md:37-40,76-77`, `src/pubrun/config.py:62-73,165-175`, `src/pubrun/_config_boot.py:79-115`, `tests/test_import_modes.py:113-198` | Omitted stripping Windows `APPDATA` alongside `XDG_CONFIG_HOME`, fixing `_resolve_layers` (shared by `resolve_config` and `resolve_config_with_provenance`) with `copy.deepcopy`, exact highest-to-lowest boot file search order (`./.pubrun.toml` -> `./.config/pubrun/config.toml` -> user `config.toml`), and `HOME`/`XDG_CONFIG_HOME`/`APPDATA` test isolation. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Specified all four mechanisms explicitly in `E-01`, `Proposed changes`, and `V-01` (`D-2`, recommendation strength: very strong). |
| PR-004 | HIGH | IN-SCOPE | R2/S7 | `.aw/records/plans/pending/20261122-bugs-audit-04-l7ko8p-fix-config-boot-discovery-and-capture-mode-or-depth-enforcem.ipd.md:128-133`, `.aw/system/workflows/plan-review/steps/r2-executability.md:57-60`, `.aw/system/workflows/plan-review/steps/s7-finalize.md:31-46` | `## Approval and execution gate` omitted the HARD MUST pasted-output honesty rule, never-push rule, `--scope-reason`/`--scope-ack` scope declaration, and conditional runner vs standalone `aw ipd finalize l7ko8p` ownership, and used vague manual-move wording. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Replaced `## Approval and execution gate` with a compliant 5-item Execution contract noting the `OQ-01` precondition (recommendation strength: very strong). |
| PR-005 | MEDIUM | IN-SCOPE | Check P/R2/R4 | `.aw/records/plans/pending/20261122-bugs-audit-04-l7ko8p-fix-config-boot-discovery-and-capture-mode-or-depth-enforcem.ipd.md:22-59,96-126` | `Workflow history` was oldest-first; `V-01`..`V-03` depended on `tests/test_config_capture_modes.py` not created until `E-04`; lacked a Mermaid diagram for the branching boot-config resolution flow (Requirement 12(b)); `Spec / documentation sync` was bare `N/A`; code citations lacked `path::Symbol` format; and acronyms (`XDG`, `TOML`) were unexpanded. | C:Low; U:Low; S:Low; F:Low; Overall:Low | FIXED | Reordered `Workflow history` newest-first, co-located per-bug tests inside `E-01`..`E-03`, added boot-resolution flowchart, updated `Spec / documentation sync` honestly, standardized `path::Symbol` citations, and expanded acronyms (recommendation strength: strong). |

### Decisions

| ID | Question | Chosen | Alternatives considered | Basis | Reversible |
|---|---|---|---|---|---|
| D-1 | What exact payload must `get_environment`, `get_git`, `get_host`, `get_process_info`, and `get_python_runtime` return when `depth == "off"`? | Return `{"capture_state": {"status": "suppressed"}}` (or with `"detail"` matching `host.py`). | Return `{}` (violates `schemas/manifest.schema.json` `required: ["capture_state"]` on all five sections). | `schemas/manifest.schema.json:790-795,874-879,1170-1195`, `src/pubrun/capture/environment.py:16`, `src/pubrun/capture/git.py:50`, `src/pubrun/capture/host.py:16` | yes |
| D-2 | In what order should `src/pubrun/_config_boot.py::resolve_import_mode` inspect config files? | Search highest-to-lowest precedence (`./.pubrun.toml` -> `./.config/pubrun/config.toml` -> user `config.toml`), returning on the first file providing a valid `[imports].mode` or `[core].auto_start` so local overrides global without opening lower files on the common path. | Always parse and merge all three files (adds extra startup filesystem I/O in `_config_boot.py` when `.pubrun.toml` already answers). | `src/pubrun/_config_boot.py:1-15,79-115`, `src/pubrun/config.py:62-155` | yes |

### Step S6

- Checked: `steps/s6-rereview.md` trigger rules against all Round 1 edits. No `E-*` or `V-*` items were added or removed (still `E-01`..`E-04` and `V-01`..`V-04`), `- Scope-Paths:` and `- Item-Dependencies:` did not change, and a full cross-section sweep confirmed zero stale tokens (`get_process` without `_info`, `_user_config_path`, `load_boot_config`, false `pyproject.toml` claim) and consistent escalation of `PR-001` into `OQ-01` and `05-l7ko8p.json`.

AW-REVIEW: DONE
