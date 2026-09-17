"""Integration tests for Aspire transfer exception resolution contracts."""

from __future__ import annotations

import json
from datetime import date

import duckdb
from fastapi.testclient import TestClient


def _seed_transfer_session(pristine_db: duckdb.DuckDBPyConnection, *, session_id: str = "sess-transfer") -> None:
    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            },
            "Savings": {
                "dojo_name": "Savings",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            },
            "Brokerage": {
                "dojo_name": "Brokerage",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            },
        },
        "categories": {},
    }
    labels = {
        "v_AccountTransfer": "Transfer",
        "v_AtoB": "Ready to Assign",
        "v_StartingBalance": "Starting Balance",
        "v_BalanceAdjustment": "Balance Adjustment",
        "v_Today": "2025-01-10",
    }

    pristine_db.execute(
        """
        UPDATE onboarding_state
        SET onboarding_mode = 'aspire',
            onboarding_status = 'in_progress',
            migration_session_id = $session_id,
            updated_at = CURRENT_TIMESTAMP
        WHERE onboarding_id = 'primary'
        """,
        {"session_id": session_id},
    )

    pristine_db.execute(
        """
        INSERT INTO aspire_migration_sessions (
            migration_session_id,
            extraction_status,
            mapping_status,
            import_status,
            dataset_fingerprint,
            mapping_json,
            special_labels_json,
            status_symbols_json,
            updated_at
        ) VALUES (
            $session_id,
            'completed',
            'completed',
            'not_started',
            'fp-transfer',
            $mapping_json,
            $labels_json,
            '{}',
            CURRENT_TIMESTAMP
        )
        """,
        {
            "session_id": session_id,
            "mapping_json": json.dumps(mapping, separators=(",", ":"), sort_keys=True),
            "labels_json": json.dumps(labels, separators=(",", ":"), sort_keys=True),
        },
    )

    pristine_db.executemany(
        """
        INSERT INTO aspire_staging_transactions (
            migration_session_id,
            row_index,
            transaction_date,
            amount_minor,
            category_name,
            account_name,
            memo,
            status,
            is_break
        ) VALUES (?, ?, DATE '2025-01-10', ?, 'Transfer', ?, ?, 'cleared', FALSE)
        """,
        [
            [session_id, 1, -50000, "Checking", "Outbound transfer"],
            [session_id, 2, 50000, "Savings", "Inbound candidate A"],
            [session_id, 3, 50000, "Brokerage", "Inbound candidate B"],
        ],
    )


def _seed_preview_session(
    pristine_db: duckdb.DuckDBPyConnection,
    *,
    session_id: str,
    mapping: dict,
    net_worth_decisions_json: str | None = None,
) -> None:
    labels = {
        "v_AccountTransfer": "Transfer",
        "v_AtoB": "Ready to Assign",
        "v_StartingBalance": "Starting Balance",
        "v_BalanceAdjustment": "Balance Adjustment",
        "v_Today": "2025-01-10",
    }

    pristine_db.execute(
        """
        UPDATE onboarding_state
        SET onboarding_mode = 'aspire',
            onboarding_status = 'in_progress',
            migration_session_id = $session_id,
            updated_at = CURRENT_TIMESTAMP
        WHERE onboarding_id = 'primary'
        """,
        {"session_id": session_id},
    )

    pristine_db.execute(
        """
        INSERT INTO aspire_migration_sessions (
            migration_session_id,
            extraction_status,
            mapping_status,
            import_status,
            dataset_fingerprint,
            mapping_json,
            special_labels_json,
            status_symbols_json,
            net_worth_decisions_json,
            updated_at
        ) VALUES (
            $session_id,
            'completed',
            'completed',
            'not_started',
            'fp-preview',
            $mapping_json,
            $labels_json,
            '{}',
            $net_worth_decisions_json,
            CURRENT_TIMESTAMP
        )
        """,
        {
            "session_id": session_id,
            "mapping_json": json.dumps(mapping, separators=(",", ":"), sort_keys=True),
            "labels_json": json.dumps(labels, separators=(",", ":"), sort_keys=True),
            "net_worth_decisions_json": net_worth_decisions_json,
        },
    )


