# Auditoria honesta da reforma de UI -- branch `ux/redesign-v1`

> **Data**: 2026-05-05  
> **Auditor**: Opus 4.7 (1M context), sessão Claude Code interativa, independente.  
> **Plano**: `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md`  
> **Modo**: somente leitura + execução de smoke/pytest/runtime + capturas no navegador.  
> **Não confiei** em commit messages, em proof-of-work declarado pelos executores, nem nos 25 PNGs em `docs/auditorias/redesign/UX-RD-*.png`. Recapturei tudo.

---

## Resumo executivo

| Indicador | Score |
|---|---|
| **Fidelidade média ao mockup** (29 telas, 4 dimensões cada) | **57/100** |
| **Saúde funcional pós-redesign** | **78/100** |

**Top 5 problemas (gravidade decrescente)**:

1. **5 telas Bem-estar (Rotina, Memórias, Cruzamentos, Privacidade, Editor TOML) NÃO têm aba na navegação** -- `app.py:132-145` declara apenas 12 abas (Hoje, Humor, Diário, Eventos, Medidas, Treinos, Marcos, Alarmes, Contadores, Ciclo, Tarefas, Recap). Páginas existem em código mas inacessíveis por deep-link `?cluster=Bem-estar&tab=<X>`. **Correção**: adicionar Rotina/Memórias/Cruzamentos/Privacidade/Editor TOML em `ABAS_POR_CLUSTER["Bem-estar"]`.
2. **5 abas Bem-estar mostram conteúdo de outras 2 páginas** -- `app.py:625-637` faz Treinos+Marcos -> `be_memorias` e Alarmes+Contadores+Tarefas -> `be_rotina`. Comentário do código admite: "preservar o invariante N=12 abas". É fraude de UI. **Correção**: ou criar páginas reais (be_treinos, be_marcos, be_alarmes, be_contadores, be_tarefas), ou remover as abas-fantasma.
3. **Tela Extrato: bug grave de agregação** -- `paginas/extrato.py` mostra Receita R$ 16.477,62 e Despesa R$ 0,00 para abril/2026. Backend tem 78 transações no mês com despesas reais R$ 3.391,77. Receita+Despesa+Imposto somam R$ 16.477,62 -- provável bug de filtro por `tipo`. **Correção**: revisar filtro de `tipo == "Despesa"` em `paginas/extrato.py`.
4. **make lint quebrado (exit 1)** -- 11 erros de acentuação em `.md` (8 em `novo-mockup/`, 3 em `docs/sprints/`). A própria branch deixou o lint vermelho. **Correção**: corrigir os 11 .md ou normalizar `scripts/check_acentuacao.py` para excluir `novo-mockup/`.
5. **60 .py novos sem citação filosófica final** -- violação massiva da regra 10 do CLAUDE.md em **39 arquivos de src/** + 21 em scripts/tests. Padrão antigo do projeto: `# "Frase." -- Autor`. Padrão da branch: nada. **Correção**: sprint corretiva adicionando citação em todos os arquivos novos.

---

## 1. Diff visual real vs mockup (29 telas)

Setup: dashboard rodando em `127.0.0.1:8765` via `streamlit run src/dashboard/app.py`; mockups em `127.0.0.1:8766/mockups/*.html` via `python -m http.server`. Captura headless playwright em viewport 1440x900. PNGs em `.playwright-mcp/auditoria/{mockups,dashboard}/`.

### Tabela das 29 telas

> **% fidelidade** = média ponderada de Estrutura (25%), Tipografia (25%), Paleta (25%), Conteúdo (25%).

| # | Mockup | Cluster/Tab | Estr | Tipo | Pal | Cont | **%** | Achado principal |
|---|---|---|--:|--:|--:|--:|--:|---|
| 00 | shell-navegacao | (chrome global) | 80 | 90 | 95 | 60 | **81** | sidebar tem 8 clusters mas falta breadcrumb-ações do mockup |
| 01 | visao-geral | Home/Visão Geral | 50 | 80 | 90 | 30 | **62** | KPIs financeiros (RECEITA/DESPESA/SALDO/RESERVA) em vez de agentic-first do mockup (VALIDAÇÃO 4-WAY/COBERTURA/FALTA HUMANO/ALERTAS); bloco "16 clusters" do mockup ausente |
| 02 | extrato | Finanças/Extrato | 70 | 85 | 90 | 30 | **69** | **Despesa R$ 0,00 em abril (real R$ 3.391,77) -- bug**; botões "Importar OFX"/"Exportar" ausentes; "Sem despesas no período" engana |
| 03 | contas | Finanças/Contas | 80 | 85 | 90 | 80 | **84** | OK, 4 contas (Itaú/Santander/Nubank/C6) + 1 cartão; cores D7 funcionando |
| 04 | pagamentos | Finanças/Pagamentos | 75 | 85 | 90 | 70 | **80** | calendário 14 dias funcional; "Vencimentos detalhados" lateral OK; falta legenda categorias no calendário |
| 05 | projecoes | Finanças/Projeções | 75 | 85 | 90 | 75 | **81** | 3 cenários, gráfico linhas, KPIs + Marcos; aporte mensal mostra R$ 0,00 (deveria extrair do extrato) |
| 06 | busca-global | Documentos/Busca Global | 70 | 80 | 90 | 65 | **76** | **Cabeçalho duplicado**: "Busca Global" (h1 redesign) + "BUSCA GLOBAL" (h1 antigo); chips canônicos OK |
| 07 | catalogacao | Documentos/Catalogação | 70 | 80 | 90 | 70 | **77** | **Cabeçalho duplicado** (idem 06); 4 KPIs OK; 48 arquivos catalogados |
| 08 | completude | Documentos/Completude | 75 | 80 | 90 | 65 | **77** | matriz tipo x mês funcional, "COBERTURA 0%" alerta; toggle ">=2 transações" presente; 852 lacunas reportadas |
| 09 | revisor | Documentos/Revisor | 50 | 80 | 90 | 40 | **65** | **título promete 4-way, painel real é só ETL x Opus (2-way)**; lista densa de transações ausente; atalhos j/k/a/r não testáveis no estático |
| 10 | validacao-arquivos | Documentos/Extração Tripla | 70 | 80 | 85 | 70 | **76** | layout 3-col (lista/viewer/tabela) presente; viewer central renderizou vazio; 30 campos extraídos / 0 aprovados humano / 0 divergências |
| 11 | categorias | Análise/Categorias | 80 | 85 | 90 | 85 | **85** | árvore + treemap + KPIs (cobertura 93%); 4 não-classificadas; bem implementado |
| 12 | analise | Análise/Análise | 80 | 80 | 90 | 80 | **83** | Sankey, 4 KPIs, 3 sub-tabs (Fluxo/Comparativo/Padrões); bom |
| 13 | metas | Metas/Metas | 75 | 80 | 90 | 80 | **81** | 3 metas + donuts (Reserva 100%, Quitar Nubank PF/PJ 0%); falta seção "metas operacionais" |
| 14 | skills-d7 | Sistema/Skills D7 | 30 | 80 | 90 | 10 | **53** | **empty state "COBERTURA D7 AINDA NÃO INICIALIZADA"** -- nenhuma skill renderizada; honesto mas tela quase vazia |
| 15 | irpf | Análise/IRPF | 75 | 80 | 90 | 75 | **80** | compilação automática funcional; 4/8 categorias com dados; pacote IRPF 2026 lateral OK; falta lista 21 eventos do mockup |
| 16 | inbox | Inbox/Inbox | 70 | 80 | 90 | 25 | **66** | dropzone OK; **badge "EM CALIBRAÇÃO"** + todos KPIs em 0; lista de arquivos vazia (data/raw vazio) |
| 17 | bem-estar-hoje | Bem-estar/Hoje | 60 | 80 | 90 | 30 | **65** | 4 sliders (Humor/Ansiedade/Energia/Foco); cards "Sem diário/eventos/medidas hoje"; mockup tem layout muito mais rico (chips agenda, multi-tag, frase do dia, mosaico decisivo) |
| 18 | humor-heatmap | Bem-estar/Humor | 60 | 80 | 90 | 35 | **66** | heatmap 13x7 + toggle A/B/Sobreposto + 4 KPIs; **falta bloco "Distribuição de Tags" + painel "Detalhe do dia"**; vault tem 1 célula real |
| 19 | diario-emocional | Bem-estar/Diário | 70 | 80 | 90 | 50 | **73** | 1 registro real renderizado (alegria, gratidão); filtros laterais OK; mockup tem timeline rica + cards expansíveis |
| 20 | rotina | Bem-estar/Rotina | 0 | 0 | 0 | 0 | **0** | **deep-link `?tab=Rotina` cai em Hoje** -- aba não declarada em ABAS_POR_CLUSTER (`app.py:132-145`); página `be_rotina.py` existe mas inacessível direto |
| 21 | recap | Bem-estar/Recap | 75 | 80 | 90 | 60 | **76** | 4 KPIs (humor médio, eventos, treinos, peso) + comparativo de humor + bairros frequentes; bom |
| 22 | eventos | Bem-estar/Eventos | 70 | 80 | 90 | 50 | **73** | timeline 1 evento real (rolezinho 2026-04-29 padaria do bairro); filtros + bairros frequentes laterais; mockup tem calendário + heatmap intensidade |
| 23 | memorias | Bem-estar/Memórias | 0 | 0 | 0 | 0 | **0** | **deep-link `?tab=Memórias` cai em Hoje** -- idem 20; `be_memorias.py` é renderizado em Treinos+Marcos mas não em "Memórias" |
| 24 | medidas | Bem-estar/Medidas | 30 | 80 | 90 | 0 | **50** | **só empty state**: "Nenhuma medida registrada ainda. Crie arquivos em `<vault>/medidas/<pessoa>/<data>.md`"; mockup tem comparativo última vs primeira + gráficos de evolução |
| 25 | ciclo | Bem-estar/Ciclo | 30 | 80 | 90 | 0 | **50** | **só empty state**: "Nenhum registro de ciclo encontrado..."; mockup tem track de fluxo + fase + sintomas |
| 26 | cruzamentos | Bem-estar/Cruzamentos | 0 | 0 | 0 | 0 | **0** | **deep-link cai em Hoje**; `be_cruzamentos.py` existe mas só dentro de expander Recap (`app.py:639`) |
| 27 | privacidade | Bem-estar/Privacidade | 0 | 0 | 0 | 0 | **0** | idem 26; mockup é matriz A<->B granular complexa; nada acessível direto |
| 28 | rotina-toml | Bem-estar/Editor TOML | 0 | 0 | 0 | 0 | **0** | idem 26; expander dentro de Recap |

**Média geral das 29 telas**: 1.667/29 = **57,5/100**.

### Estatísticas

- **Telas com 80+ fidelidade** (boas): 7 (00, 03, 04, 05, 11, 12, 13).
- **Telas com 60-79 fidelidade** (parciais): 13.
- **Telas com 50-59** (empty state ou bug grave): 3 (14, 24, 25).
- **Telas com 0**: 5 (20, 23, 26, 27, 28) -- todas Bem-estar inacessíveis por deep-link.

---

## 2. Regressão funcional

### 2.1 Bateria runtime (logs em `/tmp/auditoria_redesign/logs/`)

| Comando | Exit | Resultado |
|---|---|---|
| `make lint` | **1 (FAIL)** | ruff OK; **acentuação: 11 erros em .md** (`docs/sprints/backlog/sprint_micro_01a*.md`, `docs/sprints/concluidos/sprint_garantia_expirando_01*.md`, `novo-mockup/README.md`, `novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md`). |
| `make smoke` | **0 (PASS)** | 23 checagens, 0 erros, 0 avisos. **10/10 contratos OK**. XLSX `data/output/ouroboros_2026.xlsx` (460 KB, 1 mai 22:18). |
| `pytest tests/ -q` | **0 (PASS)** | **2520 passed, 9 skipped, 1 xfailed** em 58.62s. |

> **Nota**: durante o setup tentei abrir `data/output/extrato_consolidado.xlsx` -- não existe. O XLSX real chama `ouroboros_2026.xlsx` (nome divergente do CLAUDE.md, que usa `extrato_consolidado.xlsx` em vários lugares). Pequena divergência documental.

### 2.2 Features pré-redesign -- testes manuais via deep-link

Capturas em `.playwright-mcp/auditoria/dashboard/`:

| Feature | Resultado | Evidência |
|---|---|---|
| Drill-down `?cluster=Análise&tab=Categorias` | **PASS** | breadcrumb "Ouroboros / Análise / Categorias", tab "Categorias" ativa, h1 "CATEGORIAS" |
| Drill-down `?cluster=Documentos&tab=Revisor` | **PASS** | breadcrumb correto, tab "Revisor" ativa, h1 "REVISOR" + badge "26 PENDÊNCIAS / FIDELIDADE 0%" |
| Drill-down `?cluster=Inbox&tab=Inbox` | **PASS** | "INBOX" + dropzone + KPIs |
| Drill-down `?cluster=Finanças&tab=Extrato` | **PASS** | breadcrumb + KPIs + tabela |
| Deep-link Bem-estar Privacidade/Cruzamentos/Rotina/Memórias/Editor TOML | **FAIL** | renderiza Hoje (default), não declarada em `ABAS_POR_CLUSTER` |
| Autocomplete Busca Global | **não testei** (Streamlit headless dificulta digitação interativa) |
| Revisor 4-way | **PARCIAL** | UI mostra ETL x Opus apenas (2-way); título do bloco diz "COMPARAÇÃO ETL x OPUS"; texto descritivo promete 4-way (`paginas/revisor.py`) |
| Contagem documentos | **PASS** | Catalogação mostra 48 catalogados, bate com `data/output/grafo.sqlite` |
| `st.download_button` (Pacote IRPF) | **não testei** click (precisa interação real) |

### 2.3 Pipeline ETL ponta-a-ponta

**Não rodei** `./run.sh --tudo` para preservar `data/output/`. Validei estado atual:

- `data/output/ouroboros_2026.xlsx` (460 KB, modificado 89.4h atrás): **8 abas íntegras** -- `extrato`, `renda`, `dividas_ativas`, `inventario`, `prazos`, `resumo_mensal`, `irpf`, `analise`.
- `data/output/grafo.sqlite` (5.4 MB): tabelas `node` e `edge` presentes.
- `extrato`: 6094 linhas, **4760 despesas (R$ 546.738,70)** + **482 receitas (R$ 608.809,31)** + transferências.
- abril/2026: **78 transações, R$ 11.622,50 receitas, R$ 3.391,77 despesas**.
- `make smoke` declarou 82 relatórios mensais .md gerados. Sem rodar `--tudo`.

---

## 3. Honestidade do código

### 3.1 TODO/FIXME/HACK em `src/`

```
src/dashboard/app.py:563:        # placeholder até esta sprint.
```

**1 ocorrência**, contextualizada no comentário.

### 3.2 Fallback que esconde feature não implementada

| Local | Comportamento | Severidade |
|---|---|---|
| `app.py:402-415` `_renderizar_fallback_cluster()` | mostra "Cluster X reservado pelo redesign mas as páginas ainda não foram implementadas" -- honesto | OK |
| `paginas/skills_d7.py` (UX-RD-05) | tela inteira é empty state "COBERTURA D7 AINDA NÃO INICIALIZADA" -- honesto | OK |
| `paginas/be_medidas.py` | só empty state "Nenhuma medida registrada ainda. Crie arquivos em `<vault>/medidas/<pessoa>/<data>.md`" -- funcional sem dado | OK |
| `paginas/be_ciclo.py` | só empty state "Nenhum registro de ciclo encontrado..." -- funcional | OK |
| `app.py:625-637` Treinos+Marcos -> `be_memorias`, Alarmes+Contadores+Tarefas -> `be_rotina` | **5 abas-fantasma duplicando 2 páginas** -- fraude de UI | **CRÍTICO** |
| `app.py:639-643` Cruzamentos/Privacidade/Editor TOML em expanders dentro de Recap | **3 mockups inteiros virados expander oculto**, deep-link não funciona | **CRÍTICO** |

### 3.3 Dados mockados/sintéticos como reais

`grep` em `src/dashboard/` por `mock|fake|dummy|lorem`: zero dado fabricado em runtime. Todas as ocorrências são **referências a arquivos de mockup HTML** ou comentários sobre testes -- é convenção da branch (declara explicitamente origem do design).

### 3.4 Hex hardcoded fora de tema

11 ocorrências em src/dashboard/, **todas como fallback defensivo** `var(--token, #cor)` ou em comentários documentais (paleta WCAG-AA validada). Zero hex puramente hardcoded em runtime.

### 3.5 Citação filosófica final (CLAUDE.md regra 10)

**Padrão antigo** (verificado em `src/pipeline.py`, `src/inbox_processor.py`, `src/utils/logger.py`, `src/extractors/itau_pdf.py`, `src/transform/categorizer.py`): `# "Frase." -- Autor`.

**Padrão da branch**: ausente.

| Categoria | Total | Sem citação | % |
|---|--:|--:|--:|
| `.py` novos em src/ | 39 | 39 | **100%** |
| `.py` novos em scripts/ | 2 | 2 | 100% |
| `.py` novos em tests/ | 19 | 19 | 100% |
| **Total** | **60** | **60** | **100%** |

**Violação massiva.** Regra 10 do CLAUDE.md ("Citação de filósofo como comentário final de todo arquivo .py novo") está sendo ignorada. Achado colateral -> **deve virar sprint UX-RD-CIT-01**.

### 3.6 Arquivos >=800 linhas (CLAUDE.md "Limite de 800 linhas")

| Arquivo | Linhas | Origem |
|---|--:|---|
| `src/dashboard/tema_css.py` | 1320 | NOVO (UX-RD-02) -- gerador CSS, justificável |
| `src/dashboard/paginas/busca.py` | 1220 | MODIFICADO -- UX-RD-09 |
| `src/dashboard/paginas/extrato.py` | 1069 | MODIFICADO -- UX-RD-06 |
| `src/dashboard/paginas/categorias.py` | 809 | NOVO -- UX-RD-12 (paleta WCAG inline) |
| `src/dashboard/paginas/contas.py` | 800 | MODIFICADO -- UX-RD-07 (no limite) |

**5 arquivos** acima do limite. Todos em `src/dashboard/`, todos em escopo do redesign. Decomposição em helpers é viável em pelo menos 3 (`busca`, `extrato`, `categorias`). Achado colateral -> **sprint UX-RD-DECOMP-01**.

---

## 4. Coerência arquitetural

| Invariante | Status | Evidência |
|---|---|---|
| **ADR-13** (sem cliente Anthropic API programático) | **OK** | `grep -rE '(from\|import)\s+anthropic\|Anthropic\(' src/ scripts/ tests/` retorna zero |
| **Schema XLSX** (8 abas) | **OK** | `extrato`, `renda`, `dividas_ativas`, `inventario`, `prazos`, `resumo_mensal`, `irpf`, `analise` íntegras |
| **Schema grafo SQLite** (ADR-14) | **OK** | tabelas `node`, `edge`, `sqlite_sequence` |
| **ADR-24** (`pessoa_a`/`pessoa_b`/`casal`) | **OK** | 65 ocorrências em `src/intake/`, `src/transform/`, `src/dashboard/`. Padrão preservado |
| **22 extratores** (CLAUDE.md) | **OK** | `ls src/extractors/*.py` (excl. `__init__.py`) = **22 arquivos** |
| **Vault graceful** (Bem-estar) | **OK** | `varrer_vault.py:63-77` -- env `OUROBOROS_VAULT` -> candidatos canônicos -> `None` + warning sem crash |

**Achado adicional**: `src/extractors/__init__.py` exporta apenas 8 (`ExtratorBase` + 7 bancários). Os outros 14 extratores (boleto, contracheque, danfe, das_parcsn, dirpf, energia_ocr, garantia, nfce, ofx, receita_medica, recibo_nao_fiscal, xml_nfe, etc.) **não estão em `__all__`**. Existem como arquivos mas o registry pythônico está incompleto. Não é regressão da branch (pré-existente provavelmente), mas merece registro.

---

## 5. Dívida que o dono não viu

### 5.1 Achados colaterais não formalizados

`grep -rniE 'achado colateral|sub-?sprint|sprint-filha|todo depois|criar (uma )?sprint' docs/sprints/concluidos/sprint_ux_rd_*.md` -> **zero matches**.

19 sprints consecutivas sem **nenhum** achado colateral declarado é estatisticamente improvável. Sinais:

- 39 arquivos sem citação filosófica -> ninguém viu (ou ninguém disse)?
- 5 arquivos >800 linhas -> mesmo
- Discrepância "12 abas declaradas vs 12 páginas reais entregues" -> resolvida com 5 abas-fantasma sem documento de decisão arquitetural
- Bug Despesa R$ 0,00 no Extrato -> não detectado

**Hipótese**: o ciclo executor -> validador automático aprovou cada sprint individualmente sem verificar contratos cross-sprint. Validador humano (o dono) viu screenshots, não código nem deep-link.

### 5.2 Testes que assertam estrutura, não comportamento

Antipadrão presente nos novos testes:

```
tests/test_busca_catalogacao_redesign.py:42  assert hasattr(pag_busca, "_renderizar_facetas_laterais")
tests/test_busca_catalogacao_redesign.py:43  assert callable(pag_busca._renderizar_facetas_laterais)
tests/test_busca_catalogacao_redesign.py:66  assert hasattr(pag_busca, "_highlight_termo")
tests/test_sistema_redesign.py:32            assert hasattr(skills_d7, "renderizar")
tests/test_sistema_redesign.py:33            assert callable(skills_d7.renderizar)
tests/test_sistema_redesign.py:38            assert hasattr(styleguide, "renderizar")
tests/test_visao_geral_redesign.py:165       assert classe X em CSS local
tests/test_visao_geral_redesign.py:201       assert SVG sem quebra de linha
```

Esses testes inflam o contador (parte dos "+502 testes vs baseline ~2018") mas não validam comportamento real. Bug do Extrato passou pelo gauntlet pytest sem ser detectado -- porque os testes redesign não cobrem agregação financeira.

### 5.3 Código duplicado entre páginas Bem-estar

12 páginas `be_*.py` compartilham scaffolding:
- Cabeçalho mono `BEM-ESTAR / X` + descrição + badge UX-RD-NN.
- Filtros laterais (Modo, Período, Pessoa).
- Empty state quando vault não tem dados.

Não foi extraído para `componentes/be_layout.py`. Há ganho real de DRY se for sprint corretiva.

---

## 6. Veredicto final

### 6.1 Score de fidelidade ao mockup

**57/100** (média de 29 telas, 4 dimensões cada).

Distribuição:
- 7 telas >=80% (sucesso)
- 13 telas 60-79% (parcial)
- 3 telas 50-59% (empty state ou bug grave)
- 5 telas em 0% (deep-link quebrado)

### 6.2 Score de saúde funcional

| Componente | Pontos |
|---|--:|
| Pytest 2520 passed / (2520+0 failed) x 30 | 30/30 |
| Smoke aritmético 10/10 contratos | 30/30 |
| Pipeline `--tudo` (não rodei, mas XLSX/grafo íntegros + smoke OK) | 18/20 |
| Drill-down operando em 4 clusters | 5/5 |
| Deep-link Revisor 4-way (parcial: só ETL x Opus visível) | 3/5 |
| Autocomplete Busca Global (não testei interação) | 0/5 |
| Revisor 4-way pleno (não implementado) | 3/5 |
| CSV export (não testei click) | 0/5 |

**Total: 89/100, descontado 11 do lint quebrado = 78/100.**

### 6.3 Top 5 problemas (priorizado)

| # | Severidade | Arquivo:linha | Problema | Correção 1-linha |
|--:|---|---|---|---|
| 1 | P0 | `app.py:132-145` | 5 abas Bem-estar inexistentes na lista (Rotina, Memórias, Cruzamentos, Privacidade, Editor TOML) -- deep-link cai em Hoje | adicionar as 5 strings em `ABAS_POR_CLUSTER["Bem-estar"]` |
| 2 | P0 | `paginas/extrato.py` (extração) | Despesa R$ 0,00 enquanto backend tem R$ 3.391,77 em abril/2026 (78 trans) | revisar filtro `tipo == "Despesa"` na agregação dos KPIs |
| 3 | P0 | `app.py:625-637` | 5 abas-fantasma (Treinos/Marcos -> Memórias; Alarmes/Contadores/Tarefas -> Rotina) -- usuário vê 12, recebe 7 conteúdos | criar páginas reais OU remover abas-fantasma e renomear `ABAS_POR_CLUSTER` |
| 4 | P1 | `Makefile:43` (`make lint` chama `check_acentuacao.py`) | exit 1: 11 erros em `.md` (8 em `novo-mockup/`, 3 em `docs/sprints/`) | corrigir os 11 .md ou adicionar `novo-mockup/` ao excluded de `check_acentuacao.py` |
| 5 | P1 | 39 .py em src/ (lista em seção 3.5) | regra 10 do CLAUDE.md (citação filosófica final) violada em 100% dos novos | sprint corretiva UX-RD-CIT-01 adicionando citação em todos |

### 6.4 Achados colaterais a virar sprint formal

| ID sugerido | Tema | Origem |
|---|---|---|
| **UX-RD-CIT-01** | Adicionar citação filosófica final em 60 arquivos novos | regra 10 CLAUDE.md, seção 3.5 |
| **UX-RD-DECOMP-01** | Decompor 5 arquivos >800 linhas em helpers | CLAUDE.md "Limite 800 linhas", seção 3.6 |
| **UX-RD-DEEPLINK-01** | Habilitar deep-link `?tab=Privacidade/Cruzamentos/Rotina/Memorias/EditorTOML` | top problema #1 |
| **UX-RD-EXTRATO-FIX-01** | Corrigir agregação Despesa R$ 0 no Extrato | top problema #2 |
| **UX-RD-12ABAS-01** | Decidir: criar Treinos/Marcos/Alarmes/Contadores/Tarefas reais OU remover do mockup/ABAS_POR_CLUSTER | top problema #3 |
| **UX-RD-LINT-01** | Corrigir 11 erros de acentuação em .md, restaurar `make lint` exit 0 | top problema #4 |
| **UX-RD-VG-01** | Decidir Visão Geral: KPIs financeiros (atual) vs agentic-first (mockup) | tela 01, divergência semântica |
| **UX-RD-REVISOR-4W-01** | Implementar comparação 4-way real (ETL x Opus x Grafo x Humano) na Revisor | tela 09 |
| **UX-RD-DUP-HEAD-01** | Eliminar cabeçalho duplicado em Busca Global e Catalogação | telas 06, 07 |
| **UX-RD-BE-DRY-01** | Extrair scaffolding de be_*.py para componentes/be_layout.py | seção 5.3 |
| **UX-RD-TESTES-COMPORT-01** | Substituir asserts hasattr/callable por testes de comportamento | seção 5.2 |

### 6.5 O que esta auditoria NÃO cobriu (para honestidade)

- **Não testei** click real em `st.download_button`, autocomplete e atalhos de teclado j/k/a/r -- playwright headless dificulta interação dinâmica de Streamlit.
- **Não rodei** `./run.sh --tudo` (preservei `data/output/` por segurança).
- **Não validei** mobile bridge (Mob-Ouroboros companion).
- **Não medi** acessibilidade WCAG (contraste foi inspecionado parcialmente em Categorias).
- **Não comparei** performance (carga das páginas, cache D7).
- **Não inspecionei** o conteúdo de `docs/sprints/concluidos/sprint_ux_rd_*.md` em profundidade -- só grep por palavras-chave.

### 6.6 Recomendação geral

A reforma **avançou em fundação visual** (paleta Dracula consistente, sidebar 8-clusters, badges UX-RD-NN em cada tela, breadcrumb topbar, smoke 10/10 + 2520 pytests verdes) mas **superestimou cobertura dos mockups Bem-estar**. Cinco mockups inteiros (Rotina, Memórias, Cruzamentos, Privacidade, Editor TOML) ficaram inacessíveis por deep-link. Cinco abas declaradas duplicam outras 2 páginas. O comentário em `app.py:622` ("preservar o invariante N=12 abas") explicita a decisão -- uma fraude de UI deliberada para "fechar" a Onda 6 sem implementar o restante.

A urgência é resolver os P0 (deep-link, abas-fantasma, bug Extrato) antes de declarar a reforma encerrada. Corrigir o lint e adicionar citação filosófica é higiene base.

19 sprints num único dia (2026-05-04) sem nenhum achado colateral declarado é o sinal mais forte: o ciclo `executor -> validador -> commit -> push` automatizado fechou sprints sem que a inteligência crítica visse o produto integrado. Recomendo retomar o **VALIDATE** humano (você, dono) entre Onda e Onda -- não apenas screenshot, mas deep-link manual.

---

---

## 7. Auditoria de UI/UX profunda (atualização 2026-05-05 16:30)

> Re-auditoria após pedido do dono: análise estética e funcional **considerando o todo**, não amostragem. Medidas extraídas via `getComputedStyle()` do DOM ao vivo (Streamlit em `127.0.0.1:8765` e mockups em `127.0.0.1:8766`).
> Logs: `/tmp/auditoria_redesign/logs/{medir_estilos,medir_estetica2,medir_diff_componentes}.log`.

### 7.1 Sistema tipográfico — **divergência grave**

O mockup separa rigorosamente **Inter (sans)** para corpo + **JetBrains Mono** para números, headings técnicos e UI dura (badges, breadcrumb, KPI value). O dashboard injeta `"Source Code Pro", monospace` em **quase tudo** -- perdeu a hierarquia.

| Elemento | Mockup | Dashboard | Diagnóstico |
|---|---|---|---|
| Corpo (parágrafo) | `Inter` 14px fw400 | `"Source Code Pro", monospace` 13px fw400 | dashboard usa MONO em texto longo (anti-padrão de leitura) |
| Sidebar item | `Inter` 13px fw400 | `"Source Code Pro", monospace` 13px fw400 | divergência de família |
| KPI value | `JetBrains Mono` 32px fw500 ls -0.64px | `JetBrains Mono` 33.75px fw**400** ls -0.56px | dashboard com peso menor (400 vs 500) |
| KPI label | `Inter` 11px fw500 ls 0.88px UPPERCASE color text-muted | `"Source Code Pro"` 15px fw400 normal color text-primary | tudo errado: família, tamanho (+36%), peso, caps, cor |
| Page-title | `JetBrains Mono` **40px** fw500 ls -0.8px **UPPERCASE** + **gradient text** | `monospace` (genérico!) 28px fw700 ls normal sem caps cor sólida `#bd93f9` | -30% tamanho, sem gradient, peso errado, família genérica |
| Breadcrumb | `JetBrains Mono` 12px ls 0.48px UPPERCASE text-muted | igual | OK -- único item correto |
| Botão | `Inter` 12-13px fw500 | `"Source Code Pro"` 15px fw400 | divergência total |
| Pill/Badge | `JetBrains Mono` 11px fw500 ls 0.44px UPPERCASE | `JetBrains Mono` 13px fw400 ls 0 sem caps | maior, sem peso, sem caps, sem letter-spacing |
| Tab ativa | -- (mockup usa `<a>` na sidebar) | `"Source Code Pro"` 15px fw700, height 56px | aba fica gigante (56px) |
| H3 | `JetBrains Mono` 11px fw700 UPPERCASE text-muted (mini-cabeçalhos de card) | `"JetBrains Mono"` 18px fw600 UPPERCASE color cyan | dashboard fez h3 ser 64% maior e mudou cor |

**Resumo**: dashboard tem 1320 linhas em `tema_css.py` (3.4× mais que mockup) mas perdeu o sistema dual sans/mono. Resultado visual: tudo "monoespaçado" e maior, sem ritmo tipográfico.

### 7.2 Sistema de cores -- aplicação parcial dos tokens

Tokens canônicos do mockup (`novo-mockup/_shared/tokens.css`):

```
--bg-base:     #0e0f15  (fundo página)
--bg-surface:  #1a1d28  (sidebar, topbar, card)
--bg-elevated: #232735  (card hover, KPI hover)
--bg-inset:    #0a0b10  (input, sprint-tag)
--text-primary:   #f8f8f2
--text-secondary: #a8a9b8
--text-muted:     #6c6f7d
--accent-purple: #bd93f9 (Dracula)
+ 6 acentos Dracula
```

Aplicação observada no dashboard:

| Token | Mockup | Dashboard | Status |
|---|---|---|---|
| `--bg-base` | aplicado em `body` | aplicado | OK |
| `--bg-surface` | sidebar + topbar + card padrão | sidebar OK; topbar **invisível**; card OK | parcial -- topbar não aparece visualmente |
| `--bg-elevated` | card-hover, KPI-hover, drawer | sem hover state observável | hover não-implementado |
| `--text-muted` em KPI label | aplicado | trocado por `text-secondary` (#a8a9b8 vs #6c6f7d) | mais claro do que deveria |
| `--accent-purple` em page-title | combinado em **gradient** com text-primary | usado **sólido** no h1 | gradient text não aplicado |
| `--accent-cyan` em h3 | não usado | h3 do dashboard fica cyan | divergência: mockup não usa cyan em h3 |

### 7.3 Espaçamento e layout

Mockup tem **scale 4px-base** rigorosa: sp-1=4 sp-2=8 sp-3=12 sp-4=16 sp-5=20 sp-6=24 sp-8=32 sp-10=40 sp-12=48 sp-16=64.

| Métrica | Mockup | Dashboard | Diff |
|---|---|---|---|
| Sidebar width | **240px** | 245px | +5px, OK |
| Topbar height | **56px** | -- (não há topbar separada; usa breadcrumb dentro do `main`) | mockup tem `border-bottom 1px subtle` na topbar; dashboard mistura no body |
| Page header height | **72px** | 101px | +40% |
| Main padding | **24px** (sp-6) | streamlit padrão `1rem` (16px) | dashboard mais apertado |
| Card padding | **16px** (sp-4) | 14px 18px | quase igual |
| Card border-radius | **6px** (r-md) | 8px | +2px |
| Botão border-radius | **4px** (r-sm) | 7.5px | +3.5px (botões muito mais redondos) |
| Botão padding | 6px 12px | **3.75px 11.25px** | mais fino vertical |
| Botão height | ~27px | **44px** (CTA) ou 38px (secundário) | botão CTA **63% mais alto** |
| Pill border-radius | **999px** (full) | 2px | mockup é pill round, dashboard é tag retangular |
| Page-header bottom-border | 1px subtle | sem border | divergência |

### 7.4 Page title -- duplicação e perda de hierarquia

**Mockup**: 1 page-title por tela. JetBrains Mono 40px, font-weight 500, letter-spacing -0.02em, UPPERCASE, com **gradient text** (`linear-gradient(180deg, var(--text-primary) 0%, color-mix(in oklch, var(--text-primary) 80%, var(--accent-purple)) 100%)` aplicado via `-webkit-background-clip: text`).

**Dashboard** (medido em `?cluster=Documentos&tab=Revisor`):

```
h1[1] "Protocolo Ouroboros" (st.title global): visível, 246x101px, monospace 28px fw700, color #bd93f9 sólido
h1[2] "BUSCA GLOBAL"        (tab paralela invisível, 0x0)
h1[3] "CATALOGAÇÃO"          (tab paralela invisível, 0x0)
h1[4] "COMPLETUDE"           (tab paralela invisível, 0x0)
h1[5] "REVISOR"              (página atual): visível, 628x67px
h1[6] "MOC — Abril 2026"     (tab paralela invisível, 0x0)
```

**Achados graves**:
1. **2 h1 visíveis simultaneamente** ("Protocolo Ouroboros" + "REVISOR") -- viola HTML/A11y (1 h1 por documento).
2. **6 h1 no DOM**, 4 invisíveis -- `st.tabs()` mantém todas renderizadas; cada página tem seu próprio h1; arquitetura de tabs paralelas + h1 por página colide.
3. **`st.title("Protocolo Ouroboros")` global** (`app.py:238`) sobrepõe a hierarquia.
4. **Gradient text não aplicado** em nenhum h1.
5. **UPPERCASE só no h1 da página** (REVISOR), não no global. Mockup canonicamente quer **todos os page-title em uppercase com gradient**.

**Correção**: remover `st.title("Protocolo Ouroboros")` (regredir para apenas o brand HTML do shell na sidebar) + garantir que cada página produza seu próprio `<h1 class="page-title">` com `text-transform: uppercase` + gradient via CSS.

### 7.5 Sidebar -- "OOuroboros" e perda de glyphs

| Item | Mockup | Dashboard |
|---|---|---|
| Brand | SVG `ouroboros` (círculo + 2 setas) + texto "Ouroboros" | letra "**O**" como placeholder (`shell.py:140`) + texto "Ouroboros" -- visualmente lê **"OOuroboros"** |
| Cluster headers | UPPERCASE 11px ls 0.10em mono text-muted **+ glyph SVG cluster** ao lado | UPPERCASE 11px ls 0.10em **sem ícone** |
| Item ativo | `linear-gradient(90deg, rgba(189,147,249,0.12), transparent 60%)` + `border-left: 2px solid accent-purple` | **MESMA fórmula aplicada corretamente** -- único componente sidebar fiel |
| Item count | `.count` mono 10px text-muted | implementado parcialmente |
| Busca | `<kbd>/</kbd>` posicionado absoluto no canto direito | mostrado, mas placeholder "Buscar fornecedor, sha8" + kbd "/" fica visualmente esquisito |

**Glyphs.js do mockup tem 23 ícones SVG inline custom** (`ouroboros`, `inbox`, `home`, `docs`, `analise`, `metas`, `financas`, `search`, `upload`, `download`, `diff`, `validar`, `rejeitar`, `revisar`, `drag`, `more`, `filter`, `expand`, `collapse`, `close`, `terminal`, `folder`, `arrow-left/right`). Estilo: "mono-linha 1.5px, traço quadrado, viewBox 24x24". **Dashboard usa Material Symbols** (do Streamlit) em vez do sistema próprio.

### 7.6 Botões -- 3 sistemas distintos perdidos

**Mockup define 5 variantes** (`components.css:158-177`):

```
.btn          (default): bg-elevated, border subtle, color primary, 13px Inter fw500, padding 6 12, radius 4
.btn-primary  : bg accent-purple, color text-inverse (#0e0f15), 13px Inter fw500
.btn-ghost    : transparent, sem border-color
.btn-danger   : transparent, color accent-red, border red 30%
.btn-sm       : padding 4 8, font 12px
.btn-icon     : padding 6, svg 14x14
```

**Dashboard expõe**:
- Botões Streamlit nativos: 15px Source Code Pro fw400 padding 3.75 11.25 radius 7.5
- Botão CTA: bg `#bd93f9` color **white** (mockup quer `text-inverse #0e0f15` -- preto sobre roxo, contraste WCAG-AAA; dashboard usa branco em roxo, contraste pior)
- 92 botões "keyboard_double_arrow_left" expondo o **nome do ícone Material Symbols como texto bruto** (vide §7.11)
- Sem variantes `btn-ghost` nem `btn-danger` aplicadas com identidade visual

### 7.7 KPI tile -- estrutura inconsistente entre páginas

**Mockup** (`components.css:204-241`):

```
.kpi  -- bg-surface, border 1px subtle, radius 6, padding 12 16, min-w 180, height 96
        ::after  -- linha gradient horizontal accent-purple, opacity 0, .5 no hover
.kpi-label  -- 11px fw500 ls 0.08em UPPERCASE Inter color text-muted
.kpi-value  -- 32px fw500 ls -0.02em JetBrains Mono tabular-nums
.kpi-delta  -- 12px JetBrains Mono, color por sentido (up/down/flat)
.kpi-grid   -- display grid, auto-fit minmax(180px, 1fr), gap 12
```

**Dashboard**:
- Em `Visão Geral` (`paginas/visao_geral.py`): cards CSS custom sem `[data-testid='stMetric']` (não usa st.metric -- minha medição retornou ausente).
- Em `Revisor`: usa `st.metric` (8 instâncias). Value 33.75px Source Code Pro fw400. Label 15px Source Code Pro fw400 sem caps -- 100% errado vs mockup.
- **Sem linha gradient ::after** no hover (decoração de elevação ausente).
- **Sem `.kpi-delta`** estilizado.

**Inconsistência interna**: Visão Geral usa um padrão (cards CSS custom), Revisor usa outro (st.metric). Não há "KPI canônico" único na branch.

### 7.8 Pills/badges -- divergência de shape

**Mockup**: pill é **totalmente redondo** (`border-radius: 999px`), 11px JetBrains Mono fw500 ls 0.44px UPPERCASE, padding 2 8. 4 famílias D7 (graduado/calibracao/regredindo/pendente) + 4 famílias humano (aprovado/rejeitado/revisar/pendente) com cor de fundo 10-15% opacidade + cor de texto + border 25-30% opacidade.

**Dashboard**: badges encontradas têm `border-radius: 2px` (retangular), texto sem caps, peso 400. Os badges "UX-RD-NN" mostrados em cada tela usam estilo próprio que não bate com o mockup.

**Visualmente**: mockup tem pílulas redondas com ar; dashboard tem retângulos pequenos, mais quadrados.

### 7.9 Inputs -- placeholder duplicado

A captura do dashboard mostra:

```
sidebar-search input  background #0a0b10 (bg-inset, OK), border 1px subtle, placeholder "Buscar fornecedor, sha8 /"
                                                            ^^^^^^^^^^^^^^^ texto incluindo o "/" do kbd
+ kbd "/" posicionado no canto direito
```

O `/` aparece duas vezes: no placeholder do input + no kbd do canto. No mockup, o placeholder é apenas "Buscar fornecedor, sha8 ou valor" e o kbd `/` é elemento separado.

### 7.10 Tabelas -- ausência de tabela canônica

**Mockup** (`components.css:298-326`):

```
.table  -- 13px, border-collapse, row-h 32, sticky thead
.table thead th  -- mono 11px fw500 ls 0.06em UPPERCASE bg-surface, color text-muted, border-bottom strong
.table tbody tr:hover  -- bg-elevated
.table tbody tr.selected  -- rgba(189,147,249,0.08)
.col-num  -- text-align right, mono, tabular-nums
.col-mono -- mono
```

**Dashboard**: usa `st.dataframe` (apenas em algumas páginas) ou markdown table. Cabeçalhos da dataframe Streamlit são 15px Source Code Pro -- **muito maiores e mono** comparado ao mockup (11px UPPERCASE). Não há `:hover` row, não há `.col-num` específico para alinhar números à direita.

### 7.11 Iconografia -- 92 ícones vazando como texto

**Achado crítico**: na tela do Revisor, **92 botões expõem o nome do ícone Material Symbols como texto bruto** (ex.: `"keyboard_double_arrow_left"`). Material Symbols funciona injetando uma fonte que mapeia ligaturas; quando a font não carrega ou é sobrescrita pela `font-family: "Source Code Pro", monospace` global do tema, o texto bruto vaza.

```
grep 'material-symbols\|fonts.googleapis' src/dashboard/tema_css.py  --> ZERO
```

`tema_css.py` **não importa** Material Symbols, mas Streamlit injeta automaticamente -- e o tema do redesign sobrescreve `font-family` em `[data-testid='stIconMaterial']` ou similar via cascata. Resultado: paginadores, botões collapse/expand, ícones de tab fechar etc. mostram "keyboard_arrow_down", "keyboard_double_arrow_left", "expand_more", "close" como texto.

**Mockup tem 23 glyphs SVG inline custom** (`novo-mockup/_shared/glyphs.js`) com estética "mono-linha 1.5px, traço quadrado, viewBox 24x24". Sistema completamente diferente que **não foi portado** para o dashboard.

### 7.12 Gráficos -- biblioteca diferente

**Mockup**: **SVG inline custom** desenhado à mão. Em 12 dos 29 mockups encontrei `<svg viewBox=...>` direto, com `polyline`, `path`, `rect`. Estilo: linhas finas (1.4-1.5px), sem hover boxes pesados, sem modebar, sem axis ticks padronizados. Sparkline em `.acc-spark`, donut customizado em metas, heatmap em `<rect class="cell">`, sankey custom.

**Dashboard**: **Plotly** (8 gráficos por página em média). Plotly traz:
- Modebar com botões de zoom/pan/reset (não está no mockup) -- modebar está VISÍVEL no Revisor.
- Hover boxes brancas com fonte sans (mockup tem hover sutil em cor accent).
- Axis ticks com peso de fonte default (Inter) que muda na cascata do tema.
- Cores divergentes da paleta Dracula (Plotly usa paleta default colorida).

**Resultado**: visual **completamente diferente** do mockup minimalista. Mesmo a tela 12 (Análise) que tem Sankey mostrou cores Plotly Sankey diferentes do mockup.

### 7.13 Estados (hover, focus, active, selected, disabled)

| Estado | Mockup define | Dashboard observado |
|---|---|---|
| Sidebar item :hover | `bg-elevated` + cor primary | aparente sim |
| Sidebar item .active | gradient + border-left | OK |
| Card.interactive :hover | `border-color accent-purple` + `transform translateY(-1px)` + `box-shadow 0 6px 20px -10px rgba(189,147,249,0.3)` | nenhum hover-effect observável em cards |
| KPI :hover | border-strong + ::after gradient opacity 0.5 | sem hover |
| Botão :active | `transform translateY(1px)` | sem feedback de press |
| `:focus-visible` | `box-shadow: 0 0 0 2px var(--bg-base), 0 0 0 4px var(--accent-purple)` (anel duplo) | Streamlit usa anel próprio |
| Tabela tr :hover | `bg-elevated` | dataframe Streamlit não tem hover por linha |
| Tabela tr.selected | `rgba(189,147,249,0.08)` | sem suporte |

**Resumo**: micro-interações do mockup praticamente não foram portadas. A camada visual está estática.

### 7.14 Componentes UX ausentes

| Componente do mockup | Local | Status no dashboard |
|---|---|---|
| **Drawer lateral** (`components.css:328-354`) | mockup 02 (extrato), 09 (revisor) | **ausente** -- não há `[role="dialog"]` nem painel deslizante |
| **Atalhos de teclado** `g h`, `g i`, `g v`, `g r`, `g f`, `?` | `shell.js:196-275` | **parcial** -- dashboard tem 5 kbd visíveis (`/`, `j`, `k`, `a`, `r`) mas faltam os prefixos `g X` (chord) e `?` (overlay help) |
| **Overlay "Lista de atalhos"** | `shell.js:241-275` chamado por `?` | **ausente** -- `?` não abre nada |
| **Topbar com ações** (Atualizar, Exportar, etc.) | `components.css:144` `.topbar-actions` | dashboard não tem topbar separada; "Importar OFX"/"Exportar" do mockup 02 não aparecem |
| **Skill instr** (`components.css:357-387`) | mockup 16 (inbox) | **ausente** -- Inbox tem dropzone mas não mostra "como reusar" do mockup |
| **Confidence bar** (.confidence-bar de 36×4px) | mockup 09 (revisor) | **ausente** |
| **Diff viewer** (added/removed gutters) | tokens existem, sem componente CSS dedicado em `components.css`; usado em mockup 09 | dashboard usa `st.dataframe` sem diff visual |
| **Sprint tag** (`.sprint-tag` 11px mono UPPERCASE bg-inset) | todos mockups | dashboard tem badges UX-RD-NN próprios, mas estilo diferente |
| **Modal/dialog** | -- | Streamlit não usa `st.dialog` na branch |
| **Page-meta** (acima do título -- contexto) | `.page-meta` em mockups 09, 18, 22 | ausente |
| **Drawer-tabs** (tabs internas dentro de drawer) | components.css:344 | ausente |

### 7.15 Comportamento JS dos mockups que o dashboard precisaria reproduzir

`shell.js` mais `_<tela>-render.js` definem:

| Tela | `_<tela>-data.js` | Comportamento JS |
|---|---|---|
| 09 revisor | `_revisor-data.js` (3.9 KB) + `_revisor-render.js` (13 KB) | renderiza cards de transação com 4 colunas (ETL/Opus/Grafo/Humano), atalhos `j/k/a/r`, contador "29 / 1 de 29", drawer detalhe |
| 10 validacao-arquivos | `_extracao-data.js` (16 KB) + `_extracao-render.js` (14 KB) | layout 3-col (lista \| viewer \| tabela ETL×Opus×Humano) |
| 16 inbox | `_inbox-data.js` (2.9 KB) + `_inbox-render.js` (6.9 KB) | dropzone + lista densa de arquivos com sha8, status, próxima ação |
| 14 skills-d7 | `_skills-d7-data.js` (6.3 KB) + `_skills-d7-render.js` (15 KB) | painel rico de skills com snapshot, evolução |
| 13 metas | `_metas-data.js` (3.3 KB) + `_metas-render.js` (10 KB) | metas com donuts, barras, comparativo |
| 01 visao-geral | `_visao-render.js` (8.6 KB) | KPI cards + cluster grid + atividade recente + skill-instr |

**O dashboard reconstruiu cada uma destas em Python+CSS**, mas com perda visual significativa nas 5 telas Bem-estar inacessíveis (vide §6.3). Para "ficar idêntico ao mockup" o dashboard precisaria:

1. Implementar drawer lateral via `st.dialog` ou `streamlit-modal`.
2. Portar `glyphs.js` (23 ícones) como SVG inline em `componentes/glyphs.py`.
3. Refazer `tema_css.py` separando `Inter` (sans) de `JetBrains Mono` (mono) com regras precisas por seletor (não global).
4. Substituir Plotly por SVG inline custom em ao menos: sparklines, donuts, heatmap, sankey simples.
5. Aplicar gradient text na page-title.
6. Implementar pill com `border-radius: 999px` em todas as classes `.pill-*`.
7. Restaurar variantes de botão (`btn-ghost`, `btn-danger`, `btn-sm`, `btn-icon`).
8. Importar Material Symbols explicitamente OU desabilitar (ícones do Streamlit) e suprimir o vazamento de texto.
9. Suprimir `st.title("Protocolo Ouroboros")` global (`app.py:238`) -- o brand já vem do shell HTML.
10. Implementar atalhos `g X` (chord) e `?` (overlay help), além de `j/k/a/r`.
11. Aplicar transições/`:hover` em cards, KPIs, botões.
12. Restaurar `topbar-actions` com botões secundários (Atualizar, Exportar, Importar OFX).
13. Decompor `tema_css.py` (1320 linhas) em módulos por componente alinhados com `components.css` do mockup.

### 7.16 Score estético revisado

A nota anterior (57%) considerava 4 dimensões macro. Com medição de **componentes individuais** ao DOM ao vivo:

| Sub-dimensão | Aplicação canônica | Score |
|---|--:|--:|
| Tipografia (família/tamanho/peso/letter-spacing/caps) | 8 critérios; 1 OK (breadcrumb) | 12% |
| Cores (tokens aplicados nos lugares certos) | 11 critérios; 6 OK | 55% |
| Espaçamento (4px scale) | 10 critérios; 6 OK | 60% |
| Page-title (UPPERCASE + gradient + 40px mono) | 5 critérios; 0 OK | 0% |
| Sidebar (brand SVG + glyphs cluster + item ativo) | 5 critérios; 1 OK (item ativo) | 20% |
| Botões (5 variantes + estados active/hover) | 7 critérios; 2 OK | 28% |
| KPI (label UPPERCASE + value mono + ::after gradient) | 6 critérios; 2 OK | 33% |
| Pills/badges (radius full + UPPERCASE + 11px mono) | 4 critérios; 0 OK | 0% |
| Iconografia (23 glyphs custom) | 0 portados; Material vazando | 0% |
| Gráficos (SVG inline custom vs Plotly) | 0 telas usam SVG inline custom | 0% |
| Estados (hover/focus/active/selected) | 8 estados; 1 OK (sidebar.active) | 12% |
| Componentes UX (drawer, atalhos chord, modal, topbar-actions) | 6 componentes; 0 implementados, 1 parcial | 8% |

**Score estético detalhado: ~20-25%.**

Quando o dono diz **"a ideia é o projeto ser idêntico ao mockup em tudo"**, a fidelidade real é da ordem de **20%**, não 57%. O 57% anterior considerava só presença/ausência de seções; o 20% considera identidade visual e funcional 1:1.

### 7.17 Top 10 problemas estéticos (P0/P1) -- complemento aos da §6.3

| # | Severidade | Problema | Arquivo:linha | Correção |
|--:|---|---|---|---|
| 11 | P0 | 92 botões expondo "keyboard_double_arrow_left" como texto bruto na Revisor | `tema_css.py` (sobrescrita global `font-family`) | adicionar regra `[data-testid="stIconMaterial"], .material-symbols-outlined { font-family: "Material Symbols Outlined" !important; }` |
| 12 | P0 | 2 h1 visíveis simultaneamente ("Protocolo Ouroboros" + "REVISOR"); 6 h1 no DOM | `app.py:238` `st.title("Protocolo Ouroboros")` + uso de st.tabs com h1 por aba | remover st.title global; usar apenas brand HTML do shell na sidebar; gerar 1 page-title h1 por página |
| 13 | P0 | "OOuroboros" na sidebar (placeholder letra "O" em vez do glyph SVG) | `componentes/shell.py:140` `<span>O</span>` | criar `componentes/glyphs.py` portando os 23 SVGs do mockup; usar `glyph('ouroboros', 20)` |
| 14 | P0 | Page-title sem UPPERCASE, sem gradient text, font-family "monospace" genérica, 28px em vez de 40px | `tema_css.py:318+` `.page-title` declarado mas h1 do dashboard não recebe a classe | aplicar `class="page-title"` em todos os h1 das páginas; suprimir h1 redundante |
| 15 | P0 | Tipografia global `"Source Code Pro", monospace` sobrescreve Inter em sidebar items, KPI label, parágrafos | `tema_css.py:162-163` define ff-sans/ff-mono mas alguma regra global aplica mono em tudo | trocar regras-globais por seletores específicos: `body` → Inter; `.mono, .kpi-value, .breadcrumb, code, pre` → JetBrains Mono |
| 16 | P0 | Pills tem `border-radius: 2px` (retangular) em vez de `999px` (full-rounded) | `tema_css.py` (estilo de badge UX-RD-NN) | aplicar regra do mockup `border-radius: 999px` em todas as classes `.pill-*` |
| 17 | P1 | Plotly modebar visível em todos os gráficos | `paginas/*.py` chamadas `st.plotly_chart` sem `config={'displayModeBar': False}` | adicionar `config={'displayModeBar': False}` em todos `st.plotly_chart` |
| 18 | P1 | Plotly cores não-Dracula em sankey, bar, donut | template Plotly default | criar `dashboard/tema_plotly.py` com template custom usando paleta Dracula |
| 19 | P1 | Sem hover/transition em cards e KPIs (estética estática) | `tema_css.py` falta regras `:hover`, `transition`, `transform` | portar regras `.card.interactive:hover` e `.kpi:hover` do mockup |
| 20 | P1 | Drawer lateral, atalhos `g X` chord, overlay `?` ausentes | sem implementação | sprints separadas por componente (drawer, chord, help-overlay) |

### 7.18 Recomendação revisada

A reforma fez **trabalho real de fundação** (paleta Dracula no nível dos tokens, sidebar com gradient correto em item ativo, breadcrumb mono UPPERCASE) -- mas o que o dono pediu (**"idêntico ao mockup em tudo"**) requer reconstrução componente por componente: tipografia, page-title, ícones, gráficos, estados, drawers. Isso não cabe em 1-2 sprints corretivas.

**Sugestão de roteiro** (mínimo 5 sprints):

- **UX-RD-CSS-FIX-01** -- corrigir tipografia (Inter vs Mono), pills round, page-title gradient, h1 único.
- **UX-RD-GLYPHS-01** -- portar 23 SVGs custom para `componentes/glyphs.py`.
- **UX-RD-PLOTLY-01** -- template Plotly Dracula + suprimir modebar; substituir sparklines/donuts por SVG inline custom.
- **UX-RD-INTERACOES-01** -- hover/focus/transitions em cards, KPIs, botões; restaurar variantes btn.
- **UX-RD-DRAWER-CHORD-01** -- drawer lateral via st.dialog + atalhos `g X` chord + overlay `?`.

Sem essas 5, o dashboard **não fica idêntico ao mockup**. Continua sendo "Streamlit com tema Dracula" e não "Ouroboros conforme o blueprint".

---

---

## 8. Auditoria UI/UX detalhe-do-detalhe -- correções e refinamentos (2026-05-05 17:00)

> Rodada nova com 5 agentes Explore em paralelo + validação direta no DOM via playwright. Esta seção **corrige** afirmações da §7 que eram superficiais ou incorretas.

### 8.1 Correções honestas à §7

Validação direta de `.pill`, `.page-title`, `.sprint-tag` na tela Categorias revelou que **eu havia medido elementos errados** em §7. Os elementos corretos do tema mostram:

| Componente | §7 disse | Verdade no DOM | Veredicto |
|---|---|---|---|
| `.pill` border-radius | "2px (retangular)" | **999px (full round)** OK | **§7 estava errado** |
| `.pill` font-family | -- | JetBrains Mono OK | OK |
| `.pill` text-transform | "sem caps" | UPPERCASE OK | **§7 estava errado** |
| `.pill` font-size | 13px | **15px** (mockup pede 11px) | divergência menor |
| `.page-title` text-transform | "sem uppercase" | **UPPERCASE** OK | **§7 estava errado** |
| `.page-title` background-image | "color sólido" | **`linear-gradient(rgb(248,248,242), oklch(...))` + `background-clip: text`** OK | **§7 estava errado** |
| `.page-title` font-size | 28px | 28px (mockup pede 40px) | divergência real |
| `.page-title` font-family | "monospace genérica" | **`"Source Code Pro", monospace`** (mockup pede `JetBrains Mono`) | divergência real |
| `.page-title` font-weight | 700 | 700 (mockup pede 500) | divergência real |
| `.sprint-tag` border-radius | -- | 2px OK (mockup pede `r-xs` = 2px) | OK |
| `.sprint-tag` font-size | -- | **15px** (mockup pede 11px) | divergência menor |
| Anel ouroboros animado | "decoração estática" | **3 animações em execução** (ob-halo + 2x ob-rotate) OK | **§7 estava errado** |

A §7 mediu elementos genéricos (spans Streamlit) em vez dos elementos com classes do tema. As pills, page-title, sprint-tag, breadcrumb que **carregam classes do tema** estão de fato aplicadas com a maioria das propriedades do mockup. As divergências reais são em **escala** (15px vs 11px, 28px vs 40px) e **família tipográfica** (Source Code Pro em vez de JetBrains Mono) -- provavelmente por override do Streamlit base CSS.

### 8.2 Mapa componente×tema (resultado do agente 8a)

39 classes do `components.css` do mockup foram mapeadas em `tema_css.py`:

- **PRESENTES com equivalência exata: 38** (`tema_css.py` linhas 298-621).
- **DIVERGENTE: 1** -- `.kpi-grid` usa `repeat(auto-fit, minmax(220px, 1fr))` em `tema_css.py:1156-1161`; mockup usa `minmax(180px, 1fr)` (`components.css:241`). KPI cards renderizam 40px mais largos que o mockup.
- **AUSENTES: 0**.

Conclusão: o tema CSS foi portado integralmente. As divergências visuais que aparecem são por (a) elementos do Streamlit que **não recebem as classes** do tema (ex.: `<button kind="primary">` não vira `<button class="btn-primary">`), (b) overrides do Streamlit base que sobrescrevem propriedades específicas em cascata (font-size, font-family).

### 8.3 Animações e transições (resultado do agente 8b)

Inventário completo:

**Mockup (`@keyframes`)**:
- `ob-rotate` (80s linear infinite) -- `_visao-render.js:13`
- `ob-halo` (6s ease-in-out infinite) -- `_visao-render.js:14`
- `chegou` (0.8s ease-out) -- `16-inbox.html:51`
- `rot-slow`, `rot-rev`, `pulse-soft`, `flow` -- `index.html:7-10` (landing, fora do dashboard)

**Dashboard (`@keyframes`)**:
- `ob-rotate` -- `paginas/visao_geral.py:230` OK
- `ob-halo` -- `paginas/visao_geral.py:234` OK
- `inbox-chegou` (renomeado de `chegou`) -- `paginas/inbox.py:692` OK

**Validação direta**: anel ouroboros tem **3 animações em execução** confirmadas via `getAnimations()` -- ob-halo + 2× ob-rotate, todas com `playState='running'`.

**Transitions**: 100% das transições do mockup (`.sidebar-item .15s`, `.btn .15s/.12s`, `.card .18s triplo`, `.kpi .18s duplo + ::after`, `.table tbody tr`) **estão presentes** em `tema_css.py` com timing idêntico.

**Hover/active/focus states**: todos os 6 hover-states canônicos do mockup (sidebar-item, btn, btn-primary, card.interactive, kpi, table tr) **estão implementados** em `tema_css.py`. `:active { transform: translateY(1px) }` em `tema_css.py:351`. `:focus-visible` com box-shadow duplo presente.

**Único achado**: nome `chegou` virou `inbox-chegou` -- inconsistência cosmética; não causa bug.

### 8.4 Gráficos (resultado do agente 8c)

10 das 29 telas têm visualizações; 19 são tabelas/texto puro.

| Tela | Mockup | Dashboard | Status |
|---|---|---|---|
| 02 Extrato | `<polyline>` saldo + área gradient SVG inline | SVG inline custom | **IDÊNTICO** |
| 03 Contas | sparkline polyline `.acc-spark` por conta | SVG inline custom | **IDÊNTICO** |
| 05 Projeções | 3 linhas (otimista/real/pessimista) com `stroke-dasharray` SVG | Plotly Scatter (`projecoes.py:663-788`) | SIMILAR |
| 11 Categorias | treemap Plotly + árvore | Plotly treemap | **IDÊNTICO** |
| 12 Análise | Sankey path-based custom | Plotly Sankey (`analise_avancada.py:433-474`) | **IDÊNTICO** |
| 13 Metas | donut SVG (circle + dasharray) + gauge | Plotly Pie + Indicator (`metas.py:195-494`) | **IDÊNTICO** |
| 14 Skills D7 | line chart polyline + grid dashed | SVG inline custom | **IDÊNTICO** |
| 18 Humor | heatmap 13×7 grid + polyline overlay | SVG inline custom (`be_humor.py:106`) | **IDÊNTICO** |
| 24 Medidas | line multi-série | SVG inline custom | **IDÊNTICO** |
| 25 Ciclo | anel/aurora circle stroke -90° rotate | SVG inline custom | **IDÊNTICO** |
| 26 Cruzamentos | linhas + scatter + dashed | SVG inline custom | **IDÊNTICO** |

**9/10 IDÊNTICO + 1 SIMILAR (Plotly em projeções)**. Resultado **muito melhor** que minha §7 sugeria. Nenhuma tela substitui gráfico por tabela.

> Ressalva ao resultado do agente: minha medição direta na Análise/Categorias mostrou Plotly modebar **VISÍVEL** (`modebar_visible: true`). A presença do modebar nos charts Plotly é um delta visual ainda válido (mockup é estático/sem modebar). Sugestão: passar `config={'displayModeBar': False}` em todas as chamadas `st.plotly_chart`.

### 8.5 UX patterns (resultado do agente 8e)

15 padrões auditados:

**PRESENTE (9)**:
1. **Drawer lateral** (`componentes/drawer_transacao.py`) -- HTML+CSS `position:fixed`, com syntax highlight JSON.
2. **Atalhos teclado** `g h`, `g i`, `g v`, `g r`, `g f`, `g c`, `/`, `?`, `Esc` -- `componentes/atalhos_teclado.py:1-264`. **Todos os 9 mapeados** (eu havia dito que faltavam os `g X`; estava errado).
3. **Overlay help (?)** -- abre modal com tabela de atalhos (`atalhos_teclado.py:155-209`).
4. **Modal/dialog** -- `componentes/modal_transacao.py:136` usa `@st.dialog("Detalhes da transação", width="large")`.
5. **Tabs aninhadas** -- 7 clusters usam `st.tabs()` em `app.py`.
6. **Sticky header em tabela** -- `tema_css.py:543`. Funciona em `<table>` HTML; `st.dataframe` é limitação Streamlit.
7. **Tabs internas (sub-tabs)** -- presentes em Análise (Fluxo/Comparativo/Padrões).
8. **ARIA labels parcial** -- `aria-label` em brand glyph, busca, sidebar, breadcrumb (`shell.py:140,160,237,289`).
9. **Loading state** -- `st.spinner` em `grafo_obsidian.py:160` e `irpf.py:145`.

**PARCIAL (4)**:
- **Breadcrumb não-clicável** -- `<span>` em vez de `<a href>` (`shell.py:268-269`).
- **Focus order** -- ordem DOM natural respeita; sem `tabindex` customizado.
- **Deep-link Bem-estar** -- 5 abas quebradas (já documentado §6.3).
- **Auto-completar Busca Global** -- usa `st.button` columns em vez de `st.popover` (`busca.py:764-830`).

**AUSENTE (3)**:
- `st.popover` -- não usado em nenhum lugar.
- Skip links (`<a href="#main-root">`) -- ausentes.
- `::-webkit-scrollbar` custom -- não declarado em `tema_css.py`.
- `st.toast` -- não usado.

**Score UX patterns: 73/100.**

### 8.6 Achados de glyphs (icones SVG)

`glyphs.js` do mockup tem 23 SVGs custom (ouroboros, inbox, home, docs, analise, metas, financas, search, upload, download, diff, validar, rejeitar, revisar, drag, more, filter, expand, collapse, close, terminal, folder, arrow-left/right). 

Validação direta: `.sidebar-brand-glyph` no DOM do dashboard tem `text="O"` e **`has_svg: false`** -- letra placeholder, não foi portado o SVG `ouroboros` do `glyphs.js`. Os outros 22 ícones também não foram portados (dashboard usa Material Symbols nativos do Streamlit).

### 8.7 H1 duplicado confirmado

Validação direta na Visão Geral:

```
h1[1]: "Protocolo Ouroboros" (st.title global) -- visível, fs 28px, color #bd93f9 sólido, bg_image=none
h1[2]: "Os arquivos da sua vida financeira..." (page-title hero) -- visível, fs 28px, ff "JetBrains Mono"
```

**Dois h1 visíveis simultaneamente**. O primeiro vem do `st.title("Protocolo Ouroboros")` em `app.py:238`; o segundo é o page-title da página. Em Categorias é o mesmo: "Protocolo Ouroboros" + "CATEGORIAS".

A `.page-title` da página atual tem gradient + UPPERCASE corretos -- mas o `st.title` global rouba o foco visual e a hierarquia HTML.

### 8.8 Sumário tela-por-tela (resultado do agente 8d)

29 telas detalhadas em 5-8 achados cada. Padrões emergentes:

- **Telas com fidelidade alta** (estrutura+componentes do mockup respeitados): 03 Contas, 11 Categorias, 12 Análise, 13 Metas, 18 Humor, 24 Medidas, 25 Ciclo, 26 Cruzamentos.
- **Telas com calendário/visualização ausente**: 04 Pagamentos (calendário 7×2 não-renderizado visualmente; só lista upcoming), 28 Editor TOML (sem syntax highlight nativo no st.text_area).
- **Telas em fallback / não-implementadas via dispatcher**: 05 Projeções (`projecoes.py` não existe -- caiu no `_renderizar_fallback_cluster`); 20 Rotina, 23 Memórias, 26 Cruzamentos, 27 Privacidade, 28 Editor TOML (deep-link quebrado).
- **Detalhe de proporção**: maioria dos mockups usam grid CSS preciso (ex.: `grid-template-columns: 1.6fr 1fr`); dashboard usa `st.columns(1.6, 1)` proporcional, sem garantia de px exato. Diferença visível em viewports estreitos.
- **Animações**: somente Visão Geral (anel ouroboros) tem animação portada com sucesso. Inbox tem `inbox-chegou` declarada mas Streamlit `st.rerun()` perde o estado da animação a cada interação.

### 8.9 Score revisado e final

| Sub-dimensão | Score | Notas |
|---|--:|---|
| Componentes CSS portados (39 classes) | **97%** | 38/39 PRESENTE; 1 DIVERGENTE em `.kpi-grid` |
| Animações + transitions + hover/focus/active | **95%** | 100% transitions/hover; só renomeação `chegou` |
| Gráficos (29 telas com 10 visuais) | **95%** | 9 IDÊNTICO + 1 SIMILAR; modebar visível -- ressalva |
| UX patterns (15 padrões) | **73%** | 9 PRESENTE, 4 PARCIAL, 3 AUSENTE; deep-link bem-estar bloqueia |
| Iconografia (23 glyphs custom) | **0%** | nenhum portado; Material Symbols vazando "keyboard_double_arrow_left" |
| Tipografia (escala fs em px) | **45%** | mockup `fs-11/12/13/14/16/18/20/24/32/40` -- dashboard usa 13/15/18/28; perde escala fina |
| H1/page-title hierarquia | **40%** | gradient + UPPERCASE OK, mas h1 duplicado por `st.title` global; fs 28 vs 40 |
| Acessibilidade (ARIA, skip links, focus) | **55%** | aria-labels presentes; faltam skip links, role tablist |
| Conteúdo / dados visuais reais | **60%** | bug Despesa R$ 0,00; vault Bem-estar quase vazio; KPIs OK em maioria |
| Estrutura de telas (29 mockups) | **80%** | 24 implementadas e acessíveis; 5 deep-link quebrado |

**Score honesto consolidado** (média ponderada das 10 dimensões): **64/100**.

A reforma fez **trabalho de fundação muito mais sólido** do que minha §7 apurou. As classes do mockup estão portadas, animações operam, gráficos majoritariamente em SVG inline custom como o mockup pede, atalhos `g X` funcionam, drawer/dialog implementados.

As divergências reais e bloqueadoras são:
1. **Deep-link Bem-estar quebrado** (5 telas inacessíveis -- §6.3).
2. **5 abas-fantasma** duplicando 2 páginas (§3.2).
3. **H1 duplicado** (`st.title` global + page-title da página).
4. **Iconografia 0% portada** -- 23 SVGs custom + brand "OOuroboros" mostrando letra "O".
5. **Tipografia escala-grossa** -- fs-11 do mockup vira 15px no dashboard; fs-40 do page-title vira 28px.
6. **`.kpi-grid` largo demais** (220px vs 180px).
7. **Plotly modebar visível** em todos os charts.
8. **Bug Despesa R$ 0,00** (§3.2).
9. **`make lint` quebrado** (§6.3).
10. **Citação filosófica em 60 .py novos** (§3.5).

### 8.10 Roteiro de sprints corretivas revisado

| ID sugerido | Tema | Esforço |
|---|---|--:|
| **UX-RD-DEEPLINK-01** | declarar 5 abas Bem-estar em ABAS_POR_CLUSTER, remover expanders ocultos | S |
| **UX-RD-12ABAS-01** | criar `be_treinos`, `be_marcos`, `be_alarmes`, `be_contadores`, `be_tarefas` reais OU remover abas-fantasma | M |
| **UX-RD-EXTRATO-FIX-01** | corrigir filtro `tipo == "Despesa"` em `paginas/extrato.py` | XS |
| **UX-RD-H1-FIX-01** | remover `st.title("Protocolo Ouroboros")` global; manter brand HTML do shell | XS |
| **UX-RD-GLYPHS-01** | portar 23 SVGs do `glyphs.js` para `componentes/glyphs.py`; injetar no `.sidebar-brand-glyph` | M |
| **UX-RD-FONTS-01** | restaurar escala 11/12/13/14/16/18/20/24/32/40 do mockup; suprimir override Source Code Pro vazando em `.page-title`, `.pill`, `.sprint-tag` | M |
| **UX-RD-MAT-FIX-01** | corrigir vazamento "keyboard_double_arrow_left" via regra `font-family` específica para `[data-testid="stIconMaterial"]` | XS |
| **UX-RD-PLOTLY-01** | passar `config={'displayModeBar': False}` em todas as chamadas `st.plotly_chart`; criar template Plotly Dracula | S |
| **UX-RD-KPIGRID-01** | trocar `minmax(220px, 1fr)` por `minmax(180px, 1fr)` (`tema_css.py:1158`) | XS |
| **UX-RD-LINT-01** | corrigir 11 erros de acentuação em .md | XS |
| **UX-RD-CIT-01** | citação filosófica em 60 .py novos | XS |
| **UX-RD-CRUMB-01** | converter `.breadcrumb .seg` em `<a href>` clicável | XS |
| **UX-RD-A11Y-01** | adicionar skip links + role="tablist" + aria-current | S |

**13 sprints corretivas** -- 6× XS (1-2h cada), 4× S (1 dia), 3× M (3-5 dias). Roteiro total: ~3 semanas para fechar todos os deltas.

---

## Anexos

- Logs:
  - `/tmp/auditoria_redesign/logs/{lint,smoke,pytest}.log` (gauntlet)
  - `/tmp/auditoria_redesign/logs/{cap_mockups,cap_dashboard,cap_features}.log` (capturas)
  - `/tmp/auditoria_redesign/logs/{medir_estilos,medir_estetica2,medir_diff_componentes,medir_anim_dim,medir_dim_hover_focus,letra_morta,validar_classes_aplicadas}.log` (medição UI/UX detalhada)
- Capturas: `.playwright-mcp/auditoria/{mockups,dashboard}/*.png`
- Plano da auditoria: `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md`
- Mockup canônico (referência): `novo-mockup/_shared/{tokens.css,components.css,glyphs.js,shell.js}`
- Sub-agentes Explore (5): tema componentes, animações, gráficos, UX patterns, 29 telas -- transcripts em `/tmp/claude-1000/.../tasks/<id>.output`

---

*"Não basta ter olhos abertos: é preciso ver." -- Honoré de Balzac*
