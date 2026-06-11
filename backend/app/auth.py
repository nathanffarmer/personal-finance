from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings


async def require_app_auth(
    x_app_password: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Single-user auth via X-App-Password header.

    Empty APP_PASSWORD disables auth (localhost dev only).
    """
    if not settings.app_password:
        return
    if x_app_password != settings.app_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-App-Password header",
        )
