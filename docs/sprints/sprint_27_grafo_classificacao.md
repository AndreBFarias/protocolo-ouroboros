# Sprint 27 -- Grafo de Conhecimento + Classificação v2

## Status: Pendente (proposta 2026-04-16)
Issue: #12

## Objetivo

Construir o **cérebro relacional** do sistema: persistência em SQLite com nós e arestas tipadas que ligam transações, documentos, entidades, pessoas e períodos. Simultaneamente, refatorar o categorizador atual para operar com **contexto** e **score de confiança**, limpando a dívida técnica do `categorias.yaml`.

O grafo é o que permite consultas que hoje são impossíveis: "tudo relacionado à Neoenergia nos últimos 12 meses", "qual boleto corresponde a este pagamento", "esse empréstimo com o Rodrigo foi quitado?".

---

## Duas metades que se encaixam

### Metade A: Grafo de Conhecimento
Nós + arestas + motores de linking.

### Metade B: Classificação v2
Refactor do categorizador atual para alimentar o grafo com categorias de qualidade e score explícito.

Fazer junto pois são acoplados: a qualidade do grafo depende da qualidade da categorização, e a classificação v2 depende do grafo pra fazer inferência contextual (ex.: "Uber no dia de consulta médica").

---

## Modelo de dados

### Nós (tabela `nodes`)

| Tipo | Chave natural | Exemplos |
|------|---------------|----------|
| `Transacao` | hash(data+valor+conta+descricao) | cada linha do extrato |
| `Documento` | hash do arquivo + linha_digitavel/chave_nfe | PDFs, imagens (Sprint 26) |
| `Entidade` | slug canônico | `neoenergia`, `itau`, `dr-souza-clinica` |
| `Pessoa` | uuid interno | contrapartes privadas (hashadas) |
| `Conta` | bankid+branchid+acctid | Itau-0341-9110-4, NubankPF-0260-97737068-1 |
| `Cartao` | BIN + últimos 4 dígitos | C6-Elite-1234, Santander-Black-7342 |
| `Periodo` | YYYY-MM | 2026-03 (competência, não pagamento) |
| `Evento` | uuid interno | "emprestimo-rodrigo-2025", "mudanca-2024-03" |
| `Categoria` | nome | Energia, Saúde, Aluguel |
| `Assinatura` | (entidade, mes_inicio) | Netflix-2024-01 |

### Arestas (tabela `edges`)

| Verbo | Domínio → Contradomínio | Confiança típica |
|-------|-------------------------|------------------|
| `paga` | `Transacao` → `Documento` | 0.9 se valor+data OK |
| `emitido_por` | `Documento` → `Entidade` | 1.0 (extração) |
| `referente_a` | `Documento` → `Periodo` | 1.0 |
| `categoria` | `Transacao` → `Categoria` | 0.7-1.0 |
| `contraparte` | `Transacao` → `Entidade`/`Pessoa` | 0.8-1.0 |
| `origem` | `Transacao` → `Conta`/`Cartao` | 1.0 |
| `parte_de` | `Transacao` → `Evento` | 0.6-0.9 |
| `reembolsa` | `Transacao` → `Transacao` | 0.7 |
| `transferencia_par` | `Transacao` → `Transacao` | 1.0 (já existe) |
| `dedutivel_em` | `Transacao` → `AnoFiscal` | 0.5-1.0 |
| `instancia_de` | `Transacao` → `Assinatura` | 0.8 |
| `substitui` | Entidade → Entidade | 1.0 (ex.: CEB virou Neoenergia) |

### Schema SQL

```sql
CREATE TABLE nodes (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  attrs JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_nodes_type ON nodes(type);

CREATE TABLE edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_id TEXT NOT NULL REFERENCES nodes(id),
  to_id TEXT NOT NULL REFERENCES nodes(id),
  verb TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 1.0,
  evidence TEXT,
  source TEXT,             -- 'regex', 'motor1', 'motor2', 'llm', 'manual'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (from_id, to_id, verb)
);
CREATE INDEX idx_edges_from_verb ON edges(from_id, verb);
CREATE INDEX idx_edges_to_verb ON edges(to_id, verb);
CREATE INDEX idx_edges_confidence ON edges(confidence);
```

Localização: `data/output/grafo.sqlite` (já coberto por `data/` no `.gitignore`).

---

## Motores (algoritmos de inferência)

### Motor 1 -- Linking Documento ↔ Transação

Pra cada `Documento` recém-ingerido (Sprint 26), busca `Transacao` candidatas:
- Mesma "categoria compatível" (energia-pagamento para conta de luz)
- `|valor_doc - valor_transacao| <= max(1.00, valor_doc * 0.02)` (tolerância de 2% ou R$1)
- Data da transação entre `data_emissao - 3 dias` e `data_vencimento + 10 dias`

