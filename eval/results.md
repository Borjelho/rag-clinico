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

**Tamanho real do acervo** (confirmado rodando `ingest.py` + `chunking.py`
sobre `data/raw/prontuario_sinteticos/`): 8 fontes (5 PDFs + 3 CSVs), 155
paginas de PDF com texto extraivel, 44.757 linhas de CSV. Apos chunking
(config baseline 1000/150): 9.804 chunks totais, sendo 536 de PDF e 9.268 de
CSV — um desbalanceamento de ~17x a favor dos prontuarios, relevante para a
secao 5.

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

### 5.1 Bug encontrado e corrigido: comparacao nao reprocessava de verdade

Antes de rodar a comparacao "para valer", encontramos um problema em
`reprocess_pipeline()`: a funcao era um no-op (so tinha um exemplo comentado
de como a integracao *deveria* ficar). Resultado: as 3 configuracoes eram
avaliadas sobre a mesma base vetorial ja existente, gerando numeros
identicos entre elas — o que parecia (erradamente) confirmar que o tamanho
do chunk nao fazia diferenca.

Corrigimos `reprocess_pipeline()` para, a cada configuracao: (1) sobrescrever
`PDF_CHUNK_SIZE`/`PDF_CHUNK_OVERLAP` em `src/chunking.py` e rodar
`chunk_all()` de verdade; (2) reindexar o Chroma via `embeddings.run_indexing()`;
(3) invalidar o cache do `rag_chain` (`_vectorstore`/`_chain`), que senao
continuaria apontando para a colecao antiga.

**Evidencia de que o fix funciona** — contagem real de chunks por config,
rodando `chunk_all()` sobre o acervo atual (8 fontes: 5 PDFs + 3 CSVs):

| Config | pdf_chunk_size | overlap | Chunks de PDF | Chunks de CSV | Total |
| ------ | -------------- | ------- | -------------- | -------------- | ----- |
| baseline_1000_150 | 1000 | 150 | 536 | 9.268 | 9.804 |
| menor_512_64 | 512 | 64 | 945 | 9.268 | 10.213 |
| maior_1500_200 | 1500 | 200 | 371 | 9.268 | 9.639 |

Os chunks de PDF variam bastante entre configs (371 a 945), como esperado —
antes do fix, os 3 rodavam sobre os mesmos 536. Os chunks de CSV nao mudam
porque o agrupamento de prontuarios usa `CSV_MAX_CHARS`, um parametro
separado que essas configs nao tocam.

### 5.2 Resultado por configuracao (fidelidade / relevancia)

> _TBD — preencher apos rodar `uv run eval/compare_chunking.py` com o Ollama
> ativo. O fix garante que cada linha agora reflete uma base vetorial
> genuinamente diferente; antes do fix os 3 numeros abaixo sairiam iguais
> por construcao, entao qualquer resultado anterior a esta correcao deve
> ser descartado._

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
- **Hipotese do desbalanceamento do acervo** (levantada por Bryan antes do
  fix, ao ver os 3 resultados identicos): com ~9.268 chunks de CSV contra
  apenas 371-945 de PDF dependendo da config, os prontuarios podem "afogar"
  as bulas na busca por similaridade, independentemente do tamanho do chunk.
  Essa hipotese continua plausivel (o desbalanceamento e real, ver tabela
  5.1), mas precisa ser reverificada com os numeros desta secao (5.2), ja
  que a evidencia original (resultados identicos) veio do bug, nao de um
  teste valido.
- Decisao final: qual configuracao a squad adotou e o motivo.

## 6. Conclusao

> Sintese: a RAG esta "boa o suficiente" para um contexto clinico?
> Preencher com base nos numeros: taxa de recusa correta nos controles
> negativos, fidelidade media, e casos criticos remanescentes.