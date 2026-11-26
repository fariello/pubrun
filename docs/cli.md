[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)

# pubrun CLI Reference

The `pubrun` CLI is accessible via `pubrun <command>`, `pbr <command>` (a convenient shorthand alias), or `python -m pubrun <command>`. It provides a family of subcommands for setup, post-execution analysis, diagnostics, and benchmarking, plus top-level diagnostic flags. Run `pubrun -h` for the authoritative command list (shown alphabetically).

**Help, shorthand, and global flags:**
- `pubrun help [CMD]` and `pubrun <CMD> help` print top-level or subcommand help.
- Bare `pubrun` (with no subcommand or flag) prints top-level help followed by the number of runs found in the output directory.
- **Selector-first shorthand:** you can place a run selector (index, run-id prefix, or path) before the subcommand, for example `pubrun 1 cpu` (rewritten to `pubrun cpu 1`).
- **Global `--no-color`:** accepted in any position on the command line (sets `NO_COLOR=1` internally). When placed after `pubrun run`, `--no-color` is not consumed by `pubrun` and is passed through to the child command instead.

### Output conventions

pubrun status lines use a consistent set of prefixes so output is easy to scan and grep:

| Prefix | Meaning |
|---|---|
| `[INFO ]` | informational / progress (green) |
| `[ OK  ]` | success (green) |
| `[WARN ]` | warning (yellow) |
| `[ERROR]` | error (red) |
| `[DEBUG]` | debug detail (light blue) — silent unless `PUBRUN_DEBUG` is set |
| `[FAIL ]` | a failed built-in self-test (`--run-tests`) (red) |

Color is optional reinforcement only, and the textual label is authoritative. The status-line
prefixes (`[INFO ]`, `[ OK  ]`, `[WARN ]`, `[ERROR]`, `[DEBUG]`, `[FAIL ]`), `self-check`, and
`inspect` disable color when `NO_COLOR` is set, `--no-color` is passed, or the output stream is
not a terminal. By contrast, `show`, `status`, `res`/`cpu`/`mem`, and `diff` check only
`NO_COLOR` and `--no-color` (not whether stdout is a terminal), and parts of the `status`
summary, `show` report, and `diff` output use dim text. Pass `--no-color` or set `NO_COLOR=1`
when piping or redirecting output from those commands. If you parse pubrun output in a script,
match on the level word (for example `WARN`), not the exact bracketing.

### Selecting a run

Every command that takes a run (`show`/`report`, `res`/`cpu`/`mem`, `methods`, `inspect`,
`rerun`, `diff`, `status`, and `combined`) accepts run selectors from the forms below:

| Form | Example | Meaning |
|---|---|---|
| **Recency index** | `pubrun show 1` | `1` = most recent run, `2` = second most recent, and so on (1-based). A bare positive integer (<= 999). |
| **Run id / prefix** | `pubrun show 8b9dc889` | The full run id or a unique leading prefix. |
| **Directory-name substring** | `pubrun show train-20260509` | A unique substring of the run directory name. |
| **Directory path** | `pubrun show ./runs/pubrun-20260509` | A run directory or its `manifest.json` path (not accepted by `status` or `combined`). |

`status` and `combined` accept only a recency index, a run-id prefix, or a unique substring of
the run directory name, searched within `--dir` or the configured output directory. They do not
accept an arbitrary directory path or a `manifest.json` path. `show`/`report`, `res`/`cpu`/`mem`,
`methods`, `inspect`, `rerun`, and `diff` accept those three selector forms and also accept a
run directory path or a `manifest.json` path directly.

The recency index counts within the current output directory (or the one given by `--dir`
where that flag exists). `pubrun status` shows the index in its leading `#` column, so the
number you see is the number you pass. Omitting the argument entirely selects the most recent
matching run (equivalent to `1`).

A run id being a bare small integer is effectively impossible (ids are timestamp+hash), so the
recency index never collides in practice; in the vanishing case it would, pubrun refuses to
guess and asks you to pass the full id or the directory path.

### Standard run filters

Commands that scan or select runs share a common set of run-filter flags:

| Flag | Description |
|---|---|
| `-f QUERY`, `--filter QUERY` | Include only runs whose script name, arguments, or run id contain `QUERY`. |
| `-F QUERY`, `--not-filter QUERY` | Exclude runs whose script name, arguments, or run id contain `QUERY`. |
| `-s STATUS`, `--status STATUS` | Include only runs with one of the comma-separated statuses (for example `completed,failed`). |
| `-S STATUS`, `--not-status STATUS` | Exclude runs with one of the comma-separated statuses. |
| `--older-than AGE` | Include only runs older than `AGE` (for example `7d`, `24h`, `30m`, `90s`, or `30` for 30 days). |
| `--exit-code CODE` | Include only runs whose exit code equals the integer `CODE`. |
| `-n N`, `--limit N` | Limit selection to the `N` most recent matching runs. |

`-n`/`--limit` is accepted only by `clean`, `combined`, `methods`, `show`/`report`, and `status`.
It is not accepted by `inspect`, `diff`, `rerun`, or `res`/`cpu`/`mem`.

---

## Commands

### `init` — Project Initialization

Creates a `.pubrun.toml` configuration file and displays getting-started guidance.

```bash
pubrun init [DEST]
```

**Options:**

| Argument | Description |
|---|---|
| `DEST` | Destination path (default: `.pubrun.toml`) |

**Example:**
```bash
pubrun init                    # Create .pubrun.toml in current directory
pubrun init ./config/.pubrun.toml  # Custom path
```

After init, add `import pubrun` to your script to begin tracking.

---

### `report-bug` / `feedback` — Report a Bug or Send Feedback

Two commands (same behavior): open the GitHub issue tracker in your default browser and
print system-configuration telemetry to the console for easy copy-paste. `report-bug` is
for bug reports / feature requests; `feedback` is for general feedback — both land as GitHub
issues.

```bash
pubrun report-bug
pubrun feedback
```

> **Changed in 1.4.0:** the old `bug-report` command (and its `issue` alias) were renamed to
> `report-bug`; `feedback` is now its own command rather than an alias.

---

### `cite` — Academic Citation

Generates a formatted citation for crediting `pubrun` in academic publications. The
citation includes the archived Zenodo **concept DOI** (`10.5281/zenodo.20801582`), which
always resolves to the latest archived release.

```bash
pubrun cite [--style apa|mla|chicago|bibtex]
```

**Example:**
```bash
pubrun cite --style bibtex
```

---

### `self-check` — Environment / Install Diagnostics

