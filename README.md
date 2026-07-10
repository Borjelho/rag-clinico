# rag-clinico - Assistente Clínico de Consulta a Documentos

Assistente de perguntas e respostas sobre um acervo clínico local de bulas, protocolos e prontuários sintéticos. O projeto usa RAG (Retrieval-Augmented Generation) para recuperar trechos relevantes, gerar respostas com um modelo local via Ollama e exibir as fontes consultadas.

> **Uso educacional.** O sistema não substitui avaliação clínica profissional. O acervo deve conter somente documentos públicos e dados sintéticos; nunca utilize dados reais de pacientes.

## Arquitetura

```text
Arquivos PDF e CSV
  -> ingestão (SQLite)
  -> chunking (SQLite)
  -> embeddings (Chroma local)
  -> recuperação por similaridade
  -> RAG com Ollama
  -> interface Streamlit ou CLI
```

Antes de chamar o LLM, a RAG compara a distância cosseno do melhor trecho recuperado com `RETRIEVER_MAX_DISTANCE`. Perguntas sem trecho suficientemente próximo são recusadas. O prompt também instrui o modelo a responder apenas com o contexto recuperado.

## Stack

| Camada                     | Tecnologia atual                                                         |
| -------------------------- | ------------------------------------------------------------------------ |
| Linguagem                  | Python 3.12                                                              |
| Leitura de PDF             | pdfplumber                                                               |
| Persistência intermediária | SQLite                                                                   |
| Chunking de PDFs           | `RecursiveCharacterTextSplitter` (1.000 caracteres, sobreposição de 150) |
| Chunking de CSVs           | Agrupamento por paciente/tabela (até 1.800 caracteres)                   |
| Embeddings                 | `sentence-transformers`, com `intfloat/multilingual-e5-base` por padrão  |
| Base vetorial              | Chroma com distância cosseno                                             |
| Orquestração               | LangChain (LCEL)                                                         |
| LLM                        | Ollama, com `llama3.1` por padrão                                        |
| Interface                  | Streamlit                                                                |
| Avaliação                  | LLM-as-a-Judge via Ollama, com fallback heurístico                       |

## Estrutura de Pastas

```text
rag-clinico/
├── data/
│   ├── raw/prontuario_sinteticos/
│   │   ├── bulas/                 # PDFs de bulas
│   │   ├── protocolos/            # PDFs de protocolos e diretrizes
│   │   └── prontuarios/           # CSVs de dados sintéticos
│   └── processed/                 # SQLite gerado pela ingestão (não versionado)
├── docs/
│   ├── embeddings.md
│   └── ingestao-e-chunking.md
├── eval/
│   ├── test_questions.json        # 12 perguntas de avaliação
│   ├── evaluate.py                # avaliação da RAG
│   ├── compare_chunking.py        # comparação de configurações de chunk
│   └── results.md                 # relatório de avaliação com resultados
├── src/
│   ├── ingest.py                  # PDF/CSV -> SQLite
│   ├── chunking.py                # SQLite -> chunks
│   ├── embeddings.py              # chunks -> Chroma
│   ├── rag_chain.py               # recuperação, prompt e LLM
│   ├── app.py                     # interface Streamlit
│   ├── retriever.py
│   ├── storage.py
│   └── vectorstore.py
├── tests/
│   └── test_vectorstore_retriever.py
├── .env.example
├── CONTRIBUICOES.md
├── pyproject.toml
├── requirements.txt
├── README.md
└── uv.lock
```

