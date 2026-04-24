# ADR-22 — Navegação em 5 clusters (reorganização das 13 abas)

**Status:** ACEITO
**Data:** 2026-04-24
**Sprint:** 92b
**Substitui:** nada (complementa ADR-19 sobre interatividade)
**Reservado original:** ADR-22 estava reservado para fusão total da Sprint 94 (conforme commit a79a6f3). Esta ADR assume o número por decisão do dono em 2026-04-24 — Sprint 94 herdará próximo número livre (ADR-23).

## Contexto

Auditoria de UX 2026-04-23 (`docs/ux/audit_2026-04-23.md` §3 e §5 item 5) identificou que o dashboard expunha 13 abas flat em linha única via `st.tabs([...])`. Consequências observadas em telas 1600x1000 e inferiores:

- **Overflow horizontal**: 13 abas com rótulos PT-BR (ex: "Grafo + Obsidian", "Busca Global") não cabem numa linha; Streamlit rola lateralmente e a aba 12-13 some atrás da borda direita.
- **Hierarquia invisível**: "Metas" (uma aba isolada) pesa tanto quanto "Extrato" (o hub central). Não há sinal visual de que Visão Geral é o ponto de entrada.
- **Cognição fragmentada**: abas adjacentes não compartilham domínio (Categorias → Extrato → Contas → Pagamentos → Projeções → Metas → Análise misturam fluxos financeiros, análise e metas).
- **Audit item 5**: recomendou agrupamento em ~5 clusters seguindo modelo mental do usuário.

Sprint 92a já entregou polish cirúrgico (hero numbering 01-13, contraste treemap WCAG, labels humanos no pyvis, etc.). 92a mantém a estrutura flat; 92b reorganiza a navegação.

## Decisão

Adotar **hierarquia de 2 níveis** na navegação do dashboard:

1. **Nível 1 — Cluster** (`st.sidebar.radio`): 5 áreas canônicas, horizontais no topo da sidebar abaixo do logo.
2. **Nível 2 — Aba** (`st.tabs`): apenas as abas daquele cluster, renderizadas no corpo principal.

### Mapa canônico dos 5 clusters

| Cluster | Abas absorvidas | Hero numbers |
|---|---|---|
| Hoje | Visão Geral | 01 |
| Dinheiro | Extrato, Contas, Pagamentos, Projeções | 02–05 |
| Documentos | Catalogação, Completude, Busca Global, Grafo + Obsidian | 06–09 |
| Análise | Categorias, Análise, IRPF | 10–12 |
| Metas | Metas | 13 |

### Session state namespace

- `cluster_ativo` — chave nova (domínio exclusivo do radio). Não colide com `filtro_*` (drill-down), `avancado_*` (filtros manuais Extrato) ou `seletor_*` (outros selectbox da sidebar).

### URL schema (backward compatibility)

- **URL antiga** (`?tab=Extrato&categoria=Farmácia`) continua funcionando: `ler_filtros_da_url` infere cluster="Dinheiro" via `MAPA_ABA_PARA_CLUSTER`.
- **URL nova** (`?cluster=Dinheiro&tab=Extrato&categoria=Farmácia`) ativa cluster explicitamente.
- Campo `cluster` incluído na whitelist de `CAMPOS_FILTRO_RECONHECIDOS` do leitor.

## Alternativas consideradas

1. **Manter 13 abas flat + CSS wrap.** Descartado: `st.tabs` não suporta wrap nativo; CSS custom quebraria tema Dracula e acessibilidade de teclado.
2. **Menu de nível único via `st.selectbox` (dropdown).** Descartado: perde a fixação visual das áreas; usuário perde noção de "onde estou".
3. **Multi-page app nativo (`pages/`).** Descartado: exigiria refatoração profunda (cada aba hoje recebe `dados, periodo, pessoa, ctx` — multi-page app quebra estado compartilhado); migração cabe numa sprint INFRA futura, não nesta.
4. **6 clusters (separar IRPF de Análise).** Descartado: IRPF é análise tributária, alinha semanticamente com Categorias/Análise; 5 clusters dá carga cognitiva menor (±7 é o limite de Miller, 5 está folgado).

## Consequências

### Positivas

- Sidebar única com escolha clara de área; corpo principal limpo com 1–4 abas.
- Hero numbering (01–13) da Sprint 92a preservado e ganha função: sinaliza a ordem sugerida de consumo mesmo dentro do cluster.
- URL compartilhável explicitamente (`?cluster=X&tab=Y`) facilita deep-linking em ferramentas externas (email, Obsidian).
- Backward compatibility: toda URL gravada por drill-down anterior continua válida.

### Negativas

- Mudança de cluster força `rerun` completo do Streamlit (carrega apenas 1–4 páginas; aceitável).
- Usuário acostumado com `st.tabs` flat precisa re-aprender um passo (cluster → aba). Mitigação: radio "Área" é sempre visível, acima das abas.

## Rollback plan

Reverter a navegação em 1 commit:

1. `git revert <commit-da-92b>` — reverte `app.py`, `drilldown.py`, testes e ADR em bloco.
2. Alternativa manual (se o revert tiver conflitos com sprints posteriores):
   - Em `src/dashboard/app.py::main`, remover bloco `st.sidebar.radio("Área", ...)` e `if cluster == "..."` branches.
   - Restaurar `st.tabs([...])` com as 13 abas na ordem original.
   - Em `src/dashboard/componentes/drilldown.py`, remover `cluster` de `CAMPOS_FILTRO_RECONHECIDOS` e remover `MAPA_ABA_PARA_CLUSTER`.
3. Rodar `.venv/bin/pytest tests/ -q` — deve voltar ao baseline pré-92b.

Critério para disparar rollback:

- Usuário relata confusão recorrente em 3+ sessões.
- Performance de troca de cluster piora >500ms em amostragem real.
- Bug de session state em `cluster_ativo` produz tela branca sem repro determinístico.

## Testes de regressão obrigatórios

1. `test_cluster_ativo_persistido_em_session_state` — radio grava em `st.session_state["cluster_ativo"]`.
2. `test_url_antiga_infere_cluster` — `?tab=Extrato` sem `cluster` infere `Dinheiro` via `MAPA_ABA_PARA_CLUSTER`.
3. `test_url_nova_ativa_cluster_explicito` — `?cluster=Dinheiro&tab=Extrato` ativa cluster explicitamente.
4. `test_whitelist_inclui_cluster` — `CAMPOS_FILTRO_RECONHECIDOS` contém `"cluster"`.
5. Baseline pytest ≥1456 passed preservado (testes existentes de renderização por página continuam verdes).

## Relacionamento com outras ADRs

- **ADR-19** (drill-down): mantida. `aplicar_drilldown` continua gravando `?tab=X` + filtros; Sprint 92b apenas enriquece o leitor para também lidar com `cluster`.
- **ADR-20** (tracking documental): não afetada.
- **ADR-18** (Controle de Bordo): não afetada.

---

*"A hierarquia não é opressão, é clareza: sabe onde está, sabe para onde ir." — princípio de arquitetura da informação*
