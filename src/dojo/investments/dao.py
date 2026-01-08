"""DuckDB data access helpers for the investments domain."""

from __future__ import annotations

from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import duckdb

from dojo.investments.sql import load_sql


def _row_to_namespace(description: Sequence[tuple[object, ...]], row: tuple[object, ...]) -> SimpleNamespace:
    columns = [str(desc[0]) for desc in description]
    payload: dict[str, object] = {name: value for name, value in zip(columns, row, strict=True)}
    return SimpleNamespace(**payload)


@dataclass(frozen=True)
class InvestmentAccountRow:
    account_id: str
    current_balance_minor: int


@dataclass(frozen=True)
class InvestmentAccountDetailRow:
    detail_id: UUID
    risk_free_sweep_rate: float
    manager: str | None
    is_self_directed: bool | None
    tax_classification: str | None
    uninvested_cash_minor: int


@dataclass(frozen=True)
class ActivePositionRow:
    position_id: UUID
    concept_id: UUID
    account_id: str
    security_id: UUID
    quantity: float
    avg_cost_minor: int
    ticker: str


@dataclass(frozen=True)
class ActivePositionWithPriceRow(ActivePositionRow):
    name: str | None
    close_minor: int | None


@dataclass(frozen=True)
class SecurityRow:
    security_id: UUID
    ticker: str
    name: str | None
    type: str
    currency: str


@dataclass(frozen=True)
class ActiveSecurityRow:
    security_id: UUID
    ticker: str
    last_market_date: date | None


