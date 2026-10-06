# H33-2-B2 and the public leaderboard: evidence audit

**Snapshot date: 2026-10-05 (UTC).** This is an evidence review, not a claim that a score can be predicted from the public leaderboard. Read this before proposing that the H33 file earned an organizer score or that H41-A is ready to upload.

## Bottom line

The supplied experiment list reports `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` at **0.2778**. In the dated public-page observation captured on **2026-10-05 UTC**, the leaderboard showed **0.3262 at rank 1**, **0.3222 at rank 2**, **0.3220 at rank 3**, and **0.3195 at rank 4**. It also showed **0.2778 at rank 13** for participant `extradr19`. The leaderboard does not expose submission filenames or file hashes, so the rank-13 row cannot be attributed to the H33 TIFF from this page alone. GEMSDOE32's own page labels its H33 artifact `UNSCORED` and says that no organizer score exists for artifacts in that repository. Therefore:

- `0.2778` for the specific H33 filename remains **user-reported / not artifact-authenticated**.
- `0.3262` was the highest score in this dated observation; `0.3195` was rank 4 then. Current standings are unknown; neither value is asserted as current.
- A score attached to a leaderboard participant is not evidence that a particular TIFF earned it without an organizer receipt linking participant, submission ID, and file hash.
- The current H41-A TIFF is a distinct, format-checked research candidate, but its strict spatial holdout mean is zero. Its submission gate is **closed**. Do not spend a competition slot on it.

The public score table is dynamic. The date above is the observation date, not a promise that the page remains unchanged. This project does not monitor it: DrivenData's Terms prohibit robots, spiders, or other automatic access for any purpose, including monitoring, and manual monitoring requires prior written consent. The official page is linked for reference; the dated machine-readable record is [`research/leaderboard-observation.json`](leaderboard-observation.json).

## What H33-2-B2 changed

The GEMSDOE32 owner-authored page describes H33-2-B2 as a 2-pixel / 200 m catalogue-flank prune of an existing 0.2708 base. Its own validation JSON records:

| Quantity | Owner-reported value | Evidence status |
|---|---:|---|
| Base raster positive pixels | 40,199 | Reproduced as a value in the owner report; base bytes are not included in this repository's clean validation inputs |
| H33-2-B2 positive pixels | 37,654 | Also visible on the owner page; the educational comparison raster is checksum-pinned locally |
| Pixels removed | 2,545 (6.33% of base) | Arithmetic from the two counts above |
| Rule | Remove every prediction within 2 pixels (200 m) of the catalogue | Owner-authored H33 description |
| Owner-reported local-model proxy DTI | 0.26305 base; 0.26792 H33-2-B2; +0.00487; 4/4 folds positive | `research/upstream-h33-validation.json`; not an organizer score and not independently rerun here |
| Owner-reported live-anchored projection | 0.27467 | A model projection, explicitly not an organizer score |
| Score in the supplied experiment list | 0.2778 | User-reported filename-to-score mapping; no public receipt linking that TIFF to a leaderboard row |

This is principally **post-hoc thinning of an existing prediction field**, not a new fault detector or a new geological observation. The probable metric mechanism is plausible: the official score is a distance-weighted Tversky index with false-positive weight `alpha = 0.2`, false-negative weight `beta = 0.8`, and a 300 m triangular tolerance. Redundant dots can add false-positive mass without improving the maximum prediction covering a truth pixel; removing such dots can improve the ratio. But thinning can also remove a prediction that is the only nearby support for a real new fault. The tradeoff depends on the hidden truth, so the public formula does **not** prove the reported filename earned 0.2778.

The contest target is fault presence, not a geothermal-vent probability. The initial prize labels are described by the organizer as manually identified faults missing from the public USGS catalogue; the final round adds expert-verified discoveries. A catalogue buffer is therefore a reasonable sparsification hypothesis for the initial round, not a universal geological rule. It may be counterproductive for faults that branch from, intersect, or transfer strain into known structures, and can reduce coverage of the later expanded label set.

## Official leaderboard snapshot

| Rank | Participant shown by DrivenData | Public score |
|---:|---|---:|
| 1 | `nchuzhoy` | 0.3262 |
| 2 | `kinghorton42` | 0.3222 |
| 3 | `alexoktaba` | 0.3220 |
| 4 | `DARD` | 0.3195 |
| 13 | `extradr19` | 0.2778 |

This small table is transcribed from the public leaderboard on 2026-10-05 and is **historical only, not a current standings claim**. It corrects the stale assumption that 0.3195 was the leader in that observation and makes the score-to-file ambiguity explicit. Participant labels are reproduced as shown; no identity beyond the page is inferred.

## Why the scientific premise is useful—and where the prompt overstates it

Faulds, Henry & Hinz (2005) describe the northern Walker Lane as dominated by NW-striking, left-stepping dextral faults, N-striking normal faults, and subordinate ENE-striking sinistral faults; they interpret dextral fault arrays terminating in northerly normal faults as a transition from shear to extension. This is a sound regional motivation for testing cross-population structure. It does **not** establish that strike alone determines slip sense, or that every local corridor hosts geothermal flow.

There is a study-location/author correction:

