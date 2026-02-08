"""Google Sheets API client wrapper used by the Aspire migration.

This module is intentionally small and defensive:
- Use read-only scopes.
- Avoid logging any returned values.
- Treat google client libraries as optional dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
)


class GoogleSheetsAuthError(RuntimeError):
    pass


class GoogleSheetsApiError(RuntimeError):
    pass


def _require_google_api() -> Any:
    try:
        from googleapiclient.discovery import build  # type: ignore[import-not-found]
        from googleapiclient.errors import HttpError  # type: ignore[import-not-found]

        return (build, HttpError)
    except Exception as exc:  # pragma: no cover
        raise GoogleSheetsApiError(
            "Missing optional dependencies for Google Sheets API. "
            "Install with `uv sync --extra gsheets` (or `uv run --extra gsheets ...`)."
        ) from exc


ValueRenderOption = Literal["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"]


@dataclass(frozen=True)
class GoogleSheetsClient:
    """Minimal wrapper around the Sheets v4 API."""

    credentials: Any

    def _service(self) -> Any:
        build, _HttpError = _require_google_api()
        # cache_discovery=False avoids file writes in some environments.
        return build("sheets", "v4", credentials=self.credentials, cache_discovery=False)

    def get_spreadsheet_metadata(self, *, spreadsheet_id: str) -> dict[str, Any]:
        _build, HttpError = _require_google_api()
        try:
            service = self._service()
            # Only request what we need.
            req = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields="spreadsheetId,properties.title,namedRanges(name,range)",
            )
            return dict(req.execute())
        except HttpError as exc:  # pragma: no cover
            raise GoogleSheetsApiError("Sheets API error while fetching metadata") from exc
        except Exception as exc:  # pragma: no cover
            raise GoogleSheetsAuthError("Failed to authenticate with Google Sheets") from exc

    def batch_get_values(
        self,
        *,
        spreadsheet_id: str,
        ranges: list[str],
        value_render_option: ValueRenderOption = "UNFORMATTED_VALUE",
    ) -> dict[str, Any]:
        _build, HttpError = _require_google_api()
        try:
            service = self._service()
            req = service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges,
                valueRenderOption=value_render_option,
            )
            return dict(req.execute())
        except HttpError as exc:  # pragma: no cover
            raise GoogleSheetsApiError("Sheets API error while fetching values") from exc
        except Exception as exc:  # pragma: no cover
            raise GoogleSheetsAuthError("Failed to authenticate with Google Sheets") from exc
