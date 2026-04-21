## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 85
  title: "XLSX de Docs Faltantes: checklist mês-a-mês com status (pendente/disponível/inbox/irrecuperável)"
  touches:
    - path: src/analysis/docs_faltantes.py
      reason: "novo: motor de cálculo do inventário + status"
    - path: scripts/gerar_xlsx_docs_faltantes.py
      reason: "novo: CLI que exporta docs_faltantes.xlsx"
    - path: data/output/docs_faltantes.xlsx
      reason: "saída mantida fora do git (já em .gitignore via data/)"
    - path: mappings/docs_esperados.yaml
      reason: "novo: regras do que é esperado (G4F jan-dez, Infobase jan-dez, etc.)"
    - path: src/dashboard/paginas/completude.py
      reason: "Sprint 75 + 85: aba Completude também exporta o XLSX e marca irrecuperáveis"
    - path: tests/test_docs_faltantes.py
      reason: "testes de cobertura"
  n_to_n_pairs:
    - ["tipos esperados em docs_esperados.yaml", "extratores existentes em src/extractors/"]
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_docs_faltantes.py -v"
      timeout: 60
  acceptance_criteria:
    - "mappings/docs_esperados.yaml lista por tipo: G4F, Infobase, Energia (Neoenergia), Água (CAESB), Internet (Claro), Plano Saúde, Psiquiatra (Ludens), Aluguel (Ki-Sabor), etc."
    - "Para cada tipo declara frequência: mensal, quinzenal, anual"
    - "scripts/gerar_xlsx_docs_faltantes.py gera data/output/docs_faltantes.xlsx com 1 aba por tipo + aba consolidada"
    - "Cada linha da aba tem: mes_ref, tipo, fornecedor, valor_esperado, valor_observado (XLSX extrato), status (pendente/inbox/disponivel/irrecuperavel)"
    - "Andre pode marcar coluna 'status' manualmente como 'irrecuperavel' quando o doc não vai mais aparecer (boleto antigo apagado do site)"
    - "Aba Completude do dashboard (Sprint 75) lê este XLSX como fonte auxiliar e EXCLUI irrecuperáveis do cálculo de gap"
    - "Proteção: ao re-rodar o script, linhas marcadas 'irrecuperavel' pelo usuário são PRESERVADAS (merge, não sobrescrever)"
  proof_of_work_esperado: |
    .venv/bin/python scripts/gerar_xlsx_docs_faltantes.py
    ls -la data/output/docs_faltantes.xlsx
    # abrir manualmente no LibreOffice e ver 1 aba por tipo com X/Y preenchidos
```

---

# Sprint 85 — XLSX de Documentos Faltantes expandido

**Status:** BACKLOG
**Prioridade:** P1
**Dependências:** Sprint 75 (gap analysis base)
**Issue:** UX-ANDRE-09

## Problema

Andre pediu:

> "também me cria um xlsx com os dados faltantes expandidos. Contracheques G4F: todos os meses (XLSX ou PDF). Infobase: todos os meses (XLSX ou PDF). Aqui do caso G4F - Janeiro - 2025 por exemplo. De forma que eu coloque os documentos um a um ali e vá marcando no excel os docs que estão na inbox."

> "vai ter documentos que acho que não vou conseguir, tipo boletos dos meses anteriores pq no site deles não aparecem mais."

Precisa:
- Inventário declarativo do que é ESPERADO (não só o que existe no XLSX de transações).
- Status por mês × tipo.
- Estado "irrecuperável" que o usuário pode marcar manualmente, persistente entre execuções.

## Implementação

### Fase 1 — `mappings/docs_esperados.yaml`

```yaml
tipos:
  - id: contracheque_g4f
    nome: "Contracheque G4F"
    pessoa: andre
    frequencia: mensal
    periodo_inicio: "2024-01"
    periodo_fim: "2026-12"     # atualizar anualmente
    extras_anuais: ["13o"]     # cria entrada extra por ano
    extrator: contracheque_pdf
    tracking_irpf: true

  - id: contracheque_infobase
    nome: "Contracheque Infobase"
    pessoa: andre
    frequencia: mensal
    periodo_inicio: "2022-01"
    periodo_fim: "2024-03"     # Andre saiu da Infobase em 2024-03
    extras_anuais: ["13o"]
    extrator: contracheque_pdf
    tracking_irpf: true

  - id: bolsa_nees
    nome: "Bolsa NEES/UFAL"
    pessoa: vitoria
    frequencia: mensal
    periodo_inicio: "2024-06"
    periodo_fim: "2026-12"
    extrator: null  # manual
    tracking_irpf: true

  - id: conta_energia
    nome: "Conta Neoenergia"
    pessoa: casal
    frequencia: mensal
    periodo_inicio: "2019-10"
    periodo_fim: "2026-12"
    extrator: energia_ocr
    tracking_irpf: false

  - id: conta_agua
    nome: "Conta CAESB"
    pessoa: casal
    frequencia: mensal
    periodo_inicio: "2019-10"
    periodo_fim: "2026-12"
    extrator: null  # OCR futuro
    tracking_irpf: false

  - id: internet
    nome: "Fatura Claro"
    pessoa: casal
    frequencia: mensal
    periodo_inicio: "2020-01"
    periodo_fim: "2026-12"
    extrator: null

  - id: plano_saude
    nome: "Plano de Saúde"
    pessoa: casal
    frequencia: mensal
    periodo_inicio: "2022-01"
    periodo_fim: "2026-12"
    tracking_irpf: true

  - id: psiquiatra
    nome: "Clínica Ludens (psiquiatra)"
    pessoa: andre
    frequencia: mensal
    periodo_inicio: "2023-01"
    periodo_fim: "2026-12"
    tracking_irpf: true

  - id: aluguel
    nome: "Aluguel (Ki-Sabor padaria)"
    pessoa: casal
    frequencia: mensal
    periodo_inicio: "2022-06"
    periodo_fim: "2026-12"
    extrator: null  # recibo manual
    tracking_irpf: true  # comprovante de moradia
