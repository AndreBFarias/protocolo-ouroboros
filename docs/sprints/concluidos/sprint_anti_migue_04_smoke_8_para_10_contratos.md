# Sprint ANTI-MIGUE-04 -- Smoke aritmético 8 → 10 contratos

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29, item 39).
**Prioridade**: P1
**Onda**: 1
**concluida_em**: 2026-04-29
**Esforço real**: 1h
**Commit**: `f6bd88f`

## Problema

Auditoria honesta 2026-04-29 reportou que `scripts/smoke_aritmetico.py` "declara 8 contratos mas só 6 estão implementados" (item 39). **Verificado: o agente da auditoria errou — havia 8 contratos reais.** Mas o gap estrutural apontado procede: faltava invariante de coerência inter-aba **"`resumo_mensal.receita_total` == soma de `tipo=Receita` no `extrato`"**.

Sem esse invariante, o `resumo_mensal` poderia divergir do `extrato` silenciosamente (cache desatualizado, geração parcial, erro de filtro).

## Hipótese

Adicionar 2 contratos de coerência inter-aba:
- `contrato_resumo_mensal_receita_coerente`
- `contrato_resumo_mensal_despesa_coerente` (par natural)

Tolerância R$ 0,01 (arredondamento float). Aplicado em `mes_ref` que aparece nas duas abas.

## Implementação

1. Mudar assinatura dos 8 contratos existentes de `(df, renda)` para `(df, renda, resumo)`.
2. Adicionar 2 contratos novos.
3. `main()` ler aba `resumo_mensal` com fallback `pd.DataFrame(columns=...)` se ausente.
4. Atualizar docstring + saída literal `[SMOKE-ARIT] 10/10 contratos OK`.
5. Atualizar `tests/test_smoke_aritmetico.py` (assert "10/10") + adicionar teste regressivo `test_xlsx_com_resumo_divergente_falha_em_strict`.

## Proof-of-work

```
$ make smoke
[SMOKE-ARIT] 10/10 contratos OK

$ pytest tests/test_smoke_aritmetico.py -q
5 passed in 4.28s

$ pytest tests/ -q
2.019 passed (+1 desde 2.018, regressão zero)
```

## Acceptance atendido

- [x] 10 contratos implementados e validados em runtime real.
- [x] Smoke roda sobre XLSX real do projeto sem violação.
- [x] Teste regressivo cobrindo divergência receita resumo vs extrato.
- [x] Pytest baseline cresceu (+1).
- [x] Lint exit 0.
