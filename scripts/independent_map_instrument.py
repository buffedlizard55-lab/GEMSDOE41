#!/usr/bin/env python3
"""Independent-map instrument: which evidence finds faults the catalogue does NOT contain?

The catalogue-strand holdout used elsewhere in this repository measures credit against
faults that ARE in the published catalogue.  Measured here, that instrument turns out to
be ANTI-informative for this competition: the archived file with the highest reported
score (H33-2-B2, 0.2778) has almost the lowest catalogue-strand credit of the whole
ledger, because it deliberately targets off-catalogue structural positions.

This script builds and applies the missing instrument:

  TRUTH  = fault pixels carried by the USGS State Geologic Map Compilation (SGMC) that lie
           300 m or more from every pixel of the competition catalogue.  These are faults a
           second, independent public compilation contains and the USGS/INGENIOUS catalogue
           omits - the same *kind* of object the competition's hidden labels are, at the cost
           of being far denser and not being geothermal-filtered.

  SCORE  = the official distance-weighted Tversky index of a frozen prediction against that
           truth, with catalogue pixels masked exactly as the official rule masks them.

Because SGMC is used as TRUTH here, no candidate evaluated with this instrument may use SGMC
as an input; that separation is asserted in the output.

Output: evidence/independent_map_instrument.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems41.metric import dti  # noqa: E402

K_CALIBRATED = 14_088

LEDGER = [
    ("H33-2-B2", "data/comparison-h33.tif", 0.2778),
    ("H27-4-solo-d2.8", "data/scored/r02708-h27-4-solo-d2-8.tif", 0.2708),
    ("H32-1-prethin", "data/scored/r02649-h32-1-prethin-tip-euler.tif", 0.2649),
    ("H33d-stepover", "data/scored/r02632-h33d-analog-tip-stepover.tif", 0.2632),
    ("dotted-d2.8-44090", "data/scored/r02600-dotted-d2-8-44090.tif", 0.2600),
    ("dotted-d1.5", "data/scored/r02477-dotted-d1-5.tif", 0.2477),
    ("topo-gap-d1.5", "data/scored/r02449-topo-gap-closure-d1-5.tif", 0.2449),
    ("h19-5-powerlaw", "data/scored/r01922-h19-5-powerlaw.tif", 0.1922),
    ("h19-4-multiline", "data/scored/r01894-h19-4-multiline.tif", 0.1894),
    ("h16-1-topo-geophys", "data/scored/r01855-h16-1-topo-geophys.tif", 0.1855),
    ("h28-dotted-ridge", "data/scored/r01839-h28-dotted-ridge.tif", 0.1839),
    ("hedge-v2", "data/scored/r01563-hedge-v2.tif", 0.1563),
    ("ens12", "data/scored/r01563-ens12-adopted.tif", 0.1563),
    ("h25-ctx-ridge", "data/scored/r01280-h25-ctx-ridge.tif", 0.1280),
    ("r13-lattice", "data/scored/r00904-r13-lattice-s5.tif", 0.0904),
    ("placeholder-2314b599", "data/scored/r00107-placeholder-2314b599.tif", 0.0107),
]


def read(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float32)
    a[~np.isfinite(a)] = 0.0
    return np.clip(a, 0.0, 1.0)


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    den = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / den) if den else 0.0


def main() -> None:
    cat = (read(ROOT / "data/existing_faults.tif") > 0.5)
    foot = np.isfinite(read(ROOT / "data/sample_submission.tif"))
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as s:
        sgmc = s.read(1) > 0
    d_cat = distance_transform_edt(~cat)
    truth = sgmc & (d_cat > 3.0) & foot
    print("SGMC px", int(sgmc.sum()), "off-catalogue truth px", int(truth.sum()))

    rows = []
    for name, rel, score in LEDGER:
        pred = read(ROOT / rel)
        r = dti(pred, truth, footprint=foot, known=cat)
        n = int((pred > 0).sum())
        T_hidden = score * (0.8 * K_CALIBRATED + 0.2 * n)
        rows.append(dict(name=name, reported_score=score, emitted_px=n,
                         T_hidden_implied=round(T_hidden, 1),
                         sgmc_tp=round(r["tp"], 2), sgmc_fp=round(r["fp"], 1),
                         sgmc_dti=round(r["dti"], 6),
                         sgmc_credit_per_mass=round(r["credit_per_mass"], 6)))
        del pred
    sc = np.array([row["reported_score"] for row in rows])
    pr = np.array([row["sgmc_credit_per_mass"] for row in rows])
    pd_ = np.array([row["sgmc_dti"] for row in rows])
    out = dict(
        truth=dict(source="derived_sgmc_faults_100m_u8.tif (USGS SGMC-derived, owner CI mirror)",
                   description="SGMC fault pixels >=300 m from every catalogue pixel, inside the scored footprint",
                   truth_px=int(truth.sum()),
                   provenance_caveat="owner-CI derivative of the public USGS SGMC; geometry is not organiser-authenticated",
                   derivation_url="https://www.usgs.gov/programs/national-cooperative-geologic-mapping-program/science/usgs-state-geologic-map"),
        instrument="official DTI transcribed in src/gems41/metric.py; catalogue pixels masked",
        rows=rows,
        rank_correlation=dict(
            spearman_proxy_dti_vs_reported_score=round(spearman(pd_, sc), 3),
            spearman_proxy_credit_per_mass_vs_reported_score=round(spearman(pr, sc), 3),
            note="A positive rank correlation is evidence that this instrument tracks the hidden-set ordering; "
                 "it does not prove the hidden truth is SGMC-like.",
        ),
        best_row_by_dti=max(rows, key=lambda r: r["sgmc_dti"]),
        caveats=[
            "SGMC is denser (62k off-catalogue px) and mostly pre-Quaternary; the competition truth is smaller and geothermal-filtered.",
            "No candidate evaluated here may use SGMC as an input feature (asserted by the builder).",
            "Reported scores are owner/user reports, not organizer receipts.",
        ],
    )
    (ROOT / "evidence/independent_map_instrument.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{'file':22s} {'score':>6s} {'N':>7s} {'sgmc_T':>8s} {'sgmc_dti':>9s} {'cpm':>8s}")
    for r in rows:
        print(f"{r['name']:22s} {r['reported_score']:6.4f} {r['emitted_px']:7d} {r['sgmc_tp']:8.0f} "
              f"{r['sgmc_dti']:9.5f} {r['sgmc_credit_per_mass']:8.5f}")
    print(json.dumps(out["rank_correlation"], indent=1))


if __name__ == "__main__":
    main()