Score:
- 0.95 se 3 critérios batem perfeito
- 0.80 se 2 batem e 1 é frouxo (valor dentro da tolerância)
- 0.50 se só 1 bate (loga alerta, não grava)

Ambiguidade: se 2+ candidatas empatam em score, grava com menor score e cria um `Alerta/ambiguidade` (ver Sprint 29).

### Motor 2 -- Resolução de Entidade (string → nó canônico)

Hoje regex em `categorias.yaml` é o que identifica entidades. Substituir por:
- **Camada 1**: tabela de aliases em `mappings/entidades.yaml` (bancos, utilities conhecidas, farmácias).
- **Camada 2**: fuzzy match via `rapidfuzz` (Levenshtein) com threshold 85%.
- **Camada 3**: embeddings sentence-transformers para casos semânticos ("Neoenergia Brasília" vs "Neoenergia Pernambuco" são entidades diferentes, apesar de string similar -- usa contexto de estado no doc).
- **Camada 4 (Sprint 28)**: Claude Code resolve ambiguidade residual.

### Motor 3 -- Eventos e cadeias

- **Parcelamento**: série de N transações com mesmo contraparte, valor igual ou semelhante, intervalo mensal -> cria `Evento` com aresta `parte_de` em cada.
- **Assinatura**: série recorrente ≥ 3 meses, mesma entidade, valor semelhante -> cria `Assinatura` e aresta `instancia_de`.
- **Estorno/reembolso**: transação positiva dentro de 30 dias de débito da mesma entidade, valor igual ou parcial -> aresta `reembolsa`.
- **Transferência interna** (já existe): detecção de pares A->B entre contas próprias. Manter lógica atual, só registrar no grafo.

---

## Metade B: Classificação v2

### Princípios
1. Separar pessoas (privadas) das categorias (taxonomia).
2. Contexto importa: conta PF vs PJ, cartão crédito vs débito.
3. Score de confiança explícito.
4. Eliminar "Questionável" como lixeira.

### Entregas

- [ ] **Limpeza do YAML**: extrair 36+ regras `transferencia_<nome>` para `mappings/pessoas.yaml` (privado, gitignore).
- [ ] Criar `mappings/pessoas.yaml.example` com estrutura.
- [ ] **Regras contextuais** em `categorias.yaml`:
  ```yaml
  combustivel:
    regex: "POSTO|SHELL|IPIRANGA|BR MANIA"
    regras_contextuais:
      - quando: {conta_tipo: "PJ"}
        categoria: "Combustível PJ"
        classificacao: "Obrigatório"
        tag_irpf: "despesa_operacional"
      - quando: {conta_tipo: "PF"}
        categoria: "Transporte"
        classificacao: "Questionável"
  ```
- [ ] Parser seguro de condicionais (zero `eval`, só comparações declarativas).
- [ ] **Score de confiança**:
  - Override manual: 1.0
  - Regra contextual que casa 100%: 0.9
  - Regra regex + regra_valor cumprida: 0.85
  - Regra regex simples: 0.7
  - Fallback `Nao-Classificado`: 0.2
- [ ] **Novo status `Nao-Classificado`** substitui `Outros + Questionável` como fallback. `Questionável` fica reservado para categorias reais ambíguas (lazer, compras de utilidade duvidosa).
- [ ] **Loop de aprendizado**: padrões novos (3+ ocorrências sem match) geram `data/output/sugestoes_categorizacao.md`. Usuário revisa via `python -m src.transform.revisar_sugestoes` (CLI Rich/Textual).
- [ ] **Inferência contextual via grafo**: após Motor 3, a classificação é revisitada:
  - Uber no dia de consulta médica (ligação via `Periodo` + `Entidade/clinica`) -> tag `dedutivel_medico` com score 0.6.
  - Compra Amazon com descrição "livro" + cartão PJ -> categoria `Material PJ` dedutível.

---

## Entregas consolidadas

- [ ] `src/graph/schema.sql` -- DDL SQLite
- [ ] `src/graph/store.py` -- CRUD + queries (vizinhos, caminhos, top-N, agregações)
- [ ] `src/graph/linker.py` -- Motor 1
- [ ] `src/graph/entity_resolver.py` -- Motor 2
- [ ] `src/graph/event_detector.py` -- Motor 3
- [ ] `src/graph/query_cli.py` -- `python -m src.graph.query --entidade <slug>` retorna timeline
- [ ] `mappings/entidades.yaml` -- 30 entidades canônicas iniciais (bancos, utilities, IAs, farmácias)
- [ ] `mappings/pessoas.yaml` (gitignore) + `mappings/pessoas.yaml.example`
- [ ] `src/transform/categorizer.py` -- refatorado para contexto + score
- [ ] `src/transform/entity_context.py` -- deriva `conta_tipo`, `instrumento` da transação
- [ ] `src/transform/confidence.py` -- cálculo de score
- [ ] `src/transform/revisar_sugestoes.py` -- CLI de loop
- [ ] `src/pipeline.py` -- chama grafo após categorização; novo passo `construir_grafo`
- [ ] Migração única: script `scripts/construir_grafo_inicial.py` roda sobre as 2.859 transações históricas + documentos existentes, popula o grafo.
- [ ] Gauntlet novo: `tests/test_grafo_integridade.py` e `tests/test_categorizer_v2.py`.

