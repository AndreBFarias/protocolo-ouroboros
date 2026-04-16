# Roadmap -- Protocolo Ouroboros

```
VERSÃO: 4.1 | SPRINTS: 29 (14 concluídas, 15 pendentes)
CÉREBRO INTELIGENTE: sprints 26-29 (propostas em 2026-04-16)
ÚLTIMA ATUALIZAÇÃO: 2026-04-16 (renumeração fecha gap da antiga Sprint 07)
```

---

## Visão

Sistema de inteligência financeira pessoal para o casal André e Vitória. Pipeline ETL que centraliza dados bancários de múltiplas fontes em XLSX consolidado, dashboard Streamlit, relatórios mensais, integração Obsidian e -- a partir das sprints 26-29 -- grafo de conhecimento com LLM orquestrado.

**Evolução em três horizontes:**
1. **Curto (pendentes + visão)**: dashboard redesign, relatórios diagnósticos, consolidação, automação bancária, pacote IRPF.
2. **Médio (cérebro inteligente 26-29)**: ingestão universal, grafo de conhecimento, LLM orquestrado via Claude Opus, UX navegável.
3. **Longo (futuro)**: LLM local, grafos analíticos, unificação com Controle_de_Bordo_OS e vault Obsidian em ecossistema único.

---

## Estado atual -- mapa por status

| Status | Sprints | Total |
|--------|---------|-------|
| Concluídas | 01, 02, 03, 04, 05, 06, 07, 12, 13, 14 (parcial), 17, 18, 19, 23 (parcial) | 14 |
| Pendentes (execução imediata) | 20, 21, 22 | 3 |
| Visão | 24, 25 | 2 |
| Cérebro Inteligente (propostas 2026-04-16) | 26, 27, 28, 29 | 4 |
| Futuro / backlog | 08, 09, 10, 11, 15, 16 | 6 |

---

## Sprints Concluídas (14)

| Sprint | Tema | Issue |
|--------|------|-------|
| 01 | MVP: pipeline ETL + 6 extratores + XLSX 8 abas | #1 |
| 02 | Infra: categorização 100%, Makefile, OCR | #2 |
| 03 | Dashboard Streamlit v1 (6 abas, dark mode) | #3 |
| 04 | Inteligência: overrides, IRPF tagger, validador | #4 |
| 05 | Relatórios + Projeções (3 cenários, 7 metas) | #5 |
| 06 | Integração Obsidian (frontmatter quebrado pendente na 22) | #6 |
| 07 | Dashboard v2 (Dracula theme) | #15 |
| 12 | Rebranding Protocolo Ouroboros | #16 |
| 13 | UI/UX e outputs profissionais | #17 |
| 14 | Acentuação e qualidade (parcial -- completada na 18) | #18 |
| 17 | Auditoria Final (GitHub-readiness) | #19 |
| 18 | Dívida técnica (acentuação + deduplicação) | #20 |
| 19 | Bugs críticos (crashes, projeções, classificação) | #21 |
| 23 | Verdade nos dados (parcial: análise quali/quanti, CNPJ) | #22 |

---

## Sprints Pendentes -- execução imediata (3)

### Sprint 20 -- Dashboard Redesign
CSS refinado, tipografia, layout responsivo. Pré-requisito informal das Sprints 26-29.

### Sprint 21 -- Relatórios Diagnósticos
Contextualização, detecção de anomalias, comparação inter-mensal. Evolução dos relatórios MD automáticos.

### Sprint 22 -- Consolidação
Corrigir módulos fantasmas (`health_check.py`, `doc_generator.py`), registrar `energia_ocr.py` no pipeline, reparar frontmatter do sync Obsidian. **Bloqueio da Sprint 29.**

---

## Sprints Visão (2)

### Sprint 24 -- Automação Bancária
OFX manual (feito), Belvo (inviável gratuito -- ver `docs/AUTOMACAO_BANCARIA.md`), Gmail API (setup pendente), MeuPluggy (a testar). Em andamento.

### Sprint 25 -- Pacote IRPF (Declaração Facilitada)
Organização de documentos por tipo, extração de CNPJ aprimorada, resumo IRPF, eventual export `.DEC` da Receita. Alinha-se com Sprint 27 (grafo) e Sprint 10 (simulação tributária futura).

---

## Cérebro Inteligente -- propostas 2026-04-16 (4)

Quatro sprints grandes que transformam o pipeline em sistema de conhecimento financeiro. Detalhamento nos arquivos linkados.

### Sprint 26 -- Ingestão Universal de Documentos  ([#11](https://github.com/AndreBFarias/protocolo-ouroboros/issues/11))
Qualquer PDF/imagem de boleto/NF/fatura/contrato ingerido via inbox, Gmail, Drive ou upload vira nó `Documento` com campos estruturados. OCR cascata (pdfplumber → Tesseract → Donut/LayoutLMv3 → API externa opt-in).
[`docs/sprints/sprint_26_ingestao_universal.md`](sprints/sprint_26_ingestao_universal.md)

### Sprint 27 -- Grafo + Classificação v2  ([#12](https://github.com/AndreBFarias/protocolo-ouroboros/issues/12))
SQLite `nodes`/`edges` com motores de linking (doc↔transação), resolução fuzzy de entidades, detecção de eventos (parcelamento, assinaturas). Refactor do categorizador para contexto e score.
[`docs/sprints/sprint_27_grafo_classificacao.md`](sprints/sprint_27_grafo_classificacao.md)

