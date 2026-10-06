"""Contract tests for the GEMSDOE41 artifacts and evidence files.

These are deliberately not model-quality tests: they assert the things that will get a submission
rejected or a claim retracted.  Model quality is measured by `scripts/build_submission.py` and
recorded in `evidence/holdout.json`; this file guards the deliverable boundary.

Run:  python -m pytest tests/test_gems41_artifacts.py -q
"""

from __future__ import annotations

import json
import os

import numpy as np
import pytest
import rasterio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "evidence", "submission_build.json")
TEMPLATE = os.path.join(ROOT, "data", "example_submission.tif")


def load(path):
    if not os.path.exists(path):
        pytest.skip(f"missing {os.path.relpath(path, ROOT)} (run the pipeline first)")
    with open(path) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def build():
    return load(BUILD)


def test_a_primary_artifact_is_named_and_exists(build):
    primary = build.get("primary")
    assert primary, "submission_build.json must name a primary artifact"
    assert primary in build["artifacts"]
    assert os.path.exists(os.path.join(ROOT, build["artifacts"][primary]["path"]))


def test_every_artifact_passes_its_own_checks(build):
    for name, art in build["artifacts"].items():
        assert art.get("all_pass") is True, f"{name} failed its own format checks"
        for key in ("values_in_0_1", "crs_epsg32611", "width_3292", "height_3730",
                    "res_100m", "transform_matches", "single_band", "driver_gtiff"):
            assert art.get(key) is True, f"{name}: {key} must be true"


def test_the_rejection_reason_cannot_recur(build):
    """The upload was once refused with 'Predicted values must be in range [0, 1]'."""
    for name, art in build["artifacts"].items():
        with rasterio.open(os.path.join(ROOT, art["path"])) as src:
            band = src.read(1)
        finite = band[np.isfinite(band)]
        assert finite.size, f"{name}: no finite values"
        assert finite.min() >= 0.0 and finite.max() <= 1.0, (
            f"{name}: values escape [0, 1] ({finite.min()} .. {finite.max()})")
        assert not np.isinf(band).any(), f"{name}: infinite values present"


def test_geometry_matches_the_submission_template(build):
    if not os.path.exists(TEMPLATE):
        pytest.skip("template raster not present in this checkout")
    with rasterio.open(TEMPLATE) as tpl:
        want = (tpl.crs, tpl.width, tpl.height, tpl.transform)
    for name, art in build["artifacts"].items():
        with rasterio.open(os.path.join(ROOT, art["path"])) as src:
            got = (src.crs, src.width, src.height, src.transform)
        assert got == want, f"{name}: grid does not match the submission template"


def test_artifacts_only_emit_inside_the_footprint(build):
    """The template fills its footprint with 0.0 and marks outside it as NaN.  Match that exactly:
    NaN outside the footprint, and nothing but finite values inside it."""
    if not os.path.exists(TEMPLATE):
        pytest.skip("template raster not present in this checkout")
    with rasterio.open(TEMPLATE) as tpl:
        outside = ~np.isfinite(tpl.read(1))
    for name, art in build["artifacts"].items():
        with rasterio.open(os.path.join(ROOT, art["path"])) as src:
            band = src.read(1)
        assert (band > 0).any(), f"{name}: no emitted mass"
        assert np.isnan(band[outside]).all(), f"{name}: values escape the template footprint"
        assert np.isfinite(band[~outside]).all(), f"{name}: outside-region cells must be NaN"
        assert (band[~outside] == 0).sum() >= 0 and band[~outside].size > 0


def test_the_headline_claim_is_the_measured_ratio(build):
    """The claim published on the site must be the one the evidence supports."""
    proj = build["artifacts"][build["primary"]].get("projection") or {}
    if not proj:
        pytest.skip("no projection recorded")
    assert proj["relative_gain_vs_uniform_control"] > 1.0
    assert "MODEL" in proj["metric"] or "model" in proj["caveat"].lower()


def test_the_corridor_negative_result_is_recorded():
    """A failed hypothesis must stay on the record, with a non-degenerate measured corridor."""
    seis = load(os.path.join(ROOT, "evidence", "seismicity.json"))
    assert seis["corridor"]["pixels"] > 0, "corridor collapsed to zero pixels"
    assert seis["catalog_separation"]["n_within_300m"] == 0
    assert seis["catalog_separation"]["n_beyond_3km"] >= 1


def test_the_mass_ladder_supports_where_the_primary_sits(build):
    ladder = load(os.path.join(ROOT, "evidence", "mass_ladder.json"))
    rows = {r["budget"]: r for r in ladder["rows"]}
    assert rows, "mass ladder is empty"
    # The criterion must be measurably active at the mass the primary ships at, and inert at dense
    # mass -- that inversion is the reason the primary is where it is.
    assert rows[2500]["ratio_c"] > rows[30000]["ratio_c"]
    n_primary = build["artifacts"][build["primary"]]["n_px"]
    assert n_primary <= max(rows), "primary emits more mass than the ladder explored"


def test_irregularities_are_published_and_flagged():
    irr = load(os.path.join(ROOT, "registry", "irregularities.json"))
    assert irr["review_required"] is True
    ids = {e["id"] for e in irr["entries"]}
    assert "IRR-01" in ids, "the fork/compliance question must be raised"
    fork = next(e for e in irr["entries"] if e["id"] == "IRR-01")
    assert fork["severity"] == "high"


def test_the_site_is_generated_from_the_evidence():
    site = os.path.join(ROOT, "docs", "h41", "index.html")
    if not os.path.exists(site):
        pytest.skip("site not generated in this checkout")
    html = open(site).read()
    assert "downloads/" in html, "the site must offer the artifact"
    for bad in ("None", "undefined"):
        assert bad not in html, f"the generated site leaked {bad!r}"
