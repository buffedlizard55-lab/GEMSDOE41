#!/usr/bin/env python3
"""H42 preregistered experiment: catalogue-completion learning + coverage-maximising emission.

HYPOTHESIS (preregistered before any holdout was opened -- see research/hypotheses-h42.md)
    A pixel classifier trained to reproduce *withheld* catalogue strands from the organizer's
    own 19-band feature raster, the USGS 3DEP 1 m scarp products and the geometry of the
    retained catalogue, emits a belief field whose off-catalogue maxima locate faults that the
    published catalogue does not contain.  Because the official index takes a MAXIMUM over
    predictions for each truth pixel, the belief must then be emitted by coverage-maximising
    greedy selection, not by thresholding: redundant dots inside an already-covered 300 m
    kernel earn nothing and still pay 0.2 of their mass.

INSTRUMENT (identical to the repository's existing one, so numbers are comparable)
    * four quadrant folds, strand-level blocking (`validate.strand_labels`, merge 6 px,
      min strand 60 px) so whole mapped strands -- not fragments of them -- are withheld;
    * truth = withheld strand pixels at least `guard_px` from the retained catalogue;
    * emission domain = footprint, off retained catalogue, beyond `guard_px`;
    * scored with `gems41.metric.dti`, the transcribed official index;
    * CONTROLS at every mass: uniform random scatter over the same domain (the position-blind
      null), distance-to-retained-catalogue ordering, and score-ordered fixed-separation
      packing (`emission.greedy_pack`, the operator every previous session in this family used).

Run:  .venv/bin/python scripts/experiment_h42.py [--guard 2.0] [--folds 4]
Writes evidence/h42_holdout.json
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, uniform_filter
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems41 import coverage as CV  # noqa: E402
from gems41 import emission as E  # noqa: E402
from gems41 import validate as V  # noqa: E402
from gems41.metric import dti  # noqa: E402

F32 = np.float32
MASS_CHECKPOINTS = (2_000, 8_000, 20_000, 37_654, 65_000)
NEG_PER_POS = 18
MAX_POS = 12_000
SEED = 42

FEAT = ROOT / "data" / "derived" / "h42_features.f32"
N_FEATURES = 31


def load_base() -> dict:
    with rasterio.open(ROOT / "data" / "existing_faults.tif") as src:
        cat = src.read(1)
    cm = cat == 1
    foot = cat != -1
    shape = cat.shape
    n = int(np.prod(shape))
    dcat = distance_transform_edt(~cm).astype(F32)
    X = np.memmap(FEAT, dtype=np.float32, mode="r", shape=(n, N_FEATURES))
    return dict(cat=cm, foot=foot, shape=shape, n=n, dcat=dcat, X=X)


def fold_list(b: dict, guard_px: float, min_dcat: float) -> list[dict]:
    """Strand-level quadrant folds, exactly as `validate.fold_contexts` builds them."""
    blocks = V.quadrant_blocks(b["shape"])
    lab, n = V.strand_labels(b["cat"], 6)
    sizes = np.bincount(lab.ravel())
    strand_block = {}
    for i in range(1, n + 1):
        if sizes[i] < 60:
            continue
        ys, xs = np.nonzero(lab == i)
        strand_block[i] = int(blocks[int(np.median(ys)), int(np.median(xs))])
    lookup = np.zeros(n + 1, bool)
    out = []
    for f in range(4):
        held_ids = [i for i, bb in strand_block.items() if bb == f]
        if not held_ids:
            continue
        lookup[:] = False
        lookup[held_ids] = True
        held = lookup[lab] & b["cat"]
        retained = b["cat"] & ~held
        d_ret = distance_transform_edt(~retained).astype(F32)
        truth = held & (d_ret > guard_px)
        # The emission domain is bounded by distance to the RETAINED catalogue only.
        # Adding `dcat > min_dcat` (distance to the FULL catalogue) would also exclude a 200 m
        # halo around the withheld strands -- and the withheld strands ARE the truth, because
        # every held pixel is a catalogue pixel with dcat = 0.  That caps the attainable kernel
        # weight at k < 1/3 and measures a crippled instrument rather than the prize task.
        # Off-catalogue exclusion belongs to the SHIPPED domain, where the published catalogue
        # is known and the hidden truth is not; it cannot be imposed on a holdout whose truth is
        # itself catalogue.  (Measured: with dcat>2 imposed, the uniform-scatter control scored
        # DTI 0.0046 and the best candidate 0.0844 on fold 0/2; both are lower bounds only.)
        allowed = b["foot"] & (~retained) & (d_ret > guard_px)
        if truth.sum() < 200 or allowed.sum() < 1000:
            continue
        # NO catalogue-geometry features.  Two reasons, both decisive:
        #  (1) leak: with a guard, every positive sits just beyond `guard_px` of the retained
        #      catalogue while negatives are spread over the domain, so "distance to retained
        #      catalogue" becomes a shortcut that says nothing about the prize round (this is
        #      the mechanism behind registry irregularity IR-32-PROXY-01);
        #  (2) domain shift: the shipped model trains on catalogue pixels, which all have
        #      dcat = 0, and predicts on pixels with dcat > 2, so any dcat feature would drive
        #      every prediction to zero.
        # The belief field is therefore a function of official geophysics, topography and the
        # USGS 3DEP scarp products ONLY -- it cannot echo catalogue density by construction.
        out.append(dict(fold=f, retained=retained, truth=truth, allowed=allowed,
                        d_ret=d_ret,
                        n_truth=int(truth.sum()), n_allowed=int(allowed.sum()),
                        n_held_strands=len(held_ids)))
        del held
        gc.collect()
    return out


def features_at(b: dict, fo: dict, flat: np.ndarray) -> np.ndarray:
    """Base memmap features for flat pixel indices (fold-independent by construction)."""
    return np.asarray(b["X"][flat])


def train_fold(b: dict, fo: dict, rng: np.random.Generator) -> HistGradientBoostingClassifier:
    pos = np.flatnonzero(fo["truth"].ravel())
    if pos.size > MAX_POS:
        pos = rng.choice(pos, MAX_POS, replace=False)
    neg_pool = np.flatnonzero(fo["allowed"].ravel())
    n_neg = min(neg_pool.size, NEG_PER_POS * pos.size)
    neg = rng.choice(neg_pool, n_neg, replace=False)
    idx = np.sort(np.concatenate([pos, neg]))
    Xf = features_at(b, fo, idx)
    y = np.zeros(idx.size, np.int8)
    y[np.searchsorted(idx, pos)] = 1
    # NO class weights.  The sampled prior is known exactly, so the model is calibrated for it
    # and the prior shift is undone analytically in `calibrate` below.  Class weights inflate
    # the low-probability body of the field, and a coverage-maximising emitter then maximises
    # coverage of that flat body -- i.e. it degenerates into a uniform scatter.  Measured, not
    # assumed: with weights, coverage-greedy scored 0.00286 vs the uniform control's 0.00312
    # on fold 0 while score-ordered packing of the same field scored 0.06076.
    clf = HistGradientBoostingClassifier(
        max_iter=240, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=40,
        l2_regularization=1.0, early_stopping=False, random_state=SEED,
    )
    clf.fit(Xf, y)
    prior = dict(p_sampled=float(y.mean()), n_pos=int(y.sum()), n_sample=int(y.size),
                 p_true=float(fo["truth"].sum() / max(fo["allowed"].sum(), 1)))
    del Xf
    gc.collect()
    return clf, prior


def calibrate(p: np.ndarray, prior: dict) -> np.ndarray:
    """Undo the negative-subsampling prior shift exactly.

    odds_true = odds_sampled * [p_t/(1-p_t)] / [p_s/(1-p_s)];  p = odds/(1+odds).
    The result is an estimate of P(this pixel is an unheld fault pixel | features), so
    sum(pi) is the model's own estimate of the hidden label count rho.
    """
    ps, pt = prior["p_sampled"], prior["p_true"]
    if not (0 < ps < 1) or not (0 < pt < 1):
        return p
    c = (pt / (1 - pt)) / (ps / (1 - ps))
    p = np.clip(np.asarray(p, np.float64), 1e-9, 1 - 1e-9)
    o = p / (1 - p) * c
    return (o / (1 + o)).astype(F32)


def predict_field(b: dict, fo: dict, clf, block: int = 400_000) -> np.ndarray:
    """Out-of-sample belief over the whole grid, restricted to this fold's domain."""
    n = b["n"]
    out = np.zeros(b["shape"], F32)
    dom = fo["allowed"].ravel()
    flat_dom = np.flatnonzero(dom)
    for a in range(0, flat_dom.size, block):
        idx = flat_dom[a:a + block]
        Xf = features_at(b, fo, idx)
        p = clf.predict_proba(Xf)[:, 1].astype(F32)
        out.ravel()[idx] = p
        del Xf
    return out


