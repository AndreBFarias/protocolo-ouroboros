---
titulo: Estado do todo 2026-05-08 — visão executiva consolidada
data: 2026-05-08
escopo: projeto inteiro (dashboard + ETL + grafo + XLSX + mob)
audiencia: dono
referencias:
  - docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md
  - docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md
  - docs/auditorias/VALIDACAO_END2END_2026-05-08.md
---

# Estado do todo — 8 de maio de 2026

## TL;DR

O projeto está **75% montado** como infraestrutura sólida e **<5% no salto de inteligência prometido**. O dashboard é bonito e funcional para o que tem; falta ETL profundo (vínculo cupom-transação, itens individualizados, OCR de imagem). Mob v1.0.0 não republicou ainda e bloqueia 29% das páginas Bem-estar. Skills D7 + Inbox + Memórias acabaram de ganhar fundação (Batch 6 hoje).

**Caminho para "100% real" deste lado**: 5 sprints INFRA fim-a-fim (~25h, paralelizável → ~8h wall clock).

**Caminho para "100% completo"**: Fase 1 (deste lado) + Mob v1.0.0 republicar (~50h paralelo, fora deste worktree).

---

## 1. O que JÁ funciona (tem que celebrar)

### Dashboard (15 páginas com dado real ou determinístico ≥95%)

- **Visão Geral, Extrato, Contas, Pagamentos, Projeções, Busca, Catalogação, Completude, Categorias, Análise, Metas, IRPF, Inbox** (com leitor pós-batch 6).
- **Revisor + Validação Tripla**: estrutura completa, Opus simulado via supervisor artesanal (ADR-13).
- **be_rotina, be_privacidade, be_editor_toml, be_cruzamentos, be_recap (parcial)**: lendo TOML/cache local.

### ETL produtivo

- **6094 transações** (8 abas XLSX, 82 meses, 6 bancos).
- **24/24 holerites** + **19/19 DAS PARCSN** + **413/413 extratos bancários** (OFX/CSV/XLS).
- **1106 fornecedores** normalizados.
- **104 categorias** com auto-classificação.
- **6127 edges** transação ↔ categoria (100% das transações categorizadas).

### Auditoria visual completa pós-Onda V

- 28 páginas auditadas side-by-side com mockups canônicos.
- 9 retoques visuais finais aplicados ao vivo (UX-V-FINAL-FIX + 2 da topbar/scroll).
- 33 sprints de correção integradas com gauntlet verde (lint+smoke+pytest 2671 passed).

---

## 2. O que NÃO funciona (gap crítico)

### Salto da inteligência (visão prometida)

| Pergunta canônica | Resposta hoje | Esperado |
|---|---|---|
| "Gastei R$ 73,35 na DROGASIL em 2021-04-07, quais remédios comprei?" | "Não sei" | Lista de itens com EAN |
| "Quanto economizo se trocar marca de chocolate?" | "Não sei" | Análise por produto canônico |
| "Cupom do supermercado: minha esposa pagou?" | Talvez (precisa decifrar OCR à mão) | Vinculado em 1 click |

### Cobertura cruzada (números honestos)

| Vínculo | Cobertura |
|---|--:|
| transação ↔ NF/cupom (`documento_de`) | **0,4%** (25/6086) |
| NF ↔ item (`contem_item`) | 80% (mas só 41 itens, todos de 2 NFCe) |
| transação ↔ categoria | 100% |
| transação ↔ fornecedor | 99,9% |

**Implicação**: forma do dashboard pronta, mas a substância semântica (drill-down item) não existe.

### OCR fraco confirmado

- Item NFCe Americanas: gravou "**CONTROLE P55**" em vez de "PS5" (PlayStation 5). Sistema sabe da incerteza (`aliases` tem ambas variantes), mas o canônico ficou errado.
- Cupom JPEG (52 itens, R$ 513,31): **0/5 processados**.

### Skeleton bloqueado por mob (29% do dashboard)

8 páginas Bem-estar (Hoje, Humor, Diário, Eventos, Memórias, Medidas, Ciclo, Recap) têm skeleton-mockup canônico esperando vault populado pelo app `Protocolo-Mob-Ouroboros`. Mob está em refundação golden-zebra (~50h restantes para republicar v1.0.0).

### Snapshots manuais desatualizados (XLSX abas)

| Aba | Última atualização | Status |
|---|---|---|
| extrato | automatizado | OK |
| renda | automatizado | OK |
| resumo_mensal | automatizado | OK |
| irpf | automatizado | OK |
| analise | automatizado | OK |
| **dividas_ativas** | snapshot 2023-XX-XX manual | **DESATUALIZADO** |
| **inventario** | snapshot manual | **DESATUALIZADO** |
| **prazos** | manual (V-2.2.A enriquece em runtime) | parcial |

---

## 3. Roadmap priorizado para conclusão real

### Fase 1 — Crítica (14h, paralelizar em 3 worktrees → ~6h wall clock)

| ID | Esforço | Justificativa |
|---|--:|---|
| INFRA-OCR-OPUS-VISAO | 6h | Substitui OCR fraco; habilita cupom JPEG e melhora NFCe |
| INFRA-PROCESSAR-INBOX-MASSA | 4h | Rodar leitor em ~854 arquivos brutos (hoje só 5 fixtures) |
| INFRA-LINKING-NFE-TRANSACAO | 4h | Matcher massa transação↔NF; meta 0,4% → 15% |

