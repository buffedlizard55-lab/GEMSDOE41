#!/usr/bin/env python3
"""Independent physical validation of the structural geometry.

Asks one question: do known geothermal wells and springs in this footprint concentrate on the
structural elements (transfer corridors, tip extensions, relay ramps) beyond what the site
*area* and a *blocked permutation null* predict?  See src/gems41/sites.py for why this test
exists and what a negative result means.

Run:  python3 scripts/run_site_control.py [--data data]
Writes evidence/site_control.json and docs/downloads/site-control.json
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
from gems41 import grid as G  # noqa: E402
from gems41 import sites as S  # noqa: E402
from gems41.structure import build_elements  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--perm", type=int, default=200)
    args = ap.parse_args()
    d = args.data
    t0 = time.time()

    with rasterio.open(f"{d}/existing_faults.tif") as src:
        cat = src.read(1)
    cat_mask = cat == 1
    footprint = G.footprint_mask(cat)

    traces = C.extract_traces(cat_mask)
    C.attach_kinematics(traces, f"{d}/gdr_qfaults_traces.csv")
    A, B, pop = C.population_masks(cat_mask.shape, traces)
    elems = build_elements(traces, A, B)
    elems["corridor"] = elems["transfer"] | elems["extension"] | elems["relay"]
    corridor = elems["corridor"]

    st = S.load_sites(f"{d}/gdr_wellspring_in_footprint.csv")
    print(f"sites: {st['n']} records, {st['n_hot']} hot (geothermometer >150 C or T >50 C)")

    out = dict(
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        sites_total=int(st["n"]),
        sites_hot=int(st["n_hot"]),
        population_summary=pop,
        element_counts=elems["counts"],
        corridor_px=int(corridor.sum()),
        footprint_px=int(footprint.sum()),
        tests={},
        per_element={},
    )

    for hot in (True, False):
        for radius in (3.0, 7.5, 15.0):
            key = f"{'hot' if hot else 'all'}_r{radius:g}px"
            r = S.enrichment(st, corridor, footprint, hot_only=hot, radius_px=radius, n_perm=args.perm)
            out["tests"][key] = r
            print(f"  {key:12s} obs={r['observed_fraction']:.4f} area={r['area_fraction']:.4f} "
                  f"enr_area={r['enrichment_vs_area']} enr_null={r['enrichment_vs_null']} "
                  f"p={r['p_value_blocked_permutation']:.4f}")

    # does the corridor add information beyond the published catalogue?
    out["vs_catalogue"] = S.compare_distances(st, corridor, cat_mask)
    print(f"  vs catalogue: {out['vs_catalogue']}")

    # per-element attribution: which element family carries the signal?
    for name in ("transfer", "extension", "relay"):
        if name not in elems:
            continue
        r = S.enrichment(st, elems[name], footprint, hot_only=True, radius_px=7.5, n_perm=args.perm)
        out["per_element"][name] = r
        print(f"  {name:10s} px={int(elems[name].sum()):7d} enr_area={r['enrichment_vs_area']} "
              f"p={r['p_value_blocked_permutation']:.4f}")

    # control: the published catalogue itself, which MUST show enrichment if the test has power
    out["control_known_catalogue"] = S.enrichment(
        st, cat_mask, footprint, hot_only=True, radius_px=7.5, n_perm=args.perm
    )
    c = out["control_known_catalogue"]
    print(f"  control (published catalogue): enr_area={c['enrichment_vs_area']} p={c['p_value_blocked_permutation']:.4f}")

    os.makedirs("evidence", exist_ok=True)
    os.makedirs("docs/downloads", exist_ok=True)
    json.dump(out, open("evidence/site_control.json", "w"), indent=1, default=float)
    json.dump(out, open("docs/downloads/site-control.json", "w"), indent=1, default=float)
    print(f"done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
