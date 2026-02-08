"""Normalization helpers for Aspire label matching.

Used only for *proposals* (duplicate detection). Exact strings remain the
source-of-truth labels for storage and display.
"""

from __future__ import annotations

import re


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_label(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = _NON_ALNUM_RE.sub(" ", raw)
    collapsed = " ".join(raw.split())
    return collapsed
