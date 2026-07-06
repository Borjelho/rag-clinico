from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from storage import (
    DB_PATH,
    clear_chunks,
    connect_database,
    count_chunks,
    create_chunks_schema,
    insert_chunk,
)


PDF_CHUNK_SIZE = 1000
PDF_CHUNK_OVERLAP = 150
CSV_MAX_CHARS = 1800
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def next_chunk_index(counters: dict[int, int], source_id: int) -> int:
    chunk_index = counters[source_id]
    counters[source_id] += 1
    return chunk_index


def build_metadata(**values: object) -> dict[str, object]:
    return {key: value for key, value in values.items() if value is not None}


def load_patient_names(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT patient_id, patient_name
        FROM csv_rows
        WHERE table_name = 'patients'
        ORDER BY row_number
        """
    ).fetchall()
    patient_names: dict[str, str] = {}

    for row in rows:
        patient_id = row["patient_id"]
        if not patient_id:
            continue
        patient_name = row["patient_name"]
        if patient_name:
            patient_names[patient_id] = patient_name

    return patient_names


def patient_header(patient_id: str | None, patient_name: str | None) -> str:
    return (
        f"Paciente: {patient_name or 'nao informado'}\n"
        f"ID do paciente: {patient_id or 'nao informado'}"
    )


def pdf_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=PDF_CHUNK_SIZE,
        chunk_overlap=PDF_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_pdfs(conn: sqlite3.Connection, counters: dict[int, int]) -> int:
    rows = conn.execute(
        """
        SELECT
            s.id AS source_id,
            s.source_type,
            s.category,
            s.name AS document_name,
            p.page_number,
            p.text
        FROM pdf_pages p
        JOIN sources s ON s.id = p.source_id
        WHERE s.source_type = 'pdf'
        ORDER BY s.path, p.page_number
        """
    ).fetchall()

    splitter = pdf_splitter()
    chunks_count = 0

    for row in rows:
        page_text = row["text"].strip()
        if not page_text:
            continue

        for part in splitter.split_text(page_text):
            content = (
                f"Documento: {row['document_name']}\n"
                f"Pagina: {row['page_number']}\n\n"
                f"{part.strip()}"
            )
            metadata = build_metadata(
                source_id=row["source_id"],
                source_type=row["source_type"],
                category=row["category"],
                document_name=row["document_name"],
                page_start=row["page_number"],
                page_end=row["page_number"],
            )
            insert_chunk(
                conn,
                source_id=row["source_id"],
                chunk_index=next_chunk_index(counters, row["source_id"]),
                content=content,
                metadata=metadata,
            )
            chunks_count += 1

    return chunks_count


def csv_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT table_name FROM csv_rows ORDER BY table_name"
    ).fetchall()
    return [row["table_name"] for row in rows]


def grouped_csv_rows(conn: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            s.id AS source_id,
            s.source_type,
            s.category,
            s.name AS document_name,
            c.table_name,
            c.row_number,
            c.patient_id,
            c.patient_name,
            c.content_text
        FROM csv_rows c
        JOIN sources s ON s.id = c.source_id
        WHERE c.table_name = ?
        ORDER BY s.id, c.patient_id IS NULL, c.patient_id, c.row_number
        """,
        (table_name,),
    ).fetchall()


def chunk_grouped_csv(
    conn: sqlite3.Connection,
    counters: dict[int, int],
    patient_names: dict[str, str],
    table_name: str,
    max_chars: int = CSV_MAX_CHARS,
) -> int:
    rows = grouped_csv_rows(conn, table_name)
    chunks_count = 0
    current_key: tuple[int, str] | None = None
    current_rows: list[sqlite3.Row] = []
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal chunks_count, current_rows, current_lines

        if not current_rows:
            return

        first = current_rows[0]
        row_numbers = [row["row_number"] for row in current_rows]
        row_start = min(row_numbers)
        row_end = max(row_numbers)
        patient_id = first["patient_id"]
        patient_name = first["patient_name"] or patient_names.get(patient_id)
        body = "\n".join(current_lines)
        content = (
            f"Fonte: {first['document_name']}\n"
            f"Tabela: {first['table_name']}\n"
            f"{patient_header(patient_id, patient_name)}\n"
            f"Linhas: {row_start}-{row_end}\n\n"
            f"{body}"
        )
        metadata = build_metadata(
            source_id=first["source_id"],
            source_type=first["source_type"],
            category=first["category"],
            document_name=first["document_name"],
            table_name=first["table_name"],
            patient_id=patient_id,
            patient_name=patient_name,
            row_start=row_start,
            row_end=row_end,
            row_numbers=row_numbers,
        )
        insert_chunk(
            conn,
            source_id=first["source_id"],
            chunk_index=next_chunk_index(counters, first["source_id"]),
            content=content,
            metadata=metadata,
        )
        chunks_count += 1
        current_rows = []
        current_lines = []

    for row in rows:
        group_key = (
            row["source_id"],
            row["patient_id"] or f"row:{row['row_number']}",
        )
        line = row["content_text"].strip()
        if not line:
            continue

        if current_key is not None and group_key != current_key:
            flush()

        current_key = group_key
        next_size = len("\n".join(current_lines)) + len(line) + 1
        if current_lines and next_size > max_chars:
            flush()
            current_key = group_key

        current_rows.append(row)
        current_lines.append(line)

    flush()
    return chunks_count


def chunk_csvs(
    conn: sqlite3.Connection,
    counters: dict[int, int],
    patient_names: dict[str, str],
) -> int:
    chunks_count = 0
    for table_name in csv_tables(conn):
        chunks_count += chunk_grouped_csv(conn, counters, patient_names, table_name)
    return chunks_count


def chunk_all(conn: sqlite3.Connection) -> tuple[int, int, int]:
    create_chunks_schema(conn)
    clear_chunks(conn)

    counters: dict[int, int] = defaultdict(int)
    patient_names = load_patient_names(conn)
    pdf_chunks_count = chunk_pdfs(conn, counters)
    csv_chunks_count = chunk_csvs(conn, counters, patient_names)
    return count_chunks(conn), pdf_chunks_count, csv_chunks_count


def print_summary(
    chunks_count: int,
    pdf_chunks_count: int,
    csv_chunks_count: int,
) -> None:
    print("Chunking concluido.")
    print(f"Chunks gerados: {chunks_count}")
    print(f"Chunks de PDF: {pdf_chunks_count}")
    print(f"Chunks de CSV: {csv_chunks_count}")
    print(f"Banco atualizado em: {DB_PATH.relative_to(PROJECT_ROOT).as_posix()}")


def main() -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Banco nao encontrado em {DB_PATH}. Rode uv run src/ingest.py antes."
        )

    conn = connect_database()
    try:
        chunks_count, pdf_chunks_count, csv_chunks_count = chunk_all(conn)
        conn.commit()
        print_summary(chunks_count, pdf_chunks_count, csv_chunks_count)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
