# CLAUDE_2.md — Controle de Bordo: Roadmap Completo

```
STATUS: PLANEJAMENTO | SPRINTS: 2-10 | DEPENDE DE: CLAUDE.md (Sprint 1 completa)
```

---

## VISÃO

O Controle de Bordo não é uma planilha glorificada. É um **sistema de inteligência financeira pessoal** que:

- Aprende o perfil financeiro do casal a cada mês processado
- Documenta sua própria infraestrutura conforme cresce
- Projeta cenários futuros baseado em dados reais
- Cruza metas de vida (apê, saúde, carreira) com capacidade financeira real
- Roda 100% local, sem dependência de cloud, com LLM local pra análise

---

## PRINCÍPIO ARQUITETURAL

```
Cada vez que o pipeline encontrar um tipo de arquivo novo,
ele DEVE documentar:
  1. Formato detectado (estrutura, encoding, delimitador)
  2. Campos extraídos e mapeamento pro schema
  3. Regras de parsing aplicadas
  4. Edge cases encontrados

Isso vai em: docs/extractors/BANCO_FORMATO.md (auto-gerado)

O projeto se auto-documenta. Nenhum conhecimento fica só no código.
```

---

## SPRINT 2 — EXTRATORES COMPLETOS + INFRA BASE

> Depende de: Sprint 1 (scaffold + Itaú + Nubank + XLSX writer)

### Entregas

- [ ] **Extrator Santander PDF** — fatura cartão de crédito
  - Parsear seções: Parcelamentos, Despesas, Pagamentos
  - Detectar compras internacionais (USD → BRL com cotação)
  - Extrair IOF como linha separada

- [ ] **Extrator C6 Bank** — CSV e/ou PDF
  - Detectar formato automaticamente (CSV Nubank-like vs PDF)
  - Separar CC, CDB, cartão

- [ ] **Extrator Caixa** — PDF extrato (salário Infobase)
  - Provavelmente protegido por senha

- [ ] **Extrator genérico de contas fixas**
  - Energia (Neoenergia): PDF ou screenshot → OCR
  - Água (CAESB): PDF boleto
  - Parser de boleto genérico: extrair valor, vencimento, beneficiário

- [ ] **Auto-documentação de formatos**
  ```
  docs/extractors/
  ├── itau_extrato_cc.md      # Auto-gerado na Sprint 1
  ├── nubank_csv.md            # Auto-gerado na Sprint 1
  ├── santander_fatura.md      # Auto-gerado agora
  ├── c6_csv.md
  ├── caixa_extrato.md
  └── neoenergia_fatura.md
  ```
  Cada doc contém: exemplo de input, colunas mapeadas, regex aplicados, problemas encontrados.

- [ ] **Makefile / Taskfile**
  ```makefile
  process:    ./run.sh $(MES)
  dashboard:  ./run.sh --dashboard
  test:       pytest tests/ -v
  lint:       ruff check src/
  docs:       python -m src.utils.doc_generator
  validate:   python -m src.utils.validator --mes $(MES)
  ```

- [ ] **CI local** — pre-commit hooks
  ```yaml
  # .pre-commit-config.yaml
  - ruff check
  - ruff format
  - sem dados financeiros no commit (grep sensível)
  - schema validation do XLSX
  ```

---

## SPRINT 3 — DASHBOARD STREAMLIT v1

> Depende de: Sprint 2 (todos os extratores)

### Entregas

- [ ] **Página: Visão Geral**
  - Cards: receita, despesa, saldo, economia vs mês anterior
  - Gráfico de barras: receita vs despesa por mês (últimos 6)
  - Gráfico pizza: distribuição por classificação (Obrigatório/Questionável/Supérfluo)
  - Indicador de saúde financeira (verde/amarelo/vermelho)

- [ ] **Página: Por Categoria**
  - Treemap interativo: categorias → subcategorias → transações
  - Ranking de categorias por valor
  - Evolução temporal de cada categoria (line chart)
  - Filtro por quem (André/Vitória/Casal)

- [ ] **Página: Extrato Completo**
  - Tabela interativa com filtros (data, banco, categoria, quem)
  - Busca por texto no campo local
  - Export pra CSV

- [ ] **Página: Contas e Dívidas**
  - Status de cada conta fixa (pago/pendente/atrasado)
  - Calendário de vencimentos do mês
  - Tracker da dívida Nubank (se estão deixando caducar: countdown pra prescrição)

- [ ] **Sidebar global**
  - Seletor de mês
  - Toggle André/Vitória/Casal
  - Saldo atual consolidado

