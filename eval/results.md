# Relatorio de Avaliacao da RAG Clinica

> Documento de avaliacao exigido na entrega final (Parte B do desafio).
> Cobre: conjunto de teste, medicao de fidelidade e relevancia, casos
> insatisfatorios e comparacao entre configuracoes de chunk.
>
> Os numeros abaixo sao preenchidos apos rodar `evaluate.py` e
> `compare_chunking.py` sobre o pipeline real (nao no modo `--mock`).

## 1. Conjunto de teste

O gabarito (`eval/test_questions.json`) tem 12 perguntas: 10 com resposta
verificavel no acervo e 2 de controle negativo (fora do acervo), para medir
se a RAG recusa corretamente perguntas sem base documental.

| Faixa | Categoria | Qtd | Proposito |
| ----- | --------- | --- | --------- |
| Q01-Q07 | Bulas (clonazepam, dipirona, Ozempic) | 7 | Doses, indicacoes, contraindicacoes, reacoes adversas |
| Q08 | Protocolo (cancer de pulmao) | 1 | Fator de risco |
| Q09-Q10 | Protocolo (doenca de Wilson) | 2 | Diagnostico, CID-10, heranca |
| Q11-Q12 | Fora do acervo (amoxicilina, apendicite) | 2 | Controle negativo: deve recusar |

Cada pergunta traz resposta esperada e trecho-fonte, servindo de gabarito
para o LLM as a Judge.

## 2. Metodo de avaliacao

- **Juiz:** LLM as a Judge (modelo local via Ollama), temperatura 0.
- **Fidelidade (0-5):** a resposta esta ancorada no contexto recuperado, sem alucinar.
- **Relevancia (0-5):** a resposta de fato responde a pergunta.
- **Controle negativo:** recusar corretamente pontua 5/5; inventar resposta pontua 0.

Comando: `uv run eval/evaluate.py --config baseline`

## 3. Resultado da configuracao baseline

> Preencher apos rodar no pipeline real.

- Media de fidelidade: **_TBD_ / 5**
- Media de relevancia: **_TBD_ / 5**

| ID | Categoria | Fidelidade | Relevancia | Observacao |
| -- | --------- | ---------- | ---------- | ---------- |
| Q01 | bula | _TBD_ | _TBD_ | |
| Q02 | bula | _TBD_ | _TBD_ | |
| Q03 | bula | _TBD_ | _TBD_ | |
| Q04 | bula | _TBD_ | _TBD_ | |
| Q05 | bula | _TBD_ | _TBD_ | |
| Q06 | bula | _TBD_ | _TBD_ | |
| Q07 | bula | _TBD_ | _TBD_ | |
| Q08 | protocolo | _TBD_ | _TBD_ | |
| Q09 | protocolo | _TBD_ | _TBD_ | |
| Q10 | protocolo | _TBD_ | _TBD_ | |
| Q11 | fora_do_acervo | _TBD_ | _TBD_ | recusa esperada |
| Q12 | fora_do_acervo | _TBD_ | _TBD_ | recusa esperada |

## 4. Casos insatisfatorios

> Preencher com os casos onde a RAG falhou. Em saude, alucinacao e falha grave.
> Para cada caso: qual pergunta, o que saiu errado e a causa provavel.

| ID | Sintoma | Causa provavel |
| -- | ------- | -------------- |
| _TBD_ | ex.: recuperou contexto irrelevante | ex.: chunk grande demais diluiu o trecho-alvo |
| _TBD_ | ex.: alucinou dose nao presente na bula | ex.: retriever nao trouxe a pagina de posologia |
| _TBD_ | ex.: nao recusou pergunta fora do acervo | ex.: limiar de similaridade permissivo demais |

## 5. Otimizacao de chunking

Comparacao de configuracoes com o mesmo gabarito (`compare_chunking.py`).

Comando: `uv run eval/compare_chunking.py`

| Config | chunk_size | overlap | Fidelidade | Relevancia |
| ------ | ---------- | ------- | ---------- | ---------- |
| baseline | 1000 | 150 | _TBD_ | _TBD_ |
| menor | 512 | 64 | _TBD_ | _TBD_ |
| maior | 1500 | 200 | _TBD_ | _TBD_ |

**Racional da otimizacao** (preencher apos rodar):

- Qual config teve melhor fidelidade/relevancia e por que.
- Efeito de chunks menores: tendem a recuperar trechos mais precisos, mas
  podem fragmentar contexto que precisa ser lido junto (ex.: posologia).
- Efeito de chunks maiores: preservam contexto, mas podem diluir o trecho-alvo
  e trazer ruido para o LLM.
- Decisao final: qual configuracao a squad adotou e o motivo.

## 6. Conclusao

> Sintese: a RAG esta "boa o suficiente" para um contexto clinico?
> Preencher com base nos numeros: taxa de recusa correta nos controles
> negativos, fidelidade media, e casos criticos remanescentes.