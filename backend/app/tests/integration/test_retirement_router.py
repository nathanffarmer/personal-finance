"""Retirement router smoke tests."""

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings, get_settings
from backend.app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(app_password="")
    return TestClient(app)


SCENARIO = {
    "current_age": 65,
    "retirement_age": 65,
    "end_age": 95,
    "current_portfolio": 1_000_000,
    "asset_allocation": {"equity": 0.6, "bond": 0.4, "cash": 0.0},
    "annual_contributions": 0,
    "annual_spend_real": 40_000,
    "withdrawal_strategy": {"kind": "four_percent", "params": {}},
    "glide_path": {"kind": "static", "params": {}},
}


def test_deterministic_endpoint(client):
    resp = client.post("/api/retirement/project/deterministic", json=SCENARIO)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["ages"]) == 31
    assert body["ages"][0] == 65


def test_monte_carlo_endpoint(client):
    resp = client.post(
        "/api/retirement/project/monte_carlo",
        json={"scenario": SCENARIO, "trials": 500, "method": "bootstrap", "seed": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trials"] == 500
    assert 0.0 <= body["success_rate"] <= 1.0
    assert len(body["percentiles"]["p50"]) == 31


def test_monte_carlo_clamps_trial_count(client):
    resp = client.post(
        "/api/retirement/project/monte_carlo",
        json={"scenario": SCENARIO, "trials": 5, "method": "bootstrap", "seed": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["trials"] == 100  # clamped up to MIN_TRIALS


def test_fire_endpoint(client):
    resp = client.post(
        "/api/retirement/fire/numbers",
        json={
            "annual_spend": 40_000,
            "current_age": 30,
            "target_age": 60,
            "swr": 0.04,
            "real_return": 0.05,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["regular_fire"] == pytest.approx(1_000_000)
    assert body["coast_fire"] < body["regular_fire"]
