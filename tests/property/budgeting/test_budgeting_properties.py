"""
Property-based tests for budgeting service invariants.

This module uses the Hypothesis library to perform property-based testing
on core budgeting functionalities, ensuring that fundamental invariants
(e.g., conservation of money, cache correctness) hold true under a wide
range of generated inputs.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from importlib import resources
from types import SimpleNamespace
import duckdb

from hypothesis import given, settings, strategies as st

from dojo.budgeting.schemas import BudgetAllocationRequest, NewTransactionRequest
from dojo.budgeting.services import TransactionEntryService
from dojo.budgeting.dao import BudgetingDAO
from dojo.core.migrate import apply_migrations
from dojo.testing.fixtures import apply_base_budgeting_fixture


@contextmanager
def ledger_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Creates an in-memory DuckDB connection with schema and base fixtures applied.

    This fixture is used by property-based tests to provide a clean and consistent
    database state for each test run.

    Yields
    ------
    Generator[duckdb.DuckDBPyConnection, None, None]
        An in-memory DuckDB connection object.
    """
    conn = duckdb.connect(database=":memory:")
    # Get the package path where migration SQL files are located.
    migrations_pkg = resources.files("dojo.sql.migrations")
    # Apply all schema migrations to the in-memory database.
    apply_migrations(conn, migrations_pkg)
    # Apply a base set of budgeting data for tests.
    apply_base_budgeting_fixture(conn)
    try:
        yield conn
    finally:
        # Ensure the connection is closed after the test completes.
        conn.close()


def build_transaction_service() -> TransactionEntryService:
    """
    Builds and returns a new TransactionEntryService instance.

    Returns
    -------
    TransactionEntryService
        A new instance of the TransactionEntryService.
    """
    return TransactionEntryService()


def _fetch_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> SimpleNamespace | None:
    """
    Executes an SQL query and fetches a single row as a SimpleNamespace.

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection
        The DuckDB connection object.
    sql : str
        The SQL query string to execute.
    params : list[object] | tuple[object, ...] | None, optional
        Parameters to bind to the SQL query.

    Returns
    -------
    SimpleNamespace | None
        A SimpleNamespace object if a row is fetched, otherwise None.
    """
    cursor = conn.execute(sql, params or [])
    row = cursor.fetchone()
    if row is None:
        return None
    # Extract column names from the cursor description.
    columns = [column[0] for column in cursor.description or ()]
    # Map column names to row values and create a SimpleNamespace.
    data = {columns[idx]: row[idx] for idx in range(len(columns))}
    return SimpleNamespace(**data)


# --- Conservation of Money Invariant ---

# Predefined categories available for reallocation tests.
CATEGORIES = ["groceries", "housing"]
# Strategy for generating allocation amounts (1 to 100 USD in minor units).
allocation_amount_strategy = st.integers(min_value=1, max_value=100_00)


@st.composite
def reallocation_strategy(draw):
    """
    Hypothesis strategy for generating valid budget reallocation requests.

    This strategy ensures that `from_category` and `to_category` are distinct
    and draws a valid allocation amount.

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    BudgetAllocationRequest
        A generated `BudgetAllocationRequest` for reallocating funds.
    """
    # Draw a source category from the predefined list.
    from_category = draw(st.sampled_from(CATEGORIES))
    # Draw a destination category, ensuring it's different from the source.
    to_category = draw(st.sampled_from([c for c in CATEGORIES if c != from_category]))
    # Draw an allocation amount.
    amount = draw(allocation_amount_strategy)
    return BudgetAllocationRequest(
        from_category_id=from_category,
        to_category_id=to_category,
        amount_minor=amount,
    )


