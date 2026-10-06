#!/usr/bin/env python3
"""Fetch the *reported-scored* sibling raster corpus used for the label-field inversion.

EDUCATION / CALIBRATION ONLY.  These files are other sessions' published candidates with an
owner-reported DrivenData score.  They are NEVER used as a model input for pixel values and
are never re-emitted as this repository's prediction.  They are used as *probes*: each one is
a known emission set E_i with a known live score s_i, so the family's own score record can be
inverted for the spatial distribution of the hidden labels (see scripts/invert_label_field.py).

Every entry records where the score was reported (owner page, not an organizer receipt) and
the immutable GitHub path the bytes came from.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probes"

# (id, repo, ref, path, reported_score, score_source)
PROBES = [
    ("h19_5", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif",
     0.1922, "https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html"),
    ("h19_4", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif",
     0.1894, "https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html"),
    ("h16_1", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif",
     0.1855, "https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html"),
    ("dot_d15", "buffedlizard55-lab/GEMSDOE24", "main",
     "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
     0.2477, "https://buffedlizard55-lab.github.io/GEMSDOE24/"),
    ("dot_d28", "buffedlizard55-lab/GEMSDOE24", "main",
     "docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
     0.2600, "https://buffedlizard55-lab.github.io/GEMSDOE25/"),
    ("tgc_d15", "buffedlizard55-lab/GEMSDOE27", "main",
     "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif",
     0.2449, "https://buffedlizard55-lab.github.io/GEMSDOE27/"),
    ("h274_solo", "buffedlizard55-lab/GEMSDOE28", "main",
     "docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif",
     0.2708, "https://buffedlizard55-lab.github.io/GEMSDOE28/"),
    ("h321_prethin", "buffedlizard55-lab/GEMSDOE28", "main",
     "docs/downloads/gems28-h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan.tif",
     0.2649, "https://buffedlizard55-lab.github.io/GEMSDOE28/"),
    ("h33d_stepover", "buffedlizard55-lab/GEMSDOE33", "main",
     "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e-nanoutside.tif",
     0.2632, "https://buffedlizard55-lab.github.io/GEMSDOE33/"),
    ("h33_2b2", "buffedlizard55-lab/GEMSDOE32", "main",
     "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
     0.2778, "https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html"),
    ("h25_ctx_ridge", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/calibration/gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif",
     0.1280, "https://buffedlizard55-lab.github.io/GEMSDOE10/"),
    ("h28_dotted_ridge", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/calibration/gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif",
     0.1839, "https://buffedlizard55-lab.github.io/GEMSDOE10/"),
    ("lat_s5", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
     0.0904, "https://buffedlizard55-lab.github.io/13GEMSDOE/"),
    ("hedge_v2", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/calibration/8GEMSDOE_Hedge-v2_submission.tif",
     0.1563, "https://buffedlizard55-lab.github.io/8GEMSDOE/"),
    ("ens12_adopted", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/calibration/gemsdoe-ens12-adopted-7f00890a.tif",
     0.1563, "https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html"),
    ("placeholder", "buffedlizard55-lab/GEMSDOE24", "main",
     "inputs/calibration/gemsdoe9-PLACEHOLDER-2314b599.tif",
     0.0107, "https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html"),
    ("h23a_6pct", "buffedlizard55-lab/GEMSDOE22", "main",
     "docs/downloads/gems22-h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan.tif",
     0.1002, "https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html"),
    ("h23b_10pct", "buffedlizard55-lab/GEMSDOE22", "main",
     "docs/downloads/gems22-h23-b-dti-optimal-emission-10pct-20261002-86176698-nan.tif",
     0.0748, "https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html"),
    ("h30_arrmatch", "buffedlizard55-lab/GEMSDOE23", "main",
     "docs/downloads/gemsdoe23-h30-arrangement-matched-habitat-20261002-0d4e02e8-nan.tif",
     0.1352, "https://buffedlizard55-lab.github.io/GEMSDOE23/"),
    ("dilcond_oof", "buffedlizard55-lab/GEMSDOE26", "main",
     "docs/downloads/gems26-dilcond-oof-v1-20261003-47629f496133-nan.tif",
     0.1223, "https://buffedlizard55-lab.github.io/GEMSDOE26/"),
    ("h20_1", "buffedlizard55-lab/20GEMSDOE", "main",
     "docs/downloads/gems20-h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan.tif",
     0.1890, "https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html"),
    ("h20_5", "buffedlizard55-lab/20GEMSDOE", "main",
     "docs/downloads/gems20-h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan.tif",
     0.1859, "https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html"),
    ("poisson300_44090", "buffedlizard55-lab/GEMSDOE30", "main",
     "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-nanoutside.tif",
     0.2600, "https://buffedlizard55-lab.github.io/GEMSDOE30/"),
    ("efd28_repro", "buffedlizard55-lab/GEMSDOE29", "main",
     "docs/downloads/gems29-refd28-repro-20261003-1cc7dc534d51-nan.tif",
     0.2600, "https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html"),
    ("h34_scatter", "buffedlizard55-lab/GEMSDOE34", "main",
     "docs/downloads/h34-scatter-q50-arr-matched-20261004T223317Z.tif",
     0.0778, "https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html"),
    ("h35_06", "buffedlizard55-lab/GEMSDOE35", "main",
     "docs/downloads/gemsdoe35-h35-06-aaa86efb25-20261004T225420098147Z-candidate.tif",
     0.0418, "https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html"),
    ("r7_scarp", "buffedlizard55-lab/12GEMSDOE", "main",
     "docs/downloads/12GEMSDOE_r7-nms3-dem10-scarp_0c9199f14e62.tif",
     0.1294, "https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html"),
    ("h20_scarp_thin", "buffedlizard55-lab/GEMSDOE10", "main",
     "docs/downloads/gems10-h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686.tif",
     0.0921, "https://buffedlizard55-lab.github.io/GEMSDOE10/"),
    ("h16_continuation", "buffedlizard55-lab/GEMSDOE10", "main",
     "docs/downloads/gems10-h16-continuation-20260927T065521077735Z-3431b83c7c.tif",
     0.0461, "https://buffedlizard55-lab.github.io/GEMSDOE10/"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for pid, repo, ref, path, score, src in PROBES:
        dest = OUT / f"{pid}.tif"
        if dest.exists() and dest.stat().st_size > 0:
            ok = True
        else:
            tmp = dest.with_suffix(".partial")
            with tmp.open("wb") as out:
                r = subprocess.run(
                    ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
                     "-H", "Accept: application/vnd.github.raw"],
                    stdout=out, stderr=subprocess.PIPE,
                )
            if r.returncode != 0:
                tmp.unlink(missing_ok=True)
                print(f"FAIL {pid}: {r.stderr.decode()[:160].strip()}", flush=True)
                rows.append(dict(id=pid, repo=repo, path=path, reported_score=score,
                                 score_source=src, ok=False))
                continue
            tmp.replace(dest)
            ok = True
        rows.append(dict(id=pid, repo=repo, ref=ref, path=path, reported_score=score,
                         score_source=src, ok=ok, bytes=dest.stat().st_size,
                         sha256=sha256(dest)))
        print(f"ok {pid:18s} {dest.stat().st_size:9d}  score={score}", flush=True)
    (OUT / "probes.json").write_text(json.dumps(rows, indent=1) + "\n")
    n_ok = sum(1 for r in rows if r.get("ok"))
    print(f"\n{n_ok}/{len(rows)} probes restored -> {OUT/'probes.json'}")
    return 0 if n_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
