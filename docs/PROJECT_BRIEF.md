# GEMSDOE41 project brief and standing instructions

> **Read this document and the root `README.md` before every project session.** The README is the short operating charter; this file preserves the requirements and claims that drive the work. Keep scientific claims sourced, distinguish organizer-observed scores from local estimates, and record irregularities instead of silently treating them as facts.

## Mission

Build an auditable, useful system for the DOE Geologic Enhanced Mapping System (GEMS) Prize Challenge that can research, test, validate, and produce a competition-compliant single-band GeoTIFF for fault discovery in the GeoDAWN area. The objective is to improve the chance of identifying faults not represented by the public USGS/INGENIOUS catalogue, not to reproduce the catalogue's own spatial density. Make the GeoTIFF easy to find and download, with a unique submission name and a concise note, and explain the upload process prominently.

**Core values:**

- **Maximize P(Win).** Treat scarce competition submissions as experiments, not lottery tickets. Prefer hypotheses with a physical mechanism, suitable data, a preregistered spatial holdout, and a measured gain over a matched baseline.
- **Own the Outcome.** Carry each result from source provenance through code, tests, raster bytes, and honest reporting. Correct errors and disclose limitations.

## Non-negotiable scientific and competition requirements

1. Read the full user task/brief before changing the project; do not rely on memory or summaries alone.
2. Research competition rules, data, scoring, and geology from official or primary sources. Link sources so a reviewer can check them. Record access dates and hashes where possible.
3. Generate **new** hypotheses and artifacts; never copy a prior submission. A prior artifact may be inspected only as a learning/baseline reference. Run an explicit uniqueness check against any retrievable prior artifacts before calling a new file unique.
4. Before spending any weekly submission slot, preregister 3–5 candidate hypotheses, state the data layers, physical signature, off-catalogue rationale, novelty, expected value, and cost, then test the top candidate on spatially blocked holdout data against a matched in-repository baseline. A holdout against known catalogue faults is only a proxy: it cannot establish performance on the hidden, deliberately new fault set.
5. If a candidate depends on external data, name the specific free, official source and verify its availability before calling it viable. Do not silently substitute an owner mirror for an organizer-authenticated input.
6. For a submission GeoTIFF, preserve the competition grid exactly: EPSG:32611, 100 m, same transform/bounds/shape, one float32 band, prediction values in [0, 1]. Reopen the written bytes and verify the format and range; avoid sentinel values or NaN in the scored footprint. The competition page says outside-area values should be null/NaN; any all-finite encoding used to prevent validator rejection must be explained and checked against the sample template.
7. Label each score as one of: official leaderboard score, owner-reported claim, local proxy/holdout score, or model projection. Never call a local estimate an organizer score.
8. Keep an irregularity/limitations register. The contest's private labels, DrivenData login, hidden scoring implementation, submission-slot availability, and GPU or external-data needs are not assumed to be available unless actually verified.
9. The intended deliverable is one obvious, downloadable `.tif`, a unique submission name, a short submission note, an executive-summary/upload guide, source links, a reproducible build, and validation evidence.

## Historical experiments supplied by the project owner

The owner supplied public links and scores from GEMSDOE-family projects. These are **owner-provided context, not independently organizer-verified provenance**. Keep them as comparison history, not evidence that a particular artifact achieved a score unless its identity is independently linked to an official result.

The supplied history includes (among many others):

- earlier catalogue/density and dual-family approaches reported around 0.156;
- early point/ridge/topography approaches from roughly 0.01 to 0.19;
- H19-4/H19-5 multi-line / dotted emission reports around 0.189–0.192;
- the H24–H28 topographic-gap / dotted-ridge family reported around 0.248–0.271;
- H32/H33 structural and emission experiments, including a claimed 0.2778 association;
- H39 and subsequent repositories with unscored or zero-status files.

The full list of historical site URLs, file labels, and owner-provided scores is preserved in the original user task in the conversation history. Do not promote the supplied scores to ground truth without an official artifact-to-score record.

## Verified findings for this checkout (2026-10-05 UTC)

