# Python Guide — Architecture, Correctness, and State

This guide focuses on **non-lintable rules**: architectural patterns, correctness guarantees, and domain conventions. Mechanical style, formatting, and most micro–best practices are delegated to our linters (Ruff, Pyright, formatters). When in doubt, treat **the linters + their config as the single source of truth** for style.

This file should stay short and high-signal. If a rule can be enforced in a linter, put it in the linter config, not here.


## 1. Organize by Domain, Not by Layer

Code lives next to the domain it serves.

- Group modules by responsibility, e.g.:

    src/dojo/
      core/
        app.py
        db.py
        config.py
      budgeting/
        routers.py
        service.py
        dao.py
      investments/
        routers.py
        service.py
        optimizer.py

- Cross-cutting helpers live under a small `infra/` (or `platform/`) only when they are truly shared.
- When adding new code, put it next to the module that **owns the concept in the domain**, not where it’s most “convenient” to import.

If you’re unsure where something belongs, it probably means we need a new small domain package, not a bigger `utils.py`.


## 2. Application Wiring & Dependencies

FastAPI apps follow the **application factory** + **explicit container** pattern:

- `dojo.core.app:create_app` is the only place we assemble the app.
- `build_container(cfg)` (or equivalent) is the only place we call `.from_defaults()` or build long-lived services.
- All long-lived services are attached to `app.state.*` and accessed via typed dependencies:

    async def get_transaction_service(request: Request) -> TransactionEntryService:
        return request.app.state.transaction_service

Rules:

- Never hide new global singletons in imports or module top-levels.
- Always thread dependencies through the container and FastAPI `Depends`.
- Never read env vars in leaf modules. Read config once at startup into a typed `Settings` object and pass that inward.


## 3. Data Flow: Functional Core, Imperative Shell

The “core logic” of money movement and analytics must be:

- Pure (no I/O, no global reads/writes).
- Typed (Pyright should be happy).
- Deterministic (no hidden randomness, no “current time” lookups inside).

The shell (routers, CLIs, background jobs) is where we:

- Parse inputs.
- Manage DB connections.
- Call external services.
- Log, retry, and enforce timeouts.

Rules:

- Domain services should be mostly pure methods that take plain data classes and return new data / SQL operations.
- Side effects (DB writes, HTTP calls, logging) should be confined to a thin layer at the edges.
- If a function mixes complex business rules with I/O, split it: one pure function for the rules, one small wrapper for the side effects.


## 4. State Machines and `match/case` (Exhaustiveness Is Mandatory)

We treat domain state as **closed sets** and want the type system and pattern matching to enforce exhaustiveness.

### 4.1 Model State with Enums / Literals

- Encode discrete states as `Enum`, `Literal` types, or Pydantic discriminated unions—never ad-hoc strings.
- Examples: transaction status, ledger entry kind, budget category type, portfolio regime.

    from enum import Enum

    class LedgerEntryKind(str, Enum):
        TRANSACTION = "transaction"
        ALLOCATION = "allocation"
        TRANSFER = "transfer"

### 4.2 Use `match/case` for Branching on Closed Sets

**Rule (hard requirement):** When branching on a closed set (enums, literals, discriminated unions), use `match/case` instead of long `if/elif` chains.

Bad:

    if kind == LedgerEntryKind.TRANSACTION:
        handle_transaction(entry)
    elif kind == LedgerEntryKind.ALLOCATION:
        handle_allocation(entry)
    elif kind == LedgerEntryKind.TRANSFER:
        handle_transfer(entry)
    else:
        raise ValueError("unknown kind")

Good:

    class UnexpectedEntryKind(RuntimeError):
        ...

    def handle_entry(kind: LedgerEntryKind, entry: LedgerEntry) -> None:
        match kind:
            case LedgerEntryKind.TRANSACTION:
                handle_transaction(entry)
            case LedgerEntryKind.ALLOCATION:
                handle_allocation(entry)
            case LedgerEntryKind.TRANSFER:
                handle_transfer(entry)
            case _:
                # This should be unreachable: treat as a bug, not user error.
                raise UnexpectedEntryKind(kind)

