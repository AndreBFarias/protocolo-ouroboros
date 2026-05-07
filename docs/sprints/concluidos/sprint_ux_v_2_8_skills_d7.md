---
id: UX-V-2.8
titulo: Página Skills D7 com 5 KPIs + inventário 18 skills + cobertura por cluster
status: concluida
prioridade: alta
data_criacao: 2026-05-07
concluida_em: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02, UX-V-03]
co_executavel_com: [UX-V-2.10, UX-V-2.14, UX-V-2.16]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 14)
mockup: novo-mockup/mockups/14-skills-d7.html
---

# Sprint UX-V-2.8 -- Skills D7 paridade

## Contexto

Auditoria identificou que página Skills D7 caía em fallback graceful (V-03 entregou skeleton + CTA mob). Quando `data/output/skill_d7_log.json` existe, deve renderizar:
- 5 KPIs no topo (Cobertura D7 / Taxa de Graduação / Regressões 30D / Confiança Média / Execuções 30D)
- Inventário 18 skills com pílulas D7 (graduado/calibrando/regredindo/bloqueado)
- Distribuição por estado (4 grandes números)
- Cobertura por cluster (Finanças/Documentos/Análise/Sistema com bar chart)

## Página afetada

`src/dashboard/paginas/skills_d7.py` apenas.

## Objetivo

1. Renderizar layout completo do mockup quando `skill_d7_log.json` existir.
2. Manter fallback V-03 quando ausente.
3. Criar gerador determinístico do log se necessário (parse de `scripts/gauntlet/` outputs ou auditoria de extractors via `make conformance-*`).

## Validação ANTES (grep obrigatório)

```bash
ls data/output/skill_d7_log.json 2>/dev/null
grep -n "_carregar_snapshot\|skill_d7_log\|_lista_skills_html" src/dashboard/paginas/skills_d7.py | head -10
test -f scripts/auditar_cobertura_total.py && head -30 scripts/auditar_cobertura_total.py
```

## Spec de implementação

Se `skill_d7_log.json` existir com schema `{skills: [...], evolucao: [...], cobertura_cluster: {...}}`:

```python
def _kpis_d7_html(snapshot: dict) -> str:
    skills = snapshot.get('skills', [])
    n = len(skills)
    grad = sum(1 for s in skills if s.get('estado') == 'graduado')
    cobertura = (grad / n * 100) if n > 0 else 0
    regressoes = sum(1 for s in skills if s.get('estado') == 'regredindo')
    confianca = sum(s.get('confianca', 0) for s in skills) / n if n > 0 else 0
    execucoes = sum(s.get('runs', 0) for s in skills)
    return minificar(f"""
    <div class="kpi-grid">
      <div class="kpi"><span class="kpi-label">COBERTURA D7</span>
        <span class="kpi-value" style="color:var(--accent-purple);">{cobertura:.0f}%</span>
        <span class="kpi-sub">{grad}/{n} · meta 75%</span></div>
      <div class="kpi"><span class="kpi-label">TAXA DE GRADUAÇÃO</span>
        <span class="kpi-value">+{grad}/Q1</span>
        <span class="kpi-sub">no trimestre</span></div>
      <div class="kpi"><span class="kpi-label">REGRESSÕES 30D</span>
        <span class="kpi-value" style="color:var(--accent-orange);">{regressoes}</span>
        <span class="kpi-sub">cat-presentes</span></div>
      <div class="kpi"><span class="kpi-label">CONFIANÇA MÉDIA</span>
        <span class="kpi-value">{confianca*100:.1f}%</span>
        <span class="kpi-sub">média ponderada</span></div>
      <div class="kpi"><span class="kpi-label">EXECUÇÕES 30D</span>
        <span class="kpi-value">{execucoes:,}</span>
        <span class="kpi-sub">runs/dia · p95 2.4s</span></div>
    </div>
    """)
```

Manter `_lista_skills_html` existente (já tem pílulas D7 canônicas).

Se ausente: manter `fallback_estado_inicial_html` da V-03.

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_skill_d7.py -q
```

## Proof-of-work runtime-real

Validação visual em `cluster=Sistema&tab=Skills+D7`. Quando log existe, mostrar 5 KPIs + inventário 18 + cobertura cluster. Quando não, fallback rico (V-03).

## Critério de aceitação

1. 5 KPIs no topo quando log existe.
2. Inventário renderiza 18 skills com pills D7.
3. Cobertura por cluster com bar chart.
4. Fallback V-03 preservado.
5. Lint OK + cluster pytest verde.

## Não-objetivos

- NÃO criar scripts de geração de log_d7 (escopo separado).
- NÃO mexer em outras páginas.

## Referência

- Mockup: `novo-mockup/mockups/14-skills-d7.html`.
- VALIDATOR_BRIEF: `(a)/(b)/(k)/(o)/(u)`.

*"Skill medida é skill auditável." -- princípio V-2.8*
