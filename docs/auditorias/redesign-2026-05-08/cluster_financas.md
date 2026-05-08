# Auditoria visual 2026-05-08 — Cluster Finanças

## 02 — Extrato (sprint UX-V-2 não tem; precisa V-3.1)

**Mockup vs dashboard**:
- Filt-bar inline canônica (CONTA · CATEGORIA · PERÍODO · BUSCA + chips só-saídas/com-sidecar/não-categorizadas) — **AUSENTE** no dashboard.
- Lista por dia com header "2026-04-30 · QUI -R$ 2.832,40" + linhas com pílulas tipo (NB/IF/PX/UB/EX) — **AUSENTE**.
- Layout 2-col (lista + sidebar Saldo+Breakdown) — dashboard tem 3 cards lado a lado no topo (Saldo 90D + Breakdown + Origens).
- Dashboard tem "> Filtros avançados" expander + "Buscar por local" — versão pobre do que o mockup propõe.

**Classificação**: ALTA. Confirma necessidade de criar UX-V-3.1-EXTRATO-FILT (proposta na auditoria 2026-05-07 e não materializada).

---

## 03 — Contas (sprint UX-V-2.1 — concluída)

**Pontos OK**:
- Sparkline em cada conta corrente — implementada.
- Separação Contas Correntes & Investimento × Cartões de Crédito — implementada.
- Barra de utilização % no cartão (2% usado, verde) — implementada.
- Classe D7 (d7-graduado) + limite estimado — implementada.

**Pontos faltantes**:
- Baseboard de cada card de conta corrente: dashboard mostra `transações 30d / banco_origem`. Mockup mostra `último OFX / sha8 / sincronizado HH:MM / txns 30d` (4 campos vs 2). Falta dado de OFX por conta.
- Cartão de crédito: dashboard tem `LIMITE / USADO / DISPONÍVEL`. Mockup tem `LIMITE / USADO / FATURA ABERTA` + `vence 2026-05-10 9d`. Diferença semântica (DISPONÍVEL vs FATURA ABERTA + data).

**Classificação**: MÉDIA. V-2.1 entregou estrutura; sub-sprint UX-V-2.1.A para baseboard 4-campos + fatura aberta seria adequada.

---

## 05 — Projeções (sprint não tinha UX-V-2; auditoria 2026-05-07 marcou BAIXA)

**Migués observados**:
- **Aporte mensal médio R$ 0,00** no KPI — cálculo aparente errado (KPI "Em 5 anos" mostra crescimento mas aporte 0).
- **Sliders ausentes**: mockup tem APORTE MENSAL slider + RETORNO A.A. slider + HORIZONTE select com "recalcula em tempo real". Dashboard só mostra os 4 KPIs estáticos.
- **Marcos**: dashboard mostra 2 marcos (Reserva 100% / Entrada Apto 12m). Mockup mostra 5 marcos (1ª centena / Reserva 6m / Entrada apto / 1/4 milhão / 1/2 milhão).
- **Independência Financeira "fora do horizonte"** vs mockup "2042 · 16a" — cálculo difere; provável que o fora-do-horizonte seja symptom do aporte 0.

**Classificação**: ALTA (subiu de BAIXA da auditoria 2026-05-07). Precisa sprint nova UX-V-2.0-PROJECOES (não estava no plano original V-2 batch).
