"""Avaliacao da RAG clinica: fidelidade e relevancia via LLM as a Judge.

Este modulo e desacoplado da RAG chain. Ele espera uma funcao de resposta
com a assinatura:

    answer(pergunta: str) -> dict com chaves:
        - "resposta": str          (texto gerado pela RAG)
        - "contextos": list[str]   (trechos recuperados que embasaram a resposta)
        - "fontes": list[str]      (nomes dos documentos-fonte citados) [opcional]

Enquanto a rag_chain (src/rag_chain.py) nao estiver pronta, use --mock para
rodar com respostas simuladas e validar o pipeline de avaliacao.

Uso:
    uv run eval/evaluate.py --mock
    uv run eval/evaluate.py                # usa a RAG real (quando disponivel)
    uv run eval/evaluate.py --config nome  # rotula a run (ex.: baseline, chunk_512)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
QUESTIONS_PATH = EVAL_DIR / "test_questions.json"
RESULTS_JSON = EVAL_DIR / "results.json"

# Juiz LLM local via Ollama. Ajuste o modelo conforme o que a squad rodar.
JUDGE_MODEL = "llama3.1"


# --------------------------------------------------------------------------- #
# Carga do gabarito
# --------------------------------------------------------------------------- #
def load_questions() -> list[dict]:
    with QUESTIONS_PATH.open(encoding="utf-8") as file:
        data = json.load(file)
    return data["perguntas"]


# --------------------------------------------------------------------------- #
# Provedor de respostas: RAG real ou mock
# --------------------------------------------------------------------------- #
def get_rag_answer_fn() -> Callable[[str], dict]:
    """Importa a RAG real de src/rag_chain.py.

    Espera-se que rag_chain exponha uma funcao `answer(pergunta) -> dict`.
    Enquanto nao existir, esta funcao levanta ImportError e o chamador
    deve cair para o modo --mock.
    """
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from rag_chain import answer  # type: ignore

    return answer


def mock_answer(pergunta: str) -> dict:
    """Resposta simulada para validar o pipeline de avaliacao sem a RAG.

    Devolve algo plausivel para perguntas dentro do acervo e uma recusa
    para perguntas claramente fora dele. NAO e uma RAG real; serve so
    para exercitar evaluate.py de ponta a ponta.
    """
    fora = ["amoxicilina", "apendicite", "apendice"]
    if any(term in pergunta.lower() for term in fora):
        return {
            "resposta": "Nao encontrei essa informacao no acervo clinico disponivel.",
            "contextos": [],
            "fontes": [],
        }
    return {
        "resposta": "[MOCK] Resposta simulada baseada no acervo para: " + pergunta,
        "contextos": ["[MOCK] trecho recuperado de exemplo do acervo."],
        "fontes": ["documento_exemplo.pdf"],
    }


# --------------------------------------------------------------------------- #
# Juiz LLM
# --------------------------------------------------------------------------- #
JUDGE_PROMPT = """Voce e um avaliador rigoroso de um sistema de perguntas e \
respostas clinico. Avalie a RESPOSTA GERADA em duas dimensoes, comparando com \
a RESPOSTA DE REFERENCIA e o CONTEXTO RECUPERADO.

1. FIDELIDADE (0 a 5): a resposta esta fundamentada no contexto recuperado, \
sem inventar informacao que nao esteja la? 5 = totalmente ancorada; \
0 = alucinada ou sem base no contexto.

2. RELEVANCIA (0 a 5): a resposta de fato responde a pergunta feita? \
5 = responde completamente; 0 = nao responde ou foge do tema.

Se a pergunta for de CONTROLE NEGATIVO (a referencia indica RECUSA_ESPERADA), \
entao a resposta correta e recusar ou sinalizar ausencia de fonte. Nesse caso, \
pontue FIDELIDADE 5 e RELEVANCIA 5 se a resposta recusou corretamente, e 0 se \
ela inventou uma resposta.

PERGUNTA:
{pergunta}

RESPOSTA DE REFERENCIA:
{referencia}

CONTEXTO RECUPERADO:
{contexto}

RESPOSTA GERADA:
{resposta}