def _seed_apply_session(
    pristine_db: duckdb.DuckDBPyConnection,
    *,
    session_id: str,
    mapping: dict,
    transactions: list[tuple[int, int, str, str, str]],
    net_worth_decisions: dict | None = None,
    net_worth_marks: list[tuple[int, str, str, int, str | None, str | None]] | None = None,
) -> None:
    labels = {
        "v_AccountTransfer": "Transfer",
        "v_AtoB": "Ready to Assign",
        "v_StartingBalance": "Starting Balance",
        "v_BalanceAdjustment": "Balance Adjustment",
        "v_Today": "2025-01-10",
    }

    pristine_db.execute(
        """
        UPDATE onboarding_state
        SET onboarding_mode = 'aspire',
            onboarding_status = 'in_progress',
            migration_session_id = $session_id,
            updated_at = CURRENT_TIMESTAMP
        WHERE onboarding_id = 'primary'
        """,
        {"session_id": session_id},
    )

    pristine_db.execute(
        """
        INSERT INTO aspire_migration_sessions (
            migration_session_id,
            extraction_status,
            mapping_status,
            import_status,
            dataset_fingerprint,
            mapping_json,
            special_labels_json,
            status_symbols_json,
            net_worth_decisions_json,
            updated_at
        ) VALUES (
            $session_id,
            'completed',
            'completed',
            'not_started',
            'fp-apply',
            $mapping_json,
            $labels_json,
            '{}',
            $net_worth_decisions_json,
            CURRENT_TIMESTAMP
        )
        """,
        {
            "session_id": session_id,
            "mapping_json": json.dumps(mapping, separators=(",", ":"), sort_keys=True),
            "labels_json": json.dumps(labels, separators=(",", ":"), sort_keys=True),
            "net_worth_decisions_json": (
                json.dumps(net_worth_decisions, separators=(",", ":"), sort_keys=True)
                if net_worth_decisions is not None
                else None
            ),
        },
    )

    pristine_db.executemany(
        """
        INSERT INTO aspire_staging_transactions (
            migration_session_id,
            row_index,
            transaction_date,
            amount_minor,
            category_name,
            account_name,
            memo,
            status,
            is_break
        ) VALUES (?, ?, DATE '2025-01-10', ?, ?, ?, ?, 'cleared', FALSE)
        """,
        [
            [session_id, row_index, amount_minor, category_name, account_name, memo]
            for row_index, amount_minor, category_name, account_name, memo in transactions
        ],
    )

    if net_worth_marks:
        pristine_db.executemany(
            """
            INSERT INTO aspire_staging_net_worth_marks (
                migration_session_id,
                row_index,
                mark_date,
                category_name,
                amount_minor,
                note,
                breakpoint
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                [
                    session_id,
                    row_index,
                    mark_date,
                    category_name,
                    amount_minor,
                    note,
                    breakpoint,
                ]
                for row_index, mark_date, category_name, amount_minor, note, breakpoint in net_worth_marks
            ],
        )


def _seed_mapping_preview_session(
    pristine_db: duckdb.DuckDBPyConnection,
    *,
    session_id: str,
) -> None:
    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            },
            "Savings": {
                "dojo_name": "Savings",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            },
        },
        "categories": {
            "Groceries": {
                "dojo_name": "Groceries",
                "group_name": "Living",
                "is_active": True,
                "goal_type": "recurring",
                "goal_amount_minor": 2500,
                "goal_frequency": "monthly",
            }
        },
    }
    labels = {
        "v_AccountTransfer": "Transfer",
        "v_AtoB": "Ready to Assign",
        "v_StartingBalance": "Starting Balance",
        "v_BalanceAdjustment": "Balance Adjustment",
        "v_Today": "2025-01-10",
    }

    pristine_db.execute(
        """
        UPDATE onboarding_state
        SET onboarding_mode = 'aspire',
            onboarding_status = 'in_progress',
            migration_session_id = $session_id,
            updated_at = CURRENT_TIMESTAMP
        WHERE onboarding_id = 'primary'
        """,
        {"session_id": session_id},
    )

    pristine_db.execute(
        """
        INSERT INTO aspire_migration_sessions (
            migration_session_id,
            extraction_status,
            mapping_status,
            import_status,
            dataset_fingerprint,
            mapping_json,
            special_labels_json,
            status_symbols_json,
            user_def_amounts_json,
            category_type_symbols_json,
            configuration_rows_json,
            dashboard_category_proxy_json,
            updated_at
        ) VALUES (
            $session_id,
            'completed',
            'completed',
            'not_started',
            'fp-mapping-preview',
            $mapping_json,
            $labels_json,
            '{}',
            $user_def_amounts_json,
            $category_type_symbols_json,
            $configuration_rows_json,
            $dashboard_proxy_json,
            CURRENT_TIMESTAMP
        )
        """,
        {
            "session_id": session_id,
            "mapping_json": json.dumps(mapping, separators=(",", ":"), sort_keys=True),
            "labels_json": json.dumps(labels, separators=(",", ":"), sort_keys=True),
            "user_def_amounts_json": json.dumps({"Groceries": 2500}, separators=(",", ":"), sort_keys=True),
            "category_type_symbols_json": json.dumps(
                {
                    "v_CategoryGroupSymbol": "grp",
                    "v_ReportableCategorySymbol": "rep",
                    "v_NonReportableCategorySymbol": "non",
                    "v_DebtAccountSymbol": "debt",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            "configuration_rows_json": json.dumps(
                [
                    {
                        "row_type_symbol": "grp",
                        "name": "Living",
                        "monthly_target_minor": 0,
                        "due_date": None,
                        "goal_amount_minor": 0,
                    },
                    {
                        "row_type_symbol": "rep",
                        "name": "Groceries",
                        "monthly_target_minor": 2500,
                        "due_date": None,
                        "goal_amount_minor": 0,
                    },
                ],
                separators=(",", ":"),
                sort_keys=True,
            ),
            "dashboard_proxy_json": json.dumps(
                {
                    "Groceries": {
                        "configured_budget_minor": 2500,
                        "budgeted_minor": 1500,
                        "activity_minor": -2800,
                        "available_minor": 5500,
                    }
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
    )

    pristine_db.executemany(
        """
        INSERT INTO aspire_staging_transactions (
            migration_session_id,
            row_index,
            transaction_date,
            amount_minor,
            category_name,
            account_name,
            memo,
            status,
            is_break
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, FALSE)
        """,
        [
            [session_id, 1, date(2024, 12, 20), -3000, "Groceries", "Checking", "older", "cleared"],
            [session_id, 2, date(2025, 1, 5), -5000, "Groceries", "Checking", "current", "cleared"],
            [session_id, 3, date(2025, 1, 8), 2000, "Groceries", "Checking", "refund pending", "pending"],
            [session_id, 4, date(2025, 1, 12), -9000, "Groceries", "Checking", "future", "cleared"],
            [session_id, 5, date(2025, 1, 9), -10000, "Rent", "Savings", "rent", "cleared"],
        ],
    )

    pristine_db.executemany(
        """
        INSERT INTO aspire_staging_allocations (
            migration_session_id,
            row_index,
            allocation_date,
            amount_minor,
            from_category_name,
            to_category_name
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            [session_id, 1, date(2024, 12, 15), 10000, "Ready to Assign", "Groceries"],
            [session_id, 2, date(2025, 1, 3), 2000, "Ready to Assign", "Groceries"],
            [session_id, 3, date(2025, 1, 7), 500, "Groceries", "Rent"],
            [session_id, 4, date(2025, 1, 12), 700, "Ready to Assign", "Groceries"],
        ],
    )


