# Evidence - assess documentation (20260719-230705)

Reproducible record of what was inspected.

## Method

Delegated a thorough doc-vs-code cross-check to an `explore` agent (accuracy-first), then
independently re-verified the load-bearing findings at the shell. Docs are treated as claims to
verify against code, per the lens.

## Documents inspected

- `README.md` - CLI section (`:250-254` show), diagnostic-flags table (`:301` `--show-config`),
  feature/framing (`:5-7`).
- `docs/cli.md` - `show`/`show config` family (`:442-494`), `--show-config` (`:725-736`),
  `--info` (`:738-744`).
- `docs/configuration.md` - precedence table (`:9-22`), spot-checked keys (`:53-55,88,135,184`),
  env vars (`:331-334`).
- `docs/manifest.md` - config section (`:249-253`), capture-state list (`:458,465-466`).
- `CHANGELOG.md` - `[Unreleased]` entries (`:9-71`).
- `schemas/manifest.schema.json` - `config_section` (source_files, notices), `status_value` enum,
  `packages_section.mode` enum.

## Code cross-checked

- `src/pubrun/__main__.py` - show-config dispatch (`:2488-2514`), `_run_show_config` (`:592-665`),
  `_render_config_toml` (`:569-578`), `--all`/`config_extra` args (`:2420,2427`), `--show-config`
  handler (`:2808-2812`), `_show_info` (`:1851-1889`), `--info` help (`:2467`).
- `src/pubrun/config.py` - `_resolve_layers` / `resolve_config` (`:144-186`), `load_local_config`
  (`:105-129`), env wiring (`:157-163`).
- `src/pubrun/capture/packages.py` - `imported-transitive` support (`:23,41,61`).
- `src/pubrun/resources/default.toml` - key defaults (hardware `:247`, packages `:180-183`,
  console `:95`, core `:21-35`).

## Commands run (independent re-verification of key findings)

- `grep -n "show config" README.md` -> none (confirms D1 omission).
- `grep -n "show-config" README.md` -> `:301` row, no deprecation note (confirms D1 stale row).
- `sed -n '252p' docs/manifest.md` + schema `config_section.source_files.items` -> string vs object
  (confirms D2).
- `grep imported-transitive src/pubrun/capture/packages.py` + schema `packages_section.mode.enum`
  -> supported in code, absent from enum (confirms D4).

## Coverage note (what was checked and found ACCURATE)

- The `show config` family docs (cli.md), the `--show-config` deprecation note (cli.md), the `--info`
  help (prior mismatch already corrected), the config precedence ORDER, `[core].profile` inert
  status, 6 spot-checked config keys + 4 env vars, `config.notices` doc+schema, and the `pending`/
  `timeout` capture states doc+schema were all verified ACCURATE. The 4 findings are the exceptions.

## Sampling / limits

- Config-key verification was a spot-check of the keys the docs explicitly mention, not an exhaustive
  key-by-key audit of every `default.toml` entry. A full key audit is out of this run's scope.
- `.agents/workflows/` and `workflow-artifacts/` excluded from assessment scope per the harness rules.
