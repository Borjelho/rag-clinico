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
| Linguagem          | Python 3.11+                                               |
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
│   ├── ingest.py                # lê PDFs/CSV/FHIR, extrai texto, salva em data/processed
│   ├── chunking.py              # estratégias de split
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
└── requirements.txt
```

## Setup

### Pré-requisitos

- Python 3.11 ou superior
- [Ollama](https://ollama.com) instalado e rodando localmente
- Git

### 1. Clonar o repositório

```bash
git clone https://github.com/Borjelho/rag-clinico.git
cd rag-clinico
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Baixar o modelo LLM local via Ollama

```bash
ollama pull <A decidir>
```

### 5. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite o .env se necessário (ex.: nome do modelo, path do vectorstore)
```

### 6. Rodar a ingestão do acervo

```bash
python src/ingest.py
```

### 7. Gerar embeddings e popular a base vetorial

```bash
python src/embeddings.py
```

### 8. Rodar a interface

```bash
streamlit run src/app.py
```

A aplicação estará disponível em `http://localhost:8501`.

## Avaliação

Para rodar a avaliação de fidelidade e relevância sobre o conjunto de teste:

```bash
python eval/evaluate.py
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