Report-only checks of the **current machine** for pubrun performance/config pitfalls and
install health. It flags network filesystems (NFS/Lustre/GPFS/CIFS) backing the pubrun
install, output dir, `$TMPDIR`, or Python install (a common cause of slow runs on HPC), low
free RAM, high load, an unwritable output dir, missing `git`, an unsupported Python, and
config errors. It never modifies anything.

It also runs a short **live filesystem probe** (a `statvfs` capacity check in a background
daemon thread, with a ~5s wait budget) and warns if a mount is **wedged/hung** or **slow to
respond**. These warnings are framed honestly as a **system-wide** hazard — a mount that
takes 34s to answer a capacity query will slow *any* script doing I/O there, not just pubrun.
This probe runs only when you invoke `self-check` (or `bench`); it is **never** run by
`import pubrun` or during a normal run, so it can never hang your host script.

**By default it is itemized**: one line per check with its outcome (`[ OK  ]`/`[WARN ]`/
`[INFO ]`) so you can see *what* was checked and how each did, plus a `N checks in 0.0Xs`
timing footer — not just a bare "OK".

```bash
pubrun self-check [--show-suggestions|-v] [--quiet|-q] [--json] [--strict]
```

**Options:**

| Flag | Description |
|---|---|
| `--show-suggestions`, `-v` | Add per-item remediation detail beneath each WARN/INFO check. |
| `--quiet`, `-q` | Print only a one-line verdict instead of the itemized per-check list. |
| `--json` | Emit the full structured result — `checks` (every check + outcome), `findings`, and `elapsed_seconds`. |
| `--strict` | Exit non-zero if any warning fired (useful in CI / HPC job pre-checks). Keys on WARN only, so the HPC login-node `INFO` nudge does not trip it. |

See [Research Use & HPC](hpc.md) for guidance on diagnosing slow runs on clusters.

---

### `inspect` — Post-hoc Run Diagnosis

Report-only reproducibility assessment of a **completed run's** manifest. `inspect` reads
the recorded manifest, first fills in sections from a parent snapshot when the manifest
names one in `meta_ref` (see **Parent snapshots** below), and then
sorts the recorded evidence into seven categories:

| Category | What it looks at |
|---|---|
| Source | Git commit, dirty state, and whether a dirty tree was recorded without its changes. |
| Runtime | Python version and implementation, host, and operating system. |
| Dependencies | Package capture mode, capture status, and recorded package versions. |
| Inputs & Outputs | Files recorded through `pubrun.open()` or the `register_*` APIs, and how strongly each was verified. |
| Capture Completeness | Run outcome, per-section capture status, resource scope, console, subprocess tracking, and seeds. |
| Parent Metadata | Whether the `meta_ref` parent snapshot was found, allowed, recent, and consistent with the child run. |
| Invocation | Script identity, working directory, and whether the rerun command was redacted. |

Each category gets a status (`adequate`, `gaps`, `mismatch`, `uncertain`, or `not_checked`).
There is no numerical reproducibility score. `inspect` also lists findings, a prioritized
**next step**, and the recorded signals from the run (filesystem type, memory, load). It
prints a glaring banner when the inspecting host differs from where the run executed (for
example an HPC login node versus a compute node), because live re-checks then reflect the
wrong machine.

Output is **terse by default** (a summary, the categories that need attention, the next
step, and the non-guarantee note); use `--show-suggestions` for per-category, per-check,
and per-finding detail, or `--json` for the complete structured assessment.

```bash
pubrun inspect [RUN_DIR] [--show-suggestions|-v] [--preflight] [--json] [--strict] [--fail-on {warn,mismatch,unknown}] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE]
```

**Options:**

