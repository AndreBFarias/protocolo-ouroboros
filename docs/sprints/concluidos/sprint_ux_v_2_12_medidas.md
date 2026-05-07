---
id: UX-V-2.12
titulo: Bem-estar / Medidas com 6 cards corporais (sparkline + variação 30d) + tabela 6 semanas
status: concluída
prioridade: alta
data_criacao: 2026-05-07
concluida_em: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02, UX-V-03]
co_executavel_com: [UX-V-2.9, UX-V-2.11, UX-V-2.13, UX-V-2.15]
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 24)
mockup: novo-mockup/mockups/24-medidas.html
---

# Sprint UX-V-2.12 -- Medidas paridade

## Contexto

Auditoria: dashboard em fallback V-03. Mockup tem toggle Pessoa A/B + 6 cards (Peso/Gordura corp/Cintura/Pressão/Frequência rep/Sono médio) com sparklines coloridas + variação 30d + tabela histórico semanal 6 semanas.

## Página afetada

`src/dashboard/paginas/be_medidas.py` apenas.

## Objetivo

1. Quando `<vault>/.ouroboros/cache/medidas.json` existir, renderizar 6 cards + tabela.
2. Cada card: label + valor atual + sparkline (últimos 30 dias) + variação 30d (delta sinalizado).
3. Toggle Pessoa A/B.
4. Tabela histórico semanal das 6 semanas mais recentes.
5. Fallback V-03 mantido.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_medidas.py
ls .ouroboros/cache/medidas.json 2>/dev/null
grep -n "sparkline_html\|fallback_estado_inicial_html" src/dashboard/paginas/be_medidas.py | head -5
```

## Spec de implementação

```python
from src.dashboard.componentes.ui import sparkline_html


METRICAS_CORPO = [
    ("peso", "PESO", "kg", "var(--accent-purple)"),
    ("gordura", "GORDURA CORP.", "%", "var(--accent-orange)"),
    ("cintura", "CINTURA", "cm", "var(--accent-yellow)"),
    ("pressao_sis", "PRESSÃO", "/100 mmHg", "var(--accent-cyan)"),
    ("freq_card", "FREQ. CARD.", "bpm", "var(--accent-green)"),
    ("sono_horas", "SONO MÉDIO", "h/noite", "var(--accent-pink)"),
]


def _card_medida_html(medidas: list[dict], chave: str, label: str, unidade: str, cor: str) -> str:
    pontos = [m.get(chave) for m in medidas[-30:] if isinstance(m.get(chave), (int, float))]
    if not pontos:
        return f'<div class="med-card"><span class="med-label">{label}</span><span class="med-vazio">--</span></div>'
    valor = pontos[-1]
    delta = (pontos[-1] - pontos[0]) if len(pontos) >= 2 else 0
    sparkline = sparkline_html(pontos, cor=cor, largura=140, altura=32)
    sinal = "↘" if delta < 0 else "↗" if delta > 0 else "="
    return minificar(f"""
    <div class="med-card">
      <span class="med-label">{label}</span>
      <span class="med-valor">{valor:.1f}<span class="med-unid">{unidade}</span></span>
      <span class="med-delta">{sinal} {delta:+.1f} / 30d</span>
      <div class="med-sparkline">{sparkline}</div>
    </div>
    """)
```

CSS em `be_medidas.css`: `.med-card`, `.med-label`, `.med-valor`, `.med-unid`, `.med-delta`, `.med-sparkline`, `.med-vazio`.

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_resto.py -q
```

## Proof-of-work

Validação visual em `cluster=Bem-estar&tab=Medidas`. Quando medidas.json tem dados, mostrar 6 cards + tabela. Senão fallback V-03.

## Critério de aceitação

1. 6 cards renderizando quando dados existem (mesmo se 1 ponto = sem sparkline).
2. Tabela histórico 6 semanas.
3. Toggle A/B funcional.
4. Fallback V-03 preservado.
5. CSS + lint OK + cluster pytest verde.

## Não-objetivos

- NÃO implementar importação Mi Fit/Garmin (escopo separado).
- NÃO mexer em outras páginas.

## Referência

- Mockup: 24-medidas.html.
- VALIDATOR_BRIEF: (a)/(b)/(k)/(o)/(u).

*"Corpo medido é corpo cuidado." -- princípio V-2.12*
