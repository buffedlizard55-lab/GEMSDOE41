"""Contract tests for the H42 deliverable and the instruments behind it.

These guard the things that get a submission rejected or a claim retracted:
the delivered bytes, the geometry, the range-error hardening, the uniqueness of the artifact,
the honesty of the manifest, and the internal consistency of the score-record calculus.

Run:  python -m pytest tests/test_h42_artifact.py -q
"""
from __future__ import annotations

import json
import os

import numpy as np
import pytest
import rasterio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "docs", "downloads", "manifest.json")
BUILD = os.path.join(ROOT, "evidence", "h42_submission_build.json")
CALC = os.path.join(ROOT, "evidence", "score_record_calculus.json")
HOLDOUT = os.path.join(ROOT, "evidence", "h42_holdout.json")
TEMPLATE = os.path.join(ROOT, "data", "sample_submission.tif")
CATALOGUE = os.path.join(ROOT, "data", "existing_faults.tif")


def load(path):
    if not os.path.exists(path):
        pytest.skip(f"missing {os.path.relpath(path, ROOT)} (run the H42 pipeline first)")
    with open(path) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def build():
    return load(BUILD)


@pytest.fixture(scope="module")
def manifest():
    return load(MANIFEST)


def test_delivered_file_exists_and_is_the_featured_one(build, manifest):
    path = os.path.join(ROOT, build["file"]["path"])
    assert os.path.exists(path), build["file"]["path"]
    assert manifest["filename"] == build["file"]["name"]
    assert manifest["slot_eligible"] is False


def test_reopened_bytes_match_the_receipt_exactly(build):
    """AGENTS.md #9: re-open the actual delivered file, not the array that produced it."""
    import hashlib

    path = os.path.join(ROOT, build["file"]["path"])
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    assert h.hexdigest() == build["checks"]["sha256"]
    assert os.path.getsize(path) == build["checks"]["bytes"]
    with rasterio.open(path) as src:
        arr = src.read(1, masked=False)
    px = hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()
    assert px == build["checks"]["pixel_sha256"]
    assert px.startswith(build["file"]["pixel_sha12"])


def test_grid_is_the_organizer_template_exactly(build):
    if not os.path.exists(TEMPLATE):
        pytest.skip("template raster not present in this checkout")
    path = os.path.join(ROOT, build["file"]["path"])
    with rasterio.open(TEMPLATE) as tpl, rasterio.open(path) as src:
        assert (src.crs, src.width, src.height, src.transform) == (
            tpl.crs, tpl.width, tpl.height, tpl.transform)
        assert src.count == 1 and src.dtypes[0] == "float32"
        assert tuple(round(float(r), 6) for r in src.res) == (100.0, 100.0)


def test_range_error_hardening(build):
    """Every stored cell finite and in [0,1]; the portal's range rejection cannot fire."""
    path = os.path.join(ROOT, build["file"]["path"])
    with rasterio.open(path) as src:
        arr = src.read(1, masked=False)
        mask = src.dataset_mask()
    assert np.isfinite(arr).all()
    assert arr.min() >= 0.0 and arr.max() <= 1.0
    assert arr.size == 12_279_160
    if os.path.exists(TEMPLATE):
        with rasterio.open(TEMPLATE) as tpl:
            foot = np.isfinite(tpl.read(1))
        # rasterio's mask is uint8 with 255 inside, NOT boolean (IRR-14)
        assert int((mask > 0).sum()) == int(foot.sum())
        assert (arr[~foot] == 0).all()
        with rasterio.open(path) as src:
            masked = src.read(1, masked=True)
        assert masked.mask[~foot].all(), "a mask-honouring reader must see null outside the bounds"


def test_emission_is_off_catalogue_and_inside_the_footprint(build):
    if not (os.path.exists(CATALOGUE) and os.path.exists(TEMPLATE)):
        pytest.skip("competition rasters not present in this checkout")
    path = os.path.join(ROOT, build["file"]["path"])
    with rasterio.open(path) as src:
        arr = src.read(1, masked=False)
    with rasterio.open(CATALOGUE) as src:
        cat = src.read(1)
    with rasterio.open(TEMPLATE) as src:
        foot = np.isfinite(src.read(1))
    pos = arr > 0
    assert int(pos.sum()) == build["checks"]["n_positive_px"] > 0
    assert not (pos & (cat == 1)).any(), "mass on published-catalogue pixels is inert; ship none"
    assert (pos & foot).sum() == pos.sum()
    assert set(np.unique(arr[pos])).issubset({1.0}), "the optimum of a linear-fractional index is binary"


