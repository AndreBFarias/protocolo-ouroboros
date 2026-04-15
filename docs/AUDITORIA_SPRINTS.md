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

*"O que não se mede não se melhora; o que não se audita não se confia." -- Peter Drucker*
