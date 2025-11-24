"""FastAPI application factory (`build_container`)."""

from importlib import resources
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from dojo.budgeting.routers import router as budgeting_router
from dojo.budgeting.services import AccountAdminService, BudgetCategoryAdminService, TransactionEntryService
from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection
from dojo.core.migrate import apply_migrations
from dojo.core.routers import router as core_router


def _static_directory() -> Path:
    return Path(str(resources.files("dojo.frontend").joinpath("static")))


def _apply_startup_migrations(settings: Settings) -> None:
    """Apply idempotent migrations on startup so the DB is ready for requests."""

    migrations_pkg = resources.files("dojo.sql.migrations")
    with get_connection(settings.db_path) as conn:
        apply_migrations(conn, migrations_pkg)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory that wires dependencies and routers."""

    settings = settings or get_settings()
    _apply_startup_migrations(settings)

    app = FastAPI(title="Dojo", version="0.1.0")
    app.state.settings = settings

    # Application-scoped services
    app.state.transaction_service = TransactionEntryService()
    app.state.account_admin_service = AccountAdminService()
    app.state.budget_category_admin_service = BudgetCategoryAdminService()

    app.include_router(core_router, prefix="/api")
    app.include_router(budgeting_router, prefix="/api")

    if settings.testing:
        from dojo.testing.routers import router as testing_router

        app.include_router(testing_router, prefix="/api")
    else:
        @app.api_route(
            "/api/testing/{path:path}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
            include_in_schema=False,
        )
        def _testing_routes_disabled(path: str) -> None:  # pragma: no cover - simple guard
            raise HTTPException(status_code=404, detail="Testing routes disabled")

    static_dir = _static_directory()
    app.mount(
        "/",
        StaticFiles(directory=str(static_dir), html=True),
        name="spa",
    )
    return app

