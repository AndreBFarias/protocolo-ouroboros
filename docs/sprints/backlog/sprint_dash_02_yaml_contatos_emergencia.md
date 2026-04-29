# Sprint DASH-02 — YAML estruturado de contatos de emergência

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 8 + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 6
**Esforço estimado**: 2h
**Depende de**: nenhuma

## Problema

Contatos de emergência do casal não estão estruturados; PII espalhado em notas Obsidian sem schema.

## Hipótese

`mappings/contatos_emergencia.yaml` (gitignored, PII): para cada pessoa, lista de [nome, parentesco, telefone, instituição, observação]. UI no dashboard cluster Hoje.

## Acceptance criteria

- Schema validado por pydantic ou check manual.
- UI exibe contatos com mascaramento de telefone (XX.XXXX-XXXX).
- Arquivo no .gitignore.

## Gate anti-migué

9 checks padrão.
