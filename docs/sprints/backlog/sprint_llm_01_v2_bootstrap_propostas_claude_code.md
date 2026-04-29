# Sprint LLM-01-V2 — Bootstrap de propostas via Claude Code interativo

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_01_infra_anthropic_basica (arquivada).
**Prioridade**: P0
**Onda**: 2
**Esforço estimado**: 2h
**Depende de**: nenhuma

## Problema

ADR-13 declara que NÃO HAVERÁ `src/llm/` nem dependência `anthropic`. Mas o ciclo de proposições previsto em ADR-08 ainda precisa de bootstrap mínimo.

## Hipótese

Template Markdown + script de contexto + skill de auditoria habilitam o ciclo sem nenhuma chamada programática.

## Implementação proposta

1. `docs/propostas/_template.md` com frontmatter (id, tipo, hipotese, evidencia, decisao_humana, sha).
2. `scripts/supervisor_contexto.sh` que dumpa: stats XLSX, pendências em `docs/propostas/`, últimas armadilhas, últimos commits.
3. Skill `/auditar-cobertura` em `.claude/skills/auditar-cobertura.md` (ver LLM-04-V2).
4. Diretório `docs/propostas/_rejeitadas/` com README explicando ciclo.

## Acceptance criteria

- Template válido (frontmatter parseável por pyyaml).
- Script executável e testado em runtime.
- Não introduz `anthropic` em deps (`grep anthropic pyproject.toml` retorna 0 linhas).

## Gate anti-migué

9 checks padrão.
