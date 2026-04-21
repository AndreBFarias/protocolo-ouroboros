# Roadmap -- Protocolo Ouroboros

```
VERSÃO: 7.5 | SPRINTS: 95 (46 concluídas, 0 em produção, 36 backlog, 13 arquivadas)
ROTA: Catalogador universal artesanal (Fases ALFA → ZETA) + Fase ETA (auditoria) + Fase IOTA (integração Controle de Bordo) + Fase KAPPA (UX polish + tracking documental + workflow)
ÚLTIMA ATUALIZAÇÃO: 2026-04-21 tarde. Andre compartilhou a visão real do projeto. Criadas Fases IOTA (integração com ~/Controle de Bordo/) e KAPPA (UX + tracking documental + workflow). 3 ADRs novos (18, 19, 20) + 12 sprints novas (70-81) + golden test cases em docs/GOLDEN_TEST_CASES.md. Fase ETA quase completa -- só 68b em execução residual.
```

---

## Visão

Catalogador universal artesanal da vida financeira do casal. O usuário joga QUALQUER arquivo do dia a dia (foto de cupom fiscal, DANFE PDF, XML NFe, recibo, receita médica, garantia, holerite, extrato, boleto, conta de luz, HEIC do celular) numa inbox única. O sistema:

1. Classifica o tipo e move pra pasta estruturada
2. Extrai conteúdo completo -- inclusive itens individuais de NF (20 produtos classificados, não só o total)
3. Linka tudo no grafo: transação bancária ↔ documento ↔ item ↔ fornecedor ↔ categoria
4. Apresenta tudo em dashboard + Obsidian + busca global

**Princípio central:** o Supervisor Artesanal é Claude Code Opus via browser (assinatura Max do usuário). Nada de cliente programático Anthropic. Cada sessão interativa lê arquivos originais, compara com outputs do pipeline determinístico, e propõe regras em `mappings/*.yaml`. Humano aprova. Regras aprovadas fazem o pipeline crescer e a dependência do LLM encolher. Quando o pipeline cobrir tudo, IA deixa de ser necessária -- autossuficiência.

**Fases:**

1. **ALFA** -- resíduos técnicos da sessão 2026-04-18 (sprints 37-40 retroativas) -- CONCLUÍDA
2. **BETA** -- infra universal: intake multiformato + grafo + workflow do supervisor (41-43)
3. **GAMA** -- extratores por formato de documento (44-47b)
4. **DELTA** -- linking e classificação de itens (48-50)
5. **EPSILON** -- UX rica: dashboard, busca, grafo visual (51-53)
6. **ZETA** -- consumo dos dados granulares (sprints 21, 25, 33, 34, 35, 36 já no backlog)

**Higiene INFRA (fora de fase):** sprints pontuais de dívida pré-existente detectada por validador-sprint como achado colateral. Executáveis em qualquer janela, baixa prioridade, não bloqueiam fases.

---

## Estado atual -- mapa por status

| Status | Sprints | Total |
|--------|---------|-------|
| Concluídas (fases anteriores) | 01-07, 12-14, 17-19, 22, 23, 30, 37-40, 41, 41b, 41c, 41d, 42, 43, 44, 44b, 45, 47c, 54 | 31 |
| Concluídas Fase ETA (auditoria 2026-04-21) | 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 68b, 69 | 16 |
| Backlog ativo (ALFA→EPSILON) | 46-53 (inclui 47a, 47b) | 11 |
| Backlog consumidor (ZETA) | 20, 21, 24, 25, 33, 34, 35, 36 (pós-EPSILON) | 8 |
| Fase ETA residual sprint-nova | 82 (canonicalizer variantes curtas, achado 68b-A) | 1 |
| **Backlog Fase IOTA (integração Controle de Bordo)** | **70, 71** | **2** |
| **Concluídas Fase KAPPA (baseline de higiene)** | **81** | **1** |
| **Backlog Fase KAPPA (UX polish + tracking documental + workflow)** | **72, 73, 74, 75, 76, 77, 78, 79, 80** | **9** |
| Arquivadas (substituídas) | 08, 09, 10, 11, 15, 16, 26, 27a, 28, 29a, 29b, 31, 32 | 13 |

