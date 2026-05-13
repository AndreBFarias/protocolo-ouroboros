---
id: FA-OFX-DUPLICACAO-ACCOUNTS
titulo: 0. SPEC (machine-readable)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-24'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: Fa-ofx-duplicacao
  title: "ExtratorOFX duplica transacoes ao iterar account + accounts"
  depends_on:
    - sprint_id: F
      artifact: "tests/test_ofx_parser.py (teste xfail registra bug)"
  touches:
    - path: src/extractors/ofx_parser.py
      reason: "remover duplo loop ou deduplicar por fitid"
    - path: tests/test_ofx_parser.py
      reason: "remover @pytest.mark.xfail e validar contagem unica"
  forbidden:
    - "Quebrar arquivos OFX que tenham somente accounts[] sem account"
    - "Remover dedup por UUID do pipeline sem testar impacto global"
  tests:
    - cmd: ".venv/bin/pytest tests/test_ofx_parser.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Arquivo OFX com 3 STMTTRN retorna exatamente 3 objetos dataclass"
    - "Arquivo OFX com accounts[] multiplos continua funcionando"
    - "Nenhum dado real do casal perdido (rodar re-processamento antes/depois e comparar contagens)"
```

---

# Sprint Fa-ofx-duplicacao -- deduplicacao interna do ExtratorOFX

**Status:** BACKLOG P2 (derivada da Sprint F)
**Origem:** `tests/test_ofx_parser.py` expoe que OFX sintetico com 3 STMTTRN retorna 6 objetos de dado apos passar por `ExtratorOFX.extrair()`. Causa raiz em `src/extractors/ofx_parser.py:96-119`: itera `ofx.account.statement.transactions` E `ofx.accounts` (quando presente), mas ofxparse expoe o mesmo statement nas duas colecoes em arquivos OFX com uma unica conta -- resultado e duplicata exata.

## Problema

Trecho atual em `ofx_parser.py` (linhas 96-119):

```python
if ofx.account and ofx.account.statement:
    for transacao_ofx in ofx.account.statement.transactions:
        t = self._converter_transacao(...)
        if t:
            transacoes.append(t)

if hasattr(ofx, "accounts"):
    for conta in ofx.accounts:
        if hasattr(conta, "statement") and conta.statement:
            for transacao_ofx in conta.statement.transactions:
                t = self._converter_transacao(...)
                if t:
                    transacoes.append(t)
```

Problema: `ofx.account` **aponta para o mesmo objeto** dentro de `ofx.accounts` quando o arquivo tem conta unica. Loop duplo cria duplicatas exatas (mesmo FITID, mesmo valor, mesma data). Dedup por UUID no pipeline (Sprint 22) mascara o bug em volume real, mas o extrator esta devolvendo lixo.

## Mitigacao

**Caminho A (recomendada):** manter so o loop em `ofx.accounts`:

```python
contas = list(getattr(ofx, "accounts", []) or [])
if not contas and ofx.account:
    contas = [ofx.account]

for conta in contas:
    if hasattr(conta, "statement") and conta.statement:
        for transacao_ofx in conta.statement.transactions:
            ...
```

**Caminho B (defensiva):** dedupe por (FITID, data, valor) antes de retornar -- preserva contrato atual mas adiciona overhead.

## Teste regressivo

`tests/test_ofx_parser.py::test_statement_unico_nao_deveria_duplicar` esta marcado `@pytest.mark.xfail` hoje; apos fix, remover xfail e o teste passa verde.

## Fora do escopo

- Migrar para ofxtools (libreria alternativa).
- Re-executar dedup por UUID global (ja tratado na Sprint 22).

---

*"Duplicatas silenciosas enganam o gauntlet." -- lição da Sprint F*
