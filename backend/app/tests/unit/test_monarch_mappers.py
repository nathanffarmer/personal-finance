"""Tests for the Monarch -> Pydantic mapping layer.

Uses recorded-style fixture dicts so we don't need a live Monarch session.
"""

from datetime import date

import pytest

from backend.app.models.monarch import NetWorthByType
from backend.app.services.monarch_client import (
    MonarchClient,
    _extract_list,
    map_account,
    map_category,
    map_holding,
    map_transaction,
)


def test_map_account_normalizes_type_and_balance():
    raw = {
        "id": "acct_1",
        "displayName": "Chase Checking",
        "type": {"name": "depository"},
        "subtype": {"name": "checking"},
        "institution": {"name": "Chase"},
        "currentBalance": 1234.56,
        "availableBalance": 1000.0,
        "currency": "USD",
        "isHidden": False,
        "updatedAt": "2026-05-19T12:34:56Z",
    }
    acct = map_account(raw)
    assert acct.id == "acct_1"
    assert acct.name == "Chase Checking"
    assert acct.type == "depository"
    assert acct.subtype == "checking"
    assert acct.institution == "Chase"
    assert acct.balance_current == pytest.approx(1234.56)
    assert acct.balance_available == pytest.approx(1000.0)
    assert acct.updated_at is not None


def test_map_account_handles_credit_card_subtype():
    raw = {
        "id": "acct_cc",
        "name": "Amex",
        "type": "credit_card",
        "currentBalance": -250.0,
    }
    acct = map_account(raw)
    assert acct.type == "credit"
    assert acct.balance_current == -250.0


def test_map_account_falls_back_to_other_for_unknown_type():
    raw = {"id": "x", "name": "Mystery", "type": "asteroid_mining", "currentBalance": 0}
    assert map_account(raw).type == "other"


def test_map_holding_classifies_etf_as_equity():
    raw = {
        "accountId": "acct_1",
        "security": {"ticker": "VTI", "name": "Vanguard Total Stock", "type": "ETF"},
        "quantity": 10,
        "totalValue": 2500.0,
        "costBasis": 2000.0,
    }
    h = map_holding(raw)
    assert h.account_id == "acct_1"
    assert h.ticker == "VTI"
    assert h.quantity == 10
    assert h.market_value == 2500.0
    assert h.cost_basis == 2000.0
    assert h.asset_class == "us_equity"


def test_map_holding_handles_bond_security():
    raw = {
        "account": {"id": "acct_2"},
        "security": {"ticker": "BND", "name": "Vanguard Bond", "type": "BOND"},
        "quantity": 100,
        "totalValue": 8000.0,
    }
    assert map_holding(raw).asset_class == "bond"


def test_map_transaction_pulls_category_and_merchant():
    raw = {
        "id": "tx_1",
        "date": "2026-05-15",
        "amount": -42.50,
        "merchant": {"name": "Whole Foods"},
        "originalDescription": "WHOLEFDS",
        "account": {"id": "acct_1"},
        "category": {"id": "cat_groceries", "name": "Groceries"},
        "pending": False,
        "notes": None,
        "tags": [{"name": "shared"}],
    }
    t = map_transaction(raw)
    assert t.id == "tx_1"
    assert t.date == date(2026, 5, 15)
    assert t.amount == pytest.approx(-42.5)
    assert t.merchant == "Whole Foods"
    assert t.description == "WHOLEFDS"
    assert t.category_id == "cat_groceries"
    assert t.category_name == "Groceries"
    assert t.tags == ["shared"]


def test_map_category_extracts_group():
    raw = {"id": "cat_1", "name": "Groceries", "group": {"name": "Food"}, "icon": "🛒"}
    c = map_category(raw)
    assert c.name == "Groceries"
    assert c.group == "Food"


def test_extract_list_handles_plain_list():
    payload = [{"id": "a"}, {"id": "b"}]
    assert _extract_list(payload, "accounts") == payload


def test_extract_list_handles_key_wrapper():
    payload = {"accounts": [{"id": "a"}]}
    assert _extract_list(payload, "accounts") == [{"id": "a"}]


def test_extract_list_handles_edges_wrapper():
    payload = {"transactions": {"edges": [{"node": {"id": "t1"}}, {"node": {"id": "t2"}}]}}
    assert _extract_list(payload, "transactions") == [{"id": "t1"}, {"id": "t2"}]


def test_extract_list_unwraps_data():
    payload = {"data": {"accounts": [{"id": "a"}]}}
    assert _extract_list(payload, "accounts") == [{"id": "a"}]


def test_extract_list_returns_empty_when_missing():
    assert _extract_list({"foo": "bar"}, "accounts") == []


def test_net_worth_aggregates_by_type():
    from backend.app.models.monarch import Account

    accounts = [
        Account(id="1", name="Checking", type="depository", balance_current=5000),
        Account(id="2", name="Brokerage", type="investment", balance_current=200000),
        Account(id="3", name="Credit Card", type="credit", balance_current=-1500),
        Account(id="4", name="Mortgage", type="loan", balance_current=-300000),
        Account(id="5", name="Hidden", type="depository", balance_current=999, is_hidden=True),
    ]
    nw = MonarchClient.net_worth(accounts)
    assert nw.by_type == NetWorthByType(
        cash=5000.0, investment=200000.0, credit=-1500.0, loan=-300000.0
    )
    assert nw.total == pytest.approx(5000 + 200000 - 1500 - 300000)


def test_net_worth_handles_positive_signed_liabilities():
    """Liabilities reduce net worth even if Monarch reports them as positive."""
    from backend.app.models.monarch import Account

    accounts = [
        Account(id="1", name="Checking", type="depository", balance_current=5000),
        # Same debts as above but reported as positive balances.
        Account(id="2", name="Credit Card", type="credit", balance_current=1500),
        Account(id="3", name="Mortgage", type="loan", balance_current=300000),
    ]
    nw = MonarchClient.net_worth(accounts)
    assert nw.by_type.credit == -1500.0
    assert nw.by_type.loan == -300000.0
    assert nw.total == pytest.approx(5000 - 1500 - 300000)
