# Community benchmark corpus

Collected, accepted community benchmark results (IPD 20260722-2209-01, Phase 2 "local pull"
model). This directory is populated by the maintainer-run tool `benchmarks/pull_submissions.py`,
NOT by any GitHub Action. Nothing here is written automatically by CI.

## Layout

- `accepted/<sha256>.redacted.json` - an accepted result, content-addressed by the SHA-256 of its
  exact bytes. Every file passed the same fail-closed validation the server uses (schema
  `pubrun-benchmark/5` + structural share-safety) and the 256 KB store cap. All files are
  redacted (hostname/username/home paths masked); none contain personal data.
- `accepted/<sha256>.meta.json` - ingestion metadata for that result: the submission `kind`
  (`url` or `inline`), source host (for a URL), fetch timestamp, digest, validator and
  share-safety versions, and a `sources` list of every issue that contributed those exact bytes
  (the same result can arrive from more than one issue; all are recorded).
- `summary.csv` / `summary.md` - the aggregated overhead tables, regenerated from `accepted/` by
  `benchmarks/aggregate.py` on each `--apply` run.

## Regenerating / collecting

From a source checkout, authenticated with `gh`:

```bash
# Dry run (default): show what would be stored/retagged, write nothing.
python3 benchmarks/pull_submissions.py

# Apply: store accepted results here, re-tag issues, regenerate the summaries.
python3 benchmarks/pull_submissions.py --apply
```

Content addressing makes re-runs idempotent: an already-stored result is a no-op (its issue is
appended to the sidecar's `sources` if new). See the tool's `--help` for options.
