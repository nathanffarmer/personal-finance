from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status
from monarchmoney import (
    LoginFailedException,
    MonarchMoney,
    RequireMFAException,
)

from ..config import Settings, get_settings
from ..models.monarch import (
    Account,
    AssetClass,
    BalancePoint,
    Category,
    Holding,
    NetWorth,
    NetWorthByType,
    Transaction,
)

logger = logging.getLogger(__name__)


_TYPE_MAP: dict[str, str] = {
    "depository": "depository",
    "brokerage": "investment",
    "investment": "investment",
    "retirement": "investment",
    "credit": "credit",
    "credit_card": "credit",
    "loan": "loan",
    "mortgage": "loan",
    "real_estate": "real_estate",
    "vehicle": "other",
    "valuables": "other",
    "other_asset": "other",
    "other_liability": "other",
}


def _normalize_type(raw: str | None) -> str:
    if not raw:
        return "other"
    key = raw.lower()
    return _TYPE_MAP.get(key, "other")


def _classify_asset(security: dict[str, Any] | None) -> AssetClass:
    if not security:
        return "unknown"
    t = (security.get("type") or "").lower()
    if t in ("equity", "etf", "stock", "mutual_fund"):
        return "us_equity"
    if t in ("bond", "fixed_income"):
        return "bond"
    if t in ("cash", "money_market"):
        return "cash"
    if t in ("crypto", "real_estate", "commodity"):
        return "alt"
    return "unknown"


def map_account(raw: dict[str, Any]) -> Account:
    """Map a MonarchMoney account dict to our Account schema.

    The Monarch GraphQL shape uses snake_case-ish dict keys; we tolerate
    missing fields and coerce types defensively.
    """
    type_raw = (raw.get("type") or {}).get("name") if isinstance(raw.get("type"), dict) else raw.get("type")
    inst = raw.get("institution") or {}
    return Account(
        id=str(raw["id"]),
        name=raw.get("displayName") or raw.get("name") or "Unnamed",
        type=_normalize_type(type_raw),  # type: ignore[arg-type]
        subtype=(raw.get("subtype") or {}).get("name") if isinstance(raw.get("subtype"), dict) else raw.get("subtype"),
        institution=inst.get("name") if isinstance(inst, dict) else None,
        balance_current=float(raw.get("currentBalance") or raw.get("displayBalance") or 0.0),
        balance_available=_optional_float(raw.get("availableBalance")),
        currency=raw.get("currency") or "USD",
        is_hidden=bool(raw.get("isHidden") or raw.get("hideFromList") or False),
        updated_at=_parse_dt(raw.get("updatedAt") or raw.get("lastSyncedAt")),
    )


def map_holding(raw: dict[str, Any]) -> Holding:
    sec = raw.get("security") or {}
    return Holding(
        account_id=str(raw.get("accountId") or (raw.get("account") or {}).get("id") or ""),
        ticker=sec.get("ticker") or sec.get("symbol"),
        name=sec.get("name") or raw.get("name") or "Holding",
        quantity=float(raw.get("quantity") or 0.0),
        market_value=float(raw.get("totalValue") or raw.get("value") or 0.0),
        cost_basis=_optional_float(raw.get("costBasis")),
        asset_class=_classify_asset(sec),
    )


def map_transaction(raw: dict[str, Any]) -> Transaction:
    cat = raw.get("category") or {}
    acct = raw.get("account") or {}
    return Transaction(
        id=str(raw["id"]),
        date=_parse_date(raw.get("date")) or date.today(),
        amount=float(raw.get("amount") or 0.0),
        merchant=(raw.get("merchant") or {}).get("name") if isinstance(raw.get("merchant"), dict) else (raw.get("merchant") or ""),
        description=raw.get("plaidName") or raw.get("originalDescription") or "",
        account_id=str(acct.get("id") or raw.get("accountId") or ""),
        category_id=str(cat.get("id")) if cat.get("id") is not None else None,
        category_name=cat.get("name"),
        pending=bool(raw.get("pending") or False),
        notes=raw.get("notes"),
        tags=[t.get("name", "") for t in (raw.get("tags") or []) if isinstance(t, dict)],
    )


