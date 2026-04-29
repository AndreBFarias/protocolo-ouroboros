# Sprint DOC-26 — Extrator de multas Detran

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 7 + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: DOC-24

## Problema

Multas Detran chegam por email/PDF; sem extrator, perdem contexto (auto da infração, pontos CNH).

## Hipótese

`src/extractors/multa_detran_pdf.py` parseia auto de infração: AIT, placa, data, local, valor, pontos CNH. Linka ao veículo + alerta.

## Acceptance criteria

- 3 amostras 4-way.
- Alerta de pontos CNH acumulando perto do limite (20).

## Gate anti-migué

9 checks padrão.