def test_mapping_preview_uses_as_of_cutoff_and_reports_proxy_drift(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    _seed_mapping_preview_session(pristine_db, session_id="sess-mapping-preview")

    response = api_client.get("/api/onboarding/aspire/mapping")
    assert response.status_code == 200, response.text
    payload = response.json()

    accounts = payload["mapping"]["accounts"]
    assert accounts["Checking"]["current_balance_minor"] == -8000
    assert accounts["Checking"]["pending_balance_minor"] == 2000
    assert accounts["Savings"]["current_balance_minor"] == -10000

    groceries = payload["mapping"]["categories"]["Groceries"]
    assert groceries["configured_budget_minor"] == 2500
    assert groceries["budgeted_minor"] == 1500
    assert groceries["activity_minor"] == -3000
    assert groceries["available_minor"] == 5500

    assert groceries["proxy_configured_budget_minor"] == 2500
    assert groceries["proxy_budgeted_minor"] == 1500
    assert groceries["proxy_activity_minor"] == -2800
    assert groceries["proxy_available_minor"] == 5500

    assert groceries["drift_configured_budget_minor"] == 0
    assert groceries["drift_budgeted_minor"] == 0
    assert groceries["drift_activity_minor"] == -200
    assert groceries["drift_available_minor"] == 0

    assert payload["category_proxy_coverage_count"] == 1
    assert payload["category_proxy_drift_count"] == 1


def test_transfer_resolutions_reject_external_kind(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    _seed_transfer_session(pristine_db)

    response = api_client.post(
        "/api/onboarding/aspire/transfers",
        json={"resolutions": {"1": {"kind": "external"}}},
    )

    assert response.status_code == 422


def test_transfer_resolutions_support_link_and_system_resolution(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    _seed_transfer_session(pristine_db)

    get_response = api_client.get("/api/onboarding/aspire/transfers")
    assert get_response.status_code == 200, get_response.text
    payload = get_response.json()
    assert payload["auto_pairs"] == []
    assert sorted(row["row_index"] for row in payload["exceptions"]) == [1, 2, 3]

    save_response = api_client.post(
        "/api/onboarding/aspire/transfers",
        json={
            "resolutions": {
                "1": {"kind": "linked", "linked_row_index": 2},
                "2": {"kind": "linked", "linked_row_index": 1},
                "3": {"kind": "opening_balance"},
            }
        },
    )
    assert save_response.status_code == 200, save_response.text

    preview_response = api_client.get("/api/onboarding/aspire/preview")
    assert preview_response.status_code == 200, preview_response.text
    preview_payload = preview_response.json()
    assert "unresolved_transfer_exceptions" not in preview_payload["blockers"]
    assert preview_payload["can_apply"] is True


def test_transfer_resolutions_support_undo_by_resave(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    _seed_transfer_session(pristine_db)

    save_response = api_client.post(
        "/api/onboarding/aspire/transfers",
        json={
            "resolutions": {
                "1": {"kind": "linked", "linked_row_index": 2},
                "2": {"kind": "linked", "linked_row_index": 1},
                "3": {"kind": "opening_balance"},
            }
        },
    )
    assert save_response.status_code == 200, save_response.text

    undo_response = api_client.post(
        "/api/onboarding/aspire/transfers",
        json={
            "resolutions": {
                "3": {"kind": "opening_balance"},
            }
        },
    )
    assert undo_response.status_code == 200, undo_response.text

    transfers_response = api_client.get("/api/onboarding/aspire/transfers")
    assert transfers_response.status_code == 200, transfers_response.text
    saved = transfers_response.json()["saved_resolutions"]
    assert set(saved.keys()) == {"3"}

    preview_response = api_client.get("/api/onboarding/aspire/preview")
    assert preview_response.status_code == 200, preview_response.text
    blockers = preview_response.json()["blockers"]
    assert "unresolved_transfer_exceptions" in blockers


def test_preview_returns_budget_parity_payload(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    _seed_transfer_session(pristine_db)

    save_response = api_client.post(
        "/api/onboarding/aspire/transfers",
        json={
            "resolutions": {
                "1": {"kind": "linked", "linked_row_index": 2},
                "2": {"kind": "linked", "linked_row_index": 1},
                "3": {"kind": "opening_balance"},
            }
        },
    )
    assert save_response.status_code == 200, save_response.text

    preview_response = api_client.get("/api/onboarding/aspire/preview")
    assert preview_response.status_code == 200, preview_response.text
    payload = preview_response.json()

    budget_parity = payload["budget_parity"]
    assert budget_parity is not None
    assert budget_parity["month_start"] == "2025-01-01"
    assert isinstance(budget_parity["rows"], list)


def test_preview_blocks_duplicate_mapping_collisions(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "A": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Groceries": {
                "dojo_name": "Food",
                "group_name": "Living",
                "is_active": True,
            },
            "Dining": {
                "dojo_name": "Food",
                "group_name": "Living",
                "is_active": True,
            },
        },
    }
    _seed_preview_session(pristine_db, session_id="sess-collision", mapping=mapping)

    preview_response = api_client.get("/api/onboarding/aspire/preview")
    assert preview_response.status_code == 200, preview_response.text
    blockers = preview_response.json()["blockers"]
    assert "duplicate_mapping_collision:category:food" in blockers


def test_preview_blocks_unknown_net_worth_classification(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "A": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Groceries": {
                "dojo_name": "Groceries",
                "group_name": "Living",
                "is_active": True,
            }
        },
    }
    decisions = {
        "Brokerage": {
            "decision": "duplicate_derive_from_ledger",
            "classification": "unknown",
            "ledger_account_id": "Checking",
        }
    }
    _seed_preview_session(
        pristine_db,
        session_id="sess-classification",
        mapping=mapping,
        net_worth_decisions_json=json.dumps(decisions, separators=(",", ":"), sort_keys=True),
    )

    preview_response = api_client.get("/api/onboarding/aspire/preview")
    assert preview_response.status_code == 200, preview_response.text
    blockers = preview_response.json()["blockers"]
    assert "missing_net_worth_classification:Brokerage" in blockers


def test_save_net_worth_decisions_serializes_cutover_dates(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    _seed_preview_session(
        pristine_db,
        session_id="sess-save-net-worth",
        mapping={"accounts": {}, "categories": {}},
    )

    response = api_client.post(
        "/api/onboarding/aspire/net-worth",
        json={
            "decisions": {
                "401k": {
                    "decision": "track_forward",
                    "classification": "asset",
                    "cutover_date": "2025-01-10",
                    "destinations": [
                        {
                            "name": "401k",
                            "institution_name": "Vanguard",
                            "account_class": "investment",
                            "account_type": "asset",
                            "starting_value_minor": 0,
                            "statement_cash_minor": 0,
                            "tax_classification": "401k",
                            "is_self_directed": False,
                            "holdings": [],
                        }
                    ],
                }
            }
        },
    )

    assert response.status_code == 200, response.text
    stored = pristine_db.execute(
        "SELECT net_worth_decisions_json FROM aspire_migration_sessions WHERE migration_session_id = 'sess-save-net-worth'"
    ).fetchone()
    assert stored is not None
    assert json.loads(stored[0]) == {
        "401k": {
            "classification": "asset",
            "cutover_date": "2025-01-10",
            "decision": "track_forward",
            "destinations": [
                {
                    "account_class": "investment",
                    "account_type": "asset",
                    "holdings": [],
                    "institution_name": "Vanguard",
                    "interest_rate_apy": None,
                    "is_self_directed": False,
                    "loan_mode": None,
                    "name": "401k",
                    "note": None,
                    "original_principal_minor": None,
                    "starting_value_minor": 0,
                    "statement_cash_minor": 0,
                    "tax_classification": "401k",
                    "valuation_source": None,
                }
            ],
            "ledger_account_id": None,
        }
    }


def test_apply_blocks_budget_parity_mismatch_without_force(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
    monkeypatch,
) -> None:
    from dojo.aspire_migration import routers
    from dojo.aspire_migration.schemas import BudgetParityResponse

    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Groceries": {
                "dojo_name": "Groceries",
                "group_name": "Living",
                "is_active": True,
            }
        },
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-parity-gate",
        mapping=mapping,
        transactions=[(1, -5000, "Groceries", "Checking", "Groceries run")],
    )

    def _forced_mismatch(_conn, **kwargs):
        return BudgetParityResponse(month_start=kwargs["month_start"], mismatches=1, max_abs_diff_minor=500, rows=[])

    monkeypatch.setattr(routers, "_compute_budget_parity", _forced_mismatch)

    preview_response = api_client.get("/api/onboarding/aspire/preview")
    assert preview_response.status_code == 200, preview_response.text
    assert "budget_parity_mismatch" in preview_response.json()["blockers"]

    apply_response = api_client.post("/api/onboarding/aspire/apply", json={"force": False})
    assert apply_response.status_code == 400, apply_response.text
    assert "Budget parity mismatch detected" in apply_response.json()["detail"]