class InvestmentDAO:
    """Encapsulates DuckDB reads/writes for investment tracking."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _fetchone_namespace(
        self,
        sql: str,
        params: Sequence[object] | Mapping[str, object] | None = None,
    ) -> SimpleNamespace | None:
        cursor = self._conn.execute(sql, params or {})
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_namespace(cursor.description, row)

    def _fetchall_namespaces(
        self,
        sql: str,
        params: Sequence[object] | Mapping[str, object] | None = None,
    ) -> list[SimpleNamespace]:
        cursor = self._conn.execute(sql, params or {})
        rows = cursor.fetchall()
        if not rows:
            return []
        return [_row_to_namespace(cursor.description, row) for row in rows]

    # Transaction control -------------------------------------------------
    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        self._conn.execute("COMMIT")

    def rollback(self) -> None:
        self._conn.execute("ROLLBACK")

    @contextmanager
    def transaction(self) -> Generator[InvestmentDAO, None, None]:
        self.begin()
        try:
            yield self
        except Exception:
            self.rollback()
            raise
        else:
            self.commit()

    # Account validation --------------------------------------------------
    def require_active_investment_account(self, account_id: str) -> InvestmentAccountRow:
        row = self._fetchone_namespace(
            load_sql("select_active_investment_account.sql"),
            {"account_id": account_id},
        )
        if row is None:
            raise ValueError(f"Unknown or inactive investment account: {account_id}")
        return InvestmentAccountRow(
            account_id=str(row.account_id),
            current_balance_minor=int(row.current_balance_minor),
        )

    # Reads ---------------------------------------------------------------
    def get_active_uninvested_cash_minor(self, account_id: str) -> int:
        row = self._fetchone_namespace(
            load_sql("select_active_uninvested_cash.sql"),
            {"account_id": account_id},
        )
        if row is None or row.uninvested_cash_minor is None:
            return 0
        return int(row.uninvested_cash_minor)

    def get_active_positions_with_prices(self, account_id: str) -> list[ActivePositionWithPriceRow]:
        rows = self._fetchall_namespaces(
            load_sql("select_active_positions_with_prices.sql"),
            {"account_id": account_id},
        )
        out: list[ActivePositionWithPriceRow] = []
        for row in rows:
            out.append(
                ActivePositionWithPriceRow(
                    position_id=UUID(str(row.position_id)),
                    concept_id=UUID(str(row.concept_id)),
                    account_id=str(row.account_id),
                    security_id=UUID(str(row.security_id)),
                    quantity=float(row.quantity),
                    avg_cost_minor=int(row.avg_cost_minor),
                    ticker=str(row.ticker),
                    name=str(row.name) if row.name is not None else None,
                    close_minor=int(row.close_minor) if row.close_minor is not None else None,
                )
            )
        return out

    def get_active_positions_for_reconcile(self, account_id: str) -> list[ActivePositionRow]:
        rows = self._fetchall_namespaces(
            load_sql("select_active_positions_for_reconcile.sql"),
            {"account_id": account_id},
        )
        out: list[ActivePositionRow] = []
        for row in rows:
            out.append(
                ActivePositionRow(
                    position_id=UUID(str(row.position_id)),
                    concept_id=UUID(str(row.concept_id)),
                    account_id=str(row.account_id),
                    security_id=UUID(str(row.security_id)),
                    quantity=float(row.quantity),
                    avg_cost_minor=int(row.avg_cost_minor),
                    ticker=str(row.ticker),
                )
            )
        return out

    def get_security_by_ticker(self, ticker: str) -> SecurityRow | None:
        row = self._fetchone_namespace(
            load_sql("select_security_by_ticker.sql"),
            {"ticker": ticker},
        )
        if row is None:
            return None
        return SecurityRow(
            security_id=UUID(str(row.security_id)),
            ticker=str(row.ticker),
            name=str(row.name) if row.name is not None else None,
            type=str(row.type),
            currency=str(row.currency),
        )

    def ensure_security(
        self,
        *,
        ticker: str,
        recorded_at: datetime,
        name: str | None = None,
        security_type: str = "STOCK",
        currency: str = "USD",
    ) -> SecurityRow:
        normalized = ticker.strip().upper()
        existing = self.get_security_by_ticker(normalized)
        if existing is not None:
            return existing

        security_id = uuid4()
        self._conn.execute(
            load_sql("insert_security.sql"),
            {
                "security_id": str(security_id),
                "ticker": normalized,
                "name": name,
                "type": security_type,
                "currency": currency,
                "recorded_at": recorded_at,
            },
        )
        created = self.get_security_by_ticker(normalized)
        if created is None:  # pragma: no cover - defensive
            raise RuntimeError(f"Failed to create security for ticker={normalized}")
        return created

    # SCD2: investment_account_details ------------------------------------
    def get_active_investment_account_detail(self, account_id: str) -> InvestmentAccountDetailRow | None:
        row = self._fetchone_namespace(
            load_sql("select_active_investment_account_detail.sql"),
            {"account_id": account_id},
        )
        if row is None:
            return None
        return InvestmentAccountDetailRow(
            detail_id=UUID(str(row.detail_id)),
            risk_free_sweep_rate=float(row.risk_free_sweep_rate or 0.0),
            manager=str(row.manager) if row.manager is not None else None,
            is_self_directed=bool(row.is_self_directed) if row.is_self_directed is not None else None,
            tax_classification=str(row.tax_classification) if row.tax_classification is not None else None,
            uninvested_cash_minor=int(row.uninvested_cash_minor or 0),
        )

    def scd2_set_uninvested_cash_minor(
        self, account_id: str, uninvested_cash_minor: int, *, recorded_at: datetime
    ) -> None:
        current = self.get_active_investment_account_detail(account_id)
        if current is not None and current.uninvested_cash_minor == uninvested_cash_minor:
            return

        if current is not None:
            self._conn.execute(
                load_sql("close_investment_account_detail.sql"),
                {
                    "detail_id": str(current.detail_id),
                    "valid_to": recorded_at,
                    "updated_at": recorded_at,
                },
            )
            risk_free_sweep_rate = current.risk_free_sweep_rate
            manager = current.manager
            is_self_directed = current.is_self_directed
            tax_classification = current.tax_classification
        else:
            risk_free_sweep_rate = 0.0
            manager = None
            is_self_directed = None
            tax_classification = None

        self._conn.execute(
            load_sql("insert_investment_account_detail_version.sql"),
            {
                "detail_id": str(uuid4()),
                "account_id": account_id,
                "risk_free_sweep_rate": risk_free_sweep_rate,
                "manager": manager,
                "is_self_directed": is_self_directed,
                "tax_classification": tax_classification,
                "uninvested_cash_minor": uninvested_cash_minor,
                "valid_from": recorded_at,
                "valid_to": "9999-12-31 00:00:00",
                "created_at": recorded_at,
                "updated_at": recorded_at,
            },
        )

    # SCD2: positions ------------------------------------------------------
    def close_position(self, position_id: UUID, *, recorded_at: datetime) -> None:
        self._conn.execute(
            load_sql("close_position.sql"),
            {
                "position_id": str(position_id),
                "valid_to": recorded_at,
                "recorded_at": recorded_at,
            },
        )

    def insert_position(
        self,
        *,
        position_id: UUID,
        concept_id: UUID,
        account_id: str,
        security_id: UUID,
        quantity: float,
        avg_cost_minor: int,
        recorded_at: datetime,
    ) -> None:
        self._conn.execute(
            load_sql("insert_position.sql"),
            {
                "position_id": str(position_id),
                "concept_id": str(concept_id),
                "account_id": account_id,
                "security_id": str(security_id),
                "quantity": quantity,
                "avg_cost_minor": avg_cost_minor,
                "valid_from": recorded_at,
                "valid_to": "9999-12-31 00:00:00",
                "recorded_at": recorded_at,
            },
        )

    # Market data sync -----------------------------------------------------
    def list_active_securities_with_last_market_date(self) -> list[ActiveSecurityRow]:
        rows = self._fetchall_namespaces(load_sql("select_active_securities_with_last_market_date.sql"))
        out: list[ActiveSecurityRow] = []
        for row in rows:
            out.append(
                ActiveSecurityRow(
                    security_id=UUID(str(row.security_id)),
                    ticker=str(row.ticker),
                    last_market_date=row.last_market_date,
                )
            )
        return out

    def upsert_market_prices(self, rows: list[Mapping[str, object]]) -> None:
        if not rows:
            return
        self._conn.executemany(load_sql("upsert_market_price.sql"), rows)
