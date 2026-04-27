## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 90a-1
  title: "Endurecer file_detector._detectar_pdf para exigir âncoras de extrato bancário"
  prioridade: P3
  estimativa: ~1h
  origem: "achado colateral durante execução da Sprint 90a -- causa raiz não tocada por restrição de escopo"
  touches:
    - path: src/utils/file_detector.py
      reason: "linhas 510-532 -- _detectar_pdf hoje aceita qualquer PDF com substring 'ITAÚ UNIBANCO' ou 'SANTANDER'"
    - path: tests/test_file_detector.py
      reason: "regressão -- holerite com menção a banco no rodapé não casa bancário; extrato real continua casando"
  forbidden:
    - "Mexer no schema de DeteccaoArquivo (campo `periodo` etc)"
    - "Quebrar qualquer comportamento existente em PDFs bancários reais"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_file_detector.py tests/test_intake_holerite_prioridade.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "_detectar_pdf exige >= 2 marcadores tipicos de extrato (Saldo Anterior, EXTRATO DE CONTA, Agência:, número de agência típico) além da menção ao banco"
    - "Holerite com menção 'Pagamento Itaú' no rodapé não casa bancario_itau_cc no detector legado"
    - "Extrato Itaú real continua casando bancario_itau_cc"
    - "Sprint 90a continua passando (defesa em profundidade preservada)"
  proof_of_work_esperado: |
    .venv/bin/pytest tests/test_file_detector.py tests/test_intake_holerite_prioridade.py -v
    # Tudo passa
    
    grep -n "ITAU\|ITAÚ\|SANTANDER" src/utils/file_detector.py
    # Marcadores existem mas agora exigem ancoras adicionais
```

---

# Sprint 90a-1 -- Endurecer file_detector._detectar_pdf

**Status:** BACKLOG (P3, criada 2026-04-26 como sprint-filha da Sprint 90a)
**Origem:** Achado colateral. Sprint 90a fixou o sintoma (holerite cai em pasta bancária) com defesa em profundidade no `registry.py`, mas a causa raiz está em `src/utils/file_detector.py::_detectar_pdf` (linhas 510-532) que aceita qualquer PDF com substring `"ITAÚ UNIBANCO"` ou `"SANTANDER"` no texto bruto -- incluindo holerites que mencionam o banco no rodapé.

## Motivação

Sprint 90a defendeu via pre-check `_tem_assinatura_holerite` no `registry.py`. Funciona, mas é cinto-e-suspensórios. Se um dia alguém remover o pre-check (refactor, consolidação), a causa raiz volta a expor o bug. Endurecer `_detectar_pdf` elimina a necessidade da defesa redundante.

Hoje, `_detectar_pdf` para Itaú casa quando texto contém:
- `"ITAÚ UNIBANCO"` ou `"itau.com.br"`.

Isso bate em qualquer documento que menciona o banco como forma de pagamento (holerite, recibo, comprovante de TED).

## Escopo

### Fase 1 -- Endurecer regras (30min)

Para cada banco em `_detectar_pdf`, exigir **>= 2 marcadores** dos quais 1 é o nome do banco e os outros são típicos de extrato:

```python
ANCORAS_EXTRATO_ITAU = [
    "Saldo Anterior",
    "EXTRATO DE CONTA",
    "Agência:",
    "Conta:",
    "6450",  # agência canônica do André
]

# casa apenas se >= 2 das âncoras + nome do banco
```

### Fase 2 -- Testes regressivos (30min)

`tests/test_file_detector.py`:
- Holerite com "Pagamento via Itaú" no rodapé -> NÃO casa bancario_itau_cc no detector legado.
- Extrato Itaú real (com SALDO ANTERIOR + EXTRATO DE CONTA + agência 6450) -> casa.
- Recibo de TED Itaú (só o nome) -> NÃO casa.

## Armadilhas

- **Defesa redundante da Sprint 90a:** se quebrar essa, ainda existe `_tem_assinatura_holerite` no registry. Não é fim de mundo, mas atenção.
- **Configurabilidade:** se um dia outra agência for válida (Vitória abre conta Itaú?), as âncoras precisam ser ampliáveis. Considerar mover para `mappings/extratores_legados.yaml`.

## Dependências

- Sprint 90a já em main (commit `b8ab3fe`).
- Sprint 90b (DAS PARCSN drift) é independente -- pode ser feita antes ou depois.

---

*"Defesa em profundidade é boa; defesa na causa raiz é melhor." -- princípio do fix-no-tronco*
