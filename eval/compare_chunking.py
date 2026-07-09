"""Otimizacao de chunking: compara >= 2 configuracoes com o mesmo conjunto de teste.

Atende a dimensao "Otimizacao de chunks" da rubrica: rodar o mesmo gabarito
sob configuracoes diferentes de chunk (tamanho / overlap), reavaliar e
documentar o ganho ou a perda.

Fluxo por configuracao:
    1. (re)processa o chunking com os parametros da config
    2. (re)gera embeddings e reindexa o vector store
    3. roda evaluate() sobre o gabarito
    4. coleta media de fidelidade e relevancia

Assim como evaluate.py, este script e desacoplado. Enquanto o pipeline real
(chunking parametrizavel + embeddings + vector store) nao estiver pronto, use
--mock para exercitar a comparacao de ponta a ponta e validar a tabela de saida.

Uso:
    uv run eval/compare_chunking.py --mock
    uv run eval/compare_chunking.py            # usa o pipeline real (quando pronto)

Integracao com o pipeline real (quando as frentes de chunking/embeddings/vector
store estiverem prontas), implemente `reprocess_pipeline(config)` chamando os
modulos da squad. Os pontos de plugue estao marcados com TODO(integracao).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from evaluate import (
    evaluate,
    load_questions,
    mock_answer,
    get_rag_answer_fn,
)

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
COMPARISON_JSON = EVAL_DIR / "chunking_comparison.json"


# --------------------------------------------------------------------------- #
# Configuracoes de chunk a comparar.
# A rubrica pede no minimo 2. Aqui deixamos 3 para dar margem de analise:
# uma baseline, uma com chunks menores e uma com chunks maiores.
# Os nomes dos parametros seguem os que Lucas definiu em src/chunking.py
# (PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP).
# --------------------------------------------------------------------------- #
CHUNK_CONFIGS = [
    {"label": "baseline_1000_150", "pdf_chunk_size": 1000, "pdf_chunk_overlap": 150},
    {"label": "menor_512_64", "pdf_chunk_size": 512, "pdf_chunk_overlap": 64},
    {"label": "maior_1500_200", "pdf_chunk_size": 1500, "pdf_chunk_overlap": 200},
]


def reprocess_pipeline(config: dict) -> None:
    """Reprocessa chunking + embeddings + vector store para a config dada.

    TODO(integracao): quando as frentes estiverem prontas, este corpo deve:
      1. sobrescrever PDF_CHUNK_SIZE / PDF_CHUNK_OVERLAP em src/chunking.py
         (ou passar via parametro/env) e rodar chunk_all()
      2. rodar src/embeddings.py para regenerar os vetores
      3. reindexar o vector store (Chroma)

    Enquanto isso nao existe, e um no-op (usado no modo --mock).
    """
    # Exemplo de como sera a integracao (deixado comentado de proposito):
    #
    #   import chunking
    #   chunking.PDF_CHUNK_SIZE = config["pdf_chunk_size"]
    #   chunking.PDF_CHUNK_OVERLAP = config["pdf_chunk_overlap"]
    #   conn = storage.connect_database()
    #   chunking.chunk_all(conn)
    #   conn.close()
    #   embeddings.build_index()   # regenera vetores + reindexa Chroma
    #
    return None


def run_comparison(use_mock: bool) -> dict:
    if use_mock:
        answer_fn = mock_answer
        use_llm_judge = False
        print("Modo MOCK: pipeline simulado, juiz heuristico.")
    else:
        answer_fn = get_rag_answer_fn()
        use_llm_judge = True

    # Garante que o gabarito existe / e valido antes de comecar.
    load_questions()

    runs = []
    for config in CHUNK_CONFIGS:
        print(f"\n=== Config: {config['label']} "
              f"(size={config['pdf_chunk_size']}, overlap={config['pdf_chunk_overlap']}) ===")
        if not use_mock:
            reprocess_pipeline(config)

        resultado = evaluate(answer_fn, use_llm_judge, config["label"])
        runs.append(
            {
                "label": config["label"],
                "pdf_chunk_size": config["pdf_chunk_size"],
                "pdf_chunk_overlap": config["pdf_chunk_overlap"],
                "media_fidelidade": resultado["media_fidelidade"],
                "media_relevancia": resultado["media_relevancia"],
                "linhas": resultado["linhas"],
            }
        )

    comparison = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "juiz": "heuristica" if use_mock else "llm",
        "runs": runs,
    }
    return comparison


def print_table(comparison: dict) -> None:
    print("\n" + "=" * 64)
    print("COMPARACAO DE CONFIGURACOES DE CHUNK")
    print("=" * 64)
    header = f"{'Config':<22}{'size':>6}{'overlap':>9}{'fidelid.':>10}{'relev.':>9}"
    print(header)
    print("-" * 64)
    for run in comparison["runs"]:
        print(
            f"{run['label']:<22}"
            f"{run['pdf_chunk_size']:>6}"
            f"{run['pdf_chunk_overlap']:>9}"
            f"{run['media_fidelidade']:>10}"
            f"{run['media_relevancia']:>9}"
        )
    print("-" * 64)

    melhor = max(
        comparison["runs"],
        key=lambda r: (r["media_fidelidade"] + r["media_relevancia"]),
    )
    print(f"Melhor config (fidelidade + relevancia): {melhor['label']}")


def save_comparison(comparison: dict) -> None:
    with COMPARISON_JSON.open("w", encoding="utf-8") as file:
        json.dump(comparison, file, ensure_ascii=False, indent=2)
    print(f"Comparacao salva em {COMPARISON_JSON.relative_to(PROJECT_ROOT).as_posix()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara configuracoes de chunking.")
    parser.add_argument("--mock", action="store_true", help="Usa pipeline simulado.")
    args = parser.parse_args()

    comparison = run_comparison(use_mock=args.mock)
    print_table(comparison)
    save_comparison(comparison)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())