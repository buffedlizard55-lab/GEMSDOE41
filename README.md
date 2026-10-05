# GEMSDOE41 — GEMS fault-discovery research

**Live research site (GitHub Pages):** [buffedlizard55-lab.github.io/GEMSDOE41](https://buffedlizard55-lab.github.io/GEMSDOE41/) — main dashboard, obvious GeoTIFF download, and executive-summary guide.

> **Start-of-session rule:** before doing any work on this project, reread this entire `README.md`, then reread [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md). The README preserves the complete operating prompt; the brief preserves the evidence ledger, source links, dates, decisions, and irregularities. Keep both current as work proceeds.

## Full project prompt to carry forward

Review this repository and develop the DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge project toward a top leaderboard result. Work autonomously and carefully: research official rules, data, geology, existing methods, and historical project reports; verify claims line by line; cite trustworthy sources; distinguish official scores from owner reports, model projections, and local validation; and flag irregularities rather than silently treating them as facts.

Generate a **new, unique GeoTIFF** from the Walker Lane / Basin-and-Range structural-transfer hypothesis—not by copying a previous submission. Classify mapped traces by strike, score geometric strain-transfer corridors and orientation compatibility, and verify that predictions concentrate at inter-population junctions rather than merely reproducing the density of the existing fault catalogue. Do not add a new geophysical transform to this structural candidate. Prior submissions may be inspected only for education, auditing, and baselines; do not reuse their prediction pixels.

Explain why the H33 result was said to score 0.2778, check whether that file-to-score attribution is real, and assess whether the current approach can beat it and the current official leaderboard. Research **three to five previously untried hypotheses**, ranked by expected improvement and implementation cost. For each, identify its data layers, target physical signature, off-catalogue rationale, difference from inspected prior work, and free official data source; verify that the required data are actually obtainable before calling a candidate viable. Do not invent a numeric score forecast.

Before using any competition submission slot, preregister the test and validate the top candidate on a spatially blocked holdout against matched baselines. **Do not recommend or spend a slot on a candidate that has not beaten the current spatially blocked holdout best under the preregistered gate.** A holdout against known faults is only a proxy for discovery of the hidden expert labels, not evidence of a leaderboard score. If a candidate fails or cannot be evaluated, say so and keep it explicitly unscored.

Prioritize a valid single-band float32 GeoTIFF with probabilities in `[0,1]` inside its valid footprint, matching the official template's EPSG:32611 CRS, 100 m resolution, shape, geotransform, and bounds. Preserve the published null/NaN convention outside the valid footprint. Give the file a unique submission name and a short note. Create a clean GitHub Pages site with an obvious download and an executive-summary submission guide; include organized, sourced research and a live/current feed. Provide a reproducible build and independently reopen and validate the written raster.

Run at least three implementation/review passes: (1) implement and verify; (2) independently review, find defects, and fix them; (3) recheck the whole result against this prompt and the project brief. Surface all important limitations. Attempt a pull request and merge to `main` if GitHub permissions and checks allow. Follow the Arena Core Values explicitly: **“Maximize P(Win)”** and **“Own the Outcome.”**

### Standing corrections and scientific constraints

- **Never copy a prior submission raster** to create a new candidate.
- Do not spend a slot unless the preregistered spatial holdout gate passes and the candidate beats the best matched control.
- The registered 300 m catalogue exclusion reduces density echoes but can remove valid corrections: competition staff have said truth can occur within 300 m of known faults. Keep this tradeoff prominent.
- The Emerson Pass paper is **Anderson & Faulds (2012)**. **Siler, Mayhew & Faulds (2012)** is about Astor Pass. Do not conflate them.
- DrivenData data downloads are authentication-gated in this environment. A public owner mirror is useful for development but is not organizer-authenticated; record this limitation and the source hashes.
- Never present an owner-maintained score, model projection, or proxy holdout metric as an organizer score.

## Current executive summary

- **Candidate:** H41-A, a paired NW-tip to N/NNE-trace corridor score with independent `det_elev` orientation support. It is a new implementation in this repository and uses no new magnetic, gravity, or radiometric transform.
- **Status:** unscored research candidate. The preregistered holdout had zero H41-A support in all four test interiors; the candidate DTI is null/unevaluable, the terrain-only control pooled at 0.046888, and the promotion gate failed. No competition slot is authorized.
- **Artifact:** [`docs/downloads/gemsdoe41-h41a-bimodal-transfer-20261005.tif`](docs/downloads/gemsdoe41-h41a-bimodal-transfer-20261005.tif), 39,793 nonzero pixels and 30,000.000 expected probability mass; independent format audit passed.
- **Important input irregularity:** the owner-mirror `example_submission.tif` has the same positive-cell mask as `existing_faults.tif` (60,988 of 60,988 cells). This conflicts with the official problem page's description of the sample as predicting total fault absence. The build uses it only for grid and valid-footprint metadata; its values are never predictions.
- **Current leaderboard snapshot (2026-10-05 UTC):** public #1 `nchuzhoy` 0.3262; the 0.2778 row appears at #13 for `extradr19`. The official row does not identify the H33-2-B2 artifact. See the H33 attribution discussion in [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md).
- **Competition target:** identify faults missing from the public catalogue. Recovering withheld catalogue traces in a local holdout is only a proxy; it does not validate discovery of hidden expert labels.

The dated result ledger and current validation status are maintained in [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md), [`docs/hypotheses.md`](docs/hypotheses.md), and `docs/evidence/`. Do not infer a leaderboard score from any local result.

## Download and submission guidance

The primary download and status dashboard are in the [project site](docs/index.html). The executive-summary upload guide is [`docs/submission-guide.html`](docs/submission-guide.html). The candidate file, format receipt, holdout report, and input audit are linked there after the build has run. The file is deliberately labeled **unscored**; do not use a weekly slot while `slot_eligible` is false.

Submission note (for identification only; this does **not** authorize an upload):

> `GEMSDOE41 H41-A | paired NW–N/NNE transfer corridors with det_elev orientation support; 300 m catalogue exclusion; unscored research candidate`

The exclusion can miss real new-fault truth within 300 m of mapped traces. Review the full tradeoff and official format caveat in the site guide before any future upload.

## Reproduction

The large competition inputs are **not checked into Git**. Place the locally available, hash-pinned owner-mirror files under `data/raw/`:

- `example_submission.tif`
- `existing_faults.tif`
- `training_features.tif`
- `source_manifest.json`

Install dependencies and audit the inputs first:

```bash
python -m pip install -e '.[test]'
python scripts/audit_inputs.py
python -m pytest -q
```

After reviewing [`docs/hypotheses.md`](docs/hypotheses.md) and the registered thresholds, run the holdout and build:

```bash
python scripts/build_submission.py --data-dir data/raw
```

The build writes `docs/downloads/gemsdoe41-h41a-bimodal-transfer-20261005.tif` and the build/holdout receipts under `docs/evidence/`. It never uploads to DrivenData. Do not change registered parameters after looking at holdout results and still call that same test preregistered; any new experiment needs a new, dated protocol and an explicit exploratory label.

The repository's Python package and tests are defined in [`pyproject.toml`](pyproject.toml). Large local data, virtual environments, and caches are ignored by Git.

## Research and evidence

- [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) — dated official leaderboard, H33 attribution audit, format and data findings, citations, current decision, and irregularities.
- [`docs/hypotheses.md`](docs/hypotheses.md) — three ranked hypotheses, source availability, preregistered H41-A parameters, controls, holdout split, and promotion gate.
- [`docs/evidence/prior_raster_uniqueness.md`](docs/evidence/prior_raster_uniqueness.md) — exact support-mask overlap with two retrievable prior GeoTIFFs.
- [`docs/evidence/review_log.md`](docs/evidence/review_log.md) — three implementation/review passes, defects found, fixes, and final gate result.
- [`docs/index.html`](docs/index.html) — GitHub Pages research and live-feed landing page.
- [`docs/submission-guide.html`](docs/submission-guide.html) — concise candidate status, format, limitations, and upload guidance.
- [DrivenData problem, metric, and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Anderson & Faulds (2012), Emerson Pass](https://www.osti.gov/biblio/1110518); [Siler, Mayhew & Faulds (2012), Astor Pass](https://www.osti.gov/biblio/1110516)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS ComCat live event API](https://earthquake.usgs.gov/fdsnws/event/1/)
- [USGS TNM Access API / 3DEP](https://tnmaccess.nationalmap.gov/api/v1/products); [USGS 3DHP Flowline service](https://hydro.nationalmap.gov/arcgis/rest/services/3DHP_all/MapServer/50)

**Project principle:** maximize probability of winning by selecting only evidence-backed candidates; own the outcome by preserving provenance, tests, reproducible artifacts, limitations, and correction history.
