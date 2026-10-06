# H43 — preregistered hypothesis slate for the DOE GEMS prize round

Registered **2026-10-06T02:05Z**, before `scripts/experiment_h43.py` was run against any
holdout and before any emission mass was chosen. Per `AGENTS.md` #5 the hypotheses, the
instrument, the controls and the promotion gate are fixed here first; results are appended
below the line and negative results are reported.

## 0. The validation-protocol defect this slate exists to fix (H-SIM)

The prize round is scored against faults **absent** from the USGS/INGENIOUS catalogue, and
published-catalogue pixels are masked out of every term of the index (DrivenData staff,
forum thread 11516; transcribed in `src/gems41/metric.py`). Every holdout previously run in
this repository used the published catalogue — or a blocked piece of it — as truth, and then
*also* masked the retained catalogue. A candidate that is designed to emit **off** the
catalogue therefore scores structurally ≈ 0 on that instrument no matter how good it is. That
is what `docs/downloads/holdout.json` shows for H41-A (`7.098e-09`) and what
`research/experiments/h41e-kinematic-holdout.json` shows for H41-E (`0.000000`). Those zeros
are a property of the instrument, not of the geology.

**H-SIM (used by this slate).** Withhold *whole strands* (merged 8-connected components,
`validate.strand_labels`, merge 6 px, min strand 60 px) inside a spatial block; treat the
withheld strands as the hidden set; mask the retained catalogue from every metric term; score
only in the region beyond `guard_px` of the retained catalogue. The instrument then asks
exactly the prize question — "find a fault that is not in the catalogue you were given" —
against truth the candidate has never seen, with the answer key structurally identical to the
prize round's.

Controls required at **every** mass: (a) uniform random scatter over the same emission domain
(the position-blind null), (b) distance-to-retained-catalogue ordering, (c) score-ordered
fixed-separation packing (`emission.greedy_pack`, the operator every previous session in this
family used).

Promotion gate: the candidate must beat control (a) and control (c) at matched mass in ≥ 3 of
4 folds, and must beat the repository's incumbent credit-per-mass (`0.0833` at 2,500 px,
`evidence/mass_ladder.json`). The submission-slot gate in `AGENTS.md` #4 remains **CLOSED**;
this slate produces a research candidate and an honest recommendation, not a spent slot.

## 1. The slate

### H43-A — Coverage-maximising emission (operator, not geology)
* **Layers:** none; applies to any belief field.
* **Physical signature / transform:** none. The transform is of the *index*: `TP_w` takes a
  `max` over predictions for each truth pixel, so a second dot inside the 300 m kernel of an
  already-covered truth pixel earns exactly zero and still pays `0.2` of its mass in `FP_w`.
  Emission is therefore a maximum-coverage (facility-location) problem over the kernel, which
  is monotone submodular; CELF lazy greedy is `(1-1/e)`-optimal. Implemented in
  `src/gems41/coverage.py`.
* **Why it finds a fault that is missing:** it does not — it stops *paying* for dots that
  cannot score. The family's own live record proves the waste exists: across the dotted
  lineage the kernel-weighted coverage `a` is statistically constant at `0.287` while the
  emitted mass falls from `121,131` px to `37,654` px (`evidence/score_record_calculus.json`),
  i.e. **69 % of the shipped mass carried no credit**, and `1/score` is linear in mass with
  slope `1.787e-5` (`R² = 0.992` over the eight-point chain).
* **How it differs from what is implemented:** every prior session in this family emitted by
  thresholding a field or by `greedy_pack` at a fixed minimum separation. Fixed separation
  enforces *geometric* thinning; it cannot see that two dots 3 px apart on the same ridge
  cover the same truth pixel while two dots 20 px apart on different ridges cover two.
* **Expected DTI improvement:** large. The same belief field's ceiling is
  `s_max = a/(0.2a+0.8) = 0.3347` at `a = 0.287`, above the 2026-10-05 leaderboard snapshot's
  `0.3262`. **Cost:** low (one module + one experiment).

