# Sprint LLM-03-V2 — Proposição de regra de categoria via Edit em mappings/proposicoes/

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_03_supervisor_propor_regra_categoria (arquivada).
**Prioridade**: P2
**Onda**: 2
**Esforço estimado**: 1h
**Depende de**: LLM-01-V2

## Problema

Fornecedor frequente sem regra em `mappings/categorias.yaml` cai em fallback `Outros + Questionável`. Precisa caminho para o supervisor propor regra nova.

## Hipótese

Quando query no grafo mostra fornecedor com >=5 transações classificadas como `Outros`, supervisor abre `mappings/proposicoes/<fornecedor>.yaml` via Edit. Humano revisa, aprova → arquivo move para `mappings/categorias.yaml` (merge).

## Implementação proposta

1. Skill `/propor-regra <fornecedor>` que abre proposta pré-populada.
2. Script `scripts/aplicar_proposta_regra.py` que merge proposta aprovada em categorias.yaml.
3. Workflow em CLAUDE.md.

## Acceptance criteria

- Skill funcional.
- Script de merge testado.
- Demo: 1 fornecedor real proposto + aprovado + aplicado.

## Gate anti-migué

9 checks padrão.
