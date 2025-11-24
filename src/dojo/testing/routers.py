"""
API routers for testing utilities.

These endpoints provide functionalities for managing the database state
during testing, such as resetting and seeding the database with fixtures.
These routes are typically only active in development/testing environments.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from ..core.config import Settings, get_settings
from . import services

# Initialize the API router for testing-specific endpoints.
router = APIRouter(tags=["testing"])


class SeedRequest(BaseModel):
    """
    Request payload for seeding the database with a fixture.

    Attributes
    ----------
    fixture : str
        The path to the SQL fixture file, relative to the project root
        (e.g., `tests/fixtures/base_budgeting.sql`).
    """

    fixture: str


@router.post("/testing/reset_db", status_code=status.HTTP_204_NO_CONTENT)
def reset_database(settings: Settings = Depends(get_settings)):
    """
    Resets the database to a clean state.

    This operation deletes the existing database file and then re-runs
    all necessary migrations, effectively providing a fresh database
    schema for testing.

    Parameters
    ----------
    settings : Settings
        Application settings, injected via FastAPI's Depends, providing the database path.

    Raises
    ------
    HTTPException
        500 Internal Server Error if an error occurs during the database reset.
    """
    try:
        # Call the service function to perform the database reset.
        services.reset_db(db_path=settings.db_path)
    except Exception as e:
        # Catch any exceptions during reset and return an appropriate HTTP error.
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/testing/seed_db", status_code=status.HTTP_204_NO_CONTENT)
def seed_database(
    payload: SeedRequest = Body(...), settings: Settings = Depends(get_settings)
):
    """
    Seeds the database with data from a specified fixture file.

    This endpoint is used to populate the database with predefined test data,
    which is essential for consistent and reproducible testing scenarios.

    Parameters
    ----------
    payload : SeedRequest
        The request body containing the path to the fixture file.
    settings : Settings
        Application settings, injected via FastAPI's Depends, providing the database path.

    Raises
    ------
    HTTPException
        404 Not Found if the fixture file specified in the payload does not exist.
        500 Internal Server Error for other unexpected errors during seeding.
    """
    try:
        # Call the service function to seed the database with the specified fixture.
        services.seed_db(db_path=settings.db_path, fixture_path=payload.fixture)
    except FileNotFoundError as e:
        # Handle cases where the fixture file is not found.
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Handle other exceptions during seeding.
        raise HTTPException(status_code=500, detail=str(e))