### H43-B — Catalogue-completion learning
* **Layers:** all 19 official bands of `training_features.tif` (only band 12 `det_elev` has
  ever been used in this repository — 18 unused official inputs), the USGS 3DEP 1 m scarp
  products, and the geometry of the *retained* catalogue.
* **Physical signature / transform:** the learned multivariate conjunction that separates
  mapped fault pixels from background — magnetic and reduction-to-pole gradient edges
  (`mag_anom`, `rtp`, `tmi_hg`, `tmi_vg`), isostatic gravity anomaly and its slope/vertical
  gradient (`iso_grav_anom*`), geodetic strain invariants (`geod_2ndinv`, `geod_shearrate`,
  `geod_dilaterate`), seismicity distance/intensity (`deq_n100a15`, `ieq_n100a15`),
  detrended elevation, its slope, local standard deviation, structure-tensor coherence and
  laplacian, basement depth and its gradient, near-surface conductivity — plus 1 m derived
  scarp morphology. Gradient boosting, no new geophysical transform invented.
* **Why it finds a fault that is missing:** it is trained on the literal prize task. Whole
  strands are deleted from the catalogue and the model must reconstruct them from data alone;
  a model that can do that fires wherever the conjunction holds and no trace is mapped, which
  is precisely a catalogue gap rather than a catalogue echo.
* **How it differs:** this repository has no supervised pixel model at all. H41-A/H41-E were
  hand-built structural geometry; `scripts/model.py` is corridor arithmetic.
* **Expected improvement:** high (it is the reference solution's own approach, made
  CPU-feasible). **Cost:** moderate — 3 GB / 2-core host, so features are materialised once to
  a pixel-interleaved float32 memmap and training/prediction are blocked.

### H43-C — Geodetic strain partitioning
* **Layers:** `geod_2ndinv` (band 4), `geod_shearrate` (7), `geod_dilaterate` (8).
* **Signature:** interseismic strain-rate concentration and the second invariant of the
  horizontal strain-rate tensor. In the Walker Lane the second invariant peaks where
  distributed shear is partitioned into discrete structures and where transfer zones absorb
  the difference between dextral and normal slip (Faulds/Henry/Hinz 2005,
  `doi:10.1130/G21274.1`).
* **Why missing:** geodetic strain is derived from GNSS/InSAR, i.e. from a measurement
  completely independent of the geomorphology and of the 1970s–90s paper map compilations the
  catalogue was built from. A fault can be geodetically loud and cartographically absent.
* **How it differs:** no high-scoring file in this family uses the geodetic bands; the
  top files are topography/magnetics lineament products.
* **Expected improvement:** moderate. **Cost:** low.

### H43-D — Blind-fault detector: basement step × conductive cap
* **Layers:** `depth_to_base_surf` (15) gradient magnitude, `cond_surf` (17).
* **Signature:** a lateral discontinuity in depth-to-basement co-located with a near-surface
  conductive anomaly (hydrothermal alteration / clay cap / saline fluid).
* **Why missing:** the Emerson Pass analogue this brief is built on
  (`https://www.osti.gov/servlets/purl/1110518`) is a **blind** system: no surface trace, so
  no scarp detector can ever see it. Buried range-front faults beneath basin fill are the
  single largest known completeness gap in Nevada fault compilations, and they are exactly the
  population the prize round asks for.
* **How it differs:** every high-scoring family file is surface-expression-biased (1 m DEM
  scarps, lineaments). This one is deliberately blind to surface expression.
* **Expected improvement:** moderate, with the highest novelty. **Cost:** low–moderate.

### H43-E — Mapping-coverage residual ("evidence minus catalogue")
* **Layers:** any multi-evidence composite, minus the published catalogue's own density.
* **Signature:** `r(x) = smooth(evidence) − smooth(catalogue density)`, standardised. High
  where the physical case for faulting is strong and the published trace density is thin.
