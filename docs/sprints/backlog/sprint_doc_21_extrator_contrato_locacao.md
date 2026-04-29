# Sprint DOC-21 — Extrator de contrato de locação

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 6 (Casa) + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3 (cobertura documental)
**Esforço estimado**: 4h
**Depende de**: ANTI-MIGUE-01 (gate 4-way obrigatório para extratores novos)

## Problema

Contrato de locação imobiliária é documento legal recorrente do casal mas não tem extrator dedicado — cai em catch-all `recibo_nao_fiscal`.

## Hipótese

`src/extractors/contrato_locacao_pdf.py` extrai: locador, locatário, imóvel, valor mensal, data início/fim, índice de reajuste. Cria nodes `documento` + `fornecedor` (locador) + `periodo` (vigência) + arestas.

## Acceptance criteria

- Extrator funcional em fixture sintética + 1 amostra real.
- Gate 4-way ≥3 amostras antes de mover para concluidos.
- Linkado em mappings/tipos_documento.yaml com prio `especifico`.

## Gate anti-migué

Padrão dos 9 checks de ANTI-MIGUE-01 + frontmatter `concluida_em`.