Responda APENAS com um JSON valido, sem texto adicional, no formato:
{{"fidelidade": <int 0-5>, "relevancia": <int 0-5>, "justificativa": "<uma frase>"}}"""


def judge_with_llm(item: dict, resposta: str, contextos: list[str]) -> dict:
    """Chama o LLM juiz via Ollama e devolve as notas.

    Requer `ollama` instalado e o modelo baixado. Se indisponivel,
    levanta excecao e o chamador cai para judge_heuristic.
    """
    import ollama  # type: ignore

    contexto_txt = "\n---\n".join(contextos) if contextos else "(nenhum contexto recuperado)"
    prompt = JUDGE_PROMPT.format(
        pergunta=item["pergunta"],
        referencia=item["resposta_esperada"],
        contexto=contexto_txt,
        resposta=resposta,
    )
    response = ollama.chat(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.0},
    )
    raw = response["message"]["content"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(raw)
    return {
        "fidelidade": int(parsed["fidelidade"]),
        "relevancia": int(parsed["relevancia"]),
        "justificativa": parsed.get("justificativa", ""),
    }


def judge_heuristic(item: dict, resposta: str, contextos: list[str]) -> dict:
    """Juiz de fallback sem LLM, para validar o pipeline no modo mock.

    Regras simples: recusa correta em controle negativo pontua alto;
    resposta com contexto pontua medio; resposta sem contexto pontua baixo.
    NAO substitui o LLM as a Judge na avaliacao final; e so andaime.
    """
    is_negativo = item.get("tipo") == "controle_negativo"
    recusou = any(
        termo in resposta.lower()
        for termo in ["nao encontrei", "nao consta", "fora do acervo", "nao ha", "ausencia"]
    )

    if is_negativo:
        nota = 5 if recusou else 0
        return {
            "fidelidade": nota,
            "relevancia": nota,
            "justificativa": "Recusou corretamente." if recusou else "Deveria ter recusado.",
        }

    if recusou:
        return {
            "fidelidade": 3,
            "relevancia": 0,
            "justificativa": "Recusou uma pergunta que estava no acervo.",
        }

    fidelidade = 4 if contextos else 1
    relevancia = 4 if len(resposta) > 20 else 1
    return {
        "fidelidade": fidelidade,
        "relevancia": relevancia,
        "justificativa": "Heuristica (andaime, sem LLM).",
    }


# --------------------------------------------------------------------------- #
# Loop de avaliacao
# --------------------------------------------------------------------------- #
def evaluate(answer_fn: Callable[[str], dict], use_llm_judge: bool, config_label: str) -> dict:
    questions = load_questions()
    linhas = []
    soma_fid = 0
    soma_rel = 0

    for item in questions:
        saida = answer_fn(item["pergunta"])
        resposta = saida.get("resposta", "")
        contextos = saida.get("contextos", [])

        notas = None
        if use_llm_judge:
            try:
                notas = judge_with_llm(item, resposta, contextos)
            except Exception as exc:  # noqa: BLE001
                print(f"  [aviso] juiz LLM falhou em {item['id']} ({exc}); usando heuristica.")
        if notas is None:
            notas = judge_heuristic(item, resposta, contextos)

        soma_fid += notas["fidelidade"]
        soma_rel += notas["relevancia"]
        linhas.append(
            {
                "id": item["id"],
                "categoria": item["categoria"],
                "tipo": item["tipo"],
                "pergunta": item["pergunta"],
                "resposta_gerada": resposta,
                "n_contextos": len(contextos),
                "fidelidade": notas["fidelidade"],
                "relevancia": notas["relevancia"],
                "justificativa": notas["justificativa"],
            }
        )
        print(f"  {item['id']}: fid={notas['fidelidade']} rel={notas['relevancia']}")

    n = len(questions)
    resultado = {
        "config": config_label,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "juiz": "llm" if use_llm_judge else "heuristica",
        "total_perguntas": n,
        "media_fidelidade": round(soma_fid / n, 2),
        "media_relevancia": round(soma_rel / n, 2),
        "linhas": linhas,
    }
    return resultado


def save_results(resultado: dict) -> None:
    historico = []
    if RESULTS_JSON.exists():
        with RESULTS_JSON.open(encoding="utf-8") as file:
            historico = json.load(file)
    historico.append(resultado)
    with RESULTS_JSON.open("w", encoding="utf-8") as file:
        json.dump(historico, file, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Avalia a RAG clinica.")
    parser.add_argument("--mock", action="store_true", help="Usa respostas simuladas.")
    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="Usa juiz heuristico em vez de LLM as a Judge.",
    )
    parser.add_argument(
        "--config",
        default="baseline",
        help="Rotulo da configuracao avaliada (ex.: baseline, chunk_512_overlap_50).",
    )
    args = parser.parse_args()

    if args.mock:
        answer_fn = mock_answer
        print("Modo MOCK: respostas simuladas.")
    else:
        try:
            answer_fn = get_rag_answer_fn()
        except Exception as exc:  # noqa: BLE001
            print(f"Nao consegui importar a RAG real ({exc}).")
            print("Rode com --mock enquanto src/rag_chain.py nao estiver pronto.")
            return 1

    use_llm_judge = not args.no_llm_judge and not args.mock
    print(f"Avaliando config '{args.config}' (juiz: {'LLM' if use_llm_judge else 'heuristica'})...")

    resultado = evaluate(answer_fn, use_llm_judge, args.config)
    save_results(resultado)

    print()
    print(f"Media fidelidade: {resultado['media_fidelidade']}/5")
    print(f"Media relevancia: {resultado['media_relevancia']}/5")
    print(f"Resultados salvos em {RESULTS_JSON.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())