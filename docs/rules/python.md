# Python Best Practices & Style Guide (Codebase-Wide)

This guide emphasizes maintainability, clarity, correctness, and determinism over cleverness.


## Naming & Organization

Organize packages by **domain responsibility** with a shared `infra/` (or `platform/`) for true cross-cutting utilities. New code belongs **next to the closest responsible module**.

Prefer the **smallest reasonable change**. If you must refactor, isolate it in its own commit (no mixed refactor + feature).

Examples of structure:

    core/
        db.py
        logging.py
    orders/
        routers.py
        service.py
    pricing/
        router.py
        service.py
        discounts.py



## Compatibility & Change Control

We are at v0; breaking changes are allowed. Every breaking change must:

1. Add a bullet under **CHANGELOG.md › Unreleased › Breaking Changes** with a one-line migration note.
2. Apply the `breaking-change` label on the PR.

Feature flags are **read once at the edge** (config load) and **passed inward**; do not sprinkle flags across modules or read the same flag in multiple places.



## Imports & Dependencies

Imports are **at the top of the file**, grouped and ordered per PEP8: stdlib, third-party, local. Never modify `sys.path`; no dynamic/nested/try-except imports; dependencies must be declared and expected to exist.

**Example — import grouping**

    import pathlib
    from dataclasses import dataclass

    import numpy as np
    import pandas as pd

    from orders.dao import OrderDAO



## Types & Functions

Write **pure, typed functions** by default and **always** include return annotations. Prefer builtin type forms (`list[str] | None`), avoid `typing` aliases unless necessary. Avoid hidden globals and mutable default arguments.

Use `assert` **only** for internal invariants that may be stripped with `-O`. Use explicit validation with typed exceptions for user/data errors.

**Example — type annotations and validation**

    def top_n(xs: list[int], n: int) -> list[int]:
        # Why: we require a positive n and do not allow n > len(xs) to prevent surprises.
        if n <= 0:
            raise ValueError("n must be positive")
        if n > len(xs):
            raise ValueError("n must not exceed length of xs")
        return sorted(xs, reverse=True)[:n]

**Anti-pattern**

    def add_user(u: dict = {}):    # BAD: mutable default
        ...



## Control Flow & Exceptions

Prefer `match/case` when branching on enums/tagged states. Catch exceptions at the **innermost layer that can actually handle them**. Never use `except:` (bare). Wrap third-party exceptions at boundaries with domain exceptions; do not silence failures.

**Example — pattern matching**

    def status_to_message(code: int) -> str:
        # Why: pattern matching keeps branching flat and readable.
        match code:
            case 200:
                return "ok"
            case 404:
                raise NotFound("resource not found")
            case _:
                raise UnexpectedStatus(code)

**Example — exception handling**

    def load_order(order_id: str) -> dict:
        # Why: only this layer knows how to map persistence errors to domain errors.
        try:
            return OrderDAO().get(order_id)
        except DatabaseTimeout as exc:
            # What: convert infra error to domain exception with context and re-raise.
            raise OrderUnavailable(f"Order {order_id} temporarily unavailable") from exc



## Statics over Dynamics

We **always** prefer simple, static, type-safe behavior over dynamic features. Code should be explicit and predictable.

- **`getattr` / `setattr` are forbidden.** Their use is a strong indication of a design flaw.
- **Prefer objects over dictionaries for structured data.** Instead of dictionaries with string keys, use `dataclasses` or Pydantic `BaseModel` to define clear, typed contracts for your data structures. This improves readability, enables static analysis, and prevents runtime errors from typos in keys.

**Example — typed data object**

    from dataclasses import dataclass

    @dataclass(frozen=True)
    class UserProfile:
        user_id: str
        email: str
        is_active: bool

    # GOOD: Clear, typed, and predictable.
    def process_user(profile: UserProfile):
        ...

**Anti-pattern**

    # BAD: Dynamic, error-prone, and hard to reason about.
    def process_user(profile: dict):
        if profile["is_active"]:  # Prone to typos, no static analysis.
            ...



## Numerics, DataFrames, and Performance

Favor **NumPy/Pandas vectorization** and **functional composition**. Think Rust: **avoid aliasing mutable data**; use a single “owner” for a frame; copy at boundaries if needed and return new objects.

