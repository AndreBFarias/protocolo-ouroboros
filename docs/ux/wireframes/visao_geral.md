# Wireframe — Visão Geral (pós-92a/b/c)

**Contexto:** hoje o usuário aterriza sem hero, sem "Pagamentos urgentes" inline
e sem "Orçamento restante" — precisa ir para Pagamentos e Projeções para montar
a foto. A Visão Geral redesenhada concentra a leitura de rotina.

**Viewport alvo:** 1600×1000, degradando graciosamente até 900×700.

---

## Layout — 12 colunas, 3 zonas verticais

```
+-------------------------------------------------------------------------+
| SIDEBAR (fixa 240px)        | AREA PRINCIPAL (grid 12 col)              |
|                             |                                           |
| [LOGO 64x64]                | [HERO HERO HERO HERO HERO HERO HERO]      |
| Protocolo Ouroboros         |  01 — Hoje                                |
|                             |  "Como está abril/26 e o que vem adiante"|
| Dados de 23/04/2026 22:03   |                                           |
| ---------------             | ============ ZONA A — OVERVIEW ============|
| Granularidade [Mês v]       | +----------+ +----------+ +-------------+ |
| Mês          [2026-04 v]    | | TAXA     | | SUPERFL. | | MAIOR GASTO | |
| Pessoa       [Todos v]      | | 68,9%    | | R$ 134   | | Impostos    | |
| Forma pgto   [Todas v]      | | verde    | | alerta   | | R$ 1.463    | |
|                             | +----------+ +----------+ +-------------+ |
| ---------------             |                                           |
| Receita  R$ 15.622,50       | +--- SAUDE FINANCEIRA: SAUDÁVEL ----+     |
| Despesa  R$  4.855,73       | | Poupança de 69% da receita        |     |
| Saldo    R$ 10.766,77       | | [ progress bar 69% ================]|   |
|                             | +------------------------------------+    |
|                             |                                           |
|                             | ============ ZONA B — ACCAO PENDENTE ====== |
|                             | +-- PAGAMENTOS URGENTES (proximos 7d) --+ |
|                             | | C6 vence em 2d (25/04)  R$ X   Pendente| |
|                             | | Internet em 5d          R$ 220 Pendente| |
|                             | | [ver todos no cluster Dinheiro >]      | |
|                             | +---------------------------------------+ |
|                             |                                           |
|                             | ============ ZONA C — CONTEXTO ============ |
|                             | +--- RECEITA vs DESPESA (6 meses) ---+    |
|                             | |  Jan | Fev | Mar | Abr              |    |
|                             | |  bars + linha de saldo              |    |
|                             | |  Legenda ABAIXO (padrão Sprint 77)  |    |
|                             | +------------------------------------+    |
|                             |                                           |
|                             | +--- DISTRIBUICAO POR CLASSIFICACAO ---+  |
|                             | |  Obrigatório   R$ 4.203,73 (86%)     | |
|                             | |  Questionável  R$   517,60 (11%)     | |
|                             | |  Supérfluo     R$   134,39 ( 3%)     | |
|                             | +-------------------------------------+   |
+-------------------------------------------------------------------------+
```

---

## Mudanças vs atual (aba_01_visao_geral.png)

- **(+) Hero com numeração** (01 Hoje) — cria slot mental consistente com Catalogação/Busca/Grafo (que já usam hero).
- **(+) Zona B "Pagamentos urgentes"** puxa 3-5 primeiros boletos com venc <= 7d do módulo `pagamentos.py::carregar_boletos_inteligente` + `alertas_vencimento`. Link "ver todos" navega ao cluster Dinheiro > Pagamentos.
- **(+) Saúde financeira com progress bar inline** em vez do callout atual (que só diz texto).
- **(=) Cards KPI** — manter, mudar só para usar `metric_semantic_html` (cor por sinal automático).
- **(=) Gráfico Receita vs Despesa** — já existe, aplicar `legenda_abaixo` e drill-down para Extrato (já aplicado).
- **(=) Distribuição por classificação** — migra de barras horizontais para **lista textual com % e valor**. Pesquisa usabilidade: em viewport 1600 a barra horizontal estreita rotaciona texto (bug observado). Lista textual resolve + é mais scanável.
- **(-) Remover** duplicação com sidebar (Receita/Despesa/Saldo já estão na sidebar; não repetir em card no topo).

---

## Estados

### Estado vazio (sem dados no mês)

```
+---------------------------+
| 01 — Hoje                 |
| Nenhum dado para 2026-04  |
|                           |
| Dicas:                    |
| 1. Verifique se o pipeline|
|    rodou (make process)   |
| 2. Ajuste o mês na sidebar|
+---------------------------+
```

### Estado de erro (arquivo XLSX ausente)

Usar `callout_html(tipo="error", titulo="Dados ausentes", mensagem="...")` (componente novo da Sprint 92c).

### Estado de dados parciais (alguns bancos sem fechamento)

Card do banco afetado com badge "parcial" (amarelo) ao lado do nome.

---

## Responsive

- **>= 1200px:** layout 3-coluna como acima.
- **900-1200px:** cards KPI em 2 colunas, gráficos empilhados.
- **< 900px:** tudo em 1 coluna, sidebar vira `st.sidebar` colapsável (default do Streamlit).

---

## Tokens usados

- `hero_titulo_html("01", "Hoje", "Como está abril/26 e o que vem adiante.")`
- `card_html` para 3 KPIs
- `progress_inline_html(0.69, CORES["positivo"], "Poupança de 69%")` — helper novo
- `callout_html("warning", "C6 vence em 2 dias...")` — helper novo
- `legenda_abaixo(fig)` no Receita vs Despesa
