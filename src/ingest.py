from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "prontuario_sinteticos"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROCESSED_DIR / "documents.db"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def relative_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


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


def reset_database(db_path: Path) -> sqlite3.Connection:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    return conn


def start_run(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "INSERT INTO ingestion_runs (started_at, status) VALUES (?, ?)",
        (utc_now(), "running"),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("INSERT em ingestion_runs não retornou lastrowid")
    return cursor.lastrowid


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
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
            utc_now(),
            status,
            message,
            sources_count,
            pdf_pages_count,
            csv_rows_count,
            run_id,
        ),
    )


def discover_pdfs() -> list[Path]:
    pdf_dirs = [RAW_DIR / "bulas", RAW_DIR / "protocolos"]
    pdfs: list[Path] = []
    for pdf_dir in pdf_dirs:
        if pdf_dir.exists():
            pdfs.extend(sorted(pdf_dir.glob("*.pdf")))
    return sorted(pdfs, key=lambda path: relative_path(path))


def discover_csvs() -> list[Path]:
    csv_dir = RAW_DIR / "prontuarios"
    if not csv_dir.exists():
        return []
    return sorted(csv_dir.glob("*.csv"), key=lambda path: relative_path(path))


def pdf_category(path: Path) -> str:
    if path.parent.name == "bulas":
        return "bula"
    if path.parent.name == "protocolos":
        return "protocolo"
    return path.parent.name


def register_source(
    conn: sqlite3.Connection,
    path: Path,
    source_type: str,
    category: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO sources (
            path, name, source_type, category, content_sha256, size_bytes, ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            relative_path(path),
            path.name,
            source_type,
            category,
            file_sha256(path),
            path.stat().st_size,
            utc_now(),
        ),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("INSERT em sources não retornou lastrowid")
    return cursor.lastrowid


def ingest_pdf(conn: sqlite3.Connection, path: Path) -> int:
    source_id = register_source(conn, path, "pdf", pdf_category(path))
    pages_count = 0

    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = normalize_text(page.extract_text())
            conn.execute(
                """
                INSERT INTO pdf_pages (source_id, page_number, text, text_sha256)
                VALUES (?, ?, ?, ?)
                """,
                (source_id, page_number, text, text_sha256(text)),
            )
            pages_count += 1

    return pages_count


def first_present(row: dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        value = row.get(key, "").strip()
        if value:
            return value
    return ""


def value_or_missing(value: str | None) -> str:
    value = (value or "").strip()
    return value if value else "nao informado"


def patient_id_for_row(table_name: str, row: dict[str, str]) -> str:
    if table_name == "patients":
        return first_present(row, ["Id", "ID", "PATIENT", "patient_id"])
    return first_present(row, ["PATIENT", "patient", "patient_id", "Id", "ID"])


def patient_row_to_text(row: dict[str, str]) -> str:
    patient_id = patient_id_for_row("patients", row)
    name = " ".join(
        part
        for part in [row.get("PREFIX", ""), row.get("FIRST", ""), row.get("LAST", "")]
        if part.strip()
    )
    return (
        f"Paciente {patient_id}. Nome: {value_or_missing(name)}. "
        f"Nascimento: {value_or_missing(row.get('BIRTHDATE'))}. "
        f"Obito: {value_or_missing(row.get('DEATHDATE'))}. "
        f"Estado civil: {value_or_missing(row.get('MARITAL'))}. "
        f"Raca: {value_or_missing(row.get('RACE'))}. "
        f"Etnia: {value_or_missing(row.get('ETHNICITY'))}. "
        f"Genero: {value_or_missing(row.get('GENDER'))}. "
        f"Local de nascimento: {value_or_missing(row.get('BIRTHPLACE'))}. "
        f"Cidade: {value_or_missing(row.get('CITY'))}. "
        f"Estado: {value_or_missing(row.get('STATE'))}. "
        f"Condado: {value_or_missing(row.get('COUNTY'))}."
    )


def allergy_row_to_text(row: dict[str, str]) -> str:
    patient_id = patient_id_for_row("allergies", row)
    return (
        f"Paciente {patient_id} possui alergia: "
        f"{value_or_missing(row.get('DESCRIPTION'))}. "
        f"Codigo: {value_or_missing(row.get('CODE'))}. "
        f"Inicio: {value_or_missing(row.get('START'))}. "
        f"Fim: {value_or_missing(row.get('STOP'))}. "
        f"Encontro: {value_or_missing(row.get('ENCOUNTER'))}."
    )


def medication_row_to_text(row: dict[str, str]) -> str:
    patient_id = patient_id_for_row("medications", row)
    return (
        f"Paciente {patient_id} recebeu medicamento: "
        f"{value_or_missing(row.get('DESCRIPTION'))}. "
        f"Codigo: {value_or_missing(row.get('CODE'))}. "
        f"Inicio: {value_or_missing(row.get('START'))}. "
        f"Fim: {value_or_missing(row.get('STOP'))}. "
        f"Motivo: {value_or_missing(row.get('REASONDESCRIPTION'))}. "
        f"Codigo do motivo: {value_or_missing(row.get('REASONCODE'))}. "
        f"Dispensas: {value_or_missing(row.get('DISPENSES'))}. "
        f"Custo total: {value_or_missing(row.get('TOTALCOST'))}."
    )


def generic_csv_row_to_text(table_name: str, row: dict[str, str]) -> str:
    fields = [
        f"{key}: {value.strip()}"
        for key, value in row.items()
        if value is not None and value.strip()
    ]
    return f"Registro da tabela {table_name}. " + "; ".join(fields) + "."


def csv_row_to_text(table_name: str, row: dict[str, str]) -> str:
    if table_name == "patients":
        return patient_row_to_text(row)
    if table_name == "allergies":
        return allergy_row_to_text(row)
    if table_name == "medications":
        return medication_row_to_text(row)
    return generic_csv_row_to_text(table_name, row)


def ingest_csv(conn: sqlite3.Connection, path: Path) -> int:
    table_name = path.stem
    source_id = register_source(conn, path, "csv", table_name)
    rows_count = 0

    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row_number, row in enumerate(reader, start=2):
            normalized_row = {key: value or "" for key, value in row.items() if key}
            patient_id = patient_id_for_row(table_name, normalized_row) or None
            content_json = json.dumps(
                normalized_row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            content_text = csv_row_to_text(table_name, normalized_row)
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
                    text_sha256(content_json),
                ),
            )
            rows_count += 1

    return rows_count


def count_sources(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])


