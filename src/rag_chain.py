"""RAG chain: retriever (Chroma) + prompt + LLM (Ollama), via LangChain (LCEL).

Contrato usado por eval/evaluate.py (ver docstring de eval/evaluate.py):

    answer(pergunta: str) -> dict com chaves:
        - "resposta": str          texto gerado pela RAG
        - "contextos": list[str]   trechos recuperados que embasaram a resposta
        - "fontes": list[str]      nomes/rotulos dos documentos-fonte citados

A aplicacao responde exclusivamente com base no acervo ingerido (requisito do
desafio). Isso e garantido em duas camadas:

    1. Camada de retrieval: se a melhor distancia (cosseno) entre a pergunta
       e os chunks recuperados for maior que RETRIEVER_MAX_DISTANCE, a
       pergunta e considerada fora do acervo e recusada sem nem chamar o LLM.
    2. Camada de prompt: mesmo com contexto recuperado, o LLM e instruido a
       recusar se o contexto nao contiver de fato a resposta (ver
       src/prompts.py).

Uso via CLI (util para testar antes de subir o Streamlit):

    uv run src/rag_chain.py --pergunta "Qual a meia-vida do clonazepam?"
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from embeddings import get_vectorstore
from prompts import REFUSAL_MESSAGE, build_prompt

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))

# Distancia cosseno maxima aceitavel entre a pergunta e o chunk mais proximo
# (0 = identico, 2 = oposto; o Chroma do projeto usa "hnsw:space": "cosine",
# ver src/embeddings.py). Perguntas fora desse limite sao recusadas antes de
# chamar o LLM. Valor inicial de andaime -- ajustar durante a Semana 4 usando
# eval/evaluate.py e eval/compare_chunking.py com o conjunto de teste real.
RETRIEVER_MAX_DISTANCE = float(os.getenv("RETRIEVER_MAX_DISTANCE", "0.45"))

# Modulo mantem estado (vectorstore/chain) em cache para nao recarregar o
# modelo de embeddings a cada pergunta -- importante na interface Streamlit.
_vectorstore = None
_chain = None


def get_llm() -> ChatOllama:
    return ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=LLM_TEMPERATURE,
    )


def format_source(metadata: dict[str, Any]) -> str:
    """Formata o rotulo de fonte citavel a partir dos metadados do chunk.

    Segue os metadados definidos em src/chunking.py / src/embeddings.py:
    PDFs tem page_start/page_end; CSVs tem table_name/patient_name.
    """
    document_name = metadata.get("document_name") or "documento desconhecido"

    page_start = metadata.get("page_start")
    if page_start:
        page_end = metadata.get("page_end", page_start)
        if page_end and page_end != page_start:
            return f"{document_name} (páginas {page_start}-{page_end})"
        return f"{document_name} (página {page_start})"

    table_name = metadata.get("table_name")
    if table_name:
        patient_name = metadata.get("patient_name")
        if patient_name:
            return f"{document_name} (paciente: {patient_name})"
        return document_name

    return document_name


def retrieve(pergunta: str, k: int = RETRIEVER_K) -> list[tuple[Document, float]]:
    """Busca os k chunks mais proximos da pergunta, com a distancia de cada um."""
    vectorstore = get_or_load_vectorstore()
    return vectorstore.similarity_search_with_score(pergunta, k=k)


def is_in_scope(
    results: list[tuple[Document, float]],
    max_distance: float = RETRIEVER_MAX_DISTANCE,
) -> bool:
    """Decide se a pergunta esta dentro do acervo, pela distancia do melhor chunk."""
    if not results:
        return False
    _best_doc, best_distance = results[0]
    return best_distance <= max_distance


def build_context_block(results: list[tuple[Document, float]]) -> str:
    """Monta o bloco de contexto numerado que vai para o prompt do LLM."""
    blocks = []
    for position, (document, _distance) in enumerate(results, start=1):
        fonte = format_source(document.metadata)
        blocks.append(f"[{position}] Fonte: {fonte}\n{document.page_content.strip()}")
    return "\n\n".join(blocks)


def get_or_load_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    return _vectorstore


def get_chain():
    """Monta (uma vez) a chain LCEL: prompt | llm | parser."""
    global _chain
    if _chain is None:
        prompt = build_prompt()
        llm = get_llm()
        _chain = prompt | llm | StrOutputParser()
    return _chain


def answer(pergunta: str, k: int = RETRIEVER_K) -> dict[str, Any]:
    """Responde uma pergunta clinica com base exclusivamente no acervo ingerido.

    Retorna sempre um dict com "resposta", "contextos" e "fontes" (contrato
    usado por eval/evaluate.py). Perguntas fora do acervo (ou sem contexto
    suficiente) recebem REFUSAL_MESSAGE com contextos/fontes vazios.
    """
    pergunta = pergunta.strip()
    if not pergunta:
        return {"resposta": REFUSAL_MESSAGE, "contextos": [], "fontes": []}

    results = retrieve(pergunta, k=k)

    if not is_in_scope(results):
        return {"resposta": REFUSAL_MESSAGE, "contextos": [], "fontes": []}

    contexto = build_context_block(results)
    chain = get_chain()
    resposta = chain.invoke({"pergunta": pergunta, "contexto": contexto})

    return {
        "resposta": resposta.strip(),
        "contextos": [document.page_content for document, _distance in results],
        "fontes": sorted({format_source(document.metadata) for document, _ in results}),
    }


def print_answer(pergunta: str) -> None:
    resultado = answer(pergunta)
    print(f"\nPergunta: {pergunta}\n")
    print(f"Resposta:\n{resultado['resposta']}\n")
    if resultado["fontes"]:
        print("Fontes citadas:")
        for fonte in resultado["fontes"]:
            print(f"  - {fonte}")
    else:
        print("(nenhuma fonte -- pergunta tratada como fora do acervo)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa a RAG chain via linha de comando.")
    parser.add_argument(
        "--pergunta",
        metavar="TEXTO",
        help="pergunta a ser feita a RAG (se omitido, roda um exemplo fixo)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=RETRIEVER_K,
        help="quantidade de chunks a recuperar (default: %(default)s)",
    )
    args = parser.parse_args()

    pergunta = args.pergunta or "Qual a meia-vida de eliminação do clonazepam?"
    print_answer(pergunta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
