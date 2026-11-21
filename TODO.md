# TODO

Known issues and deferred improvements for future releases.

---

## Release-time actions (MUST do when publishing the next PyPI release)

### Yank prior releases from PyPI after 1.4.0 is live

pubrun <= 1.3.0 was published under **BSD-3-Clause** before the project relicensed to
**Apache-2.0**, and earlier releases (`v1.0.0`-`v1.3.0`) also carried erroneous
placeholder citation metadata introduced by automated tooling. When the clean Apache-2.0
**1.4.0** release is published to PyPI, **yank every prior release (`0.1.1`-`1.3.0`)** so
new installs resolve to `1.4.0` while existing pinned installs keep working.

Steps (maintainer / operator, gated inside `release-review` Section 9):
1. Publish the clean Apache-2.0 `1.4.0` release to PyPI first (never leave the package with
   zero installable versions).
2. Yank `0.1.1`-`1.3.0` on PyPI (Manage -> each release -> Options -> **Yank**; do NOT
   delete).
3. Confirm `pip install pubrun` resolves to `1.4.0` and yanked versions show the yanked
   banner on PyPI.
4. Confirm the `v1.4.0` GitHub Release triggers Zenodo to refresh concept DOI
   `10.5281/zenodo.20801582` (currently pointing at `v1.2.0`) to the clean `1.4.0` archive.

---

## Deferred ideas (need their own design pass / IPD)

### Full repo-wide em/en-dash sweep

`AGENTS.md` forbids em/en dashes in authored Markdown, but many docs and CHANGELOG entries
predate that rule and still contain them (`CHANGELOG.md` has ~50 dash lines; several
`docs/*.md` files too). `README.md`, `CONTRIBUTING.md`, `docs/research-use.md`, and
`docs/hpc.md` are clean, but a repo-wide sweep is still outstanding, ideally with a
scripted, reviewable transform plus a follow-up grep gate and a pre-commit or CI check to
prevent regressions. Deferred from the sanitizer and adoption-and-signal IPDs. Needs its
own IPD.

### Enable pytest-randomly in CI

The flaky-test isolation work added `pytest-randomly` to `[dev]` but disabled it by default
via `-p no:randomly` in `addopts`, so CI stays deterministic. Enabling randomized test order
in CI (or a dedicated CI job) would catch cross-test state leaks that a fixed order hides.
Deferred as OQ1=C in `.agents/plans/executed/20260720-0026-01-flaky-test-isolation-hardening.md`.

### Runs directory index for fast `pubrun status` (PERF-09)

When a user accumulates 500+ runs, `pubrun status` gets slow because it reads and parses
`manifest.json` (or `.pubrun.lock`) from every single run directory. A lightweight index
file (`.pubrun-index.json`) in the runs directory could cache the key metadata (`run_id`,
`status`, `started_at`, `script`, `exit_code`) so status queries are O(1) instead of O(n).

Deferred because most users clean regularly and will not hit 500 runs. Implement only after
benchmarking confirms >1s scan time at realistic run counts.

---

## Removed from Roadmap

### Determinism Tracking (`[capture.determinism]`)

**Removed.** Recording pseudorandom seeds (`random.getstate()`, `numpy.random.get_state()`,
`torch.manual_seed()`) was considered but rejected for the following reasons:

1. **Fragile detection**: Detecting which RNG libraries are in use requires probing
   optional imports (numpy, torch, tensorflow, jax) at runtime. Each has a different
   API surface, and versions change frequently.
2. **Locking seeds is harmful**: Overwriting user seeds would break scripts that
   intentionally use randomness for exploration. Recording-only is the only safe option.
3. **Recording-only has limited value**: If the user did not explicitly set a seed,
   recording the internal RNG state is useless for reproduction (the state is opaque
   and not portable across library versions).
4. **Better solved by the user**: A single `pubrun.annotate(seed=42)` call is more
   explicit, safer, and requires no magic detection.

The `[capture.determinism].depth = "off"` config key is retained for forward compatibility
but documented as "not yet implemented / reserved."

### `summary.txt` Generation (`[logging].write_summary`)

**Removed.** A human-readable glance file was planned but is superseded by:

- `pubrun status <run-id>`: shows the same information interactively.
- `pubrun report --basic`: produces a full diagnostic summary.
- `manifest.json`: machine-readable and more complete.

Writing a redundant text file to every run directory adds disk I/O, increases the
run directory footprint, and provides no information not already available via the
CLI. The config key is retained as "not yet implemented / reserved" for users who
may want it in the future.
