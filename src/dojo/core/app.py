"""
This module contains the FastAPI application factory (`create_app`) and related utilities.

It centralizes the creation and configuration of the FastAPI app, including
database migration, service instantiation, and router registration,
ensuring explicit dependency management.
"""

from importlib import resources
from pathlib import Path
import logging

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from dojo.budgeting.routers import router as budgeting_router
from dojo.budgeting.services import (
    AccountAdminService,
    BudgetCategoryAdminService,
    TransactionEntryService,
)
from dojo.core.config import Settings, get_settings
from dojo.core.db import get_connection
from dojo.core.migrate import apply_migrations
from dojo.core.routers import router as core_router

logger = logging.getLogger(__name__)


def _static_directory() -> Path:
    """
    Determines the path to the static frontend files.

    Returns
    -------
    Path
        The absolute path to the static files directory.
    """
    # Using importlib.resources to reliably locate the static directory
    # within the installed package, regardless of execution context.
    return Path(str(resources.files("dojo.frontend").joinpath("static")))


def _apply_startup_migrations(settings: Settings) -> None:
    """
    Applies idempotent database migrations on application startup.

    This ensures that the database schema is up-to-date and ready for
    application requests.

    Parameters
    ----------
    settings : Settings
        The application settings, containing the database path.
    """
    # Locate migration scripts within the package.
    migrations_pkg = resources.files("dojo.sql.migrations")
    # Establish a connection and apply all pending migrations.
    with get_connection(settings.db_path) as conn:
        apply_migrations(conn, migrations_pkg)


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Creates and configures the FastAPI application instance.

    This function acts as the application factory, responsible for:
    - Loading application settings.
    - Applying database migrations.
    - Instantiating and attaching application-scoped services to the app state.
    - Including API routers.
    - Serving static frontend files.

    Parameters
    ----------
    settings : Settings | None, optional
        Application settings. If None, settings are loaded using `get_settings()`.

    Returns
    -------
    FastAPI
        The configured FastAPI application.
    """
    # Load settings, defaulting to environment/file if not provided.
    settings = settings or get_settings()
    # Ensure the database schema is current before starting the application when enabled.
    if settings.run_startup_migrations:
        _apply_startup_migrations(settings)
    else:
        logger.info("Skipping startup migrations (run_startup_migrations=false)")

    app = FastAPI(title="Dojo", version="0.1.0")
    # Store settings and API host/port in app state for easy access across the application.
    app.state.settings = settings
    app.state.api_host = settings.api_host
    app.state.api_port = settings.api_port

    # Application-scoped services
    # Instantiate and attach application-level services to the app state.
    # This makes them accessible globally via `app.state.<service_name>`
    # and to request dependencies via `request.app.state.<service_name>`.
    app.state.transaction_service = TransactionEntryService()
    app.state.account_admin_service = AccountAdminService()
    app.state.budget_category_admin_service = BudgetCategoryAdminService()

    # Include API routers for different functional domains.
    # All API routes will be prefixed with "/api".
    app.include_router(core_router, prefix="/api")
    app.include_router(budgeting_router, prefix="/api")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """
        Health check endpoint for Kubernetes probes.
        """
        return {"status": "ok"}

    # Conditionally include testing routes. These provide endpoints
    # for managing test data and state, and should only be active in testing environments.
    if settings.testing:
        from dojo.testing.routers import router as testing_router

        app.include_router(testing_router, prefix="/api")
    else:
        # Disable testing routes in non-testing environments to prevent
        # accidental exposure of test-specific functionalities in production.
        @app.api_route(
            "/api/testing/{path:path}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
            include_in_schema=False,
        )
        def _testing_routes_disabled(
            path: str,
        ) -> None:  # pragma: no cover - simple guard
            raise HTTPException(status_code=404, detail="Testing routes disabled")

    # Mount the static files directory to serve the frontend Single Page Application (SPA).
    # All requests not matching API routes will be served by the SPA.
    static_dir = _static_directory()
    app.mount(
        "/",
        StaticFiles(directory=str(static_dir), html=True),
        name="spa",
    )
    return app
