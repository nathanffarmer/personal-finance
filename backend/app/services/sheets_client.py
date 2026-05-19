from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from ..config import Settings, get_settings
from ..models.sheets import (
    Assumptions,
    CashFlow,
    GlideParams,
    OneOff,
    SheetsStatus,
    TargetRow,
    WithdrawalParams,
)

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").replace("%", "").strip()
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    f = _to_float(value)
    return int(f) if f is not None else None


def _scalar(rows: list[list[Any]] | None) -> Any:
    if not rows:
        return None
    first = rows[0]
    return first[0] if first else None


def _parse_json_cell(rows: list[list[Any]] | None) -> dict[str, Any]:
    raw = _scalar(rows)
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _parse_cashflow_table(rows: list[list[Any]] | None) -> list[CashFlow]:
    flows: list[CashFlow] = []
    if not rows:
        return flows
    for r in rows:
        if not r:
            continue
        start = _to_int(r[0])
        monthly = _to_float(r[1] if len(r) > 1 else None)
        if start is None or monthly is None:
            continue
        cola = True
        if len(r) > 2:
            cola = str(r[2]).strip().lower() not in ("false", "no", "0", "")
        flows.append(CashFlow(start_age=start, monthly_real=monthly, cola=cola))
    return flows


def _parse_oneoffs(rows: list[list[Any]] | None) -> list[OneOff]:
    items: list[OneOff] = []
    if not rows:
        return items
    for r in rows:
        if not r:
            continue
        age = _to_int(r[0])
        amount = _to_float(r[1] if len(r) > 1 else None)
        if age is None or amount is None:
            continue
        items.append(OneOff(age=age, amount_real=amount))
    return items


def _parse_targets(rows: list[list[Any]] | None) -> list[TargetRow]:
    out: list[TargetRow] = []
    if not rows:
        return out
    for r in rows:
        if not r:
            continue
        age = _to_int(r[0])
        target = _to_float(r[1] if len(r) > 1 else None)
        if age is None or target is None:
            continue
        out.append(TargetRow(age=age, target_net_worth=target))
    return out


def _assumptions_from_ranges(named: dict[str, list[list[Any]] | None]) -> Assumptions:
    glide_params_raw = _parse_json_cell(named.get("assumption_glide_params"))
    withdrawal_params_raw = _parse_json_cell(named.get("assumption_withdrawal_params"))
    ss_rows = named.get("social_security_table") or []
    ss = _parse_cashflow_table(ss_rows[:1]) if ss_rows else []

    return Assumptions(
        current_age=_to_int(_scalar(named.get("assumption_current_age"))),
        retirement_age=_to_int(_scalar(named.get("assumption_retirement_age"))),
        end_age=_to_int(_scalar(named.get("assumption_end_age"))),
        annual_spend_real=_to_float(_scalar(named.get("assumption_annual_spend_real"))),
        annual_contributions=_to_float(_scalar(named.get("assumption_annual_contributions"))),
        swr=_to_float(_scalar(named.get("assumption_swr"))),
        equity_mean=_to_float(_scalar(named.get("assumption_equity_mean"))),
        equity_sd=_to_float(_scalar(named.get("assumption_equity_sd"))),
        bond_mean=_to_float(_scalar(named.get("assumption_bond_mean"))),
        bond_sd=_to_float(_scalar(named.get("assumption_bond_sd"))),
        correlation=_to_float(_scalar(named.get("assumption_correlation"))),
        glide_kind=_scalar(named.get("assumption_glide_kind")),
        glide_params=GlideParams(**glide_params_raw) if glide_params_raw else None,
        withdrawal_kind=_scalar(named.get("assumption_withdrawal_kind")),
        withdrawal_params=WithdrawalParams(**withdrawal_params_raw)
        if withdrawal_params_raw
        else None,
        social_security=ss[0] if ss else None,
        pensions=_parse_cashflow_table(named.get("pensions_table")),
        one_offs=_parse_oneoffs(named.get("one_offs_table")),
    )


# Keys we try to read out of the assumptions tab.
ASSUMPTION_NAMED_RANGES = [
    "assumption_current_age",
    "assumption_retirement_age",
    "assumption_end_age",
    "assumption_annual_spend_real",
    "assumption_annual_contributions",
    "assumption_swr",
    "assumption_equity_mean",
    "assumption_equity_sd",
    "assumption_bond_mean",
    "assumption_bond_sd",
    "assumption_correlation",
    "assumption_glide_kind",
    "assumption_glide_params",
    "assumption_withdrawal_kind",
    "assumption_withdrawal_params",
    "social_security_table",
    "pensions_table",
    "one_offs_table",
]


class SheetsClient:
    """Wraps the Google Sheets v4 API for our specific tab contract.

    Reads named ranges off the Assumptions tab and writes Monarch
    snapshots + projection results to dedicated tabs.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._service = None
        self._last_write_at: datetime | None = None

    def _build_service(self):
        if self._service is not None:
            return self._service

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google API libraries missing: {exc}",
            ) from exc

        token_path = self._settings.google_token_file
        if not token_path or not os.path.exists(token_path):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Google OAuth token missing. "
                    "Run `python scripts/bootstrap_oauth.py` once to authorize."
                ),
            )

        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._service

    def _require_sheet_id(self) -> str:
        sid = self._settings.sheet_id
        if not sid:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SHEET_ID not configured. Set SHEET_ID in your .env.",
            )
        return sid

    def status(self) -> SheetsStatus:
        try:
            self._build_service()
            return SheetsStatus(
                authorized=True,
                sheet_id=self._settings.sheet_id or None,
                last_write_at=self._last_write_at.isoformat() if self._last_write_at else None,
            )
        except HTTPException as exc:
            return SheetsStatus(
                authorized=False,
                sheet_id=self._settings.sheet_id or None,
                error=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            )

    def read_named_range(self, name: str) -> list[list[Any]] | None:
        service = self._build_service()
        sheet_id = self._require_sheet_id()
        try:
            res = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheet_id, range=name)
                .execute()
            )
        except Exception as exc:  # pragma: no cover - exercised in integration
            logger.warning("Sheets read of %s failed: %s", name, exc)
            return None
        return res.get("values")

    def read_tab(self, tab: str) -> list[list[Any]]:
        service = self._build_service()
        sheet_id = self._require_sheet_id()
        res = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=tab)
            .execute()
        )
        return res.get("values", [])

    def read_assumptions(self) -> Assumptions:
        named = {name: self.read_named_range(name) for name in ASSUMPTION_NAMED_RANGES}
        return _assumptions_from_ranges(named)

    def read_targets(self) -> list[TargetRow]:
        return _parse_targets(self.read_named_range("targets_table"))

    def write_range(self, range_a1: str, values: list[list[Any]]) -> int:
        service = self._build_service()
        sheet_id = self._require_sheet_id()
        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=sheet_id,
                range=range_a1,
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )
        self._last_write_at = datetime.utcnow()
        return int(result.get("updatedRows") or 0)

    def overwrite_tab(self, tab: str, values: list[list[Any]]) -> int:
        """Clear then write the entire tab starting at A1."""
        service = self._build_service()
        sheet_id = self._require_sheet_id()
        # Clear existing range first.
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id, range=tab
        ).execute()
        return self.write_range(f"{tab}!A1", values)


_client: SheetsClient | None = None


def get_sheets_client() -> SheetsClient:
    global _client
    if _client is None:
        _client = SheetsClient(get_settings())
    return _client
