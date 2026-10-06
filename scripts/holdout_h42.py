#!/usr/bin/env python3
"""20 km four-colour blocked holdout for the H42 emission family (catalogue-free surfaces).

This reuses the *exact* fold design of `scripts/run_pipeline.py::evaluate`:

  fold_id   = (row//200 + 2*(col//200)) % 4        (20 km blocks, deterministic)
  held      = (fold_id == f) & footprint
  forbidden = within 3 px (300 m) of the held region
  training  = labels & ~forbidden
  evaluation= held & (erode(held) > 3 px)          (interior only)

Differences, all deliberate and declared:

  * The candidate fields here are catalogue-free by construction (terrain slope,
    LiDAR scarp evidence, TMI).  Nothing in `score` or `allowed` reads `labels`, so a
    held-out strand cannot influence where the mass goes: the only catalogue use is the
    thinning rule (no emission within 2 px of a *training* trace), which is the local
    analogue of the H33-2-B2 post-hoc thinning applied fold-consistently.
  * Mass is packed inside each fold's evaluation domain, so every arm competes at equal
    mass on identical ground and the FP term is measured where the truth is.
  * Controls: uniform-random at the same mass, plus training-catalogue density (the
    control run_pipeline uses), plus the archived H33 raster marked CONTAMINATED.

The instrument's own ceiling is stated everywhere: its truth is *published* catalogue
faults, so it cannot reward a genuinely new fault.  It ranks emission geometries.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems41 import lidar as L  # noqa: E402
from gems41.metric import dti  # noqa: E402
from gemsdoe41 import density as D  # noqa: E402

F32 = np.float32
SEPS = (3.0, 4.0)
BUDGETS = (10_000, 20_000, 40_000)
SURFACES = ("SA_slope_scarp", "SB_slope_scarp_tmi", "SH_basin_strong")


def rb(path: Path, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(band).astype(F32)
    a[~np.isfinite(a)] = 0.0
    a[a < -1e37] = 0.0
    return a


def main() -> None:
    labels = rb(ROOT / "data/existing_faults.tif") > 0.5
    with rasterio.open(ROOT / "data/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    h, w = labels.shape
    rr, cc = np.mgrid[0:h, 0:w]
    fold_id = ((rr // 200) + 2 * (cc // 200)) % 4

    slope = D.norm01(D.smooth(rb(ROOT / "data/training_features.tif", 19), 1.0), foot)
    det = D.norm01(D.smooth(rb(ROOT / "data/training_features.tif", 12), 1.0), foot)
    tmi = D.norm01(D.smooth(rb(ROOT / "data/training_features.tif", 3), 1.0), foot)
    scarp = D.norm01(D.smooth(L.load_products(str(ROOT / "data/external/lidar_scarp_features_u8.tif"))["evidence"], 1.0), foot)
    det_up = np.clip(det, 0.0, 1.0)
    surfaces = {
        "SA_slope_scarp": D.geometric_mean({"s": slope, "k": scarp}, {"s": 0.6, "k": 0.4}),
        "SB_slope_scarp_tmi": D.geometric_mean({"s": slope, "k": scarp, "t": tmi},
                                               {"s": 0.5, "k": 0.3, "t": 0.2}),
        "SH_basin_strong": D.geometric_mean(
            {"f": (slope ** 0.5) * ((1.0 - det_up) ** 1.5), "k": scarp, "t": tmi},
            {"f": 0.55, "k": 0.25, "t": 0.20}),
    }
    h33 = rb(ROOT / "data/comparison-h33.tif") if (ROOT / "data/comparison-h33.tif").exists() else None

    rng = np.random.default_rng(20261006)
    out = {"design": "20km four-colour blocks, strand-safe interior scoring, equal mass per arm",
           "fold_formula": "(row//200 + 2*(col//200)) % 4", "guard": "no emission within 2 px of training traces",
           "seps": list(SEPS), "budgets": list(BUDGETS), "surfaces": list(SURFACES), "folds": []}

    for f in range(4):
        t0 = time.time()
        held = (fold_id == f) & foot
        forbidden = distance_transform_edt(~held) <= 3
        training = labels & ~forbidden
        evaluation = held & (distance_transform_edt(held) > 3)
        d_train = distance_transform_edt(~training).astype(F32)
        allowed = evaluation & (d_train > 2.0)
        n_eval = int(evaluation.sum())
        arms: dict[str, dict] = {}

        def score_arm(name: str, sel: np.ndarray, note: str = "") -> None:
            r = dti(sel.astype(F32), labels, footprint=evaluation)
            n = int(sel.sum())
            mass = float(sel.sum(dtype=np.float64))
            arms[name] = dict(n_px=n, mass=mass, tp=round(r["tp"], 2), fp=round(r["fp"], 2),
                              dti=round(r["dti"], 6),
                              cpm=round(r["credit_per_mass"], 5), note=note)

        for sname in SURFACES:
            for sep in SEPS:
                for budget in BUDGETS:
                    sel = D.greedy_pack(surfaces[sname], allowed, min_sep=sep, budget=budget,
                                        candidate_cap=2_000_000)
                    score_arm(f"{sname}|sep{sep}|N{budget}", sel)
                    del sel
        # controls at 20k, equal mass, same domain
        cand = np.flatnonzero(allowed.ravel())
        sel = np.zeros(labels.shape, bool)
        sel.ravel()[rng.choice(cand, size=20_000, replace=False)] = True
        score_arm("CONTROL_uniform_random|N20000", sel, "uniform random, same domain/mass")
        del sel
        dens = gaussian_filter(training.astype(F32), 10)
        dens[~allowed] = 0.0
        sel = D.greedy_pack(dens, allowed, min_sep=3.0, budget=20_000, candidate_cap=2_000_000)
        score_arm("CONTROL_training_density|N20000", sel, "density of training catalogue")
        del sel, dens
        if h33 is not None:
            m = h33 > 0
            frac = np.zeros(labels.shape, F32)
            frac[evaluation] = np.minimum(h33[evaluation], 1.0)
            arms["historical_h33_CONTAMINATED"] = dict(
                n_px=int((m & evaluation).sum()),
                mass=float(frac[evaluation].sum(dtype=np.float64)),
                dti=round(dti(frac, labels, footprint=evaluation)["dti"], 6),
                note="built with the full catalogue; not a clean comparator")
            del m, frac
        out["folds"].append(dict(fold=f, evaluation_cells=n_eval,
                                 training_label_px=int(training.sum()),
                                 held_px=int(held.sum()),
                                 arms=arms, seconds=round(time.time() - t0, 1)))
        print(f"fold {f}: eval={n_eval:,} arms={len(arms)} "
              f"({time.time()-t0:.0f}s)", flush=True)
        for k, v in sorted(arms.items(), key=lambda kv: -kv[1]["dti"])[:6]:
            print(f"   {k:44s} dti={v['dti']:.4f} mass={v['mass']:.0f} cpm={v.get('cpm')}")
        del held, forbidden, training, evaluation, d_train, allowed
        import gc
        gc.collect()

    names = sorted({k for fo in out["folds"] for k in fo["arms"]})
    summary = {}
    for name in names:
        ds = [fo["arms"][name]["dti"] for fo in out["folds"] if name in fo["arms"]]
        summary[name] = dict(mean_dti=round(float(np.mean(ds)), 6),
                             min_dti=round(float(np.min(ds)), 6),
                             max_dti=round(float(np.max(ds)), 6), folds=len(ds))
    out["summary"] = dict(sorted(summary.items(), key=lambda kv: -kv[1]["mean_dti"]))
    best_valid = max((kv for kv in out["summary"].items() if "CONTROL" not in kv[0]
                      and "CONTAMINATED" not in kv[0]), key=lambda kv: kv[1]["mean_dti"])
    out["best_valid_arm"] = best_valid[0]
    out["best_valid_mean_dti"] = best_valid[1]["mean_dti"]
    out["control_uniform_20k"] = out["summary"].get("CONTROL_uniform_random|N20000")
    (ROOT / "evidence/h42_holdout_20km.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(best_valid=best_valid[0], mean=best_valid[1]["mean_dti"],
                          uniform_control=out["control_uniform_20k"]), indent=1))
    print("top of table:")
    for k, v in list(out["summary"].items())[:10]:
        print(f"  {k:44s} {v['mean_dti']:.4f} (min {v['min_dti']:.4f})")


if __name__ == "__main__":
    main()
