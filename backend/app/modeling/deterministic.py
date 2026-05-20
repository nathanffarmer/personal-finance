"""Deterministic year-by-year retirement projection.

All values are real (today's dollars). Uses the allocation-weighted expected
return from the scenario's return assumptions.
"""

from __future__ import annotations

from ..models.retirement import DeterministicProjection, ScenarioInput
from .glide_path import equity_share_schedule
from .tax import estimate_tax_on_withdrawal
from .withdrawal import vpw_rate_for_age, withdrawal_for_year


def _cashflow_income(scenario: ScenarioInput, age: int) -> float:
    """Annual real income from Social Security + pensions at a given age."""
    total = 0.0
    if scenario.social_security and age >= scenario.social_security.start_age:
        total += scenario.social_security.monthly_real * 12
    for pension in scenario.pensions:
        if age >= pension.start_age:
            total += pension.monthly_real * 12
    return total


def _one_off(scenario: ScenarioInput, age: int) -> float:
    return sum(c.amount_real for c in scenario.one_off_cashflows if c.age == age)


def project_deterministic(scenario: ScenarioInput) -> DeterministicProjection:
    n_years = scenario.end_age - scenario.current_age + 1
    eq_schedule = equity_share_schedule(scenario)
    ra = scenario.return_assumptions

    balance = scenario.current_portfolio
    years: list[int] = []
    ages: list[int] = []
    balances: list[float] = []
    contributions: list[float] = []
    withdrawals: list[float] = []
    taxes: list[float] = []
    eq_shares: list[float] = []
    bond_shares: list[float] = []
    depleted_age: int | None = None

    cash_share = scenario.asset_allocation.cash
    state: dict = {}

    for i in range(n_years):
        age = scenario.current_age + i
        eq = float(eq_schedule[i])
        bond = max(0.0, 1.0 - eq - cash_share)
        # Allocation-weighted expected real return (cash assumed 0% real).
        exp_return = eq * ra.equity_mean + bond * ra.bond_mean

        contribution = 0.0
        withdrawal = 0.0
        tax = 0.0

        if age < scenario.retirement_age:
            contribution = scenario.annual_contributions
            balance = balance * (1.0 + exp_return) + contribution
        else:
            years_remaining = scenario.end_age - age
            guaranteed = _cashflow_income(scenario, age)
            if scenario.withdrawal_strategy.kind == "vpw":
                gross = vpw_rate_for_age(age) * max(balance, 0.0)
            else:
                target, state = withdrawal_for_year(
                    scenario=scenario,
                    age=age,
                    balance=max(balance, 0.0),
                    state=state,
                    years_remaining=years_remaining,
                )
                gross = max(0.0, target - guaranteed)
            tax = estimate_tax_on_withdrawal(gross, scenario.tax)
            withdrawal = gross
            balance = (balance - withdrawal - tax) * (1.0 + exp_return)

        balance += _one_off(scenario, age)
        if balance <= 0 and depleted_age is None:
            depleted_age = age
            balance = 0.0

        years.append(i)
        ages.append(age)
        balances.append(round(balance, 2))
        contributions.append(round(contribution, 2))
        withdrawals.append(round(withdrawal, 2))
        taxes.append(round(tax, 2))
        eq_shares.append(round(eq, 4))
        bond_shares.append(round(bond, 4))

    return DeterministicProjection(
        years=years,
        ages=ages,
        balance_real=balances,
        contributions=contributions,
        withdrawals=withdrawals,
        taxes=taxes,
        equity_share=eq_shares,
        bond_share=bond_shares,
        depleted_age=depleted_age,
    )
