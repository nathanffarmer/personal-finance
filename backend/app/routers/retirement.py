from __future__ import annotations

from fastapi import APIRouter, Depends

from ..modeling.deterministic import project_deterministic
from ..modeling.fire import compute_fire_numbers
from ..modeling.monte_carlo import run_monte_carlo
from ..models.retirement import (
    AssetAllocation,
    DeterministicProjection,
    FireNumbers,
    FireRequest,
    MonteCarloRequest,
    MonteCarloResult,
    ScenarioInput,
)
from ..services.monarch_client import MonarchClient, get_monarch_client

router = APIRouter(prefix="/api/retirement", tags=["retirement"])

# Guard against accidentally huge or empty trial counts.
MIN_TRIALS = 100
MAX_TRIALS = 50_000


@router.post("/project/deterministic", response_model=DeterministicProjection)
async def deterministic(scenario: ScenarioInput) -> DeterministicProjection:
    return project_deterministic(scenario)


@router.post("/project/monte_carlo", response_model=MonteCarloResult)
async def monte_carlo(req: MonteCarloRequest) -> MonteCarloResult:
    req.trials = max(MIN_TRIALS, min(MAX_TRIALS, req.trials))
    return run_monte_carlo(req)


@router.post("/fire/numbers", response_model=FireNumbers)
async def fire_numbers(req: FireRequest) -> FireNumbers:
    return compute_fire_numbers(req)


@router.post("/scenario/from_monarch", response_model=ScenarioInput)
async def scenario_from_monarch(
    partial: ScenarioInput,
    monarch: MonarchClient = Depends(get_monarch_client),
) -> ScenarioInput:
    """Hydrate current_portfolio + asset_allocation from live Monarch data.

    The caller sends a ScenarioInput with their planning assumptions; this
    endpoint overwrites the portfolio value and allocation with real numbers
    derived from investment-account holdings.
    """
    accounts = await monarch.list_accounts()
    investment_accounts = [
        a for a in accounts if a.type == "investment" and not a.is_hidden
    ]

    equity_value = 0.0
    bond_value = 0.0
    cash_value = 0.0
    other_value = 0.0
    total = 0.0

    for account in investment_accounts:
        holdings = await monarch.list_holdings(account.id)
        if not holdings:
            # No holdings detail: treat the balance as unclassified.
            other_value += account.balance_current
            total += account.balance_current
            continue
        for h in holdings:
            total += h.market_value
            if h.asset_class in ("us_equity", "intl_equity"):
                equity_value += h.market_value
            elif h.asset_class == "bond":
                bond_value += h.market_value
            elif h.asset_class == "cash":
                cash_value += h.market_value
            else:
                other_value += h.market_value

    # Cash sitting in depository accounts also counts toward the portfolio.
    for account in accounts:
        if account.type == "depository" and not account.is_hidden:
            cash_value += account.balance_current
            total += account.balance_current

    if total <= 0:
        # Nothing classifiable; keep the caller's assumptions untouched.
        return partial

    # Split unclassified holdings evenly between equity and bond buckets.
    equity_share = (equity_value + other_value * 0.5) / total
    bond_share = (bond_value + other_value * 0.5) / total
    cash_alloc = cash_value / total
    # Re-normalize to guard against float drift.
    s = equity_share + bond_share + cash_alloc
    if s > 0:
        equity_share, bond_share, cash_alloc = (
            equity_share / s,
            bond_share / s,
            cash_alloc / s,
        )

    return partial.model_copy(
        update={
            "current_portfolio": round(total, 2),
            "asset_allocation": AssetAllocation(
                equity=round(equity_share, 4),
                bond=round(bond_share, 4),
                cash=round(cash_alloc, 4),
            ),
        }
    )
