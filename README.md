# rag-clinico — Assistente Clínico de Consulta a Documentos

Assistente de perguntas e respostas que consulta um acervo clínico (protocolos, diretrizes, bulas e prontuários sintéticos) usando RAG (Retrieval-Augmented Generation) rodando **100% localmente**. Toda resposta é fundamentada no acervo ingerido e cita o documento-fonte; perguntas fora do escopo são recusadas.

## Visão Geral da Arquitetura

```
Acervo clínico → Ingestão → Persistência local (SQLite)
→ Chunking → Embeddings → Base vetorial local (Chroma)
→ Retriever → Pipeline RAG (LangChain) → LLM (Ollama)
→ Interface (Streamlit) → Avaliação (fidelidade + relevância)
→ Otimização de chunks
```

## Stack

| Camada             | Tecnologia                                                 |
| ------------------ | ---------------------------------------------------------- |
| Linguagem          | Python 3.12                                                |
| Leitura de PDF     | pypdf / pdfplumber                                         |
| Persistência local | SQLite                                                     |
| Chunking           | LangChain Text Splitters (recursivo, semântico)            |
| Embeddings         | sentence-transformers (multilingual, compatível com PT-BR) |
| Base vetorial      | Chroma                                                     |
| LLM                | Ollama (modelo local)                                      |
| Orquestração       | LangChain (LCEL)                                           |
| Interface          | Streamlit                                                  |
| Avaliação          | RAGAS (faithfulness / relevância) + LLM-as-judge           |

## Estrutura de Pastas

```
rag-clinico/
├── data/
│   ├── raw/                    # PDFs originais (protocolos, bulas, prontuários sintéticos)
│   │   ├── protocolos/
│   │   ├── bulas/
│   │   └── prontuarios/
│   └── processed/              # texto extraído/normalizado (não versionado)
│
├── vectorstore/                # base Chroma persistida localmente (não versionado)
│
├── src/
│   ├── __init__.py
│   ├── ingest.py                # lê PDFs/CSV, extrai texto, salva em SQLite
│   ├── chunking.py              # gera chunks com metadados e salva no SQLite
│   ├── embeddings.py             # gera vetores, popula o Chroma
│   ├── rag_chain.py              # retriever + prompt + LLM (LCEL)
│   ├── prompts.py                # templates de prompt
│   └── app.py                    # interface Streamlit
│
├── eval/
│   ├── test_questions.json       # gabarito: 8-12 perguntas + resposta esperada + trecho-fonte
│   ├── evaluate.py                # roda avaliação de fidelidade/relevância
│   ├── compare_chunking.py        # compara configurações de chunk
│   └── results.md                 # relatório final de avaliação
│
├── notebooks/                     # exploração rápida (opcional)
│   └── exploracao.ipynb
│
├── tests/                          # testes unitários (opcional)
│   └── test_chunking.py
│
├── CONTRIBUICOES.md
├── .env.example
├── .gitignore
├── README.md
├── pyproject.toml
└── uv.lock
```

## Setup

### Pré-requisitos

- [uv](https://docs.astral.sh/uv/) instalado ([instruções de instalação](https://docs.astral.sh/uv/getting-started/installation/))
- [Ollama](https://ollama.com) instalado e rodando localmente
- Git

> Não precisa ter Python pré-instalado — o `uv` gerencia a versão do Python automaticamente a partir do `.python-version` do projeto.

### 1. Clonar o repositório

```bash
git clone https://github.com/Borjelho/rag-clinico.git
cd rag-clinico
```

### 2. Instalar as dependências

```bash
uv sync
```

Isso cria o ambiente virtual (`.venv/`) automaticamente e instala todas as dependências com as versões exatas travadas no `uv.lock` — não é necessário criar/ativar venv manualmente.

### 3. Configurar identidade do Git (uma vez por pessoa)

```bash
git config user.name "Nome Sobrenome"
git config user.email "email@dominio.com"
```

### 4. Baixar o modelo LLM local via Ollama

```bash
ollama pull <TBD>
```

### 5. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite o .env se necessário (ex.: nome do modelo, path do vectorstore)
```

### 6. Rodar a ingestão do acervo

```bash
uv run src/ingest.py
```

### 7. Gerar chunks

```bash
uv run src/chunking.py
```

O chunking lê o banco `data/processed/documents.db`, quebra PDFs e CSVs em trechos menores e salva os chunks com metadados no próprio SQLite.

### 8. Gerar embeddings e popular a base vetorial

```bash
uv run src/embeddings.py
```

### 9. Rodar a interface

```bash
uv run streamlit run src/app.py
```

A aplicação estará disponível em `http://localhost:8501`.

### Adicionando novas dependências

Combine com a squad antes de rodar isso — só quem está mexendo em dependências deve atualizar o lockfile, pra evitar conflito de merge:

```bash
uv add <nome-do-pacote>
```

Depois de qualquer atualização de dependências, os demais integrantes devem rodar:

```bash
git pull
uv sync
```

## Avaliação

Para rodar a avaliação de fidelidade e relevância sobre o conjunto de teste:

```bash
uv run eval/evaluate.py
```

Os resultados são registrados em `eval/results.md`, incluindo:

- Tabela de fidelidade/relevância por pergunta
- Casos insatisfatórios identificados e causa provável
- Comparação entre configurações de chunking testadas

## Fontes de Dados

Documente aqui as fontes públicas utilizadas (protocolo/diretriz, bula, gerador de prontuários sintéticos), com link e licença/termos de uso de cada uma.

> ⚠️ **Nunca utilizar dados reais de pacientes.** Apenas documentos públicos e prontuários sintéticos (ex.: gerados via Synthea).

## Trabalho em Equipe

- Cada integrante commita com nome/e-mail próprios (`git config user.name` / `user.email`).
- Papéis e liderança são rotativos — ver `CONTRIBUICOES.md` para o registro de quem fez o quê.
- Contribuições individuais e reflexões estão documentadas em [CONTRIBUICOES.md](./CONTRIBUICOES.md).
