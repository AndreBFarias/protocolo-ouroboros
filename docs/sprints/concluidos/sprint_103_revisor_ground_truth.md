---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 103
  title: "Revisor visual com ground-truth (3 colunas: ETL/Opus/Humano + diff + CSV)"
  prioridade: P1
  estimativa: ~3-4h
  origem: "ESTADO_ATUAL.md backlog -- evolucao da Sprint D2 para alimentar futuras metricas de fidelidade do extrator"
  touches:
    - path: src/dashboard/paginas/revisor.py
      reason: "schema +2 colunas (valor_etl, valor_opus), helper extrair_valor_etl_para_dimensao, helper gerar_ground_truth_csv, UI 3-colunas, botao Exportar CSV"
    - path: tests/test_sprint_103_ground_truth.py
      reason: "14 testes regressivos cobrindo migration, persistence, mapping de dimensoes, export CSV, mascaramento PII"
  forbidden:
    - "Quebrar API existente de salvar_marcacao (parametros novos sao opcionais)"
    - "Quebrar testes da Sprint D2 (39 testes existentes do revisor mantidos)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_sprint_103_ground_truth.py tests/test_revisor.py tests/test_dashboard_revisor.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Tabela revisao ganha 2 colunas: valor_etl TEXT, valor_opus TEXT (default NULL)"
    - "Migration graceful: DBs antigos (Sprint D2) sao migrados in-place via ALTER TABLE"
    - "salvar_marcacao aceita kwargs valor_etl e valor_opus (None preserva valor anterior via COALESCE)"
    - "extrair_valor_etl_para_dimensao mapeia 5 dimensoes canonicas com fallbacks (path para pessoa)"
    - "gerar_ground_truth_csv produz CSV com 8 colunas + flag divergencia + PII mascarada"
    - "UI mostra 'ETL: <valor>' acima do radio em cada dimensao"
    - "Botao 'Exportar ground-truth CSV' grava em docs/revisoes/ com timestamp"
    - "39 testes do revisor (Sprint D2) continuam passando"
  proof_of_work_esperado: |
    .venv/bin/pytest tests/test_sprint_103_ground_truth.py -v
    # 14 passed
    
    grep "valor_etl\|valor_opus\|gerar_ground_truth_csv" src/dashboard/paginas/revisor.py | wc -l
    # > 10
```

---

# Sprint 103 -- Revisor com ground-truth

**Status:** CONCLUÍDA (2026-04-28, +14 testes 103 sem regressão dos 39 da Sprint D2)

## Motivação

A Sprint D2 (commit `b3026a7`) entregou o Revisor Visual: humano marca cada dimensão de cada pendência como OK/Erro/N-A. Mas a marcação humana **isolada** não permite medir fidelidade do extrator — precisaria saber o que o ETL "achou" e comparar com o veredito humano.

Sprint 103 transforma a tabela `revisao` num registro **3-colunas** (ETL/Opus/Humano) por dimensão, permitindo:
1. Visualização side-by-side na UI: humano vê o que o pipeline extraiu antes de marcar.
2. Export ground-truth CSV: análise quantitativa pós-sessão.
3. Flag `divergencia`: facilita filtro de casos onde ETL errou ou Opus discordou de ETL.

## Implementação

### 1. Schema migration graceful

`garantir_schema()` agora detecta DBs antigos via `PRAGMA table_info(revisao)` e adiciona colunas faltantes via `ALTER TABLE ADD COLUMN`. DBs criados pela Sprint D2 são migrados sem perda de dados na primeira chamada após upgrade.

### 2. salvar_marcacao retrocompatível

```python
def salvar_marcacao(
    caminho, item_id, dimensao, ok,
    observacao="", valor_etl=None, valor_opus=None,
)
```

`COALESCE(excluded.valor_etl, valor_etl)` no UPDATE: passar `None` preserva o valor anterior (humano pode atualizar `ok` e `observacao` sem precisar reinformar valor_etl).

### 3. Helper `extrair_valor_etl_para_dimensao(pendencia, dimensao) -> str`

Mapeia metadata canônico para string visível por dimensão:

| Dimensão | Fonte |
|---|---|
| data | `metadata.data_emissao` |
| valor | `metadata.total` formatado (`f"{x:.2f}"`) |
| itens | `len(metadata.itens)` se lista; vazio se ausente |
| fornecedor | `metadata.razao_social` ou `nome_canonico` (PII mascarada) |
| pessoa | `metadata.pessoa` ou inferida do path (`andre/`, `casal/`, `vitoria/`) |

Vazio significa "ETL não soube" — sinal claro para o humano.

### 4. Helper `gerar_ground_truth_csv(caminho_db, caminho_csv) -> int`

Cabeçalho:
```
item_id, dimensao, valor_etl, valor_opus, valor_humano, divergencia, observacao, ts
```

`valor_humano` mapeia `ok={1: "OK", 0: "Erro", None: "Não-aplicável"}`.
`divergencia = "1"` se (`valor_etl != valor_opus` E ambos não-vazios) OU (humano marcou Erro).

PII mascarada nos campos `valor_etl`, `valor_opus` e `observacao` antes da escrita (LGPD-safe). DB inexistente produz CSV apenas com cabeçalho — sem levantar.

### 5. UI

- Cada dimensão (`data`, `valor`, `itens`, `fornecedor`, `pessoa`) mostra `st.caption("ETL: <valor>")` ACIMA do radio.
- Botão "Exportar ground-truth CSV" grava em `docs/revisoes/ground_truth_<timestamp>.csv`.
- Layout: 3 colunas (`Gerar relatório` | `Sugerir patch` | `Exportar CSV`).

## Resultado

| Métrica | Antes | Depois |
|---|---|---|
| `pytest` | 1.903 passed | **1.917 passed** (+14) |
| Testes do revisor | 39 (Sprint D2) | **53** (39 + 14 da 103) |
| Colunas na tabela `revisao` | 5 | 7 |
| Helpers públicos novos | -- | `extrair_valor_etl_para_dimensao`, `gerar_ground_truth_csv` |
| Botões de export na UI | 2 (relatório + patch) | 3 (+CSV) |
| `make lint` | exit 0 | **exit 0** |
| `make smoke` | 8/8 + 23/23 | **8/8 + 23/23** |

## Próximos passos sugeridos (não escopo desta sprint)

- Quando dono autorizar a sessão humana de validação via Revisor (~6.5h), ela pode preencher `valor_humano` para 760 arquivos. Após isso, exportar CSV e analisar fidelidade quantitativa por extrator.
- Sprint 103b: integrar `valor_opus` automaticamente — supervisor Opus principal lê pendência via API e propõe valor; UI mostra discordância com ETL antes do humano decidir.

---

*"Verdade não se decreta -- se compara." -- princípio do ground-truth honesto*
