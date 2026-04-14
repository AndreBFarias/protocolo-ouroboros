# Auditoria de Sprints -- Controle de Bordo

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
  - `itau_pdf` (PDF protegido, senha 051273)
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
- Makefile com 13 targets (process, xlsx, relatorio, check, lint, clean, etc.)
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

## Sprint 5 -- Relatórios e Projeções -- NÃO VALIDADA

**Objetivo:** Projeções financeiras, metas de economia, cenários.

### Entregue (não validado)

- `src/dashboard/projecoes.py` (334 linhas) -- página de projeções financeiras
- `src/dashboard/metas.py` (290 linhas) -- página de acompanhamento de metas
- `src/dashboard/scenarios.py` (174 linhas) -- simulador de cenários
- `mappings/metas.yaml` (43 linhas) -- definições de metas do usuário
- `src/load/relatorio.py` modificado para incluir projeções

### Status

Código criado por subagente que finalizou com créditos esgotados antes de validação completa. Lint passa (`ruff check` sem erros), mas funcionalidade não foi testada no browser. Não há garantia de que as páginas renderizam corretamente ou que os cálculos estão corretos.

### Risco

Código em produção sem teste. Pode quebrar o dashboard existente se importado incorretamente. Requer sessão dedicada de validação.

---

## Sprint 6 -- Integração Obsidian -- NÃO VALIDADA

**Objetivo:** Sincronizar relatórios financeiros com vault Obsidian.

### Entregue (não validado)

- `src/obsidian/sync.py` (349 linhas) -- sincronizador vault Obsidian
- 44 relatórios mensais sincronizados para `~/Controle de Bordo/Pessoal/Financeiro/Relatórios/`
- 7 notas de metas criadas no vault
- MOC (Map of Content) "Dashboard Financeiro" com Dataview queries

### Status

Código criado por subagente. Lint passa, vault populado com arquivos. Porém:
- Dataview queries não foram validadas no Obsidian (podem ter erro de sintaxe)
- Frontmatter YAML gerado não foi verificado contra schema Dataview
- Idempotência do sync não testada exaustivamente

### Risco

Se Dataview queries estiverem erradas, o MOC mostra tabelas vazias ou erros. Os arquivos em si são Markdown válido e não quebram o vault.

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

*"O que não se mede não se melhora; o que não se audita não se confia." -- Peter Drucker*
