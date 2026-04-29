---
name: propor-extrator
description: Use quando o supervisor (Opus principal) detecta que o classifier retorna `tipo=None` para um arquivo de `data/raw/_classificar/` ou inbox e nao ha extrator dedicado. Gera proposta em `docs/propostas/extracao/<tipo>_<data>.md` baseada em `_template.md` para o humano revisar.
---

# Skill `/propor-extrator`

## Quando usar

- Achei um arquivo em `data/raw/_classificar/` ou em inbox que o classifier nao reconhece.
- `make conformance-<tipo>` retorna exit 1 e o tipo nao tem extrator em `src/extractors/`.
- Vejo padrao recorrente em `mappings/tipos_documento.yaml` com `extrator: null`.

## Como invocar

O usuario digita:

```
/propor-extrator <tipo_canonico> [<caminho-amostra>]
```

Eu (Opus principal) executo:

```bash
python scripts/propor_extrator.py <tipo> --amostra <caminho> --executar
```

Resultado: arquivo gerado em `docs/propostas/extracao/<tipo>_<data>.md` com:
- Frontmatter YAML pre-populado (id, tipo=extracao, hipotese, sha, decisao_humana=pendente).
- Corpo Markdown com contexto + mudanca proposta + trade-offs + como aprovar/rejeitar.

## Fluxo posterior (humano)

1. Humano abre o `.md` gerado e edita: refina hipotese, adiciona regex de teste, lista trade-offs reais.
2. Marca `decisao_humana.status: aprovada`.
3. Roda `/sprint-ciclo sprint_doc_<X>_extrator_<tipo>.md` quando a sub-spec ficar pronta.
4. Move proposta para `docs/propostas/_aprovadas/` e atualiza `aplicada_em` com SHA do commit que mergeou o extrator.

## Achado-bloqueio

Antes de gerar, calculo SHA da hipotese normalizada e checo se ja existe match em `docs/propostas/_rejeitadas/` (Sprint LLM-06-V2 implementa o guard formal). Match → aborto + mostro motivo da rejeicao original.

## Referencias

- `docs/propostas/_template.md` (Sprint LLM-01-V2) — template canonico.
- `scripts/propor_extrator.py` — implementacao do gerador.
- `docs/sprints/concluidos/sprint_llm_02_v2_proposicao_extrator_via_edit.md` — spec original.
- ADR-13: por que sou Opus interativo, nao API programatica.