def test_no_sibling_raster_is_an_input(build):
    """Uniqueness: the builder must not read the probe corpus or any prior submission.

    Checked on the AST rather than on the raw text, because the module docstring *names* the probe
    corpus in order to say that it is never opened here.  Only string literals in executable code
    count.
    """
    import ast

    path = os.path.join(ROOT, "scripts", "build_h42_submission.py")
    tree = ast.parse(open(path).read())
    # the raw module docstring node, NOT ast.get_docstring(), which cleans/dedents it and would
    # then fail to compare equal to the literal it came from
    raw_doc = tree.body[0].value.value if (tree.body and isinstance(tree.body[0], ast.Expr)
                                           and isinstance(tree.body[0].value, ast.Constant)) else ""
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value != raw_doc]
    forbidden = ("data/probes", "comparison-h33", "gems24-", "gems25-", "gems28-", "gemsdoe32-",
                 "h19-5", "d2-8", "h33-2-b2", "prior_reference")
    for lit in literals:
        for token in forbidden:
            assert token not in lit, f"{token!r} appears in a code literal: {lit[:120]!r}"
    # every raster the builder opens must be an organizer input or this repo's own derived file
    opened = [lit for lit in literals if lit.endswith(".tif")]
    assert opened, "expected the builder to name at least one raster"
    for lit in opened:
        assert "probes" not in lit and "downloads" not in lit, lit
    assert build["uniqueness"]


def test_manifest_note_is_short_and_states_the_gate(manifest):
    assert len(manifest["note"]) <= 200
    assert "CLOSED" in manifest["note"]
    assert manifest["submission_name"].startswith("GEMS41-H42-Completion-")
    assert manifest["format"]["all_checks_passed"] is True
    assert manifest["format"]["min_distance_to_catalogue_px"] > 2.0


def test_holdout_gate_is_recorded_and_passed(manifest):
    g = manifest["h42_holdout"]["promotion_gate"]
    assert g["beats_position_blind_null"].startswith("4/4")
    assert g["credit_per_mass_at_2000px"] > g["incumbent_best_credit_per_mass"]
    agg = manifest["h42_holdout"]["mean_dti_by_strategy_and_mass"]
    m = str(manifest["h42_holdout"]["chosen"]["mass"])
    assert agg["coverage_greedy"][m]["mean_dti"] > agg["uniform_scatter"][m]["mean_dti"]
    assert agg["coverage_greedy"][m]["mean_dti"] > agg["belief_greedy_pack"][m]["mean_dti"]


def test_holdout_used_four_folds_and_identical_masses():
    h = load(HOLDOUT)
    assert len(h["folds"]) == 4
    masses = {int(c["mass"]) for c in h["folds"][0]["coverage_greedy"]}
    for f in h["folds"]:
        assert {int(c["mass"]) for c in f["coverage_greedy"]} == masses
        assert {int(c["n_px"]) for c in f["controls"]["uniform_scatter"]} == masses
        assert f["summary"]["n_truth"] > 0
        # the calibration check nothing in training targets
        assert 0.5 < f["rho_model"] / f["summary"]["n_truth"] < 1.2


def test_score_record_calculus_is_internally_consistent():
    c = load(CALC)
    assert abs(c["kernel_sum"] - 9.380297810508184) < 1e-9
    for tag in ("regression_full_chain", "regression_dotted_core"):
        r = c[tag]
        # ceiling is the M -> 0 intercept of 1/s, and equals a/(0.2a+0.8)
        assert r["ceiling_s_max"] == pytest.approx(1.0 / r["intercept_c0"], rel=1e-9)
        assert r["ceiling_s_max"] == pytest.approx(
            r["coverage_a"] / (0.2 * r["coverage_a"] + 0.8), rel=1e-6)
        assert 0.0 < r["coverage_a"] < 1.0
        assert r["tp_w_rho_a"] == pytest.approx(r["coverage_a"] * r["rho"], rel=1e-6)
        assert r["r2"] > 0.9
        # every projected score must lie strictly below the ceiling and above the incumbent
        for v in r["extrapolated_score_by_mass"].values():
            assert v < r["ceiling_s_max"]
    # containment of the nested lineage was verified from the bytes, not assumed
    cont = c["lineage_containment"]
    for k in ("dot_d15_in_h19_5", "dot_d28_in_h19_5", "h321_prethin_in_h19_5",
              "h274_solo_in_h19_5", "h33_2b2_in_h19_5"):
        assert cont[k] == 1.0, k


def test_null_model_reproduces_a_live_score():
    c = load(CALC)
    chk = c["null_model"]["empirical_check"]
    assert chk["probe"] == "h34_scatter"
    assert abs(chk["relative_error"]) < 0.01
    # and the incumbent's positional skill over that null is the factor quoted in the docs
    inc = [r for r in c["null_model"]["rows"] if r["id"] == "h33_2b2"][0]
    assert inc["reported"] / chk["reported"] > 3.0


def test_failed_inversion_is_published_not_hidden():
    inv = os.path.join(ROOT, "evidence", "label_field_inversion.json")
    if not os.path.exists(inv):
        pytest.skip("inversion evidence not present")
    d = json.load(open(inv))
    assert d["loo"]["rmse"] > 0.05, "a suspiciously good fit here would mean the basis was leaking"
    assert d["loo"]["within_0p01"] <= 5
    assert "evidence_class" in d and "owner-reported" in d["evidence_class"]