@given(reallocations=st.lists(reallocation_strategy(), min_size=1, max_size=5))
@settings(max_examples=10, deadline=None)
def test_conservation_of_money_in_reallocation(reallocations):
    """
    Verifies the conservation of money invariant during budget reallocations.

    This property test asserts that the total sum of `available_minor` balances
    across all relevant budget categories remains constant after a series of
    random reallocations within a given month. Funds are merely moved between
    categories, not created or destroyed.

    Parameters
    ----------
    reallocations : list[BudgetAllocationRequest]
        A list of generated `BudgetAllocationRequest` objects representing
        reallocations to be performed.
    """
    with ledger_connection() as conn:
        service = build_transaction_service()
        dao = BudgetingDAO(conn)
        month = date.today().replace(day=1)

        # Prime the categories with some initial funds to allow for reallocations.
        # This ensures there's enough 'available_minor' to draw from.
        service.allocate_envelope(conn, "groceries", 500_00, month)
        service.allocate_envelope(conn, "housing", 1500_00, month)

        # Get initial total available funds across the relevant categories.
        initial_available_row = _fetch_namespace(
            conn,
            "SELECT SUM(available_minor) AS total_available FROM budget_category_monthly_state WHERE month_start = ?",
            [month],
        )
        initial_available = (
            int(initial_available_row.total_available) if initial_available_row else 0
        )

        # Perform the generated reallocations.
        for reallocation in reallocations:
            from_category_state_record = dao.get_category_month_state(
                reallocation.from_category_id, month
            )

            # Only perform reallocation if the source category has sufficient funds.
            if (
                from_category_state_record
                and from_category_state_record.available_minor
                >= reallocation.amount_minor
            ):
                service.allocate_envelope(
                    conn,
                    reallocation.to_category_id,
                    reallocation.amount_minor,
                    month,
                    from_category_id=reallocation.from_category_id,
                )

        # Get final total available funds after all reallocations.
        final_available_row = _fetch_namespace(
            conn,
            "SELECT SUM(available_minor) AS total_available FROM budget_category_monthly_state WHERE month_start = ?",
            [month],
        )
        final_available = (
            int(final_available_row.total_available) if final_available_row else 0
        )

        # Assert that the total available funds remain unchanged.
        assert initial_available == final_available


# --- Cache Correctness Invariant ---

# Strategy for generating transaction amounts (negative, for spending scenarios).
transaction_amount_strategy = st.integers(min_value=-100_00, max_value=-1)
# Strategy for generating allocation amounts (positive).
allocation_amount_strategy = st.integers(min_value=1, max_value=500_00)


@st.composite
def inflow_transactions_strategy(draw):
    """
    Hypothesis strategy for generating inflow transaction requests.

    These transactions are typically used to increase the "Ready to Assign"
    pool of funds before allocations or spending.

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    NewTransactionRequest
        A generated `NewTransactionRequest` for an inflow transaction.
    """
    amount = draw(st.integers(min_value=1000_00, max_value=5000_00))
    return NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="income",
        amount_minor=amount,
    )


@st.composite
def spending_transactions_strategy(draw):
    """
    Hypothesis strategy for generating spending transaction requests.

    These transactions simulate outflows from an account and are categorized
    to impact budget categories.

    Parameters
    ----------
    draw : Callable
        A function provided by Hypothesis to draw values from other strategies.

    Returns
    -------
    NewTransactionRequest
        A generated `NewTransactionRequest` for a spending transaction.
    """
    amount = draw(transaction_amount_strategy)
    return NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="groceries",
        amount_minor=amount,
    )


