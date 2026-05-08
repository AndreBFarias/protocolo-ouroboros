---
id: UX-V-3.7
titulo: Bem-estar Diário — form NOVA ENTRADA com 4 tabs Trigger/Vitória/Reflexão/Observação
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 19)
mockup: novo-mockup/mockups/19-diario-emocional.html
---

# Sprint UX-V-3.7 — Diário com layout 3-col canônico + form completo

## Contexto

Inspeção 2026-05-08: dashboard tem layout 2-col com filtros laterais simples + lista cronológica + botão "Registrar diário" (modal). Form NOVA ENTRADA inteiramente ausente da view principal.

Mockup `19-diario-emocional.html` mostra layout 3-col:
- **Esquerda**: 3 facetas (TIPO/PARA QUEM/PERÍODO) com counts.
- **Centro**: form NOVA ENTRADA com 4 tabs (Trigger/Vitória/Reflexão/Observação) + título + intensidade pílulas 1-5 + esse registro é para + tags + corpo.
- **Embaixo**: TIMELINE com entradas.

## Objetivo

1. Layout 3-col com `st.columns([1, 2.5, 0.5])` ou similar.
2. Form NOVA ENTRADA com tabs (`st.tabs(["Trigger", "Vitória", "Reflexão", "Observação"])`).
3. Cada tab: título input + intensidade pílulas 1-5 + esse registro é para (3 opções) + tags (chips) + corpo textarea.
4. Botão "Salvar trigger/vitória/etc" muda label conforme tab ativa.
5. Timeline embaixo do form com entradas filtradas pelas facetas.
6. Facetas mostram counts reais.

## Validação ANTES (grep)

```bash
grep -n "Trigger\|Vitória\|Reflexão\|Observação\|st.tabs" src/dashboard/paginas/be_diario.py | head
```

## Não-objetivos

- NÃO implementar persistência markdown completa nesta sprint (placeholder OK).
- NÃO mexer no formato de leitura do `diario-emocional.json`.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k be_diario -q
```

Captura visual: 3-col com facetas + form 4-tab + timeline.

## Critério de aceitação

1. Layout 3-col em viewport >=1280px.
2. Form com 4 tabs.
3. Intensidade pílulas 1-5 funcionais.
4. Timeline embaixo do form com entradas.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `19-diario-emocional.html`.

*"Diário emocional precisa de fricção mínima — tab certa, tudo na mão." — princípio V-3.7*