### 4.3 Exhaustiveness & Safety

We want changes in valid states to break loudly.

- When adding a new enum value or union case, tests should fail or Pyright should complain until all `match` branches are updated.
- `case _` is only for “this should never happen” conditions. Do not use it to silently swallow new states.
- If you must allow unknown states (e.g., forward-compat deserialization), normalize them at the boundary (parsing layer) and keep core logic on a known, closed set.

For non-trivial state machines:

- Add a small “state transition” test that enumerates allowed transitions and fails on any unexpected combination.
- Prefer explicit transition functions (e.g., `advance_reconciliation_state`) that `match` on both current state and event and return the next state.


## 5. Exceptions and Domain Errors

We prefer **typed domain exceptions** instead of generic `ValueError` / `RuntimeError` in core flows.

Rules:

- Catch infra exceptions (DB, HTTP, filesystem) at the boundary and rethrow as domain exceptions with context.
- Don’t catch exceptions you can’t actually handle; let them bubble to FastAPI/CLI where they become responses or logs.
- Use `assert` only for internal invariants that truly indicate a programmer error; everything else should raise a real exception.

Example:

    class BudgetConstraintError(RuntimeError):
        ...

    def allocate_funds(...) -> None:
        if amount_minor < 0:
            raise BudgetConstraintError("Allocation amount must be non-negative")


## 6. Data Structures: Dataclasses over Dicts

Structured data should be expressed as **typed objects**, not generic `dict[str, Any]`.

Rules:

- Use `@dataclass(frozen=True)` or Pydantic models for payloads, rows, and internal DTOs.
- Do not pass around “bags of data” as untyped dicts in domain code.
- Conversions from/to dict (FastAPI, JSON, DB rows) should happen at the edge, not in the core.


## 7. Numerics and Money

We follow financial rules in `fin_math.md`. For Python code specifically:

- Ledger values (account balances, transaction amounts) must be stored as integers in minor units (cents) or `Decimal` with fixed quantization.
- Analytical code (returns, optimizations) should use float64 arrays / Series and keep everything vectorized where possible.
- Do not mix ledger math and analytics math in the same function; keep a clean boundary.


## 8. Determinism and Seeding

Simulations, optimizers, and any code that samples randomness must be deterministic under a fixed seed.

Rules:

- Seed randomness once, at process entry (see app entrypoints), and treat the seed as immutable configuration.
- Do not call `random.seed` / `np.random.seed` inside library functions.
- For sampling-heavy functions, accept an explicit RNG object when needed rather than touching global RNGs.

For new stochastic algorithms, add tests that:

- Run twice with the same seed and assert identical outputs.
- Run with different seeds and assert outputs differ in plausible ways.


## 9. Logging and Observability

- No `print` in library code; use structured logging.
- Log domain events at the edges of flows (starting a complex operation, finishing it, and any non-fatal anomalies).
- For money movement, log enough to reconstruct what happened and why, without leaking secrets.

If you’re unsure what to log, think: “how would I debug this issue in production with only logs and DB access?”


## 10. Tests and Invariants

Tests should:

- Cover domain invariants (envelope constraints, temporal ledger semantics) with property tests where possible.
- Include “golden path” tests that reflect real-world flows (payday → allocation → spend → reconcile).
- Fail loudly when we change enums, states, or schema in breaking ways.

When you change core behavior:

- Update or add tests first.
- Make sure tests describe what must never happen again, not just what you changed.


## 11. What Linters Cover (So We Don’t Repeat It Here)

The following concerns are delegated to tooling and should not be restated as prose rules:

- Import ordering and grouping.
- Banned patterns like modifying `sys.path`, nested imports, bare `except:`, unused variables, etc.
- Formatting (spacing, quotes, line length, etc.).
- Most stylistic nitpicks.

If you want a mechanical rule, ask first: “Can Ruff/Pyright/formatter enforce this?” If yes, change the config and keep this document focused on **architecture, state, and correctness**.

