# Contribuições Individuais

### TODO

No final do projeto cada membro deve preencher sua propria `Reflexão individual`, sugestão de como responder:

1. Qual parte construiu/avaliou e como isso demonstra as competências de construir e avaliar uma RAG.
2. Qual foi o caso mais insatisfatório encontrado.
3. O que a otimização de chunking mudou, com números da avaliação.
4. O que faria diferente com mais tempo.
5. Como decidiria se a RAG está boa o suficiente para um contexto clínico.

## Resumo das Contribuições

| Pessoa                      | Frente inicial      | Frente após rotação | Principais entregas | Commits/PRs             |
| --------------------------- | ------------------- | ------------------- | ------------------- | ----------------------- |
| Alex Yure Fernandes Moreira | TBD                 | TBD                 | TBD                 | `hash`, `hash` ou `#PR` |
| Bryan Fernando Serafim      | TBD                 | TBD                 | TBD                 | `hash`, `hash` ou `#PR` |
| Joao Vitor Moreira Lemos    | TBD                 | TBD                 | TBD                 | `hash`, `hash` ou `#PR` |
| Lucas Lima Dantas           | Ingestão e Chunking | Embeddings          | Ingestão e chunking | `PR #1`, `PR #2`        |
| Rafael de Almeida Maurina   | TBD                 | TBD                 | TBD                 | `hash`, `hash` ou `#PR` |

---

## Alex Yure Fernandes Moreira

### Contribuições

| Área                             | O que foi feito | Arquivos relacionados          |
| -------------------------------- | --------------- | ------------------------------ |
| Exemplo: Ingestão e persistência | TBD             | Exemplo: `src/...`, `data/...` |

### Commits/PRs principais

| Referência      | Descrição |
| --------------- | --------- |
| `hash` ou `#PR` | TBD       |

### Reflexão individual

TBD

---

## Bryan Fernando Serafim

### Contribuições

| Área                             | O que foi feito | Arquivos relacionados          |
| -------------------------------- | --------------- | ------------------------------ |
| Exemplo: Ingestão e persistência | TBD             | Exemplo: `src/...`, `data/...` |

### Commits/PRs principais

| Referência      | Descrição |
| --------------- | --------- |
| `hash` ou `#PR` | TBD       |

### Reflexão individual

TBD

---

## Joao Vitor Moreira Lemos

### Contribuições

| Área                             | O que foi feito | Arquivos relacionados          |
| -------------------------------- | --------------- | ------------------------------ |
| Exemplo: Ingestão e persistência | TBD             | Exemplo: `src/...`, `data/...` |

### Commits/PRs principais

| Referência      | Descrição |
| --------------- | --------- |
| `hash` ou `#PR` | TBD       |

### Reflexão individual

TBD

---

## Lucas Lima Dantas

### Contribuições

| Área                    | O que foi feito                                                                                                       | Arquivos relacionados              |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Ingestão e persistência | Ingestão de documentos clinicos nos formatos pdf e csv, persistidos localmente em um banco de dados relacional SQLite | `src/storage.py` e `src/ingest.py` |
| Chunking                | Consome o banco relacional local e cria as chunks com seus perspectivos metadados                                     | `chunking.py`                      |

### Commits/PRs principais

| Referência | Descrição                       |
| ---------- | ------------------------------- |
| `PR #1`    | Feature/ingestao e persistencia |
| `PR #2`    | Feature/chunking                |

### Reflexão individual

Minha contribuição foi a parte de ingestão e chunking inicial. Trabalhei para ler os PDFs e CSVs, normalizar os conteúdos e organizar tudo no banco de dados para as próximas etapas da RAG. A maior dificuldade foi lidar com os prontuários em CSV, porque eles têm uma estrutura diferente dos PDFs. Foi necessário transformar os registros em texto e agrupá-los por paciente para evitar que informações relacionadas ficassem separadas.
Não participei diretamente da avaliação e da otimização de chunking, então não seria justo apresentar números como se fossem resultados do meu trabalho. Com mais tempo, eu melhoraria o tratamento de PDFs com formatos mais complexos e criaria mais testes para diferentes formatos de CSV. Para considerar a RAG adequada em um contexto clínico, eu verificaria se as respostas são baseadas nas fontes recuperadas, se as perguntas fora do acervo são recusadas e se não há mistura de informações entre pacientes.

## Rafael de Almeida Maurina

### Contribuições

| Área                             | O que foi feito | Arquivos relacionados          |
| -------------------------------- | --------------- | ------------------------------ |
| Exemplo: Ingestão e persistência | TBD             | Exemplo: `src/...`, `data/...` |

### Commits/PRs principais

| Referência      | Descrição |
| --------------- | --------- |
| `hash` ou `#PR` | TBD       |

### Reflexão individual

TBD
