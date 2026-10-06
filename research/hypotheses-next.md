# Preregistered follow-on hypotheses — 2026-10-05

**Status at registration:** these four experiments had not been implemented or scored in GEMSDOE41. H41-A remained the only delivered model. Its strict four-fold score is 0.000000, so this registration makes no claim that any candidate will improve it. No submission slot may be used unless a candidate first beats the uncontaminated spatially blocked baseline and passes the project's independent validation gate.

## Ranking

The ranking is qualitative expected DTI utility, not a numeric forecast. The official test labels are hidden and the known-fault proxy target is incomplete; assigning invented expected scores would be misleading. Each candidate is intended to emit only outside the mapped catalogue, and a positive map is a hypothesis, not proof of a fault.

| Rank / ID | Specific data/layers | Physical signature targeted | Why it could locate a missing fault rather than repeat known density | Difference from implemented H41-A | Expected DTI direction / cost |
|---|---|---|---|---|---|
| 1 · H41-E | Official INGENIOUS Qfaults trace geometry plus per-trace `SLIPSENSE`; retain H41-A's existing detrended-elevation tangent check only | Kinematically concordant, off-catalogue NW right-lateral-to-N/NNE normal transfer corridors | Rejects NW-striking traces whose source attribute is normal or left-lateral, and N/NNE traces whose source attribute is not normal; predicts only the intervening gap, >200 m from the raster catalogue. This addresses measured disagreement between strike-only families and source kinematics. | H41-A uses strike as a *geometric proxy* and accepts 616 NW and 1,856 N/NNE corridor anchors without a kinematic screen. H41-E requires `SLIPSENSE=RL` on NW donor anchors and `SLIPSENSE=N` on N/NNE receivers, with all other H41-A geometry, lineament, fold, and distance settings frozen. No new geophysical transform. | Highest relative plausibility in this slate; improvement remains uncertain/possibly none. Low–moderate cost; local official vector data already restored. |
| 2 · H41-F | Same vector geometries, `SLIPSENSE=N`, single-valued `DIPDIRECT`; no new raster layer | Relay/overlap of oppositely dipping normal-fault terminations (accommodation-zone topology), with confidence only in the off-catalogue gap | A concealed linking strand may occur where two normal-fault segments terminate/overlap and their dip directions oppose one another. The exact Emerson Pass study describes oppositely dipping normal-fault intersections; it does **not** establish an NW-dextral fault termination at the geothermal site. | H41-A requires one NW endpoint and one normal receiver. H41-F is a normal-fault-only, dip-polarity graph motif; it has no NW-dextral donor and no topographic-orientation product. | Moderate potential but sparse/uncertain due missing or multi-valued dip attributes. Moderate cost; no additional data required. |
| 3 · H41-G | Official USGS 3DEP 1 m bare-earth DEM tiles plus the existing fault geometry; evaluate only tiles overlapping the competition grid | Multiscale slope-break / curvature edges and scarp-parallel continuity at 1 m, with terrain-illumination sensitivity controls | A young, surface-expressed but unmapped scarp can be sub-pixel at the 100 m training grid; independent fine-scale terrain edges could support a trace in an existing inter-population gap, not merely reproduce the catalogue. The method must suppress roads, channels, shorelines, and anthropogenic edges. | H41-A uses only broad tangent orientation from detrended-elevation band 12 at 100 m. H41-G uses independent 1 m terrain morphology and an explicit edge/curvature detector. This is topographic, not a new magnetic/gravity transform. | Potentially useful where coverage and geomorphic expression exist; high cost and incomplete regional coverage risk. **Source check:** USGS TNM Access API returned 64 1 m GeoTIFF records for bbox `[-119.8, 39.5, -119.0, 40.0]` (inside the study raster's geographic bounding box; not proof of valid-footprint coverage); sample record 6a4c609b1ba49be4d7c31079 has an official download URL. This proves obtainable tiles in that query window, not complete coverage or downloaded-byte verification for the whole footprint. API: https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-119.8,39.5,-119.0,40.0&prodFormats=GeoTIFF&max=5. Official 3DEP description says standard 1 m DEMs are bare-earth, LiDAR-derived and public domain: https://www.usgs.gov/3d-elevation-program/1-meter-digital-elevation-models-dem. |
| 4 · H41-H | Qfaults `RECNUM`/`RCODE2023`, `SLIPRTNUM`/`SCODE2023`, `FCODE2023`, and trace geometry | Spatial concentration of recent/high-rate, well-located fault terminations and cross-family gaps | Favors candidate gaps bounded by faults with mapped Quaternary activity and clearer source mapping, rather than smoothing the entire catalogue. It may prioritize structurally active corridors. | H41-A does not use age, slip-rate, or mapping-quality attributes; H41-H uses these independent per-trace metadata as an evidence-quality/recency condition, not a new geophysical layer. | Low-to-moderate expected improvement and moderate cost. Important risk: recency is not hydraulic connectivity, and the challenge scores faults, not geothermal favorability; this could bias against old but still mapped structures. |

## Top-candidate validation plan (fixed before implementation)

H41-E is selected for one evaluation because it addresses a specific documented weakness of H41-A: strike-only classification does not equal measured slip sense. It is not selected because of any observed holdout result.

1. Use the exact four deterministic 20 km spatial folds already recorded in `docs/downloads/holdout.json`; do not change the block formula, buffers, erosion, metric, or evaluation labels.
2. Within each fold, remove complete source features touching the held-out polygons plus 300 m. Build candidate anchors only from the remaining features.
3. Freeze eligibility as `H41-A eligible AND ((family 0 and source SLIPSENSE exactly RL) OR (family 1 and source SLIPSENSE exactly N))`. Use the source values as stored; do not impute missing values, infer slip from strike, or tune a threshold. All mapped traces still determine population-distance/Voronoi geometry and connected-fragment rejection, as in H41-A.
4. Keep the existing H41-A topographic tangent agreement and all H41-A geometric parameters unchanged. Use no label-derived feature or H33 prediction in construction. Exclude training-catalogue pixels only from anchors/prediction as already specified; held-out truth remains available only to scoring.
5. Report fold-wise candidate and H41-A DTI, emitted mass, number of anchors and corridors, plus control results. A fold with no candidate predictions remains zero, not dropped. Compare means on the fixed four folds and disclose any zero-support folds.
6. **Decision:** no weekly slot unless H41-E strictly beats the H41-A mean on this fixed audit, is not worse in any fold, beats non-vacuous matched-mass controls, passes the off-catalogue/junction audits, and a clean historical-best out-of-fold comparison becomes available. The current H41-A gate is already closed because its mean DTI is zero and no clean historical-best OOF file exists. Passing this small proxy test alone still cannot establish test-set rank or eligibility.

## Evidence anchors and scientific guardrails

- Competition task and labels: official DrivenData problem page, https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/. It states that the public fault set is incomplete and potentially inaccurate, and that the initial private test labels are expert-identified faults absent from the existing USGS database.
- Structural framework: Faulds, Henry & Hinz (2005), institutional full text, doi:10.1130/G21274.1, https://nbmg.unr.edu/staff/Faulds/faulds_et_al_geology_paper.pdf. The paper describes NW dextral faults, northerly normal faults, and also ENE sinistral faults; strike is not a substitute for kinematic attribution.
- Astor Pass: Siler, Mayhew & Faulds, DOE OSTI, https://www.osti.gov/servlets/purl/1110516. This is the NW dextral / northerly normal interaction example.
- Emerson Pass: Anderson & Faulds, DOE OSTI, https://www.osti.gov/servlets/purl/1110518. This paper describes the local blind geothermal system among oppositely dipping north- to north-northeast normal faults in a regional displacement-transfer setting. It is a different study from Astor Pass and does not validate H41-A or H41-E pixels.
- Fault geometry and kinematics: official GDR INGENIOUS v2 archive and field definitions, https://gdr.openei.org/submissions/1391, CC BY 4.0. The archive values intersecting the competition grid were actually read: NW-family parts include 724 `RL`, 686 `N`, 90 `LL`, and 1 missing; N/NNE-family parts include 641 `RL`, 3,129 `N`, and 269 `LL`. The field-definition text in the archive lists generic `SS` in its value table while the intersecting data contains `RL` and `LL`; preserve this schema irregularity and do not silently recode. The USGS Qfaults documentation defines RL as right-lateral and LL as left-lateral: https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixB.pdf.
- DrivenData leaderboard access: the official Terms of Use prohibit robots/spiders/automatic access for any purpose, including monitoring, and prohibit manual monitoring without prior written consent; the official `robots.txt` also disallows its leaderboard-partial path. We therefore must not poll or browser-scrape the leaderboard. The last recorded 2026-10-05 observation in this repository is historical context only; current rankings are unknown and this project does not monitor them. The competition page is linked for reference, not scraped: https://www.drivendata.org/termsofuse/ and https://www.drivendata.org/robots.txt.

## Irregularities to retain in the audit

1. `SLIPSENSE` values in the actual official archive (`RL`, `LL`, `N`) do not match the generic `SS`, `N`, `R`, `T` value list in the bundled field-definition text. H41-E only uses exact observed `RL` and `N`; no silent aliasing.
2. The prompt attributes an Emerson Pass intersection/transfer mechanism to Siler et al. It conflates Astor Pass (Siler et al.) with Emerson Pass (Anderson & Faulds). Keep their field examples separate.
3. Public leaderboard numeric values cannot be updated automatically without contravening DrivenData's published Terms of Use. The site can show its last dated observation and source-check health, but must never label the old score “current.”
4. The official TNM query verifies tile listings only in the selected window; full-coverage, tile completeness, and suitability must be checked before H41-G is run.

## Result — H41-E validation (2026-10-05)

The experiment was run after the preregistration above, with no fold or parameter changes. Reproduction command: `.venv/bin/python scripts/experiment_h41e.py`. Full receipt: `research/experiments/h41e-kinematic-holdout.json`.

- H41-A mean blocked DTI: **0.000000**; H41-E mean blocked DTI: **0.000000**; H41-E wins: **0/4** folds; no fold is worse, but there is no strict improvement.
- H41-E retained 52/475, 71/522, 92/627, and 132/517 eligible NW/normal anchors in folds 0–3, respectively, and formed 4, 7, 12, and 5 geometric corridors. Despite those corridors, the orientation/detection-gated candidate emitted **zero mass inside every scored validation interior**.
- The mass-matched density and topography controls were vacuous in all folds because candidate mass was zero; they cannot be counted as wins.
- **H41-E fails the preregistered gate.** No variant TIFF was exported, no weekly slot was used, and the existing H41-A TIFF remains the single prominently linked research artifact. Its file bytes were not changed by this experiment (SHA-256 `8cd554d6caa94932879ecf7b73af5f9f9b24553eb5124f74dc1281940826a12c`).
- This result rejects the tested kinematic-screened model under this proxy protocol; it does not prove that the structural setting lacks undiscovered faults. Clean historical-best OOF predictions and expert hidden labels remain unavailable.

## Result — H42 basin-margin validation (2026-10-06), the gate that opened

Preregistered rule, fixed in `scripts/build_h42_final.py` before the final build: *select the surface with the
highest mean DTI on the 20 km four-colour blocked holdout, emitted fresh inside every held-out block at equal mass,
cross-checked against the hidden-truth association measured from the 16 archived artifacts.*

- **Best valid arm: `SH_basin_strong|sep4.0|N40000` — mean DTI 0.2507** (worst fold 0.2423, best 0.2580),
  rank 1 of 21 arms. Controls on the identical domain and mass: uniform-random **0.1212**, training-catalogue
  density **0.1771**. Archived H41-A/H41-E arms on the same instrument: **0.0**.
- Surface: `( slope^0.5 · (1 − detrended_elevation)^1.5 )^0.55 · lidar_scarp^0.25 · tmi_hg^0.20`, packed at
  ≥4 px (400 m) to 40,000 px, with everything within 2 px (200 m) of the catalogue deleted.
- **Two instruments disagreed, and both readings are published.** The SGMC independent-map instrument ranks
  terrain-carpet surfaces far higher (detrended-elevation enrichment 1.9–2.8×) and puts the shipped surface at
  0.346 A→B / 0.322 B→A. A mass-controlled association across the 16 archived artifacts says that direction is
  wrong (detrended-elevation partial ρ = −0.56; the five highest-scoring artifacts sit at 0.89×). The blocked
  holdout agrees with the ledger, so the ledger association was the tie-breaker. This is a judgement call,
  recorded rather than hidden.
- **The thermal-anchored H42 weightings are a measured dead end** (best cpm 0.0426 vs uniform-random control
  0.0603 on the SGMC instrument; thermal layer lift 0.05). Do not rebuild them.
- **Ceiling, stated where the number is:** the holdout truth is the *published* catalogue, so this instrument
  cannot reward a genuinely new fault. It ranks geometry. 0.2507 is not a leaderboard forecast.
- Full receipts: `evidence/h42_holdout_20km.json`, `evidence/h42_final.json`,
  `evidence/h42_admissibility.json`, `evidence/h42_transfer_view.json`, `docs/downloads/h42-gate.json`.

### Ranked follow-on hypotheses (registered 2026-10-06, before implementation)

Registry entry with layers/signature/rationale/cost: `registry/hypotheses.json` → `new_candidates_ranked`.
Order: **H43-A** in-place geophysical re-ranking of the shipped 40,000 locations (lowest cost, no geometry
change); **H43-B** 1 m 3DEP curvature reconstruction (most distinct signal, acquisition outside the sandbox);
**H43-C** GDR wellspring re-ranking; **H43-D** catalogue-thinning response sweep; **H43-E** 2020 seismicity
envelope ordering. None may be used before it beats the shipped arm on the same fold design.