| Flag | Description |
|---|---|
| `RUN_DIR` | Run directory to inspect. Defaults to the most recent matching run. |
| `--show-suggestions`, `-v` | Show per-category status, preflight checks, and per-finding detail with next steps. |
| `--preflight` | Also compare supported recorded requirements against the current machine (read-only and offline; see below). |
| `--json` | Emit the full structured reproducibility assessment as JSON (top-level `findings` is preserved). |
| `--strict` | Exit `1` when the strict threshold triggers. The threshold is `warn` unless `--fail-on` is given. |
| `--fail-on {warn,mismatch,unknown}` | Set the strict threshold. Passing `--fail-on` turns on strict exit checking by itself (no `--strict` needed) and works with or without `--preflight`. |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code` | Standard run selectors (which single run to inspect). |

**Evidence statuses:** every category, finding, and preflight check says where its evidence
came from:

| Status | Meaning |
|---|---|
| `observed` | pubrun measured it directly on the run (or, during preflight, on this machine). |
| `inferred` | Derived indirectly, for example a command reconstructed from `.pubrun.lock` or an input guessed from `argv`. |
| `asserted` | Supplied by the caller (for example a digest passed to `register_input()`) and not verified by pubrun. |
| `inherited` | Copied from a parent `meta_ref` snapshot rather than observed on the child run. |
| `unavailable` | pubrun tried to obtain it and could not (capture failed, a file is missing, a snapshot was blocked). |
| `not_checked` | Not evaluated, for example capture was off or a file was recorded by path or size only. |

`unavailable` and `not_checked` are never reported as a match: unknown is not the same as
verified.

**Preflight (`--preflight`):** compares what the run recorded with the machine you are on now.
It checks Python version and implementation, platform, recorded package versions, source
state (Git commit, dirty tree, script digest), accessible input files (existence, size, and
digest when one was recorded), the working directory, and command redaction. Each check is
`match`, `mismatch`, `portability_diff` (an expected difference such as a different hostname
or a newer Python patch release), `unknown`, or `not_checked`. Preflight is read-only and
offline: it never runs the recorded command, never installs or fetches anything, never
contacts the network, and never changes files, environment variables, or random seeds. It
only reads files and runs local `git` queries.

**Strict thresholds (`--strict` / `--fail-on`):** without either flag, `inspect` exits `0`
after a successful assessment, whatever it found.

| Threshold | Exits `1` when |
|---|---|
| `warn` (default for `--strict`) | Any finding has severity `warn`, including portability differences such as a different host. |
| `mismatch` | Any finding or preflight check is a `mismatch`, or any `warn` finding has `material` impact. Portability-only warnings pass. |
| `unknown` | Anything `mismatch` catches, plus any preflight check that is `unknown` or `not_checked`. Without `--preflight`, also any category that is `uncertain` or `not_checked`. |

**JSON output (`--json`):** a single object with these ten top-level keys:

| Key | Contents |
|---|---|
| `schema_version` | Assessment format version (currently `"1.0"`). |
| `mode` | `"manifest"`, or `"preflight"` when `--preflight` was given. |
| `summary` | One-sentence overall summary. |
| `next_action` | The single highest-value next step. |
| `next_actions` | All suggested next steps, highest priority first. |
| `disclaimer` | The non-guarantee note (always present). |
| `categories` | Seven objects with `name`, `label`, `status`, `evidence_status`, `summary`, `finding_codes`, `warn_count`, and `info_count`. |
| `findings` | Objects with `severity`, `code`, `message`, `suggestion`, `category`, `evidence_status`, `impact` (`material`, `portability`, `incidental`, or `informational`), `comparison`, and `details`. |
| `parent_metadata` | The parent snapshot report: `meta_ref`, `resolved_path`, `status`, `inherited_sections`, `direct_sections`, `parent_started_at_utc`, `child_started_at_utc`, `age_seconds`, `script_modified_after_parent`, `identity_mismatches`, and `warnings`. |
| `preflight` | `requested`, `status`, `counts` per outcome, and `checks`. When `--preflight` is not given, `requested` is `false` and `status` is `"not_checked"`. |

> **Not a guarantee:** recorded provenance and an absence of findings support reproduction
> analysis, but they do not guarantee equivalent scientific or bitwise results, especially for
> legacy or sparse manifests. Every output form says so.

**Parent snapshots (`meta_ref`):** when the manifest names a parent `meta.json`, `inspect`
fills sections the child did not capture (hardware, process, python, packages, environment,
git, host) from the parent, in memory only; `manifest.json` is never modified. Inherited sections
are reported as `inherited`, not `observed`. The Parent Metadata category reports whether the
snapshot was missing, blocked by the `[report]` path policy, invalid, older than one day,
newer than the child run, or inconsistent with what the child observed directly (for example
hostname or Python version). A script modified after the parent snapshot is flagged, but an
unchanged script modification time does not prove the dependencies matched. See
[HPC](hpc.md#diagnosing-a-finished-run) and [Manifest](manifest.md#meta-snapshot).

> **Honesty note:** pubrun does not patch `open()` or subprocess globally, so file-I/O and
> subprocess provenance are recorded only when the script uses `pubrun.open()`, explicit
> external file registration (`pubrun.register_input()`, `pubrun.register_output()`, or
> `pubrun.register_file()`), or `pubrun.subprocess`. `inspect` does not claim a feature was
> "off" when the manifest merely shows no records unless it can determine this definitively.

**File-provenance findings:** `inspect` evaluates recorded `data_files` (`inputs`, `outputs`, and `mixed`) by evidence strength and hashing outcome:

- **`WARN` findings (fail `--strict`):** `file_provenance_changed` (a tracked file changed between access and hashing) and `file_provenance_hash_failed` (content hashing failed, a target was unavailable, or a verified caller-supplied digest did not match).
- **`INFO` findings (do not fail `--strict`):** `no_file_provenance` (no files were recorded), `file_provenance_unverified_paths` (files recorded by path/stat metadata only or pending outputs without content hashes), `file_provenance_asserted_only` (caller-asserted digests not independently verified by pubrun), and `file_provenance_over_budget` (files skipped because hashing size or time budgets were exceeded).

**Example:**
```bash
pubrun inspect                          # diagnose the most recent run
pubrun inspect runs/pubrun-XYZ -v       # full detail for a specific run
pubrun inspect -f train.py --json       # latest run matching "train.py", as JSON
pubrun inspect runs/pubrun-XYZ --preflight                    # compare against this machine
pubrun inspect runs/pubrun-XYZ --preflight --fail-on mismatch # CI or job gate: exit 1 on material mismatch
pubrun inspect runs/pubrun-XYZ --preflight --json | jq '.preflight.status'
```

---

### `bench` — Overhead Benchmark Runner

Friendly front-end over the benchmark harness (`benchmarks/harness.py`). Runs the suite
locally by default; on an HPC login node it detects the batch scheduler (**Slurm, PBS/Torque,
LSF, or SGE/Grid Engine**) and **offers** to submit to a compute node (and never submits
without confirmation; on Slurm it can wait for completion and then contribute from the login
node). By default it writes **only a redacted, share-safe** result file (`*.redacted.json`)
and, on an interactive terminal, offers to contribute it to `fariello/pubrun`.

**Requires a source checkout** (the benchmark tooling is intentionally not shipped in the
pip package to keep installs lightweight). Clone the repo and run from it.

```bash
pubrun bench [--quick | --full | --rigorous] [--no-baseline] [--iterations N] [--passes N]
             [--local | --submit] [--scheduler {auto,slurm,pbs,lsf,sge,local}] [-y|--yes]
             [--unredacted] [--json] [--contribute | --no-contribute]
             [--prepare-submission] [--wait-timeout SECONDS] [--no-submit] [--gh-repo O/N]
