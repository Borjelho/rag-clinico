from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


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
            patient_name TEXT,
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
    create_chunks_schema(conn)


def connect_database(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def create_chunks_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            page_start INTEGER,
            page_end INTEGER,
            table_name TEXT,
            patient_id TEXT,
            patient_name TEXT,
            row_start INTEGER,
            row_end INTEGER,
            row_numbers_json TEXT,
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
            UNIQUE (source_id, chunk_index)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_patient ON chunks(patient_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_table ON chunks(table_name);
        CREATE INDEX IF NOT EXISTS idx_chunks_patient_name ON chunks(patient_name);
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
    patient_name: str | None,
    content_json: str,
    content_text: str,
    content_sha256: str,
) -> None:
    conn.execute(
        """
        INSERT INTO csv_rows (
            source_id, table_name, row_number, patient_id, patient_name, content_json,
            content_text, content_sha256
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id,
            table_name,
            row_number,
            patient_id,
            patient_name,
            content_json,
            content_text,
            content_sha256,
        ),
    )


def count_sources(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])


def clear_chunks(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM chunks")


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def metadata_text(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    return str(value)


def metadata_int(metadata: dict[str, Any], key: str) -> int | None:
    value = metadata.get(key)
    if value is None:
        return None
    return int(value)


def insert_chunk(
    conn: sqlite3.Connection,
    source_id: int,
    chunk_index: int,
    content: str,
    metadata: dict[str, Any],
) -> None:
    row_numbers = metadata.get("row_numbers")
    conn.execute(
        """
        INSERT INTO chunks (
            source_id, chunk_index, content, content_sha256, metadata_json,
            page_start, page_end, table_name, patient_id, patient_name,
            row_start, row_end, row_numbers_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id,
            chunk_index,
            content,
            text_sha256(content),
            compact_json(metadata),
            metadata_int(metadata, "page_start"),
            metadata_int(metadata, "page_end"),
            metadata_text(metadata, "table_name"),
            metadata_text(metadata, "patient_id"),
            metadata_text(metadata, "patient_name"),
            metadata_int(metadata, "row_start"),
            metadata_int(metadata, "row_end"),
            compact_json(row_numbers) if row_numbers is not None else None,
        ),
    )


def count_chunks(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
