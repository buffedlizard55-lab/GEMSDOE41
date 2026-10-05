# Prior-raster support audit — 2026-10-05 UTC

This is a pixel-support comparison, not a score or geological validation. The two prior GeoTIFFs were retrieved from the public GEMSDOE32 Pages/GitHub repository using the GitHub Contents API, inspected locally, and **not used to construct** H41-A. Local copies are kept in ignored `data/prior_reference/`; the new candidate was built from the competition inputs and H41-A code only.

## Compared files

| Artifact | Public source | SHA-256 | Nonzero support |
|---|---|---|---:|
| H27-4 base (`gems32-probe-S1-ANCHOR-identical-to-live-02600.tif`) | [GEMSDOE32 report](https://buffedlizard55-lab.github.io/GEMSDOE32/) · [direct TIFF](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/downloads/gems32-probe-S1-ANCHOR-identical-to-live-02600.tif) | `4dc4cc54b061cb4567a5500c8fa2bfe750a39340b02c8cdbb4308916f36cbcc3` | 44,090 |
| H33-2-B2 (`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`) | [GEMSDOE32 report](https://buffedlizard55-lab.github.io/GEMSDOE32/) · [direct TIFF](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` | 37,654 |
| New H41-A candidate | [`gemsdoe41-h41a-bimodal-transfer-20261005.tif`](../downloads/gemsdoe41-h41a-bimodal-transfer-20261005.tif) | `128ce3e92bcb0292a6a9f5a96d91877eee4f2ee7225d347311892dc8797aa902` | 39,793 |

All three files have the exact 3730×3292, EPSG:32611, 100 m template grid. For each comparison, support means finite cells with value >0, clipped to the 5,167,373-cell valid template footprint. Jaccard is intersection divided by union.

## Results

| Prior | Intersection | Candidate fraction inside prior | Jaccard |
|---|---:|---:|---:|
| H27-4 base | 423 | 1.063% | 0.0050683 |
| H33-2-B2 | 423 | 1.063% | 0.0054918 |

The low measured overlap is evidence that H41-A's nonzero support is not a copy of either checked raster. It does **not** establish uniqueness against all historical or inaccessible artifacts, and it does not show that the candidate support is geologically correct or likely to score.

The H33 artifact-to-score claim is treated separately in [`PROJECT_BRIEF.md`](../PROJECT_BRIEF.md): GEMSDOE32 labels its H33-2-B2 artifact unscored and reports a 0.2747 model projection; a later owner-maintained PR says “owner-reported” 0.2778; the current public leaderboard's 0.2778 row is for `extradr19` and does not name this raster.
