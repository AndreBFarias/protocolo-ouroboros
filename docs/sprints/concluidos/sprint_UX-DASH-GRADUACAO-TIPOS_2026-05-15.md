---
id: UX-DASH-GRADUACAO-TIPOS
titulo: Página dashboard `graduacao_tipos.py` com tabela viva + KPIs + dossiê inline
status: concluída
concluida_em: 2026-05-15
prioridade: P0
data_criacao: 2026-05-15
fase: PRODUCAO_READY
epico: 5
depende_de:
  - META-TIPOS-ALIAS-BIDIRECIONAL (recomendado antes para chaves consistentes)
esforco_estimado_horas: 2
origem: auditoria 2026-05-15. `scripts/dossie_tipo.py:6` docstring oficial declara "o dashboard `src/dashboard/paginas/graduacao_tipos.py` consome `data/output/graduacao_tipos.json`". Arquivo NÃO existe; nenhuma rota Streamlit consome o JSON. Dono não tem visão viva. Fere padrão (kk) "sprint encerra com produto final" — dados existem mas UI não.
---

# Sprint UX-DASH-GRADUACAO-TIPOS

## Contexto

`data/output/graduacao_tipos.json` é o snapshot vivo do ciclo de graduação. Hoje só pode ser consultado via:
- `cat data/output/graduacao_tipos.json` (manual)
- `scripts/dossie_tipo.py listar-tipos` (CLI, sem KPIs)
- Hook SessionStart (resumo no boot, sem interatividade)

Sem dashboard, o dono não vê: quantos tipos faltam graduar, quais estão REGREDINDO, quando foi a última atualização, atalho para dossiê detalhado.

## Hipótese e validação ANTES

H1: nenhum arquivo dashboard consome o JSON:

```bash
grep -rln "graduacao_tipos.json" src/dashboard/
# Esperado: 0 hits
```

H2: roadmap menciona `UX-DASH-GRADUACAO-TIPOS (criar)` como sub-sprint:

```bash
grep -A 1 "UX-DASH-GRADUACAO-TIPOS" docs/sprints/ROADMAP_ATE_PROD.md
# Esperado: 1 menção "criar"
```

## Objetivo

Criar `src/dashboard/paginas/graduacao_tipos.py` com:

1. **KPIs no topo** (4 cards): Tipos GRADUADOS (X/22), Tipos PENDENTES, Tipos CALIBRANDO, Tipos REGREDINDO. Cor semântica (verde/amarelo/laranja/vermelho).
2. **Tabela viva** com colunas: `tipo` (alias visível), `status`, `amostras_ok` (count), `divergencias_ativas` (count), `atualizado_em` (relativo: "há 2h"), `dossiê` (link interno).
3. **Filtros** por status (selectbox multi).
4. **Botão "snapshot agora"** que invoca `scripts/dossie_tipo.py snapshot` via subprocess.
5. **Expander por tipo** que abre conteúdo do `data/output/dossies/<tipo>/estado.json` formatado.
6. **Entry no `src/dashboard/app.py`** cluster Sistema (ou Documentos) para deep-link.

## Não-objetivos

- Não exibir conteúdo das `provas_artesanais/<sha>.json` na tabela (link para dossiê, não inline).
- Não permitir edição inline do `estado.json` (CLI tem `--graduar-se-pronto`).
- Não criar gráfico de evolução temporal (futuro: Plotly time-series após registro de histórico).

## Proof-of-work runtime-real

```bash
# 1. Página carrega sem erro
.venv/bin/streamlit run src/dashboard/app.py &
PID=$!
sleep 5
curl -s http://localhost:8501/graduacao_tipos | head -20
kill $PID

# 2. Validação programática (sem UI)
.venv/bin/python -c "
from src.dashboard.paginas.graduacao_tipos import _carregar_dados
d = _carregar_dados()
assert d['total'] == 22, f'esperado 22, veio {d[\"total\"]}'
assert d['graduados'] >= 9
print(f'OK {d[\"graduados\"]}/22 graduados')
"
```

## Acceptance

- `src/dashboard/paginas/graduacao_tipos.py` criado e wireado em `app.py`.
- Tabela com 22 linhas (cada tipo do YAML, com alias quando aplicável).
- KPIs corretos contra `graduacao_tipos.json`.
- Botão snapshot funciona.
- 3+ testes em `tests/test_dashboard_graduacao.py` (carregar_dados, render mínimo, snapshot trigger).
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (kk) Sprint encerra com produto final — dashboard fecha o ciclo de graduação para o dono.
- (a) Edit incremental — adicionar em `app.py` sem rewriter.

---

*"Dado sem tela é dado morto; tela sem dado é fachada vazia." — princípio do dashboard honesto*
