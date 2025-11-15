"""FastAPI application factory (`build_container`)."""

from importlib import resources
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dojo.budgeting.routers import router as budgeting_router
from dojo.budgeting.services import AccountAdminService, BudgetCategoryAdminService, TransactionEntryService
from dojo.core.config import Settings, get_settings
from dojo.core.routers import router as core_router


def _static_directory() -> Path:
    return Path(resources.files("dojo.frontend").joinpath("static"))


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory that wires dependencies and routers."""

    settings = settings or get_settings()
    app = FastAPI(title="Dojo", version="0.1.0")
    app.state.settings = settings

    # Application-scoped services
    app.state.transaction_service = TransactionEntryService()
    app.state.account_admin_service = AccountAdminService()
    app.state.budget_category_admin_service = BudgetCategoryAdminService()

    app.include_router(core_router)
    app.include_router(budgeting_router)

    static_dir = _static_directory()
    app.mount(
        "/",
        StaticFiles(directory=str(static_dir), html=True),
        name="spa",
    )
    return app


app = create_app()
