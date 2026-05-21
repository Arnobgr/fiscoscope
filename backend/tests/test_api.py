import json

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Point the app at a temp output dir with two sample files."""
    (tmp_path / "meta.json").write_text(
        json.dumps({"mode": "full", "sources": {}, "output_files": []})
    )
    (tmp_path / "kpi_overhead_rate.json").write_text(
        json.dumps({"france": [{"year": 2025, "value": 22.3}]})
    )
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path)
    return TestClient(api.app)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    assert r.json()["mode"] == "full"


def test_list_kpis_excludes_meta(client):
    r = client.get("/api/kpis")
    assert r.status_code == 200
    assert r.json() == {"kpis": ["kpi_overhead_rate"]}


def test_get_kpi(client):
    r = client.get("/api/kpi/kpi_overhead_rate")
    assert r.status_code == 200
    assert r.json()["france"][0]["year"] == 2025


def test_get_kpi_missing_returns_404(client):
    r = client.get("/api/kpi/does_not_exist")
    assert r.status_code == 404


def test_get_kpi_invalid_name_returns_404(client):
    # Uppercase fails the ^[a-z0-9_]+$ guard — never touches the filesystem.
    r = client.get("/api/kpi/Bad-Name")
    assert r.status_code == 404


def test_get_kpi_meta_blocked(client):
    # meta is served at /api/meta only, not via the generic KPI route.
    r = client.get("/api/kpi/meta")
    assert r.status_code == 404
