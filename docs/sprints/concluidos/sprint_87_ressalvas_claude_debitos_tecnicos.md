## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 87
  title: "Ressalvas técnicas IOTA/KAPPA: itens que Claude pode resolver sem mão humana"
  touches:
    - path: src/dashboard/paginas/visao_geral.py
      reason: "aplicar aplicar_drilldown no gráfico Receita vs Despesa"
    - path: src/dashboard/paginas/categorias.py
      reason: "aplicar aplicar_drilldown no Top 10 Categorias"
    - path: src/dashboard/paginas/grafo_obsidian.py
      reason: "aplicar aplicar_drilldown nos bar charts Top Fornecedores"
    - path: src/dashboard/paginas/extrato.py
      reason: "coluna 'Doc?' consultar grafo (arestas documento_de) em vez de só categoria"
    - path: src/extractors/boleto_pdf.py
      reason: "novo: extrator de boleto PDF gerando node documento no grafo"
    - path: src/pipeline.py
      reason: "passo novo para preencher metadata.arquivo_original nos nodes existentes"
    - path: src/obsidian/sync_rico.py
      reason: "gerar MOC mensal em Pessoal/Casal/Financeiro/Meses/"
    - path: mappings/tipos_documento.yaml
      reason: "regras para parcelas IRPF/DAS/comprovantes que hoje caem skip_nao_identificado"
    - path: src/analysis/pagamentos.py
      reason: "reconciliação boleto↔transação via grafo quando arestas documento_de existem"
    - path: src/dashboard/tema.py
      reason: "aplicar legenda_abaixo nos 4 plots principais (visao_geral, projecoes, analise_avancada)"
    - path: tests/test_drilldown_paginas_extras.py
      reason: "validar aplicar_drilldown em 3 plots novos"
    - path: tests/test_boleto_pdf.py
      reason: "validar extrator de boleto"
    - path: tests/test_gap_consultando_grafo.py
      reason: "validar reconciliação via edges"
  n_to_n_pairs:
    - ["customdata dos plots adicionais", "filtros lidos em extrato._aplicar_drilldown"]
    - ["tipos absorvidos em inbox_routing.yaml", "regex em tipos_documento.yaml"]
  forbidden:
    - "Introduzir dependência nova que exija bibliotecas de sistema (bzip2 etc.)"
    - "Sobrescrever notas do vault com sincronizado: true=false"
    - "Rodar ingestão em volume real (Sprint 86 item 86.12 é responsabilidade do André)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/ -q"
      timeout: 180
    - cmd: ".venv/bin/python scripts/smoke_aritmetico.py --strict"
      timeout: 60
  acceptance_criteria:
    - "Drill-down ativo em pelo menos 4 gráficos: treemap Categorias (já feito Sprint 73), Receita vs Despesa, Top 10 Categorias, Top Fornecedores"
    - "Extrator de boleto PDF produz node documento no grafo com metadata.arquivo_original preenchido (permite GTC-01 end-to-end)"
    - "Coluna 'Doc?' do Extrato mostra 'OK' (verde) quando transação tem aresta documento_de no grafo; '!' (amarelo) quando categoria obrigatória sem aresta; vazio caso contrário"
    - "Pipeline passo novo que, em modo --backfill-metadata, percorre nodes tipo=documento existentes e preenche arquivo_original quando ausente (best-effort via data/raw/)"
    - "mappings/tipos_documento.yaml ganha regras para: ExibirDAS (parcelamento MEI), ANDRE DA SILVA BATISTA (histórico Serasa/Registrato), comprovantes CPF — reduzindo skip_nao_identificado do adapter Sprint 70"
    - "Sync rico gera Meses/YYYY-MM.md MOC mensal com Dataview listando documentos do mês"
    - "src/analysis/pagamentos.py::carregar_boletos usa arestas documento_de como fonte primária quando o grafo tem >= 10 arestas desse tipo; fallback para heurística textual"
    - "Helper legenda_abaixo(fig) aplicado em 4 plots: Receita vs Despesa (visao_geral), projeções (projecoes), heatmap e sankey (analise_avancada)"
    - "Zero regressão: baseline de testes mantido ou cresce"
    - "Nenhum acceptance exige ambiente pyvis funcional (Sprint 86 item 86.1 fica fora)"
  proof_of_work_esperado: |
    # 1. Drill-down em 4 gráficos
    grep -l "aplicar_drilldown" src/dashboard/paginas/*.py | wc -l  # >=4
    # 2. Extrator de boleto
    .venv/bin/pytest tests/test_boleto_pdf.py -v
    # 3. Coluna Doc? consulta grafo
    .venv/bin/pytest tests/test_gap_consultando_grafo.py -v
    # 4. Gauntlet
    make lint && .venv/bin/pytest tests/ -q && make smoke
```

---

# Sprint 87 — Ressalvas técnicas IOTA/KAPPA (Claude)

**Status:** BACKLOG
**Prioridade:** P2 (polish, não bloqueia uso diário — acessar dashboard e inbox já está funcional)
**Dependências:** Sprints 72, 73, 74, 75, 76, 77, 78, 79, 80 (todas do caminho crítico)
**Relação:** complementa Sprint 86 (checklist humano); as duas juntas fecham o ciclo IOTA/KAPPA
**Issue:** RESSALVA-IOTA-KAPPA-CLAUDE

## Problema

Durante a execução do caminho crítico IOTA + KAPPA em 2026-04-22, Claude
consolidou 14 sprints em sequência e acumulou 20 ressalvas formais. Parte
dessas ressalvas não exige decisão humana — são débito técnico que pode
ser resolvido autonomamente, sem pedir aprovação nova. Esta sprint agrupa
esses itens num único escopo coeso.

A Sprint 86 (companheira) lista as ressalvas que exigem mão humana
(instalar libbz2-dev, validar visualmente o dashboard, aprovar decisões
arquiteturais, popular dados em volume real).

## Escopo detalhado (9 itens)

### 87.1 — Drill-down em 3 gráficos adicionais (R73-1)

Hoje apenas o treemap "Gastos por Categoria" usa `aplicar_drilldown`. O
spec da Sprint 73 pedia 4 gráficos. Os 3 faltantes têm plots estáveis e
custo de aplicação é baixo (6 linhas por gráfico):

1. **Receita vs Despesa** em `src/dashboard/paginas/visao_geral.py`
   - Plot de bar agrupado por `mes_ref`
   - `fig.update_traces(customdata=df["mes_ref"])`
   - `aplicar_drilldown(fig, "mes_ref", "Extrato", key_grafico="bar_receita_despesa")`

2. **Top 10 Categorias** em `src/dashboard/paginas/categorias.py`
   - `fig.update_traces(customdata=agrupado["categoria"])`
   - `aplicar_drilldown(fig, "categoria", "Extrato", key_grafico="top10_categorias")`

3. **Top Fornecedores** em `src/dashboard/paginas/grafo_obsidian.py::_bar_chart`
   - `customdata=df["fornecedor"]`
   - `aplicar_drilldown(fig, "fornecedor", "Extrato", key_grafico="top_fornecedores")`

### 87.2 — Coluna "Doc?" do Extrato consultar o grafo (R74-3)

Hoje a coluna marca `!` quando a categoria está em `categorias_tracking`.
Ampliar para:

- Se existe aresta `documento_de` apontando para a transação no grafo: `OK` (verde)
- Se categoria obrigatória e sem aresta: `!` (amarelo)
- Senão: vazio

Implementação: carregar set `ids_com_doc` (transações com >=1 aresta
`documento_de`) uma vez por render via `lru_cache` curto. Helper em
`src/graph/queries.py` ou nova função `transacoes_com_documento()`.

A Sprint 75 já tem infra similar em `calcular_completude(ids_com_doc=...)`;
extrair para módulo comum.

### 87.3 — Extrator de boleto PDF (R74-1, R70-3)

**Crítico para GTC-01 end-to-end funcionar.** Hoje `inbox/natacao_andre.pdf`
foi detectado como `boleto_servico` pela cascata do YAML, mas não existe
extrator que leia o PDF e crie node `documento` no grafo.

Criar `src/extractors/boleto_pdf.py`:

- Entrada: Path de PDF; senha via `mappings/senhas.yaml` se necessário
- Extrair via `pdfplumber`: linha digitável, valor, vencimento, pagador, emissor, CNPJ quando existe
- Montar dict `{tipo_documento: "boleto_servico", data_emissao, total, fornecedor, cnpj_emissor, arquivo_original}`
- Registrar no grafo via `ingerir_documento_fiscal` ou adapter equivalente
- Registrar no passo 14 do `pipeline.py` (após extratores documentais existentes)

Acceptance: após rodar `scripts/reprocessar_documentos.py` com `inbox/natacao_andre.pdf` em `data/raw/casal/boletos/`, há 2 novos nodes `documento` no grafo com `metadata.tipo_documento="boleto_servico"` e `metadata.arquivo_original` preenchido com path absoluto.

### 87.4 — Regras YAML para tipos documentais faltantes (R70-3)

Hoje 25 PDFs do inbox legado (`parcelas IRPF`, `ANDRE DA SILVA BATISTA`,
`Comprovante de Situação Cadastral CPF`, `ExibirDAS`) caem em
`skip_nao_identificado` do adapter da Sprint 70.

Adicionar em `mappings/tipos_documento.yaml`:

- **das_mei** — arquivos `ExibirDAS-*.pdf` (DAS Simples Nacional MEI)
  - `regex_nome`: `^ExibirDAS`
  - `regex_conteudo`: `DAS - Documento de Arrecadação`
  - `pasta_destino_template`: `data/raw/{pessoa}/impostos/das/`

- **comprovante_cpf** — `Comprovante de Situação Cadastral no CPF.pdf`
  - `regex_conteudo`: `Situação\\s+Cadastral\\s+no\\s+CPF`
  - `pasta_destino_template`: `data/raw/{pessoa}/documentos_pessoais/`

- **irpf_parcela** — `Nª PARCELA.pdf`, `Nª (2ªvia) parcela.pdf`
  - `regex_nome`: `\\d{1,2}[ªa]\\s*(VIA\\s*)?PARCELA`
  - `regex_conteudo`: `DARF|Receita\\s+Federal`
  - `pasta_destino_template`: `data/raw/{pessoa}/impostos/irpf_parcelas/`

Adicionar correspondentes em `mappings/inbox_routing.yaml::tipos_absorvidos`.

### 87.5 — Backfill de metadata.arquivo_original nos nodes antigos (R71-1)

Nodes `documento` no grafo podem ter `arquivo_original` ausente (quando
ingeridos por extratores antigos que não preenchiam). Isso faz o sync rico
da Sprint 71 gerar wikilink apontando para arquivo inexistente em
`_Attachments/`.

Adicionar passo `--backfill-metadata` no `src/pipeline.py`:

- Percorre `db.listar_nodes(tipo="documento")`
- Para cada node sem `arquivo_original`, tenta localizar em `data/raw/` via sha256 registrado (se houver) ou por nome canônico
- Atualiza metadata com path absoluto quando encontra

### 87.6 — MOC mensal no vault (R71-2)

Sprint 71 criou `Documentos/YYYY-MM/` e `Fornecedores/` mas não gerou
`Meses/YYYY-MM.md` (MOC mensal). Hoje existe versão antiga em
`Pessoal/Financeiro/Relatorios/` do `src/obsidian/sync.py`.

Adicionar função `_render_moc_mensal(mes_ref, db)` em `sync_rico.py`:

- Lê nodes `documento` do mês
- Gera markdown com Dataview que lista docs, fornecedores únicos, total
- Escreve em `Pessoal/Casal/Financeiro/Meses/YYYY-MM.md`
- Respeita soberania humana (tag `#sincronizado-automaticamente`)

### 87.7 — Reconciliação boleto↔transação via grafo (R79-1)

`src/analysis/pagamentos.py::carregar_boletos` usa hoje substring textual
para reconciliar boleto esperado (aba `prazos`) com pago (extrato). Quando
o grafo tem arestas `documento_de`, a reconciliação fica mais precisa:

- Para cada boleto_servico em `listar_nodes(tipo="documento")` com `tipo_documento="boleto_servico"`:
  - Se tem aresta `documento_de` apontando para transação X → status=`pago`
  - Se não tem → status depende de `vencimento` vs hoje

Fallback para a heurística textual quando o grafo tem < 10 arestas
`documento_de` (estado atual da Sprint 87 pré-87.3). Threshold define
quando confiar no grafo como fonte primária.

### 87.8 — Aplicar `legenda_abaixo` em 4 plots (R77-1)

Token está publicado em `src/dashboard/tema.py::legenda_abaixo`. Aplicar
em:

- `src/dashboard/paginas/visao_geral.py` — plots com legendas horizontais
- `src/dashboard/paginas/projecoes.py` — gráfico de cenários
- `src/dashboard/paginas/analise_avancada.py` — sankey e heatmap

Cada aplicação é 1 linha: `tema.legenda_abaixo(fig)` antes do `st.plotly_chart`.

### 87.9 — Testes novos (cobertura das mudanças acima)

- `tests/test_drilldown_paginas_extras.py`: 3 testes que validam customdata setado nos gráficos modificados em 87.1
- `tests/test_boleto_pdf.py`: 5+ testes do extrator (linha digitável, valor, vencimento, pagador, cnpj)
- `tests/test_gap_consultando_grafo.py`: 3 testes que simulam grafo com arestas `documento_de` e confirmam que a coluna Doc? e os alertas mudam

## Armadilhas conhecidas

| Ref | Armadilha | Mitigação |
|---|---|---|
| A87-1 | Aplicar drilldown em mais plots pode conflitar com outros widgets que usam session_state | Usar `key_grafico` únicos e testar com fixture |
| A87-2 | Extrator de boleto precisa lidar com PDFs scaneados (OCR fallback) | Se `pdfplumber.extract_text` retorna <20 chars, tenta OCR tesseract; se falhar, marca como `nao_identificado` |
| A87-3 | Regra YAML para IRPF parcela pode colidir com `boleto_servico` genérico (ambas têm linha digitável) | Ordem das regras no YAML importa; específicas antes de genéricas |
| A87-4 | Backfill de metadata pode demorar em grafo grande | Rodar como passo explícito `--backfill-metadata`, não automático no pipeline regular |
| A87-5 | MOC mensal regenera toda execução — poluição git em `docs/` se o vault for versionado | MOC escreve apenas se `_conteudo_mudou`, como as outras notas do sync_rico |

## Ordem de execução sugerida

1. **87.4** (regras YAML) — rápido, reduz ruído antes de 87.3
2. **87.3** (extrator de boleto) — desbloqueia GTC-01 end-to-end
3. **87.5** (backfill metadata) — completa o contrato de arquivo_original
4. **87.2** (coluna Doc? consulta grafo) — usa as arestas criadas em 87.3
5. **87.7** (reconciliação via grafo) — mesma ideia
6. **87.1** (drilldown em 3 plots) — UX polish, rápido
7. **87.8** (legenda_abaixo) — UX polish, trivial
8. **87.6** (MOC mensal) — feature menos crítica, por último
9. **87.9** (testes) — em paralelo a cada item acima

## Evidências obrigatórias

- [ ] 4 ou mais grafos com `aplicar_drilldown` (grep confirmando)
- [ ] Extrator de boleto com >=5 testes, GTC-01 end-to-end passando
- [ ] Regras YAML reduzem skip_nao_identificado de 25 para < 10 no inbox legado do André
- [ ] Backfill de metadata recupera `arquivo_original` em >=80% dos nodes pre-existentes
- [ ] MOC mensal aparece em `Pessoal/Casal/Financeiro/Meses/{mes}.md` com Dataview funcional
- [ ] Reconciliação via grafo tem fallback e threshold configurável
- [ ] 4 plots aplicam `legenda_abaixo`
- [ ] Gauntlet verde: make lint exit 0, pytest >= 1046 passed, smoke 8/8 OK

---

*"O que sobrou é débito técnico — mas é débito bem catalogado." — princípio pós-Sprint 79*
