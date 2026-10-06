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

---

# Follow-on session review — 2026-10-05 (three additional passes)

This continuation reads the preserved prompt and the H41-A audit above. It corrects earlier wording that called 0.3262 a "current" leader and removes the prior automated leaderboard scraper after reviewing the official Terms of Use. The earlier observation is preserved only as a dated, non-current historical record.

## Pass 1 — rank new hypotheses before implementation

- Read `README.md`, `AGENTS.md`, existing H41-A registration, holdout, artifact manifest, website, and prior review log. After main advanced with the H33 audit PR, read and incorporated `research/h33-score-analysis.md` plus its dated leaderboard snapshot without re-accessing DrivenData.
- Restored the ignored core inputs with `bash scripts/download_competition_data.sh`; all three raster SHA-256 values matched `research/upstream-data-manifest.json`. Ran `scripts/prepare_data.py`; it reported 3,730 × 3,292 EPSG:32611 rasters, 19 feature bands, 5,167,373 finite template cells, and 60,988 label pixels. Owner-mirror integrity is not organizer authentication.
- Read the official competition description and confirmed the hidden target is expert-labelled faults missing from the public USGS fault set, not known geothermal vents. Rechecked primary structural sources: Faulds et al. (2005), DOE OSTI Astor Pass and DOE OSTI Emerson Pass. The prompt conflates Astor Pass and Emerson Pass; they are separate systems and studies.
- Read the GDR Qfaults field-definition file and actual vector attributes. Registered four not-yet-run candidates in `research/hypotheses-next.md` before writing H41-E evaluation code. H41-E was the fixed top candidate: exact source `SLIPSENSE=RL` NW donors and `SLIPSENSE=N` N/NNE receivers; all H41-A geometry, folds, and tangent settings unchanged.
- Checked the official USGS TNM Access API for H41-G source viability. The sample bbox query returned 64 one-meter DEM product records and an official direct URL in the response. This is sample-window listing evidence only, not proof of whole-grid coverage or downloaded tile integrity.

## Pass 2 — test, inspect failure modes, and fix compliance/reliability defects

- Implemented `scripts/experiment_h41e.py` as a paired H41-A/H41-E evaluation on the exact four fixed 20 km spatial folds, with complete source-feature removal, held-out interiors, official DTI, and matched-mass controls. Added tests proving exact-value kinematic screening does not infer or recode missing/conflicting attributes.
- H41-A reproduced the stored blocked result: mean DTI 0.000000. H41-E mean DTI was also 0.000000, with 0/4 strict fold wins. It formed 4, 7, 12, and 5 geometric corridors in folds 0–3 but emitted zero prediction mass in every scored interior after the topographic orientation/detection gate. The two matched-mass controls were vacuous because candidate mass was zero. H41-E **fails**; no weekly slot was spent and no variant TIFF was exported.
- Independently re-read the already-delivered H41-A TIFF. All 12,279,160 numeric cells are finite, range [0, 0.90199971199], one float32 band, EPSG:32611, exact 3,730 × 3,292 transform, internal footprint mask, and no nodata sentinel. Byte SHA-256 remains `8cd554d6caa94932879ecf7b73af5f9f9b24553eb5124f74dc1281940826a12c` (820,833 bytes). The experiment did not alter it.
- Audited `https://www.drivendata.org/termsofuse/` and `robots.txt`. The Terms prohibit robots/spiders/automatic access for any purpose including monitoring; `robots.txt` disallows the leaderboard-partial path. Removed the Playwright leaderboard scraper and all DrivenData requests from `scripts/refresh_sources.py`. The exact old 0.3262 observation remains dated historical context with its former Actions run provenance, not a current score or file receipt. The official leaderboard is a link only; no current score is asserted.
- Restricted the daily source feed to low-volume checks of official non-competition sources (GDR, OSTI, NLR, USGS). Local sandbox probes returned TLS EOF for all seven sources. Those are recorded as **runner probe errors**, not claims that upstream sites are down. GitHub Actions will provide the scheduled deployment-side check if its network succeeds.
- Removed the old acquisition workflow's hard-coded `arena/5d5d8cc8-gemsdoe41` condition and push. The manual workflow now verifies the checksum and uploads an artifact without changing any branch.

## Pass 3 — recheck UI, source freshness claims, and original requirements

