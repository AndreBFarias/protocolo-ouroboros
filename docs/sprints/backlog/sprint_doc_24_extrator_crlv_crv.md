# Sprint DOC-24 — Extrator de CRLV/CRV digital (gov.br)

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 7 (Mobilidade) + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: ANTI-MIGUE-01

## Problema

Casal tem 0 nodes de veículos no grafo. CRLV/CRV é documento gov.br padrão; sem extrator, contexto de mobilidade fica fora.

## Hipótese

`src/extractors/crlv_pdf.py` parseia layout gov.br: placa, RENAVAM, chassi, marca/modelo, ano, proprietário, validade. Cria node `documento` + node `fornecedor` (DETRAN) + alerta de validade.

## Acceptance criteria

- Extrator + 3 amostras 4-way ([A] e [V]).
- Alerta no dashboard se validade < 90d.

## Gate anti-migué

9 checks padrão.
