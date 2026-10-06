"""An instrument that is independent of the fault catalogue: geothermal well/spring sites.

WHY THIS INSTRUMENT EXISTS
--------------------------
The blocked-recovery holdout in `validate.py` has a hard ceiling: its truth is faults that are
*in* the published catalogue, so a hypothesis which claims "the unmapped faults live in the
transfer gaps between the two mapped populations" cannot be rewarded by it — and it was not.
Two independent implementations (this one and the sibling session's, merged on `main`) both
measured DTI = 0.0000 for the corridor-only field on catalogue-truth holdouts.

A test that CAN discriminate is to score the structural geometry against a physical
manifestation that is *not* the catalogue: where geothermal fluids actually reach the surface.

  THE FRAMEWORK PREDICTS THIS.  Faulds et al. (2005) — "The strike-slip faults end in arrays of
  ~N-striking normal faults, suggesting that dextral shear diffuses into extension in the Great
  Basin."  Anderson & Faulds (Emerson Pass, OSTI 1110519) — "The NW-striking right-lateral
  Pyramid Lake fault … terminates … and transfers strain to the NNE-striking down to the west
  Lake Range fault, resulting in high geothermal potential."  Faulds et al. (2015, DOE
  DE-EE0002748) catalogue the host settings: step-overs/relay ramps ~32 %, normal x strike-slip
  intersections 22 %, normal-fault terminations 22 %.

  A TRANSFER CORRIDOR THAT HOSTS NO THERMAL ANOMALY IS NOT A TRANSFER CORRIDOR.

THE DATA (free, official, already cited by this project)
  GDR 1391 -> `gdr_wellspring_in_footprint.csv`: 27,092 geo-referenced spring/well records inside
  the competition footprint, with `temp_c` and three independent geothermometer estimates
  (quartz, chalcedony, Na-K-Ca) and `dist_known_fault_px`.  This is a *measured* surface
  manifestation, not a model output and not a fault map.

WHAT A NEGATIVE RESULT WOULD MEAN  (stated before the test is run, so it cannot be reinterpreted)
  If sites do not concentrate on the corridors beyond what the surrounding area and the known
  faults already explain, then the corridor geometry has no independent physical support at the
  100 m grid and must not be shipped as a discovery claim.
"""

from __future__ import annotations

import csv

import numpy as np
from scipy.ndimage import distance_transform_edt

F32 = np.float32


def load_sites(path: str) -> dict:
    """Read the GDR well/spring table into arrays, with the hot subset flagged."""
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    rec = {k: [] for k in ("row", "col", "temp_c", "qz", "ch", "cat", "dist_fault_px", "layer", "thermalclass")}
    for r in rows:
        try:
            row = int(float(r.get("row", "")))
            col = int(float(r.get("col", "")))
        except (TypeError, ValueError):
            continue
        if not (0 <= row < 3730 and 0 <= col < 3292):
            continue
        rec["row"].append(row)
        rec["col"].append(col)
        for key, src in (("temp_c", "temp_c"), ("qz", "geothermquartz_c"), ("ch", "geothermchalc_c"),
                         ("cat", "geothermcat_c"), ("dist_fault_px", "dist_known_fault_px")):
            try:
                rec[key].append(float(r.get(src, "") or "nan"))
            except ValueError:
                rec[key].append(float("nan"))
        rec["layer"].append(r.get("layer", ""))
        rec["thermalclass"].append(r.get("thermalclass", ""))
    out = {k: np.asarray(v) for k, v in rec.items()}
    # "hot" = at least one independent geothermometer above 150 C, or a measured T above 50 C
    hot = (
        (out["qz"] > 150) | (out["ch"] > 150) | (out["cat"] > 150) | (out["temp_c"] > 50)
    )
    out["hot"] = hot
    out["n"] = out["row"].size
    out["n_hot"] = int(hot.sum())
    return out