Cabeçalho de cada sprint arquivada explica motivo e substituta.

---

## Fase ALFA -- Resíduos técnicos retroativos (CONCLUÍDA)

Bugs encontrados e corrigidos durante a sessão 2026-04-18, documentados como sprints individuais em 2026-04-19.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 37 | Fix: OFX encoding com espaços no header C6 | CONCLUÍDA | ALTA |
| 38 | Fix: Deduplicator fuzzy remove por (data+valor+local) | CONCLUÍDA | ALTA |
| 39 | Fix: IRPF gerador_pacote sort com tag mista str/NaN | CONCLUÍDA | ALTA |
| 40 | Fix: Categorizer fallback respeita tipo da transação | CONCLUÍDA | MEDIA |

---

## Fase ETA -- Correções da auditoria profunda (2026-04-21)

Auditoria manual do dashboard em 2026-04-21 descobriu um bug estrutural de classificação de tipo que vinha distorcendo TODAS as métricas financeiras desde o MVP original (Sprints 01-04). Além disso, sprints 47a/b, 48, 49, 50 foram aprovadas com pytest verde mas têm grafo real vazio (plumbing existente, dados inexistentes). 15 sprints novas para restaurar confiança nos dados e corrigir UI/UX detectada. Sprints 67-69 derivaram dos achados M56-1/M56-2/M56-3 durante o smoke aritmético.

**P0 (crítica, bloqueante):**

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 55 | Fix crítico classificador de tipo (1.761 transações falsamente "Receita") | CONCLUÍDA | **P0 CRÍTICA** |
| 56 | Smoke runtime-real aritmético (contrato global do XLSX) | CONCLUÍDA | **P0** |

**P1 (importante):**

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 57 | Ingestão de volume real (ativar Sprints 47a/b, 48, 49, 50) | CONCLUÍDA | P1 |
| 59 | Fix chips de sugestão na Busca Global | CONCLUÍDA | P1 |
| 60 | Labels humanos no grafo + truncamento correto em bar chart | CONCLUÍDA | P1 |
| 67 | Fix classificação em Receita/Transferência Interna (achado M56-2) | BACKLOG | P1 |
| 68 | Fix falso-positivo de transferência interna (achado M56-3) | BACKLOG | P1 |

**P2 (polish):**

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 58 | Atualizar CLAUDE.md + VALIDATOR_BRIEF com contagens reais | EM EXECUÇÃO | P2 |
| 61 | Projeções com contexto explícito (3 ritmos) | BACKLOG | P2 |
| 62 | Responsividade dos cards em viewport <1200px | BACKLOG | P2 |
| 63 | Remover prefixo numérico de sprint dos títulos | BACKLOG | P2 |
| 64 | Contas: aviso snapshot + NaN→traço | BACKLOG | P2 |

**P3 (refinamento):**

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 65 | Localização PT-BR dos gráficos Plotly | BACKLOG | P3 |
| 66 | Canonicalização de nomes (acentuação plausível + razão social) | BACKLOG | P3 |
| 69 | Higiene acentuação em scripts/reprocessar_documentos.py (achado M56-1) | BACKLOG | P3 |

Ordem de execução sugerida: 55 → 56 → (57, 58, 59, 60 em paralelo) → (61-69 em paralelo).

---

## Fase IOTA -- Integração com ~/Controle de Bordo/ (2026-04-21 tarde)

Gatilho: Andre compartilhou que o Controle de Bordo já é o hub central dele (vault Obsidian PARA com motor de inbox em `.sistema/scripts/`). Ouroboros deve consumir dessa inbox e escrever de volta no vault, sem duplicar processadores. **ADR-18** formaliza o contrato de coabitação estrutural.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 70 | Inbox unificada (Ouroboros lê ~/Controle de Bordo/Inbox/ e roteia financeiros para data/raw/) | BACKLOG | **P0** |
| 71 | Sync rico bidirecional: vault ganha Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments} | BACKLOG | P1 |

**ADR:** ADR-18 (integração Controle de Bordo).

---

## Fase KAPPA -- UX polish + tracking documental + workflow (2026-04-21 tarde)

