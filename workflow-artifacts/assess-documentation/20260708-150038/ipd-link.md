# IPD link

- IPD: `.agents/plans/pending/2026-07-08-assess-documentation.md`
- Summary: Sync docs to the 2026-07-07 CLI/UX batch. Two genuine accuracy defects introduced
  by the batch (bench `--passes` help still says "(default 2)" while the default tier is 3; the
  CHANGELOG claims a `pubrun bench --no-baseline` flag that exists only on the harness) plus
  README lag (self-check `--quiet`/`--json`/itemized-default, diff `--table`/summarize, bench
  `--rigorous`/baseline, recency run selector, res peak/avg/min + tree CPU, output prefixes)
  and a couple of `cli.md`/`configuration.md` gaps (res `--average`; `[diff]` ignore-list
  placeholders; status `#` column). 11 findings (1 High, 6 Medium, 4 Low); all documentation /
  help-string edits, Low remediation risk.
