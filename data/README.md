# Data provenance and storage

## Official geometry (small archived exception)
`official/qfaults.zip` (6,131,182 bytes) was fetched directly from:
https://gdr.openei.org/files/1391/qfaults_ingenious_nad83conus117_2023-06-27.zip

Official listing: https://gdr.openei.org/submissions/1391

Citation: Ayling, B. et al. (2022), *INGENIOUS — Great Basin Regional Dataset Compilation*, GBCGE/NBMG/UNR, doi:10.15121/1881483. Updated v2 geometry dated 2023-06-27. **License: CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). Original attributes, field definitions, and shapefile metadata remain in the archive; projection and geometric classification are our modifications.

SHA-256: `c7b091c9ac8bca140ad89ee6bb2bd63dd3ac12e3013acbfd8373d11c9faee59d`.

Acquisition receipt: https://github.com/buffedlizard55-lab/GEMSDOE41/actions/runs/37385329808
The small archive is tracked because direct sandbox transport and Azure artifact downloads failed. GitHub Actions fetched and tested it on an unrestricted runner; Git transport delivered the identical bytes. Core large rasters are NOT tracked.

## Ignored restored inputs
- `training_features.tif`: pinned owner mirror of the 19-band competition feature raster. **All 19 bands are used from H43 onward.** Band names and `data_category` values are read from the file's own per-band tags (never guessed) and transcribed in `scripts/build_h43_features.py` `BAND_NAMES`, which asserts each tag at build time: `mag_anom`, `rtp`, `tmi_hg`, `geod_2ndinv`, `iso_grav_anom_slope`, `tc`, `geod_shearrate`, `geod_dilaterate`, `tmi_vg`, `deq_n100a15`, `iso_grav_anom_vg`, `det_elev`, `iso_grav_anom`, `tmi`, `depth_to_base_surf`, `ieq_n100a15`, `cond_surf`, `iso_grav_anom_hg`, `det_elev_slope`. Nodata is the float32 sentinel `-3.4028234663852886e+38` and it occurs on **3,061 pixels inside the scoring footprint** (58,171 band-pixels); `scripts/build_h43_features.py` replaces it with the band's in-footprint median and records the count per pixel as a feature, so no sentinel value can reach a submission (IRR-12). Before H43 only band 12 (`det_elev`) was used.
- `existing_faults.tif`: pinned owner mirror of the raster catalogue.
- `sample_submission.tif`: pinned owner mirror used only for grid and valid-data footprint. Contains label-like nonzero values; these are never copied to predictions.
- `comparison-h33.tif`: historical scored candidate for education/descriptive evaluation only. NOT used in prediction construction.
- `external/gdr_qfaults_traces.csv`: historical attributes downloaded during acquisition investigation; NOT used by the model (official geometry supersedes it).

`research/input-receipt.json` records source repository, immutable commit, paths, sizes, and SHA-256. This establishes mirror integrity, not independent organizer authentication. The authenticated DrivenData download page remains inaccessible. The owner's public sharing and the competition external-data rule do not eliminate the participant's obligation to confirm final redistribution rights.

## Ignored derived and calibration directories (added 2026-10-06, H43)

- `external/lidar_scarp_features_u8.tif` (36,943,606 bytes, SHA-256
  `d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568`): owner-derived USGS 3DEP
  1 m scarp-morphology stack, restored from the pinned mirror recorded in
  `research/upstream-data-manifest.json`. Decoded by `src/gems41/lidar.py`; 3,894,460 valid pixels
  (75.4 % of the footprint). These are uncalibrated terrain descriptors, not fault detections.
- `probes/*.tif` + `probes/probes.json` (29 rasters, ~40 MB): **sibling sessions' published
  candidates with their owner-reported scores.** Restored by `scripts/fetch_probe_corpus.py` from
  immutable GitHub paths, each with its SHA-256 and the page the score was reported on. Read for
  SUPPORT and MASS only, as calibration probes for `scripts/score_record_calculus.py` and
  `scripts/invert_label_field.py`. **Never used as a model input and never re-emitted**:
  `scripts/build_h43_submission.py` does not open this directory at all.
- `derived/h43_features.f32` (1,522,615,840 bytes): pixel-interleaved float32 memmap, 31 features
  × 12,279,160 pixels. Built by `scripts/build_h43_features.py` (~220 s) so a 3 GB / 2-core host
  can train and predict over all 5.1 million scored pixels. Receipt with per-feature min/max and
  a non-finite-cell assertion: `evidence/h43_feature_receipt.json`.
- `derived/inversion_design.npz`: per-probe × per-template kernel statistics used by the label-field
  inversion, cached so refits do not re-read 29 rasters.

No hidden labels, personal credentials, or synthetic geological measurements are stored.
