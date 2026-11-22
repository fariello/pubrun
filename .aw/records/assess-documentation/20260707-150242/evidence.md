# Evidence — assess documentation (20260707-150242)

Reproducible record of what was inspected. No files were modified.

## Commands run
- `python -m pubrun -h` — authoritative registered command list (20): init, report-bug,
  feedback, cite, self-check, inspect, bench, clean, combined, cpu, diff, mem, meta, methods,
  rerun, res, run, show, status, ui (ui aliases: tui, gui).
- `python -m pubrun -h | grep -cE '^    [a-z]'` → 20.
- `grep -n "fourteen\|thirteen commands" README.md docs/cli.md` → README.md:166 "fourteen";
  docs/cli.md:5 "thirteen commands".
- `grep -n "pubrun combined\|Timestamped console\|GitHub Actions CI" README.md` → roadmap
  future items at 380/384/385 vs shipped section at 189.
- `ls .github/workflows/` → ci.yml, dependency-audit.yml, secret-scan.yml (CI exists).
- `grep register_artifact register_metadata src/pubrun` → no matches (roadmap items 4/5
  genuinely future).

## Files inspected
- `README.md` — full read (446 lines): header/footer nav, CLI Reference section (164-265),
  Roadmap (375-385), Citation (389-408), License (416-418), License/Attribution/Citation
  (427-446).
- `docs/cli.md` — command count (5), rename note (47), `show`/`res`/`cpu`/`mem` sections
  (245, 355, 394, 427, 437), nav (1, 616).
- `CHANGELOG.md` — nav header (1) and footer (542).
- `src/pubrun/__main__.py` — subparser registration + dispatch + hidden aliases
  (report-bug 1854, feedback 1860/2390, combined 1963/2373, show 2121, report alias
  2068/2165/2192, res 2096, resources alias 2225).
- `src/pubrun/capture/console.py` — timestamped capture (223 and TqdmSafeTee usage).
- `docs/configuration.md` — `[capture.file_io].level` (235), `system_metrics` (194),
  absence of `[capture.filesystem]` (correct).
- `docs/` directory listing — confirmed architecture.md, functional_spec.md, api.md, cli.md,
  configuration.md, manifest.md, performance.md, research-use.md, hpc.md all present;
  design/file-io-provenance-evaluation.md present but not in nav.

## Method
Accuracy-first: every doc claim about commands/features was checked against `-h` output and
the source (`file:line`). Roadmap "future" items were each grepped for an implementation.
Nav link targets were checked for existence. Nothing was inferred from names alone.

## Sampling / truncation notes
- Full files were read for README.md, docs/cli.md, and the relevant `__main__.py` regions.
- The audit sub-task returned line-cited findings; each High/Medium finding was independently
  spot-verified against the code before inclusion.