def enrichment(
    sites: dict,
    target: np.ndarray,
    footprint: np.ndarray,
    *,
    hot_only: bool = True,
    radius_px: float = 7.5,
    block_px: int = 100,
    n_perm: int = 300,
    seed: int = 41,
) -> dict:
    """Site enrichment inside `target`, against an area control and a blocked permutation null.

    * area control: the fraction of in-footprint *area* within `radius_px` of `target`
    * blocked permutation: sites are shuffled between cells of a `block_px` grid within the
      footprint, which preserves the regional sampling density (GDR does not sample uniformly)
      while destroying any relationship to the target geometry.
    """
    d = distance_transform_edt(~target).astype(F32)
    row = sites["row"]
    col = sites["col"]
    if hot_only:
        row, col = row[sites["hot"]], col[sites["hot"]]
    n = row.size
    if n == 0:
        return dict(n=0)
    hit = d[row, col] <= radius_px
    obs = float(hit.mean())
    area = float((d[footprint] <= radius_px).mean())

    # --- blocked permutation: keep the count per block, shuffle positions inside the block
    rng = np.random.default_rng(seed)
    br = (row // block_px).astype(np.int64)
    bc = (col // block_px).astype(np.int64)
    keys = br * 10_000 + bc
    uniq, inv = np.unique(keys, return_inverse=True)
    # candidate pool per block = in-footprint cells of that block
    fp_r, fp_c = np.nonzero(footprint)
    fk = (fp_r // block_px).astype(np.int64) * 10_000 + (fp_c // block_px).astype(np.int64)
    order = np.argsort(fk, kind="stable")
    fk_s = fk[order]
    starts = np.searchsorted(fk_s, uniq, "left")
    ends = np.searchsorted(fk_s, uniq, "right")
    counts = np.bincount(inv, minlength=uniq.size)
    null = []
    for _ in range(n_perm):
        rr = np.empty(n, dtype=np.int64)
        cc = np.empty(n, dtype=np.int64)
        for i in range(uniq.size):
            m = counts[i]
            if m == 0:
                continue
            pool = order[starts[i] : ends[i]]
            pick = rng.choice(pool, size=m, replace=m > pool.size)
            rr[inv == i] = fp_r[pick]
            cc[inv == i] = fp_c[pick]
        null.append(float((d[rr, cc] <= radius_px).mean()))
    null = np.asarray(null)
    p = float((1 + int((null >= obs).sum())) / (n_perm + 1))
    return dict(
        n_sites=int(n),
        hot_only=hot_only,
        radius_px=radius_px,
        observed_fraction=round(obs, 5),
        area_fraction=round(area, 5),
        enrichment_vs_area=round(obs / area, 3) if area > 0 else None,
        null_mean=round(float(null.mean()), 5),
        null_sd=round(float(null.std()), 5),
        enrichment_vs_null=round(obs / float(null.mean()), 3) if null.mean() > 0 else None,
        p_value_blocked_permutation=p,
        n_blocks=int(uniq.size),
        n_perm=n_perm,
    )


def compare_distances(sites: dict, target: np.ndarray, known_catalogue: np.ndarray, *, radius_px: float = 7.5) -> dict:
    """Is the corridor adding anything beyond the published catalogue?

    Reports, for the hot sites: the fraction within `radius_px` of the catalogue, the fraction
    within `radius_px` of the corridor, and the fraction of *catalogue-detached* sites (further
    than 30 px = 3 km from any catalogued fault, i.e. where a new fault is the only explanation)
    that the corridor nevertheless captures.
    """
    d_t = distance_transform_edt(~target).astype(F32)
    d_c = distance_transform_edt(~known_catalogue).astype(F32)
    row = sites["row"][sites["hot"]]
    col = sites["col"][sites["hot"]]
    if row.size == 0:
        return dict(n=0)
    on_cat = d_c[row, col] <= radius_px
    on_cor = d_t[row, col] <= radius_px
    detached = d_c[row, col] > 30.0
    return dict(
        n_hot=int(row.size),
        frac_within_corridor=round(float(on_cor.mean()), 4),
        frac_within_catalogue=round(float(on_cat.mean()), 4),
        n_catalogue_detached=int(detached.sum()),
        corridor_capture_of_detached=round(float(on_cor[detached].mean()), 4) if detached.sum() else None,
        frac_of_detached_within_corridor=round(float(detached.mean() and on_cor[detached].mean()), 4)
        if detached.sum()
        else None,
        note="catalogue-detached = more than 3 km from every published fault, where an unmapped fault is the only available explanation",
    )
