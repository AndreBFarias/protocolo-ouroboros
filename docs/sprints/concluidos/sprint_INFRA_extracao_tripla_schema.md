---
id: INFRA-EXTRACAO-TRIPLA-SCHEMA
titulo: Schema canônico extracao_tripla.json + popular Opus em >=3 amostras reais
status: concluida
concluida_em: 2026-05-08
prioridade: altissima
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
co_executavel_com: []
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md M2 + UX-V-2.4 spec original
mockup: novo-mockup/mockups/10-validacao-arquivos.html <!-- noqa: accent -->
bloqueia: [UX-V-2.4-FIX, UX-V-4-REVISOR]
---

# Sprint INFRA-EXTRACAO-TRIPLA-SCHEMA — base de dados da extração tripla

## Contexto

A spec UX-V-2.4 declarou: *"Se schema extracao_tripla.json não existe, PARAR e propor sub-sprint INFRA-EXTRACAO-TRIPLA-SCHEMA antes de continuar"*. A sub-sprint nunca foi criada e o resultado é a Validação Tripla com coluna Opus 100% vazia, paridade 0%, status nunca atinge CONSENSO/DIVERGENTE (sempre SÓ ETL ou SÓ HUMANO).

Esta sprint endereça a fundação de dados.

## Objetivo

1. Definir schema canônico em `data/output/extracao_tripla.json` (fonte única para Validação Tripla + Revisor).
2. Implementar carregador `src/dashboard/dados_extracao_tripla.py` com graceful fallback.
3. Popular o JSON com >=3 amostras reais via runner `scripts/popular_extracao_tripla.py` (lê CSV existente `validacao_arquivos.csv` + chama Opus interativo via supervisor artesanal ADR-13 OU usa heurística sem-API enquanto LLM v2 não existe).

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
ls data/output/extracao_tripla.json 2>&1 | head
ls data/output/validacao_arquivos.csv | xargs head -3
grep -rn "extracao_tripla\|validacao_arquivos" src/dashboard/paginas/extracao_tripla.py | head
```

## Schema canônico

```json
{
  "$schema": "https://ouroboros/schemas/extracao_tripla/v1.json",
  "registros": [
    {
      "sha256": "b7d2a04f...",
      "filename": "fatura_c6_cartao_2026-03.pdf",
      "tipo": "fatura_cartao",
      "etl": {
        "extractor_versao": "c6_cartao v1.8.2",
        "campos": {
          "banco": ["C6 Bank", 1.0],
          "total_fatura": [2847.90, 0.95]
        }
      },
      "opus": {
        "versao": "opus_v1_supervisor_artesanal",
        "campos": {
          "banco": ["C6 Bank", 0.99],
          "total_fatura": [2874.90, 0.71]
        }
      },
      "humano": {
        "validado_em": null,
        "campos": {}
      }
    }
  ]
}
```

## Não-objetivos (padrão `(t)`)

- NÃO chamar Anthropic API automaticamente (ADR-13: supervisor artesanal via Claude Code).
- NÃO inventar valores Opus diferentes de ETL — só popular Opus quando há diferença real registrada via supervisor.
- NÃO modificar `validacao_arquivos.csv` (snapshot histórico).

## Proof-of-work (padrão `(u)`)

```bash
test -f data/output/extracao_tripla.json
python3 -c "
import json, pathlib
data = json.loads(pathlib.Path('data/output/extracao_tripla.json').read_text())
print(f'registros={len(data[\"registros\"])}')
print(f'com_opus={sum(1 for r in data[\"registros\"] if r[\"opus\"][\"campos\"])}')
"
# Esperado: registros=>=3, com_opus=>=3
```

## Critério de aceitação

1. `data/output/extracao_tripla.json` existe e segue schema acima.
2. >=3 registros têm Opus com >=1 campo divergente do ETL.
3. Carregador `dados_extracao_tripla.py` retorna lista parseada.
4. `make lint && make smoke` verde + pytest baseline mantida.

## Referência

- Auditoria: `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md` M2.
- Spec original: `docs/sprints/concluidos/sprint_ux_v_2_4_validacao_tripla.md`.
- ADR-13 (supervisor artesanal).
- VALIDATOR_BRIEF padrões: `(k)/(s)/(u)`.

*"Sem schema, não há comparação. Sem comparação, não há validação." — princípio INFRA-EXTRACAO-TRIPLA*