**Impacto**: dashboard sai de "extrator de extrato" para "organizador automático fim-a-fim" parcial. Drill-down farmácia começa a responder.

### Fase 2 — Cupom dedicado + drill-down (11h, paralelo Fase 1)

| ID | Esforço |
|---|--:|
| INFRA-EXTRATOR-CUPOM-FOTO | 8h |
| INFRA-DRILL-DOWN-ITEM | 3h |

### Fase 3 — Automação de snapshots manuais (16h, paralelo)

| ID | Esforço | Tema |
|---|--:|---|
| INFRA-AUTOMAT-DIVIDAS-ATIVAS | 6h | Ler de boletos PDF + extrato |
| INFRA-AUTOMAT-INVENTARIO | 4h | Cruzar NF de bens duráveis com depreciação tabelada |
| INFRA-AUTOMAT-PRAZOS | 6h | Ler de mappings/prazos.yaml + extrato histórico (V-2.2.A já tem início) |

### Fase 4 — Modularização (15h, qualidade arquitetural, paralelo)

5 splits para conformar limite 800L:
- INFRA-SPLIT-PROJECOES (2h)
- INFRA-SPLIT-RECAP (2h)
- INFRA-SPLIT-EXTRATO (4h)
- INFRA-SPLIT-CATALOGACAO (3h)
- INFRA-SPLIT-REVISOR (4h)

### Fase 5 — Aguarda mob (paralelo, fora deste worktree)

8 páginas Bem-estar ganham vida quando mob v1.0.0 republicar.

---

## 4. Comparativo de impacto

| Estado | Dashboard funcional | Drill-down item | Cobertura doc-trans |
|---|--:|--:|--:|
| **Hoje** | 68% (19/28) | 0% | 0,4% |
| **Pós-Fase 1** | 71% | 30% | 15% |
| **Pós-Fase 1+2** | 75% | 80% | 25% |
| **Pós-Fase 1+2+3** | 82% | 90% | 35% |
| **Tudo + mob v1.0.0** | 100% | 95% | 50%+ |

---

## 5. Decisões arquiteturais sugeridas

### ADR-26 — Opus como OCR canônico para imagens

Justificativa empírica: Opus leu cupom JPEG degradado de 52 itens sem erros perceptíveis em <30 segundos. OCR local errou "P55" vs "PS5" óbvio. Custo ~$0.005/imagem é aceitável para volume mensal de 5-20 cupons. Fallback OCR local mantido para offline.

### ADR-27 — Linking massa via matcher determinístico

Edge `documento_de` deve ser populado por matcher canônico (`valor + data ±3d + categoria_compatível`) rodado periodicamente. Quando ambíguo, gera edge `peso=0.5` + flag `revisar_humano=true`. Quando único, `peso=1.0`. Humano pode override via Revisor.

### ADR-28 — Snapshots manuais como anti-padrão

Abas `dividas_ativas`, `inventario`, `prazos` foram snapshots manuais de 2023. Visão futura: tudo automatizado a partir de fontes brutas (boletos PDF, NF de durables, prazos.yaml + histórico). Snapshots manuais ficam como dado histórico, não atualizam mais.

---

## 6. O que pedir ao mob

Para destravar 8 páginas Bem-estar do dashboard, o app `Protocolo-Mob-Ouroboros` (golden-zebra) precisa republicar v1.0.0 com:

- I-FOTO + I-AUDIO + I-VIDEO `[todo]` (cápsulas multimídia em vault)
- I-TAREFA + I-ALARME + I-CONTADOR `[todo]` (rotina diária)
- I-CICLO `[todo]` (ciclo menstrual)
- I-EXERCICIO `[todo]` (treinos para Memórias)

Schema do `memorias.json` definido hoje em `mappings/schema_memorias.json` + ADR-25 (sprint INFRA-MEMORIAS-SCHEMA do Batch 6).

---

## 7. Resumo da sessão maratona 2026-05-08

| Categoria | Quantidade |
|---|--:|
| Sprints integradas em main | 38 (33 UX + 5 INFRA) |
| Commits | ~45 |
| Pytest | 2613 → **2671** (+58 testes novos) |
| Lint | passed |
| Smoke | 10/10 |
| Documentos de auditoria | 4 (paridade visual, inventário, validação fim-a-fim, estado do todo) |
| Specs novas em backlog | 13 (8 INFRA do Batch 6 + 5 INFRA fim-a-fim) |
| Sprints concluídas (formato canônico) | 38 movidas para `concluidos/` |

---

## 8. Recomendação

Despachar **Batch 7** em paralelo agora com Fase 1 (3 sprints, ~6h wall clock):
- INFRA-OCR-OPUS-VISAO
- INFRA-PROCESSAR-INBOX-MASSA
- INFRA-LINKING-NFE-TRANSACAO

Ao final do Batch 7, validar empiricamente: pegar transação DROGASIL > R$ 50 e confirmar que dashboard mostra cupom + itens. Se sim, salto da inteligência foi consumado.

Fase 2 (extrator cupom_foto + drill-down) e Fase 3 (snapshots automatizados) podem rodar em paralelo após Fase 1.

Modularização (Fase 4) é débito arquitetural não-bloqueante; pode esperar.

---

*"Forma sem substância é maquete. Substância sem forma é planilha. Onde os dois se encontram, vira ferramenta de vida." — princípio do estado do todo*
