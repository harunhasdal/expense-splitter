from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.errors import global_exception_handler
from core.logging import setup_logging
from core.middleware import CorrelationIDMiddleware, CSRFMiddleware, SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Expense Splitter API",
        docs_url=None if settings.disable_docs else "/docs",
        redoc_url=None if settings.disable_docs else "/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (applied in reverse order — last added = outermost)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-Id"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    app.add_exception_handler(Exception, global_exception_handler)

    # Routers
    from auth.router import router as auth_router
    from balance.router import router as balance_router
    from expenses.router import router as expenses_router
    from groups.router import router as groups_router
    from settlements.router import router as settlements_router

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(groups_router, prefix="/groups", tags=["groups"])
    app.include_router(expenses_router, prefix="/groups", tags=["expenses"])
    app.include_router(settlements_router, prefix="/groups", tags=["settlements"])
    app.include_router(balance_router, prefix="/groups", tags=["balance"])

    @app.get("/health", tags=["health"])
    async def health() -> JSONResponse:
        from sqlalchemy import text

        from core.db import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return JSONResponse({"status": "ok", "db": "ok"})
        except Exception:
            return JSONResponse({"status": "degraded", "db": "unavailable"}, status_code=503)

    return app


app = create_app()
