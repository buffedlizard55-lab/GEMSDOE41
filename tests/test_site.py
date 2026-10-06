import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from refresh_sources import SOURCE_CHECKS, build_snapshot  # noqa: E402


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.targets.append(value)


def test_all_local_site_links_exist():
    for path in [ROOT / "index.html", *(ROOT / "docs").glob("*.html")]:
        parser = Links()
        parser.feed(path.read_text())
        for link in parser.targets:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            assert (path.parent / unquote(parts.path)).exists(), (path, link)


def test_usgs_one_meter_dem_record_uses_the_current_catalogue_url():
    record = next(
        source for source in SOURCE_CHECKS
        if source["id"] == "usgs_3dep_1m_collection_record"
    )
    assert record["url"] == (
        "https://data.usgs.gov/datacatalog/data/"
        "USGS:77ae0551-c61e-4979-aedd-d797abdcde0e"
    )
    assert record["method"] == "HEAD"
    assert "no DEM tiles" in record["scope"]
    assert not any("1-meter-digital-elevation-models-dem" in source["url"] for source in SOURCE_CHECKS)
    sources_page = (ROOT / "docs/sources.html").read_text()
    assert record["url"] in sources_page
    assert "https://www.usgs.gov/3d-elevation-program/1-meter-digital-elevation-models-dem" not in sources_page


def test_hypothesis_ids_are_workstream_qualified_in_both_research_sites():
    transfer_page = (ROOT / "docs/research.html").read_text()
    parallel_page = (ROOT / "docs/h41/hypotheses.html").read_text()
    registry = (ROOT / "research/hypothesis-id-registry.md").read_text()

    assert 'id="id-namespaces"' in transfer_page
    assert "transfer/H41-E" in transfer_page
    assert "parallel-registry/H41-E" in transfer_page
    assert "local-strike/H41-I" in transfer_page
    assert "Workstream-scoped IDs" in parallel_page
    assert "../research.html#id-namespaces" in parallel_page
    assert "Source-vector transfer ID" in registry
    assert "parallel-registry/H41-H" in registry
    assert "local-strike/H41-I" in registry
    assert "local-strike/H41-I" in parallel_page


def test_public_source_refresh_never_requests_drivendata():
    class Response:
        def __init__(self, url, json_data=None):
            self.status_code = 200
            self.url = url
            self.headers = {"Content-Type": "application/json", "Content-Length": "20"}
            self._json_data = json_data

        def raise_for_status(self):
            return None

        def json(self):
            return self._json_data

        def close(self):
            return None

    class Session:
        def __init__(self):
            self.urls = []

        def head(self, url, **kwargs):
            self.urls.append(url)
            return Response(url)

        def get(self, url, **kwargs):
            self.urls.append(url)
            return Response(url, {"total": 64, "items": [{
                "title": "sample tile",
                "metaUrl": "https://www.sciencebase.gov/catalog/item/sample",
                "downloadURL": "https://prd-tnm.s3.amazonaws.com/sample.tif",
            }]})

    session = Session()
    snapshot = build_snapshot(session=session, checked_utc="2026-10-05T23:00:00+00:00")
    assert len(session.urls) == len(SOURCE_CHECKS)
    assert all("drivendata.org" not in url.lower() for url in session.urls)
    assert snapshot["competition_leaderboard"]["current_score"] is None
    assert snapshot["competition_leaderboard"]["automated_access"] == "disabled"
    assert snapshot["source_checks_ok"] == len(SOURCE_CHECKS)
    assert snapshot["source_checks_failed"] == 0
    assert "does not prove the remote source is offline" in snapshot["failure_interpretation"]