def ingest_all(conn: sqlite3.Connection) -> tuple[int, int, int]:
    pdf_pages_count = 0
    csv_rows_count = 0

    for pdf_path in discover_pdfs():
        pdf_pages_count += ingest_pdf(conn, pdf_path)

    for csv_path in discover_csvs():
        csv_rows_count += ingest_csv(conn, csv_path)

    return count_sources(conn), pdf_pages_count, csv_rows_count


def print_summary(
    sources_count: int,
    pdf_pages_count: int,
    csv_rows_count: int,
) -> None:
    print("Ingestao concluida.")
    print(f"Fontes ingeridas: {sources_count}")
    print(f"Paginas de PDF extraidas: {pdf_pages_count}")
    print(f"Linhas CSV ingeridas: {csv_rows_count}")
    print(f"Banco salvo em: {relative_path(DB_PATH)}")


def main() -> int:
    conn = reset_database(DB_PATH)
    run_id = start_run(conn)

    try:
        sources_count, pdf_pages_count, csv_rows_count = ingest_all(conn)
        finish_run(
            conn,
            run_id,
            "success",
            "Ingestao concluida com sucesso.",
            sources_count,
            pdf_pages_count,
            csv_rows_count,
        )
        conn.commit()
        print_summary(sources_count, pdf_pages_count, csv_rows_count)
        return 0
    except Exception as exc:
        finish_run(conn, run_id, "failed", str(exc))
        conn.commit()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
