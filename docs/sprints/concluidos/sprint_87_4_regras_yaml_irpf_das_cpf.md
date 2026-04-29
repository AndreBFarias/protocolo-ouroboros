---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: 3810ac7
---

# Sprint 87.4 — Regras YAML para tipos documentais IRPF/DAS/CPF (R70-3)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P2
**Onda**: KAPPA (legado pré-plan)

## Problema

3 tipos legados (irpf_parcela, das_mei, comprovante_cpf) sem regra em `tipos_documento.yaml` caíam em `boleto_servico` (false-positive).

## Hipótese

Adicionar 3 regras com prioridade `especifico` (mais alta que `boleto_servico`). Reduz `skip_nao_identificado` do adapter Sprint 70.

## Acceptance criteria

- 3 regras novas em mappings/tipos_documento.yaml.
- Reclassificação de docs mal classificados após `--reextrair-tudo`.

## Proof-of-work

Commit `3810ac7`. Volume real revalidou sem regressão.
