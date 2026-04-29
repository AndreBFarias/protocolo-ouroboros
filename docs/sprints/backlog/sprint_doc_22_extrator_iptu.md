# Sprint DOC-22 — Extrator de IPTU

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 6 (Casa) + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: ANTI-MIGUE-01

## Problema

IPTU é despesa anual do casal mas falta extrator dedicado; cai em fallback ou ignora.

## Hipótese

`src/extractors/iptu_pdf.py` parseia carnê IPTU prefeitura: inscrição imobiliária, contribuinte, valor anual, parcelas, vencimentos. Tag IRPF `imposto_pago`.

## Acceptance criteria

- Extrator + 3 amostras 4-way (Brasília + outras prefeituras se aplicável).
- Vincula automaticamente como dedutível IRPF se aplicável.

## Gate anti-migué

9 checks padrão.