**Example — functional style with DataFrames**

    def add_margin(df: pd.DataFrame, pct: float) -> pd.DataFrame:
        # Why: avoid in-place mutation of shared frames; composition-friendly.
        return df.assign(margin=lambda d: d["price"] * pct,
                         total=lambda d: d["price"] + d["price"] * pct)

Measure first, optimize second; do not micro-optimize without evidence.

**Light performance rubric**

1. Identify candidate hot paths with simple timers (`time.perf_counter()` in a focused micro-bench description).
2. Consider memory behavior when copying vs mutating.
3. Only drop to Python loops or cython/numba after profiling shows a bottleneck.



## Comments, Docstrings, and Logging

Every **2–5 lines** of logic are preceded by a comment explaining the *reason* or *purpose* behind the code (the "why"). Add additional explanation for *what* the code does when it's non-obvious (e.g., due to complexity, domain specifics, or institutional knowledge). Keep comments in sync with code.

Use **NumPy-style** docstrings, with concise examples. No `print` in library code; use `logging` with structured context.

**Example — NumPy docstring**

    def normalize(x: np.ndarray) -> np.ndarray:
        """
        Normalize a vector to unit L2 norm.

        Parameters
        ----------
        x : np.ndarray
            Input vector.

        Returns
        -------
        np.ndarray
            Normalized vector where ||x||_2 == 1.

        Examples
        --------
        >>> normalize(np.array([3.0, 4.0]))
        array([0.6, 0.8])
        """
        # Why: normalize ensures downstream algorithms assume consistent scale.
        norm = float(np.linalg.norm(x))
        if norm == 0:
            raise ValueError("cannot normalize zero vector")
        return x / norm



## Testing & Quality Gates

Adopt **unit-first** tests with deterministic fixtures and **property-based tests** for invariants. Keep tests fast and deterministic.

CI runs **ruff** (lint/imports) + **black** (format) + **pyright** (fast type checks). **Autofix CI** will apply formatting/lint changes; developers may run tools locally but are primarily responsible for ensuring code **type checks** quickly. Developers fix lint/format locally only if autofix fails.

Flaky tests: quarantine upon first verified flake; file an issue; fix before next release.



## Configuration, Packaging, and Versioning

Load config from environment/`.env` **once at process start**; validate eagerly into a **typed settings object**. Do not use `None` sentinels for required dependencies; inject settings explicitly.

Dependencies are managed with **uv**. Use `extras:dev` for ruff/pyright/pytest; allow additional extras sparingly for optional features. Use **SemVer**. Update **CHANGELOG.md** per PR under **Unreleased**, reverse chronological.



## Determinism & Seeding

A single **global constant seed** is set at process start. Imports remain at top-of-file. No nested or lazy imports. Do not mutate the seed.

**Example — deterministic seeding (entrypoint)**

    # stdlib
    import os
    import random

    # third-party
    import numpy as np

    # local
    from platform.settings import SETTINGS  # carries SEED as an int constant

    SEED: int = SETTINGS.SEED  # immutable by convention

    # Why: establish deterministic behavior across Python, NumPy, and hash randomization.
    os.environ["PYTHONHASHSEED"] = str(SEED)
    random.seed(SEED)
    np.random.seed(SEED)



## CI Automation

CI executes linters, formatters, and type checks. An autofix bot pushes non-semantic changes (format/import-sort). Reviews are not blocked by formatting nits.

Optionally, CI may warn on forbidden file paths by comparing string/path literals against the `git ls-files` allowlist. This starts as a warning until we confirm low false positives.



## Examples & Anti-Patterns

**Import grouping (good)**

    import logging
    from pathlib import Path

    import numpy as np
    import pandas as pd

    from pricing.engine import price_quote

**Type annotations (good)**

    def pct_change(xs: np.ndarray) -> np.ndarray:
        # Why: vectorized computation is faster and easier to test.
        if xs.ndim != 1:
            raise ValueError("xs must be a 1D array")
        return xs[1:] / xs[:-1] - 1.0

