"""Interface Streamlit do assistente clinico (RAG).

Consome exclusivamente src/rag_chain.py::answer(). Nao reimplementa
retrieval nem chamadas ao LLM aqui -- so exibicao.

Rodar com:
    uv run streamlit run src/app.py
"""

from __future__ import annotations

import streamlit as st

import rag_chain
from rag_chain import LLM_MODEL, RETRIEVER_K, RETRIEVER_MAX_DISTANCE, answer


st.set_page_config(
    page_title="Assistente Clínico — Consulta a Documentos",
    page_icon="🩺",
    layout="centered",
)


@st.cache_resource(show_spinner="Carregando base vetorial e conectando ao modelo local...")
def warm_up() -> bool:
    """Forca o carregamento do vectorstore/chain uma unica vez por sessao do servidor.

    rag_chain.answer() ja faz lazy-loading sozinho; isso so evita que o
    primeiro usuario da sessao espere o carregamento sem feedback visual.
    """
    rag_chain.get_or_load_vectorstore()
    rag_chain.get_chain()
    return True


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("fontes"):
            with st.expander(f"📎 Fontes citadas ({len(message['fontes'])})"):
                for fonte in message["fontes"]:
                    st.markdown(f"- {fonte}")
        if message["role"] == "assistant" and message.get("contextos"):
            with st.expander(f"🔎 Trechos recuperados ({len(message['contextos'])})"):
                for posicao, contexto in enumerate(message["contextos"], start=1):
                    st.markdown(f"**[{posicao}]**")
                    st.text(contexto)


def main() -> None:
    st.title("🩺 Assistente Clínico — Consulta a Documentos")
    st.caption(
        "Responde com base em protocolos, diretrizes, bulas e prontuários "
        "**sintéticos** ingeridos localmente. Sempre cita a fonte; perguntas "
        "fora do acervo são recusadas."
    )
    st.warning(
        "⚠️ Uso educacional. Acervo composto apenas por documentos públicos "
        "e prontuários sintéticos (LGPD). Não substitui avaliação clínica "
        "profissional.",
        icon="⚠️",
    )

    with st.sidebar:
        st.subheader("Configuração atual")
        st.markdown(f"**Modelo LLM (Ollama):** `{LLM_MODEL}`")
        st.markdown(f"**Chunks recuperados (k):** `{RETRIEVER_K}`")
        st.markdown(f"**Limiar de distância (recusa):** `{RETRIEVER_MAX_DISTANCE}`")
        st.caption(
            "O limiar de distância decide quando uma pergunta é considerada "
            "fora do acervo antes mesmo de chamar o LLM. Ajuste via variável "
            "de ambiente `RETRIEVER_MAX_DISTANCE` durante a avaliação "
            "(Semana 4)."
        )
        if st.button("🗑️ Limpar conversa"):
            st.session_state["messages"] = []
            st.rerun()

    try:
        warm_up()
    except FileNotFoundError as exc:
        st.error(
            "Base vetorial não encontrada.\n\n"
            f"Detalhe: {exc}\n\n"
            "Rode antes, na ordem:\n"
            "1. `uv run src/ingest.py`\n"
            "2. `uv run src/chunking.py`\n"
            "3. `uv run src/embeddings.py`"
        )
        st.stop()
    except Exception as exc:  # noqa: BLE001
        st.error(
            "Não consegui inicializar o modelo de embeddings ou a base vetorial.\n\n"
            f"Detalhe: {exc}"
        )
        st.stop()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for message in st.session_state["messages"]:
        render_message(message)

    pergunta = st.chat_input("Pergunte algo sobre o acervo clínico...")
    if not pergunta:
        return

    st.session_state["messages"].append({"role": "user", "content": pergunta})
    render_message(st.session_state["messages"][-1])

    with st.chat_message("assistant"):
        with st.spinner("Consultando o acervo e gerando a resposta..."):
            try:
                resultado = answer(pergunta)
            except Exception as exc:  # noqa: BLE001
                resultado = {
                    "resposta": (
                        "Ocorreu um erro ao consultar o modelo local. Verifique se "
                        "o Ollama está rodando (`ollama serve`) e se o modelo foi "
                        f"baixado (`ollama pull {LLM_MODEL}`).\n\nDetalhe técnico: {exc}"
                    ),
                    "contextos": [],
                    "fontes": [],
                }
        st.markdown(resultado["resposta"])
        if resultado["fontes"]:
            with st.expander(f"📎 Fontes citadas ({len(resultado['fontes'])})"):
                for fonte in resultado["fontes"]:
                    st.markdown(f"- {fonte}")
        if resultado["contextos"]:
            with st.expander(f"🔎 Trechos recuperados ({len(resultado['contextos'])})"):
                for posicao, contexto in enumerate(resultado["contextos"], start=1):
                    st.markdown(f"**[{posicao}]**")
                    st.text(contexto)

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": resultado["resposta"],
            "fontes": resultado["fontes"],
            "contextos": resultado["contextos"],
        }
    )


main()
