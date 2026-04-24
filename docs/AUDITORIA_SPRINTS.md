# Auditoria de Sprints -- Protocolo Ouroboros

Registro sincero do que foi entregue, do que ficou pendente e das lições de cada sprint.

---

## Sprint 1 -- MVP

**Objetivo:** Pipeline funcional de ponta a ponta. `./run.sh 2026-04` gera XLSX + relatório.

### Entregue

- Scaffold completo do projeto (estrutura de diretórios, pyproject.toml, install.sh, run.sh)
- `inbox_processor`: detecta banco/pessoa pelo conteúdo do arquivo e move para `data/raw/{pessoa}/{banco}/`
- 6 extratores funcionais:
  - `nubank_cartao` (CSV cartão de crédito)
  - `nubank_cc` (CSV conta corrente, com UUID)
  - `c6_cc` (XLS encriptado via msoffcrypto-tool)
  - `c6_cartao` (CSV)
  - `itau_pdf` (PDF protegido, senha [SENHA])
  - `santander_pdf` (PDF fatura)
- Categorizer com regex base (mappings/categorias.yaml)
- Deduplicator 3 níveis (UUID, hash, pares de transferência)
- xlsx_writer com 8 abas completas
- Gerador de relatório Markdown mensal
- Importação do histórico XLSX antigo (1.254 lançamentos, ago/2022 a jul/2023)
- **Total processado: 2.859 transações**

### Faltou

- Extrator CAESB (água) -- adiado para sprint posterior
- Parser de boleto genérico -- adiado
- Testes automatizados -- zero testes escritos nesta sprint
- Checklist do CLAUDE.md não foi atualizado após conclusão

### Observações

O doc de sprint original listava "extrator genérico de conta de água" como entrega, mas isso pertencia à Sprint 2. Sprint 1 entregou mais do que o previsto: o inbox_processor não estava no escopo original mas foi adicionado por necessidade prática (usuário não queria organizar arquivos manualmente).

---

## Sprint 2 -- Infraestrutura e Qualidade

**Objetivo:** Cobertura de categorização 100%, automação de qualidade, documentação de extratores.

### Entregue

- Categorização de 92,5% para 100% de cobertura (111 regras regex)
- Makefile com 13 targets (process, xlsx, relatorio, check, lint, clean, etc.) <!-- noqa: accent -->
- Script de pre-commit local (verificação de lint, acentuação, anonimato)
- OCR de conta de energia via tesseract (validado com gabarito manual)
- Auto-documentação em `docs/extractors/` (7 documentos, um por extrator)

### Faltou

- Extrator CAESB (água) -- adiado novamente
- Parser de boleto genérico -- adiado
- Hook ruff no pre-commit real -- `core.hooksPath` global impede; workaround via Makefile

### Observações

A subida de 92,5% para 100% exigiu análise manual de cada transação não categorizada. Muitas eram estabelecimentos únicos que apareciam 1-2 vezes. Optou-se por regex específicos em vez de categoria genérica para manter rastreabilidade.

---

## Sprint 3 -- Dashboard Streamlit

**Objetivo:** Interface visual para explorar dados financeiros.

### Entregue

- 4 páginas funcionais:
  - Visão Geral (cards de resumo, gráficos de evolução)
  - Categorias (treemap, barras horizontais por classificação)
  - Extrato (tabela filtrada com busca)
  - Contas (dívidas ativas, prazos, status de pagamento)
- Sidebar com filtros globais (mês, pessoa)
- Cards de resumo com métricas principais
- Tema dark configurado via `.streamlit/config.toml`
- 6 gráficos Plotly interativos

### Faltou

- Layout responsivo -- não testado em dispositivos móveis
- Problemas de UI visíveis: botões invisíveis com tema dark, fontes inconsistentes entre páginas
- Páginas "Projeções" e "Metas" -- planejadas para Sprint 5

### Observações

Streamlit se mostrou excelente para prototipagem rápida mas limitado para customização visual fina. O hack de troca de tabs via JavaScript (armadilha 11) exemplifica as limitações.

---

## Sprint 4 -- Inteligência e Validação

**Objetivo:** Refinamento da categorização, IRPF, validação de dados.

### Entregue

- `mappings/overrides.yaml` com 10 correções manuais (transações que regex não resolve)
- `src/transform/irpf_tagger.py`: 21 regras de classificação fiscal, 5 tipos de tag, 79 registros gerados
- `src/transform/validator.py`: 6 checagens de integridade pós-processamento
- Categorizer refatorado: overrides como prioridade máxima, detecção de padrões novos não categorizados

