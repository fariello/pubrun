# IPD: strengthen citation recourse — Zenodo DOI, JOSS path, and enforceable attribution

- Date: 2026-07-06
- Concern: citation / release-metadata / licensing posture (a deliberate strategy
  decision, not a mechanical change). The maintainer wants the *strongest practical
  recourse for non-citation* without wrecking adoption.
- Scope: `pubrun`'s citation + attribution surface only. Adds a `.zenodo.json` so the
  next GitHub release auto-mints a DOI; wires that DOI into `CITATION.cff`, the README
  "Citation" section, `docs/research-use.md`, and `pubrun cite`; fixes the author name to
  the full legal form; and (optionally, maintainer-gated) prepares a JOSS software-paper
  path and/or a CC-BY license for any distributed data/docs. Does NOT change the code
  license (stays Apache-2.0) and does NOT add a citation-as-license-condition clause
  unless the maintainer explicitly opts in (see "Open questions").
- Status: PENDING — awaiting maintainer decisions on the open questions below, then a
  plan-review pass, then execution on approval. NOT auto-executed.
- Author: opencode (its_direct/pt3-claude-opus-4.8-1m-us)

## Problem / motivation

The maintainer asked: *"what is my recourse if someone publishes a derived work and does
not cite me?"* The honest answer:

- **Missing ATTRIBUTION in a distributed derivative** is enforceable — Apache-2.0 §4(d)
  makes retaining `NOTICE` + notices a condition; breach terminates the license and
  becomes copyright infringement (DMCA/C&D/suit). `pubrun` already has this (LICENSE +
  NOTICE + README attribution, added 2026-07-05).
- **Missing CITATION in a publication is NOT enforceable by a software license.** A
  license governs copying the software, not citing ideas in a paper. So the strongest
  *practical* levers for citation are non-legal: a **DOI + a canonical citable artifact**
  (which reviewers/editors/institutions actually enforce), optionally a **peer-reviewed
  software paper** (JOSS), and — only if adoption cost is acceptable — a citation term as
  a license condition or a CC-BY license on distributed *data/docs*.

This IPD builds the high-ROI, zero-adoption-cost parts by default (DOI + citable
metadata) and records the higher-cost options as explicit maintainer decisions.

## Current state (verified 2026-07-06)

- `CITATION.cff` exists (`cff-version: 1.2.0`, `license: Apache-2.0`,
  `date-released: "2026-07-05"`, `email: "gfariello@fariel.com"`) but: (a) `given-names:
  "Gabriele"`; (b) has **no `identifiers`/DOI block**; (c) has no `version` field
  currently.
  - **NAME-CONVENTION CORRECTION (plan-review 2026-07-06):** the original draft called
    `given-names: "Gabriele"` a *defect* ("not the full legal name"). That is **wrong**
    for this repo. Per the project's standing convention (see the Apache-2.0 relicense
    CHANGELOG entry and `AGENTS.md`-level rule): **citation surfaces use the publication
    name — "Gabriele Fariello" / "Fariello, G." — while ONLY legal surfaces (`LICENSE`,
    `NOTICE`, `__copyright__`, README copyright line) use the full legal name "Gabriele
    G. R. Fariello".** `CITATION.cff` is a **citation** surface. `pubrun cite` bibtex
    already correctly emits `author = {Gabriele Fariello}` (`src/pubrun/__main__.py:687`);
    APA/MLA/Chicago emit `Fariello, G.` / `Fariello, Gabriele` (`__main__.py:679-683`).
    Therefore step 2 below is **inverted** from the original draft: do **not** push the
    legal name onto `CITATION.cff` or `pubrun cite`. The `.zenodo.json` `creators` name
    is likewise the **publication** form (`Fariello, Gabriele`), with legal name only if
    Zenodo requires a distinct legal-name field (it does not).
- **No `.zenodo.json`** in the repo → GitHub↔Zenodo integration would use only default
  metadata and no controlled author/license/keywords.
- README has a `## Citation` section (README.md:389) that already says *"A Zenodo archive
  DOI will be added on public release"* — a promise this IPD fulfills — plus a
  consolidated `## License, Attribution & Citation` section (README.md:419, added in the
  Apache-2.0 relicense).
- `pubrun cite` subcommand exists (`README.md:174`, docs/cli.md) and emits a citation
  (e.g. `--style bibtex`); it reads citation metadata, so the DOI must flow through to it.
- `docs/research-use.md` exists and is the natural home for the "how to cite / why cite"
  guidance.
