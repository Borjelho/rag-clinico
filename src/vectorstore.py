from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from storage import DB_PATH, PROJECT_ROOT, connect_database


VECTORSTORE_DIR = PROJECT_ROOT / "vectorstore"
COLLECTION_NAME = "clinical_documents"
DEFAULT_ADD_BATCH_SIZE = 1000


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def chroma_metadata_value(value: Any) -> str | int | float | bool:
    if isinstance(value, str | int | float | bool):
        return value
    return compact_json(value)


def chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {
        key: chroma_metadata_value(value)
        for key, value in metadata.items()
        if value is not None
    }


def chunk_uid(row: sqlite3.Row) -> str:
    return f"source-{row['source_id']}-chunk-{row['chunk_index']}"


def chunk_document(row: sqlite3.Row) -> Document:
    source_metadata = json.loads(row["metadata_json"])
    metadata = {
        **source_metadata,
        "chunk_id": row["id"],
        "chunk_uid": chunk_uid(row),
        "chunk_index": row["chunk_index"],
        "content_sha256": row["content_sha256"],
    }
    return Document(
        page_content=row["content"],
        metadata=chroma_metadata(metadata),
    )


def load_chunk_documents(db_path: Path = DB_PATH) -> list[Document]:
    """Carrega os chunks do SQLite como documentos do LangChain."""
    if not db_path.exists():
        raise FileNotFoundError(
            f"Banco SQLite não encontrado em {db_path}. "
            "Rode ingestão e chunking primeiro."
        )

    conn = connect_database(db_path)
    try:
        try:
            rows = conn.execute(
                """
                SELECT
                    id,
                    source_id,
                    chunk_index,
                    content,
                    content_sha256,
                    metadata_json
                FROM chunks
                ORDER BY source_id, chunk_index
                """
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise RuntimeError(
                "Tabela de chunks não encontrada no SQLite. "
                "Rode a etapa de chunking primeiro."
            ) from exc
    finally:
        conn.close()

    if not rows:
        raise RuntimeError(
            "Nenhum chunk encontrado no SQLite. "
            "Rode a etapa de chunking antes de criar o Chroma."
        )

    return [chunk_document(row) for row in rows]


def open_vectorstore(
    embeddings: Embeddings,
    persist_directory: Path = VECTORSTORE_DIR,
    collection_name: str = COLLECTION_NAME,
) -> Chroma:
    """Abre a coleção Chroma persistida usando os embeddings informados."""
    persist_directory.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
    )


def rebuild_vectorstore(
    embeddings: Embeddings,
    db_path: Path = DB_PATH,
    persist_directory: Path = VECTORSTORE_DIR,
    collection_name: str = COLLECTION_NAME,
    batch_size: int = DEFAULT_ADD_BATCH_SIZE,
) -> Chroma:
    """Recria a coleção Chroma a partir dos chunks atuais do SQLite."""
    if batch_size <= 0:
        raise ValueError("batch_size deve ser maior que zero.")

    documents = load_chunk_documents(db_path)
    vectorstore = open_vectorstore(embeddings, persist_directory, collection_name)

    try:
        vectorstore.delete_collection()
    except ValueError:
        pass

    vectorstore = open_vectorstore(embeddings, persist_directory, collection_name)
    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        vectorstore.add_documents(
            documents=batch,
            ids=[str(document.metadata["chunk_uid"]) for document in batch],
        )
    return vectorstore
