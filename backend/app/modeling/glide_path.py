"""Equity-share-by-year schedules.

All functions return a 1-D numpy array of equity share (0..1) of length
``years``, one entry per simulated year starting at ``current_age``.
"""

from __future__ import annotations

import numpy as np

from ..models.retirement import AssetAllocation, GlidePath, ScenarioInput


def equity_share_schedule(scenario: ScenarioInput) -> np.ndarray:
    years = scenario.end_age - scenario.current_age + 1
    glide = scenario.glide_path
    base_alloc = scenario.asset_allocation
    if glide.kind == "static":
        return np.full(years, base_alloc.equity, dtype=float)
    if glide.kind == "bond_tent":
        return _bond_tent(scenario, years)
    if glide.kind == "rising_equity":
        return _rising_equity(scenario, years)
    return np.full(years, base_alloc.equity, dtype=float)


def _params(glide: GlidePath, key: str, default: float) -> float:
    val = glide.params.get(key, default)
    return float(val)


def _bond_tent(scenario: ScenarioInput, years: int) -> np.ndarray:
    """Linear ramp from start_equity to trough at retirement, then ramp back up.

    Inspired by Pfau & Kitces' bond-tent: derisk into retirement, then
    re-risk over ``recovery_years`` to ``end_equity``.
    """
    glide = scenario.glide_path
    base = scenario.asset_allocation.equity
    start = _params(glide, "start_equity", base)
    trough = _params(glide, "trough_equity", max(0.0, base - 0.2))
    end = _params(glide, "end_equity", base)
    recovery = int(_params(glide, "recovery_years", 10))

    ages = np.arange(scenario.current_age, scenario.current_age + years)
    eq = np.empty(years, dtype=float)
    ret_age = scenario.retirement_age
    # pre-retirement: linear from start at current_age to trough at retirement
    pre_mask = ages < ret_age
    if pre_mask.any():
        n_pre = int(pre_mask.sum())
        if n_pre == 1:
            eq[pre_mask] = start
        else:
            eq[pre_mask] = np.linspace(start, trough, n_pre)
    # retirement..retirement+recovery: linear from trough up to end
    rec_mask = (ages >= ret_age) & (ages < ret_age + recovery)
    if rec_mask.any():
        n_rec = int(rec_mask.sum())
        if n_rec == 1:
            eq[rec_mask] = end
        else:
            eq[rec_mask] = np.linspace(trough, end, n_rec)
    # post-recovery: flat at end
    post_mask = ages >= ret_age + recovery
    eq[post_mask] = end
    return np.clip(eq, 0.0, 1.0)


def _rising_equity(scenario: ScenarioInput, years: int) -> np.ndarray:
    """Static pre-retirement, rising linearly from trough to end after retirement."""
    glide = scenario.glide_path
    base = scenario.asset_allocation.equity
    trough = _params(glide, "trough_equity", max(0.0, base - 0.2))
    end = _params(glide, "end_equity", base)

    ages = np.arange(scenario.current_age, scenario.current_age + years)
    eq = np.empty(years, dtype=float)
    pre_mask = ages < scenario.retirement_age
    eq[pre_mask] = base
    post_mask = ~pre_mask
    n_post = int(post_mask.sum())
    if n_post > 0:
        eq[post_mask] = np.linspace(trough, end, n_post) if n_post > 1 else np.array([end])
    return np.clip(eq, 0.0, 1.0)


def allocation_at(scenario: ScenarioInput, eq_share: float) -> AssetAllocation:
    cash = scenario.asset_allocation.cash
    bond = max(0.0, 1.0 - eq_share - cash)
    return AssetAllocation(equity=eq_share, bond=bond, cash=cash)
