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
| Joao Vitor Moreira Lemos    | RAG chain e interface  | Avaliação e Otimização | RAG chain (LCEL) + Streamlit; fix no compare_chunking.py | `3b21726`, `9199e17`, `<hash pós-rotação>` |
| Lucas Lima Dantas           | Ingestão e Chunking    | Embeddings          | Ingestão e chunking    | `PR #1`, `PR #2`        |
| Rafael de Almeida Maurina   | Embeddings             | VectorDB e Retriever| Embeddings + Chroma; busca com score | `6035263`, `520e224`, `e9a2869`, `1a1e5ed`, `26bcc37` |

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

| Área | O que foi feito | Arquivos relacionados |
| ---- | --------------- | --------------------- |
| RAG chain (pré-rotação) | Retriever + prompt + LLM via LangChain (LCEL). Dupla camada de recusa: (1) distância cosseno do melhor chunk acima de `RETRIEVER_MAX_DISTANCE` recusa antes de chamar o LLM; (2) o próprio prompt instrui o modelo a recusar se o contexto não contiver a resposta, cada resposta cita a fonte (documento + página, ou tabela + paciente). | `src/rag_chain.py`, `src/prompts.py` |
| Interface Streamlit (pré-rotação) | Chat com historico de sessão, expanders mostrando fontes citadas e trechos recuperados, tratamento de erro para Ollama fora do ar ou base vetorial não populada. | `src/app.py` |
| Avaliação e Otimização (pós-rotação) | Encontrei e corrigi um bug em `compare_chunking.py`: `reprocess_pipeline()` era um no-op, então as 3 configurações de chunk eram avaliadas sobre a mesma base vetorial, gerando resultados idênticos por construção. Corrigi para re-chunkar de verdade (`chunking.chunk_all()`), reindexar o Chroma (`embeddings.run_indexing()`) e invalidar o cache do `rag_chain` entre configs. Confirmei rodando o pipeline (sem LLM) que a contagem de chunks de PDF agora varia genuinamente entre configs (536 -> 945 -> 371). | `eval/compare_chunking.py`, `eval/results.md` |

### Commits/PRs principais

| Referência | Descrição |
| ---------- | --------- |
| `3b21726` | Implementa funcionalidade de RAG chain |
| `9199e17` | Ajuste na RAG chain |
| `<hash pós-rotação>` | Fix em `reprocess_pipeline()` (compare_chunking.py) + atualização de `eval/results.md` |

### Reflexão individual

Minha contribuição inicial foi a RAG chain e a interface Streamlit: montei o retriever, o prompt e a chamada ao LLM via LCEL, com uma dupla camada de recusa (distância de similaridade e instrução no próprio prompt) para que o sistema não inventasse resposta fora do acervo — que é exatamente a competência de "construir" pedida no desafio. Depois da rotação, fui para Avaliação e Otimização, e a primeira coisa que fiz foi validar o que já existia antes de rodar qualquer coisa: percebi que `compare_chunking.py` reavaliava a mesma base vetorial três vezes, porque `reprocess_pipeline()` nunca reprocessava de fato. Corrigi isso para re-chunkar, reindexar e invalidar o cache do `rag_chain` entre configurações, e confirmei rodando o pipeline (chunking real, sem LLM) que a contagem de chunks de PDF passou a variar de verdade entre as configs (536 na baseline, 945 na config menor, 371 na maior) — antes do fix, as três rodavam sobre os mesmos 536.

O caso técnico mais insatisfatório que encontrei foi descobrir que a nossa avaliação de otimização de chunking estava gerando um 'falso positivo'. Como o colega Bryan notou inicialmente, testar diferentes tamanhos de chunk parecia não alterar os resultados das respostas. Ao investigar a fundo o script compare_chunking.py, diagnostiquei que a função reprocess_pipeline() era um no-op — ou seja, ela não estava reprocessando a base de fato, fazendo com que todas as avaliações rodassem sobre a mesma base vetorial e gerassem resultados idênticos por construção.

