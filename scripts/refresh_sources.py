"""Refresh a dated snapshot of permitted non-competition public sources.

Important: DrivenData's Terms of Use prohibit automated access/monitoring. This
script MUST NOT request any drivendata.org URL, including the public leaderboard.
The competition page is linked for an explicit user-initiated visit only. Failed
checks remain visible and never turn into a current factual claim.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/source-feed.json"
HISTORICAL_LEADERBOARD = ROOT / "research/leaderboard-observation.json"

# These probes are limited to official data/literature sources outside the
# competition website. HEAD probes inspect availability metadata only. The TNM
# query reads one small JSON inventory response and does not download DEM tiles.
SOURCE_CHECKS = [
    {
        "id": "competition_rules_pdf",
        "url": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
        "method": "HEAD",
        "scope": "Availability metadata only; no PDF content is downloaded.",
    },
    {
        "id": "ingenious_gdr_record",
        "url": "https://gdr.openei.org/submissions/1391",
        "method": "HEAD",
        "scope": "Public DOE GDR record availability metadata only.",
    },
    {
        "id": "ingenious_qfaults_v2_archive",
        "url": "https://gdr.openei.org/files/1391/qfaults_ingenious_nad83conus117_2023-06-27.zip",
        "method": "HEAD",
        "scope": "Availability metadata only; archive is not downloaded by this feed.",
    },
    {
        "id": "faulds_henry_hinz_2005",
        "url": "https://nbmg.unr.edu/staff/Faulds/faulds_et_al_geology_paper.pdf",
        "method": "HEAD",
        "scope": "University-hosted paper availability metadata only.",
    },
    {
        "id": "astor_pass_osti",
        "url": "https://www.osti.gov/servlets/purl/1110516",
        "method": "HEAD",
        "scope": "DOE OSTI paper availability metadata only.",
    },
    {
        "id": "emerson_pass_osti",
        "url": "https://www.osti.gov/servlets/purl/1110518",
        "method": "HEAD",
        "scope": "DOE OSTI paper availability metadata only.",
    },
    {
        "id": "usgs_3dep_1m_inventory_sample_window",
        "url": (
            "https://tnmaccess.nationalmap.gov/api/v1/products?"
            "datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&"
            "bbox=-119.8,39.5,-119.0,40.0&prodFormats=GeoTIFF&max=1"
        ),
        "method": "GET_JSON",
        "scope": "One inventory response for a sample bbox; not evidence of full-study-area coverage.",
    },
]

COMPETITION = {
    "leaderboard_url": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "terms_url": "https://www.drivendata.org/termsofuse/",
    "robots_url": "https://www.drivendata.org/robots.txt",
    "automated_access": "disabled",
    "current_score": None,
    "reason": (
        "DrivenData Terms of Use prohibit robots, spiders, and automatic access for any purpose, "
        "including monitoring; no leaderboard request or browser scrape is made."
    ),
}


def _safe_headers(response):
    """Keep only small non-sensitive response metadata; never store page bodies."""
    headers = response.headers
    return {
        "http_status": response.status_code,
        "final_url": response.url,
        "content_type": headers.get("Content-Type"),
        "content_length": headers.get("Content-Length"),
        "last_modified": headers.get("Last-Modified"),
        "etag": headers.get("ETag"),
    }


def check_source(source, session=requests):
    row = {"id": source["id"], "url": source["url"], "method": source["method"], "scope": source["scope"]}
    response = None
    try:
        if source["method"] == "HEAD":
            response = session.head(source["url"], timeout=30, allow_redirects=True)
            if response.status_code in (405, 501):
                response.close()
                response = session.get(source["url"], timeout=30, allow_redirects=True, stream=True)
        elif source["method"] == "GET_JSON":
            response = session.get(source["url"], timeout=30, allow_redirects=True)
        else:
            raise ValueError(f"unsupported check method: {source['method']}")

        response.raise_for_status()
        row.update(status="ok", **_safe_headers(response))
        if source["method"] == "GET_JSON":
            payload = response.json()
            items = payload.get("items") or []
            row["inventory_total"] = payload.get("total")
            row["sample_products"] = [
                {
                    "title": item.get("title"),
                    "metadata_url": item.get("metaUrl"),
                    "download_url": item.get("downloadURL"),
                }
                for item in items[:1]
            ]
            if not isinstance(payload.get("total"), int) or payload["total"] < 0:
                raise ValueError("inventory response has no valid total count")
    except Exception as exc:
        row.update(status="error", error=f"{type(exc).__name__}: {str(exc)[:240]}")
    finally:
        if response is not None:
            response.close()
    return row


def build_snapshot(session=requests, checked_utc=None):
    historical = json.loads(HISTORICAL_LEADERBOARD.read_text())
    sources = [check_source(source, session=session) for source in SOURCE_CHECKS]
    return {
        "schema_version": 2,
        "checked_utc": checked_utc or datetime.now(timezone.utc).isoformat(),
        "method": "Daily low-volume availability checks of permitted official sources; no DrivenData access.",
        "competition_leaderboard": {
            **COMPETITION,
            "last_recorded_public_observation": historical,
            "snapshot_warning": "Historical context only; not current. Current rankings are unknown; this project does not monitor the leaderboard.",
        },
        "sources": sources,
        "source_checks_ok": sum(source["status"] == "ok" for source in sources),
        "source_checks_failed": sum(source["status"] != "ok" for source in sources),
        "failure_interpretation": "A probe error means this runner could not verify the endpoint; it does not prove the remote source is offline.",
    }


def main():
    snapshot = build_snapshot()
    OUT.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(json.dumps({
        "checked_utc": snapshot["checked_utc"],
        "competition_automated_access": snapshot["competition_leaderboard"]["automated_access"],
        "source_checks_ok": snapshot["source_checks_ok"],
        "source_checks_failed": snapshot["source_checks_failed"],
        "leaderboard_current_score": snapshot["competition_leaderboard"]["current_score"],
    }, indent=2))


if __name__ == "__main__":
    main()