- [ ] **Tema visual**
  - Dark mode (padrão, casal trabalha de noite)
  - Cores consistentes por categoria
  - Responsivo (funciona no celular pelo IP local)

---

## SPRINT 4 — INTELIGÊNCIA DE CATEGORIZAÇÃO

> Depende de: Sprint 3 (dashboard pra visualizar resultados)

### Entregas

- [ ] **Categorizer aprendiz**
  - Manter `mappings/overrides.yaml` onde o usuário corrige categorizações
  - Na próxima execução, overrides têm prioridade sobre regex
  - Log de "novos padrões detectados" que aparecem 3+ vezes sem match

- [ ] **Deduplicação inteligente**
  - Cruzar saídas de CC com entradas em cartão (pagamento de fatura)
  - Cruzar PIX entre contas próprias
  - Detectar a mesma transação aparecendo em 2 extratos (ex: Pix aparece no Itaú E no Nubank)
  - Marcar como `dedup: true` sem deletar (auditável)

- [ ] **Tag IRPF automática**
  - Rendimentos tributáveis: salários, PJ
  - Rendimentos isentos: rescisão até limite legal, FGTS, poupança
  - Despesas dedutíveis: consultas médicas (CNPJ de profissional de saúde)
  - Impostos pagos: DARF, DAS
  - Saldos em 31/12: snapshot automático dos saldos bancários

- [ ] **Validador de integridade**
  ```
  $ python -m src.utils.validator --mes 2026-04

   Total receitas bate com holerites
   Saldo final Itaú bate com extrato
   3 transações sem categoria (marcadas como Outros)
   Saldo C6 diverge em R$ 12,50 — verificar
  ```

---

## SPRINT 5 — RELATÓRIOS E PROJEÇÕES

> Depende de: Sprint 4 (dados limpos e categorizados)

### Entregas

- [ ] **Relatório mensal automático** (`data/output/YYYY-MM_relatorio.md`)
  ```markdown
  # Relatório Financeiro — Abril 2026

  ## Resumo
  - Receita: R$ 17.442,38
  - Despesa: R$ 11.823,45
  - Saldo: R$ 5.618,93
  - Economia vs março: +R$ 1.200

  ## Alertas
  -  Delivery subiu 30% vs mês anterior
  -  Energia caiu R$ 340 (tarifa social?)
  -  2 transações não categorizadas

  ## Metas
  - [■■■■■■░░░░] 60% — Meta de gasto < R$ 10k
  - [■■░░░░░░░░] 20% — Reserva de emergência (R$ 5k / R$ 27k)

  ## Projeção
  Se manter este ritmo:
  - Em 6 meses: R$ 33k guardados
  - Entrada do apê (R$ 50k): ~9 meses
  ```

- [ ] **Projetor de cenários**
  ```python
  # src/projections/scenarios.py

  cenarios = {
      "atual": {
          "receita": renda_atual,
          "despesa": media_3_meses,
      },
      "pos_infobase": {
          "receita": renda_atual - salario_infobase,
          "despesa": media_3_meses - economia_ifood,
      },
      "meta_ape": {
          "entrada": 50000,
          "poupanca_mensal": saldo_medio,
          "meses_ate_meta": entrada / poupanca_mensal,
      },
  }
  ```

- [ ] **Página Streamlit: Projeções**
  - Gráfico de linha: patrimônio acumulado ao longo do tempo
  - Slider: "se eu economizar R$ X por mês"
  - Marcos visuais: reserva de emergência → quitar dívida → entrada apê
  - Cenário "e se sair da Infobase" vs "e se ficar"

- [ ] **Página Streamlit: Metas e Sonhos**
  ```yaml
  # mappings/metas.yaml
  metas:
    - nome: "Reserva de emergência"
      valor_alvo: 27000
      prioridade: 1
      prazo: "2026-12"

    - nome: "Quitar dívida Nubank (Vitória)"
      valor_alvo: 10783
      prioridade: 2
      prazo: "2027-06"
      nota: "Ou deixar caducar até set/2030"

    - nome: "Plano de saúde ativo"
      tipo: "binário"
      prioridade: 1
      prazo: "2026-06"

    - nome: "Sair da Infobase"
      tipo: "binário"
      prioridade: 1
      prazo: "2026-07"
      depende_de: ["Reserva de emergência > 5000", "Plano de saúde ativo"]

    - nome: "Entrada apê Novo Gama"
      valor_alvo: 50000
      prioridade: 3
      prazo: "2028-06"

    - nome: "CNH (André + Vitória)"
      valor_alvo: 8000
      prioridade: 4
      prazo: "2027-06"

    - nome: "Filho"
      tipo: "binário"
      prioridade: 5
      prazo: "2028+"
      depende_de: ["Plano de saúde ativo", "Entrada apê"]
  ```
  - Grafo de dependências entre metas (meta X depende de Y)
  - Barra de progresso de cada meta (valor atual / alvo)
  - Timeline visual tipo Gantt simplificado

