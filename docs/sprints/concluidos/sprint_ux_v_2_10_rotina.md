---
id: UX-V-2.10
titulo: Página Bem-estar / Rotina com 4 KPIs + 3 colunas (Alarmes/Tarefas/Contadores)
status: concluida
concluida_em: 2026-05-07
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02, UX-V-03]
co_executavel_com: [UX-V-2.8, UX-V-2.14, UX-V-2.16]
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 20)
mockup: novo-mockup/mockups/20-rotina.html
---

# Sprint UX-V-2.10 -- Rotina paridade

## Contexto

Auditoria: página Rotina cai em fallback graceful (V-03) quando `<vault>/.ouroboros/rotina/*.toml` não existem. Quando existem, deve renderizar:
- 4 KPIs no topo (Tarefas Hoje 3/7, Próximo Alarme 22:00, Streak Ativo 47 dias, Conclusão Semanal 82%)
- 3 colunas: ALARMES (8 com toggle on/off), TAREFAS HOJE (com checkbox + prioridade), CONTADORES (com streak + meta)

## Página afetada

`src/dashboard/paginas/be_rotina.py` apenas.

## Objetivo

1. Quando `rotina/*.toml` existem, ler via `tomllib` e renderizar 4 KPIs + 3 colunas.
2. Manter fallback V-03 quando ausente (atual).
3. Toggles/checkboxes podem ser visualmente representados sem persistência (escopo: visual).

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_rotina.py
ls .ouroboros/rotina/*.toml 2>/dev/null
grep -n "fallback_estado_inicial_html\|tomllib\|carregar_rotina" src/dashboard/paginas/be_rotina.py | head -10
```

## Spec de implementação

```python
import tomllib
from pathlib import Path

def _carregar_rotinas_toml(vault_root: Path | None) -> dict:
    """Lê todos .toml em <vault>/.ouroboros/rotina/. Retorna agregado por tipo."""
    if vault_root is None:
        return {}
    pasta = vault_root / ".ouroboros" / "rotina"
    if not pasta.exists():
        return {}
    alarmes, tarefas, contadores = [], [], []
    for arq in pasta.glob("*.toml"):
        try:
            d = tomllib.loads(arq.read_text(encoding='utf-8'))
            alarmes.extend(d.get("alarme", []))
            tarefas.extend(d.get("tarefa", []))
            contadores.extend(d.get("contador", []))
        except Exception:
            continue
    return {"alarmes": alarmes, "tarefas": tarefas, "contadores": contadores}


def _kpis_rotina_html(dados: dict) -> str:
    n_tarefas = len(dados.get('tarefas', []))
    n_concluidas = sum(1 for t in dados.get('tarefas', []) if t.get('concluida'))
    proximo_alarme = "—"
    if dados.get('alarmes'):
        # Próximo alarme (ordem por hora, primeiro depois de agora)
        from datetime import datetime
        agora = datetime.now().strftime("%H:%M")
        futuros = [a for a in dados['alarmes'] if a.get('hora', '') > agora]
        if futuros:
            proximo_alarme = sorted(futuros, key=lambda a: a.get('hora', ''))[0].get('hora', '—')
    streak = max((c.get('streak_dias', 0) for c in dados.get('contadores', [])), default=0)
    return minificar(f"""
    <div class="kpi-grid">
      <div class="kpi"><span class="kpi-label">TAREFAS HOJE</span>
        <span class="kpi-value">{n_concluidas}/{n_tarefas}</span>
        <span class="kpi-sub">{n_tarefas - n_concluidas} a fazer</span></div>
      <div class="kpi"><span class="kpi-label">PRÓXIMO ALARME</span>
        <span class="kpi-value" style="color:var(--accent-orange);">{proximo_alarme}</span>
        <span class="kpi-sub">próximas horas</span></div>
      <div class="kpi"><span class="kpi-label">STREAK ATIVO</span>
        <span class="kpi-value" style="color:var(--accent-green);">{streak} dias</span>
        <span class="kpi-sub">contador top</span></div>
      <div class="kpi"><span class="kpi-label">ALARMES ATIVOS</span>
        <span class="kpi-value">{len(dados.get('alarmes', []))}</span>
        <span class="kpi-sub">configurados</span></div>
    </div>
    """)
```

3 colunas via `st.columns([1,1,1])` com listas estilizadas.

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_*.py -q
```

## Proof-of-work runtime-real

Validação visual em `cluster=Bem-estar&tab=Rotina`. Quando `rotina/*.toml` existem, mostrar 4 KPIs + 3 colunas (alarmes/tarefas/contadores). Quando ausentes, fallback V-03.

## Critério de aceitação

1. KPIs renderizando quando dados existem.
2. 3 colunas (alarmes/tarefas/contadores) com items estilizados.
3. Fallback V-03 preservado.
4. Lint OK + cluster pytest verde.

## Não-objetivos

- NÃO implementar persistência de toggles/checkboxes (visual only).
- NÃO mexer em outras páginas Bem-estar.

## Referência

- Mockup: `novo-mockup/mockups/20-rotina.html`.
- VALIDATOR_BRIEF: `(a)/(b)/(k)/(o)/(u)`.

*"Rotina é a infraestrutura do dia." -- princípio V-2.10*
