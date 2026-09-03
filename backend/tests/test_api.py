"""Thin API-contract checks against an in-process app with an isolated temp DB.

The temp DB / artifacts dir are configured in tests/conftest.py before import.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:  # lifespan runs the first-time seed + train
        yield c


def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["offline"] is True


def test_status_reports_flagged_and_inactive_faculty(client):
    r = client.get("/api/model/status").json()
    assert r["corpus_size"] == 200
    assert r["flagged_count"] == 13
    assert r["faculty_matching_active"] is False
    assert r["active_version"] is not None


def test_flagged_queue_matches_section_3(client):
    flagged = client.get("/api/corpus/flagged").json()
    reasons = " ".join(f["flag_reason"] for f in flagged)
    assert "duplicate_project_id" in reasons
    assert "missing_title" in reasons
    assert "missing_statement" in reasons
    assert all(f["cluster_id"] is None for f in flagged)  # excluded from the active pool


def test_recommendation_flow_and_guardrails(client):
    s = client.post("/api/students", json={
        "name": "T", "skills": ["react", "typescript"], "interests": ["web apps", "accessibility"],
    }).json()
    rec = client.post("/api/recommendations", json={"student_id": s["id"], "filters": {}}).json()
    assert rec["mode"] in {"low_confidence", "no_signal"}
    for item in rec["recommendations"]:
        assert item["project_id"]
        assert 0.0 <= item["similarity"] < 1.0
        assert item["recommendation_id"]


def test_patch_clears_flag(client):
    flagged = client.get("/api/corpus/flagged").json()
    target = next(f for f in flagged if f["flag_reason"] == "missing_title")
    fixed = client.patch(f"/api/corpus/{target['id']}", json={
        "title": "A Restored Descriptive Title", "clear_flag": True,
    }).json()
    assert fixed["is_flagged"] is False


def test_upload_then_retrain_then_rollback(client):
    before = client.get("/api/model/status").json()["active_version"]
    csv = (
        "ProjectID,Title,Problem Statement\n"
        "API-1,Edge Anomaly Detection,\"A specific and adequately long problem statement here.\"\n"
    )
    up = client.post(
        "/api/corpus/upload",
        files={"file": ("b.csv", csv, "text/csv")},
        data={"source_batch": "apitest"},
    ).json()
    assert up["inserted"] == 1
    mv = client.post("/api/model/retrain", json={"notes": "t"}).json()
    assert mv["version"] == before + 1
    rolled = client.post("/api/model/activate", json={"version": before}).json()
    assert rolled["version"] == before and rolled["is_active"] is True