---

## SPRINT 6 — INTEGRAÇÃO OBSIDIAN

> Depende de: Sprint 5 (relatórios MD prontos)

### Entregas

- [ ] **Vault financeiro no Obsidian**
  ```
  obsidian-vault/
  ├── Financeiro/
  │   ├── Relatórios/
  │   │   ├── 2026-04.md          # Gerado pelo pipeline
  │   │   ├── 2026-03.md
  │   │   └── ...
  │   ├── Metas/
  │   │   ├── Reserva de Emergência.md
  │   │   ├── Apê Novo Gama.md
  │   │   └── ...
  │   ├── Dívidas/
  │   │   ├── Nubank Vitória.md
  │   │   └── ...
  │   └── Dashboard.md            # MOC (Map of Content)
  ```

- [ ] **Sync automático**
  - Após `./run.sh`, copiar relatório MD pro vault Obsidian
  - Manter backlinks entre relatórios, metas e dívidas
  - Usar frontmatter YAML pra Dataview queries

- [ ] **Template de relatório com frontmatter**
  ```markdown
  ---
  tipo: relatorio_mensal
  mes: 2026-04
  receita: 17442.38
  despesa: 11823.45
  saldo: 5618.93
  tags: [financeiro, mensal]
  ---

  # Abril 2026

  ## Resumo
  ...

  ## Links
  - [[Reserva de Emergência]] — progresso: 20%
  - [[Apê Novo Gama]] — progresso: 5%
  ```

- [ ] **Dataview queries pra Obsidian**
  ```dataview
  TABLE receita, despesa, saldo
  FROM "Financeiro/Relatórios"
  SORT mes DESC
  LIMIT 6
  ```

---

## SPRINT 7 — LLM LOCAL PARA ANÁLISE

> Depende de: Sprint 5 (dados limpos + relatórios)

### Contexto hardware
- Acer Nitro 5, Ryzen 5 7535HS, RTX 3050 Mobile 4GB VRAM
- Viável: Gemma 2 2B, Phi-3 Mini, Qwen2 1.5B (CPU) ou quantizado 4-bit na GPU

### Entregas

- [ ] **Módulo de análise LLM** (`src/analysis/llm_analyst.py`)
  ```python
  class FinancialAnalyst:
      """
      Usa LLM local pra gerar insights que regex não pega.

      Exemplos:
      - "Vocês gastaram R$ 800 com Shopee em 3 meses.
         60% foi skincare. Considerar assinatura mensal?"
      - "O gasto com delivery caiu 40% desde que
         começaram as marmitas. Economia acumulada: R$ 3.200"
      - "Padrão detectado: gastos aumentam na última
         semana do mês. Possível compra por impulso."
      """

      def __init__(self, model="gemma-2-2b-it-Q4_K_M.gguf"):
          self.model = model

      def analisar_mes(self, df_extrato, df_historico):
          prompt = self._build_prompt(df_extrato, df_historico)
          return self._query_local(prompt)

      def sugerir_cortes(self, df_extrato):
          """Identifica onde dá pra economizar."""
          pass

      def detectar_anomalias(self, df_extrato, df_historico):
          """Gastos fora do padrão."""
          pass

      def projetar_meta(self, meta, df_historico):
          """Dado o ritmo atual, quando atinge a meta?"""
          pass
  ```

- [ ] **Integração com pipeline**
  - Após gerar relatório MD, passa pro LLM local
  - LLM adiciona seção "Insights" no relatório
  - Insights ficam na aba `analise` do XLSX também

- [ ] **Fallback sem GPU**
  - Se não tiver GPU disponível, rodar em CPU com modelo menor
  - Se modelo não disponível, gerar análise baseada em regras (sem LLM)
  - O pipeline NUNCA deve falhar por falta de LLM

- [ ] **Possível integração futura com Luna**
  - Se Luna tiver bridge rodando, o Controle de Bordo pode enviar dados financeiros
  - Luna responde com análise conversacional
  - Isso é Sprint 10+ (não bloqueia nada)

---

## SPRINT 8 — DEVOPS E ROBUSTEZ

> Depende de: Sprint 4+

### Entregas

