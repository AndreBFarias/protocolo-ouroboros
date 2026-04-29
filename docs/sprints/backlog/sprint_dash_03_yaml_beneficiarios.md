# Sprint DASH-03 — YAML de beneficiários (seguros, aposentadoria)

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 8 + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 6
**Esforço estimado**: 2h
**Depende de**: DASH-02 (mesmo padrão estrutural)

## Problema

Beneficiários de seguros/aposentadoria espalhados em apólices PDF; sem agregado, fica difícil verificar consistência.

## Hipótese

`mappings/beneficiarios.yaml` (gitignored, PII): por apólice/conta, lista de [pessoa, percentual, parentesco]. Dashboard mostra alerta se soma ≠ 100%.

## Acceptance criteria

- Schema validado.
- Alerta de inconsistência (soma percentual diferente de 100).

## Gate anti-migué

9 checks padrão.