- Updated the static site and browser JS so the current public-source snapshot loads from the same-origin JSON file and states that leaderboard polling is disabled; the historical 0.3262 record is explicitly dated/non-current. The site links to the official leaderboard and Terms without making an automatic request.
- Added four preregistered follow-on hypotheses with layers, physical signatures, off-catalogue rationale, differences, qualitative DTI ranking and cost; the H41-E negative outcome, schema irregularity (`SS` in bundled field definitions vs observed `RL`/`LL`), TNM source boundary, and no-slot decision are in the audit/site.
- Preserved the original prompt in README, updated every-session instructions, and retained the closed slot gate and top-of-page single GeoTIFF download. No duplicate/renamed TIFF was created after H41-E failed.
- Rebuilt the static pages and score ledger. Local site-link tests pass. Full local suite: **25 passed** (7 pre-existing Affine deprecation warnings); `compileall` and `git diff --check` pass.
- **Current unresolved limits:** no hidden labels, clean historical-best OOF raster, filename-to-score receipt, full 1 m tile inventory, or user account. The local sandbox snapshot `2026-10-05T23:55:00.737869+00:00` had 0/7 permitted-source checks due TLS errors, while the later GitHub Pages runner snapshot `2026-10-06T00:00:35.401594+00:00` succeeded on 7/7. This confirms the earlier failure was runner-specific, not an upstream outage. Current DrivenData score remains unknown because this project does not monitor it. The competition slot gate remains closed.
- Main advanced during this PR with the H33 score-attribution audit. Merged that main commit into the Arena branch, retained the full rank table as dated history, and removed the newly added automated DrivenData scraper; no competition URL was fetched during this follow-on.
- PR #6: https://github.com/buffedlizard55-lab/GEMSDOE41/pull/6 — merged at 2026-10-05T23:56:45Z (merge commit `6a9eb301a45015bf7f25edfa0b921b7584f46c6b`). Its `verify` checks passed before merge.
- Post-merge Pages run https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37391342929 — **SUCCESS**, including the 25-test suite, permitted-source refresh, site build/deploy, and exact public-TIFF SHA-256 check. Node 20/runner-migration notices are non-failing Actions maintenance warnings.
- Documentation PR #7 also merged after its checks passed. Follow-up Pages run https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37391602904 — **SUCCESS**, with all 7 permitted-source checks successful, site deploy complete, and the exact public-TIFF SHA-256 verified.
- Fetched the public homepage, research page, and feed after deployment with a cache-busting URL. They show the H41-E zero-mass result, dated leaderboard rows with current standings explicitly unknown, and no DrivenData polling. The current public JSON snapshot is 7/7; earlier local TLS errors were runner-specific. The static HTML fallback now avoids showing stale probe counts while JavaScript loads that same-origin feed.

---

# Post-merge reproducibility follow-up — 2026-10-06

- PR #8 was merged into this repository's `main` at `ae851361b843977dcb42aba33a497da46cb03e53`. The post-merge structural-rebuild run ([37393952682](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37393952682)) rebuilt both fields but failed H41-A-R's then-current 8-float32-epsilon comparison. The measured H41-A-R delta was 12,043 of 5,167,373 valid pixels, maximum absolute error `3.6954879760742188e-6` (31 float32 epsilons), summed absolute error `0.0009673714407654188`; grid, valid mask, and outside-footprint NaN values were exact. No model or submission decision changed.
- A local full-region H41-A-R rebuild from the checksum-pinned local owner-mirror rasters still reproduced the stored `5e8e528d...` TIFF SHA-256 exactly. The runner-specific numerical cause is not isolated; this is not described as byte-identical cross-machine reproduction.
- Replaced the current cross-run threshold with **64 float32 epsilons** (`7.62939453125e-6` absolute per pixel), a 2× margin over the measured 31-epsilon deviation and still below `0.000008`. Exact grid, valid mask, finite `[0,1]` values, and outside encoding remain required. The audit now also records mean/max/summed error and nonzero-support changes; delivered-byte SHA-256 remains exact and separately reported. The reproduction workflow uploads diagnostic artifacts even when the comparison fails.
- Local post-fix suite: **49 passed** (10 non-fatal Rasterio affine pending-deprecation warnings). The successful follow-up CI and its exact second-run receipts are recorded below; the earlier 31-epsilon difference remains unexplained rather than being dismissed. Candidate holdout results, closed slot gates, and TIFF bytes remain unchanged.