@given(
    inflows=st.lists(inflow_transactions_strategy(), min_size=1, max_size=2),
    spendings=st.lists(spending_transactions_strategy(), min_size=1, max_size=5),
    allocations=st.lists(allocation_amount_strategy, min_size=1, max_size=3),
)
@settings(max_examples=10, deadline=None)
def test_budget_category_cache_correctness(inflows, spendings, allocations):
    """
    Verifies that the `budget_category_monthly_state` table (a cache)
    correctly reflects values derived directly from source tables.

    This property test ensures consistency between the cached monthly budget
    category state and the raw data from `transactions` and `budget_allocations`
    tables after a series of randomized inflows, spendings, and allocations.

    Parameters
    ----------
    inflows : list[NewTransactionRequest]
        A list of generated inflow transaction requests.
    spendings : list[NewTransactionRequest]
        A list of generated spending transaction requests.
    allocations : list[int]
        A list of generated allocation amounts (in minor units).
    """
    with ledger_connection() as conn:
        service = build_transaction_service()
        month = date.today().replace(day=1)

        TARGET_CATEGORY = "groceries"

        # 1. Execute operations: Apply generated inflows, spendings, and allocations.

        for inflow in inflows:
            service.create(conn, inflow)

        for spending in spendings:
            service.create(conn, spending)

        for allocation in allocations:
            service.allocate_envelope(conn, TARGET_CATEGORY, allocation, month)

        # 2. Manual calculation: Directly calculate expected values from source tables.

        # Calculate expected activity for the target category from transactions.
        expected_activity_row = _fetch_namespace(
            conn,
            "SELECT SUM(amount_minor) AS total_activity FROM transactions WHERE category_id = ? AND strftime('%Y-%m', transaction_date) = ?",
            [TARGET_CATEGORY, month.strftime("%Y-%m")],
        )
        raw_activity = (
            int(expected_activity_row.total_activity)
            if expected_activity_row and expected_activity_row.total_activity
            else 0
        )
        # Activity is typically the negative of the sum of transaction amounts for an expense category.
        expected_activity = -raw_activity

        # Calculate expected allocated amount for the target category from budget_allocations.
        expected_allocated_row = _fetch_namespace(
            conn,
            "SELECT SUM(amount_minor) AS total_allocated FROM budget_allocations WHERE to_category_id = ? AND month_start = ?",
            [TARGET_CATEGORY, month],
        )
        expected_allocated = (
            int(expected_allocated_row.total_allocated)
            if expected_allocated_row and expected_allocated_row.total_allocated
            else 0
        )

        # For this test, `inflow_minor` is 0 because we only allocate from
        # "Ready to Assign" (or other categories), which primarily affects the `allocated_minor` column.
        expected_inflow = 0

        # Available balance is calculated as allocated minus activity.
        expected_available = expected_allocated - expected_activity

        # 3. Fetch from cache: Retrieve cached values from `budget_category_monthly_state`.

        cache_row = conn.execute(
            "SELECT allocated_minor, inflow_minor, activity_minor, available_minor FROM budget_category_monthly_state WHERE category_id = ? AND month_start = ?",
            [TARGET_CATEGORY, month],
        ).fetchone()

        assert cache_row is not None, (
            "Cache row was not created for the target category."
        )

        cached_allocated, cached_inflow, cached_activity, cached_available = cache_row

        # 4. Assertions: Compare manually calculated values with cached values.

        assert cached_activity == expected_activity, (
            "Activity mismatch between cached and calculated values."
        )
        assert cached_allocated == expected_allocated, (
            "Allocated amount mismatch between cached and calculated values."
        )
        assert cached_inflow == expected_inflow, (
            "Inflow mismatch between cached and calculated values."
        )
        assert cached_available == expected_available, (
            "Available balance mismatch between cached and calculated values."
        )


def test_group_category_relationship():
    """








    Verifies the integrity of `budget_category` to `budget_category_group` relationships.

















    This test asserts that every `budget_category` that has a `group_id`








    correctly links to an existing and unique `budget_category_group`.








    It helps ensure referential integrity and consistency in the budgeting structure.








    """

    with ledger_connection() as conn:
        # Fetch all category IDs and their associated group IDs.

        categories = conn.execute(
            "SELECT category_id, group_id FROM budget_categories"
        ).fetchall()

        for category_id, group_id in categories:
            # Only check categories that are assigned to a group.

            if group_id is not None:
                # Query to count groups matching the group_id.

                group_row = _fetch_namespace(
                    conn,
                    "SELECT COUNT(*) AS group_count FROM budget_category_groups WHERE group_id = ?",
                    [group_id],
                )

                # Assert that exactly one group matches the group_id, ensuring validity and uniqueness.

                assert group_row and group_row.group_count == 1, (
                    f"Category '{category_id}' has invalid group_id '{group_id}'"
                )
