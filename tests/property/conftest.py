"""Shared Hypothesis configuration for property-based suites."""

from __future__ import annotations

import os

from hypothesis import Phase, settings

PROPERTY_SEED = os.environ.get("DOJO_HYPOTHESIS_SEED", "20251211")
os.environ.setdefault("HYPOTHESIS_SEED", PROPERTY_SEED)

settings.register_profile(
    "dojo-property",
    settings(
        max_examples=100,
        phases=(Phase.explicit, Phase.generate, Phase.target),
        derandomize=False,
    ),
)
settings.load_profile("dojo-property")
