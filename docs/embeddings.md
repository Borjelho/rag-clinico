# Embeddings e Base Vetorial

Este documento explica a terceira etapa do pipeline RAG do projeto:

```text
tabela chunks -> embeddings.py -> Chroma (vectorstore/) -> rag_chain.py
```

A ideia é deixar claro como os chunks viram vetores e o que o próximo módulo, `rag_chain.py`, deve consumir.

## 1. Embeddings

A etapa de embeddings lê os chunks gerados pelo chunking e converte cada um em um vetor numérico, salvo em uma base vetorial local (Chroma).

O script responsável é:

```bash
uv run src/embeddings.py
```

Ele lê a tabela `chunks` do banco:

```text
data/processed/documents.db
```

A base vetorial gerada fica em:

```text
vectorstore/
```

Importante: ao rodar `src/embeddings.py`, a coleção do Chroma é recriada do zero (mesmo comportamento do chunking com a tabela `chunks`).

## 2. Modelo De Embedding

O modelo padrão é o `intfloat/multilingual-e5-base`, escolhido por ser multilíngue e treinado para busca (retrieval), com bom desempenho em português.

Configuração atual (via `.env`, com estes valores padrão):

```text
EMBEDDING_MODEL=intfloat/multilingual-e5-base
CHROMA_COLLECTION=acervo_clinico
```

Na primeira execução, o modelo é baixado automaticamente (~1.1 GB) e fica em cache local. Depois disso, tudo roda offline.

Se a máquina for mais fraca, dá para trocar no `.env` por `intfloat/multilingual-e5-small`. Ao trocar de modelo, é preciso reindexar, porque vetores de modelos diferentes não são compatíveis entre si.

### O detalhe dos prefixos

Os modelos da família e5 foram treinados com prefixos: os documentos são indexados como `passage: <texto>` e as perguntas são buscadas como `query: <texto>`. O script cuida disso automaticamente — quem usa a base vetorial não precisa se preocupar com isso.

## 3. Como A Indexação Funciona

Para cada chunk da tabela `chunks`:

1. O campo `content` vira o texto de entrada do modelo de embeddings.
2. O campo `metadata_json` vira os metadados do documento no Chroma, filtrando valores que o Chroma não aceita (listas como `row_numbers` e valores nulos).
3. O identificador do vetor é a combinação `source_id-chunk_index`, que é única e estável: reindexar gera sempre os mesmos IDs.

Os metadados guardam também `chunk_db_id`, que aponta de volta para a linha original na tabela `chunks`, caso seja preciso consultar os campos completos.

A busca usa distância de cosseno: quanto menor a distância, mais parecido o chunk é da pergunta.

## 4. Busca De Verificação

O script também funciona como ferramenta de inspeção da base vetorial, sem reindexar:

```bash
uv run src/embeddings.py --busca "qual a dose maxima diaria de dipirona?"
```

Exemplo simplificado de saída:

```text
[1] distancia=0.0924 | bula_dipirona_monoidratada_profissional.pdf
Documento: bula_dipirona_monoidratada_profissional.pdf
Pagina: 7

A dose maxima diaria...
```

Isso é útil na avaliação: quando uma resposta da RAG for ruim, a busca mostra se o problema está na recuperação (chunks errados voltando) ou na geração (chunks certos, resposta ruim).

## 5. Como O `rag_chain.py` Deve Continuar

O próximo passo é implementar `src/rag_chain.py` consumindo a base vetorial pronta.

O caminho esperado é:

```python
from embeddings import get_vectorstore

retriever = get_vectorstore().as_retriever(search_kwargs={"k": 4})
```

O `get_vectorstore()` já devolve um `Chroma` do LangChain configurado com o modelo de embedding certo, a coleção certa e a distância de cosseno. O retriever aplica o prefixo de busca do e5 automaticamente.

Os metadados de cada documento recuperado incluem `document_name`, `category`, `page_start`, `patient_name`, etc. — são eles que a chain deve usar para citar a fonte na resposta.

Atenção para a interface (Streamlit): o `get_vectorstore()` carrega o modelo de embedding na memória (alguns segundos). Como o Streamlit reexecuta o script a cada interação, o `app.py` deve envolver essa chamada em `@st.cache_resource` para não recarregar o modelo a cada pergunta.
