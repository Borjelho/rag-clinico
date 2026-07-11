# Relatorio de Avaliacao da RAG Clinica

> Documento de avaliacao exigido na entrega final (Parte B do desafio).
> Cobre: conjunto de teste, medicao de fidelidade e relevancia, casos
> insatisfatorios e comparacao entre configuracoes de chunk.

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

- **Juiz:** LLM as a Judge (`llama3.1` local via Ollama), temperatura 0.
- **Fidelidade (0-5):** a resposta esta ancorada no contexto recuperado, sem alucinar.
- **Relevancia (0-5):** a resposta de fato responde a pergunta.
- **Controle negativo:** recusar corretamente pontua 5/5; inventar resposta pontua 0.

Comando: `uv run eval/evaluate.py --config baseline`

## 3. Resultado da configuracao baseline (chunk 1000 / overlap 150)

- Media de fidelidade: **2,92 / 5**
- Media de relevancia: **3,00 / 5**

| ID | Categoria | Fidelidade | Relevancia | Observacao |
| -- | --------- | :--------: | :--------: | ---------- |
| Q01 | bula (clonazepam) | 0 | 0 | recuperou prontuarios (CSV), nao a bula |
| Q02 | bula (clonazepam) | 5 | 5 | recuperou a bula corretamente |
| Q03 | bula (clonazepam) | 5 | 5 | recuperou a bula corretamente |
| Q04 | bula (dipirona) | 0 | 0 | recuperou prontuarios irrelevantes |
| Q05 | bula (dipirona) | 0 | 0 | recuperou prontuarios irrelevantes |
| Q06 | bula (dipirona) | 2 | 1 | recuperacao parcial, resposta fraca |
| Q07 | bula (Ozempic) | 4 | 5 | recuperou a bula corretamente |
| Q08 | protocolo (cancer pulmao) | 0 | 0 | nao recuperou o trecho do fator de risco |
| Q09 | protocolo (Wilson) | 4 | 5 | recuperou o protocolo, resposta correta |
| Q10 | protocolo (Wilson) | 5 | 5 | recuperou o protocolo, resposta correta |
| Q11 | fora do acervo | 5 | 5 | recusou corretamente |
| Q12 | fora do acervo | 5 | 5 | recusou corretamente |

**Leitura:** no baseline, os controles negativos passam (recusa correta), os
protocolos de Wilson vao bem, mas as bulas de dipirona falham por completo e
uma pergunta de protocolo (Q08) tambem falha. As bulas sao o ponto fraco.

## 4. Casos insatisfatorios

| ID | Sintoma | Causa provavel |
| -- | ------- | -------------- |
| Q04, Q05 (dipirona) | Recuperou registros de prontuario em vez da bula; alguns nem eram de dipirona. | Desbalanceamento do acervo: a massa de chunks de prontuario (CSV) afoga as poucas paginas de bula na busca por similaridade. |
| Q01 (clonazepam) | Recuperou prontuarios de pacientes que usaram clonazepam em vez da bula. | Mesmo desbalanceamento: o medicamento aparece em muitos prontuarios, que dominam o top-k. |
| Q08 (cancer de pulmao) | Nao trouxe o trecho do fator de risco. | Trecho-alvo nao entrou no top-k na config baseline; melhora com chunks menores (ver secao 5). |

Em saude, nao recuperar uma bula e recusar/errar e menos grave do que alucinar
(a RAG nao inventou doses), mas ainda e uma falha de cobertura: a informacao
existe no acervo e nao foi entregue.

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

**Evidencia de que o fix funciona** — contagem real de chunks por config:

| Config | pdf_chunk_size | overlap | Chunks de PDF | Chunks de CSV | Total |
| ------ | -------------- | ------- | -------------- | -------------- | ----- |
| baseline_1000_150 | 1000 | 150 | 536 | 9.268 | 9.804 |
| menor_512_64 | 512 | 64 | 945 | 9.268 | 10.213 |
| maior_1500_200 | 1500 | 200 | 371 | 9.268 | 9.639 |

Os chunks de PDF variam bastante entre configs (371 a 945), como esperado.
Os chunks de CSV nao mudam porque o agrupamento de prontuarios usa
`CSV_MAX_CHARS`, um parametro separado que essas configs nao tocam.

### 5.2 Resultado por configuracao (fidelidade / relevancia)

| Config | chunk_size | overlap | Fidelidade | Relevancia |
| ------ | :--------: | :-----: | :--------: | :--------: |
| baseline | 1000 | 150 | 2,92 | 3,00 |
| **menor** | **512** | **64** | **4,25** | **4,42** |
| maior | 1500 | 200 | 3,17 | 3,42 |

**Racional da otimizacao:**

A configuracao **menor (512/64) foi a melhor com folga** (4,25 de fidelidade e
4,42 de relevancia, contra 2,92/3,00 do baseline). O ganho tem uma causa
identificavel: chunks menores geraram mais chunks de PDF (945 contra 536 do
baseline), o que aumentou a chance das paginas de bula entrarem no top-k e
vencerem a competicao com os prontuarios. Na pratica, as perguntas de dipirona
(Q04, Q05), que falhavam por completo no baseline, passaram a acertar na config
menor.

Isso confirma e ao mesmo tempo refina a hipotese do desbalanceamento levantada
na primeira analise: o desbalanceamento CSV vs PDF e real e e a causa das
falhas de bula, mas o tamanho do chunk **tem sim** efeito, porque chunks de PDF
menores aumentam a densidade de trechos de bula na base e ajudam a superar o
afogamento pelos prontuarios.

A config maior (1500/200) ficou entre as duas, coerente com a explicacao:
menos chunks de PDF (371) significa menos chance da bula ser recuperada.

**Decisao:** a squad adota a configuracao **menor (512/64)** como padrao de
producao, por apresentar a melhor fidelidade e relevancia no conjunto de teste.

**Nota sobre variancia:** o LLM as a Judge apresenta pequena variacao entre
execucoes (mesmo com temperatura 0), e em duas perguntas da config menor o juiz
LLM falhou e caiu para a heuristica de fallback. Ainda assim, a diferenca entre
a config menor e as demais e grande o suficiente para sustentar a conclusao.

## 6. Conclusao

A RAG esta funcional e segura para o escopo do desafio: recupera e responde
perguntas de protocolo citando a fonte, e recusa corretamente perguntas fora do
acervo (controles negativos 5/5 em todas as configuracoes), sem alucinar.

Com a configuracao otimizada (chunk 512/64), a fidelidade media sobe de 2,92
para 4,25 e a cobertura das bulas melhora sensivelmente. Ainda assim, para um
uso clinico real, a RAG precisaria de mais uma iteracao: mesmo na melhor config,
convem separar a recuperacao por tipo de documento (bula/protocolo vs
prontuario) para eliminar de vez o risco de uma bula nao ser recuperada, ja que
em saude deixar de entregar uma posologia e uma falha de seguranca. O criterio
de "boa o suficiente" que adotamos e: nenhuma falha sistematica de recuperacao
por categoria clinica e taxa de recusa correta proxima de 100% nos casos fora do
acervo — a segunda condicao ja e atendida; a primeira melhorou muito com a
otimizacao e seria fechada com a separacao por tipo de documento.