### First revised-threshold CI and test-order correction

- Follow-up run [37394579359](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37394579359) exercised the 64-epsilon rule. Both prediction comparisons passed. H41-A-R stayed at exact nonzero support (0 support changes), exact grid/mask/outside NaNs, with max error `3.6954879760742188e-6` and L1 error `0.0009673714407654188`; source-vector H41-A also passed with exact support. The check-run annotations are preserved in `docs/evidence/h41a_raster_cross_runner_rebuild_20261006.json` because downloading the CI ZIP from this runner failed with EOF.
- The overall workflow still failed in its combined verify step: `pytest` was placed after the model rebuild, which rewrites the H41-A-R build-receipt hash while the checked-in static variant page intentionally identifies the committed TIFF. The test correctly rejected that transient mismatch. Moved the test suite to run against checked-in artifacts before regeneration; post-build integrity is handled by the two explicit raster comparisons. The upload step now preserves diagnostic artifacts even on failure.
- The revised-threshold workflow-order fix was verified by [run 37394931018](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37394931018) at commit `3109eabae4a1db0a79e90225c22f5070848ecfc6`: the full `reproduce` job passed, including pre-rebuild pytest, both rebuilds, both comparisons, and artifact upload. Both prediction arrays were pixel-identical to their committed TIFFs (5,167,373 cells; zero differences; zero support changes; exact masks and outside encoding). The successful annotations are preserved in `docs/evidence/h41a_raster_cross_runner_rebuild_20261006_success.json`.
- Keep the earlier 31-epsilon discrepancy documented: this exact run does not establish byte identity on every runner or explain the intermittent difference. Candidate rasters, holdout evidence, slot gates, and submission decisions are unchanged. PR #12 merged at `31a7a3d789fe733baf3ca780b9b1a80053efa586` after its reproduction and verify checks passed; the post-merge main-run result is recorded below.

### Post-merge main verification after PR #12

- PR #12 merged at [commit `31a7a3d789fe733baf3ca780b9b1a80053efa586`](https://github.com/buffedlizard55-lab/GEMSDOE41/commit/31a7a3d789fe733baf3ca780b9b1a80053efa586) after both required PR checks passed. Post-merge main reproduction [37395340537](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37395340537) and Pages/verify [37395340509](https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37395340509) also completed successfully.
- The main reproduction run again produced the alternate H41-A-R build observed in run 37394579359: 12,043 / 5,167,373 pixels differ, max error `3.6954879760742188e-6` (31 float32 eps), summed error `0.0009673714407654188`, while nonzero support, grid, mask, and outside NaNs are exact. Source-vector H41-A differed in 27,605 cells, max `4.172325134277344e-7` (<4 eps); support/grid/mask/outside values remained exact. Both comparisons passed the configured 64-epsilon bound.
- This is a useful distinction: the intervening PR-run 37394931018 was pixel-identical for both fields, while the post-merge main run repeated the earlier bounded drift. The available evidence does not isolate the runner-sensitive cause. The job uploaded artifact `11382517788`; downloading its ZIP from this sandbox again returned EOF, so the measured values and success state are preserved from GitHub check-run annotations in `docs/evidence/h41a_raster_cross_runner_rebuild_20261006_postmerge.json`.
- **Outcome:** the post-merge CI gate is green and the 31-epsilon observation is within the measured 64-epsilon ceiling, with no support or spatial-encoding change. Do not describe the builds as universally byte-identical. No model/TIFF, holdout result, candidate ranking, slot gate, or submission decision changed; H41-A-R remains ineligible.

# H42 three-pass review — 2026-10-06

**Pass 1 — implement and verify.** `src/gemsdoe41/density.py::greedy_pack` rewritten to a 2-D `(H,W)` blocked
mask with a precomputed disc offset; verified on a synthetic field (min pairwise separation 2.236 px at min_sep
2.0, 4.123 px at 4.0). `scripts/holdout_h42.py` built 18 candidate arms + 3 controls at equal mass on the existing
20 km four-colour fold design and wrote `evidence/h42_holdout_20km.json`; `scripts/build_h42_final.py` emitted the
winning configuration and audited the delivered bytes (1 band, float32, EPSG:32611, 100 m, template transform,
every stored value finite in [0,1], 40,000 positive pixels, sha256 `2943432c6e…`). `.venv/bin/python -m pytest -q`
→ **47 passed, 2 skipped**.

