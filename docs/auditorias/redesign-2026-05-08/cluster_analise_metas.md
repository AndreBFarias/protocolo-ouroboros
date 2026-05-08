# Auditoria visual 2026-05-08 — Cluster Análise/Metas

## 11 — Categorias (sprint UX-V-2 não tem; auditoria 2026-05-07 marcou BAIXA)

**OK**: 4 KPIs estruturados, árvore hierárquica com barras %, treemap colorido renderizando.

**Faltantes**:
- Botões "expandir tudo / por valor" no header da árvore.
- Bloco "Regras de auto-classificação" detalhado abaixo do treemap.

**Classificação**: BAIXA. Mantém prioridade da auditoria anterior.

---

## 12 — Análise (sprint UX-V-2.6 — concluída)

**Migués detectados**:
- **Breadcrumb errado**: "ANÁLISE / VISÃO GERAL" (deveria ser só "ANÁLISE" no nível atual).
- **Tabs duplicadas**: 3 tabs no topo (Fluxo de caixa 3 / Categorias 17 / Padrões temporais 14d) + 3 sub-abas idênticas dentro do conteúdo. Confunde UX.
- **Layout 4 KPIs assimétrico**: 3 cards na primeira linha (Entradas/Saídas/Investido) + 1 card sozinho na segunda (Saldo). Mockup tem 4 cards uniformes em linha única.
- **Investido R$ 0**: similar ao migué de Projeções — cálculo retornando zero indevido.
- **Insights Derivados parcialmente implementado**: aparece "PREVISÃO" cortado no canto inferior direito, mas mockup tem 4 cards estruturados (POSITIVO / ATENÇÃO / DESCOBERTA / PREVISÃO).

**Classificação**: MÉDIA. V-2.6 entregou estrutura mas tem 5 defeitos pontuais. Sprint UX-V-2.6-FIX adequada.

---

## 13 — Metas (sprint UX-V-2.5 — concluída)

**OK**:
- 6 cards visíveis com donut % no canto superior direito, barra de progresso, 3 colunas PRAZO/RITMO/FALTA — todos elementos da spec.
- Sub-bloco "METAS FINANCEIRAS" + "METAS OPERACIONAIS · PIPELINE" presente.

**Faltantes**:
- Glyph cinza no topo do card (mockup tem retângulo decorativo; dashboard sem).
- Header info "total acumulado R$ X · meta total R$ Y" antes dos cards.

**Classificação**: BAIXA. V-2.5 cumpriu spec; só polish faltando.

---

## 15 — IRPF (sprint UX-V-2 não tem; precisa V-3.4)

**Migués observados**:
- **Dropdown "Ano-calendário" muito proeminente** acima do título — mockup não tem (ano é parte do título "IRPF 2026").
- **2 categorias faltantes** (já reconhecido auditoria 2026-05-07): mostra 5 visíveis, mockup tem 8 (rendimento_tributavel, rendimento_isento, dedutivel_medico, dedutivel_educacional, previdencia_privada, imposto_pago, inss_retido, doacao_dedutivel).
- **Barra de completude monocromática** (todas em 0% real) — mockup mostra cores >=90% verde / 70-90% amarelo + badge.
- **Botões expand/baixar inline por categoria** ausentes (mockup tem chevron e ícone de documento).
- **Checklist lateral**: dashboard tem versão pobre; mockup tem 5 itens estruturados com marcadores de status.

**Classificação**: MÉDIA. Confirma UX-V-3.4-IRPF-FINISH.
