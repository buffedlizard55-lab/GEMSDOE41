#!/usr/bin/env python3
"""Render the H42 field for the site: hillshade-style relief, catalogue in grey, emission in orange."""
from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import gaussian_filter, zoom  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
F32 = np.float32


def rb(p: Path, b: int = 1) -> np.ndarray:
    with rasterio.open(p) as s:
        a = s.read(b).astype(F32)
    a[~np.isfinite(a)] = 0.0
    a[a < -1e37] = 0.0
    return a


def main() -> None:
    with rasterio.open(ROOT / "data/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    elev = gaussian_filter(rb(ROOT / "data/training_features.tif", 12), 2.0)
    cat = rb(ROOT / "data/existing_faults.tif") > 0.5
    emis = rb(ROOT / "docs/downloads/gems41-h42-submission-primary.tif") > 0
    step = 3

    def pool(a: np.ndarray, how: str = "max") -> np.ndarray:
        h, w = a.shape
        h3, w3 = (h // step) * step, (w // step) * step
        blk = a[:h3, :w3].reshape(h3 // step, step, w3 // step, step)
        return blk.max(axis=(1, 3)) if how == "max" else blk.mean(axis=(1, 3))

    e = pool(elev, "mean")
    f = pool(foot, "max").astype(bool)
    rel = np.clip((e - np.percentile(e[f], 2)) / max(np.percentile(e[f], 98) - np.percentile(e[f], 2), 1e-6), 0, 1)
    gy, gx = np.gradient(gaussian_filter(rel, 1.0))
    shade = np.clip(0.72 + 0.85 * (-gx - gy), 0, 1)
    img = np.stack([shade, shade, shade], -1)
    img[~f] = [0.88, 0.90, 0.87]
    cm = pool(cat, "max").astype(bool) & f
    em = pool(emis, "max").astype(bool) & f
    img[cm] = [0.24, 0.30, 0.33]
    halo = gaussian_filter(em.astype(F32), 1.2)
    hot = np.clip(halo, 0, 1)
    img[..., 0] = np.clip(img[..., 0] * (1 - 0.15 * hot) + 0.95 * em, 0, 1)
    img[..., 1] = np.clip(img[..., 1] * (1 - 0.55 * em) + 0.42 * em, 0, 1)
    img[..., 2] = np.clip(img[..., 2] * (1 - 0.75 * em) + 0.05 * em, 0, 1)
    fig, ax = plt.subplots(figsize=(9.0, 8.0), dpi=130)
    ax.imshow(img, interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])
    ys, xs = np.nonzero(f)
    if ys.size:
        ax.set_xlim(xs.min() - 4, xs.max() + 4)
        ax.set_ylim(ys.max() + 4, ys.min() - 4)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title("")
    ax.text(0.01, 0.985, "grey: 3DEP/detrended relief   dark: published catalogue   orange: H42 emission (40,000 px)",
            transform=ax.transAxes, va="top", ha="left", fontsize=7.5, color="#33403d")
    out = ROOT / "docs/h42-map.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("wrote", out, out.stat().st_size, "bytes",
          "sha256", hashlib.sha256(out.read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    main()
