# Start here on every session

1. Read README.md, including the original user brief, then research/hypotheses.md, research/hypotheses-next.md, research/h33-score-analysis.md, research/review-passes.md, docs/downloads/holdout.json and docs/research.html.
2. Never rename or copy a prior submission and call it a novel prediction. Historical rasters may be read only for education and explicitly contaminated comparisons unless clean out-of-fold provenance is established.
3. Keep model inputs separate from validation truth. Withhold complete source geometries and guard against clipping-generated tips, geometric transforms, exclusion masks, and label-derived feature leakage.
4. The H41-A slot gate is CLOSED. No DrivenData submission should be automated or recommended until a candidate beats a valid clean historical-best blocked holdout. A valid GeoTIFF alone is not a pass.
5. Preregister hypotheses and parameters before examining new holdouts; report negative results and all controls. Do not tune a failed holdout into apparent success.
6. Use official sources; distinguish observations, user-reported scores, modeled results, and unknowns. Strike is not slip sense; Astor Pass is not Emerson Pass.
7. Rebuild, re-open and validate the actual delivered file. Check byte and pixel hashes, single-band float32, exact CRS/shape/transform, all finite numerical values in [0,1], and null outside via the internal mask. Test local website links and the actual download.
8. Do not track large input rasters. The 6.1 MB official CC-BY vector archive is a documented exception; keep its attribution.
9. Maintain the executive-summary download, audit receipts, permitted daily public-source feed, original brief, and three-pass review log. Failed fetches must not be presented as fresh facts.
10. Do not automate requests, browser rendering, or monitoring of any `drivendata.org` page. Its published Terms of Use prohibit robots, spiders, or other automatic access for any purpose, including monitoring; manual monitoring also requires prior written consent. This project does not monitor the leaderboard. Historical observations must be dated and labeled non-current; a participant score is not a TIFF receipt.
11. Maximize P(Win): preserve scarce submission slots. Own the Outcome: publish limitations and fix reproducibility defects end to end.

12. Latest session: read `research/hypotheses-20261006.md`, `research/review-20261006.md`, and `docs/evidence/h41i/manifest.json`. H41-I also FAILED its matched-mass gate. Preserve raw and matched-mass comparisons, conditional-sampling limitations and historical negatives. The repo is currently standalone, not a fork; do not restore the corrected IRR-01/IRR-04 claims.
13. H41 letter IDs are workstream-scoped, not globally unique. Read `research/hypothesis-id-registry.md`; qualify IDs in new code, tests, reports, and PR notes by workstream and source path. Preserve legacy keys unless a migration is explicitly audited.
