"""FIRE number formulas.

All numbers are real (today's dollars).
"""

from __future__ import annotations

from ..models.retirement import FireNumbers, FireRequest


def compute_fire_numbers(req: FireRequest) -> FireNumbers:
    """Standard FIRE multipliers.

    - regular_fire: ``annual_spend / swr``; the 4% rule gives 25x.
    - lean_fire: ``regular_fire`` of ``lean_factor * annual_spend``.
    - fat_fire: ``regular_fire`` of ``fat_factor * annual_spend``.
    - coast_fire: amount that, left to compound at ``real_return`` until
      ``target_age``, lands at ``regular_fire``.
    """
    if req.swr <= 0:
        raise ValueError("swr must be > 0")
    if req.target_age < req.current_age:
        raise ValueError("target_age must be >= current_age")

    regular = req.annual_spend / req.swr
    lean = (req.lean_factor * req.annual_spend) / req.swr
    fat = (req.fat_factor * req.annual_spend) / req.swr
    years_to_target = req.target_age - req.current_age
    growth = (1.0 + req.real_return) ** years_to_target if years_to_target > 0 else 1.0
    coast = regular / growth

    return FireNumbers(
        lean_fire=lean,
        regular_fire=regular,
        fat_fire=fat,
        coast_fire=coast,
        swr_implied_multiple=1.0 / req.swr,
    )