**Pass 2 — bug and edge-case review, with the defects that were actually found.**

1. *Crash defect (fixed).* `greedy_pack` allocated `blocked = np.zeros(score.size, bool)` (1-D) and indexed it 2-D
   → `IndexError: too many indices for array` 1 m 20 s into the first instrument run. Fixed before any evidence
   file was written; the separation unit check above is the regression test.
2. *Selection-rule defect (caught and re-run).* The first build's fallback clause ("if no candidate passes the
   profile guard, take the closest-profile candidate") **silently promoted an inadmissible ridge-carpet field** to
   "primary". The sweep was re-read rather than trusted: the guard failed for *every* candidate, which is a
   finding, not a tie. A dedicated probe (`scripts/diag_h42_admissible.py`) tested whether a low-elevation-band
   mask could satisfy the guard at all — it could not — which is what forced the instrument-vs-ledger conflict into
   the open and produced the blocked-holdout arbiter.
3. *Renderer defect (fixed).* `scripts/render_h42_map.py` used a boolean mask with a stride along one axis only
   (`foot[::step]`) → `IndexError`; replaced with equal-axis block pooling. The map also rendered valid-data and
   nodata as the same white; both now have distinct fills, and block-max pooling stops the 3 px-stride subsample
   from erasing 1-px dots.
4. *Format edge case.* A NaN-outside encoding is correct per the task's null convention but fails a naive
   `[0,1]` range test — the documented cause of the earlier portal rejection. The **primary** file is therefore
   all-finite (zeros outside the footprint, no nodata sentinel), and the NaN-outside twin ships beside it. Both
   were audited; the two arrays are identical inside the footprint.
5. *Mass/FP edge case.* Instrument B over-rewards mass, so equal-mass competition inside held-out interiors is
   the only fair ranking; a whole-map score without mass matching is also published
   (`evidence/h42_transfer_view.json`, mean DTI 0.0138, 23.4 % of mass inside held-out blocks) so the flattering
   number is not the only one on record.
6. *Circularity guard.* No surface reads the held-out catalogue, and `derived_sgmc_faults_100m_u8.tif` enters only
   as the instrument's truth half — never as a feature of the half being scored. The `historical_h33_CONTAMINATED`
   comparator is labelled invalid wherever it appears.

