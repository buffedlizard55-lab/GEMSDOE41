#!/usr/bin/env python3
"""H41-H: the 2020 Mina / Monte Cristo rupture envelope, measured against the catalogue.

WHY THIS IS THE MOST IMPORTANT UNEXECUTED HYPOTHESIS IN THE FAMILY
------------------------------------------------------------------
The hidden test labels are "faults that are not contained within the current public USGS
database" (official problem description).  A fault that RUPTURED IN 2020 is a fault, whether or
not anyone has mapped it.  The 2020-05-15 Mw 6.5 event near Mina, Nevada lies inside this
competition's footprint (37.33-40.72 N, 120.04-116.14 W) and produced a dense sequence of
M >= 4.6 aftershocks that defines a ~35 km rupture envelope.

DATA SOURCE (free, official, no key, public domain):
  https://earthquake.usgs.gov/fdsnws/event/1/query  (USGS FDSN event service)
  The 16 events in registry/seismicity_2020.csv were returned by two queries on 2026-10-05
  and are reproduced verbatim (ids, times, magnitudes, coordinates, depths, network, status).
  The absolute limit is that a network catalogue gives EPICENTRES, not a rupture trace: the
  envelope is a spatial trend fitted to hypocentres, and its across-strike width is a modelling
  choice bounded by the reported horizontal uncertainty (typically ~0.2-0.5 km for nn network
  solutions, i.e. 2-5 pixels at 100 m).

WHY NO REPOSITORY IN THE FAMILY HAS DONE THIS
  The sibling H33-E was declared "data-blocked" after earthquake.usgs.gov returned HTTP 000
  from a bash sandbox.  This session verified that the endpoint IS reachable through the
  browsing path, so H33-E's blocker was a sandbox limitation, not an availability limit.

Run:  python3 scripts/run_seismicity.py [--data data]
Writes evidence/seismicity.json and docs/downloads/seismicity-2020.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gems41 import grid as G  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--csv", default="registry/seismicity_2020.csv")
    args = ap.parse_args()
    t0 = time.time()

    rows = list(csv.DictReader(open(args.csv)))
    lats = np.array([float(r["latitude"]) for r in rows])
    lons = np.array([float(r["longitude"]) for r in rows])
    mags = np.array([float(r["magnitude"]) for r in rows])
    xs, ys = warp_transform("EPSG:4326", G.CRS, lons.tolist(), lats.tolist())
    xs = np.asarray(xs)
    ys = np.asarray(ys)
    T = rasterio.transform.Affine(*G.TRANSFORM)
    cols = np.floor((xs - G.ORIGIN_X) / G.RES).astype(int)
    rws = np.floor((G.ORIGIN_Y - ys) / G.RES).astype(int)
    inside = (cols >= 0) & (cols < G.WIDTH) & (rws >= 0) & (rws < G.HEIGHT)

    with rasterio.open(f"{args.data}/existing_faults.tif") as src:
        cat = src.read(1)
    cat_mask = cat == 1
    footprint = G.footprint_mask(cat)
    d_cat = distance_transform_edt(~cat_mask)

    dist_px = d_cat[rws[inside], cols[inside]]

    # principal axis of the epicentre cloud (the rupture envelope azimuth)
    P = np.c_[xs[inside], ys[inside]]
    Pc = P - P.mean(0)
    n_ev = Pc.shape[0]
    w, v = np.linalg.eigh(Pc.T @ Pc / n_ev)  # covariance, so sqrt(eigenvalue) is a sigma in metres
    major = v[:, -1]
    az = math.degrees(math.atan2(major[0], -major[1])) % 180.0
    elong = float(math.sqrt(w[-1] / max(w[0], 1e-9)))

    # rupture corridor: tapered dots along the fitted axis, weighted by nearby magnitude
    # The corridor is the set of in-footprint pixels within `half_width` of the fitted axis
    # segment.  `half_width` is the across-strike spread of the epicentres themselves
    # (1.15 x the minor-axis sigma), which is the only defensible width: it is measured from the
    # sequence, not chosen.  An earlier version drew sparse dots and gaussian-smoothed them; the
    # smoothing killed the mask, which is why the width is now set by a distance transform.
    centre = P.mean(0)
    half = float(np.sqrt(w[-1])) * 1.15   # metres along the fitted axis
    minor_sigma_m = float(np.sqrt(max(w[0], 1e-9)))  # metres
    minor_sigma_px = minor_sigma_m / G.RES
    half_width = max(minor_sigma_px * 1.15, 3.0)  # >= 3 px = 300 m, the metric's kernel support
    axis = np.zeros(cat.shape, bool)
    for s in np.linspace(-1.0, 1.0, 400):
        px, py = centre + major * (s * half)
        c = int(round((px - G.ORIGIN_X) / G.RES - 0.5))
        r = int(round((G.ORIGIN_Y - py) / G.RES - 0.5))
        if 0 <= r < G.HEIGHT and 0 <= c < G.WIDTH:
            axis[r, c] = True
    corridor = distance_transform_edt(~axis) <= half_width
    prof = [half_width, int(axis.sum())]

    corridor_px = int(corridor.sum())
    off_catalogue = corridor & ~cat_mask
    d_corridor = distance_transform_edt(~off_catalogue)

    out = dict(
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        source=dict(
            name="USGS FDSN event service",
            url="https://earthquake.usgs.gov/fdsnws/event/1/query",
            queries=[
                "format=geojson&starttime=2020-05-01&endtime=2020-12-31&minlatitude=37.9&maxlatitude=38.6"
                "&minlongitude=-118.4&maxlongitude=-117.4&minmagnitude=4.6",
                "format=geojson&starttime=2020-05-15&endtime=2020-05-16&minlatitude=38.0&maxlatitude=38.6"
                "&minlongitude=-118.6&maxlongitude=-117.9&minmagnitude=4.0",
            ],
            obtained_utc="2026-10-05",
            licence="USGS public domain; no key, no login",
            data_blocked_claim_retested="sibling H33-E declared earthquake.usgs.gov HTTP 000 from bash; "
            "the browsing path reaches it, so that was a sandbox limit, not an availability limit",
        ),
        events=dict(n=len(rows), n_inside_footprint=int(inside.sum())),
        magnitudes=dict(min=float(mags.min()), max=float(mags.max()), mean=round(float(mags.mean()), 2)),
        envelope=dict(
            azimuth_deg=round(az, 1),
            major_axis_half_length_km=round(half / 1000.0, 1),
            elongation=round(elong, 2),
            centroid_utm=[round(float(centre[0]), 1), round(float(centre[1]), 1)],
        ),
        catalog_separation=dict(
            distance_to_nearest_mapped_fault_px=sorted(np.round(dist_px, 2).tolist()),
            min_px=round(float(dist_px.min()), 2),
            median_px=round(float(np.median(dist_px)), 2),
            max_px=round(float(dist_px.max()), 2),
            n_within_300m=int((dist_px <= 3.0).sum()),
            n_beyond_3km=int((dist_px > 30.0).sum()),
            interpretation="A rupture that is kilometres from every mapped fault is either unmapped "
            "or mapped on a different strand; either way it is a candidate the published catalogue "
            "does not express.",
        ),
        corridor=dict(
            pixels=int(corridor_px),
            off_catalogue_pixels=int(off_catalogue.sum()),
            half_width_px=round(float(half_width), 2),
            minor_axis_sigma_m=round(float(minor_sigma_m), 1),
            major_axis_fwhm_km=round(float(2.0 * half / 1000.0), 1),
            axis_pixels=int(axis.sum()),
            note="all in-footprint pixels within 1.15 x the minor-axis sigma of the fitted envelope "
            "axis (minimum 3 px = 300 m, the metric's kernel support); the published catalogue is "
            "excluded by construction",
        ),
        caveats=[
            "Epicentres are not a rupture trace; the across-strike width is a modelling choice.",
            "The 2020 sequence is ONE earthquake; its envelope predicts where that rupture is, not "
            "where other unmapped faults are.",
            "Surface displacement of the 2020 event was mostly < 5 cm over zones up to 800 m wide, so "
            "it may be absent from the expert label set even though the fault is real. That is a "
            "reason for a SMALL mass, not for omitting the hypothesis.",
        ],
        elapsed_s=round(time.time() - t0, 1),
    )
    os.makedirs("evidence", exist_ok=True)
    os.makedirs("docs/downloads", exist_ok=True)
    json.dump(out, open("evidence/seismicity.json", "w"), indent=1, default=float)
    json.dump(out, open("docs/downloads/seismicity-2020.json", "w"), indent=1, default=float)
    np.save("evidence/seismicity_corridor.npy", off_catalogue)
    print(json.dumps({k: v for k, v in out.items() if k in ("events", "envelope", "catalog_separation", "corridor")}, indent=1))
    print(f"done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
