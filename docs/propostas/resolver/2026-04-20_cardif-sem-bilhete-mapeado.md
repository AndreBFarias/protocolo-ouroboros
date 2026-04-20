---
id: 2026-04-20_cardif-sem-bilhete-mapeado
tipo: resolver
data: 2026-04-20
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: 47c
---

# Proposta: manter Cardif preparatória em seguradoras.yaml ou remover?

## Contexto

`mappings/seguradoras.yaml` (Sprint 47c) tem 2 seguradoras:

- MAPFRE 61.074.175/0001-38 -- presente em TODOS os 5 bilhetes reais da inbox
- Cardif (BNP Paribas) 08.279.191/0001-84 -- **nenhum bilhete observado**

Cardif foi cadastrada **preparatoriamente** porque a spec da 47c mencionava
"MAPFRE/Cardif" (as 2 seguradoras dominantes de garantia estendida em
varejo brasileiro). Pergunta do supervisor: manter ociosa ou remover?

## Diff proposto

**Opção A (recomendada): manter + documentar a preparação.**

```diff
  - cnpj: "08.279.191/0001-84"
    razao_social: "BNP Paribas Cardif Seguros S.A."
    nome_canonico: "BNP PARIBAS CARDIF SEGUROS S.A."
    codigo_susep: "05720"
+   # Cadastrada preparatoriamente (Sprint 47c). Nenhum bilhete Cardif
+   # observado até 2026-04-20. Manter reduz atrito quando o primeiro
+   # aparecer -- extrator reconhece instantaneamente sem gerar proposta.
    aliases:
      - "Cardif Seguros"
      - "BNP Cardif"
      - "Cardif"
```

**Opção B (conservadora): remover.**

```diff
-
-  - cnpj: "08.279.191/0001-84"
-    razao_social: "BNP Paribas Cardif Seguros S.A."
-    ...
```

Quando bilhete Cardif aparecer, `_registrar_proposta_seguradora` abre
proposta automaticamente e o humano cadastra.

## Justificativa

**A favor de manter (A):**
- 5 linhas de YAML, zero impacto em runtime (enrich só roda com match de CNPJ).
- Cardif é líder em tier 2 de varejo (Extra, Casas Bahia). Probabilidade
  alta de surgir.
- Humano poupa passo trivial quando surgir.

**A favor de remover (B):**
- "Local First" + "menos é mais": YAML só tem o que é usado.
- Workflow de propostas já pega o caso quando surgir.

## Teste de regressão

```bash
# Se A (manter):
.venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py::TestSeguradoraYaml::test_cardif_tambem_cadastrada -v

# Se B (remover):
# - remover test_cardif_tambem_cadastrada
# - adicionar teste de que cadastro novo gera proposta corretamente
```

## Decisão humana

**Aprovada em:** (preencher -- indicar A ou B)
**Rejeitada em:** (preencher)
**Motivo:** (se rejeitada)

---

*"Registro por convicção, não por previsão." -- princípio do cadastro artesanal*
