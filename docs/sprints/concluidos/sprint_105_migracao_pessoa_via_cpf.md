---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 105
  title: "Migracao automatica NFCe casal->andre via CPF do consumidor (pessoas.yaml)"
  prioridade: P1
  estimativa: ~2h
  origem: "achado da fase Opus Sprint 103: 2 NFCes (7464/7466) em data/raw/casal/ com CPF do Andre no cupom"
  touches:
    - path: src/intake/pessoa_detector.py
      reason: "extrair CPF do conteudo do PDF/imagem e cruzar com pessoas.yaml -- ja existe esse fluxo, mas nao corre na re-classificacao"
    - path: src/intake/orchestrator.py
      reason: "antes de rotear para data/raw/casal/, checar se CPF do consumidor casa com Andre ou Vitoria isoladamente"
    - path: scripts/migrar_pessoa_via_cpf.py
      reason: "novo: roda em volume retroativo, detecta inconsistencias e migra (dry-run/executar)"
    - path: tests/test_migracao_pessoa_cpf.py
      reason: "regressao: NFCe com CPF Andre em casal/ migra; NFCe sem CPF claro fica"
  forbidden:
    - "Mover arquivos sem confirmar CPF via pessoas.yaml (gitignored)"
    - "Tocar arquivos cuja pessoa ETL ja seja explicita (nao 'casal inferido')"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_migracao_pessoa_cpf.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Quando ETL classifica 'pessoa=casal (inferido)' E o CPF no conteudo casa com Andre ou Vitoria, migra arquivo + atualiza node no grafo"
    - "Pessoa nao-inferida (declarada no metadata) nunca e tocada"
    - "Roda em --full-cycle automaticamente"
  proof_of_work_esperado: |
    # Antes
    ls data/raw/casal/nfs_fiscais/nfce/*.pdf | wc -l
    # 2 (NFCes Americanas com CPF do Andre)
    .venv/bin/python scripts/migrar_pessoa_via_cpf.py --executar
    # Depois
    ls data/raw/casal/nfs_fiscais/nfce/*.pdf | wc -l
    # 0
    ls data/raw/andre/nfs_fiscais/nfce/*.pdf | wc -l
    # +2 vs antes
```

---

# Sprint 105 -- Migração automatica pessoa via CPF

**Status:** BACKLOG (P1, criada 2026-04-28 como achado Opus Sprint 103)

## Motivação

Fase Opus identificou 2 NFCes (nodes 7464 e 7466) em `data/raw/casal/nfs_fiscais/nfce/` com CPF do Andre no cupom. Causa raiz: classifier antigo, antes da Sprint 90 ter pessoa_detector via CNPJ/CPF, roteava para `casal/` quando não conseguia determinar pessoa especifica.

Os dois nodes tem `pessoa: casal (inferido)` no metadata ETL. O Opus, lendo o conteúdo, identificou que CPF do consumidor era do Andre.

## Implementação

### 1. `src/intake/pessoa_detector.py` ja existe

Verificar se a logica `_casar_via_pessoas_yaml` (Sprint P0.2 / commit `db0...`) esta sendo chamada na rota de re-classificacao. Se não, integrar.

### 2. `scripts/migrar_pessoa_via_cpf.py`

Itera todos os PDFs/imagens em `data/raw/casal/`, extrai conteúdo via OCR/text, busca CPF, cruza com `pessoas.yaml`. Se casa com pessoa especifica:
- Move arquivo para `data/raw/<pessoa>/.../`
- Atualiza `metadata.arquivo_origem` E `pessoa` do node correspondente no grafo.

`--dry-run` por default; `--executar` aplica.

### 3. Integrar em `run.sh --full-cycle`

Apos inbox processing, rodar `migrar_pessoa_via_cpf --executar` automaticamente.

## Testes regressivos

1. NFCe sintetica com CPF do Andre em pasta `casal/` -> migra para `andre/`.
2. NFCe sem CPF claro -> mantem em `casal/` (não adivinha).
3. NFCe com pessoa explicita (não inferida) -> não toca mesmo se CPF presente.
4. Idempotencia.

## Dependências

- Sprint P0.2 (pessoa_detector com CPF/CNPJ) ja em main.
- `mappings/pessoas.yaml` deve existir com Andre e Vitoria.
