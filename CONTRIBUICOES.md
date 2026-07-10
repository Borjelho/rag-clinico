# Contribuições Individuais

### TODO

No final do projeto cada membro deve preencher sua propria `Reflexão individual`, sugestão de como responder:

1. Qual parte construiu/avaliou e como isso demonstra as competências de construir e avaliar uma RAG.
2. Qual foi o caso mais insatisfatório encontrado.
3. O que a otimização de chunking mudou, com números da avaliação.
4. O que faria diferente com mais tempo.
5. Como decidiria se a RAG está boa o suficiente para um contexto clínico.

## Resumo das Contribuições

| Pessoa                      | Frente inicial         | Frente após rotação | Principais entregas    | Commits/PRs             |
| --------------------------- | -------------------    | ------------------- | -------------------    | ----------------------- |
| Alex Yure Fernandes Moreira | VectorDB e Retriever   | Rag chain           | VectorDB e Retriever   | `165324d`, `9cc4f4e`    |
| Bryan Fernando Serafim      | Avaliação e Otimização | Ingestão e Chunking | Avaliação e Otimização | `ab3b26d`, `3f64e96`    |
| Joao Vitor Moreira Lemos    | TBD                    | TBD                 | TBD                    | `hash`, `hash` ou `#PR` |
| Lucas Lima Dantas           | Ingestão e Chunking    | Embeddings          | Ingestão e chunking    | `PR #1`, `PR #2`        |
| Rafael de Almeida Maurina   | TBD                    | TBD                 | TBD                    | `hash`, `hash` ou `#PR` |

---

## Alex Yure Fernandes Moreira

### Contribuições

| Área                             | O que foi feito                                                          | Arquivos relacionados|
| -------------------------------- | -------------------------------------------------------------------------|--------------------- |
| VectorDB                         |Implementação de uma base vetorial local em Chroma, incluindo carregamento|`src/vectorstore.py`  |
|                                  |dos chunks armazenados no SQLite, conversão para documentos do LangChain, |                      |
|                                  |normalização de metadados, geração de identificadores estáveis e          |                      |
|                                  |reconstrução da coleção em lotes.                                         |                      |
| -------------------------------- | ------------------------------------------------------------------------ | -------------------- |
| Retriever                        | Implementação de funções para abrir o retriever sobre a coleção Chroma e |`src/retriever.py`    |
|                                  |realizar buscas por similaridade.                                         |                      |
| -------------------------------- |------------------------------------------------------------------------- | -------------------- |
|Integração Rag_chain Retriever    |Integração do do rag_chain com o retriever do projeto, apenas substituindo|`src/rag_chain.py`    |
|                                  |o acesso direto ao `get_vectorstore` de `embeddings.py` e colocando os    |                      |
|                                  |componentes de vectorDB e retriever no fluxo da aplicação.                |                      |


### Commits/PRs principais

| Referência      | Descrição                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------ |
| `9cc4f4e`       | Adiciona VectorDB local com Crhoma, o retriever e um teste funcional dos componentes       |




### Reflexão individual

Durante o projeto, precisei dar uma revisada em como o RAG organiza os documentos para encontrar as informações e construir as respostas. Para isso, estudei como os trechos são transformados em representações que pudessem permitir a comparação dos seus significados, como a base vetorial armazena esse conteúdo e como o retriever seleciona os resultados mais próximos. 
Depois da rotação, tive que estudar melhor o funcionamento geral da aplicação pois o retriever que criei acabou ficando fora do fluxo, mas foi um problema fácil de corrigir alterando apenas poucas linhas para fazer o `rag_chain.py` apontar para o local correto.
Meu maior receio era não conseguir fazer bem a integração com os componentes dos outros membros, mas no final a boa documentação e a comunicação da equipe facilitaram bastante as soluções dos problemas.


---

## Bryan Fernando Serafim

### Contribuições

| Área | O que foi feito | Arquivos relacionados |
| ---- | --------------- | --------------------- |
| Avaliação | Conjunto de teste com 12 perguntas clínicas (10 ancoradas no acervo + 2 controles negativos para verificar recusa de perguntas fora do acervo) e motor de avaliação com LLM as a Judge, medindo fidelidade e relevância por pergunta. | `eval/test_questions.json`, `eval/evaluate.py` |
| Otimização de chunk | Script para comparar configurações de chunk sobre o mesmo gabarito, reprocessando o pipeline e reavaliando cada configuração. | `eval/compare_chunking.py` |
| Ingestão (pós-rotação) | Tratamento para ignorar páginas de PDF sem texto extraível, evitando chunks vazios na base vetorial. | `src/ingest.py` |
| Liderança / integração | Coordenação da sprint (dailies, workflow de Git, estratégia de branch develop) | — |

### Commits/PRs principais

| Referência | Descrição |
| ---------- | --------- |
| `ab3b26d` | Frente de avaliação: gabarito, motor (LLM as a Judge) e comparador de chunk |
| `3f64e96` | Ignora páginas de PDF sem texto extraível na ingestão |

### Reflexão individual

Construí a frente de avaliação e, na segunda metade, atuei na ingestão, o que me colocou dos dois lados das competências do desafio: avaliar e construir. O que mais me ensinou foi montar os controles negativos (perguntas fora do acervo), porque em saúde uma resposta inventada é grave, e sem esses casos não há como provar que a RAG recusa o que não sabe.

O caso mais insatisfatório que encontrei foi a recuperação das bulas, sobretudo a dipirona, que falhou em todas as perguntas (fidelidade e relevância 0): o retriever trazia prontuários em vez da bula. A causa é o desbalanceamento do acervo, cerca de 9.200 chunks de prontuário contra 540 de PDF, então os prontuários afogam as bulas na busca. Testar três configurações de chunk (1000/150, 512/64, 1500/200) deu resultados idênticos, o que confirmou o diagnóstico: o gargalo não é o tamanho do chunk, é o balanceamento do acervo.

Com mais tempo, atacaria a causa raiz: separar coleções por tipo de documento ou filtrar por tipo na recuperação. Sobre a RAG estar "boa o suficiente" para uso clínico, diria que ainda não, ela acerta protocolos e recusa o que está fora do acervo, mas a cobertura incompleta das bulas seria inaceitável num uso real. Meu critério para aprovar seria: nenhuma falha sistemática de recuperação por categoria clínica e recusa correta próxima de 100% nos casos fora do acervo.

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
