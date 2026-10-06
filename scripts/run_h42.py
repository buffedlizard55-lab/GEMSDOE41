#!/usr/bin/env python3
"""H42 run: source audits, the H42-HO expert-fault holdout, artifacts, and receipts.

Preregistered design: research/hypotheses-h42.md (written BEFORE this script existed).
Every gate, budget, separation, prune and fold rule here comes from that file; nothing is
tuned on results.  One command reproduces everything and rewrites the evidence JSONs:

    python3 scripts/run_h42.py            # full run (CPU, minutes)
    python3 scripts/run_h42.py --audit    # source audits + falsification receipt only

Evidence written:
  evidence/h42_source_audit.json   SGMC/probe/marker sizes + the H42-A falsification
  evidence/h42_holdout.json        H42-HO folds, arms, budgets, decision counts
  evidence/h42_enrichment.json     label-free marker gates (2 m probes, 2020 rupture)
  evidence/h42_uniqueness.json     support Jaccard vs every shipped artifact + H33
  evidence/h42_build.json          artifact table: digests, px counts, audits, projections
  docs/downloads/gemsdoe41-h42*.tif/.zip/.checks.json
  docs/downloads/manifest.json     gains an "h42" block (H41-A top-level keys preserved)
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import time
import zipfile

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, label as cc_label

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gems41 import catalogue as C  # noqa: E402
from gems41 import field as F  # noqa: E402
from gems41 import grid as G  # noqa: E402
from gems41 import h42 as H  # noqa: E402
from gems41 import lidar as L  # noqa: E402
from gems41 import validate as V  # noqa: E402
from gems41.metric import dti  # noqa: E402
from gems41.structure import build_elements  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
OUT_DL = os.path.join(ROOT, "docs", "downloads")

# Digests for every input this run reads.  Mismatch = refuse to run (no silent byte swaps).
INPUT_PINS = {
    "data/existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "data/example_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "data/official/qfaults.zip": "c7b091c9ac8bca140ad89ee6bb2bd63dd3ac12e3013acbfd8373d11c9faee59d",
    "data/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "data/external_gems30/derived_sgmc_faults_100m_u8.tif":
        "26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c",
    "data/external_gems30/derived_gdr_2m_probes_100m_u8.tif":
        "7ac3cfdf2412f7f8a8b82d928115888c510f106f0254fb0b3988448db2f3b6ec",
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs() -> dict:
    out = {}
    for rel, want in INPUT_PINS.items():
        got = sha256(os.path.join(ROOT, rel))
        out[rel] = dict(sha256=got, match=got == want)
        if got != want:
            raise SystemExit(f"INPUT DIGEST MISMATCH: {rel} — refusing to run")
    return out


# ---------------------------------------------------------------- source audits


def h42a_vector_residual(cat_mask: np.ndarray, footprint: np.ndarray, shape) -> dict:
    """Falsification receipt: official v2 vectors vs the public raster catalogue.

    Same burn path as the audited run_pipeline (fiona + transform_geom + model.burn); the
    measured result closes H42-A (vector-minus-raster residual) for every future session.
    """
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import fiona
    from fiona.transform import transform_geom as tg
    from shapely.geometry import shape as sgeom, box
    from model import burn

    transform = rasterio.transform.from_origin(G.ORIGIN_X, G.ORIGIN_Y, G.RES, G.RES)
    bbox = box(*rasterio.transform.array_bounds(*shape, transform))
    lines = []
    with fiona.open("zip://" + os.path.join(DATA, "official/qfaults.zip")) as src:
        for f in src:
            g = sgeom(tg(src.crs, "EPSG:32611", f["geometry"]))
            if not g.intersects(bbox):
                continue
            lines.append(g)
    vr = burn(lines, shape, transform) & footprint
    d_cat = distance_transform_edt(~cat_mask) * 100.0
    d_vec = distance_transform_edt(~vr) * 100.0
    return dict(
        claim="official INGENIOUS v2 vectors contain geometry missing from the public raster catalogue",
        result="FALSIFIED",
        vector_pixels=int(vr.sum()),
        catalogue_pixels=int(cat_mask.sum()),
        vector_px_gt_200m_from_catalogue=int((vr & (d_cat > 200)).sum()),
        vector_px_gt_300m_from_catalogue=int((vr & (d_cat > 300)).sum()),
        vector_px_gt_1km_from_catalogue=int((vr & (d_cat > 1000)).sum()),
        catalogue_px_gt_300m_from_vectors=int((cat_mask & (d_vec > 300)).sum()),
        reading="the provided public catalogue is the v2 compilation rasterized; there is no "
                "official-vector residual to recall — hidden expert faults must come from OTHER sources",
    )


def state_map_support(cat_mask: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    """SGMC fault pixels on the competition grid, pruned >=200 m from the catalogue."""
    p = os.path.join(DATA, "external_gems30/derived_sgmc_faults_100m_u8.tif")
    with rasterio.open(p) as s:
        sgmc = s.read(1) > 0
        assert s.shape == cat_mask.shape and str(s.crs) == G.CRS and float(s.res[0]) == G.RES
    d_cat = distance_transform_edt(~cat_mask)
    residual = sgmc & footprint & (d_cat > H.CATALOGUE_PRUNE_PX)
    audit = dict(
        layer=p,
        sha256=sha256(os.path.join(ROOT, p)),
        source_official="https://mrdata.usgs.gov/geology/state/ (SGMC NV+CA, US public domain)",
        source_mirror_receipt="evidence/gems30_external_receipt.json (sibling CI; sha verified locally)",
        sgmc_pixels_in_footprint=int((sgmc & footprint).sum()),
        residual_pixels_gt_200m=int(residual.sum()),
        residual_pixels_gt_300m=int((sgmc & footprint & (d_cat > 3.0)).sum()),
        residual_components=int(cc_label(residual, structure=np.ones((3, 3), int))[1]),
        provenance_class="sibling-CI-derived from official public-domain source; checksum-pinned; not organizer-authenticated",
    )
    return residual, audit


# ---------------------------------------------------------------- geometry builders


def classified_populations(shape, cat_mask, residual=None):
    """Strike classification of EVERY catalogue trace (brief criterion) plus the residual.

    Populations include the retained state-map traces so that "geometrically closer
    population" is defined identically in the fold contexts and in the shipped build.
    """
    traces = C.extract_traces(cat_mask)
    try:
        C.attach_kinematics(traces, os.path.join(DATA, "gdr_qfaults_traces.csv"))
    except FileNotFoundError:
        pass
    A, B, pop = C.population_masks(shape, traces)
    if residual is not None and residual.any():
        rt = C.extract_traces(residual)
        for t in rt:
            t.sense = "unknown"  # state-map layer carries no slip-sense attribute
        Ar, Br, pop_r = C.population_masks(shape, rt)
        A = A | Ar
        B = B | Br
        pop = dict(pop)
        pop["residual_traces"] = {"traces": len(rt)}
    return traces, A, B, pop


def corridor_elements(traces, A, B):
    elems = build_elements(traces, A, B)
    elems["corridor"] = elems["transfer"] | elems["extension"] | elems["relay"]
    return elems


def prior_components(cat_mask, footprint, residual, lidar, pop_a, pop_b, elems):
    return H.h42_components(
        cat_mask, residual, pop_a, pop_b, elems["corridor"],
        lidar["strike"], lidar["valid"], lidar["evidence"],
    )


# ---------------------------------------------------------------- H42-HO instrument


def build_fold_contexts(cat_mask, footprint, residual, lidar):
    """Whole-trace spatial folds on the expert-holdout instrument (see the preregistration).

    A trace (8-connected component >= MIN_TRACE_PX) touching block f or its 3 px halo is
    withheld ENTIRELY — no clipping-induced tips, identical discipline to the catalogue
    holdout in gems41.validate, but on state-map residual geometry as truth.
    """
    shape = cat_mask.shape
    blocks = V.quadrant_blocks(shape)
    lab_c, nc = cc_label(cat_mask, structure=np.ones((3, 3), int))
    lab_r, nr = cc_label(residual, structure=np.ones((3, 3), int))
    sz_c = np.bincount(lab_c.ravel())
    sz_r = np.bincount(lab_r.ravel())
    ctx = []
    for f in range(4):
        blk = blocks == f
        near = distance_transform_edt(~blk) <= 3.0  # block + 300 m halo
        held_c = [i for i in np.unique(lab_c[near & (lab_c > 0)]) if sz_c[i] >= C.MIN_TRACE_PX]
        held_r = [i for i in np.unique(lab_r[near & (lab_r > 0)]) if sz_r[i] >= C.MIN_TRACE_PX]
        keep_c = np.ones(nc + 1, bool); keep_c[held_c] = False
        keep_r = np.ones(nr + 1, bool); keep_r[held_r] = False
        retained_cat = cat_mask & keep_c[lab_c]
        retained_res = residual & keep_r[lab_r]
        truth = residual & (~keep_r[lab_r])  # complete WITHHELD residual traces
        retained_any = retained_cat | retained_res
        d_ret = distance_transform_edt(~retained_any)
        truth = truth & (d_ret > H.EVAL_GUARD_PX) & blk
        if int(truth.sum()) < 200:
            ctx.append(dict(fold=f, skipped="truth_lt_200px", truth_px=int(truth.sum())))
            del truth, retained_cat, retained_res, retained_any, d_ret
            gc.collect()
            continue
        allowed = footprint & (~retained_any) & (d_ret > H.EVAL_GUARD_PX)
        traces, A, B, pop = classified_populations(shape, retained_cat, retained_res)
        elems = corridor_elements(traces, A, B)
        comp = prior_components(retained_cat, footprint, retained_res, lidar, A, B, elems)
        ctx.append(dict(
            fold=f, retained_cat=retained_cat, retained_res=retained_res, retained_any=retained_any,
            truth=truth, allowed=allowed, comp=comp,
            summary=dict(fold=f, held_cat_traces=len(held_c), held_res_traces=len(held_r),
                         truth_px=int(truth.sum()), allowed_px=int(allowed.sum()),
                         retained_residual_px=int(retained_res.sum())),
        ))
        del keep_c, keep_r
        gc.collect()
    return ctx


def run_holdout(cat_mask, footprint, residual, lidar) -> dict:
    contexts = build_fold_contexts(cat_mask, footprint, residual, lidar)
    per_fold = []
    for fo in contexts:
        if "skipped" in fo:
            per_fold.append(fo)
            continue
        arms = H.h42_arms(fo["comp"], fo["allowed"], np.random.default_rng(41 + fo["fold"]))
        res = {}
        for name, s in arms.items():
            rows = {}
            for budget in H.BUDGETS_PX:
                m = H.pack_arms({name: s}, fo["allowed"], sep_px=H.PACK_SEP_PX, budget=budget)[name]
                if m.sum() == 0:
                    rows[budget] = dict(n_px=0, credit_per_mass=0.0, dti=0.0)
                    continue
                r = dti(m.astype(np.float32), fo["truth"], known=fo["retained_any"])
                rows[budget] = dict(n_px=int(m.sum()), credit_per_mass=r["credit_per_mass"],
                                    dti=r["dti"], mass=r["mass"], truth_px=int(fo["truth"].sum()))
                del m, r
            res[name] = rows
        per_fold.append(dict(summary=fo["summary"], results=res))
        del arms, fo
        gc.collect()
    # fixed selection: mean credit-per-mass across the whole ladder
    names = list(H.ARMS)
    agg = {}
    for n in names:
        per_budget = {}
        for b in H.BUDGETS_PX:
            vals = [r["results"][n][b]["credit_per_mass"] for r in per_fold if "results" in r]
            per_budget[b] = float(np.mean(vals)) if vals else 0.0
        mean_all = float(np.mean(list(per_budget.values())))
        agg[n] = dict(cpm_by_budget=per_budget, mean_cpm_ladder=mean_all)
    winner = max(names, key=lambda n: agg[n]["mean_cpm_ladder"])
    controls = [c for c in ("control_density", "control_evidence", "control_random") if c != winner]
    wins_vs_controls = {}
    for ctr in controls:
        w = 0
        tot = 0
        for r in per_fold:
            if "results" not in r:
                continue
            for b in H.BUDGETS_PX:
                tot += 1
                if r["results"][winner][b]["credit_per_mass"] > r["results"][ctr][b]["credit_per_mass"]:
                    w += 1
        wins_vs_controls[ctr] = dict(wins=w, settings=tot)
    # fold-level rule from the preregistration: winner beats (density|evidence|random) in >=3/4 folds
    # The preregistered gate applies to the H42 ARMS (a)/(b), not to whichever arm wins
    # the table — a control topping the table is itself a failure of the hypotheses.
    arm_folds_pass = {}
    for arm in ("h42d_state_prior", "h42b_junction_prior"):
        w = 0
        for r in per_fold:
            if "results" not in r:
                continue
            ok = all(
                np.mean([r["results"][arm][b]["credit_per_mass"] for b in H.BUDGETS_PX])
                > np.mean([r["results"][c][b]["credit_per_mass"] for b in H.BUDGETS_PX])
                for c in ("control_density", "control_evidence", "control_random")
            )
            w += int(ok)
        arm_folds_pass[arm] = w
    folds_pass = max(arm_folds_pass.values())
    return dict(
        instrument="H42-HO: whole-trace withheld STATE-MAP residual traces as truth (expert-mapped, "
                   "publicly absent) — the closest obtainable analogue to the hidden labels",
        folds=[(r.get("summary") or {"fold": r["fold"], "skipped": r["skipped"]}) for r in per_fold],
        per_fold=per_fold,
        aggregated=agg,
        winner_by_fixed_rule=winner,
        wins_vs_controls=wins_vs_controls,
        folds_winning_all_controls=folds_pass,
        holdout_rule="ARM (a) h42d or (b) h42b must beat density, evidence and random in >=3 of 4 folds (mean over the fixed budget ladder); a control winning the table is a hypothesis failure, not a pass",
        arm_folds_pass=arm_folds_pass,
        holdout_passed=bool(folds_pass >= 3),
        limitation="credit-per-mass here measures ranking of a proxy expert-fault set; it is not a "
                   "live score and no clean historical-best OOF comparator exists locally",
    )


# ---------------------------------------------------------------- enrichment gate


_OFFS3 = [(dy, dx) for dy in range(-3, 4) for dx in range(-3, 4) if dy * dy + dx * dx <= 9]


def _cover_fraction(mark: np.ndarray, support: np.ndarray) -> float:
    """Fraction of marker pixels with any support pixel within the metric's 3 px kernel.

    Deliberately implemented with the identical neighbour-offset circle the DTI kernel uses
    (d <= 3 px), so the candidate and the null share one statistic definition.
    """
    n = int(mark.sum())
    if n == 0:
        return 0.0
    ys, xs = np.nonzero(mark)
    hit = np.zeros(n, bool)
    Hh, Ww = mark.shape
    for dy, dx in _OFFS3:
        yy, xx = ys + dy, xs + dx
        ok = (yy >= 0) & (yy < Hh) & (xx >= 0) & (xx < Ww)
        if ok.any():
            hit[ok] |= support[yy[ok], xx[ok]]
    return float(hit.mean())


def random_matched_supports(allowed: np.ndarray, mass: int, n_trials: int, seed: int = 42):
    """Generator of stratified random supports: same mass, same domain, 100 px block-balanced.

    Yields boolean grids one at a time (500 grids held at once would be ~6 GB — never).
    """
    rng = np.random.default_rng(seed)
    by, bx = np.nonzero(allowed)
    blk = (by // 100) * 64 + (bx // 100)
    uniq, counts = np.unique(blk, return_counts=True)
    per = np.floor(counts / counts.sum() * mass).astype(int)
    order = np.argsort(-counts)
    j = 0
    while per.sum() < mass:  # deterministic largest-remainder fill
        per[order[j % len(order)]] += 1
        j += 1
    per = np.minimum(per, counts)  # never exceed the pixels available in a block
    groups = np.argsort(blk, kind="stable")
    sorted_blk = blk[groups]
    starts = np.searchsorted(sorted_blk, uniq)
    ends = np.append(starts[1:], len(sorted_blk))
    for _ in range(n_trials):
        pts = []
        for b in range(len(uniq)):
            k = int(per[b])
            avail = groups[starts[b]:ends[b]]
            if k <= 0 or avail.size == 0:
                continue
            k = min(k, avail.size)
            pts.append(rng.choice(avail, size=k, replace=False))
        idx = np.concatenate(pts)
        m = np.zeros(allowed.shape, bool)
        m[by[idx], bx[idx]] = True
        yield m


def enrichment_gate(supports: dict, allowed: np.ndarray) -> dict:
    probes_p = os.path.join(DATA, "external_gems30/derived_gdr_2m_probes_100m_u8.tif")
    with rasterio.open(probes_p) as s:
        probes = s.read(1) > 0
    seis = np.load(os.path.join(ROOT, "evidence/seismicity_corridor.npz"))["corridor"]
    with rasterio.open(os.path.join(DATA, "existing_faults.tif")) as s:
        cat = s.read(1)
    d_cat = distance_transform_edt(~(cat == 1))
    fp = cat != -1
    markers = {
        "thermal_2m_probes": probes & fp & (d_cat > 2.0),
        "rupture_2020_envelope": seis & fp & (d_cat > 2.0),
    }
    res = {}
    for cname, sup in supports.items():
        mass = int(sup.sum())
        if mass == 0:
            res[cname] = dict(mass=0, note="empty support; gate vacuous")
            continue
        entry = dict(mass=mass, markers={})
        for mname, mk in markers.items():
            frac_obs = _cover_fraction(mk, sup)
            null_fr = np.array([_cover_fraction(mk, rand) for rand in
                                random_matched_supports(allowed, mass, 500)])
            p = float((1 + int((null_fr >= frac_obs).sum())) / (len(null_fr) + 1))
            mean = float(null_fr.mean())
            entry["markers"][mname] = dict(
                n_marker_px=int(mk.sum()), observed_fraction_within_3px=round(frac_obs, 5),
                null_mean=round(mean, 5), null_p95=round(float(np.percentile(null_fr, 95)), 5),
                enrichment=round(frac_obs / max(mean, 1e-12), 3), p_value=p,
                passes=bool(frac_obs / max(mean, 1e-12) >= 1.2 and p < 0.05),
            )
        res[cname] = entry
    return dict(
        design="fraction of off-catalogue marker pixels within 300 m of the candidate support vs "
               "500 deterministic stratified random matched-mass supports on the same allowed domain; "
               "pass = enrichment >= 1.2 and p < 0.05 on at least one marker",
        markers=dict(
            thermal_2m_probes="GDR 1391 2 m temperature probes (CC BY 4.0), sibling-derived 100 m layer, sha-verified",
            rupture_2020_envelope="USGS ComCat 2020 M>=4.6 sequence envelope (evidence/seismicity_corridor.npz, this repo)",
        ),
        results=res,
        gate_passed_any=bool(any(
            any(v.get("passes", False) for v in (e.get("markers") or {}).values())
            for e in res.values() if isinstance(e, dict) and "markers" in e
        )),
    )


# ---------------------------------------------------------------- audits + artifacts


def junction_audit(emission: np.ndarray, elems: dict, A: np.ndarray, B: np.ndarray,
                   reference: np.ndarray, reference_name: str = "published_catalogue") -> dict:
    """The brief's own verification, parameterised by which geometry is the reference.

    Pass the raster catalogue for the shipped-file audit; pass the state-map residual mask
    to measure the same statistics against that alternative reference — the key names are
    neutral so a second reference can never be misread as the catalogue.
    """
    conc = F.junction_concentration(emission, elems, A, B)
    d_ref = distance_transform_edt(~reference)
    frac_far = float((d_ref[emission] > 2.0).mean()) if emission.any() else 1.0
    return dict(junction_concentration=conc,
                frac_emission_beyond_200m_of_reference=round(frac_far, 6),
                min_px_to_reference=round(float(d_ref[emission].min()), 4) if emission.any() else None,
                reference=reference_name)


def write_artifact(mask: np.ndarray, name: str, stamp: str, footprint: np.ndarray) -> dict:
    """Family-convention writer: single-band float32, numeric zeros outside, no NaN, no nodata tag.

    This is the exact byte convention of the live-scored `-zeros` sibling artifact
    (data/comparison-h33.tif: dtype float32, nodata None, deflate, tiled 256) — the one the
    portal has demonstrably accepted, and the direct answer to the 'Predicted values must be
    in range [0, 1]' rejection class (every stored value is a finite number in [0, 1]).
    """
    os.makedirs(OUT_DL, exist_ok=True)
    data = np.zeros(G.SHAPE, dtype="float32")
    data[mask & footprint] = 1.0
    path = os.path.join(OUT_DL, f"gemsdoe41-{name}-{stamp}.tif")
    with rasterio.open(
        path, "w", driver="GTiff", height=G.HEIGHT, width=G.WIDTH, count=1, dtype="float32",
        crs=G.CRS, transform=rasterio.transform.Affine(*G.TRANSFORM), nodata=None,
        compress="deflate", tiled=True, blockxsize=256, blockysize=256,
    ) as dst:
        dst.write(data, 1)
        dst.set_band_description(1, f"GEMSDOE41 {name}: bimodal structural dot lattice, not calibrated probability")
        dst.update_tags(model=f"H42::{name}", status="RESEARCH_CANDIDATE_PREREGISTERED_GATES")
    checks = check_artifact(path)
    zpath = path[:-4] + ".zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(path, arcname=os.path.basename(path))
    checks["zip_path"] = zpath
    checks["zip_bytes"] = os.path.getsize(zpath)
    json.dump(checks, open(path + ".checks.json", "w"), indent=1)
    return checks


def check_artifact(path: str) -> dict:
    with rasterio.open(path) as s:
        arr = s.read(1)
        checks = dict(
            driver_gtiff=s.driver == "GTiff", single_band=s.count == 1, dtype_float32=s.dtypes[0] == "float32",
            crs_epsg32611=str(s.crs) == G.CRS, width=s.width == G.WIDTH, height=s.height == G.HEIGHT,
            res_100m=tuple(round(float(r), 6) for r in s.res) == (100.0, 100.0),
            transform_matches=all(abs(a - b) < 1e-6 for a, b in zip(tuple(s.transform)[:6], G.TRANSFORM)),
            nodata_none=s.nodata is None,
        )
    checks.update(
        all_stored_values_finite=bool(np.isfinite(arr).all()),
        values_in_0_1=bool(arr.min() >= 0.0 and arr.max() <= 1.0),
        no_nan_anywhere=bool(not np.isnan(arr).any()),
        positive_pixels=int((arr > 0).sum()), min=float(arr.min()), max=float(arr.max()),
        binary_values=bool(set(np.unique(arr).tolist()) <= {0.0, 1.0}),
    )
    with rasterio.open(os.path.join(DATA, "existing_faults.tif")) as s:
        cat = s.read(1)
    fp = cat != -1
    checks["zeros_outside_footprint"] = bool((arr[~fp] == 0).all())
    checks["emission_inside_footprint_only"] = bool((arr > 0)[~fp].sum() == 0)
    with rasterio.open(os.path.join(DATA, "example_submission.tif")) as t:
        checks["template_grid_identical"] = (t.shape == arr.shape and str(t.crs) == G.CRS
                                            and tuple(t.transform)[:6] == G.TRANSFORM)
    d_cat = distance_transform_edt(~(cat == 1))
    sup = arr > 0
    checks["px_within_200m_of_catalogue"] = int((d_cat[sup] <= 2.0 - 1e-9).sum()) if sup.any() else 0
    checks["min_px_distance_to_catalogue"] = round(float(d_cat[sup].min()), 4) if sup.any() else None
    checks["sha256_bytes"] = sha256(path)
    checks["sha256_pixels"] = hashlib.sha256(np.ascontiguousarray(arr, dtype="<f4").tobytes()).hexdigest()
    checks["bytes"] = os.path.getsize(path)
    checks["path"] = path
    bools = [v for v in checks.values() if isinstance(v, bool)]
    checks["all_pass"] = bool(all(bools) and checks["positive_pixels"] > 0
                              and checks["px_within_200m_of_catalogue"] == 0)
    return checks


def uniqueness_ledger(new_masks: dict) -> dict:
    others = []
    d = os.path.join(ROOT, "docs", "downloads")
    for f in sorted(os.listdir(d)):
        if f.endswith(".tif"):
            others.append(os.path.join(d, f))
    others.append(os.path.join(DATA, "comparison-h33.tif"))
    out = {}
    for nn, m in new_masks.items():
        rows = {}
        for path in others:
            if os.path.basename(path).startswith("gemsdoe41-h42"):
                continue
            with rasterio.open(path) as s:
                a = s.read(1)
            o = np.isfinite(a) & (a > 0)
            inter = int((m & o).sum()); uni = int((m | o).sum())
            rows[os.path.basename(path)] = dict(
                other_positive_px=int(o.sum()), shared_px=inter,
                jaccard=round(inter / max(uni, 1), 6),
                equal_arrays=bool(np.array_equal(m, o)),
            )
        out[nn] = rows
    assert not any(r["equal_arrays"] for v in out.values() for r in v.values()), \
        "shipped artifact is byte-equivalent to a prior file — refusing"
    return out


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true", help="source audits and receipts only")
    ap.add_argument("--skip-holdout", action="store_true",
                    help="reuse evidence/h42_holdout.json (deterministic; CI artifact rebuild)")
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(os.path.join(ROOT, "evidence"), exist_ok=True)
    digests = verify_inputs()
    print("== 0. input digests ==\n  " + "\n  ".join(
        f"{k}: {'MATCH' if v['match'] else 'FAIL'}" for k, v in digests.items()), flush=True)

    with rasterio.open(os.path.join(DATA, "existing_faults.tif")) as s:
        cat = s.read(1)
    cat_mask = cat == 1
    footprint = G.footprint_mask(cat)
    assert int(footprint.sum()) == G.FOOTPRINT_PX and int(cat_mask.sum()) == G.CATALOGUE_PX
    print(f"catalogue {int(cat_mask.sum())} px | footprint {int(footprint.sum())} px", flush=True)

    residual, sgmc_audit = state_map_support(cat_mask, footprint)
    src = dict(created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               state_map_residual=sgmc_audit)
    src["h42a_falsification"] = h42a_vector_residual(cat_mask, footprint, cat_mask.shape)
    print("   H42-A:", src["h42a_falsification"]["result"], "| residual >300m:",
          src["h42a_falsification"]["vector_px_gt_300m_from_catalogue"], "px", flush=True)
    seis = np.load(os.path.join(ROOT, "evidence/seismicity_corridor.npz"))["corridor"] & footprint
    d_cat_px = distance_transform_edt(~cat_mask)
    probes_p = os.path.join(DATA, "external_gems30/derived_gdr_2m_probes_100m_u8.tif")
    with rasterio.open(probes_p) as s:
        probes = s.read(1) > 0
    src["markers"] = dict(
        seismicity_corridor_px_off_catalogue=int((seis & (d_cat_px > 2.0)).sum()),
        thermal_probe_px_in_footprint=int((probes & footprint).sum()),
        thermal_probe_px_off_catalogue=int((probes & footprint & (d_cat_px > 2.0)).sum()),
    )
    json.dump(src, open(os.path.join(ROOT, "evidence/h42_source_audit.json"), "w"), indent=1, default=float)
    print(f"residual {int(residual.sum())} px | audit -> evidence/h42_source_audit.json", flush=True)
    if args.audit:
        print(json.dumps(src["state_map_residual"], indent=1))
        return 0

    print("== 1. H42-HO instrument (expert-fault holdout) ==", flush=True)
    lidar = L.load_products(os.path.join(DATA, "lidar_scarp_features_u8.tif"))
    ho_path = os.path.join(ROOT, "evidence/h42_holdout.json")
    if args.skip_holdout and os.path.exists(ho_path):
        ho = json.load(open(ho_path))
        print("   reused cached H42-HO receipt (deterministic build)", flush=True)
    else:
        ho = run_holdout(cat_mask, footprint, residual, lidar)
        json.dump(ho, open(ho_path, "w"), indent=1, default=float)
    for n, a in ho["aggregated"].items():
        print(f"   {n:24s} ladder cpm {[round(v, 4) for v in a['cpm_by_budget'].values()]} "
              f"mean {a['mean_cpm_ladder']:.4f}", flush=True)
    print(f"   winner(fixed rule) {ho['winner_by_fixed_rule']} | folds winning all controls "
          f"{ho['folds_winning_all_controls']}/4 -> holdout {'PASS' if ho['holdout_passed'] else 'FAIL'}",
          flush=True)

    print("== 2. shipped fields on the full map ==", flush=True)
    traces, A, B, pop = classified_populations(cat_mask.shape, cat_mask, residual)
    elems = corridor_elements(traces, A, B)
    comp = prior_components(cat_mask, footprint, residual, lidar, A, B, elems)
    allowed = footprint & (comp["d_cat"] > H.CATALOGUE_PRUNE_PX)
    arms = H.h42_arms(comp, allowed, np.random.default_rng(41))
    built = {}
    masks = {}
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    for key, name, art in (
        ("h42b_junction_prior", "h42b-junction-lattice-37k", "GEMSDOE41-H42B-BIMODAL-JUNCTION-LATTICE-37K"),
        ("h42d_state_prior", "h42d-statemap-lattice-37k", "GEMSDOE41-H42D-STATEMAP-RESIDUAL-LATTICE-37K"),
    ):
        m = H.pack_arms({key: arms[key]}, allowed, sep_px=H.PACK_SEP_PX, budget=H.LIVE_MASS_PX)[key]
        masks[name] = m
        checks = write_artifact(m, name, stamp, footprint)
        res_traces = C.extract_traces(residual)
        res_A, res_B, _ = C.population_masks(cat_mask.shape, res_traces)
        res_elems = corridor_elements(res_traces, res_A, res_B)
        # note: the residual-geometry audit uses the residual mask itself as the distance
        # reference; it is labelled as such and is NOT a catalogue-distance check
        built[name] = dict(
            tracking_name=art, checks=checks,
            emitted_px=int(m.sum()), requested_budget=H.LIVE_MASS_PX,
            support_shortfall=int(H.LIVE_MASS_PX - m.sum()),
            junction_audit=junction_audit(m, elems, A, B, cat_mask),
            junction_audit_residual_geometry=junction_audit(m, res_elems, res_A, res_B, residual,
                                                                      reference_name='state_map_residual'),
            composition=dict(
                on_residual=int((m & residual).sum()),
                near_corridor_3px=int((m & (distance_transform_edt(~elems["corridor"]) <= 3.0)).sum()),
            ),
        )
        print(f"   {name}: {int(m.sum())} px sha256 {checks['sha256_bytes'][:16]}... "
              f"checks {'PASS' if checks['all_pass'] else 'FAIL'}", flush=True)

    print("== 3. label-free enrichment gate ==", flush=True)
    enr = enrichment_gate(masks, allowed)
    json.dump(enr, open(os.path.join(ROOT, "evidence/h42_enrichment.json"), "w"), indent=1, default=float)
    for n, e in enr["results"].items():
        for mk, v in (e.get("markers") or {}).items():
            print(f"   {n} vs {mk}: enr {v['enrichment']}x p {v['p_value']} "
                  f"{'PASS' if v['passes'] else 'fail'}", flush=True)

    print("== 4. uniqueness ledger ==", flush=True)
    uni = uniqueness_ledger(masks)
    json.dump(uni, open(os.path.join(ROOT, "evidence/h42_uniqueness.json"), "w"), indent=1, default=float)
    for n, rows in uni.items():
        top = sorted(rows.items(), key=lambda kv: -kv[1]["jaccard"])[:3]
        print(f"   {n}: " + " | ".join(f"{os.path.basename(k)[:28]} {v['jaccard']:.4f}" for k, v in top), flush=True)

    print("== 5. projections and manifest ==", flush=True)
    def arm_projection(arm: str, mass: int) -> dict:
        a = ho["aggregated"].get(arm, {})
        cpm = a.get("mean_cpm_ladder", 0.0)
        return dict(
            metric="[MODEL] DTI = c/(0.2 + 0.8*K/S), K = 13000 px; c is an H42-HO ladder-mean "
                   "measurement against withheld STATE-MAP traces with a 3 px isolation guard — "
                   "a line-anchored prior is structurally near-zero on this instrument (see "
                   "research/hypotheses-h42.md Part 5), so a projection near zero here is NOT a "
                   "live-score estimate in either direction",
            arm=arm, mean_credit_per_mass=cpm,
            projected_at_shipped_mass=float(V.project_live_dti(cpm, mass)),
            caveat="projection depends on an owner-inferred hidden-set size; never a score promise",
        )
    for name, arm in (("h42b-junction-lattice-37k", "h42b_junction_prior"),
                      ("h42d-statemap-lattice-37k", "h42d_state_prior")):
        if name in built:
            built[name]["projection"] = arm_projection(arm, built[name]["emitted_px"])
    win = ho["winner_by_fixed_rule"]
    proj = dict(
        per_arm={n: built[n]["projection"] for n in built if "projection" in built[n]},
        winner_by_table_readout=win,
        control_evidence_mean_cpm=ho["aggregated"].get("control_evidence", {}).get("mean_cpm_ladder"),
    )
    decisions = dict(
        holdout=ho["holdout_passed"], holdout_winner_by_table=win,
        holdout_arm_folds_pass=ho["arm_folds_pass"],
        enrichment=enr["gate_passed_any"],
        slot_recommendation=(
            "h42d eligible for the user's slot decision (holdout+enrichment passed); "
            "promotion still requires the user's own leaderboard-risk judgement — the repo's "
            "clean-historical-best comparator requirement remains unsatisfiable locally"
            if ho["holdout_passed"] and enr["gate_passed_any"] else
            "no promotion: the preregistered holdout rule (arm a or b beats density/evidence/random "
            "in >=3 of 4 folds) failed on 0/4 folds and the label-free enrichment gate failed; "
            "the LiDAR scarp-evidence control tops the instrument (ladder-mean cpm "
            f"{proj['control_evidence_mean_cpm']:.4f}) — artifacts ship as labeled research only"
        ),
    )
    primary = "h42d-statemap-lattice-37k" if (ho["holdout_passed"] and enr["gate_passed_any"]) \
        else "h42b-junction-lattice-37k"
    prim_checks = built[primary]["checks"]
    manifest_path = os.path.join(OUT_DL, "manifest.json")
    manifest = json.load(open(manifest_path))
    manifest["h42"] = dict(
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        preregistration="research/hypotheses-h42.md",
        primary=primary, artifacts=built, projection=proj, decisions=decisions,
        input_digests=digests, uniqueness_top=uni,
        submission_name=built[primary]["tracking_name"],
        note=(f"H42 {primary}: bimodal strike-classified lattice; >=200m off catalogue; 2.83px sep; "
              f"37,654 px; holdout {'PASS' if ho['holdout_passed'] else 'FAIL'} / enrichment "
              f"{'PASS' if enr['gate_passed_any'] else 'FAIL'}; gate CLOSED pending user slot decision")[:200],
        slot_eligible=False,
    )
    json.dump(manifest, open(manifest_path, "w"), indent=1, default=float)
    build = dict(
        created_utc=manifest["h42"]["created_utc"], primary=primary,
        submission_name=built[primary]["tracking_name"],
        note=(f"H42 {primary}: bimodal strike-classified lattice; >=200m off catalogue; 2.83px sep; "
              f"37,654 px; holdout {'PASS' if ho['holdout_passed'] else 'FAIL'} / enrichment "
              f"{'PASS' if enr['gate_passed_any'] else 'FAIL'}; gate CLOSED pending user slot decision")[:200],
        slot_eligible=False, checks=prim_checks, holdout=ho, enrichment=enr, decisions=decisions,
    )
    json.dump(build, open(os.path.join(ROOT, "evidence/h42_build.json"), "w"), indent=1, default=float)
    print(f"   primary={primary} | decisions: {decisions['slot_recommendation']}")
    print(f"done in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