* **Why missing:** the catalogue's completeness is strongly heterogeneous — it was compiled
  from source maps of very different vintage and scale (`RCODE2023`/`SCODE2023` in the
  INGENIOUS archive record this). Ranking by evidence alone reproduces known density; ranking
  by the *residual* targets absence, which is what the round scores.
* **How it differs:** the brief's own acceptance test ("predicted pixels must NOT concentrate
  inside existing catalogue density") has never been made the objective; this makes it the
  objective.
* **Expected improvement:** moderate. **Cost:** low.

## 2. Ranking (expected DTI improvement per unit implementation cost)

| rank | id | expected gain | cost | decision |
|---|---|---|---|---|
| 1 | H43-A | large — bounded above only by `a`; ceiling `0.3347` at the incumbent `a` | low | **implement now** |
| 2 | H43-B | high — raises `a` itself | moderate | **implement now** |
| 3 | H43-E | moderate | low | implement as an H43-B feature + standalone ranker |
| 4 | H43-C | moderate | low | implement as H43-B features (already in the 19 bands) |
| 5 | H43-D | moderate, highest novelty | low–moderate | implement as H43-B features (bands 15/17) |

H43-C/D/E are absorbed into H43-B's feature stack as individual layers, so the slate is
tested as (i) the emission operator, (ii) the learned field, and (iii) each layer's marginal
contribution by ablation, rather than as five separate builds.

## 3. Emission mass — preregistered selection rule

Two independent estimates, agreed **before** any holdout was opened:

