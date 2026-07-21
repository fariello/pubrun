# /plan-review run record - scrub-history IPD (redacted)

IPD: .agents/plans/pending/20260720-1126-01-scrub-unredacted-benchmark-from-history.md
Date: 2026-07-20  Agent: opencode / its_direct/pt3-claude-opus-4.8-1m-us

## Secrets sweep (all clean)
- gitleaks detect --log-opts=--all: 397 commits scanned, NO leaks found.
- gitleaks detect --no-git (tree): NO leaks found.
- detect-secrets --all-files: 127 raw hits; after excluding gitignored vendored trees
  (.opencode/node_modules, installer-backups) and pubrun's own redaction tests, 7 tracked
  candidates remain, ALL false positives (SHA host token in the redacted benchmark; test
  fixtures; redaction-test fake inputs). No credential/token/key in tree or history.

## Home-path footprint (names masked per self-redaction; <U>=the OS username, <P1>/<P2>=two unrelated project dirs, one private one public)

### Current tree: /home/<U> paths (uniq -c, path tails masked)
     13 ~/venv/p3.14/bin/python
     11 ~/VC/pubrun/src/pubrun/__main__.py
      7 ~/VC/pubrun/tests/test_cli.py
      4 ~/VC/pubrun/src/pubrun/status.py
      4 ~/VC/pubrun/pyproject.toml
      3 ~/VC/pubrun/tests/test_status.py
      3 ~/VC/pubrun/CONTRIBUTING.md
      3 ~/VC/pubrun/CODE_OF_CONDUCT.md
      2 ~/venv/p3.14/bin/pytest
      2 ~/VC/pubrun/tests/test_quality.py
      2 ~/VC/pubrun/src/pubrun/report/diagnostics.py
      2 ~/VC/pubrun/src/pubrun/analysis/render.py
      2 ~/VC/pubrun/README.md
      1 ~/venv/p3.14/bin/twine
      1 ~/VC/pubrun/tmp/JOSS-paper/pubrun_joss_paper.md
      1 ~/VC/pubrun/tests/test_tui.py
      1 ~/VC/pubrun/tests/test_show_sections.py
      1 ~/VC/pubrun/tests/test_examples.py
      1 ~/VC/pubrun/tests/test_events.py
      1 ~/VC/pubrun/src/pubrun/tracker.py
      1 ~/VC/pubrun/src/pubrun/resources/default.toml
      1 ~/VC/pubrun/src/pubrun/report/templates.py
      1 ~/VC/pubrun/src/pubrun/capture/liveness.py
      1 ~/VC/pubrun/src/pubrun/analysis/diff.py
      1 ~/VC/pubrun/release-notes-v1.2.0.md
      1 ~/VC/pubrun/.github/pull_request_template.md
      1 ~/VC/pubrun/examples/verify_all.py
      1 ~/VC/pubrun/examples/minimal-research-workflow/README.md
      1 ~/VC/pubrun/examples/minimal-research-workflow/manifest_excerpt.json
      1 ~/VC/pubrun/examples/minimal-research-workflow/generated_output_notes.md
      1 ~/VC/pubrun/examples/minimal-research-workflow/expected_methods_text.md
      1 ~/VC/pubrun/examples/minimal-research-workflow/analysis.py
      1 ~/VC/pubrun/CITATION.cff
      1 ~/VC/pubrun/CHANGELOG.md
      1 ~/VC/pubrun

### All history: top-level prefixes (uniq -c)
  16036 ~/VC
   3922 ~/<venv>

## Verdict
REVIEWED - REVISIONS APPLIED. Scope upgraded (human) to full scrub: remove hostname file +
replace /home/<U> -> ~ across history and tree; preserve author name/email. NO-GO until human
approval AND the separate explicit force-push GO for Step 4.
