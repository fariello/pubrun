# Decisions - assess-ui-ux 20260704-212506

## Scope
CLI commands and Python API ergonomics. Did not assess TUI (optional extra).

## Key decisions
- UX-02 deferred: argparse alias handling is deeply embedded. The fix requires
  subclassing ArgumentParser to filter aliases from _SubParsersAction choices.
  Medium-High complexity risk for a cosmetic improvement.
- The overall CLI is well-structured: clear subcommands, good --help, examples
  in help text, colored output, NO_COLOR support. The issues are novice
  onboarding gaps and minor feedback improvements, not structural problems.
- `pubrun init` proposed as a thin wrapper (not a new feature): just calls
  --create-config and prints guidance. Low complexity, high discoverability value.