```

### Fase 2 — Motor de cálculo

`src/analysis/docs_faltantes.py`:

```python
def gerar_inventario() -> pd.DataFrame:
    """Monta DataFrame com linha por (tipo, mes) dentro do período declarado."""
    regras = _load_yaml("mappings/docs_esperados.yaml")["tipos"]
    linhas = []
    for regra in regras:
        for mes in _meses_no_periodo(regra["periodo_inicio"], regra["periodo_fim"]):
            linhas.append({
                "tipo_id": regra["id"],
                "tipo_nome": regra["nome"],
                "pessoa": regra["pessoa"],
                "mes_ref": mes,
                "valor_esperado": _estimar_valor(regra, mes),  # média histórica
                "valor_observado": _buscar_no_xlsx(regra, mes),  # extrato
                "arquivo_inbox": _buscar_inbox(regra, mes),  # paths
                "documento_vinculado": _buscar_grafo(regra, mes),  # edge pago_com
                "status": _inferir_status(regra, mes),
                "observacao": "",
            })
        if regra.get("extras_anuais"):
            for ano in _anos_no_periodo(regra):
                for extra in regra["extras_anuais"]:
                    linhas.append({
                        "tipo_id": f"{regra['id']}_{extra}",
                        "tipo_nome": f"{regra['nome']} ({extra})",
                        ...
                    })
    return pd.DataFrame(linhas)

def _inferir_status(regra, mes):
    """Ordem: documento_vinculado -> disponivel | arquivo_inbox -> inbox | senão pendente."""
    # irrecuperavel fica manual, não inferido
```

### Fase 3 — Script de export

`scripts/gerar_xlsx_docs_faltantes.py`:

```python
def main():
    df = gerar_inventario()
    # Preservar coluna 'status' manual ('irrecuperavel') se XLSX já existe
    path = Path("data/output/docs_faltantes.xlsx")
    if path.exists():
        existente = pd.read_excel(path)
        df = _merge_preservando_manual(df, existente)
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, sheet_name="Consolidado", index=False)
        for tipo_id, grupo in df.groupby("tipo_id"):
            grupo.to_excel(writer, sheet_name=tipo_id[:30], index=False)
```

### Fase 4 — Merge preservando edição manual

```python
def _merge_preservando_manual(novo: pd.DataFrame, antigo: pd.DataFrame) -> pd.DataFrame:
    """Se linha antiga tem status='irrecuperavel' OU observacao preenchida, preserva."""
    chave = ["tipo_id", "mes_ref"]
    merged = novo.merge(antigo, on=chave, how="left", suffixes=("", "_antigo"))
    # Preservar status se antigo=='irrecuperavel' OU observacao não-vazia
    mask = (merged["status_antigo"] == "irrecuperavel") | (merged["observacao_antigo"].astype(str).str.strip() != "")
    merged.loc[mask, "status"] = merged.loc[mask, "status_antigo"]
    merged.loc[mask, "observacao"] = merged.loc[mask, "observacao_antigo"]
    return merged.drop(columns=[c for c in merged.columns if c.endswith("_antigo")])
```

### Fase 5 — Integração com Sprint 75 (Gap Analysis)

Aba Completude lê `docs_faltantes.xlsx` e:
- Exclui linhas `status='irrecuperavel'` do cálculo de pendências.
- Mostra contagem separada: "Irrecuperáveis: N documentos marcados conscientemente".
- Botão "Exportar XLSX docs faltantes" dispara `scripts/gerar_xlsx_docs_faltantes.py`.

## Armadilhas

| Ref | Armadilha | Como evitar |
|---|---|---|
| A85-1 | Andre edita status no XLSX, re-rodar sobrescreve | Merge preservando manual (Fase 4) |
| A85-2 | Regras em YAML crescem demais | Separar por pessoa em subdocs se > 30 tipos |
| A85-3 | Valor esperado incorreto (salário muda) | Estimar pela mediana dos últimos 6 meses observados |

## Evidências

- [ ] XLSX gerado com abas por tipo + consolidado
- [ ] Teste: editar status manualmente, re-rodar, status preservado
- [ ] Sprint 75 exclui irrecuperáveis corretamente

---

*"O que falta precisa ter nome antes de virar ação." — princípio"*
