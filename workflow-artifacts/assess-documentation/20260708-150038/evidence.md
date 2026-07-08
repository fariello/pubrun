# Evidence — assess documentation (20260708-150038)

Reproducible record of what was inspected. No files were modified. Interpreter:
`~/venv/p3.11.8` (pubrun installed editable).

## Commands run
- `python -m pubrun -h` — authoritative command list (20): bench, cite, clean, combined, cpu,
  diff, feedback, init, inspect, mem, meta, methods, report-bug, rerun, res, run, self-check,
  show, status, ui.
- `python -m pubrun bench -h` — confirmed D1 (`--passes` help still "(default 2)"), the tiers
  (`--quick`/`--full`/`--rigorous`), and D2 (NO `--no-baseline` flag on the front-end).
- `python -m pubrun self-check -h` — `--show-suggestions/-v`, `--quiet/-q`, `--json`, `--strict`
  (D3).
- `python -m pubrun diff -h` — `--table` present (D4).
- `python -m pubrun res -h` / `cpu -h` / `mem -h` — `--average`, `-l/--last`, and the standard
  run-filter flags present (D7).
- `python -m pubrun status -h` — the `#` recency column context (D11).
- `grep -n '"default":' benchmarks/harness.py` → `"default": (30, 3)` (D1 evidence).
- `grep -n "no-baseline\|no_baseline" benchmarks/harness.py src/pubrun/__main__.py` →
  present only in `harness.py:524,532,542`, absent from `__main__.py` (D2 evidence).

## Files inspected
- `README.md` — CLI section (self-check/diff/bench/res entries), Roadmap, nav header/footer,
  command-count phrasing, output-prefix mentions.
- `docs/cli.md` — every command's flags cross-checked against `-h`; "Selecting a run" and
  "Output conventions" sections; res/cpu/mem/status/bench/self-check/diff/report/show/meta.
- `docs/configuration.md` — `[diff]`, `[capture.resources]`, `[capture.file_io]` vs
  `src/pubrun/resources/default.toml`.
- `docs/manifest.md` — `resources.*` (incl. `peak_tree_cpu_percent`), `python.*` env-kind fields.
- `CHANGELOG.md` — `[Unreleased]` batch coverage; the bench `--no-baseline` line.
- Source: `benchmarks/harness.py` (tiers, `--no-baseline`), `src/pubrun/__main__.py` (bench
  parser), `src/pubrun/capture/{resources,python_runtime}.py` (manifest fields).
- Cross-referenced the batch commits `f7ed43c a262232 0da1ee5 e1eafe7 4cd956a ac73c9a fb86e84`.

## Method
Accuracy-first: every doc claim about a command/flag/default was checked against `-h` output
or source (`file:line`). The two behavior/accuracy defects (D1, D2) were independently
re-verified after the sub-agent audit. Nav targets checked for existence. Nothing inferred
from names alone.

## Sampling / truncation notes
- The sub-agent audit returned line-cited findings; each Medium/High was spot-verified against
  the live `-h` or source before inclusion.
- Full files read for README.md, docs/cli.md, and the relevant `harness.py`/`__main__.py`
  regions. `docs/configuration.md` `[diff]` block and `default.toml` ignore lists read in full.
