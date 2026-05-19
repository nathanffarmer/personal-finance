from __future__ import annotations

from pydantic import BaseModel, Field


class GlideParams(BaseModel):
    start_equity: float = 0.6
    trough_equity: float = 0.4
    end_equity: float = 0.6
    recovery_years: int = 10


class WithdrawalParams(BaseModel):
    initial_rate: float = 0.04
    upper_pct: float = 0.20
    lower_pct: float = 0.20
    adjustment_pct: float = 0.10
    prosperity_years: int = 15


class CashFlow(BaseModel):
    start_age: int
    monthly_real: float
    cola: bool = True


class OneOff(BaseModel):
    age: int
    amount_real: float


class Assumptions(BaseModel):
    """Parsed contents of the `Assumptions` tab in the user's sheet."""

    current_age: int | None = None
    retirement_age: int | None = None
    end_age: int | None = None
    annual_spend_real: float | None = None
    annual_contributions: float | None = None
    swr: float | None = None
    equity_mean: float | None = None
    equity_sd: float | None = None
    bond_mean: float | None = None
    bond_sd: float | None = None
    correlation: float | None = None
    glide_kind: str | None = None
    glide_params: GlideParams | None = None
    withdrawal_kind: str | None = None
    withdrawal_params: WithdrawalParams | None = None
    social_security: CashFlow | None = None
    pensions: list[CashFlow] = Field(default_factory=list)
    one_offs: list[OneOff] = Field(default_factory=list)


class SheetsStatus(BaseModel):
    authorized: bool
    sheet_id: str | None
    last_write_at: str | None = None
    error: str | None = None


class TargetRow(BaseModel):
    age: int
    target_net_worth: float


class PushResult(BaseModel):
    written_rows: int
    range: str