### Sprint 28 -- LLM Orquestrado via Claude  ([#13](https://github.com/AndreBFarias/protocolo-ouroboros/issues/13))
Claude Opus como LLM padrão. Provider abstrato permite troca futura pra local (Sprint 08). Contratos Pydantic, prompts versionados, cache SQLite, slash commands Claude Code como copiloto de manutenção.
[`docs/sprints/sprint_28_llm_orquestrado.md`](sprints/sprint_28_llm_orquestrado.md)

### Sprint 29 -- UX Navegável  ([#14](https://github.com/AndreBFarias/protocolo-ouroboros/issues/14))
Busca global, timeline por entidade/evento/pessoa, navegador de grafo visual (pyvis), Obsidian rico com attachments, "abrir PDF original" em qualquer lugar, página "vida de um boleto".
[`docs/sprints/sprint_29_ux_navegacao.md`](sprints/sprint_29_ux_navegacao.md)

---

## Futuro / Backlog (6)

### Sprint 08 -- LLM Local
Fica como **backend alternativo** da Sprint 28. Retomar quando Gemma/Phi-3 tiverem qualidade comparável ao Opus e o custo da API justificar troca.

### Sprint 09 -- Grafos Analíticos
Sankey, heatmap GitHub-style, trend analysis. **Complementar** (não substituto) da Sprint 29: 29 é navegação exploratória, 09 é síntese agregada.

### Sprint 10 -- IRPF Completo (Simulação + Interface)
Simulador completo vs simplificado, página Streamlit dedicada, cálculo de economia fiscal. Depende de Sprint 25.

### Sprint 11 -- Vault Final
Decisão arquitetural de unificação com Controle_de_Bordo_OS (hexagonal, Pydantic, SQLite+WAL, event bus) e vault Obsidian. Migração `JSON → DUAL_WRITE → DUAL_READ → SQLITE_ONLY`.

### Sprint 15 -- Dashboard Polish Visual
Absorvida parcialmente pela Sprint 20. Resíduo: ajustes de micro-UX.

### Sprint 16 -- Testes e CI/CD
Expandir gauntlet, fixtures sintéticas de formatos faltantes, GitHub Actions em push/PR, coverage.

---

## Ordem de execução sugerida

```
Horizonte 1 -- estabilizar base (4-6 semanas)
  └─ 23 Consolidação ──► 21 Dashboard Redesign ──► 22 Relatórios Diagnósticos

Horizonte 2 -- fechar operação manual (2-3 semanas)
  └─ 25 Automação Bancária (OFX + MeuPluggy) ──► 26 Pacote IRPF v1

Horizonte 3 -- cérebro inteligente (12-16 semanas)
  └─ 27 Ingestão Universal ──► 28 Grafo + Classificação v2 ──► 29 LLM Orquestrado ──► 30 UX Navegável

Horizonte 4 -- maturação (execução paralela, conforme prioridade)
  ├─ 11 IRPF Simulação
  ├─ 10 Grafos Analíticos
  ├─ 17 Testes e CI/CD
  └─ 09 LLM Local (gatilho: Opus caro OU local bom o bastante)

Horizonte 5 -- unificação (indefinido)
  └─ 12 Vault Final (absorção do ecossistema)
```

---

## Ecossistema de 3 Projetos

| Projeto | Caminho | Descrição |
|---------|---------|-----------|
| **Protocolo Ouroboros** (este) | `~/Desenvolvimento/protocolo-ouroboros` | Pipeline ETL financeiro maduro, grafo de conhecimento em construção |
| **Controle_de_Bordo_OS** | `~/Desenvolvimento/Controle_de_Bordo_OS` | Blueprint arquitetural hexagonal, 20 sprints planejadas |
| **Vault Obsidian** | `~/Controle de Bordo` | 1.202 notas, 24 plugins, organização PARA |

A Sprint 11 avaliará a estratégia de unificação. As sprints 26-29 já produzem dados compatíveis com o vault Obsidian (notas por entidade, attachments).

---

## Priorização visual

```
Horizonte 1 (base)
  21  ██████── Dashboard Redesign
  22  █████─── Relatórios Diagnósticos
  23  ████──── Consolidação (bloqueio da 30)

Horizonte 2 (operacional)
  25  ███───── Automação Bancária (OFX + MeuPluggy)
  26  ███───── Pacote IRPF v1

Horizonte 3 (cérebro inteligente)
  27  ██████── Ingestão Universal
  28  ██████── Grafo + Classificação v2
  29  █████─── LLM Orquestrado
  30  █████─── UX Navegável

Horizonte 4 (maturação)
  11  ███───── IRPF Simulação
  10  ██────── Grafos Analíticos
  17  ██────── Testes e CI/CD
  09  █─────── LLM Local

Horizonte 5 (unificação)
  12  █─────── Vault Final
```

---

## Referências

- Contexto técnico: [`CLAUDE.md`](../CLAUDE.md)
- Onboarding rápido: [`GSD.md`](../GSD.md)
- Armadilhas conhecidas: [`docs/ARMADILHAS.md`](ARMADILHAS.md)
- Arquitetura: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Dados faltantes: [`DADOS_FALTANTES.md`](../DADOS_FALTANTES.md)
- Automação bancária: [`docs/AUTOMACAO_BANCARIA.md`](AUTOMACAO_BANCARIA.md)

---

*"Um sistema inteligente não é o que faz tudo. É o que sabe o que fazer primeiro."*
