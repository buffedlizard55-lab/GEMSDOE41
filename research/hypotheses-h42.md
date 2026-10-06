# H42 slate — preregistered 2026-10-06, before any H42 model or artifact was built

**Rule honored here:** this file is written, with all fixed parameters and decision gates,
*before* `src/gems41/h42.py` and `scripts/run_h42.py` exist. Only acquisition-level source
audits (bytes, counts, coverage) were run first — they decide whether a source exists, not
whether the model works. Every measured number quoted below is reproducible by
`python3 scripts/run_h42.py --audit-only` or is carried in a checked-in evidence file.

## Part 1 — Why the reported 0.2778 is the family's high-water mark (evidence-based answer)

The user-reported best GEMSDOE-site artifact, `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`
(0.2778), is a **2-pixel/200 m catalogue-flank prune of a 40,199-px base reported at 0.2708**
(`registry/score_ledger.csv`; GEMSDOE32 owner page). No organizer receipt links that filename
to a leaderboard row (`research/h33-score-analysis.md`); the dated 2026-10-05 public-page
observation showed rank 1 at 0.3262. The mechanism is arithmetic, and the repository's own
transcription of the official metric proves it (`src/gems41/metric.py`, identities tested in
`tests/test_metric.py` against a brute-force implementation):

```
DTI = TP / (TP + 0.2·FP + 0.8·FN)
identity (2):  1/DTI = 0.2 + 0.2·FP/TP + 0.8·|G|/TP
marginal rule: one added unit of mass pays iff its best kernel weight k > 0.2·DTI
```

Three consequences explain the whole family's live ladder
(121,131 px → 0.1922; 60,069 → 0.2477; 44,090 → 0.2600; 37,654 → 0.2778; every gain came
from REMOVING mass, never from adding a better field):

1. **Mass is a cost; redundancy is a cost.** A truth pixel is credited once (max over the
   300 m triangular kernel). Dots closer than ~300 m along a strike do not raise TP; they raise
   FP. Minimum-separation packing at 2.83 px is therefore first-class design, measured in
   `evidence/thin_sweep.json`.
2. **Prune the dead flank.** Pixels near (but not on) the published catalogue earn no
   incremental credit for hidden faults and pay the 0.2 term — deleting them cannot lower TP.
   That is exactly what H33-2-B2 did (+0.0070 reported).
3. **Live credit-per-mass is much higher than any catalogue-truth holdout can show**
   (the family's own support measured c ≈ 0.067 on strand holdout yet lives at c ≈ 0.13 implied
   by its reported score). The hidden set is denser along structure than catalogue strands can
   express; the blocked holdout is a *ranking* instrument, never a score predictor
   (`src/gems41/validate.py` states this ceiling). [MODEL], not a measurement of the hidden set.

So beating 0.2778 requires (a) the proven emission geometry — binary dots, 2.83 px minimum
separation, ≥200 m catalogue prune, mass in the 37–44k live-validated band — and (b) a
**skeleton with real off-catalogue geological content**, because pure re-ranking of the
incumbent skeleton was measured (this repo, `evidence/mass_ladder.json`) to be nearly inert at
that mass. The five candidates below attack (b).

## Part 2 — Candidate slate (all untried in this repository before today)