- [ ] **Testes automatizados**
  ```
  tests/
  ├── fixtures/
  │   ├── itau_sample.pdf         # Dados fictícios
  │   ├── nubank_sample.csv
  │   └── santander_sample.pdf
  ├── test_extractors.py
  ├── test_categorizer.py
  ├── test_deduplicator.py
  ├── test_xlsx_writer.py
  └── test_validator.py
  ```
  - Fixtures com dados fictícios (NUNCA dados reais no repo)
  - Coverage mínimo: 80% nos extractors e transform

- [ ] **GitHub Actions (CI)**
  ```yaml
  # .github/workflows/ci.yml
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
        - run: pip install -e ".[dev]"
        - run: pytest tests/ -v --tb=short
        - run: ruff check src/
  ```

- [ ] **Schema versioning**
  - XLSX schema muda entre sprints
  - Migrator automático: detecta versão do XLSX e atualiza se necessário
  - `src/migrations/` com scripts de migração

- [ ] **Backup automático**
  ```bash
  # No run.sh, antes de processar:
  cp data/output/controle_bordo_*.xlsx data/output/backup/$(date +%Y%m%d_%H%M%S)/
  ```

- [ ] **Logging estruturado**
  ```python
  # Cada extrator loga:
  logger.info("extrator.itau", extra={
      "arquivo": "itau_extrato.pdf",
      "paginas": 2,
      "transacoes_extraidas": 47,
      "categorias_mapeadas": 42,
      "sem_categoria": 5,
      "tempo_ms": 1200,
  })
  ```

- [ ] **Health check do pipeline**
  ```bash
  ./run.sh --check
  # Verifica: Python OK, deps OK, data/raw/ existe,
  # XLSX anterior existe, tesseract OK, espaço em disco OK
  ```

---

## SPRINT 9 — GRAFOS E VISUALIZAÇÕES AVANÇADAS

> Depende de: Sprint 5 + 7

### Entregas

- [ ] **Grafo de fluxo financeiro** (Streamlit + Plotly Sankey)
  ```
  Salário G4F ─────→ Itaú ─────→ Vitória (transferência)
                         ├──→ Santander (pagamento cartão)
                         ├──→ Neoenergia (energia)
                         ├──→ CAESB (água)
                         └──→ Nubank (pagamento cartão)

  Salário Infobase ──→ Caixa ──→ ...

  PJ Vitória ────────→ Nubank ─→ ...
  ```
  - Sankey diagram mostrando de onde vem e pra onde vai cada real
  - Filtro por mês, trimestre, ano
  - Destaque em vermelho: fluxos pra dívidas/juros

- [ ] **Grafo de dependência de metas** (networkx + Streamlit)
  ```
  [Plano de Saúde] ──depende──→ [MEI Vitória ativo]
  [Sair Infobase] ──depende──→ [Plano de Saúde]
                  ──depende──→ [Reserva > R$ 5k]
  [Apê Novo Gama] ──depende──→ [Reserva completa]
                  ──depende──→ [Quitar dívida OU caducar]
  [Filho] ──────────depende──→ [Apê]
                  ──depende──→ [Plano de Saúde c/ obstetrícia]
  ```

- [ ] **Heatmap de gastos**
  - Calendário estilo GitHub contributions
  - Cada dia = intensidade de gasto
  - Hover mostra detalhes

- [ ] **Trend analysis**
  - Média móvel 3 meses por categoria
  - Detecção de tendências (subindo/descendo/estável)
  - Sazonalidade (meses mais caros vs mais baratos)

---

## SPRINT 10 — AUTOMAÇÃO IRPF

> Depende de: Sprint 4 (tags IRPF) + Sprint 5 (relatórios)

### Entregas

- [ ] **Gerador de pacote IRPF**
  ```bash
  ./run.sh --irpf 2026

  # Output: data/output/irpf_2026/
  # ├── rendimentos_tributaveis.csv
  # ├── rendimentos_isentos.csv
  # ├── despesas_medicas_dedutiveis.csv
  # ├── inss_retido.csv
  # ├── irrf_retido.csv
  # ├── bens_direitos_31_12.csv
  # ├── saldos_bancarios_31_12.csv
  # └── resumo_irpf.md
  ```

- [ ] **Simulador completo vs simplificado**
  - Puxa dados do XLSX automaticamente
  - Calcula imposto devido nos dois modelos
  - Recomenda o melhor
  - Compara com IRRF já retido → estima a pagar/restituir

- [ ] **Checklist de documentos**
  - Gera lista do que precisa juntar
  - Marca o que já tem nos dados processados
  - Alerta o que falta (ex: "informe de rendimentos do banco X não encontrado")

- [ ] **Página Streamlit: IRPF**
  - Dashboard do ano-calendário acumulado
  - Barra: rendimentos tributáveis vs teto do simplificado
  - Lista de despesas dedutíveis com valor e comprovante (tem/não tem)
  - Simulação interativa: "se eu gastar R$ X em médico, quanto economizo?"