- A prior executed IPD (`.agents/plans/executed/20260622-citation_and_release_readiness.md`)
  *sketched* a `preferred-citation` (JOSS) block + **fabricated placeholder** Zenodo/JOSS
  DOIs (`10.5281/zenodo.1234567`, `10.5281/zenodo.1234568`, `10.21105/joss.08024`).
  **VERIFIED (plan-review 2026-07-06): none of those placeholders ever landed** — the
  current `CITATION.cff` has no `identifiers` block and no `preferred-citation`, and no
  fake DOI appears anywhere in the repo. So there is **nothing stale to reconcile**; the
  current state is honest. This IPD simply *adds* the real mechanism from a clean base.
  The executor must confirm this still holds at execution time and must **never write a
  fabricated DOI** (the earlier draft's `1234567` pattern is exactly what to avoid).
- Code license is **Apache-2.0** (LICENSE + NOTICE); that stays.

## Key strategy decision (must be answered before building the optional parts)

**How far up the enforcement ladder does the maintainer want to go for citation?** The
levers, strongest-recourse vs. adoption-cost:

- **(Baseline — DEFAULT, do by default) DOI + canonical citable artifact.** `.zenodo.json`
  + DOI in `CITATION.cff`/README/`pubrun cite`. Not legally enforceable, but the *de facto*
  standard that gets software cited; zero adoption cost. **This IPD does this regardless.**
- **(Opt-in A) JOSS software paper.** Submit a short paper; make its DOI the
  `preferred-citation`. Highest citation ROI in academia; cost = writing + review time,
  zero adoption/licensing cost. Recommended, maintainer-gated (needs a `paper.md` +
  `paper.bib` — likely a separate writing effort/repo `pubrun-paper` already exists).
- **(Opt-in B) CC-BY-4.0 on distributed DATA/DOCS (not the code).** If `pubrun` ships
  datasets/figures/generated docs, license *those* CC-BY so attribution/citation of them
  is legally required. Standard in research, low cost. Only applies if such artifacts are
  distributed.
- **(Opt-in C, HIGH adoption cost) citation-as-license-condition / dual-license academic
  addendum.** Make citation a *condition* of a grant (custom/non-OSI license, or a
  dual-license academic term). This is the only path that makes non-citation legally
  actionable, but it is **non-OSI, GPL-incompatible, and repels institutional/commercial
  adopters**. Strongly recommend NOT applying to the main Apache-2.0 code; if wanted, scope
  it narrowly and get an IP attorney to draft it. Recorded here only as an explicit choice.

**Recommendation to evaluate:** do the Baseline now; strongly recommend Opt-in A (JOSS)
and Opt-in B (only if data/docs are distributed); recommend AGAINST Opt-in C for the code.

## Proposed changes (Baseline — do by default, subject to open questions)

1. **Add `.zenodo.json`** at repo root so the next GitHub release (once the repo is
   enabled in Zenodo) mints a DOI with controlled metadata: `title`, `description`,
   `creators` (name **`Fariello, Gabriele`** — the *publication* form, NOT the legal
   `Gabriele G. R.`; add `affiliation` + `orcid` only if the maintainer provides them),
   `license: Apache-2.0`, `keywords`, `upload_type: software`, `related_identifiers`
   (link to the GitHub repo). Determinism: keep it minimal and hand-maintained (no
   generated churn).
2. **Do NOT change the author name in `CITATION.cff`.** `given-names: "Gabriele"` is
   **correct** — `CITATION.cff` is a citation surface and must use the publication name,
   not the legal name (see the NAME-CONVENTION CORRECTION under "Current state"). The
   only permitted author edits here are additive: add `orcid:` **if** the maintainer
   provides one (open question 2). Leave `family-names`/`given-names`/`email` as they
   are. (This step was inverted in the original draft and would have introduced a
   convention regression.)
3. **Add the DOI to `CITATION.cff`** via an `identifiers:` block (Zenodo **concept** DOI =
   all-versions, and optionally the **version** DOI), and set/confirm `version:` +
   `date-released:` for the citing release. Reconcile with the placeholder DOI/
   `preferred-citation` block from the 2026-06-22 IPD (replace placeholders with the real
   concept DOI; keep `preferred-citation` only if Opt-in A/JOSS is chosen, else remove the
   stale placeholder so the file is honest).
4. **Update the README `## Citation` section** (README.md:389): replace the "DOI will be
   added on public release" promise with the real "Cite this DOI" badge + a concrete
   suggested citation including the DOI; keep it consistent with the
   `## License, Attribution & Citation` section.
5. **Wire the DOI through `pubrun cite`** so `pubrun cite --style bibtex` (and other
   styles) emit the DOI in the reference.
   - **VERIFIED (plan-review 2026-07-06):** `pubrun cite` does **NOT** read
     `CITATION.cff`. `_run_cite` (`src/pubrun/__main__.py:661-695`) **hardcodes** the
     citation strings for all four styles (apa/mla/chicago/bibtex). So there is **no
     shared source of truth today** — README, `CITATION.cff`, and `_run_cite` are three
     independent copies. The original draft's "update whichever is the source of truth
     so there is a SINGLE source" is therefore not a mechanical edit; it is a small
     design choice. **Decision for the executor: DO NOT introduce a CFF parser/loader.**
     Parsing YAML at CLI time would add a runtime dependency (zero-dep is a hard project
     principle) or a hand-rolled parser (complexity), for a string that changes ~once a
     year. Instead: (a) add the DOI to the hardcoded strings in `_run_cite`, AND (b) add
     a **consistency test** (see "Required tests") that reads `CITATION.cff` and asserts
     the DOI/title/author/version substrings appear in each `pubrun cite --style` output.
     The test is the drift guard; the human edits both places when the DOI lands. This
     keeps zero-dep and KISS while still preventing silent drift.
6. **Update `docs/research-use.md`** with a short "How to cite pubrun" subsection (DOI +
   example) and, honestly, what is and isn't required (attribution required under Apache
   §4(d); citation requested). **Guardrail:** `docs/research-use.md` already contains
   specific factual claims (e.g. "four to six researchers at the University of Rhode
   Island", "over 500 direct downloads on PyPI", and a "Citation status" section stating
   no publication currently cites pubrun). The executor must **not** alter or contradict
   those numbers, and must **only add** the how-to-cite text; if the honest citation
   status changes (e.g. a JOSS DOI exists), update the "Citation status" section
   truthfully rather than fabricating adoption/impact. Keep the "no publication cites it
   yet" statement until that is actually false.
