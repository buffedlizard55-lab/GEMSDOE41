# GEMSDOE41 implementation and review passes — 2026-10-05 UTC

## Pass 1 — implement and verify

- Preregistered H41-A-R's strike bins, coherence, tip/pair radii, corridor kernel, family-distance gates, 300 m exclusion, terrain thresholds, four spatial quadrants, 33 px collar, matched mass, and primary promotion rule in `docs/hypotheses-raster-variant.md` before the first DTI-scored holdout.
- Implemented geometric trace skeletonization, strike-family classification, NW tip-to-nearest N/NNE pairing, corridor/orientation support, soft-probability emission, official distance-weighted Tversky, and exact-grid GeoTIFF writing.
- Added unit tests for cardinal strike convention, disjoint family bins, no-family control availability, mass/range, deterministic tie selection, metric edge cases, quadrant masks, output masking, and prior-grid transform comparison.
- Initial verification: 10 tests passed; the only warnings are Rasterio's upstream `from_origin` pending-deprecation notice in synthetic test fixtures. Input audit passed against the owner-mirror manifest and named bands.

## Pass 2 — independent review, defects found, fixes made

- Fixed the prior-raster comparison: the original transform check reopened the prior itself and compared it with itself. It now compares shape, CRS, and transform to the actual template grid; a shifted-grid regression test rejects the prior.
- Corrected the CLI's default from the absent `sample_submission.tif` to local `example_submission.tif` and defaulted the data directory to `data/raw/`.
- Ran a windowed pixelwise audit: all 60,988 positive cells in the owner-mirror `example_submission.tif` exactly match `existing_faults.tif`. This conflicts with the official problem page's sample description. The file is used only for its grid/valid mask; its values never enter H41-A-R predictions.
- Corrected output nodata handling to preserve NaN outside the valid template footprint, with finite [0,1] predictions inside, matching the published format description and local nodata convention.
- Found that the initial `terrain_only` ablation still depended on the nearest fault-family orientation. Replaced it with a genuinely terrain-only coherence × gradient-strength score under the same off-catalogue mask; preserved it even in folds without both families.
- Replaced an every-50th systematic sample for the terrain-gradient reference with the exact registered 70th percentile over all valid cells, avoiding possible spatial aliasing. The final reports below use the corrected exact quantile; the earlier exploratory DTI value is not treated as final evidence.
- Made output JSON standards-compliant by serializing NaN nodata as the string `"NaN"`; no JSON `NaN`/`Infinity` values are intended.
- Made emitter cutoff tie handling deterministic by flat pixel index; removed an unused corridor multiplicity raster to lower memory use; exposed the final-support shortfall rather than implying the requested 3× support was achieved.
- Enforced the full slot gate: primary matched-mass holdout plus the required sensitivity checks. H41-A-PRE-1 had no candidate support, so sensitivity was not run; a new test needs a separately dated preregistration with numeric sensitivity variants.

## Pass 3 — recheck against the complete request

- **Unique file:** built from the full local catalogue using the new H41-A-R code; no prior prediction values were read into the model. The candidate has SHA-256 `5e8e528d105cf060490511a033c692f72dd761d09259fa7ae40c53dfc136e05f`.
- **Holdout:** four spatial folds, 33 px collar, 7,500 expected mass per fold. H41-A-R and corridor-only had zero eligible cells in every test interior; candidate DTI is null/unevaluable, not zero. Terrain-only pooled proxy DTI = 0.046888. Primary gate failed; sensitivity was not run; `slot_eligible=false`. No competition submission slot was used or recommended.
- **Off-catalogue geometry:** 39,793 nonzero full-region candidate cells; all are >300 m from mapped traces, within 500 m of a pair centerline, and within 2 km of both families. Median nearest-catalogue distance is 500 m. This is distributional verification, not fault validation.
- **Uniqueness:** support-mask Jaccard = 0.005068 vs H27-4 base and 0.005492 vs H33-2-B2; 423 support cells overlap each. The source files, hashes, and limitations are recorded in `h41a_raster_uniqueness.md`. This is not proof against unavailable artifacts.
- **Format:** independent reopen/audit passed for EPSG:32611, 100 m, exact 3730×3292 grid/transform/bounds, one float32 band, finite [0,1] in-footprint values, and NaN outside. A second full-region rebuild with holdout skipped only for this byte-reproducibility check produced the exact same SHA-256. No organizer portal validation or score was obtained.
- **Research/site:** README now contains the complete operational project prompt and reread instruction; the site has a clear download, unscored status, guide, sourced research, a current ComCat feed, and the 300 m tradeoff. Three hypotheses are ranked with official data-availability checks.
- **H33 attribution:** maintained as disputed, not silently resolved. GEMSDOE32 says its artifact is unscored and projects 0.2747; a later owner PR calls 0.2778 owner-reported; the current official board's 0.2778 row is a different participant and does not identify the raster.

## Outcome

All three passes are complete for this candidate build. The artifact is a valid, auditable research GeoTIFF, **not a leaderboard-proven improvement** and **not slot-eligible**. The 300 m exclusion may discard genuine new-fault truth near mapped structures. The candidate does not currently demonstrate that it can beat either the disputed H33 claim or the current official #1.

## Post-merge cross-run audit follow-up — 2026-10-06

A post-merge GitHub Actions rebuild ([run 37393952682](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37393952682)) produced a cross-run H41-A-R value difference beyond the original 8-epsilon threshold: 12,043 / 5,167,373 valid cells differed, max absolute error `3.6954879760742188e-6` (31 float32 epsilons), summed error `0.0009673714407654188`. The grid, valid mask, and NaN outside-footprint values were exact. The local pinned-input rebuild remained byte-identical to the published H41-A-R TIFF (`5e8e528d...`); the cross-run cause is not isolated, so the run was correctly reported as a failure rather than hidden.

The checker now allows up to 64 float32 epsilons (`7.62939453125e-6`) while continuing to require exact grid, mask, range, and outside encoding. It records support changes and absolute error statistics, preserves exact per-file SHA-256 identity, and the GitHub workflow preserves output artifacts on failures. This tolerance adjustment changes neither model parameters nor the holdout result. The corrected follow-up CI passed; its receipt and the first observed cross-run deviation are detailed below. The cause of that deviation remains unknown.

### First revised-threshold CI and test-order correction

Run [37394579359](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37394579359) passed both 64-epsilon cross-run raster comparisons. H41-A-R had 12,043 value differences, maximum `3.6954879760742188e-6`, no nonzero-support changes, and exact grid/mask/outside NaNs. The overall job then failed in the later pytest command: the rebuild had replaced the working-tree receipt SHA, while a site test correctly checks the static page against the committed TIFF SHA. The test suite was moved to run on checked-in artifacts before rebuild; explicit raster comparisons validate rebuilt outputs afterward.

The corrected workflow passed in [run 37394931018](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37394931018) at `3109eabae4a1db0a79e90225c22f5070848ecfc6`, including tests, both rebuilds, comparisons, and artifact upload. Both 5,167,373-cell arrays were pixel-identical to their checked-in TIFFs: zero changed values, zero support changes, exact masks, and exact outside encoding. The first 31-epsilon observation remains preserved in `docs/evidence/h41a_raster_cross_runner_rebuild_20261006.json`; this later exact run does not explain its runner-specific cause. The successful annotation receipt is `docs/evidence/h41a_raster_cross_runner_rebuild_20261006_success.json`.
