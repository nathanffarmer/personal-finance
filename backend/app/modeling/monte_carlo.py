"""Vectorized Monte Carlo retirement engine.

Simulates ``trials`` portfolio paths in real dollars. The trial axis is fully
vectorized in numpy; we loop only over the (~70) years. Returns are sourced
either from a block bootstrap of the historical series (default) or from a
multivariate-lognormal draw.
"""

from __future__ import annotations

import numpy as np

from ..models.retirement import (
    FailureBin,
    MonteCarloRequest,
    MonteCarloResult,
    PercentileBands,
    ScenarioInput,
)
from .glide_path import equity_share_schedule
from .returns import (
    block_bootstrap_returns,
    load_historical_series,
    lognormal_returns,
)
from .tax import estimate_tax_vectorized
from .withdrawal import vpw_rate_for_age


def _guaranteed_income(scenario: ScenarioInput, age: int) -> float:
    total = 0.0
    if scenario.social_security and age >= scenario.social_security.start_age:
        total += scenario.social_security.monthly_real * 12
    for pension in scenario.pensions:
        if age >= pension.start_age:
            total += pension.monthly_real * 12
    return total


def _one_off(scenario: ScenarioInput, age: int) -> float:
    return sum(c.amount_real for c in scenario.one_off_cashflows if c.age == age)


def run_monte_carlo(req: MonteCarloRequest) -> MonteCarloResult:
    scenario = req.scenario
    n_years = scenario.end_age - scenario.current_age + 1
    trials = req.trials
    ret_idx = scenario.retirement_age - scenario.current_age

    # Joint (equity, bond) real returns: shape (trials, n_years, 2).
    if req.method == "lognormal":
        ra = scenario.return_assumptions
        returns = lognormal_returns(
            trials=trials,
            years=n_years,
            equity_mean=ra.equity_mean,
            equity_sd=ra.equity_sd,
            bond_mean=ra.bond_mean,
            bond_sd=ra.bond_sd,
            correlation=ra.correlation,
            seed=req.seed,
        )
    else:
        series = load_historical_series()
        returns = block_bootstrap_returns(
            series,
            trials=trials,
            years=n_years,
            block_size=req.block_size,
            seed=req.seed,
        )

    eq_schedule = equity_share_schedule(scenario)
    cash_share = scenario.asset_allocation.cash

    balance = np.full(trials, float(scenario.current_portfolio))
    # Per-year balance history for percentile bands.
    history = np.zeros((trials, n_years))

    # Withdrawal-strategy per-trial state.
    strat = scenario.withdrawal_strategy
    initial_target = np.zeros(trials)  # for four_percent / gk seeding
    gk_withdrawal = np.zeros(trials)  # for guyton_klinger
    gk_seeded = False

    for i in range(n_years):
        age = scenario.current_age + i
        eq = float(eq_schedule[i])
        bond = max(0.0, 1.0 - eq - cash_share)
        # Portfolio return = eq * equity_return + bond * bond_return (cash 0% real).
        port_return = eq * returns[:, i, 0] + bond * returns[:, i, 1]

        if age < scenario.retirement_age:
            balance = balance * (1.0 + port_return) + scenario.annual_contributions
        else:
            guaranteed = _guaranteed_income(scenario, age)
            years_remaining = scenario.end_age - age
            gross = _withdrawal_vector(
                scenario=scenario,
                age=age,
                balance=balance,
                guaranteed=guaranteed,
                years_remaining=years_remaining,
                # max(ret_idx, 0) so an already-retired scenario seeds the
                # four-percent target at year 0 instead of never.
                first_retirement_year=(i == max(ret_idx, 0)),
                initial_target=initial_target,
                gk_withdrawal=gk_withdrawal,
                gk_seeded=gk_seeded,
            )
            if strat.kind == "guyton_klinger":
                gk_seeded = True
            tax = estimate_tax_vectorized(gross, scenario.tax)
            balance = (balance - gross - tax) * (1.0 + port_return)

        balance = balance + _one_off(scenario, age)
        balance = np.maximum(balance, 0.0)
        history[:, i] = balance

    terminal = history[:, -1]
    success_rate = float(np.mean(terminal > 0.0))

    # Failure histogram: count of trials by the age at which the portfolio
    # first hit zero. Aggregated (not one entry per trial) to keep the
    # response small even when most trials fail.
    failure_ages: list[FailureBin] = []
    zero_mask = history <= 0.0
    failed = zero_mask.any(axis=1) & (terminal <= 0.0)
    if failed.any():
        first_zero = np.argmax(zero_mask, axis=1)
        failed_ages = scenario.current_age + first_zero[failed]
        unique_ages, counts = np.unique(failed_ages, return_counts=True)
        failure_ages = [
            FailureBin(age=int(a), count=int(c))
            for a, c in zip(unique_ages, counts, strict=True)
        ]

    pct = np.percentile(history, [5, 25, 50, 75, 95], axis=0)
    bands = PercentileBands(
        p5=[round(x, 2) for x in pct[0]],
        p25=[round(x, 2) for x in pct[1]],
        p50=[round(x, 2) for x in pct[2]],
        p75=[round(x, 2) for x in pct[3]],
        p95=[round(x, 2) for x in pct[4]],
    )
    term_pct = np.percentile(terminal, [5, 50, 95])

    return MonteCarloResult(
        trials=trials,
        method=req.method,
        success_rate=round(success_rate, 4),
        median_terminal_real=round(float(np.median(terminal)), 2),
        ages=[scenario.current_age + i for i in range(n_years)],
        percentiles=bands,
        terminal_p5=round(float(term_pct[0]), 2),
        terminal_p50=round(float(term_pct[1]), 2),
        terminal_p95=round(float(term_pct[2]), 2),
        failure_ages=failure_ages,
        scenario_echo=scenario,
    )


