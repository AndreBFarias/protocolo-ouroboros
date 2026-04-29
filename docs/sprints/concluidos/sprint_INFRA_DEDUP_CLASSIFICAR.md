---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: INFRA-DEDUP-CLASSIFICAR
  title: "Dedup automatico de PDFs bit-a-bit identicos em data/raw/_classificar/"
  prioridade: P1
  estimativa: ~1.5h
  origem: "achado da fase Opus Sprint 103: 3 copias do mesmo PDF (_CLASSIFICAR_6c1cc203.pdf + _1 + _2) foram detectadas em runtime. Residual da Sprint 97 (page-split tentativo)"
  touches:
    - path: src/intake/orchestrator.py
      reason: "ao final de cada page-split tentativo, deletar copias bit-a-bit antes de marcar como _classificar"
    - path: src/intake/dedup_classificar.py
      reason: "novo modulo: helper isolado para auditoria e dedup standalone"
    - path: scripts/dedup_classificar_lote.py
      reason: "novo: roda dedup retroativo em data/raw/_classificar/ existente"
    - path: tests/test_dedup_classificar.py
      reason: "regressao: 3 PDFs bit-a-bit -> 1 sobra; com sufixos _1, _2 mantem o canonico"
  forbidden:
    - "Apagar PDFs com conteudo distinto mesmo que tenham nomes parecidos"
    - "Tocar pastas fora de data/raw/_classificar/"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dedup_classificar.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "PDFs bit-a-bit identicos em _classificar/ sao detectados via sha256 e o canonico (sem sufixo _N) e mantido"
    - "scripts/dedup_classificar_lote.py com flags --dry-run e --executar (idempotente)"
    - "Helper integrado no orchestrator: ao mover copias para _classificar, dedup automatico evita acumulacao"
    - "Suite full preserva (1.917+ tests passed)"
  proof_of_work_esperado: |
    sha256sum data/raw/_classificar/*.pdf | sort | uniq -d -w 64
    # Antes: 3 hashes iguais para 6c1cc203
    .venv/bin/python scripts/dedup_classificar_lote.py --executar
    sha256sum data/raw/_classificar/*.pdf | sort | uniq -d -w 64
    # Depois: 0 duplicatas
```

---

# Sprint INFRA-DEDUP-CLASSIFICAR

**Status:** BACKLOG (P1, criada 2026-04-28 como achado da fase Opus Sprint 103)

## Motivação

A fase Opus da Sprint 103 listou 3 pendências em `_classificar/` que são copias bit-a-bit do mesmo conteúdo:

```
_CLASSIFICAR_6c1cc203.pdf      (sha256 X)
_CLASSIFICAR_6c1cc203_1.pdf    (sha256 X)  -- duplicata
_CLASSIFICAR_6c1cc203_2.pdf    (sha256 X)  -- duplicata
```

Causa raiz: Sprint 97 (page-split heterogeneo) faz tentativa + reversao. Quando reverte, o arquivo original mais N copias com sufixo `_1`, `_2` etc. acabam ficando todos em `_classificar/`. Ninguem deduplica depois.

## Implementação

### Helper `src/intake/dedup_classificar.py`

```python
def deduplicar_classificar(pasta: Path, dry_run: bool = True) -> dict:
    """Detecta e remove copias bit-a-bit em data/raw/_classificar/.

    Mantem o arquivo canonico (sem sufixo _N) quando ele existe; senao
    mantem o de menor lexicografia.

    Devolve dict com {removidos: int, preservados: int, grupos: list[dict]}.
    """
```

Estrategia:
1. Calcula sha256 de cada PDF em `_classificar/`.
2. Agrupa por hash.
3. Para grupos com 2+ membros: mantem canônico (sem `_<N>`) e marca outros para remocao.
4. Em `dry_run`, so reporta. Em `--executar`, deleta os fosseis.

### Integração no orchestrator

Em `src/intake/orchestrator.py`, apos cada `expandir_pdf_multipage` que reverteu para single, chamar `deduplicar_classificar` na pasta destino para evitar acumulacao em runtime.

### Script `scripts/dedup_classificar_lote.py`

Wrapper CLI com `--dry-run` (default) e `--executar`. Reusa o helper.

### Integração com `run.sh --full-cycle`

No fim do `--full-cycle`, antes do pipeline final, roda `dedup_classificar_lote --executar`.

## Testes regressivos (`tests/test_dedup_classificar.py`)

1. 3 PDFs sintéticos bit-a-bit identicos -> 1 sobra (canônico).
2. 2 PDFs com sufixos `_1`, `_2` mas sem canônico -> mantem o `_1`.
3. PDFs com hashes distintos não são tocados.
4. dry_run não remove nada, so reporta.
5. Idempotente: rodar 2x devolve 0 removidos na 2a.

## Dependências

- Independente. Pode rodar agora em volume real (3 fosseis Americanas).
