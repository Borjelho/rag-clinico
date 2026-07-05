from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "documents.db"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE ingestion_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            message TEXT,
            sources_count INTEGER NOT NULL DEFAULT 0,
            pdf_pages_count INTEGER NOT NULL DEFAULT 0,
            csv_rows_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            category TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            ingested_at TEXT NOT NULL
        );

        CREATE TABLE pdf_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            text_sha256 TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
            UNIQUE (source_id, page_number)
        );

        CREATE TABLE csv_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            table_name TEXT NOT NULL,
            row_number INTEGER NOT NULL,
            patient_id TEXT,
            content_json TEXT NOT NULL,
            content_text TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
            UNIQUE (source_id, row_number)
        );

        CREATE INDEX idx_pdf_pages_source_page ON pdf_pages(source_id, page_number);
        CREATE INDEX idx_csv_rows_table ON csv_rows(table_name);
        CREATE INDEX idx_csv_rows_patient ON csv_rows(patient_id);
        """
    )


def reset_database(db_path: Path = DB_PATH) -> sqlite3.Connection:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    return conn


def start_run(conn: sqlite3.Connection, started_at: str) -> int:
    cursor = conn.execute(
        "INSERT INTO ingestion_runs (started_at, status) VALUES (?, ?)",
        (started_at, "running"),
    )
    return int(cursor.lastrowid)


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    finished_at: str,
    status: str,
    message: str,
    sources_count: int = 0,
    pdf_pages_count: int = 0,
    csv_rows_count: int = 0,
) -> None:
    conn.execute(
        """
        UPDATE ingestion_runs
        SET finished_at = ?, status = ?, message = ?, sources_count = ?,
            pdf_pages_count = ?, csv_rows_count = ?
        WHERE id = ?
        """,
        (
            finished_at,
            status,
            message,
            sources_count,
            pdf_pages_count,
            csv_rows_count,
            run_id,
        ),
    )


def insert_source(
    conn: sqlite3.Connection,
    path: str,
    name: str,
    source_type: str,
    category: str,
    content_sha256: str,
    size_bytes: int,
    ingested_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO sources (
            path, name, source_type, category, content_sha256, size_bytes, ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            path,
            name,
            source_type,
            category,
            content_sha256,
            size_bytes,
            ingested_at,
        ),
    )
    return int(cursor.lastrowid)


def insert_pdf_page(
    conn: sqlite3.Connection,
    source_id: int,
    page_number: int,
    text: str,
    text_sha256: str,
) -> None:
    conn.execute(
        """
        INSERT INTO pdf_pages (source_id, page_number, text, text_sha256)
        VALUES (?, ?, ?, ?)
        """,
        (source_id, page_number, text, text_sha256),
    )


def insert_csv_row(
    conn: sqlite3.Connection,
    source_id: int,
    table_name: str,
    row_number: int,
    patient_id: str | None,
    content_json: str,
    content_text: str,
    content_sha256: str,
) -> None:
    conn.execute(
        """
        INSERT INTO csv_rows (
            source_id, table_name, row_number, patient_id, content_json,
            content_text, content_sha256
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id,
            table_name,
            row_number,
            patient_id,
            content_json,
            content_text,
            content_sha256,
        ),
    )


def count_sources(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])
