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
