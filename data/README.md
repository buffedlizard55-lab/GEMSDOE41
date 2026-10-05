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
- `training_features.tif`: pinned owner mirror of 19-band competition features. Only band 12 (detrended elevation) is used. Other descriptive band names are not independently interpreted or used.
- `existing_faults.tif`: pinned owner mirror of the raster catalogue.
- `sample_submission.tif`: pinned owner mirror used only for grid and valid-data footprint. Contains label-like nonzero values; these are never copied to predictions.
- `comparison-h33.tif`: historical scored candidate for education/descriptive evaluation only. NOT used in prediction construction.
- `external/gdr_qfaults_traces.csv`: historical attributes downloaded during acquisition investigation; NOT used by the model (official geometry supersedes it).

`research/input-receipt.json` records source repository, immutable commit, paths, sizes, and SHA-256. This establishes mirror integrity, not independent organizer authentication. The authenticated DrivenData download page remains inaccessible. The owner's public sharing and the competition external-data rule do not eliminate the participant's obligation to confirm final redistribution rights.

No hidden labels, personal credentials, or synthetic geological measurements are stored.