Gatilho: mesma sessão, 11 screenshots de problemas concretos + visão declarada: dashboard interativo (clique em gráfico navega), tracking documental completo (clique em "Natação André" abre boleto + recibo), gap analysis, workflow via `run.sh` interativo. **ADR-19** e **ADR-20** formalizam.

### Tracking documental (coração ADR-20)

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 74 | Vinculação transação<->documento: matching heurístico + modal com preview do comprovante | BACKLOG | **P0** |
| 75 | Gap Analysis: documentos faltantes por mês/categoria com alertas inteligentes | BACKLOG | P1 |

### Interatividade (ADR-19)

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 72 | Filtro forma de pagamento (Pix/Débito/Crédito/Boleto/Transferência) | BACKLOG | P1 |
| 73 | Dashboard interativo: clique em gráfico leva para Extrato filtrado (via query_params) | BACKLOG | P1 |
| 78 | Grafo visual Obsidian-like: full-page + filtros laterais + clique navega | BACKLOG | P1 |
| 79 | Aba Pagamentos: tracking por boletos/pix/crédito com status e vencimentos | BACKLOG | P2 |

### Polish visual

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 76 | Fonte mínima 13px, logo acima do título, centralização, padding dos retângulos | BACKLOG | P1 |
| 77 | Treemap estético, legendas abaixo do título, filtros avançados funcionais, Top 10 espaçada | BACKLOG | P1 |

### Workflow

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 80 | `./run.sh` interativo: menu (Inbox / Dashboard / Relatório / Sync / Tudo) + pergunta pós-processamento | BACKLOG | P2 |

### Higiene residual

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 81 | Sweep: acentuação em test_dashboard_titulos.py + ruff em scripts/ + noqa explícito | BACKLOG | P3 |

**ADRs:** ADR-19 (dashboard interativo drill-down), ADR-20 (tracking documental completo).

### Ordem de execução sugerida (Fases IOTA + KAPPA)

Caminho crítico recomendado:

```
68b (Fase ETA residual, já em execução)
  ↓
81 (baseline limpa antes de entrar em IOTA)
  ↓
70 (Inbox unificada) ──────────────┬─→ 80 (run.sh interativo)
  ↓                                │
71 (Sync rico bidirecional)        │
  ↓                                │
74 (Vínculo doc↔tx) ─→ 75 (Gap analysis)
                                   │
72 (Filtro forma) ──→ 73 (Drill-down) ─→ 78 (Grafo full) ─→ 79 (Pagamentos)
                                   │
76 (UX v1) ──→ 77 (UX v2)
```

**Resumo linear sugerido:** 68b → 81 → 70 → 76 → 74 → 72 → 71 → 73 → 77 → 80 → 75 → 78 → 79.

---

## Higiene INFRA -- Fora de fase (dívida pré-existente)

Sprints pontuais derivadas de achados colaterais do validador-sprint. Não bloqueiam as fases BETA/GAMA/DELTA/EPSILON/ZETA; executáveis em qualquer janela livre.

| Sprint | Tema | Status | Prioridade | Origem |
|--------|------|--------|------------|--------|
| 54 | Limpeza de 22 violações de acentuação pré-existentes | CONCLUÍDA | MEDIA | COL-44-A (validador Sprint 44) |

Objetivo: reconstruir baseline verde de `make lint` e `scripts/check_acentuacao.py --all` para permitir medição limpa de regressões em sprints futuras. Sem ruído de dívida herdada, uma nova violação vira sinal claro de regressão introduzida.

---

## Fase BETA -- Infra universal (3 sprints, pré-requisito)

Objetivo: aceitar qualquer arquivo, armazenar tudo no grafo, formalizar o workflow do supervisor.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 41 | Intake Universal Multiformato (JPG/HEIC/XML/EML/ZIP/...) | CONCLUÍDA | CRÍTICA |
| 41b | Auto-detecção de pessoa via CPF do conteúdo | CONCLUÍDA | MEDIA |
| 41c | Unificação detector legado + YAML (recall 19% → 85% em data/raw/) | CONCLUÍDA | MEDIA |
| 41d | Heterogeneity Detection (page-split condicional) | CONCLUÍDA | ALTA |
| 42 | Grafo SQLite Mínimo (7.378 nodes + 24.506 edges) | CONCLUÍDA | CRÍTICA |
| 43 | Workflow Supervisor Artesanal (scripts, templates, diário) | CONCLUÍDA | CRÍTICA |

