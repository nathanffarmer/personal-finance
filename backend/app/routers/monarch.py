from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from ..config import Settings, get_settings
from ..models.monarch import (
    Account,
    BalancePoint,
    BulkCategorize,
    Category,
    Holding,
    NetWorth,
    Transaction,
    TransactionUpdate,
)
from ..services.cache import TTLCache, get_cache
from ..services.monarch_client import MonarchClient, get_monarch_client

router = APIRouter(prefix="/api/monarch", tags=["monarch"])


@router.get("/accounts", response_model=list[Account])
async def list_accounts(
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[Account]:
    return await cache.get_or_set(
        "monarch:accounts",
        settings.cache_ttl_accounts,
        client.list_accounts,
    )


@router.get("/accounts/{account_id}/holdings", response_model=list[Holding])
async def list_holdings(
    account_id: str,
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[Holding]:
    return await cache.get_or_set(
        f"monarch:holdings:{account_id}",
        settings.cache_ttl_accounts,
        lambda: client.list_holdings(account_id),
    )


@router.get("/accounts/{account_id}/history", response_model=list[BalancePoint])
async def account_history(
    account_id: str,
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[BalancePoint]:
    return await cache.get_or_set(
        f"monarch:history:{account_id}",
        settings.cache_ttl_accounts,
        lambda: client.list_account_history(account_id),
    )


@router.get("/net_worth", response_model=NetWorth)
async def net_worth(
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> NetWorth:
    accounts = await cache.get_or_set(
        "monarch:accounts",
        settings.cache_ttl_accounts,
        client.list_accounts,
    )
    return MonarchClient.net_worth(accounts)


@router.get("/transactions", response_model=list[Transaction])
async def list_transactions(
    start: date | None = None,
    end: date | None = None,
    account_id: list[str] | None = Query(default=None),
    category_id: list[str] | None = Query(default=None),
    limit: int = 100,
    offset: int = 0,
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[Transaction]:
    key = f"monarch:tx:{start}:{end}:{account_id}:{category_id}:{limit}:{offset}"
    return await cache.get_or_set(
        key,
        settings.cache_ttl_transactions,
        lambda: client.list_transactions(
            start=start,
            end=end,
            account_ids=account_id,
            category_ids=category_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/categories", response_model=list[Category])
async def list_categories(
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> list[Category]:
    return await cache.get_or_set(
        "monarch:categories",
        settings.cache_ttl_accounts,
        client.list_categories,
    )


@router.patch("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
) -> Transaction:
    result = await client.update_transaction(
        transaction_id,
        category_id=payload.category_id,
        notes=payload.notes,
    )
    cache.clear("monarch:tx:")
    return result


@router.post("/transactions/categorize_bulk")
async def categorize_bulk(
    items: list[BulkCategorize],
    client: MonarchClient = Depends(get_monarch_client),
    cache: TTLCache = Depends(get_cache),
) -> dict[str, int]:
    updated = 0
    for item in items:
        await client.update_transaction(item.id, category_id=item.category_id)
        updated += 1
    cache.clear("monarch:tx:")
    return {"updated": updated}


@router.post("/cache/clear")
async def clear_cache(cache: TTLCache = Depends(get_cache)) -> dict[str, int]:
    cleared = cache.clear("monarch:")
    return {"cleared": cleared}