Os diretórios `data/processed/` e `vectorstore/` são gerados localmente e não devem ser versionados.

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) instalado.
- [Ollama](https://ollama.com) instalado e acessível em `http://localhost:11434`.
- Git.

O projeto fixa Python 3.12 em `.python-version`; o `uv` cria e gerencia o ambiente virtual automaticamente.

## Setup

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/Borjelho/rag-clinico.git
cd rag-clinico
uv sync
```

### 2. Baixar o modelo local

```bash
ollama pull llama3.1
```

Se o serviço não estiver em execução, inicie-o em outro terminal:

```bash
ollama serve
```

### 3. Configurar o ambiente

```bash
cp .env.example .env
```

Valores padrão disponíveis em `.env`:

```dotenv
EMBEDDING_MODEL=intfloat/multilingual-e5-base
CHROMA_COLLECTION=acervo_clinico
LLM_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0
RETRIEVER_K=4
RETRIEVER_MAX_DISTANCE=0.45
```

`RETRIEVER_MAX_DISTANCE` é um limiar de distância cosseno: `0` representa vetores idênticos e valores menores são mais semelhantes. Ajuste-o apenas após avaliar o comportamento da recuperação.

## Preparar o Acervo

O acervo de entrada é lido exclusivamente de `data/raw/prontuario_sinteticos/`:

- PDFs em `bulas/` e `protocolos/`.
- CSVs em `prontuarios/`.

Execute as etapas na ordem abaixo:

```bash
uv run src/ingest.py
uv run src/chunking.py
uv run src/embeddings.py
```

> **Atenção:** essas etapas são reprocessamentos completos. A ingestão recria `data/processed/documents.db`; o chunking apaga e recria a tabela de chunks; os embeddings recriam a coleção Chroma. Faça backup dos artefatos locais caso precise preservá-los.

Na primeira execução, o modelo de embeddings pode ser baixado e armazenado no cache local.

## Usar a RAG

### Interface web

```bash
uv run streamlit run src/app.py
```

A interface fica disponível em `http://localhost:8501` e exibe os trechos recuperados e suas fontes.

### Linha de comando

```bash
uv run src/rag_chain.py --pergunta "Qual a meia-vida de eliminação do clonazepam?"
```

Para inspecionar a recuperação vetorial sem reindexar:

```bash
uv run src/embeddings.py --busca "qual a dose máxima diária de dipirona?"
```

## Avaliação

O gabarito em `eval/test_questions.json` contém 12 perguntas: 10 baseadas no acervo e 2 controles negativos, que devem ser recusados. A avaliação pontua fidelidade e relevância de 0 a 5 com um LLM local via Ollama; se ele falhar, usa uma heurística simples de fallback.

Após preparar o acervo e iniciar o Ollama, execute:

```bash
uv run eval/evaluate.py --config baseline
```

O histórico é salvo em `eval/results.json`. O relatório final da avaliação, com as médias de fidelidade e relevância, os casos insatisfatórios e a comparação entre configurações de chunk, está em `eval/results.md`.

Para comparar configurações de chunk (reprocessa e reavalia cada uma):

```bash
uv run eval/compare_chunking.py
```

Para validar o fluxo de avaliação sem a RAG ou o Ollama:

```bash
uv run eval/evaluate.py --mock
```

## Acervo Incluído

O repositório contém, no estado atual:

- Bulas profissionais de clonazepam, dipirona monoidratada e Ozempic.
- Protocolos sobre doença de Wilson e câncer de pulmão.
- CSVs sintéticos de pacientes, alergias e medicamentos.

Ao adicionar fontes, preserve o layout de diretórios de `data/raw/prontuario_sinteticos/`, registre a origem e os termos de uso, e confirme que não há dados pessoais reais.

## Fontes de Dados e Licenças

O acervo clínico é composto exclusivamente por documentos públicos e prontuários
sintéticos, em conformidade com a LGPD (nenhum dado real de paciente é utilizado).
Todas as fontes permitem perguntas com resposta verificável, pois trazem
informações objetivas (posologia, contraindicações, critérios diagnósticos).

| Fonte | Tipo | Origem | Licença / Termos |
| ----- | ---- | ------ | ---------------- |
| Bulas de medicamentos | PDF | Bulário Eletrônico da ANVISA (consultas.anvisa.gov.br) | Documentos públicos e gratuitos |
| Protocolos e diretrizes clínicas | PDF | PCDT / Diretrizes do Ministério da Saúde (gov.br/saude) e CONITEC | Documentos públicos de acesso livre |
| Prontuários sintéticos | CSV | Synthea (synthetichealth.github.io/synthea) | Apache License 2.0 — dados fictícios, sem restrição de privacidade |

**Por que o acervo permite respostas verificáveis:** bulas e protocolos são
documentos normativos com informação factual e estável (doses, exames,
contraindicações), o que torna possível montar um gabarito com resposta esperada
e trecho-fonte. Os prontuários do Synthea são "realistas, porém não reais",
gerados artificialmente, e por isso não incorrem em questões de privacidade
(LGPD), servindo para simular consultas a registros de pacientes.

## Colaboração

- Use `uv add <pacote>` somente ao alterar dependências e versione o `uv.lock` resultante.
- Após atualizar a branch, execute `uv sync` para sincronizar o ambiente.
- O registro de entregas e reflexões individuais está em [CONTRIBUICOES.md](./CONTRIBUICOES.md).
