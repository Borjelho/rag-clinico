from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from storage import DB_PATH, connect_database

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTORSTORE_DIR = PROJECT_ROOT / "vectorstore"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "acervo_clinico")
BATCH_SIZE = 64
METADATA_TYPES = (str, int, float, bool)


class SentenceTransformerEmbeddings(Embeddings):
    """Adaptação do modelo do sentence-transformers para a interface de embeddings do LangChain."""

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.uses_e5_prefixes = "e5" in model_name.lower()

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            batch_size=BATCH_SIZE,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.uses_e5_prefixes:
            texts = [f"passage: {text}" for text in texts]
        return self.encode(texts)

    def embed_query(self, text: str) -> list[float]:
        if self.uses_e5_prefixes:
            text = f"query: {text}"
        return self.encode([text])[0]


def get_embeddings(model_name: str = EMBEDDING_MODEL) -> SentenceTransformerEmbeddings:
    return SentenceTransformerEmbeddings(model_name)


def get_vectorstore(embeddings: Embeddings | None = None) -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings or get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )


def load_chunks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, source_id, chunk_index, content, metadata_json
        FROM chunks
        ORDER BY source_id, chunk_index
        """
    ).fetchall()


def chunk_id(row: sqlite3.Row) -> str:
    return f"{row['source_id']}-{row['chunk_index']}"


def chunk_metadata(row: sqlite3.Row) -> dict[str, str | int | float | bool]:
    metadata = json.loads(row["metadata_json"])
    clean = {
        key: value
        for key, value in metadata.items()
        if isinstance(value, METADATA_TYPES)
    }
    clean["chunk_db_id"] = row["id"]
    return clean


def index_chunks(vectorstore: Chroma, rows: list[sqlite3.Row]) -> int:
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        vectorstore.add_texts(
            texts=[row["content"] for row in batch],
            metadatas=[chunk_metadata(row) for row in batch],
            ids=[chunk_id(row) for row in batch],
        )
        print(f"Indexados {min(start + BATCH_SIZE, len(rows))}/{len(rows)} chunks...")
    return len(rows)


def print_summary(indexed_count: int, model_name: str) -> None:
    print("Embeddings concluidos.")
    print(f"Chunks indexados: {indexed_count}")
    print(f"Modelo: {model_name}")
    print(f"Colecao: {COLLECTION_NAME}")
    print(f"Vectorstore em: {VECTORSTORE_DIR.relative_to(PROJECT_ROOT).as_posix()}/")


def main() -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Banco nao encontrado em {DB_PATH}. Rode uv run src/ingest.py antes."
        )

    conn = connect_database()
    try:
        rows = load_chunks(conn)
    finally:
        conn.close()

    if not rows:
        raise RuntimeError("Nenhum chunk no banco. Rode uv run src/chunking.py antes.")

    embeddings = get_embeddings()
    vectorstore = get_vectorstore(embeddings)
    vectorstore.reset_collection()
    indexed_count = index_chunks(vectorstore, rows)
    print_summary(indexed_count, embeddings.model_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