def test_historical_score_is_never_mislabeled_current():
    feed = json.loads((ROOT / "docs/source-feed.json").read_text())
    competition = feed["competition_leaderboard"]
    historic = competition["last_recorded_public_observation"]
    assert competition["current_score"] is None
    assert competition["automated_access"] == "disabled"
    assert historic["observed_date_utc"] == "2026-10-05"
    assert historic["score"] == 0.3262
    rows = historic["observed_rows"]
    assert next(row for row in rows if row["rank"] == 4)["score"] == 0.3195
    assert next(row for row in rows if row["rank"] == 13)["participant"] == "extradr19"
    assert "historical only" in historic["current_status"]
    assert "unknown" in historic["current_status"]
    assert "not current" in competition["snapshot_warning"].lower()
    score_audit = (ROOT / "research/h33-score-analysis.md").read_text().lower()
    assert "filename-to-score" in score_audit
    assert "manual monitoring requires prior written consent" in score_audit
    site_js = (ROOT / "docs/site.js").read_text().lower()
    assert "fetch('source-feed.json'" in site_js
    assert "fetch('https://www.drivendata.org" not in site_js
    assert "earthquake.usgs.gov/fdsnws/event/1/query" in site_js
    home = (ROOT / "docs/index.html").read_text()
    assert 'id="comcat-status"' in home
    assert 'id="comcat-events"' in home
    assert "not proof of a fault" in home.lower()


def test_reproduction_tolerance_is_disclosed_consistently():
    guide = (ROOT / "docs/executive-summary.html").read_text()
    checker = (ROOT / "scripts/check_reproduction.py").read_text()
    assert "64 float32 epsilons" in guide
    assert "outside-footprint encoding must also match" in guide
    assert "TOLERANCE_FLOAT32_EPSILONS = 64" in checker
    assert "below 0.000001" not in guide


def test_gate_and_note_are_honest():
    """The gate may be open or closed, but it must be declared, justified and never sold as a score.

    H42 (2026-10-06) is the first arm to pass the 20 km blocked holdout at equal mass, so the
    manifest's slot gate is open for it.  The invariants kept here are the ones that stop the site
    from overclaiming: an explicit reason, a short distinguishing note, no score claim, the archived
    candidate marked not-to-submit, and the numbers on the page equal to the evidence files.
    """
    manifest = json.loads((ROOT / "docs/downloads/manifest.json").read_text())
    assert isinstance(manifest["slot_eligible"], bool)
    assert len(manifest["note"]) <= 200
    assert "unscored" in manifest["note"].lower()
    if manifest["slot_eligible"]:
        assert "slot_eligible_reason" in manifest
        gate = json.loads((ROOT / "docs/downloads/h42-gate.json").read_text())
        assert gate["gate_status"].startswith("OPEN")
        holdout = json.loads((ROOT / "evidence/h42_holdout_20km.json").read_text())
        arm = gate["candidate_arm"]
        assert gate["result"]["candidate_mean_dti"] == holdout["summary"][arm]["mean_dti"]
        assert (gate["result"]["candidate_mean_dti"]
                > gate["result"]["uniform_random_control"]
                > 0)
        assert gate["result"]["candidate_min_fold"] > gate["result"]["uniform_random_control"]
    assert "not to submit" in manifest["archived_primary"]["status"] or \
        "do not submit" in manifest["archived_primary"]["status"]
    home = (ROOT / "docs/index.html").read_text()
    assert "not a score forecast" in home or "not a score forecast" in \
        (ROOT / "docs/executive-summary.html").read_text()
    for name in ("index.html", "executive-summary.html", "research.html"):
        assert "gate" in (ROOT / "docs" / name).read_text().lower()
    # No page may claim an organizer-scored result for this artifact.
    for name in ("index.html", "executive-summary.html", "research.html"):
        text = (ROOT / "docs" / name).read_text()
        assert "scored 0.2" not in text and "achieved 0.27" not in text


def test_junction_checks_both_populations():
    audit = json.loads((ROOT / "docs/downloads/structural-audit.json").read_text())
    assert audit["junction_check_passed"] and audit["mass_within_200m_catalogue"] == 0
    assert all(value["candidate_enrichment"] > 1 for value in audit["population_density_checks"].values())
    assert not audit["comparison"]["equal_arrays"]