def test_apply_requires_documented_budget_parity_acknowledgment(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
    monkeypatch,
) -> None:
    from dojo.aspire_migration import routers
    from dojo.aspire_migration.schemas import BudgetParityResponse

    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Groceries": {
                "dojo_name": "Groceries",
                "group_name": "Living",
                "is_active": True,
            }
        },
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-parity-force",
        mapping=mapping,
        transactions=[(1, -7500, "Groceries", "Checking", "Groceries run")],
    )

    def _forced_mismatch(_conn, **kwargs):
        return BudgetParityResponse(month_start=kwargs["month_start"], mismatches=1, max_abs_diff_minor=250, rows=[])

    monkeypatch.setattr(routers, "_compute_budget_parity", _forced_mismatch)

    apply_without_ack = api_client.post("/api/onboarding/aspire/apply", json={"force": True})
    assert apply_without_ack.status_code == 400, apply_without_ack.text
    assert "acknowledge a documented semantic difference" in apply_without_ack.json()["detail"]

    apply_with_unknown_ack = api_client.post(
        "/api/onboarding/aspire/apply",
        json={
            "force": True,
            "ack_budget_parity_mismatch": True,
            "budget_parity_semantic_difference": "unknown_difference",
        },
    )
    assert apply_with_unknown_ack.status_code == 422, apply_with_unknown_ack.text

    apply_with_documented_ack = api_client.post(
        "/api/onboarding/aspire/apply",
        json={
            "force": True,
            "ack_budget_parity_mismatch": True,
            "budget_parity_semantic_difference": "month_rollover_overspending",
        },
    )
    assert apply_with_documented_ack.status_code == 200, apply_with_documented_ack.text
    assert apply_with_documented_ack.json()["import_status"] == "completed"