### Faltou

- Deduplicação cruzada CC x cartão -- mesma transação aparece no extrato CC como débito e na fatura como item. Não resolvido.
- Deduplicação PIX entre contas próprias -- hash não é suficiente quando descrições divergem entre bancos
- Validação de receitas vs holerites -- não implementada
- Conferência de saldos bancários -- não implementada
- Saldos em 31/12 para IRPF -- campo obrigatório na declaração, não coletado

### Observações

O irpf_tagger foi a entrega mais valiosa: transforma dados transacionais em informação fiscal estruturada. As 21 regras cobrem os cenários mais comuns, mas falta CNPJ automático das fontes pagadoras.

---

## Sprint 5 -- Relatórios e Projeções -- VALIDAÇÃO SUPERFICIAL

**Objetivo:** Projeções financeiras, metas de economia, cenários.

### Entregue

- `src/projections/scenarios.py` (174 linhas) -- lógica real de cenários com cálculos baseados em dados
- `src/dashboard/paginas/projecoes.py` (334 linhas) -- página funcional com 3 cenários e gráfico de patrimônio
- `src/dashboard/paginas/metas.py` (290 linhas) -- página funcional com barras de progresso
- `mappings/metas.yaml` (43 linhas) -- 7 metas reais do casal
- `src/load/relatorio.py` modificado -- seções de metas, projeção e IRPF adicionadas

### Validação realizada

- `ruff check` passou sem erros
- Pipeline `--tudo` roda sem erros com os novos arquivos
- Página Projeções aberta no browser: cenários renderizam, gráfico de patrimônio funciona
- Página Metas aberta no browser: 3 metas visíveis com progresso e prazos
- app.py integra 6 tabs sem conflito

### Validação pendente

- Lógica dos cenários não verificada em profundidade (números podem estar incorretos)
- Edge cases: meses sem dados, divisão por zero, metas sem prazo
- Relatórios melhorados não comparados com versão anterior item a item
- Cenário "Pós-Infobase" mostra saldo negativo de R$ -7.349 -- pode estar correto ou não

---

## Sprint 6 -- Integração Obsidian -- VALIDAÇÃO SUPERFICIAL

**Objetivo:** Sincronizar relatórios financeiros com vault Obsidian.

### Entregue

- `src/obsidian/sync.py` (349 linhas) -- lógica real de sync com extração de valores via regex
- 44 relatórios sincronizados em `~/Controle de Bordo/Pessoal/Financeiro/Relatórios/`
- 7 notas de metas criadas com frontmatter YAML
- MOC "Dashboard Financeiro" com Dataview queries
- `run.sh --sync` integrado

### Validação realizada

- `ruff check` passou sem erros
- 44 arquivos confirmados no vault
- 7 metas confirmadas no vault
- Frontmatter do relatório 2026-04 verificado (receita, despesa, saldo corretos)

### Validação pendente

- Dataview queries NÃO testadas no Obsidian (podem ter erro de sintaxe)
- Frontmatter de TODOS os relatórios não verificado (só 1 checado)
- Idempotência do sync não testada (rodar 2x pode duplicar dados?)
- Backlinks entre relatórios e metas não verificados

---

## Resumo Geral

| Sprint | Status | Entregas planejadas | Entregas reais | Testes |
|--------|--------|---------------------|----------------|--------|
| 1 - MVP | Concluída | 7 | 9 (+inbox_processor, +histórico) | 0 |
| 2 - Infra | Concluída | 5 | 5 | 0 |
| 3 - Dashboard | Concluída | 6 páginas | 4 páginas | 0 |
| 4 - Inteligência | Concluída | 6 | 4 | 0 |
| 5 - Projeções | Não validada | 4 | 4 (sem teste) | 0 |
| 6 - Obsidian | Não validada | 3 | 3 (sem teste) | 0 |

**Dívida técnica acumulada:**
- Zero testes automatizados em 6 sprints
- 2 sprints não validadas (5 e 6)
- Deduplicação CC x cartão incompleta
- Deduplicação PIX entre contas incompleta
- Extrator CAESB adiado 3 vezes
- Saldos bancários em 31/12 não coletados

---

## Sessão 2026-04-23 -- rota "conserta tudo" + Fases A/B/C/E (19 sprints + auditoria)

Baseline 1.139 → 1.261 passed. 30+ commits em main. Cada sprint auditada honestamente abaixo.

