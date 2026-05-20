"""Retirement modeling tests against published reference cases."""

import numpy as np
import pytest

from backend.app.modeling.deterministic import project_deterministic
from backend.app.modeling.fire import compute_fire_numbers
from backend.app.modeling.glide_path import equity_share_schedule
from backend.app.modeling.monte_carlo import run_monte_carlo
from backend.app.modeling.returns import (
    block_bootstrap_returns,
    load_historical_series,
    lognormal_returns,
)
from backend.app.modeling.tax import estimate_tax_on_withdrawal
from backend.app.modeling.withdrawal import vpw_rate_for_age
from backend.app.models.retirement import (
    AssetAllocation,
    CashFlowSpec,
    FireRequest,
    GlidePath,
    MonteCarloRequest,
    OneOffCashFlow,
    ReturnAssumptions,
    ScenarioInput,
    TaxConfig,
    WithdrawalStrategy,
)

# ---- FIRE numbers ----------------------------------------------------------

def test_fire_regular_is_25x_at_4pct():
    fire = compute_fire_numbers(
        FireRequest(annual_spend=40_000, current_age=30, target_age=60, swr=0.04)
    )
    assert fire.regular_fire == pytest.approx(1_000_000)
    assert fire.swr_implied_multiple == pytest.approx(25.0)


def test_fire_lean_and_fat_scale():
    fire = compute_fire_numbers(
        FireRequest(
            annual_spend=50_000,
            current_age=30,
            target_age=60,
            swr=0.04,
            lean_factor=0.6,
            fat_factor=2.0,
        )
    )
    assert fire.lean_fire == pytest.approx(0.6 * 50_000 / 0.04)
    assert fire.fat_fire == pytest.approx(2.0 * 50_000 / 0.04)


def test_coast_fire_discounts_to_present():
    fire = compute_fire_numbers(
        FireRequest(
            annual_spend=40_000,
            current_age=30,
            target_age=60,
            swr=0.04,
            real_return=0.05,
        )
    )
    # 1,000,000 / 1.05^30
    expected = 1_000_000 / (1.05**30)
    assert fire.coast_fire == pytest.approx(expected)
    assert fire.coast_fire < fire.regular_fire


def test_fire_rejects_bad_inputs():
    with pytest.raises(ValueError):
        compute_fire_numbers(
            FireRequest(annual_spend=1, current_age=60, target_age=50, swr=0.04)
        )


# ---- Deterministic projection ---------------------------------------------

def _simple_scenario(**overrides) -> ScenarioInput:
    base = dict(
        current_age=65,
        retirement_age=65,
        end_age=95,
        current_portfolio=1_000_000,
        asset_allocation=AssetAllocation(equity=0.6, bond=0.4, cash=0.0),
        annual_contributions=0.0,
        annual_spend_real=40_000,
        withdrawal_strategy=WithdrawalStrategy(kind="fixed_real"),
        glide_path=GlidePath(kind="static"),
        return_assumptions=ReturnAssumptions(
            equity_mean=0.05, bond_mean=0.05, equity_sd=0.0, bond_sd=0.0
        ),
    )
    base.update(overrides)
    return ScenarioInput(**base)


def test_deterministic_constant_return_matches_hand_calc():
    # 1M, withdraw 40k/yr, 5% return on a 60/40 with both means 5%.
    scenario = _simple_scenario()
    proj = project_deterministic(scenario)
    # Year 0: (1,000,000 - 40,000) * 1.05 = 1,008,000
    assert proj.balance_real[0] == pytest.approx(1_008_000, rel=1e-6)
    assert proj.ages[0] == 65
    assert proj.ages[-1] == 95
    assert proj.depleted_age is None


def test_deterministic_depletes_when_spend_too_high():
    scenario = _simple_scenario(annual_spend_real=200_000)
    proj = project_deterministic(scenario)
    assert proj.depleted_age is not None
    assert proj.balance_real[-1] == 0.0