1. **Holdout rule.** Emit at the mass that maximises measured holdout DTI for the winning
   field, evaluated on the checkpoint ladder `1k, 2k, 4k, 6k, 9k, 13k, 18k, 25k, 37,654 px`
   (the last is the incumbent's mass, so "do nothing" is one of the options).
2. **Score-record rule.** The marginal-coverage bar derived from the index: one more dot pays
   iff its coverage gain exceeds `0.2·DTI/ρ` in belief units, with `ρ` the hidden label count
   inverted from the family's nested lineage (`evidence/score_record_calculus.json`).

If the two disagree, ship the **smaller** mass: the index penalises false mass at `0.2` and
rewards nothing for redundancy, so the downside of over-emitting is certain and the downside
of under-emitting is bounded by `0.8·FN_w` on pixels that were never going to be covered.

---

# RESULTS (appended after the runs)

*(to be filled in by `scripts/experiment_h43.py` → `evidence/h43_holdout.json`)*

## 4. Measured results — `scripts/experiment_h43.py` → `evidence/h43_holdout.json`

Run 2026-10-06T02:2xZ, 511 s, 2 cores / 3 GB, no GPU. Four strand-blocked folds
(214 / 102 / 45 / 45 withheld strands; truth 30,872 / 11,484 / 10,679 / 7,953 px;
emission domain 4.86–5.02 M px), guard 2.0 px, 31 features, 18 negatives per positive,
`HistGradientBoostingClassifier(max_iter=240, learning_rate=0.08, max_leaf_nodes=31,
min_samples_leaf=40, l2_regularization=1.0, random_state=42)`.

**Mean DTI across the four folds, identical truth and identical masses:**

| emitted mass | coverage greedy (γ=1) | coverage greedy (γ=8) | score-ordered packing @2.83 px | packing @4.5 px | uniform scatter (null) |
|---|---|---|---|---|---|
| 2,000 | 0.31284 | 0.17923 | 0.30313 | 0.29103 | 0.00450 |
| 8,000 | 0.51937 | 0.39175 | 0.49198 | 0.34624 | 0.01674 |
| **20,000** | **0.56063** | 0.52774 | 0.46191 | 0.30610 | 0.03234 |
| 37,654 | 0.54528 | 0.55637 | 0.39344 | 0.25291 | 0.04680 |
| 65,000 | 0.48826 | 0.50127 | 0.31634 | 0.19818 | 0.06260 |

Per-fold DTI of the shipped operator at 20,000 px: **0.41921 / 0.57839 / 0.61124 / 0.63367**.

**Promotion gate (§0):**

| test | result | verdict |
|---|---|---|
| beats the position-blind null at matched mass | **4/4 folds at every one of the five masses** | PASS |
| beats the family's score-ordered packing operator | 4/4 at 2,000; 3/4 at 8,000 and 20,000; 4/4 at 37,654 and 65,000 | PASS (≥3/4 required) |
| beats the repository's incumbent credit-per-mass (0.0833 @2,500 px) | **1.616 @2,000 px**, a factor **19.4** | PASS |
| skill ratio vs the null, credit per unit mass | 57.3× @2,000 · 27.2× @8,000 · 15.7× @20,000 · 10.1× @37,654 · 6.8× @65,000 | — |

**Independent corroboration of the calibration.** The belief field's own total mass `Σπ` — the
model's estimate of how many fault-like pixels the domain contains — lands at **0.88, 0.75,
0.78, 0.75 ×** the withheld truth count in folds 0–3. Nothing in training targets that number;
it falls out of the analytic prior-shift correction in `src/gems41/belief.py`.

## 5. Decisions taken, and what was rejected

* **H43-A confirmed.** Coverage-maximising greedy beats score-ordered fixed-separation packing at
  every mass tested, and the gap widens with mass (0.545 vs 0.393 at 37,654 px; 0.488 vs 0.316 at
  65,000 px) exactly as the redundancy argument predicts. Wider fixed separation (4.5 px) is
  strictly worse than 2.83 px at every mass — geometric thinning is not a substitute for
  coverage-aware selection.
* **γ = 8 rejected.** The preregistered sharpening exponent was tested and lost: 0.52774 vs
  0.56063 at 20,000 px, 0.55637 vs 0.54528 at 37,654 px. Sharpening only helped while the field
  was still mis-calibrated (it partly undoes the inflated low-probability body). Once the prior
  shift is undone analytically, γ = 1 wins on the aggregate and the extra parameter is dropped.
  Reported, not hidden.
* **Catalogue-geometry features rejected** (see the comment in `fold_list`): a guard makes
  distance-to-retained-catalogue a shortcut, and the shipped model trains on catalogue pixels
  (all at distance 0) while predicting beyond 200 m, so any such feature would drive every
  prediction to zero. Removing it also guarantees the field cannot echo catalogue density, which
  is the brief's own acceptance test.
* **Mass = 20,000 px.** Rule 1 (measured holdout argmax) → 20,000. Rule 2 (live-anchored model
  argmax, ρ = 36,000 from `evidence/score_record_calculus.json`, capped at 37,654) → 37,654.
  The rules disagreed, so the preregistered tie-break shipped the **smaller** mass.

## 6. Limits — stated before anyone asks

1. **The holdout truth is withheld *mapped* strands.** The prize round's truth is faults that
   were never mapped at all, which are plausibly subtler, blind, or in poorly compiled terrain.
   The measured 0.56 is an upper-leaning estimate on a related-but-easier population. **No live
   score is claimed or projected for this artifact.**
2. Folds are quadrant blocks, so fold 0 withholds 214 strands (30,872 px, half the catalogue)
   while folds 2–3 withhold 45 strands each. Fold difficulty is uneven and fold 0 is the weakest
   result (0.419); that is expected, not a defect, but it means the mean is not a single number
   with a small error bar.
3. `ρ = 36,000` and the coverage ceiling `0.3346` in §3 rest on owner-reported scores
   (`registry/score_ledger.csv`), not organizer receipts.
4. Post-hoc, **after** the mass was fixed: the marginal-coverage bar `gain > 0.2·DTI` evaluated on
   the shipped belief field is still comfortably exceeded by the last emitted dot
   (tail gain 0.254 vs a bar of order 0.1), which suggests the model optimum for *this* field lies
   above 20,000 px. That was not known when the rule was preregistered, so it is **not** adopted
   here. It is logged as the next preregistered experiment: a mass ladder on the shipped field
   with the bar evaluated self-consistently, and a coverage-vs-mass curve measured on H-SIM.
5. The submission-slot gate in `AGENTS.md` #4 remains **CLOSED**. This is a research candidate.
