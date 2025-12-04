from datetime import date
from typing import Annotated

from fastapi import Header, HTTPException


def get_system_date(x_test_date: Annotated[str | None, Header()] = None) -> date:
    """
    Resolve the system date for a request, optionally overridden by a test header.

    During automated tests we accept an `X-Test-Date` header (YYYY-MM-DD) so that
    frontend and backend share a deterministic clock. Invalid values return a
    400 to make failures explicit.
    """

    if x_test_date:
        try:
            return date.fromisoformat(x_test_date)
        except ValueError as exc:  # pragma: no cover - defensive path
            raise HTTPException(status_code=400, detail="Invalid X-Test-Date; expected YYYY-MM-DD") from exc
    return date.today()
