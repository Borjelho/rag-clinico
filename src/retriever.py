from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever

from vectorstore import COLLECTION_NAME, VECTORSTORE_DIR, open_vectorstore


DEFAULT_SEARCH_K = 4


def get_retriever(
    embeddings: Embeddings,
    persist_directory: Path = VECTORSTORE_DIR,
    collection_name: str = COLLECTION_NAME,
    k: int = DEFAULT_SEARCH_K,
    search_type: str = "similarity",
    search_kwargs: dict[str, Any] | None = None,
) -> VectorStoreRetriever:
    """Retorna um retriever baseado na coleção Chroma persistida."""
    vectorstore = open_vectorstore(embeddings, persist_directory, collection_name)
    kwargs = {"k": k, **(search_kwargs or {})}
    return vectorstore.as_retriever(search_type=search_type, search_kwargs=kwargs)


def similarity_search(
    query: str,
    embeddings: Embeddings,
    persist_directory: Path = VECTORSTORE_DIR,
    collection_name: str = COLLECTION_NAME,
    k: int = DEFAULT_SEARCH_K,
) -> Sequence[Document]:
    """Executa uma busca direta por similaridade na coleção Chroma persistida."""
    vectorstore = open_vectorstore(embeddings, persist_directory, collection_name)
    return vectorstore.similarity_search(query, k=k)


def similarity_search_with_score(
    query: str,
    embeddings: Embeddings,
    persist_directory: Path = VECTORSTORE_DIR,
    collection_name: str = COLLECTION_NAME,
    k: int = DEFAULT_SEARCH_K,
) -> list[tuple[Document, float]]:
    """Busca por similaridade retornando a distância cosseno de cada chunk.

    Distância menor = mais parecido (0 = idêntico). É o que o rag_chain usa
    para decidir se a pergunta está dentro do acervo antes de chamar o LLM.
    """
    vectorstore = open_vectorstore(embeddings, persist_directory, collection_name)
    return vectorstore.similarity_search_with_score(query, k=k)
