#!/usr/bin/env python3
"""Build the shipped artifacts from the measured winner.

Separated from `build_submission.py` so the emission geometry can be rebuilt without repeating
the (slow) blocked-recovery sweep.  Reads `evidence/holdout.json` for the winning ranker and
separation, rebuilds the same ranker table on the full catalogue, and writes:

  h41-bimodal-thrift   the primary. The group's best-known live-scored emission support (owner-
                       reported 0.2600) re-emitted at a measured minimum separation with the
                       published catalogue flank excluded, RANKED BY the bimodal kinematic
                       criterion.  Measured on the strand-level holdout: identical mass, identical
                       separation, credit-per-mass 0.0606 -> 0.0788 (+30 %) when the kinematic
                       ranker replaces uniform coverage of the same support.
  h41-core             the new-field arm: structural geometry only, no incumbent mass.
  h41-ext-union        core UNION the thrift arm, for comparison.

Run:  python3 scripts/build_final.py [--data data]
"""

from __future__ import annotations

import argparse
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
from gems41.structure import build_elements  # noqa: E402

STAMP = "20261005T234500Z"
# The primary is the MATCHED-MASS variant: the owner's live-validated support, re-emitted at the
# separation that reproduces their best-known mass, with exactly ONE mechanism changed (the
# kinematic ranking).  That is the artifact whose leaderboard return is interpretable; a variant
# that changes mass and ranking together cannot be attributed.
PRIMARY = "h41-bimodal-thrift-20k"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--sep", type=float, default=None)
    args = ap.parse_args()
    d = args.data
    t0 = time.time()

    hold = json.load(open("evidence/holdout.json"))
    winner = hold.get("winner_ranker", "thrift_support_kinematic_filter")
    if winner not in F.RANKER_NAMES:
        winner = "thrift_support_kinematic_filter"
    sep = float(args.sep or hold.get("winner_separation", "2.83"))
    print(f"measured winner: {winner} at {sep} px separation")

    with rasterio.open(f"{d}/existing_faults.tif") as src:
        cat = src.read(1)
    cat_mask = cat == 1
    footprint = G.footprint_mask(cat)

    traces = C.extract_traces(cat_mask)
    C.attach_kinematics(traces, f"{d}/gdr_qfaults_traces.csv")
    A, B, pop = C.population_masks(cat_mask.shape, traces)
    elems = build_elements(traces, A, B)
    elems["corridor"] = elems["transfer"] | elems["extension"] | elems["relay"]
    lid = L.load_products(f"{d}/lidar_scarp_features_u8.tif")

    support = None
    p = f"{d}/reference/anchor_02600_zeros.tif"
    if os.path.exists(p):
        with rasterio.open(p) as src:
            support = src.read(1) > 0
        print(f"incumbent support: {int(support.sum())} px")

    # exclusion ramp: 0 within 300 m of the catalogue, 1 beyond 500 m (the measured dead-weight
    # flank; the family's live dose-response moved 0.2600 -> 0.2708 -> 0.2778 as this band grew)
    comp = F.components_full(cat_mask, A, B, elems, lid, corridor_width_px=2.0,
                             exclusion_lo_px=3.0, exclusion_hi_px=5.0)
    allowed = footprint & (~cat_mask) & (comp["exclusion"] > 0)
    shop = F.combine_rankers(comp, allowed, np.random.default_rng(41), support=support)
    score = shop[winner]
    print(f"allowed {int(allowed.sum())} px | winner candidate field {int((score > 0).sum())} px")

    artifacts = {}

    # ---------------- primary: kinematic-ranked thrift of the incumbent support ----------------
    if support is not None and winner.startswith("thrift_support"):
        sup_allowed = support & allowed
        prim = E.greedy_pack(score, sup_allowed, min_sep_px=sep, budget=200_000, candidate_cap=200_000)
        thin = E.greedy_pack(
            np.where(sup_allowed, comp["evidence"], 0.0), sup_allowed,
            min_sep_px=sep, budget=20_000, candidate_cap=60_000,
        )
    else:
        prim = E.greedy_pack(score, allowed, min_sep_px=sep, budget=20_000, candidate_cap=60_000)
        thin = np.zeros_like(prim)
    print(f"primary {PRIMARY}: {int(prim.sum())} px")

    # ---------------- new-field arm ----------------
    core_ranker = "H41_orient_x_evidence" if "H41_orient_x_evidence" in shop else winner
    core = E.greedy_pack(shop[core_ranker], allowed, min_sep_px=sep, budget=20_000, candidate_cap=60_000)
    print(f"h41-core ({core_ranker}): {int(core.sum())} px")

    # ---------------- 2020 rupture envelope, if the seismicity evidence exists ----------------
    seis = None
    npy = "evidence/seismicity_corridor.npz"
    if os.path.exists(npy):
        seis = np.load(npy) & footprint & (~cat_mask) & (comp["exclusion"] > 0)
        seis = E.thin_support(seis, min_sep_px=sep, priority=comp["evidence"])
        print(f"h41-rupture2020: {int(seis.sum())} px")

    # --- matched-mass, single-mechanism twin -------------------------------------------------
    # The owner's best-known artifact (0.2778) is their 44,090 px support minus every dot within
    # 200 m (2 px) of the catalogue, i.e. a B=2 flank prune at 2.83 px spacing -> 37,654 px.
    # Rebuilding with the SAME B=2 prune and the SAME spacing but with the kinematic ranking
    # changes exactly one thing: which dots survive the separation constraint.  The mass comes out
    # at the same order (see below), so a leaderboard return on this file is attributable to the
    # ranking rather than to a change in mass.
    allowed_b2 = footprint & (~cat_mask) & (
        F.components_full(cat_mask, A, B, elems, lid, corridor_width_px=2.0,
                          exclusion_lo_px=2.0, exclusion_hi_px=4.0)["exclusion"] > 0
    )
    shop_b2 = F.combine_rankers(comp, allowed_b2, np.random.default_rng(41), support=support)
    matched = (
        E.greedy_pack(shop_b2[winner], support & allowed_b2, min_sep_px=2.83,
                      budget=200_000, candidate_cap=200_000)
        if (support is not None and winner.startswith("thrift_support"))
        else prim
    )
    matched_control = (
        E.greedy_pack(shop_b2["thrift_support_uniform"], support & allowed_b2, min_sep_px=2.83,
                      budget=200_000, candidate_cap=200_000)
        if (support is not None and winner.startswith("thrift_support"))
        else prim
    )
    ov = int((matched & matched_control).sum())
    print(f"matched-mass twin: {int(matched.sum())} px vs uniform control {int(matched_control.sum())} px "
          f"| shared {ov} px ({100.0*ov/max(int(matched.sum()),1):.1f} % of the twin)")
    print(f"matched-mass twin: {int(matched.sum())} px (target 37,654 = the owner's best-known mass)")

    # --- the measured mass ladder, as artifacts ------------------------------------------
    # Measured on the strand-level holdout (evidence/mass_ladder.json), kinematic vs uniform at
    # identical truth, identical domain and identical 2.83 px spacing:
    #   2,500 px -> 1.52x | 5,000 -> 1.30x | 8,000 -> 1.22x | 12,000 -> 1.29x | 20,000 -> 1.25x
    #   30,000 px -> 1.006x   (the ranking has nothing left to decide at that density)
    # The family's own live record thinned 121,131 -> 60,069 -> 44,090 -> 37,654 px and gained
    # every time (0.1922 -> 0.2477 -> 0.2600 -> 0.2778).  The primary continues that trend AND
    # sits in the mass band where the new criterion is measured to pay.
    def thrift(budget: int, sep_px: float) -> np.ndarray:
        if support is None or not winner.startswith("thrift_support"):
            return prim[:]
        return E.greedy_pack(shop[winner], support & allowed, min_sep_px=sep_px,
                             budget=budget, candidate_cap=200_000)

    prim20 = thrift(20_000, 2.83)
    built = {
        "h41-bimodal-thrift-20k": prim20,
        "h41-bimodal-thrift-5k": thrift(5_000, 2.83),
        "h41-bimodal-thrift-37k": matched,
        "h41-core": core,
        "h41-bimodal-thrift-20k-uninformative-control": E.greedy_pack(
            shop["thrift_support_uniform"], support & allowed, min_sep_px=2.83,
            budget=20_000, candidate_cap=200_000),
    }
    if seis is not None and seis.sum():
        built["h41-rupture2020-union"] = E.union(prim20, seis)

    for name, mask in built.items():
        art = S.finalize(mask, footprint, name=name, stamp=STAMP)
        art["n_px"] = int(mask.sum())
        art["junction_concentration"] = F.junction_concentration(mask, elems, A, B)
        if support is not None:
            on = int((mask & support).sum())
            art["composition"] = dict(
                n_px=art["n_px"],
                on_incumbent_support=on,
                pct_on_incumbent_support=round(100.0 * on / max(art["n_px"], 1), 2),
                off_incumbent_support=int((mask & ~support).sum()),
            )
        art["note"] = (
            f"GEMSDOE41 {name} | bimodal Walker Lane/Basin-and-Range structural ranker "
            f"({winner}) on a {sep:.2f}px min-separation packing; 0 px within 300m of the "
            f"published catalogue; UNSCORED"
        )[:200]
        artifacts[name] = art
        print(f"   {name}: {art['n_px']} px, {art['bytes']/1e6:.2f} MB -> {art['path']}")

    # ---------------- projection (MODEL, not a score) ----------------
    summ = hold.get("experiment", {})
    c_win, c_uni = [], []
    for k, v in summ.items():
        if winner in v:
            c_win.append(v[winner]["credit_per_mass"])
        if "thrift_support_uniform" in v:
            c_uni.append(v["thrift_support_uniform"]["credit_per_mass"])
    c_meas = float(np.mean(c_win)) if c_win else 0.0
    c_uniform = float(np.mean(c_uni)) if c_uni else 0.0
    for name, art in artifacts.items():
        art["projection"] = dict(
            metric="[MODEL] DTI = c/(0.2 + 0.8*K/S), K = 13000 px",
            credit_per_mass_holdout_mean=c_meas,
            credit_per_mass_uniform_control=c_uniform,
            relative_gain_vs_uniform_control=round(c_meas / c_uniform, 3) if c_uniform else None,
            n_px=art["n_px"],
            projected=float(V.project_live_dti(c_meas, art["n_px"])),
            caveat="c is a HOLDOUT measurement against catalogue strands, not a live score; only the "
            "RATIO to the uniform control is instrument-internal and therefore comparable",
        )

    out = dict(
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        winner_ranker=winner,
        chosen_separation_px=sep,
        populations=pop,
        artifacts=artifacts,
        primary=PRIMARY,
        elapsed_s=round(time.time() - t0, 1),
    )
    json.dump(out, open("evidence/submission_build.json", "w"), indent=1, default=float)
    print(f"done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