def test_h41e_negative_result_is_reported_and_gate_stays_closed():
    result = json.loads((ROOT / "research/experiments/h41e-kinematic-holdout.json").read_text())
    assert result["means"]["H41-A"] == 0
    assert result["means"]["H41-E"] == 0
    assert result["strict_mean_improvement_over_h41a"] is False
    assert result["weekly_slot_eligible"] is False
    assert all(fold["models"]["H41-E"]["prediction_mass"] == 0 for fold in result["folds"])


def test_supplemental_h41a_raster_variant_is_visible_and_gated():
    receipt = json.loads((ROOT / "docs/evidence/h41a_raster_build_receipt.json").read_text())
    home = (ROOT / "docs/index.html").read_text()
    variant = (ROOT / "docs/h41a-raster-variant.html").read_text()
    assert receipt["candidate_id"] == "H41-A-R"
    assert receipt["slot_eligible"] is False
    assert "H41-A-R" in home
    assert receipt["output"]["path"].split("/", 2)[-1] in home
    assert "null/unevaluable" in home
    assert "H41-A-R" in variant and "do not submit" in variant.lower()
    assert receipt["output"]["sha256"] in variant
    assert receipt["submission_name"] in variant
    assert (ROOT / receipt["output"]["path"]).is_file()


def test_kinematic_ranking_page_is_linked_from_the_main_site():
    home = (ROOT / "docs/index.html").read_text()
    ranking = ROOT / "docs/h41/index.html"
    assert ranking.is_file()
    assert 'href="h41/index.html"' in home
    assert "Kinematic ranking" in home


def test_rendered_pages_disclose_restriction_and_historical_snapshot():
    home = (ROOT / "docs/index.html").read_text()
    research = (ROOT / "docs/research.html").read_text()
    sources = (ROOT / "docs/sources.html").read_text()
    assert "not current" in home.lower()
    assert "Terms of Use" in home
    assert "leaderboard monitoring is disabled" in home.lower()
    assert 'id="h33-score-audit"' in research
    assert "Current standings are unknown" in research
    assert "0.3195" in research and "0.3262" in research
    assert "current standings are unknown" in sources.lower()
    assert "0.3262" in sources


def test_reproduce_workflow_follows_the_declared_reproduction_target():
    """CI pins the H41-A rebuild against a named raster; the manifest must not silently repoint it.

    H42 became the published submission (manifest['filename']) while scripts/run_pipeline.py still
    rebuilds the H41-A field.  The workflow therefore has to read manifest['reproduction_target'].
    This test fails if either side drops that contract.
    """
    manifest = json.loads((ROOT / "docs/downloads/manifest.json").read_text())
    workflow = (ROOT / ".github/workflows/reproduce.yml").read_text()
    assert manifest["filename"] != manifest["reproduction_target"]["filename"], \
        "the published submission and the CI rebuild target are different artifacts here"
    assert (ROOT / "docs/downloads" / manifest["reproduction_target"]["filename"]).exists()
    assert (ROOT / "docs/downloads" / manifest["filename"]).exists()
    assert "reproduction_target" in workflow
    assert "expected-main.tif" in workflow


def test_the_slot_eligible_download_is_above_every_archived_build():
    """The acceptance criterion is that the submission file is obvious at the top of the site.

    H41-I keeps a prominent panel, but it is a gate-closed predecessor: on every page it must come
    after the live H42 content and carry the not-to-submit banner, otherwise the first thing a
    visitor sees is an archived download button.
    """
    import json
    manifest = json.loads((ROOT / "docs/downloads/manifest.json").read_text())
    assert manifest["slot_eligible"] is True
    for name in ("index.html", "executive-summary.html", "research.html"):
        text = (ROOT / "docs" / name).read_text()
        live = text.index(manifest["filename"])
        archived = text.index("h41i-local-strike")
        assert live < archived, f"{name}: the archived H41-I panel precedes the live download"
        banner = text.index("Earlier build (H41-I) — not the file to submit.")
        assert banner < archived
        # the H42 gate statement is present before the archived banner on the landing page
        if name == "index.html":
            assert text.index("Blocked-holdout gate") < banner