7. **CHANGELOG** entry under `[Unreleased]` describing the DOI/citation metadata addition
   and the name fix.

## Optional changes (maintainer-gated — only if the corresponding open question says yes)

- **Opt-in A (JOSS):** add `paper.md` + `paper.bib` (or coordinate with the existing
  `pubrun-paper` repo), and set `preferred-citation` in `CITATION.cff` to the paper once it
  has a DOI. (Writing the paper is out of scope for the executing agent unless told to
  draft a skeleton.)
- **Opt-in B (CC-BY data/docs):** identify any distributed data/doc artifacts, add a
  `LICENSES/CC-BY-4.0.txt` and a clear statement that *those artifacts* are CC-BY-4.0 while
  the code stays Apache-2.0. Only if such artifacts exist.
- **Opt-in C (citation-as-condition):** NOT implemented by the agent. If the maintainer
  insists, the agent records the requirement and defers to an IP attorney; it must NOT
  silently bolt a non-OSI clause onto the Apache-2.0 license.

## Anti-regression / invariants

- **Single *checked* source for citation (not a single *stored* source).** These four
  surfaces are stored independently by design (see step 5 — no CFF loader, to preserve
  zero-dep/KISS): `CITATION.cff`, the README Citation section, the hardcoded strings in
  `_run_cite` (`src/pubrun/__main__.py:661-695`), and `.zenodo.json`. The invariant is
  enforced by a **consistency test**, not by a shared data source: the test reads
  `CITATION.cff` and asserts author name (publication form), DOI, version, and license
  agree with README and `pubrun cite` output. This is the anti-drift guard.
- `pubrun cite` output stays paste-ready and deterministic; adding the DOI must not break
  existing `--style` formats. Characterize current `pubrun cite` output first, then assert
  the only diff is the added DOI.
- `.zenodo.json` and `CITATION.cff` must be valid (JSON / CFF schema) — validate in CI or
  a test.
- The code license remains Apache-2.0; NOTICE/attribution unchanged. No OSI-incompatible
  clause added to the code without an explicit Opt-in C decision.
- **Name convention preserved (two forms, by surface):** legal surfaces (`LICENSE`,
  `NOTICE`, `__copyright__`, README copyright line) keep the full legal **"Gabriele G. R.
  Fariello"**; citation surfaces (`CITATION.cff`, `.zenodo.json` creators, `pubrun cite`,
  README Citation section) keep the publication form **"Gabriele Fariello" / "Fariello,
  G."**. This change must NOT collapse the two into one form.

## Required tests / validation

- `CITATION.cff` parses (CFF 1.2.0 schema valid); `.zenodo.json` is valid JSON with the
  required Zenodo fields.
- `pubrun cite --style bibtex` (and apa/mla/chicago) includes the DOI and remains
  well-formed; extend the existing `tests/test_cli.py` cite tests
  (`test_cite_apa`/`_bibtex`/`_mla`/`_chicago`, lines ~127-142) to characterize current
  output first, then assert the only diff is the added DOI.
