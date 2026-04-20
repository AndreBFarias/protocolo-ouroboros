---
id: <yyyy-mm-dd>_<slug>
tipo: regra
data: <yyyy-mm-dd>
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: none
---

# Proposta: <título curto do que muda>

## Contexto

Descreva o padrão que motivou a proposta. Inclua referência concreta a
`arquivo:linha` ou query SQL que reproduz o caso observado. Sem contexto
verificável, a proposta não pode ser auditada depois.

Ex.: "Ao rodar `./run.sh --tudo` em 2026-04-19, 3 transações de
`NEOEN S.A.` caíram em `Outros/Questionável` porque a regex atual de
`neoenergia` em `mappings/categorias.yaml:45` exige `NEOENERGIA` literal."

## Diff proposto

Mostre o diff exato -- linhas `+` e `-`. Caller deve conseguir aplicar com
`patch` ou edição manual sem ambiguidade.

```diff
# mappings/categorias.yaml
- neoenergia:
-   regex: "NEOENERGIA"
+ neoenergia:
+   regex: "NEOEN[ERGIA]*\\s*S\\.?A?\\.?"
    categoria: "Energia"
    classificacao: "Obrigatório"
```

## Justificativa

Por que esta mudança resolve o problema?

- Quantas transações ela afeta? (Contagem real, não estimativa.)
- Risco de falso-positivo? (Rodou contra amostra negativa?)
- Alternativas consideradas e por que foram descartadas.

## Teste de regressão

Comando reproduzível que prova que a regra aprovada cobre os casos-alvo e
não quebra nada existente. Se não existir teste, incluir o comando que
seria o teste (mesmo que o teste ainda não exista -- o commit de absorção
cria).

```bash
.venv/bin/pytest tests/test_categorizer.py -k "neoenergia" -v
```

## Decisão humana

**Aprovada em:** (preencher ao aprovar)
**Rejeitada em:** (preencher ao rejeitar)
**Motivo:** (preencher se rejeitada)

---

*"Antes de alterar a regra, mostre a transação que ela corrige." -- princípio do supervisor artesanal*
