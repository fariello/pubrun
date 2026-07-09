# TOML parsing on Python 3.8–3.10 — the `tomli` dependency decision

- Date: 2026-07-08
- Status: **Decided — keep `tomli` as a conditional dependency for Python 3.8–3.10.**
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us), on maintainer request.

## Question

pubrun advertises **zero runtime dependencies**, but on Python 3.8–3.10 it installs one:
`tomli`, to parse TOML config (the stdlib `tomllib` only exists on 3.11+). This has caused
several CI/compatibility headaches. The maintainer asked whether depending on `tomli` was a
mistake, and whether pubrun should instead drop Python <3.11 support (which would make the
zero-dependency claim unconditionally true).

This documents the decision and the data behind it.

## Current mechanism

TOML is parsed in exactly four places, all trivial:

- `src/pubrun/config.py:58` — `tomllib.loads(...)` (bundled default config)
- `src/pubrun/config.py:85` — `tomllib.loads(...)` (user config)
- `src/pubrun/config.py:86` — `tomllib.TOMLDecodeError` (error handling)
- `src/pubrun/_config_boot.py:45` — `tomllib.load(f)` (boot-time config)

The import is a standard stdlib-first / backport-fallback shim:

```python
if sys.version_info >= (3, 11):
    import tomllib            # stdlib — pulls in nothing
else:
    import tomli as tomllib   # only on 3.8–3.10
```

`pyproject.toml` declares it conditionally:

```toml
"tomli>=1.1.0; python_version < '3.11'"
```

So `tomli` is **only ever installed on Python 3.8–3.10**. On 3.11+ pubrun has zero runtime
dependencies. `tomli` is a tiny, pure-Python, PSF-trusted package — it is literally the code
that became the standard-library `tomllib`. It is best understood as a **conditional polyfill
for a stdlib module**, present only where the stdlib lacks it.

## The options considered

- **A — Keep `tomli` (chosen).** Standard, correct, minimal. Cost: the ≤3.10 zero-dep
  asterisk, and a class of "is `tomli` importable?" test traps (all since fixed).
- **B — Vendor a micro TOML reader.** Would give true zero-dep on all Pythons, but means
  owning a TOML parser forever and a footgun on exotic hand-written config. More code than the
  problem warrants. Rejected.
- **C — Drop Python <3.11 (`requires-python = ">=3.11"`).** Makes zero-dep unconditionally
  true, simplifies CI, kills the bug class — but amputates every user on 3.8–3.10.
  **Rejected on the data below.**
- **D — Switch config format to JSON.** Stdlib everywhere, but worse for hand-edited config
  and breaks existing users' TOML files. Rejected.

## The data (why C is off the table)

Python version share of PyPI downloads, **June 2026** (`pypistats python_minor <pkg>
--last-month`), using scientific packages that model pubrun's actual research audience:

| Python | numpy  | pandas | scipy  | Upstream status (python.org) |
|--------|--------|--------|--------|------------------------------|
| 3.10   | 14.80% | 15.78% | 13.20% | security-only, EOL 2026-10   |
| 3.9    |  8.70% |  9.93% |  9.40% | **EOL 2025-10-31**           |
| 3.8    |  2.60% |  3.29% |  2.08% | **EOL 2024**                 |
| **3.8–3.10 total** | **~26.1%** | **~29.0%** | **~24.7%** | (pubrun's supported <3.11 band) |

Roughly **a quarter to a third of installs of typical scientific packages are still on Python
< 3.11.** For a reproducibility / provenance tool aimed at researchers — the population most
likely to run older, pinned cluster-module Pythons — dropping <3.11 would cut off ~1 in 4
likely users.

Caveats that make the real ≤3.10 share **higher**, not lower:

- **PyPI undercounts conda.** Many HPC/lab researchers install via conda-forge (not counted
  here), and those environments skew *older* than PyPI.
- **CI/mirror bots inflate newer versions**, so human usage of old versions is understated.
- 3.10 alone (~14%) is comparable to or larger than the newest stable release's share —
  i.e. more people are on the *oldest* version pubrun supports than on the newest.

## Decision

**Keep `tomli`.** It is the correct, minimal, standard way to serve the ~25–29% of pubrun's
audience still on Python 3.8–3.10. The dependency was never the problem: every issue it caused
was a **test bug** (a wholesale `sys.modules` swap, and a test that assumed `tomli` was always
importable when it is correctly absent on 3.11+), all fixed with the full 3-OS × Python-3.8–3.14
CI matrix now green.

Dropping <3.11 (Option C) is off the table until the ≤3.10 share falls substantially. Note that
"EOL" ≠ "unused" in research: EOL Python persists for years on cluster modules, so a fast
decline is not expected even after 3.10's October 2026 EOL.

## Honesty note (docs)

The "zero runtime dependencies" claim is true on 3.11+ but not on 3.8–3.10. The README already
qualifies this (`README.md:9`, `README.md:19`): *zero runtime dependencies on 3.11+; on 3.8–3.10
the sole dependency is `tomli`, a backport of stdlib `tomllib`.* Keep that qualification wherever
the zero-dependency claim appears.

## Revisit criteria

- **~Oct 2026**, when 3.10 reaches EOL — re-pull the numbers; do **not** assume a fast drop.
- If the combined 3.8–3.10 share of representative scientific packages falls below ~5–10% and
  conda-forge no longer ships those minors, reconsider Option C.
