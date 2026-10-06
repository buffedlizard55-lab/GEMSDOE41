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


def test_gate_and_note_are_honest():
    manifest = json.loads((ROOT / "docs/downloads/manifest.json").read_text())
    assert manifest["slot_eligible"] is False
    assert len(manifest["note"]) <= 200 and "CLOSED" in manifest["note"]
    for name in ("index.html", "executive-summary.html", "research.html"):
        assert "gate" in (ROOT / "docs" / name).read_text().lower()


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
