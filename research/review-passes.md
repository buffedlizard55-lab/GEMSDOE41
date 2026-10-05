# Three-pass implementation and evidence review

**Current final artifact:** `gems41-walker-transfer-v1-20261005-1616b7de764c.tif`. The pass-specific hashes and statistics below are retained as experiment history; the final endpoint correction at the end supersedes the earlier files. All earlier TIFF downloads have been retired from the site.

## Pass 1 — acquisition, research, preregistration, complete first build

- Audited the initial checkout: only `README.md` (11 bytes), no prior pipeline, holdout, or session notes. The claimed existing GPU pipeline was not present.
- Read the official problem, metric, format, data login redirect, leaderboard, and all seven extracted chunks of the official rules PDF. Reviewed the primary Astor/Emerson literature and institutional Faulds paper evidence. Corrected the conflated author/site claim.
- Audited all 39 supplied website source files through GitHub API, preserving blob identities and claim excerpts. Extracted 59 distinct reported submission IDs (including unscored entries) into a CSV ledger. Did not authenticate user-reported artifact scores.
- Preregistered four hypotheses in commit `6827e43`, before implementation. Selected H41-A, fixed parameters; did not optimize on holdout results.
- Direct sandbox downloads failed. Restored large input rasters through immutable owner mirrors and SHA-256 checks. Fetched the official INGENIOUS vector archive on GitHub Actions, archive-tested, and transferred via Git after Azure artifact transport also failed.
- Implemented CPU-only geometry classification, two geometric criteria, probabilistic DTI, blocked withholding, controls, anti-density audits, new GeoTIFF, internal null mask, independent format re-read, educational H33 comparison, and static download site.
- First artifact pixel hash `b40717f0aa92…` was a genuine new build; it passed format/concentration but failed meaningful blocked generalization. It is retired to ignored working data, not offered on the site.

## Pass 2 — substantive review and fixes

1. **Population proximity bug:** distance fields initially used only anchor-eligible traces. Corrected to use all classified mapped traces for the nearest-population criterion; quality filters still govern corridor anchors. This is a requirement-correctness fix, not a tuned hyperparameter change.
2. **Halo geometry:** replaced Manhattan dilation/erosion with Euclidean 300 m distances, matching the metric support.
3. **Whole-trace leakage edge case:** replaced sampled-only holdout intersection with exact geometric intersection against unioned validation pixel polygons buffered by 300 m. Complete source features, including all their parts, are removed. No clipping endpoints are created.
4. **Anti-density audit completeness:** added separate NW-only and N/NNE-only catalogue-density comparisons, not just combined catalogue density.
5. **Kinematic misclassification risk:** preserved source slip-sense attributes and quantified disagreements with strike-only labels. In particular, 686/1,501 NW-assigned parts carry a normal-fault source attribute. Labels are explicitly proxies, not kinematic truth.
6. **Download integrity:** verified internal mask is stored inside the TIFF (no missing `.msk` sidecar), all numeric pixels finite, exact grid and CRS, no nodata sentinel. Underlying outside values are zero; the mask marks them null, consistent with the published format.
7. **Reproducibility:** added checksum verification for the official vector archive and pinned historical benchmark, runnable data-download and prepare-data scripts, a requirements lock snapshot, and Actions re-execution.
8. **Presentation correctness:** populated pages from final measured manifests; labeled gate CLOSED throughout, made the actual TIFF primary, preserved the original brief, and distinguished site-source review from exhaustive scientific verification.

Final pixel hash after these fixes: `0d8679caafa4e52355c908f78ad7ffbc17df5ecafd22fa7f3e1d9dc013619bbe`.
Final TIFF SHA-256: `27601829f332b83cdbd7c3a8a2ea17afa5186e373a2f020152582665320c1d35`.
The mean blocked DTI is `7.098010543695007e-09` (effectively zero). No score improvement is claimed.

## Pass 3 — end-to-end requirements and independent checks

