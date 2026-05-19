from fastapi import Header, HTTPException, status

from .config import get_settings


async def require_app_auth(x_app_password: str | None = Header(default=None)) -> None:
    """Single-user auth via X-App-Password header.

    Empty APP_PASSWORD disables auth (localhost dev only).
    """
    settings = get_settings()
    if not settings.app_password:
        return
    if x_app_password != settings.app_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-App-Password header",
        )
