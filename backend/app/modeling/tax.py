"""Simple bracketed-tax approximation for retirement withdrawals.

This is deliberately an approximation, clearly labelled as such. It applies
2025 US federal brackets to ordinary income and long-term capital gains, and
draws accounts in the conventional tax-efficient order:
taxable -> pre-tax -> Roth.
"""

from __future__ import annotations

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


def _tax_from_brackets(income: float, brackets: list[tuple[float, float]]) -> float:
    if income <= 0:
        return 0.0
    tax = 0.0
    for i, (threshold, rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if income <= threshold:
            break
        taxed = min(income, upper) - threshold
        tax += taxed * rate
    return tax


def estimate_tax_on_withdrawal(gross_withdrawal: float, config: TaxConfig) -> float:
    """Estimate total federal tax for one year's gross withdrawal.

    The gross withdrawal is split across account types by their configured
    shares. Taxable-account dollars: only the gain fraction is taxed at LTCG
    rates. Pre-tax dollars: taxed as ordinary income. Roth: untaxed.
    """
    if not config.enabled or gross_withdrawal <= 0:
        return 0.0

    status = config.filing_status
    ordinary_brackets = _ORDINARY_BRACKETS[status]
    ltcg_brackets = _LTCG_BRACKETS[status]
    std_deduction = _STD_DEDUCTION[status]

    from_taxable = gross_withdrawal * config.taxable_share
    from_pretax = gross_withdrawal * config.pretax_share
    # Roth share is untaxed.

    # Pre-tax withdrawal is ordinary income, reduced by the standard deduction.
    ordinary_income = max(0.0, from_pretax - std_deduction)
    ordinary_tax = _tax_from_brackets(ordinary_income, ordinary_brackets)

    # Taxable-account: only the gain portion is a realized capital gain.
    gain_fraction = max(0.0, 1.0 - config.taxable_basis_fraction)
    realized_gain = from_taxable * gain_fraction
    # LTCG brackets stack on top of ordinary income.
    ltcg_tax = _ltcg_tax(realized_gain, ordinary_income, ltcg_brackets)

    return ordinary_tax + ltcg_tax


def _ltcg_tax(
    gain: float, ordinary_income: float, brackets: list[tuple[float, float]]
) -> float:
    """LTCG is taxed in brackets that stack on top of ordinary income."""
    if gain <= 0:
        return 0.0
    tax = 0.0
    remaining = gain
    stack_base = ordinary_income
    for i, (threshold, rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        band_lo = max(threshold, stack_base)
        band_hi = upper
        if band_hi <= stack_base:
            continue
        room = band_hi - band_lo
        if room <= 0:
            continue
        taxed = min(remaining, room)
        tax += taxed * rate
        remaining -= taxed
        if remaining <= 0:
            break
    return tax
