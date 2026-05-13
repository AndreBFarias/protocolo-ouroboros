---
id: INFRA-LINKING-HOLERITE-TOLERANCIA-RECALIBRAR
titulo: Recalibrar tolerância de fusão holerite multi-fonte (5% pode ser baixo)
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-13
fase: SANEAMENTO
depende_de:
  - INFRA-LINKING-HOLERITE-MULTI-FONTE (concluída em 2026-05-13)
esforco_estimado_horas: 2
origem: achado colateral do executor D (ab7964ac) na implementação da INFRA-LINKING-HOLERITE-MULTI-FONTE em 2026-05-13. Runtime real mostrou que apenas 1 dos 10 pares G4F+INFOBASE com mesma competência foi fundido (diff 1.07% no 13o INTEGRAL 2025-12). Os outros 9 pares ficaram fora porque diff valor_liquido é 11.7-15.5%, acima do limiar 5%.
---

# Sprint INFRA-LINKING-HOLERITE-TOLERANCIA-RECALIBRAR

## Contexto

A sprint INFRA-LINKING-HOLERITE-MULTI-FONTE (concluída 2026-05-13, commit 4ec00ea) implementou fusão pré-linker via estratégia A: holerites com mesma competência e valor_liquido ±5% são considerados "mesma realidade", gerando aresta `_alias_de` e mantendo apenas 1 representante no linking.

Runtime real revelou:
- 10 pares G4F + INFOBASE com mesma competência foram identificados.
- Apenas 1 par foi fundido: `HOLERITE|G4F_-_13º_INTEGRAL|2025-12` (R$ 5771,50) + `HOLERITE|INFOBASE_-_13º_INTEGRAL|2025-12` (R$ 5833,33), diff = 1,07%.
- 9 pares ficaram fora porque diff = 11,7-15,5%.

## Hipótese

A diferença sistemática entre G4F e INFOBASE para o mesmo holerite vem de:
- G4F é a folha bruta processada pela empresa terceirizada.
- INFOBASE é a folha consolidada (com benefícios, ajustes de PLR, descontos retroativos).

Os 2 documentos representam o **mesmo evento real** (1 depósito) mas com valores líquidos legitimamente diferentes (G4F mostra base CLT, INFOBASE mostra líquido pós-ajustes).

## Decisões pendentes

1. **Aumentar tolerância para 20%?** Resolve 9 pares mas pode falsamente fundir holerites de meses adjacentes com valor parecido.
2. **Usar competência + CPF do funcionário como chave canônica em vez de valor?** Mais robusto mas exige campos populados (validar se ambas as fontes têm CPF mascarado idêntico).
3. **Heurística híbrida**: fundir se mesma competência + valor ±20% + (mesmo CPF funcionário OU mesma empresa.razao_social pattern).

Recomendação: heurística híbrida (decisão 3).

## Validação ANTES

```bash
.venv/bin/python -c "
import sqlite3
con = sqlite3.connect('data/output/grafo.sqlite')
cur = con.execute(\"\"\"
SELECT json_extract(metadata,'\$.competencia') as comp,
       json_extract(metadata,'\$.fornecedor') as forn,
       json_extract(metadata,'\$.total') as total,
       json_extract(metadata,'\$.cpf_funcionario_mascarado') as cpf
FROM node WHERE tipo='documento'
  AND json_extract(metadata,'\$.tipo_documento') LIKE 'holerite%'
ORDER BY comp DESC
\"\"\")
for r in cur: print(r)
"
```

Confere se CPF está populado e se diff médio entre G4F e INFOBASE é consistente (~12-15%).

## Proof-of-work esperado

```bash
./run.sh --tudo 2>&1 | grep "alias_fundidos"
# Esperado: alias_fundidos >= 10 (eram 1 antes)
ls docs/propostas/linking/ | grep -i holerite | wc -l
# Esperado: <= 2 (eram 8 antes da v1; 1 antes desta v2)
```

## Padrão canônico aplicável

- (hh) Ingestão dupla escapa dedup — aplicado a documentos.
- (l) Achado colateral vira sprint-filha — esta sprint nasceu do achado do executor D.

---

*"Tolerância numérica é hipótese; só dado real confirma." -- princípio da calibração empírica*
