
from dojo.core import migrate


class RecordingConn:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, statement: str, params=None) -> None:  # noqa: ANN001
        self.calls.append(statement)
        return None


def test_execute_statements_splits_dml_and_index_transactions() -> None:
    conn = RecordingConn()
    statements = [
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET x = 1",
        "CREATE INDEX idx_t ON t(x)",
        "DELETE FROM t WHERE 1=0",
    ]

    migrate._execute_statements(conn, "001_test.sql", statements, dry_run=False)  # type: ignore[attr-defined]

    assert conn.calls == [
        "BEGIN",
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET x = 1",
        "COMMIT",
        "BEGIN",
        "CREATE INDEX idx_t ON t(x)",
        "COMMIT",
        "BEGIN",
        "DELETE FROM t WHERE 1=0",
        "COMMIT",
    ]


def test_execute_statements_dry_run_no_ops() -> None:
    conn = RecordingConn()
    migrate._execute_statements(conn, "001_test.sql", ["CREATE TABLE t(x INT)"], dry_run=True)  # type: ignore[attr-defined]
    assert conn.calls == []