- Local test suite: 18 tests pass at the first final-artifact check, including six randomized exact brute-force DTI comparisons, strike wrapping/reversal, orientation conventions, synthetic bimodal geometry, absent-population handling, whole-source removal, real file hash/value verification, local website links, feed parsing, and gate honesty.
- `git diff --check` and Python compile checks pass.
- Every published local link resolves to an existing deliverable. README, manifest, homepage, and executive guide reference the final hash-named file, not the retired pass-1 output.
- Full four-fold run repeated after fixes. Both population-density enrichment checks pass; highest-confidence junction concentration is 93.27%, with no prediction ≤200 m from catalogue. Concentration is explicitly not independent truth validation.
- Cross-machine CI rebuild and live-site deployment are tracked in GitHub Actions; their final status is recorded in the PR/session completion report rather than assumed here.

## Requirement-to-evidence matrix

| Requirement | Evidence / status |
|---|---|
| New, not copied, downloadable TIF | `docs/downloads/gems41-walker-transfer-v1-20261005-1616b7de764c.tif`; raw geometry/topography reconstruction; no prior predictions in model |
| Two geometric criteria, no new geophysical transform | `scripts/model.py`; only detrended elevation supplies an independent tangent proxy |
| Every known trace classified | Official vector coverage: all 60,988 raster catalogue pixels within 300 m; 5,540 trace parts audited in CSV; geometric vs kinematic ambiguity explicit |
| Junction rather than population-density concentration | `structural-audit.json`, combined and per-population controls |
| [0,1], matching grid, single float32 band, null outside | Independent disk re-read in `format-receipt.json`, internal mask and finite values |
| Unique name and short note | `manifest.json`, executive summary, copy-note control |
| 3–5 hypotheses before implementing | Four candidates, preregistered commit `6827e43` |
| Validate before spending slots | Four full-source spatial folds; FAILED meaningful support; gate CLOSED; no slot used |
| Beat historical best | **NOT established.** No clean historical-best OOF predictions; no authenticated hidden test access |
| Beat 0.2778 / leader | **NOT established.** Actual current leader observed 0.3262; no extrapolated score promise |
| Scientific sources and complete related-site list | `docs/sources.html`, 39-site audit, score ledger, official literature links |
| Autonomous data placement and CPU pipeline | Download/prepare scripts actually run; official vectors acquired without user intervention |
| Original prompt retained / reread | README original brief and AGENTS instructions |
| Executive subpage and simple site | Four linked pages, main download at top, automatic daily source-refresh workflow |
| Current feed | Timestamped verified snapshot plus scheduled Actions; failure states explicit, no claimed permanent live connection |
| PR and merge | To be completed after CI; no direct push to main |

## Remaining blockers and limitations, not hidden successes

- The tested standalone structural prior lacks support on strict held-out blocks. A different validation question may be appropriate for transfer gaps, but it must be preregistered on new data rather than tuned to this failure.
- True fault slip, hydraulic connectivity, heat supply, and active geothermal fluid flow cannot be inferred from strike and coarse topography alone.
- Core mirror integrity is checked, but authenticated organizer-original bytes are unavailable. Source-data rights and participant eligibility must be confirmed by the participant before final prize submission.
- Hidden labels, clean historical-best OOF predictions, and organizer filename-score receipts are unavailable. Do not invent them or ask for credentials in chat.
- Direct sandbox API permission to change Pages settings returned HTTP 403. The repository already has legacy Pages enabled; root index + docs are compatible with that. The deployment workflow attempts authorized Pages configuration with its own scoped token; verify its outcome, do not assume success.

### Final independent verification receipts

- Final code CI rebuild: https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37386650446 — **SUCCESS**. Fresh input restoration, all four folds, exact expected pixel SHA-256 comparison, and tests passed on an independent Ubuntu runner (1m36s).
- Site / tests / public-source refresh: https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37386650577 — **SUCCESS**. PR test workflow also succeeded.
- Actual local HTTP TIFF download: **879,919 bytes**, SHA-256 exactly `27601829f332b83cdbd7c3a8a2ea17afa5186e373a2f020152582665320c1d35`; homepage, all three subpages and feed returned HTTP 200.
- Final diff review caught CSV CRLF line terminators being reported as trailing whitespace; fixed both generators to emit LF and added `.gitattributes`. Full baseline-to-final `git diff --check` now passes.
- Non-failing CI warnings: upstream Actions using Node 20 are forced onto Node 24 by the runner; `ubuntu-latest` has a scheduled image migration. A future maintenance pass should pin the runner image and update supported action versions, then rerun the pixel-hash test.
- Pull request: https://github.com/buffedlizard55-lab/GEMSDOE41/pull/1 — merge is gated on successful checks; no competition upload is part of this PR.

