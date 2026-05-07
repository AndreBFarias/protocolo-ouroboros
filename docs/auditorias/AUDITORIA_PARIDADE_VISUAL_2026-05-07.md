---
titulo: Auditoria de paridade visual — mockup canônico × dashboard real
data: 2026-05-07
escopo: 29 páginas (todos os 5 clusters + Bem-estar)
metodo: comparação side-by-side via claude-in-chrome MCP, viewport 1568×685
fonte_canonica: novo-mockup/mockups/*.html
fonte_real: http://localhost:8501 (commit 1644e44 pós-Onda M)
---

# Auditoria de paridade visual — 2026-05-07

## Contexto

Pedido do dono em 2026-05-07: **prioridade ZERO é estética/UI/UX** antes de qualquer bloco fundamental novo. Objetivo: tudo igual ao mockup canônico + filtro global.

Esta auditoria mapeia divergências sistemáticas entre `novo-mockup/mockups/*.html` (29 mockups) e o dashboard real (Streamlit, 36 páginas). Compilada após Onda M completa (modularização entregou fronteiras `ui.py` + `css/paginas/` + tokens canônicos), portanto a base CSS está pronta para receber a paridade.

## Padrões macro identificados

### P1 — "Filtros globais" expander (presente no dashboard, ausente no mockup)

Todo cluster do dashboard renderiza no topo um expander `> Filtros globais` (sidebar global de pessoa A/B/casal · período · forma de pagamento). Os mockups começam direto no `page-header` — não têm essa barra.

**Decisão pendente do dono**: 
- Opção A: remover do dashboard (pixel-perfect com mockup; sacrifica filtros globais).
- Opção B: estilizar como "filtro global flutuante" (ex.: chip-bar fina entre breadcrumb e header, idêntica em todos os clusters; mantém função sem poluir layout) — **recomendação** porque filtros globais resolvem problema real (drilldown, comparação A/B).
- Opção C: mover para dentro da sidebar como dropdown único (mais radical).

### P2 — Micro-componentes visuais ausentes (alto impacto, baixo custo)

Mockup tem elementos que o dashboard cortou ou nunca implementou:

| Elemento | Onde no mockup | Status no dashboard |
|---|---|---|
| **Sparkline** em cards de conta | Contas (3 cartões) | Ausente |
| **Barra de uso %** em cartões de crédito | Contas (Nubank/C6 cartão com 36%/24% usado) | Ausente |
| **Pílulas/chips coloridas em datas** do calendário | Pagamentos | Parcial (só algumas datas) |
| **Setas de navegação mês** + cabeçalho de meses | Pagamentos | Ausente (só "próximos 14 dias") |
| **Botões de ação inline** "pagar"/"agendar"/"ver" em listas | Pagamentos, Eventos | Ausente |
| **Donuts %** no canto superior direito de cards de meta | Metas (6 donuts visuais) | Parcial (só 3, sem layout integrado) |
| **3 colunas (PRAZO/RITMO/FALTA)** por meta | Metas | Ausente (só prazo) |
| **Counters nas tabs** (ex.: "Fluxo de caixa **3**", "Categorias **6**") | Análise | Ausente |
| **Insights derivados** (4 cards: Positivo/Atenção/Descoberta/Previsão) | Análise lateral direita | Ausente |
| **% vs anterior** ou "+8% vs ano anterior" em KPIs | Análise, vários | Ausente |
| **Barra de uso global** topo de página (8 alarmes ativos / 8/8 tags compiladas / etc.) | IRPF, Rotina, várias | Parcial |
| **Calendário visual lateral** | Eventos | Ausente |
| **Bar chart "Distribuição por tipo"** | Eventos | Substituído por texto "Bairros frequentes" |
| **Cobertura por cluster** com bar chart | Skills D7 | Ausente (fallback graceful) |

### P3 — Páginas Bem-estar com dado vazio (origem mobile, não desktop)

Mockups demonstram dados sintéticos completos. Dashboard real tem páginas Bem-estar (Hoje, Humor, Diário, Eventos, Rotina, Alarmes, Treinos, Tarefas, Contadores, Ciclo, etc.) que dependem de dados oriundos do **`Protocolo-Mob-Ouroboros`** (companion Android Expo + React Native que escreve `.md` no vault Obsidian compartilhado). Desktop só **lê** do vault e gera caches em `.ouroboros/cache/*.json`.

Estado atual do mob (2026-05-07): **em refundação golden-zebra** (HEAD `eca0a1e`, plano de 21 sprints M21-M41, ~50-60h ativos restantes para republicar v1.0.0). Bloco H (fundação vault canônica) fechado; Bloco I (saves por feature) com 5/15 fechados (I-HUMOR, I-DIARIO, I-EVENTO, I-FRASE, I-DEVICES `[ok]`; I-FOTO, I-AUDIO, I-VIDEO, I-TAREFA, I-ALARME, I-CONTADOR, I-CICLO, I-EXERCICIO, I-SCANNER, I-AGENDA `[todo]`).

**Decisão correta** (atualizada após investigar `Protocolo-Mob-Ouroboros/STATE.md` + `ROADMAP.md`):

- ~~Skill `/semear-demo`~~ — **REJEITADA**. Inventaria dados quando o pipeline real (mob → vault → cache → dashboard) já existe e está em estabilização. Violaria invariante "nunca inventar dados" (CLAUDE.md regra 6).
- **Decisão escolhida**: redesenhar fallback como **"estado inicial atrativo + CTA mob"**. Cada página Bem-estar com dado ausente mostra:
  - Skeleton-mockup do layout final (igual ao mockup canônico, mas estilizado como placeholder claro)
  - CTA explicando que o registro vem do app mobile Ouroboros: "Use o app Android Ouroboros Mobile para começar a registrar humor/diário/eventos. Os dados aparecem aqui automaticamente após sync."
  - Link para `protocolo-ouroboros/run.sh --sync` (dispara `obsidian/sync_rico.py`)
  - Indicador "última sync: <data>" (lido de `.ouroboros/cache/last_sync.json`)
- **Sprint adicional**: validar que o pipeline vault → cache → dashboard funciona quando vault tem dados (testar com vault sintético + assert que páginas saem do fallback automaticamente).

### P4 — Sidebar do dashboard tem mais items que mockup

| Mockup sidebar (00-shell-navegacao) | Dashboard sidebar |
|---|---|
| HOME (Visão Geral) | HOME (Visão Geral, Finanças, Documentos, Análise, Metas) |
| INBOX | INBOX (Inbox) |
| FINANÇAS (Extrato/Contas/Pagamentos/Projeções) | FINANÇAS (idem) |
| DOCUMENTOS (Busca/Catalogação/...) | DOCUMENTOS (Busca/Catalogação/Completude/Revisor/Validação por Arquivo/Grafo + Obsidian) |
| ANÁLISE (Categorias/Análise/IRPF) | ANÁLISE (Categorias/Análise/IRPF + outras?) |
| METAS, SISTEMA, BEM-ESTAR | METAS, SISTEMA, BEM-ESTAR |

Diferença sutil: dashboard tem mais subitens em HOME ("Visão Geral, Finanças, Documentos, Análise, Metas" como links rápidos) — mockup tem só "Visão Geral".

### P5 — Topbar-actions inconsistentes com mockup

Mockup tem topbar de ações específicas e elegantes por página (ex.: "Comparar cenários" / "Salvar cenário" em Projeções; "Calendário" / "Novo evento" em Eventos). Dashboard tem **maioria igual ao mockup** (parabéns à Onda U-02), mas:

- Em algumas páginas, dashboard mostra rotulagem ligeiramente diferente ("Atualizar" vs "Recalcular") — divergência cosmética.
- Botão `primary` do mockup tem ícone "+" prefixado em alguns ("+ Novo evento", "+ Adicionar conta"); dashboard só tem texto.
- Algumas páginas têm o ícone glyph antes do texto no mockup; dashboard sem ícone.

### P6 — Hierarquia visual: mockup mais "compacto", dashboard mais "espacejado"

Mockup tem density maior (margins/paddings menores) que o dashboard real Streamlit. Quase todos os screenshots mostram que o mockup mostra MAIS conteúdo no mesmo viewport. Causa: spacing tokens canônicos (`var(--sp-*)`) já existem mas não são consumidos consistentemente em todas as páginas.

## Divergências por página

| # | Página | Estado | Prioridade |
|---|---|---|---|
| 01 | **Visão Geral** | KPIs OK, hero OK, mas faltam ícones/tipos coloridos em "Atividade Recente"; cards dos clusters estão simplificados (3 visíveis vs 6 do mockup) | ALTA |
| 02 | **Extrato** | KPIs OK, Saldo 90d OK, Breakdown OK, Origens OK. Falta: filt-bar inline canônica `.t02-filt-bar` (mockup tem CONTA/CATEGORIA/PERÍODO/BUSCA/só saídas/com sidecar); lista por dia com pílulas coloridas (mockup: "2026-04-30 · QUI" header + linhas com tipos NB/IF/PX); valores tabulares à direita | MÉDIA (já tem o essencial) |
| 03 | **Contas** | **DIVERGÊNCIA ALTA**: ausentes sparkline por conta, barras de uso de cartão, separação Contas Correntes vs Cartões de Crédito, ícone+sigla do banco no canto, "último OFX/sha8/sincronizado/txns 30d" estruturado | ALTA |
| 04 | **Pagamentos** | **DIVERGÊNCIA ALTA**: dashboard mostra só 14 dias, mockup mostra mês inteiro 5 semanas; botões pagar/agendar ausentes; valores na lista lateral ausentes; legenda fixo/variável/cartão/em atraso no rodapé do calendário | ALTA |
| 05 | **Projeções** | OK pós-fix `tema_plotly.py`. Falta: 4 KPIs (mockup tem APORTE MENSAL slider + RETORNO slider + HORIZONTE select); gráfico do mockup é SVG nativo com dashed lines (3 cenários) e marcos in-line, dashboard usa Plotly | BAIXA (Plotly é OK funcionalmente) |
| 06 | **Busca Global** | OK. Search-bar canônico + chips renderizam. Falta: facet-card lateral (TIPO/PERÍODO/CONTA/CATEGORIA com counts) que aparece quando há resultados; res-group com snippet highlight `<mark>` | MÉDIA |
| 07 | **Catalogação** | **DIVERGÊNCIA ESTRUTURAL**: mockup mostra grid 4×3 de **thumbs de arquivos** com badges PDF/IMG/CSV/XLSX/OFX; dashboard mostra KPIs agregados + cards por tipo de documento. São DUAS visões diferentes do mesmo dado. | DECIDIR: qual prevalece? |
| 08 | **Completude** | **DIVERGÊNCIA ALTA**: faltam 4 KPIs do topo (Cobertura Global, Tipos Completos, Lacunas Críticas, Lacunas Médias); eixos do heatmap diferentes (mockup: tipos de doc; dashboard: categorias de transação); legenda completo/parcial/ausente ausente | ALTA |
| 09 | **Revisor** | (não capturado por bloqueio iframe Chrome) | INVESTIGAR |
| 10 | **Validação por Arquivo / Extração Tripla** | **DIVERGÊNCIA ESTRUTURAL CRÍTICA**: mockup tem layout 3 colunas (lista de arquivos agrupados por TIPO + tabela ETL × Opus × Validação humana com PARIDADE 80%/divergências em laranja/CONSENSO/DIVERGENTE flags + botão Enviar validação); dashboard atual mostra layout 2-col (lista PDF + PDF viewer) — **funcionalidade central do mockup ausente** | ALTÍSSIMA |
| 11 | **Categorias** | OK. Árvore + treemap renderizando. Falta: botões "expandir tudo / por valor" no header; "Regras de auto-classificação" como bloco lateral inferior detalhado | BAIXA |
| 12 | **Análise** | KPIs + Sankey OK. Falta: **Insights Derivados** (4 cards Positivo/Atenção/Descoberta/Previsão) lateral direita; counters nas tabs; "+8% vs ano anterior" em KPIs | ALTA |
| 13 | **Metas** | **DIVERGÊNCIA ALTA**: dashboard mostra 3 metas em layout simples; mockup mostra 6 cards com (donut % topo + valor/total + barra progresso + 3 colunas PRAZO/RITMO/FALTA); seção "Metas Operacionais · Pipeline" ausente | ALTA |
| 14 | **Skills D7** | Dashboard em fallback graceful (data/output/skill_d7_log.json ausente). Mockup mostra: 5 KPIs no topo + Inventário 18 skills com pills D7 + Distribuição por estado + Cobertura por cluster. **Sprint para semear log_d7 + popular layout completo** | ALTA |
| 15 | **IRPF** | OK estrutural. Faltam 2 das 8 categorias canônicas (inss_retido, doacao_dedutivel) — específico desse ano sem dado; barras de progresso por categoria com cores (≥90%/70-90%) ausentes; botões expand/baixar (>) por categoria ausentes | MÉDIA |
| 16 | **Inbox** | OK pós-Onda M. Dropzone + chips PDF/CSV/etc renderizando. Mockup tem fila densa com sidecar + filtros/agrupar — dashboard fila vazia ok | BAIXA |
| 17 | **Bem-estar / Hoje** | Form OK (sliders/sono/medicação/tags). Mockup tem cards laterais com "Status do casal últimos 7 dias" (Pessoa A/B com 3.8/3.2 e barras), "Próximos alarmes & tarefas" rico, "Registros de hoje" timeline | MÉDIA |
| 18 | **Bem-estar / Humor** | Heatmap renderiza mas vazio (1 célula). Mockup heatmap colorido 13×7 + cards laterais (Média/Registros/Streak/Detalhe do dia interativo). **Sprint para popular dados de exemplo** | ALTA |
| 19 | **Bem-estar / Diário** | Renderiza com 1 entrada. Mockup tem 3-col (filtros + form NOVA ENTRADA com tabs Trigger/Vitória/Reflexão/Observação + intensidade pílulas + tags) — dashboard tem só lista pobre | MÉDIA |
| 20 | **Bem-estar / Rotina** | Dashboard mostra erro "rotina.toml não encontrado". Mockup tem KPIs (Tarefas Hoje 3/7, Próximo Alarme 22:00, Streak 47 dias, Conclusão Semanal 82%) + 3 colunas (ALARMES 8 / TAREFAS HOJE / CONTADORES 5). **Sprint: redesenhar fallback OU semear rotina.toml** | ALTA |
| 21 | **Recap** | **DIVERGÊNCIA ARQUITETURAL**: mockup propõe NARRATIVA por LLM (M30: Claude Sonnet via API) + Comparativo vs 30D anteriores (rica tabela com %) + Destaques do mês (5 cards coloridos por categoria); dashboard tem versão determinística (KPIs humor/eventos/treinos/peso + bar chart simples) explicitamente sem narrativa LLM (ADR-13). **Decisão**: manter dashboard determinístico (ADR-13 vence) MAS adicionar Comparativo vs 30D estruturado e Destaques do mês como blocos | MÉDIA |
| 22 | **Bem-estar / Eventos** | Dashboard mostra 1 evento + filtros laterais. Mockup tem timeline rica + calendário visual lateral + Distribuição por tipo + Cruzamento com humor | ALTA |
| 23 | **Memórias** | **DIVERGÊNCIA ESTRUTURAL ALTA**: mockup mostra 12 cápsulas multimídia em grid 7+5 (FOTO/ÁUDIO/TEXTO/VÍDEO com gradientes coloridos, badges, chips de categoria, dados meta como duração/evento vinculado); dashboard mostra heatmap de treinos 91 dias + tabs (Treinos/Fotos/Marcos). **São páginas diferentes funcionalmente** — Memórias do mockup é cápsulas multimídia, Memórias do dashboard é heatmap. Mob deve gravar cápsulas (foto/áudio/texto/vídeo) → desktop renderiza grid; sprint mob-bridge necessária | ALTA |
| 24 | **Medidas** | Dashboard em fallback callout. Mockup tem Toggle Pessoa A/B + 6 cards (Peso/Gordura corp/Cintura/Pressão/Frequência rep/Sono médio) com sparklines + variação 30d + tabela Histórico semanal 6 semanas | ALTA (depende de mob popular medidas/) |
| 25 | **Ciclo** | Dashboard em fallback callout. Mockup tem **anel circular gigante** com fases coloridas (Menstrual/Folicular/Fértil/Lútea), dia atual destacado + Sintomas hoje (escala 0-3 dots) + Cruzamento ciclo × humor (12 ciclos) + cards de fase + Privacidade. Visualização **muito rica**, requer SVG ou Plotly polar | ALTA (depende de mob popular ciclo/) |
| 26 | **Cruzamentos** | **DIVERGÊNCIA ESTRUTURAL ALTA**: mockup é **builder dinâmico de queries** (3 dropdowns Métrica × Cruzar com × Filtro/Janela) + Resultado scatter plot 90d com correlação +0.55 + Perguntas pré-prontas (8 sugestões clicáveis) + Insights desta query (3 cards com confiança%); dashboard tem versão simplificada com 3 expanders fechados (Humor × Eventos / Humor × Medidas / Treinos × Humor) com 1 gráfico hardcoded por expander | ALTA |
| 27 | **Privacidade** | **DIVERGÊNCIA ESTRUTURAL MASSIVA**: mockup tem privacidade granular **4 níveis** (Oculto/Agregado/Resumo/Total) **bidirecionais** (A→B e B→A separados) por campo (humor/diário/eventos/medidas/treinos/ciclo) com radio buttons + cards laterais (vault id, último sync, features opcionais) + Audit log; dashboard tem **6 toggles binários** Humor/Diário/Eventos/Medidas/Treinos/Ciclo + Salvar/Resetar. Privacidade do mockup é projeto inteiro novo | ALTÍSSIMA (decisão arquitetural) |
| 28 | **Editor TOML** | **DIVERGÊNCIA ALTA**: mockup tem layout 3-col (lista arquivos `manha.toml`/`tarde.toml`/`noite.toml`/`medicacao.toml`/`fim-de-semana.toml` com counts + editor central com syntax-highlight + Preview ao vivo direita com tabs Visual/Diff/Schema mostrando alarmes renderizados + Validação 0 erros/1 aviso por linha + "Vai afetar"); dashboard tem editor único de `rotina.toml` simples sem preview/validação inline | ALTA |
| 09 | **Revisor** | **NÃO CAPTURADO** (iframe Chrome bloqueia screenshot via claude-in-chrome — `about:blank#blocked`). Funcional via dashboard direto, mas precisa investigação manual ou MCP playwright para auditar mockup vs implementação | INVESTIGAR (workaround playwright) |

## Levas propostas (paridade visual antes dos blocos fundamentais)

### Onda V (visual parity) — antes de qualquer DOC/LLM/MOB/FONTE

Princípio: cada sprint da Onda V toca uma página inteira ou um padrão transversal. Roda em executor-sprint isolado (worktree). Validação visual side-by-side obrigatória contra mockup canônico (skill `validacao-visual`).

#### Leva V-1 — Padrões transversais (precedem todas as outras)

| Sprint | Escopo | Esforço | Bloqueia |
|---|---|---|---|
| **UX-V-01-FILTRO-GLOBAL** | Decidir Opção A/B/C; implementar canônico do filtro global em todas as páginas | 3-4h | todas |
| **UX-V-02-MICRO-COMPONENTES** | Adicionar a `ui.py`: `sparkline_html`, `bar_uso_html`, `donut_inline_html`, `prazo_ritmo_falta_html`, `tab_counter_html`, `insight_card_html`. Adicionar classes `.sparkline`, `.bar-uso`, `.donut-mini`, etc. em `components.css` (canonização) | 4-5h | V-2.x |
| **UX-V-03-FALLBACK-MOB** | Redesenhar fallbacks de páginas Bem-estar com dado ausente como "skeleton do mockup + CTA app mobile + última sync". Origem dos dados é `Protocolo-Mob-Ouroboros` (em refundação golden-zebra) → vault Obsidian → `.ouroboros/cache/*.json` → dashboard. Sem semear demo. | 4-5h | V-2.x |
| **UX-V-04-SYNC-OBSERVABILIDADE** | Sprint para tornar o pipeline vault → cache visível no dashboard: indicador "última sync" canônico em todas páginas Bem-estar, log estruturado de sync em `.ouroboros/cache/last_sync.json`, validação que páginas saem do fallback automaticamente quando cache tem dados. | 3h | V-2.x |
| **UX-V-05-TOPBAR-ICONES** | Adicionar glyphs (`+`, `-`, `>`, `~`, `*`) em todos os botões de topbar-actions conforme mockup canônico | 2h | V-2.x |

**Leva V-1 total**: ~14-18h.

#### Leva V-2 — Páginas com divergência ALTA/ESTRUTURAL (paralelos ~6h cada)

| Sprint | Página | Foco principal | Esforço |
|---|---|---|---|
| **UX-V-2.1-CONTAS** | Contas | sparkline + barras uso + separação Contas/Cartões | 4h |
| **UX-V-2.2-PAGAMENTOS** | Pagamentos | calendário mês inteiro + lista lateral com botões + legenda rodapé | 5h |
| **UX-V-2.3-COMPLETUDE** | Completude | 4 KPIs no topo + redesenhar eixos (tipos doc vs categorias) | 4h |
| **UX-V-2.4-VALIDACAO-TRIPLA** | Validação por Arquivo / Extração Tripla | Layout 3-col com tabela ETL × Opus × Humano completa, paridade %, divergências flag, Enviar validação | 8h (mais alta) |
| **UX-V-2.5-METAS** | Metas | 6 cards com donut+valor+barra+3 colunas; seção operacional | 5h |
| **UX-V-2.6-ANALISE** | Análise | Insights Derivados lateral + counters nas tabs + +X% vs anterior em KPIs | 4h |
| **UX-V-2.7-VISAO-GERAL** | Visão Geral | 6 cards de cluster completos + Atividade Recente com ícones | 3h |
| **UX-V-2.8-SKILLS-D7** | Skills D7 | popular log_d7_log.json + render layout completo (depende de V-1.4) | 4h |
| **UX-V-2.9-EVENTOS** | Bem-estar / Eventos | calendário visual + Distribuição por tipo + Cruzamento humor | 5h |
| **UX-V-2.10-ROTINA** | Bem-estar / Rotina | KPIs + 3 colunas Alarmes/Tarefas/Contadores | 5h |

**Leva V-2 total**: ~47h estimados, paralelizáveis em 4-5 worktrees → ~12h wall clock.

#### Leva V-3 — Páginas com divergência MÉDIA/BAIXA (cleanup)

| Sprint | Página | Foco | Esforço |
|---|---|---|---|
| **UX-V-3.1-EXTRATO-FILT** | Extrato | filt-bar inline canônica + lista por dia com pílulas | 3h |
| **UX-V-3.2-BUSCA-FACET** | Busca Global | facet-card lateral + res-group com snippet highlight | 3h |
| **UX-V-3.3-CATALOGACAO-RECONCILIAR** | Catalogação | decidir vista grid-de-thumbs (mockup) ou KPIs+tipos (atual); implementar consenso | 4h (depende de decisão) |
| **UX-V-3.4-IRPF-FINISH** | IRPF | 2 categorias faltantes + barras progresso colorido + botões expand | 2h |
| **UX-V-3.5-BE-HOJE-CARDS** | Be-hoje | card "Status casal" + "Próximos alarmes" + "Registros do dia" | 4h |
| **UX-V-3.6-BE-HUMOR-DEMO** | Be-humor | popular cache demo + cards laterais Streak/Detalhe interativo | 3h |
| **UX-V-3.7-BE-DIARIO** | Be-diário | form NOVA ENTRADA com tabs Trigger/Vitória/Reflexão/Observação | 3h |

**Leva V-3 total**: ~22h, paralelizáveis → ~6h wall clock.

#### Leva V-2 (continuação) — páginas adicionais ALTA/ALTÍSSIMA descobertas em 2026-05-07

| Sprint | Página | Foco principal | Esforço |
|---|---|---|---|
| **UX-V-2.11-MEMORIAS** | Memórias | Grid de cápsulas multimídia (foto/áudio/texto/vídeo) com gradientes; depende de mob gravar memórias em vault | 5h (depende mob I-FOTO/I-AUDIO/I-VIDEO) |
| **UX-V-2.12-MEDIDAS** | Medidas | 6 cards com sparkline + variação 30d + tabela histórico 6 semanas; toggle Pessoa A/B; depende mob popular `medidas/` | 5h |
| **UX-V-2.13-CICLO** | Ciclo | Anel circular SVG com fases + sintomas + cruzamento humor + cards de fase; depende mob popular `ciclo/` (I-CICLO M21-M41) | 6h (alto custo SVG) |
| **UX-V-2.14-CRUZAMENTOS** | Cruzamentos | Builder dinâmico (3 dropdowns) + scatter plot + perguntas pré-prontas + insights confiança%; muda paradigma da página | 8h (mais alta — refazer feature) |
| **UX-V-2.15-PRIVACIDADE** | Privacidade | 4 níveis × bidirecional × 6 campos (24 radio buttons) + cards laterais + audit log; **decisão arquitetural** sobre permissões granulares | 10h (altíssima — feature nova) |
| **UX-V-2.16-EDITOR-TOML** | Editor TOML | Layout 3-col com lista arquivos + editor + preview ao vivo + validação inline | 6h |
| **UX-V-2.17-RECAP** | Recap | Comparativo vs 30D anteriores estruturado + Destaques do mês (5 cards); MANTER ADR-13 (sem LLM API) | 4h |

**Total Leva V-2 expandida**: 47h iniciais + 44h adicionais = **~91h**, paralelizáveis em 5-7 worktrees → **~14h wall clock**.

#### Leva V-mob (sprints que dependem do Protocolo-Mob-Ouroboros)

Estas sprints só fecham 100% quando o mob v1.0.0 republicar (após blocos H/I/I2/J/K/L/N/O/P do golden-zebra). O dashboard pode adiantar **layout + fallback CTA**, mas a paridade visual completa requer o vault populado pelo mob.

| Sprint dashboard | Espera no mob |
|---|---|
| UX-V-2.11-MEMORIAS | I-FOTO + I-AUDIO + I-VIDEO `[todo]` |
| UX-V-2.12-MEDIDAS | bloco mob de medidas (não mapeado no roadmap mob atual) |
| UX-V-2.13-CICLO | I-CICLO `[todo]` |
| UX-V-2.10-ROTINA | I-ALARME + I-CONTADOR + I-TAREFA `[todo]` |
| UX-V-2.8-SKILLS-D7 | independe do mob (gerado pelo desktop) |
| UX-V-3.6-BE-HUMOR | I-HUMOR `[ok]` (mob já grava) — **dashboard só precisa testar com vault populado** |
| UX-V-3.7-BE-DIARIO | I-DIARIO `[ok]` (mob já grava) — **dashboard só precisa testar com vault populado** |

**Recomendação**: priorizar sprints da Onda V que **NÃO dependem do mob** (UX-V-1.x, UX-V-2.1 até V-2.7, V-2.14, V-2.15, V-2.16, V-2.17, V-3.x exceto BE-*) primeiro. Sprints que dependem do mob ficam bloqueadas por gate sync.

#### Leva V-4 — Revisor (não-capturado por bloqueio iframe)

Único: investigar Revisor via MCP playwright (que renderiza iframe interno) ou via screenshot manual. Sprint UX-V-4-REVISOR a ser criada após captura.

**Estimado**: 1 sprint (2-4h dependendo de divergências achadas).

## Ordem operacional recomendada

```
1. UX-V-01-FILTRO-GLOBAL (decisão arquitetural)
2. UX-V-02-MICRO-COMPONENTES (paralelo com V-01 — independente)
   ├─ V-03 + V-04 + V-05 (paralelos com V-02)
3. Gate: V-1 verde
4. Leva V-2: 4-5 worktrees paralelos (V-2.1 a V-2.10)
5. Gate: V-2 verde — paridade ALTA atingida
6. Leva V-3: 3-4 worktrees paralelos
7. Gate: V-3 verde — paridade MÉDIA atingida
8. Leva V-4: páginas não-capturadas (TBD)
9. Gate visual final: side-by-side em 29 páginas, dono aprova
10. INÍCIO BLOCOS FUNDAMENTAIS (DOC P0, LLM v2, etc.)
```

**Total Onda V completa (atualizado 2026-05-07)**: ~125-145h estimado, ~30-40h wall clock paralelizado (sprints mob-dependentes ficam aguardando refundação golden-zebra do mob ~50h adicionais).

## Decisões do dono (consolidadas 2026-05-07)

| # | Tópico | Decisão | Implicação |
|---|---|---|---|
| 1 | Filtro global | **Chip-bar fina canônica** entre breadcrumb e header | UX-V-01-FILTRO-GLOBAL é remodelagem, não remoção |
| 2 | Catalogação | **Híbrido** — KPIs+tipos no topo (atual) + grid de thumbs abaixo | UX-V-3.3-CATALOGACAO-RECONCILIAR adiciona grid sem remover |
| 3 | Estado vazio Bem-estar | **Fallback skeleton + CTA app mob** (sem semear demo); origem dos dados é Mob → vault → cache | UX-V-03-FALLBACK-MOB + UX-V-04-SYNC-OBSERVABILIDADE |
| 4 | Pixel-perfect | **Mockup é norte, adaptado é OK** | Cada sprint documenta divergências aceitas no spec |
| 5 | Privacidade | **Feature granular completa** (4 níveis × bidirecional × 6 campos = 24 radios + audit log + cards laterais) | UX-V-2.15-PRIVACIDADE vira feature nova substancial (~10h); requer ADR novo (Privacidade Granular A↔B) + schema TOML novo (`permissoes.toml`) |
| 6 | Cruzamentos | **Builder dinâmico + 3 padrões default como perguntas pré-prontas** | UX-V-2.14-CRUZAMENTOS vira ~10h (não 8h); preserva os 3 expanders como sugestões clicáveis no builder |
| 7 | Recap LLM | **ADR-13 vence** — Recap dashboard fica determinístico; narrativa vira skill `/gerar-recap` (Opus interativo, salva em `docs/recaps/<mes>.md`, dashboard exibe quando existe) | UX-V-2.17-RECAP fica determinístico + adicionar Comparativo 30D + Destaques + bloco "narrativa do mês (gerada manualmente via /gerar-recap)" |

## Anexos

- Screenshots: capturados em sessão claude-in-chrome MCP, viewport 1568×685, save_to_disk via tool. Comparação binária preservada na conversa.
- Mockups vs páginas: arquivo `mockups/00-shell-navegacao.html` é shell macro; cada página numerada (01-28) corresponde 1:1 a uma página dashboard (mapeamento em `MAPA.md` futuro).

*"O que se mede, se gerencia. O que se vê lado a lado, se corrige." — Onda V*
