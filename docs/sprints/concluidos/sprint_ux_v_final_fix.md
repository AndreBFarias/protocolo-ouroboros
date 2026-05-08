---
id: UX-V-FINAL-FIX
titulo: 7 defeitos visuais finais (período, sidebar Home, cards, KPIs, capitalização, projecoes)
status: concluída
concluida_em: 2026-05-08
commit: 9c2ff28
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 4
origem: navegação ao vivo do dono em 2026-05-08 + plano pode-estudar-as-ultimas-modular-cocke.md
afeta: Visão Geral, sidebar global, Pagamentos, Projeções
---

# Sprint UX-V-FINAL-FIX — 7 retoques pós-Onda V identificados ao vivo

## Contexto

Após integrar 30 sprints da Onda V (lint+smoke+pytest 2636 passed), o dono navegou pelo dashboard ao vivo e detectou 7 defeitos visuais que persistem. Esta sprint atômica fecha-os de uma só vez. Cada defeito tem arquivo+linha+fix mapeados na auditoria mestre `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md` e plano `~/.claude/plans/pode-estudar-as-ultimas-modular-cocke.md`.

## Objetivos (7 fixes em 1 commit ou 7 sub-commits)

### Defeito 1 — `Período: ...` em vez da data real
- **Arquivo**: `src/dashboard/componentes/ui.py:1102, 1199-1215`.
- **Causa**: `_resumir_periodo_chip` lê `seletor_mes_base` no primeiro frame quando session_state ainda vazio.
- **Fix**: substituir `"..."` default por mês corrente formatado (ex: usar `obter_mes_default(dados)` que já existe). Ou inverter a ordem: ler depois do selectbox renderizar.

### Defeito 2 — Sidebar HOME redireciona para sub-aba errada
- **Arquivos**: `src/dashboard/componentes/shell.py:138-147, 207`; `src/dashboard/componentes/drilldown.py:62-109` (`MAPA_ABA_PARA_CLUSTER`).
- **Causa**: clicar "Finanças"/"Documentos"/"Análise" em HOME gera `?cluster=Home&tab=Finanças`, e o dispatcher usa `MAPA_ABA_PARA_CLUSTER["Finanças"] = "Finanças"`, caindo na primeira sub-aba do cluster (Extrato).
- **Fix**: gerar href `?cluster=Finanças` (sem `tab=`) para os links HOME. Quando cluster recebe sem `tab=`, renderiza a página de visão do cluster (já existe em `paginas/financas.py` ou similar — verificar). Se não existe, fallback para primeira aba mas com toast/banner indicando.

### Defeito 3 — Cards de cluster com link sublinhado azul
- **Arquivo**: `src/dashboard/componentes/cards_clusters.py:147`.
- **Fix**: adicionar `style="text-decoration:none;color:inherit"` na tag `<a>`. Idealmente regra CSS escopada `.vg-t01-cluster-card { text-decoration: none; color: inherit; }` em `src/dashboard/css/paginas/visao_geral.css`.

### Defeito 4 — KPIs do topo Visão Geral comprimidos
- **Arquivo**: `src/dashboard/css/components.css:233-252` (`.kpi-grid`, `.kpi-label`, `.kpi-value`, `.kpi-sublabel`).
- **Fix**: aumentar gap vertical entre value e sublabel. Aplicar:
  - `.kpi-grid { row-gap: 20px; }` (ou `gap: 20px`).
  - `.kpi-card { padding: var(--sp-3) var(--sp-4); }`.
  - `.kpi-sublabel { margin-top: 8px; }`.

### Defeito 5 — Pagamentos: sub-labels KPI lowercase
- **Arquivo**: `src/dashboard/paginas/pagamentos.py:277-280`.
- **Fix**: trocar 4 strings lowercase ("consolidado do mês", "pagar imediatamente", "agendar débito", "do snapshot prazos") para Title Case ("Consolidado do mês", "Pagar imediatamente", "Agendar débito", "Do snapshot prazos").

### Defeito 6 — Projeções: slider mínimo R$ 100 + corte vertical
- **Arquivo**: `src/dashboard/paginas/projecoes.py:701-708`.
- **Fix slider**: `min_value=100, value=100, max_value=5000, step=50`.
- **Fix corte vertical**: avaliar reordenação dos blocos para que o slider apareça antes do scroll (ou compactar header/textos para reduzir altura total).

### Defeito 7 — Projeções: cards CDI/Carteira/IBOV com capitalização inconsistente
- **Arquivo**: `src/dashboard/paginas/projecoes.py:655-685` (`_card_cenario_html`).
- **Fix**: normalizar para `"CDI · Sem risco"`, `"Carteira balanceada"`, `"IBOV · Histórico"`.

## Validação ANTES (grep — padrão `(k)`)

```bash
grep -n "_resumir_periodo_chip\|seletor_mes_base" src/dashboard/componentes/ui.py | head
grep -n "MAPA_ABA_PARA_CLUSTER\|_href_para" src/dashboard/componentes/drilldown.py src/dashboard/componentes/shell.py | head
grep -n "vg-t01-cluster-card" src/dashboard/componentes/cards_clusters.py src/dashboard/css/ -r | head
grep -nE "consolidado do mês|pagar imediatamente|agendar débito|do snapshot prazos" src/dashboard/paginas/pagamentos.py
grep -nE "min_value=0|value=0|economizar a mais" src/dashboard/paginas/projecoes.py | head
grep -nE "CDI ·|Carteira |IBOV " src/dashboard/paginas/projecoes.py | head
```

## Não-objetivos

- NÃO refatorar layout dos cards (só links).
- NÃO mudar tokens canônicos.
- NÃO mexer em outras páginas além das 4 citadas (Visão Geral, Pagamentos, Projeções, sidebar global).
- NÃO modularizar projecoes.py / be_recap.py (sprints separadas em backlog).

## Proof-of-work (padrão `(u)`)

```bash
make lint && make smoke
.venv/bin/pytest tests/ -q  # esperado: 2636+ passed, 0 failed
```

Captura visual lado-a-lado em 4 URLs:
1. `?cluster=Home` (KPIs + cards de cluster sem sublinhado azul)
2. `?cluster=Home` clicar "Finanças" (deve ir para `?cluster=Finanças`, não Extrato)
3. `?cluster=Finanças&tab=Pagamentos` (sub-labels Title Case)
4. `?cluster=Finanças&tab=Projeções` (slider R$100, sub-rótulos cards normalizados)

## Critério de aceitação

1. Período mostra mês corrente (ex: "2026-04") no primeiro frame, não `"..."`.
2. Clicar "Finanças" na sidebar HOME leva a `?cluster=Finanças` (sem `tab=`).
3. Cards dos 5 clusters: link branco sem sublinhado.
4. KPIs com gap >= 20px entre `.kpi-value` e `.kpi-sublabel`.
5. Sub-labels Pagamentos em Title Case ("Consolidado do mês" etc).
6. Slider Projeções inicia em R$ 100.
7. Sub-rótulos cards Projeções normalizados (`CDI · Sem risco`, etc).
8. Lint + smoke + pytest 2636+ passed.

## Referência

- Plano: `~/.claude/plans/pode-estudar-as-ultimas-modular-cocke.md`.
- Auditoria: `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md`.
- Mockup canônico: `novo-mockup/mockups/01-visao-geral.html`, `04-pagamentos.html`, `05-projecoes.html`.

*"Polish é o último 5% que o dono percebe primeiro." — princípio UX-V-FINAL-FIX*
