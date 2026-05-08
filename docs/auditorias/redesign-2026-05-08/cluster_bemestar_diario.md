# Auditoria visual 2026-05-08 — Bem-estar diário (Hoje, Humor, Diário)

## 17 — Bem-estar Hoje (sprint UX-V-2 não tem; auditoria 2026-05-07 marcou MÉDIA → V-3.5)

**OK**: 4 sliders HUMOR/ANSIEDADE/ENERGIA/FOCO funcionando; medicação + sono + tags como spec.

**Faltantes vs mockup**:
- Cards laterais semanticamente diferentes: dashboard tem (Diários/Eventos/Medidas do dia) com counters zerados; mockup tem (Status casal A/B 7d + Próximos alarmes/tarefas + Registros do dia em timeline).
- Seletor "Esse registro é para… (para mim / Pessoa B / casal)" — ausente.
- Tags como inputs simples em vez de pílulas multi-seleção.

**Classificação**: MÉDIA. Confirma UX-V-3.5-BE-HOJE-CARDS.

---

## 18 — Humor heatmap (sprint UX-V-2 não tem; auditoria 2026-05-07 marcou ALTA → V-3.6)

**OK estrutural**: heatmap 13x7 renderiza, 4 cards laterais (Média/Registros/Melhor/Pior), modo Pessoa A/B/Sobreposto.

**Faltantes vs mockup**:
- Sparkline embaixo da MÉDIA 30 DIAS + delta "+0.18 vs 30d anteriores".
- Card "STREAK HUMOR >=4 X dias · recorde da janela 30d" ausente.
- Heatmap quase vazio (1 célula) — limitação de dado mob; fallback OK.

**Classificação**: MÉDIA-ALTA. UX-V-3.6 ou skeleton-mockup canônico V-mob.

---

## 19 — Diário emocional (sprint UX-V-2 não tem; auditoria 2026-05-07 marcou MÉDIA → V-3.7)

**Layout funcionalmente diferente**:

- **Mockup**: 3-col com facetas (TIPO/PARA QUEM/PERÍODO com counts) + form NOVA ENTRADA com 4 tabs (Trigger/Vitória/Reflexão/Observação) + intensidade pílulas + tags + corpo + Timeline.
- **Dashboard**: 2-col com filtros laterais simples (Modo radio + Período + Pessoa) + lista cronológica + botão "Registrar diário" (modal?). Form NOVA ENTRADA inteiramente ausente da view principal.

**Classificação**: ALTA. Confirma UX-V-3.7-BE-DIARIO. Reescrita do form é a essência do gap.
