# Visão Unificada — Protocolo Ouroboros + Controle de Bordo

**Última atualização:** 2026-04-21 tarde
**Escopo:** síntese da arquitetura, fases, sprints e decisões após a sessão onde o Andre compartilhou a visão real do projeto.

---

## O que é (em 1 parágrafo)

Uma central de tudo para o casal André + Vitória, começando pela gestão financeira. Andre joga qualquer documento (foto de boleto, PDF de NFe, CSV bancário, recibo, receita médica) na **inbox única do Controle de Bordo**. O Ouroboros processa, extrai, categoriza, vincula no grafo SQLite e gera notas estruturadas de volta no vault Obsidian. Dashboard Streamlit é a camada interativa; Obsidian é a navegação livre. Clicar em "Natação André" abre boleto + recibo. O workflow cabe em um `./run.sh`.

---

## Dois repositórios, um sistema

```
~/Controle de Bordo/                      ~/Desenvolvimento/protocolo-ouroboros/
(vault Obsidian -- hub de vida)           (pipeline ETL financeiro)

  Inbox/  <-----[ADAPTER Sprint 70]------ src/integrations/controle_bordo.py
    |                                                     |
    | motor do vault:                                     | motor do Ouroboros:
    | docs pessoais, notas rápidas                        | OFX, CSV, PDFs financeiros
    | .sistema/scripts/inbox_processor.py                 | src/inbox_processor.py
    |                                                     |
    V                                                     V
  Pessoal/Documentos/                             data/raw/originais/  (preserva)
  Pessoal/Andre/                                  data/raw/{pessoa}/{banco}/
  Pessoal/Vitoria/                                         |
  Pessoal/Casal/                                           V
    Financeiro/    <--[SYNC Sprint 71]----     pipeline de extração + grafo SQLite
      Documentos/{YYYY-MM}/                    data/output/grafo.sqlite
      Fornecedores/                            data/output/ouroboros_2026.xlsx
      Meses/                                          |
      _Attachments/                                   V
      Dashboard.md                             dashboard Streamlit  (porta 8501)
  .sistema/                                          + relatórios mensais .md
    scripts/, config/, docs/                         + sync Obsidian rico
```

**Regra de coabitação (ADR-18):** arquivo financeiro é do Ouroboros, o resto fica com o motor do vault. Cópia do original SEMPRE preservada em `data/raw/originais/{hash}.ext`.

---

## Ciclo canônico (visão Andre, fase KAPPA)

```
1. Andre tira foto do boleto OU joga PDF/CSV na inbox do vault
2. Roda ./run.sh
3. Menu interativo aparece (Sprint 80):
   [1] Processar Inbox
   [2] Dashboard
   [3] Relatório do período
   [4] Sync Obsidian
   [5] Tudo
4. Opção 5: adapter (Sprint 70) varre inbox, roteia financeiros, preserva originais
5. Pipeline extrai dados, popula grafo, atualiza XLSX
6. Sync rico (Sprint 71) escreve notas .md no vault
7. Pergunta: abrir dashboard, gerar relatório, ambos, nada?
8. Andre navega no dashboard:
   - Vê anomalia -> clica ponto -> vai para Extrato filtrado (Sprint 73)
   - Clica "Natação André" -> modal com boleto + recibo inline (Sprint 74)
   - Vai em Completude -> vê gap "Farmácia 0/37 comprovantes" (Sprint 75)
   - Abre Obsidian lado a lado -> mesmo dado, outra navegação
9. Leva relatório .md para análise LLM online se quiser feedback mais profundo
```

---

## Mapa das fases

| Fase | Nome | Status | Resumo |
|---|---|---|---|
| ALFA | Resíduos técnicos retroativos | CONCLUÍDA | Fixes pós-MVP (37-40) |
| BETA | Infra universal (intake + grafo + workflow supervisor) | CONCLUÍDA | Sprints 41-43 |
| GAMA | Extratores por formato | CONCLUÍDA | Sprints 44-47 |
| DELTA | Linking e classificação de itens | CONCLUÍDA | Sprints 48-50 (mas grafo real vazio -- Sprint 57 expôs) |
| EPSILON | UX inicial (dashboard, busca, grafo visual v1) | CONCLUÍDA | Sprints 51-53 |
| **ETA** | **Correções da auditoria 2026-04-21** | **quase completa** | **Sprints 55-69 (só 68b residual)** |
| **IOTA** | **Integração Controle de Bordo** | **BACKLOG** | **Sprints 70-71** |
| **KAPPA** | **UX polish + tracking documental + workflow** | **BACKLOG** | **Sprints 72-81** |
| ZETA | Consumo dos dados granulares (LLM narrativo, IRPF completo, métricas IA) | BACKLOG | Sprints 20, 21, 24, 25, 33-36 -- depois de IOTA+KAPPA |

---

## ADRs ativos

| ID | Tema | Status |
|---|---|---|
| ADR-07 | Local First | ATIVO |
| ADR-08 | Supervisor-Aprovador | ATIVO |
| ADR-09 | Autossuficiência progressiva | ATIVO |
| ADR-10 | Resiliência a dados incompletos | ATIVO |
| ADR-11 | Classificação em camadas | ATIVO |
| ADR-12 | Cruzamentos via grafo | ATIVO |
| ADR-13 | Claude Code como supervisor (sem API programática) | ATIVO |
| ADR-14 | Grafo SQLite extensível (tipos canônicos fechados + metadata) | ATIVO |
| **ADR-18** | **Integração Controle de Bordo (coabitação estrutural)** | **PROPOSTO 2026-04-21** |
| **ADR-19** | **Dashboard interativo drill-down** | **PROPOSTO 2026-04-21** |
| **ADR-20** | **Tracking documental completo** | **PROPOSTO 2026-04-21** |

