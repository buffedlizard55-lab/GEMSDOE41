# GEMSDOE41 — Walker Lane structural transfer

**[Download the new GeoTIFF](docs/downloads/gems41-walker-transfer-v1-20261005-1616b7de764c.tif)** · **[Project website](https://buffedlizard55-lab.github.io/GEMSDOE41/)** · [Submission instructions](docs/executive-summary.html)

**Research candidate, NOT cleared for a weekly submission.** This is a genuinely new structural-position prediction, not a renamed previous submission. All numerical cells are finite float32 in [0,1]; an internal mask marks the template's outside region as null. The strict blocked holdout failed to establish useful generalization. No competition slot was spent, and no leaderboard improvement is claimed.

**Dated leaderboard observation (2026-10-05 UTC only):** the public page showed rank 1 at 0.3262, rank 4 at 0.3195, and rank 13 at 0.2778 for `extradr19`. Current standings are unknown; participant rows do not identify TIFFs. The H33 filename-to-0.2778 mapping remains user-reported, not artifact-authenticated. We do not monitor the leaderboard. See the [H33 score audit](research/h33-score-analysis.md).

## Second line of work — kinematic ranking of the support (branch `arena/1ac0a279-gemsdoe41`)

A separate, independently validated result lives beside the structural-transfer model above. It
leaves the transfer-corridor hypothesis alone — **that hypothesis failed and is published as a
failure** — and instead re-ranks the *incumbent* fault support by local structural kinematics
(strike population of the adjacent strands and junction proximity) before emitting pixels.

Measured on four strand-level folds, identical truth, identical allowed domain, identical minimum
separation, credit-per-mass:

| emitted mass | kinematic ranking | uniform control | ratio |
|---|---|---|---|
| 2,500 px | 0.0833 | 0.0549 | **1.52x** |
| 5,000 px | 0.0788 | 0.0606 | **1.30x** |
| 20,000 px | 0.0727 | 0.0581 | **1.25x** |
| 30,000 px | 0.0671 | 0.0667 | 1.006x |

The criterion wins at **6 of 6** guard/separation settings (mean 0.0773 vs 0.0636, a factor of
1.22) — but it is **nearly inert at the ~37,000 px mass the public leaderboard's best files use**
(94.1 % of its pixels coincide with an uninformative control there). That is why the primary
artifact ships at 20,000 px: the mass band where the criterion is measurably active.

Three independent tests say the transfer-corridor story does **not** explain the hidden set:
corridor-only emission scores 0.0000 on the holdout; the 2020 USGS catalogue places 16 M>=4
events 7.07-83.19 px from every mapped fault (0 within 300 m, 11 beyond 3 km); and against 27,092
INGENIOUS well records the corridors are *depleted* for hot sites (0.34x, p=1.0) while the
published catalogue is enriched 2.15x at p=0.016 — so the test has power and the corridor fails
it.

Artifacts and the full write-up: **[`docs/h41/`](docs/h41/index.html)** (overview, executive
summary, submit, validation, hypotheses, sources, irregularities) with one-click GeoTIFFs in
[`docs/downloads/`](docs/downloads/index.html). All six artifacts pass range, CRS, shape and
geotransform checks on the files themselves. Sources and open compliance questions are in
`registry/sources.json` and `registry/irregularities.json` (see **IRR-01**: this repository is a
public fork of an organizers' repository and needs a human decision before merge).

**Honest limit:** credit-per-mass is measured against the *published* catalogue's strands, not the
hidden set, and projected scores are tagged `[MODEL]` because they depend on a constant inferred
from one reported hidden-set size. Nothing here claims a leaderboard score. Six open items — the
authenticated score this sandbox cannot obtain, the `K_HIDDEN_PX` calibration, two candidates whose
official archives the sandbox cannot download, the resolution floor of the mass ladder, and the
compliance question — are listed with what would unblock each one in
[`docs/h41/index.html#remaining`](docs/h41/index.html).

## Start every session here
Read the original brief below, `research/hypotheses.md`, `research/hypotheses-next.md`, `research/h33-score-analysis.md`, `docs/research.html`, `docs/h41/index.html`, and `research/review-passes.md` before changing the model. For the supplemental raster implementation, also read `docs/hypotheses-raster-variant.md`, `docs/PROJECT_BRIEF.md`, and `docs/evidence/h41a_raster_review_log.md`. Preserve honest failed experiments. **Maximize P(Win):** do not spend slots on unvalidated hypotheses. **Own the Outcome:** deliver working artifacts and report problems rather than hiding them.

## Reproduce (CPU, no GPU needed)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run_pipeline.py
.venv/bin/python scripts/build_site.py
```

GitHub CLI (`gh`) is used to restore checksum-pinned public owner mirrors because the sandbox cannot directly download their binary upstream resources. Core input rasters (~420 MB) remain ignored. The small official GDR vector archive (6.1 MB, CC BY 4.0) is preserved in `data/official/` after direct acquisition on GitHub Actions. See `data/README.md`. The H33 raster is downloaded **only for education and descriptive comparison**, never as a model input.

- `scripts/model.py`: axial trace classification, authentic endpoints, cross-population corridors, independent topographic tangent matching.
- `scripts/metric.py`: published probabilistic distance-weighted Tversky index.
- `scripts/run_pipeline.py`: four spatial block folds, full-trace withholding, controls, prediction, novelty and junction audits.
- `scripts/validate_submission.py`: independent format re-read, exact grid, range and internal-mask assertions.
- `docs/downloads/`: submission TIFF, per-trace classification, corridor geometry, machine-readable audits and manifest.
- `docs/related-sites.json`: source audit of all 39 supplied related websites. Owner claims are not official score receipts.
- `docs/source-feed.json`: timestamped health snapshot for permitted non-competition official sources. DrivenData leaderboard polling is disabled because its Terms of Use prohibit automated monitoring; its dated historical snapshot is not represented as current.
- `research/experiments/h41e-kinematic-holdout.json`: preregistered H41-E kinematic-screen test on the unchanged spatial blocks; negative result, no new TIFF or slot.
- `research/h33-score-analysis.md`: dated source audit of the reported H33 score, historical public leaderboard rows, and the unresolved participant-to-file attribution.

**Limitations:** no authenticated DrivenData account, hidden labels, organizer filename-to-score receipt, or clean historical-best out-of-fold predictions. The repository initially contained only its title, so there was no prior local pipeline or holdout to resume. Geometric strike is not measured slip sense; the brief conflates Astor Pass and Emerson Pass. The last archived leaderboard observation (0.3262 on 2026-10-05) is historical, not current. Full evidence, corrections, and next-session priorities are in the website.

## Original user brief — preserved as the project starting point

The text below is the requested project brief, not a declaration that its factual assertions have been verified. Corrections and measured status above and in the research report take precedence over historical assumptions.

<details>
<summary>Read the complete original prompt</summary>

Review the repo.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.

Walker Lane bimodal structural position, no new geophysical transform. Build this from structural position alone: classify every known fault trace in the training catalogue by strike into NW-striking dextral (Walker Lane) or NNE-to-N-striking normal (Basin-and-Range), per the structural framework Faulds, Henry, and Hinz documented for this exact region (Geology, 2005) and confirmed as a real local mechanism by Siler and colleagues' Emerson Pass blind-system study, where a dextral fault's termination transfers strain into a normal fault at their intersection. Score every pixel on two purely geometric criteria: proximity to a plausible strain-transfer corridor between a mapped NW fault's endpoint and the nearest mapped NNE fault, and whether any locally detected lineament's orientation matches whichever population is geometrically closer. Normalize to [0,1], write to the required format, and verify before download that predicted pixels concentrate at inter-population junctions, not inside either population's existing density — a candidate that just echoes the catalogue's own shape isn't a new hypothesis.

The following sites should serve as a starting point for understanding how to generate TIF submissions. These websites are researched, and tested and have generated TIF submissions. But we need to generate high scoring submissions.

Here are the results from submissions into the competition, separated by ....:

[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)

gems-submission-20260925T001403Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)

gems6_hgb88-topk03_33cec71ff0: 0.0286

....

[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)

pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193

pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830

pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)

gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560

....

[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)

gems-submission-20260926T163915Z-237f0063: 0.0343

....

[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)

gems-submission-20260926T175114Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)

lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461

....

[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)

Hedge-v2_submission: 0.1563

....

[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)

2314b599: 0.0107

....

[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html)

gems-structural-area06-v1: 0.0202

....

[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)

r7-nms3-dem10-scarp_0c9199f14e62:0.1294

r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294

....

[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)

gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782

....

[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)

GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020

....

[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)

17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187

....

[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)

H19-C_20260930T212401Z_c11e495e: 0.0297

....

[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)

h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894

h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

....

[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)

h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461

h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921

H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280

h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839

....

[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)

20261001_r13-lattice-s5_v2_nan-outside:0.0904

....

[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)

h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855

h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976

h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360

....

[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)

h19-4-reference-20260930-691e4dfa: 0.1894

....

[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)

h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890

h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan: 0.1859

....

[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)

h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002

h23-b-dti-optimal-emission-10pct-20261002-86176698-nan: 0.0748

....

[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)

h30-arrangement-matched-habitat-20261002-0d4e02e8-nan: 0.1352

....

[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)

h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477

....

[https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/)

dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE26/](https://buffedlizard55-lab.github.io/GEMSDOE26/)

dilcond-oof-v1-20261003-47629f496133-nan: 0.1223

....

[https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/)

topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449

....

[https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/)

h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan: 0.2708

h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan: 0.2649

h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan:

h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan:

....

[https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html)

efd28-repro-20261003-1cc7dc534d51-nan: 0.2600

repo-c0-habitat-emission-20261003-a4d439b07426-nan: 0.0041

sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan:

wormrank-d28-20261003-59dcaf6dd11d-zeros:

wormsurv-filter-20261003-921f10960d6e-zeros:

xfit-c0-habitat-20261003-ca879db0089a-zeros:

xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/)

d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)

h27-4-solo-d28-20261004-8acb75e1-nan:0.2708

....

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

....

[https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/)

h33d-analog-tip-stepover-r30-20261004-cb490425926e: 0.2632

....

[https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html)

h34-scatter-q50-arr-matched-20261004T223317Z: 0.0778

....

[https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html)

h35-06-aaa86efb25-20261004T225420098147Z-candidate: 0.0418

....

[https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)

anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros:

....

[https://buffedlizard55-lab.github.io/GEMSDOE37/](https://buffedlizard55-lab.github.io/GEMSDOE37/)

h6-physics-dotted-80k-20261005T055000Z-0bef9211631c:

....

[https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html)

D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero:

....

[https://buffedlizard55-lab.github.io/GEMSDOE39/](https://buffedlizard55-lab.github.io/GEMSDOE39/)

h40-e-disc-h40e-30k-zeros:

....

40GEMSDOE

:

....

41GEMSDOE

:

....

42GEMSDOE

:

....

43GEMSDOE

:

....

44GEMSDOE

:

....

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition. Must be unique submission unlike any within the GEMSDOE sites above. Verify working line by line no hallucinations.

The following is the leaderboard for the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)

We need to quickly look at the results and results from the GEMSDOE websites above.

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above. We need to come up with distinct and unique strategies to score higher in this competition leaderboard. We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents. We should store all of our information and knowledge that we can gather from official verified sources. This will serve as a starting point for other projects as well. We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for. So it's important to be contrarian but be smart about it. We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents. We need to do deep research and critical thinking and come up with new hypothesis to test.

0.3195 is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website. It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use. It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

Review the repo.

The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.

Our Core Values

Maximize P(Win)

“Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.

Own the Outcome

We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

We need to focus on being able to generate a submission into the competition.

The site should be able to generate a TIF file that is required for submission. It should be as easy as download to click a File to submit into the competition. This needs to be in the executive summary or the very beginning of the site. it should be obvious when you visit the site.

I tried to submit the document that i downloaded from the site but it returned this error on the submission form:

"Predicted values must be in range [0, 1]"

Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Here is the submission page when i click submit file

New submission

File to submitNo file chosen

You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.

Note (optional)

A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Create a executive summary subpage that explains exactly how to make a submission into the contest.

Work on the next steps from the previous sessions first.

The goal of this project is to place top of the leaderboard in this competition. The following is the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)

We need to create a project that can compete and place top of the leaderboard. We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.

This is the guidelines we need to follow.[https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/)

Get familiar with the problem through the overview and problem description,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). You might also want to reference additional resources available on the about page,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/).

Download the data from the data,[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), tab.

Create and train your own model. This reference solution,[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) implements a simple approach.

Use your model to generate predictions that match the submission format.

Tell me what are you limitations and what you need access to during this project. We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.

this pdf outlines how submissions must be entered into the competition.

[https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information. this must be done autonomously and must be constantly reviewed and improved upon. Provide suggestions and improvements and implement them.

❌ No DrivenData auth → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (verified redirect to login)

See below for links from the above site. See attached files for links from the above site.

[https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)

Download competition data from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (requires login) to data/

See links below for competition data:

[https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0)

[https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0)

[https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0)

[https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0)

[https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

Site creation

Create a github page for this repo that has clean ui, user friendly, simple and easy to use. It should be organized and clean.

It should include all relevant information in an easy to read format with official verified links as sources for review. Work line by line verify everything no hallucinations.

**The single remaining blocker to training is data placement**: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).

you need to complete the above task by yourself. Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

Run this task through multiple passes.

Pass 1: Implement the task completely and verify the result.

Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.

Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.

Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request. Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project. It should be worked on in this next session or the next session. Work line by line verify everything no hallucinations.

</details>

## Supplemental raster implementation from PR #8 — H41-A-R

The main project candidate above is the official-source **vector-based H41-A**. This repository also preserves a separate raster-derived implementation contributed by [PR #8](https://github.com/buffedlizard55-lab/GEMSDOE41/pull/8). It was originally named H41-A on its branch; because main independently preregistered a vector implementation with that ID, this distinct version is labeled **H41-A-R** here. The historical branch-local holdout protocol remains `H41-A-PRE-1`; the new label is an integration disambiguation, not a changed test or a rerun.

- **Research-only download:** [`gemsdoe41-h41a-raster-bimodal-transfer-20261005.tif`](docs/downloads/gemsdoe41-h41a-raster-bimodal-transfer-20261005.tif)
- **Unique tracking name:** `GEMSDOE41-H41A-RASTER-BIMODAL-TRANSFER`
- **Short note:** `H41-A-R raster geometry; NW-tip to N/NNE corridor + det_elev orientation; 300 m catalogue exclusion; 30k mass; local proxy only, unscored`
- **Final GeoTIFF SHA-256:** `5e8e528d105cf060490511a033c692f72dd761d09259fa7ae40c53dfc136e05f`
- **Measured holdout:** zero eligible H41-A-R support in all four 3.3 km-collared quadrants. Candidate DTI is **null/unevaluable**, not zero. Terrain-only control DTI was 0.030317, 0.059497, 0.066946, and 0.058345 by fold (0.046888 pooled); those are not candidate scores. `slot_eligible=false`; do not submit this variant.
- **Measured file:** one float32 band, EPSG:32611, 3,730×3,292, 100 m, exact owner-mirror template grid, finite `[0,1]` inside the footprint and NaN outside. Independent format validation passed locally; organizer/portal validation was not performed.

The new TIFF tag/name changes the file hash relative to the pre-merge branch artifact, but not its raster values: the cross-version audit compared all 5,167,373 valid cells exactly (zero changed cells; outside NaNs also identical). See [`docs/evidence/h41a_raster_rebuild_comparison.json`](docs/evidence/h41a_raster_rebuild_comparison.json), the [variant page](docs/h41a-raster-variant.html), the [variant-specific guide](docs/h41a-raster-submission-guide.html), the [preregistration and results](docs/hypotheses-raster-variant.md), and the [three-pass review log](docs/evidence/h41a_raster_review_log.md).

To rebuild this variant after restoring the project’s hash-pinned public owner-mirror inputs (not organizer-authenticated originals):

```bash
bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/build_h41a_raster_submission.py \
  --data-dir data \
  --template data/sample_submission.tif \
  --faults data/existing_faults.tif \
  --features data/training_features.tif \
  --compare-raster data/comparison-h33.tif
.venv/bin/python scripts/validate_h41a_raster_submission.py \
  --template data/sample_submission.tif \
  --compare-raster data/comparison-h33.tif
```

The independent comparisons to both H27-4 and H33-2-B2 are preserved in the checked-in receipt; the former comparison raster is an optional, ignored local reference under `data/prior_reference/`. The rebuild workflow checks both the main source-vector model and this raster-derived variant. Neither candidate is a leaderboard-proven improvement, and no slot should be spent unless the relevant locked spatial holdout gate is passed.