def map_category(raw: dict[str, Any]) -> Category:
    group = raw.get("group") or {}
    return Category(
        id=str(raw["id"]),
        name=raw.get("name") or "Uncategorized",
        group=group.get("name") if isinstance(group, dict) else None,
        icon=raw.get("icon"),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


class MonarchClient:
    """Thin async wrapper around the monarchmoney library.

    - Persists session to disk so we don't re-MFA on every restart.
    - Maps raw dicts to typed Pydantic models so routers never see library shapes.
    - Serializes login behind a lock to avoid double-login on first request.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._mm: MonarchMoney | None = None
        self._login_lock = asyncio.Lock()

    async def _ensure_logged_in(self) -> MonarchMoney:
        if self._mm is not None:
            return self._mm
        async with self._login_lock:
            if self._mm is not None:
                return self._mm
            mm = MonarchMoney()
            session_path = self._settings.mm_session_file
            if session_path and os.path.exists(session_path):
                try:
                    mm.load_session(session_path)
                    self._mm = mm
                    return mm
                except Exception as exc:  # pragma: no cover - depends on disk
                    logger.warning("Failed to load Monarch session: %s — re-logging in", exc)
            if not (self._settings.monarch_email and self._settings.monarch_password):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Monarch credentials not configured. Set MONARCH_EMAIL/MONARCH_PASSWORD in .env.",
                )
            try:
                await mm.login(
                    email=self._settings.monarch_email,
                    password=self._settings.monarch_password,
                    use_saved_session=False,
                    save_session=True,
                    mfa_secret_key=self._settings.monarch_mfa_secret or None,
                )
            except RequireMFAException as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Monarch requires MFA. Set MONARCH_MFA_SECRET in .env (TOTP seed) or run scripts/monarch_login.py.",
                ) from exc
            except LoginFailedException as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Monarch login failed: {exc}",
                ) from exc
            if session_path:
                os.makedirs(os.path.dirname(session_path) or ".", exist_ok=True)
                mm.save_session(session_path)
            self._mm = mm
            return mm

    async def list_accounts(self) -> list[Account]:
        mm = await self._ensure_logged_in()
        raw = await mm.get_accounts()
        return [map_account(a) for a in _extract_list(raw, "accounts")]

    async def list_holdings(self, account_id: str) -> list[Holding]:
        mm = await self._ensure_logged_in()
        raw = await mm.get_account_holdings(int(account_id))
        return [map_holding(h) for h in _extract_list(raw, "holdings", "portfolio")]

    async def list_account_history(self, account_id: str) -> list[BalancePoint]:
        mm = await self._ensure_logged_in()
        raw = await mm.get_account_history(int(account_id))
        items = _extract_list(raw, "history", "accountBalanceHistory")
        points: list[BalancePoint] = []
        for it in items:
            d = _parse_date(it.get("date"))
            if d is None:
                continue
            points.append(BalancePoint(date=d, balance=float(it.get("balance") or it.get("signedBalance") or 0.0)))
        return points

    async def list_transactions(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
        account_ids: Iterable[str] | None = None,
        category_ids: Iterable[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        mm = await self._ensure_logged_in()
        raw = await mm.get_transactions(
            limit=limit,
            offset=offset,
            start_date=start.isoformat() if start else None,
            end_date=end.isoformat() if end else None,
            account_ids=list(account_ids) if account_ids else [],
            category_ids=list(category_ids) if category_ids else [],
        )
        return [map_transaction(t) for t in _extract_list(raw, "transactions", "allTransactions")]

    async def list_categories(self) -> list[Category]:
        mm = await self._ensure_logged_in()
        raw = await mm.get_transaction_categories()
        return [map_category(c) for c in _extract_list(raw, "categories", "transactionCategories")]

    async def update_transaction(
        self,
        transaction_id: str,
        *,
        category_id: str | None = None,
        notes: str | None = None,
    ) -> Transaction:
        mm = await self._ensure_logged_in()
        raw = await mm.update_transaction(
            transaction_id=transaction_id,
            category_id=category_id,
            notes=notes,
        )
        # The mutation usually returns the updated transaction; otherwise re-fetch is overkill for one row.
        payload = _extract_first(raw, "transaction", "updateTransaction")
        return map_transaction(payload or {"id": transaction_id, "amount": 0.0, "account": {"id": ""}, "date": date.today().isoformat()})

    def status(self) -> dict[str, Any]:
        """Report configuration/session state without forcing a login."""
        return {
            "credentials_configured": bool(
                self._settings.monarch_email and self._settings.monarch_password
            ),
            "mfa_secret_configured": bool(self._settings.monarch_mfa_secret),
            "session_cached": bool(
                self._settings.mm_session_file
                and os.path.exists(self._settings.mm_session_file)
            ),
            "logged_in": self._mm is not None,
        }

    # Account types whose balance is a debt (reduces net worth).
    _LIABILITY_TYPES = ("credit", "loan")

    @staticmethod
    def net_worth(accounts: list[Account]) -> NetWorth:
        # NetWorthByType uses friendly names; depository -> cash, the rest match.
        type_to_field = {
            "depository": "cash",
            "investment": "investment",
            "credit": "credit",
            "loan": "loan",
            "real_estate": "real_estate",
            "other": "other",
        }
        bucket = NetWorthByType()
        for a in accounts:
            if a.is_hidden:
                continue
            field = type_to_field.get(a.type, "other")
            if a.type in MonarchClient._LIABILITY_TYPES:
                # Liabilities must reduce net worth regardless of whether
                # Monarch reports the balance as positive or negative — some
                # institutions/account types differ. Normalize to a negative
                # contribution so the total is correct either way.
                contribution = -abs(a.balance_current)
            else:
                contribution = a.balance_current
            setattr(bucket, field, getattr(bucket, field) + contribution)
        total = (
            bucket.cash
            + bucket.investment
            + bucket.real_estate
            + bucket.other
            + bucket.credit
            + bucket.loan
        )
        return NetWorth(total=total, by_type=bucket)


def _extract_list(payload: Any, *keys: str) -> list[dict[str, Any]]:
    """Pull a list out of nested Monarch response shapes.

    Monarch responses often wrap the data: {"accounts": [...]} or
    {"data": {"accounts": {"edges": [{"node": ...}]}}}. We try the keys
    in order and return [] if none match.
    """
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                inner = payload[key]
                if isinstance(inner, list):
                    return [item for item in inner if isinstance(item, dict)]
                if isinstance(inner, dict):
                    if "edges" in inner and isinstance(inner["edges"], list):
                        return [e.get("node") or {} for e in inner["edges"] if isinstance(e, dict)]
                    return _extract_list(inner, *keys)
        if "data" in payload and isinstance(payload["data"], dict):
            return _extract_list(payload["data"], *keys)
    return []


def _extract_first(payload: Any, *keys: str) -> dict[str, Any] | None:
    items = _extract_list(payload, *keys)
    return items[0] if items else None


_client: MonarchClient | None = None


def get_monarch_client() -> MonarchClient:
    global _client
    if _client is None:
        _client = MonarchClient(get_settings())
    return _client
