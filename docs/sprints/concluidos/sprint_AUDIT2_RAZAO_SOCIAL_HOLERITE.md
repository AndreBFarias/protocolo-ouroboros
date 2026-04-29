---
concluida_em: 2026-04-28
---

# Sprint AUDIT2-RAZAO-SOCIAL-HOLERITE -- Razao social completa em holerites

**Origem**: Auditoria self-driven 2026-04-29, achado A4.
**Prioridade**: P2.
**Estimado**: 1h.

## CONCLUÍDA em 2026-04-29

**Implementação**:
- `mappings/razao_social_canonica.yaml` (NOVO): mapping declarativo
  `sigla -> {razao_social_canonica, cnpj, aliases}`. Hoje cobre G4F
  (CNPJ oficial 06.146.852/0001-18) e INFOBASE.
- `src/extractors/contracheque_pdf.py`: novo helper
  `resolver_razao_social_canonica(sigla)` com cache via
  `functools.lru_cache(maxsize=1)`. Holerite agora grava
  `razao_social = razao_social_canonica`, `razao_social_curta = sigla`,
  e `cnpj_oficial = cnpj_oficial` em `metadata`.
- `scripts/backfill_razao_social_canonica.py` (NOVO): backfill idempotente
  em nodes documento `holerite` + nodes `fornecedor` ligados via aresta
  `fornecido_por`. Modo --dry-run honesto + --executar.
- `run.sh --reextrair-tudo`: encadeia
  `backfill_razao_social_canonica --executar`.
- `tests/test_backfill_razao_social_canonica.py` (NOVO, 7 testes): cobre
  resolver, sigla não mapeada, dry-run, idempotência, atualização de
  fornecedor associado.

**Runtime real**:
- 24 holerites atualizados; 2 fornecedores canônicos atualizados (G4F e
  INFOBASE).
- Distribuição final no grafo:
  - `G4F SOLUCOES CORPORATIVAS LTDA`: 13 holerites
  - `INFOBASE CONSULTORIA E INFORMATICA LTDA`: 11 holerites
- pytest: 2.007 → 2.014 passed (+7).

Verificação:
```sql
SELECT json_extract(metadata, '$.razao_social'), COUNT(*) FROM node
  WHERE tipo='documento'
    AND json_extract(metadata, '$.tipo_documento')='holerite'
  GROUP BY 1;
-- G4F SOLUCOES CORPORATIVAS LTDA|13
-- INFOBASE CONSULTORIA E INFORMATICA LTDA|11
```

**Beneficio para linker (Sprint 95)**: razão social completa permite
casar holerite com transações bancárias de tipo "PIX G4F SOLUCOES" sem
cutoff baixo de rapidfuzz. Sigla curta preservada em
`metadata.razao_social_curta` para display rápido em UIs.

---

## Spec original (preservada para histórico)

## Problema

`contracheque_pdf.py` extrai `razao_social = "G4F"` (sigla curta do PDF
header). Razao social oficial e "G4F SOLUCOES CORPORATIVAS LTDA". O mesmo
para INFOBASE -> "INFOBASE TECNOLOGIA E INFORMATICA LTDA".

Sigla e suficiente para display mas atrapalha entity resolution
(rapidfuzz não casa "G4F" com "G4F SOLUCOES" sem cutoff baixo) e
cruzamento com transações bancarias (que tem razao social completa).

## Implementação sugerida

1. Mapping declarativo em `mappings/razao_social_canonica.yaml`:
   ```yaml
   "G4F": "G4F SOLUCOES CORPORATIVAS LTDA"
   "INFOBASE": "INFOBASE TECNOLOGIA E INFORMATICA LTDA"
   ```
2. `contracheque_pdf.py` consulta o YAML antes de gravar.
3. Backfill nodes existentes via UPDATE.
4. Preservar sigla em `metadata.razao_social_curta` para display rapido.

## Proof-of-work esperado

Comparacao 4-way no Revisor para holerites: ETL = "G4F SOLUCOES CORPORATIVAS LTDA"
(canonica), Grafo = idem.

## Acceptance

- Holerites G4F+INFOBASE gravam razao_social completa.
- Linker (Sprint 95) casa holerites com transação "PIX G4F SOLUCOES"
  com 1.0 confidence (era 0.7-0.8 antes).
