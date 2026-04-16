# Sprint 28 -- LLM Orquestrado (Claude como Copiloto)

## Status: Pendente (proposta 2026-04-16)
Issue: #13

## Objetivo

Integrar inteligência de linguagem ao sistema de forma que (a) **Claude Code** (ou Opus via API) seja o LLM principal durante a fase de melhoria contínua, (b) o código mantenha hooks abstratos para trocar para LLM local no futuro, e (c) o LLM sempre trabalhe com **contratos estruturados** -- JSON schema, prompts versionados, evidências do grafo -- nunca com texto livre.

Decisão registrada pelo usuário: "vamos trocar pelo Claude Opus mesmo. Claude Code mesmo. A ideia é que com o Opus a gente sempre faça melhorias contínuas e consigamos depois chegar em definitivo na automação ideal."

Isso significa: **o LLM não é só uma função chamada pelo pipeline -- é o copiloto do desenvolvimento e da operação do sistema**.

---

## Três modos de uso do LLM

### Modo 1 -- Análise pontual em tempo de pipeline
Funções determinísticas dentro do pipeline que, quando heurísticas falham, delegam para o LLM e cacheiam a resposta. Exemplos:

- Classificar transação com `categoria_confianca < 0.5` (Sprint 27).
- Extrair cláusulas de contratos PDF (Sprint 26).
- Resolver ambiguidade de entidades (Motor 2 camada 4 da Sprint 27).
- Desambiguar linking de documentos com múltiplos candidatos.

### Modo 2 -- Consultas em linguagem natural (usuário pergunta)
Dashboard tem campo de texto livre onde o usuário pergunta:
- "Quanto gastei com farmácia em 2025?"
- "Quais assinaturas digitais eu pago mensalmente?"
- "Me mostra todos os gastos com o Rodrigo no último ano."

LLM traduz pergunta em query ao grafo (SQL ou API Python), executa, formata resposta em linguagem natural com números e links para as evidências.

### Modo 3 -- Operação assistida (usuário + Claude Code)
O próprio Claude Code é o operador:
- Revisa mensalmente o grafo e sugere limpezas ("você tem 5 assinaturas que não foram usadas em 90 dias").
- Propõe novas regras de categorização a partir de padrões recorrentes.
- Lê relatórios gerados pelo pipeline e escreve análises narrativas.
- Faz manutenção: detecta inconsistências no grafo, propõe merges de entidades duplicadas.

Esse modo 3 é operado via comandos (`/slash`) ou skills do Claude Code, não via código Python rodando sozinho.

---

## Princípios

1. **Contratos antes de prosa**: LLM recebe JSON estruturado (transação + contexto do grafo + exemplos) e devolve JSON validado via Pydantic. Nunca texto livre no meio do pipeline.
2. **Prompts versionados**: cada prompt mora em `src/llm/prompts/NOME.md`, committed, com changelog. Mudar prompt vira PR.
3. **Provider abstrato**: `LLMProvider` é interface. Implementações: `ClaudeAPIProvider` (agora), `LocalLLMProvider` (futuro), `ClaudeCodeOperatorProvider` (dev-time).
4. **Cache obrigatório**: resposta por (hash do prompt + hash do input) salva em SQLite. Custos e latência controlados.
5. **Evidência rastreável**: toda decisão do LLM grava no grafo a evidência usada (`source="llm"`, `evidence="prompt_v2 + contexto_3nos"`).
6. **Modo "dry run"** sempre disponível: roda o LLM, mostra o que faria, pede confirmação antes de gravar no grafo.

---

## Entregas

### 1. Infraestrutura do LLM

- [ ] `src/llm/provider.py` -- interface abstrata:
  ```python
  class LLMProvider(ABC):
      @abstractmethod
      def classificar(self, transacao: dict, contexto_grafo: dict) -> ClassificacaoResult: ...

      @abstractmethod
      def extrair_clausulas(self, texto_contrato: str) -> ContratoResult: ...

      @abstractmethod
      def responder_pergunta(self, pergunta: str, ferramentas: list) -> RespostaResult: ...

      @abstractmethod
      def sugerir_regras(self, padroes: list[dict]) -> list[RegraSugerida]: ...
  ```
- [ ] `src/llm/claude_api.py` -- implementação via `anthropic` SDK, modelo `claude-opus-4-7`, prompt caching habilitado.
- [ ] `src/llm/local.py` -- stub que levanta `NotImplementedError` com ponteiro pra Sprint 08.
- [ ] `src/llm/cache.py` -- cache SQLite (`data/output/llm_cache.sqlite`) com TTL configurável por tipo de chamada.
- [ ] `src/llm/cost_tracker.py` -- loga tokens in/out por chamada em `data/output/llm_custos.jsonl` pra monitorar gasto.

