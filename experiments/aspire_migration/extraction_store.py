"""In-memory storage for extracted Aspire datasets.

This is a temporary UX accelerant.

Milestone 3 ultimately stages extracted rows into DuckDB tables keyed by
migration_session_id so the onboarding flow can resume across server restarts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedAspireSummary:
    migration_session_id: str
    dataset_fingerprint: str

    transactions_count: int
    transactions_date_min: str | None
    transactions_date_max: str | None

    allocations_count: int
    allocations_date_min: str | None
    allocations_date_max: str | None

    net_worth_snapshots_count: int
    net_worth_date_min: str | None
    net_worth_date_max: str | None


@dataclass
class _Entry:
    created_at_s: float
    summary: ExtractedAspireSummary


class AspireExtractionStore:
    """Simple TTL-backed store keyed by migration_session_id."""

    def __init__(self, *, ttl_s: float = 60 * 60) -> None:
        self._ttl_s = ttl_s
        self._entries: dict[str, _Entry] = {}

    def _purge(self) -> None:
        now = time.time()
        self._entries = {
            session_id: entry for session_id, entry in self._entries.items() if now - entry.created_at_s <= self._ttl_s
        }

    def get_summary(self, migration_session_id: str) -> ExtractedAspireSummary | None:
        self._purge()
        entry = self._entries.get(migration_session_id)
        return entry.summary if entry else None

    def put_summary(self, summary: ExtractedAspireSummary) -> None:
        self._purge()
        self._entries[summary.migration_session_id] = _Entry(created_at_s=time.time(), summary=summary)

    def delete(self, migration_session_id: str) -> None:
        self._entries.pop(migration_session_id, None)
