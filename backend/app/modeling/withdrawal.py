"""Withdrawal-strategy targets.

Each function takes (scenario, prior_state) and returns the target withdrawal
in *real* dollars for the current year. They are stateless between trials —
callers pass a per-trial state dict.
"""

from __future__ import annotations

from typing import Any

from ..models.retirement import ScenarioInput, WithdrawalStrategy


def vpw_rate_for_age(age: int) -> float:
    """Bogleheads variable percentage withdrawal table (60/40 equity blend).

    Approximated piecewise; full table available at the Bogleheads wiki.
    """
    # Selected anchor points from the Bogleheads VPW table (60/40).
    anchors = {
        50: 0.0364,
        55: 0.0390,
        60: 0.0432,
        65: 0.0488,
        70: 0.0563,
        75: 0.0667,
        80: 0.0817,
        85: 0.1042,
        90: 0.1408,
        95: 0.2058,
        100: 0.3333,
    }
    if age <= 50:
        return anchors[50]
    if age >= 100:
        return anchors[100]
    keys = sorted(anchors.keys())
    for i in range(len(keys) - 1):
        if keys[i] <= age <= keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            frac = (age - lo) / (hi - lo)
            return anchors[lo] + frac * (anchors[hi] - anchors[lo])
    return anchors[max(keys)]


def withdrawal_for_year(
    *,
    scenario: ScenarioInput,
    age: int,
    balance: float,
    state: dict[str, Any],
    years_remaining: int,
) -> tuple[float, dict[str, Any]]:
    """Return (withdrawal_real, updated_state) for one year, age >= retirement_age.

    state is a mutable per-trial dict; for GK, we track ``initial_rate``,
    ``initial_balance`` to evaluate guardrails. Caller is responsible for
    not calling this before retirement_age.
    """
    if balance <= 0:
        return 0.0, state
    strat = scenario.withdrawal_strategy
    if strat.kind == "fixed_real":
        return float(scenario.annual_spend_real), state
    if strat.kind == "four_percent":
        # Bengen: 4% of portfolio AT retirement, fixed in real terms thereafter.
        if "initial_target" not in state:
            rate = float(strat.params.get("initial_rate", 0.04))
            state = {**state, "initial_target": rate * balance}
        return float(state["initial_target"]), state
    if strat.kind == "guyton_klinger":
        return _guyton_klinger(scenario, balance, state, years_remaining)
    if strat.kind == "vpw":
        return float(vpw_rate_for_age(age) * balance), state
    return float(scenario.annual_spend_real), state


def _guyton_klinger(
    scenario: ScenarioInput,
    balance: float,
    state: dict[str, Any],
    years_remaining: int,
) -> tuple[float, dict[str, Any]]:
    strat: WithdrawalStrategy = scenario.withdrawal_strategy
    initial_rate = float(strat.params.get("initial_rate", 0.05))
    upper_pct = float(strat.params.get("upper_pct", 0.20))
    lower_pct = float(strat.params.get("lower_pct", 0.20))
    adj_pct = float(strat.params.get("adjustment_pct", 0.10))
    prosperity_years = int(strat.params.get("prosperity_years", 15))

    if "withdrawal" not in state:
        # First year of retirement: set initial withdrawal.
        withdrawal = initial_rate * balance
        return withdrawal, {**state, "withdrawal": withdrawal}

    withdrawal = float(state["withdrawal"])
    current_rate = withdrawal / balance if balance > 0 else 0.0

    upper_guard = initial_rate * (1.0 + upper_pct)
    lower_guard = initial_rate * (1.0 - lower_pct)

    # Per Guyton-Klinger, the capital-preservation rule (the cut) is waived
    # in the final ``prosperity_years`` of the plan; the prosperity rule
    # (the raise) always applies.
    waive_cut = years_remaining <= prosperity_years
    new_state = dict(state)
    new_state.setdefault("guardrail_events", [])

    if current_rate > upper_guard and not waive_cut:
        withdrawal *= 1.0 - adj_pct
        new_state["guardrail_events"] = [*new_state["guardrail_events"], "cut"]
    elif current_rate < lower_guard:
        withdrawal *= 1.0 + adj_pct
        new_state["guardrail_events"] = [*new_state["guardrail_events"], "raise"]

    new_state["withdrawal"] = withdrawal
    return float(withdrawal), new_state