### 2. Contratos de entrada/saída (Pydantic)

- [ ] `src/llm/schemas.py` com modelos estritos para cada tipo de resposta:
  - `ClassificacaoResult` (`categoria`, `classificacao`, `tag_irpf`, `confianca`, `justificativa`)
  - `ContratoResult` (`partes`, `valor_mensal`, `data_inicio`, `data_fim`, `reajuste_indice`, `multa_rescisao`)
  - `RespostaNLResult` (`resposta_texto`, `consultas_executadas`, `evidencias`)
  - `RegraSugerida` (`regex_proposto`, `categoria`, `classificacao`, `exemplos_que_casariam`, `risco_falso_positivo`)
- [ ] Toda resposta LLM é parseada via Pydantic com retry (1 retry se JSON malformado, depois vira erro).

### 3. Prompts versionados

- [ ] `src/llm/prompts/classificar_transacao.md` -- input: JSON da transação + top 3 transações similares do grafo. Output: `ClassificacaoResult`.
- [ ] `src/llm/prompts/extrair_clausulas_contrato.md` -- input: texto OCR do contrato. Output: `ContratoResult`.
- [ ] `src/llm/prompts/responder_pergunta_financeira.md` -- input: pergunta + tool list (query grafo, query XLSX, buscar docs). Output: `RespostaNLResult`.
- [ ] `src/llm/prompts/sugerir_regra_categorizacao.md` -- input: N transações sem categoria + descrição comum. Output: `RegraSugerida`.
- [ ] `src/llm/prompts/desambiguar_linking.md` -- input: doc + K candidatos de transação. Output: `LinkingResolution`.
- [ ] `src/llm/prompts/resumo_mensal_narrativo.md` -- input: dados do mês. Output: texto de 2-3 parágrafos.

Cada prompt em Markdown com frontmatter:
```yaml
---
nome: classificar_transacao
versao: 1
modelo: claude-opus-4-7
cache_ttl_dias: 90
max_tokens: 1000
---

Você é um classificador financeiro para o Protocolo Ouroboros.
...
```

### 4. Integração com pipeline

- [ ] Em `src/transform/categorizer.py` (Sprint 27), quando `categoria_confianca < 0.5`, chamar `LLMProvider.classificar()` com contexto do grafo.
- [ ] Em `src/ingest/extractors/contrato_extractor.py` (Sprint 26), chamar `LLMProvider.extrair_clausulas()` para o texto OCR.
- [ ] Em `src/graph/entity_resolver.py` (Sprint 27), camada 4 = LLM.
- [ ] Em `src/graph/linker.py`, quando Motor 1 tem 2+ candidatos com score próximo, chamar `desambiguar_linking`.

### 5. Consulta em linguagem natural (Modo 2)

- [ ] `src/llm/nl_query.py` -- orquestra:
  1. Recebe pergunta do usuário.
  2. LLM escolhe ferramenta (`query_grafo_sql`, `query_extrato_mes`, `buscar_entidade`).
  3. Pipeline executa a ferramenta, passa resultado de volta ao LLM.
  4. LLM formata resposta com evidências.
- [ ] Usar **tool use** da API Anthropic, não prompt injection.
- [ ] Nova página no dashboard: `src/dashboard/paginas/perguntar.py` com caixa de texto + respostas acumuladas.

### 6. Operação assistida (Modo 3) -- skills Claude Code

- [ ] `.claude/commands/revisar_grafo.md` -- slash command que faz Claude ler `grafo.sqlite`, gerar relatório de inconsistências, propor limpezas.
- [ ] `.claude/commands/sugerir_regras.md` -- lê `sugestoes_categorizacao.md` (Sprint 27), escreve entradas prontas pra `categorias.yaml`.
- [ ] `.claude/commands/resumo_mensal.md` -- pega mês referência, gera análise narrativa em `data/output/relatorios/resumo_YYYY-MM.md`.
- [ ] `.claude/commands/auditar_irpf.md` -- checa se deduções têm CNPJ, documentos anexos; lista faltantes.
- [ ] `CLAUDE.md` atualizado com seção "Claude Code como copiloto do Ouroboros".

### 7. Resumos narrativos mensais