- The starting checkout contained only `README.md` (`# GEMSDOE41`) and no code or data. This is a repository inspection fact, not a scientific conclusion.
- The official problem page describes a hidden set of newly identified faults and a distance-weighted Tversky (DTI) metric. It specifies alpha=0.2, beta=0.8, a 300 m triangular distance kernel, and a single-band float32 GeoTIFF in EPSG:32611 at 100 m with the training grid's bounds/shape.
- A live read of the official leaderboard on 2026-10-05 returned public #1 `nchuzhoy` at 0.3262, #2 `kinghorton42` at 0.3222, #3 `alexoktaba` at 0.3220, and #4 `DARD` at 0.3195. The user's 0.3195 figure is therefore not the current #1 at this read time.
- H33-2-B2's score attribution is disputed. The GEMSDOE32 site calls its 37,654-pixel H33-2-B2 artifact **UNSCORED**, reports a 0.2747 live-mirror **model projection**, and says no organizer score exists for artifacts in that repository. A later owner-maintained GEMSDOE39 PR calls 0.2778 “owner-reported” and describes H33-2-B2 as a 37,654-pixel prune of a 40,199-pixel 0.2708 base (2,545 deleted cells 1.414–2 pixels from the catalogue), but supplies no organizer receipt. The current official leaderboard has a 0.2778 row at #13 for participant `extradr19`; it does not identify that participant's file as H33-2-B2. Thus **the numeric public row is real, but the H33-artifact attribution is not verified**. The proposed explanation—removing catalogue-flank emission to trade precision against recall—is a plausible hypothesis, not a verified account of why that official entry scored as it did. Sources: [GEMSDOE32 report](https://buffedlizard55-lab.github.io/GEMSDOE32/), [GEMSDOE39 PR #11](https://github.com/buffedlizard55-lab/GEMSDOE39/pull/11), [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- The supplied/linked geological-source attribution needs correction: the directly relevant *Emerson Pass* paper available from DOE OSTI is by **Anderson & Faulds (2012)** (OSTI ID 1110518), while **Siler, Mayhew & Faulds (2012)** (OSTI ID 1110516) is about **Astor Pass**, not Emerson Pass. Both discuss Walker Lane/Basin-and-Range structural intersections, but their field sites must not be conflated.
- The supplied raster mirrors were fetched from the public [`buffedlizard55-lab/GEMSDOE` GitHub data bridge](https://github.com/buffedlizard55-lab/GEMSDOE) for local analysis. Their SHA-256 hashes match the bridge manifest: example/sample `2176d08e…`, existing faults/labels `7ba308cc…`, and the 19-band training feature stack `4371c82e…`. This confirms byte integrity relative to that **owner-maintained mirror**, not organizer authentication. The DrivenData data page remains login-gated in this environment.
- The local owner-mirror `example_submission.tif` has 1 band, float32, EPSG:32611, shape 3730×3292, 100 m pixels, transform origin (243350, 4508550), bounds (243350, 4135550, 572550, 4508550), and NaN nodata outside 5,167,373 finite cells. **A windowed pixelwise audit found its positive mask exactly equals `existing_faults.tif`: all 60,988 positive cells overlap, with zero binary disagreements.** This conflicts with the official problem page's description of its sample as predicting total fault absence. The input is therefore treated strictly as a grid/footprint template; its pixel values are never used as H41-A predictions. The official organizer-provided file, not the owner mirror, remains format authority.

## Source links for the initial research

- [DrivenData GEMS problem, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData GEMS leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [GEMSDOE32 H33-2-B2 report](https://buffedlizard55-lab.github.io/GEMSDOE32/) and [GEMSDOE39 PR #11 attribution discussion](https://github.com/buffedlizard55-lab/GEMSDOE39/pull/11)
- [DrivenData competition data page (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Faulds, Henry & Hinz (2005), *Kinematics of the northern Walker Lane*, DOI 10.1130/G21274.1](https://doi.org/10.1130/G21274.1)
- [Anderson & Faulds (2012), Emerson Pass, DOE OSTI 1110518](https://www.osti.gov/biblio/1110518)
- [Siler, Mayhew & Faulds (2012), Astor Pass, DOE OSTI 1110516](https://www.osti.gov/biblio/1110516)
- [USGS GeoDAWN data release, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS National Map Downloader / 3DEP](https://apps.nationalmap.gov/downloader/) and [TNM Access API](https://tnmaccess.nationalmap.gov/api/v1/products)
- [USGS 3DHP all MapServer](https://hydro.nationalmap.gov/arcgis/rest/services/3DHP_all/MapServer) (open flowline layer 50)
- [USGS National Hydrography products](https://www.usgs.gov/national-hydrography/access-national-hydrography-products)
- [USGS ComCat FDSN event API](https://earthquake.usgs.gov/fdsnws/event/1/)
- [DrivenData staff clarification on known-fault masking](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4) (community staff reply; useful for interpretation, not a substitute for the formal competition terms).

## Current result and decision (2026-10-05 UTC)

H41-A is implemented and its corrected `H41-A-PRE-1` four-quadrant holdout completed. Code review replaced an earlier every-50th terrain-gradient sample with the exact preregistered 70th percentile; final evidence below reflects the corrected implementation, while the preliminary score is not retained as final evidence. In every fold, the full candidate and corridor-only arm had **zero eligible prediction cells** in the 3.3 km-collared evaluation interior. The candidate's DTI is therefore **null / unevaluable**, not zero; there are no paired fold comparisons and no candidate-vs-control win. The terrain-only matched-mass control has pooled local proxy DTI **0.046888**, but that is not a candidate score and cannot establish a head-to-head gain. The registered promotion gate fails; `slot_eligible` is false. No competition slot is recommended or has been used.

The full-visible-catalogue raster is nevertheless generated as a new offline research artifact. It has 39,793 nonzero pixels with 30,000 expected probability mass; all emitted support is outside 300 m of mapped traces, within 500 m of a paired-corridor centerline, and within 2 km of both mapped families. Its support-mask Jaccard is 0.00507 against the retrieved H27-4 base and 0.00549 against the retrieved H33-2-B2 raster (423 overlapping cells in each case). These comparisons establish low overlap with those two accessible supports only, not proof of global uniqueness or geological truth.

An independent byte-level format check passed: one float32 band, EPSG:32611, 3730×3292, 100 m, exact template transform/bounds, finite in-footprint values in [0,1], and NaN outside the template footprint. The output is still **UNSCORED**; the organizer's portal validator and hidden labels were not accessed. The strongest scientific limitation remains the 300 m novelty exclusion: staff have said genuine truth may lie within that distance, so the filter can discard valid corrections.

The registered collar is 33 px (3.3 km), which exceeds the 30 px tip-pair radius but is 2 px smaller than the maximum 35 px corridor centerline-plus-support reach. No candidate pixels entered any scored block, so the margin did not create a candidate overlap in this run; it remains a protocol limitation for any future nonzero fold. The sensitivity gate was not numerically specified or run; any future attempt needs a new dated preregistration. Full details are in `docs/evidence/h41a_holdout_20261005.json`, `docs/evidence/h41a_build_receipt.json`, and `docs/evidence/h41a_format_audit.json`.

The leading scientific mechanism remains a **bimodal structural-transfer corridor**: classify mapped traces into NW-striking Walker Lane and N-to-NNE Basin-and-Range populations; pair NW tips with nearby normal-family traces; then require independent local lineament-orientation support from `det_elev`. It uses no new magnetic, gravity, or radiometric transform. The execution result does **not** establish that it can beat the 0.2778 owner-reported H33 claim or the current official leader at 0.3262. The H33 file-to-score attribution remains disputed as recorded above.

## Work loop

For every session: (1) read `README.md` and this brief; (2) inspect current branch/status and data provenance; (3) check the live official leaderboard and competition page when external network tools are available; (4) preregister before tuning; (5) implement and test; (6) independently reread and audit output bytes; (7) update results, limitations, and sources; (8) do not claim a score not observed on the official leaderboard.
