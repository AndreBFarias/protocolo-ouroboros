---
concluida_em: 2026-04-26
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 98
  title: "Renomeacao retroativa: holerites em estado bruto + 13 mal classificados"
  prioridade: P1
  estimativa: 1-2h
  origem: "auditoria 2026-04-26 -- 24 holerites com nomes 'document(N).pdf' + 13 PDFs em pastas bancarias erradas"
  depends_on:
    - "Sprint 90a (preferencialmente concluída primeiro -- previne novos casos)"
  touches:
    - path: scripts/migrar_holerites_retroativo.py
      reason: "script one-shot que move + renomeia + recalcula hash"
    - path: data/raw/andre/holerites/
      reason: "destino dos 13 mal-classificados"
  forbidden:
    - "Apagar arquivos em data/raw/originais/ (preservacao inviolavel ADR-18)"
    - "Rodar sem dry-run primeiro"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/python scripts/migrar_holerites_retroativo.py --dry-run"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Script com flag --dry-run (default) e --executar"
    - "13 PDFs em itau_cc/ + santander_cartao/ que são G4F são movidos para holerites/ com nome HOLERITE_G4F_<sha8>.pdf"
    - "Holerites em holerites/ com nome 'document(N).pdf' são renomeados para HOLERITE_<fonte>_<mes>.pdf"
    - "Originais em data/raw/originais/<sha>.<ext> permanecem intocados"
    - "Hashes registrados em log: scripts/migracao_holerites_<data>.log"
    - "Apos rodar --executar e ./run.sh --tudo, baseline pytest mantida (1530+ passed)"
  proof_of_work_esperado: |
    # Antes
    ls data/raw/andre/itau_cc/*.pdf | wc -l       # = 4 (1 Itau real + 3 holerites)
    ls data/raw/andre/holerites/document* | wc -l # = 11 (nomes brutos)
    
    # Dry-run
    .venv/bin/python scripts/migrar_holerites_retroativo.py --dry-run
    # Lista 13 + 11 = 24 acoes propostas
    
    # Execucao
    .venv/bin/python scripts/migrar_holerites_retroativo.py --executar
    
    # Depois
    ls data/raw/andre/itau_cc/*.pdf | wc -l  # = 1 (so o Itau real)
    ls data/raw/andre/holerites/HOLERITE_*.pdf | wc -l  # = 24 (todos canonicos)
```

---

# Sprint 98 -- Renomeacao retroativa de holerites

**Status:** BACKLOG (P1, criada 2026-04-26)

## Motivacao

Sprint 90a previne novos casos. Esta sprint limpa o legado:
- 13 PDFs em pastas bancarias erradas (3 itau_cc + 10 santander_cartao) -- holerites G4F.
- 24 holerites em `holerites/` com nomes brutos (`document(N).pdf`, `holerite_NNNNNNNNNNNN.pdf`).

Apos limpeza, fica facil para humano abrir a pasta e entender o que tem.

## Escopo

`scripts/migrar_holerites_retroativo.py`:

```python
"""Migra holerites mal classificados ou com nomes brutos para forma canonica."""

# Fase 1: detectar holerites em pastas erradas
# Para cada PDF em itau_cc/ e santander_cartao/:
#   - abrir, extrair primeira pagina
#   - se contém "Demonstrativo de Pagamento de Salário" ou "G4F SOLUCOES":
#     - calcular sha8
#     - mover para data/raw/andre/holerites/HOLERITE_G4F_<sha8>.pdf
#     - registrar em log

# Fase 2: renomear holerites com nomes brutos
# Para cada PDF em holerites/ matching `document*` ou `holerite_NNN`:
#   - extrair fonte (G4F | Infobase) e mes_ref do conteúdo
#   - renomear para HOLERITE_<fonte>_<mes_ref>_<sha8>.pdf

# Idempotencia: se nome ja eh canonico, pular sem erro
```

## Armadilhas

- **Sprint P2.3 dedupe-on-ingest** -- ja deve estar ativa. Re-rodar `--inbox` apos a migração não deve gerar duplicatas.
- **Originais preservados**: `data/raw/originais/<sha>.<ext>` permanecem. So `data/raw/<pessoa>/<banco>/` muda.

---

*"Limpar o legado eh tao importante quanto evitar novos casos." -- principio da migração retroativa*
