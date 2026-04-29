---
concluida_em: 2026-04-27
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 95a
  title: "Holerite persiste 'liquido' separado de 'total' no metadata do grafo"
  prioridade: P2
  estimativa: ~1h
  origem: "achado colateral ACH95-1 durante execução da Sprint 95 (linking runtime)"
  touches:
    - path: src/extractors/contracheque_pdf.py
      reason: "linha 232 atual grava {'total': float(registro.get('bruto') or 0.0)} -- perde info do líquido"
    - path: tests/test_contracheque_pdf.py
      reason: "regressão para garantir que metadata.liquido é persistido"
  forbidden:
    - "Mexer no schema canônico do node 'documento' (ADR-14) -- só adicionar campo opcional em metadata"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_contracheque_pdf.py tests/test_linking_runtime.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Node holerite no grafo passa a ter metadata.liquido (float)"
    - "Sprint 95 mantém 20+ holerites linkados (sem regressão)"
    - "Linker pode opcionalmente preferir match em líquido (mais preciso) vs bruto (atual, requer diff_valor=0.30)"
  proof_of_work_esperado: |
    sqlite3 data/output/grafo.sqlite \
      "SELECT json_extract(metadata, '\$.liquido') FROM node \
       WHERE tipo='documento' AND json_extract(metadata, '\$.tipo_documento')='holerite' LIMIT 5;"
    # Esperado: 5 floats não-null
```

---

# Sprint 95a -- Holerite persiste líquido separado de bruto

**Status:** CONCLUÍDA (2026-04-27, baseline pytest 1.884 -> 1.886 +2 testes 95a)

## Resultado

`src/extractors/contracheque_pdf.py` linhas 225-241: documento dict ganhou `bruto` e `liquido` separados. `total` mantido como bruto por compat (Sprint 48 + Sprint 95). `ingerir_documento_fiscal` copia todos os campos para `metadata` automaticamente.

| Campo metadata | Antes | Depois |
|---|---|---|
| `total` | bruto | bruto (preservado) |
| `bruto` | ausente | bruto (novo) |
| `liquido` | ausente | liquido (novo) |

Testes regressivos em `tests/test_contracheque_pdf.py`:
- `test_sprint_95a_metadata_grafo_persiste_liquido_e_bruto` -- valida G4F com bruto 8657.25 e liquido 6372.37.
- `test_sprint_95a_liquido_zero_quando_registro_sem_liquido` -- graceful quando registro incompleto.

Linker (Sprint 95) NÃO foi modificado nesta sprint. O ajuste para preferir `metadata.liquido` (apertando diff_valor de 0.30 para 0.05) fica como melhoria futura -- spec 95a-1 se for medida necessária após próxima reextração.
**Origem:** Achado colateral ACH95-1 durante execução da Sprint 95. Linker precisou de tolerância de diff_valor=0.30 para casar holerite (que persiste só "bruto") com tx PAGTO SALARIO (que carrega o líquido). Persistir também o líquido permitiria match mais apertado (diff_valor=0.05).

## Motivação

Em `src/extractors/contracheque_pdf.py:232`, holerite é gravado no grafo como:
```python
{"total": float(registro.get("bruto") or 0.0)}
```

Perde-se a informação do líquido. O linker (Sprint 95) compensa com janela ampla de valor (30%), mas isso aumenta risco de falso positivo. Cenário: dois meses de holerite com bruto similar mas tx PAGTO SALARIO de meses adjacentes -- diff_valor=0.30 pode aceitar match cruzado.

## Escopo

### Fase 1 (15min)
Confirmar que `registro` tem chave `liquido` separada na função extratora. Se sim, persistir.

### Fase 2 (30min)
Editar `src/extractors/contracheque_pdf.py` para gravar:
```python
{
  "total": float(registro.get("bruto") or 0.0),
  "liquido": float(registro.get("liquido") or 0.0),
  "bruto": float(registro.get("bruto") or 0.0),
}
```

Manter `total` por compatibilidade (Sprint 48 e Sprint 95 dependem dele).

### Fase 3 (15min)
Em `src/graph/linking.py`, opcionalmente preferir `metadata.liquido` quando presente (apertar `diff_valor` para 0.05). Se não presente, fallback ao `total`.

## Armadilhas

- **Schema canônico ADR-14:** não mudar o nome de `total` (já existe e é usado). Adicionar `liquido` como campo opcional.
- **Idempotência:** `INSERT OR IGNORE` deve cobrir, mas testar duas rodadas seguidas.

## Dependências

- Sprint 95 já em main (commit `2df40ae`).

---

*"O líquido é a verdade do salário; o bruto é a aspiração do contrato." -- princípio do match-pelo-real*
