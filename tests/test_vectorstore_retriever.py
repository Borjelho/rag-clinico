from __future__ import annotations

import hashlib
import math
import re
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from langchain_core.embeddings import Embeddings

from retriever import get_retriever, similarity_search
from vectorstore import load_chunk_documents, rebuild_vectorstore


class HashEmbeddings(Embeddings):
    """Embeddings determinísticas para smoke tests de Chroma/retriever."""

    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions

        for token in re.findall(r"\w+", text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def test_vectorstore_rebuild_and_retriever_smoke() -> None:
    embeddings = HashEmbeddings()
    collection_name = "clinical_documents_vector_db_smoke_test"

    with tempfile.TemporaryDirectory(
        prefix="rag_clinico_chroma_",
        ignore_cleanup_errors=True,
    ) as temp_dir:
        persist_directory = Path(temp_dir)
        documents = load_chunk_documents()
        vectorstore = rebuild_vectorstore(
            embeddings=embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name,
        )

        direct_docs = similarity_search(
            "dipirona contraindicacoes bula",
            embeddings=embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name,
            k=3,
        )
        retriever = get_retriever(
            embeddings=embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name,
            k=4,
        )
        retrieved_docs = retriever.invoke("Doenca de Wilson tratamento protocolo")

        assert documents
        assert vectorstore._collection.count() == len(documents)
        assert len(direct_docs) == 3
        assert len(retrieved_docs) == 4
        assert all(doc.page_content.strip() for doc in direct_docs + retrieved_docs)
        assert all(
            doc.metadata.get("document_name") for doc in direct_docs + retrieved_docs
        )
        assert all(doc.metadata.get("chunk_uid") for doc in direct_docs + retrieved_docs)

        print(f"chunks_loaded={len(documents)}")
        print(f"chroma_count={vectorstore._collection.count()}")
        print(f"similarity_docs={len(direct_docs)}")
        print(f"retriever_docs={len(retrieved_docs)}")
        print("VECTOR_DB_RETRIEVER_OK")


if __name__ == "__main__":
    test_vectorstore_rebuild_and_retriever_smoke()
