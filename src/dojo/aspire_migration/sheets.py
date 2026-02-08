"""Helpers for parsing Google Sheets identifiers."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


_SPREADSHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


def parse_spreadsheet_id(value: str) -> str:
    """Parse a spreadsheet id from either an id or common Google Sheets URL forms."""

    raw = (value or "").strip()
    if not raw:
        raise ValueError("spreadsheet id is required")

    match = _SPREADSHEET_ID_RE.search(raw)
    if match:
        return match.group(1)

    try:
        parsed = urlparse(raw)
    except Exception:
        parsed = None

    if parsed and parsed.scheme in {"http", "https"}:
        qs = parse_qs(parsed.query)
        if "id" in qs and qs["id"]:
            return qs["id"][0]

    # Fall back to treating the input as a raw id.
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", raw):
        return raw

    raise ValueError("Could not parse a spreadsheet id from the provided input")
