"""Historical real-return series + sampling utilities.

The series ships as ``data/historical_real_returns.csv`` and contains annual
real (CPI-adjusted) total returns for US equity and 10-year US Treasury.

To replace with a more authoritative dataset (Shiller, Damodaran), put a CSV
with the same columns (``year,equity,bond``) at the same path. All values are
decimal annual real returns (0.07 = 7%).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DATA_PATH = Path(os.path.dirname(__file__)).parent / "data" / "historical_real_returns.csv"


@dataclass(frozen=True)
class HistoricalSeries:
    years: np.ndarray  # shape (N,)
    equity: np.ndarray  # shape (N,) annual real returns
    bond: np.ndarray  # shape (N,)

    @property
    def n(self) -> int:
        return int(self.years.shape[0])


def load_historical_series(path: Path | None = None) -> HistoricalSeries:
    p = path or DATA_PATH
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    years = np.array([int(r["year"]) for r in rows])
    equity = np.array([float(r["equity"]) for r in rows])
    bond = np.array([float(r["bond"]) for r in rows])
    return HistoricalSeries(years=years, equity=equity, bond=bond)


def block_bootstrap_returns(
    series: HistoricalSeries,
    *,
    trials: int,
    years: int,
    block_size: int = 5,
    seed: int | None = None,
) -> np.ndarray:
    """Block-bootstrap of joint (equity, bond) annual real returns.

    Returns an array shape ``(trials, years, 2)`` where the last axis is
    ``[equity_return, bond_return]``. Sampling blocks of length ``block_size``
    preserves the cross-asset correlation and short-run autocorrelation
    present in the historical record.
    """
    if trials <= 0 or years <= 0:
        raise ValueError("trials and years must be positive")
    if block_size <= 0:
        raise ValueError("block_size must be positive")

    n = series.n
    rng = np.random.default_rng(seed)
    # Number of block draws needed to cover `years` after concatenation.
    blocks_per_trial = (years + block_size - 1) // block_size
    # Pick block start indices: any year from which a contiguous block could begin.
    starts = rng.integers(0, n, size=(trials, blocks_per_trial))

    # Build (trials, blocks_per_trial * block_size) index matrix mod n
    # so we wrap around the dataset if a block runs past the end.
    offsets = np.arange(block_size)
    # shape (trials, blocks_per_trial, block_size)
    idx = (starts[:, :, None] + offsets[None, None, :]) % n
    idx = idx.reshape(trials, -1)[:, :years]

    equity_paths = series.equity[idx]
    bond_paths = series.bond[idx]
    return np.stack([equity_paths, bond_paths], axis=-1)


def lognormal_returns(
    *,
    trials: int,
    years: int,
    equity_mean: float,
    equity_sd: float,
    bond_mean: float,
    bond_sd: float,
    correlation: float,
    seed: int | None = None,
) -> np.ndarray:
    """Multivariate-lognormal joint draws for (equity, bond) returns.

    Means and SDs are in arithmetic-return space (e.g. 0.07 and 0.17).
    Returns shape ``(trials, years, 2)``.
    """
    rng = np.random.default_rng(seed)
    # Convert arithmetic mean/sd to lognormal parameters (mu, sigma in log-space).
    def to_log(mean: float, sd: float) -> tuple[float, float]:
        m = 1.0 + mean
        v = sd**2
        sigma2 = np.log(1.0 + v / (m**2))
        mu = np.log(m) - 0.5 * sigma2
        return float(mu), float(np.sqrt(sigma2))

    mu_e, sigma_e = to_log(equity_mean, equity_sd)
    mu_b, sigma_b = to_log(bond_mean, bond_sd)

    mean = np.array([mu_e, mu_b])
    cov = np.array(
        [
            [sigma_e**2, correlation * sigma_e * sigma_b],
            [correlation * sigma_e * sigma_b, sigma_b**2],
        ]
    )
    draws = rng.multivariate_normal(mean=mean, cov=cov, size=(trials, years))
    return np.exp(draws) - 1.0


def annualized_summary(returns: np.ndarray) -> dict[str, float]:
    """Sanity-check helper: mean, sd, and stock/bond corr of a (trials,years,2) array."""
    flat = returns.reshape(-1, 2)
    eq = flat[:, 0]
    bd = flat[:, 1]
    return {
        "equity_mean": float(eq.mean()),
        "equity_sd": float(eq.std(ddof=1)),
        "bond_mean": float(bd.mean()),
        "bond_sd": float(bd.std(ddof=1)),
        "correlation": float(np.corrcoef(eq, bd)[0, 1]),
    }
