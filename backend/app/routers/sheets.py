from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..models.retirement import MonteCarloResult
from ..models.sheets import Assumptions, PushResult, SheetsStatus, TargetRow
from ..services.monarch_client import MonarchClient, get_monarch_client
from ..services.sheets_client import SheetsClient, get_sheets_client

router = APIRouter(prefix="/api/sheets", tags=["sheets"])


@router.get("/status", response_model=SheetsStatus)
async def status(sheets: SheetsClient = Depends(get_sheets_client)) -> SheetsStatus:
    return sheets.status()


@router.get("/assumptions", response_model=Assumptions)
async def assumptions(sheets: SheetsClient = Depends(get_sheets_client)) -> Assumptions:
    return sheets.read_assumptions()


@router.get("/targets", response_model=list[TargetRow])
async def targets(sheets: SheetsClient = Depends(get_sheets_client)) -> list[TargetRow]:
    return sheets.read_targets()


@router.get("/tab/{tab_name}")
async def read_tab(tab_name: str, sheets: SheetsClient = Depends(get_sheets_client)) -> list[list]:
    return sheets.read_tab(tab_name)


@router.post("/push/accounts", response_model=PushResult)
async def push_accounts(
    settings: Settings = Depends(get_settings),
    sheets: SheetsClient = Depends(get_sheets_client),
    monarch: MonarchClient = Depends(get_monarch_client),
) -> PushResult:
    accounts = await monarch.list_accounts()
    rows: list[list] = [
        [
            "account_id",
            "name",
            "type",
            "subtype",
            "institution",
            "balance_current",
            "currency",
            "updated_at",
        ],
    ]
    for a in accounts:
        rows.append(
            [
                a.id,
                a.name,
                a.type,
                a.subtype or "",
                a.institution or "",
                a.balance_current,
                a.currency,
                a.updated_at.isoformat() if a.updated_at else "",
            ],
        )
    tab = settings.sheets_tab_accounts
    written = sheets.overwrite_tab(tab, rows)
    return PushResult(written_rows=written or len(rows), range=f"{tab}!A1")


@router.post("/push/holdings", response_model=PushResult)
async def push_holdings(
    settings: Settings = Depends(get_settings),
    sheets: SheetsClient = Depends(get_sheets_client),
    monarch: MonarchClient = Depends(get_monarch_client),
) -> PushResult:
    accounts = await monarch.list_accounts()
    rows: list[list] = [
        [
            "account_id",
            "ticker",
            "name",
            "quantity",
            "market_value",
            "cost_basis",
            "asset_class",
            "snapshot_at",
        ],
    ]
    now = datetime.utcnow().isoformat()
    for a in accounts:
        if a.type != "investment":
            continue
        holdings = await monarch.list_holdings(a.id)
        for h in holdings:
            rows.append(
                [
                    a.id,
                    h.ticker or "",
                    h.name,
                    h.quantity,
                    h.market_value,
                    h.cost_basis if h.cost_basis is not None else "",
                    h.asset_class,
                    now,
                ],
            )
    tab = settings.sheets_tab_holdings
    written = sheets.overwrite_tab(tab, rows)
    return PushResult(written_rows=written or len(rows), range=f"{tab}!A1")


@router.post("/push/projection", response_model=PushResult)
async def push_projection(
    result: MonteCarloResult,
    settings: Settings = Depends(get_settings),
    sheets: SheetsClient = Depends(get_sheets_client),
) -> PushResult:
    """Write Monte Carlo percentile bands to the Projections tab."""
    bands = result.percentiles
    rows: list[list] = [
        ["year", "age", "p5", "p25", "p50", "p75", "p95", "success_rate"],
    ]
    for i, age in enumerate(result.ages):
        rows.append(
            [
                i,
                age,
                bands.p5[i],
                bands.p25[i],
                bands.p50[i],
                bands.p75[i],
                bands.p95[i],
                result.success_rate,
            ],
        )
    tab = settings.sheets_tab_projections
    written = sheets.overwrite_tab(tab, rows)
    return PushResult(written_rows=written or len(rows), range=f"{tab}!A1")
