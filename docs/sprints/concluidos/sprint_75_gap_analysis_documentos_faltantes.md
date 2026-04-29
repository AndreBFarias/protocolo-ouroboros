---
concluida_em: 2026-04-22
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 75
  title: "Gap Analysis: listar documentos faltantes mês a mês, categoria por categoria"
  touches:
    - path: src/analysis/gap_documental.py
      reason: "novo módulo: calcula completude por mês/categoria"
    - path: src/dashboard/paginas/completude.py
      reason: "nova aba 'Completude' no dashboard"
    - path: src/dashboard/app.py
      reason: "incluir aba nova no seletor"
    - path: tests/test_gap_documental.py
      reason: "testes de cobertura"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_gap_documental.py -v"
      timeout: 60
  acceptance_criteria:
    - "Nova aba 'Completude' no dashboard"
    - "Tabela: linhas = meses (YYYY-MM), colunas = categorias_tracking obrigatorias, células = X/Y comprovantes"
    - "Visão detalhada: clicar em célula X/Y abre lista de transações sem documento"
    - "Alerta inteligente: 'Você pagou R$ 800 em Ki-Sabor em 5 meses consecutivos - é aluguel? Registre o contrato em Contratos/aluguel.md'"
    - "Sugestão acionável: para cada transação órfã, botão 'Foto do comprovante' abre instrução para inbox"
    - "Export CSV: lista completa de transações sem doc"
  proof_of_work_esperado: |
    .venv/bin/python -c "
    from src.analysis.gap_documental import calcular_completude
    resumo = calcular_completude()
    print(f'meses cobertos: {len(resumo)}')
    for mes in list(resumo.keys())[:3]:
        print(f'  {mes}: {resumo[mes]}')
    "
    # screenshot da aba Completude
```

---

# Sprint 75 — Gap Analysis

**Status:** CONCLUÍDA (2026-04-22)
**Prioridade:** P1
**Dependências:** Sprint 74 (vínculo existe), ADR-20
**Issue:** UX-ANDRE-03

## Problema

Andre pediu: "preciso de uma sprint que vai listar cada documento de cada mês do que tiver faltando, cada coisinha minúscula". A visão é terapêutica: ver o vazio documental dispara ação (jogar recibo na inbox).

## Implementação

### Cálculo de completude

`src/analysis/gap_documental.py`:

```python
def calcular_completude(mes: Optional[str] = None) -> dict:
    """Retorna dict {mes: {categoria: {total, com_doc, sem_doc, transacoes_orfas}}}."""
    tracking = _load_yaml("mappings/categorias_tracking.yaml")["obrigatoria_tracking"]
    transacoes = _carregar_transacoes_com_vinculo()
    resumo = defaultdict(lambda: defaultdict(dict))
    for tx in transacoes:
        if tx["categoria"] not in tracking:
            continue
        mes_ref = tx["mes_ref"]
        cat = tx["categoria"]
        info = resumo[mes_ref].setdefault(cat, {"total": 0, "com_doc": 0, "sem_doc": 0, "orfas": []})
        info["total"] += 1
        if tx.get("tem_documento"):
            info["com_doc"] += 1
        else:
            info["sem_doc"] += 1
            info["orfas"].append(tx)
    return resumo
```

### Aba Completude

`src/dashboard/paginas/completude.py`:

```python
def renderizar():
    st.header("Completude Documental")
    resumo = calcular_completude()
    # Heatmap: rows=meses, cols=categorias, cor=% cobertura
    fig = _heatmap_completude(resumo)
    st.plotly_chart(fig, use_container_width=True)
    # Lista de alertas inteligentes
    for alerta in _alertas(resumo):
        st.warning(alerta)
    # Detalhe clicável
    mes_sel = st.selectbox("Mês", sorted(resumo.keys(), reverse=True))
    cat_sel = st.selectbox("Categoria", list(resumo[mes_sel].keys()))
    info = resumo[mes_sel][cat_sel]
    st.caption(f"{info['com_doc']} / {info['total']} comprovantes")
    st.table(pd.DataFrame(info["orfas"]))
```

### Alertas inteligentes

`_alertas()` gera regras tipo:

- "Você pagou R$ X em {fornecedor} em {N} meses consecutivos - é recorrência sem contrato?"
- "Categoria Farmácia tem 0 comprovantes em {ano} mas R$ X gastos - IRPF perde dedução"
- "Transação acima de R$ 500 sem comprovante em {mes} - revisar"

## Armadilhas

| A75-1 | Heatmap com muitos meses vira ilegível | Limitar a últimos 12 meses por default; slider para expandir |
| A75-2 | Alertas falso-positivo irritam | Threshold configurável via `mappings/alertas_gap.yaml` |

## Evidências

- [x] **Módulo `src/analysis/gap_documental.py`** (~190L): `calcular_completude(df, categorias_obrigatorias, ids_com_doc)`, `alertas(resumo, valor_alto, min_meses_recorrencia)`, `orfas_para_csv(resumo)`, `carregar_categorias_obrigatorias()` com lru_cache.
- [x] **Aba "Completude" no dashboard** (`src/dashboard/paginas/completude.py`): heatmap mês × categoria com cor proporcional a % cobertura, caixas de alertas inteligentes (recorrência, valor alto, zero-cobertura), selectbox para detalhe mês/categoria, botão export CSV.
- [x] **`app.py` registra a 12ª aba** "Completude" após "Grafo + Obsidian".
- [x] 3 heurísticas de alerta: (1) fornecedor sem doc em >= 3 meses do mesmo ano ≥ R$ 100 = "recorrência contratual?"; (2) transação individual >= R$ 500 sem doc = revisar; (3) categoria com 0 comprovantes em mês com >=2 transações = "IRPF pode perder dedução".
- [x] 10 testes em `tests/test_gap_documental.py`: filtro por categoria obrigatória, respeito a `tipo in (Despesa, Imposto)`, `ids_com_doc` marca cobertura, DF vazio / categorias vazias não quebram, alerta de valor alto, alerta zero-cobertura, CSV com colunas canônicas.
- [x] Gauntlet: `make lint` exit 0, 1021 passed (+10), smoke 8/8 OK.

### Ressalva

- [R75-1] **Cobertura real do grafo ainda é zero**: a Sprint 74 criou o motor de matching, mas nenhuma aresta `documento_de` foi populada em volume. Em produção, `ids_com_doc` fica quase vazio e tudo aparece como órfão. Esse é O SINAL que o André quer ver (terapêutico), mas quando a Sprint 48 rodar em volume real via `./run.sh --inbox`, a cobertura vai subir organicamente. Não é bloqueante; é característica da Fase KAPPA começar antes da ingestão em massa.

---

*"O que não é medido escapa." — Peter Drucker*
