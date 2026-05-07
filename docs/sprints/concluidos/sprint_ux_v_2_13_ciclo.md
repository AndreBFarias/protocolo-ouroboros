---
id: UX-V-2.13
titulo: Bem-estar / Ciclo com anel circular SVG + sintomas + cruzamento humor
status: concluída
concluida_em: 2026-05-07
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02, UX-V-03]
co_executavel_com: [UX-V-2.9, UX-V-2.11, UX-V-2.12, UX-V-2.15]
esforco_estimado_horas: 6
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 25)
mockup: novo-mockup/mockups/25-ciclo.html
---

# Sprint UX-V-2.13 -- Ciclo paridade

## Contexto

Auditoria: dashboard em fallback. Mockup tem anel circular SVG gigante mostrando 28 dias do ciclo com fases coloridas (Menstrual/Folicular/Fértil/Lútea), dia atual destacado + Sintomas hoje (escala 0-3 dots) + Cruzamento ciclo × humor (12 ciclos) + cards de fase + Privacidade.

## Página afetada

`src/dashboard/paginas/be_ciclo.py` apenas.

## Objetivo

1. Quando `<vault>/.ouroboros/cache/ciclo.json` existir, renderizar:
   - Anel SVG circular 28 dias com fases coloridas
   - Sintomas hoje (escala 0-3 com dots)
   - Cards de fase (Menstrual/Folicular/Fértil/Lútea) com descrição
   - Cruzamento humor médio por fase
2. Fallback V-03 mantido.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_ciclo.py
ls .ouroboros/cache/ciclo.json 2>/dev/null
```

## Spec de implementação

```python
def _anel_ciclo_svg(dia_atual: int, total_dias: int = 28) -> str:
    """SVG anel circular com 28 segmentos coloridos por fase."""
    import math
    cx, cy, r = 150, 150, 100
    largura_anel = 30
    fases = {
        "menstrual": (1, 5, "#ff5555"),
        "folicular": (6, 13, "#bd93f9"),
        "fertil": (14, 16, "#50fa7b"),
        "lutea": (17, 28, "#ffb86c"),
    }
    
    def fase_do_dia(d):
        for nome, (ini, fim, cor) in fases.items():
            if ini <= d <= fim:
                return nome, cor
        return "lutea", "#ffb86c"
    
    segmentos = []
    angulo_seg = 360 / total_dias
    for d in range(1, total_dias + 1):
        nome, cor = fase_do_dia(d)
        ang_ini = math.radians((d - 1) * angulo_seg - 90)
        ang_fim = math.radians(d * angulo_seg - 90)
        x1 = cx + r * math.cos(ang_ini)
        y1 = cy + r * math.sin(ang_ini)
        x2 = cx + r * math.cos(ang_fim)
        y2 = cy + r * math.sin(ang_fim)
        opacidade = 1.0 if d == dia_atual else 0.6
        segmentos.append(f'<path d="M {cx} {cy} L {x1} {y1} A {r} {r} 0 0 1 {x2} {y2} Z" fill="{cor}" opacity="{opacidade}" />')
    
    return f"""
    <svg viewBox="0 0 300 300" width="300" height="300" class="anel-ciclo">
      {''.join(segmentos)}
      <circle cx="{cx}" cy="{cy}" r="{r - largura_anel}" fill="var(--bg-base)" />
      <text x="{cx}" y="{cy - 5}" text-anchor="middle" class="anel-label">d{dia_atual}</text>
      <text x="{cx}" y="{cy + 20}" text-anchor="middle" class="anel-sub">de {total_dias}</text>
    </svg>
    """
```

CSS em `be_ciclo.css`: `.anel-ciclo`, `.anel-label`, `.anel-sub`, `.fase-card`, `.sintoma-linha`, `.sintoma-dots`.

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_resto.py -q
```

## Proof-of-work

Validação visual em `cluster=Bem-estar&tab=Ciclo`. Quando ciclo.json tem dados, mostrar anel SVG + sintomas + cards de fase + cruzamento. Senão fallback V-03.

## Critério de aceitação

1. Anel SVG renderizando quando dados existem.
2. 4 cards de fase com cor canônica.
3. Fallback V-03 preservado.
4. CSS + lint OK + cluster pytest verde.

## Não-objetivos

- NÃO implementar registro de novo ciclo (escopo mob).
- NÃO usar plotly polar (custom SVG é mais leve).

## Referência

- Mockup: 25-ciclo.html.
- VALIDATOR_BRIEF: (a)/(b)/(k)/(o)/(u).

*"Ciclo é o calendário interno." -- princípio V-2.13*
