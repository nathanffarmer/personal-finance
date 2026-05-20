from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AssetAllocation(BaseModel):
    equity: float = Field(ge=0.0, le=1.0)
    bond: float = Field(ge=0.0, le=1.0)
    cash: float = Field(default=0.0, ge=0.0, le=1.0)


class CashFlowSpec(BaseModel):
    start_age: int
    monthly_real: float
    cola: bool = True


class OneOffCashFlow(BaseModel):
    age: int
    amount_real: float


WithdrawalKind = Literal["fixed_real", "four_percent", "guyton_klinger", "vpw"]
GlideKind = Literal["static", "bond_tent", "rising_equity"]


class WithdrawalStrategy(BaseModel):
    kind: WithdrawalKind = "four_percent"
    params: dict[str, Any] = Field(default_factory=dict)


class GlidePath(BaseModel):
    kind: GlideKind = "static"
    params: dict[str, Any] = Field(default_factory=dict)


class TaxConfig(BaseModel):
    enabled: bool = False
    filing_status: Literal["single", "mfj"] = "mfj"
    taxable_basis_fraction: float = 0.5
    pretax_share: float = 0.5
    roth_share: float = 0.1
    taxable_share: float = 0.4


class ReturnAssumptions(BaseModel):
    equity_mean: float = 0.06
    equity_sd: float = 0.17
    bond_mean: float = 0.02
    bond_sd: float = 0.06
    correlation: float = 0.1


class ScenarioInput(BaseModel):
    current_age: int = Field(ge=0, le=120)
    retirement_age: int
    end_age: int
    current_portfolio: float = Field(ge=0)
    asset_allocation: AssetAllocation
    annual_contributions: float = 0.0
    annual_spend_real: float
    social_security: CashFlowSpec | None = None
    pensions: list[CashFlowSpec] = Field(default_factory=list)
    one_off_cashflows: list[OneOffCashFlow] = Field(default_factory=list)
    withdrawal_strategy: WithdrawalStrategy = Field(default_factory=WithdrawalStrategy)
    glide_path: GlidePath = Field(default_factory=GlidePath)
    tax: TaxConfig = Field(default_factory=TaxConfig)
    return_assumptions: ReturnAssumptions = Field(default_factory=ReturnAssumptions)

    @model_validator(mode="after")
    def _check_ages(self) -> ScenarioInput:
        # retirement_age may be below current_age (already retired) — that is
        # valid. The breaking invariant is that the plan horizon covers both.
        if self.end_age < self.current_age:
            raise ValueError("end_age must be >= current_age")
        if self.end_age < self.retirement_age:
            raise ValueError("end_age must be >= retirement_age")
        return self


class DeterministicProjection(BaseModel):
    years: list[int]
    ages: list[int]
    balance_real: list[float]
    contributions: list[float]
    withdrawals: list[float]
    taxes: list[float]
    equity_share: list[float]
    bond_share: list[float]
    depleted_age: int | None


class PercentileBands(BaseModel):
    p5: list[float]
    p25: list[float]
    p50: list[float]
    p75: list[float]
    p95: list[float]


class MonteCarloRequest(BaseModel):
    scenario: ScenarioInput
    trials: int = 10000
    method: Literal["bootstrap", "lognormal"] = "bootstrap"
    block_size: int = 5
    seed: int | None = None


class MonteCarloResult(BaseModel):
    trials: int
    method: Literal["bootstrap", "lognormal"]
    success_rate: float
    median_terminal_real: float
    ages: list[int]
    percentiles: PercentileBands
    terminal_p5: float
    terminal_p50: float
    terminal_p95: float
    failure_ages: list[int]
    scenario_echo: ScenarioInput


class FireRequest(BaseModel):
    annual_spend: float
    current_age: int
    target_age: int
    swr: float = 0.04
    real_return: float = 0.05
    lean_factor: float = 0.6
    fat_factor: float = 2.0


class FireNumbers(BaseModel):
    lean_fire: float
    regular_fire: float
    fat_fire: float
    coast_fire: float
    swr_implied_multiple: float