Após corrigir o fluxo para garantir que a reindexação e a invalidação de cache ocorressem de verdade entre as configurações, comprovei a mudança na volumetria física dos dados: a configuração Baseline gerou 536 chunks de PDF, enquanto a configuração menor foi para 945 chunks e a maior para 371 chunks.

O que eu faria diferente com mais tempo: meu maior receio na primeira metade foi o acoplamento com o trabalho do Rafael (embeddings) e do Alex (retriever), que ainda não tinham sido mesclados quando escrevi a RAG chain, resolvi isso escrevendo contra o contrato que a Bryan já tinha definido em `evaluate.py` (`answer(pergunta) -> {"resposta", "contextos", "fontes"}`), o que fez a integração posterior ser quase sem atrito. Na segunda metade, com mais tempo eu teria rodado a comparação de chunking completa (com Ollama) antes de escrever o relatório final, em vez de documentar a correção do bug com a evidencia parcial que consegui reuni sem o LLM. Para decidir se a RAG está boa o suficiente para um contexto clínico, meu critério seria: recusa correta em praticamente 100% dos controles negativos (Q11/Q12), fidelidade média alta nas perguntas ancoradas no acervo, e nenhuma falha sistematica de recuperação numa categoria inteira (como a suspeita de que a dipirona não aparece por causa do desbalanceamento do acervo) esse último ponto, se confirmado, eu consideraria bloqueante para uso real, mesmo com boa fidelidade média geral.

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

| Área                 | O que foi feito                                                                                                             | Arquivos relacionados                                     |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Embeddings           | Converte os chunks do SQLite em vetores com modelo multilíngue (compatível com PT-BR) e popula a base vetorial local Chroma   | `src/embeddings.py`, `docs/embeddings.md`                  |
| VectorDB e Retriever | Alinha o nome da coleção via `.env`, corrige a métrica de distância (cosseno) e adiciona a busca por similaridade com score   | `src/vectorstore.py`, `src/retriever.py`                   |

### Commits/PRs principais

| Referência           | Descrição                                        |
| -------------------- | ------------------------------------------------ |
| `6035263`, `520e224` | Embeddings e indexação dos chunks no Chroma      |
| `e9a2869`, `c669918` | Busca de verificação `--busca` e documentação    |
| `1a1e5ed`, `26bcc37` | Integração do vectorstore/retriever no fluxo     |

### Reflexão individual

Minha contribuição foi a parte de embeddings e retriever. Na etapa de embeddings, fiz a transformação dos chunks em vetores e armazenamento no Chroma. Uma dificuldade que tive foi entender as exigências do modelo escolhido, como os prefixos que a família e5 usa para diferenciar documento de pergunta. Depois da rotação, na parte de vectorstore e retriever, fiz o alinhamento do nome da coleção entre os módulos e adicionei a busca com score que o rag_chain usa para recusar perguntas fora da base de conhecimento.

O caso mais insatisfatório nos testes que encontrei foi na pergunta sobre alergia a penicilina, onde o protocolo da doença de Wilson apareceu entre os melhores resultados (distancia 0.1248, quase empatado com o certo, 0.1239) porque cita muitas vezes a penicilamina. Esse caso demonstra na prática que a similaridade semântica por si não garante contexto correto, o que reforça a necessidade da resposta citar a fonte, ainda mais em contexto clínico. Com mais tempo, eu dedicaria a uma maneira de otimizar a indexação para baratear os experimentos de teste, pois reindexar tudo custava praticamente uma hora por vez. 
Por fim, para decidir se a RAG está boa o suficiente para um contexto clínico, eu usaria três critérios: recusar corretamente todas as perguntas fora do acervo, já que em saúde inventar uma resposta é a falha mais grave; ver se a fidelidade média está alta nas perguntas do gabarito; e não ter nenhuma alucinação nas perguntas de dose e posologia, onde um erro pode ser letal para um paciente.