Sprint 41 e 42 podem rodar em paralelo. Sprint 43 depende da 42 (supervisor_contexto.sh consulta grafo).

ADRs relevantes: ADR-13 (supervisor sem API), ADR-14 (schema grafo), ADR-18 (intake multiformato).

---

## Fase GAMA -- Extratores de documento (6 sprints, paralelizáveis)

Objetivo: transformar arquivos em itens estruturados no grafo.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 44 | Extrator NFe modelo 55 (DANFE PDF formal) | CONCLUÍDA | ALTA |
| 44b | Extrator NFC-e modelo 65 (mini-cupom QR SEFAZ) | CONCLUÍDA | ALTA |
| 45 | Extrator Cupom Fiscal Térmico (foto) | CONCLUÍDA | ALTA |
| 46 | Extrator XML NFe | PENDENTE | MEDIA |
| 47 | Extrator Recibo Não-Fiscal | PENDENTE | MEDIA |
| 47a | Extrator Receita Médica e Prescrição | PENDENTE | MEDIA |
| 47b | Extrator Termo de Garantia (fabricante) | PENDENTE | BAIXA |
| 47c | Extrator Cupom Bilhete de Seguro Garantia Estendida (apólice SUSEP) | CONCLUÍDA | MEDIA |

Após BETA, qualquer das GAMA pode começar. DANFE/NFC-e e cupom térmico têm maior impacto imediato (fontes dominantes do dia a dia). Sprint 47c aguarda aprovação humana via `docs/propostas/sprint_nova/sprint_47c_cupom_garantia_estendida.md`.

---

## Fase DELTA -- Linking e classificação (3 sprints)

Objetivo: conectar documentos a transações, unificar produtos, classificar itens.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 48 | Linking Documento ↔ Transação | PENDENTE | ALTA |
| 49 | Entity Resolution de Produtos | PENDENTE | MEDIA |
| 50 | Classificação de Itens via YAML | PENDENTE | ALTA |

Sequência sugerida: 48 → 49 → 50 (linking prepara material para ER, que habilita categorização coerente).

---

## Fase EPSILON -- UX rica (3 sprints)

Objetivo: interface humana sobre o grafo.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 51 | Dashboard de Catalogação | PENDENTE | ALTA |
| 52 | Busca Global Doc-Cêntrica + Timeline | PENDENTE | ALTA |
| 53 | Grafo Visual Interativo + Obsidian Rico | PENDENTE | MEDIA |

Sequência sugerida: 51 → 52 → 53 (cada uma reusa infra da anterior).

---

## Fase ZETA -- Consumo dos dados granulares (após EPSILON)

Sprints já no backlog que agora operam sobre itens, não só transações. Prioridade final definida conforme evolução do grafo.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 21 | Relatórios Diagnósticos (por categoria de item) | PENDENTE | ALTA |
| 20 | Dashboard Redesign (tipografia, layout pós-EPSILON) | PENDENTE | MEDIA |
| 33 | Resumo Mensal Narrativo | PENDENTE | MEDIA |
| 34 | Supervisor Auditor Modo 2 (valida extrações de NF) | PENDENTE | ALTA |
| 35 | IRPF Regras YAML | PENDENTE | MEDIA |
| 36 | Métricas de Autossuficiência (dash IA) | PENDENTE | MEDIA |
| 24 | Automação Bancária (pós-granularidade) | PENDENTE | BAIXA |
| 25 | Pacote IRPF completo (usa itens de NF) | PENDENTE | BAIXA |

---

## Sprints arquivadas

