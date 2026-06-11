import pytest

from backend.app.services.sheets_client import (
    _assumptions_from_ranges,
    _parse_cashflow_table,
    _parse_json_cell,
    _parse_oneoffs,
    _parse_targets,
    _scalar,
    _to_float,
    _to_int,
)


def test_to_float_strips_currency_and_commas():
    assert _to_float("$1,234.56") == pytest.approx(1234.56)
    assert _to_float("12.5%") == pytest.approx(12.5)
    assert _to_float(None) is None
    assert _to_float("") is None
    assert _to_float("abc") is None
    assert _to_float(42) == 42.0


def test_to_int_truncates_floats():
    assert _to_int("35") == 35
    assert _to_int("35.9") == 35
    assert _to_int(None) is None


def test_scalar_returns_first_cell():
    assert _scalar([["hello"]]) == "hello"
    assert _scalar(None) is None
    assert _scalar([]) is None
    assert _scalar([[]]) is None


def test_parse_json_cell_handles_string_and_dict_and_garbage():
    assert _parse_json_cell([['{"a": 1}']]) == {"a": 1}
    assert _parse_json_cell([[{"a": 2}]]) == {"a": 2}
    assert _parse_json_cell([["not json"]]) == {}
    assert _parse_json_cell(None) == {}


def test_parse_cashflow_table_skips_invalid_rows():
    rows = [
        ["67", "2500", "true"],
        ["", "", ""],
        ["62", 1800],
        ["bogus", "data"],
    ]
    flows = _parse_cashflow_table(rows)
    assert len(flows) == 2
    assert flows[0].start_age == 67
    assert flows[0].monthly_real == 2500
    assert flows[0].cola is True
    assert flows[1].start_age == 62
    assert flows[1].cola is True


def test_parse_cashflow_handles_false_cola():
    flows = _parse_cashflow_table([["62", 1800, "false"]])
    assert flows[0].cola is False


def test_parse_oneoffs():
    rows = [["50", "-25000"], ["65", 30000]]
    items = _parse_oneoffs(rows)
    assert len(items) == 2
    assert items[0].amount_real == -25000
    assert items[1].age == 65


def test_parse_targets():
    rows = [["35", "$500,000"], ["45", "1500000"]]
    targets = _parse_targets(rows)
    assert targets[0].age == 35
    assert targets[0].target_net_worth == 500000


def test_assumptions_from_ranges_full():
    named = {
        "assumption_current_age": [["35"]],
        "assumption_retirement_age": [["55"]],
        "assumption_end_age": [["95"]],
        "assumption_annual_spend_real": [["$80,000"]],
        "assumption_annual_contributions": [["$40,000"]],
        "assumption_swr": [["0.04"]],
        "assumption_equity_mean": [["0.07"]],
        "assumption_equity_sd": [["0.17"]],
        "assumption_bond_mean": [["0.02"]],
        "assumption_bond_sd": [["0.06"]],
        "assumption_correlation": [["0.1"]],
        "assumption_glide_kind": [["bond_tent"]],
        "assumption_glide_params": [
            ['{"start_equity":0.8,"trough_equity":0.4,"end_equity":0.6,"recovery_years":10}']
        ],
        "assumption_withdrawal_kind": [["guyton_klinger"]],
        "assumption_withdrawal_params": [
            ['{"initial_rate":0.05,"upper_pct":0.2,"lower_pct":0.2,"adjustment_pct":0.1,"prosperity_years":15}']
        ],
        "social_security_table": [["67", "2500"]],
        "pensions_table": [],
        "one_offs_table": [["50", "-25000"]],
    }
    a = _assumptions_from_ranges(named)
    assert a.current_age == 35
    assert a.annual_spend_real == 80000
    assert a.swr == pytest.approx(0.04)
    assert a.glide_kind == "bond_tent"
    assert a.glide_params is not None
    assert a.glide_params.start_equity == 0.8
    assert a.withdrawal_kind == "guyton_klinger"
    assert a.withdrawal_params is not None
    assert a.withdrawal_params.initial_rate == 0.05
    assert a.social_security is not None
    assert a.social_security.monthly_real == 2500
    assert len(a.one_offs) == 1
    assert a.one_offs[0].amount_real == -25000


def test_assumptions_from_ranges_tolerates_missing():
    """If the user hasn't set any named ranges yet, parser returns an empty Assumptions."""
    named = {k: None for k in ["assumption_current_age", "assumption_glide_params"]}
    a = _assumptions_from_ranges(named)
    assert a.current_age is None
    assert a.glide_params is None
    assert a.one_offs == []
