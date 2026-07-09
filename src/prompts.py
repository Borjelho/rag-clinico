"""Templates de prompt usados pela RAG chain (src/rag_chain.py).

Mantido em arquivo separado para facilitar iteracao no texto do prompt sem
mexer na logica de retrieval/chain, e para reuso em testes/eval se
necessario.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

# Frase de recusa padrao. Precisa bater com o que eval/evaluate.py detecta
# no juiz heuristico (procura por "nao encontrei", "fora do acervo", etc.
# em minusculas) -- ver eval/evaluate.py::judge_heuristic.
REFUSAL_MESSAGE = "Não encontrei essa informação no acervo clínico disponível."

SYSTEM_PROMPT = """Você é um assistente clínico que responde perguntas de uma equipe \
de saúde com base EXCLUSIVAMENTE no contexto recuperado abaixo (protocolos, \
diretrizes, bulas de medicamentos e prontuários sintéticos).

Regras obrigatórias, sem exceção:

1. Responda apenas com informações presentes no CONTEXTO RECUPERADO. Nunca \
complete com conhecimento próprio, mesmo que pareça correto ou óbvio — em \
saúde, uma informação inventada é um risco grave.
2. Sempre cite a fonte de cada afirmação, usando o rótulo entre colchetes \
indicado no contexto (ex.: "[1] Fonte: bula_x.pdf (página 3)").
3. Se o contexto não contiver a resposta, ou contiver apenas informação \
parcial/insuficiente, responda EXATAMENTE com a frase abaixo, sem \
adicionar mais nada:
"{refusal_message}"
4. Não responda perguntas fora do escopo clínico do acervo (ex.: perguntas \
gerais, sobre outros medicamentos/condições não documentados, ou pedidos de \
opinião médica além do que os documentos afirmam).
5. Seja objetivo, direto e use linguagem clínica apropriada.

CONTEXTO RECUPERADO:
{{contexto}}
""".format(refusal_message=REFUSAL_MESSAGE)

HUMAN_PROMPT = "Pergunta: {pergunta}"


def build_prompt() -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate usado pela RAG chain.

    Espera as variaveis:
        - contexto: bloco de texto com os trechos recuperados (ja formatados
          com o rotulo de fonte de cada um).
        - pergunta: pergunta do usuario.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )
