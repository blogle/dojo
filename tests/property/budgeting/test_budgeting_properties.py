"""Property-based tests for budgeting service invariants."""

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
    """Create an in-memory DuckDB connection with all migrations and base fixtures applied."""
    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg)
    apply_base_budgeting_fixture(conn)
    try:
        yield conn
    finally:
        conn.close()


def build_transaction_service() -> TransactionEntryService:
    return TransactionEntryService()


def _fetch_namespace(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> SimpleNamespace | None:
    cursor = conn.execute(sql, params or [])
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [column[0] for column in cursor.description or ()]
    data = {columns[idx]: row[idx] for idx in range(len(columns))}
    return SimpleNamespace(**data)


# --- Conservation of Money Invariant ---

CATEGORIES = ["groceries", "housing"]
allocation_amount_strategy = st.integers(min_value=1, max_value=100_00)


@st.composite
def reallocation_strategy(draw):
    from_category = draw(st.sampled_from(CATEGORIES))
    to_category = draw(st.sampled_from([c for c in CATEGORIES if c != from_category]))
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
    Verify that performing random reallocations between budget categories
    within a month asserts that the sum of all `available_minor` balances
    remains constant.
    """
    with ledger_connection() as conn:
        service = build_transaction_service()
        dao = BudgetingDAO(conn)
        month = date.today().replace(day=1)

        # Prime the categories with some funds to reallocate
        service.allocate_envelope(conn, "groceries", 500_00, month)
        service.allocate_envelope(conn, "housing", 1500_00, month)

        # Get initial total available
        initial_available_row = _fetch_namespace(
            conn,
            "SELECT SUM(available_minor) AS total_available FROM budget_category_monthly_state WHERE month_start = ?",
            [month],
        )
        initial_available = int(initial_available_row.total_available) if initial_available_row else 0

        # Perform reallocations
        for reallocation in reallocations:
            from_category_state_record = dao.get_category_month_state(
                reallocation.from_category_id, month
            )

            if from_category_state_record and from_category_state_record.available_minor >= reallocation.amount_minor:
                service.allocate_envelope(
                    conn,
                    reallocation.to_category_id,
                    reallocation.amount_minor,
                    month,
                    from_category_id=reallocation.from_category_id,
                )

        # Get final total available
        final_available_row = _fetch_namespace(
            conn,
            "SELECT SUM(available_minor) AS total_available FROM budget_category_monthly_state WHERE month_start = ?",
            [month],
        )
        final_available = int(final_available_row.total_available) if final_available_row else 0

        assert initial_available == final_available


# --- Cache Correctness Invariant ---

transaction_amount_strategy = st.integers(min_value=-100_00, max_value=-1)
allocation_amount_strategy = st.integers(min_value=1, max_value=500_00)


@st.composite
def inflow_transactions_strategy(draw):
    amount = draw(st.integers(min_value=1000_00, max_value=5000_00))
    return NewTransactionRequest(
        transaction_date=date.today(),
        account_id="house_checking",
        category_id="income",
        amount_minor=amount,
    )


@st.composite
def spending_transactions_strategy(draw):
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


    Verify that the `budget_category_monthly_state` table (a cache)


    correctly reflects the values derived directly from the


    `transactions` and `budget_allocations` tables.


    """


    with ledger_connection() as conn:


        service = build_transaction_service()


        month = date.today().replace(day=1)


        TARGET_CATEGORY = "groceries"





        # 1. Execute operations


        for inflow in inflows:


            service.create(conn, inflow)


        for spending in spendings:


            service.create(conn, spending)


        for allocation in allocations:


            service.allocate_envelope(conn, TARGET_CATEGORY, allocation, month)





        # 2. Manual calculation


        expected_activity_row = _fetch_namespace(
            conn,
            "SELECT SUM(amount_minor) AS total_activity FROM transactions WHERE category_id = ? AND strftime('%Y-%m', transaction_date) = ?",
            [TARGET_CATEGORY, month.strftime('%Y-%m')],
        )
        raw_activity = (
            int(expected_activity_row.total_activity)
            if expected_activity_row and expected_activity_row.total_activity
            else 0
        )
        expected_activity = -raw_activity

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



        


        # For this test, inflow_minor is 0 because we only allocate from 


        # Ready to Assign, which is handled via the `allocated_minor` column.


        expected_inflow = 0


        


        expected_available = expected_allocated - expected_activity





        # 3. Fetch from cache


        cache_row = conn.execute(


            "SELECT allocated_minor, inflow_minor, activity_minor, available_minor FROM budget_category_monthly_state WHERE category_id = ? AND month_start = ?",


            [TARGET_CATEGORY, month]


        ).fetchone()





        assert cache_row is not None, "Cache row was not created"


        cached_allocated, cached_inflow, cached_activity, cached_available = cache_row





        # 4. Assertions


        assert cached_activity == expected_activity, "Activity mismatch"


        assert cached_allocated == expected_allocated, "Allocation mismatch"


        assert cached_inflow == expected_inflow, "Inflow mismatch"


        assert cached_available == expected_available, "Available balance mismatch"








def test_group_category_relationship():


    """


    Verify that every `budget_category` has a valid `group_id` linking 


    it to a `budget_category_group`.


    """


    with ledger_connection() as conn:


        categories = conn.execute("SELECT category_id, group_id FROM budget_categories").fetchall()


        for category_id, group_id in categories:


            if group_id is not None:


                group_row = _fetch_namespace(
                    conn,
                    "SELECT COUNT(*) AS group_count FROM budget_category_groups WHERE group_id = ?",
                    [group_id],
                )
                assert group_row and group_row.group_count == 1, f"Category '{category_id}' has invalid group_id '{group_id}'"


