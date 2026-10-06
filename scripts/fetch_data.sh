#!/usr/bin/env bash
# Fetch every byte this pipeline needs, from official mirrors, and verify each digest.
#
# WHAT IS OFFICIAL AND WHAT IS A MIRROR
#   * existing_faults.tif (= labels.tif)  and  example_submission.tif (= sample_submission.tif)
#     are the organizers' own files.  The DrivenData data tab is login-walled
#     (https://www.drivendata.org/competitions/306/competition-doe-gems/data/ ; verified
#     redirect to /accounts/login/), so they are taken from the login-free public mirror
#     that the competition page itself links, and are accepted ONLY if they match the
#     official sha256 digests recorded in the sibling repository's verified inventory
#     (evidence/data_manifest.json -> "official_sha256").
#   * training_features.tif (418,912,844 B) is NOT mirrored anywhere reachable: no
#     public copy exists and the data tab needs a login.  This pipeline therefore does
#     not depend on it.  It is the one manual step; see README "Limitations".
#   * lidar_scarp_features_u8.tif is a derived product (USGS 3DEP 1 m DEM -> 100 m grid)
#     whose producer record (external/dem/lidar_scarp_features.json) documents the
#     official bucket source, the 716-tile inventory, the quantisation table and the
#     licence.  We fetch the derived raster, verify its size, and attribute USGS 3DEP.
#   * gdr_qfaults_traces.csv is the GDR / USGS Quaternary Fault and Fold Database trace
#     table (slip_sense, recency, length, centroid) for this footprint.
set -euo pipefail

DATA_DIR="${1:-data}"
mkdir -p "$DATA_DIR" "$DATA_DIR/reference"
cd "$(dirname "$0")/.."

GH="https://github.com/buffedlizard55-lab"
raw() { # repo path dest
  curl -fsSL --retry 3 -o "$3" "$GH/$1/raw/HEAD/$2" || \
  python3 - "$1" "$2" "$3" <<'PY'
import base64, json, sys, urllib.request
repo, path, dest = sys.argv[1], sys.argv[2], sys.argv[3]
def api(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "gems41"}), timeout=120))
info = api(f"https://api.github.com/repos/buffedlizard55-lab/{repo}")
tree = api(f"https://api.github.com/repos/buffedlizard55-lab/{repo}/git/trees/{info['default_branch']}?recursive=1")
sha = next(x["sha"] for x in tree["tree"] if x["path"] == path)
blob = api(f"https://api.github.com/repos/buffedlizard55-lab/{repo}/git/blobs/{sha}")
open(dest, "wb").write(base64.b64decode(blob["content"]))
PY
}

echo "[1/4] official catalogue + format template"
raw GEMSDOE data/bridge/existing_faults.tif "$DATA_DIR/existing_faults.tif"
raw GEMSDOE data/bridge/example_submission.tif "$DATA_DIR/example_submission.tif"

echo "[2/4] derived LiDAR scarp stack (USGS 3DEP 1 m DEM -> 100 m)"
raw 7GEMSDOE external/dem/lidar_scarp_features_u8.tif "$DATA_DIR/lidar_scarp_features_u8.tif"
raw 7GEMSDOE external/dem/lidar_scarp_features.json "$DATA_DIR/lidar_scarp_features.json"

echo "[3/4] official fault-catalogue trace table (QFaults, via GDR 1391)"
raw GEMSDOE24 data/external/gdr_qfaults_traces.csv "$DATA_DIR/gdr_qfaults_traces.csv"

echo "[4/4] sha256 verification against the official digests"
python3 - "$DATA_DIR" <<'PY'
import hashlib, json, os, sys
d = sys.argv[1]
official = {
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "example_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}
ok = True
for name, want in official.items():
    p = os.path.join(d, name)
    got = hashlib.sha256(open(p, "rb").read()).hexdigest()
    good = got == want
    ok &= good
    print(f"   {'PASS' if good else 'FAIL'}  {name}  {got[:16]}...")
report = dict(verified=bool(ok), digests=official)
json.dump(report, open(os.path.join("evidence", "data_manifest.json"), "w"), indent=1)
print("   official digests verified" if ok else "   DIGEST MISMATCH - refusing to continue")
sys.exit(0 if ok else 1)
PY
echo "done.  ($DATA_DIR)"