pubrun bench --submit-file FILE [--contribute | --no-contribute] [--prepare-submission] [--gh-repo O/N]
```

Every run begins with one **uncaptured baseline pass** (pubrun absent) that warms caches and
records the cost floor, followed by N measured passes of M iterations. Three tiers:

| Tier | Passes x iterations | Use |
|---|---|---|
| `--quick` | baseline + 2 x 15 | fast smoke check |
| `--full` (default) | baseline + 3 x 30 | the standard run |
| `--rigorous` | baseline + 5 x 50 | tight confidence intervals; can take many minutes |

The result JSON records `mode`, `baseline_pass`, the baseline sweep (separately, so it never
mixes into pubrun-overhead stats), and `total_wall_time_s` (whole-invocation wall time).

**Options:**

| Flag | Description |
|---|---|
| `--quick` / `--full` / `--rigorous` | Select a tier (see table above; `--full` is the default). |
| `--no-baseline` | Skip the initial uncaptured baseline pass (the pubrun-absent reference sweep). |
| `--iterations N` | Override iterations per scenario (takes precedence over the tier). |
| `--passes N` | Override the number of measured sweeps (default depends on tier: quick=2, full=3, rigorous=5). |
| `--local` | Run here even if an HPC scheduler is detected. |
| `--submit` | Submit the benchmark job to the detected HPC scheduler without prompting (no effect off HPC; never implies GitHub contribution). |
| `--scheduler {auto,slurm,pbs,lsf,sge,local}` | Which HPC scheduler to submit to (default `auto`). `local` forces a local run. Use to resolve the PBS-vs-SGE `qsub` ambiguity. |
| `-y`, `--yes` | Assume "yes" to the HPC scheduler submit prompt (never implies GitHub contribution). |
| `--unredacted` | Also write the identifying, unredacted result (`*.unredacted.json`, embeds hostname/paths; for local debugging only, do not share). By default only the redacted file is written. |
| `--json` | Emit the redacted/unredacted result paths as JSON. |
| `--contribute` | Publish the share-checked redacted result to GitHub after the run without prompting (uses `gh`: unlisted Gist linked from an issue, or inline if small). |
| `--no-contribute` | Never offer or attempt GitHub publication. |
| `--prepare-submission` | Copy only the redacted (safe) file into a clean `pubrun-share/` folder for a manual browser attachment via the Issue Form. |
| `--submit-file FILE` | Contribute an existing **redacted** result file (share-check + publish or prepare), without running a benchmark. |
| `--wait-timeout SECONDS` | For Slurm submit-and-wait: how long the login-node process waits for the queued job before pointing you at `--submit-file` (default ~1800s; `0` = wait forever). |
| `--no-submit` | Skip the end-of-run contribution offer entirely. |
| `--gh-repo OWNER/NAME` | Target GitHub repo for the contribution (default `fariello/pubrun`). |

**HPC scheduler submission.** On a login node, `pubrun bench` auto-detects the batch scheduler
(Slurm, PBS/Torque, LSF, or SGE/Grid Engine; precedence Slurm > PBS > LSF > SGE) from
environment variables and submit tools on `PATH` (no scheduler is queried and no network call
is made at detection). If one is found and you are not already inside an allocation, it prints
the exact submit command and prompts before submitting (never submits without `--submit`/`--yes`
or an interactive "y"). On Slurm, after submission, the login-node process polls for completion
(bounded by `--wait-timeout`), then runs the share-check and contribution offer from the login
node; if interrupted or timed out, finish later with `--submit-file`. Because PBS and SGE both
use `qsub`, an ambiguous environment is reported and you resolve it with `--scheduler pbs|sge`.
The per-scheduler submit scripts under `benchmarks/` (`submit_bench.sh`, `submit_bench_pbs.sh`,
`submit_bench_lsf.sh`, `submit_bench_sge.sh`) are starting points to adapt to your site.

**Contributing a result (consent-gated).** After a run, `pubrun bench` runs a structural
share-safety check (`benchmarks/share_safety.py`), prints a safe-file block, and on an
interactive terminal offers to publish the redacted result to `fariello/pubrun` (Enter accepts;
pass `--contribute` or `--no-contribute` to pre-decide). When publishing, it uses the GitHub
CLI (`gh`): it creates an unlisted Gist of the redacted file and opens an issue linking the raw
URL, falling back to embedding the JSON inline when under GitHub's ~65 KB body cap, and finally
to the browser Issue Form (`https://github.com/fariello/pubrun/issues/new?template=benchmark-result.yml`)
when `gh` is unavailable. A validate-only GitHub Actions workflow checks the submission as data
only and posts a pass/fail receipt; maintainers collect accepted results locally via
`benchmarks/pull_submissions.py` into `benchmarks/data/`.

**"Submit later" / HPC recovery.** Because the redacted file persists on disk, you can submit
it later without re-running:

```bash
pubrun bench --submit-file benchmarks/results/pubrun-bench-<hash>-<ts>.redacted.json
```

**Safety.** pubrun never auto-transmits an unredacted result: by default only `*.redacted.json`
is written, and the contribution path re-runs `share_safety` immediately before sending and
refuses any file that fails. The redacted copy masks hostname, OS username, and every
home-directory path while preserving analysis-relevant data (CPU/GPU model, timings,
versions, filesystem type, Slurm partition). Even redacted, a distinctive CPU/GPU model plus
a named Slurm partition can be re-identifying in a small group. See
[HPC & performance diagnosis](hpc.md) and `benchmarks/README.md` for more.

**Example:**
```bash
pubrun bench --quick --local                           # quick local run, then offers to contribute
pubrun bench --quick --contribute                      # run and publish via gh without prompting
pubrun bench --prepare-submission                      # stage redacted file in pubrun-share/ for browser attach
pubrun bench --submit-file res.redacted.json           # contribute a previously produced redacted file
```

---

### `clean` — Run Cleanup

Interactively delete old run directories. Lists candidates with their age and size, then prompts for confirmation before removal.