def test_deterministic_preretirement_contributions_grow():
    scenario = _simple_scenario(
        current_age=40,
        retirement_age=65,
        annual_contributions=20_000,
    )
    proj = project_deterministic(scenario)
    # Year 0 (age 40, pre-retirement): 1,000,000 * 1.05 + 20,000
    assert proj.balance_real[0] == pytest.approx(1_050_000 + 20_000, rel=1e-6)
    assert proj.contributions[0] == 20_000
    assert proj.withdrawals[0] == 0.0


def test_deterministic_one_off_cashflow_applied():
    scenario = _simple_scenario(
        one_off_cashflows=[OneOffCashFlow(age=70, amount_real=100_000)],
    )
    proj = project_deterministic(scenario)
    idx = proj.ages.index(70)
    idx_prev = idx - 1
    # The age-70 balance should be ~100k above the no-windfall trajectory.
    no_windfall = project_deterministic(_simple_scenario())
    assert proj.balance_real[idx] - no_windfall.balance_real[idx] == pytest.approx(
        100_000, rel=1e-6
    )
    assert idx_prev >= 0


def test_deterministic_social_security_reduces_withdrawal():
    scenario = _simple_scenario(
        social_security=CashFlowSpec(start_age=70, monthly_real=2_000),
    )
    proj = project_deterministic(scenario)
    idx_before = proj.ages.index(69)
    idx_after = proj.ages.index(70)
    # Before SS: withdraw full 40k. After SS (24k/yr): withdraw 16k.
    assert proj.withdrawals[idx_before] == pytest.approx(40_000)
    assert proj.withdrawals[idx_after] == pytest.approx(40_000 - 24_000)


# ---- Glide paths -----------------------------------------------------------

def test_static_glide_is_constant():
    scenario = _simple_scenario(glide_path=GlidePath(kind="static"))
    sched = equity_share_schedule(scenario)
    assert np.allclose(sched, 0.6)


def test_bond_tent_dips_at_retirement():
    scenario = _simple_scenario(
        current_age=55,
        retirement_age=65,
        glide_path=GlidePath(
            kind="bond_tent",
            params={
                "start_equity": 0.8,
                "trough_equity": 0.4,
                "end_equity": 0.6,
                "recovery_years": 10,
            },
        ),
    )
    sched = equity_share_schedule(scenario)
    ages = list(range(55, 96))
    retire_idx = ages.index(65)
    # Equity share should fall into retirement, then rise.
    assert sched[0] == pytest.approx(0.8, abs=0.05)
    assert sched[retire_idx] <= sched[0]
    assert sched[-1] == pytest.approx(0.6, abs=0.01)
    assert sched.min() == pytest.approx(0.4, abs=0.05)


# ---- Returns sampling ------------------------------------------------------

def test_historical_series_loads():
    series = load_historical_series()
    assert series.n >= 50
    assert series.equity.shape == series.bond.shape


def test_block_bootstrap_shape_and_determinism():
    series = load_historical_series()
    a = block_bootstrap_returns(series, trials=100, years=30, block_size=5, seed=42)
    b = block_bootstrap_returns(series, trials=100, years=30, block_size=5, seed=42)
    assert a.shape == (100, 30, 2)
    assert np.array_equal(a, b)


def test_lognormal_returns_recover_target_mean():
    draws = lognormal_returns(
        trials=20_000,
        years=30,
        equity_mean=0.07,
        equity_sd=0.17,
        bond_mean=0.02,
        bond_sd=0.06,
        correlation=0.1,
        seed=1,
    )
    eq = draws[:, :, 0]
    assert eq.mean() == pytest.approx(0.07, abs=0.01)


# ---- Monte Carlo -----------------------------------------------------------

