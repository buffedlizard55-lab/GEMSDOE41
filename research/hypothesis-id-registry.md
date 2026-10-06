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