```bash
pubrun clean [--dir PATH] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE] [-n N] [-y|--yes] [--dry-run]
```

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the output directory to scan |
| `--older-than AGE` | Only consider runs older than AGE (e.g. `7d`, `24h`, `30m`, `90s`, `30` for 30 days). Units are `d` (days), `h` (hours), `m` (minutes), and `s` (seconds); a bare number means days. An invalid, empty, or negative AGE is an error and deletes nothing |
| `-s`, `--status STATUS` | Comma-separated status filter (e.g. `completed,failed`). Without `--status`, `clean` selects all non-running runs (`completed`, `failed`, `interrupted`, `broken pipe`, `crashed`, and `ghost`) |
| `-f`/`--filter`, `-F`/`--not-filter`, `-S`/`--not-status`, `--exit-code`, `-n`/`--limit` | See [Standard run filters](#standard-run-filters) |
| `-y`, `--yes` | Skip confirmation prompt (non-interactive mode) |
| `--dry-run` | Show what would be deleted without actually deleting |

Running processes are never deleted, even if explicitly included in `--status`.

**Interactive mode** (default): displays a numbered list with exit codes, args, age, and size. The user must explicitly select runs by number, range (e.g. `1-3,5`), or type `all`. The selected runs are then displayed in a confirmation table before a final `y/N` prompt. Nothing is deleted without explicit confirmation.

**Example:**
```bash
pubrun clean                              # Interactive: list and confirm
pubrun clean --older-than 7d --yes        # Non-interactive: delete every non-running run older than 7 days
pubrun clean --status crashed,ghost --yes # Delete all crashed/ghost runs
pubrun clean --dry-run                    # Preview without deleting
```

---

### `combined` — Log Interleaver

Post-execution command that chronologically interleaves stdout and stderr logs from one or more runs using the log-line timestamps written in `standard` or `deep` console mode.

```bash
pubrun combined [RUN_ID ...] [--dir PATH] [--output FILE] [-y|--yes] [--force] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE] [-n N]
```

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the output directory to scan (default: configured `output_dir` or `./runs`) |
| `--output FILE` | Write combined logs to this file instead of stdout |
| `-y`, `--yes` | Skip confirmation prompt for files > 250 MB |
| `--force` | Force execution for files > 500 MB |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code`, `-n`/`--limit` | See [Standard run filters](#standard-run-filters) (select which runs to combine when no run IDs are given) |

> **Changed in 1.4.0:** `combined -f` now means `--filter` (consistent with every other command). The force flag is now `--force` (long form only). Previously `-f` meant `--force`.

- If multiple run IDs are supplied, each output line is prefixed with the run ID and stream origin, e.g. `[runA][stdout]`.
- If a single run is combined, each output line is prefixed with the stream origin only, e.g. `[stdout]`.
- If the logs lack timestamps (captured with `"basic"` console mode), it falls back to sequential concatenation and prints a warning.

**Example:**
```bash
pubrun combined a3f9               # Interleave stdout/stderr for run a3f9
pubrun combined a3f9 b2c1 --output all.log  # Combine multiple runs into a file
```

---

### `diff` — Semantic Comparison

Generates a structural comparison between two execution traces, filtering volatile noise
(timestamps, PIDs, per-run absolute paths) so the *meaningful* differences stand out.

```bash
pubrun diff [RUN_DIR_A [RUN_DIR_B]] [OPTIONS]
```

**Depth levels** — each level is nested: `--basic` hides the most, `--deep` hides nothing.

| Flag | What it shows |
|---|---|
| `--basic` | The user-facing, high-signal differences only: script/argv, python, git, user config. Hides volatile fields and the high-volume sections (process, hardware, resources, environment, subprocesses, packages). A single `argv` change is reported once (not also as `command_line`/`rerun_command`, which are derived from it). |
| `--standard` (default) | The above plus hardware/resource changes and **summarized** list sections — e.g. `subprocesses.count: 300 → 302` and `subprocesses.by_command.bash: +2`, rather than thousands of per-process leaf lines. |
| `--deep` | No filtering; every field, every subprocess element, and the derived `command_line`/`rerun_command` are compared. |

**Other options:**

| Flag | Description |
|---|---|
| `--table` | Render a compact aligned table (`change / field / A → B`) instead of the default git-style `+/-/~` lines. |
| `--same` / `--no-same` | Show or hide unchanged values |
| `--wrap` / `--no-wrap` | Wrap long strings or truncate with ellipsis |
| `--max-length N` | Maximum character length before truncation |
| `--no-color` | Disable ANSI color output |
| `--export [txt\|json]` | Export flattened key-value output for external diff tools (e.g., `meld`, VS Code) |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code` | Standard run filters. When run directories are omitted, the auto-selected pair is drawn from the runs matching these filters (with no filters, from all runs — the historical behavior) |

**Run arguments:** `diff` accepts zero, one, or two run arguments:
- **Zero arguments:** compares the two most recent runs with a `manifest.json` (drawn from runs matching the standard run filters when given).
- **One argument:** compares that run with the most recent other run that has a `manifest.json` (matching the standard run filters when given).
- **Two arguments:** compares `RUN_DIR_A` and `RUN_DIR_B`.
- **More than two arguments:** arguments after the second are ignored.

If a filter matches fewer than two runs (or no other run when one argument is given), `diff` reports a clear error and exits non-zero rather than silently ignoring the filter.

> **Changed in 1.4.0:** `--basic` and `--standard` are now genuinely concise — they no longer
> explode subprocess-heavy runs into thousands of lines, and they hide per-run volatile paths
> and the derived `command_line`/`rerun_command` (shown only at `--deep`). `--deep` output is
> unchanged. If you parse diff output, use `--deep` for the full element-by-element detail.

**Example:**
```bash
pubrun diff ./runs/pubrun-A ./runs/pubrun-B --same --wrap
pubrun diff -f train.py            # diff the two most recent runs whose command matches "train.py"
pubrun diff A B --table            # compact aligned table view
```

---

### `meta` — Global Environment Snapshot

Generates a standalone `meta.json` snapshot of the current environment (hardware, packages, git, environment variables) without running any script. Designed for HPC parent-child hydration workflows.

```bash
pubrun meta [--out PATH] [--basic|--standard|--deep]
```

- If `--out` is omitted, writes to `./runs/meta.json`.
- Default depth is `--deep` (captures full virtual environment).
- The console output **itemizes each gathered section** (hardware, python, packages, git,
  environment, host) with an `[ OK  ]`/`[WARN ]` outcome and per-section timing, plus a total,
  so you can see what was collected. A section that fails to capture cleanly is shown as
  `[WARN ]`. The `meta.json` file remains the complete source of truth.

**Example:**
```bash
pubrun meta --out ./shared/meta.json --deep
```

---

### `methods` — Academic Methodology Writer

Compiles a run's manifest into a publication-ready "Computational Methods" paragraph in Markdown or LaTeX.

```bash
pubrun methods [RUN_DIR] [--format markdown|latex] [--all] [-n N] [-f/-F/-s/-S ...]
```

- If `RUN_DIR` is omitted, automatically uses the **most recent** run in `./runs/` (the default, single-run behavior). Run filters (`-f`, `-F`, `-s`, `-S`, `--older-than`, `--exit-code`) still select the most-recent *matching* run.
- If the manifest references a `meta_ref`, the parent context is hydrated before generating the output.
- When a run (or aggregated `--all` set) records tracked `data_files`, `methods` adds a concise file-provenance evidence breakdown that distinguishes independently verified content digests from caller-asserted digests, path or stat-only identifications, over-budget skips, pending outputs, and changed or failed hashes. When no `data_files` are recorded, the output is unchanged.

**Aggregating many runs (`--all`):** for a study run many times (sweeps, seeds, folds), `pubrun methods --all` aggregates the whole matching set into **one** representative paragraph plus a variance note listing only the fields that differ across runs (OS, CPU, RAM, Python, git commit, pubrun version, packages). If the runs are environment-homogeneous, the output reads like the single-run paragraph with "across N runs" added.

- Bound/curate the set with the shared run filters: `-n N` (most-recent N), `-f`/`-F` (include/exclude by script/args/**run-id**), `-s`/`-S` (by status). A differing git commit across the set is *disclosed as variance*, never an error.
- When more than 25 runs are aggregated (the built-in threshold) or when at least one matching run had an unreadable or missing manifest and was skipped, `pubrun methods --all` prints a note to stderr, **clearly marked as not part of the methods section** (so it cannot be pasted into a paper). This note respects `NO_COLOR`.
- **Note the difference from `show`:** bare `pubrun show` (no run dir, filter, or `-n`) reports only the single most recent run, and `pubrun show` with run filters or `-n` prints a *separate report per matching run*; `pubrun methods` stays single-run unless you pass `--all`, and then produces *one aggregated paragraph*. This is deliberate: a methods section is a single publication artifact, so aggregation is opt-in.

**Examples:**
```bash
pubrun methods ./runs/pubrun-train-20260509-a1b2 --format latex
pubrun methods --all -f train.py            # one paragraph across all train.py runs
pubrun methods --all -n 20 -s completed      # aggregate the 20 most-recent completed runs
```

---

### `show` — Diagnostic Viewer

Renders a human-readable diagnostic summary of one or more runs, including timing, hardware, dependencies, codebase drift, and an event timeline.

```bash
pubrun show [RUN_DIR] [logs|env|packages] [--basic|--standard|--deep] [--utc] [run filters] [-n N]
pubrun show config [--all] | show run config [<id>] [--all] | show default config
```

**Alias:** `report` (hidden backward-compatible alias). `report` accepts the same depth flags (`--basic`, `--standard`, `--deep`), `--utc`, [Standard run filters](#standard-run-filters), and `-n`/`--limit`, as well as `logs`/`env`/`packages` section extracts. It does not accept `--all` and has no third positional argument, so `pubrun report run config <id>` is not accepted.

- With no `RUN_DIR`, run filter, or `-n`/`--limit`, `pubrun show` reports the single most recent run.
  When `RUN_DIR` is omitted, passing any run filter (`-f`, `-F`, `-s`, `-S`, `--older-than`, `--exit-code`)
  or `-n`/`--limit` prints a separate report for every matching run (up to `N` most recent matches when
  `-n N` is given). `RUN_DIR` must be omitted for filters or `-n` to select several runs.
- **Section extracts (`logs`, `env`, `packages`):** pass `logs`, `env`, or `packages` after `RUN_DIR` to
  print only that section (captured console logs, environment variables, or recorded packages). A bare
  section name in the `RUN_DIR` position (for example `pubrun show env`) selects the most recent matching
  run and prints that section.
- If the manifest references a `meta_ref`, the parent context is hydrated automatically.
- Timestamps display in **local time** by default; pass `--utc` for UTC. Both local and `--utc`
  timestamps use the compact `YYYY-MM-DD HH:MM:SS` form without a trailing `Z` suffix.
- The **event timeline** shows all events when there are ≤ 20; above that, it shows the
  oldest 10 and newest 10 with a `... [ N events truncated ] ...` marker between them.

**Depth Controls:**

| Flag | Scope |
|---|---|
| `--basic` | Timing and outcome only |
| `--standard` | Hardware, Git, Python, dependency summary, and `Data Files` evidence-category counts when tracked files exist (default) |
| `--deep` | Full environment variables, complete package list, subprocesses, and `[ Data Files ]` per-file listing with evidence badges (`[verified]`, `[asserted]`, `[metadata-only]`, `[path-only]`, `[over-budget]`, `[pending]`, `[changed]`, `[unavailable]`, `[failed]`), abbreviated digests, and anomaly details |

**Reproducibility summary:** `--standard` and `--deep` reports include a short
`--- Reproducibility ---` block from the same assessment `pubrun inspect` uses: the summary, the
evidence categories that need attention, sections inherited from a `meta_ref` parent snapshot
(with a note that an unchanged script modification time does not prove matching
dependencies), the next step, and the non-guarantee note. `show` never runs a preflight
comparison; the block points to `pubrun inspect --preflight` for that. The block is omitted
from `--basic` and from section extracts (`logs`, `env`, `packages`).

#### `show config` — inspect resolved configuration

`show` also renders the resolved pubrun **configuration** for three distinct contexts, so you
can see exactly what settings are (or were) in effect and how any ambiguity resolved:

```bash
pubrun show config                 # what "import pubrun" would use RIGHT NOW in this directory
pubrun show run config [<id>]      # the config a PAST run actually used (default: most recent)
pubrun show default config         # the shipped built-in defaults only
```

- **`show config`** resolves the full hierarchy (built-in defaults + user config + local
  `.pubrun.toml` + environment variables) as of now, relative to the current directory. Because
  it reflects the *ambient* environment at invocation time, a specific run may have differed;
  use `show run config` for a past run's exact config.
- **Ambiguity surfacing:** by default, only keys whose value was **overridden** by a
  higher-precedence layer are annotated, e.g.
  `capture.hardware.depth = 'off'    [local, overrides built-in 'basic']`. A config with no
  conflicts prints clean. Add `--all` to annotate every key with its source layer.
- **`show run config [<id>]`** accepts the same run selectors as other commands (recency index,
  id prefix, path). A run that **crashed before finalizing** shows its startup snapshot, labeled
  `from startup snapshot (run did not finalize...)`; a **ghost** run (one that could not write to
  disk) has no recorded config and reports a clear error.
- **`show default config`** is the canonical replacement for the deprecated `--show-config` flag.

The keywords `config`, `run`, and `default` are recognized in these forms before run selection,
so `pubrun show config` shows the current config rather than searching for a run named "config".
A run whose id genuinely starts with one of these words must be selected by its full id or path.

---

### `rerun` — Reproducibility Command

Extracts the exact shell command needed to re-execute a recorded run.

```bash
pubrun rerun [RUN_DIR] [--preflight [--strict] [--fail-on {warn,mismatch,unknown}] [--json]] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE]
```

Prints the `rerun_command` from the manifest to stdout. Internal log messages go to stderr, so this is safe for piping:

```bash
pubrun rerun ./runs/pubrun-A | bash
```

pubrun never runs the recorded command itself. It only prints it.

**Options:**

| Flag | Description |
|---|---|
| `RUN_DIR` | Run to read. Defaults to the most recent matching run. |
| `--preflight` | Before printing the command, run the same read-only, offline preflight comparison as `pubrun inspect --preflight`. Diagnostics go to stderr. |
| `--strict` | Requires `--preflight`. If the strict threshold triggers, exit `1` and print nothing to stdout. The threshold is `warn` unless `--fail-on` is given. |
| `--fail-on {warn,mismatch,unknown}` | Requires `--preflight`. Set the strict threshold; implies `--strict`. Thresholds are the same as for [`inspect`](#inspect--post-hoc-run-diagnosis). |
| `--json` | Requires `--preflight`. Print one JSON object to stdout instead of the bare command. |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code` | See [Standard run filters](#standard-run-filters) (select which run to read when `RUN_DIR` is omitted; `-n`/`--limit` is not accepted). |

**Behavior:**

- **Default (no flags):** unchanged. stdout contains only the command, so `pubrun rerun | bash`
  keeps working.
- **Invalid combinations:** `--strict`, `--fail-on`, or `--json` without `--preflight` prints an
  error to stderr, prints nothing to stdout, and exits `2`.
- **`--preflight`:** the reproducibility summary, and an advisory when the command contains
  `[REDACTED]` placeholders, go to stderr. stdout still contains only the command, so piping
  still works. A redacted command is not directly executable: supply the redacted argument
  values yourself before running it.
- **`--preflight --strict` (or `--fail-on`):** when the threshold triggers, the command exits
  `1` with empty stdout, so `pubrun rerun --preflight --strict | bash` runs nothing.
- **`--preflight --json`:** stdout is an object with three keys: `rerun_command` (the printed
  command), `executable_as_printed` (`false` when the command contains `[REDACTED]`), and
  `assessment` (the same ten-key object `pubrun inspect --preflight --json` prints). With
  `--strict` or `--fail-on`, the JSON is still printed and the exit code is `1` when the
  threshold triggers.
- **Running or crashed runs:** a run without `manifest.json` falls back to the command
  reconstructed from `.pubrun.lock`, with a warning on stderr. Under `--preflight`, that command
  is reported as `inferred` and the comparison is `unknown`, because preflight needs a finalized
  manifest; `--json` reports `preflight.status = "unknown"`, and `--strict` or `--fail-on` exits
  `1`.

**Examples:**

```bash
pubrun rerun runs/pubrun-XYZ --preflight                          # summary on stderr, command on stdout
pubrun rerun runs/pubrun-XYZ --preflight --fail-on mismatch | bash # run only if no material mismatch
pubrun rerun runs/pubrun-XYZ --preflight --json                    # structured result
```

---

### `res` — Resource Monitoring (comprehensive)

> `resources` is a backward-compatible alias of `res` (`pubrun resources` behaves identically).

Renders a **comprehensive** resource summary for a run plus CPU and memory utilization
graphs. Unlike `cpu`/`mem` (which focus on a single metric), `res` surfaces **all** captured
resource signals, each shown only when present in the manifest. Where per-sample data exists
(`events.jsonl`), each metric shows **peak / avg / min** on one line; otherwise it falls back
to the recorded peak:

- **main-process** RSS (`RSS (main)`) and CPU% (`CPU (main)`), plus end RSS,
- **process-tree** RSS (`RSS (tree)`) and CPU% (`CPU (tree)`) when the run used
  `[capture.resources].scope = "tree"`. Tree CPU is computed from summed CPU-time deltas
  across the tree and is labeled *"% of one core"* — it may legitimately exceed 100% on
  multiple cores (it is not clamped). Tree CPU is Linux-only; where unmeasured it is omitted.
- **system memory** — available RAM at start and the lowest point during the run,
- **load average** (start and 1-min peak),
- **node iowait** (labeled *node-wide, indicative only* — a whole-node hint, not run-scoped),
- **per-process I/O volume** — bytes read/written (storage layer and logical), from
  `/proc/self/io` (Linux).

```bash
pubrun res [RUN_DIR] [--average] [-l LAST] [-w WIDTH] [run filters]
```

**Options** (shared by `res`, `cpu`, and `mem`):

| Flag | Description |
|---|---|
| `--average` | Plot average/mean values instead of the default per-bucket maximum. |
| `-l`, `--last DURATION` | Only chart the last window of the run (e.g. `10m`, `2h`, `30s`). |
| `-w`, `--width N` | Override the chart width in columns. |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code` | Standard run selectors (pick which run to chart when no `RUN_DIR` is given). |

- `RUN_DIR` may be a recency index (`1` = most recent), an id prefix, or a path; if omitted,
  the most recent matching run is used.
- Parses `resource_sample` events from `events.jsonl` to render utilization timelines.
- Older runs (before these fields were captured) simply show fewer lines — no error.

The `cpu` and `mem` commands show a single focused chart; `res` shows the full picture.

**Example:**
```bash
pubrun res ./runs/pubrun-train-20260509-a1b2
pubrun cpu                    # CPU chart only (most recent run)
pubrun mem -w 120             # Memory chart, custom width
```

---

### `cpu` — CPU Utilization Chart

Renders the CPU utilization history for a run. Standalone shortcut for the CPU portion of `res`; takes the same options (`--average`, `-l/--last`, `-w/--width`, and the standard run selectors).

```bash
pubrun cpu [RUN_DIR] [--average] [-l LAST] [-w WIDTH] [run filters]
```

---

### `mem` — Memory Utilization Chart

Renders the memory (RSS) utilization history for a run. Standalone shortcut for the memory portion of `res`; takes the same options (`--average`, `-l/--last`, `-w/--width`, and the standard run selectors).

```bash
pubrun mem [RUN_DIR] [--average] [-l LAST] [-w WIDTH] [run filters]
```

---

### `run` — Import Mode Wrapper

Spawns a child process with `PUBRUN_RUN_MODE_OVERRIDE` and `PUBRUN_IMPORT_MODE` set in the environment so the launch-time `--mode` value overrides explicit in-code `import pubrun.<mode>` imports. Setting `PUBRUN_IMPORT_MODE` alone without `PUBRUN_RUN_MODE_OVERRIDE` still yields to explicit submodule imports. Useful for CI pipelines, shell scripts, Slurm submissions, and any case where you want to control pubrun behavior without modifying source code.

```bash
pubrun run [--mode MODE] -- COMMAND [ARGS...]
```

**Options:**

| Flag | Description |
|---|---|
| `--mode MODE` | Import mode for the child process: `auto` (default), `full` (capture everything incl. console), `noauto`, `nopatch`, `noconsole`, or `minimal` |

The double dash (`--`) separates pubrun wrapper options from the target command.

**Example:**
```bash
pubrun run --mode minimal -- python script.py      # No auto-start in child
pubrun run --mode nopatch -- python train.py     # Auto-start but no hooks
pubrun run --mode noconsole -- python train.py   # Auto-start but no console wrap
pubrun run -- python script.py                   # Default auto mode
```

The wrapper returns the child process exit code. It does not create a run in the wrapper process itself.

---

### `status` — Run Monitoring

Lists all runs in the output directory with their current status, or inspects a specific run in detail. Classifies runs as completed, failed, interrupted, broken pipe, running, crashed, or ghost via lock-file PID liveness checks. When a crashed run still has a `.pubrun.lock` file (its process is no longer alive), `pubrun status` closes it out by writing or updating `manifest.json` and removing `.pubrun.lock`, so this command can modify run directories.

```bash
pubrun status [RUN_ID] [--dir PATH] [-v|--verbose] [--utc] [-f QUERY] [-F QUERY] [-s STATUS] [-S STATUS] [--older-than AGE] [--exit-code CODE] [-n N]
```

**Modes:**

| Usage | Description |
|---|---|
| `pubrun status` | Compact table listing all runs (leading `#` recency index, ID, script, commit, started, status, exit code, elapsed) |
| `pubrun status -v` | Verbose listing with PID, hostname, RSS, CPU, events, signals, and directory |
| `pubrun status <run-id>` | Detailed inspection of a single run (supports prefix matching) |

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the output directory to scan (default: configured `output_dir` or `./runs`) |
| `-v`, `--verbose` | Show detailed information for each run in the listing |
| `--utc` | Display timestamps in UTC (`YYYY-MM-DD HH:MM` with a trailing `Z` suffix) instead of local time. Timestamps are always stored as UTC epochs; this only affects display. Also available on `pubrun show` (which omits the `Z` suffix). |
| `-f`/`--filter`, `-F`/`--not-filter`, `-s`/`--status`, `-S`/`--not-status`, `--older-than`, `--exit-code`, `-n`/`--limit` | See [Standard run filters](#standard-run-filters). |

**Status Values:**

| Status | Meaning |
|---|---|
| `completed` | Run finished successfully (manifest exists, outcome is "completed") |
| `failed` | Run finished with an error (manifest exists, outcome is "failed") |
| `interrupted` | Run received a termination signal — SIGINT (Ctrl+C), SIGTERM, or SIGHUP |
| `broken pipe` | Run completed but received SIGPIPE (downstream reader closed) |
| `running` | Lock file exists and the process is still alive |
| `crashed` | Lock file exists but the process is dead (killed without cleanup) |
| `ghost` | Run entered ghost mode (filesystem write failure) |

**Example:**
```bash
pubrun status                    # List all runs
pubrun status -v                 # Detailed listing
pubrun status a3f9               # Inspect run by ID prefix
pubrun status --dir /shared/runs # Scan a different directory
pubrun status -n 10              # Show last 10, full summary
```

The listing ends with a colored summary line showing total run count, date range, status frequencies, and non-zero exit codes:

```
504 runs | 2026-05-31 13:57 to 2026-07-04 14:31
  488 completed, 10 interrupted, 3 crashed, 3 broken pipe | exit 1: 10
```

When using `-n` to limit displayed rows, the summary still reflects all runs (with "(showing N)" appended).

For running processes, the inspect view also shows live RSS memory and CPU usage (cross-platform: Linux, macOS, Windows).

---

### `ui` — Interactive Dashboard

Launches the terminal user interface (TUI) dashboard to browse, inspect, and manage run records interactively. Tabs are `Run Details`, `Console Logs`, `Resources` (CPU/memory usage), `Semantic Diff`, `Actions & Citations`, and `TUI Settings`.

Requires the optional TUI extra: `pip install "pubrun[tui]"`.

```bash
pubrun ui [--dir PATH]
```

**Aliases:** `tui`, `gui`

**Options:**

| Flag | Description |
|---|---|
| `--dir PATH` | Override the directory containing the runs (default: configured `output_dir` or `./runs`) |

**Resources view:** selecting a run populates a **Resources** tab showing peak/avg/min for
CPU and memory (main process, and the process tree when captured) plus a compact sparkline of
each over the run's lifecycle — the same per-sample data `pubrun res` uses. Press `r` to jump
to it. Runs with no resource samples (very short runs, or capture off) show a clear message.

**Reproducibility view:** Run Details includes a `REPRODUCIBILITY & EVIDENCE` section with the
same summary `pubrun show` prints (categories needing attention, inherited parent sections,
next step, and the non-guarantee note). Browsing runs never starts a live preflight
comparison; use `pubrun inspect --preflight` for that. A run that is still in progress shows a
note instead. When a run's rerun command contains `[REDACTED]` placeholders, the Actions tab
shows a separate advisory below the command; the command you copy stays exactly as recorded.

**Example:**
```bash
pubrun ui
pubrun gui
```

---

## Diagnostic Flags

These flags can be used independently of any subcommand.

### `--version`

Prints the installed pubrun version and exits.

```bash
pubrun --version
```

### `--create-config [DEST]`

Bootstraps a fully commented `.pubrun.toml` configuration file.

```bash
pubrun --create-config                    # Interactive: asks local vs global
pubrun --create-config .pubrun.toml       # Direct: writes to specified path
```

- If no destination is given, an interactive prompt offers Local (`./.pubrun.toml`) or Global (`~/.config/pubrun/config.toml`).
- Refuses to overwrite an existing file.

### `--show-config` (deprecated)

Prints the complete built-in default configuration to the terminal.

```bash
pubrun --show-config
```

> **Deprecated:** use `pubrun show default config` instead. `--show-config` still works but prints
> a deprecation notice to stderr and will be removed in a future release. To see the *resolved*
> configuration (defaults plus your overrides) rather than just the defaults, use
> `pubrun show config`.

### `--info`

Prints an import-mode diagnostic block (the active mode, its behavior flags `auto_start`, `global_hooks`, `patch_subprocesses`, `patch_console`, and `signal_hooks`, and any `PUBRUN_IMPORT_MODE` environment override), followed by invocation details and hardware probe output as JSON. Use `pubrun --version` for the installed version and `pubrun show config` for the resolved configuration.

```bash
pubrun --info
```

### `--run-tests`

Executes the built-in self-test suite to verify the installation.

```bash
pubrun --run-tests
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Error (missing manifest, invalid path, config already exists, etc.), or a triggered `--strict` / `--fail-on` threshold |
| `2` | Invalid command-line arguments or an unsupported flag combination, for example `pubrun rerun --strict` without `--preflight` |
| child exit code | For `pubrun run`, returns the child process's exit code directly |
| `127` | For `pubrun run`, the child command could not be executed (not found or permission denied) |
| `128+N` | For `pubrun run`, the child process was terminated by signal `N` (for example `143` for `SIGTERM`, signal 15) |
| `130` | For `pubrun run`, interrupted by `Ctrl+C` (`KeyboardInterrupt`) |

`pubrun bench` returns the benchmark harness's nonzero exit code directly; it does not apply the `127`, `128+N`, or `130` exit-code mappings used by `pubrun run`.

---

[README](../README.md) | [Architecture](architecture.md) | [Functional Spec](functional_spec.md) | [API](api.md) | [CLI](cli.md) | [Configuration](configuration.md) | [Manifest](manifest.md) | [Performance](performance.md) | [Research Use](research-use.md) | [HPC](hpc.md) | [Changelog](../CHANGELOG.md)
