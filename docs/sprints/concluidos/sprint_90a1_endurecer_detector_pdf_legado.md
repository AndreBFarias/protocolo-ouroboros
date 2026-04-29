---
concluida_em: 2026-04-27
---

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

**Status:** CONCLUÍDA (2026-04-27, baseline pytest 1.886 -> 1.892 +6 testes 90a-1)

## Resultado

`src/utils/file_detector.py:510-552`: regras de detecção Itaú e Santander agora exigem `>= 2 ancoras` (de uma tupla de 5-6 marcadores). Antes bastava 1 substring (`ITAÚ UNIBANCO` ou `SANTANDER`).

### Itaú -- 5 âncoras
- `ITAÚ UNIBANCO` em texto upper.
- `agência: 6450` (literal) ou `AGÊNCIA: 6450`.
- `SALDO ANTERIOR`.
- `EXTRATO DE CONTA` ou `EXTRATO MENSAL`.
- `ITAU.COM.BR` ou `ITAU.COM`.

### Santander -- 6 âncoras
- `SANTANDER`.
- `4220 XXXX XXXX 7342` (cartão canônico).
- `FATURA` ou `EXTRATO`.
- `CARTÃO DE CRÉDITO` (com ou sem til).
- `VENCIMENTO` + `PAGAMENTO MÍNIMO` (combinados).
- `BANCO SANTANDER`.

## Testes regressivos (`tests/test_file_detector.py` -- novo, 6 testes)

- Extrato Itaú real (4 âncoras): casa.
- Holerite G4F com "Conta credito: ITAU UNIBANCO agencia: 6450" (1 âncora real, sem `ITAÚ` com til): NÃO casa.
- Recibo TED Itaú (1 âncora): NÃO casa.
- Fatura Santander real (4 âncoras): casa.
- Holerite G4F com "Conta credito: SANTANDER" (1 âncora): NÃO casa.
- PDF arbitrário com só "SANTANDER" no texto: NÃO casa.

Defesa em profundidade da Sprint 90a (`registry.py::_tem_assinatura_holerite`) mantida -- agora redundante mas inofensiva. Os 8 testes da Sprint 90a continuam verdes.

Suite full: 1.886 -> **1.892 passed** (+6 da 90a-1). Lint exit 0. Smoke 8/8 + 23/23.
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