### Post-merge publication review

PR #1 merged at 2026-10-05T23:09:38Z (merge commit `7114e11f73c754affde3d059f10da34b47da5a03`). Legacy GitHub Pages deployment succeeded and the public homepage was fetched and verified, including the correct final TIFF link and closed-gate warning.

The additional scheduled publication workflow exposed a permission bug: changing Pages configuration requires administrative permission that neither available token has. That unnecessary configuration step prevented the subsequent deployment. Follow-up removes the configuration mutation and deploys to the already-enabled Pages site directly with scoped `pages:write`; it also adds a real public-HTTP TIFF SHA-256 check after publication. This affects publishing only, not the scientific model or artifact.

### Further post-merge checks (transparent failure reporting)

- PR #2 merged. Publication run https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37387122753 **succeeded**, including the real public-HTTP TIFF byte-hash check. Scheduled source-refresh deployment now works without changing administrator-only settings.
- A second independent main-branch rebuild completed model generation but failed its combined strict-hash/test step (run 37386872043), despite the earlier exact-hash run passing on identical scientific code. We do not suppress that failure or assume its cause. Added an explicit cross-run raster audit that records exact equality, changed-pixel count, maximum absolute error, and summed absolute error as a CI annotation and JSON artifact.
- The scientific reproducibility criterion is now explicit: exact grid and mask plus at most **8 float32 machine epsilons** absolute pixel error (9.536743e-7). This admits only numerical drift, never a meaningful change to the prediction field. Specific delivered-file SHA-256 verification remains exact. Larger deviations fail CI. The local suite now has 19 passing tests, including a check that a 0.01 change fails this tolerance.

### Final diagnostics after follow-up fixes

- Explicit numerical audit run https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37387286219 **passed with exact bytes and pixels**: zero changed pixels, max error 0, sum error 0. The exported receipt is preserved in `research/independent-reproduction.json`. The earlier intermittent strict-step failure remains disclosed; no unobserved cause is asserted.
- The official leaderboard uses dynamic content: the initial HTTP HTML contains zero table rows. The source feed now renders the public page in Chromium when needed, parses rank-validated score cells/text, and preserves errors rather than presenting a stale number as current.
- Public leaderboard render/parse run https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37387883536 **succeeded**, observing 0.3262 and recording both HTTP and rendered-text hashes. No authentication or hidden data was used.
- Final local suite: **20 tests pass**; full baseline-to-head diff has no whitespace errors. No change to scientific parameters or the delivered TIFF was made in these publication/reproducibility follow-ups.

### Final endpoint-fragment correction (supersedes earlier artifact values)

The final geometry review found that connected-tip rejection still considered only anchor-eligible NW traces, even after population-distance fields had been corrected. A short connected NW fragment can disprove a termination even though it is too short to anchor a corridor. Fixed the endpoint-neighbor tree to include **every NW-assigned mapped part**, and added a regression fixture where a 141 m connecting fragment must suppress a false termination. This changes no preregistered numerical parameter and is not a holdout-driven selection.

The full pipeline was rebuilt after the fix. Current results:
- **268** accepted corridors (29 removed by the stricter endpoint check).
- **150,421** nonzero pixels; prediction mass **6,744.914895**.
- **92.54%** of highest-confidence pixels at defined junctions; **56.89%** of all confidence mass at junctions.
- Junction enrichment vs NW-only density **10.06×**; vs N/NNE-only density **47.29×**.
- Zero prediction mass within 200 m of the catalogue; **blocked DTI exactly 0**. Gate remains CLOSED.
- Final TIFF: `gems41-walker-transfer-v1-20261005-1616b7de764c.tif`.
- TIFF SHA-256: `8cd554d6caa94932879ecf7b73af5f9f9b24553eb5124f74dc1281940826a12c`.
- Pixel SHA-256: `1616b7de764cb328906172ccdfef4c9685971bfd1cde32fb1b29816281d4ee5f`.
- **21 local tests pass**. Earlier downloaded TIFFs are retired; the website and README point only to this corrected candidate. No competition slot has been spent.