- Siler, Mayhew & Faulds' blind-system paper is **Astor Pass**, not Emerson Pass. It documents a complex three-fault intersection near geothermal evidence and wells. It is relevant evidence for intersection-controlled circulation, but not a validation of every mapped NW-tip-to-normal-fault connector.
- Anderson & Faulds' blind-system study is **Emerson Pass**. It describes a broad left step between major north to north-northeast normal faults, opposing/overlapping normal-fault structures, and a regional setting in which Walker Lane dextral shear transfers into Basin-and-Range extension. This is not the same as Siler et al.'s Astor Pass study.
- Strike is an axial geometric measurement, not kinematic slip sense. The acquired catalogue's source slip-sense attributes disagree with a two-family strike assignment for some traces; the H41 output therefore calls its classes *geometric proxies*. Faulds et al.'s subordinate ENE sinistral population is also not represented by the forced two-family corridor model.

The 2005 regional model and the local case studies justify a **testable structural hypothesis**, not a geothermal discovery claim. The competition's official problem statement also asks for faults indicative of geothermal resources, not vent locations or reservoir temperatures.

## H41-A outcome and novelty audit

H41-A was preregistered as one of four structural hypotheses in [`research/hypotheses.md`](hypotheses.md). It uses official mapped fault geometry for strike-family position and a provided detrended-elevation band only as an independent local tangent/lineament proxy. It connects authentic, outward-facing NW-proxy endpoints to nearby N/NNE-proxy traces, suppresses pixels within 200 m of the existing raster catalogue, and requires local tangent agreement with the geometrically closer family. It does not read H33 prediction values when constructing the field.

The delivered candidate is [`gems41-walker-transfer-v1-20261005-1616b7de764c.tif`](../docs/downloads/gems41-walker-transfer-v1-20261005-1616b7de764c.tif), SHA-256 `8cd554d6caa94932879ecf7b73af5f9f9b24553eb5124f74dc1281940826a12c`. The local structural audit reports 268 accepted corridors, zero confidence mass within 200 m of the raster catalogue, 56.89% of total mass at defined junctions (versus 2.33% for the combined catalogue-density control), and 92.54% of the top 5% confidence cells at junctions. These are **construction diagnostics**, not independent evidence that the locations are faults.

The four-fold whole-source-geometry spatial holdout reports mean candidate DTI `0.0`; only fold 0 has any candidate prediction mass. The result fails the generalization gate. H41-A is distinct from the examined H33 raster (different arrays; support Jaccard about 0.00986), but neither that comparison nor a content hash proves global uniqueness against every private or unpublished submission. The file is available for inspection and download; the current evidence does not support uploading it.

## Next decision at the original H41-A audit

Do not tune H41-A against the failed audit folds. Keep those folds untouched. Before a new competition slot is considered:

1. Obtain an organizer submission receipt or explicitly continue labeling the H33 filename/score pair as user-reported.
2. Preserve the 20 km whole-trace holdout as a negative audit. Preregister a separate, geographically grouped transfer-zone test with donor/receiver structure observed but the target connector withheld; measure leakage and a catalogue-density control.
3. Test the remaining preregistered hypotheses (H41-B convergence, H41-C orientation handover, H41-D endpoint/topology stability) as distinct hypotheses on that new protocol. Do not search parameters on the failed folds.
4. Require improvement over a clean historical-best comparator before using a submission slot. A public score, locally calibrated synthetic-truth score, or format-valid TIFF is not a substitute for that test.

All four H41-A–D candidates in that initial plan use already acquired geometry and the provided topographic layer. They do not require a new external data source. If later work adds independent high-resolution terrain lineaments, the exact USGS 3DEP/DEM tiles, coverage, license, and reproducible processing must first be recorded; that is a separate hypothesis, not a condition silently assumed satisfied here.

## Later follow-on status (2026-10-05)

A separate four-hypothesis slate and fixed H41-E test are documented in [`research/hypotheses-next.md`](hypotheses-next.md) and [`research/experiments/h41e-kinematic-holdout.json`](experiments/h41e-kinematic-holdout.json). H41-E applied exact source `SLIPSENSE=RL` on NW donors and `SLIPSENSE=N` on N/NNE receivers, keeping the existing four spatial folds and model geometry fixed. Both H41-A and H41-E mean DTI were 0.0; H41-E won 0/4 folds and emitted zero prediction mass in each scored interior. It failed the preregistered gate. No new TIFF was created and no slot was used. H41-F, H41-G, and H41-H remain proposals; they have not been tested. The submission gate stays closed.

The ranked public-page rows above are preserved as a dated historical observation only. DrivenData monitoring has been removed from the daily refresh; the current score is unknown. The local permitted-source probes recorded TLS transport errors, which do not show that upstream sources are offline.

## Manual-review sources

- [Official DrivenData problem, metric, target and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — historical snapshot only; this repository does not monitor it
- [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) — automated monitoring is prohibited; manual monitoring requires prior written consent
- [DrivenData robots.txt](https://www.drivendata.org/robots.txt) — disallows the leaderboard-partial path
- [GEMSDOE32 owner-authored page for H33-2-B2](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) — secondary source, not an organizer score receipt
- [`research/upstream-h33-validation.json`](upstream-h33-validation.json) — owner-reported proxy validation values preserved for education
- [Faulds, Henry & Hinz (2005), Geology, DOI 10.1130/G21274.1](https://nbmg.unr.edu/staff/Faulds/faulds_et_al_geology_paper.pdf)
- [Siler, Mayhew & Faulds, Astor Pass (DOE OSTI)](https://www.osti.gov/servlets/purl/1110516)
- [Anderson & Faulds, Emerson Pass (DOE OSTI)](https://www.osti.gov/servlets/purl/1110518)
- [Official INGENIOUS data release, GDR 1391 (CC BY 4.0)](https://gdr.openei.org/submissions/1391)
- [Official GEMS prize rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
