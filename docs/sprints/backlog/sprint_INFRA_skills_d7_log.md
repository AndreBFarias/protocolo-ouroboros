---
id: INFRA-SKILLS-D7-LOG
titulo: Gerar data/output/skill_d7_log.json a partir do classificador D7
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: []
esforco_estimado_horas: 4
origem: docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md (skills_d7 em fallback degradado)
mockup: novo-mockup/mockups/14-skills-d7.html
---

# Sprint INFRA-SKILLS-D7-LOG — popular log de execuções D7

## Contexto

Página `skills_d7` cai em fallback degradado por falta de `data/output/skill_d7_log.json`. Mockup espera 5 KPIs (Cobertura D7, Taxa Graduação, Regressões 30D, Confiança Média, Execuções 30D) + inventário 18 skills + distribuição por estado + cobertura por cluster — todos derivados de log estruturado de runtime.

## Objetivo

Implementar `scripts/gerar_skill_d7_log.py` que, dado:
- Inventário de extratores em `src/extractors/*.py` (18 skills canônicas).
- Histórico de runs em `logs/extractors/*.log` ou `data/output/cobertura_total/*.json`.
- Tabela de classificação D7 (graduado / calibrando / regredido / bloqueado) baseada em `(taxa_acerto, n_runs, tendencia_30d)`.

Produza JSON canônico em `data/output/skill_d7_log.json` com schema:

```json
{
  "$schema": "ouroboros/schemas/skill_d7_log/v1",
  "gerado_em": "2026-05-08T20:00:00",
  "kpis": {
    "cobertura_d7_pct": 78,
    "taxa_graduacao": "+3/Q1",
    "regressoes_30d": 1,
    "confianca_media": 0.904,
    "execucoes_30d": 3836
  },
  "skills": [
    {
      "id": "s01",
      "nome": "ofx-parse",
      "descricao": "Parser de extratos OFX bancários",
      "cluster": "Finanças",
      "d7": "graduado",
      "confianca": 0.97,
      "execucoes": 184,
      "tendencia_pct": 0.4
    },
    ...
  ],
  "distribuicao": {"graduado": 14, "calibrando": 3, "regredido": 1, "bloqueado": 0},
  "cobertura_cluster": [
    {"cluster": "Finanças", "pct": 88},
    {"cluster": "Documentos", "pct": 60},
    ...
  ]
}
```

## Validação ANTES (grep)

```bash
ls src/extractors/ | grep -E "\.py$" | grep -v __ | wc -l   # esperado >=18
ls logs/extractors/ 2>&1 | head
grep -rn "skill_d7_log\|cobertura_d7" src/ scripts/ | head -10
```

## Não-objetivos

- NÃO criar página nova (skills_d7.py já consome o JSON).
- NÃO chamar Anthropic API.

## Proof-of-work

```bash
python scripts/gerar_skill_d7_log.py
test -f data/output/skill_d7_log.json
python -c "import json; d=json.load(open('data/output/skill_d7_log.json')); assert len(d['skills']) >= 18 and d['kpis']['cobertura_d7_pct'] > 0"
make lint && make smoke
```

Validação visual: cluster=Sistema&tab=Skills+D7 mostra 5 KPIs com valores reais + inventário 18 linhas + distribuição + cobertura cluster.

## Critério de aceitação

1. JSON existe e segue schema v1.
2. >=18 skills com pelo menos `id`, `nome`, `d7`, `confianca`, `execucoes`.
3. Página renderiza valores reais (não `--`).
4. Lint + smoke + pytest baseline.

## Referência

- Inventário: `docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md`.
- Mockup: `14-skills-d7.html`.
- Spec UX-V-2.8-FIX-SKELETON (já entregue) renderiza skeleton; esta sprint preenche com dado real.

*"Sistema sem painel de saúde é caixa preta." — princípio INFRA-SKILLS-D7-LOG*