def test_apply_sets_investment_baseline_from_imported_cash(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "Brokerage": {
                "dojo_name": "Brokerage",
                "account_class": "investment",
                "account_role": "tracking",
                "is_active": True,
            }
        },
        "categories": {
            "Salary": {
                "dojo_name": "Salary",
                "group_name": "Income",
                "is_active": True,
            }
        },
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-investment-baseline",
        mapping=mapping,
        transactions=[(1, 150000, "Salary", "Brokerage", "Initial funding")],
    )

    apply_response = api_client.post("/api/onboarding/aspire/apply", json={"force": False})
    assert apply_response.status_code == 200, apply_response.text

    account_row = pristine_db.execute(
        "SELECT current_balance_minor FROM accounts WHERE account_id = 'aspire_brokerage'"
    ).fetchone()
    assert account_row is not None
    assert int(account_row[0]) == 150000

    detail_row = pristine_db.execute(
        """
        SELECT ledger_baseline_minor, uninvested_cash_minor
        FROM investment_account_details
        WHERE account_id = 'aspire_brokerage' AND is_active = TRUE
        """
    ).fetchone()
    assert detail_row is not None
    assert int(detail_row[0]) == 150000
    assert int(detail_row[1]) == 150000


def test_apply_track_forward_creates_destination_accounts_and_details(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Income": {
                "dojo_name": "Income",
                "group_name": "Income",
                "is_active": True,
            }
        },
    }
    net_worth_decisions = {
        "Retirement": {
            "decision": "track_forward",
            "classification": "asset",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "Retirement IRA",
                    "account_class": "investment",
                    "account_type": "asset",
                    "starting_value_minor": 500000,
                    "statement_cash_minor": 200000,
                    "is_self_directed": False,
                    "tax_classification": "401k",
                    "holdings": [
                        {"ticker": "VTI", "quantity": 3, "avg_cost_minor": 100000},
                    ],
                }
            ],
        },
        "Mortgage": {
            "decision": "track_forward",
            "classification": "debt",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "Home Mortgage",
                    "account_class": "loan",
                    "account_type": "liability",
                    "starting_value_minor": -750000,
                    "interest_rate_apy": 6.1,
                    "original_principal_minor": 900000,
                    "loan_mode": "statement_principal",
                }
            ],
        },
        "House": {
            "decision": "track_forward",
            "classification": "asset",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "Primary Home",
                    "account_class": "tangible",
                    "account_type": "asset",
                    "starting_value_minor": 1200000,
                    "valuation_source": "appraisal",
                }
            ],
        },
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-track-forward",
        mapping=mapping,
        transactions=[(1, 10000, "Income", "Checking", "seed tx")],
        net_worth_decisions=net_worth_decisions,
    )

    apply_response = api_client.post("/api/onboarding/aspire/apply", json={"force": False})
    assert apply_response.status_code == 200, apply_response.text

    account_rows = pristine_db.execute(
        """
        SELECT name, account_class, account_type, account_role
        FROM accounts
        WHERE name IN ('Retirement IRA', 'Home Mortgage', 'Primary Home')
        ORDER BY name
        """
    ).fetchall()
    assert account_rows == [
        ("Home Mortgage", "loan", "liability", "tracking"),
        ("Primary Home", "tangible", "asset", "tracking"),
        ("Retirement IRA", "investment", "asset", "tracking"),
    ]

    investment_detail = pristine_db.execute(
        """
        SELECT iad.ledger_baseline_minor, iad.uninvested_cash_minor, iad.is_self_directed, iad.tax_classification
        FROM investment_account_details iad
        JOIN accounts a ON a.account_id = iad.account_id
        WHERE a.name = 'Retirement IRA' AND iad.is_active = TRUE
        """
    ).fetchone()
    assert investment_detail == (500000, 200000, False, "401k")

    holding_row = pristine_db.execute(
        """
        SELECT s.ticker, p.quantity, p.avg_cost_minor
        FROM positions p
        JOIN securities s ON s.security_id = p.security_id
        JOIN accounts a ON a.account_id = p.account_id
        WHERE a.name = 'Retirement IRA' AND p.is_active = TRUE
        """
    ).fetchone()
    assert holding_row is not None
    assert holding_row[0] == "VTI"
    assert float(holding_row[1]) == 3.0
    assert int(holding_row[2]) == 100000

    loan_detail = pristine_db.execute(
        """
        SELECT initial_principal_minor, interest_rate_apy
        FROM loan_account_details ld
        JOIN accounts a ON a.account_id = ld.account_id
        WHERE a.name = 'Home Mortgage' AND ld.is_active = TRUE
        """
    ).fetchone()
    assert loan_detail == (900000, 6.1)

    tangible_row = pristine_db.execute(
        """
        SELECT current_fair_value_minor
        FROM tangible_assets t
        JOIN accounts a ON a.account_id = t.account_id
        WHERE a.name = 'Primary Home' AND t.is_active = TRUE
        """
    ).fetchone()
    assert tangible_row == (1200000,)


