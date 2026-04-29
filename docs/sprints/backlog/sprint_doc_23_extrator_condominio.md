# Sprint DOC-23 — Extrator de boleto de condomínio

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 6 (Casa) + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: ANTI-MIGUE-01 + Sprint 87.3 (extrator boleto base já existe)

## Problema

Condomínio mensal vem como boleto PDF ou email; quando boleto, é detectado como `boleto_servico` genérico, perdendo metadata específica (rateio, taxa extra, etc.).

## Hipótese

Estender extrator de boleto (Sprint 87.3) com regex específica para condomínio (admin do prédio, rateio, fundo de reserva). Fornecedor canônico = administradora.

## Acceptance criteria

- Sub-classe ou flag em `boleto_pdf.py` para condomínio.
- 3 amostras 4-way.

## Gate anti-migué

9 checks padrão.