- [ ] Integrar ao `src/load/relatorio.py` (que hoje gera MD estático) uma chamada ao LLM que complementa com análise qualitativa.
- [ ] Feature-flag: `RESUMO_NARRATIVO=true` no `.env` (default: true se API key configurada).

### 8. Observabilidade e limites

- [ ] Gauge de custo em dólar por mês (modelo token price table).
- [ ] Alerta se LLM for chamado mais que N vezes num mesmo mês (default N=200).
- [ ] Todos os prompts com system message incluindo: "Nunca invente dados. Se não souber, retorne `confianca=0` e justificativa."
- [ ] Respeitar o `.env` `ANTHROPIC_API_KEY`. Se não existir, o sistema opera **sem LLM** com logs de "feature_ignorada=True".

---

## Arquivos novos/modificados

| Arquivo | Tipo |
|---------|------|
| `src/llm/*` | novo (módulo inteiro) |
| `src/llm/prompts/*.md` | novo |
| `src/dashboard/paginas/perguntar.py` | novo |
| `.claude/commands/*.md` | novo |
| `src/transform/categorizer.py` | editar (hook LLM) |
| `src/graph/*.py` | editar (hook LLM) |
| `src/load/relatorio.py` | editar (hook resumo) |
| `pyproject.toml` | `anthropic>=0.30` |
| `.env.example` | adicionar `ANTHROPIC_API_KEY` |
| `CLAUDE.md` | seção "Claude como copiloto" |

---

## Armadilhas

1. **Prompt drift**: mudar um prompt muda classificação histórica retroativamente se o cache for invalidado. Versionar com `versao` no frontmatter e nunca invalidar cache sem script de diff.
2. **Alucinação em classificação**: LLM pode inventar CNPJs ou valores. Sempre validar saída contra o input. Rejeitar se inventar.
3. **Custo**: Opus é caro. Ativar prompt caching, cache resposta-a-resposta, e usar Sonnet para tarefas volume alto + Opus só para casos complexos. Parametrizar modelo por tipo de chamada.
4. **Rate limit**: Anthropic tem RPM/TPM. Usar biblioteca com backoff exponencial.
5. **Segurança de dados**: dados financeiros vão pra servidor Anthropic. O usuário já autorizou via escolha. Documentar claramente. **Nunca enviar CPF completo ou números de conta plenos** -- mascarar antes de enviar.
6. **Tool use "hallucinations"**: LLM chama ferramenta com argumento inválido. Validar args antes de executar; se inválido, retorna erro para LLM tentar de novo.
7. **Contratos mudando**: novo campo em Pydantic quebra respostas cacheadas. Versionar schemas; resposta antiga incompatível invalida cache.
8. **`.claude/commands/` é privado do Claude Code**: não é executado automaticamente pelo pipeline Python. É gatilho manual do usuário.

---

## Critério de sucesso

1. Transação com `categoria_confianca < 0.5` após Sprint 27 é re-classificada via LLM com taxa de acerto ≥ 85% (validada em amostra manual de 50 casos).
2. Pergunta "quanto gastei com farmácia em 2025?" no dashboard retorna valor correto + link para transações específicas em menos de 10 segundos.
3. Slash command `/revisar_grafo` gera relatório acionável com pelo menos 3 sugestões por execução (ex.: merge de entidades duplicadas).
4. Resumo narrativo mensal passa em revisão qualitativa: sem alucinação, destaca padrões reais.
5. Custo médio mensal do LLM em produção fica abaixo de US$ 20 (ajustável conforme volume do usuário).
6. Sistema funciona 100% sem LLM (apenas sem esse adicional) se `ANTHROPIC_API_KEY` não estiver definida.
7. Cache reduz em 70%+ chamadas repetidas (validado em reprocessamento).

---

## Dependências

- **Sprint 26 e 28 devem estar entregues.** LLM trabalha sobre grafo e documentos.
- **Sprint 08 (LLM Local)** fica como *follow-up*: quando qualidade local for boa o suficiente, substitui `ClaudeAPIProvider` por `LocalLLMProvider` sem mudar o resto.

---

## Ordem interna recomendada

1. Infraestrutura (provider + cache + schemas).
2. Modo 1 (pipeline usa LLM em casos específicos).
3. Modo 2 (consulta em linguagem natural no dashboard).
4. Modo 3 (slash commands do Claude Code).
5. Observabilidade (custo, rate limit, alertas).

---

*"A inteligência não é saber a resposta. É saber qual pergunta fazer." -- adaptado de Claude Levi-Strauss*