Final corrected-model independent run: https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37388376088 — **SUCCESS**. Cross-run float32 variability is now measured, not conjectured: 27,605 pixels differ by at most **4.172325e-7**, summed absolute error **0.000271627**, within the prespecified 8-epsilon numerical tolerance. This is **not byte-identical reproduction**; see `research/final-reproduction.json`. The committed/downloaded artifact's exact SHA-256 remains `8cd554d6…`, independently re-read and checked. Model parameters and submission decisions are unchanged. Corrected local HTTP download: **820,833 bytes**, exact committed SHA-256.

## Current-session follow-up — 2026-10-05 UTC

### Pass 1 — inspect evidence, restore data, and improve the score feed

- Re-read the complete README brief, this review history, preregistered hypotheses, H33 validation JSON, site, official data/metric pages, official GEMS rules, the official public leaderboard, GDR 1391, the Faulds-Henry-Hinz paper, and the distinct Astor Pass and Emerson Pass papers.
- Restored the pinned owner-mirror inputs with `bash scripts/download_competition_data.sh`, then ran `scripts/prepare_data.py`. Training-feature, label, sample-template and official-vector SHA-256 values matched the checked-in receipts. These are integrity-pinned mirrors, not organizer-authenticated originals.
- Added `research/h33-score-analysis.md` to distinguish the user-reported H33 filename/score pair, the sibling's owner-reported proxy analysis, and the official participant leaderboard. The official snapshot fetched on 2026-10-05 showed #1 0.3262, #4 0.3195, and #13 0.2778 for `extradr19`; the leaderboard has no TIFF-name/hash receipt. The H33 owner page itself labels its file unscored. The 0.2778 file attribution remains unverified.
- Extended the scheduled public-source parser to retain rank, displayed participant, and score rows, and revised the site feed to state clearly that participant rows are not artifact receipts. This is publication/audit functionality only; it does not upload a competition file.

### Pass 2 — review edge cases and fix test assumptions

- Added HTML-table and rendered-DOM parser tests, including the dynamic leaderboard layout, participant names separated by line breaks, non-ranked page numbers, sequential-rank requirements, and explicit file-identity warnings.
- First test run exposed an overly literal assertion (`filenames` versus the actual wording `filename-to-score receipts`). Corrected the test to match the intended contract rather than weakening the warning. No production behavior was changed to satisfy a failing test.
- Removed exact current-score assumptions from the ongoing unit test so a future daily leaderboard update cannot fail the build merely because public ranks change. The dated 2026-10-05 facts remain in the human-readable snapshot and analysis memo.
- Confirmed the cached H33 TIFF is used only for an explicit contaminated comparison, not as a model input. Direct array comparison reproduces 186,239 differing pixels and positive-support Jaccard 0.009858; this establishes difference from that examined file only, not global uniqueness.

### Pass 3 — final requirements and artifact verification

- Rebuilt the static pages from the source generator. The home page visibly shows the dated official ranks, links to the official live leaderboard, and explains that scores are not tied to filenames. The executive summary still makes the candidate download, unique name, short note, and closed submission gate prominent.
- Re-ran the complete local suite: **23 passed**. Seven existing Affine pending-deprecation warnings remain; they are non-fatal and do not change pixels.
- Independently re-opened the committed candidate TIFF against the restored sample template. It is single-band float32, shape 3730×3292, EPSG:32611, 100 m transform, all 12,279,160 stored values finite in [0,1] (min 0, max 0.9019997), internal mask exactly matching the 5,167,373-cell footprint, no nodata tag, and SHA-256 `8cd554d6caa94932879ecf7b73af5f9f9b24553eb5124f74dc1281940826a12c`.
- The existing unique H41-A research TIFF was revalidated; this follow-up did not change the model parameters or TIFF bytes. Its holdout mean remains exactly 0, so **do not submit it**. Junction enrichment is a construction diagnostic, not truth validation. No score above 0.2778, 0.3195, or 0.3262 is predicted or claimed.
- Manual-source limitations: the browser research fetch returned the current official leaderboard, but a direct `requests` call from this sandbox ended in a TLS EOF; the daily GitHub Actions refresh is the automated public-network path. No hidden labels, DrivenData submission receipt, or private-score access exists here. The source raster mirrors' origin cannot be authenticated against the login-walled download page from this environment.