---

## Sprints backlog -- resumo executivo

### Fase ETA -- sprint-nova derivada (1)
- **82** -- Canonicalizer variantes curtas + conta-espelho de cartão (achado 68b-A) -- P1

### Fase IOTA (2)
- **70** -- Inbox unificada (P0)
- **71** -- Sync rico bidirecional (P1)

### Fase KAPPA (10)
- **72** -- Filtro forma de pagamento (P1)
- **73** -- Dashboard interativo drill-down (P1)
- **74** -- Vinculação transação↔documento + modal (P0)
- **75** -- Gap analysis (P1)
- **76** -- UX v1: fonte mínima 13px, logo, centralização (P1)
- **77** -- UX v2: treemap, legendas, filtros avançados (P1)
- **78** -- Grafo Obsidian-like (P1)
- **79** -- Aba Pagamentos (P2)
- **80** -- run.sh interativo (P2)
- **81** -- Sweep higiene (P3)

### Fases antigas ainda em backlog
- **ALFA→EPSILON residuais (11):** 46-53 (46 em execução, 48/49/50 precisam dados reais)
- **ZETA (8):** 20, 21, 24, 25, 33, 34, 35, 36

---

## Caminho crítico recomendado (próxima janela)

```
68b termina -> 81 (baseline limpa)
    ↓
70 (adapter Controle de Bordo)
    ↓
76 (UX v1 visual)  +  74 (vínculo doc↔tx) em paralelo
    ↓
72 (filtro forma)
    ↓
71 (sync rico) + 73 (drill-down) em paralelo
    ↓
77 (UX v2) + 80 (run.sh menu) em paralelo
    ↓
75 (gap analysis) -> 78 (grafo full) -> 79 (pagamentos)
    ↓
Fase ZETA (consumo dos dados: relatórios narrativos, pacote IRPF, métricas)
```

**Estimativa grosseira de esforço (cada uma é 1 sessão de executor opus + validação manual):**

- Fase IOTA: 2 sessões
- Fase KAPPA: 10 sessões (algumas paralelizáveis)
- Total até Fase ZETA começar: ~8 sessões efetivas (com paralelização)

---

## Princípios de trabalho desta sessão

1. **Opus planeja e valida** (eu). **Sonnet executa** (subagents via `executor-sprint`, default). Haiku apenas para higiene trivial (sweep de lint, mover arquivo).
2. **Evidência empírica > hipótese do planejador** (meta-regra 6). Executor verifica por `rg` antes de tocar identificador.
3. **Zero follow-up acumulado** (meta-regra 7). Todo achado vira sprint-nova OU Edit pronto.
4. **Validação runtime-real obrigatória** (check #1). `./run.sh --check` + `make smoke` + validação visual via Playwright quando diff toca UI.
5. **Preservação do original** (ADR-18). Nenhum arquivo do usuário é mexido sem cópia em `data/raw/originais/`.
6. **Nunca invadir vault fora do escopo.** `.sistema/`, `Trabalho/`, `Segredos/`, `Arquivo/` são off-limits para o Ouroboros.

---

## Pendências para decisão do Andre

Antes de despachar a Fase IOTA, confirmar (ADR-18 tem as perguntas explícitas):

1. **Mapeamento `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}.md` OK?** Ou prefere outro layout?
2. **OK consumir `~/Controle de Bordo/Inbox/` diretamente**, ou quer uma subfolder dedicada `Inbox/financeiro/`?
3. **Aceita que documentos pessoais (RG, CV, apólices) fiquem FORA** do escopo do Ouroboros por enquanto (só financeiro)?

E para a Fase KAPPA:

4. **Logo visual:** tem arte/SVG preferido, ou placeholder stylizado está OK?
5. **Categorias com tracking obrigatório** (Sprint 74): Farmácia, Saúde, Aluguel, Educação, Impostos, Seguros, Plano de saúde. Adicionar/remover?
6. **Frequência do menu interativo:** toda vez que roda `./run.sh` sem args, ou apenas em modo `--interativo`?

---

## Notas pessoais que informam o design

Esta sessão o Andre compartilhou contexto que estava ausente da documentação técnica. Fica registrado aqui porque vai pautar decisões:

- Duas jornadas de trabalho (MEC via G4F + Energisa). Saída sistemática, não abrupta.
- TDAH + Venvanse (uso deve ser 1 comprimido/dia; estava em 2).
- Muitos gastos psiquiátricos (Clínica Ludens) — tracking obrigatório para IRPF.
- Padaria Ki-Sabor R$ 800-900/mês = aluguel.
- Pressão financeira: dívidas crescendo apesar dos 2 trampos.
- Sem exercício, pouca comida caseira, estresse.
- Sênior em Python — consegue ler tudo, só não tem tempo/cabeça.

O projeto não é só técnico. É ferramenta de clareza para sair do ciclo.

---

*"Memória em disco, não em contexto. Ciclo em uma janela. Rigor de duas abas."*
