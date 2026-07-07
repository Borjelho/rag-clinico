from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTORSTORE_DIR = PROJECT_ROOT / "vectorstore"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "acervo_clinico")
BATCH_SIZE = 64


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
