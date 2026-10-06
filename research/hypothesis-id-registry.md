# H41 hypothesis identifier registry

**Audit date:** 2026-10-06 UTC

**Purpose:** prevent collisions among parallel H41 research records. This file clarifies legacy identifiers; it does not renumber experiments or alter their results.

## Decision rule

`H41-A`, `H41-E`, `H41-F`, `H41-G`, `H41-H`, and `H41-I` are **not globally unique identifiers in this checkout**. Three research lineages reuse some of these short labels for different experiments. When creating or citing new work, qualify the ID by workstream and link the source record. For example, write **transfer/H41-G**, **parallel-registry/H41-G**, or **local-strike/H41-I**, not just “H41-G/H41-I.” Existing scripts and receipts retain their historical local IDs.

## Colliding records

| Local suffix | Source-vector transfer ID and meaning | Parallel-registry ID and meaning | Local-strike transport ID and meaning |
|---|---|---|---|
| A | **transfer/H41-A:** Walker Lane/Basin-and-Range endpoint-to-nearest-fault transfer corridors, with the topographic-orientation check; see `research/hypotheses.md` and the source-vector pipeline. | **parallel-registry/H41-A:** the registry also calls its implemented corridor hypothesis H41-A. The broad geological idea overlaps, but the registry's recorded layers and experiment receipts must be compared before claiming the two implementations are identical. | Not applicable in this registration. |
| E | **transfer/H41-E:** exact `RL`/`N` slip-sense eligibility screen on transfer corridors; tested on the fixed four-fold holdout and failed (zero candidate mass in scored interiors). See `research/hypotheses-next.md` and `research/experiments/h41e-kinematic-holdout.json`. | **parallel-registry/H41-E:** shallow 2 m temperature-probe anomaly-axis/ridge evidence; proposed, not the slip-sense test. The registry's stated GDR source obtainability was not verified for that archive. | Not registered. |
| F | **transfer/H41-F:** oppositely dipping normal-fault termination/relay motif using dip-polarity attributes; proposed, not run. | **parallel-registry/H41-F:** second-derivative gravity curvature/ridge-line evidence; a different input family and physical signature. The registry notes that its required feature raster is not available in the workspace. | Not registered. |
| G | **transfer/H41-G:** independent 1 m USGS 3DEP terrain scarps/curvature in unmapped gaps; proposed, not run. An official sample-window inventory was observed, but full valid-grid coverage and tile acquisition remain unverified. | **parallel-registry/H41-G:** cross-catalogue set difference (QFaults/SGMC against the incumbent catalogue); the registry cites sibling-project evidence that the difference is nearly empty. This is not the 1 m DEM proposal. | Not registered. |
| H | **transfer/H41-H:** Qfaults recency, slip-rate, and mapping-quality attributes used to condition transfer gaps; proposed, not run. | **parallel-registry/H41-H:** 2020 USGS earthquake-sequence anchors/corridor. The parallel registry records this as implemented and measured, including a negative result for corridor-as-truth; it is not the metadata-weighting proposal. | Not registered. |
| I | No transfer/H41-I candidate is registered in the current transfer follow-on slate. | **parallel-registry/H41-I:** structural-plus-thermal conjunction proposal in `registry/hypotheses.json`. | **local-strike/H41-I:** raw mapped geometry plus the existing topographic-tangent detector, transporting local strike into confidence values. Implemented in the latest main-line PR; all nine available comparison arrays differ, but nonzero support is identical to H41-A. The strict 20 km audit scores 0; the conditional short-strand matched-mass holdout is slightly worse than H41-A (mean DTI 0.008975 vs 0.009156). The submission gate remains closed. See `research/hypotheses-20261006.md`, `research/review-20261006.md`, and `docs/evidence/h41i/manifest.json`. |

The parallel registry is mirrored to `docs/h41/hypotheses.json` and rendered at `docs/h41/hypotheses.html`; its broader kinematic/support workstream is summarized at `docs/h41/index.html`. The source-vector transfer slate is `research/hypotheses.md` plus `research/hypotheses-next.md`, and its public research page is generated from `scripts/build_site.py` as `docs/research.html`. The separate local-strike/H41-I implementation and its receipts are tracked in the latest README section and `research/hypotheses-20261006.md`.

## How to use this registry

- Candidate novelty is judged by the actual inputs, physical signature, implementation, and measured status—not by a letter alone.
- Do not describe transfer/H41-G as untried without noting that parallel-registry/H41-G is a distinct, previously analyzed catalogue-difference idea. Likewise, parallel-registry/H41-H is already an implemented seismicity variant, while transfer/H41-H remains a different unrun metadata hypothesis; local-strike/H41-I is yet another lineage and is implemented with a failed promotion gate.
- Do not silently change old JSON keys, script names, submission names, or historical page text. Add the workstream qualifier to new reports and update this audit if either lineage adopts permanent unique IDs.
- The parallel registry's status is its own recorded evidence, not a substitute for local replication. In particular, a sibling project's near-empty catalogue difference does not constitute a new local holdout result.

## H42 collision (updated 2026-10-06 by the bimodal-lattice session)

On 2026-10-06 two parallel sessions independently adopted the label "H42" for different work:

| Workstream ID | Meaning | Records |
|---|---|---|
| **basin-margin/H42** | Slope × detrended-elevation basin-margin relief × 3DEP scarp × RTP magnetics, packed 40,000 px at 400 m, thinned 200 m off catalogue; passed the 20 km four-colour blocked holdout (mean DTI 0.2507 vs 0.1212 random, 0.1771 density) and is the published submission (`manifest.json` top-level `filename`, gate `docs/downloads/h42-gate.json`). | `evidence/h42_final.json`, `evidence/h42_holdout_20km.json`, `research/hypotheses-next.md` (its H42 slate), `scripts/holdout_h42.py`/`build_h42_final.py`. |
| **bimodal-lattice/H42** | The original brief's structural prompt only (junction proximity + orientation match, no new geophysics): five hypotheses registered in `research/hypotheses-h42.md` (H42-A falsified by receipt; H42-B junction dot lattice; H42-C corroboration-intersection diagnostic; H42-D SGMC residual lattice; H42-E deferred; H42-F proposed-unbuilt). Both shipped rasters **failed** the preregistered guarded instrument and enrichment gate and ship as labeled research (`manifest.json -> h42_bimodal_lattice`, `evidence/h42_*.json` for this lineage, `scripts/run_h42.py`, `src/gems41/h42.py`). | Receipts under `evidence/h42_build.json`, `evidence/h42_holdout.json` (this lineage's H42-HO instrument), `evidence/h42_enrichment.json`, `evidence/h42_uniqueness.json`, `evidence/h42_source_audit.json`. |

The two instruments genuinely interact: the basin-margin session's gate cross-checks against an SGMC residual
projection (cpm ≈ 0.088–0.095), measured on the same class of guarded instrument on which this lineage's
line-anchored arms score ≈ 0 by construction. When citing either "H42" number, carry the workstream qualifier.
Historical files keep their local keys (`h42_bimodal_lattice` was chosen to avoid renaming anything already
published); old receipts are unaltered.

## H43 registration (added 2026-10-06 by the catalogue-completion session)

A third parallel session on 2026-10-06 first adopted "H42" as well, then took the unused **H43**
prefix on discovering this registry, and renamed its own files before merging. Nothing published by
 basin-margin/H42 or bimodal-lattice/H42 was renamed, and the shared
`docs/downloads/manifest.json` top-level featured artifact was left untouched: the H43 builder adds
exactly one key, `h43_catalogue_completion`, and a test
(`tests/test_h43_artifact.py::test_h43_does_not_displace_the_slot_eligible_artifact`) fails if it
ever displaces the slot-eligible file or drops the cross-instrument warning.

| Workstream ID | Meaning | Records |
|---|---|---|
| **catalogue-completion/H43** | A supervised catalogue-completion belief field (histogram gradient boosting over all 19 official `training_features.tif` bands — 18 previously unused here — plus local morphology of detrended elevation and of the magnetic/gravity/geodetic gradient bands, plus USGS 3DEP 1 m scarp products; **no** catalogue-geometry feature, **no** class weights, analytic prior-shift calibration), emitted by CELF lazy-greedy maximum-coverage selection over the 300 m kernel. Hypotheses H43-A (coverage emitter), H43-B (learned field), H43-C (geodetic strain partitioning), H43-D (basement-step × conductive-cap blind-fault detector), H43-E (evidence-minus-catalogue residual); C/D/E are absorbed as named layers of the H43-B feature stack, so only A and B were measured as separate arms. Instrument is **H-SIM**: strand-level quadrant blocking, withheld *mapped* strands as truth, retained catalogue masked from every term, guard 2 px. Mean DTI 0.56063 at 20,000 px vs 0.03234 position-blind null and 0.46191 score-ordered packing, 4/4 folds. **Not slot-eligible; never scored.** | `research/hypotheses-h43.md`, `research/score-record-calculus.md`, `evidence/h43_holdout.json`, `evidence/h43_feature_receipt.json`, `evidence/h43_submission_build.json`, `evidence/score_record_calculus.json`, `evidence/label_field_inversion.json` (a published **negative** result), `src/gems41/coverage.py`, `src/gems41/belief.py`, `scripts/build_h43_features.py`, `scripts/experiment_h43.py`, `scripts/build_h43_submission.py`, `scripts/fetch_probe_corpus.py`, `scripts/invert_label_field.py`, `scripts/score_record_calculus.py`, `manifest.json → h43_catalogue_completion` |

### Cross-instrument warning (applies to every "H4x" DTI in this repository)

Three different blocked-holdout instruments are now in use and **their DTI values are not
comparable**:

| instrument | truth | blocking | guard | emission domain | example number |
|---|---|---|---|---|---|
| 20 km four-colour blocked holdout | published catalogue, eroded interiors | 20 km colour blocks | 300 m | fresh inside each held-out block | basin-margin/H42 mean DTI **0.2507** |
| H43-HO / H-SIM | withheld *whole mapped strands* | quadrant blocks, strand-level | 2 px | footprint, off retained catalogue | catalogue-completion/H43 mean DTI **0.56063** |
| H42-HO (bimodal lattice) | guarded catalogue interiors | quadrant blocks | guarded | line-anchored arms score ≈0 by construction | bimodal-lattice/H42 arms **≈0** |

Different truth, different guards, different domains. Quoting 0.56063 as "better than 0.2507" is
exactly the error this registry exists to prevent. Cross-calibrating the three instruments on one
common withheld-strand truth is the first item on the next session's list.

### A third disagreement about the hidden label count

`ρ` (the hidden label count) now has three published values in this repository: 13,000
(`src/gems41/validate.py::K_HIDDEN_PX`), 14,088 (basin-margin/H42's `evidence/h42_final.json`), and
36,467 (the nested-lineage fit in `evidence/score_record_calculus.json`). All three are [MODEL]
constants inferred from owner-reported scores; the first two assume `FP_w ≈ mass`, the third keeps
the double-counting term `q`. None has been overwritten (IRR-14). Any projected score is conditional
on which one is used, and the three imply optimal emitted masses that differ by roughly a factor 3.
