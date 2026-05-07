---
id: UX-V-2.9
titulo: Bem-estar / Eventos com timeline rica + calendário visual + cruzamento humor
status: concluída
concluida_em: 2026-05-07
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02, UX-V-03]
co_executavel_com: [UX-V-2.11, UX-V-2.12, UX-V-2.13, UX-V-2.15]
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 22)
mockup: novo-mockup/mockups/22-eventos.html
---

# Sprint UX-V-2.9 -- Eventos paridade

## Contexto

Auditoria: dashboard mostra 1 evento + filtros laterais. Mockup tem timeline rica (10 eventos coloridos por tipo CASAL/TRABALHO/SAUDE/SOCIAL/VIAGEM/FAMILIA) + calendário visual lateral 5x7 + Distribuição por tipo (bar chart) + Cruzamento com humor.

## Página afetada

`src/dashboard/paginas/be_eventos.py` apenas.

## Objetivo

1. Quando vault tem `eventos.json` com itens, renderizar:
   - Timeline com cards coloridos por categoria (`.evento-card` já existe em `be_eventos.css`)
   - Calendário 5x7 lateral mostrando dias com pontos/marcadores
   - Distribuição por tipo (bar chart simples)
   - Cards de cruzamento: humor médio quando há eventos vs sem
2. Quando vault vazio, fallback V-03 (mantido).

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_eventos.py
ls .ouroboros/cache/eventos.json 2>/dev/null
grep -n "calendario\|distribuicao\|cruzamento_humor" src/dashboard/paginas/be_eventos.py | head -5
```

## Spec de implementação

```python
def _calendario_visual_html(eventos: list[dict], ano: int, mes: int) -> str:
    """Calendário 5x7 com pontos coloridos em datas com eventos."""
    from calendar import monthrange
    from datetime import date
    weekday_inicio = date(ano, mes, 1).weekday()
    _, total_dias = monthrange(ano, mes)
    dias = [None] * weekday_inicio + [date(ano, mes, d) for d in range(1, total_dias + 1)]
    while len(dias) % 7 != 0:
        dias.append(None)
    
    eventos_por_dia = {}
    for ev in eventos:
        try:
            d = date.fromisoformat(str(ev.get('data', '')))
            if d.year == ano and d.month == mes:
                eventos_por_dia.setdefault(d, []).append(ev.get('categoria', 'outro'))
        except ValueError:
            continue
    
    celulas = []
    for d in dias:
        if d is None:
            celulas.append('<div class="cv-celula cv-empty"></div>')
        else:
            evs = eventos_por_dia.get(d, [])
            dots = "".join(f'<span class="cv-dot cv-{c}"></span>' for c in evs[:3])
            celulas.append(f'<div class="cv-celula"><span class="cv-num">{d.day}</span>{dots}</div>')
    
    cabec = "".join(f'<div class="cv-head">{d}</div>' for d in ["S","T","Q","Q","S","S","D"])
    return minificar(f'<div class="calendario-visual"><div class="cv-grid">{cabec}{"".join(celulas)}</div></div>')


def _distribuicao_html(eventos: list[dict]) -> str:
    from collections import Counter
    cats = Counter(str(e.get('categoria', 'outro')) for e in eventos)
    if not cats:
        return ""
    max_v = max(cats.values())
    linhas = []
    for cat, n in cats.most_common():
        pct = (n / max_v) * 100
        linhas.append(f"""
        <div class="dist-linha">
          <span class="dist-label">{cat}</span>
          <div class="dist-bar"><span class="dist-fill" style="width:{pct}%;background:var(--accent-purple);"></span></div>
          <span class="dist-num">{n}</span>
        </div>""")
    return minificar(f'<div class="distribuicao-bloco"><h3>DISTRIBUIÇÃO POR TIPO</h3>{"".join(linhas)}</div>')
```

CSS adicionar em `be_eventos.css`: `.calendario-visual`, `.cv-grid`, `.cv-celula`, `.cv-num`, `.cv-dot`, `.cv-{categoria}`, `.distribuicao-bloco`, `.dist-linha`, `.dist-bar`, `.dist-fill`.

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_diario_eventos.py -q
```

## Proof-of-work

Validação visual em `cluster=Bem-estar&tab=Eventos`. Quando eventos.json tem dados, mostrar calendário + distribuição + timeline. Senão fallback V-03.

## Critério de aceitação

1. Calendário visual quando vault tem eventos.
2. Distribuição por tipo (bar chart simples).
3. CSS dedicado.
4. Fallback V-03 preservado.
5. Lint OK + cluster pytest verde.

## Não-objetivos

- NÃO implementar drilldown ao clicar em evento.
- NÃO criar estatísticas de cruzamento humor x eventos (escopo V-2.14).

## Referência

- Mockup: 22-eventos.html. VALIDATOR_BRIEF: (a)/(b)/(k)/(o)/(u).

*"Calendário guarda; timeline conta." -- princípio V-2.9*
