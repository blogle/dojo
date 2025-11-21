from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from ..core.config import Settings, get_settings
from . import services

router = APIRouter(prefix="/api", tags=["testing"])


class SeedRequest(BaseModel):
    fixture: str


@router.post("/testing/reset_db", status_code=status.HTTP_204_NO_CONTENT)
def reset_database(settings: Settings = Depends(get_settings)):
    """
    Resets the database to a clean state.
    Deletes the database file and re-runs all migrations.
    """
    try:
        services.reset_db(db_path=settings.db_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/testing/seed_db", status_code=status.HTTP_204_NO_CONTENT)
def seed_database(payload: SeedRequest = Body(...), settings: Settings = Depends(get_settings)):
    """
    Seeds the database with a fixture file.
    The path should be relative to the project root.
    e.g. `tests/fixtures/base_budgeting.sql`
    """
    try:
        services.seed_db(db_path=settings.db_path, fixture_path=payload.fixture)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