| Sprint | Status | Motivo | Substituída por |
|--------|--------|--------|-----------------|
| 08 | CANCELADA | API externa custa $2-5/mês com cache; hardware local não se justifica. | 43 |
| 09 | ABSORVIDA | Sankey e heatmap passam a 53. | 53 |
| 10 | CANCELADA | IRPF 2026 já declarado manualmente; 25 e 35 cobrem 2027+. | 25, 35 |
| 11 | CANCELADA | Unificação arquitetural é armadilha ambiciosa. | -- |
| 15 | ABSORVIDA | Polish fundido na 20. | 20 |
| 16 | ABSORVIDA | Testes mínimos viraram parte da 30. | 30 |
| 26 | OBSOLETA | Ingestão universal virou 41. | 41 |
| 27a | ABSORVIDA | Grafo mínimo virou 42 (schema extensível). | 42 |
| 28 | REPENSADA | LLM orquestrado programático cancelado (ADR-13). | 43 + 44-47b |
| 29a | ABSORVIDA | Busca global virou 52. | 52 |
| 29b | ABSORVIDA | Grafo visual + Obsidian rico virou 53. | 53 |
| 31 | REPENSADA | Supervisor via API programática cancelado (ADR-13). | 43 |
| 32 | ABSORVIDA | OCR de energia virou caso especial do cupom térmico. | 45 |

---

## Ordem de execução recomendada

```
Fase ALFA -- CONCLUÍDA
  └─ 37 → 38 → 39 → 40

Higiene INFRA (fora de fase, baixa prioridade)
  └─ 54 Limpeza de acentuação pré-existente (baseline verde)

Fase BETA -- infra universal (próximo bloco)
  ├─ 41 Intake multiformato  ─────┐
  └─ 42 Grafo SQLite mínimo  ─────┼── 43 Workflow Supervisor

Fase GAMA -- extratores (paralelizáveis)
  ├─ 44  DANFE PDF (NFe modelo 55)
  ├─ 44b NFC-e modelo 65 (mini-cupom QR SEFAZ)
  ├─ 45  Cupom térmico foto
  ├─ 46  XML NFe
  ├─ 47  Recibo não-fiscal
  ├─ 47a Receita médica
  ├─ 47b Termo de Garantia (fabricante)
  └─ 47c Cupom Bilhete de Seguro Garantia Estendida

Fase DELTA -- linking e classificação
  └─ 48 Linking doc↔transação → 49 ER de produtos → 50 Categorias de item

Fase EPSILON -- UX
  └─ 51 Dashboard → 52 Busca → 53 Grafo visual + Obsidian

Fase ZETA -- consumo final
  ├─ 21 Relatórios diagnósticos granulares
  ├─ 20 Dashboard polish
  ├─ 33 Resumo narrativo
  ├─ 34 Auditor Modo 2
  ├─ 35 IRPF YAML
  ├─ 36 Métricas IA
  ├─ 24 Automação bancária
  └─ 25 Pacote IRPF completo
```

---

## Workflow de sprints

Layout em `docs/sprints/{backlog,producao,concluidos,arquivadas}`. Template canônico em `docs/templates/SPRINT_TEMPLATE.md` -- agora inclui seção "Conferência Artesanal Opus".

Scripts:
- `scripts/audit_sprint_coverage.py` -- auditoria de cobertura doc ↔ git log
- `scripts/ci/validate_sprint_structure.py` -- bloqueia CI se sprint ativa estiver fora do padrão
- `scripts/finish_sprint.sh NN` -- encerra sprint (valida, atualiza Status, move para concluidos)
- `scripts/supervisor_contexto.sh` (Sprint 43) -- dumpa estado do projeto para início de sessão
- `scripts/supervisor_proposta_nova.sh` (Sprint 43) -- abre proposta com template
- `scripts/supervisor_aprovar.sh` (Sprint 43) -- absorve proposta e atualiza diário
- `hooks/sprint_auto_move.py` -- pre-commit move automática conforme Status

---

## Referências

- Plano atual: `/home/andrefarias/.claude/plans/sprint-fluffy-puddle.md`
- Prompt de execução: `docs/PROMPT_EXECUCAO.md` (Sprint 43 usa; criado na mesma sessão do re-roadmap)
- Contexto técnico: `../CLAUDE.md`
- Armadilhas: `ARMADILHAS.md`
- ADRs 13-15 ancoram decisões do re-roadmap
- Template de sprint: `templates/SPRINT_TEMPLATE.md`

---

*"Um sistema inteligente não é o que faz tudo. É o que sabe o que fazer primeiro."*
