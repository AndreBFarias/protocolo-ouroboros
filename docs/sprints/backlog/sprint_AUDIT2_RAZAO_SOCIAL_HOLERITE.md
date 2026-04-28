# Sprint AUDIT2-RAZAO-SOCIAL-HOLERITE -- Razao social completa em holerites

**Origem**: Auditoria self-driven 2026-04-29, achado A4.
**Prioridade**: P2.
**Estimado**: 1h.

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