| ID | Layers | Physical signature | Why it can catch a fault missing from the public catalogue rather than echoing it | How it differs from anything implemented here or on the 39 audited sibling sites | Rank / cost |
|---|---|---|---|---|---|
| **H42-A** Official-vector residual recall | INGENIOUS v2 vector archive (`data/official/qfaults.zip`, CC BY 4.0) vs `existing_faults.tif` | Any vector geometry burned to grid but >300 m from the raster catalogue | The hidden set is defined as expert faults absent from the public database; if the database were a superset of the raster, its additions would be that class | First test anywhere in the family of "vector-minus-raster" residual | **0 — FALSIFIED today by direct measurement:** burned official v2 vectors: 60,982 px, of which 60,981 are within 300 m of the raster catalogue (residual >200 m = 2 px, >1 km = 0 px). The provided public catalogue **is** the official v2 compilation rasterized; there are no official-vector additions to recall. Receipt: `evidence/h42_source_audit.json`. This closes the idea for every future session. |
| **H42-B** Bimodal junction dot lattice (brief-compliant primary) | Published catalogue geometry only: strike classification into NW-dextral-proxy / NNE-to-N-normal-proxy populations, tip-transfer + tip-extension + relay-ramp corridors, LiDAR-stack local lineament strike + scarp evidence | Proximity to inter-population strain-transfer corridors, graded by orientation match to the geometrically nearer population (the brief's two criteria); **new part:** emitted as metric-optimal binary dot packing instead of the failed soft continuous field | H41-A's soft field failed its holdout by *zero-mass gating and mass dilution* (150,421 px of continuous 0–0.902 values, every marginal pixel paying the 0.2 term). Packing the same hypothesis at 2.83 px separation and a live-validated mass tests the hypothesis under the metric it will be scored by | No sibling emitted the junction field as a minimum-separation binary lattice at the measured optimal band; this repo's `h41-core`/thrift artifacts are different fields (support-based re-rank, or hard-gated 20k soft field at 3.5 px) | **2 — low cost; all inputs local** |
| **H42-C** Corroboration-intersection variant of H42-B | H42-B ∪ 2020 rupture-zone envelope (`evidence/seismicity_corridor.npz`) ∪ 2 m temperature-probe anomaly pixels (GEMSDOE30 mirror of GDR 1391, CC BY 4.0) | Max, not sum, of independent evidence channels with the structural prior | An unmapped active conduit shows up as terrain (scarp stack), seismicity (2020 sequence: 16 M≥4 epicentres, all >7 px from every mapped fault), or shallow heat; requiring intersection rejects each channel's own artifacts | The family's thermal runs (h19-4/-5, 0.189–0.192) used thermal as the *base field*, not as a gate on a structural lattice; the repo's `h41-rupture2020-union` is a different composition (soft union at 20k) | **3 — low-medium cost; diagnostic only this session** |
| **H42-D** State-map residual fault lattice (new data, new support) | USGS **SGMC** state-geological-map fault traces on the competition grid (sibling CI-derived mirror, sha256 `26d142c4…` verified byte-for-byte today; official source `https://mrdata.usgs.gov/geology/state/shp/NV.zip` and `CA.zip`, US public domain) + published-catalogue geometry for the bimodal classification | Every state-map residual trace classified by axial strike into the same NW / NNE populations; score = orientation match to the nearer population × scarp evidence; emitted off-catalogue as the 2.83 px binary lattice, mass capped at the live-validated 37,654 px | **Measured, preregistration-time:** 82,151 SGMC px in footprint; **65,673 px >200 m and 61,664 px >300 m off the public catalogue** (matches the sibling receipt independently at 300 m — byte-identity cross-check); 769 traces ≥20 px; LiDAR scarp evidence on the residual is **1.64× the off-catalogue background** (0.1246 vs 0.0761 mean) — independent terrain corroboration of the kind the H41 corridors lacked (they were *depleted* on the same class of test, `evidence/site_control.json`). State-map faults are exactly expert-mapped geometry absent from the provided database | No scored sibling artifact used SGMC off-catalogue dots as an orientation-ranked bimodal lattice; GEMSDOE29 lists `sgmc-off-catalogue-44k` with **no recorded score** (irregularity IRR-09 — unresolved whether ever uploaded); this repo has never used SGMC. Support is disjoint from the catalogue by construction (≥200 m prune) and from every prior sibling skeleton by source (state geologic-map compilation, not ridge/scarp detection) | **1 — medium cost; data restored + verified this session** |
| **H42-E** 1 m bare-earth DEM LoG scarp edges (prior H41-G) | USGS 3DEP 1 m tiles (TNM inventory sample verified obtainable per `research/hypotheses-next.md`; 706/716-tile list carried by sibling CI) | Second-derivative (LoG) edge lines at 2 scales with anthropogenic-edge suppression | Sub-100 m young scarps are invisible at the training grid | Unchanged from H41-G; deferred because per-tile acquisition exceeds this session and full-footprint coverage is unverified | **4 — high cost; deferred, no slot** |

**Ranking by expected DTI improvement × evidence, then cost:** H42-D > H42-B > H42-C > H42-A
(falsified) > H42-E. H42-D ranks first because it is the only candidate with *new fault geometry*
(independent expert mapping the public catalogue lacks) **and** measured terrain corroboration,
while H42-B is the brief-mandated structural-position design shipped as the compliant primary.

## Part 3 — Fixed validation protocol (no parameter may change after results are seen)

1. **New instrument H42-HO ("expert-fault holdout").** The catalogue-strand holdout cannot
   reward off-catalogue prediction by construction (`src/gems41/validate.py` docstring). H42-HO
   therefore withholds **whole SGMC residual traces** instead: four deterministic spatial blocks
   (`gems41.validate.quadrant_blocks`, unchanged formula); every SGMC residual trace touching a
   block ∪ 3 px halo and every catalogue trace touching it are removed; truth = held-out SGMC
   residual pixels eroded 3 px from all retained geometry. This is the closest obtainable analogue
   to the hidden set: fault geometry visible to state geologists and absent from the public
   database. Arms scored with the official DTI (`gems41.metric`, guard 3 px), identical domain,
   identical 2.83 px packing, budgets {2,500 / 5,000 / 10,000 / 20,000} px per fold (a fixed
   ladder; winner chosen by mean credit-per-mass across the ladder — never on a single fold):
   (a) H42-D field (orientation×evidence on retained residual geometry); (b) H42-B junction
   field; (c) distance-to-retained-catalogue density prior; (d) scarp-evidence-only; (e) random
   matched-mass; (f) residual-proximity-only. Report every fold, including zeros.
2. **Label-free enrichment gate.** Markers: 2 m probe pixels off-catalogue (2,467) and the 2020
   rupture envelope off-catalogue (9,310 px). Statistic: fraction of marker pixels within 3 px of
   the candidate support vs 500 random matched-mass supports (deterministic seed 42, 20 km block
   bootstrap). Enrichment ≥1.2 and empirical p<0.05 on at least one marker passes; report both.
   (H41-A's analogue was 0.34×, p=1.0 — the bar is deliberately one the corridor failed.)
3. **Brief audits on the shipped file bytes:** 0 emitted px within 200 m of the catalogue;
   junction concentration vs per-population density controls (`gems41.field.junction_concentration`
   + mass-fraction enrichment); single-band float32, EPSG:32611, 3730×3292, 100 m transform,
   all stored numeric values finite in [0,1], zeros outside the footprint carried by the internal
   mask — the portal-accepted convention of the family's live-scored `-zeros` files and of this
   repo's published `format-receipt.json`.
4. **Novelty ledger:** support Jaccard and differing-pixel counts against all eight shipped
   `docs/downloads/*.tif` artifacts, the H41-A main file, and the educational H33 comparison
   raster (`data/comparison-h33.tif`, sha256 `c55bafc4…` — comparison only, never an input).
   Equality with any of them fails the build.
5. **Slot gate.** A file ships only as a candidate; this repository does not upload. Promotion
   to "spend a weekly slot" requires H42-HO arm (a) or (b) to beat controls (c)–(e) in ≥3 of 4
   folds at the ladder mean *and* pass (2). The pre-existing requirement of a clean
   historical-best OOF comparator cannot be met locally and stays recorded as an open limitation,
   not silently dropped.

## Part 4 — Sources for manual review (all free, official, no login)

- Official problem, metric, submission format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (participant-visited; this repo never automates DrivenData — Terms prohibit it: https://www.drivendata.org/termsofuse/ and https://www.drivendata.org/robots.txt)
- Official rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- INGENIOUS GDR 1391 (CC BY 4.0): https://gdr.openei.org/submissions/1391 ; archive in this repo at `data/official/qfaults.zip`, sha256 `c7b091c9…` verified this session
- USGS State Geologic Map Compilation (public domain): https://mrdata.usgs.gov/geology/state/ — the mirror bytes used here were restored from https://github.com/buffedlizard55-lab/GEMSDOE30/blob/HEAD/data/external/derived_sgmc_faults_100m_u8.tif and checked against the sibling CI receipt (sha256 match; stored copy `evidence/gems30_external_receipt.json`). Provenance class: owner/sibling-CI-derived, integrity-pinned, not organizer-authenticated.
- USGS QFaults slip-style codes: https://pubs.usgs.gov/of/2013/1165/pdf/ofr2013-1165_appendixB.pdf
- Faulds, Henry & Hinz (2005): https://nbmg.unr.edu/staff/Faulds/faulds_et_al_geology_paper.pdf
- Astor Pass (Siler et al.): https://www.osti.gov/servlets/purl/1110516 ; Emerson Pass (Anderson & Faulds): https://www.osti.gov/servlets/purl/1110518 (the brief's conflation of the two remains a logged correction)
- USGS ComCat 2020 query (events checked into `registry/seismicity_2020.csv`): https://earthquake.usgs.gov/fdsnws/event/1/
- Prior score attribution audit: https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html (owner-reported; `research/h33-score-analysis.md`)

## Part 5 — Protocol amendment A1 (2026-10-06, before results of the corrected run were seen)

The first H42-HO run (same day) returned zero for `h42d_state_prior` and `control_residual` in
every fold. Diagnosis from its own receipt (`evidence/h42_holdout.json`, first run): those two
arms were built as 1 px-wide fields ON the retained residual lines, while the fold `allowed`
domain excludes every pixel within 3 px of retained geometry — the arms were zero on the entire
scored domain *by construction*. The instrument was vacuous for them, not negative. Two fixes,
committed before re-running, with the first run's evidence preserved in git history:

1. All line-anchored arms now share the corridor's 2 px proximity kernel (`src/gems41/h42.py`,
   `h42_arms`); on the full map the maximum still sits on the mapped line itself, so the shipped
   dot placement is unchanged in kind.
2. The pass rule is evaluated on **arms (a) and (b) versus the controls**, exactly as Part 3
   already required; the script previously mislabeled "winner of the whole table beats controls"
   as the gate, which would have turned a control topping the table into a false pass. That was
   a bug in the decision logic, not a change of the decision rule.

A vacuous-first-run report and a corrected single re-run is the whole amendment. No parameter,
guard, budget, kernel width for the other arms, fold formula, or marker definition is changed.
If the corrected arms still lose to `control_evidence` (the LiDAR scarp-evidence field), the
honest conclusion is preregistered now: **neither H42 arm earns promotion**, the artifacts ship
labeled research-only, and the best promotion-supported emission geometry of this repository
remains the incumbent re-ranking line, not a new standalone prior. The terrain-evidence control
winning H42-HO would additionally tell us the state-map residual traces are *mostly terrain
features the scarp stack already finds* — in that case the residual lattice is redundant with
the family's existing LiDAR-ridge skeletons rather than additive.

## Part 6 — Irregularities raised by this session (mirrored into registry/irregularities.json)

- **IRR-09** `sgmc-off-catalogue-44k` appears on GEMSDOE29 with a **blank score** — unresolved
  whether it was submitted. No claim is made that the SGMC idea is leaderboard-untried; what is
  claimed is that *this* construction (bimodal orientation-ranked lattice with corroboration gate
  and H42-HO validation) does not exist on any audited site.
- **IRR-10** The pinned mirrors show `existing_faults.tif` **byte-identical** to `labels.tif`
  (same SHA-256 `7ba308cc…`) and `sample_submission.tif` containing 60,988 ones on the label
  pixels. Either the training labels equal the public catalogue (plausible for round 1) or the
  mirror set carries an alias. Recorded; format/grid usage is unaffected; flagged for
  organizer-level confirmation.
- **IRR-11** `mrdata.usgs.gov`, `gdr.openei.org` and all USGS endpoints return `000` from this
  sandbox's network (measured 2026-10-06), so external fetches here go through the
  GitHub-Actions/`gh api` mirror path only. That is an environment limitation, not an upstream
  outage.

**Erratum (administrative, 2026-10-06, after results):** the registry already contained an
`IRR-09` (projection-constant) before this session, so the three items above were mirrored into
`registry/irregularities.json` as **IRR-10** (label-provenance trap), **IRR-11** (sandbox network /
mirror-only acquisition), **IRR-12** (sibling `sgmc-off-catalogue-44k` unscored) and **IRR-13**
(missing `anchor_02600_zeros.tif`; `build_final.py` not rerunnable). Scientific content unchanged.

## Part 7 — Outcome log (written after all gates closed; no gate or parameter changed after this point)

Measured on the frozen protocol (full run `20261006T075812Z`, 602 s; rebuilt twice via `--skip-holdout`, final shipped build
`20261006T015420Z` — **identical pixel hashes `ee5667cd…`/`25fc92e9…` across all three builds**). Truth: withheld SGMC residual
traces, 4 folds, 3 px isolation guard; ladder budgets 2.5k/5k/10k/20k px; mean credit-per-mass:

| field | mean cpm | verdict |
|---|---|---|
| h42d_state_prior | 0.0000 | un-evaluable under guard (Part 5 note) — scored as fail |
| h42b_junction_prior | 0.0002 | arms beat controls in 0/4 folds -> **holdout FAIL** |
| control_density | 0.0110 | — |
| control_evidence | **0.0791** | tops the instrument (3.1x random) |
| control_random | 0.0259 | — |
| control_residual | 0.0000 | confirms the guard's structural zero for line-anchored fields |

Enrichment gate (500 stratified circle-nulls, x1.2 + p<0.05): **all four fail** — h42b thermal
0.591x p=1.0, h42b rupture 0.895x p=0.894; h42d thermal 0.294x p=1.0, h42d rupture 0.453x p=1.0.
Uniqueness ledger: max Jaccard 0.0323 (h42b, vs `gems41-walker-transfer-v1-20`) and 0.0118 (h42d,
vs `h41-core`); byte-equality with any shipped raster: refused by construction and verified absent.

Shipped artifacts (format checks **all PASS** on re-opened bytes; 0 px within 200 m of catalogue;
min distance 2.236 px; values exactly {0.0, 1.0}):
`docs/downloads/gemsdoe41-h42b-junction-lattice-37k-20261006T075812Z.tif` (33,144 px, pool-limited,
shortfall 4,510 vs 37,654 cap) and `gemsdoe41-h42d-statemap-lattice-37k-20261006T075812Z.tif`
(22,061 px; 18,618 on residual, 84.3%).

**Decision (verbatim, from `manifest.json -> h42.decisions.slot_recommendation`):** no promotion:
the preregistered holdout rule failed on 0/4 folds and the label-free enrichment gate failed; the
LiDAR scarp-evidence control tops the instrument (ladder-mean cpm 0.0791) — artifacts ship as
labeled research only. No submission slot was spent. The next registered idea is H42-F (open-ground
evidence x orientation), which **must not** be built against this instrument (Part 5 lesson).
