"""Router-level test: mock the MonarchClient, verify routes return mapped data."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings, get_settings
from backend.app.main import create_app
from backend.app.models.monarch import Account, Category, Holding
from backend.app.services.cache import TTLCache
from backend.app.services.monarch_client import MonarchClient, get_monarch_client


@pytest.fixture
def fake_client():
    client = AsyncMock(spec=MonarchClient)
    client.list_accounts = AsyncMock(
        return_value=[
            Account(id="a1", name="Checking", type="depository", balance_current=5000),
            Account(id="a2", name="Brokerage", type="investment", balance_current=200000),
        ],
    )
    client.list_holdings = AsyncMock(
        return_value=[
            Holding(
                account_id="a2",
                ticker="VTI",
                name="Total Stock",
                quantity=10,
                market_value=2500,
                asset_class="us_equity",
            ),
        ],
    )
    client.list_categories = AsyncMock(
        return_value=[Category(id="c1", name="Groceries", group="Food")],
    )
    client.list_account_history = AsyncMock(return_value=[])
    client.list_transactions = AsyncMock(return_value=[])
    client.update_transaction = AsyncMock()
    return client


@pytest.fixture
def app(fake_client):
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(app_password="")
    application.dependency_overrides[get_monarch_client] = lambda: fake_client
    # Fresh cache per test
    fresh_cache = TTLCache()
    from backend.app.services import cache as cache_mod
    application.dependency_overrides[cache_mod.get_cache] = lambda: fresh_cache
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def test_accounts_endpoint_returns_mapped_accounts(client):
    response = client.get("/api/monarch/accounts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Checking"
    assert data[1]["type"] == "investment"


def test_net_worth_aggregates(client):
    response = client.get("/api/monarch/net_worth")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 205000
    assert body["by_type"]["cash"] == 5000
    assert body["by_type"]["investment"] == 200000


def test_holdings_endpoint(client):
    response = client.get("/api/monarch/accounts/a2/holdings")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["ticker"] == "VTI"


def test_categories_endpoint(client):
    response = client.get("/api/monarch/categories")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Groceries"


def test_app_password_required_when_set(fake_client):
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(app_password="hunter2")
    application.dependency_overrides[get_monarch_client] = lambda: fake_client
    client = TestClient(application)

    resp_unauth = client.get("/api/monarch/accounts")
    assert resp_unauth.status_code == 401

    resp_ok = client.get("/api/monarch/accounts", headers={"X-App-Password": "hunter2"})
    assert resp_ok.status_code == 200
