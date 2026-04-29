# Sprint DOC-25 — Extrator de IPVA + apólice de seguro auto

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 7 + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: DOC-24 (precisa node veículo no grafo)

## Problema

IPVA e seguro auto são despesas anuais recorrentes do casal sem extrator dedicado.

## Hipótese

`src/extractors/ipva_pdf.py` + sub-classe de cupom_garantia para apólice auto. Linkam ao node veículo (criado por DOC-24) via `cobre`.

## Acceptance criteria

- 2 extratores (IPVA + apólice) com 3 amostras 4-way cada.
- IPVA tag IRPF `imposto_pago`.
- Apólice cria node `garantia` linkado ao veículo.

## Gate anti-migué

9 checks padrão.
