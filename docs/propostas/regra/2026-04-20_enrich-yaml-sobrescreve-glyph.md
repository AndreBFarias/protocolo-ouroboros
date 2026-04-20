---
id: 2026-04-20_enrich-yaml-sobrescreve-glyph
tipo: regra
data: 2026-04-20
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: 47c
---

# Proposta: enrich por YAML deve sobrescrever campos canônicos quando CNPJ bate

## Contexto

Ao rodar `./run.sh --tudo` em 2026-04-19 contra os bilhetes MAPFRE da inbox,
o nó `seguradora` foi persistido no grafo com `razao_social =
"MAPFRE Seguros Gerais 5.À."` (glyph quebrado: `S` virou `5`, `A` virou `À`).

O `mappings/seguradoras.yaml` tem a razão canônica `"MAPFRE Seguros Gerais S.A."`.
`src/extractors/cupom_garantia_estendida_pdf.py:_enriquecer_seguradora`
usa `bilhete.setdefault("seguradora_razao_social", cfg["razao_social"])` --
`setdefault` só preenche quando ausente. O parser já preencheu com glyph,
então o YAML nunca sobrescreve.

Reprodução:

```bash
sqlite3 data/output/grafo.sqlite "SELECT json_extract(metadata, '\$.razao_social') FROM node WHERE tipo='seguradora';"
# MAPFRE Seguros Gerais 5.À.
```

Armadilha registrada em `docs/ARMADILHAS.md#22`.

## Diff proposto

```diff
# src/extractors/cupom_garantia_estendida_pdf.py:_enriquecer_seguradora
-    bilhete.setdefault("seguradora_razao_social", cfg["razao_social"])
+    # YAML é fonte canônica quando CNPJ bate; sobrescreve valor extraído
+    # (pode ter glyph quebrado -- ver ARMADILHAS.md#22).
+    bilhete["seguradora_razao_social"] = cfg["razao_social"]
```

Mesmo padrão aplicável a `_enriquecer_*` futuros em Sprints 44 (DANFE)
e 46 (XML NFe) se surgirem.

## Justificativa

- **Impacto atual:** 1 nó seguradora com razão ilegível. Filtros textuais
  futuros (`WHERE razao_social LIKE '%MAPFRE%'`) falhariam com `5.À.`.
- **Risco de falso-positivo:** zero. Sobrescrita só ocorre com match
  exato de CNPJ contra cadastro canônico -- se o YAML tem erro, corrige
  no YAML.
- **Alternativa:** aplicar `glyph_tolerant` pós-extração na razão. Mais
  complexo e não sistêmico -- YAML DEVE ser fonte canônica.

## Teste de regressão

```bash
.venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py::TestSeguradoraYaml -v
# Novo teste: test_razao_social_canonica_sobrescreve_glyph
# Asserção: mesmo com entrada "5.À." no texto, após enrich bilhete tem "S.A."

# Pós-absorção, validar no grafo real:
./run.sh --tudo
sqlite3 data/output/grafo.sqlite \
    "SELECT json_extract(metadata, '\$.razao_social') FROM node WHERE tipo='seguradora';"
# esperado: MAPFRE Seguros Gerais S.A.
```

## Decisão humana

**Aprovada em:** (preencher ao aprovar)
**Rejeitada em:** (preencher ao rejeitar)
**Motivo:** (preencher se rejeitada)

---

*"O YAML é a verdade; o extrato é aproximação." -- princípio de fonte canônica*
