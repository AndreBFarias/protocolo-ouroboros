---
id: UX-V-2.11
titulo: Memórias com grid de cápsulas multimídia (foto/áudio/texto/vídeo)
status: backlog
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02, UX-V-03]
co_executavel_com: [UX-V-2.9, UX-V-2.12, UX-V-2.13, UX-V-2.15]
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 23)
mockup: novo-mockup/mockups/23-memorias.html
mob_dependencia: I-FOTO + I-AUDIO + I-VIDEO (golden-zebra)
---

# Sprint UX-V-2.11 -- Memórias paridade

## Contexto

Auditoria: dashboard mostra heatmap de treinos (página atual). Mockup mostra grid 7+5 de cápsulas multimídia (FOTO/ÁUDIO/TEXTO/VÍDEO com gradientes coloridos, badges, chips de categoria, dados meta). **São páginas funcionalmente diferentes** -- mob deve gravar memórias multimídia em vault.

## Página afetada

`src/dashboard/paginas/be_memorias.py` apenas.

## Objetivo

1. Quando vault tem `memorias.json` com itens, renderizar grid de cápsulas (até 12) com:
   - Badge de tipo (FOTO/ÁUDIO/TEXTO/VÍDEO) colorido
   - Gradiente como fundo (visual)
   - Título + data + chips de categoria + meta (duração se áudio/vídeo, evento vinculado se houver)
2. Quando vault vazio, fallback V-03 mantido.
3. KPIs no topo (Total / Por tipo / Vinculadas a eventos / Cápsulas para abrir).

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_memorias.py
ls .ouroboros/cache/memorias.json 2>/dev/null
grep -n "fallback_estado_inicial_html\|^def renderizar" src/dashboard/paginas/be_memorias.py | head -5
```

## Spec de implementação

```python
GRADIENTES_CAT = {
    "casal": "linear-gradient(135deg, #ff79c6 0%, #bd93f9 100%)",
    "trabalho": "linear-gradient(135deg, #8be9fd 0%, #50fa7b 100%)",
    "rolezinho": "linear-gradient(135deg, #ffb86c 0%, #ff79c6 100%)",
    "casa": "linear-gradient(135deg, #f1fa8c 0%, #50fa7b 100%)",
    "viagem": "linear-gradient(135deg, #ff5555 0%, #ff79c6 100%)",
}


def _capsula_html(memoria: dict) -> str:
    tipo = str(memoria.get('tipo', 'TEXTO')).upper()
    cat = str(memoria.get('categoria', 'casa')).lower()
    grad = GRADIENTES_CAT.get(cat, "linear-gradient(135deg, var(--bg-elevated), var(--bg-surface))")
    titulo = memoria.get('titulo', '?')[:50]
    data = memoria.get('data', '')
    duracao = memoria.get('duracao', '')
    chips = " ".join(f'<span class="capsula-chip">{c}</span>' for c in (memoria.get('tags', [])[:3]))
    return minificar(f"""
    <div class="capsula-card" style="background:{grad};">
      <span class="capsula-badge">{tipo}</span>
      <div class="capsula-body">
        <h4 class="capsula-titulo">{titulo}</h4>
        <span class="capsula-meta">{data} {duracao}</span>
        <div class="capsula-chips">{chips}</div>
      </div>
    </div>
    """)


def _kpis_memorias_html(memorias: list[dict]) -> str:
    n = len(memorias)
    from collections import Counter
    tipos = Counter(str(m.get('tipo', '?')).lower() for m in memorias)
    n_vinculadas = sum(1 for m in memorias if m.get('evento_id'))
    return minificar(f"""
    <div class="kpi-grid">
      <div class="kpi"><span class="kpi-label">TOTAL</span><span class="kpi-value">{n}</span></div>
      <div class="kpi"><span class="kpi-label">POR TIPO</span>
        <span class="kpi-value">{tipos.get('foto',0)} fotos · {tipos.get('audio',0)} áudios</span></div>
      <div class="kpi"><span class="kpi-label">VINCULADAS A EVENTOS</span>
        <span class="kpi-value">{n_vinculadas}/{n}</span></div>
      <div class="kpi"><span class="kpi-label">CÁPSULAS PARA ABRIR</span>
        <span class="kpi-value">{max(0, n - n_vinculadas)}</span></div>
    </div>
    """)
```

CSS em `be_memorias.css`: `.capsula-card`, `.capsula-badge`, `.capsula-body`, `.capsula-titulo`, `.capsula-meta`, `.capsula-chip`.

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_resto.py -q
```

## Proof-of-work

Validação visual em `cluster=Bem-estar&tab=Memórias`. Quando vault tem memorias.json, mostrar grid 4x3 cápsulas + KPIs. Senão fallback V-03.

## Critério de aceitação

1. KPIs e grid renderizando quando dados existem.
2. Fallback V-03 preservado.
3. CSS criado.
4. Lint OK + cluster pytest verde.

## Não-objetivos

- NÃO renderizar mídia real (foto/áudio/vídeo) — só badges + título + meta.
- NÃO implementar player de áudio/vídeo.

## Referência

- Mockup: 23-memorias.html. Mob bloqueante: I-FOTO/I-AUDIO/I-VIDEO ainda [todo].
- VALIDATOR_BRIEF: (a)/(b)/(k)/(o)/(u).

*"Cápsula é memória que volta." -- princípio V-2.11*
