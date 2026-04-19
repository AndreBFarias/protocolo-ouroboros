# Roadmap -- Protocolo Ouroboros

```
VERSÃO: 5.3 | SPRINTS: 42 (20 concluídas, 0 em produção, 15 backlog, 7 arquivadas)
ROTA: Re-roadmap como catalogador universal artesanal (ver `/home/andrefarias/.claude/plans/sprint-fluffy-puddle.md` para plano completo)
ÚLTIMA ATUALIZAÇÃO: 2026-04-19 (Sprints 37-40 documentadas e fechadas)
```

---

## Visão

Sistema de inteligência financeira pessoal para o casal André e Vitória. Pipeline ETL que centraliza dados bancários de múltiplas fontes em XLSX consolidado, dashboard Streamlit, relatórios diagnósticos, integração Obsidian e -- a partir da Fase 2 -- supervisor de melhoria contínua orientado por LLM que propõe regras ao pipeline determinístico para humano aprovar. A cada aprovação o pipeline cresce e a dependência do LLM diminui. O fim do caminho é um sistema autossuficiente.

**Princípio central:** LLM nunca escreve direto em produção -- sempre propõe, humano aprova via dashboard, PR automática atualiza `mappings/*.yaml`. Dados faltantes afetam apenas o relatório final, nunca travam o cérebro.

**Horizontes:**
1. **Fase 1 (30 dias)** -- base honesta + supervisor IA Modo 1.
2. **Fase 2 (60 dias)** -- redesign aprovado + IA ativa em OCR, narrativa, auditor, IRPF.
3. **Fase 3 (90 dias)** -- cérebro MVP com grafo, busca, consulta natural.
4. **Pós-90d** -- automação bancária, pacote IRPF completo, grafo avançado, UX rica.

---

## Estado atual -- mapa por status

| Status | Sprints | Total |
|--------|---------|-------|
| Concluídas | 01, 02, 03, 04, 05, 06, 07, 12, 13, 14, 17, 18, 19, 22, 23, 30, 37, 38, 39, 40 | 20 |
| Backlog ativo (Fases 1-3) | 20, 21, 27a, 28, 29a, 30, 31, 32, 33, 34, 35, 36 | 12 |
| Backlog pós-90d | 24, 25, 27b, 29b | 4 |
| Arquivadas | 08 (CAN), 09 (ABS), 10 (CAN), 11 (CAN), 15 (ABS), 16 (ABS), 26 (OBS) | 7 |

CAN=cancelada, ABS=absorvida, OBS=obsoleta. Cabeçalho de cada arquivada detalha motivo e sprint substituta.

---

## Fase 1 -- Base honesta + supervisor IA (30 dias)

Objetivo: encerrar dívidas documentais, garantir testes mínimos, habilitar Claude como auditor do pipeline determinístico.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 22 | Consolidação: lacunas de base + sync docs | CONCLUÍDA | CRÍTICA |
| 23 | Verdade nos Dados: abas fantasmas + CNPJ contextual | CONCLUÍDA | ALTA |
| 21 | Relatórios Diagnósticos (comparativo 3 meses) | PENDENTE | ALTA |
| 30 | Base Honesta: testes mínimos (40% em transform/ e extractors/) | CONCLUÍDA | CRÍTICA |
| 31 | Infra LLM + Supervisor Modo 1 (propõe regras novas) | PENDENTE | CRÍTICA |
| 20 | Dashboard Redesign (mockups ASCII antes de CSS) | PENDENTE | ALTA (Fase 1 parcial + Fase 2 conclusão) |

Sequência sugerida: **22 → 23 → 30 → 31 → 21 → 20 (mockups)**.

---

## Fase 2 -- IA ativa + Redesign completo (60 dias)

Objetivo: LLM agregando valor em OCR, narrativa diagnóstica, auditoria de outputs e loop IRPF. Dashboard visualmente maduro com métricas de autossuficiência.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 20 | Dashboard Redesign (implementação CSS pós-mockups) | PENDENTE | ALTA |
| 32 | OCR Energia via Visão do LLM (67% → 98%) | PENDENTE | MÉDIA |
| 33 | Resumo Mensal Narrativo (diagnóstico enriquecido) | PENDENTE | MÉDIA |
| 34 | Supervisor Modo 2 (auditor batch de outputs) | PENDENTE | ALTA |
| 35 | IRPF como YAML (habilita loop sem edit de .py) | PENDENTE | MÉDIA |
| 36 | Métricas IA: termômetro da autossuficiência | PENDENTE | MÉDIA |

---

## Fase 3 -- Cérebro MVP (90 dias)

