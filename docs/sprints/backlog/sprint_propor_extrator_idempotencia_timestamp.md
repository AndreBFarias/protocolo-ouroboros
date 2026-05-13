---
id: PROPOR-EXTRATOR-IDEMPOTENCIA-TIMESTAMP
titulo: 0. SPEC (machine-readable)
status: backlog
concluida_em: null
prioridade: P3
data_criacao: '2026-05-04'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: PROPOR-EXTRATOR-IDEMPOTENCIA-01
  title: "scripts/propor_extrator.py: não regravar arquivo se conteúdo (excluindo timestamp) é idêntico"
  prioridade: P3
  estimativa: 30min
  origem: "achado colateral 2026-05-04: 5 .md em docs/propostas/extracao_cupom/ regenerados com diff só de timestamp; commit 493982d mostra padrão recorrente"
  touches:
    - path: scripts/propor_extrator.py
      reason: "antes de write, comparar conteúdo existente com novo (excluindo linha 'Data: <iso>'); se idêntico, skip"
    - path: tests/test_propor_extrator_idempotencia.py
      reason: "NOVO -- 4 testes: re-execução não muda mtime, conteúdo igual skip, conteúdo novo overwrite, primeira execução grava"
  forbidden:
    - "Quebrar geração inicial (arquivo novo deve ser criado normalmente)"
    - "Tocar template de proposta (mappings/_template.md ou similar)"
  hipotese:
    - "Linha 'Data: <iso>' é gerada com datetime.now() no script. Confirmar via grep."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_propor_extrator_idempotencia.py -v"
    - cmd: ".venv/bin/python scripts/propor_extrator.py <tipo> --amostra <fixture> --executar"
  acceptance_criteria:
    - "Re-executar gerador 2x sobre mesma amostra: 2ª execução NÃO modifica arquivo (mtime preservado)"
    - "Conteúdo realmente novo: arquivo é regravado normalmente"
    - "Linha 'Data:' é a única exceção tolerada na comparação"
    - "git status após re-executar gerador: zero arquivos modificados em docs/propostas/extracao_cupom/"
  proof_of_work_esperado: |
    # Hipótese: linha Data
    grep -n "datetime.now\|isoformat" scripts/propor_extrator.py

    # AC: idempotência
    .venv/bin/python scripts/propor_extrator.py cupom --amostra <fixture> --executar
    mtime1=$(stat -c %Y docs/propostas/extracao_cupom/<sha8>.md)
    sleep 2
    .venv/bin/python scripts/propor_extrator.py cupom --amostra <fixture> --executar
    mtime2=$(stat -c %Y docs/propostas/extracao_cupom/<sha8>.md)
    test "$mtime1" = "$mtime2" && echo "idempotente OK"
    git status --short docs/propostas/extracao_cupom/
    # esperado: vazio
```

---

# Sprint PROPOR-EXTRATOR-IDEMPOTENCIA-01

**Status:** BACKLOG (P3, anti-débito)

Sub-sprint formalizada na sessão 2026-05-04 ao detectar que `git status`
mostrava 5 propostas com diff só de timestamp. Padrão repetido pelo commit
`493982d`. Idempotência fraca polui DX e mascara mudanças reais.

Não bloqueia nada. Pode ser executada em qualquer sessão livre.

---

*"O que se repete, importa. O que se repete sem mudar, distrai." — princípio do sinal vs ruído*