def test_apply_track_forward_supports_cash_credit_and_accessible_destinations(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Income": {
                "dojo_name": "Income",
                "group_name": "Income",
                "is_active": True,
            }
        },
    }
    net_worth_decisions = {
        "Cash Reserve": {
            "decision": "track_forward",
            "classification": "asset",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "Emergency Fund",
                    "account_class": "cash",
                    "account_type": "asset",
                    "starting_value_minor": 125000,
                }
            ],
        },
        "CD Ladder": {
            "decision": "track_forward",
            "classification": "asset",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "12 Month CD",
                    "account_class": "accessible",
                    "account_type": "asset",
                    "starting_value_minor": 90000,
                }
            ],
        },
        "Visa": {
            "decision": "track_forward",
            "classification": "debt",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "Travel Visa",
                    "account_class": "credit",
                    "account_type": "liability",
                    "starting_value_minor": -42000,
                }
            ],
        },
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-track-forward-liquid",
        mapping=mapping,
        transactions=[(1, 10000, "Income", "Checking", "seed tx")],
        net_worth_decisions=net_worth_decisions,
    )

    apply_response = api_client.post("/api/onboarding/aspire/apply", json={"force": False})
    assert apply_response.status_code == 200, apply_response.text

    account_rows = pristine_db.execute(
        """
        SELECT name, account_class, account_type
        FROM accounts
        WHERE name IN ('Emergency Fund', '12 Month CD', 'Travel Visa')
        ORDER BY name
        """
    ).fetchall()
    assert account_rows == [
        ("12 Month CD", "accessible", "asset"),
        ("Emergency Fund", "cash", "asset"),
        ("Travel Visa", "credit", "liability"),
    ]

    opening_rows = pristine_db.execute(
        """
        SELECT a.name, t.amount_minor
        FROM transactions t
        JOIN accounts a ON a.account_id = t.account_id
        WHERE a.name IN ('Emergency Fund', '12 Month CD', 'Travel Visa')
          AND t.category_id = 'opening_balance'
        ORDER BY a.name
        """
    ).fetchall()
    assert opening_rows == [
        ("12 Month CD", 90000),
        ("Emergency Fund", 125000),
        ("Travel Visa", -42000),
    ]

    cash_detail = pristine_db.execute(
        """
        SELECT COUNT(*)
        FROM cash_account_details d
        JOIN accounts a ON a.account_id = d.account_id
        WHERE a.name = 'Emergency Fund' AND d.is_active = TRUE
        """
    ).fetchone()
    assert cash_detail == (1,)

    accessible_detail = pristine_db.execute(
        """
        SELECT COUNT(*)
        FROM accessible_asset_details d
        JOIN accounts a ON a.account_id = d.account_id
        WHERE a.name = '12 Month CD' AND d.is_active = TRUE
        """
    ).fetchone()
    assert accessible_detail == (1,)

    credit_detail = pristine_db.execute(
        """
        SELECT COUNT(*)
        FROM credit_account_details d
        JOIN accounts a ON a.account_id = d.account_id
        WHERE a.name = 'Travel Visa' AND d.is_active = TRUE
        """
    ).fetchone()
    assert credit_detail == (1,)


