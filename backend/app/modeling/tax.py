"""Simple bracketed-tax approximation for retirement withdrawals.

This is deliberately an approximation, clearly labelled as such. It applies
2025 US federal brackets to ordinary income and long-term capital gains, and
draws accounts in the conventional tax-efficient order:
taxable -> pre-tax -> Roth.

All functions are numpy-vectorized so the Monte Carlo engine can tax every
trial in one call; the scalar helper delegates to the vectorized path.
"""

from __future__ import annotations

import numpy as np

from ..models.retirement import TaxConfig

# 2025 federal ordinary-income brackets (taxable income thresholds).
_ORDINARY_BRACKETS: dict[str, list[tuple[float, float]]] = {
    "single": [
        (0.0, 0.10),
        (11_925.0, 0.12),
        (48_475.0, 0.22),
        (103_350.0, 0.24),
        (197_300.0, 0.32),
        (250_525.0, 0.35),
        (626_350.0, 0.37),
    ],
    "mfj": [
        (0.0, 0.10),
        (23_850.0, 0.12),
        (96_950.0, 0.22),
        (206_700.0, 0.24),
        (394_600.0, 0.32),
        (501_050.0, 0.35),
        (751_600.0, 0.37),
    ],
}

# 2025 long-term capital gains brackets.
_LTCG_BRACKETS: dict[str, list[tuple[float, float]]] = {
    "single": [(0.0, 0.0), (48_350.0, 0.15), (533_400.0, 0.20)],
    "mfj": [(0.0, 0.0), (96_700.0, 0.15), (600_050.0, 0.20)],
}

# Standard deduction, 2025.
_STD_DEDUCTION = {"single": 15_000.0, "mfj": 30_000.0}


def _bracket_tax(income: np.ndarray, brackets: list[tuple[float, float]]) -> np.ndarray:
    """Cumulative progressive-bracket tax on ``income``, elementwise.

    Equivalent to integrating the marginal-rate step function over
    ``[0, income]``. ``income`` is clamped at 0, so negative values pay nothing.
    """
    income = np.maximum(income, 0.0)
    tax = np.zeros_like(income, dtype=float)
    for i, (threshold, rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else np.inf
        taxed = np.clip(np.minimum(income, upper) - threshold, 0.0, None)
        tax += taxed * rate
    return tax


def estimate_tax_vectorized(gross: np.ndarray, config: TaxConfig) -> np.ndarray:
    """Estimate federal tax for an array of gross withdrawals.

    Each withdrawal is split across account types by their configured shares.
    Taxable-account dollars: only the gain fraction is taxed at LTCG rates,
    which stack on top of ordinary income. Pre-tax dollars: ordinary income.
    Roth: untaxed.
    """
    gross = np.asarray(gross, dtype=float)
    if not config.enabled:
        return np.zeros_like(gross)

    status = config.filing_status
    ordinary_brackets = _ORDINARY_BRACKETS[status]
    ltcg_brackets = _LTCG_BRACKETS[status]
    std_deduction = _STD_DEDUCTION[status]

    from_taxable = gross * config.taxable_share
    from_pretax = gross * config.pretax_share
    # Roth share is untaxed.

    # Pre-tax withdrawal is ordinary income, reduced by the standard deduction.
    ordinary_income = np.clip(from_pretax - std_deduction, 0.0, None)
    ordinary_tax = _bracket_tax(ordinary_income, ordinary_brackets)

    # Taxable-account: only the gain portion is a realized capital gain.
    gain_fraction = max(0.0, 1.0 - config.taxable_basis_fraction)
    realized_gain = from_taxable * gain_fraction
    # LTCG stacks on top of ordinary income: the tax on the gain band is the
    # cumulative bracket tax at (ordinary + gain) minus that at (ordinary).
    ltcg_tax = _bracket_tax(ordinary_income + realized_gain, ltcg_brackets) - _bracket_tax(
        ordinary_income, ltcg_brackets
    )

    total = ordinary_tax + ltcg_tax
    # No tax owed where there was no withdrawal.
    return np.where(gross > 0.0, total, 0.0)


def estimate_tax_on_withdrawal(gross_withdrawal: float, config: TaxConfig) -> float:
    """Scalar wrapper around :func:`estimate_tax_vectorized`."""
    if not config.enabled or gross_withdrawal <= 0:
        return 0.0
    return float(estimate_tax_vectorized(np.array([gross_withdrawal]), config)[0])
