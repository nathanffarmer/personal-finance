from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

AccountType = Literal[
    "depository",
    "investment",
    "credit",
    "loan",
    "real_estate",
    "other",
]

AssetClass = Literal["us_equity", "intl_equity", "bond", "cash", "alt", "unknown"]


class Account(BaseModel):
    id: str
    name: str
    type: AccountType
    subtype: str | None = None
    institution: str | None = None
    balance_current: float
    balance_available: float | None = None
    currency: str = "USD"
    is_hidden: bool = False
    updated_at: datetime | None = None


class Holding(BaseModel):
    account_id: str
    ticker: str | None = None
    name: str
    quantity: float
    market_value: float
    cost_basis: float | None = None
    asset_class: AssetClass = "unknown"


class BalancePoint(BaseModel):
    date: date
    balance: float


class Category(BaseModel):
    id: str
    name: str
    group: str | None = None
    icon: str | None = None


class Transaction(BaseModel):
    id: str
    date: date
    amount: float
    merchant: str = ""
    description: str = ""
    account_id: str
    category_id: str | None = None
    category_name: str | None = None
    pending: bool = False
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class NetWorthByType(BaseModel):
    cash: float = 0.0
    investment: float = 0.0
    credit: float = 0.0
    loan: float = 0.0
    real_estate: float = 0.0
    other: float = 0.0


class NetWorth(BaseModel):
    total: float
    by_type: NetWorthByType


class TransactionUpdate(BaseModel):
    category_id: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class BulkCategorize(BaseModel):
    id: str
    category_id: str