**Pattern matching (good)**

    def classify(kind: str) -> int:
        # Why: explicit, flat branching; easy to extend.
        match kind:
            case "retail":
                return 1
            case "wholesale":
                return 2
            case _:
                raise ValueError(f"unknown kind: {kind}")

**Exception handling (good)**

    def parse_price(s: str) -> float:
        # Why: handle only the error we can remediate; keep message actionable.
        try:
            return float(s)
        except ValueError as exc:
            raise InvalidPrice(f"invalid price: {s!r}") from exc

**Anti-patterns (never do this)**

    # BAD: nested import
    def foo():
        import numpy as np  # ❌ forbidden
        ...

    # BAD: bare except
    try:
        ...
    except:  # ❌ forbidden
        ...

    # BAD: mutable default
    def f(cfg: dict = {}):  # ❌ forbidden
        ...

    # BAD: referencing ignored/ephemeral paths
    Path("/tmp/data.csv").read_text()  # ❌ use tracked paths only



## Performance Guidance

Measure first, then optimize. Describe the context of any micro-bench (input size, machine hints). Prefer vectorization and composition; only reach for loops/numba/cython if profiling identifies a hotspot. When copying DataFrames, be deliberate about memory; document the tradeoff in a short comment.



## Refactor vs Feature — Commit Example

**Refactor (separate commit)**

    # Why: isolate rename and function extraction to keep feature diff small.
    chore(pricing): extract margin calc; rename 'calc' -> 'compute_margin'

    - Extract compute_margin(df, pct) from engine.py
    - Rename calc -> compute_margin across pricing/
    - No behavior change (verified by tests)

**Feature (follow-up commit)**

    feat(pricing): add discounted total to quotes

    - New field 'discounted_total' computed via compute_margin + discount rules
    - Update tests for quote serialization

This sequencing preserves review clarity and minimizes risk.



## Prohibitions (Hard-Fail in CI)

- Never modify `sys.path`.
- No dynamic imports, no nested imports, no `try/except` imports.
- No `from __future__ import annotations`.
- No `getattr` or `setattr`.
- No `print` in library code.
- No `except:` (bare) or catching exceptions that cannot be handled locally.
- No hidden globals or mutable default arguments.
- No premature optimization (unjustified micro-tweaks).
- No references to ephemeral or non-tracked files; prefer the `git ls-files` allowlist.
- No mixed refactor + feature in the same commit.



## Closing Notes

Prefer domain-responsibility naming, keep changes minimal, write pure typed functions with clear return annotations, validate inputs explicitly, handle exceptions where they can be resolved, choose `match/case` for stateful branching, favor vectorization and functional composition, and keep the system deterministic via a single seed at process start. Comments explain **why**. CI automates hygiene so reviews focus on behavior and design.


## Application Structure & Dependency Management

To balance framework-idiomatic patterns with our principle of explicit dependency management, we will adhere to the following structure for FastAPI applications.

-   **Application Factory Pattern**: The application object **must** be created and configured within a factory function (e.g., `create_app()`) located in a central module like `dojo.core.app`. This factory is the designated **`build_container`** for our system.
-   **Explicit Service Instantiation**: All application-level ("singleton") services (e.g., `TransactionEntryService`) **must** be instantiated within this `create_app` factory.
-   **State-Based Injection**: These instantiated services **must** be attached to the `app.state` object. This makes dependencies explicit at startup.
-   **Request-Scoped Dependencies**: For request-level resources (like a database connection), use a standard FastAPI dependency (`Depends`) that yields the resource. For application-level services, dependencies **must** access them from the request's state (e.g., `request.app.state.transaction_service`).

This pattern ensures that all major components are constructed and wired together in one auditable location, upholding the "Simple by Design" and "Transparent ⇒ Trustworthy" values.

**Example — App Factory and Dependency Access**

```python
# In dojo.core.app
from fastapi import FastAPI, Request
from dojo.budgeting.services import TransactionEntryService
from dojo.core.config import Settings

def create_app(settings: Settings) -> FastAPI:
    app = FastAPI()

    # Instantiate and attach services to the state
    app.state.transaction_service = TransactionEntryService()

    # ... register routers ...
    return app

# In a router/dependency
async def get_transaction_service(request: Request) -> TransactionEntryService:
    return request.app.state.transaction_service
```
