"""H42 (2026-10-06): shipped artifacts, preregistered gates, site presentation.

These tests are deliberately measurement-based: every assertion reads the delivered bytes or the
receipts the builder wrote, never a claim in prose.
"""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "docs" / "downloads"
MAN = json.loads((DL / "manifest.json").read_text())
H42 = MAN["h42"]


def _tif(name):
    fn = Path(H42["artifacts"][name]["checks"]["path"]).name
    return DL / fn


def test_manifest_block_and_honest_gate_state():
    assert H42["primary"] in H42["artifacts"]
    assert H42["slot_eligible"] is False
    assert len(H42["note"]) <= 200 and "CLOSED" in H42["note"]
    d = H42["decisions"]
    assert d["holdout"] is False and d["enrichment"] is False
    assert set(d["holdout_arm_folds_pass"]) == {"h42b_junction_prior", "h42d_state_prior"}
    assert all(v == 0 for v in d["holdout_arm_folds_pass"].values())
    assert "no promotion" in d["slot_recommendation"]
    assert H42["preregistration"] == "research/hypotheses-h42.md"


def test_delivered_bytes_pass_every_format_check():
    for name in H42["artifacts"]:
        tif = _tif(name)
        assert tif.is_file(), tif
        checks = H42["artifacts"][name]["checks"]
        assert checks["all_pass"] is True, name
        with rasterio.open(tif) as src, rasterio.open(ROOT / "data/example_submission.tif") as tpl:
            a = src.read(1)
            assert src.count == 1 and src.dtypes[0] == "float32"
            assert src.crs == tpl.crs and a.shape == tpl.read(1).shape
            assert tuple(src.transform) == tuple(tpl.transform)
            assert src.nodata is None
            assert np.isfinite(a).all()
            assert set(np.unique(a)) <= {0.0, 1.0}          # range error impossible
            assert int((a > 0).sum()) == H42["artifacts"][name]["emitted_px"]
        # byte-deterministic receipt
        assert hashlib.sha256(tif.read_bytes()).hexdigest() == checks["sha256_bytes"]
        # the zip is the same bytes, intact
        zf = zipfile.ZipFile(tif.with_suffix("").with_suffix(".zip") if False else
                             str(tif)[:-4] + ".zip")
        assert zf.testzip() is None
        assert zf.read(zf.namelist()[0]) == tif.read_bytes()


def test_zero_cells_within_200m_of_catalogue():
    from scipy.ndimage import distance_transform_edt
    with rasterio.open(ROOT / "data/existing_faults.tif") as s:
        cat = s.read(1) == 1
    d = distance_transform_edt(~cat)
    for name in H42["artifacts"]:
        with rasterio.open(_tif(name)) as s:
            pos = s.read(1) > 0
        assert int((d[pos] <= 2.0 - 1e-9).sum()) == 0, name
        assert float(d[pos].min()) > 2.0, name


def test_gates_failed_and_recorded_not_rewritten():
    ho = json.loads((ROOT / "evidence/h42_holdout.json").read_text())
    assert ho["holdout_passed"] is False
    assert all(v == 0 for v in ho["arm_folds_pass"].values())
    agg = ho["aggregated"]
    # the evidence control tops the instrument; both arms stay below the best control on the ladder mean
    ctl = max(agg[k]["mean_cpm_ladder"] for k in agg if k.startswith("control"))
    assert agg["control_evidence"]["mean_cpm_ladder"] == ctl
    for arm in ("h42b_junction_prior", "h42d_state_prior"):
        assert agg[arm]["mean_cpm_ladder"] < ctl, arm
    enr = json.loads((ROOT / "evidence/h42_enrichment.json").read_text())
    assert enr["gate_passed_any"] is False
    for e in enr["results"].values():
        for v in (e.get("markers") or {}).values():
            assert v["passes"] is False


def test_uniqueness_against_every_shipped_raster():
    uni = json.loads((ROOT / "evidence/h42_uniqueness.json").read_text())
    for art, rows in uni.items():
        assert rows, art
        for other, v in rows.items():
            assert v["jaccard"] < 0.15, (art, other)
            assert not v.get("byte_equal", False), (art, other)


def test_frozen_protocol_constants():
    src = (ROOT / "src" / "gems41" / "h42.py").read_text()
    for line in ("CATALOGUE_PRUNE_PX = 2.0", "PACK_SEP_PX = 2.83",
                 "BUDGETS_PX = (2_500, 5_000, 10_000, 20_000)", "LIVE_MASS_PX = 37_654",
                 "EVAL_GUARD_PX = 3.0"):
        assert line in src, line


def test_prereg_document_contains_registration_and_outcome():
    doc = (ROOT / "research" / "hypotheses-h42.md").read_text()
    for marker in ("Part 1", "Part 2", "Part 3", "FALSIFIED", "Part 5", "amendment A1",
                   "Part 7", "0/4 folds"):
        assert marker in doc, marker
    assert "IRR-10" in doc  # erratum mapping registry ids


def test_registries_mirror_the_outcome():
    hyp = json.loads((ROOT / "registry/hypotheses.json").read_text())
    reg = hyp["h42_registration"]["registered_candidates"]
    assert {"H42-A", "H42-B", "H42-C", "H42-D", "H42-E"} <= set(reg)
    assert "FALSIFIED" in reg["H42-A"]["outcome"]
    assert "FAIL" in reg["H42-B"]["outcome"] and "FAIL" in reg["H42-D"]["outcome"]
    irr = json.loads((ROOT / "registry/irregularities.json").read_text())
    ids = {e["id"] for e in irr["entries"]}
    assert {"IRR-10", "IRR-11", "IRR-12", "IRR-13"} <= ids


def test_site_presents_the_h42_candidate_prominently():
    home = (ROOT / "docs" / "index.html").read_text()
    execsum = (ROOT / "docs" / "executive-summary.html").read_text()
    research = (ROOT / "docs" / "research.html").read_text()
    fn = _tif(H42["primary"]).name
    assert f'href="downloads/{fn}" download' in home
    assert "FIELD EXPERIMENT 42" in home
    assert H42["submission_name"] in home and H42["submission_name"] in execsum
    assert fn in execsum
    assert "id=\"h42\"" in research
    dl_index = (DL / "index.html").read_text()
    assert "gemsdoe41-h42b" in dl_index and "research only" in dl_index.lower()


def test_projection_is_labelled_model_not_score():
    for name, a in H42["artifacts"].items():
        p = a.get("projection") or {}
        assert p.get("metric", "").startswith("[MODEL]"), name
        assert "never a score promise" in p.get("caveat", ""), name
    assert H42["projection"]["per_arm"], "per-arm projections required"
