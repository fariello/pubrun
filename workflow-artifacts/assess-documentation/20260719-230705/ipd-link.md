# IPD link

- IPD: `.agents/plans/pending/20260719-2307-01-assess-documentation.md`
- Summary: Documentation accuracy is **adequate** (this session's show-config/config/manifest docs
  verified accurate). The IPD proposes 4 low-risk fixes to adjacent inaccuracies the sweep found:
  (D1) add `show config` to the README + mark `--show-config` deprecated; (D2) fix
  `config.source_files` type in manifest.md (list[object], not list[string]); (D3) reword the
  configuration precedence table so the two local files are one tier; (D4) add `imported-transitive`
  to the schema `packages_section.mode` enum (a real contract-gate gap the doc sweep exposed;
  requires CI-matrix validation). Nothing deferred.
