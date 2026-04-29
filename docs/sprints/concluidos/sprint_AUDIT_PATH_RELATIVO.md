---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-PATH-RELATIVO
  title: "Gravar metadata.arquivo_origem como path relativo a _RAIZ_REPO"
  prioridade: P2
  estimativa: ~2h
  origem: "auditoria externa 2026-04-28 P2-05 -- paths absolutos /home/andrefarias/... não funcionam em outra maquina"
  touches:
    - path: src/graph/ingestor_documento.py
      reason: "ao gravar arquivo_origem, normaliza para path relativo a _RAIZ_REPO"
    - path: src/graph/backfill_arquivo_origem.py
      reason: "detectar_paths_quebrados resolve relativo->absoluto antes de Path.exists()"
    - path: scripts/migrar_pessoa_via_cpf.py
      reason: "_atualizar_grafo grava relativo"
    - path: src/dashboard/paginas/revisor.py
      reason: "preview_documento converte relativo->absoluto antes de abrir"
    - path: tests/test_*.py (impacto)
      reason: "ajustar fixtures que comparam strings de path absolutos"
  forbidden:
    - "Quebrar nodes existentes (migracao via Sprint 104 --reextrair-tudo)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Novos nodes documento gravam metadata.arquivo_origem como 'data/raw/andre/...' (relativo)"
    - "backfill_arquivo_origem.py resolve relativo->absoluto antes de Path.exists()"
    - "Repo clonado em outra maquina com mesmo conteudo data/raw/ funciona sem rodar backfill"
    - "Migração retroativa: rodar --reextrair-tudo apos sprint converte todos para relativos"
```

---

# Sprint AUDIT-PATH-RELATIVO

**Status:** BACKLOG (P2, criada 2026-04-28 pela auditoria externa)

## Motivação

`metadata.arquivo_origem` hoje grava `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/data/raw/...` (absoluto). Se o repo for clonado em outra maquina ou se `$HOME` mudar, todos os paths aparecem como "quebrados" e o `backfill_arquivo_origem` (Sprint 98a) tenta resolver TODOS os 50+ nodes desnecessariamente.

## Implementação

### Helper canônico

```python
# src/graph/path_canonico.py
_RAIZ_REPO = Path(__file__).resolve().parents[2]

def to_relativo(p: Path | str) -> str:
    """Converte path absoluto para relativo a _RAIZ_REPO."""
    p = Path(p).resolve()
    try:
        return str(p.relative_to(_RAIZ_REPO))
    except ValueError:
        return str(p)  # path fora do repo: preserva absoluto

def to_absoluto(p: str) -> Path:
    """Converte string (relativa ou absoluta) para Path absoluto."""
    pp = Path(p)
    return pp if pp.is_absolute() else _RAIZ_REPO / pp
```

### Pontos de gravacao

- `ingestor_documento.py`: `metadata["arquivo_origem"] = to_relativo(caminho_arquivo)`.
- `backfill_arquivo_origem.py`: `to_relativo(achado)` ao gravar.
- `migrar_pessoa_via_cpf.py::_atualizar_grafo`: idem.

### Pontos de leitura

- `backfill::detectar_paths_quebrados`: `to_absoluto(ao).exists()`.
- `revisor.py::preview_documento`: `to_absoluto` antes de abrir.

## Migração

Apos sprint codada, rodar `./run.sh --reextrair-tudo` para converter os 50 nodes existentes.

## Testes regressivos

1. Novo doc ingerido: `metadata.arquivo_origem == 'data/raw/andre/holerites/HOLERITE_2025-10_G4F_2164.pdf'` (sem prefixo).
2. Path absoluto antigo no metadata: `to_absoluto` resolve corretamente.
3. backfill em DB com paths relativos: `Path.exists()` funciona.
4. Path fora do repo (rar): preserva absoluto.

## Padrão canônico para registrar

Paths em metadata SQLite são SEMPRE relativos a `_RAIZ_REPO` quando dentro do repo. Resolução para absoluto eh runtime via helper.
