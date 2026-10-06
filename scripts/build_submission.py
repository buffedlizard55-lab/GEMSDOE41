#!/usr/bin/env python3
"""End-to-end pipeline: field -> emission -> validation -> submission.

Run:  python3 scripts/build_submission.py [--data data] [--quick] [--budget 12000]

Outputs
  evidence/data_manifest.json        official-digest verification
  evidence/catalogue_kinematics.json measured two-population structure of the catalogue
  evidence/lidar_provenance.json     decode + coverage audit of the LiDAR stack
  evidence/holdout.json              blocked-recovery experiment (variants + separation)
  evidence/thin_sweep.json           separation sweep on the incumbent support
  evidence/submission_build.json     digests, checks, projection for every artifact
  docs/downloads/*.tif               the submission files (one-click downloads)
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import time

import numpy as np
import rasterio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gems41 import catalogue as C  # noqa: E402
from gems41 import emission as E  # noqa: E402
from gems41 import field as F  # noqa: E402
from gems41 import grid as G  # noqa: E402
from gems41 import lidar as L  # noqa: E402
from gems41 import submission as S  # noqa: E402
from gems41 import validate as V  # noqa: E402
from gems41.field import RANKER_NAMES as FIELD_RANKERS  # noqa: E402
from gems41.structure import build_elements  # noqa: E402

RANKERS = FIELD_RANKERS  # from field.py, single source of truth
SEPARATIONS = (2.83, 3.5, 4.0)
GUARDS = (2.0, 3.0)  # catalogue-flank exclusion, in px (200 / 300 m)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def population_table(traces) -> dict:
    out = {}
    for sense in ("RL", "N", "LL", "unknown", "nan"):
        sel = [t for t in traces if t.sense == sense]
        if not sel:
            continue
        w = np.array([t.n_px for t in sel], float)
        ang = np.radians(2.0 * np.array([t.strike for t in sel]))
        mean_strike = float(
            (np.degrees(np.arctan2((w * np.sin(ang)).sum(), (w * np.cos(ang)).sum())) / 2) % 180
        )
        nw = sum(w[i] for i, t in enumerate(sel) if 100 <= t.strike <= 170)
        nne = sum(w[i] for i, t in enumerate(sel) if t.strike < 45 or t.strike >= 170)
        out[sense] = dict(
            traces=len(sel),
            px=int(w.sum()),
            length_weighted_mean_strike=round(mean_strike, 1),
            frac_length_NW_striking=round(nw / w.sum(), 3),
            frac_length_NNE_to_N_striking=round(nne / w.sum(), 3),
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--quick", action="store_true", help="one variant/one separation only")
    ap.add_argument("--budget", type=int, default=5_000)
    args = ap.parse_args()
    d = args.data
    t0 = time.time()
    for p in ("evidence", "docs/downloads"):
        os.makedirs(p, exist_ok=True)

    print("== 1. load + verify official digests ==")
    official = {
        "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
        "example_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    }
    digests = {}
    for name, want in official.items():
        got = sha256(os.path.join(d, name))
        digests[name] = dict(sha256=got, official=want, match=got == want)
        print(f"   {'PASS' if got == want else 'FAIL'} {name}")
    if not all(v["match"] for v in digests.values()):
        print("   DIGEST MISMATCH - refusing to build")
        return 2
    with rasterio.open(f"{d}/existing_faults.tif") as src:
        cat = src.read(1)
    cat_mask = cat == 1
    footprint = G.footprint_mask(cat)
    assert int(footprint.sum()) == G.FOOTPRINT_PX
    assert int(cat_mask.sum()) == G.CATALOGUE_PX

    print("== 2. catalogue kinematics ==")
    traces = C.extract_traces(cat_mask)
    kin = C.attach_kinematics(traces, f"{d}/gdr_qfaults_traces.csv")
    pops = population_table(traces)
    A, B, pop_summary = C.population_masks(cat_mask.shape, traces)
    for k, v in pops.items():
        print(f"   {k:8s} {v}")

    print("== 3. LiDAR decode ==")
    lid = L.load_products(f"{d}/lidar_scarp_features_u8.tif")
    cov = float((lid["valid"] & footprint).sum()) / float(footprint.sum())
    print(f"   valid {lid['valid_px']} px | {100*cov:.1f}% of footprint")
    lidar_prov = dict(
        product=f"{d}/lidar_scarp_features_u8.tif",
        sha256=sha256(f"{d}/lidar_scarp_features_u8.tif"),
        bands=list(L.BANDS),
        quantisation={k: list(v) for k, v in L.QUANT.items()},
        valid_px=int(lid["valid_px"]),
        valid_fraction_of_footprint=round(cov, 4),
        source="USGS 3DEP 1 m DEM tiles -> 2 m work grid -> 100 m competition grid",
        rights="USGS 3DEP products are available without use restrictions",
        caveats=[
            "uncalibrated terrain descriptors, not fault detections",
            "roads, channels, terrace risers, paleo-shorelines, landslides and mines also create steps",
        ],
    )
    json.dump(lidar_prov, open("evidence/lidar_provenance.json", "w"), indent=1)
    json.dump(digests, open("evidence/data_manifest.json", "w"), indent=1)

    print("== 4. structural elements ==")
    elems = build_elements(traces, A, B)
    elems["corridor"] = elems["transfer"] | elems["extension"] | elems["relay"]
    print(f"   {elems['counts']} | corridor {int(elems['corridor'].sum())} px")

    descriptor = dict(
        catalogue=dict(px=int(cat_mask.sum()), traces=len(traces), min_trace_px=C.MIN_TRACE_PX),
        kinematics_join=kin,
        populations=pops,
        population_raster=pop_summary,
        element_counts=elems["counts"],
        reference_strikes=dict(walker_lane_NW_deg=C.NW_REF_DEG, basin_range_NNE_deg=C.NNE_REF_DEG),
    )
    json.dump(descriptor, open("evidence/catalogue_kinematics.json", "w"), indent=1, default=float)

    print("== 5a. orientation audit (label-free check of criterion 2) ==")
    oa = V.orientation_audit(cat_mask, traces, lid)
    for k, v in oa.items():
        print(f"   {k:4s} {v}")

    print("== 5b. blocked-recovery experiment (strand-level holdout) ==")
    seed_support = None
    if os.path.exists(f"{d}/reference/anchor_02600_zeros.tif"):
        with rasterio.open(f"{d}/reference/anchor_02600_zeros.tif") as src:
            seed_support = src.read(1) > 0
    contexts = V.fold_contexts(cat_mask, lid, incumbent_support=seed_support)
    print(f"   {len(contexts)} folds | truth px {[fo.summary['truth_px_min_guard'] for fo in contexts]} "
          f"| held strands {[fo.summary['held_strands'] for fo in contexts]}")

    def run(rank, guards, seps):
        out = {}
        for g in guards:
            for sep in seps:
                ev = V.evaluate(contexts, min_sep_px=sep, budget=args.budget, guard_px=g)
                out[f"guard{g:.0f}_sep{sep:.2f}"] = ev["summary"]
                sm = ev["summary"]
                print(f"   guard {g:.0f}px sep {sep:4.2f}: "
                      + " | ".join(f"{n.replace('baseline_','b_').replace('H41_','').replace('thrift_','t_')}"
                                   f"={sm[n]['credit_per_mass']:.4f}" for n in rank if n in sm), flush=True)
                del ev
                gc.collect()
        return out

    todo_rank = RANKERS if not args.quick else RANKERS
    todo_sep = (3.5,) if args.quick else SEPARATIONS
    todo_guard = (3.0,) if args.quick else GUARDS
    experiment = run(todo_rank, todo_guard, todo_sep)

    # winner = ranker with the highest credit-per-mass across the swept settings
    totals = {}
    for key, summ in experiment.items():
        for n, v in summ.items():
            totals.setdefault(n, []).append(v["credit_per_mass"])
    best_variant = max(totals, key=lambda n: float(np.mean(totals[n])))
    print(f"   winner by measurement: {best_variant}")

    seps = {k: v for k, v in experiment.items() if k.startswith("guard3")}
    best_sep = "2.83"
    if seps:
        best_sep = max(
            seps, key=lambda k: seps[k].get(best_variant, {"credit_per_mass": -1})["credit_per_mass"]
        ).split("sep")[1]
    json.dump(
        dict(experiment=experiment, winner_ranker=best_variant, winner_separation=best_sep,
             descriptor=descriptor, orientation_audit=oa,
             ranker_names=list(RANKERS),
             instrument=dict(
                 folds=len(contexts),
                 holdout="strand-level (components merged within 6 px), guard = distance to retained catalogue",
                 note="truth = held-out catalogue strands; cannot reward a genuinely new fault; not a live-score estimate",
                 K_hidden_px_model=V.K_HIDDEN_PX,
             )),
        open("evidence/holdout.json", "w"), indent=1, default=float,
    )
    del contexts
    gc.collect()

    print("== 6. incumbent support separation sweep (thrift arm) ==")
    anchor_path = f"{d}/reference/anchor_02600_zeros.tif"
    anchor = None
    thin_sweep = {}
    if os.path.exists(anchor_path):
        with rasterio.open(anchor_path) as src:
            anchor = src.read(1) > 0
        for sep in (2.83, 3.5, 4.0, 5.0, 6.0):
            th = E.thin_support(anchor, min_sep_px=sep)
            thin_sweep[f"{sep:.2f}"] = E.describe(th)
            print(f"   sep {sep:4.2f}: {thin_sweep[f'{sep:.2f}']['n']:6d} px "
                  f"(from {int(anchor.sum())}) nn_min={thin_sweep[f'{sep:.2f}']['nn_min']:.2f}")
        json.dump(thin_sweep, open("evidence/thin_sweep.json", "w"), indent=1, default=float)

    print("== 7. build shipped artifacts ==")
    comp = F.components_full(cat_mask, A, B, elems, lid, corridor_width_px=2.0)
    allowed = footprint & (~cat_mask) & (comp["exclusion"] > 0)
    shop = F.combine_rankers(comp, allowed, np.random.default_rng(41))
    if best_variant not in shop:
        raise SystemExit(f"winner {best_variant} is not in the shipped ranker table")
    score = shop[best_variant]
    sep = float(best_sep)
    core = E.greedy_pack(score, allowed, min_sep_px=sep, budget=20_000)
    print(f"   {best_variant}: {int(core.sum())} px at separation {sep} px")

    built = {"h41-core": core}
    if anchor is not None:
        thin = E.thin_support(anchor, min_sep_px=sep, priority=score)
        built["h41-ext-union"] = E.union(core, thin)
        print(f"   H41-ext-union: {int(built['h41-ext-union'].sum())} px "
              f"(core {int(core.sum())} + incumbent re-emitted {int(thin.sum())})")

    artifacts = {}
    for name, mask in built.items():
        art = S.finalize(mask, footprint, name=name)
        art = dict(art)
        art["n_px"] = int(mask.sum())
        art["junction_concentration"] = F.junction_concentration(mask, elems, A, B)
        # overlap with the incumbent support, reported rather than hidden
        if anchor is not None:
            art["overlap"] = dict(
                n_px=art["n_px"],
                on_incumbent_support=int((mask & anchor).sum()),
                pct_on_incumbent_support=round(100.0 * float((mask & anchor).sum()) / max(art["n_px"], 1), 2),
                off_incumbent_support=int((mask & ~anchor).sum()),
            )
        c_meas = float(np.mean(totals[best_variant]))
        art["projection"] = dict(
            metric="[MODEL] DTI = c/(0.2 + 0.8*K/S), K = 13000 px; c is a HOLDOUT measurement, not a live score",
            credit_per_mass_measured_on_holdout=c_meas,
            n_px=art["n_px"],
            projected=float(V.project_live_dti(c_meas, art["n_px"])),
        )
        artifacts[name] = art
        print(f"   {name}: {art['n_px']} px -> {art['path']} sha256 {art['sha256'][:16]}...")

    json.dump(
        dict(
            created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            artifacts=artifacts, best_variant=best_variant, experiment=experiment,
            orientation_audit=oa,
            chosen_separation_px=sep, descriptor=descriptor, digests=digests,
            elapsed_s=round(time.time() - t0, 1),
        ),
        open("evidence/submission_build.json", "w"), indent=1, default=float,
    )
    print(f"done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
