from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_app_auth
from .config import get_settings
from .routers import health, monarch, retirement, sheets


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Personal Finance", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health is unauthenticated for liveness probes.
    app.include_router(health.router)

    # All other routers gated by app password (if configured).
    protected = [Depends(require_app_auth)]
    app.include_router(monarch.router, dependencies=protected)
    app.include_router(sheets.router, dependencies=protected)
    app.include_router(retirement.router, dependencies=protected)

    return app


app = create_app()
