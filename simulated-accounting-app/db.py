import sqlite3
from typing import Any, Dict, List, Optional

COLUMNS = [
    'accounting_id', 'external_reference', 'vendor', 'invoice_number', 'invoice_date',
    'due_date', 'currency', 'subtotal', 'tax', 'total', 'line_items', 'created_at',
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accounting_id TEXT NOT NULL UNIQUE,
    external_reference TEXT UNIQUE,
    vendor TEXT,
    invoice_number TEXT,
    invoice_date TEXT,
    due_date TEXT,
    currency TEXT,
    subtotal REAL,
    tax REAL,
    total REAL,
    line_items TEXT,
    created_at TEXT NOT NULL
)
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(path: str) -> None:
    conn = connect(path)
    try:
        conn.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {column: row[column] for column in COLUMNS}


def list_records(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM records ORDER BY id").fetchall()
    return [_to_dict(row) for row in rows]


def get_record(conn: sqlite3.Connection, accounting_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM records WHERE accounting_id = ?", (accounting_id,)).fetchone()
    return _to_dict(row) if row else None


def get_by_reference(conn: sqlite3.Connection, external_reference: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM records WHERE external_reference = ?", (external_reference,)
    ).fetchone()
    return _to_dict(row) if row else None


def insert_record(conn: sqlite3.Connection, record: Dict[str, Any]) -> None:
    placeholders = ", ".join("?" for _ in COLUMNS)
    conn.execute(
        f"INSERT INTO records ({', '.join(COLUMNS)}) VALUES ({placeholders})",
        [record.get(column) for column in COLUMNS],
    )
    conn.commit()