---

## Arquivos novos/modificados

| Arquivo | Tipo |
|---------|------|
| `src/graph/*` | novo (módulo inteiro) |
| `src/transform/categorizer.py` | refatorado |
| `src/transform/entity_context.py` | novo |
| `src/transform/confidence.py` | novo |
| `src/transform/revisar_sugestoes.py` | novo |
| `mappings/entidades.yaml` | novo |
| `mappings/pessoas.yaml`, `.example` | novo + gitignore |
| `mappings/categorias.yaml` | limpeza (remove pessoas) |
| `src/pipeline.py` | editar |
| `pyproject.toml` | `rapidfuzz`, `sentence-transformers` opcional |

---

## Armadilhas

1. **Explosão combinatória**: 2.859 transações × N documentos × M entidades. Usar batching e índices. Motor 1 sobre histórico: estimar em ~30s no primeiro run.
2. **SQLite vs XLSX**: XLSX continua sendo saída humana, grafo é a verdade relacional interna. NÃO tentar substituir ainda (isso é Sprint 11).
3. **Falsos positivos do Motor 1**: exigir confidence >= 0.8 pra gravar. Amostras abaixo disso viram alerta pra Sprint 29.
4. **`pessoas.yaml` vazando no git**: adicionar ao `.gitignore` ANTES de criar. Validar no pre-commit.
5. **Regex vs Fuzzy**: fuzzy sem regex prévio pode gerar falsos positivos. Arquitetura: regex primeiro (alta precisão), fuzzy segundo (recall).
6. **Renomear "Questionável"**: em 2 fases (adicionar `Nao-Classificado`, migrar dashboards, depois limpar uso antigo).
7. **Histórico mudando retroativamente**: rodar `construir_grafo_inicial.py` vai reclassificar as 2.859 transações. Salvar snapshot antes e diffar.
8. **Sentence-transformers pesado**: 300MB+ de modelo. Opcional, com fallback pra só Levenshtein.

---

## Critério de sucesso

1. Grafo contém nós para: todas as 2.859 transações, todas as contas/cartões do casal, 30+ entidades canônicas, todos os documentos ingeridos pela Sprint 26.
2. Motor 1 consegue linkar pelo menos 80% dos documentos históricos com confidence >= 0.8.
3. Motor 3 detecta corretamente parcelamentos conhecidos (ex.: compras Amazon em 10x) e pelo menos 5 assinaturas (Netflix, Spotify, Disney, Claude, ChatGPT, etc.).
4. `python -m src.graph.query --entidade neoenergia` lista timeline completa em menos de 1 segundo.
5. `categorias.yaml` fica com < 70 regras (sem pessoas). `pessoas.yaml` (privado) tem 40+ entradas.
6. `Nao-Classificado` <= 5% das transações em meses recentes após 1 ciclo de revisão.
7. 90% das transações com categoria_confianca >= 0.7.
8. Zero regressão nos totais monetários mensais antes/depois (só categoria e score mudam).

---

## Dependências

- **Sprint 26 (Ingestão Universal)** -- fonte de `Documento`s. Pode começar esta sprint sem 27 pronta, mas linking só fica útil com 27 entregue.
- **Sprint 28 (LLM)** -- consome o grafo para inferência. Motor 2 camada 4 depende dela, mas as outras camadas funcionam sem LLM.
- **Sprint 29 (UX)** -- consome o grafo. Só inicia depois desta.
- **Sprint 11 (Vault Final)** -- futuro consolidador: XLSX vira secundário, SQLite/grafo vira primário.
- **Sprint 18 (Dívida Técnica)** -- precisa estar concluída antes de refatorar o categorizador (base estável).

---

## Ordem sugerida internamente

1. Metade B primeiro (categorizer v2) -- ganho imediato com categorias limpas.
2. Schema SQLite + store.
3. Migração inicial das transações históricas para nós.
4. Motor 2 (entidade resolver) -- beneficia Metade B também.
5. Motor 1 (linking doc-transação) -- só após Sprint 26 entregar documentos.
6. Motor 3 (eventos) -- último, consome tudo.

---

*"Tudo está em tudo." -- Anaxágoras*
