"""Tests for cache rebuild utilities."""

from __future__ import annotations

import importlib
from importlib import resources

import duckdb

from dojo.core.migrate import apply_migrations

cache_rebuild = importlib.import_module("dojo.core.cache_rebuild")
rebuild_caches = cache_rebuild.rebuild_caches


def _setup_db() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:")
    migrations_pkg = resources.files("dojo.sql.migrations")
    apply_migrations(conn, migrations_pkg, dry_run=False)
    return conn


def test_rebuilds_account_balances_and_category_cache() -> None:
    conn = _setup_db()

    conn.execute(
        """
        INSERT INTO budget_categories (category_id, name, is_active, is_system)
        VALUES
            ('groceries', 'Groceries', TRUE, FALSE),
            ('buffer', 'Buffer', TRUE, FALSE),
            ('payment_cc_main', 'Payment Reserve', TRUE, TRUE)
        ON CONFLICT (category_id) DO UPDATE
            SET name = excluded.name,
                is_active = excluded.is_active,
                is_system = excluded.is_system
        """
    )

    conn.execute(
        """
        INSERT INTO accounts (
            account_id,
            name,
            account_type,
            account_class,
            account_role,
            current_balance_minor,
            currency,
            is_active
        )
        VALUES
            ('cash_one', 'Cash One', 'asset', 'cash', 'on_budget', 9999, 'USD', TRUE),
            ('cc_main', 'Primary Card', 'liability', 'credit', 'on_budget', -5000, 'USD', TRUE)
        ON CONFLICT (account_id) DO UPDATE
            SET
                name = excluded.name,
                account_type = excluded.account_type,
                account_class = excluded.account_class,
                account_role = excluded.account_role,
                current_balance_minor = excluded.current_balance_minor,
                currency = excluded.currency,
                is_active = excluded.is_active
        """
    )

    conn.execute(
        """
        INSERT INTO budget_allocations (
            allocation_id,
            concept_id,
            allocation_date,
            month_start,
            from_category_id,
            to_category_id,
            amount_minor,
            memo,
            created_at,
            updated_at,
            is_active,
            valid_from,
            valid_to,
            recorded_at
        )
        VALUES
            (
                'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
                'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
                DATE '2025-01-05',
                DATE '2025-01-01',
                NULL,
                'groceries',
                40000,
                NULL,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                TRUE,
                CURRENT_TIMESTAMP,
                TIMESTAMP '9999-12-31 00:00:00',
                CURRENT_TIMESTAMP
            ),
            (
                'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2',
                'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2',
                DATE '2025-02-05',
                DATE '2025-02-01',
                'buffer',
                'groceries',
                10000,
                NULL,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                TRUE,
                CURRENT_TIMESTAMP,
                TIMESTAMP '9999-12-31 00:00:00',
                CURRENT_TIMESTAMP
            )
        """
    )

    conn.execute(
        """
        INSERT INTO transactions (
            transaction_version_id,
            concept_id,
            account_id,
            category_id,
            transaction_date,
            amount_minor,
            memo,
            status,
            recorded_at,
            valid_from,
            valid_to,
            is_active,
            source
        )
        VALUES
            (
                '11111111-1111-1111-1111-111111111111',
                'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa9',
                'cash_one',
                'groceries',
                DATE '2025-01-15',
                -30000,
                'cash grocery run',
                'cleared',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                TIMESTAMP '9999-12-31 00:00:00',
                TRUE,
                'test'
            ),
            (
                '22222222-2222-2222-2222-222222222222',
                'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb9',
                'cc_main',
                'groceries',
                DATE '2025-02-10',
                -15000,
                'credit grocery run',
                'cleared',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                TIMESTAMP '9999-12-31 00:00:00',
                TRUE,
                'test'
            )
        """
    )

    conn.execute(
        """
        INSERT INTO budget_category_monthly_state (
            category_id,
            month_start,
            allocated_minor,
            inflow_minor,
            activity_minor,
            available_minor
        )
        VALUES ('groceries', DATE '2025-01-01', 1, 2, 3, 4)
        """
    )

    rebuild_caches(conn)

    cash_balance_row = conn.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'cash_one'"
    ).fetchone()
    credit_balance_row = conn.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'cc_main'"
    ).fetchone()
    assert cash_balance_row is not None
    assert credit_balance_row is not None
    assert cash_balance_row[0] == -30000
    assert credit_balance_row[0] == -15000

    jan_row = conn.execute(
        """
        SELECT allocated_minor, inflow_minor, activity_minor, available_minor
        FROM budget_category_monthly_state
        WHERE category_id = 'groceries' AND month_start = DATE '2025-01-01'
        """
    ).fetchone()
    feb_row = conn.execute(
        """
        SELECT allocated_minor, inflow_minor, activity_minor, available_minor
        FROM budget_category_monthly_state
        WHERE category_id = 'groceries' AND month_start = DATE '2025-02-01'
        """
    ).fetchone()
    assert jan_row is not None
    assert feb_row is not None
    assert jan_row == (40000, 0, 30000, 10000)
    assert feb_row == (10000, 0, 15000, 5000)

    buffer_feb = conn.execute(
        """
        SELECT allocated_minor, available_minor
        FROM budget_category_monthly_state
        WHERE category_id = 'buffer' AND month_start = DATE '2025-02-01'
        """
    ).fetchone()
    assert buffer_feb is not None
    assert buffer_feb == (-10000, -10000)

    payment_row = conn.execute(
        """
        SELECT inflow_minor, available_minor
        FROM budget_category_monthly_state
        WHERE category_id = 'payment_cc_main' AND month_start = DATE '2025-02-01'
        """
    ).fetchone()
    assert payment_row is not None
    assert payment_row == (15000, 15000)