def test_apply_track_forward_investment_avoids_double_counting(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Income": {
                "dojo_name": "Income",
                "group_name": "Income",
                "is_active": True,
            }
        },
    }
    net_worth_decisions = {
        "Retirement": {
            "decision": "track_forward",
            "classification": "asset",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "Retirement IRA",
                    "account_class": "investment",
                    "account_type": "asset",
                    "starting_value_minor": 125000,
                    "statement_cash_minor": 25000,
                    "holdings": [
                        {"ticker": "VXUS", "quantity": 2, "avg_cost_minor": 50000},
                    ],
                }
            ],
        }
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-track-forward-nw",
        mapping=mapping,
        transactions=[(1, 10000, "Income", "Checking", "seed tx")],
        net_worth_decisions=net_worth_decisions,
    )

    apply_response = api_client.post("/api/onboarding/aspire/apply", json={"force": False})
    assert apply_response.status_code == 200, apply_response.text

    snapshot_response = api_client.get("/api/net-worth/current")
    assert snapshot_response.status_code == 200, snapshot_response.text
    snapshot = snapshot_response.json()
    assert snapshot["positions_minor"] == 125000
    assert snapshot["net_worth_minor"] == 135000


def test_apply_track_forward_legacy_marks_do_not_double_count_current_net_worth(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Income": {
                "dojo_name": "Income",
                "group_name": "Income",
                "is_active": True,
            }
        },
    }
    net_worth_decisions = {
        "Retirement": {
            "decision": "track_forward",
            "classification": "asset",
            "cutover_date": "2025-01-10",
            "destinations": [
                {
                    "name": "Retirement IRA",
                    "account_class": "investment",
                    "account_type": "asset",
                    "starting_value_minor": 125000,
                    "statement_cash_minor": 25000,
                    "holdings": [
                        {"ticker": "VXUS", "quantity": 2, "avg_cost_minor": 50000},
                    ],
                }
            ],
        }
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-track-forward-neutralized",
        mapping=mapping,
        transactions=[(1, 10000, "Income", "Checking", "seed tx")],
        net_worth_decisions=net_worth_decisions,
        net_worth_marks=[
            (1, "2025-01-01", "Retirement", 999999999, "legacy mark", None),
        ],
    )

    apply_response = api_client.post("/api/onboarding/aspire/apply", json={"force": False})
    assert apply_response.status_code == 200, apply_response.text

    snapshot_response = api_client.get("/api/net-worth/current")
    assert snapshot_response.status_code == 200, snapshot_response.text
    snapshot = snapshot_response.json()
    assert snapshot["positions_minor"] == 125000
    assert snapshot["net_worth_minor"] == 135000