def _withdrawal_vector(
    *,
    scenario: ScenarioInput,
    age: int,
    balance: np.ndarray,
    guaranteed: float,
    years_remaining: int,
    first_retirement_year: bool,
    initial_target: np.ndarray,
    gk_withdrawal: np.ndarray,
    gk_seeded: bool,
) -> np.ndarray:
    """Gross portfolio withdrawal across all trials for one retirement year."""
    strat = scenario.withdrawal_strategy
    safe_balance = np.maximum(balance, 0.0)

    if strat.kind == "vpw":
        # VPW prescribes a portfolio withdrawal directly; guaranteed income
        # (Social Security/pensions) is separate spending money and does not
        # offset it. This matches the deterministic engine.
        gross = vpw_rate_for_age(age) * safe_balance
        return np.minimum(gross, safe_balance)

    if strat.kind == "fixed_real":
        target = np.full_like(balance, float(scenario.annual_spend_real))
    elif strat.kind == "four_percent":
        rate = float(strat.params.get("initial_rate", 0.04))
        if first_retirement_year:
            initial_target[:] = rate * safe_balance
        target = initial_target.copy()
    elif strat.kind == "guyton_klinger":
        target = _guyton_klinger_vector(
            strat, safe_balance, gk_withdrawal, gk_seeded, years_remaining
        )
    else:
        target = np.full_like(balance, float(scenario.annual_spend_real))

    # These strategies define a total spending target; guaranteed income
    # offsets the portfolio withdrawal. Cannot withdraw more than remains.
    gross = np.maximum(0.0, target - guaranteed)
    return np.minimum(gross, safe_balance)


def _guyton_klinger_vector(
    strat,
    balance: np.ndarray,
    gk_withdrawal: np.ndarray,
    gk_seeded: bool,
    years_remaining: int,
) -> np.ndarray:
    initial_rate = float(strat.params.get("initial_rate", 0.05))
    upper_pct = float(strat.params.get("upper_pct", 0.20))
    lower_pct = float(strat.params.get("lower_pct", 0.20))
    adj_pct = float(strat.params.get("adjustment_pct", 0.10))
    prosperity_years = int(strat.params.get("prosperity_years", 15))

    if not gk_seeded:
        gk_withdrawal[:] = initial_rate * balance
        return gk_withdrawal.copy()

    with np.errstate(divide="ignore", invalid="ignore"):
        current_rate = np.where(balance > 0, gk_withdrawal / balance, 0.0)

    upper_guard = initial_rate * (1.0 + upper_pct)
    lower_guard = initial_rate * (1.0 - lower_pct)
    # Per Guyton-Klinger, the capital-preservation rule (the cut) is waived
    # in the final prosperity_years of the plan; the prosperity rule (the
    # raise) always applies.
    waive_cut = years_remaining <= prosperity_years

    if not waive_cut:
        cut = current_rate > upper_guard
        gk_withdrawal[cut] *= 1.0 - adj_pct
    raise_mask = current_rate < lower_guard
    gk_withdrawal[raise_mask] *= 1.0 + adj_pct

    return gk_withdrawal.copy()