### Rota "conserta tudo" (9 sprints)

| Sprint | Commit | Veredicto | Ressalvas |
|---|---|---|---|
| P0.1 aba renda restritiva | `20c4366` | SUCESSO | Smoke aritmético exposto após fix (contrato mascarado por dado sujo; ver ARMADILHAS A-202304-05) |
| P0.2 pessoa_detector CNPJ | `1a01c5d` | SUCESSO | Migração física dos 22 arquivos antigos ficou para Fase A1 |
| P1.1 extrator DAS PARCSN | `ff0439a` | SUCESSO | 47 arquivos físicos viram 10 únicos no grafo (idempotência por número SENDA) |
| P1.2 OCR fallback no preview | `fd04d41` | APROVADO_COM_RESSALVA | Extratores downstream precisam OCR próprio (NFCe coberto em A2) |
| P2.1 Sprint 87d fallback idempotente | `c4ec725` | SUCESSO | 6 propostas dirty viraram 2 idempotentes em runtime |
| P2.2 Sprint 91 UX v3 | `ad66dc1` | SUCESSO | 2 testes ajustados para acomodar novos patterns |
| P2.3 dedupe roteamento por hash | `37479df` | SUCESSO | Só atua em reingestões novas; não é retroativo |
| P3.1 extrator DIRPF .DEC | `f791421` | APROVADO_COM_RESSALVA | MVP parseia só cabeçalho; seções de rendimentos ficam para sprint dedicada |
| P3.2 holerite como documento | `ba036e3` | SUCESSO | +24 docs destravaram teste cobertura (meta 20 superada) |

### Fase A -- ressalvas (3 sprints)

| Sprint | Commit | Veredicto | Ressalvas |
|---|---|---|---|
| A1 migração casal→andre | `8267b3a` | SUCESSO | 4/30 arquivos ficaram em casal/ legitimamente |
| A2 NFCe com OCR | `2226661` | SUCESSO | NFCe Americanas 4p 0 chars extraiu 2 NFCe + 16 itens |
| A3 categorizer idempotente | `6d65aa7` | SUCESSO | Fecha ressalva M50-1 da Sprint 50 |

### Fase B -- ZETA (3 sprints)

| Sprint | Commit | Veredicto | Ressalvas |
|---|---|---|---|
| B1 relatórios diagnósticos | `b3348bd` | SUCESSO | Alertas heurísticos por categoria (nova >R$100, >150% média, queda <30%) |
| B2 resumo narrativo | `0d1cd36` | SUCESSO | Template heurístico sem LLM |
| B3 IRPF YAML | `0542087` | SUCESSO | 22 regras declarativas; fallback hardcoded preservado |

### Fase C -- backlog formal (3 sprints paralelas via worktrees)

| Sprint | Commits | Veredicto | Ressalvas |
|---|---|---|---|
| C1 canonicalizer TI | `0c80bf2`+`9c66b19`→`8576127` | SUCESSO | Sprint 82b (conta-espelho) adiada formalmente |
| C2 UX audit Nielsen | `58e99c7`→`e48970f` | SUCESSO | 0 LOC de produção; 3 sprints-filhas com 14 fixes priorizados |
| C3 auditoria extratores | `6ad317d`→`a123501` | APROVADO_COM_RESSALVA | 8/9 bancos divergem em 3 famílias (93a/b/c) |

### Fase E -- auditoria técnica

| Sprint | Commit | Veredicto |
|---|---|---|
| E auditoria + docs mestres | (em andamento) | SUCESSO -- 0 P0, 5 P1 mapeados, 8 P2, 2 YAMLs órfãos |

### Lições meta da sessão

1. **Worktree isolado para sprints paralelas funciona** quando escopos são disjuntos. 3 agents em C1/C2/C3 simultâneos sem conflito.
2. **Anti-débito dá frutos**: 7 sprints-filhas formalizadas, zero "TODO depois".
3. **Contratos aritméticos podem mascarar dado sujo** (A-202304-05). Limpar os dois lados simultaneamente.
4. **Padrão declarativo em YAML** consolidado: fontes_renda, pessoas, irpf_regras -- todos com schema + fallback + testes.
5. **OCR fallback não se propaga automaticamente** entre intake e extratores (A-202304-06).
6. **Auditoria automática** expôs bugs invisíveis: 8 de 9 extratores bancários divergem sem detecção prévia.

---

*"O que não se mede não se melhora; o que não se audita não se confia." -- Peter Drucker*
