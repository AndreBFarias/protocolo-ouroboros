## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 93c
  title: "Restaurar rotulagem Nubank PJ no pipeline (família C)"
  depends_on:
    - sprint_id: 93
      artifact: "docs/auditoria_extratores_2026-04-23.md"
  touches:
    - path: src/extractors/nubank_cc.py
      reason: "garantir banco_origem=Nubank (PJ) quando arquivo é PJ"
    - path: src/extractors/nubank_cartao.py
      reason: "idem para cartão PJ"
    - path: src/transform/normalizer.py
      reason: "preservar rótulo Nubank (PJ) no normalizar_transacao"
    - path: scripts/auditar_extratores.py
      reason: "aceitar Nubank (PJ) como banco_origem válido no filtro XLSX"
    - path: tests/test_nubank_cc.py
      reason: "teste de regressão que fixture PJ produz banco_origem Nubank (PJ)"
  forbidden:
    - "Alterar assinatura de normalizar_transacao"
    - "Mudar layout XLSX (coluna banco_origem é stable)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Arquivos em data/raw/vitoria/nubank_pj_* geram transações com banco_origem=Nubank (PJ)"
    - "XLSX aba extrato inclui rótulo Nubank (PJ) como valor válido (hoje só tem Nubank e Nubank (PF))"
    - "scripts/auditar_extratores.py --banco nubank_pj_cc retorna contagem no XLSX > 0"
    - "Teste de regressão cobre fixture PJ"
    - "Baseline de testes mantida"
```

---

# Sprint 93c — rotulagem Nubank PJ perdida no pipeline (família C)

**Status:** BACKLOG
**Prioridade:** P1 (Vitória tem MEI ativo, transações PJ ficam invisíveis no XLSX hoje)
**Origem:** `docs/auditoria_extratores_2026-04-23.md` §Família C

## Problema

Sprint 93 detectou que `nubank_pj_cc` e `nubank_pj_cartao` -- diretórios com arquivos brutos da conta PJ da Vitória -- geram extração bruta, mas a consolidação no XLSX tem **zero transações** com `banco_origem="Nubank (PJ)"`.

Extrator `nubank_cc.py` ou `nubank_cartao.py` detecta o subtipo PJ (via path `vitoria/nubank_pj_*`), mas:
- Produz `banco_origem="Nubank (PJ)"` corretamente no dict bruto, OU
- Normalizer sobrepõe para `"Nubank"` genérico, OU
- XLSX writer filtra para só 6 bancos pré-declarados.

Investigação inicial (Sprint 93 audit):
- XLSX tem `banco_origem` distintos: C6, Histórico, Itaú, Nubank, Nubank (PF), Santander.
- **Sem Nubank (PJ)**, embora fisicamente existam 12 + 1 = 13 arquivos PJ em `data/raw/vitoria/nubank_pj_*`.

## Fix candidato

1. Grep `Nubank (PJ)` em src/: verificar se algum extrator produz literal.
2. Se produz: rastrear onde é descartado/renomeado (provavelmente `normalizer.py::inferir_pessoa` ou `xlsx_writer.py`).
3. Restaurar rotulagem: `banco_origem="Nubank (PJ)"` chega intacto ao XLSX.
4. Teste de regressão com fixture sintética.

## Considerações

- **Sprint 90 (pessoa_detector CNPJ + razão)** ajudou a detectar que PJ é Vitória, mas `banco_origem` é ortogonal a `pessoa`.
- **Dedup por banco_origem** pode ter colapsado Nubank (PJ) em Nubank durante processamento.
- Volume atual: ~13 arquivos PJ. Delta estimado: R$ 126k + R$ 47k do relatório da auditoria.

## Armadilhas

- **MEI da Vitória** tem CNPJ 52.488.753 (`mappings/pessoas.yaml`). Dashboard filtra por `pessoa=Vitória` mas não por banco_origem específico -- PJ vs PF fica misturado em análises de receita.
- **IRPF tagger** pode usar `banco_origem` para heurísticas de "rendimento_tributavel" (PJ) vs "rendimento_isento" (PF aplicação). Rotulagem errada distorce tags.

## Proof-of-work

- `.venv/bin/python -c "import pandas as pd; df=pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato'); print(df['banco_origem'].value_counts())"` inclui `Nubank (PJ)` com contagem > 0.
- `scripts/auditar_extratores.py --banco nubank_pj_cc` retorna delta reduzido.

---

*"Um rótulo perdido no pipeline é um domínio perdido na análise." -- princípio da rotulagem canônica*