Objetivo: grafo de conhecimento mínimo, busca global, consulta em linguagem natural.

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 27a | Grafo SQLite mínimo + entity resolution | PENDENTE | ALTA |
| 29a | Busca global + abrir PDF + timeline + pergunte NL | PENDENTE | ALTA |
| 28 | LLM Orquestrado -- índice dos 3 modos + ADR-08 | PENDENTE | ALTA |

---

## Pós-90d -- expansão e maturação

| Sprint | Tema | Status | Prioridade |
|--------|------|--------|------------|
| 24 | Automação Bancária (Belvo, Gmail watcher, MeuPluggy) | PENDENTE | BAIXA |
| 25 | Pacote IRPF completo (declaração anual + simulador) | PENDENTE | BAIXA |
| 27b | Grafo avançado (Motor 1 linking, Motor 3 eventos, visualização) | PENDENTE | BAIXA |
| 29b | UX rica (grafo visual pyvis, Obsidian enriquecido, MOCs) | PENDENTE | BAIXA |

---

## Sprints arquivadas

| Sprint | Status | Motivo | Substituída por |
|--------|--------|--------|-----------------|
| 08 | CANCELADA | API externa custa $2-5/mês com cache; hardware local não se justifica. | 31 |
| 09 | ABSORVIDA | Sankey e heatmap passam a 27b. | 27b |
| 10 | CANCELADA | IRPF 2026 já declarado manualmente; 25 e 35 cobrem 2027+. | 25, 35 |
| 11 | CANCELADA | Unificação arquitetural é armadilha ambiciosa. | -- |
| 15 | ABSORVIDA | Polish fundido na 20. | 20 |
| 16 | ABSORVIDA | Testes mínimos viram parte da 30; CI cobre nos hooks portados. | 30 |
| 26 | OBSOLETA | Escopo original é 3-4 sprints; enriquecimento essencial via LLM fica em 28/32. | 28, 32 |

---

## Ordem de execução recomendada

```
Fase 1 -- 30 dias: base honesta + supervisor IA
  └─ 22 Consolidação ──► 23 Verdade nos Dados ──► 30 Testes ──► 31 Supervisor IA
     └─ (em paralelo) 21 Relatórios Diagnósticos ──► 20 Mockups

Fase 2 -- 60 dias: IA ativa + dashboard maduro
  └─ 20 CSS ──► 32 OCR Vision ──► 33 Narrativa ──► 34 Auditor Modo 2 ──► 35 IRPF YAML ──► 36 Métricas IA

Fase 3 -- 90 dias: cérebro MVP
  └─ 27a Grafo SQLite ──► 29a Busca + NL + Timeline ──► 28 ADR-08 (consolidação)

Pós-90d (prioridade sob demanda)
  ├─ 24 Automação Bancária
  ├─ 25 Pacote IRPF completo
  ├─ 27b Grafo avançado
  └─ 29b UX rica (Obsidian + pyvis)
```

---

## Workflow de sprints

Layout em `docs/sprints/{backlog,producao,concluidos,arquivadas}`. Template canônico em `docs/templates/SPRINT_TEMPLATE.md`. Scripts:

- `scripts/audit_sprint_coverage.py` -- auditoria de cobertura doc ↔ git log
- `scripts/ci/validate_sprint_structure.py` -- bloqueia CI se sprint ativa estiver fora do padrão
- `scripts/finish_sprint.sh NN` -- encerra sprint (valida, atualiza Status, move para concluidos)
- `hooks/sprint_auto_move.py` -- pre-commit move automática conforme Status

---

## Ecossistema

| Projeto | Caminho | Papel |
|---------|---------|-------|
| Protocolo Ouroboros (este) | `~/Desenvolvimento/protocolo-ouroboros` | Pipeline ETL financeiro + cérebro em construção |
| Luna | `~/Desenvolvimento/Luna` | Fonte da infra de hooks e workflow de sprints (portado em 2026-04-18) |
| Vault Obsidian | `~/Controle de Bordo` | Destino do sync (frontmatter YAML, MOCs pós-Sprint 29b) |

---

## Referências

- Plano 30/60/90 aprovado: `/home/andrefarias/.claude/plans/o-que-eu-quero-twinkly-wreath.md`
- Contexto técnico: [`CLAUDE.md`](../CLAUDE.md)
- Onboarding rápido: [`GSD.md`](../GSD.md)
- Armadilhas conhecidas: [`ARMADILHAS.md`](ARMADILHAS.md)
- Arquitetura: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Dados faltantes: [`../DADOS_FALTANTES.md`](../DADOS_FALTANTES.md)
- Template de sprint: [`templates/SPRINT_TEMPLATE.md`](templates/SPRINT_TEMPLATE.md)

---

*"Um sistema inteligente não é o que faz tudo. É o que sabe o que fazer primeiro."*