def test_apply_preserves_legacy_marks_for_parity_views(
    api_client: TestClient,
    pristine_db: duckdb.DuckDBPyConnection,
) -> None:
    mapping = {
        "accounts": {
            "Checking": {
                "dojo_name": "Checking",
                "account_class": "cash",
                "account_role": "on_budget",
                "is_active": True,
            }
        },
        "categories": {
            "Income": {
                "dojo_name": "Income",
                "group_name": "Income",
                "is_active": True,
            }
        },
    }
    _seed_apply_session(
        pristine_db,
        session_id="sess-legacy-marks",
        mapping=mapping,
        transactions=[(1, 10000, "Income", "Checking", "seed tx")],
        net_worth_marks=[
            (1, "2025-01-01", "House", 400000, "monthly mark", None),
            (2, "2025-02-01", "House", 405000, "monthly mark", "B"),
        ],
    )

    apply_response = api_client.post("/api/onboarding/aspire/apply", json={"force": False})
    assert apply_response.status_code == 200, apply_response.text
    assert apply_response.json()["legacy_marks_imported"] == 2

    marks_rows = pristine_db.execute(
        """
        SELECT mark_date, category_name, amount_minor, note, breakpoint
        FROM aspire_legacy_net_worth_marks
        ORDER BY mark_date
        """
    ).fetchall()
    assert marks_rows == [
        (date(2025, 1, 1), "House", 400000, "monthly mark", None),
        (date(2025, 2, 1), "House", 405000, "monthly mark", "B"),
    ]