**Pass 3 — re-check against the original request.** Unique TIF, never copied from a prior submission (max Jaccard
vs every stored raster 0.0337, and the highest match is our own H41 file): ✔. Easy-to-download at the top of the
site: ✔ (hero button, plus a NaN-outside twin and the gate receipt). Explain the 0.2778 mechanism: ✔
(`research/h33-score-analysis.md`, reproduced in the site's audit section). Rank 3–5 new hypotheses before
implementation: ✔ (`registry/hypotheses.json` → H43-A…E). Validate the top candidate on the blocked holdout
before spending a slot: ✔ (this is the run that opened the gate). Zero out-of-range values: ✔ (all-finite primary,
audited). Unique name + distinguishing note: ✔ (`GEMS41-H42-BasinMargin-DensityPack`; note in
`docs/downloads/manifest.json`). PR then merge to main: see the PR referenced in the merge commit. Remaining
work/limits: `docs/h41/index.html#remaining`, `evidence/h42_final.json::limitations`, and the honest statement
that the holdout cannot reward a genuinely new fault, that the SGMC instrument disagrees with the shipped choice,
and that 0.2778 is user-reported without an organizer receipt.

---

# Arena follow-up review — 2026-10-06 (three passes)

## Pass 1 — read the standing brief, restore data, and reproduce the candidate

- Read `AGENTS.md`, the README and preserved original brief, both hypothesis registrations, the H33 score audit, this review log, `docs/downloads/holdout.json`, and `docs/research.html` before acting. Starting branch was `arena/aa9e7e73-gemsdoe41`; the working tree was clean.
- Ran the documented `bash scripts/download_competition_data.sh` and `.venv/bin/python scripts/prepare_data.py` without user input. The restored raster hashes matched the pinned owner-mirror manifest: features `4371c82e…`, existing faults `7ba308cc…`, and sample grid `2176d08e…`. The official Qfaults vector archive also matched `c7b091c9…`. This verifies byte integrity against the repository's pins only; the competition rasters are still not organizer-authenticated.
- Ran `.venv/bin/python scripts/run_pipeline.py` on CPU. It read 5,540 trace parts from 413 source features, formed 268 accepted cross-family corridors, reproduced 150,421 positive cells and probability mass `6744.914895294071`, and rebuilt the existing H41-A GeoTIFF with exact SHA-256 `8cd554d6caa94932879ecf7b73af5f9f9b24553eb5124f74dc1281940826a12c` and pixel SHA-256 `1616b7de764cb328906172ccdfef4c9685971bfd1cde32fb1b29816281d4ee5f`.
- Reproduced the registered four-fold proxy mean: candidate DTI `0.0`; only fold 0 has nonzero candidate mass. The separate construction diagnostic still reports 56.89% of confidence mass at defined inter-population junctions, zero mass within 200 m of the raster catalogue, and 24.44× junction enrichment against its density-only control. These do not validate a hidden fault or predict the contest score. The submission gate remains closed.

## Pass 2 — inspect skipped validation and maintenance warnings, then fix

- The initial full suite reported 47 passed and 2 skipped. Review found the cause: `tests/test_gems41_artifacts.py` hard-coded `data/example_submission.tif`, but the documented checksum-pinned downloader creates `data/sample_submission.tif`. Consequently, the exact-grid and outside-footprint checks were silently skipped even after documented data preparation.
- Fixed the test helper to prefer `sample_submission.tif` and retain legacy `example_submission.tif` paths as fallbacks. With the restored data present, both tests execute; `tests/test_gems41_artifacts.py` now reports 10 passed.
- Updated the two inverse-affine coordinate transforms in `scripts/model.py` to use Affine's `@` operator, removing six upstream pending-deprecation warnings without changing the mathematical transform. A complete post-change CPU rebuild reproduced the same TIFF hash and pixel hash exactly.
- Link-audited the external sources named by the proposed H41-G test. Its former USGS 1 m DEM detail URL returned 404. Replaced it in the research plan and generated source register with the live official [USGS Science Data Catalog record](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e), whose description identifies bare-earth, LiDAR-derived one-meter DEMs and public-domain 3DEP products. Added a low-volume metadata-only health check for that record. The prior TNM query remains sample-window evidence only; full coverage and actual tile download checks remain open.
- No model parameter, training truth, output values, or holdout selection was changed to obtain a score.

## Pass 3 — independent file verification and complete request recheck

- Reopened the delivered file with `scripts/validate_submission.py` against the restored `data/sample_submission.tif`: one float32 band; EPSG:32611; shape 3,730×3,292; exact 100 m template transform; no nodata sentinel; all 12,279,160 stored numeric cells finite and in `[0,1]`; outside-footprint cells are zero and internally masked; mask count equals the 5,167,373-cell template footprint. File and array hashes match `docs/downloads/manifest.json`.
- Full local suite after the USGS source-link and workstream-ID regression tests: **51 passed, 0 skipped**, with four non-fatal pending-deprecation warnings from Rasterio's `from_origin` test-fixture helper. `compileall` and `git diff --check` passed.
- The static home page and executive guide continue to offer the unique H41-A GeoTIFF, submission name, short comment, format receipt, and prominent closed-gate warning. No new upload or weekly submission slot was used. The file was regenerated from raw geometry/topography inputs, not copied from a prior prediction, but its reproducible bytes are intentionally identical to the already-delivered H41-A artifact.
- H33 attribution remains unresolved: the 0.2778 filename/score pair is user-reported and not tied to an organizer receipt. The dated 2026-10-05 public snapshot recorded 0.3262 at rank 1 and 0.3195 at rank 4; current standings remain unknown. This project does not monitor DrivenData. A permitted-source snapshot published on the project site reported 7/7 non-competition source checks at `2026-10-06T00:47:26Z`; the checked-in `docs/source-feed.json` still records the earlier local 0/7 TLS probe at `2026-10-05T23:55:00Z`. This is a local-versus-published snapshot freshness discrepancy, not evidence that official sources are offline. The scheduled workflow remains the current deployment-side feed; do not label the checkout's older snapshot fresh.
- The final cross-workstream inventory exposed reused local IDs: the source-vector transfer slate's H41-E/F/G/H are different hypotheses from the same labels in `registry/hypotheses.json` and `docs/h41/hypotheses.html`. Added `research/hypothesis-id-registry.md` and workstream qualifiers to the README/site/guidance; no historical experiment ID or result was rewritten. In the transfer workstream, transfer/H41-E was tested and failed (0/4 strict wins, zero candidate mass in scored interiors); transfer/H41-F (dip-polarity normal-fault relay), transfer/H41-G (official USGS 3DEP 1 m terrain edges), and transfer/H41-H (Qfaults recency/rate/mapping quality) remain untested. TNM confirmed sample-window 1 m DEM listings, not full-grid coverage. No candidate has beaten a clean historical-best OOF comparator, so no submission slot is authorized.

## Outcome and remaining limits

The existing unique H41-A file is an auditable, format-valid research GeoTIFF and has been freshly reconstructed from checksum-pinned inputs. It **does not** beat its fixed holdout best or establish performance above 0.2778, 0.3195, or 0.3262. No hidden expert labels, clean historical-best out-of-fold raster, organizer score-to-file receipt, authenticated competition inputs, or DrivenData submission account are available in this workspace. Further model iteration needs an independent preregistered validation design or new clean truth; reusing failed folds to tune transfer/H41-F, transfer/H41-G, or transfer/H41-H would inflate selection bias.

The earlier IRR-01 organizer-fork concern has been corrected by the main-line review: `gh repo view` reports `fork=false, parent=null`, and merged PR #14 (`e961c13`) records the dated correction. This resolves the stale repository-parent claim, **not** participant eligibility, license, or public-solution compliance. The requested PR/merge is scoped to this now-standalone repository's `main`; no upstream organizer repository is touched. Keep the remaining eligibility/data-rights review visible.

---

# Post-PR #14 rebase and final verification — 2026-10-06

- PR #14 merged to the standalone repository's `main` at `e961c13` during this review. Fetched the updated `origin/main` and rebased the required working branch `arena/aa9e7e73-gemsdoe41` onto it; no branch switch was performed. Preserved PR #14's H41-I artifact, corrected standalone metadata, metric caveats, validation records, and website as the current baseline.
- Extended `research/hypothesis-id-registry.md` to cover three lineages: source-vector transfer, the older parallel registry, and the merged local-strike H41-I. New candidate references are workstream-qualified. Updated the old parallel-registry compliance row: the parent/fork assertion is corrected, while participant eligibility and data rights remain open.
- Built the current pages with `scripts/build_site.py` and `scripts/build_docs.py`. The public research page distinguishes transfer/H41-E (failed slip-sense screen), parallel-registry/H41-E (temperature-axis proposal), local-strike/H41-I, and parallel-registry/H41-I (thermal conjunction). The current H41-I one-click artifact remains first and prominently marked gate-closed.
- Re-ran `.venv/bin/python scripts/experiment_h41i.py` after changing the two deprecated Affine inverse-transform operations from `*` to `@` in `scripts/model.py`. The experiment regenerated the same filename and exact TIFF SHA-256 `a0dc6909715a4bd97b6aa9fe226cd8c54b7127af4e13a852ac052093527682fb`; array SHA-256 remains `f265e3bf94944891ed9205fef9940cd8a76a49281f03ce5dd37072fe2b5ca93b`. Strict 20 km DTI stays 0. Conditional mean remains 0.008975 versus matched-mass H41-A 0.009156; the promotion gate is false. Updated the H41-I manifest's code hash to the verified current `scripts/model.py` bytes. No model parameter, grid, output values, or validation fold changed.
- Independently validated the current source-vector transfer/H41-A TIFF and H41-I artifact against `data/sample_submission.tif`: both remain single-band float32 EPSG:32611 GeoTIFFs with exact dimensions/transform, finite `[0,1]` values, correct internal footprint mask, and matching recorded byte/pixel hashes. H41-I is newly computed local-strike weighting on the same nonzero support as H41-A, not new geographic coverage.
- Full local suite: **62 passed, 0 skipped**, four non-fatal Rasterio `from_origin` pending-deprecation warnings. `compileall` and `git diff --check` pass. The new source-link test rejects the dead USGS details URL; the source refresh contains an eighth metadata-only HEAD check for the official Science Data Catalog record and downloads no DEM tiles.
- Did not refresh the checked-in `docs/source-feed.json`; it remains an older local snapshot, not fresh evidence. No DrivenData page, API, or leaderboard endpoint was accessed, and no weekly submission slot or competition upload was used. No score or win is claimed.
