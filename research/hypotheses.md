# Preregistered candidates — 2026-10-05, before model implementation

Initial audit: commit a3d465c contained only an 11-byte README. No local models, historical holdout best, split manifest, tests, or pipeline existed. Novelty relative to this repo is therefore trivial; novelty relative to siblings is assessed by method, not claimed exhaustively across private/unpublished experiments.

Ranking is qualitative expected utility, NOT a predicted DTI gain. All four target structural geometry; no new magnetic, gravity, conductivity, or thermal transform is proposed. Only H41-A will be implemented and evaluated in this run to avoid holdout fishing.

| Rank / ID | Layers and physical signature | Why potentially missing faults, not catalogue repetition | Difference from prior work reviewed | Cost / expected improvement |
|---|---|---|---|---|
| 1 H41-A | Training fault geometry, detrended elevation (band 12): NW endpoint → nearest N/NNE trace corridor, independent topographic tangent agreement with closer population | Off-catalogue connector gaps between unlike populations; endpoint-specific rather than generic fault density | Neither H33 catalogue-flank pruning nor detector-tip union; all-new confidence field from bipartite fault geometry | Moderate / most plausible among these, highly uncertain and potentially low recall |
| 2 H41-B | Same inputs: overlapping outward endpoint cones from two distinct NW traces meeting one N/NNE receiver | Requires two independent donor terminations, focuses previously unmapped relay splays | A three-trace graph motif instead of H33's union of generic tips; differs from H41-A's single nearest receiver | Moderate-high / more precise, fewer discoveries |
| 3 H41-C | Same inputs: local switch in matched lineament strike across the geometric Voronoi boundary of NW and N/NNE families | Targets cross-family handover, not within-family lineament continuation | Uses orientation transition location rather than broad strain or detector field | Moderate / plausible but noisy at 100 m |
| 4 H41-D | Same inputs: stable nearest-family corridors across trace simplification and endpoint perturbation (100–300 m) | Rejects false catalogue-segmentation endpoints while retaining robust unmapped connectors | Stability-selected topology, not changing dot budget on an existing submission | High / potential robustness gain, not independent new geology |

## Fixed H41-A design and gate
- Axial strikes (0–180°, clockwise from north); population prototypes 135° and 10°.
- Every usable trace assigned to nearest prototype, but only traces within 30° of that prototype eligible as corridor anchors. Neither strike nor the assigned label proves slip sense. Other orientations remain in the audit table.
- NW endpoints paired to geometrically nearest N/NNE trace. Maximum gap 5 km; endpoint must face receiver within 60° of outward tangent (unless within 200 m). Suppress connected artificial segmentation endpoints and boundary truncations.
- Corridor width 500 m, endpoint taper, reject pixels <=200 m from catalogue. Candidate score is corridor proximity multiplied by topographic tangent agreement; no catalogue-density multiplier.
- Independent lineament orientation from a smoothed detrended-elevation structure tensor; coherent gradients are a lineament proxy, not verified faults. Missing/flat areas receive zero support.
- Four deterministic spatial block folds, 20 km blocks, withheld blocks plus 300 m halo removed from anchors. Remove entire vector traces touching held-out regions to avoid leak through same-trace strike/endpoints. Score on held-out block interiors, not artificial cut tips. Rebuild geometry separately in each fold. No tuning on these outcomes.
- Evaluate official probabilistic DTI (300 m triangular support, alpha=.2, beta=.8); compare fresh density-only and topography-only controls, geometry ablation, and the historical H33 file as a contaminated descriptive benchmark (NOT a clean out-of-fold prediction).
- Slot gate requires beating controls in all four folds AND a valid clean historical-best comparison. Since no historical clean holdout exists locally, the slot gate remains CLOSED unless one becomes available. No automatic DrivenData upload.
- Verify junction concentration versus area and catalogue-density control, off-catalogue mass, pixel-array novelty, and exact grid/value format. Export even a failed candidate for research, prominently label not recommended for submission.

## Evidence anchors and correction
Faulds, Henry & Hinz (2005), doi:10.1130/G21274.1, https://nbmg.unr.edu/staff/Faulds/faulds_et_al_geology_paper.pdf supports NW dextral faults terminating in northerly normal fault systems. It also describes ENE sinistral faults; a forced binary kinematic truth would be wrong.

Siler, Mayhew & Faulds: https://www.osti.gov/servlets/purl/1110516 is **Astor Pass**, with NW dextral / NNW normal intersections. Emerson Pass: **Anderson & Faulds**, https://www.osti.gov/servlets/purl/1110518, describes opposing normal faults and a regional displacement-transfer setting. The prompt conflates these studies. Neither validates any pixel of this proposed model.

No new external dataset is essential: raster catalogue is a fallback if vectors cannot be obtained. Official full vectors are public at https://gdr.openei.org/files/1391/qfaults_ingenious_nad83conus117_2023-06-27.zip (CC BY 4.0, https://gdr.openei.org/submissions/1391). The listing is verified accessible; direct sandbox binary transport failed, so a GitHub Actions fetch is being tested before relying on it. Input mirrors have checksums but are not organizer-authenticated.
