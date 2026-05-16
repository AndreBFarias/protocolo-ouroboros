---
id: LINK-AUDIT-02-BOOST-DIFF-VALOR-ZERO
titulo: "Boost +0,05 em `_calcular_score` quando `diff_valor_absoluto <= 0,01`"
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-16
fase: QUALIDADE
epico: 3
depende_de:
  - LINK-AUDIT-01 (concluída — diagnóstico identificou problema)
esforco_estimado_horas: 2
origem: "achado colateral do executor `a51d3c56` (LINK-AUDIT-01) 2026-05-15. Diagnóstico empírico revelou que motor `_calcular_score` linear NÃO prioriza `diff_valor=0` perfeito sobre delta temporal menor. Resultado: 14 propostas de linking ficam em empate top-1/top-2 = 0,000 e linker descarta por falta de margem. Após ajuste de margem_empate 0,05→0,02 (sprint anterior), 3 docs liberam mas 14 empates restam."
---

# Sprint LINK-AUDIT-02-BOOST-DIFF-VALOR-ZERO

## Contexto

Em `src/graph/linking.py::_calcular_score`, o motor calcula similaridade
linear: `0,5 * janela_data + 0,3 * diff_valor + 0,2 * outros`. Quando 2
candidatos têm a mesma data mas valores idênticos (`diff_valor=0`), o
score é igual ao de candidatos com `diff_valor` razoável — o motor não
distingue.

A heurística semântica é simples: **valor exato é prova forte**. Boost
de `+0,05` no score quando `diff_valor_absoluto <= 0,01` (1 centavo)
desempata corretamente sem mexer no resto da fórmula.

## Hipótese e validação ANTES

```bash
grep -n "_calcular_score\|diff_valor" src/graph/linking.py | head -10

.venv/bin/python scripts/diagnosticar_linking.py --grafo data/output/grafo.sqlite
# Esperado: 14 propostas com score_top1 == score_top2 (empate)
```

## Objetivo

1. Editar `src/graph/linking.py::_calcular_score`:
   ```python
   # Boost para match exato de valor (1 centavo)
   if abs(diff_valor) <= 0.01:
       score += 0.05
   ```
2. Re-rodar `_diagnosticar_linking` para medir ganho.
3. Adicionar parâmetro `boost_valor_exato_threshold` em `mappings/linking_config.yaml` (default 0.01).
4. Atualizar `margem_empate_por_tipo` no YAML caso necessário.

## Não-objetivos

- Não tocar `_consolidar_pares_ofx_xlsx_mesmo_banco` (sprint anterior).
- Não criar motor não-linear ou ML.
- Não tocar `mappings/categorias.yaml`.

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/diagnosticar_linking.py --grafo data/output/grafo.sqlite
# Esperado: número de empates DIMINUI; linking_pct aumenta
```

## Acceptance

- Boost aplicado em `_calcular_score` com config em YAML.
- Pelo menos 7 dos 14 empates restantes resolvidos.
- Pytest > 3080 (testes existentes + 2 testes novos do boost).
- Lint exit 0. Smoke 10/10.

## Padrões aplicáveis

- (n) Defesa em camadas — boost + margem_empate são duas heurísticas independentes.
- (a) Edit cirúrgico em função pequena.

---

*"Valor exato é prova; empate é dúvida que merece desempate." — princípio do score honesto*
