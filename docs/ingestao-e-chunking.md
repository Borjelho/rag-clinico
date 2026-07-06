# Ingestão e Chunking

Este documento explica as duas primeiras etapas do pipeline RAG do projeto:

```text
Arquivos brutos -> ingest.py -> SQLite -> chunking.py -> tabela chunks -> embeddings.py
```

A ideia é deixar claro o que já está pronto e o que o próximo módulo, `embeddings.py`, deve consumir.

## 1. Ingestão

A ingestão é a etapa que lê os arquivos originais e salva o conteúdo extraído em um banco SQLite local.

O script responsável é:

```bash
uv run src/ingest.py
```

Ele lê os arquivos em:

```text
data/raw/prontuario_sinteticos/
```

Hoje o projeto ingere dois tipos de fonte:

- PDFs em `bulas/` e `protocolos/`.
- CSVs em `prontuarios/`.

O banco gerado fica em:

```text
data/processed/documents.db
```

Importante: ao rodar `src/ingest.py`, o banco é recriado do zero.

## 2. O Que A Ingestão Salva

A ingestão cria e preenche algumas tabelas principais.

### `sources`

Guarda um registro para cada arquivo ingerido.

Campos importantes:

- `id`: identificador interno da fonte.
- `path`: caminho do arquivo original.
- `name`: nome do arquivo.
- `source_type`: tipo da fonte, por exemplo `pdf` ou `csv`.
- `category`: categoria simples, por exemplo `bula`, `protocolo`, `patients`, `allergies`, `medications`.

### `pdf_pages`

Guarda o texto extraído de cada página de PDF.

Campos importantes:

- `source_id`: referência para `sources.id`.
- `page_number`: número da página.
- `text`: texto extraído da página.

### `csv_rows`

Guarda cada linha dos CSVs já convertida para texto.

Campos importantes:

- `source_id`: referência para `sources.id`.
- `table_name`: nome do CSV sem extensão, por exemplo `patients`.
- `row_number`: número da linha no arquivo original.
- `patient_id`: identificador do paciente, quando existir.
- `patient_name`: nome do paciente, preenchido a partir da tabela `patients`.
- `content_json`: linha original normalizada em JSON.
- `content_text`: texto pronto para ser usado no RAG.

## 3. Chunking

O script responsável é:

```bash
uv run src/chunking.py
```

Ele lê o banco criado pela ingestão e salva os chunks no mesmo SQLite.

## 4. Como O Chunking Funciona

### PDFs

Para PDFs, o script lê `pdf_pages`, quebra o texto de cada página usando `RecursiveCharacterTextSplitter` e salva cada pedaço como um chunk.

Configuração atual:

```python
PDF_CHUNK_SIZE = 1000
PDF_CHUNK_OVERLAP = 150
```

Cada chunk de PDF inclui no texto informações como documento e página.

Exemplo simplificado:

```text
Documento: bula_ozempic_profissional.pdf
Pagina: 3

Texto extraído da página...
```

### CSVs

Para CSVs, o script lê `csv_rows` e agrupa linhas por paciente quando existe `patient_id`.

Isso permite juntar, por exemplo, várias medicações do mesmo paciente em um chunk, respeitando um limite de tamanho.

Configuração atual:

```python
CSV_MAX_CHARS = 1800
```

Cada chunk de CSV inclui no texto informações como fonte, tabela, paciente e linhas originais.

Exemplo simplificado:

```text
Fonte: medications.csv
Tabela: medications
Paciente: Maria Silva
ID do paciente: abc-123
Linhas: 10-15

Paciente abc-123 recebeu medicamento...
```

## 5. Tabela `chunks`

A saída principal do chunking é a tabela `chunks`.

Essa é a tabela mais importante para a próxima etapa, `embeddings.py`.

Campos principais:

- `id`: identificador do chunk.
- `source_id`: referência para o arquivo original em `sources`.
- `chunk_index`: posição do chunk dentro daquela fonte.
- `content`: texto que deve ser enviado para o modelo de embeddings.
- `content_sha256`: hash do conteúdo, útil para conferência/debug.
- `metadata_json`: metadados do chunk em JSON.
- `page_start` e `page_end`: páginas de origem, quando for PDF.
- `table_name`: tabela CSV de origem, quando for CSV.
- `patient_id` e `patient_name`: paciente associado, quando existir.
- `row_start`, `row_end` e `row_numbers_json`: linhas CSV usadas no chunk.

## 6. Metadados

O campo `metadata_json` existe para facilitar a etapa de embeddings e busca vetorial.

Ele contém informações úteis para filtros, rastreabilidade e citação da fonte.

Exemplo de metadados para PDF:

```json
{
  "source_id": 1,
  "source_type": "pdf",
  "category": "bula",
  "document_name": "bula_ozempic_profissional.pdf",
  "page_start": 3,
  "page_end": 3
}
```

Exemplo de metadados para CSV:

```json
{
  "source_id": 5,
  "source_type": "csv",
  "category": "medications",
  "document_name": "medications.csv",
  "table_name": "medications",
  "patient_id": "abc-123",
  "patient_name": "Maria Silva",
  "row_start": 10,
  "row_end": 15,
  "row_numbers": [10, 11, 12, 13, 14, 15]
}
```

## 7. Como O `embeddings.py` Deve Continuar

O próximo passo é implementar `src/embeddings.py` lendo a tabela `chunks`.

O caminho esperado é:

1. Abrir o banco `data/processed/documents.db`.
2. Buscar os chunks na tabela `chunks`.
3. Para cada chunk, usar `content` como texto de entrada do modelo de embeddings.
4. Usar `metadata_json` como metadados do documento no Chroma.
5. Salvar também algum identificador estável, como `chunk.id` ou uma combinação de `source_id` e `chunk_index`.

Consulta base sugerida:

```sql
SELECT
    id,
    source_id,
    chunk_index,
    content,
    metadata_json
FROM chunks
ORDER BY source_id, chunk_index;
```

Em Python, a ideia geral seria:

```python
import json

rows = conn.execute("""
    SELECT id, content, metadata_json
    FROM chunks
    ORDER BY source_id, chunk_index
""").fetchall()

texts = [row["content"] for row in rows]
metadatas = [json.loads(row["metadata_json"]) for row in rows]
ids = [str(row["id"]) for row in rows]
```

Depois disso, `texts`, `metadatas` e `ids` podem ser enviados para o Chroma.