def test_monte_carlo_4pct_30yr_success_is_high():
    """Trinity-style sanity check: 4% rule, 60/40, 30 years should mostly succeed."""
    scenario = _simple_scenario(
        annual_spend_real=40_000,
        withdrawal_strategy=WithdrawalStrategy(kind="four_percent"),
    )
    result = run_monte_carlo(
        MonteCarloRequest(scenario=scenario, trials=2_000, method="bootstrap", seed=7)
    )
    assert 0.80 <= result.success_rate <= 1.0
    assert len(result.percentiles.p50) == 31
    assert result.ages[0] == 65


def test_monte_carlo_is_deterministic_with_seed():
    scenario = _simple_scenario(
        withdrawal_strategy=WithdrawalStrategy(kind="four_percent")
    )
    r1 = run_monte_carlo(
        MonteCarloRequest(scenario=scenario, trials=500, method="bootstrap", seed=99)
    )
    r2 = run_monte_carlo(
        MonteCarloRequest(scenario=scenario, trials=500, method="bootstrap", seed=99)
    )
    assert r1.success_rate == r2.success_rate
    assert r1.percentiles.p50 == r2.percentiles.p50


def test_monte_carlo_overspending_mostly_fails():
    scenario = _simple_scenario(
        annual_spend_real=150_000,
        withdrawal_strategy=WithdrawalStrategy(kind="fixed_real"),
    )
    result = run_monte_carlo(
        MonteCarloRequest(scenario=scenario, trials=1_000, method="bootstrap", seed=3)
    )
    assert result.success_rate < 0.5
    assert len(result.failure_ages) > 0


def test_guyton_klinger_beats_fixed_real_at_same_initial_rate():
    """GK guardrails cut spending in downturns, so success should not be worse."""
    gk_scenario = _simple_scenario(
        annual_spend_real=50_000,
        withdrawal_strategy=WithdrawalStrategy(
            kind="guyton_klinger", params={"initial_rate": 0.05}
        ),
    )
    fixed_scenario = _simple_scenario(
        annual_spend_real=50_000,
        withdrawal_strategy=WithdrawalStrategy(kind="fixed_real"),
    )
    gk = run_monte_carlo(
        MonteCarloRequest(scenario=gk_scenario, trials=2_000, method="bootstrap", seed=11)
    )
    fixed = run_monte_carlo(
        MonteCarloRequest(
            scenario=fixed_scenario, trials=2_000, method="bootstrap", seed=11
        )
    )
    assert gk.success_rate >= fixed.success_rate


def test_lognormal_method_runs():
    scenario = _simple_scenario(
        withdrawal_strategy=WithdrawalStrategy(kind="four_percent")
    )
    result = run_monte_carlo(
        MonteCarloRequest(scenario=scenario, trials=500, method="lognormal", seed=5)
    )
    assert result.method == "lognormal"
    assert 0.0 <= result.success_rate <= 1.0


# ---- VPW table -------------------------------------------------------------

def test_vpw_rate_increases_with_age():
    assert vpw_rate_for_age(60) < vpw_rate_for_age(75) < vpw_rate_for_age(90)
    assert vpw_rate_for_age(45) == vpw_rate_for_age(50)  # clamped below 50


# ---- Tax -------------------------------------------------------------------

def test_tax_disabled_returns_zero():
    assert estimate_tax_on_withdrawal(100_000, TaxConfig(enabled=False)) == 0.0


def test_tax_on_pretax_withdrawal_is_positive():
    config = TaxConfig(
        enabled=True,
        filing_status="mfj",
        pretax_share=1.0,
        roth_share=0.0,
        taxable_share=0.0,
    )
    tax = estimate_tax_on_withdrawal(100_000, config)
    assert tax > 0
    # Effective rate should be modest after the standard deduction.
    assert 0.0 < tax / 100_000 < 0.20


def test_roth_withdrawal_is_untaxed():
    config = TaxConfig(
        enabled=True,
        pretax_share=0.0,
        roth_share=1.0,
        taxable_share=0.0,
    )
    assert estimate_tax_on_withdrawal(100_000, config) == 0.0