- A **consistency test** (the drift guard, per the revised step 5): read `CITATION.cff`,
  and assert the author name (**publication form** — bibtex `Gabriele Fariello`, APA
  `Fariello, G.`, NOT the legal `Gabriele G. R.`), the DOI, the version, and the license
  agree across `CITATION.cff`, `.zenodo.json`, the README citation block, and each
  `pubrun cite --style` output. This test also fails if anyone reintroduces the legal
  name onto a citation surface.
- Full suite green (baseline this session: 686 passed, 2 skipped, 1 known SIGPIPE flake
  in `tests/test_status.py` that passes in isolation — do not attribute it to this work).

## Spec / documentation sync

`README.md` (`## Citation` + `## License, Attribution & Citation`), `docs/research-use.md`,
`docs/cli.md` (`pubrun cite` if its output/flags change), `CHANGELOG.md`. Run
`/assess documentation` after implementation.

## Open questions (maintainer — must answer before execution)

1. **Enforcement ladder:** Baseline only, or Baseline + Opt-in A (JOSS), + Opt-in B
   (CC-BY data/docs), and/or Opt-in C (citation-as-license-condition — recommended
   AGAINST for the code)? Default if unanswered: **Baseline + prepare Opt-in A skeleton**,
   no Opt-in C.
2. **ORCID / affiliation** for `.zenodo.json` + `CITATION.cff` `creators`/`authors`
   (strongly recommended for citation disambiguation). Provide, or omit? (These are the
   ONLY additive author-field edits permitted — the display name stays the publication
   form per the name-convention correction; ORCID/affiliation disambiguate it without
   changing it.)
3. **DOI type in `CITATION.cff`:** cite the **concept DOI** (all versions — recommended so
   the citation never goes stale) and/or the **version DOI**?
4. **JOSS paper (Opt-in A):** does the existing `~/VC/pubrun-paper` repo cover this? Should
   the agent draft a `paper.md`/`paper.bib` skeleton here, or leave paper authorship to the
   maintainer and only wire `preferred-citation` once a DOI exists?
5. **Does pubrun distribute any DATA/DOCS artifacts** (datasets, figures, generated
   corpora) that should be CC-BY-4.0 (Opt-in B)? If none, Opt-in B is N/A.
6. **When does the DOI actually get minted?** Zenodo mints on a *GitHub release* only after
   the repo is toggled on in Zenodo and the maintainer's Zenodo/ORCID is linked — an
   operator step the agent cannot do. Confirm the maintainer will (a) enable the repo in
   Zenodo, then (b) cut the release; the agent fills the concept DOI into `CITATION.cff`/
   README **after** the first minted DOI is known (or leaves a clearly-marked placeholder
   + a follow-up task, never a fake DOI).

## Plan-review record (2026-07-06)

Reviewed via `.agents/workflows/plan-review/plan-review.md`. Verdict: **APPROVE WITH
REVISIONS APPLIED**. Evidence re-opened against the actual repo. Findings fixed in place:

- **PR-1 (BLOCKER, name convention):** original step 2 would have pushed the legal name
  `Gabriele G. R.` onto `CITATION.cff` (a citation surface), regressing the project's
  two-form convention. Inverted: citation surfaces keep the publication name; only legal
  surfaces use the legal name. `pubrun cite` already does this correctly
  (`__main__.py:679-687`).
- **PR-2 (HIGH, false premise):** `pubrun cite` does **not** read `CITATION.cff` — it
  hardcodes strings (`__main__.py:661-695`). "Single source of truth" restated as a
  single *checked* source (a consistency test), with an explicit KISS/zero-dep decision
  NOT to add a CFF loader.
- **PR-3 (MEDIUM, stale claim):** the 2026-06-22 placeholder DOIs never landed; current
  `CITATION.cff` is clean. "Reconcile" restated as "confirm clean, never fabricate a
  DOI."
- **PR-4 (MEDIUM, fabrication risk):** added a guardrail so `docs/research-use.md`'s
  existing factual adoption claims are not altered/contradicted.
- **PR-5 (LOW, accuracy):** recorded the `CITATION.cff` `email` field and the concrete
  test targets (existing `test_cli.py` cite tests) + this session's suite baseline.

## Approval and execution gate

This IPD is a proposal. It MUST be reviewed and approved by a human before execution and is
NOT auto-executed. Because a real DOI requires an operator action in Zenodo, execution is
two-phase: (1) land `.zenodo.json`, the name fix, the citation-metadata scaffolding, docs,
and tests (no fabricated DOI — use a clearly-labeled placeholder + follow-up); (2) after the
maintainer enables Zenodo and the first release mints the concept DOI, fill the real DOI
into `CITATION.cff`/README/`pubrun cite` and validate. On completion, move this IPD to
`.agents/plans/executed/`. Recommended: run `plan-review` on this IPD, and consult an IP
attorney before any Opt-in C.