---

## SPRINTS FUTURAS (backlog)

### Sprint 11 — Alertas e notificações
- [ ] Bot Telegram ou notificação desktop
- [ ] Alerta de conta a vencer em 3 dias
- [ ] Alerta de gasto acima do orçamento
- [ ] Resumo semanal automático

### Sprint 12 — Multi-moeda e investimentos
- [ ] Rastrear cripto (já tem dados da exchange)
- [ ] Rastrear CDB, poupança, Tesouro Direto
- [ ] Calcular rentabilidade real (vs inflação)
- [ ] Consolidar patrimônio total

### Sprint 13 — API interna
- [ ] FastAPI servindo os dados do XLSX
- [ ] Endpoints: `/saldo`, `/gastos/{mes}`, `/metas`
- [ ] Integração com Luna via API local
- [ ] Webhook pra triggers (ex: "saldo < R$ 500")

### Sprint 14 — Mobile / PWA
- [ ] Streamlit PWA acessível pelo celular na rede local
- [ ] Input rápido: "gastei R$ 50 no mercado" via interface mínima
- [ ] Camera → OCR de recibo → auto-categoriza

### Sprint 15 — Orçamento participativo
- [ ] Definir orçamento por categoria
- [ ] Semáforo: verde (dentro), amarelo (80%), vermelho (estourou)
- [ ] Vitória e André veem o mesmo dashboard com visões diferentes

---

## REGISTRO DE INFRAESTRUTURA (auto-gerado)

O Opus DEVE manter este arquivo atualizado conforme constrói:

```
docs/INFRA.md

# Infraestrutura — Controle de Bordo

## Extratores implementados
| Banco | Formato | Status | Doc |
|-------|---------|--------|-----|
| Itaú | PDF s/ senha |  Sprint 1 | docs/extractors/itau.md |
| Nubank | CSV |  Sprint 1 | docs/extractors/nubank.md |
| Santander | PDF fatura |  Sprint 2 | docs/extractors/santander.md |
| ... | ... | ... | ... |

## Schema XLSX
| Aba | Colunas | Versão | Migração |
|-----|---------|--------|----------|
| extrato | 12 | v1.0 | — |
| renda | 8 | v1.0 | — |
| ... | ... | ... | ... |

## Categorias mapeadas
| Regex | Categoria | Hits total | Última ocorrência |
|-------|-----------|-----------|-------------------|
| IFD\*|IFOOD | Delivery | 234 | 2026-04-13 |
| ... | ... | ... | ... |

## Decisões técnicas
| Data | Decisão | Motivo |
|------|---------|--------|
| 2026-04-14 | pdfplumber > tabula pra Itaú | tabula não lidou com layout |
| ... | ... | ... |
```

**Regra: a cada arquivo novo processado pela primeira vez, o Opus atualiza INFRA.md.**

---

## PRIORIZAÇÃO GERAL

```
Sprint 1  ████████ MVP: extrair, categorizar, gerar XLSX
Sprint 2  ████████ Todos os bancos + auto-doc
Sprint 3  ██████── Dashboard Streamlit v1
Sprint 4  ██████── Inteligência: dedup, IRPF tags, validação
Sprint 5  █████─── Relatórios + projeções + metas
Sprint 6  ████──── Obsidian sync
Sprint 7  ████──── LLM local
Sprint 8  ███───── DevOps: testes, CI, backup
Sprint 9  ███───── Grafos e viz avançada
Sprint 10 ██────── IRPF automação completa
Sprint 11+        Alertas, API, mobile, orçamento
```

**Filosofia: cada sprint entrega valor usável. Nunca ficar 3 sprints sem output concreto.**

---

## COMO O OPUS DEVE AGIR

1. **Ler CLAUDE.md primeiro** → montar Sprint 1
2. **Ler CLAUDE_2.md** → entender o norte, mas NÃO tentar fazer tudo de uma vez
3. **A cada arquivo novo em `data/raw/`**: ler, entender, documentar em `docs/extractors/`, implementar extrator
4. **A cada sprint completa**: atualizar `docs/INFRA.md`, rodar testes, validar XLSX
5. **Nunca quebrar o que já funciona** — testes de regressão antes de merge
6. **Se não souber algo**: documentar a dúvida em `docs/TODO.md` e seguir
7. **Dados reais NUNCA no Git** — `data/` no `.gitignore`, fixtures com dados fictícios

---

*"Um sistema inteligente não é o que faz tudo. É o que sabe o que fazer primeiro."*
