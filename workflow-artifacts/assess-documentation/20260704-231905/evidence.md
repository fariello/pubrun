# Evidence - assess-documentation 20260704-231905

## Methodology

Cross-referenced every documented claim against the canonical source:
- Defaults: compared docs tables against `default.toml` flattened output
- CLI commands: compared docs sections against `pubrun --help` and `pubrun bogus` error
- API surface: compared docs table against `pubrun.__all__`
- Config keys: compared docs against full flatten of `load_default_config()`
- CHANGELOG: checked for [Unreleased] entries covering today's commits

## Files inspected
- docs/api.md (277 lines)
- docs/configuration.md (265 lines)
- docs/cli.md (378 lines)
- docs/functional_spec.md (773 lines)
- docs/architecture.md
- docs/manifest.md
- docs/research-use.md
- README.md (371 lines)
- CHANGELOG.md (first 40 lines)
- src/pubrun/resources/default.toml (full, via load_default_config())
- src/pubrun/__init__.py (__all__ export)
- pubrun --help, pubrun status --help, pubrun clean --help, pubrun diff --help,
  pubrun run --help, pubrun boguscmd (error output)

## Commands run
- `python -c "import pubrun; print(pubrun.__all__)"` — verified API surface
- `python -c "from pubrun.config import load_default_config; ..."` — flattened all config keys
- `pubrun --help` — verified command list
- `pubrun bogus` — verified error message (primary commands only)

## Key finding pattern
The root cause of all High-severity findings was the same: code behavior was
changed (capture_mode default, command renames) without updating the corresponding
documentation. The docs became stale immediately upon code change and remained so
until this assessment caught them.