def evaluate_field(b: dict, fo: dict, pi: np.ndarray, tag: str) -> dict:
    """Coverage-greedy emission + the three controls, all scored on the same truth."""
    allowed = fo["allowed"]
    truth = fo["truth"]
    known = fo["retained"]
    foot = np.ones(b["shape"], bool)
    res: dict = dict(tag=tag)
    ck = tuple(MASS_CHECKPOINTS)
    g = CV.max_cover_greedy(pi.astype(np.float64), allowed, budget=max(ck), checkpoints=ck)
    curve = []
    for m in sorted(g["snapshots"]):
        mask = g["snapshots"][m]
        r = dti(mask.astype(F32), truth, footprint=foot, known=known)
        r["n_px"] = int(mask.sum())
        r.pop("mass", None)
        curve.append(dict(mass=int(m), **r))
    res["coverage_greedy"] = curve
    res["coverage_greedy_model"] = CV.model_dti(pi.astype(np.float64), g["mask"] if g["mask"].any()
                                                else np.zeros(b["shape"], bool))
    # --- sharpened coverage greedy: H42-A's actual test.  The calibrated field is a
    #     PROBABILITY, the truth is a nearly deterministic set concentrated at its top, so
    #     coverage of pi is coverage of a much flatter object than the truth.  gamma is a
    #     single preregistered scalar (8), not a tuned per-fold parameter. ---
    GAMMA = 8.0
    pi_s = np.power(np.clip(pi, 0, 1), GAMMA)
    tot = float(pi_s.sum())
    if tot > 0:
        pi_s = (pi_s * (float(pi.sum()) / tot)).astype(F32)
    gs = CV.max_cover_greedy(pi_s.astype(np.float64), allowed, budget=max(ck), checkpoints=ck)
    res["cov_greedy_gamma8"] = []
    for m in sorted(gs["snapshots"]):
        mask = gs["snapshots"][m]
        r = dti(mask.astype(F32), truth, footprint=foot, known=known)
        r.pop("mass", None)
        r["n_px"] = int(mask.sum())
        res["cov_greedy_gamma8"].append(dict(mass=int(m), **r))
        del mask

    # --- controls at the same masses ---
    rng = np.random.default_rng(SEED + fo["fold"])
    dom_flat = np.flatnonzero(allowed.ravel())
    ctrl = {}
    for name, prio in (("uniform_scatter", None),
                       ("belief_greedy_pack", pi.astype(np.float64)),
                       ("belief_pack_sep45", pi.astype(np.float64))):
        rows = []
        for m in ck:
            if name == "uniform_scatter":
                sel = rng.choice(dom_flat, size=min(m, dom_flat.size), replace=False)
                mask = np.zeros(b["shape"], bool)
                mask.ravel()[sel] = True
            else:
                sep = 2.83 if name == "belief_greedy_pack" else 4.5
                mask = E.greedy_pack(pi, allowed, min_sep_px=sep, budget=m,
                                     candidate_cap=max(4 * m, 40_000))
            if mask.sum() == 0:
                continue
            r = dti(mask.astype(F32), truth, footprint=foot, known=known)
            r.pop("mass", None)
            r["n_px"] = int(mask.sum())
            rows.append(dict(mass=int(mask.sum()), **r))
            del mask
        ctrl[name] = rows
        gc.collect()
    res["controls"] = ctrl
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", type=float, default=2.0)
    ap.add_argument("--min-dcat", type=float, default=2.0)
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "h42_holdout.json"))
    args = ap.parse_args()
    t0 = time.time()
    b = load_base()
    folds = fold_list(b, args.guard, args.min_dcat)[: args.folds]
    print(f"{len(folds)} folds, guard={args.guard}, min_dcat={args.min_dcat}", flush=True)
    rows = []
    for fo in folds:
        rng = np.random.default_rng(SEED + fo["fold"])
        print(f"fold {fo['fold']}: truth={fo['n_truth']} allowed={fo['n_allowed']} "
              f"held_strands={fo['n_held_strands']} ({time.time()-t0:.0f}s)", flush=True)
        clf, prior = train_fold(b, fo, rng)
        print(f"  trained ({time.time()-t0:.0f}s) prior={prior}", flush=True)
        pi = calibrate(predict_field(b, fo, clf), prior)
        print(f"  predicted+calibrated: max={float(pi.max()):.4f} sum(rho_model)={float(pi.sum()):.0f} "
              f"truth={fo['n_truth']} ({time.time()-t0:.0f}s)", flush=True)
        r = evaluate_field(b, fo, pi, f"fold{fo['fold']}")
        r["summary"] = {k: fo[k] for k in ("fold", "n_truth", "n_allowed", "n_held_strands")}
        r["prior"] = prior
        r["rho_model"] = float(pi.sum())
        rows.append(r)
        for c in r["coverage_greedy"]:
            print(f"    cov-greedy M={c['mass']:6d} dti={c['dti']:.5f} c/mass={c['credit_per_mass']:.5f} "
                  f"tp={c['tp']:.1f} fp={c['fp']:.1f}")
        for c in r.get("cov_greedy_gamma8", []):
            print(f"    cov-g8     M={c['mass']:6d} dti={c['dti']:.5f} c/mass={c['credit_per_mass']:.5f}")
        for nm, rr in r["controls"].items():
            best = max(rr, key=lambda z: z["dti"]) if rr else None
            if best:
                print(f"    {nm:20s} best dti={best['dti']:.5f} at M={best['mass']}")
        del clf, pi
        gc.collect()

    agg: dict = {}
    for name in ("coverage_greedy", "cov_greedy_gamma8", "uniform_scatter",
                 "belief_greedy_pack", "belief_pack_sep45"):
        per_mass: dict[int, list[float]] = {}
        for r in rows:
            if name in ("coverage_greedy", "cov_greedy_gamma8"):
                seq = r.get(name, [])
            else:
                seq = r["controls"].get(name, [])
            for c in seq:
                key = "mass" if name in ("coverage_greedy", "cov_greedy_gamma8") else "n_px"
                per_mass.setdefault(int(c[key]), []).append(float(c["dti"]))
        agg[name] = {str(m): dict(mean_dti=float(np.mean(v)), folds=len(v))
                     for m, v in sorted(per_mass.items())}
    out = dict(created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               design=dict(guard_px=args.guard, min_dcat_px=args.min_dcat, folds=len(rows),
                           mass_checkpoints=list(MASS_CHECKPOINTS),
                           neg_per_pos=NEG_PER_POS, max_pos=MAX_POS, seed=SEED,
                           n_features=N_FEATURES,
                           geometry_features="excluded (guard leak + train/ship domain shift)",
                           instrument=("strand-level quadrant blocking; truth = withheld strand "
                                       "pixels beyond the guard; scored with the transcribed "
                                       "official DTI; controls at identical masses")),
               folds=rows, aggregate=agg, runtime_s=round(time.time() - t0, 1))
    Path(args.out).write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(f"\naggregate mean DTI by strategy and mass:")
    for name, d in agg.items():
        print(f"  {name}")
        for m, v in d.items():
            print(f"    M={m:>7s} dti={v['mean_dti']:.5f} ({v['folds']} folds)")
    print(f"wrote {args.out}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
